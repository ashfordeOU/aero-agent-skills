#!/usr/bin/env python3
"""Gate 3 contract test: DO-160 radio frequency emissions.

Exercises scripts/radio_frequency_emissions_logic.py (stdlib unittest,
offline). Contract: DO-160 section 21 emission side (CE102 conducted and
RE102 radiated): dBuV and dBuV/m conversions, the reference-only typical
limit curves, emission margin at each frequency, worst case frequency,
the pass or fail verdict, and the ERP far-field sanity check; invalid
inputs raise ValueError.

Anchors:
- dbu_v_from_volts(1.0) = 120 dBuV; volts_from_dbu_v(120.0) = 1 V
- dbu_v_per_m_from_v_per_m(1.0) = 120 dBuV/m
- ce102_limit_db(150e3, 'A') = 60 dBuV (reference-only typical curve)
- re102_limit_db(100e6, 'A') = 24 dBuV/m (reference-only typical floor)
- worked example: measured 72 dBuV at 150 kHz gives margin -12 dB
  (fail); measured 40 dBuV/m at 100 MHz gives margin -16 dB (fail)
- worst_case_frequency((50e3, 150e3, 5e6), (18, -12, 2)) -> 150 kHz,
  -12 dB
- field_strength_from_erp(100, 10) = sqrt(30) V/m, 134.7712 dBuV/m
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import radio_frequency_emissions_logic as rfe  # noqa: E402


class TestConductedEmissionConversions(unittest.TestCase):
    """Volts to dBuV and back (CE102 measurement amplitude scaling)."""

    def test_one_volt_is_120_dbu_v(self):
        self.assertAlmostEqual(rfe.dbu_v_from_volts(1.0), 120.0, places=9)

    def test_milli_and_microvolt_anchors(self):
        self.assertAlmostEqual(rfe.dbu_v_from_volts(1e-3), 60.0, places=9)
        self.assertAlmostEqual(rfe.dbu_v_from_volts(1e-6), 0.0, places=9)

    def test_dbu_v_to_volts_anchor(self):
        self.assertAlmostEqual(rfe.volts_from_dbu_v(120.0), 1.0, places=12)
        self.assertAlmostEqual(rfe.volts_from_dbu_v(0.0), 1e-6, places=12)
        self.assertAlmostEqual(rfe.volts_from_dbu_v(-20.0), 1e-7, places=12)

    def test_volts_dbu_v_round_trip(self):
        for volts in (0.25, 2.0, 37.5):
            self.assertAlmostEqual(
                rfe.volts_from_dbu_v(rfe.dbu_v_from_volts(volts)),
                volts,
                places=9,
            )

    def test_dbu_v_from_volts_rejects_negative_and_zero(self):
        with self.assertRaises(ValueError):
            rfe.dbu_v_from_volts(-1e-3)
        with self.assertRaises(ValueError):
            rfe.dbu_v_from_volts(0.0)


class TestRadiatedFieldConversions(unittest.TestCase):
    """Field strength V/m to dBuV/m (RE102 antenna measurement scaling)."""

    def test_one_vpm_is_120_dbu_vpm(self):
        self.assertAlmostEqual(rfe.dbu_v_per_m_from_v_per_m(1.0), 120.0, places=9)
        self.assertAlmostEqual(rfe.dbu_v_per_m_from_v_per_m(1e-6), 0.0, places=9)

    def test_vpm_conversion_rejects_negative_and_zero(self):
        with self.assertRaises(ValueError):
            rfe.dbu_v_per_m_from_v_per_m(-2.0)
        with self.assertRaises(ValueError):
            rfe.dbu_v_per_m_from_v_per_m(0.0)


class TestCe102Limits(unittest.TestCase):
    """Reference-only typical CE102 band curve, 10 kHz to 10 MHz."""

    def test_ce102_band_values(self):
        self.assertAlmostEqual(rfe.ce102_limit_db(50e3, "A"), 78.0, places=9)
        self.assertAlmostEqual(rfe.ce102_limit_db(150e3, "A"), 60.0, places=9)
        self.assertAlmostEqual(rfe.ce102_limit_db(5e6, "A"), 70.0, places=9)

    def test_ce102_band_edges(self):
        self.assertAlmostEqual(rfe.ce102_limit_db(10e3, "B"), 78.0, places=9)
        self.assertAlmostEqual(rfe.ce102_limit_db(100e3, "B"), 60.0, places=9)
        self.assertAlmostEqual(rfe.ce102_limit_db(2e6, "B"), 70.0, places=9)
        self.assertAlmostEqual(rfe.ce102_limit_db(10e6, "B"), 70.0, places=9)

    def test_ce102_out_of_band_raises(self):
        with self.assertRaises(ValueError):
            rfe.ce102_limit_db(5e3, "A")
        with self.assertRaises(ValueError):
            rfe.ce102_limit_db(20e6, "A")

    def test_ce102_unsupported_category_raises(self):
        with self.assertRaises(ValueError):
            rfe.ce102_limit_db(150e3, "D")
        with self.assertRaises(ValueError):
            rfe.ce102_limit_db(150e3, "x")

    def test_ce102_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            rfe.ce102_limit_db(-1.0, "A")
        with self.assertRaises(ValueError):
            rfe.ce102_limit_db(0.0, "A")


class TestRe102Limits(unittest.TestCase):
    """Reference-only typical RE102 category floors, 2 MHz to 18 GHz."""

    def test_re102_category_floors(self):
        self.assertAlmostEqual(rfe.re102_limit_db(100e6, "A"), 24.0, places=9)
        self.assertAlmostEqual(rfe.re102_limit_db(100e6, "B"), 34.0, places=9)
        self.assertAlmostEqual(rfe.re102_limit_db(100e6, "C"), 44.0, places=9)

    def test_re102_band_edges_accepted(self):
        self.assertAlmostEqual(rfe.re102_limit_db(2e6, "A"), 24.0, places=9)
        self.assertAlmostEqual(rfe.re102_limit_db(18e9, "A"), 24.0, places=9)

    def test_re102_out_of_band_raises(self):
        with self.assertRaises(ValueError):
            rfe.re102_limit_db(1e6, "A")
        with self.assertRaises(ValueError):
            rfe.re102_limit_db(2e10, "A")

    def test_re102_bad_category_and_negative_freq_raise(self):
        with self.assertRaises(ValueError):
            rfe.re102_limit_db(100e6, "H")
        with self.assertRaises(ValueError):
            rfe.re102_limit_db(-5e6, "A")


class TestEmissionMargins(unittest.TestCase):
    """margin_db = limit_db - measured_db, negative margin is a fail."""

    def test_conducted_margin_pass(self):
        self.assertAlmostEqual(
            rfe.conducted_emission_margin(50.0, 60.0), 10.0, places=9
        )

    def test_conducted_margin_worked_example(self):
        # Measured 72 dBuV at 150 kHz against the CE102 limit 60 dBuV.
        limit = rfe.ce102_limit_db(150e3, "A")
        self.assertAlmostEqual(limit, 60.0, places=9)
        self.assertAlmostEqual(
            rfe.conducted_emission_margin(72.0, limit), -12.0, places=9
        )

    def test_radiated_margin_worked_example(self):
        # Measured 40 dBuV/m at 100 MHz against the RE102 category A
        # floor 24 dBuV/m, and a passing 20 dBuV/m measurement.
        limit = rfe.re102_limit_db(100e6, "A")
        self.assertAlmostEqual(limit, 24.0, places=9)
        self.assertAlmostEqual(
            rfe.radiated_emission_margin(40.0, limit), -16.0, places=9
        )
        self.assertAlmostEqual(
            rfe.radiated_emission_margin(20.0, limit), 4.0, places=9
        )

    def test_margin_functions_agree_when_units_align(self):
        # Both margins are plain dB differences, so numerically equal
        # inputs give equal margins on the conducted and radiated sides.
        self.assertAlmostEqual(
            rfe.conducted_emission_margin(72.0, 60.0),
            rfe.radiated_emission_margin(72.0, 60.0),
            places=9,
        )


class TestWorstCaseFrequency(unittest.TestCase):
    """Frequency of the minimum emission margin over a sweep."""

    def test_worst_case_picks_minimum_margin(self):
        freqs = (50e3, 150e3, 5e6)
        margins = (18.0, -12.0, 2.0)
        freq, margin = rfe.worst_case_frequency(freqs, margins)
        self.assertEqual(freq, 150e3)
        self.assertAlmostEqual(margin, -12.0, places=9)

    def test_worst_case_tie_resolves_first(self):
        freq, margin = rfe.worst_case_frequency((1e6, 2e6, 3e6), (-5.0, -5.0, 0.0))
        self.assertEqual(freq, 1e6)
        self.assertAlmostEqual(margin, -5.0, places=9)

    def test_worst_case_rejects_empty_and_mismatched(self):
        with self.assertRaises(ValueError):
            rfe.worst_case_frequency([], [])
        with self.assertRaises(ValueError):
            rfe.worst_case_frequency((50e3, 150e3), (18.0,))

    def test_worst_case_rejects_non_positive_frequency(self):
        with self.assertRaises(ValueError):
            rfe.worst_case_frequency((-50e3, 150e3), (10.0, -12.0))
        with self.assertRaises(ValueError):
            rfe.worst_case_frequency((0.0, 150e3), (10.0, -12.0))


class TestEmissionVerdict(unittest.TestCase):
    """Pass or fail verdict dict from margins, frequencies, kind."""

    def test_verdict_single_point_pass(self):
        verdict = rfe.emission_verdict(10.0, 150e3, "A", "conducted")
        self.assertTrue(verdict["pass"])
        self.assertAlmostEqual(verdict["worst_margin_db"], 10.0, places=9)
        self.assertEqual(verdict["worst_frequency_hz"], 150e3)
        self.assertEqual(verdict["category"], "A")
        self.assertEqual(verdict["kind"], "CE102")

    def test_verdict_conducted_sweep_fail(self):
        # Measured 60, 72, 68 dBuV at 50 kHz, 150 kHz, 5 MHz against the
        # CE102 curve 78, 60, 70 dBuV: margins 18, -12, 2 dB.
        freqs = (50e3, 150e3, 5e6)
        measured = (60.0, 72.0, 68.0)
        margins = [
            rfe.conducted_emission_margin(m, rfe.ce102_limit_db(f, "A"))
            for m, f in zip(measured, freqs)
        ]
        verdict = rfe.emission_verdict(margins, freqs, "A", "CE102")
        self.assertFalse(verdict["pass"])
        self.assertAlmostEqual(verdict["worst_margin_db"], -12.0, places=9)
        self.assertEqual(verdict["worst_frequency_hz"], 150e3)

    def test_verdict_radiated_sweep_fail(self):
        # Measured 15, 40, 20 dBuV/m at 10 MHz, 100 MHz, 1 GHz against
        # the category A floor 24 dBuV/m: margins 9, -16, 4 dB.
        freqs = (10e6, 100e6, 1e9)
        measured = (15.0, 40.0, 20.0)
        margins = [
            rfe.radiated_emission_margin(m, rfe.re102_limit_db(f, "A"))
            for m, f in zip(measured, freqs)
        ]
        verdict = rfe.emission_verdict(margins, freqs, "A", "radiated")
        self.assertFalse(verdict["pass"])
        self.assertAlmostEqual(verdict["worst_margin_db"], -16.0, places=9)
        self.assertEqual(verdict["worst_frequency_hz"], 100e6)
        self.assertEqual(verdict["kind"], "RE102")

    def test_verdict_kind_canonicalization(self):
        conducted = rfe.emission_verdict(10.0, 150e3, "B", "conducted")
        conducted_alt = rfe.emission_verdict(10.0, 150e3, "B", "CE102")
        radiated = rfe.emission_verdict(10.0, 100e6, "B", "radiated")
        radiated_alt = rfe.emission_verdict(10.0, 100e6, "B", "Re102")
        self.assertEqual(conducted["kind"], conducted_alt["kind"])
        self.assertEqual(radiated["kind"], radiated_alt["kind"])
        with self.assertRaises(ValueError):
            rfe.emission_verdict(10.0, 150e3, "A", "lightning")

    def test_verdict_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rfe.emission_verdict([], [], "A", "conducted")
        with self.assertRaises(ValueError):
            rfe.emission_verdict([10.0, 5.0], (150e3,), "A", "conducted")
        with self.assertRaises(ValueError):
            rfe.emission_verdict(10.0, (150e3, 200e3), "A", "conducted")
        with self.assertRaises(ValueError):
            rfe.emission_verdict([10.0], [150e3], "Q", "conducted")
        with self.assertRaises(ValueError):
            rfe.emission_verdict([10.0], [-150e3], "A", "conducted")


class TestErpSanityCheck(unittest.TestCase):
    """Inverse-square far-field sanity check of a radiating source."""

    def test_erp_field_anchor(self):
        # 100 W ERP at 10 m: E = sqrt(30 * 100) / 10 = sqrt(30) V/m.
        field = rfe.field_strength_from_erp(100.0, 10.0)
        self.assertAlmostEqual(field, 5.477225575, places=9)
        self.assertAlmostEqual(
            rfe.dbu_v_per_m_from_v_per_m(field), 134.7712, places=3
        )

    def test_erp_inverse_square_scaling(self):
        # Halving the distance doubles the field; quadrupling the ERP at
        # the same distance doubles the field as well.
        base = rfe.field_strength_from_erp(100.0, 10.0)
        self.assertAlmostEqual(
            rfe.field_strength_from_erp(100.0, 5.0), 2.0 * base, places=9
        )
        self.assertAlmostEqual(
            rfe.field_strength_from_erp(400.0, 10.0), 2.0 * base, places=9
        )

    def test_erp_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rfe.field_strength_from_erp(-5.0, 10.0)
        with self.assertRaises(ValueError):
            rfe.field_strength_from_erp(100.0, 0.0)
        with self.assertRaises(ValueError):
            rfe.field_strength_from_erp(100.0, -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
