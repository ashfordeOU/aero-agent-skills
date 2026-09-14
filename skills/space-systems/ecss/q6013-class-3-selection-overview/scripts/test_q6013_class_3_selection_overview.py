"""Contract tests for the clause 6.2.1 lowest-class selection duty logic."""

import unittest

from q6013_class_3_selection_overview_logic import (
    COVERAGE_TOLERANCE,
    DUTY_STATES,
    SELECTION_CATEGORIES,
    SELECTION_DUTIES,
    assess_class3_selection,
    component_category,
    component_dispositions,
    duty_disposition,
    evaluate_component_selection,
    outstanding_duties,
    selection_coverage,
    validate_duty_register,
    validate_identifier,
)


def evidenced(reference="SEL-001"):
    """Return a duty declaration carrying an evidence reference."""
    return {"state": "evidenced", "evidence": reference}


def all_evidenced(**overrides):
    """Return a duty mapping where every register duty is evidenced."""
    declared = {duty: evidenced() for duty in SELECTION_DUTIES}
    declared.update(overrides)
    return declared


def component(**overrides):
    """Return a fully evidenced candidate component with optional overrides."""
    base = {"component": "CMP-100", "duties": all_evidenced()}
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_identifier("  CMP-100 ", "component"), "CMP-100")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("  ", "component")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(3.5, "component")


class ValidateDutyRegisterTests(unittest.TestCase):
    def test_default_register_weights_sum_to_unity(self):
        total = sum(entry["weight"] for entry in validate_duty_register().values())
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_default_register_is_returned_when_omitted(self):
        self.assertEqual(sorted(validate_duty_register()), sorted(SELECTION_DUTIES))

    def test_register_keeps_at_least_one_mandatory_duty(self):
        mandatory = [
            duty
            for duty, entry in validate_duty_register().items()
            if entry["mandatory"]
        ]
        self.assertGreaterEqual(len(mandatory), 1)

    def test_register_without_a_mandatory_duty_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_register(
                {"known-defect-review": {"weight": 1.0, "mandatory": False}}
            )

    def test_weights_not_summing_to_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_register(
                {"application-suitability": {"weight": 0.5, "mandatory": True}}
            )

    def test_non_boolean_mandatory_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_register(
                {"application-suitability": {"weight": 1.0, "mandatory": "yes"}}
            )

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_register({})


class DutyDispositionTests(unittest.TestCase):
    def setUp(self):
        self.register = validate_duty_register()

    def test_evidenced_duty_is_credited(self):
        record = duty_disposition(
            "application-suitability", evidenced(), self.register
        )
        self.assertTrue(record["credited"])
        self.assertTrue(record["applicable"])

    def test_asserted_duty_is_not_credited(self):
        record = duty_disposition(
            "application-suitability", {"state": "asserted"}, self.register
        )
        self.assertFalse(record["credited"])
        self.assertIn("asserted", record["note"])

    def test_undeclared_duty_is_open(self):
        record = duty_disposition("application-suitability", None, self.register)
        self.assertEqual(record["state"], "open")
        self.assertFalse(record["credited"])

    def test_discretionary_duty_dropped_on_a_justification(self):
        record = duty_disposition(
            "obsolescence-outlook",
            {"state": "not-applicable", "justification": "single short campaign"},
            self.register,
        )
        self.assertFalse(record["applicable"])
        self.assertFalse(record["credited"])

    def test_discretionary_duty_without_a_justification_stays_applicable(self):
        record = duty_disposition(
            "obsolescence-outlook", {"state": "not-applicable"}, self.register
        )
        self.assertTrue(record["applicable"])
        self.assertIn("without a recorded justification", record["note"])

    def test_mandatory_duty_may_not_be_claimed_not_applicable(self):
        record = duty_disposition(
            "application-suitability",
            {"state": "not-applicable", "justification": "the part is simple"},
            self.register,
        )
        self.assertTrue(record["applicable"])
        self.assertEqual(record["state"], "open")
        self.assertIn("mandatory", record["note"])

    def test_evidenced_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            duty_disposition(
                "application-suitability", {"state": "evidenced"}, self.register
            )

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            duty_disposition(
                "application-suitability", {"state": "probably"}, self.register
            )

    def test_unknown_duty_rejected(self):
        with self.assertRaises(ValueError):
            duty_disposition("colour-check", evidenced(), self.register)

    def test_declared_states_are_the_published_set(self):
        self.assertEqual(len(DUTY_STATES), 4)


class ComponentDispositionTests(unittest.TestCase):
    def test_every_register_duty_is_dispositioned(self):
        records = component_dispositions({})
        self.assertEqual(len(records), len(SELECTION_DUTIES))

    def test_dispositions_are_sorted_by_duty(self):
        records = component_dispositions(all_evidenced())
        names = [record["duty"] for record in records]
        self.assertEqual(names, sorted(names))

    def test_duty_outside_the_register_rejected(self):
        with self.assertRaises(ValueError):
            component_dispositions({"colour-check": evidenced()})

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            component_dispositions(["application-suitability"])


class SelectionCoverageTests(unittest.TestCase):
    def test_everything_evidenced_is_unity(self):
        records = component_dispositions(all_evidenced())
        self.assertAlmostEqual(selection_coverage(records), 1.0, places=9)

    def test_nothing_declared_is_zero(self):
        records = component_dispositions({})
        self.assertAlmostEqual(selection_coverage(records), 0.0, places=9)

    def test_one_open_discretionary_duty_costs_its_weight(self):
        records = component_dispositions(
            all_evidenced(**{"known-defect-review": {"state": "asserted"}})
        )
        self.assertAlmostEqual(selection_coverage(records), 0.85, places=9)

    def test_a_dropped_duty_leaves_the_denominator(self):
        records = component_dispositions(
            all_evidenced(
                **{
                    "obsolescence-outlook": {
                        "state": "not-applicable",
                        "justification": "single short campaign",
                    }
                }
            )
        )
        self.assertAlmostEqual(selection_coverage(records), 1.0, places=9)

    def test_empty_disposition_list_rejected(self):
        with self.assertRaises(ValueError):
            selection_coverage([])


class OutstandingDutyTests(unittest.TestCase):
    def test_nothing_outstanding_when_all_evidenced(self):
        self.assertEqual(outstanding_duties(component_dispositions(all_evidenced())), ())

    def test_open_duty_is_outstanding(self):
        records = component_dispositions(
            all_evidenced(**{"known-defect-review": {"state": "open"}})
        )
        self.assertEqual(outstanding_duties(records), ("known-defect-review",))

    def test_dropped_duty_is_not_outstanding(self):
        records = component_dispositions(
            all_evidenced(
                **{
                    "obsolescence-outlook": {
                        "state": "not-applicable",
                        "justification": "single short campaign",
                    }
                }
            )
        )
        self.assertEqual(outstanding_duties(records), ())

    def test_outstanding_list_is_sorted(self):
        records = component_dispositions({})
        owed = outstanding_duties(records)
        self.assertEqual(list(owed), sorted(owed))


class ComponentCategoryTests(unittest.TestCase):
    def test_all_evidenced_is_closed(self):
        records = component_dispositions(all_evidenced())
        self.assertEqual(component_category(records, 1.0, 0.7), "selection-closed")

    def test_mandatory_gap_blocks_whatever_the_coverage(self):
        records = component_dispositions(
            all_evidenced(**{"application-suitability": {"state": "asserted"}})
        )
        self.assertEqual(component_category(records, 0.8, 0.7), "selection-blocked")

    def test_discretionary_gap_above_the_floor_is_closed(self):
        records = component_dispositions(
            all_evidenced(**{"known-defect-review": {"state": "asserted"}})
        )
        self.assertEqual(component_category(records, 0.85, 0.7), "selection-closed")

    def test_coverage_below_the_floor_is_open(self):
        records = component_dispositions(
            all_evidenced(
                **{
                    "known-defect-review": {"state": "asserted"},
                    "obsolescence-outlook": {"state": "asserted"},
                    "procurement-availability": {"state": "asserted"},
                }
            )
        )
        self.assertEqual(component_category(records, 0.65, 0.7), "selection-open")

    def test_exactly_met_floor_counts_as_met(self):
        records = component_dispositions(
            all_evidenced(**{"known-defect-review": {"state": "asserted"}})
        )
        self.assertEqual(component_category(records, 0.85, 0.85), "selection-closed")

    def test_coverage_outside_the_unit_interval_rejected(self):
        records = component_dispositions(all_evidenced())
        with self.assertRaises(ValueError):
            component_category(records, 1.5, 0.7)

    def test_floor_outside_the_unit_interval_rejected(self):
        records = component_dispositions(all_evidenced())
        with self.assertRaises(ValueError):
            component_category(records, 1.0, -0.1)

    def test_categories_are_the_published_set(self):
        self.assertEqual(len(SELECTION_CATEGORIES), 3)


class EvaluateComponentSelectionTests(unittest.TestCase):
    def test_fully_evidenced_component_is_closed(self):
        record = evaluate_component_selection(component())
        self.assertEqual(record["category"], "selection-closed")
        self.assertAlmostEqual(record["coverage"], 1.0, places=9)
        self.assertEqual(record["outstanding"], ())

    def test_mandatory_gap_is_reported_separately(self):
        record = evaluate_component_selection(
            component(
                duties=all_evidenced(
                    **{"excluded-technology-check": {"state": "asserted"}}
                )
            )
        )
        self.assertEqual(record["mandatory_outstanding"], ("excluded-technology-check",))
        self.assertEqual(record["category"], "selection-blocked")

    def test_notes_carry_the_reason_a_duty_earned_nothing(self):
        record = evaluate_component_selection(
            component(duties=all_evidenced(**{"known-defect-review": {"state": "asserted"}}))
        )
        self.assertTrue(any("asserted" in note for note in record["notes"]))

    def test_missing_duties_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_component_selection({"component": "CMP-100"})

    def test_missing_component_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_component_selection({"duties": all_evidenced()})

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_component_selection(["CMP-100"])


class AssessClass3SelectionTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "components": [
                component(),
                component(component="CMP-101"),
            ]
        }
        base.update(overrides)
        return base

    def test_fully_evidenced_list_closes(self):
        result = assess_class3_selection(self._spec())
        self.assertEqual(result["verdict"], "selection-closed")
        self.assertAlmostEqual(result["list_coverage"], 1.0, places=9)
        self.assertEqual(result["outstanding_duties"], ())

    def test_one_mandatory_gap_blocks_the_whole_list(self):
        spec = self._spec(
            components=[
                component(),
                component(
                    component="CMP-102",
                    duties=all_evidenced(
                        **{"manufacturer-identification": {"state": "asserted"}}
                    ),
                ),
            ]
        )
        result = assess_class3_selection(spec)
        self.assertEqual(result["verdict"], "selection-blocked")
        self.assertEqual(result["category_counts"]["selection-blocked"], 1)

    def test_governing_component_is_the_lowest_coverage(self):
        spec = self._spec(
            components=[
                component(),
                component(component="CMP-102", duties={}),
            ]
        )
        result = assess_class3_selection(spec)
        self.assertEqual(result["governing_component"]["component"], "CMP-102")

    def test_governing_tie_breaks_on_the_component_identifier(self):
        spec = self._spec(
            components=[component(component="CMP-900"), component(component="CMP-110")]
        )
        result = assess_class3_selection(spec)
        self.assertEqual(result["governing_component"]["component"], "CMP-110")

    def test_findings_rank_the_blocked_component_first(self):
        spec = self._spec(
            components=[
                component(
                    component="CMP-100",
                    duties=all_evidenced(
                        **{
                            "known-defect-review": {"state": "asserted"},
                            "obsolescence-outlook": {"state": "asserted"},
                            "procurement-availability": {"state": "asserted"},
                        }
                    ),
                ),
                component(
                    component="CMP-102",
                    duties=all_evidenced(
                        **{"operating-range-coverage": {"state": "asserted"}}
                    ),
                ),
            ]
        )
        result = assess_class3_selection(spec)
        self.assertEqual(result["findings"][0]["severity"], 0)
        self.assertEqual(result["findings"][0]["component"], "CMP-102")

    def test_outstanding_duties_are_unioned_across_the_list(self):
        spec = self._spec(
            components=[
                component(
                    component="CMP-100",
                    duties=all_evidenced(**{"known-defect-review": {"state": "open"}}),
                ),
                component(
                    component="CMP-101",
                    duties=all_evidenced(
                        **{"procurement-availability": {"state": "open"}}
                    ),
                ),
            ]
        )
        result = assess_class3_selection(spec)
        self.assertEqual(
            result["outstanding_duties"],
            ("known-defect-review", "procurement-availability"),
        )

    def test_raising_the_floor_can_open_a_closed_list(self):
        spec = self._spec(
            components=[
                component(
                    component="CMP-100",
                    duties=all_evidenced(**{"known-defect-review": {"state": "open"}}),
                )
            ]
        )
        loose = assess_class3_selection(dict(spec, floor=0.7))
        tight = assess_class3_selection(dict(spec, floor=0.95))
        self.assertEqual(loose["verdict"], "selection-closed")
        self.assertEqual(tight["verdict"], "selection-open")

    def test_exactly_met_list_floor_counts_as_met(self):
        result = assess_class3_selection(self._spec(floor=1.0))
        self.assertTrue(result["meets_floor"])
        self.assertEqual(result["verdict"], "selection-closed")

    def test_duplicate_component_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_selection(self._spec(components=[component(), component()]))

    def test_empty_component_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_selection(self._spec(components=[]))

    def test_missing_components_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_selection({"floor": 0.7})

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_selection(self._spec(floor=1.1))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_selection(["components"])

    def test_tolerance_is_representation_sized(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
