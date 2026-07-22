from __future__ import annotations

from pathlib import Path

import pytest

from pilot.plugins.security import (
    PluginValidationError,
    confine_to_root,
    validate_plugin_name,
    validate_repo_url,
)


@pytest.mark.parametrize("name", ["cloudflare", "my-plugin", "my_plugin_2", "a", "A1"])
def test_validate_plugin_name_accepts_simple_identifiers(name: str) -> None:
    assert validate_plugin_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "..",
        "../evil",
        "a/b",
        "a\\b",
        "-leading-dash",
        "_leading-underscore",
        ".hidden",
        "has space",
        "a" * 65,
    ],
)
def test_validate_plugin_name_rejects_unsafe_input(name: str) -> None:
    with pytest.raises(PluginValidationError):
        validate_plugin_name(name)


def test_validate_repo_url_accepts_plain_https() -> None:
    assert validate_repo_url("https://github.com/frappe/example-plugin") == "https://github.com/frappe/example-plugin"


@pytest.mark.parametrize(
    "repo",
    [
        "http://github.com/frappe/example-plugin",
        "git@github.com:frappe/example-plugin.git",
        "ssh://git@github.com/frappe/example-plugin.git",
        "file:///etc/passwd",
        "file:///home/user/.ssh/",
        "https://user:token@github.com/frappe/example-plugin",
        "not-a-url",
    ],
)
def test_validate_repo_url_rejects_unsafe_schemes_and_credentials(repo: str) -> None:
    with pytest.raises(PluginValidationError):
        validate_repo_url(repo)


def test_confine_to_root_allows_direct_children(tmp_path: Path) -> None:
    root = tmp_path / "plugins-data"
    root.mkdir()

    assert confine_to_root(root, "cloudflare") == (root / "cloudflare").resolve()


@pytest.mark.parametrize("escape", ["../outside", "../../etc", "a/../../outside"])
def test_confine_to_root_rejects_traversal(tmp_path: Path, escape: str) -> None:
    root = tmp_path / "plugins-data"
    root.mkdir()

    with pytest.raises(PluginValidationError):
        confine_to_root(root, escape)
