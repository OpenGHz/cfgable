"""Tests for the construction metaclass and the ConfigurableBasis mixins.

The cfgable subclasses are defined at module scope on purpose: the metaclass
resolves the `config` type via ``get_type_hints(cls.__init__)``, which looks names up
in the defining module's globals. Defining them here exercises that resolution after
the framework was relocated out of mcap_data_loader.
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass

import pytest
from pydantic import BaseModel, ConfigDict

from cfgable import (
    ConfigurableBasis,
    InitConfigMixin,
    NoConfig,
    dump_or_repr,
    fetch_config,
)


class CfgA(BaseModel, frozen=True):
    """A sample frozen config."""

    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")

    a: int = 1
    """first value"""
    b: int = 2
    """second value"""


class Comp(InitConfigMixin):
    """A plain component taking a single pydantic config."""

    def __init__(self, config: CfgA):
        self.config = config


@dataclass(frozen=True)
class DCfg:
    x: int = 1


class DComp(InitConfigMixin):
    """A component taking a single dataclass config."""

    def __init__(self, config: DCfg):
        self.config = config


# ---- construction paths ------------------------------------------------------


def test_build_from_flat_kwargs():
    # The Hydra-style path: instantiate(cls, **fields) assembles the config.
    c = Comp(a=5, b=6)
    assert isinstance(c.config, CfgA)
    assert (c.config.a, c.config.b) == (5, 6)


def test_build_from_config_object_is_not_copied():
    cfg = CfgA(a=5)
    c = Comp(cfg)
    assert c.config is cfg


def test_build_from_mapping():
    c = Comp({"a": 7})
    assert isinstance(c.config, CfgA)
    assert (c.config.a, c.config.b) == (7, 2)


def test_kwargs_override_existing_config_leaves_original_intact():
    cfg = CfgA(a=1)
    c = Comp(cfg, a=9)
    assert c.config.a == 9
    assert cfg.a == 1  # original frozen config untouched (model_copy)


def test_extra_kwargs_are_dropped_with_warning(caplog):
    with caplog.at_level(logging.WARNING):
        c = Comp(CfgA(), z=5)
    assert isinstance(c.config, CfgA)
    assert "Extra fields" in caplog.text


def test_target_key_is_stripped_from_mapping_fields():
    c = Comp({"_target_": f"{__name__}.CfgA", "a": 3})
    assert isinstance(c.config, CfgA)
    assert c.config.a == 3


def test_dataclass_config():
    d = DComp(x=5)
    assert isinstance(d.config, DCfg)
    assert d.config.x == 5


# ---- NoConfig ----------------------------------------------------------------


class Empty(ConfigurableBasis):
    """A component that needs no configuration."""

    config = None

    def on_configure(self) -> bool:
        return True


def test_no_config_placeholder():
    e = Empty()
    assert isinstance(e.config, NoConfig)


# ---- config_post_init / configure / WeakSet ----------------------------------


class WithPost(ConfigurableBasis):
    """Exercises config_post_init and the configure() lifecycle."""

    interface: None  # no interface object to build in configure()

    def __init__(self, config: CfgA):
        self.config = config

    def config_post_init(self):
        super().config_post_init()
        self.ready = True

    def on_configure(self) -> bool:
        return True


def test_config_post_init_fires():
    w = WithPost(a=1)
    assert w.ready is True
    assert w.configured is False  # ConfigurableBasis.config_post_init set _configured


def test_configure_and_all_configure():
    w = WithPost(a=1)
    assert w.configure() is True
    assert w.configured is True
    with pytest.raises(RuntimeError):
        w.configure()  # already configured
    assert WithPost.all_configure() is True  # idempotent over tracked instances


# ---- copy --------------------------------------------------------------------


def test_copy_basemodel_config():
    c = Comp(CfgA(a=1, b=2))
    c2 = c.copy(update={"a": 9})
    assert isinstance(c2, Comp) and c2 is not c
    assert c2.config.a == 9 and c2.config.b == 2
    assert c.config.a == 1  # original untouched


def test_copy_dataclass_config_rejects_update():
    d = DComp(DCfg(x=1))
    assert isinstance(d.copy(), DComp)
    with pytest.raises(NotImplementedError):
        d.copy(update={"x": 2})


# ---- dump / save_config ------------------------------------------------------


def test_dump_includes_target():
    c = Comp(CfgA(a=3))
    dumped = c.dump()
    assert dumped["a"] == 3
    assert dumped["_target_"] == f"{__name__}.Comp"


def test_save_config_roundtrip_yaml_and_json(tmp_path):
    import yaml

    c = Comp(CfgA(a=4, b=5))

    yaml_path = tmp_path / "c.yaml"
    c.save_config(yaml_path)
    reloaded = CfgA(**yaml.safe_load(yaml_path.read_text()))
    assert reloaded == c.config

    json_path = tmp_path / "c.json"
    c.save_config(json_path)
    data = json.loads(json_path.read_text())
    assert data["a"] == 4 and data["_target_"] == f"{__name__}.Comp"


# ---- fetch_config (vendored get_in) ------------------------------------------


def test_fetch_config():
    cfg = {"a": {"b": 1}}
    assert fetch_config(cfg, "a.b") == 1
    assert fetch_config(cfg, "a.c", default=2, no_default=False) == 2
    with pytest.raises(KeyError):
        fetch_config(cfg, "a.c")  # no_default defaults to True


# ---- dump_or_repr ------------------------------------------------------------


def test_dump_or_repr_branches():
    c = Comp(CfgA(a=1))
    assert dump_or_repr(c)["_target_"] == f"{__name__}.Comp"

    class HasConfig:
        config = CfgA(a=2)

    assert dump_or_repr(HasConfig())["a"] == 2

    sentinel = object()
    assert dump_or_repr(sentinel) == repr(sentinel)
    assert dump_or_repr(sentinel, handler=lambda o: "handled") == "handled"


# ---- import isolation: core must not pull in hydra ---------------------------


def test_import_cfgable_does_not_import_hydra():
    code = (
        "import sys, cfgable; "
        "assert 'hydra' not in sys.modules and 'omegaconf' not in sys.modules"
    )
    subprocess.check_call([sys.executable, "-c", code])
