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

class NodeHealth(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NODE_HEALTH_UNSPECIFIED: _ClassVar[NodeHealth]
    NODE_HEALTH_HEALTHY: _ClassVar[NodeHealth]
    NODE_HEALTH_DEGRADED: _ClassVar[NodeHealth]
    NODE_HEALTH_FAILED: _ClassVar[NodeHealth]
NODE_HEALTH_UNSPECIFIED: NodeHealth
NODE_HEALTH_HEALTHY: NodeHealth
NODE_HEALTH_DEGRADED: NodeHealth
NODE_HEALTH_FAILED: NodeHealth

class NodeStatus(_message.Message):
    __slots__ = ("site_id", "node_id", "observed_at", "health", "location", "time_quality", "battery_percent", "software_version")
    SITE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    HEALTH_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    TIME_QUALITY_FIELD_NUMBER: _ClassVar[int]
    BATTERY_PERCENT_FIELD_NUMBER: _ClassVar[int]
    SOFTWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    site_id: str
    node_id: str
    observed_at: _timestamp_pb2.Timestamp
    health: NodeHealth
    location: _common_pb2.GeoPoint
    time_quality: _common_pb2.TimeQuality
    battery_percent: float
    software_version: str
    def __init__(self, site_id: _Optional[str] = ..., node_id: _Optional[str] = ..., observed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., health: _Optional[_Union[NodeHealth, str]] = ..., location: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., time_quality: _Optional[_Union[_common_pb2.TimeQuality, _Mapping]] = ..., battery_percent: _Optional[float] = ..., software_version: _Optional[str] = ...) -> None: ...
