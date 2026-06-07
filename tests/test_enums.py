from enum import auto

from cfgable import StrEnum


class Color(StrEnum):
    red = auto()
    green = auto()
    BLUE = auto()


def test_members_are_strings():
    assert isinstance(Color.red, str)
    assert Color.red == "red"


def test_str_is_the_value():
    assert str(Color.green) == "green"


def test_auto_lowercases_member_name():
    assert Color.BLUE.value == "blue"
    assert Color.BLUE == "blue"


def test_repr_keeps_enum_style():
    # ReprEnum: str() is the value, repr() stays enum-style.
    assert "Color" in repr(Color.red)
    assert str(Color.red) == "red"
