"""Contract tests for the Annex B (de-)mating logbook and cycle-control logic."""

import unittest
from datetime import date

from q2030_demating_logbook_logic import (
    DEFAULT_MAXIMUM_CYCLES,
    EVENT_FIELDS,
    MANDATORY_EVENT_FIELDS,
    OPERATIONS,
    assess_demating_logbook,
    connector_rows,
    connector_state,
    cycle_status,
    cycles_remaining,
    mating_cycles,
    normalise_identifier,
    parse_day,
    render_control_table,
    validate_event,
    validate_log,
)


def event(connector, day, operation, operator="a.tech", remark=None):
    """Build one logbook entry."""
    return {
        "connector_id": connector,
        "event_date": day,
        "operation": operation,
        "operator": operator,
        "remark": remark,
    }


PAIR = [
    event("J01", "2026-03-01", "mate"),
    event("J01", "2026-03-04", "demate"),
]


class FieldOrderTests(unittest.TestCase):
    def test_entry_field_order_is_the_worked_example_order(self):
        self.assertEqual(
            EVENT_FIELDS,
            ("connector_id", "event_date", "operation", "operator", "remark"),
        )

    def test_remark_is_the_only_optional_field(self):
        self.assertEqual(
            tuple(f for f in EVENT_FIELDS if f not in MANDATORY_EVENT_FIELDS),
            ("remark",),
        )

    def test_only_two_operations_exist(self):
        self.assertEqual(OPERATIONS, ("mate", "demate"))


class NormaliseTests(unittest.TestCase):
    def test_identifier_is_trimmed_and_lowered(self):
        self.assertEqual(normalise_identifier("  J01 ", "id"), "j01")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("   ", "id")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(7, "id")

    def test_iso_day_parsed(self):
        self.assertEqual(parse_day("2026-03-01", "d"), date(2026, 3, 1))

    def test_date_object_passes_through(self):
        self.assertEqual(parse_day(date(2026, 3, 1), "d"), date(2026, 3, 1))

    def test_malformed_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("01/03/2026", "d")


class ValidateEventTests(unittest.TestCase):
    def test_valid_entry_normalised(self):
        entry = validate_event(event(" J01 ", "2026-03-01", "MATE", " A.Tech "))
        self.assertEqual(entry["connector_id"], "j01")
        self.assertEqual(entry["operation"], "mate")
        self.assertEqual(entry["operator"], "a.tech")

    def test_unknown_field_refused(self):
        bad = event("J01", "2026-03-01", "mate")
        bad["torque_nm"] = 0.4
        with self.assertRaises(ValueError):
            validate_event(bad)

    def test_unknown_operation_refused(self):
        with self.assertRaises(ValueError):
            validate_event(event("J01", "2026-03-01", "inspect"))

    def test_blank_operator_refused(self):
        with self.assertRaises(ValueError):
            validate_event(event("J01", "2026-03-01", "mate", operator=None))

    def test_remark_kept_as_trimmed_text(self):
        entry = validate_event(event("J01", "2026-03-01", "mate", remark="  first fit  "))
        self.assertEqual(entry["remark"], "first fit")

    def test_non_mapping_entry_refused(self):
        with self.assertRaises(ValueError):
            validate_event(["J01", "2026-03-01", "mate"])


class ValidateLogTests(unittest.TestCase):
    def test_entries_grouped_per_connector_in_first_entry_order(self):
        log = validate_log(
            [
                event("J02", "2026-03-01", "mate"),
                event("J01", "2026-03-02", "mate"),
                event("J02", "2026-03-03", "demate"),
            ]
        )
        self.assertEqual(log["order"], ("j02", "j01"))
        self.assertEqual(len(log["grouped"]["j02"]), 2)

    def test_backwards_date_for_one_connector_refused(self):
        with self.assertRaises(ValueError):
            validate_log(
                [
                    event("J01", "2026-03-04", "mate"),
                    event("J01", "2026-03-01", "demate"),
                ]
            )

    def test_same_day_mate_and_demate_allowed(self):
        log = validate_log(
            [
                event("J01", "2026-03-01", "mate"),
                event("J01", "2026-03-01", "demate"),
            ]
        )
        self.assertEqual(len(log["grouped"]["j01"]), 2)

    def test_demate_without_a_mate_refused(self):
        with self.assertRaises(ValueError):
            validate_log([event("J01", "2026-03-01", "demate")])

    def test_two_mates_without_a_demate_refused(self):
        with self.assertRaises(ValueError):
            validate_log(
                [
                    event("J01", "2026-03-01", "mate"),
                    event("J01", "2026-03-02", "mate"),
                ]
            )

    def test_interleaved_connectors_do_not_disturb_alternation(self):
        log = validate_log(
            [
                event("J01", "2026-03-01", "mate"),
                event("J02", "2026-03-01", "mate"),
                event("J01", "2026-03-02", "demate"),
                event("J02", "2026-03-02", "demate"),
            ]
        )
        self.assertEqual(set(log["order"]), {"j01", "j02"})

    def test_non_sequence_log_refused(self):
        with self.assertRaises(ValueError):
            validate_log({"connector_id": "j01"})


class CycleCountingTests(unittest.TestCase):
    def test_one_mate_demate_pair_is_one_cycle(self):
        log = validate_log(PAIR)
        self.assertEqual(mating_cycles(log["grouped"]["j01"]), 1)

    def test_a_mate_left_in_place_still_consumes_a_cycle(self):
        log = validate_log([event("J01", "2026-03-01", "mate")])
        self.assertEqual(mating_cycles(log["grouped"]["j01"]), 1)

    def test_three_pairs_are_three_cycles(self):
        entries = []
        for day in range(1, 4):
            entries.append(event("J01", "2026-03-0%d" % day, "mate"))
            entries.append(event("J01", "2026-03-0%d" % day, "demate"))
        log = validate_log(entries)
        self.assertEqual(mating_cycles(log["grouped"]["j01"]), 3)

    def test_state_after_a_mate_is_mated(self):
        log = validate_log([event("J01", "2026-03-01", "mate")])
        self.assertEqual(connector_state(log["grouped"]["j01"]), "mated")

    def test_state_after_a_demate_is_demated(self):
        log = validate_log(PAIR)
        self.assertEqual(connector_state(log["grouped"]["j01"]), "demated")

    def test_empty_entry_list_reads_as_demated(self):
        self.assertEqual(connector_state([]), "demated")

    def test_malformed_entry_refused_by_counter(self):
        with self.assertRaises(ValueError):
            mating_cycles([{"connector": "j01"}])


class CountdownTests(unittest.TestCase):
    def test_remaining_is_maximum_minus_used(self):
        self.assertEqual(cycles_remaining(3, 10), 7)

    def test_remaining_floors_at_zero(self):
        self.assertEqual(cycles_remaining(14, 10), 0)

    def test_negative_used_refused(self):
        with self.assertRaises(ValueError):
            cycles_remaining(-1, 10)

    def test_zero_maximum_refused(self):
        with self.assertRaises(ValueError):
            cycles_remaining(0, 0)

    def test_boolean_used_refused(self):
        with self.assertRaises(ValueError):
            cycles_remaining(True, 10)


class StatusBandTests(unittest.TestCase):
    def test_low_usage_is_within_limit(self):
        self.assertEqual(cycle_status(3, 10), "within-limit")

    def test_four_fifths_opens_the_warning_band(self):
        self.assertEqual(cycle_status(8, 10), "approaching-limit")

    def test_just_below_four_fifths_is_still_within_limit(self):
        self.assertEqual(cycle_status(7, 10), "within-limit")

    def test_equal_to_maximum_is_at_limit(self):
        self.assertEqual(cycle_status(10, 10), "at-limit")

    def test_beyond_maximum_is_exceeded(self):
        self.assertEqual(cycle_status(11, 10), "exceeded")

    def test_band_edge_is_integer_exact_for_an_odd_maximum(self):
        # 4/5 of 7 is 5.6; the band must open at 6, not at a rounded 5.
        self.assertEqual(cycle_status(5, 7), "within-limit")
        self.assertEqual(cycle_status(6, 7), "approaching-limit")


class ControlTableTests(unittest.TestCase):
    def test_rows_carry_the_countdown(self):
        log = validate_log(PAIR)
        rows = connector_rows(log, {"J01": 5})
        self.assertEqual(rows[0]["cycles_used"], 1)
        self.assertEqual(rows[0]["maximum_cycles"], 5)
        self.assertEqual(rows[0]["cycles_remaining"], 4)
        self.assertTrue(rows[0]["maximum_declared"])

    def test_default_maximum_applied_when_none_declared(self):
        log = validate_log(PAIR)
        rows = connector_rows(log)
        self.assertEqual(rows[0]["maximum_cycles"], DEFAULT_MAXIMUM_CYCLES)
        self.assertFalse(rows[0]["maximum_declared"])

    def test_maxima_keys_are_normalised(self):
        log = validate_log(PAIR)
        rows = connector_rows(log, {" j01 ": 3})
        self.assertEqual(rows[0]["maximum_cycles"], 3)

    def test_non_positive_declared_maximum_refused(self):
        log = validate_log(PAIR)
        with self.assertRaises(ValueError):
            connector_rows(log, {"J01": 0})

    def test_table_has_a_header_and_one_row_per_connector(self):
        log = validate_log(
            [
                event("J01", "2026-03-01", "mate"),
                event("J02", "2026-03-01", "mate"),
            ]
        )
        lines = render_control_table(connector_rows(log))
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("CONNECTOR"))

    def test_table_columns_are_aligned(self):
        log = validate_log(
            [
                event("J01", "2026-03-01", "mate"),
                event("harness-cable-j55", "2026-03-01", "mate"),
            ]
        )
        lines = render_control_table(connector_rows(log))
        used_column = lines[0].index("USED")
        self.assertEqual(lines[1][used_column], "1")
        self.assertEqual(lines[2][used_column], "1")

    def test_table_refuses_a_malformed_row(self):
        with self.assertRaises(ValueError):
            render_control_table([{"connector": "j01"}])


class AssessmentTests(unittest.TestCase):
    def test_conformant_log_has_no_findings(self):
        result = assess_demating_logbook(PAIR, {"J01": 5})
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["verdict"], "cycle-control-conformant")
        self.assertEqual(result["connector_count"], 1)
        self.assertEqual(result["event_count"], 2)

    def test_exhausted_connector_is_a_finding(self):
        entries = []
        for day in range(1, 4):
            entries.append(event("J01", "2026-03-0%d" % day, "mate"))
            entries.append(event("J01", "2026-03-0%d" % day, "demate"))
        result = assess_demating_logbook(entries, {"J01": 2})
        self.assertEqual(result["verdict"], "cycle-control-nonconformant")
        self.assertTrue(any("maximum of 2" in f for f in result["findings"]))

    def test_last_allowed_cycle_is_reported(self):
        result = assess_demating_logbook(PAIR, {"J01": 1})
        self.assertTrue(any("last allowed" in f for f in result["findings"]))

    def test_undeclared_maximum_is_reported(self):
        result = assess_demating_logbook(PAIR)
        self.assertTrue(any("no declared" in f for f in result["findings"]))

    def test_unexpected_final_state_is_reported(self):
        result = assess_demating_logbook(
            PAIR, {"J01": 5}, expected_final_state={"J01": "mated"}
        )
        self.assertTrue(any("is left demated" in f for f in result["findings"]))

    def test_expected_state_must_be_a_known_state(self):
        with self.assertRaises(ValueError):
            assess_demating_logbook(PAIR, {"J01": 5}, expected_final_state={"J01": "stowed"})

    def test_rendered_table_is_returned_with_the_assessment(self):
        result = assess_demating_logbook(PAIR, {"J01": 5})
        self.assertTrue(result["rendered"][0].startswith("CONNECTOR"))


if __name__ == "__main__":
    unittest.main()
