---
name: python-config-style
description: >-
  Write Python configuration, command-line, and class-initialization code in the user's
  house style: pydantic config classes (frozen, with attribute docstrings as the field
  docs), Hydra for whole-application config wiring via `_target_` + `instantiate`,
  pydantic-settings (`CliApp`) for small-script CLIs, and a single `config` parameter in
  every `__init__`. Use this whenever writing or refactoring Python that defines a
  configuration model, parses command-line arguments, structures a class or top-level
  function around its settings, or chooses between Hydra and pydantic-settings — even if
  the user never names the libraries. Triggers on: "add a config", "write a config class",
  "make a CLI for this script", "add command-line args", "pydantic config", "hydra
  config", "refactor this to take a config", "配置类", "加个配置", "写个命令行",
  "加命令行参数", "把它改成吃 config 的", and similar Python config / CLI / class-init work.
---

# Python Config Style

This is the user's house style for **configuration, command-line interfaces, and how
classes receive their settings** in Python. Apply it whenever you write or refactor code
that touches any of those — new config models, a script's CLI, a class constructor, or the
wiring that builds an application from parts.

It rests on four pillars:

1. **Config is plain, validated data** — every component's settings live in a pydantic
   model (`BaseModel`), documented with attribute docstrings.
2. **Whole-application wiring is declarative** — Hydra YAML with `_target_` selects and
   composes components; `instantiate` turns the tree into live objects.
3. **Small scripts get config from the command line** — pydantic-settings `CliApp` turns
   one config model into a validated CLI. No `argparse`, no Hydra ceremony.
4. **One config in, one config stored** — every `__init__` (and every top-level worker
   function) takes a single `config` parameter and reads fields off it.

## Why this shape

The point is **uniform construction**. A component never invents its own ad-hoc keyword
arguments; it declares one config type and reads from it. That makes every object
buildable the same way — from Python, from a YAML file, or from the command line — and
makes configs serializable and round-trippable (you can dump a live object back to the
YAML that would rebuild it). Validation happens once, at the boundary, so the rest of the
code trusts its `config`.

Keep this reasoning in mind rather than applying the rules mechanically: when a situation
isn't covered below, choose the option that preserves "settings are validated data that
flow in as one object."

## Which tool for which job

| You are… | Use | Details |
|---|---|---|
| Defining any component's settings | a pydantic config class | below |
| Building a class or a top-level worker function | a single `config` parameter | below |
| Wiring a whole app: selecting/composing many components, experiment configs, multirun | **Hydra** (`_target_` + `instantiate`) | [references/hydra-app-config.md](references/hydra-app-config.md) |
| A standalone script with a handful of options | **pydantic-settings** (`CliApp`) | [references/pydantic-settings-cli.md](references/pydantic-settings-cli.md) |

The Hydra-vs-pydantic-settings line is about **scope**: Hydra is for assembling an
application out of interchangeable parts (and for sweeps/experiments); pydantic-settings is
for a single script you run with a few flags. When unsure, ask "is the user composing a
system, or running one tool?"

## Pydantic config classes

The canonical shape — study it, then read the rules:

```python
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, NonNegativeFloat, NonNegativeInt, field_validator


class DataCollectionConfig(BaseModel, frozen=True):
    """Configuration for the data collection."""

    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")

    update_rate: NonNegativeFloat = 0
    """The maximum update rate for the managers; 0 means as fast as possible."""

    fsm: DemonstrateFSMConfig
    """The finite state machine config."""

    managers: Dict[str, Optional[ManagerConfigBasis]] = {}
    """Managers that drive the demonstration actions."""

    log_metrics: int = -1
    """Log metrics every N seconds; -1 disables it."""

    @field_validator("managers", mode="after")
    def drop_empty_managers(cls, v: dict):
        return {name: m for name, m in v.items() if m is not None}
```

**The rules, with the reasoning:**

- **Name it `<Thing>Config`.** Abstract bases end in `ConfigBasis`; a top-level
  CLI/entry config may end in `Args`. The suffix makes "this is data, not behavior"
  obvious at a glance.

- **Subclass `BaseModel` and default to `frozen=True`.** A config is a fact about how a
  component was built; freezing it prevents a component from mutating shared settings out
  from under whoever else holds them, and lets pydantic cache attribute access. Drop
  `frozen` only when something genuinely needs to rewrite its own config.

- **Document every field with an attribute docstring** — the triple-quoted string *below*
  the field — and turn on `use_attribute_docstrings=True` so pydantic adopts that text as
  the field's `description`. This is the single source of truth for field docs: it shows up
  in `--help` (pydantic-settings) and in any generated schema, with no duplication. Do not
  restate the same text in `Field(description=...)`.

- **Reach for `Field()` only for behavior, not for docs** — i.e. constraints
  (`Field(min_length=1)`), a non-trivial default, or aliases. If a field only needs a type,
  a default, and a docstring, don't wrap it in `Field()`.

- **Prefer pydantic's constrained types** (`NonNegativeFloat`, `NonNegativeInt`,
  `PositiveInt`, `NonNegativeInt`, …) over a bare `int`/`float` plus a hand-written
  validator. The type states the constraint declaratively and shows up in the schema.

- **Set `model_config` deliberately.** Common choices:
  - `use_attribute_docstrings=True` — adopt attribute docstrings as descriptions (use
    nearly always).
  - `extra="forbid"` — reject unknown keys, so a typo in YAML or on the CLI fails loudly
    instead of being silently ignored.
  - `arbitrary_types_allowed=True` — when a field holds a live instance (a device handle,
    another component) rather than plain data.

- **Validators run `mode="after"` and return `self` / the value.** Use `@field_validator`
  for one field, `@model_validator(mode="after")` for cross-field invariants; annotate the
  model validator's return as `Self`. Validate at the boundary so the rest of the code
  doesn't re-check.

- **Compose configs by nesting.** A field whose type is another `*Config` builds a tree;
  this is what lets Hydra assemble and `instantiate` rebuild the whole thing. Mutable
  defaults (`= {}`, `= []`) are safe here — pydantic deep-copies them per instance.

For the fuller catalog — enums with `StrEnum` + `auto()`, kebab-case aliases, the `NoConfig`
placeholder, `extra="forbid"` trade-offs, and more worked examples — read
[references/pydantic-config.md](references/pydantic-config.md).

## One config in, one config stored

Every class and every top-level worker function takes its settings as a **single `config`
argument** and reads fields off it. Don't explode a config into a long kwargs list, and
don't scatter `self.lr`, `self.batch_size`, … across the instance — keep `self.config` and
read `self.config.lr`.

```python
class DataSampler(DataSamplerBasis):
    def __init__(self, config: DataSamplerConfig):
        self.config = config
```

```python
def reorganize_data_by_episode(config: ReorganizeDataByEpisodeConfig) -> ExecutionSummary:
    source_root = config.source_root.expanduser().resolve()
    ...
```

**Why:** one parameter means one construction protocol. The same object can be built in
Python (`DataSampler(cfg)`), from YAML (Hydra `instantiate`), or from the CLI, because all
three just need to produce one `config`. Keeping the whole config on `self` (instead of
copying fields out) keeps the object honest about what it was configured with, which is
what makes `dump()`/round-tripping work.

**In Hydra-wired projects** (those built on `ConfigurableBasis` / the `InitConfigMeta`
metaclass from the `cfgable` package), the base class is the bridge: it lets Hydra pass the
YAML fields as flat kwargs and assembles them into your `config` model automatically before
`__init__` runs, then calls `config_post_init()`. So:
- declare `def __init__(self, config: YourConfig)` and set `self.config = config` (or rely
  on the base to set it),
- put **derived / post-construction state** in `config_post_init()`, not in `__init__`, so
  it runs no matter how the object was built.

See [references/hydra-app-config.md](references/hydra-app-config.md) for how the bridge
maps YAML → config, and what to do in plain projects that don't use it.

## Small-script CLIs

For a single script with a few options, the CLI *is* a pydantic config model, parsed by
`pydantic_settings.CliApp`. Attribute docstrings become `--help` text; the worker takes the
validated config:

```python
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel
from pydantic_settings import CliApp


class ReorganizeConfig(BaseModel):
    model_config = {"use_attribute_docstrings": True}

    source_root: Path = Path("data/aao_data")
    """Source root in the format <task>/<episode>."""

    dry_run: bool = False
    """Log planned operations without writing anything."""


def main(cli_args: Optional[List[str]] = None) -> None:
    config = CliApp.run(ReorganizeConfig, cli_args=cli_args)
    do_the_work(config)


if __name__ == "__main__":
    main()
```

Full pattern — kebab-case flag aliases, `parse_config`/`main(cli_args=None)` scaffolding,
custom argument normalization for multi-value flags — in
[references/pydantic-settings-cli.md](references/pydantic-settings-cli.md).

## Before you finish — quick checklist

- [ ] Settings live in a `*Config` `BaseModel`, `frozen=True` unless mutation is needed.
- [ ] Every field has an attribute docstring; `use_attribute_docstrings=True` is set; no
      duplicated `description=`.
- [ ] Constrained types used where they fit; validators are `mode="after"`.
- [ ] Each class / worker function takes a single `config` and stores it as `self.config`.
- [ ] Whole-app wiring went through Hydra (`_target_` + `instantiate`); a lone script got
      a `CliApp` CLI — not the other way around.
- [ ] Derived state in `config_post_init()` (in `ConfigurableBasis` projects), not
      `__init__`.
