"""Contract tests for the clause 5.5.1.5.1 coupon test-objective screening logic."""

import unittest

from e2008_solar_array_esd_test_purpose_logic import (
    ENVELOPE_ABSOLUTE_TOLERANCE,
    RECOGNIZED_MECHANISMS,
    assess_test_purpose,
    at_or_above,
    driving_mechanisms,
    effective_rules,
    envelope_shortfalls,
    group_rules_by_mechanism,
    normalize_mechanism,
    validate_design_rules,
    validate_environment,
    validate_plan,
)

# A high-voltage array in a charging environment: the surface differential
# potential clears both the charging onset and the inception threshold, and the
# string can both reach the propagation voltage and feed a discharge.
ENVIRONMENT = {
    "differential_potential_v": 1200.0,
    "differential_onset_v": 400.0,
    "exposed_dielectric_area_m2": 0.35,
    "inception_threshold_v": 900.0,
    "string_voltage_v": 100.0,
    "propagation_threshold_v": 80.0,
    "string_current_a": 3.0,
    "sustaining_current_a": 0.8,
}

PLAN = {
    "mechanisms_exercised": [
        "differential-surface-charging",
        "triple-junction-inception",
        "string-to-string-propagation",
    ],
    "applied_bias_v": 1200.0,
    "applied_string_current_a": 3.0,
    "discharge_count": 60,
    "required_discharge_count": 50,
}

RULES = [
    {"rule_id": "coverglass-overhang", "mechanism": "triple-junction-inception",
     "embodied_on_coupon": True, "representative": True},
    {"rule_id": "grounded-front-coating", "mechanism": "differential-surface-charging",
     "embodied_on_coupon": True, "representative": True},
    {"rule_id": "string-gap-and-insulation", "mechanism": "string-to-string-propagation",
     "embodied_on_coupon": True, "representative": True},
]


def _environment(**overrides):
    env = dict(ENVIRONMENT)
    env.update(overrides)
    return env


def _plan(**overrides):
    plan = dict(PLAN)
    plan["mechanisms_exercised"] = list(PLAN["mechanisms_exercised"])
    plan.update(overrides)
    return plan


def _rules(**overrides):
    rules = [dict(rule) for rule in RULES]
    for rule_id, changes in overrides.items():
        for rule in rules:
            if rule["rule_id"].replace("-", "_") == rule_id:
                rule.update(changes)
    return rules


class AtOrAboveTests(unittest.TestCase):
    def test_value_above_threshold(self):
        self.assertTrue(at_or_above(1200.0, 900.0))

    def test_value_below_threshold(self):
        self.assertFalse(at_or_above(500.0, 900.0))

    def test_exact_equality_counts_as_reached(self):
        self.assertTrue(at_or_above(900.0, 900.0))

    def test_equality_within_tolerance_counts_as_reached(self):
        self.assertTrue(at_or_above(900.0 - ENVELOPE_ABSOLUTE_TOLERANCE / 2.0, 900.0))

    def test_non_numeric_threshold_rejected(self):
        with self.assertRaises(ValueError):
            at_or_above(900.0, "900")


class MechanismNameTests(unittest.TestCase):
    def test_recognized_name_is_returned(self):
        self.assertEqual(
            normalize_mechanism("triple-junction-inception"), "triple-junction-inception"
        )

    def test_surrounding_space_and_case_are_absorbed(self):
        self.assertEqual(
            normalize_mechanism("  Triple-Junction-Inception "),
            "triple-junction-inception",
        )

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mechanism("sparking")

    def test_non_string_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mechanism(3)

    def test_three_mechanisms_are_recognized(self):
        self.assertEqual(len(RECOGNIZED_MECHANISMS), 3)


class EnvironmentTests(unittest.TestCase):
    def test_validated_environment_is_float_valued(self):
        env = validate_environment(ENVIRONMENT)
        self.assertAlmostEqual(env["differential_potential_v"], 1200.0, places=9)

    def test_missing_environment_key_rejected(self):
        env = _environment()
        del env["string_current_a"]
        with self.assertRaises(ValueError):
            validate_environment(env)

    def test_negative_environment_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(_environment(string_voltage_v=-100.0))

    def test_non_mapping_environment_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment([1200.0])

    def test_all_three_mechanisms_drive_in_the_base_environment(self):
        self.assertEqual(len(driving_mechanisms(ENVIRONMENT)), 3)

    def test_no_exposed_dielectric_drops_surface_charging(self):
        driving = driving_mechanisms(_environment(exposed_dielectric_area_m2=0.0))
        self.assertNotIn("differential-surface-charging", driving)
        self.assertIn("triple-junction-inception", driving)

    def test_potential_exactly_at_inception_still_drives(self):
        env = _environment(differential_potential_v=900.0)
        self.assertAlmostEqual(
            env["differential_potential_v"], env["inception_threshold_v"], places=9
        )
        self.assertIn("triple-junction-inception", driving_mechanisms(env))

    def test_potential_below_inception_drops_that_mechanism(self):
        driving = driving_mechanisms(_environment(differential_potential_v=500.0))
        self.assertNotIn("triple-junction-inception", driving)

    def test_string_unable_to_feed_drops_propagation(self):
        driving = driving_mechanisms(_environment(string_current_a=0.2))
        self.assertNotIn("string-to-string-propagation", driving)

    def test_low_voltage_array_drives_nothing(self):
        driving = driving_mechanisms(
            _environment(differential_potential_v=50.0, string_voltage_v=28.0)
        )
        self.assertEqual(driving, ())

    def test_driving_set_is_ordered_and_unique(self):
        driving = driving_mechanisms(ENVIRONMENT)
        self.assertEqual(list(driving), sorted(set(driving)))


class DesignRuleTests(unittest.TestCase):
    def test_rules_validate_to_records(self):
        records = validate_design_rules(RULES)
        self.assertEqual(len(records), 3)

    def test_rules_group_under_their_mechanism(self):
        grouped = group_rules_by_mechanism(RULES)
        self.assertEqual(len(grouped["triple-junction-inception"]), 1)
        self.assertEqual(len(grouped), len(RECOGNIZED_MECHANISMS))

    def test_effective_rules_drop_an_unembodied_provision(self):
        rules = _rules(coverglass_overhang={"embodied_on_coupon": False})
        self.assertEqual(effective_rules(rules, "triple-junction-inception"), [])

    def test_effective_rules_drop_a_non_representative_provision(self):
        rules = _rules(coverglass_overhang={"representative": False})
        self.assertEqual(effective_rules(rules, "triple-junction-inception"), [])

    def test_effective_rules_keep_a_carried_provision(self):
        carried = effective_rules(RULES, "string-to-string-propagation")
        self.assertEqual(carried[0]["rule_id"], "string-gap-and-insulation")

    def test_empty_rule_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_rules([])

    def test_duplicate_rule_id_rejected(self):
        rules = [dict(RULES[0]), dict(RULES[0])]
        with self.assertRaises(ValueError):
            validate_design_rules(rules)

    def test_missing_rule_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_rules([{"rule_id": "r", "mechanism": "triple-junction-inception"}])

    def test_non_boolean_flag_rejected(self):
        rules = _rules(coverglass_overhang={"embodied_on_coupon": 1})
        with self.assertRaises(ValueError):
            validate_design_rules(rules)

    def test_blank_rule_id_rejected(self):
        rules = _rules(coverglass_overhang={"rule_id": "   "})
        with self.assertRaises(ValueError):
            validate_design_rules(rules)


class PlanTests(unittest.TestCase):
    def test_plan_normalizes_the_exercised_set(self):
        conditions = validate_plan(_plan())
        self.assertEqual(len(conditions["mechanisms_exercised"]), 3)

    def test_duplicate_exercised_mechanism_is_collapsed(self):
        conditions = validate_plan(
            _plan(mechanisms_exercised=[
                "triple-junction-inception", "triple-junction-inception"
            ])
        )
        self.assertEqual(conditions["mechanisms_exercised"],
                         ("triple-junction-inception",))

    def test_mechanisms_exercised_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_plan(_plan(mechanisms_exercised="triple-junction-inception"))

    def test_non_integer_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(_plan(discharge_count=60.5))

    def test_boolean_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(_plan(discharge_count=True))

    def test_negative_required_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(_plan(required_discharge_count=-1))

    def test_missing_plan_key_rejected(self):
        plan = _plan()
        del plan["applied_bias_v"]
        with self.assertRaises(ValueError):
            validate_plan(plan)


class EnvelopeTests(unittest.TestCase):
    def test_bias_bounding_the_differential_potential_has_no_shortfall(self):
        self.assertEqual(
            envelope_shortfalls(ENVIRONMENT, PLAN, "triple-junction-inception"), []
        )

    def test_bias_exactly_at_the_differential_potential_has_no_shortfall(self):
        plan = _plan(applied_bias_v=ENVIRONMENT["differential_potential_v"])
        self.assertAlmostEqual(
            plan["applied_bias_v"], ENVIRONMENT["differential_potential_v"], places=9
        )
        self.assertEqual(
            envelope_shortfalls(ENVIRONMENT, plan, "triple-junction-inception"), []
        )

    def test_low_bias_is_a_shortfall(self):
        findings = envelope_shortfalls(
            ENVIRONMENT, _plan(applied_bias_v=300.0), "triple-junction-inception"
        )
        self.assertEqual(len(findings), 1)

    def test_propagation_checks_the_string_current_too(self):
        findings = envelope_shortfalls(
            ENVIRONMENT, _plan(applied_string_current_a=0.5),
            "string-to-string-propagation",
        )
        self.assertEqual(len(findings), 1)

    def test_propagation_current_exactly_at_the_worst_case_passes(self):
        plan = _plan(applied_string_current_a=ENVIRONMENT["string_current_a"])
        self.assertAlmostEqual(
            plan["applied_string_current_a"], ENVIRONMENT["string_current_a"], places=9
        )
        self.assertEqual(
            envelope_shortfalls(ENVIRONMENT, plan, "string-to-string-propagation"), []
        )

    def test_propagation_can_raise_both_shortfalls(self):
        findings = envelope_shortfalls(
            ENVIRONMENT, _plan(applied_bias_v=10.0, applied_string_current_a=0.5),
            "string-to-string-propagation",
        )
        self.assertEqual(len(findings), 2)


class PurposeAssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "environment": _environment(),
            "design_rules": _rules(),
            "plan": _plan(),
        }
        spec.update(overrides)
        return spec

    def test_a_sound_plan_demonstrates_the_purpose(self):
        result = assess_test_purpose(self._spec())
        self.assertTrue(result["purpose_demonstrable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_undeclared_rule_leaves_a_mechanism_uncovered(self):
        rules = [rule for rule in _rules()
                 if rule["mechanism"] != "triple-junction-inception"]
        result = assess_test_purpose(self._spec(design_rules=rules))
        self.assertFalse(result["purpose_demonstrable"])
        self.assertIn("triple-junction-inception", result["uncovered_mechanisms"])
        self.assertAlmostEqual(result["coverage_fraction"], 2.0 / 3.0, places=9)

    def test_rule_not_embodied_on_the_coupon_is_a_finding(self):
        rules = _rules(coverglass_overhang={"embodied_on_coupon": False})
        result = assess_test_purpose(self._spec(design_rules=rules))
        self.assertFalse(result["purpose_demonstrable"])
        self.assertIn("not embodied", result["findings"][0])

    def test_non_representative_embodiment_raises_its_own_finding(self):
        rules = _rules(string_gap_and_insulation={"representative": False})
        result = assess_test_purpose(self._spec(design_rules=rules))
        self.assertEqual(len(result["findings"]), 2)

    def test_mechanism_never_driven_by_the_plan_is_a_finding(self):
        plan = _plan(mechanisms_exercised=[
            "differential-surface-charging", "triple-junction-inception"
        ])
        result = assess_test_purpose(self._spec(plan=plan))
        self.assertIn("string-to-string-propagation", result["uncovered_mechanisms"])

    def test_envelope_shortfall_uncovers_the_mechanism(self):
        result = assess_test_purpose(self._spec(plan=_plan(applied_bias_v=300.0)))
        self.assertFalse(result["purpose_demonstrable"])
        self.assertIn("differential-surface-charging", result["uncovered_mechanisms"])

    def test_thin_discharge_population_is_a_finding(self):
        result = assess_test_purpose(self._spec(plan=_plan(discharge_count=5)))
        self.assertFalse(result["purpose_demonstrable"])
        self.assertIn("falls short", result["findings"][-1])

    def test_discharge_population_exactly_at_the_requirement_passes(self):
        result = assess_test_purpose(self._spec(plan=_plan(discharge_count=50)))
        self.assertTrue(result["purpose_demonstrable"])

    def test_benign_environment_demonstrates_nothing(self):
        env = _environment(differential_potential_v=50.0, string_voltage_v=28.0)
        result = assess_test_purpose(self._spec(environment=env))
        self.assertEqual(result["driving_mechanisms"], ())
        self.assertFalse(result["purpose_demonstrable"])
        self.assertAlmostEqual(result["coverage_fraction"], 0.0, places=9)

    def test_grounded_front_surface_narrows_the_objective(self):
        env = _environment(exposed_dielectric_area_m2=0.0)
        result = assess_test_purpose(self._spec(environment=env))
        self.assertEqual(len(result["driving_mechanisms"]), 2)
        self.assertTrue(result["purpose_demonstrable"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["plan"]
        with self.assertRaises(ValueError):
            assess_test_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_purpose(["environment"])


if __name__ == "__main__":
    unittest.main()
