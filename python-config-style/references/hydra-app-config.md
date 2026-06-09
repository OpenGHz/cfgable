# Hydra for whole-application config

Use Hydra to assemble an application out of interchangeable components, and for experiment /
sweep configs. Each component is selected and configured by a YAML file; `instantiate` turns
the resolved config tree into live objects. This pairs with the single-`config` `__init__`
convention via a small bridge described below.

## Table of contents

- [Directory layout](#directory-layout)
- [YAML shape: _target_ + fields](#yaml-shape)
- [The bridge: how flat YAML becomes one config object](#the-bridge)
- [Plain projects without the bridge](#plain-projects-without-the-bridge)
- [Loading and instantiating](#loading-and-instantiating)
- [Interpolation, packages, defaults](#interpolation-packages-defaults)
- [Round-tripping: dump and save_config](#round-tripping)

## Directory layout

Group config files by component type — one directory per kind, one file per selectable
variant:

```
configs/
├── defaults/
│   └── config_infer.yaml      # top-level entry config (composes the rest)
├── robots/
│   ├── airbot_play.yaml
│   └── airbot_mmk.yaml
├── samplers/
│   ├── ros.yaml
│   └── video.yaml
├── managers/
│   ├── tk.yaml
│   └── joy.yaml
└── sensors/ …
```

A file under `robots/` is a complete, ready-to-instantiate robot; switching robots means
switching which file is selected, not editing fields.

## YAML shape

Each node carries `_target_` (the dotted path to the class) and the config fields as
**siblings** of it:

```yaml
# configs/samplers/ros_struct.yaml
# @package _global_

sampler:
  _target_: airdc.common.samplers.mcap_samplers.sampler_ros_struct.McapDataSamplerROSStruct
  av_coder:
    frame_format: rgb24
  task_info:
    operator: auto_atom
    station: mujoco
    task_name: ${task_name}
  writer:
    chunk_size: 16777216
```

```yaml
# configs/robots/airbot_play.yaml
_target_: airbot_ie.robots.airbot_play.AIRBOTPlay
```

A bare `_target_` with no fields (above) builds the component with its config defaults.

## The bridge

Here is the subtlety that makes the flat YAML work with the single-`config` `__init__`.

The classes inherit a base (`ConfigurableBasis`, driven by the `InitConfigMeta` metaclass
from the `cfgable` package). When Hydra's `instantiate` calls `TheClass(av_coder=..., task_info=...)`
with the YAML fields as keyword arguments, the metaclass intercepts construction:

1. It resolves the class's **config type** from the annotation on `__init__`
   (`def __init__(self, config: McapDataSamplerROSStructConfig)`), or from a class-scope
   `config` annotation.
2. It assembles those keyword arguments into that pydantic model — `config = ConfigType(**fields)`
   — validating them in the process.
3. It calls the real `__init__(self, config)` with the assembled model, sets
   `self.config = config` if `__init__` didn't, then calls `config_post_init()`.

So you write the component the normal way — one `config` parameter — and the YAML stays flat
and readable. The metaclass is what reconciles "Hydra passes kwargs" with "we take one
config."

Consequences for how you write components in these projects:

- **Declare `def __init__(self, config: YourConfig)`** and (optionally) `self.config = config`.
  Annotate `config` so the metaclass can find the type.
- **Put derived state in `config_post_init()`**, not `__init__`. It runs after the config is
  set regardless of construction path (Python, YAML, CLI), so it's the reliable place to
  build caches, open handles, set flags:

  ```python
  class DemonstrateManagerBasis(ConfigurableBasis):
      """Demonstrate manager."""

      def __init__(self, config: ManagerConfigBasis):
          self.config = config

      @final
      def config_post_init(self):
          super().config_post_init()
          self.finalized = False
          self._locked = False
          self.fsms = []
  ```

- **A component needing no config** declares the placeholder type (`NoConfig`) or marks the
  class-scope `config` type as `None`, so the metaclass still has something to resolve.
- **`_target_` can point at a factory function** (not only a class) when construction needs
  logic — e.g. `fsm: {_target_: airbot_ie.configs.fsm.get_fsm_config}`.

## Plain projects without the bridge

If you are not in a `ConfigurableBasis` project, standard Hydra `instantiate` passes YAML
fields as kwargs to `__init__`, which collides with a single-`config` signature. Two ways to
keep the one-config convention:

1. **Nest the config under its own `_target_`** so `instantiate` builds the model first and
   passes it as `config=`:

   ```yaml
   _target_: my_pkg.sampler.Sampler
   config:
     _target_: my_pkg.sampler.SamplerConfig
     rate: 30
   ```

   With `Sampler.__init__(self, config: SamplerConfig)`, `instantiate` constructs
   `SamplerConfig(rate=30)` then `Sampler(config=that)`.

2. **Make the config the `_target_`** and instantiate it, then hand it to the class in code:

   ```python
   cfg = instantiate(yaml_cfg)          # builds SamplerConfig
   sampler = Sampler(cfg)
   ```

Prefer option 1 for fully-declarative trees.

## Loading and instantiating

This codebase wraps the Hydra calls in small helpers (`cfgable.hydra_utils`)
so callers don't repeat the initialize/compose dance:

```python
from cfgable.hydra_utils import (
    init_hydra_config,          # path -> composed DictConfig
    hydra_instance,             # DictConfig -> instantiated object
    hydra_instance_from_dict,   # dict -> instantiated object
    hydra_instance_from_config_path,  # path (+ overrides) -> instantiated object
)
from omegaconf import OmegaConf

cfg = init_hydra_config("defaults/config_infer.yaml")
cfg = OmegaConf.to_container(cfg, resolve=True, throw_on_missing=True)
demonstrator = hydra_instance_from_dict(cfg)
```

Under the hood these are thin wrappers over `hydra.initialize` / `hydra.compose` and
`hydra.utils.instantiate`. Use them rather than re-implementing config loading; add overrides
through `init_hydra_config(path, overrides=["task_name=open_door"])`.

## Interpolation, packages, defaults

- **`# @package _global_`** at the top of a file places its keys at the root of the composed
  config (instead of nested under the file's group), so a `samplers/ros.yaml` can contribute
  a top-level `sampler:` and `dataset:`.
- **`${var}`** interpolates another config value (`task_name: ${task_name}`); resolve with
  `OmegaConf.to_container(cfg, resolve=True)`.
- Use Hydra **defaults lists** in the top-level entry config to pick one variant per group.

## Round-tripping

Because every object stores its whole `config`, it can serialize back to the YAML that would
rebuild it. The base mixin provides:

- `obj.dump(mode="python"|"json")` → a dict of the config plus a `_target_` key pointing at
  the class.
- `obj.save_config(path)` → write that out (YAML/JSON), so a live, possibly-overridden object
  becomes a config file you can `instantiate` again.

This is the practical payoff of "store the whole config and never explode it into ad-hoc
attributes": construction is reversible.
