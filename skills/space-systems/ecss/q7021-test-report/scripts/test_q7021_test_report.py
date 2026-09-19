"""Contract tests for the ECSS-Q-ST-70-21C flammability test-report logic."""

import copy
import datetime
import unittest

from q7021_test_report_logic import (
    BLOCKING_FIELDS,
    SECTION_ORDER,
    assess_test_report,
    completeness_ratio,
    consistency_findings,
    missing_fields,
    parse_iso_date,
    report_skeleton,
)


def good_report():
    return {
        "identification": {
            "report_ref": "FR-2026-118",
            "material": "polyimide-tape-grade-b",
            "test_date": "2026-04-14",
            "laboratory": "materials-lab-2",
            "operator": "op-17",
        },
        "specimens": {
            "specimen_count": 3,
            "thickness_mm": 0.08,
            "orientation": "machine-direction",
            "batch_ref": "LOT-7741",
            "preparation_method": "die-cut",
        },
        "conditions": {
            "oxygen_concentration_pct": 30.0,
            "pressure_kpa": 101.3,
            "conditioning_end_date": "2026-04-13",
            "ignition_source": "premixed-burner",
            "gas_flow_lpm": 12.0,
            "ambient_temperature_c": 22.0,
            "conditioning_hours": 48,
        },
        "results": {
            "specimen_results": [
                {"specimen_id": "S1", "burn_length_mm": 62.0, "specimen_length_mm": 300.0},
                {"specimen_id": "S2", "burn_length_mm": 88.0, "specimen_length_mm": 300.0},
                {"specimen_id": "S3", "burn_length_mm": 71.0, "specimen_length_mm": 300.0},
            ],
            "worst_case_burn_length_mm": 88.0,
        },
        "observations": {
            "dripping": "none observed",
            "self_extinguishing": True,
            "smoke": "light grey",
            "afterglow": "none",
            "char_appearance": "brittle char to 90 mm",
        },
        "deviations": {"deviations_recorded": "none"},
    }


class ParseIsoDateTests(unittest.TestCase):
    def test_parses_a_string(self):
        self.assertEqual(parse_iso_date("2026-04-14"), datetime.date(2026, 4, 14))

    def test_rejects_a_free_text_date(self):
        with self.assertRaises(ValueError):
            parse_iso_date("14 April 2026")

    def test_rejects_an_empty_string(self):
        with self.assertRaises(ValueError):
            parse_iso_date("   ")


class SkeletonTests(unittest.TestCase):
    def test_skeleton_follows_the_reporting_order(self):
        self.assertEqual([name for name, _ in report_skeleton()], list(SECTION_ORDER))

    def test_every_section_declares_its_blocking_fields(self):
        for name, fields in report_skeleton():
            self.assertEqual(fields, list(BLOCKING_FIELDS[name]))

    def test_conditions_carry_the_ignition_source(self):
        self.assertIn("ignition_source", BLOCKING_FIELDS["conditions"])


class MissingFieldTests(unittest.TestCase):
    def test_a_full_report_is_missing_nothing(self):
        missing = missing_fields(good_report())
        self.assertEqual(missing["blocking"], [])
        self.assertEqual(missing["advisory"], [])

    def test_an_absent_blocking_field_is_named_with_its_section(self):
        report = good_report()
        del report["conditions"]["oxygen_concentration_pct"]
        self.assertEqual(missing_fields(report)["blocking"],
                         ["conditions.oxygen_concentration_pct"])

    def test_an_empty_string_counts_as_absent(self):
        report = good_report()
        report["identification"]["laboratory"] = "   "
        self.assertIn("identification.laboratory", missing_fields(report)["blocking"])

    def test_an_empty_result_list_counts_as_absent(self):
        report = good_report()
        report["results"]["specimen_results"] = []
        self.assertIn("results.specimen_results", missing_fields(report)["blocking"])

    def test_a_false_observation_still_counts_as_present(self):
        report = good_report()
        report["observations"]["self_extinguishing"] = False
        self.assertNotIn("observations.self_extinguishing",
                         missing_fields(report)["blocking"])

    def test_an_advisory_omission_is_kept_out_of_the_blocking_list(self):
        report = good_report()
        del report["conditions"]["gas_flow_lpm"]
        missing = missing_fields(report)
        self.assertEqual(missing["blocking"], [])
        self.assertEqual(missing["advisory"], ["conditions.gas_flow_lpm"])

    def test_a_whole_absent_section_lists_all_its_blocking_fields(self):
        report = good_report()
        del report["deviations"]
        self.assertIn("deviations.deviations_recorded", missing_fields(report)["blocking"])

    def test_a_section_outside_the_structure_is_rejected(self):
        report = good_report()
        report["invoice"] = {"amount": 1200}
        with self.assertRaises(ValueError):
            missing_fields(report)

    def test_a_non_mapping_section_is_rejected(self):
        report = good_report()
        report["observations"] = "all fine"
        with self.assertRaises(ValueError):
            missing_fields(report)

    def test_a_non_mapping_report_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_fields([("identification", {})])


class ConsistencyTests(unittest.TestCase):
    def test_a_coherent_report_raises_nothing(self):
        self.assertEqual(consistency_findings(good_report()), [])

    def test_a_burn_longer_than_the_specimen_is_caught(self):
        report = good_report()
        report["results"]["specimen_results"][1]["burn_length_mm"] = 420.0
        report["results"]["worst_case_burn_length_mm"] = 420.0
        findings = consistency_findings(report)
        self.assertTrue(any("300" in f for f in findings))

    def test_a_result_count_disagreeing_with_the_specimen_count_is_caught(self):
        report = good_report()
        report["specimens"]["specimen_count"] = 5
        self.assertTrue(any("5 specimen" in f for f in consistency_findings(report)))

    def test_a_quoted_worst_case_that_is_not_the_worst_is_caught(self):
        report = good_report()
        report["results"]["worst_case_burn_length_mm"] = 71.0
        self.assertTrue(any("worst case" in f for f in consistency_findings(report)))

    def test_a_worst_case_reached_by_a_different_sum_is_accepted(self):
        # 0.1 + 0.2 is not 0.3 in binary floating point; the worst-case
        # comparison absorbs that instead of raising a phantom contradiction.
        report = good_report()
        for index, value in enumerate((0.1 + 0.2, 0.05, 0.2)):
            report["results"]["specimen_results"][index]["burn_length_mm"] = value
        report["results"]["worst_case_burn_length_mm"] = 0.3
        self.assertEqual(consistency_findings(report), [])

    def test_a_test_dated_before_its_conditioning_is_caught(self):
        report = good_report()
        report["identification"]["test_date"] = "2026-04-10"
        self.assertTrue(any("before the conditioning" in f
                            for f in consistency_findings(report)))

    def test_a_test_on_the_conditioning_end_date_is_accepted(self):
        report = good_report()
        report["identification"]["test_date"] = "2026-04-13"
        self.assertEqual(consistency_findings(report), [])

    def test_an_impossible_oxygen_concentration_is_caught(self):
        report = good_report()
        report["conditions"]["oxygen_concentration_pct"] = 140.0
        self.assertTrue(any("oxygen concentration" in f
                            for f in consistency_findings(report)))

    def test_a_non_physical_pressure_is_caught(self):
        report = good_report()
        report["conditions"]["pressure_kpa"] = 0.0
        self.assertTrue(any("pressure" in f for f in consistency_findings(report)))

    def test_a_result_row_without_a_burn_length_is_caught(self):
        report = good_report()
        del report["results"]["specimen_results"][0]["burn_length_mm"]
        self.assertTrue(any("no burn length" in f for f in consistency_findings(report)))

    def test_a_result_row_that_is_not_a_mapping_is_caught(self):
        report = good_report()
        report["results"]["specimen_results"][0] = "S1: 62 mm"
        self.assertTrue(any("not a mapping" in f for f in consistency_findings(report)))

    def test_results_given_as_prose_are_caught(self):
        report = good_report()
        report["results"]["specimen_results"] = "all three passed"
        self.assertTrue(any("list of specimen rows" in f
                            for f in consistency_findings(report)))

    def test_a_free_text_test_date_raises(self):
        report = good_report()
        report["identification"]["test_date"] = "mid April"
        with self.assertRaises(ValueError):
            consistency_findings(report)


class CompletenessTests(unittest.TestCase):
    def test_a_full_report_is_complete(self):
        self.assertAlmostEqual(completeness_ratio(good_report()), 1.0, places=9)

    def test_one_missing_blocking_field_lowers_the_ratio(self):
        report = good_report()
        del report["identification"]["laboratory"]
        total = sum(len(f) for f in BLOCKING_FIELDS.values())
        self.assertAlmostEqual(completeness_ratio(report),
                               (total - 1) / float(total), places=9)

    def test_an_advisory_omission_does_not_move_the_ratio(self):
        report = good_report()
        del report["observations"]["smoke"]
        self.assertAlmostEqual(completeness_ratio(report), 1.0, places=9)


class AssessTestReportTests(unittest.TestCase):
    def test_a_complete_coherent_report_is_fileable(self):
        result = assess_test_report(good_report())
        self.assertTrue(result["fileable"])
        self.assertEqual(result["verdict"], "fileable")

    def test_an_advisory_omission_is_still_fileable(self):
        report = good_report()
        del report["conditions"]["ambient_temperature_c"]
        result = assess_test_report(report)
        self.assertTrue(result["fileable"])
        self.assertEqual(result["verdict"], "fileable-with-advisories")

    def test_a_blocking_omission_returns_the_report_for_completion(self):
        report = good_report()
        del report["conditions"]["ignition_source"]
        result = assess_test_report(report)
        self.assertFalse(result["fileable"])
        self.assertEqual(result["verdict"], "return-for-completion")

    def test_a_complete_but_contradictory_report_returns_for_correction(self):
        report = good_report()
        report["results"]["worst_case_burn_length_mm"] = 62.0
        result = assess_test_report(report)
        self.assertEqual(result["verdict"], "return-for-correction")
        self.assertFalse(result["fileable"])

    def test_a_blocking_omission_outranks_a_contradiction(self):
        report = good_report()
        del report["identification"]["report_ref"]
        report["results"]["worst_case_burn_length_mm"] = 62.0
        self.assertEqual(assess_test_report(report)["verdict"], "return-for-completion")

    def test_the_skeleton_travels_with_the_verdict(self):
        self.assertEqual([name for name, _ in assess_test_report(good_report())["skeleton"]],
                         list(SECTION_ORDER))

    def test_the_input_report_is_not_mutated(self):
        report = good_report()
        before = copy.deepcopy(report)
        assess_test_report(report)
        self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()
