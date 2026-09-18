"""Contract tests for the coating defect grouping and disposition logic."""

import unittest

from q7031_paint_defect_control_logic import (
    DEFECT_FAMILIES,
    DISPOSITION_ORDER,
    LIMIT_TOLERANCE,
    SURFACE_ALLOWANCE_FACTORS,
    assess_defects,
    defect_density_per_m2,
    defect_family_limits,
    grade_defect,
    surface_allowance_factor,
    validate_defect,
    validate_positive,
    worst_disposition,
)


def defect(**overrides):
    base = {
        "family": "pinhole",
        "count": 2,
        "max_dimension_mm": 0.2,
        "surface_category": "general",
    }
    base.update(overrides)
    return base


class ValidatorTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive(2, "x"), 2.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "area_m2")

    def test_defect_record_is_normalised(self):
        record = validate_defect(defect(family="Pinhole", surface_category="General"))
        self.assertEqual(record["family"], "pinhole")
        self.assertEqual(record["surface_category"], "general")

    def test_unrecorded_location_defaults(self):
        self.assertEqual(validate_defect(defect())["location"], "unrecorded")

    def test_missing_defect_key_rejected(self):
        broken = defect()
        del broken["count"]
        with self.assertRaises(ValueError):
            validate_defect(broken)

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(defect(count=0))

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(defect(count=2.5))

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(defect(count=True))

    def test_negative_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(defect(max_dimension_mm=-0.1))


class FamilyAndSurfaceTests(unittest.TestCase):
    def test_every_family_carries_a_disposition(self):
        for name in DEFECT_FAMILIES:
            self.assertIn(DEFECT_FAMILIES[name]["disposition"], DISPOSITION_ORDER)

    def test_family_lookup_is_case_insensitive(self):
        self.assertEqual(
            defect_family_limits("PINHOLE"), defect_family_limits("pinhole")
        )

    def test_family_lookup_returns_a_copy(self):
        limits = defect_family_limits("pinhole")
        limits["max_dimension_mm"] = 99.0
        self.assertAlmostEqual(
            defect_family_limits("pinhole")["max_dimension_mm"], 0.5, places=12
        )

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            defect_family_limits("scratch-mark")

    def test_optical_surface_keeps_no_allowance(self):
        self.assertAlmostEqual(surface_allowance_factor("optical"), 0.0, places=12)

    def test_general_surface_keeps_the_full_allowance(self):
        self.assertAlmostEqual(surface_allowance_factor("general"), 1.0, places=12)

    def test_bonding_is_tighter_than_thermal_control(self):
        self.assertTrue(
            SURFACE_ALLOWANCE_FACTORS["bonding"] < SURFACE_ALLOWANCE_FACTORS["thermal-control"]
        )

    def test_unknown_surface_rejected(self):
        with self.assertRaises(ValueError):
            surface_allowance_factor("wherever")

    def test_non_string_surface_rejected(self):
        with self.assertRaises(ValueError):
            surface_allowance_factor(3)


class DensityTests(unittest.TestCase):
    def test_density_is_count_over_area(self):
        self.assertAlmostEqual(defect_density_per_m2(6, 3.0), 2.0, places=12)

    def test_zero_count_gives_zero_density(self):
        self.assertAlmostEqual(defect_density_per_m2(0, 3.0), 0.0, places=12)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            defect_density_per_m2(-1, 3.0)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            defect_density_per_m2(2.0, 3.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            defect_density_per_m2(2, 0.0)


class GradeDefectTests(unittest.TestCase):
    def test_small_pinhole_population_is_accepted(self):
        record = grade_defect(defect(count=2), 2.0)
        self.assertEqual(record["disposition"], "accept")
        self.assertEqual(record["findings"], [])

    def test_density_exactly_on_the_limit_is_accepted(self):
        record = grade_defect(defect(count=8), 2.0)
        self.assertAlmostEqual(record["density_per_m2"], 4.0, places=12)
        self.assertFalse(record["density_exceeded"])

    def test_dense_pinholes_earn_a_strip(self):
        record = grade_defect(defect(count=40), 2.0)
        self.assertTrue(record["density_exceeded"])
        self.assertEqual(record["disposition"], "strip-and-recoat")

    def test_oversize_pinhole_is_caught_on_size_alone(self):
        record = grade_defect(defect(count=1, max_dimension_mm=1.5), 10.0)
        self.assertTrue(record["size_exceeded"])
        self.assertFalse(record["density_exceeded"])

    def test_a_run_is_never_allowed(self):
        record = grade_defect(defect(family="run", count=1, max_dimension_mm=3.0), 10.0)
        self.assertEqual(record["disposition"], "local-rework")

    def test_contamination_earns_a_strip(self):
        record = grade_defect(
            defect(family="contamination", count=1, max_dimension_mm=1.0), 10.0
        )
        self.assertEqual(record["disposition"], "strip-and-recoat")

    def test_optical_surface_escalates_to_a_referral(self):
        record = grade_defect(defect(count=1, surface_category="optical"), 10.0)
        self.assertEqual(record["disposition"], "refer-to-review-board")

    def test_bonding_surface_tightens_the_size_limit(self):
        general = grade_defect(defect(surface_category="general"), 10.0)
        bonding = grade_defect(defect(surface_category="bonding"), 10.0)
        self.assertAlmostEqual(
            bonding["size_limit_mm"], general["size_limit_mm"] * 0.25, places=12
        )

    def test_same_defect_can_pass_a_panel_and_fail_a_radiator(self):
        general = grade_defect(defect(count=6, max_dimension_mm=0.4), 2.0)
        thermal = grade_defect(
            defect(count=6, max_dimension_mm=0.4, surface_category="thermal-control"), 2.0
        )
        self.assertEqual(general["disposition"], "accept")
        self.assertEqual(thermal["disposition"], "strip-and-recoat")

    def test_both_breaches_are_reported_separately(self):
        record = grade_defect(defect(count=40, max_dimension_mm=1.5), 2.0)
        self.assertEqual(len(record["findings"]), 2)


class WorstDispositionTests(unittest.TestCase):
    def test_empty_lot_is_accepted(self):
        self.assertEqual(worst_disposition([]), "accept")

    def test_strip_beats_rework(self):
        self.assertEqual(
            worst_disposition(["local-rework", "strip-and-recoat", "accept"]),
            "strip-and-recoat",
        )

    def test_referral_beats_everything(self):
        self.assertEqual(
            worst_disposition(["strip-and-recoat", "refer-to-review-board"]),
            "refer-to-review-board",
        )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition(["scrap-it"])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition("accept")


class AssessDefectsTests(unittest.TestCase):
    def test_clean_surface_is_acceptable(self):
        result = assess_defects({"inspected_area_m2": 2.0, "defects": []})
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["total_defect_count"], 0)

    def test_counts_are_grouped_by_family(self):
        result = assess_defects(
            {
                "inspected_area_m2": 4.0,
                "defects": [defect(count=2), defect(count=3),
                            defect(family="inclusion", count=1, max_dimension_mm=0.3)],
            }
        )
        self.assertEqual(result["counts_by_family"]["pinhole"], 5)
        self.assertEqual(result["counts_by_family"]["inclusion"], 1)

    def test_lot_carries_the_worst_disposition(self):
        result = assess_defects(
            {
                "inspected_area_m2": 2.0,
                "defects": [defect(count=1),
                            defect(family="run", count=1, max_dimension_mm=4.0),
                            defect(family="contamination", count=1, max_dimension_mm=2.0)],
            }
        )
        self.assertEqual(result["disposition"], "strip-and-recoat")

    def test_total_density_uses_the_inspected_area(self):
        result = assess_defects(
            {"inspected_area_m2": 4.0, "defects": [defect(count=2), defect(count=2)]}
        )
        self.assertAlmostEqual(result["total_density_per_m2"], 1.0, places=12)

    def test_findings_from_every_defect_are_kept(self):
        result = assess_defects(
            {
                "inspected_area_m2": 1.0,
                "defects": [defect(count=40, max_dimension_mm=1.5),
                            defect(family="sag", count=1, max_dimension_mm=5.0)],
            }
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_defects({"defects": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_defects([defect()])

    def test_non_sequence_defects_rejected(self):
        with self.assertRaises(ValueError):
            assess_defects({"inspected_area_m2": 2.0, "defects": defect()})

    def test_tolerance_is_small(self):
        self.assertAlmostEqual(LIMIT_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=1)
