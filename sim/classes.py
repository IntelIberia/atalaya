"""Cinemática por clase C1-C8 para el simulador (T1.11, REQ-FUN-004).

Cada valor lleva su procedencia (`Sourced.source`): una cita con URL o la marca «NO VERIFICADO».
**Todos los valores actuales son NO VERIFICADO**: son estimaciones de orden de magnitud para un
simulador sintético, no se contrastaron con fichas técnicas en esta tarea; los de C6/C7 son
declarados, no medidos (no hay datos públicos fiables, MEGAPROMPT). Sustituir por valores
con fuente exige actualizar este catálogo y su test.

C9 (confusores no aéreos) no vuela y no tiene trayectoria. C4 comparte la cinemática de C3:
acústicamente iguales; se distinguen por fusión.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, fields

NO_VERIFICADO = "NO VERIFICADO"


@dataclass(frozen=True)
class Sourced:
    value: float
    source: str


@dataclass(frozen=True)
class ClassKinematics:
    class_id: str
    description: str
    cruise_speed_mps: Sourced
    max_speed_mps: Sourced
    max_accel_mps2: Sourced
    max_turn_rate_dps: Sourced
    can_hover: bool


def _nv(value: float, why: str) -> Sourced:
    return Sourced(value, f"{NO_VERIFICADO}: {why}")


_MULTI = "estimación de orden de magnitud para multirrotores comerciales; sin contrastar con fichas"
_FPV = "estimación para FPV de carreras; sin contrastar"
_FIXED = "estimación para ala fija eléctrica pequeña; sin contrastar"
_DECL = "valor declarado (sin datos públicos fiables, MEGAPROMPT FASE 1); no medido"
_MANNED = "estimación para avioneta ligera; giro estándar de 3 °/s con margen; sin contrastar"


def _fpv(class_id: str, description: str) -> ClassKinematics:
    return ClassKinematics(
        class_id, description,
        _nv(25.0, _FPV), _nv(45.0, _FPV), _nv(20.0, _FPV), _nv(360.0, _FPV), can_hover=False,
    )  # fmt: skip


CATALOG: Mapping[str, ClassKinematics] = {
    "C1": ClassKinematics(
        "C1", "Multirrotor eléctrico pequeño (< 2 kg)",
        _nv(10.0, _MULTI), _nv(19.0, _MULTI), _nv(6.0, _MULTI), _nv(120.0, _MULTI), can_hover=True,
    ),
    "C2": ClassKinematics(
        "C2", "Multirrotor mediano o pesado (2-25 kg)",
        _nv(8.0, _MULTI), _nv(15.0, _MULTI), _nv(4.0, _MULTI), _nv(60.0, _MULTI), can_hover=True,
    ),
    "C3": _fpv("C3", "FPV con radiofrecuencia"),
    "C4": _fpv("C4", "FPV sin radiofrecuencia (misma cinemática que C3)"),
    "C5": ClassKinematics(
        "C5", "Ala fija eléctrica",
        _nv(20.0, _FIXED), _nv(32.0, _FIXED), _nv(4.0, _FIXED), _nv(25.0, _FIXED), can_hover=False,
    ),
    "C6": ClassKinematics(
        "C6", "Ala fija con motor de pistón",
        _nv(45.0, _DECL), _nv(55.0, _DECL), _nv(3.0, _DECL), _nv(10.0, _DECL), can_hover=False,
    ),
    "C7": ClassKinematics(
        "C7", "Reactor o turbina",
        _nv(150.0, _DECL), _nv(250.0, _DECL), _nv(30.0, _DECL), _nv(6.0, _DECL), can_hover=False,
    ),
    "C8": ClassKinematics(
        "C8", "Aeronave tripulada (confusor, ADS-B)",
        _nv(60.0, _MANNED), _nv(90.0, _MANNED), _nv(3.0, _MANNED), _nv(6.0, _MANNED),
        can_hover=False,
    ),
}  # fmt: skip


def kinematics(class_id: str) -> ClassKinematics:
    try:
        return CATALOG[class_id]
    except KeyError:
        raise ValueError(f"clase sin trayectoria en el simulador: {class_id!r}") from None


def _source_ok(source: str) -> bool:
    text = source.strip()
    return text.startswith(NO_VERIFICADO) or "https://" in text


def catalog_problems(catalog: Mapping[str, ClassKinematics]) -> list[str]:
    """Valores sin fuente ni marca NO VERIFICADO, no positivos o crucero > máximo."""
    problems: list[str] = []
    for class_id, entry in catalog.items():
        for field in fields(entry):
            item = getattr(entry, field.name)
            if not isinstance(item, Sourced):
                continue
            if not _source_ok(item.source):
                problems.append(f"{class_id}.{field.name}: sin fuente ni marca {NO_VERIFICADO}")
            if not (math.isfinite(item.value) and item.value > 0):
                problems.append(f"{class_id}.{field.name}: valor no positivo o no finito")
        if entry.cruise_speed_mps.value > entry.max_speed_mps.value:
            problems.append(f"{class_id}: crucero mayor que la velocidad máxima")
    return problems
