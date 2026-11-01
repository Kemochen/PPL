"""Select a known-compatible WebKit test runtime, never the first arbitrary device."""
import json
import os
import subprocess

RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-26-2"


def select_device(devices):
    phones = [device for device in devices.get(RUNTIME, [])
              if device.get("isAvailable", True) and device["name"].startswith("iPhone")]
    if not phones:
        raise ValueError("An available iOS 26.2 iPhone simulator is required for the iOS 26+ app; refusing to silently use an older runtime.")
    return min(phones, key=lambda device: ("Pro Max" not in device["name"], "Pro" not in device["name"], device["name"]))


if __name__ == "__main__":
    result = subprocess.run(["xcrun", "simctl", "list", "devices", "available", "-j"],
                            check=True, capture_output=True, text=True)
    device = select_device(json.loads(result.stdout)["devices"])
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as handle:
        handle.write("SIMULATOR_ID=" + device["udid"] + "\n")
    print(f"Native offline tests: {device['name']} / iOS 26.2 / {device['udid']}")
