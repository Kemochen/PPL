"""Packaging tests use synthetic headers only, never a distributable app."""
import hashlib
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
import zipfile

from ios.package_ipa import package_app, validate_app


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "PPL.app"
        self.app.mkdir()
        self.info = dict(CFBundlePackageType="APPL", CFBundleSupportedPlatforms=["iPhoneOS"],
                         CFBundleIdentifier="com.pplcalculator.mobile", CFBundleExecutable="PPL",
                         MinimumOSVersion="15.0", CFBundleVersion="1", CFBundleShortVersionString="0.1.0")
        self.save_info()
        self.binary()

    def save_info(self):
        with (self.app / "Info.plist").open("wb") as handle:
            plistlib.dump(self.info, handle)

    def binary(self, platform=2, cpu=0x0100000C):
        command = struct.pack("<6I", 0x32, 24, platform, 15 << 16, 18 << 16, 0)
        (self.app / "PPL").write_bytes(struct.pack("<8I", 0xFEEDFACF, cpu, 0, 2, 1, len(command), 0, 0) + command)
        (self.app / "PPL").chmod(0o755)

    def test_payload_and_checksum(self):
        output = self.root / "PPL-AltStore.ipa"
        result = package_app(self.app, output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), {"Payload/PPL.app/Info.plist", "Payload/PPL.app/PPL"})
            self.assertIsNone(archive.testzip())
        self.assertEqual(result["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertIn(result["sha256"], output.with_suffix(".ipa.sha256").read_text())

    def test_simulator_plist_rejected(self):
        self.info["CFBundleSupportedPlatforms"] = ["iPhoneSimulator"]
        self.save_info()
        with self.assertRaisesRegex(ValueError, "Simulator"):
            validate_app(self.app)

    def test_offline_app_without_its_resources_is_rejected(self):
        self.info["PPLOffline"] = True
        self.save_info()
        with self.assertRaisesRegex(ValueError, "Offline resource missing"):
            validate_app(self.app)

    def test_native_app_requires_data_and_rejects_runtime_files(self):
        self.info["PPLNative"] = True
        self.info["PPLOffline"] = True
        self.save_info()
        with self.assertRaisesRegex(ValueError, "Native POH data"):
            validate_app(self.app)
        (self.app / "NativeData.json").write_text("{}")
        validate_app(self.app)
        (self.app / "legacy.wasm").write_bytes(b"not allowed")
        with self.assertRaisesRegex(ValueError, "runtime"):
            validate_app(self.app)

    def test_arm64_simulator_binary_rejected(self):
        self.binary(platform=7)
        with self.assertRaisesRegex(ValueError, "iOS device"):
            validate_app(self.app)

    def test_wrong_cpu_rejected(self):
        self.binary(cpu=0x01000007)
        with self.assertRaisesRegex(ValueError, "arm64"):
            validate_app(self.app)

    def test_missing_or_truncated_binary_rejected(self):
        (self.app / "PPL").write_bytes(b"not a binary")
        with self.assertRaisesRegex(ValueError, "truncated"):
            validate_app(self.app)

    def test_executable_traversal_rejected(self):
        self.info["CFBundleExecutable"] = "../outside"
        self.save_info()
        with self.assertRaisesRegex(ValueError, "executable name"):
            validate_app(self.app)

    def test_output_inside_bundle_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            package_app(self.app, self.app / "invalid.ipa")

    def test_repeat_build_replaces_old_files(self):
        output = self.root / "PPL-AltStore.ipa"
        (self.app / "obsolete.txt").write_text("old")
        package_app(self.app, output)
        (self.app / "obsolete.txt").unlink()
        package_app(self.app, output)
        with zipfile.ZipFile(output) as archive:
            self.assertNotIn("Payload/PPL.app/obsolete.txt", archive.namelist())


if __name__ == "__main__":
    unittest.main()
