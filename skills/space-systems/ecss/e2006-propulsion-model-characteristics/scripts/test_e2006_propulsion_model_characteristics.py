#!/usr/bin/env python3
"""Gate 3 contract test for e2006-propulsion-model-characteristics."""

import unittest

import e2006_propulsion_model_characteristics_logic as logic


def all_required_elements():
    items = []
    for family in sorted(logic.REQUIRED_ELEMENTS):
        items.extend(logic.REQUIRED_ELEMENTS[family])
    return items


def segments():
    return [
        {"id": "bond-strap", "resistance_ohm": 0.01},
        {"id": "panel-hinge", "resistance_ohm": 0.02},
        {"id": "harness-shield", "resistance_ohm": 0.005},
    ]


def model(**overrides):
    base = {
        "elements": all_required_elements(),
        "cell_size_m": 0.001,
        "plasma_density_m3": 1.0e14,
        "electron_temperature_ev": 2.0,
        "cells_per_debye": 1.0,
        "declared_beam_current_a": 1.75,
        "thrust_n": 0.1,
        "beam_voltage_v": 1200.0,
        "ion_mass_amu": 131.3,
        "beam_current_rel_tol": 0.05,
        "grounding_segments": segments(),
        "max_grounding_resistance_ohm": 0.1,
        "potential_boundary_condition": "floating",
    }
    base.update(overrides)
    return base


class CategorizeModelElement(unittest.TestCase):
    def test_envelope_is_outer_geometry(self):
        self.assertEqual(
            logic.categorize_model_element("spacecraft-outer-envelope"),
            "outer-geometry",
        )

    def test_thruster_location_is_outer_geometry(self):
        self.assertEqual(
            logic.categorize_model_element("thruster-location-and-orientation"),
            "outer-geometry",
        )

    def test_beam_current_is_thruster_source(self):
        self.assertEqual(
            logic.categorize_model_element("beam-current-and-divergence"),
            "thruster-source",
        )

    def test_charge_exchange_source_is_thruster_source(self):
        self.assertEqual(
            logic.categorize_model_element("charge-exchange-ion-source"),
            "thruster-source",
        )

    def test_string_voltage_is_power_subsystem(self):
        self.assertEqual(
            logic.categorize_model_element("solar-array-string-voltage-distribution"),
            "power-subsystem",
        )

    def test_exposed_conductors_are_power_subsystem(self):
        self.assertEqual(
            logic.categorize_model_element("exposed-conductor-inventory"),
            "power-subsystem",
        )

    def test_structure_reference_is_grounding(self):
        self.assertEqual(
            logic.categorize_model_element("structure-ground-reference"),
            "grounding-reference",
        )

    def test_neutralizer_coupling_is_grounding(self):
        self.assertEqual(
            logic.categorize_model_element("neutralizer-coupling-to-plasma"),
            "grounding-reference",
        )

    def test_element_id_is_case_and_space_insensitive(self):
        self.assertEqual(
            logic.categorize_model_element("  Harness-Routing "), "power-subsystem"
        )

    def test_uncategorized_element_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_model_element("attitude-control-law")

    def test_empty_element_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_model_element("  ")

    def test_non_string_element_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_model_element(3.14)


class ElementIsRequired(unittest.TestCase):
    def test_envelope_is_required(self):
        self.assertTrue(logic.element_is_required("spacecraft-outer-envelope"))

    def test_boom_geometry_is_optional(self):
        self.assertFalse(logic.element_is_required("appendage-boom-geometry"))

    def test_harness_routing_is_optional(self):
        self.assertFalse(logic.element_is_required("harness-routing"))

    def test_floating_boundary_condition_is_required(self):
        self.assertTrue(
            logic.element_is_required("floating-potential-boundary-condition")
        )

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            logic.element_is_required("reaction-wheel-model")


class MissingModelElements(unittest.TestCase):
    def test_full_declaration_misses_nothing(self):
        self.assertEqual(logic.missing_model_elements(all_required_elements()), {})

    def test_optional_elements_do_not_satisfy_required_ones(self):
        missing = logic.missing_model_elements(["appendage-boom-geometry"])
        self.assertEqual(len(missing), 4)
        self.assertIn("spacecraft-outer-envelope", missing["outer-geometry"])

    def test_dropping_one_thruster_element_is_reported(self):
        declared = [
            e for e in all_required_elements() if e != "neutral-efflux-source"
        ]
        missing = logic.missing_model_elements(declared)
        self.assertEqual(missing, {"thruster-source": ["neutral-efflux-source"]})

    def test_dropping_two_grounding_elements_lists_both(self):
        dropped = {"structure-ground-reference", "neutralizer-coupling-to-plasma"}
        declared = [e for e in all_required_elements() if e not in dropped]
        missing = logic.missing_model_elements(declared)
        self.assertEqual(missing["grounding-reference"], sorted(dropped))

    def test_empty_declaration_misses_every_family(self):
        self.assertEqual(len(logic.missing_model_elements([])), 4)

    def test_unknown_element_in_declaration_raises(self):
        with self.assertRaises(ValueError):
            logic.missing_model_elements(
                all_required_elements() + ["orbit-propagator"]
            )

    def test_declaration_must_be_a_list(self):
        with self.assertRaises(ValueError):
            logic.missing_model_elements("spacecraft-outer-envelope")


class DebyeLength(unittest.TestCase):
    def test_debye_length_of_the_declared_plasma(self):
        self.assertAlmostEqual(logic.debye_length(1.0e14, 2.0), 0.00105131816, places=9)

    def test_density_scaling_is_inverse_square_root(self):
        ratio = logic.debye_length(1.0e14, 2.0) / logic.debye_length(4.0e14, 2.0)
        self.assertAlmostEqual(ratio, 2.0, places=9)

    def test_temperature_scaling_is_square_root(self):
        ratio = logic.debye_length(1.0e14, 8.0) / logic.debye_length(1.0e14, 2.0)
        self.assertAlmostEqual(ratio, 2.0, places=9)

    def test_zero_density_raises(self):
        with self.assertRaises(ValueError):
            logic.debye_length(0.0, 2.0)

    def test_negative_temperature_raises(self):
        with self.assertRaises(ValueError):
            logic.debye_length(1.0e14, -2.0)


class MeshResolution(unittest.TestCase):
    def test_fine_mesh_is_debye_resolved(self):
        result = logic.mesh_resolution(0.001, 1.0e14, 2.0)
        self.assertTrue(result["debye_resolved"])
        self.assertAlmostEqual(result["debye_length_m"], 0.00105131816, places=9)
        self.assertGreater(result["cells_per_debye_achieved"], 1.0)

    def test_coarse_mesh_is_not_resolved(self):
        result = logic.mesh_resolution(0.01, 1.0e14, 2.0)
        self.assertFalse(result["debye_resolved"])

    def test_cell_size_exactly_at_the_limit_is_resolved(self):
        limit = logic.debye_length(1.0e14, 2.0)
        result = logic.mesh_resolution(limit, 1.0e14, 2.0)
        self.assertTrue(result["debye_resolved"])

    def test_cell_size_a_few_ulps_over_the_limit_is_resolved(self):
        limit = logic.debye_length(1.0e14, 2.0)
        over = limit * (1.0 + 1.0e-13)
        self.assertGreater(over, limit)
        self.assertTrue(logic.mesh_resolution(over, 1.0e14, 2.0)["debye_resolved"])

    def test_cell_size_one_percent_over_the_limit_is_not_resolved(self):
        limit = logic.debye_length(1.0e14, 2.0)
        self.assertFalse(
            logic.mesh_resolution(limit * 1.01, 1.0e14, 2.0)["debye_resolved"]
        )

    def test_two_cells_per_debye_halves_the_limit(self):
        one = logic.mesh_resolution(0.0005, 1.0e14, 2.0, cells_per_debye=1.0)
        two = logic.mesh_resolution(0.0005, 1.0e14, 2.0, cells_per_debye=2.0)
        self.assertAlmostEqual(
            one["cell_size_limit_m"] / two["cell_size_limit_m"], 2.0, places=9
        )

    def test_zero_cell_size_raises(self):
        with self.assertRaises(ValueError):
            logic.mesh_resolution(0.0, 1.0e14, 2.0)

    def test_zero_cells_per_debye_raises(self):
        with self.assertRaises(ValueError):
            logic.mesh_resolution(0.001, 1.0e14, 2.0, cells_per_debye=0.0)

    def test_missing_plasma_density_raises(self):
        with self.assertRaises(ValueError):
            logic.mesh_resolution(0.001, None, 2.0)


class BeamCurrentFromThrust(unittest.TestCase):
    def test_xenon_beam_current_for_a_tenth_newton(self):
        self.assertAlmostEqual(
            logic.beam_current_from_thrust(0.1, 1200.0, 131.3), 1.74981713, places=7
        )

    def test_current_scales_linearly_with_thrust(self):
        low = logic.beam_current_from_thrust(0.1, 1200.0, 131.3)
        high = logic.beam_current_from_thrust(0.2, 1200.0, 131.3)
        self.assertAlmostEqual(high / low, 2.0, places=10)

    def test_higher_beam_voltage_needs_less_current(self):
        low = logic.beam_current_from_thrust(0.1, 1200.0, 131.3)
        high = logic.beam_current_from_thrust(0.1, 4800.0, 131.3)
        self.assertAlmostEqual(low / high, 2.0, places=9)

    def test_lighter_ion_needs_more_current(self):
        xenon = logic.beam_current_from_thrust(0.1, 1200.0, 131.3)
        krypton = logic.beam_current_from_thrust(0.1, 1200.0, 83.8)
        self.assertGreater(krypton, xenon)

    def test_zero_thrust_raises(self):
        with self.assertRaises(ValueError):
            logic.beam_current_from_thrust(0.0, 1200.0, 131.3)

    def test_zero_beam_voltage_raises(self):
        with self.assertRaises(ValueError):
            logic.beam_current_from_thrust(0.1, 0.0, 131.3)

    def test_zero_ion_mass_raises(self):
        with self.assertRaises(ValueError):
            logic.beam_current_from_thrust(0.1, 1200.0, 0.0)


class BeamCurrentConsistency(unittest.TestCase):
    def test_declared_current_agrees_with_the_thrust(self):
        result = logic.beam_current_consistency(1.75, 0.1, 1200.0, 131.3)
        self.assertTrue(result["consistent"])
        self.assertLess(result["relative_error"], 1.0e-3)

    def test_transposed_current_is_inconsistent(self):
        result = logic.beam_current_consistency(5.71, 0.1, 1200.0, 131.3)
        self.assertFalse(result["consistent"])
        self.assertGreater(result["relative_error"], 2.0)

    def test_error_exactly_at_the_tolerance_is_consistent(self):
        expected = logic.beam_current_from_thrust(0.1, 1200.0, 131.3)
        declared = expected * 1.05
        result = logic.beam_current_consistency(
            declared, 0.1, 1200.0, 131.3, relative_tolerance=0.05
        )
        self.assertTrue(result["consistent"])

    def test_error_beyond_the_tolerance_is_inconsistent(self):
        expected = logic.beam_current_from_thrust(0.1, 1200.0, 131.3)
        result = logic.beam_current_consistency(
            expected * 1.2, 0.1, 1200.0, 131.3, relative_tolerance=0.05
        )
        self.assertFalse(result["consistent"])

    def test_zero_declared_current_raises(self):
        with self.assertRaises(ValueError):
            logic.beam_current_consistency(0.0, 0.1, 1200.0, 131.3)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            logic.beam_current_consistency(
                1.75, 0.1, 1200.0, 131.3, relative_tolerance=-0.01
            )

    def test_missing_thrust_raises(self):
        with self.assertRaises(ValueError):
            logic.beam_current_consistency(1.75, None, 1200.0, 131.3)


class GroundingReturnResistance(unittest.TestCase):
    def test_series_segments_sum(self):
        self.assertAlmostEqual(logic.grounding_return_resistance(segments()), 0.035)

    def test_single_segment_returns_its_own_value(self):
        self.assertAlmostEqual(
            logic.grounding_return_resistance([{"id": "a", "resistance_ohm": 0.04}]),
            0.04,
        )

    def test_zero_resistance_segment_is_allowed(self):
        total = logic.grounding_return_resistance(
            [{"id": "a", "resistance_ohm": 0.0}, {"id": "b", "resistance_ohm": 0.01}]
        )
        self.assertAlmostEqual(total, 0.01)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            logic.grounding_return_resistance([{"id": "a", "resistance_ohm": -0.01}])

    def test_missing_resistance_raises(self):
        with self.assertRaises(ValueError):
            logic.grounding_return_resistance([{"id": "a"}])

    def test_non_numeric_resistance_raises(self):
        with self.assertRaises(ValueError):
            logic.grounding_return_resistance([{"id": "a", "resistance_ohm": "low"}])

    def test_empty_segment_list_raises(self):
        with self.assertRaises(ValueError):
            logic.grounding_return_resistance([])

    def test_segment_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.grounding_return_resistance(["bond-strap"])


class GroundingPathWithinLimit(unittest.TestCase):
    def test_total_below_the_limit_passes(self):
        self.assertTrue(logic.grounding_path_within_limit(0.035, 0.1))

    def test_total_above_the_limit_fails(self):
        self.assertFalse(logic.grounding_path_within_limit(0.5, 0.1))

    def test_total_exactly_at_the_limit_passes(self):
        self.assertTrue(logic.grounding_path_within_limit(0.1, 0.1))

    def test_float_summed_total_a_few_ulps_over_the_limit_passes(self):
        total = logic.grounding_return_resistance(
            [{"id": "a", "resistance_ohm": 0.1}, {"id": "b", "resistance_ohm": 0.2}]
        )
        self.assertGreater(total, 0.3)
        self.assertTrue(logic.grounding_path_within_limit(total, 0.3))

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            logic.grounding_path_within_limit(0.035, 0.0)

    def test_negative_total_raises(self):
        with self.assertRaises(ValueError):
            logic.grounding_path_within_limit(-0.01, 0.1)


class PotentialReferenceFloats(unittest.TestCase):
    def test_floating_reference_is_representable(self):
        self.assertTrue(logic.potential_reference_floats("floating"))

    def test_chamber_wall_clamp_is_not_representable(self):
        self.assertFalse(logic.potential_reference_floats("clamped-to-chamber-wall"))

    def test_fixed_at_zero_is_not_representable(self):
        self.assertFalse(logic.potential_reference_floats("fixed-at-zero"))

    def test_condition_is_case_insensitive(self):
        self.assertTrue(logic.potential_reference_floats("  Floating "))

    def test_unrecognized_condition_raises(self):
        with self.assertRaises(ValueError):
            logic.potential_reference_floats("whatever-the-solver-does")

    def test_non_string_condition_raises(self):
        with self.assertRaises(ValueError):
            logic.potential_reference_floats(None)


class AssessPropulsionModel(unittest.TestCase):
    def test_complete_model_is_representative(self):
        report = logic.assess_propulsion_model(model())
        self.assertTrue(report["representative"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["missing_elements"], {})
        self.assertEqual(len(report["families_declared"]), 4)

    def test_grounding_resistance_is_reported(self):
        report = logic.assess_propulsion_model(model())
        self.assertAlmostEqual(report["grounding_resistance_ohm"], 0.035)
        self.assertTrue(report["grounding_within_limit"])

    def test_missing_required_element_is_a_finding(self):
        declared = [
            e for e in all_required_elements() if e != "biased-surface-potentials"
        ]
        report = logic.assess_propulsion_model(model(elements=declared))
        self.assertFalse(report["representative"])
        self.assertIn("power-subsystem", report["findings"][0])

    def test_coarse_mesh_is_a_finding(self):
        report = logic.assess_propulsion_model(model(cell_size_m=0.02))
        self.assertFalse(report["representative"])
        self.assertTrue(any("Debye-length" in f for f in report["findings"]))

    def test_inconsistent_beam_current_is_a_finding(self):
        report = logic.assess_propulsion_model(model(declared_beam_current_a=3.5))
        self.assertFalse(report["representative"])
        self.assertTrue(
            any("thrust-implied" in f for f in report["findings"])
        )

    def test_excessive_grounding_resistance_is_a_finding(self):
        report = logic.assess_propulsion_model(
            model(max_grounding_resistance_ohm=0.01)
        )
        self.assertFalse(report["grounding_within_limit"])
        self.assertTrue(
            any("return-path resistance" in f for f in report["findings"])
        )

    def test_clamped_potential_is_a_finding(self):
        report = logic.assess_propulsion_model(
            model(potential_boundary_condition="clamped-to-chamber-wall")
        )
        self.assertFalse(report["potential_reference_floats"])
        self.assertTrue(any("free-flying" in f for f in report["findings"]))

    def test_several_defects_are_all_reported(self):
        report = logic.assess_propulsion_model(
            model(
                cell_size_m=0.02,
                declared_beam_current_a=3.5,
                potential_boundary_condition="fixed-at-zero",
            )
        )
        self.assertEqual(len(report["findings"]), 3)

    def test_optional_elements_are_accepted(self):
        declared = all_required_elements() + [
            "appendage-boom-geometry",
            "harness-routing",
        ]
        report = logic.assess_propulsion_model(model(elements=declared))
        self.assertTrue(report["representative"])

    def test_duplicate_element_raises(self):
        declared = all_required_elements() + ["spacecraft-outer-envelope"]
        with self.assertRaises(ValueError):
            logic.assess_propulsion_model(model(elements=declared))

    def test_empty_element_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_propulsion_model(model(elements=[]))

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_propulsion_model(
                model(elements=all_required_elements() + ["thermal-radiator-model"])
            )

    def test_model_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_propulsion_model(["spacecraft-outer-envelope"])

    def test_missing_grounding_segments_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_propulsion_model(model(grounding_segments=None))

    def test_missing_grounding_limit_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_propulsion_model(model(max_grounding_resistance_ohm=None))


if __name__ == "__main__":
    unittest.main()
