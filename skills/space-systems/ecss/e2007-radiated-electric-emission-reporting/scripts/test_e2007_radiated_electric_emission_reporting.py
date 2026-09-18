#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-emission-reporting.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_emission_reporting.py
"""

import unittest

from e2007_radiated_electric_emission_reporting_logic import (
    CONTINUITY_CONTINUOUS,
    CONTINUITY_MARGINAL,
    CONTINUITY_OPEN,
    DEFAULT_CONTINUITY_LIMIT_OHM,
    MARGINAL_FRACTION,
    PACKAGE_COMPLETE,
    PACKAGE_DATA_ONLY,
    PACKAGE_UNSUPPORTED,
    antennas_in_data,
    antennas_without_statement,
    assemble_emission_report,
    at_least,
    at_most,
    categorize_continuity,
    categorize_package,
    conflicting_statements,
    exceedances,
    governing_statement,
    margin_db,
    statements_outside_run,
    validate_continuity_statement,
    validate_continuity_statements,
    validate_emission_record,
    validate_emission_records,
    worst_margin_db,
)

RUN_START = 100.0
RUN_END = 4000.0


def statement(
    antenna="biconical-1",
    resistance=0.02,
    measured_at=120.0,
    method="four-wire",
    recorded_by="emc-operator",
):
    return {
        "antenna_id": antenna,
        "resistance_ohm": resistance,
        "measured_at_s": measured_at,
        "method": method,
        "recorded_by": recorded_by,
    }


def emission(
    frequency=100.0e6,
    level=30.0,
    limit=40.0,
    antenna="biconical-1",
    polarization="horizontal",
):
    return {
        "frequency_hz": frequency,
        "level_dbuv_per_m": level,
        "limit_dbuv_per_m": limit,
        "antenna_id": antenna,
        "polarization": polarization,
    }


def data_set():
    return [
        emission(100.0e6, 30.0),
        emission(200.0e6, 28.0, polarization="vertical"),
        emission(900.0e6, 26.0, antenna="horn-1"),
    ]


def statement_set():
    return [statement("biconical-1"), statement("horn-1", resistance=0.03)]


class TestStatementValidation(unittest.TestCase):
    def test_statement_is_normalized(self):
        record = validate_continuity_statement(statement())
        self.assertEqual(record["antenna_id"], "biconical-1")
        self.assertAlmostEqual(record["resistance_ohm"], 0.02, places=9)

    def test_negative_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_continuity_statement(statement(resistance=-0.01))

    def test_negative_measurement_time_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_continuity_statement(statement(measured_at=-1.0))

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_continuity_statement(statement(method="guesswork"))

    def test_missing_signatory_is_rejected(self):
        record = statement()
        del record["recorded_by"]
        with self.assertRaises(ValueError):
            validate_continuity_statement(record)

    def test_boolean_resistance_is_not_a_number(self):
        record = statement()
        record["resistance_ohm"] = True
        with self.assertRaises(ValueError):
            validate_continuity_statement(record)

    def test_statements_sort_by_antenna_then_time(self):
        ordered = validate_continuity_statements(list(reversed(statement_set())))
        self.assertEqual(ordered[0]["antenna_id"], "biconical-1")

    def test_an_empty_statement_list_is_allowed_at_validation(self):
        self.assertEqual(validate_continuity_statements([]), [])


class TestContinuityGrouping(unittest.TestCase):
    def test_a_low_resistance_path_is_continuous(self):
        self.assertEqual(
            categorize_continuity(statement(resistance=0.01)), CONTINUITY_CONTINUOUS
        )

    def test_a_resistance_just_under_the_limit_is_marginal(self):
        marginal = DEFAULT_CONTINUITY_LIMIT_OHM * MARGINAL_FRACTION
        self.assertEqual(
            categorize_continuity(statement(resistance=marginal)), CONTINUITY_MARGINAL
        )

    def test_a_resistance_exactly_on_the_limit_is_still_not_open(self):
        self.assertEqual(
            categorize_continuity(statement(resistance=DEFAULT_CONTINUITY_LIMIT_OHM)),
            CONTINUITY_MARGINAL,
        )

    def test_a_resistance_over_the_limit_is_open(self):
        self.assertEqual(
            categorize_continuity(statement(resistance=1.5)), CONTINUITY_OPEN
        )

    def test_a_non_positive_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_continuity(statement(), limit_ohm=0.0)


class TestEmissionRecords(unittest.TestCase):
    def test_record_is_normalized(self):
        record = validate_emission_record(emission())
        self.assertAlmostEqual(record["frequency_hz"], 100.0e6, places=3)

    def test_non_positive_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_record(emission(frequency=0.0))

    def test_unknown_polarization_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_record(emission(polarization="slant"))

    def test_an_empty_data_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_records([])

    def test_margin_is_limit_minus_level(self):
        self.assertAlmostEqual(margin_db(emission(level=30.0, limit=40.0)), 10.0, places=9)

    def test_a_level_exactly_on_its_limit_is_not_an_exceedance(self):
        self.assertEqual(exceedances([emission(level=40.0, limit=40.0)]), [])

    def test_a_level_over_its_limit_is_an_exceedance(self):
        over = exceedances([emission(level=44.0, limit=40.0)])
        self.assertEqual(len(over), 1)
        self.assertAlmostEqual(over[0]["margin_db"], -4.0, places=9)

    def test_worst_margin_picks_the_smallest(self):
        self.assertAlmostEqual(worst_margin_db(data_set()), 10.0, places=9)

    def test_antennas_in_data_are_listed_once_each(self):
        self.assertEqual(antennas_in_data(data_set()), ["biconical-1", "horn-1"])


class TestStatementCoverage(unittest.TestCase):
    def test_every_antenna_covered_leaves_nothing_missing(self):
        self.assertEqual(antennas_without_statement(data_set(), statement_set()), [])

    def test_an_uncovered_antenna_is_named(self):
        missing = antennas_without_statement(data_set(), [statement("biconical-1")])
        self.assertEqual(missing, ["horn-1"])

    def test_a_statement_inside_the_run_window_is_not_stale(self):
        self.assertEqual(statements_outside_run(statement_set(), RUN_START, RUN_END), [])

    def test_a_statement_taken_before_the_run_is_stale(self):
        stale = statements_outside_run([statement(measured_at=10.0)], RUN_START, RUN_END)
        self.assertEqual(len(stale), 1)

    def test_a_statement_on_the_window_edge_is_accepted(self):
        self.assertEqual(
            statements_outside_run([statement(measured_at=RUN_END)], RUN_START, RUN_END),
            [],
        )

    def test_an_inverted_run_window_is_rejected(self):
        with self.assertRaises(ValueError):
            statements_outside_run(statement_set(), RUN_END, RUN_START)

    def test_duplicate_statements_are_reported(self):
        pair = [statement("biconical-1", 0.02), statement("biconical-1", 0.09, 200.0)]
        self.assertEqual(conflicting_statements(pair), ["biconical-1"])

    def test_the_worst_case_statement_governs(self):
        pair = [statement("biconical-1", 0.02), statement("biconical-1", 0.09, 200.0)]
        self.assertAlmostEqual(
            governing_statement(pair, "biconical-1")["resistance_ohm"], 0.09, places=9
        )

    def test_governing_statement_raises_for_an_unstated_antenna(self):
        with self.assertRaises(ValueError):
            governing_statement(statement_set(), "loop-1")


class TestPackageGrouping(unittest.TestCase):
    def test_data_with_every_statement_is_complete(self):
        self.assertEqual(
            categorize_package(data_set(), statement_set()), PACKAGE_COMPLETE
        )

    def test_data_with_a_statement_missing_is_data_only(self):
        self.assertEqual(
            categorize_package(data_set(), [statement("biconical-1")]),
            PACKAGE_DATA_ONLY,
        )

    def test_data_behind_an_open_antenna_is_unsupported(self):
        statements = [statement("biconical-1"), statement("horn-1", resistance=2.0)]
        self.assertEqual(
            categorize_package(data_set(), statements), PACKAGE_UNSUPPORTED
        )


class TestBoundHelpers(unittest.TestCase):
    def test_at_least_absorbs_representation_error(self):
        self.assertTrue(at_least(0.1 + 0.2, 0.3))

    def test_at_most_absorbs_representation_error(self):
        self.assertTrue(at_most(0.3, 0.1 + 0.2))


class TestReportAssembly(unittest.TestCase):
    def test_a_complete_package_is_reportable(self):
        report = assemble_emission_report(
            data_set(), statement_set(), RUN_START, RUN_END
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], "reportable")
        self.assertEqual(report["package"], PACKAGE_COMPLETE)

    def test_a_missing_statement_makes_the_report_incomplete(self):
        report = assemble_emission_report(
            data_set(), [statement("biconical-1")], RUN_START, RUN_END
        )
        self.assertEqual(report["verdict"], "report-incomplete")
        self.assertTrue(
            any("no continuity statement" in m for m in report["findings"])
        )

    def test_an_open_antenna_is_a_finding(self):
        statements = [statement("biconical-1"), statement("horn-1", resistance=2.0)]
        report = assemble_emission_report(data_set(), statements, RUN_START, RUN_END)
        self.assertTrue(any("not supported" in m for m in report["findings"]))
        self.assertEqual(report["package"], PACKAGE_UNSUPPORTED)

    def test_a_stale_statement_is_a_finding(self):
        statements = [statement("biconical-1", measured_at=5.0), statement("horn-1")]
        report = assemble_emission_report(data_set(), statements, RUN_START, RUN_END)
        self.assertTrue(any("outside the run" in m for m in report["findings"]))

    def test_a_two_wire_statement_is_a_limitation_not_a_finding(self):
        statements = [
            statement("biconical-1", method="two-wire"),
            statement("horn-1"),
        ]
        report = assemble_emission_report(data_set(), statements, RUN_START, RUN_END)
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("two-wire" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], "reportable")

    def test_an_exceedance_is_a_limitation_on_an_otherwise_complete_package(self):
        records = data_set()
        records[0] = emission(100.0e6, level=44.0, limit=40.0)
        report = assemble_emission_report(records, statement_set(), RUN_START, RUN_END)
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("exceeds its limit" in m for m in report["limitations"]))

    def test_report_carries_the_continuity_row_per_antenna(self):
        report = assemble_emission_report(
            data_set(), statement_set(), RUN_START, RUN_END
        )
        self.assertEqual(len(report["continuity"]), 2)
        self.assertEqual(report["continuity"][0]["category"], CONTINUITY_CONTINUOUS)

    def test_assembly_propagates_an_empty_data_set(self):
        with self.assertRaises(ValueError):
            assemble_emission_report([], statement_set(), RUN_START, RUN_END)


if __name__ == "__main__":
    unittest.main()
