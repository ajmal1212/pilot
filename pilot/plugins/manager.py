from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Type

from pilot.plugins.base import BasePilotPlugin
from pilot.utils import installed_plugins_dir

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)

_BUNDLED_ROOT = Path(__file__).parent
_INSTALLED_NAMESPACE = "pilot_installed_plugins"


class PluginManager:
    """Manages discovery, registration, and hooks for Pilot plugins.

    Two sources are loaded, keyed by their directory name (the plugin
    "slug"):

    - Bundled plugins ship inside `pilot/plugins/` with core, are reviewed
      and released together with Pilot, and can't be modified or removed
      through the plugin API.
    - Installed plugins are cloned by an admin into a data directory
      outside the `pilot` package (`pilot.utils.installed_plugins_dir`)
      and are the only ones the install/update/uninstall endpoints touch.
    """

    _plugins: Dict[str, BasePilotPlugin] = {}
    _initialized: bool = False

    @classmethod
    def load_plugins(cls) -> None:
        cls._plugins.clear()

        for item in _iter_plugin_dirs(_BUNDLED_ROOT):
            cls._try_load(item.name, f"pilot.plugins.{item.name}")

        installed_root = installed_plugins_dir()
        if installed_root.is_dir():
            _register_namespace_package(_INSTALLED_NAMESPACE, installed_root)
            for item in _iter_plugin_dirs(installed_root):
                cls._try_load(item.name, f"{_INSTALLED_NAMESPACE}.{item.name}")

        cls._initialized = True

    @classmethod
    def _try_load(cls, slug: str, module_name: str) -> None:
        try:
            instance = _import_plugin(module_name)
        except ImportError:
            return
        except Exception as e:
            logger.error(f"Failed to load plugin from {module_name}: {e}")
            return
        if instance is None:
            return
        cls._plugins[slug] = instance
        logger.info(f"Loaded Pilot Plugin: {slug} (v{instance.version}, bundled={cls.is_bundled(slug)})")

    @classmethod
    def load_installed_plugin_or_raise(cls, slug: str) -> BasePilotPlugin:
        """Load one just-installed plugin and surface failures instead of swallowing them.

        Used right after an install/update so the caller gets a real error
        instead of a task that reports success while the plugin silently
        failed to import.
        """
        installed_root = installed_plugins_dir()
        _register_namespace_package(_INSTALLED_NAMESPACE, installed_root)
        module_name = f"{_INSTALLED_NAMESPACE}.{slug}"
        instance = _import_plugin(module_name)
        if instance is None:
            raise ImportError(f"{module_name} does not define a `Plugin` subclass of BasePilotPlugin.")
        cls._plugins[slug] = instance
        return instance

    @classmethod
    def register_routes(cls, app: Flask) -> None:
        """Registers all plugin API blueprints into the Flask app."""
        cls.load_plugins()
        for slug, plugin in cls._plugins.items():
            try:
                plugin.register_routes(app)
            except Exception as e:
                logger.error(f"Failed to register routes for plugin {slug}: {e}")

    @classmethod
    def get_config_tables(cls) -> Dict[str, Type[Any]]:
        """Collects config table schemas registered by all active plugins."""
        cls.load_plugins()
        tables: Dict[str, Type[Any]] = {}
        for slug, plugin in cls._plugins.items():
            try:
                tables.update(plugin.register_config_tables())
            except Exception as e:
                logger.error(f"Failed to get config tables for plugin {slug}: {e}")
        return tables

    @classmethod
    def get_plugins(cls) -> List[BasePilotPlugin]:
        """Returns all loaded plugin instances."""
        cls.load_plugins()
        return list(cls._plugins.values())

    @classmethod
    def get_plugin(cls, slug: str) -> BasePilotPlugin | None:
        """Returns a specific plugin by its directory slug."""
        cls.load_plugins()
        return cls._plugins.get(slug)

    @classmethod
    def is_bundled(cls, slug: str) -> bool:
        """Whether `slug` ships with core, as opposed to being user-installed.

        Checked against the filesystem directly (not load state) so it
        stays correct even when a bundled plugin fails to import.
        """
        return (_BUNDLED_ROOT / slug / "plugin.py").is_file()

    @classmethod
    def list_plugin_info(cls) -> List[Dict[str, Any]]:
        """Returns metadata for all discovered plugin directories."""
        cls.load_plugins()
        info_list = [cls._describe(item, bundled=True) for item in _iter_plugin_dirs(_BUNDLED_ROOT)]

        installed_root = installed_plugins_dir()
        if installed_root.is_dir():
            info_list += [cls._describe(item, bundled=False) for item in _iter_plugin_dirs(installed_root)]

        return info_list

    @classmethod
    def _describe(cls, item: Path, *, bundled: bool) -> Dict[str, Any]:
        slug = item.name
        instance = cls._plugins.get(slug)
        repo_url, branch = ("", "") if bundled else _git_origin(item)
        return {
            "name": slug,
            "version": instance.version if instance else "1.0.0",
            "installed": instance is not None,
            "bundled": bundled,
            "repo": repo_url,
            "branch": branch,
            "path": str(item),
        }


def _iter_plugin_dirs(root: Path):
    for item in sorted(root.iterdir()):
        if item.is_dir() and not item.name.startswith(("_", ".")):
            yield item


def _import_plugin(module_name: str) -> BasePilotPlugin | None:
    module = importlib.import_module(module_name + ".plugin")
    importlib.reload(module)
    plugin_class = getattr(module, "Plugin", None)
    if plugin_class and isinstance(plugin_class, type) and issubclass(plugin_class, BasePilotPlugin):
        return plugin_class()
    return None


def _register_namespace_package(name: str, root: Path) -> None:
    """Make `root` importable as `name`, so each subdirectory under it is a
    regular submodule with normal package semantics (relative imports work).
    """
    existing = sys.modules.get(name)
    if existing is not None:
        existing.__path__ = [str(root)]
        return
    spec = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    spec.submodule_search_locations = [str(root)]
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module


def _git_origin(path: Path) -> tuple[str, str]:
    repo_url = ""
    branch = ""
    try:
        res_url = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=path, capture_output=True, text=True, timeout=10
        )
        if res_url.returncode == 0:
            repo_url = res_url.stdout.strip()
        res_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, capture_output=True, text=True, timeout=10
        )
        if res_branch.returncode == 0:
            branch = res_branch.stdout.strip()
    except Exception:
        pass
    return repo_url, branch
