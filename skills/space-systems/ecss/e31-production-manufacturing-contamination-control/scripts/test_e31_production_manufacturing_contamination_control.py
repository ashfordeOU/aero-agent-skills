"""Contract tests for the clause 4.6 production and contamination control logic."""

import unittest

from e31_production_manufacturing_contamination_control_logic import (
    REQUIRED_CONTROLS,
    STEFAN_BOLTZMANN,
    SURFACE_TYPES,
    allocation_rollup,
    area_growth_ratio,
    assess_production_controls,
    contaminated_absorptance,
    contaminated_emittance,
    evaluate_surface,
    marking_findings,
    net_rejection_w_m2,
    radiator_area_m2,
    repair_findings,
    stage_control_findings,
    storage_findings,
    validate_fraction,
    validate_surface_type,
)

FULL_CONTROLS = {
    stage: list(controls) for stage, controls in REQUIRED_CONTROLS.items()
}


def _item(**overrides):
    item = {
        "id": "RAD-PY",
        "surface_type": "radiator",
        "alpha_bol": 0.14,
        "emittance_bol": 0.85,
        "molecular_mg_per_m2": 2.0,
        "obscuration_fraction": 0.005,
        "k_molecular": 0.01,
        "k_particulate": 1.2,
        "k_molecular_emittance": 0.001,
        "heat_w": 300.0,
        "radiator_temperature_k": 300.0,
        "sink_temperature_k": 4.0,
        "solar_flux_w_m2": 1361.0,
        "view_factor": 0.1,
        "stage_allocations": {
            "manufacture": 0.4,
            "integration": 0.3,
            "storage": 0.2,
            "launch": 0.3,
            "on-orbit": 0.6,
        },
        "end_of_life_budget": 2.0,
        "stage_controls": {stage: list(controls) for stage, controls in FULL_CONTROLS.items()},
        "marking": {"inside_active_area": False, "outgassing_qualified": True},
        "storage": {"days_in_storage": 120.0, "shelf_life_days": 365.0,
                    "purge_maintained": True},
        "repair": {"repaired": False},
        "area_growth_limit": 1.3,
    }
    item.update(overrides)
    return item


class ValidationTests(unittest.TestCase):
    def test_fraction_returned_as_float(self):
        self.assertAlmostEqual(validate_fraction(0, "alpha"), 0.0)

    def test_unity_fraction_allowed(self):
        self.assertAlmostEqual(validate_fraction(1.0, "alpha"), 1.0)

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.4, "alpha")

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(-0.1, "alpha")

    def test_boolean_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(True, "alpha")

    def test_surface_type_is_normalised(self):
        self.assertEqual(validate_surface_type(" MLI "), "mli")

    def test_unknown_surface_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_type("solar-cell")

    def test_surface_vocabulary_has_three_entries(self):
        self.assertEqual(len(SURFACE_TYPES), 3)


class OpticalDegradationTests(unittest.TestCase):
    def test_absorptance_rises_with_both_contributions(self):
        value = contaminated_absorptance(0.14, 2.0, 0.005, 0.01, 1.2)
        self.assertAlmostEqual(value, 0.14 + 0.02 + 0.006, places=12)

    def test_clean_surface_keeps_its_absorptance(self):
        self.assertAlmostEqual(contaminated_absorptance(0.14, 0.0, 0.0, 0.01, 1.2),
                               0.14, places=12)

    def test_absorptance_is_capped_at_unity(self):
        self.assertAlmostEqual(contaminated_absorptance(0.9, 40.0, 0.5, 0.01, 1.2),
                               1.0, places=12)

    def test_emittance_is_depressed_by_molecular_film(self):
        self.assertAlmostEqual(contaminated_emittance(0.85, 2.0, 0.001), 0.848, places=12)

    def test_emittance_driven_to_zero_is_refused(self):
        with self.assertRaises(ValueError):
            contaminated_emittance(0.85, 2000.0, 0.001)

    def test_zero_beginning_of_life_emittance_rejected(self):
        with self.assertRaises(ValueError):
            contaminated_emittance(0.0, 1.0, 0.001)


class RejectionTests(unittest.TestCase):
    def test_rejection_matches_the_closed_form(self):
        value = net_rejection_w_m2(0.85, 0.14, 300.0, 4.0, 1361.0, 0.1)
        expected = 0.85 * STEFAN_BOLTZMANN * (300.0 ** 4 - 4.0 ** 4) - 0.14 * 1361.0 * 0.1
        self.assertAlmostEqual(value, expected, places=6)

    def test_solar_load_reduces_the_rejection(self):
        shaded = net_rejection_w_m2(0.85, 0.14, 300.0, 4.0, 0.0, 0.1)
        sunlit = net_rejection_w_m2(0.85, 0.14, 300.0, 4.0, 1361.0, 0.1)
        self.assertGreater(shaded - sunlit, 1.0)

    def test_warm_sink_rejected(self):
        with self.assertRaises(ValueError):
            net_rejection_w_m2(0.85, 0.14, 300.0, 320.0, 0.0, 0.1)

    def test_area_is_heat_over_rejection(self):
        per_area = net_rejection_w_m2(0.85, 0.14, 300.0, 4.0, 1361.0, 0.1)
        self.assertAlmostEqual(
            radiator_area_m2(300.0, 0.85, 0.14, 300.0, 4.0, 1361.0, 0.1),
            300.0 / per_area,
            places=9,
        )

    def test_absorbed_load_exceeding_rejection_is_refused(self):
        with self.assertRaises(ValueError):
            radiator_area_m2(300.0, 0.05, 0.95, 250.0, 4.0, 1361.0, 1.0)

    def test_zero_heat_load_rejected(self):
        with self.assertRaises(ValueError):
            radiator_area_m2(0.0, 0.85, 0.14, 300.0, 4.0, 1361.0, 0.1)

    def test_growth_ratio_is_a_quotient(self):
        self.assertAlmostEqual(area_growth_ratio(1.25, 1.0), 1.25, places=12)

    def test_zero_beginning_area_rejected(self):
        with self.assertRaises(ValueError):
            area_growth_ratio(1.25, 0.0)


class AllocationTests(unittest.TestCase):
    def test_total_and_dominant_stage(self):
        result = allocation_rollup({"manufacture": 0.4, "on-orbit": 0.6}, 2.0)
        self.assertAlmostEqual(result["total"], 1.0, places=12)
        self.assertEqual(result["dominant_stage"], "on-orbit")
        self.assertTrue(result["within_budget"])

    def test_total_exactly_on_budget_is_within(self):
        result = allocation_rollup({"manufacture": 1.0, "on-orbit": 1.0}, 2.0)
        self.assertTrue(result["within_budget"])

    def test_overspend_is_flagged(self):
        result = allocation_rollup({"manufacture": 1.5, "on-orbit": 1.0}, 2.0)
        self.assertFalse(result["within_budget"])

    def test_unallocated_remainder_is_reported(self):
        result = allocation_rollup({"manufacture": 0.5}, 2.0)
        self.assertAlmostEqual(result["unallocated"], 1.5, places=12)

    def test_empty_allocation_rejected(self):
        with self.assertRaises(ValueError):
            allocation_rollup({}, 2.0)

    def test_negative_allocation_rejected(self):
        with self.assertRaises(ValueError):
            allocation_rollup({"manufacture": -0.1}, 2.0)


class ControlTests(unittest.TestCase):
    def test_full_declaration_raises_nothing(self):
        self.assertEqual(
            stage_control_findings("procurement", REQUIRED_CONTROLS["procurement"]), []
        )

    def test_missing_control_is_a_finding(self):
        findings = stage_control_findings("procurement", ["approved-supplier"])
        self.assertEqual(len(findings), 1)

    def test_control_names_are_normalised(self):
        self.assertEqual(
            stage_control_findings("repair", ["Approved-Repair-Procedure",
                                              "post-repair-reverification"]),
            [],
        )

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_control_findings("painting", ["process-specification"])

    def test_every_stage_owes_at_least_two_controls(self):
        for stage, controls in REQUIRED_CONTROLS.items():
            self.assertGreaterEqual(len(controls), 2, stage)


class MarkingStorageRepairTests(unittest.TestCase):
    def test_clean_marking_raises_nothing(self):
        self.assertEqual(marking_findings("radiator", False, True), [])

    def test_marking_in_the_active_area_is_a_finding(self):
        self.assertEqual(len(marking_findings("optical", True, True)), 1)

    def test_unqualified_marking_medium_is_a_finding(self):
        self.assertEqual(len(marking_findings("mli", False, False)), 1)

    def test_storage_inside_shelf_life_raises_nothing(self):
        self.assertEqual(storage_findings(120.0, 365.0, True), [])

    def test_storage_exactly_at_shelf_life_raises_nothing(self):
        self.assertEqual(storage_findings(365.0, 365.0, True), [])

    def test_storage_past_shelf_life_is_a_finding(self):
        self.assertEqual(len(storage_findings(400.0, 365.0, True)), 1)

    def test_lost_purge_is_a_finding(self):
        self.assertEqual(len(storage_findings(120.0, 365.0, False)), 1)

    def test_unrepaired_item_raises_nothing(self):
        self.assertEqual(repair_findings(False, False, False), [])

    def test_repair_without_procedure_and_reverification_gives_two_findings(self):
        self.assertEqual(len(repair_findings(True, False, False)), 2)

    def test_properly_closed_repair_raises_nothing(self):
        self.assertEqual(repair_findings(True, True, True), [])


class SurfaceEvaluationTests(unittest.TestCase):
    def test_nominal_surface_is_controlled(self):
        record = evaluate_surface(_item())
        self.assertTrue(record["controlled"])
        self.assertGreater(record["area_eol_m2"], record["area_bol_m2"])

    def test_growth_beyond_the_limit_is_a_finding(self):
        record = evaluate_surface(_item(area_growth_limit=1.0))
        self.assertFalse(record["area_growth_acceptable"])
        self.assertFalse(record["controlled"])

    def test_missing_stage_controls_are_reported(self):
        controls = {stage: list(c) for stage, c in FULL_CONTROLS.items()}
        del controls["repair"]
        record = evaluate_surface(_item(stage_controls=controls))
        self.assertFalse(record["controlled"])

    def test_overspent_allocation_is_reported(self):
        record = evaluate_surface(_item(end_of_life_budget=0.5))
        self.assertFalse(record["allocations"]["within_budget"])
        self.assertFalse(record["controlled"])

    def test_findings_are_prefixed_with_the_item_id(self):
        record = evaluate_surface(_item(area_growth_limit=1.0))
        self.assertTrue(record["findings"][0].startswith("RAD-PY: "))

    def test_growth_limit_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_surface(_item(area_growth_limit=0.9))

    def test_missing_key_rejected(self):
        item = _item()
        del item["marking"]
        with self.assertRaises(ValueError):
            evaluate_surface(item)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_surface(_item(id="  "))


class AssessmentTests(unittest.TestCase):
    def test_single_clean_item_passes(self):
        result = assess_production_controls({"items": [_item()]})
        self.assertTrue(result["controlled"])
        self.assertAlmostEqual(result["controlled_fraction"], 1.0, places=12)

    def test_driving_item_is_the_largest_growth(self):
        result = assess_production_controls(
            {"items": [_item(), _item(id="OPT-BAFFLE", surface_type="optical",
                                      molecular_mg_per_m2=6.0)]}
        )
        self.assertEqual(result["driving_item"], "OPT-BAFFLE")

    def test_one_failing_item_fails_the_set(self):
        result = assess_production_controls(
            {"items": [_item(), _item(id="MLI-TOP", surface_type="mli",
                                      repair={"repaired": True})]}
        )
        self.assertFalse(result["controlled"])
        self.assertAlmostEqual(result["controlled_fraction"], 0.5, places=12)

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_controls({"items": [_item(), _item()]})

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_controls({"items": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_controls("items")


if __name__ == "__main__":
    unittest.main()
