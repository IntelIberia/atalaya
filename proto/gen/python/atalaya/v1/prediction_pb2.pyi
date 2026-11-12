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

class HorizonEstimate(_message.Message):
    __slots__ = ("horizon_s", "position", "position_covariance")
    HORIZON_S_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    POSITION_COVARIANCE_FIELD_NUMBER: _ClassVar[int]
    horizon_s: float
    position: _common_pb2.GeoPoint
    position_covariance: _common_pb2.PositionCovariance
    def __init__(self, horizon_s: _Optional[float] = ..., position: _Optional[_Union[_common_pb2.GeoPoint, _Mapping]] = ..., position_covariance: _Optional[_Union[_common_pb2.PositionCovariance, _Mapping]] = ...) -> None: ...

class DestinationProbability(_message.Message):
    __slots__ = ("destination_id", "probability")
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    destination_id: str
    probability: float
    def __init__(self, destination_id: _Optional[str] = ..., probability: _Optional[float] = ...) -> None: ...

class Prediction(_message.Message):
    __slots__ = ("track_id", "generated_at", "horizons", "destination_probabilities", "origin_heatmap")
    TRACK_ID_FIELD_NUMBER: _ClassVar[int]
    GENERATED_AT_FIELD_NUMBER: _ClassVar[int]
    HORIZONS_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_PROBABILITIES_FIELD_NUMBER: _ClassVar[int]
    ORIGIN_HEATMAP_FIELD_NUMBER: _ClassVar[int]
    track_id: str
    generated_at: _timestamp_pb2.Timestamp
    horizons: _containers.RepeatedCompositeFieldContainer[HorizonEstimate]
    destination_probabilities: _containers.RepeatedCompositeFieldContainer[DestinationProbability]
    origin_heatmap: bytes
    def __init__(self, track_id: _Optional[str] = ..., generated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., horizons: _Optional[_Iterable[_Union[HorizonEstimate, _Mapping]]] = ..., destination_probabilities: _Optional[_Iterable[_Union[DestinationProbability, _Mapping]]] = ..., origin_heatmap: _Optional[bytes] = ...) -> None: ...
