"""Select a known-compatible WebKit test runtime, never the first arbitrary device."""
import json
import os
import subprocess

RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-18-6"


def select_device(devices):
    phones = [device for device in devices.get(RUNTIME, [])
              if device.get("isAvailable", True) and device["name"].startswith("iPhone")]
    if not phones:
        raise ValueError("An available iOS 18.6 iPhone simulator is required. iOS 18.5 has a known WebKit overlay loading bug; refusing to silently use it.")
    return min(phones, key=lambda device: ("SE" not in device["name"], device["name"]))


if __name__ == "__main__":
    result = subprocess.run(["xcrun", "simctl", "list", "devices", "available", "-j"],
                            check=True, capture_output=True, text=True)
    device = select_device(json.loads(result.stdout)["devices"])
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as handle:
        handle.write("SIMULATOR_ID=" + device["udid"] + "\n")
    print(f"Native offline tests: {device['name']} / iOS 18.6 / {device['udid']}")
