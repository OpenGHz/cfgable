"""Class/string reflection helpers used by the cfgable framework."""

from inspect import isclass
from typing import Any, Type, Union

from pydantic import ImportString, validate_call

from ._typing import T


def get_fully_qualified_class_name(obj_or_cls) -> str:
    """Return ``"module.QualName"`` for a class or an instance."""
    if isinstance(obj_or_cls, type):
        cls = obj_or_cls
    else:
        cls = type(obj_or_cls)
    return f"{cls.__module__}.{cls.__qualname__}"


def get_full_class_name(obj: Union[Any, Type]) -> str:
    """Return ``"module.QualName"`` for a class or an instance."""
    cls = obj if isclass(obj) else obj.__class__
    return f"{cls.__module__}.{cls.__qualname__}"


@validate_call
def import_string(import_path: ImportString[T]) -> T:
    """Import and return the object at a dotted path (validated by pydantic)."""
    return import_path
