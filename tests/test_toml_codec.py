from __future__ import annotations

from dataclasses import dataclass

from pilot._internal.toml_codec import TomlDataclassCodec, dumps_toml, loads_toml


@dataclass
class ServiceConfig:
    name: str
    port: int
    enabled: bool = True


SERVICE_CODEC = TomlDataclassCodec(
    from_config_dict=lambda data: ServiceConfig(**data["service"]),
    to_config_dict=lambda config: {
        "service": {
            "name": config.name,
            "port": config.port,
            "enabled": config.enabled,
        }
    },
)


def test_toml_dict_round_trip() -> None:
    data = {
        "service": {"name": "worker", "port": 7000, "enabled": True},
        "routes": [{"name": "api", "hosts": ["one.test", "two.test"]}],
    }

    assert loads_toml(dumps_toml(data)) == data


def test_dataclass_dict_round_trip() -> None:
    config = ServiceConfig(name="admin", port=7001)

    assert SERVICE_CODEC.from_dict(SERVICE_CODEC.to_dict(config)) == config


def test_dataclass_toml_round_trip() -> None:
    config = ServiceConfig(name="admin", port=7001, enabled=False)

    assert SERVICE_CODEC.loads(SERVICE_CODEC.dumps(config)) == config
