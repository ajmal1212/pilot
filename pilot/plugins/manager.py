from __future__ import annotations

import importlib
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Type

from pilot.plugins.base import BasePilotPlugin

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages discovery, registration, and hooks for Pilot plugins."""

    _plugins: Dict[str, BasePilotPlugin] = {}
    _initialized: bool = False

    @classmethod
    def load_plugins(cls) -> None:
        """Discovers and instantiates plugins in pilot/plugins directory."""
        cls._plugins.clear()
        plugins_dir = Path(__file__).parent
        for item in plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith(("_", ".")):
                plugin_module_name = f"pilot.plugins.{item.name}.plugin"
                try:
                    module = importlib.import_module(plugin_module_name)
                    importlib.reload(module)
                    plugin_class = getattr(module, "Plugin", None)
                    if plugin_class and issubclass(plugin_class, BasePilotPlugin):
                        instance = plugin_class()
                        cls._plugins[instance.name] = instance
                        logger.info(f"Loaded Pilot Plugin: {instance.name} (v{instance.version})")
                except ImportError:
                    pass
                except Exception as e:
                    logger.error(f"Failed to load plugin from {plugin_module_name}: {e}")

        cls._initialized = True

    @classmethod
    def register_routes(cls, app: Flask) -> None:
        """Registers all plugin API blueprints into the Flask app."""
        cls.load_plugins()
        for plugin in cls._plugins.values():
            try:
                plugin.register_routes(app)
            except Exception as e:
                logger.error(f"Failed to register routes for plugin {plugin.name}: {e}")

    @classmethod
    def get_config_tables(cls) -> Dict[str, Type[Any]]:
        """Collects config table schemas registered by all active plugins."""
        cls.load_plugins()
        tables: Dict[str, Type[Any]] = {}
        for plugin in cls._plugins.values():
            try:
                tables.update(plugin.register_config_tables())
            except Exception as e:
                logger.error(f"Failed to get config tables for plugin {plugin.name}: {e}")
        return tables

    @classmethod
    def get_plugins(cls) -> List[BasePilotPlugin]:
        """Returns all loaded plugin instances."""
        cls.load_plugins()
        return list(cls._plugins.values())

    @classmethod
    def get_plugin(cls, name: str) -> BasePilotPlugin | None:
        """Returns a specific plugin by name."""
        cls.load_plugins()
        return cls._plugins.get(name)

    @classmethod
    def list_plugin_info(cls) -> List[Dict[str, Any]]:
        """Returns metadata for all installed plugin directories."""
        cls.load_plugins()
        plugins_dir = Path(__file__).parent
        info_list = []

        for item in plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith(("_", ".")):
                name = item.name
                instance = cls._plugins.get(name)

                repo_url = ""
                branch = ""
                try:
                    res_url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=item, capture_output=True, text=True)
                    if res_url.returncode == 0:
                        repo_url = res_url.stdout.strip()
                    res_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=item, capture_output=True, text=True)
                    if res_branch.returncode == 0:
                        branch = res_branch.stdout.strip()
                except Exception:
                    pass

                info_list.append({
                    "name": name,
                    "version": instance.version if instance else "1.0.0",
                    "installed": instance is not None,
                    "repo": repo_url,
                    "branch": branch,
                    "path": str(item)
                })
        return info_list
