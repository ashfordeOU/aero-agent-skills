"""Contract tests for the ultracleaning plan logic."""

import unittest

from q7054_ultracleaning_plan_logic import (
    BASELINE_NVR_MG_PER_01M2,
    BASELINE_PARTICULATE_LEVEL_UM,
    FINAL_VERIFICATION,
    MOLECULAR_VERIFICATION,
    PARTICULATE_VERIFICATION,
    assign_process,
    build_ultracleaning_plan,
    plan_coverage,
    qualified_processes,
    validate_item,
    validate_operation,
    verification_points_for,
)


def base_item(**overrides):
    """An aluminium bracket owed a level 100 surface and half a milligram."""
    item = {
        "id": "bracket-01",
        "material": "aluminium-alloy",
        "required_particulate_level_um": 100.0,
        "required_nvr_mg_per_01m2": 0.50,
        "sequence": 10,
    }
    item.update(overrides)
    return item


class ItemValidationTests(unittest.TestCase):
    def test_a_complete_item_validates(self):
        self.assertEqual(validate_item(base_item())["id"], "bracket-01")

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(base_item(material="beryllium"))

    def test_empty_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(base_item(id="  "))

    def test_non_positive_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(base_item(required_particulate_level_um=0.0))

    def test_float_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(base_item(sequence=10.5))

    def test_negative_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(base_item(sequence=-1))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(["bracket-01"])


class ProcessAssignmentTests(unittest.TestCase):
    def test_a_process_landing_exactly_on_the_requirement_qualifies(self):
        self.assertIn("carbon-dioxide-snow", qualified_processes(base_item()))

    def test_the_gentlest_qualified_process_is_assigned(self):
        self.assertEqual(assign_process(base_item())["process"], "carbon-dioxide-snow")

    def test_an_incompatible_process_is_never_offered(self):
        item = base_item(material="silver-coating")
        self.assertNotIn("plasma", qualified_processes(item))
        self.assertNotIn("aqueous-ultrasonic", qualified_processes(item))

    def test_a_composite_falls_back_to_the_aqueous_route(self):
        item = base_item(
            material="polymer-composite",
            required_particulate_level_um=50.0,
            required_nvr_mg_per_01m2=0.10,
        )
        self.assertEqual(assign_process(item)["process"], "aqueous-ultrasonic")

    def test_an_unreachable_pairing_returns_no_process_with_a_reason(self):
        item = base_item(
            material="magnesium-alloy",
            required_particulate_level_um=25.0,
            required_nvr_mg_per_01m2=0.01,
        )
        assignment = assign_process(item)
        self.assertIsNone(assignment["process"])
        self.assertIn("reaches level", assignment["reason"])

    def test_a_loose_requirement_admits_the_gentlest_wipe(self):
        item = base_item(
            required_particulate_level_um=400.0, required_nvr_mg_per_01m2=1.50
        )
        self.assertEqual(assign_process(item)["process"], "precision-solvent-wipe")

    def test_candidate_list_is_sorted_and_stable(self):
        candidates = qualified_processes(base_item())
        self.assertEqual(candidates, sorted(candidates))


class VerificationPointTests(unittest.TestCase):
    def test_both_ladders_beyond_the_baseline_owe_both_measurements(self):
        points = verification_points_for(base_item())
        self.assertEqual(points, [PARTICULATE_VERIFICATION, MOLECULAR_VERIFICATION])

    def test_a_requirement_exactly_on_the_baseline_owes_nothing(self):
        item = base_item(
            required_particulate_level_um=BASELINE_PARTICULATE_LEVEL_UM,
            required_nvr_mg_per_01m2=BASELINE_NVR_MG_PER_01M2,
        )
        self.assertEqual(verification_points_for(item), [])

    def test_a_particulate_only_claim_owes_one_measurement(self):
        item = base_item(
            required_particulate_level_um=300.0,
            required_nvr_mg_per_01m2=BASELINE_NVR_MG_PER_01M2,
        )
        self.assertEqual(verification_points_for(item), [PARTICULATE_VERIFICATION])

    def test_a_molecular_only_claim_owes_the_residue_weighing(self):
        item = base_item(
            required_particulate_level_um=BASELINE_PARTICULATE_LEVEL_UM,
            required_nvr_mg_per_01m2=0.20,
        )
        self.assertEqual(verification_points_for(item), [MOLECULAR_VERIFICATION])


class OperationValidationTests(unittest.TestCase):
    def test_a_complete_operation_validates(self):
        op = validate_operation(
            {"name": "bolt torqueing", "sequence": 20, "contaminating": True}
        )
        self.assertTrue(op["contaminating"])

    def test_contaminating_defaults_to_false(self):
        op = validate_operation({"name": "alignment survey", "sequence": 20})
        self.assertFalse(op["contaminating"])

    def test_non_boolean_contaminating_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation({"name": "swage", "sequence": 20, "contaminating": "yes"})

    def test_operation_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation({"sequence": 20})


class PlanBuildTests(unittest.TestCase):
    def test_entries_are_ordered_by_sequence(self):
        plan = build_ultracleaning_plan(
            [base_item(id="b", sequence=30), base_item(id="a", sequence=10)]
        )
        self.assertEqual([e["id"] for e in plan["entries"][:2]], ["a", "b"])

    def test_the_plan_closes_with_a_delivery_verification(self):
        plan = build_ultracleaning_plan([base_item()])
        self.assertEqual(plan["entries"][-1]["id"], FINAL_VERIFICATION)

    def test_the_closing_verification_sits_after_everything_else(self):
        plan = build_ultracleaning_plan(
            [base_item(sequence=10)],
            [{"name": "harness routing", "sequence": 40}],
        )
        self.assertEqual(plan["entries"][-1]["sequence"], 41)

    def test_a_later_contaminating_operation_is_a_finding(self):
        plan = build_ultracleaning_plan(
            [base_item(sequence=10)],
            [{"name": "bolt torqueing", "sequence": 20, "contaminating": True}],
        )
        self.assertTrue(any("does not survive to delivery" in f for f in plan["findings"]))

    def test_an_earlier_contaminating_operation_is_not_a_finding(self):
        plan = build_ultracleaning_plan(
            [base_item(sequence=30)],
            [{"name": "bolt torqueing", "sequence": 20, "contaminating": True}],
        )
        self.assertEqual(plan["findings"], [])

    def test_an_item_with_no_qualified_process_is_a_finding(self):
        plan = build_ultracleaning_plan(
            [
                base_item(
                    material="magnesium-alloy",
                    required_particulate_level_um=25.0,
                    required_nvr_mg_per_01m2=0.01,
                )
            ]
        )
        self.assertTrue(any("no qualified process" in f for f in plan["findings"]))

    def test_an_item_claiming_nothing_beyond_the_baseline_is_queried(self):
        plan = build_ultracleaning_plan(
            [
                base_item(
                    required_particulate_level_um=BASELINE_PARTICULATE_LEVEL_UM,
                    required_nvr_mg_per_01m2=BASELINE_NVR_MG_PER_01M2,
                )
            ]
        )
        self.assertTrue(any("belongs in the ultracleaning plan" in f for f in plan["findings"]))

    def test_duplicate_item_ids_rejected(self):
        with self.assertRaises(ValueError):
            build_ultracleaning_plan([base_item(), base_item()])

    def test_an_empty_item_set_rejected(self):
        with self.assertRaises(ValueError):
            build_ultracleaning_plan([])

    def test_a_mapping_passed_as_items_rejected(self):
        with self.assertRaises(ValueError):
            build_ultracleaning_plan(base_item())

    def test_a_mapping_passed_as_operations_rejected(self):
        with self.assertRaises(ValueError):
            build_ultracleaning_plan([base_item()], {"name": "x", "sequence": 1})


class CoverageTests(unittest.TestCase):
    def test_a_sound_plan_closes(self):
        plan = build_ultracleaning_plan([base_item()])
        coverage = plan_coverage(plan)
        self.assertTrue(coverage["plan_closes"])
        self.assertEqual(coverage["items_without_process"], 0)

    def test_coverage_counts_every_verification_point(self):
        plan = build_ultracleaning_plan([base_item(), base_item(id="bracket-02")])
        self.assertEqual(plan_coverage(plan)["verification_points"], 6)

    def test_an_open_finding_stops_the_plan_closing(self):
        plan = build_ultracleaning_plan(
            [base_item(sequence=10)],
            [{"name": "bolt torqueing", "sequence": 20, "contaminating": True}],
        )
        self.assertFalse(plan_coverage(plan)["plan_closes"])

    def test_coverage_rejects_something_that_is_not_a_plan(self):
        with self.assertRaises(ValueError):
            plan_coverage({"items": 3})


if __name__ == "__main__":
    unittest.main()
