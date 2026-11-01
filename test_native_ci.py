import unittest
from ios.select_simulator import RUNTIME, select_device


class SimulatorSelectionTests(unittest.TestCase):
    def test_avoids_broken_runtime_even_when_listed_first(self):
        devices = {"com.apple.CoreSimulator.SimRuntime.iOS-18-5": [{"name": "iPhone 16", "udid": "broken"}],
                   RUNTIME: [{"name": "iPhone 16", "udid": "good"}]}
        self.assertEqual(select_device(devices)["udid"], "good")

    def test_prefers_pro_max_without_requiring_se(self):
        devices = {RUNTIME: [{"name": "iPhone 17 Pro Max", "udid": "max"},
                             {"name": "iPhone 17 Pro", "udid": "pro"},
                             {"name": "iPhone SE (3rd generation)", "udid": "small"}]}
        self.assertEqual(select_device(devices)["udid"], "max")

    def test_pro_and_regular_iphone_remain_valid(self):
        for name in ("iPhone 17 Pro", "iPhone 17"):
            self.assertEqual(select_device({RUNTIME: [{"name": name, "udid": "phone"}]})["udid"], "phone")

    def test_no_silent_fallback_to_other_runtimes(self):
        for devices in ({}, {"com.apple.CoreSimulator.SimRuntime.iOS-18-5": [{"name": "iPhone 16"}]},
                        {RUNTIME: [{"name": "iPhone 16", "isAvailable": False}]},
                        {RUNTIME: [{"name": "iPad mini"}]}):
            with self.subTest(devices=devices), self.assertRaisesRegex(ValueError, "26.2"):
                select_device(devices)
