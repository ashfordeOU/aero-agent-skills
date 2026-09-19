"""Contract test for the total-ionising-dose hardness assurance leaf."""

import unittest

from q6015_total_ionising_dose_hardness_assurance_logic import (
    DOSE_SENSITIVITY_BANDS,
    EVIDENCE_REQUIRED_MARGIN,
    FINDING_CAPABILITY_BELOW_DOSE,
    FINDING_GENERIC_DATA_LATE,
    FINDING_MARGIN_SHORTFALL,
    FINDING_NO_TEST,
    achieved_design_margin,
    assess_part,
    assess_total_ionising_dose,
    design_dose_krad,
    dose_at_shielding,
    dose_sensitivity_group,
    evidence_findings,
    margin_meets_requirement,
    required_design_margin,
    validate_dose_depth_curve,
    validate_mission,
    validate_part,
)

CURVE = [(1.0, 100.0), (2.0, 50.0), (4.0, 25.0), (10.0, 10.0)]


def mission(**kw):
    record = {
        "curve_duration_years": 5.0,
        "required_lifetime_years": 5.0,
        "phase": "phase-b",
    }
    record.update(kw)
    return record


def part(pid="U1", **kw):
    record = {
        "id": pid,
        "family": "bipolar-linear",
        "evidence": "flight-lot-test",
        "shielding_mm": 2.0,
        "capability_krad": 200.0,
    }
    record.update(kw)
    return record


class TestCurveValidation(unittest.TestCase):
    def test_valid_curve_is_normalized_to_pairs(self):
        points = validate_dose_depth_curve(CURVE)
        self.assertEqual(len(points), 4)
        self.assertAlmostEqual(points[0][1], 100.0, places=9)

    def test_single_point_curve_raises(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(1.0, 100.0)])

    def test_non_ascending_thickness_raises(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(2.0, 100.0), (1.0, 50.0)])

    def test_dose_rising_with_shielding_raises(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(1.0, 50.0), (2.0, 100.0)])

    def test_non_positive_thickness_raises(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(0.0, 100.0), (2.0, 50.0)])

    def test_malformed_point_raises(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(1.0, 100.0), (2.0,)])


class TestDoseAtShielding(unittest.TestCase):
    def test_tabulated_point_returns_its_own_dose(self):
        self.assertAlmostEqual(dose_at_shielding(CURVE, 2.0), 50.0, places=9)

    def test_interpolation_lands_between_neighbours(self):
        value = dose_at_shielding(CURVE, 3.0)
        self.assertLess(value, 50.0)
        self.assertGreater(value, 25.0)

    def test_thickness_below_span_is_refused(self):
        with self.assertRaises(ValueError):
            dose_at_shielding(CURVE, 0.5)

    def test_thickness_above_span_is_refused(self):
        with self.assertRaises(ValueError):
            dose_at_shielding(CURVE, 25.0)

    def test_flat_segment_returns_the_flat_value(self):
        flat = [(1.0, 40.0), (2.0, 40.0), (3.0, 20.0)]
        self.assertAlmostEqual(dose_at_shielding(flat, 1.5), 40.0, places=9)


class TestLifetimeScaling(unittest.TestCase):
    def test_same_duration_leaves_the_dose_alone(self):
        self.assertAlmostEqual(design_dose_krad(50.0, 5.0, 5.0), 50.0, places=9)

    def test_longer_lifetime_raises_the_design_dose(self):
        self.assertAlmostEqual(design_dose_krad(50.0, 5.0, 15.0), 150.0, places=9)

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            design_dose_krad(50.0, 0.0, 5.0)


class TestEvidenceAndMargin(unittest.TestCase):
    def test_flight_lot_test_carries_the_narrowest_margin(self):
        self.assertAlmostEqual(
            required_design_margin("flight-lot-test", "phase-d"), 2.0, places=9
        )

    def test_generic_family_data_carries_the_widest_margin(self):
        self.assertAlmostEqual(
            required_design_margin("generic-family-data", "proposal"), 10.0, places=9
        )

    def test_no_test_evidence_has_no_usable_margin(self):
        self.assertIsNone(required_design_margin("no-test-evidence", "phase-b"))

    def test_unknown_evidence_raises(self):
        with self.assertRaises(ValueError):
            required_design_margin("vendor-brochure", "phase-b")

    def test_generic_data_is_accepted_before_design_freeze(self):
        self.assertEqual(evidence_findings("generic-family-data", "phase-b"), [])

    def test_generic_data_after_design_freeze_is_a_finding(self):
        self.assertIn(
            FINDING_GENERIC_DATA_LATE,
            evidence_findings("generic-family-data", "phase-d"),
        )

    def test_no_test_evidence_is_always_a_finding(self):
        self.assertIn(FINDING_NO_TEST, evidence_findings("no-test-evidence", "proposal"))

    def test_margin_exactly_at_requirement_is_met(self):
        self.assertTrue(margin_meets_requirement(2.0, 2.0))

    def test_margin_just_below_requirement_is_not_met(self):
        self.assertFalse(margin_meets_requirement(1.9, 2.0))

    def test_achieved_margin_is_capability_over_dose(self):
        self.assertAlmostEqual(achieved_design_margin(200.0, 50.0), 4.0, places=9)

    def test_zero_design_dose_raises(self):
        with self.assertRaises(ValueError):
            achieved_design_margin(200.0, 0.0)


class TestSensitivityGrouping(unittest.TestCase):
    def test_high_capability_is_dose_hard(self):
        self.assertEqual(dose_sensitivity_group(500.0), "dose-hard")

    def test_band_floor_belongs_to_its_own_band(self):
        self.assertEqual(dose_sensitivity_group(100.0), "dose-tolerant")

    def test_low_capability_is_dose_critical(self):
        self.assertEqual(dose_sensitivity_group(3.0), "dose-critical")

    def test_every_band_name_is_distinct(self):
        names = [name for _, name in DOSE_SENSITIVITY_BANDS]
        self.assertEqual(len(names), len(set(names)))


class TestPartValidation(unittest.TestCase):
    def test_non_mapping_part_raises(self):
        with self.assertRaises(ValueError):
            validate_part(["U1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part(""))

    def test_missing_family_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part("U1", family=""))

    def test_negative_capability_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part("U1", capability_krad=-1.0))

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            validate_mission(mission(phase="phase-z"))


class TestAssessPart(unittest.TestCase):
    def test_comfortable_part_is_compliant(self):
        result = assess_part(part(), CURVE, mission())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["design_dose_krad"], 50.0, places=9)
        self.assertAlmostEqual(result["achieved_margin"], 4.0, places=9)

    def test_part_exactly_at_required_margin_is_compliant(self):
        result = assess_part(part("U2", capability_krad=100.0), CURVE, mission())
        self.assertAlmostEqual(result["achieved_margin"], 2.0, places=9)
        self.assertTrue(result["compliant"])

    def test_margin_shortfall_is_reported(self):
        result = assess_part(part("U3", capability_krad=80.0), CURVE, mission())
        self.assertIn(FINDING_MARGIN_SHORTFALL, result["findings"])
        self.assertFalse(result["compliant"])

    def test_capability_below_design_dose_is_reported(self):
        result = assess_part(part("U4", capability_krad=20.0), CURVE, mission())
        self.assertIn(FINDING_CAPABILITY_BELOW_DOSE, result["findings"])
        self.assertIn(FINDING_MARGIN_SHORTFALL, result["findings"])

    def test_lifetime_extension_can_break_a_passing_part(self):
        ok = assess_part(part(), CURVE, mission())
        stretched = assess_part(part(), CURVE, mission(required_lifetime_years=15.0))
        self.assertTrue(ok["compliant"])
        self.assertFalse(stretched["compliant"])

    def test_untested_capability_is_never_compliant(self):
        result = assess_part(
            part("U5", evidence="no-test-evidence", capability_krad=1000.0),
            CURVE,
            mission(),
        )
        self.assertIn(FINDING_NO_TEST, result["findings"])
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["required_margin"])


class TestEquipmentAssessment(unittest.TestCase):
    def test_tightest_part_drives_the_verdict(self):
        report = assess_total_ionising_dose(
            [part("U1"), part("U2", capability_krad=60.0)], CURVE, mission()
        )
        self.assertEqual(report["tightest_part_id"], "U2")
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["U2"])

    def test_groups_collect_part_ids(self):
        report = assess_total_ionising_dose(
            [part("U1"), part("U2", capability_krad=500.0)], CURVE, mission()
        )
        self.assertEqual(report["sensitivity_groups"]["dose-hard"], ["U2"])
        self.assertEqual(report["sensitivity_groups"]["dose-tolerant"], ["U1"])

    def test_duplicate_part_id_raises(self):
        with self.assertRaises(ValueError):
            assess_total_ionising_dose([part("U1"), part("U1")], CURVE, mission())

    def test_empty_parts_list_raises(self):
        with self.assertRaises(ValueError):
            assess_total_ionising_dose([], CURVE, mission())

    def test_non_list_parts_raises(self):
        with self.assertRaises(ValueError):
            assess_total_ionising_dose(part(), CURVE, mission())

    def test_evidence_table_covers_every_documented_grade(self):
        self.assertIn("similar-part-data", EVIDENCE_REQUIRED_MARGIN)
        self.assertIn("same-part-other-lot", EVIDENCE_REQUIRED_MARGIN)


if __name__ == "__main__":
    unittest.main()
