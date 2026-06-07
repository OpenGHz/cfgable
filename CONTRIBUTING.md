# Contributing to cfgable

Thanks for your interest in improving cfgable! Bug reports, feature ideas, and pull
requests are all welcome.

## Development setup

cfgable uses a `src/` layout and [Hatchling](https://hatch.pypa.io/) as its build
backend. An editable install with the `dev` extra pulls in the test dependencies
(including the optional Hydra bridge):

```bash
git clone https://github.com/OpenGHz/cfgable.git
cd cfgable
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the tests

```bash
pytest
```

The test suite lives in [`tests/`](tests/) and exercises the core protocol, enums,
frozen-config helpers, reflection utilities, and the Hydra bridge.

## Conventions

- **Single `config` parameter.** Every configurable class takes exactly one `config`
  argument. New features should preserve this protocol.
- **Keep the core pydantic-only.** `import cfgable` must never import Hydra or
  OmegaConf. Anything that depends on them belongs in `cfgable.hydra_utils`.
- **Configs are pydantic models** with attribute docstrings
  (`ConfigDict(use_attribute_docstrings=True)`), typically frozen and `extra="forbid"`.
- **Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/)
  (e.g. `feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
- Add or update tests for any behavioral change.

## Pull request process

1. Fork the repository and create a topic branch from `main`.
2. Make your change with accompanying tests.
3. Ensure `pytest` passes locally.
4. Open a pull request describing the motivation and the change; link any related issue.

By contributing, you agree that your contributions will be licensed under the project's
[MIT License](LICENSE).
