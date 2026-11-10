import datetime

from atalaya.v1 import common_pb2 as _common_pb2
from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SensorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SENSOR_TYPE_UNSPECIFIED: _ClassVar[SensorType]
    SENSOR_TYPE_ACOUSTIC: _ClassVar[SensorType]
    SENSOR_TYPE_REMOTE_ID: _ClassVar[SensorType]
    SENSOR_TYPE_ADSB: _ClassVar[SensorType]
    SENSOR_TYPE_RF_PRESENCE: _ClassVar[SensorType]
    SENSOR_TYPE_HUMAN: _ClassVar[SensorType]

class RemoteIdStandard(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REMOTE_ID_STANDARD_UNSPECIFIED: _ClassVar[RemoteIdStandard]
    REMOTE_ID_STANDARD_EN_4709_002: _ClassVar[RemoteIdStandard]
    REMOTE_ID_STANDARD_ASTM_F3411: _ClassVar[RemoteIdStandard]
SENSOR_TYPE_UNSPECIFIED: SensorType
SENSOR_TYPE_ACOUSTIC: SensorType
SENSOR_TYPE_REMOTE_ID: SensorType
SENSOR_TYPE_ADSB: SensorType
SENSOR_TYPE_RF_PRESENCE: SensorType
SENSOR_TYPE_HUMAN: SensorType
REMOTE_ID_STANDARD_UNSPECIFIED: RemoteIdStandard
REMOTE_ID_STANDARD_EN_4709_002: RemoteIdStandard
REMOTE_ID_STANDARD_ASTM_F3411: RemoteIdStandard

class AcousticBandLevel(_message.Message):
    __slots__ = ("center_frequency_hz", "level_db_spl")
    CENTER_FREQUENCY_HZ_FIELD_NUMBER: _ClassVar[int]
    LEVEL_DB_SPL_FIELD_NUMBER: _ClassVar[int]
    center_frequency_hz: float
    level_db_spl: float
    def __init__(self, center_frequency_hz: _Optional[float] = ..., level_db_spl: _Optional[float] = ...) -> None: ...

class AcousticObservation(_message.Message):
    __slots__ = ("band_levels", "signal_to_noise_db")
    BAND_LEVELS_FIELD_NUMBER: _ClassVar[int]
    SIGNAL_TO_NOISE_DB_FIELD_NUMBER: _ClassVar[int]
    band_levels: _containers.RepeatedCompositeFieldContainer[AcousticBandLevel]
    signal_to_noise_db: float
    def __init__(self, band_levels: _Optional[_Iterable[_Union[AcousticBandLevel, _Mapping]]] = ..., signal_to_noise_db: _Optional[float] = ...) -> None: ...

class RemoteIdObservation(_message.Message):
    __slots__ = ("operator_id", "operator_location", "uas_id", "self_id_description", "standard", "aircraft_position", "message_time")
    OPERATOR_ID_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_LOCATION_FIELD_NUMBER: _ClassVar[int]
    UAS_ID_FIELD_NUMBER: _ClassVar[int]
    SELF_ID_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    STANDARD_FIELD_NUMBER: _ClassVar[int]
    AIRCRAFT_POSITION_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TIME_FIELD_NUMBER: _ClassVar[int]
    operator_id: str
    operator_location: _common_pb2.GeoPoint
    uas_id: str
    self_id_description: str
    standard: RemoteIdStandard
    aircraft_position: _common_pb2.GeoPoint
    message_time: _timestamp_pb2.Timestamp
    def __init__(self, operator_id: _Optional[str] = ..., operator_location: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., uas_id: _Optional[str] = ..., self_id_description: _Optional[str] = ..., standard: _Optional[_Union[RemoteIdStandard, str]] = ..., aircraft_position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., message_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AdsbObservation(_message.Message):
    __slots__ = ("callsign", "aircraft_position", "position_covariance", "message_time")
    CALLSIGN_FIELD_NUMBER: _ClassVar[int]
    AIRCRAFT_POSITION_FIELD_NUMBER: _ClassVar[int]
    POSITION_COVARIANCE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TIME_FIELD_NUMBER: _ClassVar[int]
    callsign: str
    aircraft_position: _common_pb2.GeoPoint
    position_covariance: _common_pb2.PositionCovariance
    message_time: _timestamp_pb2.Timestamp
    def __init__(self, callsign: _Optional[str] = ..., aircraft_position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., position_covariance: _Optional[_Union[_common_pb2.PositionCovariance, _Mapping]] = ..., message_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class RfPresenceObservation(_message.Message):
    __slots__ = ("center_frequency_hz", "bandwidth_hz", "received_power_dbm")
    CENTER_FREQUENCY_HZ_FIELD_NUMBER: _ClassVar[int]
    BANDWIDTH_HZ_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_POWER_DBM_FIELD_NUMBER: _ClassVar[int]
    center_frequency_hz: float
    bandwidth_hz: float
    received_power_dbm: float
    def __init__(self, center_frequency_hz: _Optional[float] = ..., bandwidth_hz: _Optional[float] = ..., received_power_dbm: _Optional[float] = ...) -> None: ...

class HumanObservation(_message.Message):
    __slots__ = ("sighting_id",)
    SIGHTING_ID_FIELD_NUMBER: _ClassVar[int]
    sighting_id: str
    def __init__(self, sighting_id: _Optional[str] = ...) -> None: ...

class Detection(_message.Message):
    __slots__ = ("detection_id", "site_id", "node_id", "observed_at", "sensor_type", "time_quality", "position", "position_covariance", "position_error", "bearing_deg", "bearing_uncertainty_deg", "class_scores", "detection_confidence", "acoustic", "remote_id", "adsb", "rf_presence", "human")
    DETECTION_ID_FIELD_NUMBER: _ClassVar[int]
    SITE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    SENSOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    TIME_QUALITY_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    POSITION_COVARIANCE_FIELD_NUMBER: _ClassVar[int]
    POSITION_ERROR_FIELD_NUMBER: _ClassVar[int]
    BEARING_DEG_FIELD_NUMBER: _ClassVar[int]
    BEARING_UNCERTAINTY_DEG_FIELD_NUMBER: _ClassVar[int]
    CLASS_SCORES_FIELD_NUMBER: _ClassVar[int]
    DETECTION_CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    ACOUSTIC_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ID_FIELD_NUMBER: _ClassVar[int]
    ADSB_FIELD_NUMBER: _ClassVar[int]
    RF_PRESENCE_FIELD_NUMBER: _ClassVar[int]
    HUMAN_FIELD_NUMBER: _ClassVar[int]
    detection_id: str
    site_id: str
    node_id: str
    observed_at: _timestamp_pb2.Timestamp
    sensor_type: SensorType
    time_quality: _common_pb2.TimeQuality
    position: _common_pb2.GeoPoint
    position_covariance: _common_pb2.PositionCovariance
    position_error: _common_pb2.ErrorEllipse
    bearing_deg: float
    bearing_uncertainty_deg: float
    class_scores: _containers.RepeatedCompositeFieldContainer[_common_pb2.ClassScore]
    detection_confidence: float
    acoustic: AcousticObservation
    remote_id: RemoteIdObservation
    adsb: AdsbObservation
    rf_presence: RfPresenceObservation
    human: HumanObservation
    def __init__(self, detection_id: _Optional[str] = ..., site_id: _Optional[str] = ..., node_id: _Optional[str] = ..., observed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., sensor_type: _Optional[_Union[SensorType, str]] = ..., time_quality: _Optional[_Union[_common_pb2.TimeQuality, _Mapping]] = ..., position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., position_covariance: _Optional[_Union[_common_pb2.PositionCovariance, _Mapping]] = ..., position_error: _Optional[_Union[_common_pb2.ErrorEllipse, _Mapping]] = ..., bearing_deg: _Optional[float] = ..., bearing_uncertainty_deg: _Optional[float] = ..., class_scores: _Optional[_Iterable[_Union[_common_pb2.ClassScore, _Mapping]]] = ..., detection_confidence: _Optional[float] = ..., acoustic: _Optional[_Union[AcousticObservation, _Mapping]] = ..., remote_id: _Optional[_Union[RemoteIdObservation, _Mapping]] = ..., adsb: _Optional[_Union[AdsbObservation, _Mapping]] = ..., rf_presence: _Optional[_Union[RfPresenceObservation, _Mapping]] = ..., human: _Optional[_Union[HumanObservation, _Mapping]] = ...) -> None: ...
