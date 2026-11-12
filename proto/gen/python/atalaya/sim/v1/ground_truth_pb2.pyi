import datetime

from atalaya.v1 import common_pb2 as _common_pb2
from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GroundTruth(_message.Message):
    __slots__ = ("target_id", "simulated_at", "true_position", "class_id", "is_forged", "launch_point")
    TARGET_ID_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_AT_FIELD_NUMBER: _ClassVar[int]
    TRUE_POSITION_FIELD_NUMBER: _ClassVar[int]
    CLASS_ID_FIELD_NUMBER: _ClassVar[int]
    IS_FORGED_FIELD_NUMBER: _ClassVar[int]
    LAUNCH_POINT_FIELD_NUMBER: _ClassVar[int]
    target_id: str
    simulated_at: _timestamp_pb2.Timestamp
    true_position: _common_pb2.GeoPoint
    class_id: str
    is_forged: bool
    launch_point: _common_pb2.GeoPoint
    def __init__(self, target_id: _Optional[str] = ..., simulated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., true_position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., class_id: _Optional[str] = ..., is_forged: _Optional[bool] = ..., launch_point: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ...) -> None: ...
