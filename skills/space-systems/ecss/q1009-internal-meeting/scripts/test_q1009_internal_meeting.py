"""Contract tests for the clause 5.2.2.1 internal review-board sitting logic."""

import unittest

from q1009_internal_meeting_logic import (
    DEFAULT_QUORUM_FRACTION,
    MANDATORY_BOARD_FUNCTIONS,
    QUORUM_TOLERANCE,
    REQUIRED_PACKAGE_ITEMS,
    absent_mandatory_functions,
    agenda_admissibility,
    assess_internal_meeting,
    decision_gaps,
    minutes_status,
    normalize_function,
    package_gaps,
    quorum_ratio,
    quorum_status,
    validate_board,
    validate_member,
    voting_counts,
)


def member(function, present=True, voting=True):
    return {"function": function, "present": present, "voting": voting}


FULL_BOARD = [
    member("chair"),
    member("product-assurance"),
    member("design-engineering"),
    member("production"),
    member("configuration-management", voting=False),
]

FULL_PACKAGE = list(REQUIRED_PACKAGE_ITEMS)


def decision(item, **over):
    record = {
        "agenda_item": item,
        "disposition": "rework",
        "rationale": "departure removed by the released rework procedure",
        "owner": "production-lead",
        "due_day": 12,
    }
    record.update(over)
    return record


class NormalizeFunctionTests(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(normalize_function("Design Engineering"), "design-engineering")

    def test_collapses_inner_whitespace(self):
        self.assertEqual(normalize_function("  product   assurance "), "product-assurance")

    def test_underscores_become_hyphens(self):
        self.assertEqual(normalize_function("cause_analysis"), "cause-analysis")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_function("   ")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_function(7)


class BoardValidationTests(unittest.TestCase):
    def test_roster_returns_one_record_per_member(self):
        self.assertEqual(len(validate_board(FULL_BOARD)), 5)

    def test_member_keys_normalised(self):
        record = validate_member({"function": "Chair", "present": True, "voting": True})
        self.assertEqual(record, {"function": "chair", "present": True, "voting": True})

    def test_missing_member_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_member({"function": "chair", "present": True})

    def test_non_boolean_presence_rejected(self):
        with self.assertRaises(ValueError):
            validate_member({"function": "chair", "present": 1, "voting": True})

    def test_duplicate_board_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_board(FULL_BOARD + [member("Chair")])

    def test_empty_roster_rejected(self):
        with self.assertRaises(ValueError):
            validate_board([])

    def test_non_sequence_roster_rejected(self):
        with self.assertRaises(ValueError):
            validate_board({"function": "chair"})


class MandatoryFunctionTests(unittest.TestCase):
    def test_full_board_has_no_absentees(self):
        self.assertEqual(absent_mandatory_functions(FULL_BOARD), ())

    def test_absent_member_is_not_a_sitting_function(self):
        roster = [member("chair"), member("product-assurance", present=False),
                  member("design-engineering"), member("production")]
        self.assertEqual(absent_mandatory_functions(roster), ("product-assurance",))

    def test_every_mandatory_function_reported_when_only_chair_sits(self):
        roster = [member("chair")] + [
            member(f, present=False) for f in MANDATORY_BOARD_FUNCTIONS[1:]
        ]
        self.assertEqual(absent_mandatory_functions(roster), MANDATORY_BOARD_FUNCTIONS[1:])

    def test_advisory_attendance_still_counts_as_sitting(self):
        roster = [member("chair"), member("product-assurance", voting=False),
                  member("design-engineering"), member("production")]
        self.assertEqual(absent_mandatory_functions(roster), ())


class QuorumTests(unittest.TestCase):
    def test_voting_counts_exclude_advisory_members(self):
        self.assertEqual(voting_counts(FULL_BOARD), (4, 4))

    def test_absent_voting_member_lowers_the_attending_count(self):
        roster = list(FULL_BOARD)
        roster[3] = member("production", present=False)
        self.assertEqual(voting_counts(roster), (3, 4))

    def test_board_without_voting_members_rejected(self):
        with self.assertRaises(ValueError):
            voting_counts([member("chair", voting=False)])

    def test_ratio_is_the_attending_share(self):
        roster = list(FULL_BOARD)
        roster[3] = member("production", present=False)
        self.assertAlmostEqual(quorum_ratio(roster), 0.75, places=9)

    def test_exactly_half_meets_a_half_quorum(self):
        roster = [member("chair"), member("product-assurance"),
                  member("design-engineering", present=False),
                  member("production", present=False)]
        status = quorum_status(roster, DEFAULT_QUORUM_FRACTION)
        self.assertAlmostEqual(status["ratio"], DEFAULT_QUORUM_FRACTION, places=9)
        self.assertTrue(status["fraction_met"])

    def test_two_thirds_fraction_rejects_a_half_attendance(self):
        roster = [member("chair"), member("product-assurance"),
                  member("design-engineering", present=False),
                  member("production", present=False)]
        self.assertFalse(quorum_status(roster, 2.0 / 3.0)["fraction_met"])

    def test_quorum_tolerance_is_small_and_positive(self):
        self.assertGreater(QUORUM_TOLERANCE, 0.0)
        self.assertLess(QUORUM_TOLERANCE, 1e-6)

    def test_fraction_met_but_mandatory_absent_is_not_a_quorum(self):
        roster = [member("chair"), member("product-assurance"),
                  member("design-engineering"), member("production", present=False)]
        status = quorum_status(roster)
        self.assertTrue(status["fraction_met"])
        self.assertFalse(status["quorum_met"])
        self.assertEqual(status["absent_mandatory_functions"], ("production",))

    def test_full_board_makes_quorum(self):
        self.assertTrue(quorum_status(FULL_BOARD)["quorum_met"])

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            quorum_status(FULL_BOARD, 0.0)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            quorum_status(FULL_BOARD, 1.5)

    def test_non_numeric_fraction_rejected(self):
        with self.assertRaises(ValueError):
            quorum_status(FULL_BOARD, "half")


class PackageTests(unittest.TestCase):
    def test_complete_package_has_no_gaps(self):
        self.assertEqual(package_gaps(FULL_PACKAGE), ())

    def test_missing_cause_analysis_reported(self):
        partial = [i for i in FULL_PACKAGE if i != "cause-analysis"]
        self.assertEqual(package_gaps(partial), ("cause-analysis",))

    def test_mapping_form_with_false_flag_counts_as_missing(self):
        supplied = {i: True for i in FULL_PACKAGE}
        supplied["effectivity-list"] = False
        self.assertEqual(package_gaps(supplied), ("effectivity-list",))

    def test_free_text_item_names_are_normalised(self):
        self.assertEqual(package_gaps(["Nonconformance Report"] + FULL_PACKAGE[1:]), ())

    def test_gaps_reported_in_package_order(self):
        self.assertEqual(package_gaps([]), REQUIRED_PACKAGE_ITEMS)

    def test_non_collection_package_rejected(self):
        with self.assertRaises(ValueError):
            package_gaps("nonconformance-report")


class AgendaTests(unittest.TestCase):
    def test_complete_item_is_admissible(self):
        records = agenda_admissibility([{"item": "ncr-0101", "package": FULL_PACKAGE}])
        self.assertTrue(records[0]["admissible"])

    def test_incomplete_item_is_inadmissible_with_named_gaps(self):
        records = agenda_admissibility(
            [{"item": "ncr-0102", "package": FULL_PACKAGE[:-1]}]
        )
        self.assertFalse(records[0]["admissible"])
        self.assertEqual(records[0]["package_gaps"], ("proposed-disposition",))

    def test_agenda_order_preserved(self):
        records = agenda_admissibility(
            [{"item": "ncr-0103", "package": FULL_PACKAGE},
             {"item": "ncr-0101", "package": FULL_PACKAGE}]
        )
        self.assertEqual([r["item"] for r in records], ["ncr-0103", "ncr-0101"])

    def test_duplicate_agenda_item_rejected(self):
        with self.assertRaises(ValueError):
            agenda_admissibility(
                [{"item": "ncr-0101", "package": FULL_PACKAGE},
                 {"item": "NCR 0101", "package": FULL_PACKAGE}]
            )

    def test_empty_agenda_rejected(self):
        with self.assertRaises(ValueError):
            agenda_admissibility([])

    def test_agenda_item_missing_package_key_rejected(self):
        with self.assertRaises(ValueError):
            agenda_admissibility([{"item": "ncr-0101"}])


class DecisionRecordTests(unittest.TestCase):
    def test_complete_record_has_no_gaps(self):
        self.assertEqual(decision_gaps(decision("ncr-0101")), ())

    def test_missing_owner_reported(self):
        self.assertEqual(decision_gaps(decision("ncr-0101", owner=None)), ("owner",))

    def test_blank_rationale_counts_as_missing(self):
        self.assertEqual(decision_gaps(decision("ncr-0101", rationale="   ")), ("rationale",))

    def test_non_mapping_decision_rejected(self):
        with self.assertRaises(ValueError):
            decision_gaps(["ncr-0101"])

    def test_due_day_zero_is_a_real_value_not_a_gap(self):
        self.assertEqual(decision_gaps(decision("ncr-0101", due_day=0)), ())


class MinutesTests(unittest.TestCase):
    def test_heard_item_with_record_closes_the_minute(self):
        records = agenda_admissibility([{"item": "ncr-0101", "package": FULL_PACKAGE}])
        status = minutes_status(records, [decision("ncr-0101")])
        self.assertTrue(status["minutes_complete"])
        self.assertEqual(status["heard"], ["ncr-0101"])

    def test_heard_item_without_record_is_an_open_minute(self):
        records = agenda_admissibility([{"item": "ncr-0101", "package": FULL_PACKAGE}])
        status = minutes_status(records, [])
        self.assertEqual(status["open_minutes"][0]["reason"], "no-decision-recorded")

    def test_deferred_item_needs_no_decision(self):
        records = agenda_admissibility([{"item": "ncr-0102", "package": []}])
        status = minutes_status(records, [])
        self.assertEqual(status["deferred"], ["ncr-0102"])
        self.assertTrue(status["minutes_complete"])

    def test_incomplete_record_names_the_missing_fields(self):
        records = agenda_admissibility([{"item": "ncr-0101", "package": FULL_PACKAGE}])
        status = minutes_status(records, [decision("ncr-0101", due_day=None)])
        self.assertEqual(status["open_minutes"][0]["missing"], ("due_day",))

    def test_two_records_for_one_item_rejected(self):
        records = agenda_admissibility([{"item": "ncr-0101", "package": FULL_PACKAGE}])
        with self.assertRaises(ValueError):
            minutes_status(records, [decision("ncr-0101"), decision("NCR 0101")])

    def test_record_for_a_deferred_item_is_unattached(self):
        records = agenda_admissibility([{"item": "ncr-0102", "package": []}])
        status = minutes_status(records, [decision("ncr-0102")])
        self.assertIn("ncr-0102", status["unattached_decisions"])

    def test_non_sequence_decisions_rejected(self):
        records = agenda_admissibility([{"item": "ncr-0101", "package": FULL_PACKAGE}])
        with self.assertRaises(ValueError):
            minutes_status(records, decision("ncr-0101"))


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "board": list(FULL_BOARD),
            "agenda": [{"item": "ncr-0101", "package": FULL_PACKAGE}],
            "decisions": [decision("ncr-0101")],
        }
        spec.update(over)
        return spec

    def test_clean_sitting_is_valid(self):
        result = assess_internal_meeting(self._spec())
        self.assertTrue(result["sitting_valid"])
        self.assertTrue(result["agenda_cleared"])
        self.assertEqual(result["findings"], [])

    def test_absent_mandatory_function_invalidates_the_sitting(self):
        board = list(FULL_BOARD)
        board[2] = member("design-engineering", present=False)
        result = assess_internal_meeting(self._spec(board=board))
        self.assertFalse(result["sitting_valid"])
        self.assertTrue(any("design-engineering" in f for f in result["findings"]))

    def test_incomplete_package_defers_the_item_and_is_reported(self):
        result = assess_internal_meeting(
            self._spec(agenda=[{"item": "ncr-0102", "package": FULL_PACKAGE[:3]}],
                       decisions=[])
        )
        self.assertFalse(result["agenda_cleared"])
        self.assertTrue(result["sitting_valid"])
        self.assertEqual(result["minutes"]["deferred"], ["ncr-0102"])
        self.assertTrue(any("deferred" in f for f in result["findings"]))

    def test_heard_item_without_a_decision_fails_the_sitting(self):
        result = assess_internal_meeting(self._spec(decisions=[]))
        self.assertFalse(result["sitting_valid"])
        self.assertTrue(any("no decision recorded" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["agenda"]
        with self.assertRaises(ValueError):
            assess_internal_meeting(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_internal_meeting(["board"])

    def test_stricter_quorum_fraction_can_fail_a_full_sitting_short_of_it(self):
        board = list(FULL_BOARD)
        board[3] = member("production", present=False)
        result = assess_internal_meeting(self._spec(board=board, quorum_fraction=0.9))
        self.assertFalse(result["quorum"]["fraction_met"])


if __name__ == "__main__":
    unittest.main()
