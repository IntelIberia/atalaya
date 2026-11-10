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

class CoverageStatus(_message.Message):
    __slots__ = ("site_id", "region_id", "boundary", "estimated_probability", "uncertainty", "assessed_at")
    SITE_ID_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    UNCERTAINTY_FIELD_NUMBER: _ClassVar[int]
    ASSESSED_AT_FIELD_NUMBER: _ClassVar[int]
    site_id: str
    region_id: str
    boundary: _containers.RepeatedCompositeFieldContainer[_common_pb2.GeoPoint]
    estimated_probability: float
    uncertainty: _common_pb2.ErrorEllipse
    assessed_at: _timestamp_pb2.Timestamp
    def __init__(self, site_id: _Optional[str] = ..., region_id: _Optional[str] = ..., boundary: _Optional[_Iterable[_Union[_common_pb2.GeoPoint, _Mapping]]] = ..., estimated_probability: _Optional[float] = ..., uncertainty: _Optional[_Union[_common_pb2.ErrorEllipse, _Mapping]] = ..., assessed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
