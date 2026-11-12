from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class Sensitivity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SENSITIVITY_UNSPECIFIED: _ClassVar[Sensitivity]
    PUBLIC: _ClassVar[Sensitivity]
    OPERATOR: _ClassVar[Sensitivity]
    FCSE_ONLY: _ClassVar[Sensitivity]
SENSITIVITY_UNSPECIFIED: Sensitivity
PUBLIC: Sensitivity
OPERATOR: Sensitivity
FCSE_ONLY: Sensitivity
SENSITIVITY_FIELD_NUMBER: _ClassVar[int]
sensitivity: _descriptor.FieldDescriptor
REQUIRED_FIELD_NUMBER: _ClassVar[int]
required: _descriptor.FieldDescriptor
