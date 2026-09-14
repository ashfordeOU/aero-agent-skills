"""Contract tests for the clause 12.6.11.2.2 blocking diode electron irradiation logic."""

import unittest

from e2008_electron_irradiation_test_process_690_logic import (
    BIAS_REVERSE,
    BIAS_SHORTED,
    DEFAULT_RUN_POLICY,
    RUN_ACCEPTED,
    RUN_BEAM_OUTSIDE_METHOD,
    RUN_CHARACTERISATION_INCOMPLETE,
    RUN_LADDER_INVALID,
    RUN_NOT_PERFORMED,
    assess_irradiation_run,
    beam_energy_error_mev,
    beam_energy_within_method,
    bias_conditions,
    control_drift_fraction,
    cumulative_fluence,
    delivered_fluence,
    fluence_reconciliation_error,
    flux_within_window,
    forward_drop_rise_v,
    ladder_reconciliation_errors,
    ladder_rises,
    leakage_growth_ratio,
    segment_fluence,
    validate_run_policy,
    validate_segment,
    validate_step,
)

CONTROL = {"pre_forward_drop_v": 0.7200, "post_forward_drop_v": 0.7205}


def _step(index, target, duration, **overrides):
    step = {
        "target_fluence_per_cm2": target,
        "bias_condition": BIAS_SHORTED,
        "segments": [{"flux_per_cm2_s": 5.0e10, "duration_s": duration}],
        "pre_forward_drop_v": [0.72, 0.74, 0.78][index],
        "post_forward_drop_v": [0.74, 0.78, 0.86][index],
        "pre_reverse_leakage_ua": [0.5, 0.7, 1.2][index],
        "post_reverse_leakage_ua": [0.7, 1.2, 3.0][index],
    }
    step.update(overrides)
    return step


def _ladder(**per_step):
    steps = [
        _step(0, 1.0e13, 200.0),
        _step(1, 3.0e13, 400.0),
        _step(2, 1.0e14, 1400.0),
    ]
    for index, overrides in per_step.items():
        steps[int(index[-1])].update(overrides)
    return steps


def _policy(**overrides):
    policy = dict(DEFAULT_RUN_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "measured_energy_mev": 1.0,
        "sample_count": 8,
        "steps": _ladder(),
        "control_part": dict(CONTROL),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_run_policy(DEFAULT_RUN_POLICY), DEFAULT_RUN_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_policy("one mev")

    def test_an_inverted_flux_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_policy(
                _policy(min_flux_per_cm2_s=1.0e11, max_flux_per_cm2_s=1.0e9)
            )

    def test_a_negative_energy_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_policy(_policy(energy_tolerance_mev=-0.05))

    def test_a_match_tolerance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_policy(_policy(fluence_match_tolerance_fraction=1.2))

    def test_a_zero_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_policy(_policy(min_sample_count=0))


class BeamTests(unittest.TestCase):
    def test_a_beam_on_the_nominal_electron_has_no_error(self):
        self.assertAlmostEqual(beam_energy_error_mev(1.0), 0.0, places=12)

    def test_a_low_beam_reports_a_negative_error(self):
        self.assertAlmostEqual(beam_energy_error_mev(0.9), -0.1, places=9)

    def test_a_beam_inside_the_tolerance_is_within_the_method(self):
        self.assertTrue(beam_energy_within_method(1.04))

    def test_a_beam_exactly_on_the_tolerance_is_still_within_the_method(self):
        self.assertTrue(beam_energy_within_method(1.05))

    def test_a_beam_well_outside_the_tolerance_is_refused(self):
        self.assertFalse(beam_energy_within_method(1.30))

    def test_a_flux_inside_the_window_is_accepted(self):
        self.assertTrue(flux_within_window(5.0e10))

    def test_a_flux_exactly_on_the_window_ceiling_is_accepted(self):
        self.assertTrue(flux_within_window(1.0e11))

    def test_a_flux_above_the_window_is_refused(self):
        self.assertFalse(flux_within_window(5.0e11))


class LadderTests(unittest.TestCase):
    def test_a_segment_delivers_its_rate_over_its_duration(self):
        fluence = segment_fluence({"flux_per_cm2_s": 5.0e10, "duration_s": 200.0})
        self.assertAlmostEqual(fluence / 1.0e13, 1.0, places=9)

    def test_a_segment_without_a_duration_is_refused(self):
        with self.assertRaises(ValueError):
            validate_segment({"flux_per_cm2_s": 5.0e10})

    def test_a_step_sums_its_segments(self):
        step = _step(0, 1.0e13, 100.0)
        step["segments"] = [
            {"flux_per_cm2_s": 5.0e10, "duration_s": 100.0},
            {"flux_per_cm2_s": 5.0e10, "duration_s": 100.0},
        ]
        self.assertAlmostEqual(delivered_fluence(step) / 1.0e13, 1.0, places=9)

    def test_a_step_with_no_exposure_segment_is_refused(self):
        with self.assertRaises(ValueError):
            delivered_fluence(_step(0, 1.0e13, 200.0, segments=[]))

    def test_an_unrecognised_bias_condition_is_refused(self):
        with self.assertRaises(ValueError):
            validate_step(_step(0, 1.0e13, 200.0, bias_condition="floating"))

    def test_a_step_missing_a_readout_is_refused(self):
        step = _step(0, 1.0e13, 200.0)
        del step["post_reverse_leakage_ua"]
        with self.assertRaises(ValueError):
            validate_step(step)

    def test_the_cumulative_fluence_runs_up_the_ladder(self):
        totals = cumulative_fluence(_ladder())
        self.assertAlmostEqual(totals[0] / 1.0e13, 1.0, places=9)
        self.assertAlmostEqual(totals[1] / 3.0e13, 1.0, places=9)
        self.assertAlmostEqual(totals[2] / 1.0e14, 1.0, places=9)

    def test_a_rising_ladder_is_recognised(self):
        self.assertTrue(ladder_rises(_ladder()))

    def test_a_repeated_fluence_point_is_not_a_rise(self):
        steps = _ladder(step1={"target_fluence_per_cm2": 1.0e13})
        self.assertFalse(ladder_rises(steps))

    def test_a_falling_ladder_is_refused(self):
        steps = _ladder(step2={"target_fluence_per_cm2": 2.0e13})
        self.assertFalse(ladder_rises(steps))

    def test_one_bias_state_is_reported_once(self):
        self.assertEqual(bias_conditions(_ladder()), (BIAS_SHORTED,))

    def test_a_changed_bias_state_is_reported_separately(self):
        steps = _ladder(step1={"bias_condition": BIAS_REVERSE})
        self.assertEqual(bias_conditions(steps), (BIAS_SHORTED, BIAS_REVERSE))

    def test_a_ladder_reaching_its_points_reconciles_to_zero(self):
        for error in ladder_reconciliation_errors(_ladder()):
            self.assertAlmostEqual(error, 0.0, places=9)

    def test_a_shortfall_reconciles_negative(self):
        self.assertAlmostEqual(
            fluence_reconciliation_error(1.0e13, 9.0e12), -0.1, places=9
        )

    def test_an_overshoot_reconciles_positive(self):
        self.assertAlmostEqual(
            fluence_reconciliation_error(1.0e13, 1.1e13), 0.1, places=9
        )

    def test_a_zero_target_has_no_reconciliation(self):
        with self.assertRaises(ValueError):
            fluence_reconciliation_error(0.0, 1.0e13)


class ReadoutTests(unittest.TestCase):
    def test_the_forward_drop_rise_is_measured_across_the_step(self):
        self.assertAlmostEqual(forward_drop_rise_v(_ladder()[2]), 0.08, places=9)

    def test_the_leakage_growth_is_a_ratio_not_a_difference(self):
        self.assertAlmostEqual(leakage_growth_ratio(_ladder()[0]), 1.4, places=9)

    def test_a_quiet_control_part_shows_almost_no_drift(self):
        self.assertLess(control_drift_fraction(CONTROL), 0.01)

    def test_a_drifting_control_part_is_measured(self):
        drift = control_drift_fraction(
            {"pre_forward_drop_v": 0.72, "post_forward_drop_v": 0.75}
        )
        self.assertAlmostEqual(drift, 0.03 / 0.72, places=9)

    def test_a_control_part_with_a_zero_reading_is_refused(self):
        with self.assertRaises(ValueError):
            control_drift_fraction(
                {"pre_forward_drop_v": 0.0, "post_forward_drop_v": 0.72}
            )


class RunVerdictTests(unittest.TestCase):
    def test_a_clean_run_is_accepted(self):
        outcome = assess_irradiation_run(_case())
        self.assertEqual(outcome["verdict"], RUN_ACCEPTED)
        self.assertEqual(outcome["findings"], [])

    def test_an_accepted_run_reports_the_whole_degradation_span(self):
        outcome = assess_irradiation_run(_case())
        self.assertAlmostEqual(outcome["forward_drop_rise_v"], 0.14, places=9)
        self.assertAlmostEqual(outcome["leakage_growth_ratio"], 6.0, places=9)

    def test_an_empty_ladder_is_not_a_run(self):
        outcome = assess_irradiation_run(_case(steps=[]))
        self.assertEqual(outcome["verdict"], RUN_NOT_PERFORMED)

    def test_an_absent_ladder_is_refused_outright(self):
        case = _case()
        del case["steps"]
        with self.assertRaises(ValueError):
            assess_irradiation_run(case)

    def test_an_unrecorded_beam_energy_is_refused_outright(self):
        case = _case()
        del case["measured_energy_mev"]
        with self.assertRaises(ValueError):
            assess_irradiation_run(case)

    def test_a_beam_off_the_nominal_electron_fails_the_method(self):
        outcome = assess_irradiation_run(_case(measured_energy_mev=1.30))
        self.assertEqual(outcome["verdict"], RUN_BEAM_OUTSIDE_METHOD)

    def test_a_segment_outside_the_rate_window_fails_the_method(self):
        steps = _ladder(
            step1={
                "segments": [{"flux_per_cm2_s": 5.0e11, "duration_s": 40.0}],
                "target_fluence_per_cm2": 3.0e13,
            }
        )
        outcome = assess_irradiation_run(_case(steps=steps))
        self.assertEqual(outcome["verdict"], RUN_BEAM_OUTSIDE_METHOD)

    def test_a_ladder_that_does_not_rise_is_invalid(self):
        steps = _ladder(step1={"target_fluence_per_cm2": 1.0e13})
        outcome = assess_irradiation_run(_case(steps=steps))
        self.assertEqual(outcome["verdict"], RUN_LADDER_INVALID)

    def test_a_mixed_bias_ladder_is_invalid(self):
        steps = _ladder(step1={"bias_condition": BIAS_REVERSE})
        outcome = assess_irradiation_run(_case(steps=steps))
        self.assertEqual(outcome["verdict"], RUN_LADDER_INVALID)
        self.assertTrue(any("bias condition" in t for t in outcome["findings"]))

    def test_a_step_that_missed_its_fluence_point_is_invalid(self):
        steps = _ladder(
            step2={
                "segments": [{"flux_per_cm2_s": 5.0e10, "duration_s": 400.0}]
            }
        )
        outcome = assess_irradiation_run(_case(steps=steps))
        self.assertEqual(outcome["verdict"], RUN_LADDER_INVALID)

    def test_a_run_with_no_control_part_is_incomplete(self):
        case = _case()
        del case["control_part"]
        outcome = assess_irradiation_run(case)
        self.assertEqual(outcome["verdict"], RUN_CHARACTERISATION_INCOMPLETE)

    def test_a_drifting_control_part_leaves_the_run_incomplete(self):
        outcome = assess_irradiation_run(
            _case(
                control_part={
                    "pre_forward_drop_v": 0.72,
                    "post_forward_drop_v": 0.75,
                }
            )
        )
        self.assertEqual(outcome["verdict"], RUN_CHARACTERISATION_INCOMPLETE)

    def test_too_few_parts_is_reported_as_its_own_finding(self):
        outcome = assess_irradiation_run(_case(sample_count=2))
        self.assertTrue(any("part(s)" in text for text in outcome["findings"]))

    def test_the_beam_verdict_wins_but_every_finding_is_still_listed(self):
        outcome = assess_irradiation_run(
            _case(measured_energy_mev=1.30, sample_count=1)
        )
        self.assertEqual(outcome["verdict"], RUN_BEAM_OUTSIDE_METHOD)
        self.assertGreaterEqual(len(outcome["findings"]), 2)


if __name__ == "__main__":
    unittest.main()
