"""Contract tests for the clause 5.2.18.1.1 spurious switch-off recovery.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: recovery that waits on a
command, a retrigger budget the disturbance exhausts, a recovery slower
than the load's hold-up, and the cycle count that separates the three.
"""

import unittest

from e2020_rlcl_spurious_switch_off_recovery_logic import (
    DEFAULT_RECOVERY_POLICY,
    RECOVERY_NOT_AUTONOMOUS,
    RECOVERY_SLOWER_THAN_HOLD_UP,
    RETRIGGER_BUDGET_EXHAUSTED,
    SPURIOUS_TRIP_RECOVERY_DEMONSTRATED,
    UNLIMITED_ATTEMPTS,
    assess_spurious_switch_off_recovery,
    attempts_remaining,
    disturbance_records,
    hold_up_margin,
    recovery_advisories,
    recovery_is_autonomous,
    recovery_latency,
    retrigger_cycle_period,
    retrigger_cycles_required,
    validate_disturbance,
    validate_limiter_record,
    validate_load_record,
    validate_recovery_policy,
    worst_disturbance,
)


def _policy(**overrides):
    policy = dict(DEFAULT_RECOVERY_POLICY)
    policy.update(overrides)
    return policy


def _limiter(**overrides):
    limiter = {
        "id": "rlcl-4",
        "retrigger_enabled": True,
        "autonomous_retrigger": True,
        "trip_detection_s": 0.002,
        "off_interval_s": 0.008,
        "turn_on_ramp_s": 0.001,
        "retrigger_attempts": 8,
    }
    limiter.update(overrides)
    return limiter


def _load(**overrides):
    load = {"id": "payload-front-end", "hold_up_s": 0.2}
    load.update(overrides)
    return load


def _disturbances():
    return [
        {"name": "bus-transient", "duration_s": 0.004},
        {"name": "inrush-of-neighbour", "duration_s": 0.020},
    ]


def _case(**overrides):
    case = {
        "limiter": _limiter(),
        "load": _load(),
        "disturbances": _disturbances(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_recovery_policy(DEFAULT_RECOVERY_POLICY),
            DEFAULT_RECOVERY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_recovery_policy("min_hold_up_margin")

    def test_non_boolean_autonomy_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_recovery_policy(_policy(require_autonomous_recovery="yes"))

    def test_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_recovery_policy(_policy(min_hold_up_margin=0.9))

    def test_advisory_below_the_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_recovery_policy(
                _policy(min_hold_up_margin=2.0, thin_margin_advisory=1.5)
            )

    def test_zero_attempt_headroom_advisory_rejected(self):
        with self.assertRaises(ValueError):
            validate_recovery_policy(_policy(attempt_headroom_advisory=0))


class LimiterValidationTests(unittest.TestCase):
    def test_good_limiter_validates(self):
        record = validate_limiter_record(_limiter())
        self.assertEqual(record["id"], "rlcl-4")
        self.assertEqual(record["retrigger_attempts"], 8)

    def test_non_mapping_limiter_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(["rlcl-4"])

    def test_blank_limiter_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(id="   "))

    def test_zero_off_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(off_interval_s=0.0))

    def test_negative_ramp_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(turn_on_ramp_s=-0.001))

    def test_non_boolean_retrigger_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(retrigger_enabled=1))

    def test_zero_retrigger_attempts_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(retrigger_attempts=0))

    def test_unlimited_attempts_accepted(self):
        record = validate_limiter_record(
            _limiter(retrigger_attempts=UNLIMITED_ATTEMPTS)
        )
        self.assertIs(record["retrigger_attempts"], UNLIMITED_ATTEMPTS)


class LoadAndDisturbanceTests(unittest.TestCase):
    def test_good_load_validates(self):
        self.assertAlmostEqual(validate_load_record(_load())["hold_up_s"], 0.2, places=9)

    def test_zero_hold_up_rejected(self):
        with self.assertRaises(ValueError):
            validate_load_record(_load(hold_up_s=0.0))

    def test_non_mapping_disturbance_rejected(self):
        with self.assertRaises(ValueError):
            validate_disturbance(["bus-transient"])

    def test_blank_disturbance_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_disturbance({"name": " ", "duration_s": 0.01})

    def test_negative_disturbance_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_disturbance({"name": "dip", "duration_s": -0.01})

    def test_empty_disturbance_list_rejected(self):
        with self.assertRaises(ValueError):
            disturbance_records([])

    def test_duplicate_disturbance_rejected(self):
        with self.assertRaises(ValueError):
            disturbance_records([_disturbances()[0], _disturbances()[0]])


class CycleCountTests(unittest.TestCase):
    def test_cycle_period_is_detection_plus_off_interval(self):
        self.assertAlmostEqual(retrigger_cycle_period(_limiter()), 0.010, places=9)

    def test_a_short_disturbance_costs_one_cycle(self):
        self.assertEqual(retrigger_cycles_required(_limiter(), 0.004), 1)

    def test_a_zero_length_disturbance_still_costs_one_cycle(self):
        self.assertEqual(retrigger_cycles_required(_limiter(), 0.0), 1)

    def test_a_disturbance_of_exactly_two_periods_costs_two_cycles(self):
        self.assertEqual(retrigger_cycles_required(_limiter(), 0.020), 2)

    def test_a_disturbance_a_hair_over_two_periods_costs_three(self):
        self.assertEqual(retrigger_cycles_required(_limiter(), 0.0201), 3)

    def test_a_representation_error_does_not_buy_a_whole_cycle(self):
        limiter = _limiter(trip_detection_s=0.1, off_interval_s=0.2)
        self.assertEqual(retrigger_cycles_required(limiter, 0.3 + 0.3 + 0.3), 3)

    def test_latency_adds_the_ramp_to_the_cycles(self):
        self.assertAlmostEqual(recovery_latency(_limiter(), 0.020), 0.021, places=9)


class MarginTests(unittest.TestCase):
    def test_margin_is_hold_up_over_latency(self):
        self.assertAlmostEqual(hold_up_margin(_load(), 0.05), 4.0, places=9)

    def test_zero_latency_rejected(self):
        with self.assertRaises(ValueError):
            hold_up_margin(_load(), 0.0)

    def test_autonomous_recovery_needs_both_flags(self):
        self.assertTrue(recovery_is_autonomous(_limiter()))
        self.assertFalse(recovery_is_autonomous(_limiter(retrigger_enabled=False)))
        self.assertFalse(recovery_is_autonomous(_limiter(autonomous_retrigger=False)))

    def test_spare_attempts_counted_against_the_budget(self):
        self.assertEqual(attempts_remaining(_limiter(), 2), 6)

    def test_an_unlimited_budget_reports_no_spare_count(self):
        self.assertIsNone(
            attempts_remaining(_limiter(retrigger_attempts=UNLIMITED_ATTEMPTS), 2)
        )

    def test_the_longest_recovery_governs(self):
        worst, latency = worst_disturbance(_limiter(), _disturbances())
        self.assertEqual(worst["name"], "inrush-of-neighbour")
        self.assertAlmostEqual(latency, 0.021, places=9)

    def test_a_tie_is_broken_on_the_disturbance_name(self):
        worst, _ = worst_disturbance(
            _limiter(),
            [
                {"name": "zeta-dip", "duration_s": 0.004},
                {"name": "alpha-dip", "duration_s": 0.004},
            ],
        )
        self.assertEqual(worst["name"], "alpha-dip")


class AdvisoryTests(unittest.TestCase):
    def test_a_comfortable_chain_raises_no_advisory(self):
        self.assertEqual(
            recovery_advisories(_limiter(), _load(), _disturbances()), ()
        )

    def test_a_thin_margin_is_named(self):
        advisories = recovery_advisories(
            _limiter(), _load(hold_up_s=0.035), _disturbances()
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("hold-up margin", advisories[0])

    def test_an_unlimited_budget_is_named(self):
        advisories = recovery_advisories(
            _limiter(retrigger_attempts=UNLIMITED_ATTEMPTS), _load(), _disturbances()
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("unlimited retrigger budget", advisories[0])

    def test_thin_attempt_headroom_is_named(self):
        advisories = recovery_advisories(
            _limiter(retrigger_attempts=3), _load(), _disturbances()
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("retrigger attempts left", advisories[0])

    def test_a_zero_turn_on_ramp_is_named(self):
        advisories = recovery_advisories(
            _limiter(turn_on_ramp_s=0.0), _load(), _disturbances()
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("zero turn-on ramp", advisories[0])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_chain_passes(self):
        result = assess_spurious_switch_off_recovery(_case())
        self.assertEqual(result["verdict"], SPURIOUS_TRIP_RECOVERY_DEMONSTRATED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_the_governing_numbers_are_reported(self):
        result = assess_spurious_switch_off_recovery(_case())
        self.assertEqual(result["worst_disturbance"], "inrush-of-neighbour")
        self.assertEqual(result["retrigger_cycles"], 2)
        self.assertAlmostEqual(result["recovery_latency_s"], 0.021, places=9)
        self.assertEqual(result["attempts_remaining"], 6)

    def test_retrigger_switched_off_closes_the_assessment(self):
        case = _case(limiter=_limiter(retrigger_enabled=False))
        result = assess_spurious_switch_off_recovery(case)
        self.assertEqual(result["verdict"], RECOVERY_NOT_AUTONOMOUS)
        self.assertIn("retrigger switched off", result["findings"][0])

    def test_command_dependent_recovery_closes_the_assessment(self):
        case = _case(limiter=_limiter(autonomous_retrigger=False))
        result = assess_spurious_switch_off_recovery(case)
        self.assertEqual(result["verdict"], RECOVERY_NOT_AUTONOMOUS)
        self.assertIn("external command", result["findings"][0])

    def test_autonomy_requirement_can_be_waived(self):
        case = _case(limiter=_limiter(autonomous_retrigger=False))
        result = assess_spurious_switch_off_recovery(
            case, _policy(require_autonomous_recovery=False)
        )
        self.assertEqual(result["verdict"], SPURIOUS_TRIP_RECOVERY_DEMONSTRATED)

    def test_an_exhausted_retrigger_budget_fails(self):
        case = _case(limiter=_limiter(retrigger_attempts=1))
        result = assess_spurious_switch_off_recovery(case)
        self.assertEqual(result["verdict"], RETRIGGER_BUDGET_EXHAUSTED)
        self.assertEqual(result["retrigger_cycles"], 2)

    def test_a_recovery_slower_than_the_hold_up_fails(self):
        case = _case(load=_load(hold_up_s=0.02))
        result = assess_spurious_switch_off_recovery(case)
        self.assertEqual(result["verdict"], RECOVERY_SLOWER_THAN_HOLD_UP)
        self.assertAlmostEqual(result["hold_up_margin"], 0.02 / 0.021, places=9)

    def test_a_margin_exactly_on_the_bound_passes(self):
        case = _case(load=_load(hold_up_s=0.0315))
        result = assess_spurious_switch_off_recovery(case)
        self.assertAlmostEqual(result["hold_up_margin"], 1.5, places=9)
        self.assertEqual(result["verdict"], SPURIOUS_TRIP_RECOVERY_DEMONSTRATED)

    def test_a_longer_disturbance_can_flip_a_passing_case(self):
        case = _case(
            limiter=_limiter(retrigger_attempts=UNLIMITED_ATTEMPTS),
            disturbances=[{"name": "long-brownout", "duration_s": 0.135}],
        )
        result = assess_spurious_switch_off_recovery(case)
        self.assertEqual(result["retrigger_cycles"], 14)
        self.assertAlmostEqual(result["recovery_latency_s"], 0.141, places=9)
        self.assertEqual(result["verdict"], RECOVERY_SLOWER_THAN_HOLD_UP)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_spurious_switch_off_recovery(["limiter"])

    def test_missing_disturbances_rejected(self):
        case = _case()
        del case["disturbances"]
        with self.assertRaises(ValueError):
            assess_spurious_switch_off_recovery(case)

    def test_missing_load_rejected(self):
        case = _case()
        del case["load"]
        with self.assertRaises(ValueError):
            assess_spurious_switch_off_recovery(case)


if __name__ == "__main__":
    unittest.main()
