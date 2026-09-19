"""Contract tests for the clause 4.7.7.4 mechanism grounding and bonding logic."""

import unittest

from e3301_grounding_bonding_logic import (
    ASPECT_RATIO_LIMIT,
    DC_RESISTANCE_LIMIT_OHM,
    MATERIAL_RESISTIVITY_OHM_M,
    RATIO_TOLERANCE,
    assess_bonding,
    aspect_ratio,
    bulk_resistance_ohm,
    coverage_findings,
    grade_strap,
    parallel_resistance_ohm,
    strap_dc_resistance_ohm,
    validate_strap,
)


def good_strap(**overrides):
    strap = {
        "id": "BS-1",
        "mechanism": "SADM",
        "length_m": 0.060,
        "width_m": 0.025,
        "thickness_m": 0.0005,
        "material": "tinned-copper-braid",
        "joint_resistance_ohm": 5.0e-4,
    }
    strap.update(overrides)
    return strap


class ValidateStrapTests(unittest.TestCase):
    def test_returns_resistivity_for_the_material(self):
        record = validate_strap(good_strap())
        self.assertAlmostEqual(record["resistivity_ohm_m"],
                               MATERIAL_RESISTIVITY_OHM_M["tinned-copper-braid"], places=12)

    def test_material_case_is_normalised(self):
        self.assertEqual(validate_strap(good_strap(material="Copper"))["material"], "copper")

    def test_every_tabulated_material_validates(self):
        for material in MATERIAL_RESISTIVITY_OHM_M:
            self.assertEqual(validate_strap(good_strap(material=material))["material"], material)

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap(good_strap(material="unobtainium"))

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap(good_strap(width_m=0.0))

    def test_negative_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap(good_strap(thickness_m=-0.0005))

    def test_negative_joint_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap(good_strap(joint_resistance_ohm=-1.0e-4))

    def test_missing_key_rejected(self):
        strap = good_strap()
        del strap["mechanism"]
        with self.assertRaises(ValueError):
            validate_strap(strap)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap("BS-1")

    def test_blank_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap(good_strap(mechanism="  "))

    def test_boolean_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_strap(good_strap(length_m=True))


class GeometryTests(unittest.TestCase):
    def test_ratio_is_length_over_width(self):
        self.assertAlmostEqual(aspect_ratio(0.080, 0.020), 4.0, places=9)

    def test_wider_strap_lowers_the_ratio(self):
        self.assertAlmostEqual(aspect_ratio(0.080, 0.040), 2.0, places=9)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            aspect_ratio(0.0, 0.020)

    def test_limit_constant_is_four(self):
        self.assertAlmostEqual(ASPECT_RATIO_LIMIT, 4.0, places=9)

    def test_ratio_exactly_on_the_limit_does_not_meet_it(self):
        graded = grade_strap(good_strap(length_m=0.080, width_m=0.020))
        self.assertAlmostEqual(graded["aspect_ratio"], ASPECT_RATIO_LIMIT, places=9)
        self.assertFalse(graded["ratio_ok"])

    def test_ratio_below_the_limit_passes(self):
        graded = grade_strap(good_strap(length_m=0.060, width_m=0.025))
        self.assertTrue(graded["ratio_ok"])

    def test_ratio_tolerance_is_tight(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class ResistanceTests(unittest.TestCase):
    def test_bulk_resistance_matches_the_closed_form(self):
        value = bulk_resistance_ohm(1.0, 1.0, 1.0, 2.0e-8)
        self.assertAlmostEqual(value, 2.0e-8, places=15)

    def test_resistance_scales_with_length(self):
        short = bulk_resistance_ohm(0.05, 0.02, 0.0005, 1.72e-8)
        long_strap = bulk_resistance_ohm(0.10, 0.02, 0.0005, 1.72e-8)
        self.assertAlmostEqual(long_strap, 2.0 * short, places=15)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            bulk_resistance_ohm(0.05, 0.02, 0.0, 1.72e-8)

    def test_joints_dominate_a_short_braid(self):
        total = strap_dc_resistance_ohm(good_strap())
        self.assertGreater(total, 9.0e-4)

    def test_measured_value_overrides_the_model(self):
        total = strap_dc_resistance_ohm(good_strap(measured_resistance_ohm=2.5e-3))
        self.assertAlmostEqual(total, 2.5e-3, places=12)

    def test_zero_measured_resistance_rejected(self):
        with self.assertRaises(ValueError):
            strap_dc_resistance_ohm(good_strap(measured_resistance_ohm=0.0))

    def test_resistance_limit_constant_is_ten_milliohm(self):
        self.assertAlmostEqual(DC_RESISTANCE_LIMIT_OHM, 0.010, places=12)

    def test_resistance_exactly_on_the_limit_does_not_meet_it(self):
        graded = grade_strap(good_strap(measured_resistance_ohm=DC_RESISTANCE_LIMIT_OHM))
        self.assertAlmostEqual(graded["dc_resistance_ohm"], DC_RESISTANCE_LIMIT_OHM, places=12)
        self.assertFalse(graded["resistance_ok"])

    def test_high_resistance_is_flagged(self):
        graded = grade_strap(good_strap(measured_resistance_ohm=0.05))
        self.assertFalse(graded["compliant"])
        self.assertEqual(len(graded["findings"]), 1)

    def test_two_equal_bonds_in_parallel_halve_the_resistance(self):
        self.assertAlmostEqual(parallel_resistance_ohm([0.004, 0.004]), 0.002, places=12)

    def test_parallel_needs_at_least_one_bond(self):
        with self.assertRaises(ValueError):
            parallel_resistance_ohm([])

    def test_parallel_rejects_a_zero_branch(self):
        with self.assertRaises(ValueError):
            parallel_resistance_ohm([0.004, 0.0])


class GradeStrapTests(unittest.TestCase):
    def test_healthy_strap_is_compliant(self):
        graded = grade_strap(good_strap())
        self.assertTrue(graded["compliant"])
        self.assertEqual(graded["findings"], [])

    def test_long_narrow_strap_raises_the_geometry_finding(self):
        graded = grade_strap(good_strap(length_m=0.200, width_m=0.010))
        self.assertFalse(graded["ratio_ok"])
        self.assertIn("length-to-width", graded["findings"][0])

    def test_both_findings_can_appear_together(self):
        graded = grade_strap(
            good_strap(length_m=0.200, width_m=0.010, measured_resistance_ohm=0.02)
        )
        self.assertEqual(len(graded["findings"]), 2)

    def test_custom_limits_are_honoured(self):
        graded = grade_strap(good_strap(length_m=0.200, width_m=0.010), ratio_limit=25.0)
        self.assertTrue(graded["ratio_ok"])

    def test_zero_ratio_limit_rejected(self):
        with self.assertRaises(ValueError):
            grade_strap(good_strap(), ratio_limit=0.0)


class CoverageTests(unittest.TestCase):
    def test_every_mechanism_bonded_is_clean(self):
        result = coverage_findings(["SADM"], [good_strap()])
        self.assertEqual(result["findings"], [])
        self.assertIn("SADM", result["bonded"])

    def test_unbonded_mechanism_is_flagged(self):
        result = coverage_findings(["SADM", "APM"], [good_strap()])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("APM", result["findings"][0])

    def test_orphan_strap_is_flagged(self):
        result = coverage_findings(["SADM"], [good_strap(id="BS-9", mechanism="GHOST")])
        self.assertEqual(len(result["findings"]), 2)

    def test_duplicate_mechanism_name_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(["SADM", "SADM"], [good_strap()])

    def test_empty_mechanism_inventory_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings([], [good_strap()])

    def test_two_bonds_on_one_mechanism_are_both_recorded(self):
        result = coverage_findings(["SADM"], [good_strap(), good_strap(id="BS-2")])
        self.assertEqual(len(result["bonded"]["SADM"]), 2)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "mechanisms": ["SADM"],
            "straps": [good_strap()],
        }
        spec.update(overrides)
        return spec

    def test_healthy_design_reports_no_findings(self):
        result = assess_bonding(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_one_record_per_strap(self):
        result = assess_bonding(self._spec(straps=[good_strap(), good_strap(id="BS-2")]))
        self.assertEqual(len(result["straps"]), 2)

    def test_duplicate_strap_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_bonding(self._spec(straps=[good_strap(), good_strap()]))

    def test_geometry_finding_fails_the_assessment(self):
        result = assess_bonding(self._spec(straps=[good_strap(length_m=0.3, width_m=0.01)]))
        self.assertFalse(result["compliant"])

    def test_missing_bond_fails_the_assessment(self):
        result = assess_bonding(self._spec(mechanisms=["SADM", "BAPTA"]))
        self.assertFalse(result["compliant"])

    def test_empty_strap_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_bonding(self._spec(straps=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["mechanisms"]
        with self.assertRaises(ValueError):
            assess_bonding(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bonding(["straps"])

    def test_limit_overrides_reach_every_strap(self):
        result = assess_bonding(
            self._spec(straps=[good_strap(measured_resistance_ohm=2.0e-3)],
                       resistance_limit_ohm=1.0e-3)
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
