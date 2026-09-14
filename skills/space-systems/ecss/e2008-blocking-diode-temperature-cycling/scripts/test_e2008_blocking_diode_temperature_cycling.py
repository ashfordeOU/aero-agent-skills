"""Contract tests for the clause 12.6.5 blocking diode cycling logic."""

import unittest

from e2008_blocking_diode_temperature_cycling_logic import (
    CRACKED,
    CYCLING_NOT_EVALUATED,
    DEFAULT_CYCLING_POLICY,
    DRIFT_EXCEEDED,
    FORWARD_VOLTAGE,
    MONITORED_PARAMETERS,
    PROFILE_DEFICIENT,
    REVERSE_LEAKAGE,
    RUN_VERDICTS,
    SAMPLE_CATEGORIES,
    SAMPLES_FAILED,
    SAMPLES_PASSED,
    WITHIN_DRIFT,
    assess_temperature_cycling_run,
    categorize_sample,
    cycle_amplitude_k,
    cycling_completeness,
    parameter_drift_fraction,
    ramp_rate_k_per_min,
    required_cycle_count,
    validate_cycling_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CYCLING_POLICY)
    policy.update(overrides)
    return policy


def _mission(**overrides):
    mission = {
        "eclipse_cycles_per_year": 100.0,
        "years": 10.0,
        "test_margin_factor": 1.25,
    }
    mission.update(overrides)
    return mission


def _profile(**overrides):
    profile = {
        "applied_cycles": 1250,
        "hot_plateau_c": 100.0,
        "cold_plateau_c": -100.0,
        "plateau_dwell_min": 10.0,
        "transition_min": 25.0,
    }
    profile.update(overrides)
    return profile


def _sample(identifier="s1", forward_after=0.71, leakage_after=1.02e-6, cracked=False):
    return {
        "id": identifier,
        "readings": {
            FORWARD_VOLTAGE: {"before": 0.70, "after": forward_after},
            REVERSE_LEAKAGE: {"before": 1.0e-6, "after": leakage_after},
        },
        "cracked": cracked,
    }


def _run(**overrides):
    run = {
        "mission": _mission(),
        "profile": _profile(),
        "samples": [_sample("s%d" % n) for n in range(1, 21)],
    }
    run.update(overrides)
    return run


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cycling_policy(DEFAULT_CYCLING_POLICY),
            DEFAULT_CYCLING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy("eclipse")

    def test_inverted_plateaus_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy(_policy(min_hot_plateau_c=-120.0))

    def test_an_amplitude_wider_than_the_plateaus_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy(_policy(min_cycle_amplitude_k=400.0))

    def test_a_margin_below_the_mission_itself_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy(_policy(min_test_margin_factor=0.8))

    def test_a_drift_cap_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy(_policy(max_parameter_drift_fraction=1.4))

    def test_every_verdict_parameter_and_category_is_declared(self):
        self.assertEqual(len(set(RUN_VERDICTS)), 4)
        self.assertEqual(len(set(SAMPLE_CATEGORIES)), 3)
        self.assertEqual(len(set(MONITORED_PARAMETERS)), 2)


class RequiredCycleTests(unittest.TestCase):
    def test_the_mission_sizes_the_cycle_count(self):
        self.assertEqual(required_cycle_count(_mission()), 1250)

    def test_a_fractional_count_rounds_up_never_down(self):
        mission = _mission(eclipse_cycles_per_year=90.0, years=15.0)
        self.assertEqual(required_cycle_count(mission), 1688)

    def test_a_whole_count_is_not_inflated_by_the_rounding(self):
        mission = _mission(eclipse_cycles_per_year=80.0, years=10.0)
        self.assertEqual(required_cycle_count(mission), 1000)

    def test_a_margin_under_the_policy_floor_rejected(self):
        with self.assertRaises(ValueError):
            required_cycle_count(_mission(test_margin_factor=1.0))

    def test_a_margin_exactly_at_the_policy_floor_is_accepted(self):
        policy = _policy()
        floor = float(policy["min_test_margin_factor"])
        self.assertAlmostEqual(floor, policy["min_test_margin_factor"], places=9)
        self.assertEqual(
            required_cycle_count(_mission(test_margin_factor=floor), policy), 1250
        )

    def test_a_zero_eclipse_rate_rejected(self):
        with self.assertRaises(ValueError):
            required_cycle_count(_mission(eclipse_cycles_per_year=0.0))

    def test_a_non_mapping_mission_rejected(self):
        with self.assertRaises(ValueError):
            required_cycle_count([100.0, 10.0, 1.25])


class ProfileArithmeticTests(unittest.TestCase):
    def test_amplitude_spans_both_plateaus(self):
        self.assertAlmostEqual(cycle_amplitude_k(100.0, -100.0), 200.0, places=9)

    def test_an_inverted_pair_of_plateaus_rejected(self):
        with self.assertRaises(ValueError):
            cycle_amplitude_k(-100.0, 100.0)

    def test_ramp_rate_is_the_span_over_the_transition(self):
        self.assertAlmostEqual(ramp_rate_k_per_min(200.0, 25.0), 8.0, places=9)

    def test_a_zero_transition_rejected(self):
        with self.assertRaises(ValueError):
            ramp_rate_k_per_min(200.0, 0.0)

    def test_completeness_of_a_full_run_is_one(self):
        self.assertAlmostEqual(cycling_completeness(1250, 1250), 1.0, places=12)

    def test_completeness_of_a_short_run_reports_its_share(self):
        self.assertAlmostEqual(cycling_completeness(625, 1250), 0.5, places=12)

    def test_a_zero_applied_count_rejected(self):
        with self.assertRaises(ValueError):
            cycling_completeness(0, 1250)


class DriftTests(unittest.TestCase):
    def test_no_movement_is_zero_drift(self):
        self.assertAlmostEqual(parameter_drift_fraction(0.70, 0.70), 0.0, places=12)

    def test_drift_is_relative_and_unsigned(self):
        self.assertAlmostEqual(parameter_drift_fraction(1.0, 0.9), 0.1, places=9)
        self.assertAlmostEqual(parameter_drift_fraction(1.0, 1.1), 0.1, places=9)

    def test_a_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_fraction(0.0, 0.1)


class SampleGroupingTests(unittest.TestCase):
    def test_a_quiet_sample_stays_within_drift(self):
        self.assertEqual(categorize_sample(_sample())["category"], WITHIN_DRIFT)

    def test_drift_exactly_at_the_cap_is_still_within_drift(self):
        policy = _policy()
        cap = float(policy["max_parameter_drift_fraction"])
        sample = _sample(forward_after=0.70 * (1.0 + cap))
        sentence = categorize_sample(sample, policy)
        self.assertAlmostEqual(
            sentence["parameter_drift"][FORWARD_VOLTAGE], cap, places=9
        )
        self.assertEqual(sentence["category"], WITHIN_DRIFT)

    def test_a_walked_forward_voltage_exceeds_the_drift_cap(self):
        self.assertEqual(
            categorize_sample(_sample(forward_after=0.95))["category"],
            DRIFT_EXCEEDED,
        )

    def test_a_walked_reverse_leakage_exceeds_the_drift_cap(self):
        self.assertEqual(
            categorize_sample(_sample(leakage_after=5.0e-6))["category"],
            DRIFT_EXCEEDED,
        )

    def test_a_crack_outranks_a_tidy_drift_record(self):
        self.assertEqual(categorize_sample(_sample(cracked=True))["category"], CRACKED)

    def test_the_worst_parameter_is_reported_alongside_the_category(self):
        sentence = categorize_sample(_sample(forward_after=0.95))
        self.assertAlmostEqual(
            sentence["worst_drift"],
            max(sentence["parameter_drift"].values()),
            places=12,
        )

    def test_an_unrecognised_parameter_rejected(self):
        with self.assertRaises(ValueError):
            categorize_sample({"id": "s1", "readings": {"case-temperature": {}}})

    def test_a_sample_with_no_readings_rejected(self):
        with self.assertRaises(ValueError):
            categorize_sample({"id": "s1", "readings": {}})

    def test_a_non_boolean_crack_flag_rejected(self):
        sample = _sample()
        sample["cracked"] = "yes"
        with self.assertRaises(ValueError):
            categorize_sample(sample)

    def test_a_non_mapping_sample_rejected(self):
        with self.assertRaises(ValueError):
            categorize_sample(["s1"])


class RunAssessmentTests(unittest.TestCase):
    def test_a_full_mission_equivalent_run_passes(self):
        result = assess_temperature_cycling_run(_run())
        self.assertEqual(result["verdict"], SAMPLES_PASSED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["cycling_completeness"], 1.0, places=12)

    def test_a_short_run_cannot_sentence_the_samples(self):
        result = assess_temperature_cycling_run(_run(profile=_profile(applied_cycles=600)))
        self.assertEqual(result["verdict"], CYCLING_NOT_EVALUATED)
        self.assertEqual(result["required_cycles"], 1250)

    def test_a_short_run_outranks_a_cracked_sample(self):
        samples = [_sample("s%d" % n) for n in range(1, 20)] + [
            _sample("s20", cracked=True)
        ]
        result = assess_temperature_cycling_run(
            _run(profile=_profile(applied_cycles=600), samples=samples)
        )
        self.assertEqual(result["verdict"], CYCLING_NOT_EVALUATED)

    def test_extra_cycles_beyond_the_requirement_still_pass(self):
        result = assess_temperature_cycling_run(
            _run(profile=_profile(applied_cycles=2000))
        )
        self.assertEqual(result["verdict"], SAMPLES_PASSED)

    def test_a_cycle_count_exactly_at_the_requirement_passes(self):
        run = _run()
        required = required_cycle_count(_mission())
        result = assess_temperature_cycling_run(
            _run(profile=_profile(applied_cycles=required), samples=run["samples"])
        )
        self.assertEqual(result["applied_cycles"], result["required_cycles"])
        self.assertEqual(result["verdict"], SAMPLES_PASSED)

    def test_a_shallow_hot_plateau_is_a_profile_deficiency(self):
        result = assess_temperature_cycling_run(
            _run(profile=_profile(hot_plateau_c=40.0))
        )
        self.assertEqual(result["verdict"], PROFILE_DEFICIENT)

    def test_a_shallow_cold_plateau_is_a_profile_deficiency(self):
        result = assess_temperature_cycling_run(
            _run(profile=_profile(cold_plateau_c=-40.0))
        )
        self.assertEqual(result["verdict"], PROFILE_DEFICIENT)

    def test_a_short_plateau_dwell_is_a_profile_deficiency(self):
        result = assess_temperature_cycling_run(
            _run(profile=_profile(plateau_dwell_min=1.0))
        )
        self.assertEqual(result["verdict"], PROFILE_DEFICIENT)

    def test_a_shock_fast_transition_is_a_profile_deficiency(self):
        result = assess_temperature_cycling_run(
            _run(profile=_profile(transition_min=2.0))
        )
        self.assertEqual(result["verdict"], PROFILE_DEFICIENT)
        self.assertAlmostEqual(result["ramp_rate_k_per_min"], 100.0, places=9)

    def test_a_ramp_exactly_at_the_ceiling_is_accepted(self):
        policy = _policy()
        ceiling = float(policy["max_ramp_rate_k_per_min"])
        transition = 200.0 / ceiling
        result = assess_temperature_cycling_run(
            _run(profile=_profile(transition_min=transition)), policy
        )
        self.assertAlmostEqual(result["ramp_rate_k_per_min"], ceiling, places=9)
        self.assertEqual(result["verdict"], SAMPLES_PASSED)

    def test_a_profile_deficiency_outranks_a_failed_reject_fraction(self):
        samples = [_sample("s%d" % n) for n in range(1, 18)] + [
            _sample("s18", forward_after=0.95),
            _sample("s19", forward_after=0.95),
            _sample("s20", forward_after=0.95),
        ]
        result = assess_temperature_cycling_run(
            _run(profile=_profile(hot_plateau_c=40.0), samples=samples)
        )
        self.assertEqual(result["verdict"], PROFILE_DEFICIENT)

    def test_one_cracked_sample_fails_the_lot_outright(self):
        samples = [_sample("s%d" % n) for n in range(1, 20)] + [
            _sample("s20", cracked=True)
        ]
        result = assess_temperature_cycling_run(_run(samples=samples))
        self.assertEqual(result["verdict"], SAMPLES_FAILED)
        self.assertEqual(result["cracked_samples"], 1)

    def test_a_reject_fraction_over_the_cap_fails_the_lot(self):
        samples = [_sample("s%d" % n) for n in range(1, 18)] + [
            _sample("s18", forward_after=0.95),
            _sample("s19", forward_after=0.95),
            _sample("s20", forward_after=0.95),
        ]
        result = assess_temperature_cycling_run(_run(samples=samples))
        self.assertEqual(result["verdict"], SAMPLES_FAILED)
        self.assertAlmostEqual(result["reject_fraction"], 0.15, places=12)

    def test_a_reject_fraction_exactly_at_the_cap_passes(self):
        policy = _policy(max_reject_fraction=0.10)
        samples = [_sample("s%d" % n) for n in range(1, 19)] + [
            _sample("s19", forward_after=0.95),
            _sample("s20", forward_after=0.95),
        ]
        result = assess_temperature_cycling_run(_run(samples=samples), policy)
        self.assertAlmostEqual(
            result["reject_fraction"], policy["max_reject_fraction"], places=9
        )
        self.assertEqual(result["verdict"], SAMPLES_PASSED)

    def test_every_sample_is_sentenced(self):
        result = assess_temperature_cycling_run(_run())
        self.assertEqual(len(result["sentences"]), 20)

    def test_missing_mission_block_rejected(self):
        run = _run()
        del run["mission"]
        with self.assertRaises(ValueError):
            assess_temperature_cycling_run(run)

    def test_missing_profile_block_rejected(self):
        run = _run()
        del run["profile"]
        with self.assertRaises(ValueError):
            assess_temperature_cycling_run(run)

    def test_an_empty_sample_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_cycling_run(_run(samples=[]))

    def test_a_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_cycling_run(["mission"])

    def test_a_negative_plateau_dwell_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_cycling_run(
                _run(profile=_profile(plateau_dwell_min=-5.0))
            )


if __name__ == "__main__":
    unittest.main()
