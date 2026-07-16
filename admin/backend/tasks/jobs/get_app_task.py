from pilot.commands.get_app import GetAppCommand
from pilot.core.marketplace import Marketplace
from pilot.exceptions import BenchError

from .base_task import BaseTask


class GetAppTask(BaseTask):
    @classmethod
    def _parser(cls):
        p = super()._parser()
        p.add_argument("--repo", default="")
        p.add_argument("--branch", default="")
        p.add_argument("--marketplace-app", default="")
        return p

    def __init__(self, bench, bench_root, args):
        super().__init__(bench, bench_root, args)
        self.repo = args.repo
        self.branch = args.branch
        self.marketplace_app = args.marketplace_app

    def run(self) -> None:
        if self.marketplace_app:
            repo, branch = self._resolve_marketplace_app()
        else:
            repo, branch = self.repo, self.branch
        self._step("fetch", f"Fetch {self.marketplace_app or self.repo}")
        GetAppCommand(self.bench, repo, branch, install_dependencies=bool(self.marketplace_app)).run()
        self._step("done")

    def _resolve_marketplace_app(self) -> tuple[str, str]:
        resolver = next(
            (r for r in Marketplace(self.bench).read_all_apps() if r.app == self.marketplace_app), None
        )
        if not resolver:
            raise BenchError(f"'{self.marketplace_app}' not found in marketplace.")
        return resolver.repo, resolver.target


if __name__ == "__main__":
    GetAppTask.main()
