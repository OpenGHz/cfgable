# cfgable

English | [简体中文](README.zh-CN.md)

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built on pydantic](https://img.shields.io/badge/built%20on-pydantic-e92063.svg)](https://docs.pydantic.dev/)

A small, reusable configuration framework for Python, built on
[pydantic](https://docs.pydantic.dev/). It lets every component declare a **single
`config` object** and be constructed uniformly — from Python, from a YAML file, or from
Hydra — with validation happening once at the boundary.

The core depends only on pydantic; the Hydra bridge is optional.

## Requirements

- Python 3.9 or newer
- pydantic 2.x
- Hydra support requires the optional `hydra` extra

## Install

```bash
pip install "cfgable @ git+https://github.com/OpenGHz/cfgable.git"
pip install "cfgable[hydra] @ git+https://github.com/OpenGHz/cfgable.git"
```

From a local checkout, use `pip install .` for the core package or `pip install
".[hydra]"` for the optional Hydra bridge.

## The idea

1. A component's settings are a pydantic model (`*Config`), documented with attribute
   docstrings.
2. Every class takes **one** `config` parameter and reads fields off it.
3. Inheriting `ConfigurableBasis` lets the same class be built from an explicit config,
   a plain mapping, or **flat keyword arguments** — the shape Hydra's `instantiate`
   passes — because the `InitConfigMeta` metaclass assembles and validates the config
   for you, then calls `config_post_init()`.

```python
from typing import Optional
from pydantic import BaseModel, ConfigDict, PositiveInt
from cfgable import ConfigurableBasis


class CameraConfig(BaseModel, frozen=True):
    """Configuration for a camera."""

    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")

    device: str = "/dev/video0"
    """Video device path."""
    fps: PositiveInt = 30
    """Capture rate in frames per second."""
    serial: Optional[str] = None
    """Optional camera serial number for disambiguation."""


class Camera(ConfigurableBasis):
    """A camera built from a single validated config."""

    def __init__(self, config: CameraConfig):
        self.config = config

    def config_post_init(self):
        super().config_post_init()
        self._opened = False

    def on_configure(self) -> bool:
        self._opened = True
        return True


# All three build the same object:
cam = Camera(CameraConfig(fps=60))            # explicit config
cam = Camera({"fps": 60})                     # mapping
cam = Camera(fps=60)                          # flat kwargs (Hydra-style)
```

Use `ConfigurableBasis` when the component has a configure lifecycle. For plain
objects that only need config assembly, inherit from `InitConfigMixin`.

## With Hydra

Point `_target_` at the class and list the config fields as siblings; the metaclass turns
them into the `config` model:

```yaml
# camera.yaml
_target_: my_pkg.Camera
fps: 60
device: /dev/video2
```

```python
from cfgable.hydra_utils import init_hydra_config, hydra_instance

cam = hydra_instance(init_hydra_config("camera.yaml"))
```

For plain classes you can also nest the config under its own `_target_` so standard
`hydra.utils.instantiate` builds `Camera(config=CameraConfig(...))`.

## Round-tripping

Because a component keeps its whole `config`, it can serialize back to the config that
would rebuild it:

```python
cam.dump()                 # -> dict of fields + a "_target_" pointing at the class
cam.save_config("cam.yaml")
```

The saved YAML can be loaded again by passing the path back to the component:

```python
cam = Camera("cam.yaml")
```

## What's in the box

- `ConfigurableBasis`, `InitConfigMixin`, `InitConfigABCMixin` — base classes for the
  single-`config` construction protocol.
- `InitConfigMeta` / `InitConfigABCMeta` — the metaclass that assembles configs.
- `NoConfig` — placeholder for components that need no settings.
- `StrEnum`, `ReprEnum` — a string-enum backport (use this `StrEnum`, not `enum.StrEnum`,
  for consistent behavior across Python 3.9–3.13).
- `ForceSetAttr` / `force_set_attr` — controlled mutation of otherwise-frozen configs.
- `import_string`, `get_fully_qualified_class_name`, `dump_or_repr`, `fetch_config`.
- `cfgable.hydra_utils` — `init_hydra_config`, `hydra_instance`,
  `hydra_instance_from_dict`, `hydra_instance_from_config_path` (needs `[hydra]`).

`import cfgable` never imports Hydra — the bridge is loaded only when you import
`cfgable.hydra_utils`.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup and conventions, and please follow the
[Code of Conduct](CODE_OF_CONDUCT.md). To report a security issue, see
[SECURITY.md](SECURITY.md). Release notes are tracked in
[CHANGELOG.md](CHANGELOG.md), and support options are listed in [SUPPORT.md](SUPPORT.md).

## License

Released under the [MIT License](LICENSE).
