"""Gate 3 contract test for the ECSS-E-ST-20C 5.5.4 drive current leaf.

stdlib unittest, offline, deterministic. Run:
    python3 test_e20_solar_array_drive_current_capability.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_solar_array_drive_current_capability_logic as logic  # noqa: E402

SQRT_HALF = 0.7071067811865476


def wire(**overrides):
    element = {
        "element_id": "SA1-W01",
        "kind": "harness-wire",
        "gauge_awg": 20,
        "bundle_count": 8,
        "conductor_temperature_c": 110.0,
        "insulation_rating_c": 200.0,
        "in_vacuum": True,
    }
    element.update(overrides)
    return element


def pin(**overrides):
    element = {
        "element_id": "SA1-J02-P5",
        "kind": "connector-pin",
        "rated_current_a": 5.0,
        "bundle_count": 1,
        "conductor_temperature_c": 20.0,
        "insulation_rating_c": 200.0,
        "in_vacuum": False,
    }
    element.update(overrides)
    return element


def slip_ring(**overrides):
    element = {
        "element_id": "SADM-SR-A",
        "kind": "slip-ring-contact",
        "rated_current_per_contact_a": 3.0,
        "contact_count": 4,
        "sharing_factor": 0.8,
        "single_contact_failure": False,
        "conductor_temperature_c": 20.0,
        "insulation_rating_c": 200.0,
    }
    element.update(overrides)
    return element


class TestElementCategorization(unittest.TestCase):
    def test_wire_aliases_resolve_to_one_family(self):
        for token in ("wire", "Harness Wire", "cable", "harness_wire"):
            self.assertEqual(logic.categorize_path_element(token), logic.HARNESS_WIRE)

    def test_pin_aliases_resolve_to_one_family(self):
        for token in ("pin", "connector-pin", "Contact Pin"):
            self.assertEqual(logic.categorize_path_element(token), logic.CONNECTOR_PIN)

    def test_slip_ring_aliases_resolve_to_one_family(self):
        for token in ("slip-ring", "SADM slip ring", "slip ring contact"):
            self.assertEqual(
                logic.categorize_path_element(token), logic.SLIP_RING_CONTACT
            )

    def test_every_family_is_declared(self):
        self.assertEqual(len(logic.PATH_ELEMENT_FAMILIES), 3)
        self.assertIn(
            logic.categorize_path_element("wire"), logic.PATH_ELEMENT_FAMILIES
        )

    def test_unknown_family_is_rejected_not_guessed(self):
        with self.assertRaises(ValueError):
            logic.categorize_path_element("busbar")

    def test_empty_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_path_element("  ")


class TestDeratingFactors(unittest.TestCase):
    def test_wire_gauge_lookup(self):
        self.assertAlmostEqual(logic.wire_base_rating(20), 6.5, places=9)
        self.assertAlmostEqual(logic.wire_base_rating(14), 19.0, places=9)

    def test_gauge_outside_the_table_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.wire_base_rating(19)

    def test_non_integer_gauge_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.wire_base_rating(20.0)

    def test_bundle_bands(self):
        self.assertAlmostEqual(logic.bundle_derating_factor(1), 1.00, places=9)
        self.assertAlmostEqual(logic.bundle_derating_factor(3), 0.85, places=9)
        self.assertAlmostEqual(logic.bundle_derating_factor(4), 0.75, places=9)
        self.assertAlmostEqual(logic.bundle_derating_factor(7), 0.65, places=9)
        self.assertAlmostEqual(logic.bundle_derating_factor(16), 0.55, places=9)
        self.assertAlmostEqual(logic.bundle_derating_factor(64), 0.45, places=9)

    def test_bundle_count_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.bundle_derating_factor(0)

    def test_temperature_derating_at_mid_range(self):
        self.assertAlmostEqual(
            logic.temperature_derating_factor(110.0, 200.0), SQRT_HALF, places=9
        )

    def test_temperature_derating_is_clamped_below_the_reference(self):
        self.assertAlmostEqual(
            logic.temperature_derating_factor(-40.0, 200.0), 1.0, places=9
        )

    def test_conductor_at_the_insulation_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.temperature_derating_factor(200.0, 200.0)

    def test_conductor_above_the_insulation_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.temperature_derating_factor(215.0, 200.0)

    def test_insulation_rating_below_the_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.temperature_derating_factor(10.0, 15.0)

    def test_vacuum_derating(self):
        self.assertAlmostEqual(logic.vacuum_derating_factor(True), 0.80, places=9)
        self.assertAlmostEqual(logic.vacuum_derating_factor(False), 1.00, places=9)

    def test_vacuum_flag_must_be_boolean(self):
        with self.assertRaises(ValueError):
            logic.vacuum_derating_factor("yes")


class TestSlipRingCapability(unittest.TestCase):
    def test_parallel_contacts_are_reduced_by_the_sharing_factor(self):
        self.assertAlmostEqual(logic.slip_ring_capability(3.0, 4), 9.6, places=9)

    def test_perfect_sharing_is_the_optimistic_bound(self):
        self.assertAlmostEqual(
            logic.slip_ring_capability(3.0, 4, sharing_factor=1.0), 12.0, places=9
        )
        self.assertLess(
            logic.slip_ring_capability(3.0, 4),
            logic.slip_ring_capability(3.0, 4, sharing_factor=1.0),
        )

    def test_single_contact_failure_drops_one_contact(self):
        self.assertAlmostEqual(
            logic.slip_ring_capability(3.0, 4, single_contact_failure=True),
            7.2,
            places=9,
        )

    def test_one_contact_cannot_survive_a_contact_failure(self):
        with self.assertRaises(ValueError):
            logic.slip_ring_capability(3.0, 1, single_contact_failure=True)

    def test_sharing_factor_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.slip_ring_capability(3.0, 4, sharing_factor=1.2)

    def test_zero_sharing_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.slip_ring_capability(3.0, 4, sharing_factor=0.0)

    def test_non_positive_contact_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.slip_ring_capability(0.0, 4)

    def test_failure_flag_must_be_boolean(self):
        with self.assertRaises(ValueError):
            logic.slip_ring_capability(3.0, 4, single_contact_failure="yes")


class TestWorstCaseSectionCurrent(unittest.TestCase):
    def test_reference_condition_is_the_measured_short_circuit_current(self):
        self.assertAlmostEqual(logic.worst_case_section_current(4.0), 4.0, places=9)

    def test_hot_case_and_parallel_strings_raise_the_applied_current(self):
        current = logic.worst_case_section_current(
            4.0, 4.6e-4, 78.0, 1.0, 0.0, 2
        )
        self.assertAlmostEqual(current, 8.184, places=9)

    def test_hot_case_exceeds_the_cold_case(self):
        hot = logic.worst_case_section_current(4.0, 4.6e-4, 80.0)
        cold = logic.worst_case_section_current(4.0, 4.6e-4, -60.0)
        self.assertGreater(hot, cold)

    def test_near_sun_distance_raises_the_applied_current(self):
        near = logic.worst_case_section_current(4.0, 4.6e-4, 28.0, 0.9)
        self.assertAlmostEqual(near, 4.938271605, places=8)

    def test_negative_temperature_coefficient_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_section_current(4.0, -1.0e-4)

    def test_non_positive_reference_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_section_current(0.0)

    def test_zero_parallel_strings_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_section_current(4.0, 4.6e-4, 28.0, 1.0, 0.0, 0)

    def test_non_positive_solar_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_section_current(4.0, 4.6e-4, 28.0, 0.0)

    def test_incidence_at_ninety_degrees_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_section_current(4.0, 4.6e-4, 28.0, 1.0, 90.0)


class TestElementCapability(unittest.TestCase):
    def test_wire_capability_matches_hand_calculation(self):
        detail = logic.element_capability(wire())
        self.assertEqual(detail["family"], logic.HARNESS_WIRE)
        self.assertAlmostEqual(detail["capability_a"], 2.3900209204, places=9)

    def test_pin_capability_at_benign_conditions(self):
        detail = logic.element_capability(pin())
        self.assertEqual(detail["family"], logic.CONNECTOR_PIN)
        self.assertAlmostEqual(detail["capability_a"], 5.0, places=9)

    def test_slip_ring_capability_uses_the_sharing_chain(self):
        detail = logic.element_capability(slip_ring())
        self.assertEqual(detail["family"], logic.SLIP_RING_CONTACT)
        self.assertAlmostEqual(detail["capability_a"], 9.6, places=9)

    def test_slip_ring_does_not_take_loom_bundle_derating(self):
        detail = logic.element_capability(slip_ring(bundle_count=20))
        self.assertAlmostEqual(detail["bundle_factor"], 1.0, places=9)
        self.assertAlmostEqual(detail["capability_a"], 9.6, places=9)

    def test_non_mapping_element_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.element_capability("SA1-W01")

    def test_element_without_an_identifier_is_rejected(self):
        element = wire()
        del element["element_id"]
        with self.assertRaises(ValueError):
            logic.element_capability(element)

    def test_wire_without_a_gauge_is_rejected(self):
        element = wire()
        del element["gauge_awg"]
        with self.assertRaises(ValueError):
            logic.element_capability(element)

    def test_pin_with_a_zero_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.element_capability(pin(rated_current_a=0.0))

    def test_element_of_an_unknown_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.element_capability(wire(kind="busbar"))


class TestElementMargin(unittest.TestCase):
    def test_comfortable_margin_passes(self):
        graded = logic.element_margin(12.5, 10.0, 0.20)
        self.assertAlmostEqual(graded["margin"], 0.25, places=9)
        self.assertEqual(graded["verdict"], "pass")

    def test_thin_margin_fails(self):
        graded = logic.element_margin(11.5, 10.0, 0.20)
        self.assertAlmostEqual(graded["margin"], 0.15, places=9)
        self.assertEqual(graded["verdict"], "fail")

    def test_zero_required_margin_boundary_passes(self):
        graded = logic.element_margin(10.0, 10.0, 0.0)
        self.assertAlmostEqual(graded["margin"], 0.0, places=12)
        self.assertEqual(graded["verdict"], "pass")

    def test_zero_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.element_margin(0.0, 10.0)

    def test_zero_applied_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.element_margin(12.0, 0.0)

    def test_negative_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.element_margin(12.0, 10.0, -0.1)


class TestAssessPowerPath(unittest.TestCase):
    def setUp(self):
        self.benign = [
            wire(gauge_awg=14, bundle_count=1, conductor_temperature_c=20.0, in_vacuum=False),
            pin(rated_current_a=13.0),
            slip_ring(),
        ]
        self.stressed = [
            wire(gauge_awg=14, bundle_count=4, conductor_temperature_c=20.0, in_vacuum=True),
            pin(rated_current_a=13.0, bundle_count=4, in_vacuum=True),
            slip_ring(contact_count=5, single_contact_failure=True),
        ]

    def test_benign_path_is_compliant_and_names_the_weakest_element(self):
        result = logic.assess_power_path(self.benign, 5.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["weakest_element"], "SADM-SR-A")
        self.assertAlmostEqual(result["weakest_margin"], 0.92, places=9)

    def test_stressed_path_flags_every_undersized_element(self):
        result = logic.assess_power_path(self.stressed, 8.184)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)
        self.assertEqual(result["weakest_element"], "SA1-J02-P5")

    def test_every_element_is_graded(self):
        result = logic.assess_power_path(self.stressed, 8.184)
        self.assertEqual(len(result["elements"]), 3)
        for detail in result["elements"]:
            self.assertIn(detail["verdict"], ("pass", "fail"))
            self.assertAlmostEqual(detail["applied_current_a"], 8.184, places=9)

    def test_a_generous_total_does_not_excuse_a_weak_element(self):
        result = logic.assess_power_path(self.stressed, 8.184)
        total = sum(d["capability_a"] for d in result["elements"])
        self.assertGreater(total, 3.0 * 8.184)
        self.assertFalse(result["compliant"])

    def test_empty_element_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_power_path([], 5.0)

    def test_non_positive_applied_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_power_path(self.benign, 0.0)

    def test_assessment_is_deterministic_across_runs(self):
        first = logic.assess_power_path(self.stressed, 8.184)
        second = logic.assess_power_path(self.stressed, 8.184)
        self.assertEqual(first["findings"], second["findings"])
        self.assertAlmostEqual(
            first["weakest_margin"], second["weakest_margin"], places=12
        )


if __name__ == "__main__":
    unittest.main()
