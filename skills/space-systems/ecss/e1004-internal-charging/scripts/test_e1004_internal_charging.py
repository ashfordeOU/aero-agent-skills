#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2.1.3 + Annex B.4/B.5
worst-case trapped electron spectrum for internal (deep-dielectric)
charging (FLUMIC + NASA worst-case GEO envelope).

Exercises scripts/e1004_internal_charging_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a model flux must
be a finite non-negative number per (energy, percentile) pair; a model
spectrum across energies is only free of energy_order_violations when
flux is non-increasing as energy increases; the worst-case envelope
takes the higher of the two models' fluxes at each energy and records
the dominant model; a percentile at or above 99% carries a caveat;
clause 9.2.1.3 applies only to MEO/GEO/GTO/HEO orbit regimes, and an
unknown orbit_regime raises ValueError; risk screening flags risk only
when the enveloped flux at the requested energy meets or exceeds the
threshold; invalid inputs (non-positive energy, percentile outside
(0, 100), empty energy collections, a negative flux threshold, an
unmodeled screening energy, or a model_fn returning a negative or
non-finite value) raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_internal_charging_logic as ic  # noqa: E402


def flumic_model_fn(energy_mev, percentile):
    """Synthetic FLUMIC-like flux: decreases with energy, increases
    with percentile. Deterministic, offline, not a real FLUMIC
    coefficient set."""
    return (percentile / 100.0) * (2000.0 / energy_mev)


def nasa_geo_model_fn(energy_mev, percentile):
    """Synthetic NASA-worst-case-GEO-like flux: decreases with energy,
    fixed regardless of percentile (percentile accepted but ignored,
    matching the real model's non-parameterized nature)."""
    return 1000.0 / energy_mev


def energy_increasing_model_fn(energy_mev, percentile):
    """Deliberately broken: flux increases with energy."""
    return percentile * energy_mev


def envelope_crossing_model_fn(energy_mev, percentile):
    """Deliberately broken: increases with energy fast enough to
    overtake nasa_geo_model_fn's decreasing flux at high energy,
    producing an increasing step in the worst-case envelope even
    though nasa_geo_model_fn alone stays consistent."""
    return 100.0 * energy_mev


class ValidateEnergyMevTest(unittest.TestCase):
    def test_valid_passes(self):
        ic.validate_energy_mev(0.1)
        ic.validate_energy_mev(2.0)

    def test_zero_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_energy_mev(0)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_energy_mev(-1)


class ValidatePercentileTest(unittest.TestCase):
    def test_valid_passes(self):
        ic.validate_percentile(50)
        ic.validate_percentile(99.9)
        ic.validate_percentile(0.1)

    def test_zero_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_percentile(0)

    def test_hundred_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_percentile(100)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_percentile(-5)


class PercentileCaveatTest(unittest.TestCase):
    def test_below_threshold_returns_none(self):
        self.assertIsNone(ic.percentile_caveat(95))

    def test_at_threshold_returns_caveat(self):
        self.assertIsNotNone(ic.percentile_caveat(99))

    def test_above_threshold_returns_caveat(self):
        self.assertIsNotNone(ic.percentile_caveat(99.9))

    def test_invalid_percentile_raises(self):
        with self.assertRaises(ValueError):
            ic.percentile_caveat(100)


class CheckOrbitApplicabilityTest(unittest.TestCase):
    def test_geo_is_applicable(self):
        self.assertTrue(ic.check_orbit_applicability("GEO"))

    def test_meo_gto_heo_are_applicable(self):
        self.assertTrue(ic.check_orbit_applicability("MEO"))
        self.assertTrue(ic.check_orbit_applicability("GTO"))
        self.assertTrue(ic.check_orbit_applicability("HEO"))

    def test_leo_is_known_but_not_applicable(self):
        self.assertFalse(ic.check_orbit_applicability("LEO"))

    def test_l2_is_known_but_not_applicable(self):
        self.assertFalse(ic.check_orbit_applicability("L2"))

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            ic.check_orbit_applicability("MARS-ORBIT")


class ComputeModelFluxTest(unittest.TestCase):
    def test_valid_computation(self):
        entry = ic.compute_model_flux(2.0, 90, flumic_model_fn, "FLUMIC")
        self.assertEqual(entry["model_name"], "FLUMIC")
        self.assertEqual(entry["energy_mev"], 2.0)
        self.assertEqual(entry["percentile"], 90)
        self.assertAlmostEqual(entry["flux_cm2_day"], 0.9 * (2000.0 / 2.0))

    def test_non_positive_energy_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_model_flux(0, 90, flumic_model_fn, "FLUMIC")

    def test_invalid_percentile_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_model_flux(2.0, 100, flumic_model_fn, "FLUMIC")

    def test_negative_model_result_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_model_flux(2.0, 90, lambda e, p: -1.0, "FLUMIC")

    def test_nan_model_result_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_model_flux(2.0, 90, lambda e, p: float("nan"), "FLUMIC")

    def test_non_numeric_model_result_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_model_flux(2.0, 90, lambda e, p: "bad", "FLUMIC")


class ComputeModelSpectrumTest(unittest.TestCase):
    def test_consistent_spectrum_has_no_violations(self):
        spectrum = ic.compute_model_spectrum([0.5, 1.0, 2.0, 4.0], 90, flumic_model_fn, "FLUMIC")
        self.assertEqual(
            [e["energy_mev"] for e in spectrum["entries"]], [0.5, 1.0, 2.0, 4.0]
        )
        self.assertEqual(spectrum["energy_order_violations"], [])

    def test_unsorted_input_is_sorted_ascending(self):
        spectrum = ic.compute_model_spectrum([4.0, 0.5, 2.0, 1.0], 90, flumic_model_fn, "FLUMIC")
        self.assertEqual(
            [e["energy_mev"] for e in spectrum["entries"]], [0.5, 1.0, 2.0, 4.0]
        )

    def test_inconsistent_spectrum_reports_violations(self):
        spectrum = ic.compute_model_spectrum(
            [0.5, 1.0, 2.0], 90, energy_increasing_model_fn, "BROKEN"
        )
        self.assertTrue(spectrum["energy_order_violations"])

    def test_empty_energies_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_model_spectrum([], 90, flumic_model_fn, "FLUMIC")


class ComputeWorstCaseEnvelopeTest(unittest.TestCase):
    def test_flumic_dominates_at_high_percentile(self):
        envelope = ic.compute_worst_case_envelope([1.0, 2.0], 90, flumic_model_fn, nasa_geo_model_fn)
        for entry in envelope["entries"]:
            self.assertEqual(entry["dominant_model"], "FLUMIC")
            self.assertEqual(entry["envelope_flux_cm2_day"], entry["flumic_flux_cm2_day"])

    def test_nasa_geo_dominates_at_low_percentile(self):
        envelope = ic.compute_worst_case_envelope([1.0, 2.0], 30, flumic_model_fn, nasa_geo_model_fn)
        for entry in envelope["entries"]:
            self.assertEqual(entry["dominant_model"], "NASA-worst-case-GEO")
            self.assertEqual(entry["envelope_flux_cm2_day"], entry["nasa_geo_flux_cm2_day"])

    def test_envelope_has_no_violations_for_consistent_models(self):
        envelope = ic.compute_worst_case_envelope(
            [0.5, 1.0, 2.0, 4.0], 90, flumic_model_fn, nasa_geo_model_fn
        )
        self.assertEqual(envelope["energy_order_violations"], [])

    def test_envelope_reports_violations_when_a_model_is_broken(self):
        # At e=1 and e=2, nasa_geo_model_fn (1000/e) dominates and is
        # still decreasing; at e=10, envelope_crossing_model_fn (100*e)
        # overtakes nasa_geo_model_fn and exceeds the e=2 envelope
        # value, producing an increasing step despite each model being
        # individually well-behaved in isolation.
        envelope = ic.compute_worst_case_envelope(
            [1.0, 2.0, 10.0], 90, envelope_crossing_model_fn, nasa_geo_model_fn
        )
        self.assertTrue(envelope["energy_order_violations"])

    def test_empty_energies_raises(self):
        with self.assertRaises(ValueError):
            ic.compute_worst_case_envelope([], 90, flumic_model_fn, nasa_geo_model_fn)


class ScreenInternalChargingRiskTest(unittest.TestCase):
    def setUp(self):
        self.envelope = ic.compute_worst_case_envelope(
            [1.0, 2.0, 4.0], 90, flumic_model_fn, nasa_geo_model_fn
        )

    def test_flux_above_threshold_flags_risk(self):
        result = ic.screen_internal_charging_risk(self.envelope, 2.0, 1.0)
        self.assertTrue(result["risk_flagged"])
        self.assertEqual(result["energy_threshold_mev"], 2.0)

    def test_flux_below_threshold_does_not_flag_risk(self):
        result = ic.screen_internal_charging_risk(self.envelope, 2.0, 1.0e9)
        self.assertFalse(result["risk_flagged"])

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            ic.screen_internal_charging_risk(self.envelope, 2.0, -1.0)

    def test_unmodeled_energy_raises(self):
        with self.assertRaises(ValueError):
            ic.screen_internal_charging_risk(self.envelope, 3.0, 1.0)


class InternalChargingSpecificationTest(unittest.TestCase):
    def test_applicable_regime_flags_risk_when_threshold_low(self):
        spec = ic.internal_charging_specification(
            "GEO", [1.0, 2.0, 4.0], 90, flumic_model_fn, nasa_geo_model_fn, 2.0, 1.0
        )
        self.assertTrue(spec["applicable"])
        self.assertTrue(spec["verified"])
        self.assertTrue(spec["screening"]["risk_flagged"])
        self.assertIsNone(spec["caveat"])

    def test_applicable_regime_does_not_flag_when_threshold_high(self):
        spec = ic.internal_charging_specification(
            "MEO", [1.0, 2.0, 4.0], 90, flumic_model_fn, nasa_geo_model_fn, 2.0, 1.0e9
        )
        self.assertFalse(spec["screening"]["risk_flagged"])

    def test_inapplicable_regime_short_circuits(self):
        spec = ic.internal_charging_specification(
            "LEO", [1.0, 2.0], 90, flumic_model_fn, nasa_geo_model_fn, 1.0, 1.0
        )
        self.assertFalse(spec["applicable"])
        self.assertNotIn("envelope", spec)

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            ic.internal_charging_specification(
                "MARS-ORBIT", [1.0], 90, flumic_model_fn, nasa_geo_model_fn, 1.0, 1.0
            )

    def test_high_percentile_carries_caveat(self):
        spec = ic.internal_charging_specification(
            "GTO", [1.0, 2.0], 99.5, flumic_model_fn, nasa_geo_model_fn, 2.0, 1.0
        )
        self.assertIsNotNone(spec["caveat"])

    def test_unverified_when_model_is_broken(self):
        spec = ic.internal_charging_specification(
            "HEO",
            [1.0, 2.0, 10.0],
            90,
            envelope_crossing_model_fn,
            nasa_geo_model_fn,
            2.0,
            1.0,
        )
        self.assertFalse(spec["verified"])


if __name__ == "__main__":
    unittest.main()
