from dataclasses import dataclass


@dataclass
class ProductionConfig:
    enabled: bool = False
    nginx: bool = False
    lightweight: bool = False
