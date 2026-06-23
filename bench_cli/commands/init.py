from __future__ import annotations

import shutil
from collections.abc import Callable
from typing import TYPE_CHECKING

from bench_cli.commands.base import Command

if TYPE_CHECKING:
    from bench_cli.core.bench import Bench

_BENCH_DIRS = ("apps", "sites", "logs", "config", "pids", "env", "admin", "tasks")


class InitCommand(Command):
    name = "init"
    help = "Initialise the bench."
    # Heavy/irreversible — never guess the target bench.
    requires_explicit_bench = True

    def __init__(self, bench: "Bench") -> None:
        self.bench = bench
        self._step_counter = 0
        self._total_steps = 0
        self._rollback_actions: list[tuple[str, Callable[[], None]]] = []

    def run(self) -> None:
        try:
            self._do_run()
        except Exception as exc:
            print(f"\nError: {exc}", flush=True)
            self._rollback()
            raise

    # ── rollback infrastructure ────────────────────────────────────────────

    def _on_rollback(self, label: str, fn: Callable[[], None]) -> None:
        self._rollback_actions.append((label, fn))

    def _rollback(self) -> None:
        if not self._rollback_actions:
            return
        print("\nRolling back changes...", flush=True)
        for label, fn in reversed(self._rollback_actions):
            print(f"  Removing {label}...", flush=True)
            try:
                fn()
            except Exception as e:
                print(f"    Warning: rollback step failed — {e}", flush=True)
        print(
            "\nRollback complete. bench.toml is preserved — fix the issue and run init again.",
            flush=True,
        )

    def _remove_bench_dirs(self) -> None:
        for name in _BENCH_DIRS:
            p = self.bench.path / name
            if p.exists() or p.is_symlink():
                shutil.rmtree(p, ignore_errors=True)

    def _remove_nginx_symlink(self) -> None:
        import subprocess

        from bench_cli.platform import _privileged

        symlink = self.bench.config.nginx.config_dir / f"{self.bench.config.name}.conf"
        if symlink.exists() or symlink.is_symlink():
            subprocess.run(_privileged(["unlink", str(symlink)]), capture_output=True, check=False)

    def _remove_systemd_units(self) -> None:
        import subprocess

        from bench_cli.managers.systemd_process_manager import SystemdProcessManager

        mgr = SystemdProcessManager(self.bench)
        for f in mgr.user_unit_dir.glob(f"{self.bench.config.name}*"):
            f.unlink(missing_ok=True)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            check=False,
            env=mgr._systemctl_env(),
        )

    def _remove_openrc_services(self) -> None:
        from bench_cli.managers.openrc_process_manager import OpenRCProcessManager

        OpenRCProcessManager(self.bench).remove_services()

    # ── init steps ─────────────────────────────────────────────────────────

    def _do_run(self) -> None:
        from bench_cli.managers.python_env_manager import PythonEnvManager
        from bench_cli.platform import is_linux

        self._check_passwordless_sudo()

        production = self.bench.config.production.enabled
        volume_enabled = is_linux() and self.bench.config.volume.enabled
        dedicated_db = is_linux() and bool(self.bench.config.mariadb.instance)
        # Passwordless sudo is set up by install.sh and enforced above by
        # _check_passwordless_sudo, so the steps below never block on a prompt.
        python_env_manager = PythonEnvManager(self.bench)

        # The ordered list of steps that will actually run, so the progress total
        # is derived from the steps themselves rather than a hand-counted number
        # that drifts whenever a step is added or removed.
        steps: list[tuple[str, Callable[[], None]]] = [
            ("Validate bench.toml", self.bench.config.validate),
            ("Install system packages", self._install_system_packages),
        ]
        if volume_enabled:
            steps.append(("Set up ZFS volumes", self._setup_volume))
        if dedicated_db:
            steps.append(("Provision MariaDB instance", self._provision_mariadb_instance))
        steps += [
            ("Create bench directory structure", self._create_bench_structure),
            ("Create Python virtualenv", lambda: self._create_virtualenv(python_env_manager)),
            ("Clone and install framework app", lambda: self._install_framework_apps(python_env_manager)),
            ("Install Node.js", python_env_manager.install_node),
            ("Install Node.js dependencies", python_env_manager.install_node_dependencies),
            ("Configure Redis", self._configure_redis),
            ("Download admin frontend", self._download_admin_frontend),
            ("Generate process config", lambda: self._generate_process_config(production)),
        ]
        if production:
            steps += [
                ("Setup process manager", self._setup_process_manager),
                ("Setup nginx", self._setup_nginx),
                ("Setup Let's Encrypt SSL", self._setup_letsencrypt),
            ]

        self._total_steps = len(steps)
        for description, action in steps:
            self._step(description)
            action()

        print("\nBench initialised. Next steps:")
        print("  bench new-site site1.example.com   # create your first site")
        print("  bench start                        # start all processes")

    def _create_bench_structure(self) -> None:
        self.bench.create_directories()
        self.bench.write_common_site_config()
        self._on_rollback("bench directories", self._remove_bench_dirs)

    def _create_virtualenv(self, python_env_manager) -> None:
        python_env_manager.ensure_python()
        python_env_manager.create_venv()

    def _install_framework_apps(self, python_env_manager) -> None:
        for app in self.bench.init_apps():
            if not app.is_cloned:
                print(f"  Cloning {app.config.name}...")
                app.clone()
            print(f"  Installing {app.config.name}...")
            python_env_manager.install_app(app)
        self.bench.write_apps_txt()

    def _configure_redis(self) -> None:
        from bench_cli.managers.redis_manager import RedisManager

        RedisManager(self.bench.config.redis, self.bench).generate_configs()

    def _generate_process_config(self, production: bool) -> None:
        from bench_cli.managers.process_manager import ProcessManagerFactory

        self._write_common_config_for_production(production)
        ProcessManagerFactory.create(self.bench).generate_config()

    def _check_passwordless_sudo(self) -> None:
        from bench_cli.platform import has_passwordless_sudo, is_linux

        if not is_linux() or has_passwordless_sudo():
            return
        raise RuntimeError(
            "Passwordless sudo is not configured for this user. bench init needs it to "
            "install packages and manage services without a password prompt.\n"
            "Set it up by re-running the installer:\n"
            "  curl -fsSL https://raw.githubusercontent.com/frappe/bench-cli/main/install.sh | bash\n"
            "or add /etc/sudoers.d/<user> containing: <user> ALL=(ALL) NOPASSWD: ALL"
        )

    def _step(self, description: str) -> None:
        self._step_counter += 1
        print(f"[{self._step_counter}/{self._total_steps}] {description}...", flush=True)

    def _download_admin_frontend(self) -> None:
        from bench_cli.commands.admin import BuildAdminCommand, _cli_root, download_admin_frontend

        if not download_admin_frontend(_cli_root()):
            print("  Pre-built download failed — building from source (requires Node.js)...")
            BuildAdminCommand().run()

    def _setup_volume(self) -> None:
        from bench_cli.commands.volume import VolumeSetupCommand

        VolumeSetupCommand(self.bench.config.volume, self.bench.path, bench_config=self.bench.config).run()

    def _provision_mariadb_instance(self) -> None:
        from bench_cli.managers.mariadb_manager import MariaDBManager

        # Runs after _setup_volume: if volume is enabled, the bench's mariadb
        # dataset is already mounted at the instance datadir, so install-db
        # writes straight onto ZFS; otherwise the datadir is a plain directory.
        MariaDBManager(self.bench.config.mariadb).provision_instance(self.bench.config_path)

    # Build/runtime deps for compiling frappe's Python and Node wheels on Alpine.
    # musl ships no manylinux wheels, so the full header set is needed; bash and
    # tzdata are runtime deps frappe assumes are present. python3-dev provides
    # Python.h: Alpine ships a system python that `uv venv` reuses, so C
    # extensions (mysqlclient, etc.) need the matching dev headers to compile.
    _ALPINE_BUILD_PACKAGES = (
        "build-base", "pkgconf", "mariadb-dev", "git", "bash", "tzdata",
        "python3-dev", "linux-headers", "libffi-dev", "openssl-dev", "libxml2-dev",
        "libxslt-dev", "jpeg-dev", "zlib-dev", "freetype-dev", "tiff-dev",
        "lcms2-dev", "openjpeg-dev",
    )

    def _install_system_packages(self) -> None:
        from bench_cli.managers.mariadb_manager import MariaDBManager
        from bench_cli.managers.python_env_manager import PythonEnvManager
        from bench_cli.managers.redis_manager import RedisManager
        from bench_cli.platform import get_package_manager, is_alpine, is_linux

        pkg = get_package_manager()
        if is_linux():
            pkg.update()

        mariadb_manager = MariaDBManager(self.bench.config.mariadb)
        if mariadb_manager.is_dedicated:
            # Install the package only; the instance is provisioned after volume
            # setup (see _do_run) so a ZFS-backed datadir, if any, is mounted
            # before mariadb-install-db runs against it.
            freshly_installed = not mariadb_manager.is_installed()
            mariadb_manager.install()
            if freshly_installed and is_linux():
                # apt auto-starts the shared mariadb service on port 3306 after
                # installation. Stop and disable it so the dedicated instance can
                # claim its port without a conflict when provision_instance runs.
                mariadb_manager.stop_shared()

        else:
            freshly_installed = not mariadb_manager.is_installed()
            mariadb_manager.install()
            mariadb_manager.start()
            if freshly_installed:
                mariadb_manager.secure_installation()
            elif not mariadb_manager.check_credentials():
                raise RuntimeError(
                    "MariaDB is already installed but the configured root password is incorrect. "
                    "Fix mariadb.root_password in bench.toml (or secure the existing MariaDB) and retry."
                )
        RedisManager(self.bench.config.redis, self.bench).install()
        if is_alpine():
            pkg.install(*self._ALPINE_BUILD_PACKAGES)
        elif is_linux():
            # python3-dev provides Python.h for C-extension wheels when uv reuses
            # a system python (it isn't needed when uv downloads a managed one).
            pkg.install("build-essential", "pkg-config", "libmariadb-dev", "git", "python3-dev")
        PythonEnvManager(self.bench).ensure_python()

    def _write_common_config_for_production(self, production: bool) -> None:
        if not production:
            return
        import json

        common_config_path = self.bench.sites_path / "common_site_config.json"
        existing: dict = {}
        if common_config_path.exists():
            try:
                existing = json.loads(common_config_path.read_text())
            except Exception:
                pass
        existing["dns_multitenant"] = 1
        common_config_path.write_text(json.dumps(existing, indent=2))

    def _setup_process_manager(self) -> None:
        if self.bench.config.production.process_manager == "openrc":
            from bench_cli.managers.openrc_process_manager import OpenRCProcessManager

            mgr = OpenRCProcessManager(self.bench)
            mgr.install_config()
            mgr.reload()
            self._on_rollback("openrc services", self._remove_openrc_services)
        elif self.bench.config.production.process_manager == "systemd":
            from bench_cli.managers.systemd_process_manager import SystemdProcessManager

            mgr = SystemdProcessManager(self.bench)
            mgr.install_config()
            mgr.reload()
            self._on_rollback("systemd user units", self._remove_systemd_units)
        else:
            import subprocess

            from bench_cli.platform import get_package_manager, is_linux

            pkg = get_package_manager()
            if is_linux() and not pkg.is_installed("supervisor"):
                pkg.install("supervisor")
                subprocess.run(["sudo", "systemctl", "disable", "--now", "supervisor"], check=False)
            from bench_cli.managers.supervisor_process_manager import SupervisorProcessManager

            mgr = SupervisorProcessManager(self.bench)
            mgr.install_config()
            mgr.reload()
            # supervisor config lives inside config/ — _remove_bench_dirs handles it

    def _setup_nginx(self) -> None:
        from bench_cli.commands.setup.nginx import SetupNginxCommand

        SetupNginxCommand(self.bench).run()
        self._on_rollback("nginx config symlink", self._remove_nginx_symlink)

    def _setup_letsencrypt(self) -> None:
        if not self.bench.config.letsencrypt.email:
            print("  Skipped — no letsencrypt.email set in bench.toml")
            return
        from bench_cli.commands.setup.letsencrypt import SetupLetsEncryptCommand

        SetupLetsEncryptCommand(self.bench).run()
