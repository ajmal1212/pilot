import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pilot.plugins import git_ops
from pilot.plugins.manager import PluginManager
from pilot.plugins.security import confine_to_root, validate_plugin_name, validate_repo_url
from pilot.tasks import Task, step
from pilot.utils import installed_plugins_dir, make_private_directory


@dataclass(kw_only=True)
class InstallPluginTask(Task):
    command: ClassVar[str] = "install-plugin"

    repo: str
    branch: str = "main"
    plugin_name: str

    def run(self) -> None:
        self.validate_inputs()
        plugin_dir = self.clone_repo()
        self.validate_plugin(plugin_dir)
        self.build_frontend()
        self.load_plugin()
        self.record_audit(
            "plugin",
            {"event": "install", "plugin": self.plugin_name, "repo": self.repo, "branch": self.branch},
        )

    @step("validate_inputs", "Validating plugin name and repository")
    def validate_inputs(self) -> None:
        try:
            validate_plugin_name(self.plugin_name)
            validate_repo_url(self.repo)
        except Exception as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        if PluginManager.is_bundled(self.plugin_name):
            print(f"'{self.plugin_name}' is a bundled plugin name and cannot be reused.", file=sys.stderr)
            sys.exit(1)

    @step("clone", lambda self: f"Cloning {self.repo} ({self.branch}) into plugins-data/{self.plugin_name}")
    def clone_repo(self) -> Path:
        plugins_root = installed_plugins_dir()
        make_private_directory(plugins_root, parents=True)
        dest = confine_to_root(plugins_root, self.plugin_name)

        if dest.exists():
            print(f"Plugin directory {dest} already exists. Pulling latest...", file=sys.stdout)
            res = git_ops.pull(dest)
            if res.returncode != 0:
                print(f"Git pull failed: {res.stderr}", file=sys.stderr)
                sys.exit(1)
            return dest

        res = git_ops.clone(self.repo, self.branch, dest)
        if res.returncode != 0:
            print(f"Git clone failed: {res.stderr}", file=sys.stderr)
            sys.exit(1)
        return dest

    @step("validate", lambda self: f"Validating plugin {self.plugin_name}")
    def validate_plugin(self, plugin_dir: Path) -> None:
        plugin_file = plugin_dir / "plugin.py"
        if not plugin_file.exists():
            print(f"Plugin is missing {plugin_file.name}: {plugin_file}", file=sys.stderr)
            sys.exit(1)

    @step("build_frontend", lambda self: "Building frontend static assets")
    def build_frontend(self) -> None:
        frontend_dir = Path(__file__).parents[2] / "admin" / "frontend"
        if (frontend_dir / "package.json").exists():
            res = subprocess.run(
                ["npm", "run", "build"], cwd=frontend_dir, capture_output=True, text=True, timeout=600
            )
            if res.returncode != 0:
                print(f"Frontend build warning: {res.stderr}", file=sys.stderr)

    @step("load_plugin", lambda self: f"Initializing plugin {self.plugin_name}")
    def load_plugin(self) -> None:
        try:
            PluginManager.load_installed_plugin_or_raise(self.plugin_name)
        except Exception as e:
            print(f"Plugin cloned but failed to load: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    InstallPluginTask.main()
