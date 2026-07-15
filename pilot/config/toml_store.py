from __future__ import annotations

from pathlib import Path

from pilot._internal.bench_toml import dumps_config, load_config
from pilot._internal.toml_codec import dumps_toml, load_toml
from pilot.config.bench_config import BenchConfig
from pilot.secure_files import write_private_text


class BenchTomlStore:
    """Single entry point for reading and writing a bench's ``bench.toml``.

    Wraps internal parsing and serialization so every caller funnels through
    one object instead of touching the file directly.
    """

    FILENAME = "bench.toml"

    def __init__(self, path: Path) -> None:
        # Accept either the bench directory or the bench.toml file itself.
        self.path = path / self.FILENAME if path.is_dir() else path

    @classmethod
    def for_bench(cls, bench_root: Path) -> "BenchTomlStore":
        return cls(Path(bench_root) / cls.FILENAME)

    def exists(self) -> bool:
        return self.path.exists()

    def read(self, validate: bool = True) -> BenchConfig:
        """Typed config. ``validate=False`` parses a half-configured file."""
        return load_config(self.path, validate=validate)

    def read_raw(self) -> dict:
        """Parsed TOML as a plain dict, preserving every section as written."""
        return load_toml(self.path)

    def read_flat(self) -> dict:
        """Wizard's flat-key settings dict (parse-only)."""
        from pilot.config.bench_toml_builder import BenchTomlBuilder

        return BenchTomlBuilder.read_settings(self.path)

    def write(self, config: BenchConfig) -> None:
        write_private_text(self.path, dumps_config(config))

    def write_flat(self, name: str, settings: dict, port_offset: int = 0) -> None:
        """Serialise the wizard's flat-key settings dict to bench.toml.

        production.enabled has no flat key (it's flipped only by `bench setup
        production`, never by editing config) so BenchTomlBuilder always builds
        it as the dataclass default (False). Preserve whatever's already on
        disk, or a wizard/settings save on an already-production bench would
        silently demote it back to "development"."""
        from pilot.config.bench_toml_builder import BenchTomlBuilder

        config = BenchTomlBuilder(name, settings, port_offset=port_offset).build()
        if self.path.exists():
            config.production.enabled = self.read_raw().get("production", {}).get("enabled", False)
        self.write(config)

    def write_raw(self, data: dict) -> None:
        write_private_text(self.path, dumps_toml(data))
