"""Contract test for the ads-b-surveillance leaf (DO-260B-style model).

Offline, deterministic, stdlib only. Run from the leaf directory:

    python3 scripts/test_ads_b_surveillance.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

import ads_b_surveillance_logic as adsb


class TestNicContainmentRadius(unittest.TestCase):
    """NIC to containment radius mapping."""

    def test_nic8_radius_exact_anchor(self):
        self.assertEqual(adsb.nic_containment_radius(8), 185.2)

    def test_nic_table_spot_checks(self):
        for nic, radius in [(11, 7.5), (10, 25.0), (9, 75.0), (7, 370.4),
                            (1, 37040.0)]:
            self.assertEqual(adsb.nic_containment_radius(nic), radius)

    def test_nic0_unknown_is_none(self):
        self.assertIsNone(adsb.nic_containment_radius(0))

    def test_nic_out_of_range_valueerror(self):
        for bad in (-1, 12, 99):
            with self.assertRaises(ValueError):
                adsb.nic_containment_radius(bad)

    def test_nic_rejects_non_integer(self):
        with self.assertRaises(ValueError):
            adsb.nic_containment_radius(8.0)


class TestNacpAccuracy(unittest.TestCase):
    """NACp to 95-percent horizontal accuracy bound mapping."""

    def test_nacp9_accuracy_exact_anchor(self):
        self.assertEqual(adsb.nacp_accuracy(9), 30.0)

    def test_nacp_table_spot_checks(self):
        for nacp, bound in [(11, 3.0), (10, 10.0), (8, 92.6), (5, 926.0),
                            (1, 18520.0)]:
            self.assertEqual(adsb.nacp_accuracy(nacp), bound)

    def test_nacp0_unknown_is_none(self):
        self.assertIsNone(adsb.nacp_accuracy(0))

    def test_nacp_out_of_range_valueerror(self):
        for bad in (-1, 12, 11.5):
            with self.assertRaises(ValueError):
                adsb.nacp_accuracy(bad)


class TestSilProbability(unittest.TestCase):
    """SIL to per-flight-hour integrity probability mapping."""

    def test_sil2_probability_exact_anchor(self):
        self.assertEqual(adsb.sil_probability(2), 1e-5)

    def test_sil_table_spot_checks(self):
        self.assertEqual(adsb.sil_probability(3), 1e-7)
        self.assertEqual(adsb.sil_probability(1), 1e-3)

    def test_sil0_unknown_is_none(self):
        self.assertIsNone(adsb.sil_probability(0))

    def test_sil_out_of_range_valueerror(self):
        for bad in (-1, 4, 2.0):
            with self.assertRaises(ValueError):
                adsb.sil_probability(bad)

    def test_sil3_stricter_than_sil2(self):
        self.assertLess(adsb.sil_probability(3), adsb.sil_probability(2))


class TestNicForRadius(unittest.TestCase):
    """Category selection for a required containment radius."""

    def test_exact_bound_selects_nic11(self):
        self.assertEqual(adsb.nic_for_radius(7.5), 11)

    def test_required_100m_selection(self):
        # NIC 9 (75 m) is too small and NIC 8 (185.2 m) covers 100 m,
        # so the tightest covering category is NIC 8.
        self.assertEqual(adsb.nic_for_radius(100.0), 8)

    def test_required_between_table_values(self):
        self.assertEqual(adsb.nic_for_radius(200.0), 7)
        self.assertEqual(adsb.nic_for_radius(400.0), 6)
        self.assertEqual(adsb.nic_for_radius(20000.0), 1)

    def test_uncoverable_requirement_returns_zero(self):
        self.assertEqual(adsb.nic_for_radius(1e6), 0)

    def test_nonpositive_required_radius_valueerror(self):
        for bad in (0.0, -1.0, -100.0):
            with self.assertRaises(ValueError):
                adsb.nic_for_radius(bad)


class TestNacpForAccuracy(unittest.TestCase):
    """Category selection for a required 95-percent accuracy."""

    def test_required_50m_selection_anchor(self):
        # NACp 9 (30 m) is too small and NACp 8 (92.6 m) covers 50 m.
        self.assertEqual(adsb.nacp_for_accuracy(50.0), 8)

    def test_exact_bound_selects_nacp11(self):
        self.assertEqual(adsb.nacp_for_accuracy(3.0), 11)

    def test_required_between_table_values(self):
        self.assertEqual(adsb.nacp_for_accuracy(100.0), 7)
        self.assertEqual(adsb.nacp_for_accuracy(300.0), 6)
        self.assertEqual(adsb.nacp_for_accuracy(500.0), 5)

    def test_uncoverable_requirement_returns_zero(self):
        self.assertEqual(adsb.nacp_for_accuracy(1e6), 0)

    def test_nonpositive_required_accuracy_valueerror(self):
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                adsb.nacp_for_accuracy(bad)


class TestAdsbRange(unittest.TestCase):
    """1090 MHz extended squitter radio line-of-sight range."""

    def test_range_workexample_bounds(self):
        # 10 000 ft own, 30 000 ft target: spec bound 600-650 km.
        r = adsb.adsb_range_km(10000, 30000)
        self.assertGreaterEqual(r, 600.0)
        self.assertLessEqual(r, 650.0)

    def test_range_workexample_value(self):
        # 4.12 * (sqrt(3048) + sqrt(9144)) = 621.43 km.
        self.assertAlmostEqual(adsb.adsb_range_km(10000, 30000),
                               621.4317938421485, places=6)

    def test_range_zero_zero_is_zero(self):
        self.assertEqual(adsb.adsb_range_km(0, 0), 0.0)

    def test_range_single_altitude(self):
        # 10 000 ft alone: 4.12 * sqrt(3048) = 227.46 km.
        self.assertAlmostEqual(adsb.adsb_range_km(10000),
                               227.45982326556046, places=6)
        self.assertAlmostEqual(adsb.adsb_range_km(0, 30000),
                               393.9719705765881, places=6)

    def test_range_negative_altitude_valueerror(self):
        for bad in (-1.0, -100.0):
            with self.assertRaises(ValueError):
                adsb.adsb_range_km(bad)
        with self.assertRaises(ValueError):
            adsb.adsb_range_km(10000, -1)


class TestAdsbAssessment(unittest.TestCase):
    """End-to-end surveillance assessment dict."""

    def test_assessment_workexample(self):
        out = adsb.adsb_assessment(8, 9, 2, 10000, 30000)
        self.assertEqual(set(out.keys()),
                         {"containment_radius_m", "accuracy_95_m",
                          "integrity_prob", "range_km"})
        self.assertEqual(out["containment_radius_m"], 185.2)
        self.assertEqual(out["accuracy_95_m"], 30.0)
        self.assertEqual(out["integrity_prob"], 1e-5)
        self.assertAlmostEqual(out["range_km"], 621.4317938421485,
                               places=6)

    def test_assessment_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            adsb.adsb_assessment(8, 9, 4, 10000, 30000)
        with self.assertRaises(ValueError):
            adsb.adsb_assessment(8, 9, 2, 10000, -500)

    def test_assessment_ground_station(self):
        # Ground ADS-B receiver at 0 ft own altitude, target at 30000 ft.
        out = adsb.adsb_assessment(8, 9, 3, 0, 30000)
        self.assertEqual(out["integrity_prob"], 1e-7)
        self.assertAlmostEqual(out["range_km"], 393.9719705765881,
                               places=6)


class TestDeterminism(unittest.TestCase):
    """Repeated calls return identical results."""

    def test_deterministic_range(self):
        self.assertEqual(adsb.adsb_range_km(10000, 30000),
                         adsb.adsb_range_km(10000, 30000))

    def test_deterministic_selection(self):
        self.assertEqual(adsb.nic_for_radius(1234.5),
                         adsb.nic_for_radius(1234.5))
        self.assertEqual(adsb.nacp_for_accuracy(1234.5),
                         adsb.nacp_for_accuracy(1234.5))


if __name__ == "__main__":
    unittest.main()
