from dataclasses import dataclass

@dataclass
class CloudflareConfig:
    enabled: bool = False
    tunnel_name: str = ""
    tunnel_token: str = ""
    domain: str = ""
    api_token: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.tunnel_token)
