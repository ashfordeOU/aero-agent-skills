#!/usr/bin/env python3
"""Contract test for diode acceptance testing, general (offline).

Walks the clause workflow step by step: the diode record validation, the
four record states held apart, the per-diode activities a part owes and
the sampled activities it does not, the sampled share against the
declared minimum, the two populations summarised separately, the wholly
untested population, the absent population, the failure policy, and the
roll-up into one lot verdict. This is the gate 3 review evidence.
"""

import copy
import unittest

from e2008_diode_acceptance_testing_general_logic import (
    DEFAULT_ACCEPTANCE_POLICY,
    DIODE_ACCEPTED,
    DIODE_FAILED,
    DIODE_NOT_RUN,
    DIODE_NO_RECORD,
    LOT_ACCEPTED,
    LOT_NOT_ACCEPTED,
    OUTCOME_FAILED,
    OUTCOME_NOT_RUN,
    OUTCOME_PASSED,
    PER_DIODE_ACTIVITIES,
    SAMPLED_ACTIVITIES,
    assess_diode,
    assess_diode_acceptance,
    resolve_policy,
    sampled_activity_coverage,
    summarise_population,
    validate_diode_record,
)


def _diode(diode_id, population="delivery", sampled=(), **overrides):
    records = {a: OUTCOME_PASSED for a in PER_DIODE_ACTIVITIES}
    for activity in sampled:
        records[activity] = OUTCOME_PASSED
    record = {
        "diode_id": diode_id,
        "population": population,
        "acceptance_records": records,
    }
    record.update(copy.deepcopy(overrides))
    return record


def _lot(delivery=10, qualification=10):
    diodes = []
    for index in range(delivery):
        sampled = SAMPLED_ACTIVITIES if index == 0 else ()
        diodes.append(_diode("DEL-%02d" % index, "delivery", sampled))
    for index in range(qualification):
        sampled = SAMPLED_ACTIVITIES if index == 0 else ()
        diodes.append(_diode("QUA-%02d" % index, "qualification", sampled))
    return {"lot_id": "LOT-9", "diodes": diodes}


class RecordValidationTests(unittest.TestCase):
    def test_a_sound_record_validates(self):
        record = validate_diode_record(_diode("DEL-00"))
        self.assertEqual(record["population"], "delivery")
        self.assertEqual(
            len(record["acceptance_records"]), len(PER_DIODE_ACTIVITIES)
        )

    def test_an_unknown_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_record(_diode("DEL-00", population="spares"))

    def test_an_activity_outside_the_acceptance_set_rejected(self):
        diode = _diode("DEL-00")
        diode["acceptance_records"]["diode-launch-rehearsal"] = OUTCOME_PASSED
        with self.assertRaises(ValueError):
            validate_diode_record(diode)

    def test_an_unknown_outcome_rejected(self):
        diode = _diode("DEL-00")
        diode["acceptance_records"]["diode-visual-inspection"] = "probably-fine"
        with self.assertRaises(ValueError):
            validate_diode_record(diode)

    def test_a_blank_diode_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_record(_diode("   "))

    def test_a_non_mapping_diode_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_record(["DEL-00"])


class DiodeVerdictTests(unittest.TestCase):
    def test_a_fully_recorded_diode_is_accepted(self):
        result = assess_diode(_diode("DEL-00"))
        self.assertEqual(result["verdict"], DIODE_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_record_ranks_worst(self):
        diode = _diode("DEL-01")
        del diode["acceptance_records"]["diode-visual-inspection"]
        result = assess_diode(diode)
        self.assertEqual(result["verdict"], DIODE_NO_RECORD)
        self.assertEqual(result["missing"], ["diode-visual-inspection"])

    def test_an_unrun_activity_is_held_apart_from_absence(self):
        diode = _diode("DEL-02")
        diode["acceptance_records"]["diode-visual-inspection"] = OUTCOME_NOT_RUN
        result = assess_diode(diode)
        self.assertEqual(result["verdict"], DIODE_NOT_RUN)
        self.assertEqual(result["missing"], [])

    def test_a_recorded_failure_is_held_apart_from_absence(self):
        diode = _diode("DEL-03")
        diode["acceptance_records"][
            "diode-reverse-leakage-measurement"
        ] = OUTCOME_FAILED
        result = assess_diode(diode)
        self.assertEqual(result["verdict"], DIODE_FAILED)
        self.assertTrue(result["findings"])

    def test_absence_outranks_a_failure_on_the_same_part(self):
        diode = _diode("DEL-04")
        del diode["acceptance_records"]["diode-visual-inspection"]
        diode["acceptance_records"][
            "diode-forward-voltage-measurement"
        ] = OUTCOME_FAILED
        result = assess_diode(diode)
        self.assertEqual(result["verdict"], DIODE_NO_RECORD)

    def test_a_part_never_drawn_into_a_sample_owes_nothing_extra(self):
        result = assess_diode(_diode("DEL-05"))
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["verdict"], DIODE_ACCEPTED)


class SampledCoverageTests(unittest.TestCase):
    def _members(self, total, drawn, activity, outcome=OUTCOME_PASSED):
        members = []
        for index in range(total):
            diode = _diode("DEL-%02d" % index)
            if index < drawn:
                diode["acceptance_records"][activity] = outcome
            members.append(diode)
        return members

    def test_an_exactly_met_share_is_not_reported_short(self):
        activity = SAMPLED_ACTIVITIES[0]
        members = self._members(20, 2, activity)
        entry = sampled_activity_coverage(members, activity, 0.10)
        self.assertAlmostEqual(entry["sampled_share"], 0.10, places=9)
        self.assertTrue(entry["meets_sample_share"])
        self.assertEqual(entry["findings"], [])

    def test_a_short_draw_is_reported(self):
        activity = SAMPLED_ACTIVITIES[1]
        members = self._members(20, 1, activity)
        entry = sampled_activity_coverage(members, activity, 0.10)
        self.assertFalse(entry["meets_sample_share"])
        self.assertTrue(entry["findings"])

    def test_a_sampled_failure_is_counted_for_the_population(self):
        activity = SAMPLED_ACTIVITIES[2]
        members = self._members(10, 4, activity, OUTCOME_FAILED)
        entry = sampled_activity_coverage(members, activity, 0.10)
        self.assertEqual(entry["failed"], 4)
        self.assertEqual(entry["passed"], 0)
        self.assertTrue(any("speaks for the population" in f for f in entry["findings"]))

    def test_a_per_diode_activity_is_not_a_sampled_one(self):
        members = self._members(10, 10, SAMPLED_ACTIVITIES[0])
        with self.assertRaises(ValueError):
            sampled_activity_coverage(members, PER_DIODE_ACTIVITIES[0], 0.10)

    def test_an_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            sampled_activity_coverage([], SAMPLED_ACTIVITIES[0], 0.10)

    def test_a_share_outside_the_unit_interval_rejected(self):
        members = self._members(10, 10, SAMPLED_ACTIVITIES[0])
        with self.assertRaises(ValueError):
            sampled_activity_coverage(members, SAMPLED_ACTIVITIES[0], 1.5)


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertAlmostEqual(
            settings["min_sample_share"],
            DEFAULT_ACCEPTANCE_POLICY["min_sample_share"],
            places=9,
        )
        self.assertFalse(settings["carry_dispositioned_failure"])

    def test_a_non_boolean_failure_policy_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"carry_dispositioned_failure": "sometimes"})

    def test_a_zero_sample_share_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_sample_share": 0.0})


class PopulationTests(unittest.TestCase):
    def test_both_populations_are_summarised_separately(self):
        case = _lot()
        delivery = summarise_population(case["diodes"], "delivery")
        qualification = summarise_population(case["diodes"], "qualification")
        self.assertEqual(delivery["diodes"], 10)
        self.assertEqual(qualification["diodes"], 10)
        self.assertAlmostEqual(qualification["accepted_share"], 1.0, places=9)

    def test_a_wholly_untested_population_is_its_own_finding(self):
        case = _lot()
        for diode in case["diodes"]:
            if diode["population"] == "qualification":
                diode["acceptance_records"] = {}
        summary = summarise_population(case["diodes"], "qualification")
        self.assertTrue(summary["wholly_untested"])
        self.assertTrue(
            any("no acceptance work at all" in f for f in summary["findings"])
        )

    def test_an_absent_population_reports_present_false(self):
        case = _lot(delivery=6, qualification=0)
        summary = summarise_population(case["diodes"], "qualification")
        self.assertFalse(summary["present"])
        self.assertEqual(summary["diodes"], 0)


class LotRollUpTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        result = assess_diode_acceptance(_lot())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_untested_qualification_population_blocks_the_lot(self):
        case = _lot()
        for diode in case["diodes"]:
            if diode["population"] == "qualification":
                diode["acceptance_records"] = {}
        result = assess_diode_acceptance(case)
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertTrue(
            any("qualification population" in f for f in result["findings"])
        )

    def test_a_missing_population_blocks_the_lot(self):
        case = _lot(delivery=10, qualification=0)
        result = assess_diode_acceptance(case)
        self.assertEqual(result["missing_populations"], ["qualification"])
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)

    def test_the_failure_policy_decides_a_dispositioned_failure(self):
        case = _lot()
        case["diodes"][2]["acceptance_records"][
            "diode-forward-voltage-measurement"
        ] = OUTCOME_FAILED
        strict = assess_diode_acceptance(copy.deepcopy(case))
        self.assertEqual(strict["verdict"], LOT_NOT_ACCEPTED)
        carried = copy.deepcopy(case)
        carried["policy"] = {
            "carry_dispositioned_failure": True,
            "min_per_diode_share": 0.5,
        }
        self.assertEqual(
            assess_diode_acceptance(carried)["verdict"], LOT_ACCEPTED
        )

    def test_the_weakest_part_is_named_by_rank(self):
        case = _lot()
        case["diodes"][1]["acceptance_records"][
            "diode-visual-inspection"
        ] = OUTCOME_NOT_RUN
        del case["diodes"][3]["acceptance_records"]["diode-visual-inspection"]
        result = assess_diode_acceptance(case)
        self.assertEqual(result["weakest_diode"], case["diodes"][3]["diode_id"])
        self.assertIn(DIODE_NOT_RUN, result["grouped_diodes"])
        self.assertIn(DIODE_NO_RECORD, result["grouped_diodes"])

    def test_a_diode_listed_twice_rejected(self):
        case = _lot()
        case["diodes"].append(copy.deepcopy(case["diodes"][0]))
        with self.assertRaises(ValueError):
            assess_diode_acceptance(case)

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_acceptance({"lot_id": "LOT-9", "diodes": []})

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_acceptance("all the diodes were accepted")


if __name__ == "__main__":
    unittest.main()
