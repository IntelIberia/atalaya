import datetime

from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Evidence(_message.Message):
    __slots__ = ("evidence_id", "sha256", "media_type", "captured_at", "custodian_pseudonym", "custody_signature")
    EVIDENCE_ID_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    MEDIA_TYPE_FIELD_NUMBER: _ClassVar[int]
    CAPTURED_AT_FIELD_NUMBER: _ClassVar[int]
    CUSTODIAN_PSEUDONYM_FIELD_NUMBER: _ClassVar[int]
    CUSTODY_SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    evidence_id: str
    sha256: str
    media_type: str
    captured_at: _timestamp_pb2.Timestamp
    custodian_pseudonym: str
    custody_signature: bytes
    def __init__(self, evidence_id: _Optional[str] = ..., sha256: _Optional[str] = ..., media_type: _Optional[str] = ..., captured_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., custodian_pseudonym: _Optional[str] = ..., custody_signature: _Optional[bytes] = ...) -> None: ...
