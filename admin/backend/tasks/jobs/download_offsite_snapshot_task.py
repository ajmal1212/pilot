import sys

from pilot.integrations.s3.snapshots import OffsiteSnapshot

from .base_task import BaseTask


class DownloadOffsiteSnapshotTask(BaseTask):
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
        from pilot.managers.volume_manager import VolumeManager

        self._step("upload", f"Download snapshot {self.tag}")
        try:
            offsite_snapshot = OffsiteSnapshot.from_config(self.bench.config.s3)
            offsite_snapshot.upload(self.bench.config.name, self.tag, self.dataset)
        except Exception as e:
            ...