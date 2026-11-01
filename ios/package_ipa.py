"""Package our unsigned arm64 device build for re-signing with AltStore Classic."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import struct
import tempfile
import zipfile


def validate_app(app):
    app = Path(app).resolve()
    if not app.is_dir() or app.suffix != ".app":
        raise ValueError("Expected an existing .app directory")
    with (app / "Info.plist").open("rb") as handle:
        info = plistlib.load(handle)
    if info.get("CFBundlePackageType") != "APPL":
        raise ValueError("Bundle is not an iOS application")
    if "iPhoneOS" not in info.get("CFBundleSupportedPlatforms", []):
        raise ValueError("Simulator builds cannot be installed with AltStore")
    if not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", info.get("CFBundleIdentifier", "")):
        raise ValueError("Missing or invalid bundle identifier")
    executable = info.get("CFBundleExecutable", "")
    if not executable or executable in (".", "..") or "/" in executable or "\\" in executable:
        raise ValueError("Invalid executable name")
    for path in app.rglob("*"):
        if path.is_symlink():
            raise ValueError("Unexpected symlink in application bundle")
    binary = (app / executable).read_bytes()
    if len(binary) < 32:
        raise ValueError("Missing or truncated Mach-O executable")
    magic, cpu, _, filetype, count, size, _, _ = struct.unpack_from("<8I", binary)
    if (magic, cpu, filetype) != (0xFEEDFACF, 0x0100000C, 2):
        raise ValueError("Expected a thin arm64 Mach-O device executable")
    if 32 + size > len(binary) or count > size // 8:
        raise ValueError("Invalid Mach-O command header")
    offset = 32
    device = False
    for _ in range(count):
        if offset + 8 > 32 + size:
            raise ValueError("Truncated Mach-O command")
        command, length = struct.unpack_from("<2I", binary, offset)
        if length < 8 or offset + length > 32 + size:
            raise ValueError("Invalid Mach-O command size")
        if command == 0x32:  # LC_BUILD_VERSION: arm64 simulators also use Mach-O.
            if length < 24 or struct.unpack_from("<I", binary, offset + 8)[0] != 2:
                raise ValueError("Mach-O was not built for an iOS device")
            device = True
        if command == 0x2C:  # LC_ENCRYPTION_INFO_64
            if length < 24 or struct.unpack_from("<I", binary, offset + 16)[0] != 0:
                raise ValueError("Encrypted executables cannot be re-signed")
        offset += length
    if not device:
        raise ValueError("Missing iOS device build command")
    if info.get("PPLNative") is True:
        if not (app / "NativeData.json").is_file():
            raise ValueError("Native POH data is missing")
        if any(path.suffix in (".py", ".pyc", ".wasm", ".whl", ".html", ".js") for path in app.rglob("*")):
            raise ValueError("Native app unexpectedly contains a Python / Web runtime")
    elif info.get("PPLOffline") is True:
        for resource in ("index.html", "bootstrap.js", "engine.zip", "manifest.json", "static/styles.css",
                         "static/platform.js", "static/performance.js", "static/aircraft.js",
                         "runtime/pyodide.js", "runtime/pyodide.asm.js", "runtime/pyodide.asm.wasm",
                         "runtime/python_stdlib.zip", "runtime/pyodide-lock.json"):
            if not (app / "BundledWeb" / resource).is_file():
                raise ValueError("Offline resource missing: " + resource)
        manifest = json.loads((app / "BundledWeb/manifest.json").read_text(encoding="utf-8"))
        if manifest.get("network_required") is not False or not list((app / "BundledWeb/runtime").glob("numpy-*.whl")):
            raise ValueError("Offline runtime or bundled NumPy is missing")
    return info


def package_app(app, output):
    app, output = Path(app).resolve(), Path(output).resolve()
    info = validate_app(app)
    if output.is_relative_to(app):
        raise ValueError("Output must be outside the application bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(app.rglob("*")):
                if path.is_file():
                    archive.write(path, "Payload/" + app.name + "/" + path.relative_to(app).as_posix())
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("IPA failed CRC verification")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".ipa.sha256").write_text(f"{digest}  {output.name}\n", encoding="ascii")
    return {"file": output.name, "bundle_id": info["CFBundleIdentifier"],
            "version": info.get("CFBundleShortVersionString"), "build": info.get("CFBundleVersion"),
            "minimum_ios": info.get("MinimumOSVersion"), "sha256": digest,
            "offline": info.get("PPLOffline", False),
            "native_swift": info.get("PPLNative", False),
            "signing": "Unsigned; re-sign using AltStore Classic before installation"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(package_app(args.app, args.output), indent=2))
