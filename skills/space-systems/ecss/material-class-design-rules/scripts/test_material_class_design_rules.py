"""
Contract tests for material_class_design_rules_logic.py
ECSS-E-ST-32C §4.5.9–§4.5.12

Run: python3 test_material_class_design_rules.py
stdlib unittest; deterministic; offline.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from material_class_design_rules_logic import (
    categorize_material_class,
    check_metal_design_rules,
    check_non_metallic_design_rules,
    check_composite_design_rules,
    check_adhesive_bonded_design_rules,
    TML_LIMIT_PCT,
    CVCM_LIMIT_PCT,
    BOND_LINE_MIN_MM,
    BOND_LINE_MAX_MM,
    ELONGATION_MIN_PCT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metal_spec(**overrides):
    base = dict(
        material_id="ALUMINIUM",
        yield_mpa=270.0,
        ultimate_mpa=310.0,
        elongation_pct=8.0,
        scc_susceptible=False,
        scc_mitigation=False,
        contact_materials=[],
        galvanic_protection=False,
    )
    base.update(overrides)
    return base


def _non_metallic_spec(**overrides):
    base = dict(
        tml_pct=0.5,
        cvcm_pct=0.05,
        radiation_qualified=True,
        temp_min_c=-60.0,
        temp_max_c=120.0,
    )
    base.update(overrides)
    return base


def _composite_spec(**overrides):
    base = dict(
        symmetric_layup=True,
        balanced_layup=True,
        hygrothermal_knockdown_applied=True,
        min_ply_thickness_mm=0.125,
        zero_ply_fraction=0.50,
        micro_crack_assessment=False,
    )
    base.update(overrides)
    return base


def _adhesive_spec(**overrides):
    base = dict(
        bond_line_thickness_mm=0.20,
        surface_cleaned=True,
        primer_applied=True,
        thermal_cycling_load_considered=True,
        peel_stress_mpa=2.0,
        peel_allowable_mpa=5.0,
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# categorize_material_class
# ---------------------------------------------------------------------------

class TestCategorizeValidClasses(unittest.TestCase):

    def test_categorize_metal_returns_canonical(self):
        result = categorize_material_class("METAL")
        self.assertEqual(result, "METAL")

    def test_categorize_non_metallic_mixed_case(self):
        result = categorize_material_class("non_metallic")
        self.assertEqual(result, "NON_METALLIC")

    def test_categorize_composite_with_spaces(self):
        result = categorize_material_class("composite")
        self.assertEqual(result, "COMPOSITE")

    def test_categorize_adhesive_bonded_hyphen(self):
        result = categorize_material_class("adhesive-bonded")
        self.assertEqual(result, "ADHESIVE_BONDED")

    def test_categorize_unknown_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            categorize_material_class("CERAMIC")
        self.assertIn("Unrecognized", str(ctx.exception))


# ---------------------------------------------------------------------------
# Metal rules — §4.5.9
# ---------------------------------------------------------------------------

class TestMetalDesignRules(unittest.TestCase):

    def test_metal_fully_compliant_returns_empty(self):
        violations = check_metal_design_rules(_metal_spec())
        self.assertEqual(violations, [])

    def test_metal_elongation_below_floor_flagged(self):
        violations = check_metal_design_rules(_metal_spec(elongation_pct=1.5))
        self.assertTrue(
            any("ductility floor" in v for v in violations),
            f"Expected ductility floor violation; got {violations}",
        )

    def test_metal_elongation_exactly_at_floor_accepted(self):
        violations = check_metal_design_rules(_metal_spec(elongation_pct=ELONGATION_MIN_PCT))
        self.assertFalse(any("ductility" in v for v in violations))

    def test_metal_scc_susceptible_without_mitigation_flagged(self):
        violations = check_metal_design_rules(
            _metal_spec(scc_susceptible=True, scc_mitigation=False)
        )
        self.assertTrue(any("SCC" in v for v in violations))

    def test_metal_scc_susceptible_with_mitigation_accepted(self):
        violations = check_metal_design_rules(
            _metal_spec(scc_susceptible=True, scc_mitigation=True)
        )
        self.assertFalse(any("SCC" in v for v in violations))

    def test_metal_galvanic_incompatible_pair_without_protection_flagged(self):
        violations = check_metal_design_rules(
            _metal_spec(
                material_id="ALUMINIUM",
                contact_materials=["COPPER"],
                galvanic_protection=False,
            )
        )
        self.assertTrue(any("Galvanic" in v for v in violations))

    def test_metal_galvanic_incompatible_pair_with_protection_accepted(self):
        violations = check_metal_design_rules(
            _metal_spec(
                material_id="ALUMINIUM",
                contact_materials=["COPPER"],
                galvanic_protection=True,
            )
        )
        self.assertFalse(any("Galvanic" in v for v in violations))

    def test_metal_ultimate_below_yield_flagged(self):
        violations = check_metal_design_rules(_metal_spec(yield_mpa=300.0, ultimate_mpa=290.0))
        self.assertTrue(any("ultimate_mpa" in v for v in violations))

    def test_metal_missing_key_raises_key_error(self):
        spec = _metal_spec()
        del spec["yield_mpa"]
        with self.assertRaises(KeyError):
            check_metal_design_rules(spec)


# ---------------------------------------------------------------------------
# Non-metallic rules — §4.5.10
# ---------------------------------------------------------------------------

class TestNonMetallicDesignRules(unittest.TestCase):

    def test_non_metallic_fully_compliant_returns_empty(self):
        violations = check_non_metallic_design_rules(_non_metallic_spec())
        self.assertEqual(violations, [])

    def test_non_metallic_tml_exceeded_flagged(self):
        violations = check_non_metallic_design_rules(
            _non_metallic_spec(tml_pct=TML_LIMIT_PCT + 0.01)
        )
        self.assertTrue(any("TML" in v for v in violations))

    def test_non_metallic_tml_at_limit_accepted(self):
        violations = check_non_metallic_design_rules(
            _non_metallic_spec(tml_pct=TML_LIMIT_PCT)
        )
        self.assertFalse(any("TML" in v for v in violations))

    def test_non_metallic_cvcm_exceeded_flagged(self):
        violations = check_non_metallic_design_rules(
            _non_metallic_spec(cvcm_pct=CVCM_LIMIT_PCT + 0.01)
        )
        self.assertTrue(any("CVCM" in v for v in violations))

    def test_non_metallic_not_radiation_qualified_flagged(self):
        violations = check_non_metallic_design_rules(
            _non_metallic_spec(radiation_qualified=False)
        )
        self.assertTrue(any("radiation" in v.lower() for v in violations))

    def test_non_metallic_inverted_temperature_range_flagged(self):
        violations = check_non_metallic_design_rules(
            _non_metallic_spec(temp_min_c=80.0, temp_max_c=20.0)
        )
        self.assertTrue(any("temp_max_c" in v for v in violations))

    def test_non_metallic_missing_key_raises_key_error(self):
        spec = _non_metallic_spec()
        del spec["tml_pct"]
        with self.assertRaises(KeyError):
            check_non_metallic_design_rules(spec)


# ---------------------------------------------------------------------------
# Composite rules — §4.5.11
# ---------------------------------------------------------------------------

class TestCompositeDesignRules(unittest.TestCase):

    def test_composite_fully_compliant_returns_empty(self):
        violations = check_composite_design_rules(_composite_spec())
        self.assertEqual(violations, [])

    def test_composite_unsymmetric_layup_flagged(self):
        violations = check_composite_design_rules(_composite_spec(symmetric_layup=False))
        self.assertTrue(any("symmetric" in v.lower() for v in violations))

    def test_composite_unbalanced_layup_flagged(self):
        violations = check_composite_design_rules(_composite_spec(balanced_layup=False))
        self.assertTrue(any("balanced" in v.lower() for v in violations))

    def test_composite_missing_hygrothermal_knockdown_flagged(self):
        violations = check_composite_design_rules(
            _composite_spec(hygrothermal_knockdown_applied=False)
        )
        self.assertTrue(any("hygrothermal" in v.lower() for v in violations))

    def test_composite_high_zero_ply_fraction_no_assessment_flagged(self):
        violations = check_composite_design_rules(
            _composite_spec(zero_ply_fraction=0.85, micro_crack_assessment=False)
        )
        self.assertTrue(any("micro-crack" in v.lower() for v in violations))

    def test_composite_high_zero_ply_fraction_with_assessment_accepted(self):
        violations = check_composite_design_rules(
            _composite_spec(zero_ply_fraction=0.85, micro_crack_assessment=True)
        )
        self.assertFalse(any("micro-crack" in v.lower() for v in violations))

    def test_composite_zero_ply_at_threshold_boundary_accepted(self):
        violations = check_composite_design_rules(
            _composite_spec(zero_ply_fraction=0.80, micro_crack_assessment=False)
        )
        self.assertFalse(any("micro-crack" in v.lower() for v in violations))

    def test_composite_missing_key_raises_key_error(self):
        spec = _composite_spec()
        del spec["symmetric_layup"]
        with self.assertRaises(KeyError):
            check_composite_design_rules(spec)


# ---------------------------------------------------------------------------
# Adhesive-bonded rules — §4.5.12
# ---------------------------------------------------------------------------

class TestAdhesiveBondedDesignRules(unittest.TestCase):

    def test_adhesive_fully_compliant_returns_empty(self):
        violations = check_adhesive_bonded_design_rules(_adhesive_spec())
        self.assertEqual(violations, [])

    def test_adhesive_bond_line_too_thin_flagged(self):
        violations = check_adhesive_bonded_design_rules(
            _adhesive_spec(bond_line_thickness_mm=BOND_LINE_MIN_MM - 0.01)
        )
        self.assertTrue(any("below the minimum" in v for v in violations))

    def test_adhesive_bond_line_too_thick_flagged(self):
        violations = check_adhesive_bonded_design_rules(
            _adhesive_spec(bond_line_thickness_mm=BOND_LINE_MAX_MM + 0.01)
        )
        self.assertTrue(any("exceeds the maximum" in v for v in violations))

    def test_adhesive_bond_line_at_limits_accepted(self):
        for t in [BOND_LINE_MIN_MM, BOND_LINE_MAX_MM]:
            with self.subTest(thickness=t):
                violations = check_adhesive_bonded_design_rules(
                    _adhesive_spec(bond_line_thickness_mm=t)
                )
                thickness_violations = [
                    v for v in violations
                    if "below the minimum" in v or "exceeds the maximum" in v
                ]
                self.assertEqual(thickness_violations, [])

    def test_adhesive_no_surface_cleaning_flagged(self):
        violations = check_adhesive_bonded_design_rules(_adhesive_spec(surface_cleaned=False))
        self.assertTrue(any("cleaned" in v.lower() for v in violations))

    def test_adhesive_no_primer_flagged(self):
        violations = check_adhesive_bonded_design_rules(_adhesive_spec(primer_applied=False))
        self.assertTrue(any("primer" in v.lower() for v in violations))

    def test_adhesive_thermal_cycling_load_absent_flagged(self):
        violations = check_adhesive_bonded_design_rules(
            _adhesive_spec(thermal_cycling_load_considered=False)
        )
        self.assertTrue(any("thermal-cycling" in v.lower() for v in violations))

    def test_adhesive_peel_stress_exceeds_allowable_flagged(self):
        violations = check_adhesive_bonded_design_rules(
            _adhesive_spec(peel_stress_mpa=6.0, peel_allowable_mpa=5.0)
        )
        self.assertTrue(any("Peel stress" in v for v in violations))

    def test_adhesive_peel_stress_at_allowable_accepted(self):
        violations = check_adhesive_bonded_design_rules(
            _adhesive_spec(peel_stress_mpa=5.0, peel_allowable_mpa=5.0)
        )
        self.assertFalse(any("Peel stress" in v for v in violations))

    def test_adhesive_missing_key_raises_key_error(self):
        spec = _adhesive_spec()
        del spec["peel_stress_mpa"]
        with self.assertRaises(KeyError):
            check_adhesive_bonded_design_rules(spec)


if __name__ == "__main__":
    unittest.main()
