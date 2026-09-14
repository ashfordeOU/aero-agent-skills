"""Contract tests for the clause 7.6.2 treatment of failed bare cells.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a policy that fixes
no treatment for a listed mode, a component exhibiting a mode nobody
declared, the one-mode-is-enough withdrawal, a failed test article kept
for its evidence, and a lot left short by its own withdrawals.
"""

import unittest

from e2008_failed_bare_cell_components_logic import (
    CELL_CRACK,
    COATING_DAMAGE,
    CONTACT_DELAMINATION,
    DEFAULT_LISTED_FAILURE_MODES,
    DEFAULT_TREATMENT_POLICY,
    DELIVERABLE,
    ELECTRICAL_OPEN_CIRCUIT,
    FAILED_COMPONENTS_TREATED,
    LOT_QUANTITY_SHORTFALL,
    POWER_DEGRADATION,
    RELEASED_TO_LOT,
    SEGREGATED_FOR_INVESTIGATION,
    SEGREGATED_FOR_REWORK,
    TEST_ARTICLE,
    TREATMENT_NOT_ESTABLISHED,
    WITHDRAWN_AND_SCRAPPED,
    assess_failed_bare_cell_components,
    batch_treatments,
    delivered_quantity,
    lot_quantity_shortfall,
    nonconformance_records,
    treatment_for_component,
    validate_component_record,
    validate_listed_failure_modes,
    validate_treatment_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_TREATMENT_POLICY)
    policy.update(overrides)
    return policy


def _component(identifier="cc-01", modes=(), role=DELIVERABLE, cycles=0, **extra):
    record = {
        "id": identifier,
        "role": role,
        "failure_modes": list(modes),
        "rework_cycles_done": cycles,
    }
    record.update(extra)
    return record


def _batch():
    return [
        _component("cc-01"),
        _component("cc-02"),
        _component("cc-03", modes=[CELL_CRACK]),
    ]


def _case(**overrides):
    case = {"components": _batch(), "ordered_quantity": 2}
    case.update(overrides)
    return case


class ListedModeTests(unittest.TestCase):
    def test_the_default_mode_list_validates(self):
        listed = validate_listed_failure_modes(DEFAULT_LISTED_FAILURE_MODES)
        self.assertIn(CELL_CRACK, listed)

    def test_an_empty_mode_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_listed_failure_modes([])

    def test_a_repeated_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_listed_failure_modes([CELL_CRACK, CELL_CRACK])

    def test_an_unnamed_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_listed_failure_modes(["  "])


class PolicyTests(unittest.TestCase):
    def test_the_default_policy_covers_every_listed_mode(self):
        settings = validate_treatment_policy(DEFAULT_TREATMENT_POLICY)
        self.assertEqual(len(settings["listed_modes"]), len(DEFAULT_LISTED_FAILURE_MODES))

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_treatment_policy("reworkable_modes")

    def test_a_mode_in_both_treatment_sets_rejected(self):
        with self.assertRaises(ValueError):
            validate_treatment_policy(
                _policy(
                    reworkable_modes=(CONTACT_DELAMINATION, CELL_CRACK),
                )
            )

    def test_a_listed_mode_with_no_treatment_rejected(self):
        with self.assertRaises(ValueError):
            validate_treatment_policy(
                _policy(reworkable_modes=(CONTACT_DELAMINATION,))
            )

    def test_a_policy_mode_outside_the_listed_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_treatment_policy(
                _policy(reworkable_modes=(CONTACT_DELAMINATION, COATING_DAMAGE, "warped-cell"))
            )

    def test_a_negative_rework_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_treatment_policy(_policy(max_rework_cycles=-1))

    def test_a_non_boolean_segregation_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_treatment_policy(_policy(segregation_required="yes"))

    def test_a_no_rework_policy_is_legitimate(self):
        settings = validate_treatment_policy(_policy(max_rework_cycles=0))
        self.assertEqual(settings["max_rework_cycles"], 0)


class ComponentRecordTests(unittest.TestCase):
    def test_a_component_record_is_read_back(self):
        record = validate_component_record(_component(modes=[COATING_DAMAGE]))
        self.assertEqual(record["id"], "cc-01")
        self.assertEqual(record["failure_modes"], (COATING_DAMAGE,))

    def test_a_blank_component_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_component_record(_component(identifier=" "))

    def test_an_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_component_record(_component(role="spare"))

    def test_a_mode_the_criteria_never_listed_rejected(self):
        with self.assertRaises(ValueError):
            validate_component_record(_component(modes=["warped-cell"]))

    def test_a_non_list_mode_field_rejected(self):
        record = _component()
        record["failure_modes"] = CELL_CRACK
        with self.assertRaises(ValueError):
            validate_component_record(record)

    def test_a_repeated_mode_is_recorded_once(self):
        record = validate_component_record(_component(modes=[CELL_CRACK, CELL_CRACK]))
        self.assertEqual(record["failure_modes"], (CELL_CRACK,))

    def test_a_negative_rework_history_rejected(self):
        with self.assertRaises(ValueError):
            validate_component_record(_component(cycles=-2))

    def test_a_component_with_no_role_stated_is_a_deliverable(self):
        record = validate_component_record({"id": "cc-09"})
        self.assertEqual(record["role"], DELIVERABLE)


class TreatmentTests(unittest.TestCase):
    def test_a_clean_component_is_released_to_the_lot(self):
        treatment = treatment_for_component(_component())
        self.assertEqual(treatment["disposition"], RELEASED_TO_LOT)
        self.assertFalse(treatment["withdrawn_from_lot"])
        self.assertTrue(treatment["counts_toward_delivery"])

    def test_one_listed_mode_is_enough_to_withdraw_a_component(self):
        treatment = treatment_for_component(_component(modes=[COATING_DAMAGE]))
        self.assertTrue(treatment["withdrawn_from_lot"])
        self.assertFalse(treatment["counts_toward_delivery"])

    def test_an_irreversible_mode_scraps_the_component(self):
        treatment = treatment_for_component(_component(modes=[CELL_CRACK]))
        self.assertEqual(treatment["disposition"], WITHDRAWN_AND_SCRAPPED)
        self.assertFalse(treatment["rework_permitted"])

    def test_a_reworkable_mode_opens_rework_and_a_retest(self):
        treatment = treatment_for_component(_component(modes=[CONTACT_DELAMINATION]))
        self.assertEqual(treatment["disposition"], SEGREGATED_FOR_REWORK)
        self.assertTrue(treatment["rework_permitted"])
        self.assertTrue(treatment["retest_required"])

    def test_a_component_out_of_rework_cycles_is_scrapped(self):
        treatment = treatment_for_component(
            _component(modes=[CONTACT_DELAMINATION], cycles=1)
        )
        self.assertEqual(treatment["disposition"], WITHDRAWN_AND_SCRAPPED)
        self.assertEqual(treatment["rework_cycles_left"], 0)

    def test_one_irreversible_mode_overrides_a_reworkable_one(self):
        treatment = treatment_for_component(
            _component(modes=[CONTACT_DELAMINATION, ELECTRICAL_OPEN_CIRCUIT])
        )
        self.assertEqual(treatment["disposition"], WITHDRAWN_AND_SCRAPPED)

    def test_a_failed_test_article_is_retained_for_its_evidence(self):
        treatment = treatment_for_component(
            _component(modes=[CELL_CRACK], role=TEST_ARTICLE)
        )
        self.assertEqual(treatment["disposition"], SEGREGATED_FOR_INVESTIGATION)
        self.assertTrue(treatment["withdrawn_from_lot"])

    def test_a_clean_test_article_never_counted_as_delivered(self):
        treatment = treatment_for_component(_component(role=TEST_ARTICLE))
        self.assertEqual(treatment["disposition"], RELEASED_TO_LOT)
        self.assertFalse(treatment["counts_toward_delivery"])

    def test_segregation_and_a_nonconformance_follow_the_failure(self):
        treatment = treatment_for_component(_component(modes=[COATING_DAMAGE]))
        self.assertTrue(treatment["segregation_required"])
        self.assertTrue(treatment["nonconformance_required"])

    def test_a_return_by_retest_request_is_recorded_not_granted(self):
        treatment = treatment_for_component(
            _component(modes=[CONTACT_DELAMINATION], return_requested_by_retest=True)
        )
        self.assertTrue(treatment["withdrawn_from_lot"])
        self.assertTrue(
            any("re-test alone" in finding for finding in treatment["findings"])
        )

    def test_a_policy_without_a_retest_step_says_so(self):
        treatment = treatment_for_component(
            _component(modes=[CONTACT_DELAMINATION]),
            DEFAULT_LISTED_FAILURE_MODES,
            _policy(retest_after_rework_required=False),
        )
        self.assertTrue(treatment["rework_permitted"])
        self.assertFalse(treatment["retest_required"])

    def test_a_clean_component_raises_no_finding(self):
        self.assertEqual(treatment_for_component(_component())["findings"], [])


class BatchTests(unittest.TestCase):
    def test_a_batch_is_treated_component_by_component(self):
        treatments = batch_treatments(_batch())
        self.assertEqual(len(treatments), 3)

    def test_a_duplicate_component_id_rejected(self):
        components = _batch()
        components[2]["id"] = "cc-01"
        with self.assertRaises(ValueError):
            batch_treatments(components)

    def test_an_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            batch_treatments([])

    def test_only_released_deliverables_count_toward_delivery(self):
        self.assertEqual(delivered_quantity(batch_treatments(_batch())), 2)

    def test_the_shortfall_is_what_the_withdrawals_left(self):
        treatments = batch_treatments(_batch())
        self.assertEqual(lot_quantity_shortfall(treatments, 3), 1)

    def test_a_lot_that_still_meets_its_order_is_not_short(self):
        treatments = batch_treatments(_batch())
        self.assertEqual(lot_quantity_shortfall(treatments, 2), 0)

    def test_a_surplus_lot_reports_no_negative_shortfall(self):
        treatments = batch_treatments(_batch())
        self.assertEqual(lot_quantity_shortfall(treatments, 1), 0)

    def test_a_non_integer_order_quantity_rejected(self):
        treatments = batch_treatments(_batch())
        with self.assertRaises(ValueError):
            lot_quantity_shortfall(treatments, 2.5)

    def test_every_withdrawn_component_needs_a_nonconformance_entry(self):
        records = nonconformance_records(batch_treatments(_batch()))
        self.assertEqual(records, ("cc-03",))


class AssessmentTests(unittest.TestCase):
    def test_a_treated_batch_that_still_meets_its_order_closes_clean(self):
        result = assess_failed_bare_cell_components(_case())
        self.assertEqual(result["verdict"], FAILED_COMPONENTS_TREATED)
        self.assertEqual(result["quantity_shortfall"], 0)

    def test_withdrawals_can_leave_the_lot_short(self):
        result = assess_failed_bare_cell_components(_case(ordered_quantity=3))
        self.assertEqual(result["verdict"], LOT_QUANTITY_SHORTFALL)
        self.assertEqual(result["quantity_shortfall"], 1)

    def test_a_policy_with_an_unplaced_mode_establishes_no_treatment(self):
        result = assess_failed_bare_cell_components(
            _case(), _policy(irreversible_modes=(CELL_CRACK,))
        )
        self.assertEqual(result["verdict"], TREATMENT_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_the_scrapped_rework_and_retained_lists_are_separated(self):
        components = [
            _component("cc-01"),
            _component("cc-02", modes=[POWER_DEGRADATION]),
            _component("cc-03", modes=[COATING_DAMAGE]),
            _component("cc-04", modes=[CELL_CRACK], role=TEST_ARTICLE),
        ]
        result = assess_failed_bare_cell_components(
            _case(components=components, ordered_quantity=1)
        )
        self.assertEqual(result["scrapped_components"], ["cc-02"])
        self.assertEqual(result["rework_components"], ["cc-03"])
        self.assertEqual(result["retained_components"], ["cc-04"])

    def test_every_withdrawn_component_is_named(self):
        result = assess_failed_bare_cell_components(_case())
        self.assertEqual(result["withdrawn_components"], ["cc-03"])

    def test_a_batch_with_nothing_failed_needs_no_segregation(self):
        result = assess_failed_bare_cell_components(
            _case(components=[_component("cc-01"), _component("cc-02")])
        )
        self.assertFalse(result["segregation_required"])
        self.assertEqual(result["nonconformance_records"], [])

    def test_the_delivered_and_ordered_quantities_travel_with_the_verdict(self):
        result = assess_failed_bare_cell_components(_case())
        self.assertEqual(result["delivered_quantity"], 2)
        self.assertEqual(result["ordered_quantity"], 2)

    def test_a_missing_components_list_rejected(self):
        case = _case()
        del case["components"]
        with self.assertRaises(ValueError):
            assess_failed_bare_cell_components(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_bare_cell_components(["components"])

    def test_a_non_integer_ordered_quantity_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_bare_cell_components(_case(ordered_quantity="two"))


if __name__ == "__main__":
    unittest.main()
