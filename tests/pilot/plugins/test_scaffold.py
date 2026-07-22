from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pilot.plugins.scaffold import scaffold_plugin
from pilot.plugins.security import PluginValidationError


def _scaffold(tmp_path: Path, slug: str, label: str | None = None) -> Path:
    with patch("pilot.plugins.scaffold.installed_plugins_dir", return_value=tmp_path):
        return scaffold_plugin(slug, label=label)


def test_scaffold_creates_the_expected_files(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-plugin")

    assert plugin_dir == tmp_path / "my-plugin"
    for rel in (
        "__init__.py",
        "plugin.py",
        "api.py",
        "README.md",
        "frontend/package.json",
        "frontend/vite.config.js",
        "frontend/src/index.js",
        "frontend/src/Settings.vue",
    ):
        assert (plugin_dir / rel).is_file(), rel


def test_scaffolded_python_files_are_syntactically_valid(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-plugin")

    ast.parse((plugin_dir / "plugin.py").read_text())
    ast.parse((plugin_dir / "api.py").read_text())


def test_scaffolded_plugin_py_uses_a_valid_python_identifier_for_a_hyphenated_slug(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-plugin")

    content = (plugin_dir / "plugin.py").read_text()
    assert "my_plugin_bp" in content
    assert "my-plugin_bp" not in content


def test_scaffolded_package_json_is_valid_and_named_after_the_slug(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-plugin")

    data = json.loads((plugin_dir / "frontend" / "package.json").read_text())
    assert data["name"] == "pilot-plugin-my-plugin-frontend"
    assert "vue" in data["devDependencies"]


def test_scaffold_uses_slug_as_default_label(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-cool-plugin")

    index_js = (plugin_dir / "frontend" / "src" / "index.js").read_text()
    assert "My Cool Plugin" in index_js


def test_scaffold_uses_a_custom_label_when_given(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-plugin", label="Totally Custom Label")

    index_js = (plugin_dir / "frontend" / "src" / "index.js").read_text()
    assert "Totally Custom Label" in index_js


def test_scaffold_escapes_a_label_containing_quotes(tmp_path: Path) -> None:
    plugin_dir = _scaffold(tmp_path, "my-plugin", label='He said "hi" and it\'s fine')

    # Must still be syntactically valid JS/Vue after embedding the label.
    index_js = (plugin_dir / "frontend" / "src" / "index.js").read_text()
    assert 'He said \\"hi\\" and it\'s fine' in index_js


def test_scaffold_rejects_invalid_name(tmp_path: Path) -> None:
    with pytest.raises(PluginValidationError):
        _scaffold(tmp_path, "../escape")


def test_scaffold_rejects_a_bundled_plugin_name(tmp_path: Path) -> None:
    with pytest.raises(PluginValidationError):
        with patch("pilot.plugins.scaffold.PluginManager.is_bundled", return_value=True):
            _scaffold(tmp_path, "cloudflare")


def test_scaffold_rejects_an_already_existing_plugin_dir(tmp_path: Path) -> None:
    (tmp_path / "my-plugin").mkdir()

    with pytest.raises(PluginValidationError):
        _scaffold(tmp_path, "my-plugin")
