"""H2.8: garantía comprobable de que ninguna muestra llega a disco (REQ-PRIV-002).

Tres capas, todas usadas por ``tests/live/test_no_disk.py`` y por la ejecución en directo:

(a) **Estática** (``scan_package``): AST de ``live/``. Prohíbe importar módulos que escriben
    sonido o serializan objetos, las llamadas de NumPy que vuelcan arrays, abrir ficheros en
    escritura (salvo el exportador permitido de H2.13, aún inexistente), ``Path.write_*``,
    ``os.open``/``os.write`` y pasar arrays de sonido a ``print`` o ``logging``.
(b) **Dinámica** (``WriteAudit``): gancho ``sys.addaudithook`` que, mientras está activo, bloquea
    y registra aperturas en escritura, renombrados, borrados, copias de ``shutil`` y conexiones de
    red a destinos que no sean locales; ``snapshot`` compara directorios antes y después.
(c) **Proceso**: ``disable_core_dumps`` (``RLIMIT_CORE = 0``) e ``install_wipe_on_signals``
    (borrado del búfer ante SIGINT/SIGTERM).

Riesgo residual declarado: la memoria del proceso puede paginarse a la swap del sistema; no se
puede impedir desde Python sin privilegios (macOS cifra la swap; comprobado con ``sysctl
vm.swapusage`` en el registro de tareas).
"""

from __future__ import annotations

import ast
import os
import re
import resource
import signal
import sys
import threading
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any

LIVE_DIR = Path(__file__).resolve().parent

FORBIDDEN_MODULES = frozenset(
    {
        "wave",
        "aifc",
        "sunau",
        "soundfile",
        "audioread",
        "pickle",
        "cPickle",
        "dill",
        "joblib",
        "shelve",
        "marshal",
        "sqlite3",
        "dbm",
        "tempfile",
        "scipy.io.wavfile",
        "scipy.io",
    }
)
FORBIDDEN_NUMPY_CALLS = frozenset(
    {"save", "savez", "savez_compressed", "savetxt", "tofile", "memmap", "dump"}
)
FORBIDDEN_METHODS = frozenset({"write_bytes", "write_text", "tofile", "dump"})
FORBIDDEN_OS_CALLS = frozenset({"open", "write", "pwrite", "writev", "replace", "rename"})
LOG_FUNCS = frozenset(
    {"print", "debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
)
# Identificadores que contienen sonido o representaciones suyas: no pueden ir a logs ni a print.
SIGNAL_NAMES = re.compile(
    r"(?i)^(samples?|window|block|indata|emb|embeddings?|scores|audio|buf|segment|resampled|"
    r"arr|wave|signal|ring)$"
)
# Único módulo que podrá abrir un fichero en escritura (H2.13, resumen sin sonido).
EXPORT_ALLOWLIST: frozenset[str] = frozenset({"export.py"})
_WRITE_MODE = re.compile(r"[wax+]")


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.detail}"


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _mode_of_open(call: ast.Call) -> str | None:
    """Modo literal de ``open``; ``"?"`` si no es literal (se trata como escritura)."""
    mode_node: ast.AST | None = call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "mode":
            mode_node = kw.value
    if mode_node is None:
        return "r"
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return mode_node.value
    return "?"


def _signal_args(call: ast.Call) -> list[str]:
    hits: list[str] = []
    for arg in [*call.args, *(k.value for k in call.keywords)]:
        for node in ast.walk(arg):
            name = node.id if isinstance(node, ast.Name) else None
            if isinstance(node, ast.Attribute):
                name = node.attr
            if name and SIGNAL_NAMES.match(name):
                hits.append(name)
    return hits


def scan_source(source: str, filename: str) -> list[Violation]:
    tree = ast.parse(source, filename=filename)
    out: list[Violation] = []
    allow_write = Path(filename).name in EXPORT_ALLOWLIST

    def add(node: ast.AST, rule: str, detail: str) -> None:
        out.append(Violation(filename, getattr(node, "lineno", 0), rule, detail))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES or alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    add(node, "import-prohibido", alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            full = {f"{module}.{a.name}" for a in node.names} | {module}
            if any(m in FORBIDDEN_MODULES or m.split(".")[0] in FORBIDDEN_MODULES for m in full):
                add(node, "import-prohibido", module)
            if module in {"numpy", "os"}:
                bad = FORBIDDEN_NUMPY_CALLS if module == "numpy" else FORBIDDEN_OS_CALLS
                for alias in node.names:
                    if alias.name in bad:
                        add(node, "llamada-prohibida", f"{module}.{alias.name}")
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            head, _, attr = name.rpartition(".")
            if name == "open" or name in {"io.open", "builtins.open"}:
                mode = _mode_of_open(node)
                if (mode == "?" or _WRITE_MODE.search(mode or "")) and not allow_write:
                    add(node, "open-escritura", f"open(..., {mode!r})")
            elif (
                (head in {"np", "numpy"} and attr in FORBIDDEN_NUMPY_CALLS)
                or (head == "os" and attr in FORBIDDEN_OS_CALLS)
                or (attr in FORBIDDEN_METHODS and not allow_write)
            ):
                add(node, "llamada-prohibida", name)
            if (name in LOG_FUNCS or attr in LOG_FUNCS) and (hits := _signal_args(node)):
                add(node, "sonido-en-log", f"{name}({', '.join(hits)})")
    return out


def scan_package(directory: Path = LIVE_DIR) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(directory.rglob("*.py")):
        violations.extend(scan_source(path.read_text(encoding="utf-8"), str(path)))
    return violations


# --- (b) gancho de auditoría -------------------------------------------------------------

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_FS_EVENTS = frozenset(
    {
        "os.rename",
        "os.remove",
        "os.rmdir",
        "os.mkdir",
        "os.truncate",
        "os.link",
        "os.symlink",
        "os.chmod",
        "os.utime",
        "shutil.copyfile",
        "shutil.copymode",
        "shutil.copystat",
        "shutil.copytree",
        "shutil.move",
        "shutil.rmtree",
        "shutil.make_archive",
        "shutil.unpack_archive",
    }
)
_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class AuditViolation(PermissionError):
    """Operación prohibida durante una sesión en directo."""


def _is_write_open(args: tuple[Any, ...]) -> bool:
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else 0
    if isinstance(mode, str) and _WRITE_MODE.search(mode):
        return True
    return isinstance(flags, int) and bool(flags & _WRITE_FLAGS)


def _is_remote(address: Any) -> bool:
    if isinstance(address, tuple) and address:
        return str(address[0]) not in _LOCAL_HOSTS
    # Sockets UNIX u otros: se tratan como no permitidos.
    return True


class _AuditState:
    lock = threading.Lock()
    active: list[WriteAudit] = []
    installed = False


def _hook(event: str, args: tuple[Any, ...]) -> None:
    if not _AuditState.active:
        return
    reason: str | None = None
    if event == "open" and _is_write_open(args):
        reason = f"open en escritura: {args[0]!r}"
    elif event in _FS_EVENTS:
        reason = f"{event}: {args[0]!r}" if args else event
    elif event in {"socket.connect", "socket.sendto"} and _is_remote(args[1]):
        reason = f"{event} a destino no local: {args[1]!r}"
    if reason is None:
        return
    for audit in list(_AuditState.active):
        audit.events.append(reason)
    if any(a.block for a in _AuditState.active):
        raise AuditViolation(reason)


class WriteAudit:
    """Contexto que registra (y por defecto bloquea) escrituras a disco y red no local.

    Los ganchos de auditoría de Python no se pueden quitar: se instala uno solo por proceso y se
    activa o desactiva con este contexto.
    """

    def __init__(self, *, block: bool = True) -> None:
        self.block = block
        self.events: list[str] = []

    def __enter__(self) -> WriteAudit:
        with _AuditState.lock:
            if not _AuditState.installed:
                sys.addaudithook(_hook)
                _AuditState.installed = True
            _AuditState.active.append(self)
        return self

    def __exit__(self, *exc: object) -> None:
        with _AuditState.lock:
            _AuditState.active.remove(self)


def snapshot(directories: Iterable[Path]) -> dict[str, tuple[int, int]]:
    """Ruta → (tamaño, mtime_ns) de todos los ficheros bajo ``directories``."""
    state: dict[str, tuple[int, int]] = {}
    for base in directories:
        for root, _dirs, files in os.walk(base):
            for name in files:
                path = Path(root, name)
                try:
                    st = path.stat()
                except OSError:
                    continue
                state[str(path)] = (st.st_size, st.st_mtime_ns)
    return state


# --- (c) proceso -------------------------------------------------------------------------


def disable_core_dumps() -> tuple[int, int]:
    """``RLIMIT_CORE = 0`` (blando y duro): un fallo no vuelca la memoria del búfer a disco."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    return resource.getrlimit(resource.RLIMIT_CORE)


@contextmanager
def install_wipe_on_signals(wipe: Callable[[], None]) -> Iterator[Callable[[int, Any], None]]:
    """Ante SIGINT/SIGTERM borra el búfer y termina; restaura los manejadores al salir."""

    def _handler(signum: int, frame: FrameType | None) -> None:
        wipe()
        if signum == signal.SIGINT:
            raise KeyboardInterrupt
        raise SystemExit(128 + signum)

    previous = {s: signal.signal(s, _handler) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield _handler
    finally:
        for s, h in previous.items():
            signal.signal(s, h)
