from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Type

if TYPE_CHECKING:
    from flask import Flask


class BasePilotPlugin(ABC):
    """Base class for all Pilot plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the plugin."""
        pass

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_routes(self, app: Flask) -> None:
        """Register Flask blueprints/routes for this plugin."""
        pass

    def register_config_tables(self) -> Dict[str, Type[Any]]:
        """
        Return a dict mapping config section names to dataclass/config classes.
        Example: {"cloudflare": CloudflareConfig}
        """
        return {}

    def on_bench_start(self, bench: Any) -> None:
        """Hook called when a bench service is started."""
        pass

    def on_bench_stop(self, bench: Any) -> None:
        """Hook called when a bench service is stopped."""
        pass
