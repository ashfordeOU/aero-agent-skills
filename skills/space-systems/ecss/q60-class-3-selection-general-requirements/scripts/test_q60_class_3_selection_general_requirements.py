"""Contract tests for the clause 6.2.1 Class 3 selection readiness logic."""

import unittest

from q60_class_3_selection_general_requirements_logic import (
    PREREQUISITE_NAMES,
    PREREQUISITES,
    READINESS_TOLERANCE,
    SELECTION_STATES,
    assess_class_3_selection_readiness,
    blocking_open,
    declare_prerequisite,
    next_prerequisite_to_close,
    normalise_state,
    prerequisite_is_blocking,
    prerequisite_weight,
    readiness_index,
    validate_candidate_id,
)

BLOCKING = [name for name, _w, blocking in PREREQUISITES if blocking]
NON_BLOCKING = [name for name, _w, blocking in PREREQUISITES if not blocking]


def all_closed(**overrides):
    """Return a declaration ledger with every prerequisite closed."""
    ledger = {name: {"state": "closed"} for name in PREREQUISITE_NAMES}
    ledger.update(overrides)
    return ledger


def spec(**overrides):
    """Return one assessment spec with optional overrides."""
    base = {"candidate": {"part_id": "RES-0603-10K"}, "prerequisites": all_closed()}
    base.update(overrides)
    return base


class CandidateTests(unittest.TestCase):
    def test_surrounding_space_is_stripped(self):
        self.assertEqual(validate_candidate_id("  RES-1 "), "RES-1")

    def test_blank_candidate_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate_id("   ")

    def test_non_string_candidate_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate_id(603)


class LedgerShapeTests(unittest.TestCase):
    def test_every_prerequisite_carries_a_positive_weight(self):
        for name in PREREQUISITE_NAMES:
            self.assertGreater(prerequisite_weight(name), 0)

    def test_blocking_flag_is_a_boolean(self):
        for name in PREREQUISITE_NAMES:
            self.assertIsInstance(prerequisite_is_blocking(name), bool)

    def test_ledger_holds_both_kinds(self):
        self.assertTrue(BLOCKING)
        self.assertTrue(NON_BLOCKING)

    def test_weight_lookup_ignores_case(self):
        name = PREREQUISITE_NAMES[0]
        self.assertEqual(prerequisite_weight(name.upper()), prerequisite_weight(name))

    def test_unknown_prerequisite_weight_rejected(self):
        with self.assertRaises(ValueError):
            prerequisite_weight("vibes-assessment")

    def test_unknown_prerequisite_blocking_rejected(self):
        with self.assertRaises(ValueError):
            prerequisite_is_blocking("vibes-assessment")

    def test_state_lookup_ignores_case(self):
        self.assertEqual(normalise_state("CLOSED"), "closed")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalise_state("mostly-done")

    def test_declared_states_are_the_three_expected(self):
        self.assertEqual(sorted(SELECTION_STATES), ["closed", "not-applicable", "open"])


class DeclarationTests(unittest.TestCase):
    def test_closed_prerequisite_is_satisfied(self):
        record = declare_prerequisite(BLOCKING[0], {"state": "closed"})
        self.assertTrue(record["satisfied"])
        self.assertEqual(record["disposition"], "closed")

    def test_undeclared_prerequisite_stands_open(self):
        record = declare_prerequisite(BLOCKING[0], None)
        self.assertFalse(record["satisfied"])
        self.assertEqual(record["disposition"], "prerequisite-not-declared")

    def test_entry_without_a_state_stands_open(self):
        record = declare_prerequisite(BLOCKING[0], {"justification": "later"})
        self.assertEqual(record["disposition"], "prerequisite-not-declared")

    def test_open_blocking_prerequisite_is_named_as_blocking(self):
        record = declare_prerequisite(BLOCKING[0], {"state": "open"})
        self.assertEqual(record["disposition"], "blocking-prerequisite-open")

    def test_open_non_blocking_prerequisite_is_plain_open(self):
        record = declare_prerequisite(NON_BLOCKING[0], {"state": "open"})
        self.assertEqual(record["disposition"], "prerequisite-open")

    def test_justified_not_applicable_leaves_the_denominator(self):
        record = declare_prerequisite(
            NON_BLOCKING[0],
            {"state": "not-applicable", "justification": "no heritage build exists"},
        )
        self.assertFalse(record["applies"])
        self.assertEqual(record["disposition"], "not-applicable-justified")

    def test_unjustified_not_applicable_still_applies(self):
        record = declare_prerequisite(NON_BLOCKING[0], {"state": "not-applicable"})
        self.assertTrue(record["applies"])
        self.assertEqual(record["disposition"], "not-applicable-without-justification")

    def test_blank_justification_does_not_count(self):
        record = declare_prerequisite(
            NON_BLOCKING[0], {"state": "not-applicable", "justification": "  "}
        )
        self.assertEqual(record["disposition"], "not-applicable-without-justification")

    def test_waiver_on_a_blocking_prerequisite_is_refused(self):
        record = declare_prerequisite(
            BLOCKING[0],
            {"state": "open", "waiver": {"granted": True, "rationale": "schedule"}},
        )
        self.assertFalse(record["satisfied"])
        self.assertEqual(record["disposition"], "waiver-on-blocking-prerequisite")

    def test_waiver_on_a_non_blocking_prerequisite_closes_it(self):
        record = declare_prerequisite(
            NON_BLOCKING[0],
            {"state": "open", "waiver": {"granted": True, "rationale": "accepted risk"}},
        )
        self.assertTrue(record["satisfied"])
        self.assertEqual(record["disposition"], "closed-under-waiver")

    def test_waiver_without_a_rationale_closes_nothing(self):
        record = declare_prerequisite(
            NON_BLOCKING[0], {"state": "open", "waiver": {"granted": True}}
        )
        self.assertFalse(record["satisfied"])
        self.assertEqual(record["disposition"], "waiver-without-rationale")

    def test_ungranted_waiver_is_ignored(self):
        record = declare_prerequisite(
            NON_BLOCKING[0],
            {"state": "open", "waiver": {"granted": False, "rationale": "asked"}},
        )
        self.assertEqual(record["disposition"], "prerequisite-open")

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            declare_prerequisite(BLOCKING[0], "closed")

    def test_non_mapping_waiver_rejected(self):
        with self.assertRaises(ValueError):
            declare_prerequisite(NON_BLOCKING[0], {"state": "open", "waiver": "granted"})

    def test_unknown_prerequisite_declaration_rejected(self):
        with self.assertRaises(ValueError):
            declare_prerequisite("vibes-assessment", {"state": "closed"})


class IndexTests(unittest.TestCase):
    def _records(self, ledger):
        return [declare_prerequisite(name, ledger.get(name)) for name in PREREQUISITE_NAMES]

    def test_fully_closed_ledger_reads_one(self):
        self.assertAlmostEqual(readiness_index(self._records(all_closed())), 1.0, places=9)

    def test_index_is_weighted_not_counted(self):
        heavy = max(PREREQUISITE_NAMES, key=prerequisite_weight)
        light = min(PREREQUISITE_NAMES, key=prerequisite_weight)
        self.assertNotEqual(prerequisite_weight(heavy), prerequisite_weight(light))
        heavy_open = readiness_index(
            self._records(all_closed(**{heavy: {"state": "open"}}))
        )
        light_open = readiness_index(
            self._records(all_closed(**{light: {"state": "open"}}))
        )
        self.assertLess(heavy_open, light_open)

    def test_justified_not_applicable_leaves_the_index_whole(self):
        ledger = all_closed(
            **{
                NON_BLOCKING[0]: {
                    "state": "not-applicable",
                    "justification": "no heritage build exists",
                }
            }
        )
        self.assertAlmostEqual(readiness_index(self._records(ledger)), 1.0, places=9)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            readiness_index([])

    def test_record_without_applies_rejected(self):
        with self.assertRaises(ValueError):
            readiness_index([{"weight": 1, "satisfied": True}])

    def test_everything_not_applicable_is_rejected(self):
        ledger = {
            name: {"state": "not-applicable", "justification": "out of scope"}
            for name in PREREQUISITE_NAMES
        }
        with self.assertRaises(ValueError):
            readiness_index(self._records(ledger))


class NextStepTests(unittest.TestCase):
    def _records(self, ledger):
        return [declare_prerequisite(name, ledger.get(name)) for name in PREREQUISITE_NAMES]

    def test_blocking_item_is_named_before_a_heavier_non_blocking_one(self):
        light_blocker = min(BLOCKING, key=prerequisite_weight)
        heavy_non_blocker = max(NON_BLOCKING, key=prerequisite_weight)
        ledger = all_closed(
            **{
                light_blocker: {"state": "open"},
                heavy_non_blocker: {"state": "open"},
            }
        )
        self.assertEqual(next_prerequisite_to_close(self._records(ledger)), light_blocker)

    def test_heavier_item_wins_between_two_of_a_kind(self):
        heavy = max(NON_BLOCKING, key=prerequisite_weight)
        light = min(NON_BLOCKING, key=prerequisite_weight)
        ledger = all_closed(**{heavy: {"state": "open"}, light: {"state": "open"}})
        self.assertEqual(next_prerequisite_to_close(self._records(ledger)), heavy)

    def test_nothing_open_returns_none(self):
        self.assertIsNone(next_prerequisite_to_close(self._records(all_closed())))

    def test_blocking_open_lists_only_blockers(self):
        ledger = all_closed(
            **{BLOCKING[0]: {"state": "open"}, NON_BLOCKING[0]: {"state": "open"}}
        )
        self.assertEqual(blocking_open(self._records(ledger)), (BLOCKING[0],))

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            blocking_open("records")


class AssessmentTests(unittest.TestCase):
    def test_fully_closed_selection_may_proceed(self):
        result = assess_class_3_selection_readiness(spec())
        self.assertTrue(result["ready_for_procurement"])
        self.assertEqual(result["verdict"], "proceed-to-procurement")
        self.assertEqual(result["findings"], [])

    def test_open_blocker_holds_the_purchase_order(self):
        result = assess_class_3_selection_readiness(
            spec(prerequisites=all_closed(**{BLOCKING[0]: {"state": "open"}}))
        )
        self.assertEqual(result["verdict"], "hold")
        self.assertEqual(result["blocking_open"], (BLOCKING[0],))

    def test_undeclared_prerequisite_is_reported_not_assumed_closed(self):
        ledger = all_closed()
        del ledger[NON_BLOCKING[0]]
        result = assess_class_3_selection_readiness(spec(prerequisites=ledger))
        dispositions = {f["disposition"] for f in result["findings"]}
        self.assertIn("prerequisite-not-declared", dispositions)

    def test_waiver_on_a_blocker_is_the_worst_finding(self):
        ledger = all_closed(
            **{
                BLOCKING[0]: {
                    "state": "open",
                    "waiver": {"granted": True, "rationale": "schedule"},
                }
            }
        )
        result = assess_class_3_selection_readiness(spec(prerequisites=ledger))
        self.assertEqual(
            result["findings"][0]["disposition"], "waiver-on-blocking-prerequisite"
        )

    def test_closed_under_waiver_is_still_reported(self):
        ledger = all_closed(
            **{
                NON_BLOCKING[0]: {
                    "state": "open",
                    "waiver": {"granted": True, "rationale": "accepted risk"},
                }
            }
        )
        result = assess_class_3_selection_readiness(spec(prerequisites=ledger))
        dispositions = {f["disposition"] for f in result["findings"]}
        self.assertIn("closed-under-waiver", dispositions)
        self.assertAlmostEqual(result["readiness_index"], 1.0, places=9)

    def test_findings_are_ranked_worst_first(self):
        ledger = all_closed(
            **{
                BLOCKING[0]: {"state": "open"},
                NON_BLOCKING[0]: {"state": "not-applicable"},
            }
        )
        result = assess_class_3_selection_readiness(spec(prerequisites=ledger))
        severities = [f["severity"] for f in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_next_to_close_is_returned(self):
        ledger = all_closed(**{BLOCKING[1]: {"state": "open"}})
        result = assess_class_3_selection_readiness(spec(prerequisites=ledger))
        self.assertEqual(result["next_to_close"], BLOCKING[1])

    def test_lower_required_readiness_still_respects_a_blocker(self):
        ledger = all_closed(**{BLOCKING[0]: {"state": "open"}})
        result = assess_class_3_selection_readiness(
            spec(prerequisites=ledger, required_readiness=0.1)
        )
        self.assertFalse(result["ready_for_procurement"])

    def test_exactly_met_readiness_sits_on_the_agreed_level(self):
        light = min(NON_BLOCKING, key=prerequisite_weight)
        ledger = all_closed(**{light: {"state": "open"}})
        result = assess_class_3_selection_readiness(spec(prerequisites=ledger))
        total = sum(prerequisite_weight(n) for n in PREREQUISITE_NAMES)
        expected = (total - prerequisite_weight(light)) / total
        self.assertAlmostEqual(result["readiness_index"], expected, places=9)

    def test_candidate_identifier_is_carried_through(self):
        result = assess_class_3_selection_readiness(spec())
        self.assertEqual(result["part_id"], "RES-0603-10K")

    def test_unknown_prerequisite_in_the_ledger_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_selection_readiness(
                spec(prerequisites=all_closed(**{"vibes-assessment": {"state": "closed"}}))
            )

    def test_missing_prerequisites_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_selection_readiness({"candidate": {"part_id": "RES-1"}})

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_selection_readiness(spec(candidate=["RES-1"]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_selection_readiness(["candidate"])

    def test_out_of_range_required_readiness_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_selection_readiness(spec(required_readiness=2.0))

    def test_boolean_required_readiness_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_selection_readiness(spec(required_readiness=True))

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(READINESS_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
