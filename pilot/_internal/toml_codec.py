from __future__ import annotations

import io
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

ConfigT = TypeVar("ConfigT")
ConfigDict = dict[str, Any]


def load_toml(path: Path) -> ConfigDict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def loads_toml(value: str) -> ConfigDict:
    return tomllib.loads(value)


def dumps_toml(data: Mapping[str, Any]) -> str:
    """Serialize the TOML value shapes used by Pilot configuration files."""
    output = io.StringIO()

    def write_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, list):
            return "[" + ", ".join(write_value(item) for item in value) + "]"
        return str(value)

    def write_section(obj: Mapping[str, Any], prefix: str = "") -> None:
        scalars = {
            key: value
            for key, value in obj.items()
            if not isinstance(value, (dict, list))
            or (isinstance(value, list) and not any(isinstance(item, dict) for item in value))
        }
        tables = {key: value for key, value in obj.items() if isinstance(value, dict)}
        arrays = {
            key: value
            for key, value in obj.items()
            if isinstance(value, list) and any(isinstance(item, dict) for item in value)
        }

        for key, value in scalars.items():
            output.write(f"{key} = {write_value(value)}\n")

        for key, value in tables.items():
            output.write(f"\n[{prefix}{key}]\n")
            write_section(value, prefix=f"{prefix}{key}.")

        for key, entries in arrays.items():
            for entry in entries:
                output.write(f"\n[[{prefix}{key}]]\n")
                write_section(entry, prefix=f"{prefix}{key}.")

    write_section(data)
    return output.getvalue()


@dataclass(frozen=True)
class TomlDataclassCodec(Generic[ConfigT]):
    """Convert one dataclass schema through a plain-dict TOML boundary.

    Schema-specific aliases, defaults, and migrations belong in the supplied
    callbacks. The generic codec owns only the conversion pipeline.
    """

    from_config_dict: Callable[[ConfigDict], ConfigT]
    to_config_dict: Callable[[ConfigT], ConfigDict]

    def from_dict(self, data: ConfigDict) -> ConfigT:
        return self.from_config_dict(data)

    def to_dict(self, config: ConfigT) -> ConfigDict:
        return self.to_config_dict(config)

    def loads(self, value: str) -> ConfigT:
        return self.from_dict(loads_toml(value))

    def load(self, path: Path) -> ConfigT:
        return self.from_dict(load_toml(path))

    def dumps(self, config: ConfigT) -> str:
        return dumps_toml(self.to_dict(config))
