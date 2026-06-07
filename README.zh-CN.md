# cfgable

[English](README.md) | 简体中文

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built on pydantic](https://img.shields.io/badge/built%20on-pydantic-e92063.svg)](https://docs.pydantic.dev/)

cfgable 是一个基于 [pydantic](https://docs.pydantic.dev/) 的轻量、可复用 Python
配置框架。它让每个组件都声明一个**单一的 `config` 对象**，并且可以用统一方式构造：
从 Python 代码、YAML 文件，或 Hydra 构造。验证只在边界处执行一次。

核心包只依赖 pydantic；Hydra 桥接是可选功能。

## 要求

- Python 3.9 或更新版本
- pydantic 2.x
- Hydra 支持需要安装可选的 `hydra` extra

## 安装

```bash
pip install "cfgable @ git+https://github.com/OpenGHz/cfgable.git"
pip install "cfgable[hydra] @ git+https://github.com/OpenGHz/cfgable.git"
```

如果从本地 checkout 安装，核心包使用 `pip install .`，可选 Hydra 桥接使用
`pip install ".[hydra]"`。

## 核心思路

1. 组件的设置由 pydantic model（`*Config`）表达，并用属性 docstring 编写文档。
2. 每个类只接收**一个** `config` 参数，并从中读取字段。
3. 继承 `ConfigurableBasis` 后，同一个类可以从显式 config、普通 mapping，或
   **扁平关键字参数**构造。扁平关键字参数正是 Hydra 的 `instantiate` 传入的形状。
   `InitConfigMeta` 元类会为你组装并验证 config，然后调用 `config_post_init()`。

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

当组件需要 configure 生命周期时，使用 `ConfigurableBasis`。如果普通对象只需要 config
组装能力，则继承 `InitConfigMixin`。

## 配合 Hydra 使用

将 `_target_` 指向类，并把 config 字段作为同级字段列出；元类会把这些字段转换成
`config` model：

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

对于普通类，也可以把 config 嵌套在自己的 `_target_` 下，这样标准的
`hydra.utils.instantiate` 会构造 `Camera(config=CameraConfig(...))`。

## 往返序列化

因为组件保留完整的 `config`，所以它可以序列化回能够重建自己的配置：

```python
cam.dump()                 # -> dict of fields + a "_target_" pointing at the class
cam.save_config("cam.yaml")
```

保存后的 YAML 可以通过把路径再次传给组件来加载：

```python
cam = Camera("cam.yaml")
```

## 包含内容

- `ConfigurableBasis`, `InitConfigMixin`, `InitConfigABCMixin` — 单一 `config`
  构造协议的基类。
- `InitConfigMeta` / `InitConfigABCMeta` — 负责组装 config 的元类。
- `NoConfig` — 适用于不需要设置的组件的占位 config。
- `StrEnum`, `ReprEnum` — string-enum backport（请使用这里的 `StrEnum`，而不是
  `enum.StrEnum`，以便在 Python 3.9–3.13 间保持一致行为）。
- `ForceSetAttr` / `force_set_attr` — 对原本 frozen 的 config 进行受控修改。
- `import_string`, `get_fully_qualified_class_name`, `dump_or_repr`, `fetch_config`。
- `cfgable.hydra_utils` — `init_hydra_config`, `hydra_instance`,
  `hydra_instance_from_dict`, `hydra_instance_from_config_path`（需要 `[hydra]`）。

`import cfgable` 永远不会导入 Hydra；只有在导入 `cfgable.hydra_utils` 时才会加载桥接模块。

## 开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## 贡献

欢迎提交 issue 和 pull request。开发环境与约定请见
[CONTRIBUTING.md](CONTRIBUTING.md)，并请遵守
[Code of Conduct](CODE_OF_CONDUCT.md)。报告安全问题请参阅
[SECURITY.md](SECURITY.md)。发布记录维护在 [CHANGELOG.md](CHANGELOG.md)，支持渠道见
[SUPPORT.md](SUPPORT.md)。

## 许可证

本项目基于 [MIT License](LICENSE) 发布。
