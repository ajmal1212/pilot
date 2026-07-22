from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from pilot.exceptions import BenchError

_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
ALLOWED_REPO_SCHEMES = ("https",)


class PluginValidationError(BenchError):
    """A plugin name, repository URL, or install path failed validation."""


def validate_plugin_name(name: str) -> str:
    """Reject anything but a short alphanumeric identifier.

    This is the primary defense against path traversal: every filesystem
    path built from a plugin name must start from a name that already
    passed this check.
    """
    if not _NAME_PATTERN.fullmatch(name):
        raise PluginValidationError(
            "Plugin name must be 1-64 characters of letters, digits, '-' or '_', "
            "and must start with a letter or digit."
        )
    return name


def validate_repo_url(repo: str) -> str:
    """Require a plain https URL with no embedded credentials.

    Blocking file:// and local paths stops a caller from cloning arbitrary
    server-local files into a plugin directory that then gets imported and
    can serve its contents back over HTTP.
    """
    parsed = urlsplit(repo)
    if parsed.scheme not in ALLOWED_REPO_SCHEMES:
        raise PluginValidationError("Plugin repository must be an https:// URL.")
    if parsed.username or parsed.password:
        raise PluginValidationError("Plugin repository URL must not contain embedded credentials.")
    if not parsed.hostname:
        raise PluginValidationError("Plugin repository URL is missing a host.")
    return repo


def confine_to_root(root: Path, name: str) -> Path:
    """Resolve `root / name` and assert it did not escape `root`.

    Defense in depth alongside `validate_plugin_name`: even if a future
    caller forgets to validate the name first, a path outside `root` is
    refused rather than deleted, cloned into, or imported.
    """
    root = root.resolve()
    candidate = (root / name).resolve()
    if candidate != root and root not in candidate.parents:
        raise PluginValidationError("Plugin path escapes the plugins directory.")
    return candidate
