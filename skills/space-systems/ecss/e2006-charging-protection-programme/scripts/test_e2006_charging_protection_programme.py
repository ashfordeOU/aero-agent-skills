"""Gate 3 contract test for e2006-charging-protection-programme.

Offline, deterministic, stdlib unittest. Exercises the hazard index,
the risk bands and their exact edges, the mitigation and verification
coverage checks, the milestone schedule check, the aggregate programme
report and every ValueError path.
"""

import unittest

import e2006_charging_protection_programme_logic as logic


def geo_dielectric_item():
    return {
        "name": "antenna-reflector-skin",
        "environment": "geostationary",
        "exposure": "exposed-dielectric",
        "exposed_area_m2": 2.5,
    }


def leo_harness_item():
    return {
        "name": "internal-power-harness",
        "environment": "equatorial-low-earth-orbit",
        "exposure": "shielded-internal-harness",
        "exposed_area_m2": 0.01,
    }


def severe_plan_entry():
    return {
        "measures": ["conductive-surface-treatment", "grounding-and-bonding",
                     "shielding-or-filtering"],
        "methods": ["analysis", "inspection", "test", "measurement"],
        "schedule": {
            "hazard-assessment": "SRR",
            "mitigation-plan": "PDR",
            "verification-closure": "QR",
        },
    }


def negligible_plan_entry():
    return {
        "measures": [],
        "methods": ["analysis"],
        "schedule": {
            "hazard-assessment": "PDR",
            "mitigation-plan": "CDR",
            "verification-closure": "AR",
        },
    }


class HazardIndexTests(unittest.TestCase):

    def test_worst_case_geostationary_dielectric_saturates(self):
        self.assertAlmostEqual(
            logic.hazard_index("geostationary", "exposed-dielectric", 1.0),
            1.0)

    def test_area_factor_saturates_above_one_square_metre(self):
        small = logic.hazard_index("geostationary", "exposed-dielectric", 1.0)
        large = logic.hazard_index("geostationary", "exposed-dielectric", 9.0)
        self.assertAlmostEqual(small, large)

    def test_small_area_reduces_the_index(self):
        value = logic.hazard_index("geostationary", "exposed-dielectric", 0.01)
        self.assertAlmostEqual(value, 0.46, places=9)

    def test_shielded_harness_in_benign_orbit_is_tiny(self):
        value = logic.hazard_index("equatorial-low-earth-orbit",
                                   "shielded-internal-harness", 0.01)
        self.assertAlmostEqual(value, 0.0184, places=9)

    def test_index_never_exceeds_unity(self):
        for environment in logic.ENVIRONMENT_SEVERITY:
            for exposure in logic.EXPOSURE_FACTOR:
                value = logic.hazard_index(environment, exposure, 100.0)
                self.assertLessEqual(value, 1.0)
                self.assertGreater(value, 0.0)

    def test_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            logic.hazard_index("lunar-surface", "exposed-dielectric", 1.0)

    def test_unknown_exposure_raises(self):
        with self.assertRaises(ValueError):
            logic.hazard_index("geostationary", "painted-panel", 1.0)

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            logic.hazard_index("geostationary", "exposed-dielectric", 0.0)

    def test_negative_area_raises(self):
        with self.assertRaises(ValueError):
            logic.hazard_index("geostationary", "exposed-dielectric", -1.0)

    def test_non_numeric_area_raises(self):
        with self.assertRaises(ValueError):
            logic.hazard_index("geostationary", "exposed-dielectric", "2 m2")

    def test_non_string_environment_raises(self):
        with self.assertRaises(ValueError):
            logic.hazard_index(None, "exposed-dielectric", 1.0)


class RiskBandTests(unittest.TestCase):

    def test_top_of_the_range_is_severe(self):
        self.assertEqual(logic.categorize_risk(1.0), "severe")

    def test_severe_edge_is_inclusive(self):
        self.assertEqual(logic.categorize_risk(0.75), "severe")

    def test_edge_one_ulp_low_is_absorbed_into_severe(self):
        self.assertEqual(logic.categorize_risk(0.75 - 1e-16), "severe")

    def test_genuinely_below_the_edge_is_significant(self):
        self.assertEqual(logic.categorize_risk(0.74), "significant")

    def test_significant_edge_is_inclusive(self):
        self.assertEqual(logic.categorize_risk(0.5), "significant")

    def test_low_edge_is_inclusive(self):
        self.assertEqual(logic.categorize_risk(0.25), "low")

    def test_below_the_low_edge_is_negligible(self):
        self.assertEqual(logic.categorize_risk(0.24), "negligible")

    def test_zero_index_is_negligible(self):
        self.assertEqual(logic.categorize_risk(0.0), "negligible")

    def test_index_above_unity_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk(1.2)

    def test_negative_index_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk(-0.1)

    def test_non_numeric_index_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk("severe")


class ItemAssessmentTests(unittest.TestCase):

    def test_geostationary_dielectric_is_severe(self):
        result = logic.assess_item_hazard(geo_dielectric_item())
        self.assertEqual(result["risk"], "severe")
        self.assertAlmostEqual(result["hazard_index"], 1.0)

    def test_shielded_harness_is_negligible(self):
        result = logic.assess_item_hazard(leo_harness_item())
        self.assertEqual(result["risk"], "negligible")

    def test_item_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_item_hazard(["antenna-reflector-skin"])

    def test_item_missing_a_key_raises(self):
        item = geo_dielectric_item()
        del item["exposure"]
        with self.assertRaises(ValueError):
            logic.assess_item_hazard(item)


class MitigationCoverageTests(unittest.TestCase):

    def test_severe_band_demands_three_measures(self):
        self.assertEqual(len(logic.required_mitigation_measures("severe")), 3)

    def test_negligible_band_demands_none(self):
        self.assertEqual(logic.required_mitigation_measures("negligible"), ())

    def test_full_set_is_covered(self):
        result = logic.check_mitigation_coverage(
            "severe", severe_plan_entry()["measures"])
        self.assertTrue(result["covered"])
        self.assertEqual(result["missing"], [])

    def test_partial_set_reports_the_gap(self):
        result = logic.check_mitigation_coverage(
            "severe", ["grounding-and-bonding"])
        self.assertFalse(result["covered"])
        self.assertEqual(result["missing"],
                         ["conductive-surface-treatment",
                          "shielding-or-filtering"])

    def test_extra_measure_does_not_break_coverage(self):
        result = logic.check_mitigation_coverage(
            "low", ["grounding-and-bonding", "operational-constraint"])
        self.assertTrue(result["covered"])

    def test_unknown_measure_raises(self):
        with self.assertRaises(ValueError):
            logic.check_mitigation_coverage("low", ["paint-it-black"])

    def test_measures_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.check_mitigation_coverage("low", "grounding-and-bonding")

    def test_unknown_risk_band_raises(self):
        with self.assertRaises(ValueError):
            logic.required_mitigation_measures("catastrophic")


class VerificationCoverageTests(unittest.TestCase):

    def test_severe_band_demands_every_method(self):
        self.assertEqual(set(logic.required_verification_methods("severe")),
                         logic.VERIFICATION_METHODS)

    def test_negligible_band_demands_only_the_desk_method(self):
        self.assertEqual(logic.required_verification_methods("negligible"),
                         ("analysis",))

    def test_measurement_gap_is_reported_for_a_severe_item(self):
        result = logic.check_verification_coverage(
            "severe", ["analysis", "inspection", "test"])
        self.assertFalse(result["covered"])
        self.assertEqual(result["missing"], ["measurement"])

    def test_significant_band_does_not_demand_measurement(self):
        result = logic.check_verification_coverage(
            "significant", ["analysis", "inspection", "test"])
        self.assertTrue(result["covered"])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            logic.check_verification_coverage("low", ["vibe-check"])

    def test_methods_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.check_verification_coverage("low", 4)


class ScheduleTests(unittest.TestCase):

    def test_severe_hazard_assessment_is_due_at_the_first_review(self):
        self.assertEqual(
            logic.required_milestone("hazard-assessment", "severe"), "SRR")

    def test_low_hazard_assessment_is_due_by_the_preliminary_review(self):
        self.assertEqual(
            logic.required_milestone("hazard-assessment", "low"), "PDR")

    def test_planned_review_on_the_edge_is_on_time(self):
        result = logic.check_schedule("mitigation-plan", "severe", "PDR")
        self.assertTrue(result["on_time"])

    def test_earlier_planned_review_is_on_time(self):
        result = logic.check_schedule("mitigation-plan", "severe", "SRR")
        self.assertTrue(result["on_time"])

    def test_later_planned_review_is_late(self):
        result = logic.check_schedule("hazard-assessment", "severe", "CDR")
        self.assertFalse(result["on_time"])
        self.assertEqual(result["latest_acceptable"], "SRR")

    def test_unknown_activity_raises(self):
        with self.assertRaises(ValueError):
            logic.required_milestone("thermal-balance", "severe")

    def test_unknown_review_raises(self):
        with self.assertRaises(ValueError):
            logic.check_schedule("mitigation-plan", "severe", "TRR")

    def test_non_string_review_raises(self):
        with self.assertRaises(ValueError):
            logic.check_schedule("mitigation-plan", "severe", 2)


class ProgrammeReportTests(unittest.TestCase):

    def test_complete_programme_is_compliant(self):
        plan = {
            "antenna-reflector-skin": severe_plan_entry(),
            "internal-power-harness": negligible_plan_entry(),
        }
        report = logic.build_protection_programme(
            [geo_dielectric_item(), leo_harness_item()], plan)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["items"]), 2)

    def test_item_absent_from_the_plan_is_a_finding(self):
        report = logic.build_protection_programme(
            [geo_dielectric_item()], {})
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["findings"]), 1)
        self.assertIsNone(report["items"][0]["mitigation"])

    def test_late_milestone_is_a_finding(self):
        entry = severe_plan_entry()
        entry["schedule"]["hazard-assessment"] = "CDR"
        report = logic.build_protection_programme(
            [geo_dielectric_item()], {"antenna-reflector-skin": entry})
        self.assertFalse(report["compliant"])
        self.assertTrue(any("hazard-assessment" in f
                            for f in report["findings"]))

    def test_missing_measure_and_method_are_reported_separately(self):
        entry = severe_plan_entry()
        entry["measures"] = ["grounding-and-bonding"]
        entry["methods"] = ["analysis"]
        report = logic.build_protection_programme(
            [geo_dielectric_item()], {"antenna-reflector-skin": entry})
        self.assertEqual(len(report["findings"]), 2)

    def test_missing_scheduled_activity_is_a_finding(self):
        entry = severe_plan_entry()
        del entry["schedule"]["verification-closure"]
        report = logic.build_protection_programme(
            [geo_dielectric_item()], {"antenna-reflector-skin": entry})
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["findings"]), 1)

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            logic.build_protection_programme([], {})

    def test_plan_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.build_protection_programme([geo_dielectric_item()], [])

    def test_duplicate_item_name_raises(self):
        with self.assertRaises(ValueError):
            logic.build_protection_programme(
                [geo_dielectric_item(), geo_dielectric_item()],
                {"antenna-reflector-skin": severe_plan_entry()})

    def test_plan_entry_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.build_protection_programme(
                [geo_dielectric_item()],
                {"antenna-reflector-skin": ["grounding-and-bonding"]})

    def test_schedule_must_be_a_mapping(self):
        entry = severe_plan_entry()
        entry["schedule"] = ["SRR"]
        with self.assertRaises(ValueError):
            logic.build_protection_programme(
                [geo_dielectric_item()], {"antenna-reflector-skin": entry})

    def test_report_is_deterministic(self):
        plan = {"antenna-reflector-skin": severe_plan_entry()}
        first = logic.build_protection_programme(
            [geo_dielectric_item()], plan)
        second = logic.build_protection_programme(
            [geo_dielectric_item()], plan)
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(first["items"][0]["hazard_index"],
                         second["items"][0]["hazard_index"])


if __name__ == "__main__":
    unittest.main()
