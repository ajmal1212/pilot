from dataclasses import dataclass, field


@dataclass
class BenchesDatasetConfig:
    reservation: str = "10G"
    quota: str = "50G"
    data_dir: str = "/home/bench"


@dataclass
class MariaDBDatasetConfig:
    reservation: str = "5G"
    quota: str = "20G"
    data_dir: str = "/var/lib/mysql"


@dataclass
class ImageConfig:
    size: str = ""
    path: str = ""


@dataclass
class VolumeConfig:
    """Optional ZFS storage for the bench. When configured, the bench gets a
    pool backed by a dedicated disk, a preallocated image file, or
    auto-resolved at init time. Omitting the [volume] section skips ZFS
    entirely — snapshots are unavailable in that case."""

    enabled: bool = False  # True only when [volume] section is present in bench.toml
    pool: str = "bench-pool"
    backing: str = "auto"  # "device" | "image" | "auto" (resolved during bench init)
    device: str = ""
    image: ImageConfig = field(default_factory=ImageConfig)
    benches: BenchesDatasetConfig = field(default_factory=BenchesDatasetConfig)
    mariadb: MariaDBDatasetConfig = field(default_factory=MariaDBDatasetConfig)

    @property
    def benches_dataset(self) -> str:
        return f"{self.pool}/benches"

    @property
    def mariadb_dataset(self) -> str:
        return f"{self.pool}/mariadb"

    @property
    def image_path(self) -> str:
        return self.image.path or f"/var/lib/bench-zfs/{self.pool}.img"
