#!/usr/bin/env python3
"""Contract test for the Class 2 derating rules (offline)."""

import copy
import unittest

from q6013_class_2_derating_rules_logic import (
    DEFAULT_DERATING_TABLE,
    ON_LIMIT,
    OVER_LIMIT,
    PART_COMPLIANT,
    PART_COMPLIANT_WITH_RELAXATION,
    PART_FAMILIES,
    PART_NON_COMPLIANT,
    RELAXATION_BAND,
    STRESS_KINDS,
    WITHIN_APPROVED_RELAXATION,
    WITHIN_LIMIT,
    allowable_applied,
    apply_derating,
    assess_stress,
    assess_thermal_stress,
    derating_limit,
    junction_from_case,
    max_junction_temperature_c,
    relaxed_limit,
    stress_ratio,
    validate_derating_table,
)

GOOD_CASE = {
    "part_family": "ceramic-capacitor",
    "stresses": {
        "voltage": {"applied": 20.0, "rated": 50.0},
        "current": {"applied": 0.2, "rated": 1.0},
        "power": {"applied": 0.05, "rated": 0.5},
    },
    "predicted_junction_c": 85.0,
    "rated_max_junction_c": 125.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class TableTests(unittest.TestCase):
    def test_default_table_validates(self):
        self.assertIs(
            validate_derating_table(DEFAULT_DERATING_TABLE), DEFAULT_DERATING_TABLE
        )

    def test_table_covers_every_part_family(self):
        for family in PART_FAMILIES:
            self.assertIn(family, DEFAULT_DERATING_TABLE)

    def test_table_covers_every_stress_kind(self):
        for family in PART_FAMILIES:
            for kind in STRESS_KINDS:
                self.assertIn(kind, DEFAULT_DERATING_TABLE[family])

    def test_every_limit_sits_inside_the_rating(self):
        for family in PART_FAMILIES:
            for kind in STRESS_KINDS:
                limit = DEFAULT_DERATING_TABLE[family][kind]
                self.assertGreater(limit, 0.0)
                self.assertLess(limit, 1.0)

    def test_non_mapping_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_derating_table("default")

    def test_table_missing_a_family_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_TABLE)
        del broken["power-mosfet"]
        with self.assertRaises(ValueError):
            validate_derating_table(broken)

    def test_table_missing_a_stress_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_TABLE)
        del broken["film-resistor"]["power"]
        with self.assertRaises(ValueError):
            validate_derating_table(broken)

    def test_table_limit_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_TABLE)
        broken["signal-diode"]["voltage"] = 1.4
        with self.assertRaises(ValueError):
            validate_derating_table(broken)

    def test_table_missing_the_thermal_step_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_TABLE)
        del broken["magnetic-inductor"]["junction_step_down_c"]
        with self.assertRaises(ValueError):
            validate_derating_table(broken)


class LimitLookupTests(unittest.TestCase):
    def test_ceramic_capacitor_voltage_limit(self):
        self.assertAlmostEqual(
            derating_limit("ceramic-capacitor", "voltage"), 0.60, places=9
        )

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            derating_limit("vacuum-tube", "voltage")

    def test_unknown_stress_kind_rejected(self):
        with self.assertRaises(ValueError):
            derating_limit("power-mosfet", "torque")

    def test_relay_is_the_tightest_current_family(self):
        limits = {f: derating_limit(f, "current") for f in PART_FAMILIES}
        self.assertAlmostEqual(
            limits["electromechanical-relay"], min(limits.values()), places=9
        )

    def test_relaxed_limit_is_the_table_limit_plus_the_band(self):
        self.assertAlmostEqual(
            relaxed_limit("ceramic-capacitor", "voltage"),
            derating_limit("ceramic-capacitor", "voltage") + RELAXATION_BAND,
            places=9,
        )


class StressRatioTests(unittest.TestCase):
    def test_ratio_is_the_quotient(self):
        self.assertAlmostEqual(stress_ratio(25.0, 50.0), 0.5, places=9)

    def test_zero_applied_is_allowed(self):
        self.assertAlmostEqual(stress_ratio(0.0, 50.0), 0.0, places=9)

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(25.0, 0.0)

    def test_negative_applied_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(-1.0, 50.0)

    def test_non_numeric_applied_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio("twenty", 50.0)

    def test_allowable_is_rating_times_limit(self):
        self.assertAlmostEqual(
            allowable_applied("ceramic-capacitor", "voltage", 50.0), 30.0, places=9
        )


class AssessStressTests(unittest.TestCase):
    def test_stress_well_inside_the_limit_is_within(self):
        graded = assess_stress("ceramic-capacitor", "voltage", 10.0, 50.0)
        self.assertEqual(graded["verdict"], WITHIN_LIMIT)
        self.assertTrue(graded["compliant"])

    def test_stress_exactly_on_the_limit_is_on_limit_and_compliant(self):
        allowable = allowable_applied("ceramic-capacitor", "voltage", 50.0)
        graded = assess_stress("ceramic-capacitor", "voltage", allowable, 50.0)
        self.assertEqual(graded["verdict"], ON_LIMIT)
        self.assertTrue(graded["compliant"])
        self.assertAlmostEqual(graded["ratio"], graded["limit"], places=9)

    def test_representation_error_at_the_limit_is_absorbed(self):
        allowable = allowable_applied("ceramic-capacitor", "voltage", 50.0)
        drifted = allowable + allowable * 2.0e-16
        graded = assess_stress("ceramic-capacitor", "voltage", drifted, 50.0)
        self.assertTrue(graded["compliant"])

    def test_stress_above_the_limit_without_a_record_is_over(self):
        graded = assess_stress("ceramic-capacitor", "voltage", 32.0, 50.0)
        self.assertEqual(graded["verdict"], OVER_LIMIT)
        self.assertFalse(graded["compliant"])

    def test_approved_record_carries_a_stress_inside_the_band(self):
        graded = assess_stress(
            "ceramic-capacitor", "voltage", 32.0, 50.0, relaxation_approved=True
        )
        self.assertEqual(graded["verdict"], WITHIN_APPROVED_RELAXATION)
        self.assertTrue(graded["compliant"])
        self.assertTrue(graded["relaxation_used"])

    def test_stress_exactly_on_the_band_edge_is_carried(self):
        rated = 50.0
        applied = rated * relaxed_limit("ceramic-capacitor", "voltage")
        graded = assess_stress(
            "ceramic-capacitor", "voltage", applied, rated, relaxation_approved=True
        )
        self.assertEqual(graded["verdict"], WITHIN_APPROVED_RELAXATION)

    def test_stress_past_the_band_is_over_even_with_a_record(self):
        graded = assess_stress(
            "ceramic-capacitor", "voltage", 40.0, 50.0, relaxation_approved=True
        )
        self.assertEqual(graded["verdict"], OVER_LIMIT)
        self.assertFalse(graded["compliant"])

    def test_record_does_not_move_a_compliant_stress(self):
        graded = assess_stress(
            "ceramic-capacitor", "voltage", 10.0, 50.0, relaxation_approved=True
        )
        self.assertEqual(graded["verdict"], WITHIN_LIMIT)
        self.assertFalse(graded["relaxation_used"])

    def test_non_boolean_relaxation_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_stress(
                "ceramic-capacitor", "voltage", 10.0, 50.0, relaxation_approved="yes"
            )

    def test_headroom_is_zero_on_the_limit(self):
        allowable = allowable_applied("film-resistor", "power", 0.25)
        graded = assess_stress("film-resistor", "power", allowable, 0.25)
        self.assertAlmostEqual(graded["headroom"], 0.0, places=9)


class ThermalTests(unittest.TestCase):
    def test_derated_cap_steps_down_from_the_rating(self):
        self.assertAlmostEqual(
            max_junction_temperature_c("ceramic-capacitor", 125.0), 100.0, places=9
        )

    def test_junction_below_the_cap_is_within(self):
        graded = assess_thermal_stress("ceramic-capacitor", 70.0, 125.0)
        self.assertEqual(graded["verdict"], WITHIN_LIMIT)

    def test_junction_exactly_on_the_cap_is_on_limit_and_compliant(self):
        cap = max_junction_temperature_c("power-mosfet", 150.0)
        graded = assess_thermal_stress("power-mosfet", cap, 150.0)
        self.assertEqual(graded["verdict"], ON_LIMIT)
        self.assertTrue(graded["compliant"])

    def test_junction_above_the_cap_is_over(self):
        graded = assess_thermal_stress("power-mosfet", 145.0, 150.0)
        self.assertEqual(graded["verdict"], OVER_LIMIT)
        self.assertFalse(graded["compliant"])

    def test_headroom_matches_the_gap_to_the_cap(self):
        graded = assess_thermal_stress("power-mosfet", 100.0, 150.0)
        self.assertAlmostEqual(graded["headroom_c"], 20.0, places=9)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_stress("power-mosfet", -300.0, 150.0)


class JunctionDerivationTests(unittest.TestCase):
    def test_junction_is_case_plus_resistance_times_power(self):
        self.assertAlmostEqual(junction_from_case(70.0, 20.0, 1.0), 90.0, places=9)

    def test_zero_dissipation_leaves_the_case_temperature(self):
        self.assertAlmostEqual(junction_from_case(70.0, 20.0, 0.0), 70.0, places=9)

    def test_negative_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            junction_from_case(70.0, -5.0, 1.0)

    def test_case_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_from_case(-400.0, 20.0, 1.0)


class ApplyDeratingTests(unittest.TestCase):
    def test_derated_part_is_compliant(self):
        result = apply_derating(GOOD_CASE)
        self.assertEqual(result["verdict"], PART_COMPLIANT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["junction_source"], "predicted")

    def test_over_voltage_part_is_non_compliant(self):
        case = _case(GOOD_CASE)
        case["stresses"]["voltage"]["applied"] = 45.0
        result = apply_derating(case)
        self.assertEqual(result["verdict"], PART_NON_COMPLIANT)
        self.assertTrue(any("voltage stress" in f for f in result["findings"]))

    def test_approved_relaxation_is_compliant_and_reported(self):
        case = _case(GOOD_CASE)
        case["stresses"]["voltage"]["applied"] = 32.0
        case["stresses"]["voltage"]["relaxation_approved"] = True
        result = apply_derating(case)
        self.assertEqual(result["verdict"], PART_COMPLIANT_WITH_RELAXATION)
        self.assertTrue(result["relaxation_used"])
        self.assertTrue(any("relaxation band" in f for f in result["findings"]))

    def test_relaxation_beyond_the_band_is_still_non_compliant(self):
        case = _case(GOOD_CASE)
        case["stresses"]["voltage"]["applied"] = 45.0
        case["stresses"]["voltage"]["relaxation_approved"] = True
        result = apply_derating(case)
        self.assertEqual(result["verdict"], PART_NON_COMPLIANT)

    def test_thermal_ceiling_takes_no_relaxation(self):
        case = _case(GOOD_CASE, predicted_junction_c=115.0)
        case["stresses"]["voltage"]["relaxation_approved"] = True
        result = apply_derating(case)
        self.assertEqual(result["verdict"], PART_NON_COMPLIANT)
        self.assertTrue(any("no relaxation" in f for f in result["findings"]))

    def test_junction_derived_from_a_measured_case_temperature(self):
        case = _case(GOOD_CASE)
        del case["predicted_junction_c"]
        case["case_temperature_c"] = 70.0
        case["thermal_resistance_c_per_w"] = 20.0
        case["dissipated_w"] = 1.0
        result = apply_derating(case)
        self.assertEqual(result["junction_source"], "derived-from-case")
        self.assertAlmostEqual(
            result["thermal"]["predicted_junction_c"], 90.0, places=9
        )
        self.assertEqual(result["verdict"], PART_COMPLIANT)

    def test_half_a_derivation_rejected(self):
        case = _case(GOOD_CASE)
        del case["predicted_junction_c"]
        case["case_temperature_c"] = 70.0
        with self.assertRaises(ValueError):
            apply_derating(case)

    def test_missing_junction_is_reported_not_silently_passed(self):
        case = _case(GOOD_CASE)
        del case["predicted_junction_c"]
        result = apply_derating(case)
        self.assertIsNone(result["thermal"])
        self.assertTrue(any("not yet demonstrated" in f for f in result["findings"]))

    def test_junction_without_a_rated_maximum_rejected(self):
        case = _case(GOOD_CASE)
        del case["rated_max_junction_c"]
        with self.assertRaises(ValueError):
            apply_derating(case)

    def test_tightest_stress_is_named(self):
        result = apply_derating(GOOD_CASE)
        self.assertIn(result["tightest_stress"], STRESS_KINDS)

    def test_tightest_margin_is_the_smallest_gap(self):
        result = apply_derating(GOOD_CASE)
        gaps = [entry["limit"] - entry["ratio"] for entry in result["electrical"]]
        self.assertAlmostEqual(result["tightest_margin"], min(gaps), places=9)

    def test_unknown_stress_kind_in_a_case_rejected(self):
        case = _case(GOOD_CASE)
        case["stresses"]["torque"] = {"applied": 1.0, "rated": 2.0}
        with self.assertRaises(ValueError):
            apply_derating(case)

    def test_stress_entry_missing_a_rating_rejected(self):
        case = _case(GOOD_CASE)
        case["stresses"]["voltage"] = {"applied": 20.0}
        with self.assertRaises(ValueError):
            apply_derating(case)

    def test_empty_stress_mapping_rejected(self):
        with self.assertRaises(ValueError):
            apply_derating(_case(GOOD_CASE, stresses={}))

    def test_uncategorized_family_rejected(self):
        with self.assertRaises(ValueError):
            apply_derating(_case(GOOD_CASE, part_family=None))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            apply_derating(["ceramic-capacitor"])

    def test_every_family_grades_a_fully_derated_part_as_compliant(self):
        for family in PART_FAMILIES:
            case = {
                "part_family": family,
                "stresses": {
                    kind: {
                        "applied": 0.1 * derating_limit(family, kind),
                        "rated": 1.0,
                    }
                    for kind in STRESS_KINDS
                },
                "predicted_junction_c": 25.0,
                "rated_max_junction_c": 125.0,
            }
            self.assertEqual(apply_derating(case)["verdict"], PART_COMPLIANT)


if __name__ == "__main__":
    unittest.main(verbosity=1)
