"""Contract tests for the clause 5.2.11.2 receiving-chain integrity logic."""

import copy
import datetime
import unittest

from e2007_measurement_chain_integrity_check_logic import (
    DEVIATION_TOLERANCE_DB,
    ELEMENT_KINDS,
    assess_chain_integrity,
    assess_run,
    bypassed_elements,
    chain_gain_db,
    check_timing,
    deviation_db,
    expected_indication_dbuv,
    parse_timestamp,
    validate_chain,
    within_allowance,
)

# Antenna factor and cable loss enter as negative gains, the preamplifier as a
# positive one; the chain is a net 1 dB loss from the field to the indication.
CHAIN = [
    {"id": "horn-a", "kind": "transducer", "gain_db": -26.0},
    {"id": "cable-1", "kind": "cable", "gain_db": -3.5},
    {"id": "lna-1", "kind": "preamplifier", "gain_db": 30.0},
    {"id": "cable-2", "kind": "cable", "gain_db": -1.5},
    {"id": "rx-1", "kind": "receiver", "gain_db": 0.0},
]

RUN_START = "2026-09-18T09:30:00"


def check(**overrides):
    record = {
        "time": "2026-09-18T09:05:00",
        "injected_dbuv": 80.0,
        "measured_dbuv": 79.0,
        "injection_point": "horn-a",
    }
    record.update(overrides)
    return record


def run(**overrides):
    record = {"id": "ce-run-1", "start_time": RUN_START, "check": check()}
    record.update(overrides)
    return record


class ValidateChainTests(unittest.TestCase):
    def test_chain_is_returned_head_to_tail(self):
        validated = validate_chain(CHAIN)
        self.assertEqual(validated[0]["id"], "horn-a")
        self.assertEqual(validated[-1]["kind"], "receiver")

    def test_kind_is_case_insensitive(self):
        chain = copy.deepcopy(CHAIN)
        chain[0]["kind"] = "Transducer"
        self.assertEqual(validate_chain(chain)[0]["kind"], "transducer")

    def test_every_governed_kind_is_recognised(self):
        self.assertIn("attenuator", ELEMENT_KINDS)
        self.assertIn("filter", ELEMENT_KINDS)

    def test_single_element_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain([CHAIN[0]])

    def test_chain_not_starting_at_the_transducer_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain(CHAIN[1:])

    def test_chain_not_ending_at_the_receiver_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain(CHAIN[:-1])

    def test_second_transducer_rejected(self):
        chain = copy.deepcopy(CHAIN)
        chain[1]["kind"] = "transducer"
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_receiver_in_the_middle_rejected(self):
        chain = copy.deepcopy(CHAIN)
        chain[2]["kind"] = "receiver"
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_duplicate_element_id_rejected(self):
        chain = copy.deepcopy(CHAIN)
        chain[3]["id"] = "cable-1"
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_unknown_element_key_rejected(self):
        chain = copy.deepcopy(CHAIN)
        chain[1]["length_m"] = 3.0
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_missing_element_key_rejected(self):
        chain = copy.deepcopy(CHAIN)
        del chain[1]["gain_db"]
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_non_finite_gain_rejected(self):
        chain = copy.deepcopy(CHAIN)
        chain[1]["gain_db"] = float("nan")
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_mapping_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain({"id": "horn-a"})


class GainAndDeviationTests(unittest.TestCase):
    def test_end_to_end_gain_is_the_sum_of_the_elements(self):
        self.assertAlmostEqual(chain_gain_db(CHAIN), -1.0, places=9)

    def test_expected_indication_applies_the_chain_gain(self):
        self.assertAlmostEqual(expected_indication_dbuv(80.0, CHAIN), 79.0, places=9)

    def test_deviation_is_signed_measured_minus_expected(self):
        self.assertAlmostEqual(deviation_db(81.5, 79.0), 2.5, places=9)

    def test_exactly_met_allowance_is_met(self):
        self.assertTrue(within_allowance(2.0, 2.0))

    def test_negative_deviation_uses_the_same_allowance(self):
        self.assertTrue(within_allowance(-2.0, 2.0))

    def test_deviation_beyond_the_allowance_fails(self):
        self.assertFalse(within_allowance(2.5, 2.0))

    def test_tolerance_absorbs_representation_error_only(self):
        self.assertTrue(within_allowance(2.0 + DEVIATION_TOLERANCE_DB / 2.0, 2.0))

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            within_allowance(0.5, -2.0)

    def test_boolean_level_rejected(self):
        with self.assertRaises(ValueError):
            expected_indication_dbuv(True, CHAIN)


class BypassTests(unittest.TestCase):
    def test_injection_at_the_head_bypasses_nothing(self):
        self.assertEqual(bypassed_elements(CHAIN, "horn-a"), [])

    def test_injection_at_the_preamplifier_bypasses_the_front_end(self):
        self.assertEqual(bypassed_elements(CHAIN, "lna-1"), ["horn-a", "cable-1"])

    def test_injection_at_the_receiver_bypasses_almost_everything(self):
        self.assertEqual(len(bypassed_elements(CHAIN, "rx-1")), 4)

    def test_unknown_injection_point_rejected(self):
        with self.assertRaises(ValueError):
            bypassed_elements(CHAIN, "cable-9")

    def test_blank_injection_point_rejected(self):
        with self.assertRaises(ValueError):
            bypassed_elements(CHAIN, "   ")


class TimingTests(unittest.TestCase):
    def test_age_is_reported_in_minutes(self):
        timing = check_timing("2026-09-18T09:05:00", RUN_START, 60.0)
        self.assertAlmostEqual(timing["age_minutes"], 25.0, places=9)
        self.assertTrue(timing["precedes_run"])
        self.assertFalse(timing["stale"])

    def test_check_after_the_run_started_does_not_precede_it(self):
        timing = check_timing("2026-09-18T09:45:00", RUN_START, 60.0)
        self.assertFalse(timing["precedes_run"])
        self.assertAlmostEqual(timing["age_minutes"], -15.0, places=9)

    def test_check_older_than_the_window_is_stale(self):
        timing = check_timing("2026-09-18T07:00:00", RUN_START, 60.0)
        self.assertTrue(timing["stale"])

    def test_check_exactly_at_the_window_edge_is_not_stale(self):
        timing = check_timing("2026-09-18T08:30:00", RUN_START, 60.0)
        self.assertAlmostEqual(timing["age_minutes"], 60.0, places=9)
        self.assertFalse(timing["stale"])

    def test_datetime_objects_are_accepted(self):
        timing = check_timing(
            datetime.datetime(2026, 9, 18, 9, 0), datetime.datetime(2026, 9, 18, 9, 30), 60.0
        )
        self.assertAlmostEqual(timing["age_minutes"], 30.0, places=9)

    def test_mixed_time_zone_awareness_rejected(self):
        with self.assertRaises(ValueError):
            check_timing("2026-09-18T09:05:00+00:00", RUN_START, 60.0)

    def test_malformed_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_timestamp("18/09/2026 09:05")

    def test_non_positive_window_rejected(self):
        with self.assertRaises(ValueError):
            check_timing("2026-09-18T09:05:00", RUN_START, 0.0)


class AssessRunTests(unittest.TestCase):
    def test_clean_run_conforms(self):
        grading = assess_run(run(), CHAIN, 2.0, 60.0)
        self.assertTrue(grading["conforming"])
        self.assertEqual(grading["findings"], [])
        self.assertAlmostEqual(grading["deviation_db"], 0.0, places=9)

    def test_missing_check_is_a_finding(self):
        grading = assess_run(run(check=None), CHAIN, 2.0, 60.0)
        self.assertFalse(grading["conforming"])
        self.assertFalse(grading["checked"])
        self.assertIn("no chain-integrity check", grading["findings"][0])

    def test_indication_outside_the_allowance_is_a_finding(self):
        grading = assess_run(run(check=check(measured_dbuv=85.0)), CHAIN, 2.0, 60.0)
        self.assertFalse(grading["conforming"])
        self.assertAlmostEqual(grading["deviation_db"], 6.0, places=9)

    def test_partial_injection_is_a_finding_naming_the_unverified_elements(self):
        grading = assess_run(run(check=check(injection_point="lna-1")), CHAIN, 2.0, 60.0)
        self.assertEqual(grading["bypassed"], ["horn-a", "cable-1"])
        self.assertIn("unverified", grading["findings"][0])

    def test_check_performed_after_the_run_began_is_a_finding(self):
        grading = assess_run(
            run(check=check(time="2026-09-18T09:50:00")), CHAIN, 2.0, 60.0
        )
        self.assertFalse(grading["conforming"])
        self.assertIn("after the run began", grading["findings"][0])

    def test_stale_check_is_a_finding(self):
        grading = assess_run(
            run(check=check(time="2026-09-18T06:00:00")), CHAIN, 2.0, 60.0
        )
        self.assertIn("beyond the", grading["findings"][0])

    def test_unknown_run_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_run(run(operator="lab"), CHAIN, 2.0, 60.0)

    def test_unknown_check_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_run(run(check=check(source="tracking-generator")), CHAIN, 2.0, 60.0)

    def test_missing_check_key_rejected(self):
        record = check()
        del record["injected_dbuv"]
        with self.assertRaises(ValueError):
            assess_run(run(check=record), CHAIN, 2.0, 60.0)

    def test_blank_run_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_run(run(id=" "), CHAIN, 2.0, 60.0)


class CampaignTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "chain": CHAIN,
            "runs": [
                run(id="ce-run-1"),
                run(
                    id="ce-run-2",
                    start_time="2026-09-18T11:00:00",
                    check=check(time="2026-09-18T10:50:00", measured_dbuv=79.4),
                ),
            ],
            "allowance_db": 2.0,
            "max_age_minutes": 60.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_campaign_is_compliant(self):
        result = assess_chain_integrity(self._spec())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["conforming_fraction"], 1.0, places=9)

    def test_one_defective_run_halves_the_conforming_fraction(self):
        spec = self._spec()
        spec["runs"][1]["check"]["measured_dbuv"] = 90.0
        result = assess_chain_integrity(spec)
        self.assertAlmostEqual(result["conforming_fraction"], 0.5, places=9)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_reused_check_record_is_flagged_on_both_runs(self):
        spec = self._spec()
        spec["runs"][1]["start_time"] = "2026-09-18T09:35:00"
        spec["runs"][1]["check"] = check()
        result = assess_chain_integrity(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)
        self.assertTrue(all("reused" in finding for finding in result["findings"]))

    def test_unchecked_run_is_reported_once(self):
        spec = self._spec()
        spec["runs"][1]["check"] = None
        result = assess_chain_integrity(spec)
        self.assertEqual(result["conforming_count"], 1)

    def test_duplicate_run_id_rejected(self):
        spec = self._spec()
        spec["runs"][1]["id"] = "ce-run-1"
        with self.assertRaises(ValueError):
            assess_chain_integrity(spec)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_chain_integrity(self._spec(runs=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_chain_integrity(["chain"])

    def test_missing_allowance_rejected(self):
        spec = self._spec()
        del spec["allowance_db"]
        with self.assertRaises(ValueError):
            assess_chain_integrity(spec)

    def test_staleness_window_defaults_when_not_declared(self):
        spec = self._spec()
        del spec["max_age_minutes"]
        result = assess_chain_integrity(spec)
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
