"""Shared typing primitives for the cfgable framework."""

from pathlib import Path
from typing import Any, Dict, Optional, Protocol, Type, TypeVar, Union

from pydantic import BaseModel
from typing_extensions import runtime_checkable

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)
T = TypeVar("T")


@runtime_checkable
class DataClassProto(Protocol):
    """Protocol for dataclass types."""

    @classmethod
    def __dataclass_fields__(cls) -> Dict[str, Any]: ...


# A config is a pydantic model or a dataclass instance.
ConfigType = Union[BaseModel, DataClassProto]
# Things that can be *resolved into* a config: a config type, a mapping of
# fields, or a path/dotted-string pointing at one.
OtherCfgType = Optional[
    Union[Type[Union[DataClassProto, BaseModel]], Dict[str, Any], str, Path]
]
AllConfigType = Union[ConfigType, OtherCfgType]
