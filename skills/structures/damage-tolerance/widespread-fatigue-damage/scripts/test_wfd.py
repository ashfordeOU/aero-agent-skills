#!/usr/bin/env python3
"""Gate 3 contract test: widespread fatigue damage screening logic.

Exercises scripts/wfd_logic.py (stdlib unittest, offline). Contract:
docs/harness-contract.md gate 3. Analytic checks on the MSD screen with
crack lengths [0.4, 1.1, 0.9, 1.3, 0.7, 1.2] mm and threshold 1.0 mm:
the sites strictly above 1.0 are 1.1, 1.3, 1.2, so sites_exceeding = 3
of 6 and the verdict is "susceptible" (3 >= 2). The clean set
[0.4, 0.9, 0.7, 0.6, 0.8] gives 0 exceeding and "not-susceptible".
Boundary: a site at exactly 1.0 is not counted (strictly greater), so
[1.0, 1.0, 0.9] stays not-susceptible while [1.0, 1.01, 1.02] flips to
susceptible with exactly 2 sites. classify_damage(3, 1) = "msd",
classify_damage(1, 3) = "med", classify_damage(3, 3) = "msd+med",
classify_damage(1, 1) = "none". supplemental_inspection_required is
True for baseline structure when the screen is susceptible or WFD
resistance is not shown, and False for non-baseline structure.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wfd_logic  # noqa: E402

THRESHOLD = 1.0  # mm


class ClassifyDamageTest(unittest.TestCase):
    def test_msd_from_sites(self):
        # 3 cracked fastener-hole sites, 1 cracked element: MSD only.
        self.assertEqual(wfd_logic.classify_damage(3, 1), "msd")

    def test_med_from_elements(self):
        # 1 cracked site, 3 cracked load-path elements: MED only.
        self.assertEqual(wfd_logic.classify_damage(1, 3), "med")

    def test_both_msd_and_med(self):
        self.assertEqual(wfd_logic.classify_damage(3, 3), "msd+med")
        self.assertEqual(wfd_logic.classify_damage(2, 2), "msd+med")

    def test_none(self):
        self.assertEqual(wfd_logic.classify_damage(1, 1), "none")
        self.assertEqual(wfd_logic.classify_damage(0, 0), "none")

    def test_med_at_zero_sites(self):
        self.assertEqual(wfd_logic.classify_damage(0, 2), "med")

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            wfd_logic.classify_damage(-1, 0)


class ScreenMsdTest(unittest.TestCase):
    def test_analytic_susceptible_screen(self):
        # Lengths above 1.0 mm: 1.1, 1.3, 1.2 -> 3 of 6 sites.
        report = wfd_logic.screen_msd([0.4, 1.1, 0.9, 1.3, 0.7, 1.2], THRESHOLD)
        self.assertEqual(report["total_sites"], 6)
        self.assertEqual(report["sites_exceeding"], 3)
        self.assertEqual(report["threshold"], 1.0)
        self.assertEqual(report["verdict"], "susceptible")

    def test_clean_site_set_not_susceptible(self):
        # No site above 1.0 mm: 0 exceeding of 5.
        report = wfd_logic.screen_msd([0.4, 0.9, 0.7, 0.6, 0.8], THRESHOLD)
        self.assertEqual(report["total_sites"], 5)
        self.assertEqual(report["sites_exceeding"], 0)
        self.assertEqual(report["verdict"], "not-susceptible")

    def test_exact_boundary_not_counted(self):
        # Sites exactly at the threshold are not counted (strictly greater).
        report = wfd_logic.screen_msd([1.0, 1.0, 0.9], THRESHOLD)
        self.assertEqual(report["sites_exceeding"], 0)
        self.assertEqual(report["verdict"], "not-susceptible")

    def test_two_site_minimum_flips_verdict(self):
        # Exactly 2 sites above the threshold: susceptible.
        report = wfd_logic.screen_msd([1.0, 1.01, 1.02], THRESHOLD)
        self.assertEqual(report["sites_exceeding"], 2)
        self.assertEqual(report["verdict"], "susceptible")
        # One site above the threshold is not a population: not susceptible.
        report = wfd_logic.screen_msd([1.0, 1.0001, 0.9], THRESHOLD)
        self.assertEqual(report["sites_exceeding"], 1)
        self.assertEqual(report["verdict"], "not-susceptible")

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            wfd_logic.screen_msd([0.5], 0.0)

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            wfd_logic.screen_msd([-0.2, 1.1], THRESHOLD)


class SupplementalInspectionTest(unittest.TestCase):
    def test_susceptible_baseline_requires_inspection(self):
        self.assertTrue(
            wfd_logic.supplemental_inspection_required("susceptible", True, False)
        )
        self.assertTrue(
            wfd_logic.supplemental_inspection_required("susceptible", True, True)
        )

    def test_baseline_without_shown_resistance_requires_inspection(self):
        # Not susceptible but WFD resistance not shown for the design.
        self.assertTrue(
            wfd_logic.supplemental_inspection_required("not-susceptible", True, False)
        )

    def test_clean_baseline_with_resistance_needs_no_inspection(self):
        self.assertFalse(
            wfd_logic.supplemental_inspection_required("not-susceptible", True, True)
        )

    def test_non_baseline_never_requires_inspection(self):
        self.assertFalse(
            wfd_logic.supplemental_inspection_required("susceptible", False, False)
        )


class WfdScreenReportTest(unittest.TestCase):
    def test_analytic_report_msd_case(self):
        # 6 sites, 3 above 1.0 mm, 1 cracked element: msd, susceptible,
        # baseline without shown resistance -> supplemental inspection.
        report = wfd_logic.wfd_screen_report(
            [0.4, 1.1, 0.9, 1.3, 0.7, 1.2], 1, THRESHOLD, True, False
        )
        self.assertEqual(
            set(report.keys()),
            {
                "classification",
                "site_cracks",
                "element_cracks",
                "sites_exceeding",
                "verdict",
                "supplemental_inspection_required",
            },
        )
        self.assertEqual(report["classification"], "msd")
        self.assertEqual(report["site_cracks"], 6)
        self.assertEqual(report["element_cracks"], 1)
        self.assertEqual(report["sites_exceeding"], 3)
        self.assertEqual(report["verdict"], "susceptible")
        self.assertTrue(report["supplemental_inspection_required"])

    def test_analytic_report_med_case(self):
        # 1 cracked site, 2 cracked elements, 0 above threshold, baseline
        # with WFD resistance shown: med, not susceptible, no inspection.
        report = wfd_logic.wfd_screen_report(
            [0.9], 2, THRESHOLD, True, True
        )
        self.assertEqual(report["classification"], "med")
        self.assertEqual(report["site_cracks"], 1)
        self.assertEqual(report["element_cracks"], 2)
        self.assertEqual(report["sites_exceeding"], 0)
        self.assertEqual(report["verdict"], "not-susceptible")
        self.assertFalse(report["supplemental_inspection_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
