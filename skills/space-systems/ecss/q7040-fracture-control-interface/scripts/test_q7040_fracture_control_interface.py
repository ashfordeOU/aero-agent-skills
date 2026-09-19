#!/usr/bin/env python3
"""Contract test for the brazing to fracture-control interface (offline)."""

import copy
import unittest

from q7040_fracture_control_interface_logic import (
    CATEGORY_FRACTURE_CRITICAL,
    CATEGORY_LOW_RISK,
    CATEGORY_NON_CRITICAL,
    DELIVERABLE_DAMAGE_TOLERANCE,
    DELIVERABLE_FCI_ENTRY,
    DELIVERABLE_NDI_PLAN,
    DELIVERABLE_REPAIR_CONCURRENCE,
    NDI_PENETRANT,
    NDI_PROOF_TEST,
    NDI_RADIOGRAPHY,
    NDI_ULTRASONIC,
    ROUTE_LOW_RISK,
    ROUTE_NDI_DEMONSTRATED,
    ROUTE_NOT_APPLICABLE,
    ROUTE_PROOF_TEST,
    ROUTE_REDESIGN,
    assess_fracture_interface,
    categorize_item,
    critical_crack_size,
    damage_tolerance_margin,
    detectable_flaw_size,
    interface_deliverables,
)

FCI_DELIVERABLES = interface_deliverables(CATEGORY_FRACTURE_CRITICAL)

GOOD_CASE = {
    "item_id": "BRZ-FCI-03",
    "failure_is_catastrophic": True,
    "released_mass_contained": False,
    "fail_safe_path": False,
    "fracture_toughness_mpa_sqrt_m": 40.0,
    "peak_stress_mpa": 120.0,
    "geometry_factor": 1.12,
    "ndi_method": NDI_ULTRASONIC,
    "ndi_base_capability_m": 0.0004,
    "proof_test_feasible": True,
    "deliverables_held": FCI_DELIVERABLES,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class CategorisationTests(unittest.TestCase):
    def test_a_catastrophic_uncontained_part_with_no_redundancy_is_an_fci(self):
        self.assertEqual(
            categorize_item(True, False, False), CATEGORY_FRACTURE_CRITICAL
        )

    def test_a_contained_failure_is_not_fracture_critical(self):
        self.assertEqual(categorize_item(True, True, False), CATEGORY_NON_CRITICAL)

    def test_a_fail_safe_path_drops_the_part_to_low_risk(self):
        self.assertEqual(categorize_item(True, False, True), CATEGORY_LOW_RISK)

    def test_a_non_catastrophic_failure_is_outside_the_programme(self):
        self.assertEqual(categorize_item(False, False, False), CATEGORY_NON_CRITICAL)

    def test_a_non_boolean_consequence_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item("catastrophic", False, False)


class CriticalCrackSizeTests(unittest.TestCase):
    def test_the_critical_size_matches_an_independently_worked_value(self):
        # K=40 MPa*sqrt(m), sigma=120 MPa, beta=1.12 worked by hand to
        # a_cr = 0.0281949658 m; the literal is the oracle, not a second
        # evaluation of the same expression.
        self.assertAlmostEqual(
            critical_crack_size(40.0, 120.0, 1.12), 0.0281949658, places=9
        )

    def test_a_unit_geometry_factor_case_matches_its_worked_value(self):
        self.assertAlmostEqual(
            critical_crack_size(80.0, 100.0, 1.0), 0.2037183272, places=9
        )

    def test_a_higher_stress_shrinks_the_critical_crack(self):
        self.assertLess(
            critical_crack_size(40.0, 240.0, 1.12),
            critical_crack_size(40.0, 120.0, 1.12),
        )

    def test_a_tougher_joint_tolerates_a_larger_crack(self):
        self.assertGreater(
            critical_crack_size(80.0, 120.0, 1.12),
            critical_crack_size(40.0, 120.0, 1.12),
        )

    def test_a_zero_stress_is_rejected(self):
        with self.assertRaises(ValueError):
            critical_crack_size(40.0, 0.0, 1.12)

    def test_a_negative_toughness_is_rejected(self):
        with self.assertRaises(ValueError):
            critical_crack_size(-40.0, 120.0, 1.12)


class DetectableFlawTests(unittest.TestCase):
    def test_a_brazed_joint_is_harder_to_inspect_than_a_solid_section(self):
        self.assertGreater(
            detectable_flaw_size(NDI_ULTRASONIC, 0.0004),
            0.0004,
        )

    def test_the_penalty_is_applied_as_declared(self):
        self.assertAlmostEqual(
            detectable_flaw_size(NDI_RADIOGRAPHY, 0.0005, 3.0), 0.0015, places=12
        )

    def test_a_surface_only_method_cannot_size_a_buried_flaw(self):
        with self.assertRaises(ValueError):
            detectable_flaw_size(NDI_PENETRANT, 0.0004)

    def test_a_proof_test_has_no_detectable_flaw_size(self):
        with self.assertRaises(ValueError):
            detectable_flaw_size(NDI_PROOF_TEST, 0.0004)

    def test_a_penalty_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            detectable_flaw_size(NDI_ULTRASONIC, 0.0004, 0.5)


class MarginTests(unittest.TestCase):
    def test_a_comfortable_margin_is_demonstrated(self):
        result = damage_tolerance_margin(0.010, 0.001)
        self.assertTrue(result["demonstrated"])
        self.assertAlmostEqual(result["achieved_factor"], 10.0, places=9)

    def test_a_margin_exactly_on_the_required_factor_is_demonstrated(self):
        result = damage_tolerance_margin(0.004, 0.001, 4.0)
        self.assertAlmostEqual(
            result["achieved_factor"], result["required_factor"], places=9
        )
        self.assertTrue(result["demonstrated"])

    def test_a_margin_well_under_the_factor_is_not_demonstrated(self):
        result = damage_tolerance_margin(0.0015, 0.001, 4.0)
        self.assertFalse(result["demonstrated"])
        self.assertGreater(result["shortfall"], 2.0)

    def test_a_required_factor_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            damage_tolerance_margin(0.004, 0.001, 0.5)

    def test_a_zero_detectable_size_is_rejected(self):
        with self.assertRaises(ValueError):
            damage_tolerance_margin(0.004, 0.0)


class DeliverableTests(unittest.TestCase):
    def test_a_non_critical_part_owes_the_interface_nothing(self):
        self.assertEqual(interface_deliverables(CATEGORY_NON_CRITICAL), [])

    def test_an_fci_owes_the_ndi_plan_and_the_damage_tolerance_assessment(self):
        owed = interface_deliverables(CATEGORY_FRACTURE_CRITICAL)
        self.assertIn(DELIVERABLE_NDI_PLAN, owed)
        self.assertIn(DELIVERABLE_DAMAGE_TOLERANCE, owed)

    def test_an_fci_may_not_be_rebrazed_without_fracture_control(self):
        self.assertIn(
            DELIVERABLE_REPAIR_CONCURRENCE,
            interface_deliverables(CATEGORY_FRACTURE_CRITICAL),
        )

    def test_a_low_risk_part_is_listed_but_owes_no_ndi_plan(self):
        owed = interface_deliverables(CATEGORY_LOW_RISK)
        self.assertIn(DELIVERABLE_FCI_ENTRY, owed)
        self.assertNotIn(DELIVERABLE_NDI_PLAN, owed)

    def test_an_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            interface_deliverables("quite-important")


class InterfaceAssessmentTests(unittest.TestCase):
    def test_a_demonstrable_fci_is_routed_through_inspection(self):
        result = assess_fracture_interface(_case())
        self.assertEqual(result["category"], CATEGORY_FRACTURE_CRITICAL)
        self.assertEqual(result["route"], ROUTE_NDI_DEMONSTRATED)
        self.assertEqual(result["findings"], [])

    def test_an_undemonstrable_fci_goes_to_a_proof_test_when_feasible(self):
        result = assess_fracture_interface(_case(peak_stress_mpa=600.0))
        self.assertEqual(result["route"], ROUTE_PROOF_TEST)
        self.assertFalse(result["margin"]["demonstrated"])

    def test_an_undemonstrable_fci_without_a_proof_test_is_redesigned(self):
        result = assess_fracture_interface(
            _case(peak_stress_mpa=600.0, proof_test_feasible=False)
        )
        self.assertEqual(result["route"], ROUTE_REDESIGN)

    def test_a_contained_part_leaves_the_programme_with_no_margin_work(self):
        result = assess_fracture_interface(_case(released_mass_contained=True))
        self.assertEqual(result["route"], ROUTE_NOT_APPLICABLE)
        self.assertIsNone(result["margin"])

    def test_a_fail_safe_part_takes_the_low_risk_route(self):
        result = assess_fracture_interface(
            _case(fail_safe_path=True, deliverables_held=[])
        )
        self.assertEqual(result["route"], ROUTE_LOW_RISK)
        self.assertTrue(result["missing_deliverables"])

    def test_a_missing_deliverable_is_a_finding_even_on_a_good_margin(self):
        result = assess_fracture_interface(_case(deliverables_held=[]))
        self.assertEqual(result["route"], ROUTE_NDI_DEMONSTRATED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_penetrant_inspection_cannot_be_the_demonstrating_method(self):
        with self.assertRaises(ValueError):
            assess_fracture_interface(_case(ndi_method=NDI_PENETRANT))

    def test_an_item_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_fracture_interface(_case(item_id=" "))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_fracture_interface("it is a bracket")

    def test_a_deliverables_field_that_is_not_a_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_fracture_interface(_case(deliverables_held=17))


if __name__ == "__main__":
    unittest.main()
