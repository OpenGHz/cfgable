from collections import OrderedDict

import pytest

from cfgable import get_fully_qualified_class_name, import_string


def test_import_string_returns_object():
    assert import_string("collections.OrderedDict") is OrderedDict


def test_import_string_bad_path_raises():
    with pytest.raises(Exception):
        import_string("collections.NoSuchThingHere")


def test_get_fully_qualified_class_name_for_class_and_instance():
    assert get_fully_qualified_class_name(OrderedDict) == "collections.OrderedDict"
    assert get_fully_qualified_class_name(OrderedDict()) == "collections.OrderedDict"
