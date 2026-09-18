"""Contract tests for the clause 5.2.3 customer review board sitting logic."""

import unittest

from q1009_customer_meeting_logic import (
    CONFIRMATION_STATES,
    IMPACT_DIMENSIONS,
    IMPACT_TOLERANCE,
    MANDATORY_CUSTOMER_FUNCTIONS,
    SUPPLIER_FUNCTION,
    assess_customer_meeting,
    assess_higher_level_impacts,
    budget_impact,
    confirmation_status,
    convening_status,
    interface_impact,
    normalize_token,
    schedule_impact,
    validate_attendance,
)


def attendance(absent=(), supplier=True):
    roster = [
        {"function": f, "present": f not in absent} for f in MANDATORY_CUSTOMER_FUNCTIONS
    ]
    roster.append({"function": SUPPLIER_FUNCTION, "present": supplier})
    return roster


def parameters(value=4.8):
    return [
        {"name": "harness-mass-kg", "value": value, "lower": 0.0, "upper": 5.0},
        {"name": "connector-keying-angle-deg", "value": 45.0, "lower": 44.5, "upper": 45.5},
    ]


def impacts(consumed=4.0, allocated=10.0, value=4.8, slip=2, available_float=5):
    return {
        "system-budget": {"consumed": consumed, "allocated": allocated},
        "interfaces": parameters(value),
        "schedule": {"slip_days": slip, "float_days": available_float},
    }


def statements(state="confirmed"):
    return [
        {"id": "cause-1", "kind": "cause", "state": state},
        {"id": "consequence-1", "kind": "consequence", "state": "confirmed"},
    ]


class NormalizeTests(unittest.TestCase):
    def test_case_and_spacing_normalised(self):
        self.assertEqual(normalize_token("Customer Chair"), "customer-chair")

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(" ")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(None)


class AttendanceTests(unittest.TestCase):
    def test_roster_returns_one_record_per_function(self):
        self.assertEqual(len(validate_attendance(attendance())), 4)

    def test_duplicate_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendance(attendance() + [{"function": "Customer Chair", "present": True}])

    def test_non_boolean_presence_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendance([{"function": "customer-chair", "present": "yes"}])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendance([{"function": "customer-chair"}])

    def test_empty_roster_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendance([])

    def test_full_attendance_is_quorate_and_can_confirm(self):
        status = convening_status(attendance())
        self.assertTrue(status["quorate"])
        self.assertTrue(status["confirmation_possible"])

    def test_absent_customer_function_breaks_quorum(self):
        status = convening_status(attendance(absent=("customer-engineering",)))
        self.assertFalse(status["quorate"])
        self.assertEqual(status["absent_customer_functions"], ("customer-engineering",))

    def test_absent_supplier_leaves_a_quorate_board_unable_to_confirm(self):
        status = convening_status(attendance(supplier=False))
        self.assertTrue(status["quorate"])
        self.assertFalse(status["confirmation_possible"])


class BudgetTests(unittest.TestCase):
    def test_share_is_the_consumed_fraction(self):
        self.assertAlmostEqual(budget_impact(4.0, 10.0)["share"], 0.4, places=9)

    def test_fully_consumed_allocation_is_not_exceeded(self):
        result = budget_impact(10.0, 10.0)
        self.assertAlmostEqual(result["share"], 1.0, places=9)
        self.assertFalse(result["exceeded"])

    def test_overrun_is_exceeded(self):
        self.assertTrue(budget_impact(11.0, 10.0)["exceeded"])

    def test_zero_allocation_rejected(self):
        with self.assertRaises(ValueError):
            budget_impact(1.0, 0.0)

    def test_negative_consumption_rejected(self):
        with self.assertRaises(ValueError):
            budget_impact(-1.0, 10.0)

    def test_non_finite_consumption_rejected(self):
        with self.assertRaises(ValueError):
            budget_impact(float("inf"), 10.0)

    def test_boolean_allocation_rejected(self):
        with self.assertRaises(ValueError):
            budget_impact(1.0, True)

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(IMPACT_TOLERANCE, 0.0)
        self.assertLess(IMPACT_TOLERANCE, 1e-6)


class InterfaceTests(unittest.TestCase):
    def test_in_range_parameters_conform(self):
        self.assertTrue(interface_impact(parameters())["conforming"])

    def test_value_above_the_upper_bound_is_non_conforming(self):
        result = interface_impact(parameters(value=5.4))
        self.assertFalse(result["conforming"])
        self.assertEqual(result["non_conforming"], ("harness-mass-kg",))

    def test_value_exactly_on_the_upper_bound_conforms(self):
        result = interface_impact(parameters(value=5.0))
        self.assertAlmostEqual(result["parameters"][0]["value"], 5.0, places=9)
        self.assertTrue(result["conforming"])

    def test_value_exactly_on_the_lower_bound_conforms(self):
        result = interface_impact(parameters(value=0.0))
        self.assertTrue(result["conforming"])

    def test_inverted_range_rejected(self):
        bad = [{"name": "p", "value": 1.0, "lower": 5.0, "upper": 1.0}]
        with self.assertRaises(ValueError):
            interface_impact(bad)

    def test_duplicate_parameter_rejected(self):
        with self.assertRaises(ValueError):
            interface_impact(parameters() + [
                {"name": "Harness Mass Kg", "value": 1.0, "lower": 0.0, "upper": 5.0}
            ])

    def test_missing_bound_rejected(self):
        with self.assertRaises(ValueError):
            interface_impact([{"name": "p", "value": 1.0, "lower": 0.0}])

    def test_empty_parameter_set_rejected(self):
        with self.assertRaises(ValueError):
            interface_impact([])


class ScheduleTests(unittest.TestCase):
    def test_slip_inside_the_float_leaves_float_remaining(self):
        result = schedule_impact(2, 5)
        self.assertEqual(result["float_remaining"], 3)
        self.assertFalse(result["float_exhausted"])

    def test_slip_equal_to_the_float_exhausts_it_without_delaying(self):
        result = schedule_impact(5, 5)
        self.assertTrue(result["float_exhausted"])
        self.assertFalse(result["critical_path_impact"])

    def test_slip_beyond_the_float_hits_the_critical_path(self):
        result = schedule_impact(7, 5)
        self.assertTrue(result["critical_path_impact"])
        self.assertEqual(result["delay_days"], 2)

    def test_zero_float_activity_is_delayed_by_any_slip(self):
        self.assertEqual(schedule_impact(1, 0)["delay_days"], 1)

    def test_negative_slip_rejected(self):
        with self.assertRaises(ValueError):
            schedule_impact(-1, 5)

    def test_non_integer_slip_rejected(self):
        with self.assertRaises(ValueError):
            schedule_impact(1.5, 5)

    def test_boolean_float_rejected(self):
        with self.assertRaises(ValueError):
            schedule_impact(1, True)


class HigherLevelImpactTests(unittest.TestCase):
    def test_clean_case_is_acceptable(self):
        result = assess_higher_level_impacts(impacts())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_every_dimension_reported(self):
        result = assess_higher_level_impacts(impacts())
        for dimension in IMPACT_DIMENSIONS:
            self.assertIn(dimension, result)

    def test_missing_dimension_rejected(self):
        partial = impacts()
        del partial["interfaces"]
        with self.assertRaises(ValueError):
            assess_higher_level_impacts(partial)

    def test_unknown_dimension_rejected(self):
        extra = impacts()
        extra["vibe"] = {}
        with self.assertRaises(ValueError):
            assess_higher_level_impacts(extra)

    def test_budget_overrun_reported_and_unacceptable(self):
        result = assess_higher_level_impacts(impacts(consumed=12.0))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("system budget" in f for f in result["findings"]))

    def test_interface_breach_reported_and_unacceptable(self):
        result = assess_higher_level_impacts(impacts(value=9.0))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("harness-mass-kg" in f for f in result["findings"]))

    def test_critical_path_slip_reported_and_unacceptable(self):
        result = assess_higher_level_impacts(impacts(slip=9))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("float" in f for f in result["findings"]))

    def test_exhausted_float_is_reported_but_still_acceptable(self):
        result = assess_higher_level_impacts(impacts(slip=5, available_float=5))
        self.assertTrue(result["acceptable"])
        self.assertTrue(any("whole activity float" in f for f in result["findings"]))

    def test_missing_budget_input_rejected(self):
        bad = impacts()
        del bad["system-budget"]["allocated"]
        with self.assertRaises(ValueError):
            assess_higher_level_impacts(bad)

    def test_non_mapping_impacts_rejected(self):
        with self.assertRaises(ValueError):
            assess_higher_level_impacts(list(IMPACT_DIMENSIONS))


class ConfirmationTests(unittest.TestCase):
    def test_all_confirmed_with_the_supplier_present(self):
        result = confirmation_status(statements(), True)
        self.assertTrue(result["all_confirmed"])
        self.assertIsNone(result["blocked_by"])

    def test_disputed_statement_blocks_confirmation(self):
        result = confirmation_status(statements("disputed"), True)
        self.assertFalse(result["all_confirmed"])
        self.assertEqual(result["disputed"], ("cause-1",))

    def test_open_statement_blocks_confirmation(self):
        result = confirmation_status(statements("open"), True)
        self.assertEqual(result["open"], ("cause-1",))
        self.assertEqual(result["blocked_by"], "unconfirmed-statements")

    def test_absent_supplier_reverts_every_statement_to_open(self):
        result = confirmation_status(statements(), False)
        self.assertFalse(result["all_confirmed"])
        self.assertEqual(result["blocked_by"], "supplier-not-present")
        self.assertEqual(len(result["open"]), 2)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_status([{"id": "c1", "kind": "cause", "state": "probably"}], True)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_status([{"id": "c1", "kind": "opinion", "state": "confirmed"}], True)

    def test_duplicate_statement_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_status(statements() + [
                {"id": "Cause 1", "kind": "cause", "state": "confirmed"}
            ], True)

    def test_non_boolean_presence_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_status(statements(), "yes")

    def test_empty_statement_set_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_status([], True)

    def test_state_vocabulary_is_closed(self):
        self.assertEqual(set(CONFIRMATION_STATES), {"confirmed", "disputed", "open"})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "attendance": attendance(),
            "impacts": impacts(),
            "statements": statements(),
        }
        spec.update(over)
        return spec

    def test_clean_sitting_can_decide_a_disposition(self):
        result = assess_customer_meeting(self._spec())
        self.assertTrue(result["disposition_decidable"])
        self.assertEqual(result["outcome"], "disposition-decidable")
        self.assertEqual(result["findings"], [])

    def test_absent_customer_function_makes_the_sitting_inquorate(self):
        result = assess_customer_meeting(
            self._spec(attendance=attendance(absent=("customer-chair",)))
        )
        self.assertEqual(result["outcome"], "not-quorate")
        self.assertFalse(result["disposition_decidable"])

    def test_absent_supplier_defers_pending_confirmation(self):
        result = assess_customer_meeting(self._spec(attendance=attendance(supplier=False)))
        self.assertEqual(result["outcome"], "deferred-pending-confirmation")
        self.assertTrue(any("supplier representative absent" in f for f in result["findings"]))

    def test_disputed_statement_defers_pending_confirmation(self):
        result = assess_customer_meeting(self._spec(statements=statements("disputed")))
        self.assertEqual(result["outcome"], "deferred-pending-confirmation")
        self.assertTrue(any("disputed" in f for f in result["findings"]))

    def test_impact_findings_do_not_block_a_decision(self):
        result = assess_customer_meeting(self._spec(impacts=impacts(slip=9)))
        self.assertTrue(result["disposition_decidable"])
        self.assertFalse(result["impacts_acceptable"])

    def test_impact_findings_reach_the_meeting_findings(self):
        result = assess_customer_meeting(self._spec(impacts=impacts(value=9.0)))
        self.assertTrue(any("harness-mass-kg" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["statements"]
        with self.assertRaises(ValueError):
            assess_customer_meeting(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_customer_meeting(["attendance"])


if __name__ == "__main__":
    unittest.main()
