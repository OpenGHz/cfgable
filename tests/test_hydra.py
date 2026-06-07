"""Hydra-bridge tests. Skipped entirely unless the [hydra] extra is installed."""

import pytest

pytest.importorskip("hydra")
pytest.importorskip("omegaconf")

from pydantic import BaseModel, ConfigDict  # noqa: E402


class HCfg(BaseModel, frozen=True):
    model_config = ConfigDict(use_attribute_docstrings=True)

    a: int = 1
    """first"""
    b: int = 2
    """second"""


def test_hydra_instance_from_dict_builds_target():
    from cfgable.hydra_utils import hydra_instance_from_dict

    obj = hydra_instance_from_dict({"_target_": f"{__name__}.HCfg", "a": 5})
    assert isinstance(obj, HCfg)
    assert obj.a == 5 and obj.b == 2


def test_relative_path_between(tmp_path):
    from cfgable.hydra_utils import relative_path_between

    base = tmp_path / "a" / "b"
    target = tmp_path / "a" / "c"
    base.mkdir(parents=True)
    target.mkdir(parents=True)
    assert str(relative_path_between(target, base)) == "../c"
