import pytest
from pydantic import BaseModel, ConfigDict

from cfgable import ForceSetAttr, force_set_attr


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)
    x: int = 1


class FrozenNoValidate(BaseModel):
    model_config = ConfigDict(frozen=True)
    x: int = 1


def test_force_set_attr_allows_mutation_then_refreezes():
    f = Frozen(x=1)
    with pytest.raises(Exception):
        f.x = 2  # frozen
    with ForceSetAttr(f) as obj:
        obj.x = 5
    assert f.x == 5
    with pytest.raises(Exception):
        f.x = 6  # frozen again after the context


def test_force_set_attr_validates_bad_value():
    f = Frozen(x=1)
    with pytest.raises(Exception):
        with ForceSetAttr(f) as obj:
            obj.x = "not an int"


def test_force_set_attr_without_validate_uses_object_setattr():
    f = FrozenNoValidate(x=1)
    with ForceSetAttr(f) as obj:
        obj.x = 7
    assert f.x == 7


def test_force_set_attr_rejects_non_basemodel():
    with pytest.raises(TypeError):
        ForceSetAttr(object())


def test_force_set_attr_decorator():
    class Model(BaseModel):
        model_config = ConfigDict(frozen=True, validate_assignment=True)
        x: int = 1

        @force_set_attr
        def bump(self):
            self.x = self.x + 1

    m = Model(x=1)
    m.bump()
    assert m.x == 2
