#!/usr/bin/env python3
"""Contract test for the Class 1 part and material restrictions (offline)."""

import copy
import unittest

from q60_class_1_part_material_restrictions_logic import (
    HERMETIC_PACKAGES,
    MAX_MOISTURE_SENSITIVITY_LEVEL,
    MAX_TIN_MASS_FRACTION,
    PACKAGE_TYPES,
    PERMITTED,
    PERMITTED_WITH_MITIGATION,
    RESTRICTED,
    RESTRICTED_MATERIALS,
    TRACE_MASS_FRACTION,
    assess_finish,
    assess_material,
    assess_packaging,
    assess_part_restrictions,
    humid_life_ratio,
    is_hermetic,
    tin_whisker_margin,
)

GOOD_CASE = {
    "part_reference": "op-amp-hermetic-ceramic-8-lead",
    "package_type": "hermetic-ceramic",
    "finishes": [
        {"surface": "lead-finish", "tin_mass_fraction": 0.60},
        {"surface": "lid-seal-ring", "tin_mass_fraction": 0.10},
    ],
    "declared_materials": {"cadmium": 0.0, "zinc": 0.0},
}

NON_HERMETIC_CASE = {
    "part_reference": "dc-dc-plastic-qfn-24",
    "package_type": "non-hermetic-plastic-moulded",
    "non_hermetic_justification_approved": True,
    "moisture_sensitivity_level": 2,
    "humid_operating_hours": 500.0,
    "demonstrated_humid_life_hours": 2000.0,
    "finishes": [{"surface": "lead-finish", "tin_mass_fraction": 0.60}],
}


def _case(base=None, **overrides):
    case = copy.deepcopy(GOOD_CASE if base is None else base)
    case.update(overrides)
    return case


class PackageTypeTests(unittest.TestCase):
    def test_ceramic_case_is_hermetic(self):
        self.assertTrue(is_hermetic("hermetic-ceramic"))

    def test_moulded_plastic_case_is_not_hermetic(self):
        self.assertFalse(is_hermetic("non-hermetic-plastic-moulded"))

    def test_bare_die_is_not_hermetic(self):
        self.assertFalse(is_hermetic("bare-die-on-substrate"))

    def test_unknown_package_type_rejected(self):
        with self.assertRaises(ValueError):
            is_hermetic("shrink-wrap")

    def test_hermetic_set_is_a_subset_of_the_package_types(self):
        self.assertTrue(HERMETIC_PACKAGES.issubset(set(PACKAGE_TYPES)))


class TinFinishTests(unittest.TestCase):
    def test_margin_is_the_distance_to_the_threshold(self):
        self.assertAlmostEqual(tin_whisker_margin(0.60), 0.37, places=9)

    def test_margin_is_negative_over_the_threshold(self):
        self.assertLess(tin_whisker_margin(0.999), -1.0e-6)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            tin_whisker_margin(1.4)

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            tin_whisker_margin(-0.1)

    def test_non_numeric_fraction_rejected(self):
        with self.assertRaises(ValueError):
            tin_whisker_margin("mostly tin")

    def test_alloyed_finish_is_permitted(self):
        graded = assess_finish({"surface": "lead-finish", "tin_mass_fraction": 0.60})
        self.assertEqual(graded["verdict"], PERMITTED)
        self.assertFalse(graded["near_pure_tin"])

    def test_finish_exactly_on_the_threshold_counts_as_near_pure(self):
        graded = assess_finish(
            {"surface": "lead-finish", "tin_mass_fraction": MAX_TIN_MASS_FRACTION}
        )
        self.assertTrue(graded["near_pure_tin"])
        self.assertAlmostEqual(graded["whisker_margin"], 0.0, places=9)
        self.assertEqual(graded["verdict"], RESTRICTED)

    def test_near_pure_tin_without_rework_is_restricted(self):
        graded = assess_finish({"surface": "lead-finish", "tin_mass_fraction": 0.999})
        self.assertEqual(graded["verdict"], RESTRICTED)
        self.assertFalse(graded["acceptable"])

    def test_near_pure_tin_with_a_solder_dip_is_permitted_with_mitigation(self):
        graded = assess_finish(
            {
                "surface": "lead-finish",
                "tin_mass_fraction": 0.999,
                "mitigation": "hot-solder-dip",
            }
        )
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(graded["acceptable"])

    def test_unknown_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish(
                {
                    "surface": "lead-finish",
                    "tin_mass_fraction": 0.999,
                    "mitigation": "hope",
                }
            )

    def test_finish_without_a_surface_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish({"tin_mass_fraction": 0.60})


class RestrictedMaterialTests(unittest.TestCase):
    def test_absent_material_is_permitted(self):
        graded = assess_material("cadmium", 0.0)
        self.assertEqual(graded["verdict"], PERMITTED)
        self.assertFalse(graded["present_above_trace"])

    def test_material_exactly_at_the_trace_is_not_a_finding(self):
        graded = assess_material("zinc", TRACE_MASS_FRACTION)
        self.assertFalse(graded["present_above_trace"])
        self.assertEqual(graded["verdict"], PERMITTED)

    def test_material_above_the_trace_is_restricted(self):
        graded = assess_material("cadmium", 0.02)
        self.assertEqual(graded["verdict"], RESTRICTED)

    def test_material_above_the_trace_with_a_deviation_is_permitted_with_mitigation(self):
        graded = assess_material("zinc", 0.02, "rfd-0231")
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(graded["acceptable"])

    def test_blank_deviation_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_material("zinc", 0.02, "   ")

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            assess_material("unobtainium", 0.02)

    def test_every_restricted_material_is_graded_the_same_way(self):
        for material in RESTRICTED_MATERIALS:
            self.assertEqual(assess_material(material, 0.5)["verdict"], RESTRICTED)


class PackagingTests(unittest.TestCase):
    def test_hermetic_case_needs_no_further_argument(self):
        graded = assess_packaging(GOOD_CASE)
        self.assertEqual(graded["verdict"], PERMITTED)
        self.assertEqual(graded["findings"], [])

    def test_backed_non_hermetic_case_is_permitted_with_mitigation(self):
        graded = assess_packaging(NON_HERMETIC_CASE)
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(graded["acceptable"])

    def test_non_hermetic_case_without_an_agreed_justification_is_restricted(self):
        graded = assess_packaging(
            _case(NON_HERMETIC_CASE, non_hermetic_justification_approved=False)
        )
        self.assertEqual(graded["verdict"], RESTRICTED)

    def test_moisture_level_above_the_ceiling_is_a_finding(self):
        graded = assess_packaging(
            _case(
                NON_HERMETIC_CASE,
                moisture_sensitivity_level=MAX_MOISTURE_SENSITIVITY_LEVEL + 1,
            )
        )
        self.assertFalse(graded["acceptable"])
        self.assertTrue(
            any("moisture sensitivity level" in f for f in graded["findings"])
        )

    def test_life_ratio_exactly_on_unity_still_passes(self):
        graded = assess_packaging(
            _case(
                NON_HERMETIC_CASE,
                humid_operating_hours=500.0,
                demonstrated_humid_life_hours=1000.0,
            )
        )
        self.assertAlmostEqual(graded["humid_life_ratio"], 1.0, places=9)
        self.assertTrue(graded["acceptable"])

    def test_short_damp_life_is_a_finding(self):
        graded = assess_packaging(
            _case(NON_HERMETIC_CASE, demonstrated_humid_life_hours=400.0)
        )
        self.assertFalse(graded["acceptable"])
        self.assertTrue(any("demonstrated damp life" in f for f in graded["findings"]))

    def test_non_hermetic_case_without_a_moisture_level_rejected(self):
        case = _case(NON_HERMETIC_CASE)
        del case["moisture_sensitivity_level"]
        with self.assertRaises(ValueError):
            assess_packaging(case)

    def test_moisture_level_outside_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging(_case(NON_HERMETIC_CASE, moisture_sensitivity_level=9))

    def test_zero_humid_hours_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging(_case(NON_HERMETIC_CASE, humid_operating_hours=0.0))

    def test_life_ratio_carries_the_margin(self):
        self.assertAlmostEqual(humid_life_ratio(500.0, 2000.0), 2.0, places=9)


class AssessPartRestrictionsTests(unittest.TestCase):
    def test_clean_hermetic_part_is_permitted(self):
        result = assess_part_restrictions(GOOD_CASE)
        self.assertEqual(result["verdict"], PERMITTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_mitigations"], [])

    def test_backed_non_hermetic_part_is_permitted_with_mitigation(self):
        result = assess_part_restrictions(NON_HERMETIC_CASE)
        self.assertEqual(result["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(result["acceptable"])

    def test_near_pure_tin_finish_restricts_the_part(self):
        case = _case()
        case["finishes"][0]["tin_mass_fraction"] = 0.999
        result = assess_part_restrictions(case)
        self.assertEqual(result["verdict"], RESTRICTED)
        self.assertTrue(any("tin mass fraction" in f for f in result["findings"]))

    def test_reworked_tin_finish_becomes_a_procurement_condition(self):
        case = _case()
        case["finishes"][0]["tin_mass_fraction"] = 0.999
        case["finishes"][0]["mitigation"] = "hot-solder-dip"
        result = assess_part_restrictions(case)
        self.assertEqual(result["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(
            any("procurement condition" in m for m in result["required_mitigations"])
        )

    def test_cadmium_above_the_trace_restricts_the_part(self):
        result = assess_part_restrictions(_case(declared_materials={"cadmium": 0.03}))
        self.assertEqual(result["verdict"], RESTRICTED)
        self.assertTrue(any("cadmium is present" in f for f in result["findings"]))

    def test_agreed_deviation_carries_the_material_into_the_file(self):
        result = assess_part_restrictions(
            _case(
                declared_materials={"zinc": 0.03},
                approved_deviations={"zinc": "rfd-0231"},
            )
        )
        self.assertEqual(result["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(
            any("rfd-0231" in m for m in result["required_mitigations"])
        )

    def test_undeclared_material_is_treated_as_absent_not_as_unknown(self):
        result = assess_part_restrictions(_case(declared_materials={}))
        graded = {entry["material"]: entry for entry in result["materials"]}
        self.assertEqual(set(graded), set(RESTRICTED_MATERIALS))
        self.assertEqual(graded["mercury"]["verdict"], PERMITTED)

    def test_tightest_finish_is_named(self):
        result = assess_part_restrictions(GOOD_CASE)
        self.assertEqual(result["tightest_finish"], "lead-finish")
        self.assertAlmostEqual(result["tightest_whisker_margin"], 0.37, places=9)

    def test_duplicate_finish_surface_rejected(self):
        case = _case()
        case["finishes"].append({"surface": "lead-finish", "tin_mass_fraction": 0.20})
        with self.assertRaises(ValueError):
            assess_part_restrictions(case)

    def test_empty_finish_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_restrictions(_case(finishes=[]))

    def test_material_outside_the_restricted_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_restrictions(_case(declared_materials={"gold": 0.02}))

    def test_deviation_for_an_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_restrictions(_case(approved_deviations={"gold": "rfd-0231"}))

    def test_missing_part_reference_rejected(self):
        case = _case()
        del case["part_reference"]
        with self.assertRaises(ValueError):
            assess_part_restrictions(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_restrictions(["op-amp-hermetic-ceramic-8-lead"])

    def test_every_package_type_is_graded_without_an_exception(self):
        for package_type in PACKAGE_TYPES:
            case = _case(NON_HERMETIC_CASE, package_type=package_type)
            case["part_reference"] = "candidate-%s" % package_type
            result = assess_part_restrictions(case)
            self.assertIn(
                result["verdict"], (PERMITTED, PERMITTED_WITH_MITIGATION, RESTRICTED)
            )


if __name__ == "__main__":
    unittest.main(verbosity=1)
