import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault(
    "CREDENTIALS_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)
os.environ.setdefault("ADMIN_PASSWORD_HASH", "test-password-hash")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'host_dashboard_test.db')}",
)

from app.models import HostConfig, ImageUpdateCache
from app.schemas import DockerDiskUsage, UpdateCheckResult
from app.services.snapshot import HostSnapshot, SnapshotManager





class SnapshotManagerTests(unittest.TestCase):
    def test_update_check_results_are_read_from_snapshot_cache(self):
        manager = SnapshotManager()
        snap = HostSnapshot()
        snap.update_check_results = [
            UpdateCheckResult(
                host_id="host-a",
                image="nginx:latest",
                status="updatable",
            )
        ]
        manager._snapshots = {"host-a": snap}

        results = manager.get_update_check_results()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].image, "nginx:latest")

    def test_host_summary_uses_local_image_list_count(self):
        manager = SnapshotManager()
        snap = HostSnapshot()
        snap.host_config = HostConfig(
            host_id="host-a",
            display_name="Host A",
            enabled=True,
            agent_url="http://localhost:8080",
        )
        snap.status = "online"
        snap.image_count = 7
        snap.docker_disk = DockerDiskUsage(images_total=39)

        summary = manager.build_host_summary(snap)

        self.assertEqual(summary.image_count, 7)

    def test_failed_update_cache_rows_are_hidden_from_snapshot(self):
        manager = SnapshotManager()
        snap = HostSnapshot()
        rows = [
            ImageUpdateCache(
                host_id="host-a",
                image="nginx:latest",
                status="check_failed",
                checked_at=datetime.now(timezone.utc),
            )
        ]

        manager._apply_update_cache_rows_to_snapshot(snap, rows)

        self.assertEqual(snap.update_check_results, [])
        self.assertEqual(snap.update_count, 0)

    def test_failed_update_check_does_not_overwrite_visible_cache(self):
        manager = SnapshotManager()
        existing = ImageUpdateCache(
            host_id="host-a",
            image="nginx:latest",
            status="updatable",
            current_digest="sha256:old",
            registry_digest="sha256:new",
            checked_at=datetime.now(timezone.utc),
        )
        result = UpdateCheckResult(
            host_id="host-a",
            image="nginx:latest",
            status="check_failed",
        )

        manager._persist_update_check_result(
            MagicMock(),
            "host-a",
            result,
            existing,
            datetime.now(timezone.utc),
        )

        self.assertEqual(existing.status, "updatable")
        self.assertEqual(existing.current_digest, "sha256:old")
        self.assertEqual(existing.registry_digest, "sha256:new")
        self.assertEqual(existing.failure_count, 1)
        self.assertEqual(existing.last_failure_status, "check_failed")


if __name__ == "__main__":
    unittest.main()
