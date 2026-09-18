"""Contract tests for the clause 5.4.12.5 indirect-discharge presentation logic."""

import math
import unittest

from e2007_indirect_discharge_data_presentation_logic import (
    IMPLAUSIBLY_QUIET_DB,
    MARGIN_TOLERANCE_DB,
    NARROW_MARGIN_DB,
    assess_presentation,
    coverage_gaps,
    grade_row,
    grade_rows,
    induced_current_margin_db,
    normalize_polarity,
    normalize_verdict,
    peak_levels_by_circuit,
    validate_row,
)


def make_row(**overrides):
    """Return a well-formed compliance-table row with optional overrides."""
    row = {
        "event_id": "D1",
        "application_point": "harness-bundle-A",
        "polarity": "positive",
        "discharge_count": 10,
        "monitored_circuit": "tm-differential-pair",
        "induced_current_a": 0.4,
        "susceptibility_limit_a": 4.0,
        "verdict": "compliant",
    }
    row.update(overrides)
    return row


def make_record(**overrides):
    """Return a two-point, two-polarity presentation record."""
    record = {
        "rows": [
            make_row(event_id="D1", application_point="harness-bundle-A", polarity="positive"),
            make_row(event_id="D2", application_point="harness-bundle-A", polarity="negative"),
            make_row(event_id="D3", application_point="connector-shell-J7", polarity="positive"),
            make_row(event_id="D4", application_point="connector-shell-J7", polarity="negative"),
        ],
        "declared_application_points": ["harness-bundle-A", "connector-shell-J7"],
        "declared_monitored_circuits": ["tm-differential-pair"],
        "required_discharges_per_point": 10,
    }
    record.update(overrides)
    return record


class NormalizationTests(unittest.TestCase):
    def test_verdict_synonyms_collapse_to_compliant(self):
        for token in ("compliant", "PASS", " Passed ", "conforming"):
            self.assertEqual(normalize_verdict(token), "compliant")

    def test_verdict_synonyms_collapse_to_non_compliant(self):
        for token in ("non-compliant", "FAIL", "not compliant", "noncompliant"):
            self.assertEqual(normalize_verdict(token), "non-compliant")

    def test_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            normalize_verdict("probably fine")

    def test_blank_verdict_rejected(self):
        with self.assertRaises(ValueError):
            normalize_verdict("   ")

    def test_polarity_synonyms(self):
        self.assertEqual(normalize_polarity("+"), "positive")
        self.assertEqual(normalize_polarity("NEG"), "negative")

    def test_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarity("alternating")


class ValidateRowTests(unittest.TestCase):
    def test_normalized_row_keeps_every_cell(self):
        record = validate_row(make_row(polarity="-", verdict="PASS"))
        self.assertEqual(record["polarity"], "negative")
        self.assertEqual(record["verdict"], "compliant")
        self.assertAlmostEqual(record["induced_current_a"], 0.4, places=12)

    def test_absent_level_is_preserved_not_rejected(self):
        row = make_row()
        del row["induced_current_a"]
        self.assertIsNone(validate_row(row)["induced_current_a"])

    def test_missing_required_cell_rejected(self):
        row = make_row()
        del row["monitored_circuit"]
        with self.assertRaises(ValueError):
            validate_row(row)

    def test_non_mapping_row_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(["D1", "harness-bundle-A"])

    def test_zero_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(discharge_count=0))

    def test_boolean_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(discharge_count=True))

    def test_negative_induced_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(induced_current_a=-0.4))

    def test_non_finite_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(susceptibility_limit_a=float("inf")))

    def test_blank_application_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(application_point="  "))


class MarginTests(unittest.TestCase):
    def test_decade_below_limit_is_twenty_db(self):
        self.assertAlmostEqual(induced_current_margin_db(4.0, 0.4), 20.0, places=9)

    def test_level_on_the_limit_is_zero_db(self):
        self.assertAlmostEqual(induced_current_margin_db(4.0, 4.0), 0.0, places=9)

    def test_level_above_the_limit_is_negative(self):
        self.assertAlmostEqual(induced_current_margin_db(4.0, 40.0), -20.0, places=9)

    def test_margin_is_a_ratio_not_a_difference(self):
        self.assertAlmostEqual(
            induced_current_margin_db(8.0, 0.8),
            induced_current_margin_db(4.0, 0.4),
            places=9,
        )

    def test_zero_observed_current_rejected(self):
        with self.assertRaises(ValueError):
            induced_current_margin_db(4.0, 0.0)


class GradeRowTests(unittest.TestCase):
    def test_clean_row_carries_no_finding(self):
        record = grade_row(make_row())
        self.assertEqual(record["findings"], [])
        self.assertTrue(record["margin_compliant"])
        self.assertAlmostEqual(record["margin_db"], 20.0, places=9)

    def test_missing_level_is_the_headline_finding(self):
        row = make_row()
        row["induced_current_a"] = None
        record = grade_row(row)
        self.assertIsNone(record["margin_db"])
        self.assertEqual(len(record["findings"]), 1)
        self.assertIn("no induced current level", record["findings"][0])

    def test_verdict_contradicting_its_own_numbers_is_a_finding(self):
        record = grade_row(make_row(induced_current_a=8.0, verdict="compliant"))
        self.assertFalse(record["margin_compliant"])
        self.assertEqual(len(record["findings"]), 1)

    def test_honest_non_compliant_row_is_not_a_finding(self):
        record = grade_row(make_row(induced_current_a=8.0, verdict="fail"))
        self.assertFalse(record["margin_compliant"])
        self.assertEqual(record["findings"], [])

    def test_level_exactly_on_the_limit_counts_as_compliant(self):
        record = grade_row(make_row(induced_current_a=4.0, verdict="compliant"))
        self.assertTrue(record["margin_compliant"])
        self.assertEqual(record["findings"], [])
        self.assertLessEqual(abs(record["margin_db"]), MARGIN_TOLERANCE_DB)

    def test_narrow_margin_is_a_limitation_not_a_finding(self):
        record = grade_row(make_row(induced_current_a=3.0))
        self.assertEqual(record["findings"], [])
        self.assertEqual(len(record["limitations"]), 1)
        self.assertLess(record["margin_db"], NARROW_MARGIN_DB)

    def test_implausibly_quiet_channel_is_a_limitation(self):
        record = grade_row(make_row(induced_current_a=4.0e-5))
        self.assertEqual(record["findings"], [])
        self.assertGreater(record["margin_db"], IMPLAUSIBLY_QUIET_DB)
        self.assertIn("connected", record["limitations"][-1])


class GradeRowsTests(unittest.TestCase):
    def test_table_is_graded_row_by_row(self):
        graded = grade_rows(make_record()["rows"])
        self.assertEqual(len(graded), 4)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            grade_rows([])

    def test_duplicate_event_id_rejected(self):
        rows = [make_row(event_id="D1"), make_row(event_id="D1", polarity="negative")]
        with self.assertRaises(ValueError):
            grade_rows(rows)

    def test_peak_level_per_circuit_is_the_largest_reported(self):
        rows = [
            make_row(event_id="D1", induced_current_a=0.4),
            make_row(event_id="D2", induced_current_a=1.1, polarity="negative"),
            make_row(event_id="D3", induced_current_a=None, polarity="negative"),
        ]
        peaks = peak_levels_by_circuit(grade_rows(rows))
        self.assertAlmostEqual(peaks["tm-differential-pair"], 1.1, places=12)


class CoverageTests(unittest.TestCase):
    def test_complete_table_has_no_gap(self):
        record = make_record()
        graded = grade_rows(record["rows"])
        self.assertEqual(
            coverage_gaps(
                graded,
                record["declared_application_points"],
                record["declared_monitored_circuits"],
                required_discharges_per_point=10,
            ),
            [],
        )

    def test_untouched_application_point_is_a_gap(self):
        record = make_record()
        graded = grade_rows(record["rows"][:2])
        gaps = coverage_gaps(
            graded,
            record["declared_application_points"],
            record["declared_monitored_circuits"],
            required_discharges_per_point=10,
        )
        self.assertEqual(len(gaps), 1)
        self.assertIn("connector-shell-J7", gaps[0])

    def test_single_polarity_point_is_a_gap(self):
        graded = grade_rows([make_row(event_id="D1", polarity="positive")])
        gaps = coverage_gaps(graded, ["harness-bundle-A"], ["tm-differential-pair"])
        self.assertEqual(len(gaps), 1)
        self.assertIn("negative-polarity", gaps[0])

    def test_short_discharge_count_is_a_gap(self):
        graded = grade_rows(
            [
                make_row(event_id="D1", polarity="positive", discharge_count=3),
                make_row(event_id="D2", polarity="negative", discharge_count=10),
            ]
        )
        gaps = coverage_gaps(
            graded,
            ["harness-bundle-A"],
            ["tm-differential-pair"],
            required_discharges_per_point=10,
        )
        self.assertEqual(len(gaps), 1)
        self.assertIn("3 positive-polarity discharges", gaps[0])

    def test_unmonitored_declared_circuit_is_a_gap(self):
        graded = grade_rows(make_record()["rows"])
        gaps = coverage_gaps(
            graded,
            ["harness-bundle-A", "connector-shell-J7"],
            ["tm-differential-pair", "pyro-firing-line"],
            required_discharges_per_point=10,
        )
        self.assertEqual(len(gaps), 1)
        self.assertIn("pyro-firing-line", gaps[0])

    def test_empty_declared_point_list_rejected(self):
        graded = grade_rows(make_record()["rows"])
        with self.assertRaises(ValueError):
            coverage_gaps(graded, [], ["tm-differential-pair"])

    def test_zero_required_discharges_rejected(self):
        graded = grade_rows(make_record()["rows"])
        with self.assertRaises(ValueError):
            coverage_gaps(
                graded,
                ["harness-bundle-A"],
                ["tm-differential-pair"],
                required_discharges_per_point=0,
            )


class AssessPresentationTests(unittest.TestCase):
    def test_complete_table_is_presentable(self):
        result = assess_presentation(make_record())
        self.assertTrue(result["presentable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["row_count"], 4)
        self.assertEqual(result["levels_reported"], 4)

    def test_compliance_without_levels_is_not_presentable(self):
        record = make_record()
        for row in record["rows"]:
            row["induced_current_a"] = None
        result = assess_presentation(record)
        self.assertFalse(result["presentable"])
        self.assertEqual(result["levels_reported"], 0)
        self.assertEqual(len(result["findings"]), 4)

    def test_peaks_are_reported_per_circuit(self):
        record = make_record()
        record["rows"][2]["monitored_circuit"] = "pyro-firing-line"
        record["rows"][2]["induced_current_a"] = 1.6
        record["rows"][3]["monitored_circuit"] = "pyro-firing-line"
        record["declared_monitored_circuits"] = ["tm-differential-pair", "pyro-firing-line"]
        result = assess_presentation(record)
        self.assertAlmostEqual(
            result["peak_levels_by_circuit"]["pyro-firing-line"], 1.6, places=12
        )

    def test_missing_key_rejected(self):
        record = make_record()
        del record["declared_monitored_circuits"]
        with self.assertRaises(ValueError):
            assess_presentation(record)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_presentation(["rows"])

    def test_limitations_do_not_block_presentation(self):
        record = make_record()
        record["rows"][0]["induced_current_a"] = 3.0
        result = assess_presentation(record)
        self.assertTrue(result["presentable"])
        self.assertEqual(len(result["limitations"]), 1)

    def test_margin_moves_by_the_decade_of_the_level(self):
        tight = grade_row(make_row(induced_current_a=0.4))["margin_db"]
        loose = grade_row(make_row(induced_current_a=0.04))["margin_db"]
        self.assertAlmostEqual(loose - tight, 20.0, places=9)
        self.assertAlmostEqual(20.0 * math.log10(10.0), 20.0, places=9)


if __name__ == "__main__":
    unittest.main()
