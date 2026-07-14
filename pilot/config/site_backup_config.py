"""Per-site backup retention, stored in the site's site_config.json under
``backup_retention``. Present only while automated backups are enabled; when
absent, nothing is pruned (every backup is kept)."""

import json
from dataclasses import asdict
from pathlib import Path

from pilot.config.backup_config import BackupConfig

_KEY = "backup_retention"
_FIELDS = set(BackupConfig().__dict__)


def read_retention(site_config_path: Path) -> BackupConfig | None:
    block = _load(site_config_path).get(_KEY)
    if not isinstance(block, dict):
        return None
    return BackupConfig(**{k: v for k, v in block.items() if k in _FIELDS})


def write_retention(site_config_path: Path, config: BackupConfig) -> None:
    data = _load(site_config_path)
    data[_KEY] = asdict(config)
    site_config_path.write_text(json.dumps(data, indent=1))


def clear_retention(site_config_path: Path) -> None:
    data = _load(site_config_path)
    if data.pop(_KEY, None) is not None:
        site_config_path.write_text(json.dumps(data, indent=1))


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
