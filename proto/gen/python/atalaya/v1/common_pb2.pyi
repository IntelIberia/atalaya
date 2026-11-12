from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GeoPoint(_message.Message):
    __slots__ = ("latitude_deg", "longitude_deg", "altitude_m")
    LATITUDE_DEG_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_DEG_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_M_FIELD_NUMBER: _ClassVar[int]
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    def __init__(self, latitude_deg: _Optional[float] = ..., longitude_deg: _Optional[float] = ..., altitude_m: _Optional[float] = ...) -> None: ...

class PositionCovariance(_message.Message):
    __slots__ = ("east_east_m2", "east_north_m2", "east_up_m2", "north_north_m2", "north_up_m2", "up_up_m2")
    EAST_EAST_M2_FIELD_NUMBER: _ClassVar[int]
    EAST_NORTH_M2_FIELD_NUMBER: _ClassVar[int]
    EAST_UP_M2_FIELD_NUMBER: _ClassVar[int]
    NORTH_NORTH_M2_FIELD_NUMBER: _ClassVar[int]
    NORTH_UP_M2_FIELD_NUMBER: _ClassVar[int]
    UP_UP_M2_FIELD_NUMBER: _ClassVar[int]
    east_east_m2: float
    east_north_m2: float
    east_up_m2: float
    north_north_m2: float
    north_up_m2: float
    up_up_m2: float
    def __init__(self, east_east_m2: _Optional[float] = ..., east_north_m2: _Optional[float] = ..., east_up_m2: _Optional[float] = ..., north_north_m2: _Optional[float] = ..., north_up_m2: _Optional[float] = ..., up_up_m2: _Optional[float] = ...) -> None: ...

class ErrorEllipse(_message.Message):
    __slots__ = ("semi_major_axis_m", "semi_minor_axis_m", "orientation_deg", "confidence_level")
    SEMI_MAJOR_AXIS_M_FIELD_NUMBER: _ClassVar[int]
    SEMI_MINOR_AXIS_M_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_DEG_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_LEVEL_FIELD_NUMBER: _ClassVar[int]
    semi_major_axis_m: float
    semi_minor_axis_m: float
    orientation_deg: float
    confidence_level: float
    def __init__(self, semi_major_axis_m: _Optional[float] = ..., semi_minor_axis_m: _Optional[float] = ..., orientation_deg: _Optional[float] = ..., confidence_level: _Optional[float] = ...) -> None: ...

class ClassScore(_message.Message):
    __slots__ = ("class_id", "probability")
    CLASS_ID_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    class_id: str
    probability: float
    def __init__(self, class_id: _Optional[str] = ..., probability: _Optional[float] = ...) -> None: ...

class TimeQuality(_message.Message):
    __slots__ = ("pps_valid", "clock_offset_ms", "uncertainty_ms")
    PPS_VALID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_OFFSET_MS_FIELD_NUMBER: _ClassVar[int]
    UNCERTAINTY_MS_FIELD_NUMBER: _ClassVar[int]
    pps_valid: bool
    clock_offset_ms: float
    uncertainty_ms: float
    def __init__(self, pps_valid: _Optional[bool] = ..., clock_offset_ms: _Optional[float] = ..., uncertainty_ms: _Optional[float] = ...) -> None: ...
