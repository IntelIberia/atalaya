import datetime

from atalaya.v1 import common_pb2 as _common_pb2
from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Sighting(_message.Message):
    __slots__ = ("sighting_id", "observed_at", "observer_position", "bearing_deg", "bearing_uncertainty_deg", "estimated_altitude_m", "estimated_distance_m", "description", "evidence_ids")
    SIGHTING_ID_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    OBSERVER_POSITION_FIELD_NUMBER: _ClassVar[int]
    BEARING_DEG_FIELD_NUMBER: _ClassVar[int]
    BEARING_UNCERTAINTY_DEG_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_ALTITUDE_M_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_DISTANCE_M_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_IDS_FIELD_NUMBER: _ClassVar[int]
    sighting_id: str
    observed_at: _timestamp_pb2.Timestamp
    observer_position: _common_pb2.GeoPoint
    bearing_deg: float
    bearing_uncertainty_deg: float
    estimated_altitude_m: float
    estimated_distance_m: float
    description: str
    evidence_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, sighting_id: _Optional[str] = ..., observed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., observer_position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., bearing_deg: _Optional[float] = ..., bearing_uncertainty_deg: _Optional[float] = ..., estimated_altitude_m: _Optional[float] = ..., estimated_distance_m: _Optional[float] = ..., description: _Optional[str] = ..., evidence_ids: _Optional[_Iterable[str]] = ...) -> None: ...
