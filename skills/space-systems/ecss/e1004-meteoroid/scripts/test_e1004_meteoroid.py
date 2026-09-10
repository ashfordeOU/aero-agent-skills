#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 10.2.2.2/10.2.4 +
Annex C meteoroid model selection and application.

Exercises scripts/e1004_meteoroid_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the background flux curve
is monotonically decreasing in mass and raises on a non-positive mass;
the Earth-shielding factor is 0.5 at the surface, rises toward 1.0 with
altitude, and raises on a negative altitude; a stream's activity window
gates its enhancement (1.0 outside the window, rising to its peak
factor at peak_doy); model-selection validation flags an unknown
regime, an invalid mass, a missing date, and a missing/invalid altitude
for an earth_orbit case; total_incident_flux combines background,
shielding, and the worst-case active stream, and raises for an unknown
regime or a missing altitude on an earth_orbit case; and the aggregated
review is compliant only when there are no violations and a result was
produced.
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_meteoroid_logic as meteoroid  # noqa: E402


class BackgroundFluxTest(unittest.TestCase):
    def test_monotonically_decreasing_with_mass(self):
        small = meteoroid.background_cumulative_flux(1e-15)
        medium = meteoroid.background_cumulative_flux(1e-9)
        large = meteoroid.background_cumulative_flux(1e-3)
        self.assertGreater(small, medium)
        self.assertGreater(medium, large)

    def test_extrapolates_below_smallest_anchor(self):
        # Should not raise, and should stay above the smallest-mass anchor flux.
        flux = meteoroid.background_cumulative_flux(1e-24)
        anchor_flux = meteoroid.background_cumulative_flux(1e-21)
        self.assertGreater(flux, anchor_flux)

    def test_extrapolates_above_largest_anchor(self):
        flux = meteoroid.background_cumulative_flux(1e6)
        anchor_flux = meteoroid.background_cumulative_flux(1e2)
        self.assertLess(flux, anchor_flux)

    def test_zero_mass_raises(self):
        with self.assertRaises(ValueError):
            meteoroid.background_cumulative_flux(0)

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            meteoroid.background_cumulative_flux(-1.0)


class EarthShieldingTest(unittest.TestCase):
    def test_half_sky_blocked_at_surface(self):
        self.assertAlmostEqual(meteoroid.earth_shielding_factor(0.0), 0.5, places=6)

    def test_increases_with_altitude(self):
        low = meteoroid.earth_shielding_factor(400.0)
        high = meteoroid.earth_shielding_factor(36000.0)
        self.assertGreater(high, low)
        self.assertGreater(low, 0.5)
        self.assertLess(high, 1.0)

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            meteoroid.earth_shielding_factor(-1.0)


class DayOfYearTest(unittest.TestCase):
    def test_date_object(self):
        self.assertEqual(meteoroid.day_of_year(date(2026, 1, 1)), 1)

    def test_tuple(self):
        self.assertEqual(meteoroid.day_of_year((2026, 8, 12)), 224)


class StreamActivityTest(unittest.TestCase):
    def test_active_within_window(self):
        self.assertTrue(meteoroid.is_stream_active("perseids", 224))

    def test_inactive_outside_window(self):
        self.assertFalse(meteoroid.is_stream_active("perseids", 100))

    def test_boundary_start_and_end_inclusive(self):
        self.assertTrue(meteoroid.is_stream_active("perseids", 198))
        self.assertTrue(meteoroid.is_stream_active("perseids", 236))

    def test_unknown_stream_raises(self):
        with self.assertRaises(KeyError):
            meteoroid.is_stream_active("not_a_stream", 1)

    def test_enhancement_at_peak_equals_peak_value(self):
        factor = meteoroid.stream_enhancement_factor("perseids", 224)
        self.assertAlmostEqual(factor, 25.0, places=6)

    def test_enhancement_at_start_is_baseline(self):
        factor = meteoroid.stream_enhancement_factor("perseids", 198)
        self.assertAlmostEqual(factor, 1.0, places=6)

    def test_enhancement_outside_window_is_baseline(self):
        factor = meteoroid.stream_enhancement_factor("perseids", 100)
        self.assertEqual(factor, 1.0)

    def test_active_streams_lists_only_active(self):
        self.assertEqual(meteoroid.active_streams(224), ["perseids"])
        self.assertEqual(meteoroid.active_streams(100), [])

    def test_worst_case_defaults_when_none_active(self):
        factor, stream_id = meteoroid.worst_case_stream_enhancement(100)
        self.assertEqual(factor, 1.0)
        self.assertIsNone(stream_id)

    def test_worst_case_picks_active_stream(self):
        factor, stream_id = meteoroid.worst_case_stream_enhancement(224)
        self.assertEqual(stream_id, "perseids")
        self.assertAlmostEqual(factor, 25.0, places=6)


class ModelSelectionViolationsTest(unittest.TestCase):
    def valid_mission(self, **overrides):
        mission = {
            "regime": "earth_orbit",
            "mass_kg": 1e-9,
            "date": date(2026, 8, 12),
            "altitude_km": 700.0,
        }
        mission.update(overrides)
        return mission

    def test_valid_mission_has_no_violations(self):
        self.assertEqual(meteoroid.model_selection_violations(self.valid_mission()), [])

    def test_valid_interplanetary_mission_has_no_violations(self):
        mission = {"regime": "interplanetary", "mass_kg": 1e-9, "date": date(2026, 1, 1)}
        self.assertEqual(meteoroid.model_selection_violations(mission), [])

    def test_unknown_regime_flagged(self):
        violations = meteoroid.model_selection_violations(self.valid_mission(regime="lunar_orbit"))
        self.assertTrue(any(v["issue"] == "unknown_regime" for v in violations))

    def test_invalid_mass_flagged(self):
        violations = meteoroid.model_selection_violations(self.valid_mission(mass_kg=0))
        self.assertTrue(any(v["issue"] == "invalid_mass" for v in violations))

    def test_missing_date_flagged(self):
        violations = meteoroid.model_selection_violations(self.valid_mission(date=None))
        self.assertTrue(any(v["issue"] == "missing_date" for v in violations))

    def test_missing_altitude_for_earth_orbit_flagged(self):
        violations = meteoroid.model_selection_violations(self.valid_mission(altitude_km=None))
        self.assertTrue(any(v["issue"] == "missing_or_invalid_altitude" for v in violations))

    def test_negative_altitude_for_earth_orbit_flagged(self):
        violations = meteoroid.model_selection_violations(self.valid_mission(altitude_km=-1.0))
        self.assertTrue(any(v["issue"] == "missing_or_invalid_altitude" for v in violations))

    def test_altitude_not_required_for_interplanetary(self):
        mission = {"regime": "interplanetary", "mass_kg": 1e-9, "date": date(2026, 1, 1)}
        self.assertEqual(meteoroid.model_selection_violations(mission), [])


class TotalIncidentFluxTest(unittest.TestCase):
    def test_interplanetary_has_no_shielding(self):
        result = meteoroid.total_incident_flux("interplanetary", 1e-9, date(2026, 1, 1))
        self.assertEqual(result["shielding_factor"], 1.0)

    def test_earth_orbit_applies_shielding(self):
        result = meteoroid.total_incident_flux("earth_orbit", 1e-9, date(2026, 1, 1), altitude_km=400.0)
        self.assertLess(result["shielding_factor"], 1.0)
        self.assertAlmostEqual(
            result["total_flux"],
            result["background_flux"] * result["shielding_factor"] * result["stream_enhancement"],
            places=12,
        )

    def test_earth_orbit_missing_altitude_raises(self):
        with self.assertRaises(ValueError):
            meteoroid.total_incident_flux("earth_orbit", 1e-9, date(2026, 1, 1))

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            meteoroid.total_incident_flux("lunar_orbit", 1e-9, date(2026, 1, 1))

    def test_stream_peak_date_exceeds_quiet_date(self):
        quiet = meteoroid.total_incident_flux("interplanetary", 1e-9, date(2026, 5, 1))
        peak = meteoroid.total_incident_flux("interplanetary", 1e-9, date(2026, 8, 12))
        self.assertEqual(quiet["background_flux"], peak["background_flux"])
        self.assertGreater(peak["total_flux"], quiet["total_flux"])
        self.assertEqual(peak["active_stream"], "perseids")


class MeteoroidEnvironmentReviewTest(unittest.TestCase):
    def test_valid_mission_is_compliant(self):
        mission = {
            "regime": "earth_orbit",
            "mass_kg": 1e-9,
            "date": date(2026, 8, 12),
            "altitude_km": 700.0,
        }
        review = meteoroid.meteoroid_environment_review(mission)
        self.assertEqual(review["violations"], [])
        self.assertIsNotNone(review["result"])
        self.assertTrue(meteoroid.is_compliant(review))

    def test_invalid_mission_is_not_compliant(self):
        mission = {"regime": "earth_orbit", "mass_kg": -1.0, "date": None}
        review = meteoroid.meteoroid_environment_review(mission)
        self.assertTrue(len(review["violations"]) > 0)
        self.assertIsNone(review["result"])
        self.assertFalse(meteoroid.is_compliant(review))


if __name__ == "__main__":
    unittest.main()
