#!/usr/bin/env python3
"""Contract test for bare cell acceptance testing, general (offline).

Walks the clause workflow step by step: the cell record validation, the
four record states kept apart, the every-cell activities a cell owes and
the sampled activities it does not, the sampled fraction against the
declared minimum, the two populations summarised separately, the
wholly untested population, the failure policy, and the roll-up into one
lot verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_bare_cell_acceptance_general_logic import (
    CELL_ACCEPTED,
    CELL_FAILED,
    CELL_NOT_RUN,
    CELL_NO_RECORD,
    EVERY_CELL_ACTIVITIES,
    LOT_ACCEPTED,
    LOT_NOT_ACCEPTED,
    OUTCOME_FAILED,
    OUTCOME_NOT_RUN,
    OUTCOME_PASSED,
    SAMPLE_ACTIVITIES,
    assess_bare_cell_acceptance,
    assess_cell,
    resolve_policy,
    sample_activity_coverage,
    summarise_population,
    validate_cell_record,
)


def _cell(cell_id, population="delivery", sampled=(), **overrides):
    records = {a: OUTCOME_PASSED for a in EVERY_CELL_ACTIVITIES}
    for activity in sampled:
        records[activity] = OUTCOME_PASSED
    record = {
        "cell_id": cell_id,
        "population": population,
        "acceptance_records": records,
    }
    record.update(copy.deepcopy(overrides))
    return record


def _lot(delivery=10, qualification=10):
    cells = []
    for index in range(delivery):
        sampled = SAMPLE_ACTIVITIES if index == 0 else ()
        cells.append(_cell("DEL-%02d" % index, "delivery", sampled))
    for index in range(qualification):
        sampled = SAMPLE_ACTIVITIES if index == 0 else ()
        cells.append(_cell("QUA-%02d" % index, "qualification", sampled))
    return {"lot_id": "LOT-7", "cells": cells}


class RecordValidationTests(unittest.TestCase):
    def test_a_sound_record_validates(self):
        record = validate_cell_record(_cell("DEL-00"))
        self.assertEqual(record["population"], "delivery")
        self.assertEqual(len(record["acceptance_records"]), len(EVERY_CELL_ACTIVITIES))

    def test_an_unknown_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell("DEL-00", population="spares"))

    def test_an_activity_outside_the_acceptance_set_rejected(self):
        cell = _cell("DEL-00")
        cell["acceptance_records"]["cell-launch-rehearsal"] = OUTCOME_PASSED
        with self.assertRaises(ValueError):
            validate_cell_record(cell)

    def test_an_unknown_outcome_rejected(self):
        cell = _cell("DEL-00")
        cell["acceptance_records"]["cell-visual-inspection"] = "probably-fine"
        with self.assertRaises(ValueError):
            validate_cell_record(cell)

    def test_an_empty_cell_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell("   "))


class CellVerdictTests(unittest.TestCase):
    def test_a_fully_recorded_cell_is_accepted(self):
        result = assess_cell(_cell("DEL-00"))
        self.assertEqual(result["verdict"], CELL_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_record_ranks_worst(self):
        cell = _cell("DEL-01")
        del cell["acceptance_records"]["cell-visual-inspection"]
        result = assess_cell(cell)
        self.assertEqual(result["verdict"], CELL_NO_RECORD)
        self.assertEqual(result["missing"], ["cell-visual-inspection"])

    def test_an_unrun_activity_is_kept_apart_from_absence(self):
        cell = _cell("DEL-02")
        cell["acceptance_records"]["cell-visual-inspection"] = OUTCOME_NOT_RUN
        result = assess_cell(cell)
        self.assertEqual(result["verdict"], CELL_NOT_RUN)

    def test_a_recorded_failure_is_kept_apart_from_absence(self):
        cell = _cell("DEL-03")
        cell["acceptance_records"]["cell-electrical-performance"] = OUTCOME_FAILED
        result = assess_cell(cell)
        self.assertEqual(result["verdict"], CELL_FAILED)
        self.assertTrue(result["findings"])

    def test_a_cell_never_drawn_into_a_sample_owes_nothing_extra(self):
        result = assess_cell(_cell("DEL-04"))
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["verdict"], CELL_ACCEPTED)


class SampleCoverageTests(unittest.TestCase):
    def _members(self, total, drawn, activity, outcome=OUTCOME_PASSED):
        members = []
        for index in range(total):
            cell = _cell("DEL-%02d" % index)
            if index < drawn:
                cell["acceptance_records"][activity] = outcome
            members.append(cell)
        return members

    def test_a_sample_exactly_on_the_declared_fraction_is_accepted(self):
        activity = SAMPLE_ACTIVITIES[0]
        result = sample_activity_coverage(
            self._members(10, 1, activity), activity, 0.10
        )
        self.assertAlmostEqual(result["sampled_fraction"], 0.10, places=9)
        self.assertTrue(result["meets_sample_fraction"])

    def test_a_thin_sample_is_reported(self):
        activity = SAMPLE_ACTIVITIES[1]
        result = sample_activity_coverage(
            self._members(20, 1, activity), activity, 0.10
        )
        self.assertFalse(result["meets_sample_fraction"])
        self.assertTrue(result["findings"])

    def test_a_sampled_failure_speaks_for_the_lot(self):
        activity = SAMPLE_ACTIVITIES[2]
        result = sample_activity_coverage(
            self._members(10, 2, activity, OUTCOME_FAILED), activity, 0.10
        )
        self.assertEqual(result["failed"], 2)
        self.assertTrue(result["findings"])

    def test_an_every_cell_activity_is_not_a_sampled_one(self):
        with self.assertRaises(ValueError):
            sample_activity_coverage(
                self._members(10, 1, SAMPLE_ACTIVITIES[0]),
                "cell-visual-inspection",
                0.10,
            )

    def test_an_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            sample_activity_coverage([], SAMPLE_ACTIVITIES[0], 0.10)


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertAlmostEqual(settings["min_sample_fraction"], 0.10, places=12)
        self.assertFalse(settings["carry_dispositioned_failure"])

    def test_a_sample_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_sample_fraction": 1.5})

    def test_a_zero_sample_fraction_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_sample_fraction": 0.0})

    def test_a_non_boolean_failure_policy_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"carry_dispositioned_failure": "sometimes"})


class PopulationTests(unittest.TestCase):
    def test_each_population_is_summarised_separately(self):
        cells = _lot()["cells"]
        delivery = summarise_population(cells, "delivery")
        qualification = summarise_population(cells, "qualification")
        self.assertEqual(delivery["cells"], 10)
        self.assertEqual(qualification["cells"], 10)
        self.assertAlmostEqual(delivery["accepted_share"], 1.0, places=12)

    def test_an_absent_population_reports_as_absent(self):
        cells = [_cell("DEL-00", "delivery", SAMPLE_ACTIVITIES)]
        summary = summarise_population(cells, "qualification")
        self.assertFalse(summary["present"])
        self.assertEqual(summary["cells"], 0)

    def test_a_wholly_untested_population_is_named_as_a_decision(self):
        cells = [_cell("DEL-00", "delivery", SAMPLE_ACTIVITIES)]
        for index in range(3):
            cells.append(
                {
                    "cell_id": "QUA-%02d" % index,
                    "population": "qualification",
                    "acceptance_records": {},
                }
            )
        summary = summarise_population(cells, "qualification")
        self.assertTrue(summary["wholly_untested"])
        self.assertTrue(summary["findings"])


class LotRollUpTests(unittest.TestCase):
    def test_a_sound_lot_is_accepted(self):
        result = assess_bare_cell_acceptance(_lot())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_lot_with_no_qualification_cells_is_not_accepted(self):
        case = _lot(delivery=10, qualification=0)
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertEqual(result["missing_populations"], ["qualification"])

    def test_untested_qualification_cells_fail_a_clean_delivery_lot(self):
        case = _lot()
        for cell in case["cells"]:
            if cell["population"] == "qualification":
                cell["acceptance_records"] = {}
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertTrue(result["populations"]["qualification"]["wholly_untested"])
        self.assertTrue(result["populations"]["delivery"]["meets_every_cell_share"])

    def test_a_recorded_failure_blocks_the_lot_by_default(self):
        case = _lot()
        case["cells"][2]["acceptance_records"][
            "cell-electrical-performance"
        ] = OUTCOME_FAILED
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertIn(CELL_FAILED, result["grouped_cells"])

    def test_policy_can_carry_a_dispositioned_failure(self):
        case = _lot()
        case["cells"][2]["acceptance_records"][
            "cell-electrical-performance"
        ] = OUTCOME_FAILED
        case["policy"] = {
            "carry_dispositioned_failure": True,
            "min_every_cell_share": 0.5,
        }
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["verdict"], LOT_ACCEPTED)

    def test_a_thin_sample_blocks_the_lot(self):
        case = _lot(delivery=20, qualification=10)
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertTrue(
            any("sample fraction" in finding for finding in result["findings"])
        )

    def test_the_weakest_cell_is_named_by_rank(self):
        case = _lot()
        case["cells"][1]["acceptance_records"][
            "cell-visual-inspection"
        ] = OUTCOME_NOT_RUN
        del case["cells"][3]["acceptance_records"]["cell-visual-inspection"]
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["weakest_cell"], case["cells"][3]["cell_id"])
        self.assertIn(CELL_NOT_RUN, result["grouped_cells"])
        self.assertIn(CELL_NO_RECORD, result["grouped_cells"])

    def test_a_cell_listed_twice_rejected(self):
        case = _lot()
        case["cells"].append(copy.deepcopy(case["cells"][0]))
        with self.assertRaises(ValueError):
            assess_bare_cell_acceptance(case)

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_acceptance({"lot_id": "LOT-7", "cells": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_acceptance("all the cells were accepted")


if __name__ == "__main__":
    unittest.main()
