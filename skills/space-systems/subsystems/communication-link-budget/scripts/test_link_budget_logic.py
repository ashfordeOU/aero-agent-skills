"""Contract tests for link_budget_logic.py (gate 3, stdlib unittest, offline).

Covers the happy path, boundary values, invalid-input ValueError raises,
and physically meaningful checks: the known GEO path loss of about
201.5 dB at 8 GHz and 35786 km, and a full end-to-end geostationary
link that must close with a positive margin.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import link_budget_logic as lb


class TestFreeSpacePathLoss(unittest.TestCase):
    def test_known_geo_value(self):
        # d = 35786 km, f = 8 GHz: L_fs ~ 201.5 dB (textbook GEO check).
        loss = lb.free_space_path_loss(35786e3, 8e9)
        self.assertAlmostEqual(loss, 201.5, delta=0.6)

    def test_doubling_distance_adds_6_dB(self):
        l1 = lb.free_space_path_loss(1000.0, 1e9)
        l2 = lb.free_space_path_loss(2000.0, 1e9)
        self.assertAlmostEqual(l2 - l1, 20.0 * math.log10(2.0), delta=1e-9)

    def test_doubling_frequency_adds_6_dB(self):
        l1 = lb.free_space_path_loss(1000.0, 1e9)
        l2 = lb.free_space_path_loss(1000.0, 2e9)
        self.assertAlmostEqual(l2 - l1, 20.0 * math.log10(2.0), delta=1e-9)

    def test_small_positive_values_ok(self):
        # Boundary: d = 1 m, f = 1 GHz is far-field (lambda ~ 0.3 m),
        # so the formula yields a positive loss and does not raise.
        loss = lb.free_space_path_loss(1.0, 1e9)
        self.assertGreater(loss, 0.0)
        self.assertAlmostEqual(loss, 20.0 * math.log10(4.0 * math.pi / 0.299792458), delta=1e-6)

    def test_invalid_distance_raises(self):
        for bad in (0.0, -10.0):
            with self.assertRaises(ValueError):
                lb.free_space_path_loss(bad, 1e9)

    def test_invalid_frequency_raises(self):
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                lb.free_space_path_loss(1000.0, bad)


class TestEirpAndReceivedPower(unittest.TestCase):
    def test_eirp_is_power_plus_gain(self):
        self.assertAlmostEqual(lb.eirp_dbw(10.0, 40.0), 50.0, delta=1e-9)

    def test_received_power_default_other_losses(self):
        # Pr = 40 + 20 - 200 = -140 dBW with no other losses.
        self.assertAlmostEqual(
            lb.received_power_dbw(40.0, 20.0, 200.0), -140.0, delta=1e-9
        )

    def test_received_power_with_other_losses(self):
        # Pr = 40 + 20 - 200 - 2 = -142 dBW.
        self.assertAlmostEqual(
            lb.received_power_dbw(40.0, 20.0, 200.0, other_losses_db=2.0),
            -142.0,
            delta=1e-9,
        )

    def test_gain_adds_and_losses_subtract(self):
        self.assertAlmostEqual(
            lb.received_power_dbw(50.0, 30.0, 205.1, other_losses_db=1.5),
            50.0 + 30.0 - 205.1 - 1.5,
            delta=1e-9,
        )


class TestCarrierToNoise(unittest.TestCase):
    def test_known_value_at_300_k(self):
        # Pr = -130 dBW, T = 300 K: C/N0 = -130 + 228.6 - 10*log10(300)
        # ~ 73.83 dB-Hz.
        self.assertAlmostEqual(lb.cno_db_hz(-130.0, 300.0), 73.83, delta=0.05)

    def test_noise_temperature_doubling_costs_3_dB(self):
        c1 = lb.cno_db_hz(-120.0, 100.0)
        c2 = lb.cno_db_hz(-120.0, 200.0)
        self.assertAlmostEqual(c1 - c2, 10.0 * math.log10(2.0), delta=1e-9)

    def test_invalid_temperature_raises(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                lb.cno_db_hz(-120.0, bad)


class TestLinkMargin(unittest.TestCase):
    def test_margin_ok_when_above_requirement(self):
        # C/N0 ~ 73.83 dB-Hz, R = 1e6 bps: Eb/N0 ~ 13.83 dB; required 9.6 dB
        # leaves a positive margin.
        result = lb.link_margin(73.83, 1e6, 9.6)
        self.assertAlmostEqual(result["ebno_db"], 73.83 - 60.0, delta=0.05)
        self.assertGreater(result["margin_db"], 3.0)
        self.assertLess(result["margin_db"], 5.0)
        self.assertTrue(result["ok"])

    def test_margin_fails_when_below_requirement(self):
        result = lb.link_margin(73.83, 1e6, 20.0)
        self.assertLess(result["margin_db"], 0.0)
        self.assertFalse(result["ok"])

    def test_exact_threshold_is_ok(self):
        # Margin exactly 0.0 dB counts as ok (>= 0).
        result = lb.link_margin(70.0, 1e6, 10.0)
        self.assertAlmostEqual(result["margin_db"], 0.0, delta=1e-9)
        self.assertTrue(result["ok"])

    def test_invalid_data_rate_raises(self):
        for bad in (0.0, -1000.0):
            with self.assertRaises(ValueError):
                lb.link_margin(70.0, bad, 10.0)


class TestEndToEndGeoLink(unittest.TestCase):
    def test_geostationary_link_closes(self):
        # 10 W transmitter (10 dBW), 40 dB antenna gain, GEO slant range
        # 35786 km at 12 GHz, 30 dB receive gain, 300 K system noise
        # temperature, 2 Mbps data rate, 12 dB required Eb/N0. A healthy
        # GEO downlink must close with a clear positive margin.
        eirp = lb.eirp_dbw(10.0, 40.0)
        pl = lb.free_space_path_loss(35786e3, 12e9)
        pr = lb.received_power_dbw(eirp, 30.0, pl)
        cno = lb.cno_db_hz(pr, 300.0)
        result = lb.link_margin(cno, 2e6, 12.0)
        # Received power at GEO is far below 0 dBW...
        self.assertLess(pr, -100.0)
        # ...yet the link closes with a positive margin.
        self.assertGreater(result["margin_db"], 3.0)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
