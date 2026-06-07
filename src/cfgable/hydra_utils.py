"""Optional Hydra bridge. Requires the ``[hydra]`` extra (hydra-core + omegaconf).

Importing this module pulls in hydra/omegaconf, so it is deliberately NOT imported
by ``cfgable/__init__.py`` — import it explicitly:
``from cfgable.hydra_utils import init_hydra_config``.
"""

import hydra
import os.path as osp
from omegaconf import DictConfig
from typing import List, Optional
from pathlib import Path


def relative_path_between(path1: Path, path2: Path) -> Path:
    """Returns path1 relative to path2."""
    path1 = Path(path1).absolute()
    path2 = Path(path2).absolute()
    try:
        return path1.relative_to(path2)
    except ValueError:  # most likely because path1 is not a subpath of path2
        common_parts = Path(osp.commonpath([path1, path2])).parts
        return Path(
            "/".join(
                [".."] * (len(path2.parts) - len(common_parts))
                + list(path1.parts[len(common_parts) :])
            )
        )


def init_hydra_config(
    config_path: str, overrides: Optional[List[str]] = None
) -> DictConfig:
    """Initialize a Hydra config given only the path to the relevant config file.

    For config resolution, it is assumed that the config file's parent is the Hydra config dir.
    """
    # TODO(alexander-soare): Resolve configs without Hydra initialization.
    hydra.core.global_hydra.GlobalHydra.instance().clear()
    # Hydra needs a path relative to this file.
    hydra.initialize(
        str(
            relative_path_between(
                Path(config_path).absolute().parent, Path(__file__).absolute().parent
            )
        ),
        version_base="1.2",
    )
    cfg = hydra.compose(Path(config_path).stem, overrides)
    return cfg


def hydra_instance(cfg: DictConfig):
    return hydra.utils.instantiate(cfg)


def hydra_instance_from_config_path(config_path: str, params: dict = None):
    config = init_hydra_config(config_path)
    if params:
        config.update(params)
    return hydra_instance(config)


def hydra_instance_from_dict(config: dict):
    return hydra_instance(DictConfig(config))
