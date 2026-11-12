from atalaya.v1 import options_pb2 as _options_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SignatureClassCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SIGNATURE_CLASS_CODE_UNSPECIFIED: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C1: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C2: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C3: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C4: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C5: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C6: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C7: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C8: _ClassVar[SignatureClassCode]
    SIGNATURE_CLASS_CODE_C9: _ClassVar[SignatureClassCode]
SIGNATURE_CLASS_CODE_UNSPECIFIED: SignatureClassCode
SIGNATURE_CLASS_CODE_C1: SignatureClassCode
SIGNATURE_CLASS_CODE_C2: SignatureClassCode
SIGNATURE_CLASS_CODE_C3: SignatureClassCode
SIGNATURE_CLASS_CODE_C4: SignatureClassCode
SIGNATURE_CLASS_CODE_C5: SignatureClassCode
SIGNATURE_CLASS_CODE_C6: SignatureClassCode
SIGNATURE_CLASS_CODE_C7: SignatureClassCode
SIGNATURE_CLASS_CODE_C8: SignatureClassCode
SIGNATURE_CLASS_CODE_C9: SignatureClassCode

class SignatureClass(_message.Message):
    __slots__ = ("code", "label", "description", "synthetic")
    CODE_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SYNTHETIC_FIELD_NUMBER: _ClassVar[int]
    code: SignatureClassCode
    label: str
    description: str
    synthetic: bool
    def __init__(self, code: _Optional[_Union[SignatureClassCode, str]] = ..., label: _Optional[str] = ..., description: _Optional[str] = ..., synthetic: _Optional[bool] = ...) -> None: ...
