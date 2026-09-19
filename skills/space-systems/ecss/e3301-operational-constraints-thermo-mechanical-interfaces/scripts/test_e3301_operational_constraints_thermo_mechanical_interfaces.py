"""Contract tests for the clause 4.5.3 / 4.6 operational-constraint logic."""

import unittest

from e3301_operational_constraints_thermo_mechanical_interfaces_logic import (
    BUDGET_TOLERANCE,
    assess_contamination,
    assess_grounding,
    assess_magnetic_cleanliness,
    assess_operational_constraints,
    assess_thermo_mechanical_interface,
    deposition_over_life,
    differential_expansion_mm,
    field_at_distance_nt,
    interface_heat_flux_w,
    interface_induced_load_n,
    total_dipole_moment,
    validate_non_negative,
    validate_positive,
    within_budget,
)

SOURCES = [
    {"name": "lubricant-creep", "rate_ng_cm2_year": 12.0},
    {"name": "harness-outgassing", "rate_ng_cm2_year": 4.0},
]

PATHS = [
    {"name": "housing-to-panel", "resistance_milliohm": 2.0},
    {
        "name": "rotor-to-housing",
        "resistance_milliohm": 5.0,
        "crosses_moving_interface": True,
        "dedicated_bonding_element": True,
    },
]

INTERFACE = {
    "length_mm": 200.0,
    "cte_mechanism_ppm_per_k": 23.0,
    "cte_structure_ppm_per_k": 3.0,
    "delta_t_k": 40.0,
    "stiffness_n_per_mm": 500.0,
    "allowed_displacement_mm": 0.25,
    "allowed_load_n": 120.0,
}

MAGNETIC = {
    "static_moment_am2": 0.02,
    "moving_part_moments": [0.005],
    "distance_m": 1.0,
    "allowance_nt": 10.0,
}


class ValidationHelperTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 3), 3.0)

    def test_zero_rejected_by_positive_validator(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_boolean_rejected_by_positive_validator(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))

    def test_zero_accepted_by_non_negative_validator(self):
        self.assertAlmostEqual(validate_non_negative("x", 0), 0.0)

    def test_negative_rejected_by_non_negative_validator(self):
        with self.assertRaises(ValueError):
            validate_non_negative("x", -1e-6)

    def test_within_budget_accepts_exact_equality(self):
        self.assertTrue(within_budget(4.0, 4.0))

    def test_within_budget_rejects_a_real_overrun(self):
        self.assertFalse(within_budget(4.1, 4.0))


class ContaminationTests(unittest.TestCase):
    def test_deposition_sums_the_sources_over_life(self):
        self.assertAlmostEqual(deposition_over_life(SOURCES, 5.0), 80.0)

    def test_view_factor_scales_the_deposition(self):
        self.assertAlmostEqual(deposition_over_life(SOURCES, 5.0, 0.25), 20.0)

    def test_per_source_view_factor_overrides_the_assembly_value(self):
        sources = [
            {"name": "baffled", "rate_ng_cm2_year": 12.0, "view_factor": 0.0},
            {"name": "direct", "rate_ng_cm2_year": 4.0},
        ]
        self.assertAlmostEqual(deposition_over_life(sources, 5.0, 1.0), 20.0)

    def test_view_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            deposition_over_life(SOURCES, 5.0, 1.2)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            deposition_over_life([{"rate_ng_cm2_year": -1.0}], 5.0)

    def test_missing_rate_key_rejected(self):
        with self.assertRaises(ValueError):
            deposition_over_life([{"name": "unnamed"}], 5.0)

    def test_zero_life_rejected(self):
        with self.assertRaises(ValueError):
            deposition_over_life(SOURCES, 0.0)

    def test_allowance_exceeded_is_flagged(self):
        result = assess_contamination(SOURCES, 10.0, 100.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_deposition_exactly_on_the_allowance_is_compliant(self):
        result = assess_contamination(SOURCES, 5.0, 80.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)


class MagneticTests(unittest.TestCase):
    def test_moving_moments_add_as_magnitudes(self):
        self.assertAlmostEqual(total_dipole_moment(0.02, [0.005, 0.005]), 0.03)

    def test_negative_moment_rejected(self):
        with self.assertRaises(ValueError):
            total_dipole_moment(-0.01)

    def test_field_follows_the_inverse_cube(self):
        near = field_at_distance_nt(0.05, 1.0)
        far = field_at_distance_nt(0.05, 2.0)
        self.assertAlmostEqual(near / far, 8.0, places=9)

    def test_field_matches_the_closed_form(self):
        self.assertAlmostEqual(field_at_distance_nt(0.5, 1.0), 100.0, places=9)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            field_at_distance_nt(0.05, 0.0)

    def test_compliant_mechanism_has_no_magnetic_finding(self):
        result = assess_magnetic_cleanliness(MAGNETIC)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_moving_parts_can_break_the_allowance(self):
        spec = dict(MAGNETIC)
        spec["moving_part_moments"] = [0.5]
        result = assess_magnetic_cleanliness(spec)
        self.assertFalse(result["compliant"])

    def test_missing_magnetic_key_rejected(self):
        spec = dict(MAGNETIC)
        del spec["allowance_nt"]
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness(spec)


class GroundingTests(unittest.TestCase):
    def test_compliant_paths_report_clean(self):
        result = assess_grounding(PATHS, 10.0)
        self.assertTrue(result["compliant"])

    def test_resistance_over_the_limit_is_flagged(self):
        result = assess_grounding(PATHS, 3.0)
        self.assertFalse(result["compliant"])

    def test_moving_interface_without_a_bonding_element_is_flagged(self):
        paths = [
            {
                "name": "rotor-to-housing",
                "resistance_milliohm": 1.0,
                "crosses_moving_interface": True,
            }
        ]
        result = assess_grounding(paths, 10.0)
        self.assertFalse(result["compliant"])
        self.assertIn("wear surface", result["findings"][0])

    def test_resistance_exactly_on_the_limit_passes(self):
        result = assess_grounding([{"name": "p", "resistance_milliohm": 10.0}], 10.0)
        self.assertTrue(result["compliant"])

    def test_empty_path_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_grounding([], 10.0)

    def test_missing_resistance_rejected(self):
        with self.assertRaises(ValueError):
            assess_grounding([{"name": "p"}], 10.0)


class InterfaceTests(unittest.TestCase):
    def test_expansion_mismatch_matches_the_closed_form(self):
        self.assertAlmostEqual(
            differential_expansion_mm(200.0, 23.0, 3.0, 40.0), 0.16, places=12
        )

    def test_matched_materials_give_no_mismatch(self):
        self.assertAlmostEqual(
            differential_expansion_mm(200.0, 12.0, 12.0, 40.0), 0.0, places=12
        )

    def test_cooling_reverses_the_sign(self):
        hot = differential_expansion_mm(200.0, 23.0, 3.0, 40.0)
        cold = differential_expansion_mm(200.0, 23.0, 3.0, -40.0)
        self.assertAlmostEqual(hot, -cold, places=12)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            differential_expansion_mm(0.0, 23.0, 3.0, 40.0)

    def test_induced_load_uses_the_displacement_magnitude(self):
        self.assertAlmostEqual(interface_induced_load_n(-0.16, 500.0), 80.0, places=9)

    def test_zero_stiffness_rejected(self):
        with self.assertRaises(ValueError):
            interface_induced_load_n(0.16, 0.0)

    def test_heat_flux_is_conductance_times_delta(self):
        self.assertAlmostEqual(interface_heat_flux_w(0.5, -40.0), 20.0, places=9)

    def test_compliant_interface_reports_no_findings(self):
        result = assess_thermo_mechanical_interface(INTERFACE)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["induced_load_n"], 80.0, places=9)

    def test_displacement_exactly_on_the_allowance_is_compliant(self):
        spec = dict(INTERFACE)
        spec["allowed_displacement_mm"] = 0.16
        spec["allowed_load_n"] = 80.0
        result = assess_thermo_mechanical_interface(spec)
        self.assertTrue(result["compliant"])

    def test_stiff_interface_breaks_the_load_budget(self):
        spec = dict(INTERFACE)
        spec["stiffness_n_per_mm"] = 5000.0
        result = assess_thermo_mechanical_interface(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("induced interface load", result["findings"][0])

    def test_heat_flux_budget_is_graded_when_declared(self):
        spec = dict(INTERFACE)
        spec["conductance_w_per_k"] = 2.0
        spec["allowed_heat_flux_w"] = 10.0
        result = assess_thermo_mechanical_interface(spec)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["heat_flux_w"], 80.0, places=9)

    def test_missing_interface_key_rejected(self):
        spec = dict(INTERFACE)
        del spec["stiffness_n_per_mm"]
        with self.assertRaises(ValueError):
            assess_thermo_mechanical_interface(spec)


class CombinedAssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "contamination": {
                "sources": SOURCES,
                "life_years": 5.0,
                "allowance_ng_cm2": 120.0,
            },
            "magnetic": dict(MAGNETIC),
            "grounding": {"paths": PATHS, "limit_milliohm": 10.0},
            "interface": dict(INTERFACE),
        }
        spec.update(overrides)
        return spec

    def test_clean_mechanism_is_compliant(self):
        result = assess_operational_constraints(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_findings_from_every_area_are_collected(self):
        spec = self._spec()
        spec["contamination"]["allowance_ng_cm2"] = 10.0
        spec["magnetic"]["allowance_nt"] = 0.1
        spec["grounding"]["limit_milliohm"] = 1.0
        spec["interface"]["allowed_load_n"] = 1.0
        result = assess_operational_constraints(spec)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_missing_top_level_key_rejected(self):
        spec = self._spec()
        del spec["grounding"]
        with self.assertRaises(ValueError):
            assess_operational_constraints(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_operational_constraints(["contamination"])

    def test_contamination_sub_spec_must_be_complete(self):
        spec = self._spec()
        del spec["contamination"]["life_years"]
        with self.assertRaises(ValueError):
            assess_operational_constraints(spec)

    def test_budget_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BUDGET_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
