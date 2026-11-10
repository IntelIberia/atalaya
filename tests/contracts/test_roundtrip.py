"""Round-trip binario de los once mensajes principales de los contratos."""

from __future__ import annotations

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
from google.protobuf.message import DecodeError, Message
from hypothesis import given, settings
from hypothesis import strategies as st

TEXT = st.text(alphabet="abcXYZ09 _-ñ", min_size=1, max_size=12)
SIGNED = st.floats(-180.0, 180.0, allow_nan=False, allow_infinity=False, width=32)
NONNEGATIVE = st.floats(0.0, 1000.0, allow_nan=False, allow_infinity=False, width=32)
PROBABILITY = st.floats(0.0, 1.0, allow_nan=False, allow_infinity=False, width=32)
SMALL_PROBABILITY = st.floats(0.0, 1.0 / 3.0, allow_nan=False, allow_infinity=False)
TIMESTAMP = st.builds(
    timestamp_pb2.Timestamp,
    seconds=st.integers(0, 4_000_000_000),
    nanos=st.integers(0, 999_999_999),
)
GEO_POINT = st.builds(
    common_pb2.GeoPoint,
    latitude_deg=st.floats(-90.0, 90.0, allow_nan=False, allow_infinity=False, width=32),
    longitude_deg=SIGNED,
    altitude_m=st.one_of(st.none(), SIGNED),
)
COVARIANCE = st.builds(
    common_pb2.PositionCovariance,
    east_east_m2=NONNEGATIVE,
    east_north_m2=st.just(0.0),
    east_up_m2=st.just(0.0),
    north_north_m2=NONNEGATIVE,
    north_up_m2=st.just(0.0),
    up_up_m2=NONNEGATIVE,
)
TIME_QUALITY = st.builds(
    common_pb2.TimeQuality,
    pps_valid=st.booleans(),
    clock_offset_ms=SIGNED,
    uncertainty_ms=NONNEGATIVE,
)


@st.composite
def error_ellipses(draw: st.DrawFn) -> common_pb2.ErrorEllipse:
    minor = draw(NONNEGATIVE)
    return common_pb2.ErrorEllipse(
        semi_major_axis_m=minor + draw(NONNEGATIVE),
        semi_minor_axis_m=minor,
        orientation_deg=draw(SIGNED),
        confidence_level=draw(
            st.floats(0.125, 0.875, allow_nan=False, allow_infinity=False, width=32)
        ),
    )


ERROR_ELLIPSE = error_ellipses()
DETECTION_SCORE = st.builds(common_pb2.ClassScore, class_id=TEXT, probability=SMALL_PROBABILITY)


@st.composite
def normalized_scores(draw: st.DrawFn) -> list[common_pb2.ClassScore]:
    first_id = draw(TEXT)
    if draw(st.booleans()):
        return [common_pb2.ClassScore(class_id=first_id, probability=1.0)]
    probability = draw(PROBABILITY)
    return [
        common_pb2.ClassScore(class_id=first_id, probability=probability),
        common_pb2.ClassScore(class_id=draw(TEXT), probability=1.0 - probability),
    ]


@st.composite
def destination_probabilities(draw: st.DrawFn) -> list[prediction_pb2.DestinationProbability]:
    first_id = draw(TEXT)
    if draw(st.booleans()):
        return [prediction_pb2.DestinationProbability(destination_id=first_id, probability=1.0)]
    probability = draw(PROBABILITY)
    return [
        prediction_pb2.DestinationProbability(destination_id=first_id, probability=probability),
        prediction_pb2.DestinationProbability(
            destination_id=draw(TEXT), probability=1.0 - probability
        ),
    ]


ACOUSTIC_BAND = st.builds(
    detection_pb2.AcousticBandLevel,
    center_frequency_hz=NONNEGATIVE,
    level_db_spl=SIGNED,
)
OBSERVATIONS = st.one_of(
    st.tuples(
        st.just("acoustic"),
        st.builds(
            detection_pb2.AcousticObservation,
            band_levels=st.lists(ACOUSTIC_BAND, min_size=1, max_size=3),
            signal_to_noise_db=SIGNED,
        ),
    ),
    st.tuples(
        st.just("remote_id"),
        st.builds(
            detection_pb2.RemoteIdObservation,
            operator_id=st.one_of(st.none(), TEXT),
            operator_location=st.one_of(st.none(), GEO_POINT),
            uas_id=st.one_of(st.none(), TEXT),
            self_id_description=st.one_of(st.none(), TEXT),
            standard=st.sampled_from(
                [
                    detection_pb2.REMOTE_ID_STANDARD_EN_4709_002,
                    detection_pb2.REMOTE_ID_STANDARD_ASTM_F3411,
                ]
            ),
            aircraft_position=st.one_of(st.none(), GEO_POINT),
            message_time=st.one_of(st.none(), TIMESTAMP),
        ),
    ),
    st.tuples(
        st.just("adsb"),
        st.builds(
            detection_pb2.AdsbObservation,
            callsign=st.one_of(st.none(), TEXT),
            aircraft_position=st.one_of(st.none(), GEO_POINT),
            position_covariance=st.one_of(st.none(), COVARIANCE),
            message_time=TIMESTAMP,
        ),
    ),
    st.tuples(
        st.just("rf_presence"),
        st.builds(
            detection_pb2.RfPresenceObservation,
            center_frequency_hz=NONNEGATIVE,
            bandwidth_hz=NONNEGATIVE,
            received_power_dbm=SIGNED,
        ),
    ),
    st.tuples(st.just("human"), st.builds(detection_pb2.HumanObservation, sighting_id=TEXT)),
)
SENSOR_TYPES = {
    "acoustic": detection_pb2.SENSOR_TYPE_ACOUSTIC,
    "remote_id": detection_pb2.SENSOR_TYPE_REMOTE_ID,
    "adsb": detection_pb2.SENSOR_TYPE_ADSB,
    "rf_presence": detection_pb2.SENSOR_TYPE_RF_PRESENCE,
    "human": detection_pb2.SENSOR_TYPE_HUMAN,
}


@st.composite
def detections(draw: st.DrawFn) -> detection_pb2.Detection:
    observation_name, observation = draw(OBSERVATIONS)
    message = detection_pb2.Detection(
        detection_id=draw(TEXT),
        site_id=draw(TEXT),
        node_id=draw(TEXT),
        observed_at=draw(TIMESTAMP),
        sensor_type=SENSOR_TYPES[observation_name],
        time_quality=draw(TIME_QUALITY),
        position=draw(GEO_POINT),
        position_covariance=draw(COVARIANCE),
        position_error=draw(st.one_of(st.none(), ERROR_ELLIPSE)),
        bearing_deg=draw(st.one_of(st.none(), SIGNED)),
        bearing_uncertainty_deg=draw(NONNEGATIVE),
        class_scores=draw(st.lists(DETECTION_SCORE, min_size=1, max_size=3)),
        detection_confidence=draw(PROBABILITY),
    )
    getattr(message, observation_name).CopyFrom(observation)
    return message


ALERT = st.builds(
    alert_pb2.Alert,
    alert_id=TEXT,
    track_id=TEXT,
    level=st.sampled_from(
        [
            alert_pb2.ALERT_LEVEL_INFORMATION,
            alert_pb2.ALERT_LEVEL_WARNING,
            alert_pb2.ALERT_LEVEL_CRITICAL,
        ]
    ),
    confidence=PROBABILITY,
    created_at=TIMESTAMP,
    last_known_position=st.one_of(st.none(), GEO_POINT),
    summary=st.one_of(st.none(), TEXT),
)
COVERAGE_STATUS = st.builds(
    coverage_status_pb2.CoverageStatus,
    site_id=TEXT,
    region_id=TEXT,
    boundary=st.lists(GEO_POINT, min_size=3, max_size=5),
    estimated_probability=PROBABILITY,
    uncertainty=ERROR_ELLIPSE,
    assessed_at=TIMESTAMP,
)
DETECTION = detections()
EVIDENCE = st.builds(
    evidence_pb2.Evidence,
    evidence_id=TEXT,
    sha256=st.text(alphabet="0123456789abcdef", min_size=64, max_size=64),
    media_type=st.sampled_from(["image/jpeg", "audio/wav", "video/mp4"]),
    captured_at=TIMESTAMP,
    custodian_pseudonym=TEXT,
    custody_signature=st.binary(max_size=32),
)
GROUND_TRUTH = st.builds(
    ground_truth_pb2.GroundTruth,
    target_id=TEXT,
    simulated_at=TIMESTAMP,
    true_position=GEO_POINT,
    class_id=TEXT,
    is_forged=st.booleans(),
    launch_point=st.one_of(st.none(), GEO_POINT),
)
NODE_STATUS = st.builds(
    node_status_pb2.NodeStatus,
    site_id=TEXT,
    node_id=TEXT,
    observed_at=TIMESTAMP,
    health=st.sampled_from(
        [
            node_status_pb2.NODE_HEALTH_HEALTHY,
            node_status_pb2.NODE_HEALTH_DEGRADED,
            node_status_pb2.NODE_HEALTH_FAILED,
        ]
    ),
    location=st.one_of(st.none(), GEO_POINT),
    time_quality=TIME_QUALITY,
    battery_percent=st.one_of(st.none(), PROBABILITY.map(lambda value: value * 100.0)),
    software_version=st.one_of(st.none(), TEXT),
)
HORIZONS = st.tuples(GEO_POINT, COVARIANCE, GEO_POINT, COVARIANCE, GEO_POINT, COVARIANCE).map(
    lambda values: [
        prediction_pb2.HorizonEstimate(
            horizon_s=horizon,
            position=values[2 * index],
            position_covariance=values[2 * index + 1],
        )
        for index, horizon in enumerate((5.0, 10.0, 30.0))
    ]
)
PREDICTION = st.builds(
    prediction_pb2.Prediction,
    track_id=TEXT,
    generated_at=TIMESTAMP,
    horizons=HORIZONS,
    destination_probabilities=destination_probabilities(),
    origin_heatmap=st.binary(max_size=32),
)
SIGHTING = st.builds(
    sighting_pb2.Sighting,
    sighting_id=TEXT,
    observed_at=TIMESTAMP,
    observer_position=GEO_POINT,
    bearing_deg=SIGNED,
    bearing_uncertainty_deg=NONNEGATIVE,
    estimated_altitude_m=st.one_of(st.none(), SIGNED),
    estimated_distance_m=st.one_of(st.none(), NONNEGATIVE),
    description=st.one_of(st.none(), TEXT),
    evidence_ids=st.lists(TEXT, max_size=3),
)
SIGNATURE_CLASS = st.builds(
    signature_class_pb2.SignatureClass,
    code=st.sampled_from(
        [
            signature_class_pb2.SIGNATURE_CLASS_CODE_C1,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C2,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C3,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C4,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C5,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C6,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C7,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C8,
            signature_class_pb2.SIGNATURE_CLASS_CODE_C9,
        ]
    ),
    label=TEXT,
    description=st.one_of(st.none(), TEXT),
    synthetic=st.booleans(),
)
TRACK = st.builds(
    track_pb2.Track,
    track_id=TEXT,
    site_id=TEXT,
    position=GEO_POINT,
    state_covariance=COVARIANCE,
    velocity_east_mps=SIGNED,
    velocity_north_mps=SIGNED,
    velocity_up_mps=SIGNED,
    class_probabilities=normalized_scores(),
    updated_at=TIMESTAMP,
    time_quality=TIME_QUALITY,
)
PAYLOADS = st.one_of(
    st.tuples(st.just("detection"), DETECTION),
    st.tuples(st.just("track"), TRACK),
    st.tuples(st.just("prediction"), PREDICTION),
    st.tuples(st.just("alert"), ALERT),
    st.tuples(st.just("node_status"), NODE_STATUS),
    st.tuples(st.just("coverage_status"), COVERAGE_STATUS),
    st.tuples(st.just("sighting"), SIGHTING),
    st.tuples(st.just("evidence"), EVIDENCE),
    st.tuples(st.just("signature_class"), SIGNATURE_CLASS),
)


@st.composite
def envelopes(draw: st.DrawFn) -> envelope_pb2.Envelope:
    payload_name, payload = draw(PAYLOADS)
    return envelope_pb2.Envelope(
        site_id=draw(TEXT),
        node_id=draw(TEXT),
        sequence=draw(st.integers(0, 2**64 - 1)),
        emitted_at=draw(TIMESTAMP),
        **{payload_name: payload},
    )


TOP_LEVEL_STRATEGIES: list[tuple[str, st.SearchStrategy[Message]]] = [
    ("Alert", ALERT),
    ("CoverageStatus", COVERAGE_STATUS),
    ("Detection", DETECTION),
    ("Envelope", envelopes()),
    ("Evidence", EVIDENCE),
    ("GroundTruth", GROUND_TRUTH),
    ("NodeStatus", NODE_STATUS),
    ("Prediction", PREDICTION),
    ("Sighting", SIGHTING),
    ("SignatureClass", SIGNATURE_CLASS),
    ("Track", TRACK),
]


@pytest.mark.req("REQ-FUN-002")
@pytest.mark.parametrize(
    ("name", "strategy"), TOP_LEVEL_STRATEGIES, ids=[name for name, _ in TOP_LEVEL_STRATEGIES]
)
@settings(max_examples=200, derandomize=True, deadline=None)
@given(data=st.data())
def test_roundtrip_determinista(
    name: str, strategy: st.SearchStrategy[Message], data: st.DataObject
) -> None:
    message = data.draw(strategy, label=name)
    assert validate(message) == []
    encoded = message.SerializeToString(deterministic=True)
    assert message.SerializeToString(deterministic=True) == encoded
    restored = type(message)()
    restored.ParseFromString(encoded)
    assert restored == message
    assert restored.SerializeToString(deterministic=True) == encoded


@pytest.mark.req("REQ-FUN-002")
@pytest.mark.parametrize(
    "message_type",
    [
        alert_pb2.Alert,
        coverage_status_pb2.CoverageStatus,
        detection_pb2.Detection,
        envelope_pb2.Envelope,
        evidence_pb2.Evidence,
        ground_truth_pb2.GroundTruth,
        node_status_pb2.NodeStatus,
        prediction_pb2.Prediction,
        sighting_pb2.Sighting,
        signature_class_pb2.SignatureClass,
        track_pb2.Track,
    ],
)
def test_bytes_truncados_producen_decode_error(message_type: type[Message]) -> None:
    # Campo desconocido 127, length-delimited: el último byte pertenece a su valor.
    complete = message_type().SerializeToString() + b"\xfa\x07\x02xy"
    message_type().ParseFromString(complete)
    with pytest.raises(DecodeError):
        message_type().ParseFromString(complete[:-1])
