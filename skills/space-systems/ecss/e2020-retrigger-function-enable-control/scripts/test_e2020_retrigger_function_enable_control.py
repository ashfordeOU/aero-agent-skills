"""Contract tests for the clause 5.2.6.2.1 retrigger enable/disable control.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a design with no control
at all, a one-way inhibit dressed up as a control, a control a required
command path cannot reach, a control with no state read-back, and a
disable whose worst-case settling time runs past the declared budget.
"""

import unittest

from e2020_retrigger_function_enable_control_logic import (
    DEFAULT_CONTROL_POLICY,
    DIRECTION_DISABLE,
    DIRECTION_ENABLE,
    DISABLE_SETTLING_BUDGET_EXCEEDED,
    RETRIGGER_CONTROL_COMMANDABLE,
    RETRIGGER_CONTROL_NOT_COMMANDABLE,
    RETRIGGER_CONTROL_NOT_PROVIDED,
    assess_retrigger_enable_control,
    control_advisories,
    control_is_two_way,
    disable_settling_time_ms,
    missing_command_sources,
    settling_margin_fraction,
    settling_within_budget,
    supported_directions,
    validate_control_policy,
    validate_limiter_design,
)

BOTH_SOURCES = ("ground-telecommand", "onboard-control-procedure")


def _policy(**overrides):
    policy = dict(DEFAULT_CONTROL_POLICY)
    policy.update(overrides)
    return policy


def _design(**overrides):
    design = {
        "id": "rcl-a1",
        "enable_command_supported": True,
        "disable_command_supported": True,
        "command_sources": BOTH_SOURCES,
        "command_latency_ms": 40.0,
        "state_telemetry_provided": True,
        "dead_time_ms": 60.0,
        "trip_response_ms": 20.0,
        "command_races_dead_time": True,
    }
    design.update(overrides)
    return design


def _case(**overrides):
    case = {"limiter_design": _design()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_control_policy(DEFAULT_CONTROL_POLICY), DEFAULT_CONTROL_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_policy("max_disable_settling_ms")

    def test_empty_required_source_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_policy(_policy(required_command_sources=()))

    def test_repeated_required_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_policy(
                _policy(
                    required_command_sources=(
                        "ground-telecommand",
                        "ground-telecommand",
                    )
                )
            )

    def test_non_positive_settling_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_policy(_policy(max_disable_settling_ms=0.0))

    def test_advisory_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_policy(_policy(settling_advisory_fraction=1.4))

    def test_non_boolean_telemetry_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_policy(_policy(require_state_telemetry="yes"))


class DesignValidationTests(unittest.TestCase):
    def test_good_design_validates(self):
        checked = validate_limiter_design(_design())
        self.assertEqual(checked["id"], "rcl-a1")
        self.assertEqual(checked["command_sources"], BOTH_SOURCES)

    def test_non_mapping_design_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(["rcl-a1"])

    def test_blank_limiter_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(_design(id="   "))

    def test_non_boolean_direction_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(_design(disable_command_supported=1))

    def test_negative_command_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(_design(command_latency_ms=-5.0))

    def test_zero_dead_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(_design(dead_time_ms=0.0))

    def test_control_without_any_command_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(_design(command_sources=()))

    def test_duplicate_command_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_design(
                _design(command_sources=("ground-telecommand", "ground-telecommand"))
            )


class DirectionTests(unittest.TestCase):
    def test_both_directions_reported(self):
        self.assertEqual(
            supported_directions(_design()), (DIRECTION_ENABLE, DIRECTION_DISABLE)
        )

    def test_disable_only_is_one_way(self):
        design = _design(enable_command_supported=False)
        self.assertEqual(supported_directions(design), (DIRECTION_DISABLE,))
        self.assertFalse(control_is_two_way(design))

    def test_two_way_control_recognised(self):
        self.assertTrue(control_is_two_way(_design()))


class ReachTests(unittest.TestCase):
    def test_all_required_sources_present(self):
        self.assertEqual(missing_command_sources(_design()), ())

    def test_missing_onboard_path_named(self):
        design = _design(command_sources=("ground-telecommand",))
        self.assertEqual(
            missing_command_sources(design), ("onboard-control-procedure",)
        )

    def test_extra_command_path_is_not_a_finding(self):
        design = _design(command_sources=BOTH_SOURCES + ("test-harness-command",))
        self.assertEqual(missing_command_sources(design), ())


class SettlingTests(unittest.TestCase):
    def test_racing_disable_carries_one_more_cycle(self):
        self.assertAlmostEqual(
            disable_settling_time_ms(_design()), 120.0, places=9
        )

    def test_non_racing_disable_is_the_command_latency(self):
        design = _design(command_races_dead_time=False)
        self.assertAlmostEqual(disable_settling_time_ms(design), 40.0, places=9)

    def test_settling_exactly_on_budget_is_admissible(self):
        design = _design(command_latency_ms=170.0)
        self.assertAlmostEqual(disable_settling_time_ms(design), 250.0, places=9)
        self.assertTrue(settling_within_budget(design))

    def test_settling_past_budget_is_not_admissible(self):
        self.assertFalse(settling_within_budget(_design(command_latency_ms=200.0)))

    def test_margin_fraction_is_zero_on_the_budget(self):
        design = _design(command_latency_ms=170.0)
        self.assertAlmostEqual(settling_margin_fraction(design), 0.0, places=9)

    def test_margin_fraction_on_the_base_design(self):
        self.assertAlmostEqual(settling_margin_fraction(_design()), 0.52, places=9)


class AdvisoryTests(unittest.TestCase):
    def test_comfortable_design_raises_no_advisory(self):
        self.assertEqual(control_advisories(_design()), ())

    def test_single_command_path_raises_an_advisory(self):
        design = _design(
            command_sources=("ground-telecommand",),
        )
        policy = _policy(required_command_sources=("ground-telecommand",))
        advisories = control_advisories(design, policy)
        self.assertEqual(len(advisories), 1)
        self.assertIn("single", advisories[0])

    def test_settling_inside_the_advisory_band_is_named(self):
        advisories = control_advisories(_design(command_latency_ms=170.0))
        self.assertEqual(len(advisories), 1)
        self.assertIn("advisory band", advisories[0])

    def test_a_no_race_claim_is_flagged_for_evidence(self):
        advisories = control_advisories(_design(command_races_dead_time=False))
        self.assertEqual(len(advisories), 1)
        self.assertIn("cannot race", advisories[0])


class AssessmentTests(unittest.TestCase):
    def test_compliant_design_passes(self):
        result = assess_retrigger_enable_control(_case())
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_COMMANDABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_absent_design_closes_as_not_provided(self):
        result = assess_retrigger_enable_control({})
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_NOT_PROVIDED)
        self.assertEqual(len(result["findings"]), 1)

    def test_no_direction_at_all_closes_as_not_provided(self):
        case = _case(
            limiter_design=_design(
                enable_command_supported=False, disable_command_supported=False
            )
        )
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_NOT_PROVIDED)

    def test_one_way_inhibit_is_not_a_control(self):
        case = _case(limiter_design=_design(enable_command_supported=False))
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_NOT_COMMANDABLE)
        self.assertIn("inhibit", result["findings"][0])

    def test_unreachable_control_is_not_commandable(self):
        case = _case(
            limiter_design=_design(command_sources=("ground-telecommand",))
        )
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_NOT_COMMANDABLE)
        self.assertEqual(
            result["missing_command_sources"], ("onboard-control-procedure",)
        )

    def test_missing_state_readback_is_not_commandable(self):
        case = _case(limiter_design=_design(state_telemetry_provided=False))
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_NOT_COMMANDABLE)

    def test_read_back_may_be_waived_by_policy(self):
        case = _case(limiter_design=_design(state_telemetry_provided=False))
        result = assess_retrigger_enable_control(
            case, _policy(require_state_telemetry=False)
        )
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_COMMANDABLE)

    def test_every_reach_finding_is_named_not_only_the_first(self):
        case = _case(
            limiter_design=_design(
                command_sources=("ground-telecommand",),
                state_telemetry_provided=False,
                enable_command_supported=False,
            )
        )
        result = assess_retrigger_enable_control(case)
        self.assertEqual(len(result["findings"]), 3)

    def test_slow_settling_closes_on_the_budget_verdict(self):
        case = _case(limiter_design=_design(command_latency_ms=200.0))
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], DISABLE_SETTLING_BUDGET_EXCEEDED)
        self.assertAlmostEqual(result["disable_settling_ms"], 280.0, places=9)

    def test_settling_on_the_budget_still_passes(self):
        case = _case(limiter_design=_design(command_latency_ms=170.0))
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_COMMANDABLE)
        self.assertAlmostEqual(result["settling_margin_fraction"], 0.0, places=9)

    def test_advisories_do_not_move_the_verdict(self):
        case = _case(limiter_design=_design(command_races_dead_time=False))
        result = assess_retrigger_enable_control(case)
        self.assertEqual(result["verdict"], RETRIGGER_CONTROL_COMMANDABLE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_retrigger_enable_control(["limiter_design"])

    def test_budget_is_echoed_with_the_verdict(self):
        result = assess_retrigger_enable_control(_case())
        self.assertAlmostEqual(result["settling_budget_ms"], 250.0, places=9)


if __name__ == "__main__":
    unittest.main()
