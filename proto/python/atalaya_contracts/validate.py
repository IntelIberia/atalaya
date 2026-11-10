"""Validación estructural y semántica de los contratos Protobuf de Atalaya."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, cast

from atalaya.v1 import options_pb2
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

_REQUIRED = cast(Any, options_pb2.required)
_SUM_TOLERANCE = 1e-6
_PSD_TOLERANCE = 1e-12
_SCALAR_FLOAT_TYPES = {
    FieldDescriptor.TYPE_DOUBLE,
    FieldDescriptor.TYPE_FLOAT,
}


def validate(message: Message) -> list[str]:
    """Devuelve errores de presencia y semántica con rutas de descriptor completas."""
    if not isinstance(message, Message):
        raise TypeError("validate() requiere un mensaje Protobuf")

    errors: list[str] = []

    def present(current: Message, field: Any) -> bool:
        if field.has_presence:
            return current.HasField(field.name)
        return True

    def finite_value(value: Any, path: str) -> None:
        if not math.isfinite(float(value)):
            errors.append(f"{path}: debe ser finito")

    def finite_scalars(current: Message, field: Any, path: str) -> None:
        if field.type not in _SCALAR_FLOAT_TYPES:
            return
        if field.is_repeated:
            for index, value in enumerate(getattr(current, field.name)):
                finite_value(value, f"{path}[{index}]")
        elif present(current, field):
            finite_value(getattr(current, field.name), path)

    def field_path(parent_path: str, field: Any) -> str:
        return f"{parent_path}.{field.name}"

    def is_required(field: Any) -> bool:
        return bool(field.GetOptions().Extensions[_REQUIRED])

    def is_complete(current: Message, fields: Iterable[str]) -> bool:
        return all(current.HasField(name) for name in fields)

    def validate_probability_sum(
        current: Message,
        field_name: str,
        path: str,
        *,
        exact_one: bool,
    ) -> None:
        values = list(getattr(current, field_name))
        if not values:
            return
        probabilities = [float(item.probability) for item in values]
        if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in probabilities):
            return
        total = math.fsum(probabilities)
        valid = abs(total - 1.0) <= _SUM_TOLERANCE if exact_one else total <= 1.0
        if not valid:
            relation = "1 ± 1e-6" if exact_one else "≤ 1"
            errors.append(f"{path}.{field_name}: la suma debe ser {relation}")

    def validate_covariance(current: Message, path: str) -> None:
        names = (
            "east_east_m2",
            "east_north_m2",
            "east_up_m2",
            "north_north_m2",
            "north_up_m2",
            "up_up_m2",
        )
        if not is_complete(current, names):
            return
        xx, xy, xz, yy, yz, zz = (float(getattr(current, name)) for name in names)
        if not all(math.isfinite(value) for value in (xx, xy, xz, yy, yz, zz)):
            return
        scale = max(abs(xx), abs(xy), abs(xz), abs(yy), abs(yz), abs(zz))
        if scale == 0.0:
            return
        xx, xy, xz, yy, yz, zz = (value / scale for value in (xx, xy, xz, yy, yz, zz))
        minors = (xx * yy - xy * xy, xx * zz - xz * xz, yy * zz - yz * yz)
        determinant = xx * (yy * zz - yz * yz) - xy * (xy * zz - yz * xz) + xz * (xy * yz - yy * xz)
        if (
            min(xx, yy, zz) < -_PSD_TOLERANCE
            or min(minors) < -_PSD_TOLERANCE
            or determinant < -_PSD_TOLERANCE
        ):
            errors.append(f"{path}: la matriz de covarianza debe ser semidefinida positiva")

    def validate_ellipse(current: Message, path: str) -> None:
        ellipse = cast(Any, current)
        confidence_fields = ("confidence_level",)
        if is_complete(current, confidence_fields):
            level = float(ellipse.confidence_level)
            if not 0.0 < level < 1.0:
                errors.append(f"{path}.confidence_level: debe estar entre 0 y 1, sin incluirlos")
        axes = ("semi_major_axis_m", "semi_minor_axis_m")
        if is_complete(current, axes):
            major = float(ellipse.semi_major_axis_m)
            minor = float(ellipse.semi_minor_axis_m)
            if major < 0 or minor < 0 or major < minor:
                errors.append(
                    f"{path}.semi_major_axis_m: los ejes deben ser no negativos y el mayor ≥ menor"
                )

    def validate_semantics(current: Message, path: str) -> None:
        name = current.DESCRIPTOR.full_name
        message = cast(Any, current)
        for field in current.DESCRIPTOR.fields:
            if (
                field.name
                not in {
                    "probability",
                    "detection_confidence",
                    "confidence",
                    "estimated_probability",
                }
                or field.type not in _SCALAR_FLOAT_TYPES
                or field.is_repeated
            ):
                continue
            if present(current, field):
                value = float(getattr(current, field.name))
                if not 0.0 <= value <= 1.0:
                    errors.append(f"{field_path(path, field)}: debe estar entre 0 y 1")
        if name == "atalaya.v1.PositionCovariance":
            validate_covariance(current, path)
        elif name == "atalaya.v1.ErrorEllipse":
            validate_ellipse(current, path)
        elif name == "atalaya.v1.Detection":
            validate_probability_sum(current, "class_scores", path, exact_one=False)
            if (
                current.HasField("bearing_uncertainty_deg")
                and float(message.bearing_uncertainty_deg) < 0.0
            ):
                errors.append(f"{path}.bearing_uncertainty_deg: no puede ser negativa")
            if current.HasField("bearing_deg") and not current.HasField("bearing_uncertainty_deg"):
                errors.append(f"{path}.bearing_uncertainty_deg: requerida si hay rumbo")
            if current.HasField("position") and not (
                current.HasField("position_covariance") or current.HasField("position_error")
            ):
                errors.append(
                    f"{path}.position_covariance: se requiere covarianza o elipse para la posición"
                )
            if current.WhichOneof("observation") is None:
                errors.append(f"{path}.observation: se requiere una observación")
        elif name == "atalaya.v1.Track":
            validate_probability_sum(current, "class_probabilities", path, exact_one=True)
        elif name == "atalaya.v1.TimeQuality":
            if current.HasField("uncertainty_ms") and float(message.uncertainty_ms) < 0.0:
                errors.append(f"{path}.uncertainty_ms: no puede ser negativa")
        elif name == "atalaya.v1.Sighting":
            if (
                current.HasField("bearing_uncertainty_deg")
                and float(message.bearing_uncertainty_deg) < 0.0
            ):
                errors.append(f"{path}.bearing_uncertainty_deg: no puede ser negativa")
        elif name == "atalaya.v1.Prediction":
            validate_probability_sum(current, "destination_probabilities", path, exact_one=True)
            observed = [
                float(item.horizon_s) for item in message.horizons if item.HasField("horizon_s")
            ]
            expected = (5.0, 10.0, 30.0)
            if sorted(observed) != list(expected):
                errors.append(
                    f"{path}.horizons: se requieren exactamente los horizontes 5, 10 y 30 s"
                )
        elif name == "atalaya.v1.Envelope" and current.WhichOneof("payload") is None:
            errors.append(f"{path}.payload: se requiere un mensaje payload")

    def visit(current: Message, path: str) -> None:
        for field in current.DESCRIPTOR.fields:
            path_for_field = field_path(path, field)
            repeated = getattr(current, field.name)
            if field.is_repeated:
                if is_required(field) and not repeated:
                    errors.append(f"{path_for_field}: se requiere al menos un elemento")
                finite_scalars(current, field, path_for_field)
                if field.message_type is not None:
                    for index, child in enumerate(repeated):
                        visit(child, f"{path_for_field}[{index}]")
                continue

            field_present = present(current, field)
            if is_required(field):
                if not field.has_presence and field.message_type is None:
                    errors.append(f"{path_for_field}: campo required sin presencia explícita")
                elif not field_present:
                    errors.append(f"{path_for_field}: campo requerido ausente")
            finite_scalars(current, field, path_for_field)
            if field.message_type is not None and field_present:
                visit(repeated, path_for_field)

        validate_semantics(current, path)

    visit(message, message.DESCRIPTOR.full_name)
    return sorted(set(errors))
