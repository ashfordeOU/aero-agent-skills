#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.3.3 pre-seal burn-in leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_pre_seal_burn_in.py
"""

import unittest

from q6005_pre_seal_burn_in_logic import (
    ACCEPTANCE_INDEX,
    BOLTZMANN_EV_PER_K,
    BURN_IN_TOLERANCE,
    CONDITION_STATE_CREDIT,
    DEFAULT_ACTIVATION_ENERGY_EV,
    DEFAULT_DRIFT_LIMIT,
    KELVIN_OFFSET,
    MANDATORY_SOAK_CONDITIONS,
    MAXIMUM_INTERRUPTION_HOURS,
    MAXIMUM_STRESS_TEMPERATURE_C,
    MINIMUM_EQUIVALENT_HOURS,
    MINIMUM_STRESS_TEMPERATURE_C,
    REFERENCE_TEMPERATURE_C,
    SOAK_CONDITIONS,
    VERDICTS,
    acceleration_factor,
    assess_condition,
    assess_pre_seal_burn_in,
    condition_index,
    condition_state_credit,
    condition_weight,
    continuous_soak_segments,
    delivered_equivalent_hours,
    drift_within_limit,
    duration_is_sufficient,
    equivalent_reference_hours,
    parameter_drift_fraction,
    temperature_inside_band,
)

OPTIONAL_CONDITION = "interruptions-logged-with-their-duration"
MANDATORY_CONDITION = "package-open-throughout-the-soak"


def every_condition(state="met-and-recorded", **overrides):
    """Every soak condition in one state, with named exceptions."""
    states = {name: state for name in SOAK_CONDITIONS}
    states.update(overrides)
    return states


def nominal_segments(hours=MINIMUM_EQUIVALENT_HOURS, temperature=REFERENCE_TEMPERATURE_C):
    """One uninterrupted soak segment at the reference condition."""
    return [{"hours": hours, "temperature_c": temperature}]


def parameter(name="output-offset", before=5.0, after=5.1):
    """One parameter measured before and after the soak."""
    return {"parameter": name, "before": before, "after": after}


def run(**overrides):
    """Grade one pre-seal burn-in run."""
    case = {
        "unit_id": "HYB-BI-1",
        "segments": nominal_segments(),
        "parameters": [parameter()],
        "conditions": every_condition(),
        "minimum_hours": None,
        "drift_limit": None,
        "activation_energy_ev": None,
    }
    case.update(overrides)
    return assess_pre_seal_burn_in(**case)


class ArrheniusTests(unittest.TestCase):
    def test_the_reference_condition_accelerates_nothing(self):
        self.assertAlmostEqual(acceleration_factor(REFERENCE_TEMPERATURE_C), 1.0, places=9)

    def test_a_hotter_chamber_buys_more_than_its_hours(self):
        self.assertGreater(acceleration_factor(MAXIMUM_STRESS_TEMPERATURE_C), 1.5)

    def test_a_cooler_chamber_buys_less_than_its_hours(self):
        self.assertLess(acceleration_factor(MINIMUM_STRESS_TEMPERATURE_C), 0.75)

    def test_a_higher_activation_energy_sharpens_the_temperature_dependence(self):
        low = acceleration_factor(MAXIMUM_STRESS_TEMPERATURE_C, None, 0.3)
        high = acceleration_factor(MAXIMUM_STRESS_TEMPERATURE_C, None, 0.9)
        self.assertGreater(high, low)

    def test_a_zero_activation_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(REFERENCE_TEMPERATURE_C, None, 0.0)

    def test_a_chamber_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(-300.0)

    def test_hours_at_the_reference_convert_one_for_one(self):
        self.assertAlmostEqual(
            equivalent_reference_hours(MINIMUM_EQUIVALENT_HOURS, REFERENCE_TEMPERATURE_C),
            MINIMUM_EQUIVALENT_HOURS,
            places=9,
        )

    def test_a_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_reference_hours(-1.0, REFERENCE_TEMPERATURE_C)

    def test_the_published_constants_are_the_ones_the_arithmetic_uses(self):
        self.assertAlmostEqual(KELVIN_OFFSET, 273.15, places=9)
        self.assertAlmostEqual(BOLTZMANN_EV_PER_K, 8.617333262e-5, places=15)
        self.assertGreater(DEFAULT_ACTIVATION_ENERGY_EV, 0.0)


class ChamberBandTests(unittest.TestCase):
    def test_the_reference_condition_sits_inside_the_band(self):
        self.assertTrue(temperature_inside_band(REFERENCE_TEMPERATURE_C))

    def test_a_chamber_exactly_on_the_lower_bound_is_inside_the_band(self):
        self.assertTrue(temperature_inside_band(MINIMUM_STRESS_TEMPERATURE_C))

    def test_a_chamber_exactly_on_the_upper_bound_is_inside_the_band(self):
        self.assertTrue(temperature_inside_band(MAXIMUM_STRESS_TEMPERATURE_C))

    def test_a_chamber_below_the_band_is_outside_it(self):
        self.assertFalse(temperature_inside_band(MINIMUM_STRESS_TEMPERATURE_C - 10.0))

    def test_a_chamber_above_the_band_is_outside_it(self):
        self.assertFalse(temperature_inside_band(MAXIMUM_STRESS_TEMPERATURE_C + 10.0))


class SoakLogTests(unittest.TestCase):
    def test_an_empty_soak_log_is_rejected(self):
        with self.assertRaises(ValueError):
            continuous_soak_segments([])

    def test_a_segment_of_zero_hours_is_rejected(self):
        with self.assertRaises(ValueError):
            continuous_soak_segments([{"hours": 0.0, "temperature_c": REFERENCE_TEMPERATURE_C}])

    def test_a_segment_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            continuous_soak_segments(["24 hours at 125"])

    def test_a_short_break_leaves_the_soak_continuous(self):
        log = [
            {
                "hours": 12.0,
                "temperature_c": REFERENCE_TEMPERATURE_C,
                "interruption_hours": MAXIMUM_INTERRUPTION_HOURS,
            },
            {"hours": 12.0, "temperature_c": REFERENCE_TEMPERATURE_C},
        ]
        result = continuous_soak_segments(log)
        self.assertEqual(result["restart_count"], 0)
        self.assertEqual(len(result["segments"]), 2)

    def test_a_long_break_discards_the_hours_before_it(self):
        log = [
            {
                "hours": 12.0,
                "temperature_c": REFERENCE_TEMPERATURE_C,
                "interruption_hours": MAXIMUM_INTERRUPTION_HOURS * 2.0,
            },
            {"hours": 20.0, "temperature_c": REFERENCE_TEMPERATURE_C},
        ]
        result = continuous_soak_segments(log)
        self.assertEqual(result["restart_count"], 1)
        self.assertEqual(len(result["segments"]), 1)

    def test_the_delivered_hours_add_across_continuous_segments(self):
        log = [
            {"hours": 10.0, "temperature_c": REFERENCE_TEMPERATURE_C},
            {"hours": 14.0, "temperature_c": REFERENCE_TEMPERATURE_C},
        ]
        self.assertAlmostEqual(delivered_equivalent_hours(log), 24.0, places=9)

    def test_a_cool_chamber_delivers_fewer_equivalent_hours_than_its_log(self):
        delivered = delivered_equivalent_hours(
            nominal_segments(temperature=MINIMUM_STRESS_TEMPERATURE_C)
        )
        self.assertLess(delivered, MINIMUM_EQUIVALENT_HOURS)

    def test_a_soak_exactly_on_the_required_hours_is_sufficient(self):
        delivered = delivered_equivalent_hours(nominal_segments())
        self.assertAlmostEqual(delivered, MINIMUM_EQUIVALENT_HOURS, places=9)
        self.assertTrue(duration_is_sufficient(delivered))

    def test_a_soak_under_the_required_hours_is_insufficient(self):
        self.assertFalse(duration_is_sufficient(MINIMUM_EQUIVALENT_HOURS / 2.0))

    def test_a_programme_may_ask_for_more_hours_than_the_default(self):
        self.assertFalse(
            duration_is_sufficient(MINIMUM_EQUIVALENT_HOURS, MINIMUM_EQUIVALENT_HOURS * 2.0)
        )


class DriftTests(unittest.TestCase):
    def test_a_parameter_that_did_not_move_has_no_drift(self):
        self.assertAlmostEqual(parameter_drift_fraction(5.0, 5.0), 0.0, places=9)

    def test_drift_is_read_as_a_fraction_of_the_pre_soak_reading(self):
        self.assertAlmostEqual(parameter_drift_fraction(5.0, 5.5), 0.1, places=9)

    def test_drift_is_read_in_both_directions(self):
        self.assertAlmostEqual(parameter_drift_fraction(5.0, 4.5), 0.1, places=9)

    def test_a_zero_pre_soak_reading_gives_no_drift_fraction(self):
        with self.assertRaises(ValueError):
            parameter_drift_fraction(0.0, 1.0)

    def test_a_parameter_exactly_on_the_allowance_is_within_it(self):
        after = 5.0 * (1.0 + DEFAULT_DRIFT_LIMIT)
        self.assertAlmostEqual(
            parameter_drift_fraction(5.0, after), DEFAULT_DRIFT_LIMIT, places=9
        )
        self.assertTrue(drift_within_limit(5.0, after))

    def test_a_parameter_past_the_allowance_is_outside_it(self):
        self.assertFalse(drift_within_limit(5.0, 5.0 * (1.0 + DEFAULT_DRIFT_LIMIT * 2.0)))

    def test_a_tighter_allowance_can_be_named_for_a_programme(self):
        self.assertFalse(drift_within_limit(5.0, 5.1, 0.01))


class ConditionGradingTests(unittest.TestCase):
    def test_every_condition_carries_a_positive_weight(self):
        for name in SOAK_CONDITIONS:
            self.assertGreater(condition_weight(name), 0.0)

    def test_every_mandatory_condition_is_a_published_condition(self):
        for name in MANDATORY_SOAK_CONDITIONS:
            self.assertIn(name, SOAK_CONDITIONS)

    def test_an_unknown_condition_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_weight("oven-looked-hot")

    def test_an_unknown_condition_state_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_state_credit("more-or-less")

    def test_a_met_condition_earns_its_full_weight(self):
        record = assess_condition(OPTIONAL_CONDITION, "met-and-recorded")
        self.assertAlmostEqual(
            record["weighted_credit"], SOAK_CONDITIONS[OPTIONAL_CONDITION], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_an_unmet_mandatory_condition_is_marked_missing(self):
        record = assess_condition(MANDATORY_CONDITION, "not-met")
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-soak-condition-not-met", record["findings"])

    def test_a_full_condition_set_reaches_a_full_index(self):
        records = [assess_condition(name, "met-and-recorded") for name in SOAK_CONDITIONS]
        self.assertAlmostEqual(condition_index(records), 1.0, places=9)

    def test_an_empty_condition_set_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_index([])


class WholeBurnInTests(unittest.TestCase):
    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_nominal_soak_on_a_stable_unit_passes(self):
        result = run()
        self.assertEqual(result["verdict"], "pre-seal-burn-in-passed")
        self.assertTrue(result["unit_passed"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["condition_index"], 1.0, places=9)

    def test_a_sealed_package_invalidates_the_run(self):
        result = run(conditions=every_condition(**{MANDATORY_CONDITION: "not-met"}))
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")
        self.assertFalse(result["unit_passed"])

    def test_an_unbiased_soak_invalidates_the_run(self):
        result = run(
            conditions=every_condition(
                **{"bias-applied-at-the-specified-condition": "not-met"}
            )
        )
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")

    def test_a_short_soak_invalidates_the_run_whatever_the_log_claims(self):
        result = run(
            segments=nominal_segments(hours=MINIMUM_EQUIVALENT_HOURS / 4.0),
            conditions=every_condition(),
        )
        self.assertFalse(result["duration_sufficient"])
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")

    def test_a_cool_chamber_can_fail_the_duration_it_appears_to_have_met(self):
        result = run(segments=nominal_segments(temperature=MINIMUM_STRESS_TEMPERATURE_C))
        self.assertLess(result["delivered_equivalent_hours"], MINIMUM_EQUIVALENT_HOURS)
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")

    def test_a_chamber_outside_the_band_invalidates_the_run(self):
        result = run(
            segments=[
                {"hours": 48.0, "temperature_c": MAXIMUM_STRESS_TEMPERATURE_C + 20.0}
            ]
        )
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")
        self.assertEqual(len(result["out_of_band_temperatures"]), 1)

    def test_a_restart_after_a_long_break_is_an_open_action_when_the_hours_hold(self):
        result = run(
            segments=[
                {
                    "hours": 12.0,
                    "temperature_c": REFERENCE_TEMPERATURE_C,
                    "interruption_hours": MAXIMUM_INTERRUPTION_HOURS * 3.0,
                },
                {"hours": MINIMUM_EQUIVALENT_HOURS, "temperature_c": REFERENCE_TEMPERATURE_C},
            ]
        )
        self.assertEqual(result["restart_count"], 1)
        self.assertEqual(result["verdict"], "pre-seal-burn-in-passed-with-open-actions")

    def test_a_drifting_parameter_rejects_the_unit(self):
        result = run(parameters=[parameter(after=5.0 * (1.0 + DEFAULT_DRIFT_LIMIT * 3.0))])
        self.assertEqual(result["verdict"], "unit-rejected-on-pre-seal-burn-in")
        self.assertEqual(result["drifted_parameters"], ["output-offset"])

    def test_an_invalid_soak_outranks_a_drifting_parameter(self):
        result = run(
            parameters=[parameter(after=50.0)],
            conditions=every_condition(**{MANDATORY_CONDITION: "not-met"}),
        )
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")

    def test_an_unrecorded_optional_condition_leaves_the_run_open(self):
        result = run(conditions=every_condition(**{OPTIONAL_CONDITION: "met-not-recorded"}))
        self.assertEqual(result["verdict"], "pre-seal-burn-in-passed-with-open-actions")
        self.assertTrue(result["unit_passed"])

    def test_a_thin_condition_record_falls_under_the_acceptance_index(self):
        result = run(
            conditions=every_condition(
                **{
                    OPTIONAL_CONDITION: "not-met",
                    "chamber-temperature-continuously-recorded": "not-met",
                }
            )
        )
        self.assertLess(result["condition_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "pre-seal-burn-in-invalid")

    def test_a_repeated_monitored_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            run(parameters=[parameter(), parameter(after=5.05)])

    def test_an_unknown_condition_in_the_input_is_rejected(self):
        with self.assertRaises(ValueError):
            run(conditions=every_condition(**{"oven-door-was-shut": "met-and-recorded"}))

    def test_a_blank_unit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(unit_id=" ")

    def test_a_non_sequence_parameter_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(parameters={"parameter": "output-offset"})


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(BURN_IN_TOLERANCE, 1e-6)

    def test_the_band_brackets_the_reference_condition(self):
        self.assertLess(MINIMUM_STRESS_TEMPERATURE_C, REFERENCE_TEMPERATURE_C)
        self.assertLess(REFERENCE_TEMPERATURE_C, MAXIMUM_STRESS_TEMPERATURE_C)

    def test_the_condition_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(CONDITION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(CONDITION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_full_condition_set(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)

    def test_the_drift_allowance_is_a_small_fraction(self):
        self.assertLess(DEFAULT_DRIFT_LIMIT, 0.5)


if __name__ == "__main__":
    unittest.main()
