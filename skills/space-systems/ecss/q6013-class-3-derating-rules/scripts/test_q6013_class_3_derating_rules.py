"""Contract tests for the clause 6.2.2.5 Class 3 derating-rule logic."""

import unittest

from q6013_class_3_derating_rules_logic import (
    CLASS_3_DERATING_TABLE,
    NOMINAL_ONLY_UPLIFT,
    RELAXATION_BAND,
    STRESS_KINDS,
    allowable_applied,
    assess_derating,
    derated_junction_ceiling_c,
    derating_limits,
    derating_ratio,
    effective_applied,
    grade_junction,
    grade_stress,
    junction_temperature_c,
    resolve_junction_temperature,
    stress_ratio,
    tightest_electrical_margin,
)


def clean_part(**overrides):
    """A resistor worked comfortably inside every Class 3 derating limit."""
    part = {
        "family": "fixed-resistor",
        "stresses": {
            "voltage": {"applied": 30.0, "rating": 100.0},
            "power": {"applied": 0.20, "rating": 1.0},
        },
        "rated_junction_max_c": 125.0,
        "junction_temperature_c": 70.0,
    }
    part.update(overrides)
    return part


class DeratingTableTests(unittest.TestCase):
    def test_every_family_row_covers_every_stress_kind(self):
        for family, row in CLASS_3_DERATING_TABLE.items():
            for kind in STRESS_KINDS:
                self.assertIn(kind, row, family)

    def test_every_factor_sits_inside_the_maker_rating(self):
        for family, row in CLASS_3_DERATING_TABLE.items():
            for kind in STRESS_KINDS:
                self.assertGreater(row[kind], 0.0, family)
                self.assertLessEqual(row[kind], 1.0, family)

    def test_every_family_steps_the_junction_ceiling_down(self):
        for family, row in CLASS_3_DERATING_TABLE.items():
            self.assertGreater(row["junction_step_down_k"], 0.0, family)

    def test_family_row_is_returned_by_value(self):
        row = derating_limits("fixed-resistor")
        row["voltage"] = 0.99
        self.assertNotAlmostEqual(derating_ratio("fixed-resistor", "voltage"), 0.99)

    def test_relay_current_is_the_tightest_current_rule(self):
        # The loop walks the relay row too. Against itself the declared factor
        # is exactly equal, which is an identity rather than an ordering; every
        # other family must be strictly looser, so the relay rule is the
        # tightest and uniquely so.
        relay = derating_ratio("electromechanical-relay", "current")
        for family in CLASS_3_DERATING_TABLE:
            if family == "electromechanical-relay":
                self.assertEqual(relay, derating_ratio(family, "current"))
                continue
            self.assertLess(relay, derating_ratio(family, "current"), family)

    def test_uncategorized_family_rejected(self):
        with self.assertRaises(ValueError):
            derating_limits("mystery-component")

    def test_unknown_stress_kind_rejected(self):
        with self.assertRaises(ValueError):
            derating_ratio("fixed-resistor", "torque")


class AllowableTests(unittest.TestCase):
    def test_allowable_is_the_derated_rating(self):
        self.assertAlmostEqual(allowable_applied(100.0, 0.8), 80.0, places=9)

    def test_full_rating_is_admissible_as_a_ratio(self):
        self.assertAlmostEqual(allowable_applied(50.0, 1.0), 50.0, places=9)

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            allowable_applied(0.0, 0.8)

    def test_ratio_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            allowable_applied(100.0, 1.2)

    def test_stress_ratio_is_applied_over_rated(self):
        self.assertAlmostEqual(stress_ratio(40.0, 100.0), 0.4, places=9)

    def test_stress_ratio_rejects_a_zero_rating(self):
        with self.assertRaises(ValueError):
            stress_ratio(40.0, 0.0)


class NominalUpliftTests(unittest.TestCase):
    def test_worst_case_value_passes_through(self):
        self.assertAlmostEqual(
            effective_applied(40.0, "worst-case-analysis"), 40.0, places=9
        )

    def test_nominal_value_is_uplifted(self):
        self.assertAlmostEqual(
            effective_applied(40.0, "nominal-analysis-only"),
            40.0 * NOMINAL_ONLY_UPLIFT,
            places=9,
        )

    def test_uplift_sits_above_unity(self):
        self.assertGreater(NOMINAL_ONLY_UPLIFT, 1.0)

    def test_unknown_analysis_basis_rejected(self):
        with self.assertRaises(ValueError):
            effective_applied(40.0, "engineering-judgement")

    def test_negative_applied_value_rejected(self):
        with self.assertRaises(ValueError):
            effective_applied(-1.0, "worst-case-analysis")


class GradeStressTests(unittest.TestCase):
    def test_stress_below_the_limit_is_within(self):
        record = grade_stress("fixed-resistor", "voltage", 40.0, 100.0)
        self.assertEqual(record["disposition"], "stress-within-limit")

    def test_stress_exactly_on_the_limit_is_on_limit(self):
        allowable = allowable_applied(100.0, derating_ratio("fixed-resistor", "voltage"))
        record = grade_stress("fixed-resistor", "voltage", allowable, 100.0)
        self.assertEqual(record["disposition"], "stress-on-limit")
        self.assertAlmostEqual(record["headroom_fraction"], 0.0, places=9)

    def test_unrecorded_overshoot_is_a_breach(self):
        record = grade_stress("fixed-resistor", "voltage", 85.0, 100.0)
        self.assertEqual(record["disposition"], "stress-breach")

    def test_approved_record_carries_an_overshoot_inside_the_band(self):
        record = grade_stress(
            "fixed-resistor", "voltage", 85.0, 100.0, relaxation_approved=True
        )
        self.assertEqual(record["disposition"], "stress-inside-approved-relaxation")

    def test_approved_record_buys_nothing_past_the_band(self):
        allowable = allowable_applied(100.0, derating_ratio("fixed-resistor", "voltage"))
        beyond = allowable * (1.0 + RELAXATION_BAND * 2.0)
        record = grade_stress(
            "fixed-resistor", "voltage", beyond, 100.0, relaxation_approved=True
        )
        self.assertEqual(record["disposition"], "stress-breach")

    def test_band_edge_is_still_inside_the_relaxation(self):
        allowable = allowable_applied(100.0, derating_ratio("fixed-resistor", "voltage"))
        record = grade_stress(
            "fixed-resistor",
            "voltage",
            allowable * (1.0 + RELAXATION_BAND),
            100.0,
            relaxation_approved=True,
        )
        self.assertEqual(record["disposition"], "stress-inside-approved-relaxation")

    def test_nominal_basis_can_turn_a_pass_into_a_breach(self):
        worst = grade_stress("fixed-resistor", "voltage", 79.0, 100.0)
        nominal = grade_stress(
            "fixed-resistor", "voltage", 79.0, 100.0, "nominal-analysis-only"
        )
        self.assertEqual(worst["disposition"], "stress-within-limit")
        self.assertEqual(nominal["disposition"], "stress-breach")

    def test_record_reports_the_allowable_value_a_designer_needs(self):
        record = grade_stress("digital-integrated-circuit", "voltage", 3.0, 5.0)
        self.assertAlmostEqual(record["allowable_applied"], 4.25, places=9)

    def test_non_boolean_relaxation_flag_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("fixed-resistor", "voltage", 40.0, 100.0, relaxation_approved="yes")


class JunctionTests(unittest.TestCase):
    def test_junction_from_case_adds_the_resistance_rise(self):
        self.assertAlmostEqual(junction_temperature_c(60.0, 25.0, 0.4), 70.0, places=9)

    def test_zero_dissipation_leaves_the_case_temperature(self):
        self.assertAlmostEqual(junction_temperature_c(60.0, 25.0, 0.0), 60.0, places=9)

    def test_ceiling_is_the_rated_maximum_stepped_down(self):
        self.assertAlmostEqual(derated_junction_ceiling_c(125.0, 15.0), 110.0, places=9)

    def test_junction_inside_the_ceiling_passes(self):
        graded = grade_junction(90.0, 125.0, 15.0)
        self.assertEqual(graded["disposition"], "junction-within-ceiling")
        self.assertAlmostEqual(graded["headroom_k"], 20.0, places=9)

    def test_junction_exactly_on_the_ceiling_is_on_ceiling(self):
        graded = grade_junction(110.0, 125.0, 15.0)
        self.assertEqual(graded["disposition"], "junction-on-ceiling")

    def test_junction_past_the_ceiling_fails(self):
        graded = grade_junction(120.0, 125.0, 15.0)
        self.assertEqual(graded["disposition"], "junction-over-ceiling")

    def test_absent_junction_is_not_demonstrated(self):
        graded = grade_junction(None, 125.0, 15.0)
        self.assertEqual(graded["disposition"], "junction-not-demonstrated")
        self.assertIsNone(graded["headroom_k"])

    def test_junction_derived_when_not_predicted(self):
        part = clean_part(junction_temperature_c=None)
        part["case_temperature_c"] = 60.0
        part["thermal_resistance_k_per_w"] = 25.0
        part["dissipation_w"] = 0.4
        self.assertAlmostEqual(resolve_junction_temperature(part), 70.0, places=9)

    def test_predicted_junction_wins_over_a_derivable_one(self):
        part = clean_part()
        part["case_temperature_c"] = 200.0
        part["thermal_resistance_k_per_w"] = 25.0
        part["dissipation_w"] = 0.4
        self.assertAlmostEqual(resolve_junction_temperature(part), 70.0, places=9)

    def test_incomplete_thermal_data_gives_no_junction(self):
        part = clean_part(junction_temperature_c=None)
        part["case_temperature_c"] = 60.0
        self.assertIsNone(resolve_junction_temperature(part))

    def test_negative_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(60.0, -5.0, 0.4)


class TightestMarginTests(unittest.TestCase):
    def test_smallest_headroom_wins(self):
        records = [
            {"kind": "voltage", "headroom_fraction": 0.4},
            {"kind": "power", "headroom_fraction": 0.05},
        ]
        self.assertEqual(tightest_electrical_margin(records)["kind"], "power")

    def test_tie_is_broken_by_stress_kind(self):
        records = [
            {"kind": "voltage", "headroom_fraction": 0.2},
            {"kind": "current", "headroom_fraction": 0.2},
        ]
        self.assertEqual(tightest_electrical_margin(records)["kind"], "current")

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            tightest_electrical_margin([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            tightest_electrical_margin([{"kind": "voltage"}])


class AssessmentTests(unittest.TestCase):
    def test_clean_part_is_compliant_with_no_findings(self):
        result = assess_derating("R1", clean_part())
        self.assertEqual(result["verdict"], "derating-compliant")
        self.assertEqual(result["findings"], [])

    def test_breach_is_reported_and_named(self):
        part = clean_part()
        part["stresses"]["voltage"]["applied"] = 95.0
        result = assess_derating("R2", part)
        self.assertEqual(result["verdict"], "derating-breach")
        self.assertIn("voltage-stress-past-its-derated-limit", result["findings"])

    def test_approved_relaxation_is_a_separate_verdict(self):
        part = clean_part()
        part["stresses"]["voltage"]["applied"] = 85.0
        part["stresses"]["voltage"]["relaxation_approved"] = True
        result = assess_derating("R3", part)
        self.assertEqual(result["verdict"], "derating-compliant-on-approved-relaxation")

    def test_nominal_basis_is_reported_even_when_it_still_passes(self):
        part = clean_part()
        part["stresses"]["power"]["analysis_basis"] = "nominal-analysis-only"
        result = assess_derating("R4", part)
        self.assertEqual(result["verdict"], "derating-compliant")
        self.assertIn("power-stress-uplifted-from-nominal-analysis", result["findings"])

    def test_missing_junction_leaves_the_result_open(self):
        part = clean_part(junction_temperature_c=None)
        result = assess_derating("R5", part)
        self.assertEqual(result["verdict"], "derating-open-junction-not-demonstrated")

    def test_hot_junction_breaks_a_part_with_clean_electrical_stresses(self):
        part = clean_part(junction_temperature_c=120.0)
        result = assess_derating("R6", part)
        self.assertEqual(result["verdict"], "derating-breach")
        self.assertIn("junction-temperature-past-its-derated-ceiling", result["findings"])

    def test_tightest_margin_names_the_closest_stress(self):
        part = clean_part()
        part["stresses"]["power"]["applied"] = 0.68
        result = assess_derating("R7", part)
        self.assertEqual(result["tightest_margin"]["kind"], "power")

    def test_uncategorized_family_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_derating("R8", clean_part(family="mystery-component"))

    def test_unknown_stress_kind_rejected_by_the_assessment(self):
        part = clean_part()
        part["stresses"]["torque"] = {"applied": 1.0, "rating": 2.0}
        with self.assertRaises(ValueError):
            assess_derating("R9", part)

    def test_stress_missing_its_rating_rejected(self):
        part = clean_part()
        del part["stresses"]["voltage"]["rating"]
        with self.assertRaises(ValueError):
            assess_derating("R10", part)

    def test_empty_stress_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_derating("R11", clean_part(stresses={}))

    def test_missing_rated_junction_maximum_rejected(self):
        part = clean_part()
        del part["rated_junction_max_c"]
        with self.assertRaises(ValueError):
            assess_derating("R12", part)

    def test_empty_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_derating("  ", clean_part())

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_derating("R13", ["family"])


if __name__ == "__main__":
    unittest.main()
