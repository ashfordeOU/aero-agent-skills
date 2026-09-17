"""Contract tests for the Table 8-13 legacy class 2 screening list logic.

The cases follow the workflow one step at a time: step validation and the
hundred-percent coverage rule, the population chain that carries survivors
from one step to the next, the declared order, the burn-in percent defective
taken on the entered population, cumulative attrition against its cap, the
deliverable quantity left afterwards, and the disposition that carries them.
Each step is exercised on both sides of its limit, so a review of the record
shows what was judged and not only the verdict.
"""

import unittest

from q6013_legacy_class_2_screening_table_logic import (
    BURN_IN_STEP,
    LIMIT_TOLERANCE,
    MAX_CUMULATIVE_ATTRITION_PERCENT,
    SCREENING_SEQUENCE,
    assess_legacy_class_2_screening,
    burn_in_pda,
    cumulative_attrition,
    deliverable_check,
    screening_chain,
    sequence_order,
    validate_step,
)


def _step(name, **extra):
    record = {"step": name}
    record.update(extra)
    return record


def _steps(**overrides):
    steps = [_step(name) for name in SCREENING_SEQUENCE]
    for name, extra in overrides.items():
        key = name.replace("_", "-")
        for record in steps:
            if record["step"] == key:
                record.update(extra)
    return steps


def _spec(**overrides):
    spec = {
        "lot_size": 400,
        "steps": _steps(burn_in={"rejects": 8}, final_electrical={"rejects": 2}),
        "burn_in_allowable_percent": 5.0,
        "required_quantity": 350,
    }
    spec.update(overrides)
    return spec


class StepValidationTests(unittest.TestCase):
    def test_a_step_defaults_to_testing_the_whole_population(self):
        record = validate_step(_step("stabilization-bake"), 400)
        self.assertEqual(record["devices_tested"], 400)
        self.assertTrue(record["full_coverage"])

    def test_a_sampled_step_is_recorded_as_incomplete_coverage(self):
        record = validate_step(_step("external-visual", devices_tested=40), 400)
        self.assertFalse(record["full_coverage"])
        self.assertEqual(record["untested"], 360)

    def test_surviving_population_drops_by_the_rejects(self):
        record = validate_step(_step("burn-in", rejects=12), 400)
        self.assertEqual(record["surviving"], 388)

    def test_step_outside_the_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            validate_step(_step("radiation-screen"), 400)

    def test_testing_more_devices_than_entered_is_refused(self):
        with self.assertRaises(ValueError):
            validate_step(_step("burn-in", devices_tested=500), 400)

    def test_more_rejects_than_devices_tested_is_refused(self):
        with self.assertRaises(ValueError):
            validate_step(_step("burn-in", devices_tested=100, rejects=101), 400)

    def test_an_empty_population_is_refused(self):
        with self.assertRaises(ValueError):
            validate_step(_step("burn-in"), 0)

    def test_non_mapping_step_is_refused(self):
        with self.assertRaises(ValueError):
            validate_step(["burn-in"], 400)


class SequenceOrderTests(unittest.TestCase):
    def test_the_declared_sequence_is_in_order(self):
        self.assertTrue(sequence_order(list(SCREENING_SEQUENCE))["in_order"])

    def test_a_swapped_pair_names_the_first_out_of_order_step(self):
        names = ["stabilization-bake", "burn-in", "temperature-cycling"]
        result = sequence_order(names)
        self.assertFalse(result["in_order"])
        self.assertEqual(result["first_out_of_order"], "temperature-cycling")

    def test_an_unknown_step_name_is_refused(self):
        with self.assertRaises(ValueError):
            sequence_order(["burn-in", "radiation-screen"])

    def test_non_list_names_are_refused(self):
        with self.assertRaises(ValueError):
            sequence_order("burn-in")


class ChainTests(unittest.TestCase):
    def test_survivors_carry_from_one_step_to_the_next(self):
        chain = screening_chain(
            _steps(temperature_cycling={"rejects": 5}, burn_in={"rejects": 10}),
            400,
        )
        entering = {r["step"]: r["entering"] for r in chain["steps"]}
        self.assertEqual(entering["burn-in"], 395)
        self.assertEqual(chain["surviving"], 385)

    def test_a_declared_population_that_does_not_follow_is_refused(self):
        steps = _steps(temperature_cycling={"rejects": 5})
        for record in steps:
            if record["step"] == "burn-in":
                record["entering"] = 400
        with self.assertRaises(ValueError):
            screening_chain(steps, 400)

    def test_a_declared_population_that_follows_is_accepted(self):
        steps = _steps(temperature_cycling={"rejects": 5})
        for record in steps:
            if record["step"] == "burn-in":
                record["entering"] = 395
        chain = screening_chain(steps, 400)
        self.assertEqual(chain["surviving"], 395)

    def test_a_repeated_step_is_refused(self):
        steps = _steps()
        steps.append(_step("burn-in"))
        with self.assertRaises(ValueError):
            screening_chain(steps, 400)

    def test_absent_steps_are_named(self):
        chain = screening_chain(_steps()[:4], 400)
        self.assertIn(BURN_IN_STEP, chain["absent_steps"])

    def test_an_empty_step_list_is_refused(self):
        with self.assertRaises(ValueError):
            screening_chain([], 400)


class BurnInTests(unittest.TestCase):
    def test_rate_is_taken_on_the_entered_population(self):
        result = burn_in_pda(400, 8, 5.0)
        self.assertAlmostEqual(result["percent_defective"], 2.0, places=9)
        self.assertTrue(result["accepted"])

    def test_a_rate_landing_exactly_on_the_allowance_is_accepted(self):
        result = burn_in_pda(400, 20, 5.0)
        self.assertAlmostEqual(result["percent_defective"], 5.0, places=9)
        self.assertTrue(result["accepted"])

    def test_a_rate_past_the_allowance_rejects(self):
        result = burn_in_pda(400, 24, 5.0)
        self.assertFalse(result["accepted"])

    def test_more_failures_than_devices_entered_is_refused(self):
        with self.assertRaises(ValueError):
            burn_in_pda(100, 101, 5.0)

    def test_an_allowance_outside_a_percentage_is_refused(self):
        with self.assertRaises(ValueError):
            burn_in_pda(400, 8, 140.0)


class AttritionAndDeliveryTests(unittest.TestCase):
    def test_attrition_exactly_on_the_cap_is_accepted(self):
        result = cumulative_attrition(400, 360)
        self.assertAlmostEqual(
            result["attrition_percent"], MAX_CUMULATIVE_ATTRITION_PERCENT, places=9
        )
        self.assertTrue(result["accepted"])

    def test_attrition_past_the_cap_rejects(self):
        result = cumulative_attrition(400, 300)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["removed"], 100)

    def test_more_survivors_than_the_lot_is_refused(self):
        with self.assertRaises(ValueError):
            cumulative_attrition(400, 401)

    def test_a_short_screened_population_reports_the_shortfall(self):
        result = deliverable_check(340, 350)
        self.assertEqual(result["shortfall"], 10)
        self.assertFalse(result["accepted"])

    def test_an_exact_deliverable_quantity_is_accepted(self):
        self.assertTrue(deliverable_check(350, 350)["accepted"])

    def test_a_zero_required_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            deliverable_check(350, 0)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_run_screens_the_lot(self):
        result = assess_legacy_class_2_screening(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "lot-screened")
        self.assertEqual(result["findings"], [])

    def test_a_sampled_step_holds_the_run(self):
        spec = _spec(
            steps=_steps(
                burn_in={"rejects": 8}, external_visual={"devices_tested": 40}
            )
        )
        result = assess_legacy_class_2_screening(spec)
        self.assertIn("external-visual", result["incomplete_steps"])
        self.assertEqual(result["disposition"], "reject-screening-run")

    def test_a_burn_in_rate_past_its_allowance_holds_the_run(self):
        result = assess_legacy_class_2_screening(
            _spec(steps=_steps(burn_in={"rejects": 30}))
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("burn-in" in item for item in result["findings"]))

    def test_attrition_past_the_cap_holds_an_otherwise_clean_run(self):
        result = assess_legacy_class_2_screening(
            _spec(
                steps=_steps(
                    temperature_cycling={"rejects": 30},
                    burn_in={"rejects": 18},
                ),
                burn_in_allowable_percent=20.0,
                required_quantity=300,
            )
        )
        self.assertFalse(result["attrition"]["accepted"])
        self.assertFalse(result["accepted"])

    def test_a_short_delivery_is_reported_after_a_clean_screen(self):
        result = assess_legacy_class_2_screening(_spec(required_quantity=395))
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("short of" in item for item in result["findings"])
        )

    def test_a_truncated_sequence_names_the_absent_steps(self):
        result = assess_legacy_class_2_screening(
            _spec(steps=_steps()[:4], required_quantity=300)
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("did not run" in item for item in result["findings"])
        )

    def test_missing_steps_key_is_refused(self):
        spec = _spec()
        del spec["steps"]
        with self.assertRaises(ValueError):
            assess_legacy_class_2_screening(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_2_screening(["not", "a", "mapping"])

    def test_named_constants_are_representation_sized_or_bounded(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertLess(MAX_CUMULATIVE_ATTRITION_PERCENT, 100.0)
        self.assertEqual(len(SCREENING_SEQUENCE), 8)
        self.assertIn(BURN_IN_STEP, SCREENING_SEQUENCE)


if __name__ == "__main__":
    unittest.main()
