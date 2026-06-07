"""Helpers for mutating otherwise-frozen pydantic models in a controlled way.

Frozen configs are the default in this framework (a component should not rewrite
the settings it was handed). Occasionally a component genuinely needs to update a
frozen config — e.g. it is specifically designed to derive and reassign values.
``ForceSetAttr`` / ``force_set_attr`` make that explicit and localized rather than
dropping ``frozen`` altogether.
"""

from functools import wraps
from typing import Any, Generic

from pydantic import BaseModel

from ._typing import BaseModelT


def validate_field(obj: BaseModel, name: str, value: Any):
    """Validate a field value using the pydantic model's assignment validator."""
    obj.__pydantic_validator__.validate_assignment(obj, name, value)


class ForceSetAttr(Generic[BaseModelT]):
    """Context manager to temporarily allow setting attributes on frozen models."""

    def __init__(self, obj: BaseModelT):
        if not isinstance(obj, BaseModel):
            raise TypeError("Only Pydantic BaseModel instances are supported.")
        self._obj = obj

    def __enter__(self) -> BaseModelT:
        self._original_setattr = self._obj.__class__.__setattr__
        self._obj.__class__.__setattr__ = self._setattr
        return self._obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._obj.__class__.__setattr__ = self._original_setattr

    def _setattr(self, name, value):
        obj = self._obj
        config = obj.model_config
        if config.get("frozen", False):
            if config.get("validate_assignment", False):
                validate_field(obj, name, value)
            else:
                object.__setattr__(obj, name, value)
        else:
            setattr(obj, name, value)


def force_set_attr(method):
    """Decorator to force attribute setting on frozen pydantic models."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with ForceSetAttr(self):
            return method(self, *args, **kwargs)

    return wrapper


force_validate_field = force_set_attr(validate_field)
