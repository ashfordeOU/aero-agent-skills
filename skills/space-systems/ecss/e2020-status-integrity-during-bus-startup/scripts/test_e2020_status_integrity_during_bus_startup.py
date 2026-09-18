"""Contract tests for the clause 5.2.7.4.1 limiter state integrity logic."""

import unittest

from e2020_status_integrity_during_bus_startup_logic import (
    TIME_TOLERANCE_S,
    VOLTAGE_TOLERANCE_V,
    assess_status_integrity,
    evaluate_profile,
    evaluate_sample,
    normalise_state,
    recovery_verdicts,
    supply_valid,
    supply_window,
    validate_profile,
    validate_sample,
    zero_volt_excursions,
)

FLOOR_V = 18.0
ZERO_V = 0.5


def sample(t, v, intended="off", actual="off", reported="off"):
    return {
        "time_s": t,
        "bus_voltage_v": v,
        "intended_state": intended,
        "actual_state": actual,
        "reported_state": reported,
    }


# A clean main bus rise: dead bus, ramp through the logic supply floor, then a
# commanded turn on once the unit is awake.
CLEAN_RISE = [
    sample(0.000, 0.0),
    sample(0.010, 6.0),
    sample(0.020, 17.0),
    sample(0.030, 22.0),
    sample(0.040, 28.0),
    sample(0.050, 28.0, intended="on", actual="on", reported="on"),
]


class NormaliseStateTests(unittest.TestCase):
    def test_on_passthrough(self):
        self.assertEqual(normalise_state("on"), "on")

    def test_case_and_whitespace_folded(self):
        self.assertEqual(normalise_state("  OFF "), "off")

    def test_tripped_is_an_off_state(self):
        self.assertEqual(normalise_state("tripped"), "off")

    def test_enabled_is_an_on_state(self):
        self.assertEqual(normalise_state("Enabled"), "on")

    def test_closed_contact_is_an_on_state(self):
        self.assertEqual(normalise_state("Closed"), "on")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalise_state("standby")

    def test_non_string_state_rejected(self):
        with self.assertRaises(ValueError):
            normalise_state(1)


class ValidateSampleTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_sample(sample(0.1, 28.0, "on", "on", "on"), 0)
        self.assertEqual(record["intended_state"], "on")
        self.assertAlmostEqual(record["bus_voltage_v"], 28.0, places=9)

    def test_absent_reported_state_is_none_not_a_guess(self):
        record = validate_sample(
            {
                "time_s": 0.0,
                "bus_voltage_v": 28.0,
                "intended_state": "on",
                "actual_state": "on",
            },
            0,
        )
        self.assertIsNone(record["reported_state"])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample({"time_s": 0.0, "bus_voltage_v": 28.0}, 0)

    def test_negative_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(0.0, -1.0), 0)

    def test_non_finite_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(0.0, float("inf")), 0)

    def test_boolean_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(0.0, True), 0)

    def test_non_mapping_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(["time", 0.0], 0)


class ValidateProfileTests(unittest.TestCase):
    def test_orders_are_indexed(self):
        records = validate_profile(CLEAN_RISE)
        self.assertEqual([r["index"] for r in records], list(range(6)))

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([])

    def test_repeated_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([sample(0.0, 0.0), sample(0.0, 5.0)])

    def test_out_of_order_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([sample(0.1, 0.0), sample(0.0, 5.0)])


class SupplyWindowTests(unittest.TestCase):
    def test_above_floor_is_valid(self):
        self.assertTrue(supply_valid(28.0, FLOOR_V))

    def test_below_floor_is_not_valid(self):
        self.assertFalse(supply_valid(12.0, FLOOR_V))

    def test_exactly_at_the_floor_counts_as_valid(self):
        self.assertTrue(supply_valid(FLOOR_V, FLOOR_V))

    def test_representation_error_at_the_floor_does_not_flip_the_window(self):
        just_under = FLOOR_V - VOLTAGE_TOLERANCE_V / 10.0
        self.assertTrue(supply_valid(just_under, FLOOR_V))

    def test_window_lists_only_awake_samples(self):
        records = validate_profile(CLEAN_RISE)
        self.assertEqual(supply_window(records, FLOOR_V), [3, 4, 5])


class ZeroVoltExcursionTests(unittest.TestCase):
    def test_leading_dead_bus_is_an_excursion(self):
        records = validate_profile(CLEAN_RISE)
        runs = zero_volt_excursions(records, ZERO_V)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["start_index"], 0)
        self.assertEqual(runs[0]["end_index"], 0)

    def test_contiguous_samples_collapse_into_one_excursion(self):
        profile = [sample(0.0, 0.0), sample(0.1, 0.0), sample(0.2, 28.0, "on", "on", "on")]
        runs = zero_volt_excursions(validate_profile(profile), ZERO_V)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["end_index"], 1)

    def test_two_separated_dropouts_are_two_excursions(self):
        profile = [
            sample(0.0, 0.0),
            sample(0.1, 28.0, "on", "on", "on"),
            sample(0.2, 0.0),
            sample(0.3, 28.0, "off", "off", "off"),
        ]
        runs = zero_volt_excursions(validate_profile(profile), ZERO_V)
        self.assertEqual(len(runs), 2)

    def test_excursion_open_at_the_end_is_still_reported(self):
        profile = [sample(0.0, 28.0, "on", "on", "on"), sample(0.1, 0.0)]
        runs = zero_volt_excursions(validate_profile(profile), ZERO_V)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["start_index"], 1)

    def test_bus_that_never_falls_has_no_excursion(self):
        profile = [sample(0.0, 28.0, "on", "on", "on"), sample(0.1, 28.0, "on", "on", "on")]
        self.assertEqual(zero_volt_excursions(validate_profile(profile), ZERO_V), [])


class EvaluateSampleTests(unittest.TestCase):
    def test_agreement_inside_the_window(self):
        record = evaluate_sample(validate_sample(sample(0.0, 28.0, "on", "on", "on"), 0), FLOOR_V)
        self.assertEqual(record["state_verdict"], "match")
        self.assertEqual(record["status_verdict"], "agree")

    def test_state_mismatch_inside_the_window(self):
        record = evaluate_sample(validate_sample(sample(0.0, 28.0, "on", "off", "off"), 0), FLOOR_V)
        self.assertEqual(record["state_verdict"], "mismatch")

    def test_status_disagreement_inside_the_window(self):
        record = evaluate_sample(validate_sample(sample(0.0, 28.0, "on", "on", "off"), 0), FLOOR_V)
        self.assertEqual(record["status_verdict"], "disagree")

    def test_missing_status_is_unreported_not_agreement(self):
        raw = {
            "time_s": 0.0,
            "bus_voltage_v": 28.0,
            "intended_state": "on",
            "actual_state": "on",
        }
        record = evaluate_sample(validate_sample(raw, 0), FLOOR_V)
        self.assertEqual(record["status_verdict"], "unreported")

    def test_below_the_floor_a_mismatch_is_indeterminate_not_a_failure(self):
        record = evaluate_sample(validate_sample(sample(0.0, 6.0, "on", "off", "off"), 0), FLOOR_V)
        self.assertEqual(record["state_verdict"], "indeterminate")
        self.assertEqual(record["status_verdict"], "indeterminate")

    def test_below_the_floor_an_agreement_is_not_credited_either(self):
        record = evaluate_sample(validate_sample(sample(0.0, 6.0, "on", "on", "on"), 0), FLOOR_V)
        self.assertEqual(record["state_verdict"], "indeterminate")

    def test_non_record_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample("28 V", FLOOR_V)

    def test_profile_evaluation_keeps_sample_count(self):
        evaluated = evaluate_profile(validate_profile(CLEAN_RISE), FLOOR_V)
        self.assertEqual(len(evaluated), len(CLEAN_RISE))


class RecoveryVerdictTests(unittest.TestCase):
    def _recovered(self, after_state, settle=0.0):
        profile = [
            sample(0.0, 28.0, "on", "on", "on"),
            sample(0.1, 0.0),
            sample(0.2, 28.0, after_state, after_state, after_state),
            sample(0.3, 28.0, after_state, after_state, after_state),
        ]
        records = validate_profile(profile)
        evaluated = evaluate_profile(records, FLOOR_V)
        runs = zero_volt_excursions(records, ZERO_V)
        return recovery_verdicts(evaluated, runs, "off", settle)

    def test_recovery_into_the_default_state_passes(self):
        verdicts = self._recovered("off")
        self.assertEqual(verdicts[0]["verdict"], "recovered")

    def test_recovery_into_the_wrong_state_is_caught(self):
        verdicts = self._recovered("on")
        self.assertEqual(verdicts[0]["verdict"], "wrong-state")

    def test_settling_time_moves_the_observation_point(self):
        verdicts = self._recovered("off", settle=0.15)
        self.assertEqual(verdicts[0]["observed_index"], 3)

    def test_settling_time_landing_exactly_on_a_sample_still_observes_it(self):
        verdicts = self._recovered("off", settle=0.1)
        self.assertEqual(verdicts[0]["observed_index"], 2)

    def test_no_valid_sample_after_the_dropout_is_not_observed(self):
        profile = [sample(0.0, 28.0, "on", "on", "on"), sample(0.1, 0.0), sample(0.2, 4.0)]
        records = validate_profile(profile)
        verdicts = recovery_verdicts(
            evaluate_profile(records, FLOOR_V),
            zero_volt_excursions(records, ZERO_V),
            "off",
        )
        self.assertEqual(verdicts[0]["verdict"], "not-observed")

    def test_negative_settle_time_rejected(self):
        with self.assertRaises(ValueError):
            recovery_verdicts([], [], "off", -0.1)

    def test_unknown_default_state_rejected(self):
        with self.assertRaises(ValueError):
            recovery_verdicts([], [], "armed", 0.0)


class AssessStatusIntegrityTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "samples": CLEAN_RISE,
            "logic_supply_floor_v": FLOOR_V,
            "zero_volt_threshold_v": ZERO_V,
            "default_state": "off",
            "settle_time_s": 0.0,
        }
        spec.update(over)
        return spec

    def test_clean_start_up_is_compliant(self):
        result = assess_status_integrity(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_clean_start_up_reports_the_supply_window(self):
        result = assess_status_integrity(self._spec())
        self.assertEqual(result["supply_valid_indices"], [3, 4, 5])

    def test_state_mismatch_after_wake_up_fails(self):
        bad = list(CLEAN_RISE)
        bad[4] = sample(0.040, 28.0, intended="off", actual="on", reported="on")
        result = assess_status_integrity(self._spec(samples=bad))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["mismatch_count"], 1)

    def test_status_disagreement_is_its_own_count(self):
        bad = list(CLEAN_RISE)
        bad[5] = sample(0.050, 28.0, intended="on", actual="on", reported="off")
        result = assess_status_integrity(self._spec(samples=bad))
        self.assertEqual(result["status_disagreement_count"], 1)
        self.assertEqual(result["mismatch_count"], 0)

    def test_a_disagreement_below_the_floor_is_not_counted(self):
        bad = list(CLEAN_RISE)
        bad[1] = sample(0.010, 6.0, intended="on", actual="off", reported="on")
        result = assess_status_integrity(self._spec(samples=bad))
        self.assertTrue(result["compliant"])

    def test_missing_status_inside_the_window_is_a_finding(self):
        bad = list(CLEAN_RISE)
        bad[5] = {
            "time_s": 0.050,
            "bus_voltage_v": 28.0,
            "intended_state": "on",
            "actual_state": "on",
        }
        result = assess_status_integrity(self._spec(samples=bad))
        self.assertEqual(result["unreported_count"], 1)
        self.assertFalse(result["compliant"])

    def test_zero_volt_recovery_into_the_wrong_state_fails(self):
        profile = [
            sample(0.0, 28.0, "on", "on", "on"),
            sample(0.1, 0.0),
            sample(0.2, 28.0, "on", "on", "on"),
        ]
        result = assess_status_integrity(self._spec(samples=profile))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["recoveries"][0]["verdict"], "wrong-state")

    def test_profile_that_never_wakes_is_a_coverage_finding_not_a_pass(self):
        profile = [sample(0.0, 0.0), sample(0.1, 4.0), sample(0.2, 9.0)]
        result = assess_status_integrity(self._spec(samples=profile))
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("never reached the logic supply floor" in f for f in result["findings"])
        )

    def test_zero_threshold_above_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_status_integrity(self._spec(zero_volt_threshold_v=20.0))

    def test_zero_threshold_equal_to_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_status_integrity(self._spec(zero_volt_threshold_v=FLOOR_V))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["default_state"]
        with self.assertRaises(ValueError):
            assess_status_integrity(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_status_integrity([("samples", CLEAN_RISE)])

    def test_negative_supply_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_status_integrity(self._spec(logic_supply_floor_v=-1.0))

    def test_time_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(TIME_TOLERANCE_S, 1e-6)


if __name__ == "__main__":
    unittest.main()
