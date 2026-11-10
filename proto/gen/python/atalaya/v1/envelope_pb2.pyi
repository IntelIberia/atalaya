import datetime

from atalaya.v1 import alert_pb2 as _alert_pb2
from atalaya.v1 import coverage_status_pb2 as _coverage_status_pb2
from atalaya.v1 import detection_pb2 as _detection_pb2
from atalaya.v1 import evidence_pb2 as _evidence_pb2
from atalaya.v1 import node_status_pb2 as _node_status_pb2
from atalaya.v1 import options_pb2 as _options_pb2
from atalaya.v1 import prediction_pb2 as _prediction_pb2
from atalaya.v1 import signature_class_pb2 as _signature_class_pb2
from atalaya.v1 import sighting_pb2 as _sighting_pb2
from atalaya.v1 import track_pb2 as _track_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Envelope(_message.Message):
    __slots__ = ("site_id", "node_id", "sequence", "emitted_at", "detection", "track", "prediction", "alert", "node_status", "coverage_status", "sighting", "evidence", "signature_class")
    SITE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    EMITTED_AT_FIELD_NUMBER: _ClassVar[int]
    DETECTION_FIELD_NUMBER: _ClassVar[int]
    TRACK_FIELD_NUMBER: _ClassVar[int]
    PREDICTION_FIELD_NUMBER: _ClassVar[int]
    ALERT_FIELD_NUMBER: _ClassVar[int]
    NODE_STATUS_FIELD_NUMBER: _ClassVar[int]
    COVERAGE_STATUS_FIELD_NUMBER: _ClassVar[int]
    SIGHTING_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_CLASS_FIELD_NUMBER: _ClassVar[int]
    site_id: str
    node_id: str
    sequence: int
    emitted_at: _timestamp_pb2.Timestamp
    detection: _detection_pb2.Detection
    track: _track_pb2.Track
    prediction: _prediction_pb2.Prediction
    alert: _alert_pb2.Alert
    node_status: _node_status_pb2.NodeStatus
    coverage_status: _coverage_status_pb2.CoverageStatus
    sighting: _sighting_pb2.Sighting
    evidence: _evidence_pb2.Evidence
    signature_class: _signature_class_pb2.SignatureClass
    def __init__(self, site_id: _Optional[str] = ..., node_id: _Optional[str] = ..., sequence: _Optional[int] = ..., emitted_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., detection: _Optional[_Union[_detection_pb2.Detection, _Mapping]] = ..., track: _Optional[_Union[_track_pb2.Track, _Mapping]] = ..., prediction: _Optional[_Union[_prediction_pb2.Prediction, _Mapping]] = ..., alert: _Optional[_Union[_alert_pb2.Alert, _Mapping]] = ..., node_status: _Optional[_Union[_node_status_pb2.NodeStatus, _Mapping]] = ..., coverage_status: _Optional[_Union[_coverage_status_pb2.CoverageStatus, _Mapping]] = ..., sighting: _Optional[_Union[_sighting_pb2.Sighting, _Mapping]] = ..., evidence: _Optional[_Union[_evidence_pb2.Evidence, _Mapping]] = ..., signature_class: _Optional[_Union[_signature_class_pb2.SignatureClass, _Mapping]] = ...) -> None: ...
