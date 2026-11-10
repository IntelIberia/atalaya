"""Pruebas de validación de presencia e incertidumbre en contratos Protobuf."""

from __future__ import annotations

from typing import Any

import pytest
from atalaya.sim.v1 import ground_truth_pb2
from atalaya.v1 import (
    alert_pb2,
    common_pb2,
    coverage_status_pb2,
    detection_pb2,
    envelope_pb2,
    evidence_pb2,
    node_status_pb2,
    prediction_pb2,
    sighting_pb2,
    signature_class_pb2,
    track_pb2,
)
from atalaya_contracts.validate import validate
from google.protobuf import timestamp_pb2
from hypothesis import given, settings
from hypothesis import strategies as st


def assert_error(errors: list[str], fragment: str) -> None:
    assert any(fragment in error for error in errors), errors


def covariance(
    *,
    ee: float = 1.0,
    en: float = 0.0,
    eu: float = 0.0,
    nn: float = 1.0,
    nu: float = 0.0,
    uu: float = 1.0,
) -> common_pb2.PositionCovariance:
    return common_pb2.PositionCovariance(
        east_east_m2=ee,
        east_north_m2=en,
        east_up_m2=eu,
        north_north_m2=nn,
        north_up_m2=nu,
        up_up_m2=uu,
    )


def detection() -> detection_pb2.Detection:
    return detection_pb2.Detection(
        detection_id="d-1",
        site_id="site-1",
        node_id="node-1",
        observed_at=timestamp_pb2.Timestamp(seconds=1),
        sensor_type=detection_pb2.SENSOR_TYPE_ACOUSTIC,
        time_quality=common_pb2.TimeQuality(
            pps_valid=True, clock_offset_ms=0.0, uncertainty_ms=0.1
        ),
        class_scores=[common_pb2.ClassScore(class_id="C1", probability=0.8)],
        detection_confidence=0.9,
        acoustic=detection_pb2.AcousticObservation(
            band_levels=[
                detection_pb2.AcousticBandLevel(center_frequency_hz=1000.0, level_db_spl=40.0)
            ],
            signal_to_noise_db=12.0,
        ),
    )


def track(
    *,
    state_covariance: common_pb2.PositionCovariance | None = None,
    class_probabilities: list[common_pb2.ClassScore] | None = None,
) -> track_pb2.Track:
    return track_pb2.Track(
        track_id="track-1",
        site_id="site-1",
        position=common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0),
        state_covariance=state_covariance or covariance(),
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=0.0,
        class_probabilities=class_probabilities
        if class_probabilities is not None
        else [common_pb2.ClassScore(class_id="C1", probability=1.0)],
        updated_at=timestamp_pb2.Timestamp(seconds=1),
        time_quality=common_pb2.TimeQuality(
            pps_valid=True, clock_offset_ms=0.0, uncertainty_ms=0.1
        ),
    )


def prediction(
    *,
    horizons: list[prediction_pb2.HorizonEstimate] | None = None,
    destination_probabilities: list[prediction_pb2.DestinationProbability] | None = None,
) -> prediction_pb2.Prediction:
    default_horizons = [
        prediction_pb2.HorizonEstimate(
            horizon_s=seconds,
            position=common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0),
            position_covariance=covariance(),
        )
        for seconds in (5.0, 10.0, 30.0)
    ]
    return prediction_pb2.Prediction(
        track_id="track-1",
        generated_at=timestamp_pb2.Timestamp(seconds=1),
        horizons=horizons if horizons is not None else default_horizons,
        destination_probabilities=destination_probabilities
        if destination_probabilities is not None
        else [
            prediction_pb2.DestinationProbability(destination_id="a", probability=0.6),
            prediction_pb2.DestinationProbability(destination_id="b", probability=0.4),
        ],
    )


@pytest.mark.req("REQ-FUN-062")
def test_detection_completa_valida() -> None:
    assert validate(detection()) == []


@pytest.mark.req("REQ-FUN-062")
def test_detection_rechaza_campos_required_ausentes() -> None:
    errors = validate(detection_pb2.Detection())
    assert_error(errors, "Detection.detection_id")
    assert_error(errors, "Detection.class_scores")
    assert_error(errors, "Detection.time_quality")


@pytest.mark.req("REQ-FUN-062")
def test_valores_cero_explicitos_cuentan_como_presentes() -> None:
    message = detection()
    message.detection_confidence = 0.0
    message.bearing_deg = 0.0
    message.bearing_uncertainty_deg = 0.0
    assert validate(message) == []


@pytest.mark.req("REQ-FUN-062")
@pytest.mark.parametrize("probability", [-0.01, 1.01, float("nan"), float("inf")])
def test_detection_rechaza_probabilidades_fuera_de_rango(probability: float) -> None:
    message = detection()
    message.class_scores[0].probability = probability
    assert_error(validate(message), "class_scores[0].probability")


@pytest.mark.req("REQ-FUN-062")
def test_probabilidades_muy_grandes_se_rechazan_sin_desbordar_la_suma() -> None:
    message = detection()
    message.class_scores[0].probability = 1e308
    message.class_scores.add(class_id="C2", probability=1e308)
    errors = validate(message)
    assert "atalaya.v1.Detection.class_scores[0].probability: debe estar entre 0 y 1" in errors
    assert "atalaya.v1.Detection.class_scores[1].probability: debe estar entre 0 y 1" in errors


@pytest.mark.req("REQ-FUN-062")
def test_detection_rechaza_suma_de_class_scores_mayor_que_uno() -> None:
    message = detection()
    message.class_scores.add(class_id="C2", probability=0.3)
    assert_error(validate(message), "class_scores")


@pytest.mark.req("REQ-FUN-062")
def test_detection_class_scores_no_tolera_sumas_superiores_a_uno() -> None:
    message = detection()
    message.class_scores[0].probability = 0.5000005
    message.class_scores.add(class_id="C2", probability=0.5)
    assert "atalaya.v1.Detection.class_scores: la suma debe ser ≤ 1" in validate(message)


@pytest.mark.req("REQ-FUN-062")
@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan")])
def test_detection_rechaza_confianza_invalida(confidence: float) -> None:
    message = detection()
    message.detection_confidence = confidence
    assert_error(validate(message), "detection_confidence")


@pytest.mark.req("REQ-FUN-062")
def test_detection_con_rumbo_exige_incertidumbre() -> None:
    message = detection()
    message.bearing_deg = 10.0
    assert_error(validate(message), "bearing_uncertainty_deg")


@pytest.mark.req("REQ-FUN-062")
def test_detection_rechaza_incertidumbre_de_rumbo_negativa() -> None:
    message = detection()
    message.bearing_deg = 10.0
    message.bearing_uncertainty_deg = -0.1
    assert "atalaya.v1.Detection.bearing_uncertainty_deg: no puede ser negativa" in validate(
        message
    )


@pytest.mark.req("REQ-FUN-062")
def test_detection_con_posicion_exige_covarianza_o_elipse() -> None:
    message = detection()
    message.position.latitude_deg = 1.0
    message.position.longitude_deg = 2.0
    assert_error(validate(message), "position_covariance")


@pytest.mark.req("REQ-FUN-062")
def test_detection_con_covarianza_o_elipse_valida_incertidumbre_de_posicion() -> None:
    with_covariance = detection()
    with_covariance.position.latitude_deg = 1.0
    with_covariance.position.longitude_deg = 2.0
    with_covariance.position_covariance.CopyFrom(covariance())
    assert validate(with_covariance) == []

    with_ellipse = detection()
    with_ellipse.position.latitude_deg = 1.0
    with_ellipse.position.longitude_deg = 2.0
    with_ellipse.position_error.semi_major_axis_m = 2.0
    with_ellipse.position_error.semi_minor_axis_m = 1.0
    with_ellipse.position_error.orientation_deg = 0.0
    with_ellipse.position_error.confidence_level = 0.95
    assert validate(with_ellipse) == []


@pytest.mark.req("REQ-FUN-062")
def test_covarianza_semidefinida_positiva_admite_matriz_cero() -> None:
    message = track(state_covariance=covariance(ee=0, nn=0, uu=0))
    assert validate(message) == []


@pytest.mark.req("REQ-FUN-062")
def test_covarianza_semidefinida_admite_matriz_singular_correlacionada() -> None:
    message = track(state_covariance=covariance(ee=1, en=1, nn=1, uu=0))
    assert validate(message) == []


@pytest.mark.req("REQ-FUN-062")
@pytest.mark.parametrize(
    "matrix",
    [
        covariance(ee=-0.1),
        covariance(ee=1, en=2, nn=1),
        covariance(ee=1, en=0, eu=0, nn=1, nu=2, uu=1),
    ],
)
def test_track_rechaza_covarianza_no_psd(matrix: common_pb2.PositionCovariance) -> None:
    assert (
        "atalaya.v1.Track.state_covariance: la matriz de covarianza debe ser semidefinida positiva"
        in validate(track(state_covariance=matrix))
    )


@pytest.mark.req("REQ-FUN-062")
def test_track_rechaza_covarianza_no_finita_con_ruta_exacta() -> None:
    message = track(state_covariance=covariance(ee=float("nan")))
    assert "atalaya.v1.Track.state_covariance.east_east_m2: debe ser finito" in validate(message)


@pytest.mark.req("REQ-FUN-062")
def test_track_exige_probabilidades_que_sumen_uno() -> None:
    scores = [
        common_pb2.ClassScore(class_id="C1", probability=0.6),
        common_pb2.ClassScore(class_id="C2", probability=0.3),
    ]
    assert_error(validate(track(class_probabilities=scores)), "class_probabilities")


@pytest.mark.req("REQ-FUN-062")
def test_track_rechaza_covarianza_obligatoria_ausente_con_ruta_exacta() -> None:
    message = track()
    message.ClearField("state_covariance")
    assert "atalaya.v1.Track.state_covariance: campo requerido ausente" in validate(message)


@pytest.mark.req("REQ-FUN-062")
def test_track_valido_acepta_suma_con_tolerancia() -> None:
    message = track(
        class_probabilities=[
            common_pb2.ClassScore(class_id="C1", probability=0.4),
            common_pb2.ClassScore(class_id="C2", probability=0.6000005),
        ]
    )
    assert validate(message) == []


@pytest.mark.req("REQ-FUN-062")
@pytest.mark.parametrize("confidence_level", [0.0, 1.0, -0.1, 1.1, float("nan")])
def test_elipse_exige_nivel_de_confianza_entre_cero_y_uno(
    confidence_level: float,
) -> None:
    message = detection()
    message.position_error.semi_major_axis_m = 2.0
    message.position_error.semi_minor_axis_m = 1.0
    message.position_error.orientation_deg = 0.0
    message.position_error.confidence_level = confidence_level
    assert_error(validate(message), "position_error.confidence_level")


@pytest.mark.req("REQ-FUN-062")
def test_elipse_rechaza_ejes_invertidos() -> None:
    message = detection()
    message.position_error.semi_major_axis_m = 1.0
    message.position_error.semi_minor_axis_m = 2.0
    message.position_error.orientation_deg = 0.0
    message.position_error.confidence_level = 0.95
    assert_error(validate(message), "position_error.semi_major_axis_m")


@pytest.mark.req("REQ-FUN-062")
def test_elipse_parcial_reporta_rutas_required_ausentes() -> None:
    message = detection()
    message.position_error.confidence_level = 0.95
    errors = validate(message)
    assert (
        "atalaya.v1.Detection.position_error.semi_major_axis_m: campo requerido ausente" in errors
    )
    assert (
        "atalaya.v1.Detection.position_error.semi_minor_axis_m: campo requerido ausente" in errors
    )


@pytest.mark.req("REQ-FUN-062")
def test_sighting_rechaza_incertidumbre_de_rumbo_negativa() -> None:
    message = sighting_pb2.Sighting(
        sighting_id="s-1",
        observed_at=timestamp_pb2.Timestamp(seconds=1),
        observer_position=common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0),
        bearing_deg=10.0,
        bearing_uncertainty_deg=-5.0,
    )
    assert "atalaya.v1.Sighting.bearing_uncertainty_deg: no puede ser negativa" in validate(message)


@pytest.mark.req("REQ-FUN-062")
def test_detection_rechaza_incertidumbre_de_tiempo_negativa() -> None:
    message = detection()
    message.time_quality.uncertainty_ms = -0.1
    assert_error(validate(message), "time_quality.uncertainty_ms")


@pytest.mark.req("REQ-FUN-062")
def test_prediction_completa_valida() -> None:
    assert validate(prediction()) == []


@pytest.mark.req("REQ-FUN-062")
def test_prediction_exige_horizontes_de_cinco_diez_y_treinta_segundos() -> None:
    message = prediction(
        horizons=[
            prediction_pb2.HorizonEstimate(
                horizon_s=5.0,
                position=common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0),
                position_covariance=covariance(),
            ),
            prediction_pb2.HorizonEstimate(
                horizon_s=10.0,
                position=common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0),
                position_covariance=covariance(),
            ),
        ]
    )
    assert_error(validate(message), "horizons")


@pytest.mark.req("REQ-FUN-062")
def test_prediction_rechaza_horizonte_duplicado() -> None:
    message = prediction()
    message.horizons[2].horizon_s = 10.0
    assert_error(validate(message), "horizons")


@pytest.mark.req("REQ-FUN-062")
def test_prediction_rechaza_covarianza_ausente_en_horizonte_de_diez_segundos() -> None:
    message = prediction()
    message.horizons[1].ClearField("position_covariance")
    assert (
        "atalaya.v1.Prediction.horizons[1].position_covariance: campo requerido ausente"
        in validate(message)
    )


@pytest.mark.req("REQ-FUN-062")
def test_prediction_rechaza_suma_de_destinos_distinta_de_uno() -> None:
    destinations = [
        prediction_pb2.DestinationProbability(destination_id="a", probability=0.5),
        prediction_pb2.DestinationProbability(destination_id="b", probability=0.4),
    ]
    errors = validate(prediction(destination_probabilities=destinations))
    assert "atalaya.v1.Prediction.destination_probabilities: la suma debe ser 1 ± 1e-6" in errors


@pytest.mark.req("REQ-FUN-062")
def test_detection_requiere_exactamente_un_tipo_de_observacion() -> None:
    message = detection()
    message.ClearField("acoustic")
    assert_error(validate(message), "Detection.observation")


@pytest.mark.req("REQ-FUN-062")
def test_envelope_requiere_un_payload() -> None:
    message = envelope_pb2.Envelope(
        site_id="site-1",
        node_id="node-1",
        sequence=0,
        emitted_at=timestamp_pb2.Timestamp(seconds=1),
    )
    assert_error(validate(message), "Envelope.payload")


@pytest.mark.req("REQ-FUN-062")
def test_confidence_y_probabilidad_genericas_estan_en_rango() -> None:
    alert = alert_pb2.Alert(confidence=1.1)
    coverage = coverage_status_pb2.CoverageStatus(estimated_probability=-0.1)
    assert_error(validate(alert), "Alert.confidence")
    assert_error(validate(coverage), "CoverageStatus.estimated_probability")


@pytest.mark.req("REQ-FUN-062")
def test_validate_rechaza_objetos_que_no_son_mensajes_protobuf() -> None:
    with pytest.raises(TypeError, match="mensaje Protobuf"):
        validate("no es protobuf")  # type: ignore[arg-type]


@pytest.mark.req("REQ-FUN-062")
@pytest.mark.parametrize(
    "message",
    [
        alert_pb2.Alert(),
        coverage_status_pb2.CoverageStatus(),
        detection_pb2.Detection(),
        envelope_pb2.Envelope(),
        evidence_pb2.Evidence(),
        ground_truth_pb2.GroundTruth(),
        node_status_pb2.NodeStatus(),
        prediction_pb2.Prediction(),
        signature_class_pb2.SignatureClass(),
        sighting_pb2.Sighting(),
        track_pb2.Track(),
    ],
)
def test_cada_tipo_valida_presencia_de_campos_required(message: Any) -> None:
    assert validate(message)


@pytest.mark.req("REQ-FUN-062")
@settings(max_examples=50, derandomize=True)
@given(*(st.floats(-10, 10) for _ in range(9)))
def test_covarianza_construida_como_a_por_a_traspuesta_es_psd(
    a: float,
    b: float,
    c: float,
    d: float,
    e: float,
    f: float,
    g: float,
    h: float,
    i: float,
) -> None:
    # Para cualquier A, C = A · Aᵀ es semidefinida positiva.
    message = track(
        state_covariance=covariance(
            ee=a * a + b * b + c * c,
            en=a * d + b * e + c * f,
            eu=a * g + b * h + c * i,
            nn=d * d + e * e + f * f,
            nu=d * g + e * h + f * i,
            uu=g * g + h * h + i * i,
        )
    )
    assert validate(message) == []
