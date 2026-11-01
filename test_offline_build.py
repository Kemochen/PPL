import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from ios.build_offline import python_bundle, verified_download
from ios.offline.engine import dispatch
import json


class OfflineBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_python_bundle_reuses_all_calculators_without_host_binaries(self):
        target = self.root / "engine.zip"
        versions = python_bundle(target)
        self.assertIn("flask", versions)
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
            for module in ("app.py", "takeoff.py", "landing.py", "cruise.py", "climb.py",
                           "weight_balance.py", "aircraft.py", "performance.py", "reference_1974.py", "offline_engine.py"):
                self.assertIn(module, names)
            self.assertTrue(any(name.startswith("flask/") for name in names))
            self.assertIn("markupsafe/_native.py", names)
            self.assertFalse(any(Path(name).suffix in (".so", ".pyd", ".dll", ".pyc") for name in names))

    def test_verified_cache_uses_no_network(self):
        target = self.root / "cached.bin"
        target.write_bytes(b"verified")
        with patch("ios.build_offline.urlopen") as download:
            self.assertEqual(verified_download("https://example.test/asset", target, hashlib.sha256(b"verified").digest()), b"verified")
        download.assert_not_called()

    def test_corrupt_download_is_rejected_and_not_cached(self):
        target = self.root / "cached.bin"
        with patch("ios.build_offline.urlopen", return_value=io.BytesIO(b"wrong")):
            with self.assertRaisesRegex(ValueError, "Integrity mismatch"):
                verified_download("https://example.test/asset", target, hashlib.sha256(b"right").digest())
        self.assertFalse(target.exists())

    def test_in_memory_dispatch_never_opens_a_socket(self):
        with patch("socket.socket", side_effect=AssertionError("Network is disabled")):
            result = json.loads(dispatch("/api/takeoff", "POST", json.dumps({
                "weight_lbs": "2300", "pressure_altitude_ft": "2000", "oat_c": "20"}), False))
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["body"]["result"]["ground_roll_ft"], 1000)
