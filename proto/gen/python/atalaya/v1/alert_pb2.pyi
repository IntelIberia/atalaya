import datetime

from atalaya.v1 import common_pb2 as _common_pb2
from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AlertLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ALERT_LEVEL_UNSPECIFIED: _ClassVar[AlertLevel]
    ALERT_LEVEL_INFORMATION: _ClassVar[AlertLevel]
    ALERT_LEVEL_WARNING: _ClassVar[AlertLevel]
    ALERT_LEVEL_CRITICAL: _ClassVar[AlertLevel]
ALERT_LEVEL_UNSPECIFIED: AlertLevel
ALERT_LEVEL_INFORMATION: AlertLevel
ALERT_LEVEL_WARNING: AlertLevel
ALERT_LEVEL_CRITICAL: AlertLevel

class Alert(_message.Message):
    __slots__ = ("alert_id", "track_id", "level", "confidence", "created_at", "last_known_position", "summary")
    ALERT_ID_FIELD_NUMBER: _ClassVar[int]
    TRACK_ID_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_KNOWN_POSITION_FIELD_NUMBER: _ClassVar[int]
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    alert_id: str
    track_id: str
    level: AlertLevel
    confidence: float
    created_at: _timestamp_pb2.Timestamp
    last_known_position: _common_pb2.GeoPoint
    summary: str
    def __init__(self, alert_id: _Optional[str] = ..., track_id: _Optional[str] = ..., level: _Optional[_Union[AlertLevel, str]] = ..., confidence: _Optional[float] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., last_known_position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., summary: _Optional[str] = ...) -> None: ...
