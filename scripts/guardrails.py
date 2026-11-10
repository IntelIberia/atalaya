#!/usr/bin/env python3
"""Guardarraíles legales y de seguridad de Atalaya (REQ-SEC-001, REQ-LEG-001/002/005/007).

Bloquea (exit 2) cambios que introduzcan:
  sdr-tx          llamadas o comandos de TRANSMISIÓN por radio (Atalaya solo recibe)
  offensive-term  términos de capacidad ofensiva en código (lista blanca: identificadores
                  defensivos concretos en scripts/guardrails_allowlist.txt)
  audio-file      ficheros de audio fuera de tests/fixtures/sinteticos/ (por extensión
                  o por cabecera)
  pilot-public    campos pilot_* u operator_* en esquemas que no sean FCSE_ONLY
  secret          secretos en el contenido
  secret-file     ficheros .env* o rutas secrets/

Los patrones se escriben por fragmentos para que este fichero no contenga los
términos literales. Solo biblioteca estándar.

Uso:
  guardrails.py --staged            # contenido del índice (hook pre-commit)
  guardrails.py --range A..B        # ficheros cambiados en un rango (CI)
  guardrails.py --paths F [F ...]   # ficheros del disco
  guardrails.py --command "CMD"     # comando de shell (hook PreToolUse de Claude Code)
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

ALLOWLIST_FILE = Path(__file__).resolve().parent / "guardrails_allowlist.txt"

CODE_EXTENSIONS = frozenset(
    [
        ".py",
        ".pyi",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".kt",
        ".kts",
        ".java",
        ".ts",
        ".tsx",
        ".js",
        ".mjs",
        ".cjs",
        ".svelte",
        ".rs",
        ".go",
        ".sh",
        ".bash",
        ".zsh",
        ".proto",
        ".ino",
        ".cmake",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".sql",
        ".ipynb",
        ".grc",
        ".cfg",
        ".ini",
        ".conf",
        ".dockerfile",
    ]
)
CODE_NAMES = frozenset(["Makefile", "Dockerfile", "Containerfile", "Jenkinsfile"])
AUDIO_EXTENSIONS = frozenset(
    [
        ".wav",
        ".flac",
        ".mp3",
        ".ogg",
        ".m4a",
        ".opus",
        ".aac",
        ".aiff",
        ".aif",
        ".wma",
        ".pcm",
        ".raw",
        ".amr",
        ".caf",
        ".3gp",
        ".webm",
        ".mka",
    ]
)
AUDIO_FIXTURES_DIR = "tests/fixtures/sinteticos/"
SCHEMA_EXTENSIONS = frozenset([".proto", ".json", ".yaml", ".yml"])

# --- (a) transmisión por radio -------------------------------------------------------
_TX = "t" + "x"
SDR_TX_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"hackrf" + r"_transfer\b[^\n]*\s-[tc]\b",  # TX desde fichero / onda continua
        r"\bhackrf_start_" + _TX + r"\b",
        r"\bhackrf_set_" + _TX + r"vga_gain\b",
        r"\bSOAPY_SDR_" + _TX.upper() + r"\b",
        r"\.write" + r"Stream\s*\(",
        r"\." + _TX + r"\s*\(",  # pyadi-iio: método de transmisión de muestras
        r"\b" + _TX + r"_(?:lo|hardwaregain\w*|enabled_channels|cyclic_buffer|destroy_buffer)\b",
        r"\bosmosdr\.sink\b",
        r"\buhd\.usrp_sink\b",
        r"\biio\.\w*_sink\b",
        r"\bsoapy\.sink\b",
        r"\brpi" + _TX + r"\b",
        r"\bsendiq\b",
        r"\bosmocom_siggen\w*",
        r"\besp_wifi_80211_" + _TX + r"\b",  # inyección de tramas Wi-Fi en ESP32
        r"\besp_ble_gap_(?:start_advertising|config_adv_data\w*)\b",
        r"\bble_gap_adv_start\b",
    )
)

# --- (b) términos ofensivos -------------------------------------------------------------
OFFENSIVE_PATTERN = re.compile(
    "|".join(
        (
            r"(?<![A-Za-z])ja" + r"m(?:m\w*|_\w*)?(?![a-z])",
            "spo" + r"of\w*",
            r"de-?" + "auth\\w*",
            "take" + r"-?over\w*",
            "inhi" + r"b\w*",
            "supla" + r"nt\w*",
            "interfe" + r"rir|interfi" + r"er\w+",
            "desaut" + r"entic\w*",
            "neutrali" + r"[zsc]\w*",
            r"tom\w*\s+(?:el\s+)?" + "cont" + "rol",
        )
    ),
    re.IGNORECASE,
)
IDENT_RE = re.compile(r"\w+")
# Letras de otros alfabetos visualmente idénticas a las latinas (evasión por homoglifos).
CONFUSABLES = str.maketrans("аеорсухіјѕАЕОРСХІЈЅ", "aeopcyxijsAEOPCXIJS")

# --- (c) audio ------------------------------------------------------------------------
AUDIO_MAGIC: tuple[tuple[int, bytes], ...] = (
    (8, b"WAVE"),  # RIFF....WAVE
    (0, b"fLaC"),
    (0, b"OggS"),
    (0, b"ID3"),
    (8, b"AIFF"),
    (4, b"ftypM4A"),
)

# --- (d) datos de piloto/operador -----------------------------------------------------
PILOT_FIELD_RE = re.compile(r"(?<![A-Za-z])(?:pilot|piloto|operator|operador)(?:_\w+|[A-Z]\w*)")
# Debe declararse como sensibilidad, no basta mencionarlo (p. ej. en un comentario).
FCSE_ONLY_RE = re.compile(r"sensitivity[\"')\]]*\s*[:=]\s*[\"']?FCSE_ONLY\b")
COMMENT_RE = re.compile(r"\s(?://|#).*$")

# --- (e) secretos ---------------------------------------------------------------------
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"\bAKIA[0-9A-Z]{16}\b",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
        r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
        r"\bgithub_pat_[A-Za-z0-9_]{40,}\b",
        r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
        r"\bAIza[0-9A-Za-z_\-]{35}\b",
        r"\bsk-ant-[A-Za-z0-9_\-]{20,}",
        r"(?i)\b(?:password|passwd|pwd|secret|api_?key|token)\b['\"]?\s*[:=]\s*['\"][^'\"\s]{8,}['\"]",
        r"\b[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY)\s*[:=]\s*(?!['\"$?{-])[^\s#]{8,}",
    )
)
SECRET_FILE_RE = re.compile(r"(?:^|/)(?:\.env(?:\.(?!example$)[\w.-]+)?|\.envrc|secrets/.*)$")

# --- comandos de shell (hook PreToolUse) ------------------------------------------------
SECRET_PATH_IN_CMD = re.compile(
    r"(?:^|[\s/'\"=<>])(?:\.env(?:\.[\w.-]+)?(?=$|[\s'\";|&)<>/])|secrets/)"
)
FORCE_PUSH_RE = re.compile(r"\bgit\s+push\b[^\n;&|]*\s(?:--force(?:-with-lease)?|-f\b|\+\S)")
NO_VERIFY_RE = re.compile(
    r"\bgit\b[^\n;&|]*\bcommit\b[^\n;&|]*\s(?:--no-v\w*|-[a-zA-Z]*n[a-zA-Z]*\b)"
    r"|\bgit\b[^\n;&|]*\bcommit-tree\b"
    r"|\b(?:chmod|rm|mv|cp|ln|truncate|tee)\b[^\n;&|]*\.githooks"
    r"|>\s*\.githooks/"
)
HOOKS_PATH_RE = re.compile(r"core\.hooksPath", re.IGNORECASE)
HOOKS_PATH_READ_RE = re.compile(r"--get(?:-all)?\s+core\.hooksPath\b", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    path: str
    rule: str
    detail: str
    line: int = 0

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.rule}] {where}: {self.detail}"


def load_allowlist(path: Path = ALLOWLIST_FILE) -> frozenset[str]:
    if not path.exists():
        return frozenset()
    items = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        token = raw.split("#", 1)[0].strip()
        if token:
            items.add(token)
    return frozenset(items)


def _is_audio_bytes(data: bytes) -> bool:
    if len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0:  # trama MPEG sin ID3
        return True
    return any(data[off : off + len(sig)] == sig for off, sig in AUDIO_MAGIC)


def _decode(content: str | bytes, force_text: bool = False) -> str | None:
    if isinstance(content, str):
        return content
    if not force_text and b"\x00" in content[:8192]:
        return None  # binario
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _enclosing_identifier(line: str, start: int, end: int) -> str:
    for m in IDENT_RE.finditer(line):
        if m.start() <= start and m.end() >= end:
            return m.group(0)
    return line[start:end]


CLAUDE_SETTINGS = ".claude/settings.json"


def _json_pilot_fields(rel: str, text: str) -> list[Violation]:
    """Asocia la sensibilidad al objeto del campo, incluso en JSON compacto."""
    pending: list[Any] = [json.loads(text)]
    violations = []
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                if PILOT_FIELD_RE.search(key) and not (
                    isinstance(child, dict) and child.get("sensitivity") == "FCSE_ONLY"
                ):
                    violations.append(
                        Violation(rel, "pilot-public", f"«{key}» debe ser FCSE_ONLY (REQ-LEG-007)")
                    )
                if (
                    isinstance(child, str)
                    and PILOT_FIELD_RE.search(child)
                    and value.get("sensitivity") != "FCSE_ONLY"
                ):
                    violations.append(
                        Violation(
                            rel, "pilot-public", f"«{child}» debe ser FCSE_ONLY (REQ-LEG-007)"
                        )
                    )
                pending.append(child)
        elif isinstance(value, list):
            pending.extend(value)
    return violations


def _settings_without_deny(text: str) -> str:
    """En .claude/settings.json se pueden NOMBRAR herramientas de TX solo para denegarlas:
    se analiza todo el fichero excepto la lista permissions.deny. Si no es JSON válido,
    se analiza entero (fallo cerrado)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(data, dict) and isinstance(data.get("permissions"), dict):
        data["permissions"].pop("deny", None)
    return json.dumps(data, indent=1, ensure_ascii=False)  # una clave por línea; sin escapar


def check_file(
    path: str, content: str | bytes, allowlist: frozenset[str] | None = None
) -> list[Violation]:
    """Comprueba un fichero (ruta relativa al repo, estilo POSIX) y su contenido."""
    allow = load_allowlist() if allowlist is None else allowlist
    rel = PurePosixPath(path).as_posix()  # normaliza "./" iniciales
    suffix = PurePosixPath(rel).suffix.lower()
    violations: list[Violation] = []

    if SECRET_FILE_RE.search(rel):
        violations.append(Violation(rel, "secret-file", "fichero de secretos versionado"))

    in_fixtures = rel.startswith(AUDIO_FIXTURES_DIR)
    raw = content.encode("utf-8") if isinstance(content, str) else content
    if not in_fixtures and (suffix in AUDIO_EXTENSIONS or _is_audio_bytes(raw[:16])):
        violations.append(
            Violation(rel, "audio-file", f"audio fuera de {AUDIO_FIXTURES_DIR} (REQ-LEG-005)")
        )

    name = PurePosixPath(rel).name
    shebang = raw.startswith(b"#!")
    is_code = (
        suffix in CODE_EXTENSIONS
        or name in CODE_NAMES
        or name.startswith("Dockerfile")
        or (suffix == "" and shebang)
    )
    text = _decode(content, force_text=is_code)
    if text is None:
        return violations
    if rel == CLAUDE_SETTINGS:
        text = _settings_without_deny(text)
    is_schema = suffix in SCHEMA_EXTENSIONS
    if suffix == ".json":
        try:
            violations.extend(_json_pilot_fields(rel, text))
            is_schema = False
        except (ValueError, RecursionError):
            # JSON ilegible: se conserva la comprobación conservadora por línea.
            pass
    for n, line in enumerate(text.splitlines(), 1):
        if is_code:
            for pat in SDR_TX_PATTERNS:
                if pat.search(line):
                    violations.append(
                        Violation(rel, "sdr-tx", "transmisión por radio (REQ-LEG-002)", n)
                    )
                    break
            folded = line.translate(CONFUSABLES)
            for m in OFFENSIVE_PATTERN.finditer(folded):
                ident = _enclosing_identifier(folded, m.start(), m.end())
                if ident not in allow:
                    violations.append(
                        Violation(rel, "offensive-term", f"«{ident}» (REQ-LEG-001)", n)
                    )
        if is_schema:
            code = COMMENT_RE.sub("", line) if suffix != ".json" else line
            for m in PILOT_FIELD_RE.finditer(code):
                field = code[m.start() :].split(";", 1)[0].split("}", 1)[0]
                if not FCSE_ONLY_RE.search(field):
                    violations.append(
                        Violation(
                            rel,
                            "pilot-public",
                            f"«{m.group(0)}» debe ser FCSE_ONLY (REQ-LEG-007)",
                            n,
                        )
                    )
        for pat in SECRET_PATTERNS:
            if pat.search(line):
                violations.append(Violation(rel, "secret", "posible secreto", n))
                break
    return violations


def _glob_hits_secret(command: str) -> bool:
    """Un comodín que podría expandirse a .env o secrets/ también cuenta como acceso."""
    for token in command.split():
        if any(c in token for c in "*?["):
            parts = token.split("/")
            if fnmatch.fnmatch(".env", parts[-1]) or any(
                fnmatch.fnmatch("secrets", x) for x in parts[:-1]
            ):
                return True
    return False


def check_command(command: str) -> list[Violation]:
    """Comprueba un comando de shell antes de ejecutarlo (hook PreToolUse)."""
    found: list[Violation] = []
    unquoted = re.sub(r"['\"\\]", "", command)
    if SECRET_PATH_IN_CMD.search(unquoted) or _glob_hits_secret(unquoted):
        found.append(Violation("<bash>", "secret-file", "acceso a .env o secrets/"))
    if any(p.search(unquoted) for p in SDR_TX_PATTERNS):
        found.append(Violation("<bash>", "sdr-tx", "transmisión por radio (REQ-LEG-002)"))
    if FORCE_PUSH_RE.search(command):
        found.append(Violation("<bash>", "force-push", "git push forzado"))
    if NO_VERIFY_RE.search(command) or (
        HOOKS_PATH_RE.search(command) and not HOOKS_PATH_READ_RE.search(command)
    ):
        found.append(Violation("<bash>", "hook-bypass", "evasión de los hooks de git"))
    return found


# --- obtención de cambios ----------------------------------------------------------------
def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def _changed(diff_args: list[str]) -> list[str]:
    out = _git("diff", "--name-only", "--diff-filter=ACMRT", "-z", *diff_args)
    return [p for p in out.decode("utf-8").split("\0") if p]


def staged_files() -> list[tuple[str, bytes]]:
    return [(p, _git("show", f":{p}")) for p in _changed(["--cached"])]


def range_files(rev_range: str) -> list[tuple[str, bytes]]:
    head = re.split(r"\.{2,3}", rev_range)[-1] or "HEAD"
    return [(p, _git("show", f"{head}:{p}")) for p in _changed([rev_range])]


def disk_files(paths: list[str]) -> list[tuple[str, bytes]]:
    return [(p, Path(p).read_bytes()) for p in paths if Path(p).is_file()]


EXIT_BLOCKED = 2
EXIT_USAGE = 64  # distinto de EXIT_BLOCKED: un error de uso no es un bloqueo


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def main(argv: list[str] | None = None) -> int:
    ap = _Parser(description=__doc__.splitlines()[0] if __doc__ else None)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--range", metavar="A..B")
    mode.add_argument("--paths", nargs="+")
    mode.add_argument("--command")
    args = ap.parse_args(argv)
    if args.range is not None and ".." not in args.range:
        ap.error("--range debe tener la forma A..B o A...B")

    try:
        if args.command is not None:
            violations = check_command(args.command)
        else:
            if args.staged:
                files = staged_files()
            elif args.range:
                files = range_files(args.range)
            else:
                files = disk_files(args.paths)
            allow = load_allowlist()
            violations = [v for p, data in files for v in check_file(p, data, allow)]
    except (subprocess.CalledProcessError, OSError) as exc:
        # Fallo cerrado: si no se puede verificar, se bloquea.
        print(
            f"GUARDARRAÍL: no se pudo verificar ({exc}); bloqueado por seguridad.", file=sys.stderr
        )
        return EXIT_BLOCKED

    if violations:
        print(
            "GUARDARRAÍL: cambio bloqueado (ver CLAUDE.md, restricciones legales):", file=sys.stderr
        )
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return EXIT_BLOCKED
    return 0


if __name__ == "__main__":
    sys.exit(main())
