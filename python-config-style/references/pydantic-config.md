# Pydantic config classes — full reference

The conventions for writing configuration models. Read this when you need more than the
canonical shape in SKILL.md — enums, aliases, composition, the placeholder config, and the
trade-offs behind each `model_config` flag.

## Table of contents

- [The base shape](#the-base-shape)
- [model_config flags and when to use them](#model_config-flags-and-when-to-use-them)
- [Field documentation: attribute docstrings](#field-documentation-attribute-docstrings)
- [Constrained types over manual validators](#constrained-types-over-manual-validators)
- [Validators](#validators)
- [Composition and nesting](#composition-and-nesting)
- [Enums](#enums)
- [Kebab-case aliases for the CLI](#kebab-case-aliases-for-the-cli)
- [Naming: Config / ConfigBasis / Args](#naming)
- [The NoConfig placeholder](#the-noconfig-placeholder)

## The base shape

```python
from typing import List

from pydantic import BaseModel, ConfigDict


class KeyFilterConfig(BaseModel, frozen=True):
    """The dict key filter config."""

    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")

    include: List[str] = []
    """The list of keys to include."""

    exclude: List[str] = []
    """The list of keys to exclude."""
```

`frozen=True` goes in the class signature (`class X(BaseModel, frozen=True)`), not in
`model_config` — both work, but the signature form is the house style and reads as "this
class is immutable" right at the declaration.

## model_config flags and when to use them

Set these consciously; each encodes a decision.

- **`use_attribute_docstrings=True`** — almost always. Makes the triple-quoted string under
  each field its `description`, so docs live in exactly one place and flow into `--help` and
  JSON schema.

- **`extra="forbid"`** — default to this for configs that are written by hand (YAML, CLI,
  literal kwargs). An unknown key is almost always a typo or a stale field name; forbidding
  it turns a silent no-op into a loud error. Relax to the pydantic default (`"ignore"`) only
  when a config legitimately receives extra keys it should tolerate.

- **`arbitrary_types_allowed=True`** — when a field holds a *live object* (a camera handle,
  another instantiated component, a numpy array) rather than plain serializable data. This
  is common in this codebase because configs sometimes carry already-built interfaces:

  ```python
  class ConcurrentWrapperConfig(BaseModel):
      """The config for the concurrent wrapper."""

      model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

      interface: InterfaceType
      """The interface instance to be wrapped."""
      concurrent: ConcurrentMode = ConcurrentMode.process
      """The concurrent mode."""
  ```

  A config that carries instances usually should **not** be `frozen` if those instances are
  swapped after construction, and usually isn't serialized to YAML.

## Field documentation: attribute docstrings

The doc for a field is the string literal *immediately below* it. Multi-line is fine:

```python
update_rate: NonNegativeFloat = 0
"""The maximum update rate for the managers.
0 means as fast as possible."""
```

With `use_attribute_docstrings=True`, pydantic uses this as the field `description`. **Do not
also pass `description=` to `Field()`** — that duplicates the text and the two drift apart.
If you find existing code with both (a docstring *and* `Field(description=...)`), collapse to
the docstring when you touch it.

## Constrained types over manual validators

Prefer a constrained type when one expresses the rule:

```python
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

update_rate: NonNegativeFloat = 0      # not: float + a validator that checks >= 0
batch_size: NonNegativeInt = 0
chunk_count: PositiveInt = 1
```

Reserve validators for rules no type captures (cross-field constraints, normalization,
conditional requirements).

## Validators

Run validators `mode="after"` so they see parsed, typed values. Return the value (field
validator) or `self` (model validator, annotated `-> Self`).

```python
from typing import Dict
from typing_extensions import Self
from pydantic import model_validator, field_validator


class ManagerConfigBasis(BaseModel, frozen=True):
    """Configuration for the manager."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    key_to_action: KeyToAction = Field(min_length=1)
    """Mapping from action names to manager interface (key/button) names."""

    instruction: Dict[str, str] = {}
    """Instruction strings per interface name; missing ones are auto-filled."""

    @model_validator(mode="after")
    def fill_missing_instructions(self) -> Self:
        for key, action in default_actions().items():
            self.instruction.setdefault(key, action)
        return self
```

Note `Field(min_length=1)` carries a *constraint* and no `description=` — the docstring
still owns the documentation.

A `@field_validator` that just prunes a value:

```python
@field_validator("managers", mode="after")
def drop_empty(cls, v: dict):
    return {name: m for name, m in v.items() if m is not None}
```

## Composition and nesting

Configs reference other configs by type, forming a tree that mirrors the object tree:

```python
from typing import Dict, Optional


class DataCollectionConfig(BaseModel, frozen=True):
    """Configuration for the data collection."""

    model_config = ConfigDict(use_attribute_docstrings=True, arbitrary_types_allowed=True)

    fsm: DemonstrateFSMConfig
    """The finite state machine config."""
    managers: Dict[str, Optional[ManagerConfigBasis]] = {}
    """Managers that drive the demonstration actions."""
```

This nesting is exactly what Hydra composes from separate YAML files and what `instantiate`
walks to build the live objects. Mutable defaults (`{}`, `[]`) are safe — pydantic copies
them per instance.

A CLI-facing top-level config can be assembled by **multiple inheritance** when its shape is
"almost the same but flatter" than the runtime config:

```python
class DataCollectionArgs(DemonstrateConfig, DataCollectionConfig):
    """Top-level arguments for data collection — similar to DataCollectionConfig
    but shaped for the CLI."""

    fsm: StateMachineConfig          # overrides the field with a CLI-friendlier type
    """The finite state machine config."""
    job_id: Optional[int] = None
    """Job id; a random one is generated when omitted."""
```

## Enums

Use `StrEnum` with `auto()` members, each with an attribute docstring. String enums
serialize cleanly to/from YAML and the CLI:

```python
from enum import auto
from cfgable import StrEnum   # consistent StrEnum across Python versions


class ConcurrentMode(StrEnum):
    """Concurrent mode."""

    thread = auto()
    process = auto()
    asynchronous = auto()
    none = auto()
```

## Kebab-case aliases for the CLI

By default a field `source_root` becomes `--source_root`. To also accept `--source-root`,
add a validation alias. This codebase centralizes that in a base class that adds the
kebab form to every field automatically:

```python
from pydantic import BaseModel, AliasChoices


class BaseModelWithFieldAliases(BaseModel):
    """Adds the kebab-case form of each field name as an accepted alias,
    on top of any existing validation_alias."""

    def __init_subclass__(cls, **kwargs):
        for name, field in cls.model_fields.items():
            kebab = name.replace("_", "-")
            alias = field.validation_alias
            choices = list(alias.choices) if isinstance(alias, AliasChoices) else ([alias] if alias else [])
            if kebab not in choices:
                field.validation_alias = AliasChoices(*choices, kebab)
        super().__init_subclass__(**kwargs)
```

Subclass it for CLI configs that want both `--source_root` and `--source-root` to work.

## Naming

- `XxxConfig` — a concrete config. Default suffix.
- `XxxConfigBasis` — an abstract base config meant to be subclassed.
- `XxxArgs` — a top-level entry/CLI config (often a flattened composition of runtime
  configs).

## The NoConfig placeholder

A component that genuinely needs no settings still participates in the single-`config`
protocol by declaring a placeholder, so the construction machinery (metaclass, Hydra) has a
config type to resolve:

```python
class NoConfig(BaseModel, frozen=True):
    """A placeholder config indicating no configuration is needed."""
```

Annotate `config: NoConfig` (or set the class-scope config type to `None` per the framework
in [references/hydra-app-config.md](references/hydra-app-config.md)) rather than dropping the
`config` parameter.
