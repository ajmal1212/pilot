import sys

from pilot.integrations.s3.snapshots import OffsiteSnapshot

from .base_task import BaseTask


class DownloadSnapshotTask(BaseTask):
    @classmethod
    def _parser(cls):
        p = super()._parser()
        p.add_argument("dataset")
        p.add_argument("tag")
        return p

    def __init__(self, bench, bench_root, args):
        super().__init__(bench, bench_root, args)
        self.dataset = args.dataset
        self.tag = args.tag

    def run(self) -> None:
        self._step("download", f"Download snapshot {self.tag}")
        try:
            offsite_snapshot = OffsiteSnapshot.from_config(self.bench.config.s3)
            restore_dataset = offsite_snapshot.download(self.bench.config.name, self.tag, self.dataset)
        except Exception as e:
            print(f"Offsite snapshot download failed: {e}")
            sys.exit(1)

        print(f"Snapshot received into {restore_dataset}@{self.tag}")
        self._step("done")


if __name__ == "__main__":
    DownloadSnapshotTask.main()
