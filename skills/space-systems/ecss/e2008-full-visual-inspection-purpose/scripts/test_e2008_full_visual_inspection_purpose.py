"""Contract tests for the clause 5.5.3.2.1 full visual examination logic."""

import unittest

from e2008_full_visual_inspection_purpose_logic import (
    BASE_ACUITY_MM,
    DEFAULT_MIN_ILLUMINANCE_LUX,
    SEVERITY_GRADES,
    assess_full_visual_inspection,
    coverage_fraction,
    disposition_from_grades,
    group_imperfections,
    resolvable_feature_mm,
    validate_zone,
    zone_optical_findings,
)


def _zone(zone_id, area=100.0, magnification=10.0, lux=1500.0, inspected=True,
          accessible=True, access_means=None):
    zone = {
        "id": zone_id,
        "area_cm2": area,
        "magnification": magnification,
        "illuminance_lux": lux,
        "inspected": inspected,
        "directly_accessible": accessible,
    }
    if access_means is not None:
        zone["access_means"] = access_means
    return zone


def _spec(**overrides):
    spec = {
        "zones": [_zone("front-laydown"), _zone("interconnect-run"), _zone("rear-harness")],
        "smallest_feature_mm": 0.05,
        "imperfections": [],
    }
    spec.update(overrides)
    return spec


class ResolvableFeatureTests(unittest.TestCase):
    def test_unaided_view_resolves_the_base_acuity(self):
        self.assertAlmostEqual(resolvable_feature_mm(1.0), BASE_ACUITY_MM, places=9)

    def test_ten_times_magnification_resolves_a_tenth(self):
        self.assertAlmostEqual(resolvable_feature_mm(10.0), 0.01, places=9)

    def test_doubling_magnification_halves_the_feature(self):
        coarse = resolvable_feature_mm(5.0)
        fine = resolvable_feature_mm(10.0)
        self.assertAlmostEqual(fine, coarse / 2.0, places=9)

    def test_magnification_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_mm(0.5)

    def test_zero_magnification_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_mm(0.0)

    def test_boolean_magnification_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_mm(True)


class ZoneValidationTests(unittest.TestCase):
    def test_zone_defaults_to_inspected_and_accessible(self):
        record = validate_zone(
            {"id": "z1", "area_cm2": 10.0, "magnification": 4.0, "illuminance_lux": 1200.0}
        )
        self.assertTrue(record["inspected"])
        self.assertTrue(record["directly_accessible"])

    def test_zone_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_zone({"id": "z1", "area_cm2": 10.0, "magnification": 4.0})

    def test_blank_zone_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_zone(_zone("   "))

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_zone(_zone("z1", area=0.0))

    def test_non_boolean_inspected_flag_rejected(self):
        zone = _zone("z1")
        zone["inspected"] = "yes"
        with self.assertRaises(ValueError):
            validate_zone(zone)


class CoverageTests(unittest.TestCase):
    def test_all_zones_examined_gives_whole_coverage(self):
        self.assertAlmostEqual(
            coverage_fraction([_zone("a"), _zone("b"), _zone("c")]), 1.0, places=9
        )

    def test_one_zone_skipped_lowers_coverage(self):
        zones = [_zone("a", area=75.0), _zone("b", area=25.0, inspected=False)]
        self.assertAlmostEqual(coverage_fraction(zones), 0.75, places=9)

    def test_coverage_weights_by_area_not_zone_count(self):
        zones = [_zone("a", area=900.0), _zone("b", area=100.0, inspected=False)]
        self.assertAlmostEqual(coverage_fraction(zones), 0.9, places=9)

    def test_duplicate_zone_id_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction([_zone("a"), _zone("a")])

    def test_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction([])


class ZoneOpticsTests(unittest.TestCase):
    def test_adequate_zone_gives_no_findings(self):
        self.assertEqual(zone_optical_findings(_zone("a"), 0.05), [])

    def test_uninspected_zone_is_the_only_finding_reported(self):
        findings = zone_optical_findings(_zone("a", inspected=False, lux=1.0), 0.05)
        self.assertEqual(len(findings), 1)
        self.assertIn("was not examined", findings[0])

    def test_magnification_exactly_resolving_the_target_is_adequate(self):
        target = resolvable_feature_mm(10.0)
        self.assertEqual(zone_optical_findings(_zone("a", magnification=10.0), target), [])

    def test_too_coarse_a_magnification_is_flagged(self):
        findings = zone_optical_findings(_zone("a", magnification=1.0), 0.01)
        self.assertEqual(len(findings), 1)
        self.assertIn("cannot show", findings[0])

    def test_illuminance_exactly_on_the_floor_is_adequate(self):
        self.assertEqual(
            zone_optical_findings(_zone("a", lux=DEFAULT_MIN_ILLUMINANCE_LUX), 0.05), []
        )

    def test_dim_zone_is_flagged(self):
        findings = zone_optical_findings(_zone("a", lux=200.0), 0.05)
        self.assertEqual(len(findings), 1)
        self.assertIn("below the", findings[0])

    def test_unreachable_zone_without_access_means_is_flagged(self):
        findings = zone_optical_findings(_zone("a", accessible=False), 0.05)
        self.assertEqual(len(findings), 1)
        self.assertIn("no access means", findings[0])

    def test_unreachable_zone_with_declared_access_means_is_adequate(self):
        zone = _zone("a", accessible=False, access_means="inspection mirror")
        self.assertEqual(zone_optical_findings(zone, 0.05), [])

    def test_target_feature_must_be_positive(self):
        with self.assertRaises(ValueError):
            zone_optical_findings(_zone("a"), 0.0)


class ImperfectionGroupingTests(unittest.TestCase):
    def test_absent_list_gives_zero_totals(self):
        self.assertEqual(group_imperfections(None, ["a"]), {g: 0 for g in SEVERITY_GRADES})

    def test_counts_group_by_grade(self):
        totals = group_imperfections(
            [
                {"zone": "a", "severity": "minor"},
                {"zone": "a", "severity": "minor"},
                {"zone": "b", "severity": "major"},
            ],
            ["a", "b"],
        )
        self.assertEqual(totals["minor"], 2)
        self.assertEqual(totals["major"], 1)
        self.assertEqual(totals["critical"], 0)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            group_imperfections([{"zone": "a", "severity": "cosmetic"}], ["a"])

    def test_imperfection_on_an_undeclared_zone_rejected(self):
        with self.assertRaises(ValueError):
            group_imperfections([{"zone": "z9", "severity": "minor"}], ["a"])

    def test_imperfection_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            group_imperfections([{"zone": "a"}], ["a"])


class DispositionTests(unittest.TestCase):
    def test_clean_article_is_accepted(self):
        self.assertEqual(disposition_from_grades({g: 0 for g in SEVERITY_GRADES}), "accept")

    def test_minor_only_is_accepted(self):
        self.assertEqual(disposition_from_grades({"minor": 4}), "accept")

    def test_major_calls_for_repair(self):
        self.assertEqual(disposition_from_grades({"major": 1, "minor": 4}), "repair")

    def test_critical_overrides_the_lower_grades(self):
        self.assertEqual(
            disposition_from_grades({"critical": 1, "major": 3, "minor": 9}), "reject"
        )

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            disposition_from_grades({"minor": -1})


class AssessmentTests(unittest.TestCase):
    def test_whole_article_examination_is_complete(self):
        result = assess_full_visual_inspection(_spec())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_coverage_is_reported_as_whole(self):
        result = assess_full_visual_inspection(_spec())
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertTrue(result["coverage_complete"])

    def test_skipped_zone_breaks_completeness(self):
        zones = [_zone("a"), _zone("b", inspected=False), _zone("c")]
        result = assess_full_visual_inspection(_spec(zones=zones))
        self.assertFalse(result["complete"])
        self.assertEqual(result["uninspected_zones"], ["b"])

    def test_skipped_zone_lowers_the_coverage_fraction(self):
        zones = [_zone("a", area=80.0), _zone("b", area=20.0, inspected=False)]
        result = assess_full_visual_inspection(_spec(zones=zones))
        self.assertAlmostEqual(result["coverage_fraction"], 0.8, places=9)

    def test_coarse_zone_breaks_completeness_at_full_coverage(self):
        zones = [_zone("a"), _zone("b", magnification=1.0), _zone("c")]
        result = assess_full_visual_inspection(_spec(zones=zones))
        self.assertTrue(result["coverage_complete"])
        self.assertFalse(result["complete"])

    def test_zone_records_carry_the_resolvable_feature(self):
        result = assess_full_visual_inspection(_spec())
        self.assertAlmostEqual(
            result["zone_records"][0]["resolvable_feature_mm"], 0.01, places=9
        )

    def test_areas_sum_across_zones(self):
        result = assess_full_visual_inspection(_spec())
        self.assertAlmostEqual(result["total_area_cm2"], 300.0, places=9)
        self.assertAlmostEqual(result["examined_area_cm2"], 300.0, places=9)

    def test_critical_imperfection_drives_the_disposition(self):
        result = assess_full_visual_inspection(
            _spec(imperfections=[{"zone": "interconnect-run", "severity": "critical"}])
        )
        self.assertEqual(result["disposition"], "reject")

    def test_finding_free_inspection_can_still_report_imperfections(self):
        result = assess_full_visual_inspection(
            _spec(imperfections=[{"zone": "rear-harness", "severity": "minor"}])
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["imperfection_totals"]["minor"], 1)

    def test_custom_illuminance_floor_is_applied(self):
        zones = [_zone("a", lux=1200.0), _zone("b"), _zone("c")]
        result = assess_full_visual_inspection(
            _spec(zones=zones, min_illuminance_lux=1400.0)
        )
        self.assertFalse(result["complete"])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["smallest_feature_mm"]
        with self.assertRaises(ValueError):
            assess_full_visual_inspection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_full_visual_inspection(["zones"])

    def test_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_full_visual_inspection(_spec(zones=[]))


if __name__ == "__main__":
    unittest.main()
