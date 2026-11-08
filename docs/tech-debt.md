# Deuda técnica

Se revisa en cada cierre de fase. Formato: qué, por qué existe, impacto y cómo saldarla.

| ID | Qué | Por qué | Impacto | Cómo saldarla | Desde |
|---|---|---|---|---|---|
| TD-01 | `libcst>=1.8.6,<1.9` fijado | libcst 1.9 no publica wheel macOS x86_64 (Mac Intel) y exige Rust | Sin parches de libcst ≥ 1.9 (solo lo usa mutmut, herramienta de desarrollo) | Retirar el límite cuando haya wheel x86_64 o máquina ARM/Linux | T0.2 |
| TD-02 | `pytest<9` fijado | mutmut 3.7 (la última instalable sin libcst 1.9) usa `Item._nodeid`, eliminado en pytest 9 | Sin novedades de pytest 9 | Subir a mutmut ≥ 3.8 cuando TD-01 se resuelva | T0.3 |
| TD-03 | GNU Make 3.81 (macOS) sin `.SHELLFLAGS`/pipefail | Versión del sistema | Las tuberías en recetas ocultarían fallos (ocurrió); mitigado: prohibidas por `tests/test_makefile.py` | Opcional: `brew install make` (gmake 4) y documentarlo | T0.9 |
| TD-04 | Tests de CLI en subproceso excluidos de mutmut | mutmut 3 no resuelve su configuración en procesos hijos | Esa ruta se cubre con tests en proceso equivalentes | Revisar con nuevas versiones de mutmut | T0.3 |
| TD-05 | `license_check` no evalúa dependencias exclusivas de otras plataformas | Solo lee metadatos de lo instalado (p. ej. colorama en Windows) | Una dependencia GPL solo de Windows pasaría | Leer licencias desde el índice (PyPI) además de lo instalado | T0.11 |
| TD-06 | Mosquitto con usuario/contraseña compartidos, sin TLS | FASE 0 mínima | Autenticación de nodos débil en local | mTLS por dispositivo (REQ-SEC-004, FASE 5/12) | T0.10 |
| TD-07 | Mapa ENS con códigos de memoria | Sin consulta al BOE en la FASE 0 | Posibles erratas de códigos | Verificar contra RD 311/2022 antes de la FASE 12 | T0.12 |
