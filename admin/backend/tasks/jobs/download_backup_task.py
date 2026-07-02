import sys
from pathlib import Path

from pilot.integrations.s3.backups import OffsiteBackup

from .base_task import BaseTask


class DownloadBackupTask(BaseTask):
    @classmethod
    def _parser(cls):
        p = super()._parser()
        p.add_argument("site")
        p.add_argument("timestamp")
        return p

    def __init__(self, bench, bench_root, args):
        super().__init__(bench, bench_root, args)
        self.site = args.site
        self.timestamp = args.timestamp

    def _backups_path(self) -> Path:
        return self.bench.sites_path / self.site / "private" / "backups"

    def run(self) -> None:
        self._step("download", f"Download backup {self.timestamp}")
        try:
            offsite_backup = OffsiteBackup.from_config(self.bench.config.s3)
            files = offsite_backup.get_backup(self.site, self.timestamp)
            if not files:
                raise ValueError(f"No offsite backup found for {self.timestamp}")

            backups_path = self._backups_path()
            backups_path.mkdir(parents=True, exist_ok=True)
            for filename in files.values():
                # Same directory, same filename Frappe already uses locally —
                # the next local scan just picks these up, no separate merge needed.
                offsite_backup.download(self.site, self.timestamp, filename, backups_path / filename)
        except Exception as e:
            print(f"Offsite backup download failed: {e}")
            sys.exit(1)

        self._step("done")


if __name__ == "__main__":
    DownloadBackupTask.main()
