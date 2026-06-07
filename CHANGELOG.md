# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 0.1.0 - 2026-06-07

Initial public baseline.

- `ConfigurableBasis`, `InitConfigMixin`, `InitConfigABCMixin`, and
  `InitConfigMixinBasis` — base classes for the single-`config` construction protocol.
- `InitConfigMeta` / `InitConfigABCMeta` — metaclasses that assemble and validate a
  component's `config` from an explicit object, a mapping, or flat keyword arguments.
- `NoConfig` placeholder for components that need no settings.
- `StrEnum` / `ReprEnum` string-enum backport for consistent behavior across
  Python 3.9–3.13.
- `ForceSetAttr` / `force_set_attr` / `validate_field` / `force_validate_field` for
  controlled mutation and validation of frozen configs.
- Reflection helpers: `import_string`, `get_fully_qualified_class_name`,
  `get_full_class_name`, plus `dump_or_repr`, `dump_omegaconf`, and `fetch_config`.
- Optional `cfgable.hydra_utils` bridge: `init_hydra_config`, `hydra_instance`,
  `hydra_instance_from_dict`, `hydra_instance_from_config_path` (requires the
  `hydra` extra). The core never imports Hydra.
