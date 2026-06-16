import secrets
import socket
import tomllib
from pathlib import Path

from bench_cli.config.bench_toml_builder import BenchTomlBuilder
from bench_cli.exceptions import BenchError

# Added to every one of a new bench's ports together, so each bench gets its
# own non-overlapping block (nginx is shared across benches and left alone).
_PORT_BASES = {
    "http_port": 8000,
    "socketio_port": 9000,
    "redis_cache_port": 13000,
    "redis_queue_port": 11000,
    "admin_port": 8002,
}


class NewCommand:
    def __init__(self, target_directory: Path, name: str) -> None:
        self.target_directory = target_directory
        self.name = name

    def run(self) -> None:
        bench_toml = self.target_directory / "bench.toml"
        if bench_toml.exists():
            raise BenchError(f"A bench named '{self.name}' already exists at {self.target_directory}. Choose a different name or remove the existing bench.")

        benches_dir = self.target_directory.parent
        if not benches_dir.exists():
            print(f"Creating benches directory at {benches_dir}")
            benches_dir.mkdir(parents=True, exist_ok=True)

        print(f"Creating bench directory: {self.target_directory}")
        self.target_directory.mkdir(parents=True, exist_ok=True)

        offset = self._pick_port_offset(benches_dir)
        print("Writing bench.toml")
        settings = {
            "admin_password": secrets.token_hex(nbytes=5),
            **{key: base + offset for key, base in _PORT_BASES.items()},
        }
        bench_toml.write_text(BenchTomlBuilder(self.name, settings).render())

        print(f"\nBench '{self.name}' created at {self.target_directory}")
        print("\nNext step:")
        print("  bench start")
        print(f"  Open http://localhost:{settings['admin_port']} — the setup wizard guides you through the rest,")

    def _pick_port_offset(self, benches_dir: Path) -> int:
        """Smallest offset (added to every base port) that collides with
        neither another bench's bench.toml nor a port that's actually live
        right now — covers both stale configs and orphaned processes."""
        used = set()
        if benches_dir.is_dir():
            for other in benches_dir.iterdir():
                toml_path = other / "bench.toml"
                if not toml_path.exists():
                    continue
                try:
                    with open(toml_path, "rb") as f:
                        data = tomllib.load(f)
                    used.add(data.get("bench", {}).get("http_port", _PORT_BASES["http_port"]) - _PORT_BASES["http_port"])
                except Exception:
                    continue

        offset = 0
        while offset in used or any(self._port_is_live(base + offset) for base in _PORT_BASES.values()):
            offset += 1
        return offset

    @staticmethod
    def _port_is_live(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            return False
