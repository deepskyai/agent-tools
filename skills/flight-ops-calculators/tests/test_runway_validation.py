#!/usr/bin/env python3
"""Regression tests for runway-designator validation."""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(HERE, os.pardir, "scripts", "wind_components.py")
MODULE_SPEC = importlib.util.spec_from_file_location("wind_components", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("Cannot load wind_components.py")
wind_components = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(wind_components)


class RunwayValidationTests(unittest.TestCase):
    def test_valid_designators_and_headings(self):
        self.assertEqual(wind_components.parse_runway("09L"), 90.0)
        self.assertEqual(wind_components.parse_runway("36"), 0.0)
        self.assertEqual(wind_components.parse_runway("273.4"), 273.4)
        self.assertEqual(wind_components.parse_runway("360"), 0.0)

    def test_rejects_suffix_on_non_designator(self):
        for token in ("00L", "37R", "09.5C", "273R"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ValueError, "Invalid runway designator"):
                    wind_components.parse_runway(token)

    def test_rejects_heading_outside_compass_range(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 360"):
            wind_components.parse_runway("361")


if __name__ == "__main__":
    unittest.main()
