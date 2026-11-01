import unittest
from ios.select_simulator import RUNTIME, select_device


class SimulatorSelectionTests(unittest.TestCase):
    def test_avoids_broken_runtime_even_when_listed_first(self):
        devices = {"com.apple.CoreSimulator.SimRuntime.iOS-18-5": [{"name": "iPhone 16", "udid": "broken"}],
                   RUNTIME: [{"name": "iPhone 16", "udid": "good"}]}
        self.assertEqual(select_device(devices)["udid"], "good")

    def test_prefers_small_screen_phone(self):
        devices = {RUNTIME: [{"name": "iPhone 16 Pro Max", "udid": "large"},
                             {"name": "iPhone SE (3rd generation)", "udid": "small"}]}
        self.assertEqual(select_device(devices)["udid"], "small")

    def test_no_silent_fallback_to_other_runtimes(self):
        for devices in ({}, {"com.apple.CoreSimulator.SimRuntime.iOS-18-5": [{"name": "iPhone 16"}]},
                        {RUNTIME: [{"name": "iPhone 16", "isAvailable": False}]},
                        {RUNTIME: [{"name": "iPad mini"}]}):
            with self.subTest(devices=devices), self.assertRaisesRegex(ValueError, "18.6"):
                select_device(devices)
