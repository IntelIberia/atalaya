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

class Track(_message.Message):
    __slots__ = ("track_id", "site_id", "position", "state_covariance", "velocity_east_mps", "velocity_north_mps", "velocity_up_mps", "class_probabilities", "updated_at", "time_quality")
    TRACK_ID_FIELD_NUMBER: _ClassVar[int]
    SITE_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    STATE_COVARIANCE_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_EAST_MPS_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_NORTH_MPS_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_UP_MPS_FIELD_NUMBER: _ClassVar[int]
    CLASS_PROBABILITIES_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    TIME_QUALITY_FIELD_NUMBER: _ClassVar[int]
    track_id: str
    site_id: str
    position: _common_pb2.GeoPoint
    state_covariance: _common_pb2.PositionCovariance
    velocity_east_mps: float
    velocity_north_mps: float
    velocity_up_mps: float
    class_probabilities: _containers.RepeatedCompositeFieldContainer[_common_pb2.ClassScore]
    updated_at: _timestamp_pb2.Timestamp
    time_quality: _common_pb2.TimeQuality
    def __init__(self, track_id: _Optional[str] = ..., site_id: _Optional[str] = ..., position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., state_covariance: _Optional[_Union[_common_pb2.PositionCovariance, _Mapping]] = ..., velocity_east_mps: _Optional[float] = ..., velocity_north_mps: _Optional[float] = ..., velocity_up_mps: _Optional[float] = ..., class_probabilities: _Optional[_Iterable[_Union[_common_pb2.ClassScore, _Mapping]]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., time_quality: _Optional[_Union[_common_pb2.TimeQuality, _Mapping]] = ...) -> None: ...
