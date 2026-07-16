from pilot.commands.get_app import GetAppCommand
from pilot.core.app import App
from pilot.core.marketplace import Marketplace
from pilot.core.site import Site, SiteConfig
from pilot.exceptions import BenchError

from .base_task import BaseTask


class GetAndInstallAppTask(BaseTask):
    """Fetch an app (by repo or marketplace name) and install it on zero or
    more sites. Zero sites is valid: it just fetches (and, for marketplace
    apps, resolves dependencies) without installing anywhere."""

    @classmethod
    def _parser(cls):
        p = super()._parser()
        p.add_argument("--repo", default="")
        p.add_argument("--branch", default="")
        p.add_argument("--marketplace-app", default="")
        p.add_argument("--sites", nargs="*", default=[])
        return p

    def __init__(self, bench, bench_root, args):
        super().__init__(bench, bench_root, args)
        self.repo = args.repo
        self.branch = args.branch
        self.marketplace_app = args.marketplace_app
        self.sites = args.sites or []

    def run(self) -> None:
        cmd = self._fetch()
        self._install_on_sites([cmd.app, *cmd.installed_dependencies])
        self._step("done")

    def _fetch(self) -> GetAppCommand:
        # get-app resolves and installs marketplace dependencies itself; a
        # plain repo has none to resolve.
        if self.marketplace_app:
            repo, branch = self._resolve_marketplace_app()
        else:
            repo, branch = self.repo, self.branch
        self._step("fetch", f"Fetch {self.marketplace_app or self.repo}")
        cmd = GetAppCommand(self.bench, repo, branch, install_dependencies=bool(self.marketplace_app))
        cmd.run()
        return cmd

    def _resolve_marketplace_app(self) -> tuple[str, str]:
        resolver = next(
            (r for r in Marketplace(self.bench).read_all_apps() if r.app == self.marketplace_app), None
        )
        if not resolver:
            raise BenchError(f"'{self.marketplace_app}' not found in marketplace.")
        return resolver.repo, resolver.target

    def _install_on_sites(self, apps: list[App]) -> None:
        from pilot.managers.python_env_manager import PythonEnvManager

        for site in self.sites:
            safe_key = site.replace(".", "_").replace("-", "_")
            for app in apps:
                self._step(f"install_{safe_key}_{app.config.name}", f"Install {app.config.name} on {site}")
                Site(SiteConfig(name=site, apps=[]), self.bench).install_app(app)

        env = PythonEnvManager(self.bench)
        for app in apps:
            self._step("build", f"Build assets for {app.config.name}")
            env.build_assets_for_app(app)


if __name__ == "__main__":
    GetAndInstallAppTask.main()
