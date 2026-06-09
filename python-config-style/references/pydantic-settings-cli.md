# pydantic-settings for small-script CLIs

When the job is a single script run with a handful of options — not an application assembled
from parts — the command-line interface *is* a pydantic config model, parsed by
`pydantic_settings.CliApp`. No `argparse`, no Hydra. Attribute docstrings become the `--help`
text; the script's worker takes the validated config as its one argument.

Reach for this (not Hydra) when: there's one entry point, options are a flat-ish set of
flags, and you're running a tool rather than composing a system. Reach for Hydra instead when
you're selecting/combining components or running sweeps — see
[hydra-app-config.md](hydra-app-config.md).

## Table of contents

- [The shape](#the-shape)
- [Help text and flag names](#help-text-and-flag-names)
- [The parse / main scaffold](#the-parse--main-scaffold)
- [Custom argument normalization](#custom-argument-normalization)

## The shape

```python
#!/usr/bin/env python3
import logging
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, model_validator
from pydantic_settings import CliApp
from typing_extensions import Self

logger = logging.getLogger(__name__)

FileType = Literal["symlink", "hardlink", "copy", "move"]


class ReorganizeDataByEpisodeConfig(BaseModel):
    model_config = {"use_attribute_docstrings": True}

    source_root: Path = Path("data/aao_data")
    """Source root in the format <task>/<episode>."""

    output_root: Path = Path("data/aao_data_by_episode")
    """Output root in the format <episode>/<task>; created as needed."""

    dry_run: bool = False
    """Log planned operations without writing anything."""

    file_type: FileType = "symlink"
    """How to materialize episodes: symlink (default), hardlink, copy, or move."""

    episode: Optional[List[str]] = None
    """Reorganize a single episode; pass one value, or two to rename it."""

    @model_validator(mode="after")
    def validate_episode(self) -> Self:
        if self.episode is not None and len(self.episode) not in (1, 2):
            raise ValueError("--episode accepts one or two values only.")
        return self


def reorganize_data_by_episode(config: ReorganizeDataByEpisodeConfig) -> None:
    """The worker — takes the one validated config and does the job."""
    source_root = config.source_root.expanduser().resolve()
    ...
```

Same config conventions as everywhere else (see [pydantic-config.md](pydantic-config.md)):
attribute docstrings, `use_attribute_docstrings=True`, constrained types, `model_validator`
returning `Self`. The CLI config is frequently left un-`frozen` (it's built once, at the
boundary), which is fine — freeze it if you prefer.

## Help text and flag names

- With `use_attribute_docstrings=True`, each field's docstring is its `--help` description.
  Don't duplicate it into `Field(description=...)`.
- Field `source_root` maps to `--source_root`. To also accept the kebab form `--source-root`,
  give CLI configs the kebab alias — either per field with `validation_alias`, or by
  subclassing the `BaseModelWithFieldAliases` base shown in
  [pydantic-config.md](pydantic-config.md#kebab-case-aliases-for-the-cli), which adds the
  kebab alias to every field automatically.
- `bool` fields become `--dry-run` / `--no-dry-run` style flags; `Literal[...]` becomes a
  constrained choice; `List[str]` accepts repeated/space-separated values.

## The parse / main scaffold

Keep a thin, testable seam: a `parse_config` that returns the model, a `main(cli_args=None)`
that parses then runs, and the `__main__` guard. Passing `cli_args=None` lets `CliApp` read
`sys.argv`; passing a list makes `main` unit-testable.

```python
def parse_config(cli_args: Optional[List[str]] = None) -> ReorganizeDataByEpisodeConfig:
    """Parse argv (or a provided list) into a validated config."""
    return CliApp.run(ReorganizeDataByEpisodeConfig, cli_args=cli_args)


def main(cli_args: Optional[List[str]] = None) -> None:
    config = parse_config(cli_args)
    reorganize_data_by_episode(config)


if __name__ == "__main__":
    init_logging()                  # set up logging at the entry point
    try:
        main()
    except ValueError as exc:       # surface validation errors as clean exits
        raise SystemExit(str(exc))
```

Why this layout: `parse_config` isolates CLI parsing so tests can build a config from a list
of args (or directly as a model) without a subprocess; `main(cli_args=None)` is the single
entry both `__main__` and tests call; catching `ValueError` turns validation failures into a
tidy non-zero exit instead of a traceback.

## Custom argument normalization

`CliApp` expects list-valued options in a particular form. When you want a friendlier surface
syntax (e.g. `--episode 5 eval_005` for a one-or-two-value option), normalize argv *before*
handing it to `CliApp`, keeping the model clean:

```python
def normalize_cli_args(cli_args: Optional[List[str]] = None) -> List[str]:
    """Rewrite friendly multi-value flags into the JSON list form CliApp expects."""
    raw = list(sys.argv[1:] if cli_args is None else cli_args)
    out: List[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == "--episode":
            vals, i = [], i + 1
            while i < len(raw) and not raw[i].startswith("-"):
                vals.append(raw[i]); i += 1
            out += ["--episode", json.dumps(vals)]
            continue
        out.append(raw[i]); i += 1
    return out


def parse_config(cli_args: Optional[List[str]] = None) -> ReorganizeDataByEpisodeConfig:
    return CliApp.run(ReorganizeDataByEpisodeConfig, cli_args=normalize_cli_args(cli_args))
```

Do this only when the default surface syntax is awkward; most scripts need just the plain
`CliApp.run(Config)` from the scaffold above.
