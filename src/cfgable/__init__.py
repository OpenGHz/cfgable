"""cfgable: a reusable pydantic/dataclass-driven configuration framework.

Components declare a single ``config`` parameter and (optionally) inherit
``ConfigurableBasis``; the ``InitConfigMeta`` metaclass assembles that config from
explicit objects, plain mappings, or flat keyword arguments (the shape Hydra's
``instantiate`` passes), validating it once at construction.

The core exported here depends only on pydantic. The optional Hydra bridge lives
in ``cfgable.hydra_utils`` and is imported on demand, so ``import cfgable``
never pulls in hydra/omegaconf.

NOTE: do NOT add ``from .hydra_utils import ...`` to this module — it would make
hydra a hard dependency of the core. Import it explicitly where you need it.
"""

from ._typing import (
    AllConfigType,
    BaseModelT,
    ConfigType,
    DataClassProto,
    OtherCfgType,
    T,
)
from .core import (
    ConfigurableBasis,
    InitConfigABCMeta,
    InitConfigABCMixin,
    InitConfigMeta,
    InitConfigMixin,
    InitConfigMixinBasis,
    NoConfig,
    dump_omegaconf,
    dump_or_repr,
    fetch_config,
)
from .enums import ReprEnum, StrEnum
from .frozen import ForceSetAttr, force_set_attr, force_validate_field, validate_field
from .reflection import (
    get_full_class_name,
    get_fully_qualified_class_name,
    import_string,
)

__all__ = [
    # typing
    "ConfigType",
    "AllConfigType",
    "OtherCfgType",
    "DataClassProto",
    "BaseModelT",
    "T",
    # core
    "NoConfig",
    "InitConfigMeta",
    "InitConfigABCMeta",
    "InitConfigMixinBasis",
    "InitConfigMixin",
    "InitConfigABCMixin",
    "ConfigurableBasis",
    "dump_or_repr",
    "dump_omegaconf",
    "fetch_config",
    # enums
    "StrEnum",
    "ReprEnum",
    # frozen
    "ForceSetAttr",
    "force_set_attr",
    "validate_field",
    "force_validate_field",
    # reflection
    "import_string",
    "get_fully_qualified_class_name",
    "get_full_class_name",
]
