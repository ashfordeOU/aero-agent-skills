"""Contract tests for the clause 6.3.3 class 3 lot-screening logic."""

import unittest

from q6013_class_3_screening_requirements_logic import (
    EQUIVALENCE_TOLERANCE,
    EVERY_UNIT_ELEMENTS,
    SCREENING_ELEMENTS,
    TRIGGER_CONDITIONS,
    assess_class3_screening,
    burn_in_equivalent_hours,
    collect_steps,
    grade_screening_element,
    required_elements,
    required_sample_size,
    validate_lot,
    validate_screening_policy,
    validate_screening_step,
    validate_triggers,
)

POLICY = {
    "sample_numerator": 1,
    "sample_denominator": 10,
    "minimum_sample_units": 5,
    "activation_energy_ev": 0.7,
    "reference_burn_in_hours": 168.0,
    "reference_burn_in_temperature_c": 125.0,
}
LOT = {"lot_size": 100, "rated_maximum_temperature_c": 150.0}


def _step(element, basis="every-unit", units=100, hours=None, temperature_c=None):
    record = {"element": element, "basis": basis, "units_screened": units}
    if element == "burn-in":
        record["hours"] = 168.0 if hours is None else hours
        record["temperature_c"] = 125.0 if temperature_c is None else temperature_c
    return record


def _steps_for(triggers):
    return [_step(name) for name in required_elements(triggers)]


def _case(**overrides):
    triggers = overrides.pop("triggers", ["criticality-bearing-function"])
    case = {
        "policy": dict(POLICY),
        "lot": dict(LOT),
        "triggers": list(triggers),
        "screening": _steps_for(triggers),
    }
    case.update(overrides)
    return case


class TriggerTests(unittest.TestCase):
    def test_triggers_returned_normalized_and_deduplicated(self):
        self.assertEqual(
            validate_triggers(["Criticality Bearing Function", "criticality-bearing-function"]),
            ("criticality-bearing-function",),
        )

    def test_undeclared_triggers_rejected(self):
        with self.assertRaises(ValueError):
            validate_triggers(None)

    def test_unrecognized_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_triggers(["it looked a bit old"])

    def test_no_trigger_owes_no_element(self):
        self.assertEqual(required_elements([]), ())

    def test_elements_are_the_union_of_the_triggers(self):
        owed = required_elements(
            ["criticality-bearing-function", "wide-temperature-range-application"]
        )
        self.assertIn("temperature-cycling", owed)
        self.assertIn("burn-in", owed)

    def test_owed_elements_follow_the_declared_element_order(self):
        owed = required_elements(list(TRIGGER_CONDITIONS))
        self.assertEqual(list(owed), [n for n in SCREENING_ELEMENTS if n in owed])

    def test_every_trigger_demands_a_recognized_element(self):
        for trigger, elements in TRIGGER_CONDITIONS.items():
            for element in elements:
                self.assertIn(element, SCREENING_ELEMENTS, trigger)


class PolicyAndLotTests(unittest.TestCase):
    def test_policy_returned_with_floats_and_ints(self):
        graded = validate_screening_policy(dict(POLICY))
        self.assertEqual(graded["sample_denominator"], 10)
        self.assertAlmostEqual(graded["activation_energy_ev"], 0.7, places=9)

    def test_sample_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(dict(POLICY, sample_numerator=11))

    def test_non_integer_sample_denominator_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(dict(POLICY, sample_denominator=10.0))

    def test_negative_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(dict(POLICY, activation_energy_ev=-0.7))

    def test_missing_policy_key_rejected(self):
        broken = dict(POLICY)
        del broken["reference_burn_in_hours"]
        with self.assertRaises(ValueError):
            validate_screening_policy(broken)

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot({"lot_size": 0, "rated_maximum_temperature_c": 150.0})

    def test_rating_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot({"lot_size": 100, "rated_maximum_temperature_c": -400.0})


class SampleSizeTests(unittest.TestCase):
    def test_fraction_governs_a_large_lot(self):
        self.assertEqual(required_sample_size(100, POLICY), 10)

    def test_minimum_count_governs_a_small_lot(self):
        self.assertEqual(required_sample_size(12, POLICY), 5)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_size(3, POLICY), 3)

    def test_fraction_rounds_up_rather_than_down(self):
        self.assertEqual(required_sample_size(101, POLICY), 11)


class BurnInEquivalenceTests(unittest.TestCase):
    def test_reference_conditions_are_worth_their_own_hours(self):
        result = burn_in_equivalent_hours(168.0, 125.0, POLICY)
        self.assertAlmostEqual(result["acceleration_factor"], 1.0, places=9)
        self.assertAlmostEqual(result["equivalent_hours"], 168.0, places=9)

    def test_a_hotter_run_is_worth_more_than_its_hours(self):
        result = burn_in_equivalent_hours(48.0, 150.0, POLICY)
        self.assertGreater(result["acceleration_factor"], 3.0)
        self.assertGreater(result["equivalent_hours"], 150.0)

    def test_a_cooler_run_is_worth_less_than_its_hours(self):
        result = burn_in_equivalent_hours(168.0, 100.0, POLICY)
        self.assertLess(result["equivalent_hours"], 100.0)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_equivalent_hours(0.0, 125.0, POLICY)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_equivalent_hours(168.0, -300.0, POLICY)


class StepTests(unittest.TestCase):
    def test_step_returned_normalized(self):
        record = validate_screening_step(
            {"element": "External Visual Inspection", "basis": "Every Unit"}
        )
        self.assertEqual(record["element"], "external-visual-inspection")
        self.assertEqual(record["basis"], "every-unit")

    def test_unrecognized_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_step({"element": "a quick look", "basis": "sample"})

    def test_unrecognized_basis_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_step(
                {"element": "external-visual-inspection", "basis": "some of them"}
            )

    def test_burn_in_without_conditions_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_step({"element": "burn-in", "basis": "every-unit"})

    def test_repeated_element_rejected(self):
        with self.assertRaises(ValueError):
            collect_steps([_step("external-visual-inspection"),
                           _step("external-visual-inspection")])

    def test_non_sequence_screening_rejected(self):
        with self.assertRaises(ValueError):
            collect_steps(_step("external-visual-inspection"))


class GradingTests(unittest.TestCase):
    def test_every_unit_element_on_the_whole_lot_is_performed(self):
        graded = grade_screening_element(
            "external-visual-inspection",
            validate_screening_step(_step("external-visual-inspection")),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "performed")

    def test_undeclared_element_is_not_performed(self):
        graded = grade_screening_element("burn-in", None, LOT, POLICY)
        self.assertEqual(graded["state"], "not-performed")

    def test_sampling_an_every_unit_element_is_insufficient(self):
        graded = grade_screening_element(
            "burn-in",
            validate_screening_step(_step("burn-in", basis="sample", units=10)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "basis-insufficient")

    def test_short_count_on_an_every_unit_element_leaves_the_lot_uncovered(self):
        graded = grade_screening_element(
            "external-visual-inspection",
            validate_screening_step(_step("external-visual-inspection", units=90)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "lot-not-covered")

    def test_sampled_element_below_the_required_count_is_too_small(self):
        graded = grade_screening_element(
            "seal-or-package-integrity-check",
            validate_screening_step(
                _step("seal-or-package-integrity-check", basis="sample", units=6)
            ),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "sample-too-small")
        self.assertEqual(graded["detail"]["required_sample"], 10)

    def test_sampled_element_at_the_required_count_is_performed(self):
        graded = grade_screening_element(
            "seal-or-package-integrity-check",
            validate_screening_step(
                _step("seal-or-package-integrity-check", basis="sample", units=10)
            ),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "performed")

    def test_sampled_element_with_no_count_is_refused(self):
        graded = grade_screening_element(
            "seal-or-package-integrity-check",
            validate_screening_step(
                {"element": "seal-or-package-integrity-check", "basis": "sample"}
            ),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "sample-not-stated")

    def test_burn_in_above_the_rating_is_refused_before_it_is_credited(self):
        graded = grade_screening_element(
            "burn-in",
            validate_screening_step(_step("burn-in", hours=24.0, temperature_c=175.0)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "condition-outside-rating")
        self.assertNotIn("equivalent_hours", graded["detail"])

    def test_burn_in_exactly_at_the_rating_is_credited(self):
        graded = grade_screening_element(
            "burn-in",
            validate_screening_step(_step("burn-in", hours=52.0, temperature_c=150.0)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "performed")

    def test_short_hot_burn_in_is_judged_on_its_equivalent_hours(self):
        graded = grade_screening_element(
            "burn-in",
            validate_screening_step(_step("burn-in", hours=48.0, temperature_c=150.0)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "duration-short")
        self.assertLess(graded["detail"]["equivalent_hours"], 168.0)

    def test_long_cool_burn_in_is_still_short(self):
        graded = grade_screening_element(
            "burn-in",
            validate_screening_step(_step("burn-in", hours=500.0, temperature_c=85.0)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "duration-short")

    def test_burn_in_at_the_reference_lands_on_the_reference_hours(self):
        graded = grade_screening_element(
            "burn-in",
            validate_screening_step(_step("burn-in", hours=168.0, temperature_c=125.0)),
            LOT, POLICY,
        )
        self.assertEqual(graded["state"], "performed")
        self.assertAlmostEqual(graded["detail"]["equivalent_hours"], 168.0, places=9)

    def test_unrecognized_element_rejected_by_the_grader(self):
        with self.assertRaises(ValueError):
            grade_screening_element("a quick look", None, LOT, POLICY)


class AssessmentTests(unittest.TestCase):
    def test_no_trigger_closes_without_screening(self):
        result = assess_class3_screening(_case(triggers=[], screening=[]))
        self.assertEqual(result["verdict"], "screening not required at this class")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["required_elements"], [])

    def test_screening_declared_with_no_trigger_is_recorded_as_additional(self):
        result = assess_class3_screening(
            _case(triggers=[], screening=[_step("external-visual-inspection")])
        )
        self.assertEqual(result["additional_screening"], ["external-visual-inspection"])
        self.assertTrue(result["acceptable"])

    def test_fully_screened_critical_lot_is_acceptable(self):
        result = assess_class3_screening(_case())
        self.assertEqual(result["verdict"], "screening meets class 3 expectations")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["figures"]["coverage"], 1.0, places=9)

    def test_trigger_with_nothing_declared_closes_on_none_declared(self):
        result = assess_class3_screening(_case(screening=[]))
        self.assertEqual(result["verdict"], "screening owed but none declared")
        self.assertEqual(len(result["open_elements"]), 4)

    def test_missing_owed_element_is_named(self):
        steps = [s for s in _steps_for(["criticality-bearing-function"])
                 if s["element"] != "burn-in"]
        result = assess_class3_screening(_case(screening=steps))
        self.assertEqual(result["verdict"], "owed screening element not performed")
        self.assertEqual(result["open_elements"], ["burn-in"])

    def test_rating_breach_outranks_a_thin_sample_in_the_verdict(self):
        steps = _steps_for(["criticality-bearing-function"])
        for step in steps:
            if step["element"] == "burn-in":
                step["temperature_c"] = 175.0
        result = assess_class3_screening(_case(screening=steps))
        self.assertEqual(result["verdict"], "screening condition outside the part rating")

    def test_short_burn_in_closes_on_the_equivalence_verdict(self):
        steps = _steps_for(["criticality-bearing-function"])
        for step in steps:
            if step["element"] == "burn-in":
                step["hours"] = 48.0
                step["temperature_c"] = 150.0
        result = assess_class3_screening(_case(screening=steps))
        self.assertEqual(result["verdict"], "burn-in short of the reference equivalent")

    def test_cavity_trigger_permits_a_sampled_seal_check(self):
        steps = [
            _step("particle-impact-noise-detection"),
            _step("seal-or-package-integrity-check", basis="sample", units=10),
        ]
        result = assess_class3_screening(_case(triggers=["cavity-package-device"],
                                               screening=steps))
        self.assertTrue(result["acceptable"])

    def test_two_triggers_owe_the_union_and_report_every_open_element(self):
        result = assess_class3_screening(
            _case(triggers=["unverified-supply-origin", "cavity-package-device"],
                  screening=[])
        )
        self.assertEqual(len(result["required_elements"]), 4)
        self.assertEqual(len(result["findings"]), 4)

    def test_extra_element_beyond_the_owed_set_is_additional_not_a_finding(self):
        steps = _steps_for(["criticality-bearing-function"]) + [_step("temperature-cycling")]
        result = assess_class3_screening(_case(screening=steps))
        self.assertEqual(result["additional_screening"], ["temperature-cycling"])
        self.assertTrue(result["acceptable"])

    def test_missing_case_key_rejected(self):
        case = _case()
        del case["triggers"]
        with self.assertRaises(ValueError):
            assess_class3_screening(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_screening(["policy"])

    def test_every_unit_elements_are_all_recognized_elements(self):
        for element in EVERY_UNIT_ELEMENTS:
            self.assertIn(element, SCREENING_ELEMENTS)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(EQUIVALENCE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
