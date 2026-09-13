"""Contract tests for the clause 5.5.1.3.1 thermal-cycling purpose logic."""

import unittest

from e2008_thermal_cycling_test_purpose_logic import (
    CYCLE_TOLERANCE,
    DEFAULT_FATIGUE_EXPONENT,
    MINUTES_PER_YEAR,
    assess_cycling_purpose,
    cycle_equivalence_factor,
    cycle_range_k,
    extreme_findings,
    family_coverage,
    predicted_orbit_cycles,
    ramp_rate_k_per_min,
    required_test_cycles,
    validate_extremes,
)

FLIGHT_FAMILIES = [
    "cell-interconnect-weld",
    "coverglass-bond",
    "string-to-harness-termination",
    "substrate-bond",
]


class ExtremeTests(unittest.TestCase):
    def test_validated_pair_is_returned_as_floats(self):
        self.assertEqual(validate_extremes(-80, 60), (-80.0, 60.0))

    def test_swing_is_the_difference(self):
        self.assertAlmostEqual(cycle_range_k(-80.0, 60.0), 140.0, places=9)

    def test_inverted_extremes_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes(60.0, -80.0)

    def test_equal_extremes_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes(20.0, 20.0)

    def test_non_numeric_extreme_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes("-80", 60.0)

    def test_boolean_extreme_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes(True, 60.0)

    def test_non_finite_extreme_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes(-80.0, float("inf"))


class OrbitCycleTests(unittest.TestCase):
    def test_low_orbit_year_count(self):
        self.assertEqual(predicted_orbit_cycles(90.0, 1.0), 5844)

    def test_minutes_per_year_constant(self):
        self.assertAlmostEqual(MINUTES_PER_YEAR, 525960.0, places=9)

    def test_eclipse_fraction_reduces_the_count(self):
        self.assertEqual(predicted_orbit_cycles(90.0, 1.0, 0.6), 3507)

    def test_geostationary_period_gives_few_cycles(self):
        self.assertEqual(predicted_orbit_cycles(1436.0, 1.0, 0.25), 92)

    def test_exact_count_is_not_bumped_by_the_ceiling(self):
        self.assertEqual(predicted_orbit_cycles(MINUTES_PER_YEAR, 1.0), 1)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            predicted_orbit_cycles(0.0, 1.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            predicted_orbit_cycles(90.0, -1.0)

    def test_eclipse_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            predicted_orbit_cycles(90.0, 1.0, 1.4)

    def test_zero_eclipse_fraction_rejected(self):
        with self.assertRaises(ValueError):
            predicted_orbit_cycles(90.0, 1.0, 0.0)


class EquivalenceTests(unittest.TestCase):
    def test_double_swing_is_four_in_orbit_cycles(self):
        self.assertAlmostEqual(cycle_equivalence_factor(100.0, 200.0), 4.0, places=9)

    def test_equal_swings_give_unity(self):
        self.assertAlmostEqual(cycle_equivalence_factor(140.0, 140.0), 1.0, places=9)

    def test_default_exponent_is_two(self):
        self.assertAlmostEqual(DEFAULT_FATIGUE_EXPONENT, 2.0, places=9)

    def test_higher_exponent_raises_the_equivalence(self):
        soft = cycle_equivalence_factor(100.0, 200.0, 2.0)
        hard = cycle_equivalence_factor(100.0, 200.0, 3.0)
        self.assertAlmostEqual(hard, 8.0, places=9)
        self.assertAlmostEqual(soft, 4.0, places=9)

    def test_narrower_test_swing_gives_a_factor_below_one(self):
        self.assertAlmostEqual(cycle_equivalence_factor(200.0, 100.0), 0.25, places=9)

    def test_exponent_below_one_rejected(self):
        with self.assertRaises(ValueError):
            cycle_equivalence_factor(100.0, 200.0, 0.5)

    def test_zero_swing_rejected(self):
        with self.assertRaises(ValueError):
            cycle_equivalence_factor(0.0, 200.0)


class RequiredCycleTests(unittest.TestCase):
    def test_equivalence_of_four_quarters_the_count(self):
        self.assertEqual(required_test_cycles(5844, 4.0), 1461)

    def test_demonstration_factor_scales_the_count(self):
        self.assertEqual(required_test_cycles(5844, 4.0, 2.0), 2922)

    def test_partial_cycle_rounds_up(self):
        self.assertEqual(required_test_cycles(5845, 4.0), 1462)

    def test_favourable_equivalence_still_keeps_the_floor(self):
        self.assertEqual(required_test_cycles(10, 100.0), 1)

    def test_non_integer_predicted_count_rejected(self):
        with self.assertRaises(ValueError):
            required_test_cycles(5844.0, 4.0)

    def test_demonstration_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_test_cycles(5844, 4.0, 0.8)

    def test_zero_equivalence_rejected(self):
        with self.assertRaises(ValueError):
            required_test_cycles(5844, 0.0)


class RampTests(unittest.TestCase):
    def test_ramp_is_swing_over_transition(self):
        self.assertAlmostEqual(ramp_rate_k_per_min(150.0, 30.0), 5.0, places=9)

    def test_shorter_transition_raises_the_ramp(self):
        self.assertAlmostEqual(ramp_rate_k_per_min(180.0, 15.0), 12.0, places=9)

    def test_zero_transition_rejected(self):
        with self.assertRaises(ValueError):
            ramp_rate_k_per_min(150.0, 0.0)


class EnvelopeTests(unittest.TestCase):
    def test_exactly_enveloping_extremes_raise_no_finding(self):
        self.assertEqual(extreme_findings((-80.0, 60.0), (-100.0, 80.0), 20.0), [])

    def test_short_hot_limit_is_flagged(self):
        findings = extreme_findings((-80.0, 60.0), (-100.0, 70.0), 20.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("hot limit", findings[0])

    def test_short_cold_limit_is_flagged(self):
        findings = extreme_findings((-80.0, 60.0), (-90.0, 80.0), 20.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("cold limit", findings[0])

    def test_both_limits_short_give_two_findings(self):
        self.assertEqual(
            len(extreme_findings((-80.0, 60.0), (-85.0, 65.0), 20.0)), 2
        )

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            extreme_findings((-80.0, 60.0), (-100.0, 80.0), -5.0)


class FamilyCoverageTests(unittest.TestCase):
    def test_names_are_normalized_before_matching(self):
        covered, missing = family_coverage(
            ["Coverglass Bond", "cell_interconnect_weld"],
            ["coverglass-bond", "cell-interconnect-weld"],
        )
        self.assertEqual(missing, [])
        self.assertEqual(len(covered), 2)

    def test_absent_family_is_reported(self):
        covered, missing = family_coverage(["coverglass-bond"], FLIGHT_FAMILIES)
        self.assertEqual(len(covered), 1)
        self.assertEqual(len(missing), 3)

    def test_empty_flight_set_rejected(self):
        with self.assertRaises(ValueError):
            family_coverage(["coverglass-bond"], [])

    def test_blank_family_name_rejected(self):
        with self.assertRaises(ValueError):
            family_coverage(["   "], FLIGHT_FAMILIES)

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            family_coverage("coverglass-bond", FLIGHT_FAMILIES)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "orbit_period_min": 90.0,
            "mission_years": 5.0,
            "predicted_extremes_c": (-80.0, 60.0),
            "test_extremes_c": (-100.0, 80.0),
            "margin_k": 20.0,
            "planned_cycles": 20000,
            "dwell_min": 10.0,
            "required_dwell_min": 10.0,
            "transition_min": 30.0,
            "max_ramp_k_per_min": 6.0,
            "flight_families": FLIGHT_FAMILIES,
            "article_families": list(FLIGHT_FAMILIES),
        }
        spec.update(overrides)
        return spec

    def test_well_formed_run_demonstrates_the_purpose(self):
        result = assess_cycling_purpose(self._spec())
        self.assertTrue(result["demonstrated"])
        self.assertEqual(result["findings"], [])

    def test_predicted_cycle_count_is_reported(self):
        result = assess_cycling_purpose(self._spec())
        self.assertEqual(result["predicted_cycles"], 29220)

    def test_swings_are_reported_in_kelvin(self):
        result = assess_cycling_purpose(self._spec())
        self.assertAlmostEqual(result["orbit_range_k"], 140.0, places=9)
        self.assertAlmostEqual(result["test_range_k"], 180.0, places=9)

    def test_planned_equal_to_required_still_demonstrates(self):
        first = assess_cycling_purpose(self._spec())
        exact = assess_cycling_purpose(
            self._spec(planned_cycles=first["required_cycles"])
        )
        self.assertEqual(exact["cycle_margin"], 0)
        self.assertTrue(exact["demonstrated"])

    def test_short_cycle_count_is_flagged(self):
        result = assess_cycling_purpose(self._spec(planned_cycles=500))
        self.assertFalse(result["demonstrated"])
        self.assertTrue(any("short of" in f for f in result["findings"]))

    def test_ramp_on_its_bound_is_absorbed(self):
        result = assess_cycling_purpose(self._spec())
        self.assertAlmostEqual(result["ramp_rate_k_per_min"], 6.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_fast_transition_breaches_the_ramp_bound(self):
        result = assess_cycling_purpose(self._spec(transition_min=10.0))
        self.assertFalse(result["demonstrated"])
        self.assertTrue(any("ramp" in f for f in result["findings"]))

    def test_short_dwell_is_flagged(self):
        result = assess_cycling_purpose(self._spec(dwell_min=4.0))
        self.assertTrue(any("dwell" in f for f in result["findings"]))

    def test_missing_process_family_is_flagged(self):
        result = assess_cycling_purpose(
            self._spec(article_families=["coverglass-bond", "substrate-bond"])
        )
        self.assertFalse(result["demonstrated"])
        self.assertEqual(len(result["missing_families"]), 2)

    def test_narrow_test_extremes_are_flagged(self):
        result = assess_cycling_purpose(
            self._spec(test_extremes_c=(-85.0, 65.0))
        )
        self.assertFalse(result["demonstrated"])

    def test_harsher_exponent_lowers_the_required_count(self):
        soft = assess_cycling_purpose(self._spec(fatigue_exponent=2.0))
        hard = assess_cycling_purpose(self._spec(fatigue_exponent=3.0))
        self.assertLess(hard["required_cycles"], soft["required_cycles"])

    def test_demonstration_factor_raises_the_required_count(self):
        plain = assess_cycling_purpose(self._spec())
        doubled = assess_cycling_purpose(self._spec(demonstration_factor=2.0))
        self.assertEqual(
            doubled["required_cycles"],
            required_test_cycles(plain["predicted_cycles"], plain["equivalence"], 2.0),
        )

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["dwell_min"]
        with self.assertRaises(ValueError):
            assess_cycling_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cycling_purpose(["orbit_period_min"])

    def test_malformed_extreme_pair_rejected(self):
        with self.assertRaises(ValueError):
            assess_cycling_purpose(self._spec(test_extremes_c=(-100.0,)))

    def test_non_integer_planned_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_cycling_purpose(self._spec(planned_cycles=20000.0))

    def test_cycle_tolerance_is_small(self):
        self.assertAlmostEqual(CYCLE_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
