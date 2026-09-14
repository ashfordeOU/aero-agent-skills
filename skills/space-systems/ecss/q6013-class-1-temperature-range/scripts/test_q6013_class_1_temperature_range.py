"""Contract test for the ECSS-Q-ST-60-13C clause 4.2.2.6 temperature-range leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_1_temperature_range.py
"""

import unittest

from q6013_class_1_temperature_range_logic import (
    GRADE_RATED_RANGES_C,
    TEMPERATURE_TOLERANCE_K,
    THERMAL_KNOWLEDGE_MARGIN_K,
    VERDICTS,
    assess_equipment,
    assess_part,
    coverage_verdict,
    normalize_envelope,
    normalize_part,
    rated_range_for_grade,
    required_part_range_c,
    self_heating_rise_k,
    thermal_margin_k,
)

ENVELOPE = {
    "min_c": -20.0,
    "max_c": 50.0,
    "thermal_knowledge": "correlated-thermal-model",
}


def part(**overrides):
    """An automotive-grade part with no dissipation that each test perturbs."""
    base = {
        "id": "u1-regulator",
        "grade": "automotive-grade",
        "dissipation_w": 0.0,
        "thermal_resistance_k_per_w": 0.0,
    }
    base.update(overrides)
    return base


class GradeRangeTests(unittest.TestCase):
    def test_every_known_grade_has_a_low_limit_below_its_high_limit(self):
        for grade in GRADE_RATED_RANGES_C:
            low, high = rated_range_for_grade(grade)
            self.assertLess(low, high)

    def test_commercial_grade_is_the_narrowest_cold_limit(self):
        low, _ = rated_range_for_grade("commercial-grade")
        self.assertAlmostEqual(low, 0.0, places=9)

    def test_military_temperature_grade_reaches_the_coldest_limit(self):
        low, _ = rated_range_for_grade("military-temperature-grade")
        coldest = min(value[0] for value in GRADE_RATED_RANGES_C.values())
        self.assertAlmostEqual(low, coldest, places=9)

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            rated_range_for_grade("space-grade-probably")


class ThermalMarginTests(unittest.TestCase):
    def test_measured_thermal_balance_earns_the_smallest_margin(self):
        smallest = min(THERMAL_KNOWLEDGE_MARGIN_K.values())
        self.assertAlmostEqual(
            thermal_margin_k("measured-thermal-balance-test"), smallest, places=9
        )

    def test_engineering_estimate_carries_the_largest_margin(self):
        largest = max(THERMAL_KNOWLEDGE_MARGIN_K.values())
        self.assertAlmostEqual(
            thermal_margin_k("engineering-estimate"), largest, places=9
        )

    def test_correlating_a_model_reduces_the_margin(self):
        self.assertLess(
            thermal_margin_k("correlated-thermal-model"),
            thermal_margin_k("uncorrelated-thermal-model"),
        )

    def test_unknown_knowledge_state_rejected(self):
        with self.assertRaises(ValueError):
            thermal_margin_k("someone-remembers-a-test")


class SelfHeatingTests(unittest.TestCase):
    def test_rise_is_power_times_resistance(self):
        self.assertAlmostEqual(self_heating_rise_k(0.25, 40.0), 10.0, places=9)

    def test_zero_dissipation_gives_no_rise(self):
        self.assertAlmostEqual(self_heating_rise_k(0.0, 120.0), 0.0, places=9)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            self_heating_rise_k(-0.1, 10.0)

    def test_negative_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            self_heating_rise_k(0.1, -10.0)

    def test_non_numeric_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            self_heating_rise_k("half a watt", 10.0)

    def test_boolean_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            self_heating_rise_k(True, 10.0)


class EnvelopeTests(unittest.TestCase):
    def test_envelope_defaults_to_the_weakest_thermal_knowledge(self):
        checked = normalize_envelope({"min_c": -20.0, "max_c": 50.0})
        self.assertEqual(checked["thermal_knowledge"], "engineering-estimate")

    def test_inverted_envelope_rejected(self):
        with self.assertRaises(ValueError):
            normalize_envelope({"min_c": 50.0, "max_c": -20.0})

    def test_non_mapping_envelope_rejected(self):
        with self.assertRaises(ValueError):
            normalize_envelope([-20.0, 50.0])

    def test_infinite_envelope_limit_rejected(self):
        with self.assertRaises(ValueError):
            normalize_envelope({"min_c": float("-inf"), "max_c": 50.0})


class RequiredRangeTests(unittest.TestCase):
    def test_margin_widens_both_ends(self):
        low, high = required_part_range_c(ENVELOPE, 0.0)
        self.assertAlmostEqual(low, -30.0, places=9)
        self.assertAlmostEqual(high, 60.0, places=9)

    def test_self_heating_only_raises_the_hot_end(self):
        low, high = required_part_range_c(ENVELOPE, 15.0)
        self.assertAlmostEqual(low, -30.0, places=9)
        self.assertAlmostEqual(high, 75.0, places=9)

    def test_negative_rise_rejected(self):
        with self.assertRaises(ValueError):
            required_part_range_c(ENVELOPE, -1.0)


class PartNormalisationTests(unittest.TestCase):
    def test_grade_supplies_the_rated_range_when_limits_are_absent(self):
        record = normalize_part(part())
        self.assertAlmostEqual(record["rated_min_c"], -40.0, places=9)
        self.assertAlmostEqual(record["rated_max_c"], 125.0, places=9)

    def test_explicit_limits_win_over_the_grade(self):
        record = normalize_part(
            part(grade="commercial-grade", rated_min_c=-55.0, rated_max_c=150.0)
        )
        self.assertAlmostEqual(record["rated_min_c"], -55.0, places=9)
        self.assertAlmostEqual(record["rated_max_c"], 150.0, places=9)

    def test_part_without_limits_or_grade_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part({"id": "u2"})

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part(part(id="   "))

    def test_inverted_rated_range_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part(part(rated_min_c=90.0, rated_max_c=10.0))

    def test_non_boolean_extension_evidence_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part(part(extension_evidence="yes"))

    def test_unknown_declared_verdict_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part(part(declared_verdict="probably-fine"))


class VerdictTests(unittest.TestCase):
    def test_every_verdict_name_is_reachable(self):
        produced = {
            coverage_verdict(1.0, 1.0),
            coverage_verdict(-1.0, 1.0),
            coverage_verdict(1.0, -1.0),
            coverage_verdict(-1.0, -1.0),
        }
        self.assertEqual(produced, set(VERDICTS))

    def test_exact_landing_on_the_bound_counts_as_covered(self):
        self.assertEqual(coverage_verdict(0.0, 0.0), "temperature-range-covered")

    def test_representation_error_inside_tolerance_still_covers(self):
        tiny = -TEMPERATURE_TOLERANCE_K / 2.0
        self.assertEqual(coverage_verdict(tiny, tiny), "temperature-range-covered")


class AssessPartTests(unittest.TestCase):
    def test_automotive_part_covers_a_modest_envelope(self):
        record = assess_part(part(), ENVELOPE)
        self.assertEqual(record["verdict"], "temperature-range-covered")
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["hot_headroom_k"], 65.0, places=9)
        self.assertAlmostEqual(record["cold_headroom_k"], 10.0, places=9)

    def test_self_heating_can_take_a_compliant_part_out_of_range(self):
        record = assess_part(
            part(grade="industrial-grade", dissipation_w=0.5, thermal_resistance_k_per_w=60.0),
            ENVELOPE,
        )
        self.assertAlmostEqual(record["self_heating_rise_k"], 30.0, places=9)
        self.assertEqual(record["verdict"], "hot-end-shortfall")
        self.assertIn("rated-range-extension-evidence-missing", record["findings"])

    def test_commercial_grade_fails_the_cold_end(self):
        record = assess_part(part(grade="commercial-grade"), ENVELOPE)
        self.assertEqual(record["verdict"], "cold-end-shortfall")
        self.assertAlmostEqual(record["cold_headroom_k"], -30.0, places=9)

    def test_a_narrow_rated_range_fails_both_ends(self):
        record = assess_part(
            part(grade=None, rated_min_c=-10.0, rated_max_c=40.0), ENVELOPE
        )
        self.assertEqual(record["verdict"], "both-ends-shortfall")

    def test_a_part_landing_exactly_on_the_hot_requirement_passes(self):
        record = assess_part(
            part(rated_min_c=-40.0, rated_max_c=60.0, grade=None), ENVELOPE
        )
        self.assertAlmostEqual(record["hot_headroom_k"], 0.0, places=9)
        self.assertEqual(record["verdict"], "temperature-range-covered")

    def test_extension_claim_on_a_shortfall_stays_open(self):
        record = assess_part(
            part(grade="commercial-grade", extension_evidence=True), ENVELOPE
        )
        self.assertIn("rated-range-extension-claim-open", record["findings"])

    def test_extension_claim_on_a_compliant_part_is_flagged_as_unneeded(self):
        record = assess_part(part(extension_evidence=True), ENVELOPE)
        self.assertEqual(record["findings"], ["rated-range-extension-claim-not-needed"])

    def test_declared_coverage_over_a_shortfall_is_flagged(self):
        record = assess_part(
            part(grade="commercial-grade", declared_verdict="temperature-range-covered"),
            ENVELOPE,
        )
        self.assertIn("declared-coverage-overstated", record["findings"])

    def test_declared_shortfall_naming_the_wrong_end_is_flagged(self):
        record = assess_part(
            part(grade="commercial-grade", declared_verdict="hot-end-shortfall"), ENVELOPE
        )
        self.assertIn("declared-coverage-mismatched", record["findings"])

    def test_weaker_thermal_knowledge_shrinks_the_headroom(self):
        strong = assess_part(
            part(), dict(ENVELOPE, thermal_knowledge="measured-thermal-balance-test")
        )
        weak = assess_part(
            part(), dict(ENVELOPE, thermal_knowledge="engineering-estimate")
        )
        self.assertGreater(strong["hot_headroom_k"], weak["hot_headroom_k"])


class AssessEquipmentTests(unittest.TestCase):
    def test_population_rolls_up_counts_and_critical_parts(self):
        report = assess_equipment(
            [
                part(),
                part(id="u2-opamp", grade="industrial-grade"),
                part(id="u3-clock", grade="commercial-grade"),
            ],
            ENVELOPE,
        )
        self.assertEqual(report["population_size"], 3)
        self.assertEqual(report["covered_part_count"], 2)
        self.assertEqual(report["hot_critical_part_id"], "u3-clock")
        self.assertEqual(report["cold_critical_part_id"], "u3-clock")
        self.assertFalse(report["consistent"])

    def test_a_clean_population_is_consistent(self):
        report = assess_equipment([part(), part(id="u2-opamp")], ENVELOPE)
        self.assertTrue(report["consistent"])
        self.assertEqual(report["findings"], [])

    def test_duplicate_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment([part(), part()], ENVELOPE)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment([], ENVELOPE)

    def test_non_sequence_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(part(), ENVELOPE)


if __name__ == "__main__":
    unittest.main()
