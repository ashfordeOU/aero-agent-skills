#!/usr/bin/env python3
"""Contract test for blocking diode acceptance testing, general.

Walks the clause workflow step by step: the policy that declares which
activities are carried by every unit and which are drawn on a sample, the
per-unit grading over the every-unit set only, the four record states and
the ranked unit verdict, each sampled activity graded over the population
it speaks for, the per-population roll-up with its cleared share, the
detection of a population absent from the lot or present with an empty
record, and the single lot verdict. This is the gate 3 review evidence
for the leaf.
"""

import copy
import unittest

from e2008_blocking_diode_acceptance_general_logic import (
    EVERY_UNIT_ACTIVITIES,
    LOT_ACCEPTED,
    LOT_INCOMPLETE,
    LOT_POPULATION_UNTOUCHED,
    LOT_RANK,
    SAMPLED_ACTIVITIES,
    UNIT_CLEAR,
    UNIT_FAILED,
    UNIT_RANK,
    UNIT_UNDOCUMENTED,
    UNIT_UNRUN,
    assess_blocking_diode_acceptance,
    grade_unit,
    population_reach,
    population_summary,
    resolve_policy,
    sampled_activity_coverage,
)

POPULATION_SIZE = 20
DRAWN_PER_POPULATION = 3


def _records(sampled=False, **states):
    record = {name: "passed" for name in EVERY_UNIT_ACTIVITIES}
    if sampled:
        record.update({name: "passed" for name in SAMPLED_ACTIVITIES})
    record.update(states)
    return record


def _units(population, size=POPULATION_SIZE, drawn=DRAWN_PER_POPULATION):
    rows = []
    for index in range(size):
        rows.append(
            {
                "unit_id": "%s-%03d" % (population[:3].upper(), index + 1),
                "population": population,
                "records": _records(sampled=index < drawn),
            }
        )
    return rows


SOUND_LOT = {
    "lot_id": "BD-LOT-2026-11",
    "units": _units("delivery") + _units("qualification"),
}


def _lot(**overrides):
    record = copy.deepcopy(SOUND_LOT)
    record.update(overrides)
    return record


def _find(units, unit_id):
    for unit in units:
        if unit["unit_id"] == unit_id:
            return unit
    raise AssertionError("no unit %r in the lot" % unit_id)


class PolicyTests(unittest.TestCase):
    def test_the_default_policy_splits_the_activities_by_basis(self):
        settings = resolve_policy()
        self.assertEqual(settings["every_unit_activities"], EVERY_UNIT_ACTIVITIES)
        self.assertEqual(settings["sampled_activities"], SAMPLED_ACTIVITIES)

    def test_an_activity_on_both_bases_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"sampled_activities": ("visual-inspection",)})

    def test_a_policy_with_no_every_unit_activity_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"every_unit_activities": ()})

    def test_a_share_outside_zero_to_one_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_sample_share": 1.5})

    def test_a_non_boolean_failure_position_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"dispositioned_failure_closes_lot": "maybe"})

    def test_an_unknown_activity_name_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"sampled_activities": ("bend-test",)})


class UnitGradingTests(unittest.TestCase):
    def test_a_fully_recorded_unit_is_clear(self):
        row = grade_unit(
            {"unit_id": "D-1", "population": "delivery", "records": _records()}
        )
        self.assertEqual(row["verdict"], UNIT_CLEAR)
        self.assertEqual(row["absent"], [])

    def test_a_missing_every_unit_record_reads_as_absent(self):
        record = _records()
        del record["reverse-leakage-measurement"]
        row = grade_unit(
            {"unit_id": "D-2", "population": "delivery", "records": record}
        )
        self.assertEqual(row["verdict"], UNIT_UNDOCUMENTED)
        self.assertEqual(row["absent"], ["reverse-leakage-measurement"])

    def test_an_absent_state_is_not_a_pass(self):
        row = grade_unit(
            {
                "unit_id": "D-3",
                "population": "delivery",
                "records": _records(**{"visual-inspection": "absent"}),
            }
        )
        self.assertEqual(row["verdict"], UNIT_UNDOCUMENTED)

    def test_unrun_work_is_a_schedule_item_not_a_gap(self):
        row = grade_unit(
            {
                "unit_id": "D-4",
                "population": "delivery",
                "records": _records(**{"forward-voltage-measurement": "not-run"}),
            }
        )
        self.assertEqual(row["verdict"], UNIT_UNRUN)
        self.assertEqual(row["not_run"], ["forward-voltage-measurement"])

    def test_a_recorded_failure_is_its_own_state(self):
        row = grade_unit(
            {
                "unit_id": "D-5",
                "population": "delivery",
                "records": _records(**{"reverse-leakage-measurement": "failed"}),
            }
        )
        self.assertEqual(row["verdict"], UNIT_FAILED)
        self.assertEqual(row["failed"], ["reverse-leakage-measurement"])

    def test_absence_outranks_an_unrun_item_and_a_failure(self):
        row = grade_unit(
            {
                "unit_id": "D-6",
                "population": "delivery",
                "records": {
                    "forward-voltage-measurement": "failed",
                    "reverse-leakage-measurement": "not-run",
                },
            }
        )
        self.assertEqual(row["verdict"], UNIT_UNDOCUMENTED)

    def test_a_unit_never_drawn_owes_no_sampled_record(self):
        row = grade_unit(
            {"unit_id": "D-7", "population": "delivery", "records": _records()}
        )
        self.assertEqual(row["verdict"], UNIT_CLEAR)
        self.assertEqual(row["drawn_for"], [])

    def test_a_drawn_unit_reports_what_it_was_drawn_for(self):
        row = grade_unit(
            {
                "unit_id": "D-8",
                "population": "delivery",
                "records": _records(sampled=True),
            }
        )
        self.assertEqual(row["drawn_for"], sorted(SAMPLED_ACTIVITIES))

    def test_an_unknown_population_is_refused(self):
        with self.assertRaises(ValueError):
            grade_unit(
                {"unit_id": "D-9", "population": "spares", "records": _records()}
            )

    def test_an_activity_outside_the_acceptance_set_is_refused(self):
        with self.assertRaises(ValueError):
            grade_unit(
                {
                    "unit_id": "D-10",
                    "population": "delivery",
                    "records": {"radiation-campaign": "passed"},
                }
            )

    def test_an_unknown_record_state_is_refused(self):
        with self.assertRaises(ValueError):
            grade_unit(
                {
                    "unit_id": "D-11",
                    "population": "delivery",
                    "records": _records(**{"visual-inspection": "waived"}),
                }
            )

    def test_the_unit_rank_puts_an_absent_record_at_the_bottom(self):
        self.assertLess(UNIT_RANK[UNIT_UNDOCUMENTED], UNIT_RANK[UNIT_UNRUN])
        self.assertLess(UNIT_RANK[UNIT_UNRUN], UNIT_RANK[UNIT_FAILED])
        self.assertLess(UNIT_RANK[UNIT_FAILED], UNIT_RANK[UNIT_CLEAR])


class SampledActivityTests(unittest.TestCase):
    def setUp(self):
        self.settings = resolve_policy()
        self.graded = [
            grade_unit(unit, self.settings) for unit in SOUND_LOT["units"]
        ]

    def test_a_sampled_activity_is_graded_over_its_population(self):
        result = sampled_activity_coverage(
            self.graded, "thermal-shock", "delivery", 0.1
        )
        self.assertEqual(result["population_size"], POPULATION_SIZE)
        self.assertEqual(result["drawn"], DRAWN_PER_POPULATION)
        self.assertTrue(result["share_floor_met"])

    def test_a_sample_landing_exactly_on_the_floor_is_accepted(self):
        units = _units("delivery", drawn=2)
        graded = [grade_unit(unit, self.settings) for unit in units]
        result = sampled_activity_coverage(graded, "solderability", "delivery", 0.1)
        self.assertAlmostEqual(result["drawn_share"], 0.1, places=9)
        self.assertTrue(result["share_floor_met"])

    def test_a_sample_under_the_floor_is_reported_short(self):
        units = _units("delivery", drawn=1)
        graded = [grade_unit(unit, self.settings) for unit in units]
        result = sampled_activity_coverage(graded, "seal-leak-test", "delivery", 0.1)
        self.assertAlmostEqual(result["drawn_share"], 0.05, places=9)
        self.assertFalse(result["share_floor_met"])

    def test_a_failure_in_the_sample_names_the_unit(self):
        units = _units("delivery")
        units[0]["records"]["thermal-shock"] = "failed"
        graded = [grade_unit(unit, self.settings) for unit in units]
        result = sampled_activity_coverage(
            graded, "thermal-shock", "delivery", 0.1
        )
        self.assertEqual(result["failed_units"], [units[0]["unit_id"]])

    def test_an_empty_population_has_nothing_to_speak_for(self):
        graded = [
            grade_unit(unit, self.settings) for unit in _units("qualification")
        ]
        with self.assertRaises(ValueError):
            sampled_activity_coverage(graded, "thermal-shock", "delivery", 0.1)


class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.settings = resolve_policy()

    def _graded(self, units):
        return [grade_unit(unit, self.settings) for unit in units]

    def test_a_sound_population_is_wholly_clear(self):
        graded = self._graded(_units("qualification"))
        summary = population_summary(graded, "qualification", self.settings)
        self.assertTrue(summary["present"])
        self.assertAlmostEqual(summary["cleared_share"], 1.0, places=9)
        self.assertFalse(summary["wholly_untouched"])

    def test_a_cleared_share_exactly_on_the_floor_is_accepted(self):
        units = _units("delivery")
        units[-1]["records"]["forward-voltage-measurement"] = "failed"
        summary = population_summary(self._graded(units), "delivery", self.settings)
        self.assertAlmostEqual(summary["cleared_share"], 0.95, places=9)
        self.assertTrue(summary["cleared_floor_met"])

    def test_a_population_with_empty_records_is_wholly_untouched(self):
        units = [
            {"unit_id": "Q-%03d" % n, "population": "qualification", "records": {}}
            for n in range(1, 4)
        ]
        summary = population_summary(
            self._graded(units), "qualification", self.settings
        )
        self.assertTrue(summary["wholly_untouched"])

    def test_an_absent_population_reports_present_false(self):
        graded = self._graded(_units("delivery"))
        summary = population_summary(graded, "qualification", self.settings)
        self.assertFalse(summary["present"])
        self.assertEqual(summary["units"], 0)

    def test_the_weakest_unit_is_the_worst_ranked_one(self):
        units = _units("delivery")
        units[4]["records"] = {}
        summary = population_summary(self._graded(units), "delivery", self.settings)
        self.assertEqual(summary["weakest"], units[4]["unit_id"])

    def test_reach_names_a_population_missing_from_the_lot(self):
        reach = population_reach(self._graded(_units("delivery")))
        self.assertEqual(reach["absent"], ["qualification"])
        self.assertFalse(reach["both_reached"])

    def test_reach_names_a_population_present_with_no_work(self):
        units = _units("delivery") + [
            {"unit_id": "Q-001", "population": "qualification", "records": {}}
        ]
        reach = population_reach(self._graded(units))
        self.assertEqual(reach["untouched"], ["qualification"])
        self.assertFalse(reach["both_reached"])

    def test_reach_is_satisfied_when_both_populations_carry_work(self):
        reach = population_reach(self._graded(SOUND_LOT["units"]))
        self.assertTrue(reach["both_reached"])


class RolledUpLotTests(unittest.TestCase):
    def test_a_sound_lot_accepts_both_populations(self):
        result = assess_blocking_diode_acceptance(_lot())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_lot_without_the_qualification_population_is_untouched(self):
        result = assess_blocking_diode_acceptance(
            _lot(units=_units("delivery"))
        )
        self.assertEqual(result["verdict"], LOT_POPULATION_UNTOUCHED)
        self.assertTrue(any("qualification" in f for f in result["findings"]))

    def test_an_undocumented_unit_leaves_the_lot_incomplete(self):
        lot = _lot()
        _find(lot["units"], "DEL-009")["records"] = {}
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)

    def test_an_unrun_activity_leaves_the_lot_incomplete(self):
        lot = _lot()
        _find(lot["units"], "QUA-012")["records"]["visual-inspection"] = "not-run"
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)

    def test_a_short_sample_leaves_the_lot_incomplete(self):
        lot = _lot(units=_units("delivery", drawn=1) + _units("qualification"))
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)
        self.assertTrue(any("floor" in f for f in result["findings"]))

    def test_a_sampled_failure_speaks_for_the_population(self):
        lot = _lot()
        _find(lot["units"], "DEL-001")["records"]["seal-leak-test"] = "failed"
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)
        self.assertTrue(
            any("speaks for the whole" in f for f in result["findings"])
        )

    def test_one_carried_failure_within_the_floor_still_closes_the_lot(self):
        lot = _lot()
        _find(lot["units"], "DEL-020")["records"][
            "forward-voltage-measurement"
        ] = "failed"
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_ACCEPTED)

    def test_the_same_failure_opens_the_lot_when_policy_says_so(self):
        lot = _lot(policy={"dispositioned_failure_closes_lot": True})
        _find(lot["units"], "DEL-020")["records"][
            "forward-voltage-measurement"
        ] = "failed"
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)

    def test_too_many_carried_failures_break_the_cleared_floor(self):
        lot = _lot()
        for unit_id in ("DEL-018", "DEL-019", "DEL-020"):
            _find(lot["units"], unit_id)["records"][
                "reverse-leakage-measurement"
            ] = "failed"
        result = assess_blocking_diode_acceptance(lot)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)
        self.assertTrue(any("is clear against" in f for f in result["findings"]))

    def test_the_lot_rank_puts_an_untouched_population_at_the_bottom(self):
        self.assertLess(LOT_RANK[LOT_POPULATION_UNTOUCHED], LOT_RANK[LOT_INCOMPLETE])
        self.assertLess(LOT_RANK[LOT_INCOMPLETE], LOT_RANK[LOT_ACCEPTED])

    def test_a_duplicate_unit_identifier_is_refused(self):
        lot = _lot()
        lot["units"] = lot["units"] + [copy.deepcopy(lot["units"][0])]
        with self.assertRaises(ValueError):
            assess_blocking_diode_acceptance(lot)

    def test_an_empty_unit_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_acceptance(_lot(units=[]))

    def test_a_non_mapping_lot_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_acceptance("every diode was inspected")

    def test_a_lot_without_an_identifier_is_refused(self):
        lot = _lot()
        lot["lot_id"] = "   "
        with self.assertRaises(ValueError):
            assess_blocking_diode_acceptance(lot)


if __name__ == "__main__":
    unittest.main()
