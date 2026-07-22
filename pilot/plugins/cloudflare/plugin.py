from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Type

from pilot.plugins.base import BasePilotPlugin
from pilot.plugins.cloudflare.config import CloudflareConfig

if TYPE_CHECKING:
    from flask import Flask


class Plugin(BasePilotPlugin):
    @property
    def name(self) -> str:
        return "cloudflare"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_routes(self, app: Flask) -> None:
        from pilot.plugins.cloudflare.api import cloudflare_bp

        api_prefix = app.config.get("API_V1_PREFIX", "/api/v1")
        app.register_blueprint(cloudflare_bp, url_prefix=f"{api_prefix}/cloudflare")

    def register_config_tables(self) -> Dict[str, Type[Any]]:
        return {"cloudflare": CloudflareConfig}
