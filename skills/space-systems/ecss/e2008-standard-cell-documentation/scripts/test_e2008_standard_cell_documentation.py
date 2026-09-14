#!/usr/bin/env python3
"""Contract test for the standard cell documentation leaf (offline)."""

import copy
import datetime
import math
import unittest

from e2008_standard_cell_documentation_logic import (
    COMPLETE_VERDICT,
    DATA_BLOCKS,
    DISTRIBUTION_DIVISORS,
    EVALUATION_TYPES,
    INCOMPLETE_VERDICT,
    REQUIRED_FIELDS,
    assess_standard_cell_documentation,
    block_completeness,
    budget_findings,
    combined_standard_uncertainty_percent,
    documentation_completeness_ratio,
    dominant_component,
    expanded_uncertainty_percent,
    field_is_reported,
    missing_fields,
    parse_calibration_day,
    standard_uncertainty_percent,
    validate_component,
    validate_components,
    validate_record,
    variance_contributions,
)

COMPONENTS = [
    {
        "name": "primary-reference-cell",
        "value_percent": 0.40,
        "distribution": "normal",
        "evaluation": "type-b",
    },
    {
        "name": "transfer-measurement",
        "value_percent": 0.30,
        "distribution": "rectangular",
        "evaluation": "type-b",
    },
    {
        "name": "temperature-correction",
        "value_percent": 0.12,
        "distribution": "rectangular",
        "evaluation": "type-b",
    },
    {
        "name": "measurement-repeatability",
        "value_percent": 0.20,
        "distribution": "normal",
        "evaluation": "type-a",
    },
    {
        "name": "area-determination",
        "value_percent": 0.15,
        "distribution": "triangular",
        "evaluation": "type-b",
    },
]

SOUND_RECORD = {
    "identification": {
        "serial_number": "SC-2211-07",
        "cell_type": "triple-junction space cell",
        "manufacturer": "reference cell house",
        "designated_area_cm2": 30.18,
        "construction": "bare cell, 100 micron coverglass",
    },
    "calibration": {
        "calibration_value_a": 0.5032,
        "reference_spectrum": "air-mass-zero",
        "irradiance_w_m2": 1366.1,
        "cell_temperature_c": 25.0,
        "calibration_date": "2026-02-11",
        "calibrating_laboratory": "national reference laboratory",
        "calibration_method": "high-altitude comparison",
    },
    "uncertainty-budget": {
        "components": COMPONENTS,
        "combined_standard_uncertainty_percent": 0.4884,
        "coverage_factor": 2.0,
        "expanded_uncertainty_percent": 0.9768,
    },
}

EXPECTED_VARIANCE = 0.40 ** 2 + 0.09 / 3.0 + 0.0144 / 3.0 + 0.20 ** 2 + 0.0225 / 6.0


def _record(block=None, **changes):
    record = copy.deepcopy(SOUND_RECORD)
    if block is not None:
        record[block].update(changes)
    return record


def _defect_names(result):
    return {entry["defect"] for entry in result["defects"]}


def _observation_names(result):
    return {entry["observation"] for entry in result["observations"]}


class FieldReportingTests(unittest.TestCase):
    def test_a_numeric_zero_is_a_reported_value(self):
        self.assertTrue(field_is_reported(0))
        self.assertTrue(field_is_reported(0.0))

    def test_an_absent_field_is_not_reported(self):
        self.assertFalse(field_is_reported(None))

    def test_a_blank_string_is_not_reported(self):
        self.assertFalse(field_is_reported("   "))

    def test_an_empty_container_is_not_reported(self):
        self.assertFalse(field_is_reported([]))
        self.assertFalse(field_is_reported({}))

    def test_a_stated_string_is_reported(self):
        self.assertTrue(field_is_reported("SC-2211-07"))


class RecordStructureTests(unittest.TestCase):
    def test_the_sound_record_reports_every_required_field(self):
        self.assertEqual(missing_fields(SOUND_RECORD), ())
        self.assertAlmostEqual(documentation_completeness_ratio(SOUND_RECORD), 1.0, places=12)

    def test_a_dropped_field_is_named_with_its_block(self):
        record = _record()
        del record["calibration"]["calibrating_laboratory"]
        self.assertIn("calibration.calibrating_laboratory", missing_fields(record))

    def test_a_blank_field_counts_as_unreported(self):
        record = _record("identification", construction="  ")
        self.assertIn("identification.construction", missing_fields(record))

    def test_a_zero_temperature_is_a_value_and_not_a_hole(self):
        record = _record("calibration", cell_temperature_c=0.0)
        self.assertNotIn("calibration.cell_temperature_c", missing_fields(record))

    def test_block_completeness_counts_each_block_on_its_own(self):
        record = _record()
        del record["identification"]["manufacturer"]
        report = block_completeness(record)
        self.assertEqual(report["identification"]["reported"], 4)
        self.assertEqual(report["identification"]["required"], 5)
        self.assertAlmostEqual(report["calibration"]["ratio"], 1.0, places=12)

    def test_every_declared_block_appears_in_the_completeness_report(self):
        report = block_completeness(SOUND_RECORD)
        for block in DATA_BLOCKS:
            self.assertIn(block, report)
            self.assertEqual(report[block]["required"], len(REQUIRED_FIELDS[block]))

    def test_an_unknown_block_is_rejected(self):
        record = _record()
        record["shipping"] = {"carrier": "courier"}
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_a_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_record("SC-2211-07")

    def test_a_non_mapping_block_is_rejected(self):
        record = _record()
        record["calibration"] = ["air-mass-zero"]
        with self.assertRaises(ValueError):
            validate_record(record)


class ComponentTests(unittest.TestCase):
    def test_a_normal_component_is_taken_as_stated(self):
        entry = validate_component({"name": "u1", "value_percent": 0.4, "distribution": "normal"})
        self.assertAlmostEqual(standard_uncertainty_percent(entry), 0.4, places=12)

    def test_a_rectangular_component_is_divided_by_the_root_of_three(self):
        entry = validate_component(
            {"name": "u2", "value_percent": 0.3, "distribution": "rectangular"}
        )
        self.assertAlmostEqual(
            standard_uncertainty_percent(entry), 0.3 / math.sqrt(3.0), places=12
        )

    def test_every_declared_distribution_has_a_divisor_of_at_least_one(self):
        for distribution, divisor in DISTRIBUTION_DIVISORS.items():
            self.assertGreaterEqual(divisor, 1.0, distribution)

    def test_a_triangular_component_is_divided_by_the_root_of_six(self):
        entry = validate_component(
            {"name": "u3", "value_percent": 0.15, "distribution": "triangular"}
        )
        self.assertAlmostEqual(
            standard_uncertainty_percent(entry), 0.15 / math.sqrt(6.0), places=12
        )

    def test_the_sensitivity_scales_the_component(self):
        entry = validate_component(
            {"name": "u4", "value_percent": 0.4, "distribution": "normal", "sensitivity": 2.5}
        )
        self.assertAlmostEqual(standard_uncertainty_percent(entry), 1.0, places=12)

    def test_a_negative_sensitivity_contributes_its_magnitude(self):
        entry = validate_component(
            {"name": "u5", "value_percent": 0.4, "distribution": "normal", "sensitivity": -2.5}
        )
        self.assertAlmostEqual(standard_uncertainty_percent(entry), 1.0, places=12)

    def test_the_evaluation_defaults_to_type_b(self):
        entry = validate_component({"name": "u6", "value_percent": 0.1})
        self.assertEqual(entry["evaluation"], "type-b")
        self.assertIn(entry["evaluation"], EVALUATION_TYPES)

    def test_an_unknown_distribution_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component({"name": "u7", "value_percent": 0.1, "distribution": "guess"})

    def test_an_unknown_evaluation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component({"name": "u8", "value_percent": 0.1, "evaluation": "type-c"})

    def test_a_negative_component_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component({"name": "u9", "value_percent": -0.1})

    def test_a_nameless_component_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component({"value_percent": 0.1})

    def test_a_repeated_component_name_is_rejected(self):
        doubled = copy.deepcopy(COMPONENTS)
        doubled.append(copy.deepcopy(COMPONENTS[0]))
        with self.assertRaises(ValueError):
            validate_components(doubled)

    def test_an_empty_component_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_components([])


class BudgetMathTests(unittest.TestCase):
    def test_the_combined_uncertainty_is_a_root_sum_of_squares(self):
        combined = combined_standard_uncertainty_percent(COMPONENTS)
        self.assertAlmostEqual(combined, math.sqrt(EXPECTED_VARIANCE), places=12)

    def test_the_expanded_uncertainty_is_the_coverage_factor_times_the_combined(self):
        combined = combined_standard_uncertainty_percent(COMPONENTS)
        self.assertAlmostEqual(
            expanded_uncertainty_percent(COMPONENTS, 2.0), 2.0 * combined, places=12
        )

    def test_a_non_positive_coverage_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty_percent(COMPONENTS, -2.0)

    def test_the_variance_shares_add_up_to_the_whole(self):
        shares = variance_contributions(COMPONENTS)
        self.assertAlmostEqual(sum(shares.values()), 1.0, places=9)

    def test_no_component_dominates_a_balanced_budget(self):
        self.assertIsNone(dominant_component(COMPONENTS, 0.7))

    def test_a_large_component_is_named_as_dominant(self):
        loaded = copy.deepcopy(COMPONENTS)
        loaded[0]["value_percent"] = 0.60
        self.assertEqual(dominant_component(loaded, 0.7), "primary-reference-cell")

    def test_a_component_sitting_exactly_on_the_threshold_is_named(self):
        halves = [
            {"name": "a", "value_percent": 0.3, "distribution": "normal"},
            {"name": "b", "value_percent": 0.3, "distribution": "normal"},
        ]
        self.assertIsNotNone(dominant_component(halves, 0.5))

    def test_a_threshold_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            dominant_component(COMPONENTS, 1.4)


class CalibrationDayTests(unittest.TestCase):
    def test_an_iso_day_is_read(self):
        self.assertEqual(parse_calibration_day("2026-02-11"), datetime.date(2026, 2, 11))

    def test_a_date_object_passes_through(self):
        day = datetime.date(2026, 2, 11)
        self.assertEqual(parse_calibration_day(day), day)

    def test_a_malformed_day_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_calibration_day("11.02.2026")


class BudgetFindingTests(unittest.TestCase):
    def test_a_self_consistent_budget_reports_nothing(self):
        defects, observations, combined = budget_findings(SOUND_RECORD)
        self.assertEqual(defects, [])
        self.assertEqual(observations, [])
        self.assertAlmostEqual(combined, math.sqrt(EXPECTED_VARIANCE), places=12)

    def test_a_combined_uncertainty_that_does_not_follow_is_reported(self):
        record = _record("uncertainty-budget", combined_standard_uncertainty_percent=0.55)
        defects, _, _ = budget_findings(record)
        self.assertIn("combined-uncertainty-mismatch", {d["defect"] for d in defects})

    def test_an_expanded_uncertainty_that_does_not_follow_is_reported(self):
        record = _record("uncertainty-budget", expanded_uncertainty_percent=1.5)
        defects, _, _ = budget_findings(record)
        self.assertIn("expanded-uncertainty-mismatch", {d["defect"] for d in defects})

    def test_a_budget_with_no_components_returns_no_combined_value(self):
        record = _record("uncertainty-budget", components=[])
        defects, observations, combined = budget_findings(record)
        self.assertIsNone(combined)
        self.assertEqual(defects, [])
        self.assertEqual(observations, [])

    def test_a_non_positive_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            budget_findings(SOUND_RECORD, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_sheet_is_complete(self):
        result = assess_standard_cell_documentation(SOUND_RECORD)
        self.assertEqual(result["verdict"], COMPLETE_VERDICT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["notes"], [])
        self.assertEqual(result["serial_number"], "SC-2211-07")
        self.assertEqual(result["calibration_day"], "2026-02-11")

    def test_a_missing_field_makes_the_sheet_incomplete(self):
        record = _record()
        del record["identification"]["serial_number"]
        result = assess_standard_cell_documentation(record)
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertIn("field-not-reported", _defect_names(result))
        self.assertLess(result["completeness_ratio"], 1.0)

    def test_a_calibration_value_of_zero_is_reported_as_a_defect(self):
        record = _record("calibration", calibration_value_a=0.0)
        result = assess_standard_cell_documentation(record)
        self.assertIn("calibration-value-not-positive", _defect_names(result))
        self.assertNotIn("calibration.calibration_value_a", result["missing_fields"])

    def test_a_negative_calibration_value_is_reported_as_a_defect(self):
        record = _record("calibration", calibration_value_a=-0.5)
        result = assess_standard_cell_documentation(record)
        self.assertIn("calibration-value-not-positive", _defect_names(result))

    def test_a_malformed_calibration_day_is_reported_as_a_defect(self):
        record = _record("calibration", calibration_date="11.02.2026")
        result = assess_standard_cell_documentation(record)
        self.assertIn("calibration-day-malformed", _defect_names(result))
        self.assertIsNone(result["calibration_day"])

    def test_a_budget_that_does_not_recompute_makes_the_sheet_incomplete(self):
        record = _record("uncertainty-budget", combined_standard_uncertainty_percent=0.55)
        result = assess_standard_cell_documentation(record)
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertIn("combined-uncertainty-mismatch", _defect_names(result))

    def test_a_dominant_component_is_a_note_and_not_a_defect(self):
        record = _record()
        loaded = copy.deepcopy(COMPONENTS)
        loaded[0]["value_percent"] = 0.60
        record["uncertainty-budget"]["components"] = loaded
        record["uncertainty-budget"]["combined_standard_uncertainty_percent"] = 0.662231
        record["uncertainty-budget"]["expanded_uncertainty_percent"] = 1.324462
        result = assess_standard_cell_documentation(record)
        self.assertEqual(result["verdict"], COMPLETE_VERDICT)
        self.assertIn("dominant-uncertainty-component", _observation_names(result))
        self.assertEqual(result["defects"], [])

    def test_a_budget_with_no_type_a_term_is_a_note_and_not_a_defect(self):
        record = _record()
        all_type_b = copy.deepcopy(COMPONENTS)
        all_type_b[3]["evaluation"] = "type-b"
        record["uncertainty-budget"]["components"] = all_type_b
        result = assess_standard_cell_documentation(record)
        self.assertEqual(result["verdict"], COMPLETE_VERDICT)
        self.assertIn("no-type-a-component", _observation_names(result))

    def test_the_assessment_carries_the_recomputed_combined_uncertainty(self):
        result = assess_standard_cell_documentation(SOUND_RECORD)
        self.assertAlmostEqual(
            result["recomputed_combined_uncertainty_percent"],
            math.sqrt(EXPECTED_VARIANCE),
            places=12,
        )

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_standard_cell_documentation("SC-2211-07")

    def test_an_empty_sheet_reports_every_required_field_as_absent(self):
        result = assess_standard_cell_documentation({})
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertAlmostEqual(result["completeness_ratio"], 0.0, places=12)
        self.assertEqual(
            len(result["missing_fields"]),
            sum(len(fields) for fields in REQUIRED_FIELDS.values()),
        )


if __name__ == "__main__":
    unittest.main()
