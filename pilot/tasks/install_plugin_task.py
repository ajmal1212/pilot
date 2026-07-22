import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pilot.tasks import Task, step
from pilot.plugins.manager import PluginManager


@dataclass(kw_only=True)
class InstallPluginTask(Task):
    command: ClassVar[str] = "install-plugin"

    repo: str
    branch: str = "main"
    plugin_name: str

    def run(self) -> None:
        plugin_dir = self.clone_repo()
        self.validate_plugin(plugin_dir)
        self.build_frontend()
        self.load_plugin()

    @step("clone", lambda self: f"Cloning {self.repo} ({self.branch}) into pilot/plugins/{self.plugin_name}")
    def clone_repo(self) -> Path:
        plugins_root = Path(__file__).parents[1] / "plugins"
        plugins_root.mkdir(parents=True, exist_ok=True)
        dest = plugins_root / self.plugin_name

        if dest.exists():
            print(f"Plugin directory {dest} already exists. Pulling latest...", file=sys.stdout)
            res = subprocess.run(["git", "pull"], cwd=dest, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Git pull failed: {res.stderr}", file=sys.stderr)
                sys.exit(1)
            return dest

        cmd = ["git", "clone", "-b", self.branch, self.repo, str(dest)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Git clone failed: {res.stderr}", file=sys.stderr)
            sys.exit(1)
        return dest

    @step("validate", lambda self: f"Validating plugin {self.plugin_name}")
    def validate_plugin(self, plugin_dir: Path) -> None:
        plugin_file = plugin_dir / "plugin.py"
        if not plugin_file.exists():
            print(f"Warning: {plugin_file} not found.", file=sys.stdout)

    @step("build_frontend", lambda self: "Building frontend static assets")
    def build_frontend(self) -> None:
        frontend_dir = Path(__file__).parents[2] / "admin" / "frontend"
        if (frontend_dir / "package.json").exists():
            res = subprocess.run(["npm", "run", "build"], cwd=frontend_dir, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Frontend build warning: {res.stderr}", file=sys.stderr)

    @step("load_plugin", lambda self: f"Initializing plugin {self.plugin_name}")
    def load_plugin(self) -> None:
        PluginManager.load_plugins()


if __name__ == "__main__":
    InstallPluginTask.main()
