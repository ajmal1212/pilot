from __future__ import annotations

import typing
from pathlib import Path

if typing.TYPE_CHECKING:
    from pilot.core.bench import Bench
    from pilot.managers.mariadb_manager import MariaDBManager
    from pilot.managers.volume_manager import VolumeManager


class SnapshotOrchestrator:
    """Snapshot/rollback the bench's single dataset (files + database).

    Because the database lives on the same dataset, every snapshot quiesces
    MariaDB (FLUSH TABLES WITH READ LOCK) for a consistent on-disk state, and
    every rollback stops MariaDB and puts sites into maintenance mode."""

    def __init__(
        self,
        volume: VolumeManager,
        mariadb: MariaDBManager | None = None,
        bench: Bench | None = None,
    ) -> None:
        self._volume = volume
        self._mariadb = mariadb
        self._bench = bench

    @property
    def _dataset(self) -> str:
        return self._volume.config.dataset_path

    def create_snapshot(self, tag: str) -> None:
        if self._mariadb:
            with self._mariadb.snapshot_lock():
                self._volume.snapshot(self._dataset, tag)
        else:
            self._volume.snapshot(self._dataset, tag)

    def rollback_snapshot(self, tag: str) -> None:
        if self._bench:
            self._bench.set_maintenance_mode(True)
        try:
            if self._mariadb:
                self._mariadb.stop()
            try:
                self._volume.rollback_snapshot(self._dataset, tag)
            finally:
                if self._mariadb:
                    self._mariadb.start()
        finally:
            if self._bench:
                self._bench.set_maintenance_mode(False)

    def restore_downloaded_snapshot(self, tag: str) -> None:
        """Promotes a snapshot downloaded into `<dataset>-restored-<tag>`
        (see `OffsiteSnapshot.download`) to become the bench's live dataset.

        `zfs rollback` can't do this — it only replays a dataset's own
        snapshot history, and a download lives on a separate filesystem — so
        this is a rename swap instead: the current live dataset is kept,
        renamed aside (not destroyed), and the restored one takes its place.
        """
        from pilot.managers.volume_manager import VolumeError

        if not self._bench or not self._mariadb:
            raise VolumeError("Restoring a downloaded snapshot needs both a bench and a MariaDB manager.")

        restored = f"{self._dataset}-restored-{tag}"
        if not self._volume.dataset_exists(restored):
            raise VolumeError(f"No downloaded snapshot found for '{tag}'. Download it first.")

        self._bench.set_maintenance_mode(True)
        workers_stopped = self._stop_workers()
        try:
            self._mariadb.stop()
            try:
                self._swap_dataset(restored, tag)
            finally:
                self._mariadb.start()
        finally:
            if workers_stopped:
                self._bench.restart()
            self._bench.set_maintenance_mode(False)

    def _stop_workers(self) -> bool:
        """Stop the bench's production workload so nothing holds files open on
        the dataset during the swap — open file descriptors keep the old
        dataset busy and block its cleanup. Dev benches (foreground `bench
        start`) are left alone; there the swap falls back to lazy unmounts."""
        if not self._bench.config.production.enabled:
            return False
        from pilot.exceptions import BenchError
        from pilot.managers.process_manager import ProcessManager

        try:
            ProcessManager.detect_running(self._bench).stop()
        except BenchError:
            return False
        return True

    def _swap_dataset(self, restored: str, tag: str) -> None:
        from datetime import datetime

        live = self._dataset
        mariadb_datadir = Path(self._mariadb.data_dir())
        bench_path = self._bench.path

        # Bind mounts reference the mount they were created against, not the
        # dataset name — they go stale the moment the underlying dataset is
        # renamed out from under them, so drop them before touching ZFS.
        # Workers and MariaDB are stopped by now, so a plain umount should
        # succeed; lazy is only a fallback (dev mode, or a straggler process)
        # and means the old dataset stays busy until those processes exit.
        self._unmount(bench_path)
        self._unmount(mariadb_datadir)

        aside = f"{live}-before-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        # The mountpoint property travels with the dataset object through a
        # rename, not with the name — capture it before renaming `live` away,
        # then reassign it after the swap so `live` actually serves the
        # newly-restored data at the bench's real mount location.
        live_mount = self._volume.get_mountpoint(live)
        self._volume.rename_dataset(live, aside)
        # Two datasets can't both claim the same mountpoint — the old one
        # keeps the path as a property from the rename, so clear it before
        # handing that path to the newly-promoted dataset below.
        self._volume.clear_mountpoint(aside)
        self._volume.rename_dataset(restored, live)
        self._volume.set_mountpoint(live, live_mount)

        mount = self._volume.get_mountpoint(live)
        self._volume.bind_mount(mount / "benches", bench_path)
        self._volume.bind_mount(mount / "mariadb", mariadb_datadir)

        # The restore is done — the old live state is fully superseded, so
        # don't keep a second full copy of the dataset lying around.
        self._destroy_when_free(aside)
        # The received stream's snapshot travels with the rename (`live@tag`
        # now exists for real), but a promotion isn't meant to leave a
        # standing local snapshot behind — without this, the tag would look
        # locally available again right after a restore that was supposed to
        # consume it.
        self._volume.destroy_snapshot(live, tag)

    def _unmount(self, path: Path) -> None:
        from pilot.exceptions import VolumeError

        try:
            self._volume.unmount(path)
        except VolumeError:
            self._volume.unmount(path, lazy=True)

    def _destroy_when_free(self, dataset: str) -> None:
        """`zfs destroy` fails with "dataset is busy" while any process still
        references the lazily-detached old mount (open files, or a shell
        cd'd into the bench directory before the restore). That never clears
        on its own, so don't retry: keep the restore successful, park the
        dataset, and name the pinning processes so the user can close them."""
        from pilot.exceptions import VolumeError

        try:
            self._volume.destroy_dataset(dataset)
        except VolumeError:
            print(f"Dataset {dataset} is still referenced by running processes and was kept aside.")
            for line in self._volume.processes_pinning_detached_mounts():
                print(f"  {line}")
            print(f"Close them (e.g. `cd ~` in shells inside the bench), then run: sudo zfs destroy -r {dataset}")


def get_orchestrator(bench_root):
    from pilot.config.toml_store import BenchTomlStore
    from pilot.core.bench import Bench
    from pilot.managers.mariadb_manager import MariaDBManager
    from pilot.managers.volume_manager import VolumeManager

    bench_config = BenchTomlStore.for_bench(bench_root).read()
    volume = VolumeManager(bench_config.volume)
    mariadb = MariaDBManager(bench_config.mariadb)
    bench = Bench(bench_config, bench_root)
    return SnapshotOrchestrator(volume, mariadb, bench)
