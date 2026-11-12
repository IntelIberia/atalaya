"""Ejecuta mutmut con el paquete Atalaya bajo el import root que espera mutmut 3.7."""

from __future__ import annotations

import fcntl
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv[1:]
    source_root = ROOT / "src"
    package_alias = source_root / "atalaya_contracts"
    created_source_root = not source_root.exists()
    alias_target = Path("../proto/python/atalaya_contracts")
    # El lock del archivo existente se libera incluso si mutmut recibe SIGKILL.
    with (ROOT / "pyproject.toml").open("rb") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("mutación: ya hay una ejecución en curso", file=sys.stderr)
            return 2
        if package_alias.is_symlink() and package_alias.readlink() == alias_target:
            # Alias temporal de una ejecución terminada sin cleanup; no tocar enlaces ajenos.
            package_alias.unlink()
        elif package_alias.exists() or package_alias.is_symlink():
            print(
                "mutación: src/atalaya_contracts ya existe; no se altera el árbol", file=sys.stderr
            )
            return 2

        source_root.mkdir(parents=True, exist_ok=True)
        package_alias.symlink_to(alias_target, target_is_directory=True)
        try:
            command = [sys.executable, "-m", "mutmut.__main__", *arguments]
            return subprocess.run(command, cwd=ROOT, check=False).returncode
        finally:
            package_alias.unlink(missing_ok=True)
            if created_source_root:
                source_root.rmdir()


if __name__ == "__main__":
    raise SystemExit(main())
