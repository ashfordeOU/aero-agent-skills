"""
Tests for fem_modelling_requirements_logic.py
stdlib unittest only — deterministic, offline. Run:
    python3 test_fem_modelling_requirements.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fem_modelling_requirements_logic import (
    check_idealization,
    check_element_type,
    check_mesh_density,
    check_material_model,
    check_unit_system,
    check_boundary_conditions,
    evaluate_model,
)


class TestIdealization(unittest.TestCase):

    def test_stick_valid_high_aspect_ratio(self):
        ok, _ = check_idealization("STICK", 15)
        self.assertTrue(ok)

    def test_stick_at_minimum_aspect_ratio(self):
        ok, _ = check_idealization("STICK", 10)
        self.assertTrue(ok)

    def test_stick_insufficient_aspect_ratio(self):
        ok, reason = check_idealization("STICK", 5)
        self.assertFalse(ok)
        self.assertIn("10", reason)

    def test_shell_valid(self):
        ok, _ = check_idealization("SHELL", 20)
        self.assertTrue(ok)

    def test_shell_low_aspect_ratio_allowed(self):
        # SHELL has no lower aspect-ratio gate
        ok, _ = check_idealization("SHELL", 2)
        self.assertTrue(ok)

    def test_solid_valid(self):
        ok, _ = check_idealization("SOLID", 3)
        self.assertTrue(ok)

    def test_solid_at_limit(self):
        ok, _ = check_idealization("SOLID", 5)
        self.assertTrue(ok)

    def test_solid_aspect_ratio_too_high(self):
        ok, reason = check_idealization("SOLID", 6)
        self.assertFalse(ok)
        self.assertIn("5", reason)

    def test_unknown_idealization(self):
        ok, reason = check_idealization("FRAME", 10)
        self.assertFalse(ok)
        self.assertIn("Unknown", reason)

    def test_zero_aspect_ratio_rejected(self):
        ok, _ = check_idealization("STICK", 0)
        self.assertFalse(ok)

    def test_negative_aspect_ratio_rejected(self):
        ok, _ = check_idealization("SOLID", -1)
        self.assertFalse(ok)

    def test_non_numeric_aspect_ratio_rejected(self):
        ok, reason = check_idealization("STICK", "big")
        self.assertFalse(ok)
        self.assertIn("positive number", reason)


class TestElementType(unittest.TestCase):

    def test_beam_for_stick(self):
        ok, _ = check_element_type("STICK", "BEAM")
        self.assertTrue(ok)

    def test_truss_for_stick(self):
        ok, _ = check_element_type("STICK", "TRUSS")
        self.assertTrue(ok)

    def test_bar_for_stick(self):
        ok, _ = check_element_type("STICK", "BAR")
        self.assertTrue(ok)

    def test_shell_for_shell(self):
        ok, _ = check_element_type("SHELL", "SHELL")
        self.assertTrue(ok)

    def test_membrane_for_shell(self):
        ok, _ = check_element_type("SHELL", "MEMBRANE")
        self.assertTrue(ok)

    def test_hex_for_solid(self):
        ok, _ = check_element_type("SOLID", "HEX")
        self.assertTrue(ok)

    def test_tet_for_solid(self):
        ok, _ = check_element_type("SOLID", "TET")
        self.assertTrue(ok)

    def test_beam_for_solid_rejected(self):
        ok, reason = check_element_type("SOLID", "BEAM")
        self.assertFalse(ok)
        self.assertIn("incompatible", reason)

    def test_shell_for_stick_rejected(self):
        ok, _ = check_element_type("STICK", "SHELL")
        self.assertFalse(ok)

    def test_hex_for_shell_rejected(self):
        ok, _ = check_element_type("SHELL", "HEX")
        self.assertFalse(ok)

    def test_unknown_idealization_rejected(self):
        ok, reason = check_element_type("WIRE", "BEAM")
        self.assertFalse(ok)
        self.assertIn("Unknown", reason)


class TestMeshDensity(unittest.TestCase):

    def test_stress_mode_pass(self):
        # element_size=5, reference=100 -> limit=25; 5 <= 25
        ok, _ = check_mesh_density(5, 100, mode="stress")
        self.assertTrue(ok)

    def test_stress_mode_at_limit(self):
        # element_size=25, reference=100 -> limit=25; 25 <= 25
        ok, _ = check_mesh_density(25, 100, mode="stress")
        self.assertTrue(ok)

    def test_stress_mode_fail(self):
        # element_size=30, reference=100 -> limit=25; 30 > 25
        ok, reason = check_mesh_density(30, 100, mode="stress")
        self.assertFalse(ok)
        self.assertIn("25.0", reason)

    def test_modal_mode_pass(self):
        # element_size=10, reference=120 -> limit=20; 10 <= 20
        ok, _ = check_mesh_density(10, 120, mode="modal")
        self.assertTrue(ok)

    def test_modal_mode_fail(self):
        # element_size=25, reference=120 -> limit=20; 25 > 20
        ok, _ = check_mesh_density(25, 120, mode="modal")
        self.assertFalse(ok)

    def test_invalid_mode_rejected(self):
        ok, reason = check_mesh_density(1, 10, mode="buckling")
        self.assertFalse(ok)
        self.assertIn("buckling", reason)

    def test_zero_element_size_rejected(self):
        ok, _ = check_mesh_density(0, 10)
        self.assertFalse(ok)

    def test_zero_reference_size_rejected(self):
        ok, _ = check_mesh_density(1, 0)
        self.assertFalse(ok)

    def test_negative_element_size_rejected(self):
        ok, _ = check_mesh_density(-1, 10)
        self.assertFalse(ok)


class TestMaterialModel(unittest.TestCase):

    def test_linear_elastic_isotropic_material(self):
        ok, _ = check_material_model("LINEAR_ELASTIC", False, 50)
        self.assertTrue(ok)

    def test_isotropic_model_non_composite(self):
        ok, _ = check_material_model("ISOTROPIC", False, 50)
        self.assertTrue(ok)

    def test_orthotropic_composite(self):
        ok, _ = check_material_model("ORTHOTROPIC", True, 50)
        self.assertTrue(ok)

    def test_laminate_composite(self):
        ok, _ = check_material_model("LAMINATE", True, 80)
        self.assertTrue(ok)

    def test_linear_elastic_on_composite_rejected(self):
        ok, reason = check_material_model("LINEAR_ELASTIC", True, 50)
        self.assertFalse(ok)
        self.assertIn("composite", reason.lower())

    def test_orthotropic_on_non_composite_rejected(self):
        ok, reason = check_material_model("ORTHOTROPIC", False, 50)
        self.assertFalse(ok)
        self.assertIn("Non-composite", reason)

    def test_laminate_on_non_composite_rejected(self):
        ok, _ = check_material_model("LAMINATE", False, 50)
        self.assertFalse(ok)

    def test_large_temp_delta_with_linear_elastic_flagged(self):
        ok, reason = check_material_model("LINEAR_ELASTIC", False, 250)
        self.assertFalse(ok)
        self.assertIn("250", reason)

    def test_large_negative_temp_delta_also_flagged(self):
        ok, _ = check_material_model("LINEAR_ELASTIC", False, -250)
        self.assertFalse(ok)

    def test_temp_delta_at_threshold_passes(self):
        # exactly at threshold is not > threshold, so should pass
        ok, _ = check_material_model("LINEAR_ELASTIC", False, 200)
        self.assertTrue(ok)

    def test_no_temp_delta_passes(self):
        ok, _ = check_material_model("LINEAR_ELASTIC", False, None)
        self.assertTrue(ok)

    def test_unknown_model_rejected(self):
        ok, reason = check_material_model("VISCO_PLASTIC", False, 0)
        self.assertFalse(ok)
        self.assertIn("Unknown", reason)


class TestUnitSystem(unittest.TestCase):

    def test_si_n_m_cartesian(self):
        ok, _ = check_unit_system("SI_N_M", "CARTESIAN")
        self.assertTrue(ok)

    def test_si_n_mm_cylindrical(self):
        ok, _ = check_unit_system("SI_N_MM", "CYLINDRICAL")
        self.assertTrue(ok)

    def test_si_n_mm_spherical(self):
        ok, _ = check_unit_system("SI_N_MM", "SPHERICAL")
        self.assertTrue(ok)

    def test_unknown_unit_system_rejected(self):
        ok, reason = check_unit_system("US_CUSTOMARY", "CARTESIAN")
        self.assertFalse(ok)
        self.assertIn("US_CUSTOMARY", reason)

    def test_unknown_coord_system_rejected(self):
        ok, reason = check_unit_system("SI_N_M", "OBLIQUE")
        self.assertFalse(ok)
        self.assertIn("OBLIQUE", reason)


class TestBoundaryConditions(unittest.TestCase):

    def test_all_justified(self):
        bcs = [
            {"dof": "Tz", "constraint": "fixed", "justification": "Symmetry plane XZ"},
            {"dof": "Rx", "constraint": "fixed", "justification": "Pin joint at node 1"},
        ]
        ok, issues = check_boundary_conditions(bcs)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_empty_list_passes(self):
        ok, issues = check_boundary_conditions([])
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_missing_justification_flagged(self):
        bcs = [{"dof": "Tz", "constraint": "fixed", "justification": ""}]
        ok, issues = check_boundary_conditions(bcs)
        self.assertFalse(ok)
        self.assertEqual(len(issues), 1)

    def test_whitespace_only_justification_flagged(self):
        bcs = [{"dof": "Tx", "constraint": "fixed", "justification": "   "}]
        ok, issues = check_boundary_conditions(bcs)
        self.assertFalse(ok)

    def test_non_list_input_rejected(self):
        ok, issues = check_boundary_conditions("not a list")
        self.assertFalse(ok)
        self.assertTrue(len(issues) > 0)

    def test_non_dict_entry_flagged(self):
        ok, issues = check_boundary_conditions(["not a dict"])
        self.assertFalse(ok)
        self.assertTrue(any("not a dict" in i for i in issues))

    def test_multiple_missing_justifications(self):
        bcs = [
            {"dof": "Tx", "constraint": "fixed", "justification": ""},
            {"dof": "Ty", "constraint": "fixed", "justification": ""},
        ]
        ok, issues = check_boundary_conditions(bcs)
        self.assertFalse(ok)
        self.assertEqual(len(issues), 2)


class TestEvaluateModel(unittest.TestCase):

    def _make_component(self, name, idealization, aspect_ratio, element_type,
                        element_size, reference_size, material_model,
                        is_composite=False, temp_delta_k=50, mesh_mode="stress"):
        return {
            "name": name,
            "idealization": idealization,
            "aspect_ratio": aspect_ratio,
            "element_type": element_type,
            "element_size": element_size,
            "reference_size": reference_size,
            "mesh_mode": mesh_mode,
            "material_model": material_model,
            "is_composite": is_composite,
            "temp_delta_k": temp_delta_k,
        }

    def test_fully_compliant_model(self):
        model = {
            "unit_system": "SI_N_MM",
            "coord_system": "CARTESIAN",
            "components": [
                self._make_component(
                    "main_tube", "STICK", 20, "BEAM", 5, 100, "LINEAR_ELASTIC"
                )
            ],
            "boundary_conditions": [
                {"dof": "all", "constraint": "fixed",
                 "justification": "Rigid interface to launch-vehicle adapter"}
            ],
        }
        result = evaluate_model(model)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_solid_idealization_with_high_aspect_ratio(self):
        model = {
            "unit_system": "SI_N_MM",
            "coord_system": "CARTESIAN",
            "components": [
                self._make_component(
                    "bracket", "SOLID", 8, "HEX", 5, 100, "LINEAR_ELASTIC"
                )
            ],
            "boundary_conditions": [],
        }
        result = evaluate_model(model)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("IDEALIZATION" in f for f in result["findings"]))

    def test_composite_panel_compliant(self):
        model = {
            "unit_system": "SI_N_M",
            "coord_system": "CARTESIAN",
            "components": [
                self._make_component(
                    "cfrp_panel", "SHELL", 50, "SHELL", 0.01, 0.1,
                    "LAMINATE", is_composite=True, temp_delta_k=80
                )
            ],
            "boundary_conditions": [
                {"dof": "Tz", "constraint": "fixed",
                 "justification": "Pinned corner fasteners"}
            ],
        }
        result = evaluate_model(model)
        self.assertTrue(result["compliant"])

    def test_coarse_mesh_detected(self):
        model = {
            "unit_system": "SI_N_MM",
            "coord_system": "CARTESIAN",
            "components": [
                self._make_component(
                    "rib", "SHELL", 10, "SHELL", 50, 100, "LINEAR_ELASTIC"
                )
            ],
            "boundary_conditions": [
                {"dof": "all", "constraint": "fixed", "justification": "Symmetry plane"}
            ],
        }
        result = evaluate_model(model)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("MESH_DENSITY" in f for f in result["findings"]))

    def test_unjustified_bc_flagged(self):
        model = {
            "unit_system": "SI_N_MM",
            "coord_system": "CARTESIAN",
            "components": [
                self._make_component(
                    "strut", "STICK", 12, "BEAM", 5, 100, "LINEAR_ELASTIC"
                )
            ],
            "boundary_conditions": [
                {"dof": "Tz", "constraint": "fixed", "justification": ""}
            ],
        }
        result = evaluate_model(model)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("BC" in f for f in result["findings"]))

    def test_multiple_findings_aggregated(self):
        model = {
            "unit_system": "IMPERIAL",  # invalid
            "coord_system": "CARTESIAN",
            "components": [
                self._make_component(
                    "bad_comp", "SOLID", 9, "BEAM", 50, 100, "LINEAR_ELASTIC"
                )
            ],
            "boundary_conditions": [],
        }
        result = evaluate_model(model)
        self.assertFalse(result["compliant"])
        # Expect at least 3 findings: unit, idealization, element type
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_modal_mesh_criterion_applied(self):
        model = {
            "unit_system": "SI_N_M",
            "coord_system": "CARTESIAN",
            "components": [
                {
                    "name": "panel",
                    "idealization": "SHELL",
                    "aspect_ratio": 30,
                    "element_type": "SHELL",
                    "element_size": 0.005,
                    "reference_size": 0.06,
                    "mesh_mode": "modal",
                    "material_model": "LINEAR_ELASTIC",
                    "is_composite": False,
                    "temp_delta_k": 50,
                }
            ],
            "boundary_conditions": [
                {"dof": "all", "constraint": "fixed",
                 "justification": "Clamped edge per test fixture boundary"}
            ],
        }
        # 0.005 <= 0.06/6 = 0.01 -> passes
        result = evaluate_model(model)
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
