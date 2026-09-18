"""Contract tests for the clause 5.4.14.5 contact discharge presentation logic."""

import math
import unittest

from e2007_contact_discharge_data_presentation_logic import (
    COMPLIANT,
    NON_COMPLIANT,
    PRESENTATION_COMPLETE,
    PRESENTATION_INCOMPLETE,
    PRESENTATION_WITH_LIMITATIONS,
    DEFAULT_SPECIFIED_RISE_TIME_S,
    REQUIRED_SETTINGS_FIELDS,
    RISE_BANDWIDTH_PRODUCT,
    assess_contact_discharge_presentation,
    audit_generator_settings,
    bandwidth_is_adequate,
    coverage_gaps,
    criterion_allowance,
    deembed_rise_time_s,
    grade_row,
    grade_rows,
    grade_scope_record,
    missing_scope_records,
    normalize_criterion,
    normalize_polarity,
    normalize_response,
    normalize_verdict,
    required_bandwidth_hz,
    response_rank,
    scope_contribution_fraction,
    scope_rise_time_s,
    validate_row,
    validate_scope_record,
    verdict_from_response,
)


def make_settings(**overrides):
    """Return a fully filled generator-settings block."""
    settings = {
        "charge_voltage_levels_kv": [2.0, 4.0],
        "discharge_resistance_ohm": 330.0,
        "storage_capacitance_f": 150e-12,
        "tip_type": "contact-tip",
        "polarities": ["positive", "negative"],
        "discharges_per_point": 10,
    }
    settings.update(overrides)
    return settings


def make_trace(**overrides):
    """Return a well-formed calibration oscilloscope record."""
    trace = {
        "trace_id": "T1",
        "level_kv": 4.0,
        "polarity": "positive",
        "bandwidth_hz": 2.0e9,
        "measured_rise_time_s": 0.8e-9,
    }
    trace.update(overrides)
    return trace


def make_row(**overrides):
    """Return a well-formed compliance-table row."""
    row = {
        "row_id": "R1",
        "application_point": "chassis-face-A",
        "polarity": "positive",
        "level_kv": 4.0,
        "discharges_applied": 10,
        "observed_response": "no-effect",
        "required_criterion": "criterion-b",
        "verdict": "compliant",
    }
    row.update(overrides)
    return row


def make_report(**overrides):
    """Return a complete two-point, two-polarity contact discharge report."""
    report = {
        "generator_settings": make_settings(),
        "oscilloscope_records": [
            make_trace(trace_id="T1", polarity="positive"),
            make_trace(trace_id="T2", polarity="negative"),
        ],
        "rows": [
            make_row(row_id="R1", application_point="chassis-face-A", polarity="positive"),
            make_row(row_id="R2", application_point="chassis-face-A", polarity="negative"),
            make_row(row_id="R3", application_point="connector-shell-J3", polarity="positive"),
            make_row(row_id="R4", application_point="connector-shell-J3", polarity="negative"),
        ],
        "declared_application_points": ["chassis-face-A", "connector-shell-J3"],
        "declared_polarities": ["positive", "negative"],
        "required_discharges_per_point": 10,
    }
    report.update(overrides)
    return report


class NormalizationTests(unittest.TestCase):
    def test_response_synonyms_collapse(self):
        self.assertEqual(normalize_response("No Effect"), "no-effect")
        self.assertEqual(normalize_response("auto-recovered"), "self-recovering")
        self.assertEqual(normalize_response("damage"), "permanent-degradation")

    def test_unknown_response_rejected(self):
        with self.assertRaises(ValueError):
            normalize_response("mostly fine")

    def test_response_ranks_increase_with_severity(self):
        self.assertLess(response_rank("no-effect"), response_rank("self-recovering"))
        self.assertLess(
            response_rank("operator-recovered"), response_rank("permanent-degradation")
        )

    def test_criterion_synonyms_collapse(self):
        self.assertEqual(normalize_criterion("B"), "criterion-b")
        self.assertEqual(normalize_criterion("criterion c"), "criterion-c")

    def test_unknown_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion("criterion-z")

    def test_verdict_synonyms_collapse(self):
        self.assertEqual(normalize_verdict("PASS"), COMPLIANT)
        self.assertEqual(normalize_verdict(" failed "), NON_COMPLIANT)

    def test_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            normalize_verdict("under review")

    def test_polarity_synonyms_collapse(self):
        self.assertEqual(normalize_polarity("+"), "positive")
        self.assertEqual(normalize_polarity("NEG"), "negative")


class VerdictDerivationTests(unittest.TestCase):
    def test_no_effect_clears_the_strictest_criterion(self):
        self.assertEqual(verdict_from_response("no-effect", "criterion-a"), COMPLIANT)

    def test_self_recovery_fails_the_strictest_criterion(self):
        self.assertEqual(
            verdict_from_response("self-recovering", "criterion-a"), NON_COMPLIANT
        )

    def test_self_recovery_clears_the_middle_criterion(self):
        self.assertEqual(
            verdict_from_response("self-recovering", "criterion-b"), COMPLIANT
        )

    def test_permanent_degradation_fails_every_criterion(self):
        for criterion in ("criterion-a", "criterion-b", "criterion-c"):
            self.assertEqual(
                verdict_from_response("permanent-degradation", criterion),
                NON_COMPLIANT,
            )

    def test_allowance_grows_with_the_criterion_letter(self):
        self.assertLess(
            criterion_allowance("criterion-a"), criterion_allowance("criterion-c")
        )


class BandwidthTests(unittest.TestCase):
    def test_required_bandwidth_is_the_rise_time_product(self):
        self.assertAlmostEqual(
            required_bandwidth_hz(0.35e-9), 1.0e9, places=3
        )

    def test_scope_rise_time_is_the_inverse_relation(self):
        self.assertAlmostEqual(
            scope_rise_time_s(1.0e9), RISE_BANDWIDTH_PRODUCT * 1e-9, places=15
        )

    def test_bandwidth_exactly_matching_the_edge_is_adequate(self):
        edge = DEFAULT_SPECIFIED_RISE_TIME_S
        self.assertTrue(bandwidth_is_adequate(required_bandwidth_hz(edge), edge))

    def test_slow_scope_is_not_adequate(self):
        self.assertFalse(bandwidth_is_adequate(1.0e8, DEFAULT_SPECIFIED_RISE_TIME_S))

    def test_adequacy_is_graded_against_the_specified_edge_not_the_trace(self):
        # A slow front end records a slow edge. Grading it against its own
        # output would pass it; grading it against the specified edge fails it.
        slow_bandwidth = 1.0e8
        recorded = 4.0e-9
        self.assertTrue(bandwidth_is_adequate(slow_bandwidth, recorded))
        self.assertFalse(
            bandwidth_is_adequate(slow_bandwidth, DEFAULT_SPECIFIED_RISE_TIME_S)
        )

    def test_deembedding_removes_the_instrument_edge(self):
        measured = 0.8e-9
        bandwidth = 2.0e9
        instrument = scope_rise_time_s(bandwidth)
        expected = math.sqrt(measured * measured - instrument * instrument)
        self.assertAlmostEqual(
            deembed_rise_time_s(measured, bandwidth), expected, places=15
        )

    def test_a_fast_scope_contributes_almost_nothing(self):
        self.assertLess(scope_contribution_fraction(0.8e-9, 2.0e10), 0.01)

    def test_a_marginal_scope_contributes_materially(self):
        self.assertGreater(scope_contribution_fraction(0.8e-9, 1.0e9), 0.10)

    def test_edge_faster_than_the_instrument_is_rejected(self):
        with self.assertRaises(ValueError):
            deembed_rise_time_s(0.1e-9, 1.0e9)

    def test_zero_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            scope_rise_time_s(0.0)

    def test_zero_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            required_bandwidth_hz(0.0)


class SettingsAuditTests(unittest.TestCase):
    def test_complete_settings_leave_nothing_missing(self):
        audited = audit_generator_settings(make_settings())
        self.assertEqual(audited["missing"], [])
        self.assertEqual(len(audited["present"]), len(REQUIRED_SETTINGS_FIELDS))

    def test_absent_field_is_reported_missing(self):
        settings = make_settings()
        del settings["tip_type"]
        self.assertEqual(audit_generator_settings(settings)["missing"], ["tip_type"])

    def test_blank_field_is_reported_missing(self):
        audited = audit_generator_settings(make_settings(tip_type="   "))
        self.assertEqual(audited["missing"], ["tip_type"])

    def test_empty_sequence_is_reported_missing(self):
        audited = audit_generator_settings(make_settings(polarities=[]))
        self.assertEqual(audited["missing"], ["polarities"])

    def test_none_field_is_reported_missing(self):
        audited = audit_generator_settings(make_settings(discharge_resistance_ohm=None))
        self.assertEqual(audited["missing"], ["discharge_resistance_ohm"])

    def test_wrongly_typed_field_rejected(self):
        with self.assertRaises(ValueError):
            audit_generator_settings(make_settings(discharge_resistance_ohm={"r": 330}))

    def test_non_mapping_settings_rejected(self):
        with self.assertRaises(ValueError):
            audit_generator_settings(["330 ohm"])


class ScopeRecordTests(unittest.TestCase):
    def test_well_formed_trace_normalizes(self):
        record = validate_scope_record(make_trace(polarity="+"))
        self.assertEqual(record["polarity"], "positive")

    def test_blank_trace_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_scope_record(make_trace(trace_id=" "))

    def test_non_finite_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_scope_record(make_trace(bandwidth_hz=float("inf")))

    def test_graded_trace_carries_the_deembedded_edge(self):
        record = grade_scope_record(make_trace())
        self.assertTrue(record["bandwidth_is_adequate"])
        self.assertLess(record["deembedded_rise_time_s"], record["measured_rise_time_s"])


class RowTests(unittest.TestCase):
    def test_well_formed_row_normalizes(self):
        record = validate_row(make_row(verdict="PASS", polarity="-"))
        self.assertEqual(record["verdict"], COMPLIANT)
        self.assertEqual(record["polarity"], "negative")

    def test_empty_response_cell_is_carried_not_rejected(self):
        self.assertIsNone(validate_row(make_row(observed_response=""))["observed_response"])

    def test_absent_response_key_is_carried(self):
        row = make_row()
        del row["observed_response"]
        self.assertIsNone(validate_row(row)["observed_response"])

    def test_fractional_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(discharges_applied=9.5))

    def test_boolean_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(level_kv=True))

    def test_blank_application_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(make_row(application_point="  "))

    def test_agreeing_row_is_graded_as_agreeing(self):
        self.assertTrue(grade_row(make_row())["verdict_agrees"])

    def test_contradicting_row_is_caught(self):
        record = grade_row(
            make_row(observed_response="permanent-degradation", verdict="compliant")
        )
        self.assertFalse(record["verdict_agrees"])
        self.assertEqual(record["derived_verdict"], NON_COMPLIANT)

    def test_honest_non_compliant_row_agrees(self):
        record = grade_row(
            make_row(observed_response="permanent-degradation", verdict="fail")
        )
        self.assertTrue(record["verdict_agrees"])

    def test_row_at_the_top_of_its_allowance_has_no_margin(self):
        record = grade_row(
            make_row(observed_response="self-recovering", required_criterion="criterion-b")
        )
        self.assertEqual(record["margin_steps"], 0)

    def test_duplicate_row_identifier_rejected(self):
        with self.assertRaises(ValueError):
            grade_rows([make_row(), make_row()])

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            grade_rows([])


class CoverageTests(unittest.TestCase):
    def test_complete_table_has_no_gaps(self):
        report = make_report()
        graded = grade_rows(report["rows"])
        self.assertEqual(
            coverage_gaps(graded, report["declared_application_points"],
                          report["declared_polarities"], 10),
            [],
        )

    def test_point_absent_from_the_table_is_a_gap(self):
        report = make_report()
        graded = grade_rows(report["rows"][:2])
        gaps = coverage_gaps(graded, report["declared_application_points"],
                             report["declared_polarities"], 10)
        self.assertTrue(any("connector-shell-J3" in g for g in gaps))

    def test_missing_polarity_at_a_point_is_a_gap(self):
        report = make_report()
        rows = [r for r in report["rows"] if r["polarity"] == "positive"]
        gaps = coverage_gaps(grade_rows(rows), report["declared_application_points"],
                             report["declared_polarities"], 10)
        self.assertTrue(any("negative polarity" in g for g in gaps))

    def test_short_discharge_count_is_a_gap(self):
        report = make_report()
        graded = grade_rows(report["rows"])
        gaps = coverage_gaps(graded, report["declared_application_points"],
                             report["declared_polarities"], 25)
        self.assertEqual(len(gaps), 4)

    def test_empty_declared_point_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_gaps(grade_rows(make_report()["rows"]), [], ["positive"], 10)

    def test_missing_scope_pair_is_detected(self):
        report = make_report()
        graded = grade_rows(report["rows"])
        traces = [grade_scope_record(make_trace(polarity="positive"))]
        self.assertEqual(missing_scope_records(graded, traces), [(4.0, "negative")])


class AssessmentTests(unittest.TestCase):
    def test_complete_report_passes(self):
        result = assess_contact_discharge_presentation(make_report())
        self.assertEqual(result["verdict"], PRESENTATION_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_missing_settings_field_is_a_finding(self):
        settings = make_settings()
        del settings["storage_capacitance_f"]
        result = assess_contact_discharge_presentation(
            make_report(generator_settings=settings)
        )
        self.assertEqual(result["verdict"], PRESENTATION_INCOMPLETE)
        self.assertTrue(any("storage_capacitance_f" in f for f in result["findings"]))

    def test_absent_oscilloscope_records_is_a_finding(self):
        result = assess_contact_discharge_presentation(
            make_report(oscilloscope_records=[])
        )
        self.assertTrue(
            any("no calibration oscilloscope record" in f for f in result["findings"])
        )

    def test_inadequate_scope_bandwidth_is_a_finding(self):
        report = make_report(
            oscilloscope_records=[
                make_trace(
                    trace_id="T1",
                    polarity="positive",
                    bandwidth_hz=1.0e8,
                    measured_rise_time_s=4.0e-9,
                ),
                make_trace(trace_id="T2", polarity="negative"),
            ]
        )
        result = assess_contact_discharge_presentation(report)
        self.assertEqual(result["verdict"], PRESENTATION_INCOMPLETE)
        self.assertTrue(any("T1" in f for f in result["findings"]))

    def test_marginal_scope_becomes_a_limitation(self):
        report = make_report(
            oscilloscope_records=[
                make_trace(trace_id="T1", polarity="positive", bandwidth_hz=1.0e9),
                make_trace(trace_id="T2", polarity="negative", bandwidth_hz=1.0e9),
            ]
        )
        result = assess_contact_discharge_presentation(report)
        self.assertEqual(result["verdict"], PRESENTATION_WITH_LIMITATIONS)
        self.assertTrue(any("de-embedded" in n for n in result["limitations"]))

    def test_uncovered_level_and_polarity_is_a_finding(self):
        report = make_report(
            oscilloscope_records=[make_trace(trace_id="T1", polarity="positive")]
        )
        result = assess_contact_discharge_presentation(report)
        self.assertTrue(any("no oscilloscope record covers" in f for f in result["findings"]))

    def test_empty_response_cell_is_the_headline_finding(self):
        report = make_report()
        report["rows"][0] = make_row(row_id="R1", observed_response="")
        result = assess_contact_discharge_presentation(report)
        self.assertTrue(any("response cell empty" in f for f in result["findings"]))

    def test_contradicting_verdict_is_a_finding(self):
        report = make_report()
        report["rows"][2] = make_row(
            row_id="R3",
            application_point="connector-shell-J3",
            polarity="positive",
            observed_response="permanent-degradation",
            verdict="compliant",
        )
        result = assess_contact_discharge_presentation(report)
        self.assertEqual(result["verdict"], PRESENTATION_INCOMPLETE)
        self.assertTrue(any("R3" in f and "derives" in f for f in result["findings"]))

    def test_honest_failure_is_not_a_presentation_finding(self):
        report = make_report()
        report["rows"][3] = make_row(
            row_id="R4",
            application_point="connector-shell-J3",
            polarity="negative",
            observed_response="permanent-degradation",
            verdict="non-compliant",
        )
        result = assess_contact_discharge_presentation(report)
        self.assertEqual(result["findings"], [])

    def test_row_with_no_margin_is_a_limitation(self):
        report = make_report()
        report["rows"][0] = make_row(
            row_id="R1", observed_response="self-recovering",
            required_criterion="criterion-b",
        )
        result = assess_contact_discharge_presentation(report)
        self.assertTrue(any("no room left" in n for n in result["limitations"]))

    def test_coverage_gap_reaches_the_findings(self):
        report = make_report()
        report["rows"] = report["rows"][:2]
        result = assess_contact_discharge_presentation(report)
        self.assertTrue(result["coverage_gaps"])
        self.assertEqual(result["verdict"], PRESENTATION_INCOMPLETE)

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_discharge_presentation(["rows"])

    def test_string_scope_record_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_discharge_presentation(make_report(oscilloscope_records="T1"))

    def test_assessment_is_deterministic(self):
        first = assess_contact_discharge_presentation(make_report())
        second = assess_contact_discharge_presentation(make_report())
        self.assertEqual(first["verdict"], second["verdict"])
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(first["limitations"], second["limitations"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
