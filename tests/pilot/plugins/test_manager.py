from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pilot.plugins.manager import PluginManager

_PLUGIN_SOURCE = """
from pilot.plugins.base import BasePilotPlugin


class Plugin(BasePilotPlugin):
    @property
    def name(self):
        return "{name}"
"""


def _write_plugin(root: Path, slug: str, plugin_name: str | None = None) -> None:
    plugin_dir = root / slug
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text("")
    (plugin_dir / "plugin.py").write_text(_PLUGIN_SOURCE.format(name=plugin_name or slug))


def test_is_bundled_true_for_a_directory_under_the_bundled_root(tmp_path: Path) -> None:
    (tmp_path / "sample").mkdir()
    (tmp_path / "sample" / "plugin.py").write_text("")

    with patch("pilot.plugins.manager._BUNDLED_ROOT", tmp_path):
        assert PluginManager.is_bundled("sample") is True


def test_unknown_slug_is_not_bundled() -> None:
    assert PluginManager.is_bundled("some-installed-plugin") is False


def test_installed_plugin_is_discovered_and_not_bundled(tmp_path: Path) -> None:
    bundled_root = tmp_path / "bundled"
    bundled_root.mkdir()
    installed_root = tmp_path / "installed"
    _write_plugin(installed_root, "demo")

    with (
        patch("pilot.plugins.manager._BUNDLED_ROOT", bundled_root),
        patch("pilot.plugins.manager.installed_plugins_dir", return_value=installed_root),
    ):
        info = {entry["name"]: entry for entry in PluginManager.list_plugin_info()}

    assert info["demo"]["bundled"] is False
    assert info["demo"]["installed"] is True


def test_plugin_dir_resolves_bundled_then_installed(tmp_path: Path) -> None:
    bundled_root = tmp_path / "bundled"
    _write_plugin(bundled_root, "sample")
    installed_root = tmp_path / "installed"
    _write_plugin(installed_root, "demo")

    with (
        patch("pilot.plugins.manager._BUNDLED_ROOT", bundled_root),
        patch("pilot.plugins.manager.installed_plugins_dir", return_value=installed_root),
    ):
        assert PluginManager.plugin_dir("sample") == bundled_root / "sample"
        assert PluginManager.plugin_dir("demo") == installed_root / "demo"
        assert PluginManager.plugin_dir("missing") is None


def test_plugin_dir_rejects_traversal(tmp_path: Path) -> None:
    from pilot.plugins.security import PluginValidationError

    with patch("pilot.plugins.manager._BUNDLED_ROOT", tmp_path):
        try:
            PluginManager.plugin_dir("../../etc")
        except PluginValidationError:
            pass
        else:
            raise AssertionError("expected a traversal attempt to raise")


def test_has_frontend_reflects_a_built_dist_bundle(tmp_path: Path) -> None:
    bundled_root = tmp_path / "bundled"
    _write_plugin(bundled_root, "with-ui")
    frontend_dist = bundled_root / "with-ui" / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "index.js").write_text("export function init() {}")
    _write_plugin(bundled_root, "without-ui")

    with patch("pilot.plugins.manager._BUNDLED_ROOT", bundled_root):
        info = {entry["name"]: entry for entry in PluginManager.list_plugin_info()}

    assert info["with-ui"]["has_frontend"] is True
    assert info["without-ui"]["has_frontend"] is False


def test_load_installed_plugin_or_raise_surfaces_broken_plugin(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "broken"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text("")
    (plugin_dir / "plugin.py").write_text("raise RuntimeError('boom')")

    with patch("pilot.plugins.manager.installed_plugins_dir", return_value=tmp_path):
        try:
            PluginManager.load_installed_plugin_or_raise("broken")
        except Exception as e:
            assert "boom" in str(e)
        else:
            raise AssertionError("expected the broken plugin import to raise")
