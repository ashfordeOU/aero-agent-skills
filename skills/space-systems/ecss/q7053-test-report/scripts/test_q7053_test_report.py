"""Contract tests for the ECSS-Q-ST-70-53C compatibility test report."""

import copy
import unittest

from q7053_test_report_logic import (
    BOUND_TOLERANCE,
    COMPATIBLE,
    COMPATIBLE_WITH_LIMITATIONS,
    NOT_COMPATIBLE,
    REQUIRED_IDENTIFICATION_FIELDS,
    compile_test_report,
    completeness_score,
    conclusion_conflicts,
    cycle_sequence_findings,
    degradation_findings,
    grade_cycle_parameters,
    identification_findings,
    validate_cycle_record,
)

WINDOWS = {
    "temperature_c": {"min": 121.0, "max": 129.0},
    "dwell_min": {"min": 30.0},
}

IDENTIFICATION = {
    "material_designation": "polyimide-film-grade-A",
    "batch_or_lot": "LOT-2026-0417",
    "processing_state": "as-received, vacuum-baked 24 h",
    "sterilization_process": "vapour-phase hydrogen peroxide",
    "test_facility": "materials laboratory, bay 3",
}


def _cycle(index, temperature=125.0, dwell=35.0, deviation=None):
    return {
        "index": index,
        "achieved": {"temperature_c": temperature, "dwell_min": dwell},
        "deviation_reference": deviation,
    }


class IdentificationTests(unittest.TestCase):
    def test_complete_block_has_no_missing_fields(self):
        self.assertEqual(identification_findings(IDENTIFICATION), [])

    def test_absent_field_is_reported(self):
        block = dict(IDENTIFICATION)
        del block["batch_or_lot"]
        self.assertEqual(identification_findings(block), ["batch_or_lot"])

    def test_blank_field_counts_as_missing(self):
        block = dict(IDENTIFICATION, processing_state="   ")
        self.assertEqual(identification_findings(block), ["processing_state"])

    def test_every_required_field_is_checked(self):
        self.assertEqual(
            sorted(identification_findings({})), sorted(REQUIRED_IDENTIFICATION_FIELDS)
        )

    def test_non_mapping_identification_rejected(self):
        with self.assertRaises(ValueError):
            identification_findings(["material"])


class CycleRecordTests(unittest.TestCase):
    def test_valid_record_normalises(self):
        record = validate_cycle_record(_cycle(1))
        self.assertEqual(record["index"], 1)
        self.assertIsNone(record["deviation_reference"])

    def test_zero_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycle_record(_cycle(0))

    def test_non_integer_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycle_record(_cycle(1.5))

    def test_empty_achieved_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycle_record({"index": 1, "achieved": {}})

    def test_non_numeric_achieved_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycle_record({"index": 1, "achieved": {"temperature_c": "hot"}})

    def test_blank_deviation_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycle_record(_cycle(1, deviation="  "))


class SequenceTests(unittest.TestCase):
    def test_complete_run_has_no_findings(self):
        cycles = [_cycle(1), _cycle(2), _cycle(3)]
        self.assertEqual(cycle_sequence_findings(cycles, 3), [])

    def test_short_log_is_reported(self):
        findings = cycle_sequence_findings([_cycle(1), _cycle(2)], 3)
        self.assertEqual(len(findings), 1)

    def test_repeated_index_is_reported_with_the_gap_it_hides(self):
        findings = cycle_sequence_findings([_cycle(1), _cycle(2), _cycle(2)], 3)
        self.assertEqual(len(findings), 2)

    def test_gap_in_the_numbering_is_reported(self):
        findings = cycle_sequence_findings([_cycle(1), _cycle(2), _cycle(4)], 3)
        self.assertTrue(any("missing" in f for f in findings))

    def test_empty_cycle_log_rejected(self):
        with self.assertRaises(ValueError):
            cycle_sequence_findings([], 3)

    def test_zero_planned_cycles_rejected(self):
        with self.assertRaises(ValueError):
            cycle_sequence_findings([_cycle(1)], 0)


class CycleParameterTests(unittest.TestCase):
    def test_in_window_cycle_has_no_findings(self):
        graded = grade_cycle_parameters(_cycle(1), WINDOWS)
        self.assertEqual(graded["findings"], [])
        self.assertEqual(graded["breaches"], 0)

    def test_value_exactly_on_the_bound_is_inside(self):
        graded = grade_cycle_parameters(_cycle(1, temperature=129.0), WINDOWS)
        self.assertTrue(graded["parameters"]["temperature_c"]["within_window"])

    def test_value_exactly_on_a_floor_is_inside(self):
        graded = grade_cycle_parameters(_cycle(1, dwell=30.0), WINDOWS)
        self.assertTrue(graded["parameters"]["dwell_min"]["within_window"])

    def test_unpaired_breach_is_reported(self):
        graded = grade_cycle_parameters(_cycle(1, temperature=140.0), WINDOWS)
        self.assertEqual(graded["breaches"], 1)
        self.assertTrue(any("no deviation" in f for f in graded["findings"]))

    def test_breach_paired_with_a_deviation_is_not_a_finding(self):
        graded = grade_cycle_parameters(
            _cycle(1, temperature=140.0, deviation="NCR-2026-0007"), WINDOWS
        )
        self.assertEqual(graded["breaches"], 1)
        self.assertEqual(graded["findings"], [])

    def test_deviation_against_a_clean_cycle_is_a_finding(self):
        graded = grade_cycle_parameters(_cycle(1, deviation="NCR-2026-0007"), WINDOWS)
        self.assertTrue(any("nothing in it left its window" in f for f in graded["findings"]))

    def test_unrecorded_declared_parameter_is_a_finding(self):
        cycle = {"index": 1, "achieved": {"temperature_c": 125.0}}
        graded = grade_cycle_parameters(cycle, WINDOWS)
        self.assertFalse(graded["parameters"]["dwell_min"]["recorded"])
        self.assertTrue(any("never recorded" in f for f in graded["findings"]))

    def test_undeclared_recorded_parameter_is_a_finding(self):
        cycle = _cycle(1)
        cycle["achieved"]["chamber_pressure_mbar"] = 5.0
        graded = grade_cycle_parameters(cycle, WINDOWS)
        self.assertTrue(any("no window declares" in f for f in graded["findings"]))

    def test_window_with_no_bound_rejected(self):
        with self.assertRaises(ValueError):
            grade_cycle_parameters(_cycle(1), {"temperature_c": {}})

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            grade_cycle_parameters(_cycle(1), {"temperature_c": {"min": 9.0, "max": 1.0}})

    def test_empty_window_set_rejected(self):
        with self.assertRaises(ValueError):
            grade_cycle_parameters(_cycle(1), {})


class DegradationTableTests(unittest.TestCase):
    def test_complete_table_is_fully_evidenced(self):
        result = degradation_findings(
            [{"name": "tensile-strength", "pre": 50.0, "post": 48.0, "acceptable": True}]
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["evidenced"], ["tensile-strength"])

    def test_missing_post_value_is_unevidenced(self):
        result = degradation_findings([{"name": "tensile-strength", "pre": 50.0}])
        self.assertEqual(result["evidenced"], [])
        self.assertTrue(any("unevidenced" in f for f in result["findings"]))

    def test_missing_both_values_names_both(self):
        result = degradation_findings([{"name": "mass"}])
        self.assertIn("no pre", result["findings"][0])
        self.assertIn("no post", result["findings"][0])

    def test_failed_property_is_listed(self):
        result = degradation_findings(
            [{"name": "elongation", "pre": 100.0, "post": 40.0, "acceptable": False}]
        )
        self.assertEqual(result["failed"], ["elongation"])

    def test_duplicate_property_name_rejected(self):
        with self.assertRaises(ValueError):
            degradation_findings(
                [{"name": "mass", "pre": 1.0, "post": 1.0},
                 {"name": "mass", "pre": 1.0, "post": 1.0}]
            )

    def test_unnamed_property_rejected(self):
        with self.assertRaises(ValueError):
            degradation_findings([{"pre": 1.0, "post": 1.0}])

    def test_empty_property_list_rejected(self):
        with self.assertRaises(ValueError):
            degradation_findings([])


class ScoreAndConclusionTests(unittest.TestCase):
    def test_full_score_is_one(self):
        self.assertAlmostEqual(completeness_score(10, 10), 1.0, places=9)

    def test_partial_score_is_the_share(self):
        self.assertAlmostEqual(completeness_score(3, 4), 0.75)

    def test_score_above_the_requirement_rejected(self):
        with self.assertRaises(ValueError):
            completeness_score(11, 10)

    def test_zero_required_elements_rejected(self):
        with self.assertRaises(ValueError):
            completeness_score(0, 0)

    def test_compatible_over_a_failed_property_conflicts(self):
        conflicts = conclusion_conflicts(COMPATIBLE, ["elongation"], [])
        self.assertEqual(len(conflicts), 1)

    def test_compatible_over_record_findings_conflicts(self):
        conflicts = conclusion_conflicts(COMPATIBLE, [], ["cycle 2 index missing"])
        self.assertEqual(len(conflicts), 1)

    def test_not_compatible_with_nothing_failed_conflicts(self):
        self.assertEqual(len(conclusion_conflicts(NOT_COMPATIBLE, [], [])), 1)

    def test_compatible_with_limitations_tolerates_a_failure(self):
        self.assertEqual(conclusion_conflicts(COMPATIBLE_WITH_LIMITATIONS, ["mass"], []), [])

    def test_unknown_conclusion_rejected(self):
        with self.assertRaises(ValueError):
            conclusion_conflicts("probably-fine", [], [])


class CompileReportTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "report_id": "CR-70-53-2026-011",
            "identification": dict(IDENTIFICATION),
            "planned_cycles": 3,
            "parameter_windows": copy.deepcopy(WINDOWS),
            "cycles": [_cycle(1), _cycle(2), _cycle(3)],
            "properties": [
                {"name": "tensile-strength", "pre": 50.0, "post": 48.0, "acceptable": True},
                {"name": "mass", "pre": 100.0, "post": 100.2, "acceptable": True},
            ],
            "conclusion": COMPATIBLE,
        }
        spec.update(overrides)
        return spec

    def test_clean_report_is_complete(self):
        result = compile_test_report(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_score"], 1.0, places=9)
        self.assertTrue(result["report_complete"])

    def test_report_id_is_carried_through(self):
        self.assertEqual(
            compile_test_report(self._spec())["report_id"], "CR-70-53-2026-011"
        )

    def test_missing_identification_lowers_the_score(self):
        spec = self._spec()
        del spec["identification"]["test_facility"]
        result = compile_test_report(spec)
        self.assertEqual(result["missing_identification_fields"], ["test_facility"])
        self.assertLess(result["completeness_score"], 1.0)

    def test_short_cycle_log_is_reported_and_scored(self):
        spec = self._spec(cycles=[_cycle(1), _cycle(2)])
        result = compile_test_report(spec)
        self.assertFalse(result["report_complete"])
        self.assertLess(result["completeness_score"], 1.0)

    def test_unevidenced_property_is_reported(self):
        spec = self._spec()
        del spec["properties"][1]["post"]
        result = compile_test_report(spec)
        self.assertEqual(result["evidenced_properties"], ["tensile-strength"])

    def test_conclusion_conflict_is_reported(self):
        spec = self._spec()
        spec["properties"][0]["acceptable"] = False
        result = compile_test_report(spec)
        self.assertEqual(result["failed_properties"], ["tensile-strength"])
        self.assertTrue(result["conclusion_conflicts"])

    def test_limitations_conclusion_clears_the_property_conflict(self):
        spec = self._spec(conclusion=COMPATIBLE_WITH_LIMITATIONS)
        spec["properties"][0]["acceptable"] = False
        result = compile_test_report(spec)
        self.assertEqual(result["conclusion_conflicts"], [])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["conclusion"]
        with self.assertRaises(ValueError):
            compile_test_report(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            compile_test_report(["identification"])

    def test_bound_tolerance_is_small_and_positive(self):
        self.assertGreater(BOUND_TOLERANCE, 0.0)
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
