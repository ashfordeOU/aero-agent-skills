#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.8.2 spacecraft
reference grounding concept.

Exercises scripts/e20_spacecraft_grounding_reference_concept_logic.py
(stdlib unittest, offline). Contract: a circuit kind and a unit kind
each map to exactly one category and an unrecognized kind raises; the
wavelength and the electrical length ratio follow the conductor
velocity factor; the required topology is single-point at or below one
twentieth of a wavelength and multi-point above it, with a run landing
exactly on the threshold still single-point; a hybrid declaration
satisfies both cases while a single-point declaration on an
electrically long run and a multi-point declaration on a short one are
each reported with their own issue; an isolated domain carries exactly
one reference point; structure is rejected as the return for the
dedicated categories and accepted for the others; bonding uses the
per-category limit and isolation its minimum, both compliant exactly
on the limit; the common-impedance voltage is aggressor current times
shared path impedance against the victim budget; and the aggregated
review is controlled only when every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_spacecraft_grounding_reference_concept_logic as gc  # noqa: E402


def _clean_concept():
    """A domain that satisfies every clause 6.3.8.2 check."""
    return {
        "domain_id": "PWR-DOMAIN-A",
        "declared_topology": "single_point",
        "longest_return_length_m": 2.0,
        "highest_frequency_hz": 1.0e5,
        "velocity_factor": 0.66,
        "reference_point_count": 1,
        "isolation_resistance_ohm": 5.0e6,
        "circuits": [
            {
                "circuit_id": "C-PWR-01",
                "circuit_kind": "primary_power_feed",
                "uses_structure_return": False,
            },
            {
                "circuit_id": "C-DIG-01",
                "circuit_kind": "digital_bus_signal",
                "uses_structure_return": True,
            },
        ],
        "units": [
            {
                "unit_id": "U-PCU-01",
                "unit_kind": "power_conditioning_unit",
                "bonding_resistance_ohm": 1.5e-3,
            },
            {
                "unit_id": "U-TX-01",
                "unit_kind": "transmitter",
                "bonding_resistance_ohm": 1.0e-3,
            },
        ],
        "shared_returns": [
            {
                "victim_id": "C-ANA-01",
                "return_current_a": 0.5,
                "shared_path_impedance_ohm": 1.0e-3,
                "noise_budget_v": 5.0e-3,
            }
        ],
    }


class CategorizeCircuitTest(unittest.TestCase):
    def test_primary_power_feed_is_primary_power(self):
        self.assertEqual(
            gc.categorize_circuit("primary_power_feed"), "primary_power"
        )

    def test_thermistor_sensing_is_sensitive_analogue(self):
        self.assertEqual(
            gc.categorize_circuit("thermistor_sensing"), "sensitive_analogue"
        )

    def test_pyrotechnic_firing_is_pyrotechnic(self):
        self.assertEqual(
            gc.categorize_circuit("pyrotechnic_firing"), "pyrotechnic"
        )

    def test_coaxial_rf_is_radio_frequency(self):
        self.assertEqual(gc.categorize_circuit("coaxial_rf"), "radio_frequency")

    def test_every_circuit_kind_maps_to_one_category(self):
        for kind in gc.CIRCUIT_CATEGORY_BY_KIND:
            self.assertIsInstance(gc.categorize_circuit(kind), str)

    def test_uncategorized_circuit_kind_raises(self):
        with self.assertRaises(ValueError):
            gc.categorize_circuit("fuel_line")

    def test_none_circuit_kind_raises(self):
        with self.assertRaises(ValueError):
            gc.categorize_circuit(None)


class CategorizeUnitTest(unittest.TestCase):
    def test_battery_is_power_source_unit(self):
        self.assertEqual(gc.categorize_unit("battery"), "power_source_unit")

    def test_heater_string_is_power_user_unit(self):
        self.assertEqual(gc.categorize_unit("heater_string"), "power_user_unit")

    def test_payload_receiver_is_signal_receiver_unit(self):
        self.assertEqual(
            gc.categorize_unit("payload_receiver"), "signal_receiver_unit"
        )

    def test_initiator_is_pyrotechnic_unit(self):
        self.assertEqual(
            gc.categorize_unit("pyrotechnic_initiator"), "pyrotechnic_unit"
        )

    def test_uncategorized_unit_kind_raises(self):
        with self.assertRaises(ValueError):
            gc.categorize_unit("propellant_tank")


class WavelengthTest(unittest.TestCase):
    def test_wavelength_in_vacuum_at_one_megahertz(self):
        self.assertAlmostEqual(gc.wavelength_m(1.0e6), 299.792458, places=6)

    def test_velocity_factor_shortens_wavelength(self):
        self.assertAlmostEqual(
            gc.wavelength_m(1.0e6, 0.5), 149.896229, places=6
        )

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            gc.wavelength_m(0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            gc.wavelength_m(-1.0e6)

    def test_velocity_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            gc.wavelength_m(1.0e6, 1.2)

    def test_zero_velocity_factor_raises(self):
        with self.assertRaises(ValueError):
            gc.wavelength_m(1.0e6, 0.0)


class ElectricalLengthTest(unittest.TestCase):
    def test_ratio_is_length_over_wavelength(self):
        self.assertAlmostEqual(
            gc.electrical_length_ratio(29.9792458, 1.0e6), 0.1, places=9
        )

    def test_zero_length_is_zero_ratio(self):
        self.assertAlmostEqual(
            gc.electrical_length_ratio(0.0, 1.0e6), 0.0, places=12
        )

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            gc.electrical_length_ratio(-1.0, 1.0e6)


class RequiredTopologyTest(unittest.TestCase):
    def test_short_run_stays_single_point(self):
        self.assertEqual(
            gc.required_reference_topology(1.0, 1.0e6), "single_point"
        )

    def test_long_run_needs_multi_point(self):
        self.assertEqual(
            gc.required_reference_topology(50.0, 1.0e6), "multi_point"
        )

    def test_run_exactly_on_threshold_is_single_point(self):
        length = gc.wavelength_m(1.0e6) * gc.SINGLE_POINT_WAVELENGTH_FRACTION
        self.assertEqual(
            gc.required_reference_topology(length, 1.0e6), "single_point"
        )

    def test_threshold_plus_one_percent_is_multi_point(self):
        length = (
            gc.wavelength_m(1.0e6) * gc.SINGLE_POINT_WAVELENGTH_FRACTION * 1.01
        )
        self.assertEqual(
            gc.required_reference_topology(length, 1.0e6), "multi_point"
        )

    def test_velocity_factor_can_flip_the_topology(self):
        length = 12.0
        self.assertEqual(
            gc.required_reference_topology(length, 1.0e6, 1.0), "single_point"
        )
        self.assertEqual(
            gc.required_reference_topology(length, 1.0e6, 0.5), "multi_point"
        )

    def test_wavelength_fraction_outside_range_raises(self):
        with self.assertRaises(ValueError):
            gc.required_reference_topology(1.0, 1.0e6, 1.0, 1.5)


class TopologyFindingsTest(unittest.TestCase):
    def test_consistent_single_point_has_no_finding(self):
        self.assertEqual(
            gc.topology_findings("D1", "single_point", 1.0, 1.0e6), []
        )

    def test_single_point_on_long_run_is_reported(self):
        findings = gc.topology_findings("D1", "single_point", 60.0, 1.0e6)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "single_point_reference_electrically_long"
        )
        self.assertEqual(findings[0]["required_topology"], "multi_point")

    def test_multi_point_on_short_run_is_reported(self):
        findings = gc.topology_findings("D1", "multi_point", 1.0, 1.0e6)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "multi_point_reference_not_required_at_frequency",
        )

    def test_hybrid_satisfies_a_long_run(self):
        self.assertEqual(gc.topology_findings("D1", "hybrid", 60.0, 1.0e6), [])

    def test_hybrid_satisfies_a_short_run(self):
        self.assertEqual(gc.topology_findings("D1", "hybrid", 1.0, 1.0e6), [])

    def test_unrecognized_topology_raises(self):
        with self.assertRaises(ValueError):
            gc.topology_findings("D1", "star_point", 1.0, 1.0e6)


class ReferencePointTest(unittest.TestCase):
    def test_exactly_one_reference_point_passes(self):
        self.assertEqual(gc.reference_point_findings("D1", 1), [])

    def test_zero_reference_points_is_a_floating_domain(self):
        findings = gc.reference_point_findings("D1", 0)
        self.assertEqual(findings[0]["issue"], "domain_has_no_reference_point")

    def test_two_reference_points_close_a_loop(self):
        findings = gc.reference_point_findings("D1", 2)
        self.assertEqual(
            findings[0]["issue"], "domain_has_multiple_reference_points"
        )

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            gc.reference_point_findings("D1", -1)

    def test_non_integer_count_raises(self):
        with self.assertRaises(ValueError):
            gc.reference_point_findings("D1", 1.0)


class StructureReturnTest(unittest.TestCase):
    def test_primary_power_on_structure_is_reported(self):
        findings = gc.structure_return_findings(
            "C1", "primary_power_feed", True
        )
        self.assertEqual(
            findings[0]["issue"],
            "structure_used_as_return_for_dedicated_category",
        )

    def test_pyrotechnic_on_structure_is_reported(self):
        findings = gc.structure_return_findings(
            "C2", "pyrotechnic_firing", True
        )
        self.assertEqual(len(findings), 1)

    def test_sensitive_analogue_on_structure_is_reported(self):
        findings = gc.structure_return_findings(
            "C3", "low_level_analogue_signal", True
        )
        self.assertEqual(findings[0]["circuit_category"], "sensitive_analogue")

    def test_digital_signal_on_structure_is_allowed(self):
        self.assertEqual(
            gc.structure_return_findings("C4", "digital_bus_signal", True), []
        )

    def test_coaxial_rf_on_structure_is_allowed(self):
        self.assertEqual(
            gc.structure_return_findings("C5", "coaxial_rf", True), []
        )

    def test_dedicated_return_without_structure_passes(self):
        self.assertEqual(
            gc.structure_return_findings("C6", "primary_power_feed", False), []
        )

    def test_non_boolean_flag_raises(self):
        with self.assertRaises(ValueError):
            gc.structure_return_findings("C7", "primary_power_feed", "yes")


class BondingTest(unittest.TestCase):
    def test_pyrotechnic_unit_carries_the_tight_limit(self):
        self.assertAlmostEqual(
            gc.bonding_resistance_limit_ohm("pyrotechnic_unit"),
            2.5e-3,
            places=9,
        )

    def test_power_user_unit_carries_the_relaxed_limit(self):
        self.assertAlmostEqual(
            gc.bonding_resistance_limit_ohm("power_user_unit"), 1.0e-2, places=9
        )

    def test_unrecognized_unit_category_raises(self):
        with self.assertRaises(ValueError):
            gc.bonding_resistance_limit_ohm("thermal_unit")

    def test_bonded_unit_has_no_finding(self):
        self.assertEqual(
            gc.bonding_findings("U1", "transmitter", 1.0e-3), []
        )

    def test_bonding_above_limit_is_reported(self):
        findings = gc.bonding_findings("U2", "transmitter", 5.0e-3)
        self.assertEqual(
            findings[0]["issue"], "unit_bonding_resistance_above_limit"
        )
        self.assertAlmostEqual(findings[0]["limit_ohm"], 2.5e-3, places=9)

    def test_bonding_exactly_on_limit_passes_despite_rounding(self):
        # Strap, joint and interface resistance summed in that order land
        # a few ULPs above the 10 mOhm limit they add up to exactly.
        measured = 0.001 + 0.008 + 0.001
        self.assertGreater(measured, 1.0e-2)
        self.assertEqual(
            gc.bonding_findings("U3", "heater_string", measured), []
        )

    def test_same_resistance_can_pass_one_category_and_fail_another(self):
        self.assertEqual(gc.bonding_findings("U4", "heater_string", 5.0e-3), [])
        self.assertEqual(
            len(gc.bonding_findings("U5", "pyrotechnic_initiator", 5.0e-3)), 1
        )

    def test_zero_bonding_resistance_raises(self):
        with self.assertRaises(ValueError):
            gc.bonding_findings("U6", "transmitter", 0.0)


class IsolationTest(unittest.TestCase):
    def test_high_isolation_has_no_finding(self):
        self.assertEqual(gc.isolation_findings("D1", 5.0e6), [])

    def test_low_isolation_is_reported(self):
        findings = gc.isolation_findings("D1", 1.0e4)
        self.assertEqual(
            findings[0]["issue"], "domain_isolation_resistance_below_minimum"
        )

    def test_isolation_exactly_on_minimum_passes(self):
        self.assertEqual(
            gc.isolation_findings(
                "D1", gc.DEFAULT_ISOLATION_RESISTANCE_MIN_OHM
            ),
            [],
        )

    def test_custom_minimum_is_honoured(self):
        self.assertEqual(len(gc.isolation_findings("D1", 5.0e6, 1.0e7)), 1)

    def test_zero_isolation_resistance_raises(self):
        with self.assertRaises(ValueError):
            gc.isolation_findings("D1", 0.0)

    def test_zero_minimum_raises(self):
        with self.assertRaises(ValueError):
            gc.isolation_findings("D1", 1.0e6, 0.0)


class CommonImpedanceTest(unittest.TestCase):
    def test_voltage_is_current_times_impedance(self):
        self.assertAlmostEqual(
            gc.common_impedance_voltage(2.0, 5.0e-3), 1.0e-2, places=9
        )

    def test_zero_shared_impedance_couples_nothing(self):
        self.assertAlmostEqual(
            gc.common_impedance_voltage(10.0, 0.0), 0.0, places=12
        )

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            gc.common_impedance_voltage(-1.0, 1.0e-3)

    def test_negative_shared_impedance_raises(self):
        with self.assertRaises(ValueError):
            gc.common_impedance_voltage(1.0, -1.0e-3)

    def test_coupling_inside_budget_has_no_finding(self):
        path = {"return_current_a": 0.5, "shared_path_impedance_ohm": 1.0e-3}
        self.assertEqual(gc.coupling_findings("V1", path, 5.0e-3), [])

    def test_coupling_above_budget_is_reported(self):
        path = {"return_current_a": 5.0, "shared_path_impedance_ohm": 1.0e-2}
        findings = gc.coupling_findings("V2", path, 1.0e-2)
        self.assertEqual(
            findings[0]["issue"],
            "common_impedance_voltage_above_noise_budget",
        )
        self.assertAlmostEqual(findings[0]["coupled_v"], 5.0e-2, places=9)

    def test_coupling_exactly_on_budget_passes_despite_rounding(self):
        # 70 mA through a 0.1 ohm shared path is exactly the 7 mV budget,
        # but the product lands a few ULPs above it.
        path = {"return_current_a": 0.07, "shared_path_impedance_ohm": 0.1}
        self.assertGreater(0.07 * 0.1, 0.007)
        self.assertEqual(gc.coupling_findings("V3", path, 0.007), [])

    def test_zero_budget_raises(self):
        path = {"return_current_a": 0.5, "shared_path_impedance_ohm": 1.0e-3}
        with self.assertRaises(ValueError):
            gc.coupling_findings("V4", path, 0.0)


class ConceptReviewTest(unittest.TestCase):
    def test_clean_concept_is_controlled(self):
        review = gc.grounding_concept_review(_clean_concept())
        self.assertTrue(gc.is_concept_controlled(review))
        for key in (
            "topology",
            "reference_point",
            "structure_return",
            "bonding",
            "isolation",
            "coupling",
        ):
            self.assertEqual(review[key], [])

    def test_structure_return_breaks_the_concept(self):
        concept = _clean_concept()
        concept["circuits"][0]["uses_structure_return"] = True
        review = gc.grounding_concept_review(concept)
        self.assertEqual(len(review["structure_return"]), 1)
        self.assertFalse(gc.is_concept_controlled(review))

    def test_second_reference_point_breaks_the_concept(self):
        concept = _clean_concept()
        concept["reference_point_count"] = 2
        review = gc.grounding_concept_review(concept)
        self.assertEqual(len(review["reference_point"]), 1)
        self.assertFalse(gc.is_concept_controlled(review))

    def test_long_return_at_high_frequency_breaks_the_topology(self):
        concept = _clean_concept()
        concept["highest_frequency_hz"] = 1.0e8
        review = gc.grounding_concept_review(concept)
        self.assertEqual(
            review["topology"][0]["issue"],
            "single_point_reference_electrically_long",
        )

    def test_unbonded_transmitter_breaks_the_concept(self):
        concept = _clean_concept()
        concept["units"][1]["bonding_resistance_ohm"] = 2.0e-2
        review = gc.grounding_concept_review(concept)
        self.assertEqual(review["bonding"][0]["unit"], "U-TX-01")

    def test_low_isolation_breaks_the_concept(self):
        concept = _clean_concept()
        concept["isolation_resistance_ohm"] = 1.0e3
        review = gc.grounding_concept_review(concept)
        self.assertEqual(len(review["isolation"]), 1)

    def test_shared_return_over_budget_breaks_the_concept(self):
        concept = _clean_concept()
        concept["shared_returns"][0]["return_current_a"] = 40.0
        review = gc.grounding_concept_review(concept)
        self.assertEqual(len(review["coupling"]), 1)

    def test_review_does_not_mutate_the_concept(self):
        concept = _clean_concept()
        before = repr(concept)
        gc.grounding_concept_review(concept)
        self.assertEqual(repr(concept), before)

    def test_review_is_deterministic(self):
        first = gc.grounding_concept_review(_clean_concept())
        second = gc.grounding_concept_review(_clean_concept())
        self.assertEqual(first, second)

    def test_uncategorized_circuit_in_concept_raises(self):
        concept = _clean_concept()
        concept["circuits"][0]["circuit_kind"] = "coolant_loop"
        with self.assertRaises(ValueError):
            gc.grounding_concept_review(concept)

    def test_empty_collections_are_accepted(self):
        concept = _clean_concept()
        concept["circuits"] = []
        concept["units"] = []
        concept["shared_returns"] = []
        review = gc.grounding_concept_review(concept)
        self.assertTrue(gc.is_concept_controlled(review))

    def test_isclose_tolerance_is_a_representation_tolerance(self):
        self.assertLess(gc.LIMIT_REL_TOL, 1.0e-6)
        self.assertTrue(
            math.isclose(1.0e-2, 0.001 + 0.008 + 0.001, rel_tol=gc.LIMIT_REL_TOL)
        )


if __name__ == "__main__":
    unittest.main()
