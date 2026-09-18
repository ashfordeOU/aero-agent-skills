"""Contract tests for the clause 5.2.5.1.1 undervoltage provision assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a bus envelope that is not
an envelope, a limiter declaring no function at all, a threshold above the
operating band, a threshold under the limiter's own floor, a recovery level
the bus can never reach, a hysteresis narrow enough to chatter, and a
function fast enough to shed load on a dip the bus was built to survive.
"""

import unittest

from e2020_undervoltage_protection_provision_logic import (
    ALL_LIMITERS_PROTECTED,
    BUS_ENVELOPE_NOT_ESTABLISHED,
    DEFAULT_PROVISION_POLICY,
    HYSTERESIS_BELOW_CHATTER_FLOOR,
    PROTECTION_ABSENT,
    PROVISION_POLICY_NOT_ESTABLISHED,
    RECOVERY_ABOVE_BUS_MINIMUM,
    RESPONSE_INSIDE_SURVIVABLE_DIP,
    THRESHOLD_BELOW_OPERATING_FLOOR,
    THRESHOLD_INSIDE_STEADY_STATE_BAND,
    UNDERVOLTAGE_PROTECTION_MISPLACED,
    UNDERVOLTAGE_PROTECTION_MISSING,
    admissible_threshold_window,
    assess_undervoltage_protection_provision,
    limiter_provision_verdict,
    limiter_verdicts,
    provision_coverage_fraction,
    recovery_level_v,
    required_response_time_ms,
    validate_bus_envelope,
    validate_limiter_record,
    validate_provision_policy,
    weakest_placement,
)

BUS_MINIMUM_V = 26.0
CEILING_V = BUS_MINIMUM_V * 0.95


def _policy(**overrides):
    policy = dict(DEFAULT_PROVISION_POLICY)
    policy.update(overrides)
    return policy


def _bus(**overrides):
    bus = {
        "min_steady_state_v": BUS_MINIMUM_V,
        "max_steady_state_v": 29.0,
        "survivable_dip_floor_v": 20.0,
        "survivable_dip_duration_ms": 10.0,
    }
    bus.update(overrides)
    return bus


def _limiter(**overrides):
    limiter = {
        "id": "lcl-01",
        "undervoltage_protection_present": True,
        "min_operating_input_v": 18.0,
        "trip_threshold_v": 22.0,
        "hysteresis_v": 1.5,
        "response_time_ms": 25.0,
    }
    limiter.update(overrides)
    return limiter


def _second_limiter(**overrides):
    limiter = _limiter(
        id="lcl-02",
        min_operating_input_v=17.0,
        trip_threshold_v=23.5,
        hysteresis_v=1.2,
        response_time_ms=30.0,
    )
    limiter.update(overrides)
    return limiter


def _case(**overrides):
    case = {
        "bus_envelope": _bus(),
        "limiters": [_limiter(), _second_limiter()],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        rules = validate_provision_policy(DEFAULT_PROVISION_POLICY)
        self.assertAlmostEqual(rules["min_nuisance_margin_fraction"], 0.05, places=9)

    def test_a_nuisance_margin_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(_policy(min_nuisance_margin_fraction=1.0))

    def test_a_hysteresis_fraction_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(_policy(min_hysteresis_fraction=1.5))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(["min_hysteresis_fraction"])

    def test_a_policy_with_no_reference_closes_the_assessment(self):
        result = assess_undervoltage_protection_provision(
            _case(), _policy(policy_reference="  ")
        )
        self.assertEqual(result["verdict"], PROVISION_POLICY_NOT_ESTABLISHED)


class BusEnvelopeTests(unittest.TestCase):
    def test_the_reference_envelope_validates(self):
        envelope = validate_bus_envelope(_bus())
        self.assertAlmostEqual(envelope["min_steady_state_v"], BUS_MINIMUM_V, places=9)

    def test_a_maximum_below_the_minimum_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bus_envelope(_bus(max_steady_state_v=24.0))

    def test_a_dip_floor_at_the_steady_state_minimum_is_not_a_dip(self):
        with self.assertRaises(ValueError):
            validate_bus_envelope(_bus(survivable_dip_floor_v=BUS_MINIMUM_V))

    def test_a_zero_dip_duration_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bus_envelope(_bus(survivable_dip_duration_ms=0.0))

    def test_a_non_mapping_envelope_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bus_envelope(["min_steady_state_v"])


class LimiterRecordTests(unittest.TestCase):
    def test_a_non_boolean_provision_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(undervoltage_protection_present="yes"))

    def test_a_blank_limiter_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(id="   "))

    def test_a_declared_function_needs_a_threshold(self):
        limiter = _limiter()
        del limiter["trip_threshold_v"]
        with self.assertRaises(ValueError):
            validate_limiter_record(limiter)

    def test_a_declared_function_needs_a_response_time(self):
        limiter = _limiter()
        del limiter["response_time_ms"]
        with self.assertRaises(ValueError):
            validate_limiter_record(limiter)

    def test_an_absent_function_needs_no_settings(self):
        record = validate_limiter_record(
            {
                "id": "lcl-09",
                "undervoltage_protection_present": False,
                "min_operating_input_v": 18.0,
            }
        )
        self.assertIsNone(record["trip_threshold_v"])

    def test_a_negative_hysteresis_is_refused(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(hysteresis_v=-0.5))


class PlacementWindowTests(unittest.TestCase):
    def test_the_ceiling_is_the_bus_minimum_less_the_margin(self):
        window = admissible_threshold_window(_limiter(), _bus())
        self.assertAlmostEqual(window["ceiling_v"], CEILING_V, places=9)

    def test_the_floor_is_the_limiter_operating_minimum(self):
        window = admissible_threshold_window(_limiter(), _bus())
        self.assertAlmostEqual(window["floor_v"], 18.0, places=9)

    def test_an_operating_floor_above_the_ceiling_leaves_no_window(self):
        with self.assertRaises(ValueError):
            admissible_threshold_window(
                _limiter(min_operating_input_v=25.0, trip_threshold_v=25.5), _bus()
            )

    def test_the_recovery_level_is_the_threshold_plus_hysteresis(self):
        self.assertAlmostEqual(recovery_level_v(_limiter()), 23.5, places=9)

    def test_an_absent_function_has_no_recovery_level(self):
        with self.assertRaises(ValueError):
            recovery_level_v(
                {
                    "id": "lcl-09",
                    "undervoltage_protection_present": False,
                    "min_operating_input_v": 18.0,
                }
            )

    def test_the_required_response_rides_the_survivable_dip(self):
        self.assertAlmostEqual(
            required_response_time_ms(_limiter(), _bus()), 15.0, places=9
        )

    def test_a_threshold_under_the_dip_floor_is_never_exercised(self):
        self.assertIsNone(
            required_response_time_ms(_limiter(trip_threshold_v=19.0), _bus())
        )


class LimiterVerdictTests(unittest.TestCase):
    def test_the_reference_limiter_is_compliant(self):
        verdict = limiter_provision_verdict(_limiter(), _bus())
        self.assertTrue(verdict["compliant"])
        self.assertEqual(verdict["shortfalls"], ())

    def test_an_absent_function_reports_the_absence_alone(self):
        verdict = limiter_provision_verdict(
            {
                "id": "lcl-09",
                "undervoltage_protection_present": False,
                "min_operating_input_v": 18.0,
            },
            _bus(),
        )
        self.assertFalse(verdict["compliant"])
        self.assertEqual(verdict["shortfalls"], (PROTECTION_ABSENT,))

    def test_a_threshold_exactly_on_the_ceiling_is_admitted(self):
        verdict = limiter_provision_verdict(
            _limiter(trip_threshold_v=CEILING_V, hysteresis_v=1.0), _bus()
        )
        self.assertNotIn(THRESHOLD_INSIDE_STEADY_STATE_BAND, verdict["shortfalls"])
        self.assertAlmostEqual(
            verdict["threshold_headroom_fraction"], 0.0, places=9
        )

    def test_a_threshold_inside_the_operating_band_is_a_nuisance_trip(self):
        verdict = limiter_provision_verdict(
            _limiter(trip_threshold_v=25.5, hysteresis_v=0.6), _bus()
        )
        self.assertIn(THRESHOLD_INSIDE_STEADY_STATE_BAND, verdict["shortfalls"])

    def test_a_threshold_under_the_operating_floor_protects_nothing(self):
        verdict = limiter_provision_verdict(
            _limiter(trip_threshold_v=17.0, hysteresis_v=1.0), _bus()
        )
        self.assertIn(THRESHOLD_BELOW_OPERATING_FLOOR, verdict["shortfalls"])

    def test_a_recovery_above_the_bus_minimum_latches_the_unit_out(self):
        verdict = limiter_provision_verdict(
            _limiter(hysteresis_v=5.0), _bus()
        )
        self.assertIn(RECOVERY_ABOVE_BUS_MINIMUM, verdict["shortfalls"])

    def test_a_recovery_exactly_at_the_bus_minimum_is_admitted(self):
        verdict = limiter_provision_verdict(_limiter(hysteresis_v=4.0), _bus())
        self.assertNotIn(RECOVERY_ABOVE_BUS_MINIMUM, verdict["shortfalls"])

    def test_a_narrow_hysteresis_is_a_chatter_finding(self):
        verdict = limiter_provision_verdict(_limiter(hysteresis_v=0.1), _bus())
        self.assertIn(HYSTERESIS_BELOW_CHATTER_FLOOR, verdict["shortfalls"])

    def test_a_response_inside_the_survivable_dip_is_a_finding(self):
        verdict = limiter_provision_verdict(_limiter(response_time_ms=8.0), _bus())
        self.assertIn(RESPONSE_INSIDE_SURVIVABLE_DIP, verdict["shortfalls"])

    def test_a_response_exactly_on_the_requirement_is_admitted(self):
        verdict = limiter_provision_verdict(_limiter(response_time_ms=15.0), _bus())
        self.assertTrue(verdict["compliant"])


class AssessmentTests(unittest.TestCase):
    def test_a_fully_protected_bus_passes(self):
        result = assess_undervoltage_protection_provision(_case())
        self.assertEqual(result["verdict"], ALL_LIMITERS_PROTECTED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_bus_envelope_closes_the_assessment(self):
        case = _case()
        del case["bus_envelope"]
        result = assess_undervoltage_protection_provision(case)
        self.assertEqual(result["verdict"], BUS_ENVELOPE_NOT_ESTABLISHED)

    def test_one_unprotected_limiter_fails_the_provision(self):
        case = _case(
            limiters=[
                _limiter(),
                {
                    "id": "lcl-02",
                    "undervoltage_protection_present": False,
                    "min_operating_input_v": 17.0,
                },
            ]
        )
        result = assess_undervoltage_protection_provision(case)
        self.assertEqual(result["verdict"], UNDERVOLTAGE_PROTECTION_MISSING)
        self.assertEqual(result["unprotected_limiters"], ("lcl-02",))
        self.assertAlmostEqual(result["provision_coverage_fraction"], 0.5, places=12)

    def test_a_present_but_misplaced_function_is_reported_separately(self):
        result = assess_undervoltage_protection_provision(
            _case(limiters=[_limiter(hysteresis_v=0.1), _second_limiter()])
        )
        self.assertEqual(result["verdict"], UNDERVOLTAGE_PROTECTION_MISPLACED)
        self.assertIn("lcl-01", result["findings"][0])

    def test_the_weakest_placement_is_the_least_headroom(self):
        result = assess_undervoltage_protection_provision(_case())
        self.assertEqual(result["weakest_placement_id"], "lcl-02")

    def test_the_weakest_placement_helper_needs_a_placed_threshold(self):
        verdicts = limiter_verdicts(
            [
                {
                    "id": "lcl-09",
                    "undervoltage_protection_present": False,
                    "min_operating_input_v": 18.0,
                }
            ],
            _bus(),
        )
        with self.assertRaises(ValueError):
            weakest_placement(verdicts)

    def test_a_threshold_below_the_dip_floor_is_advised(self):
        result = assess_undervoltage_protection_provision(
            _case(limiters=[_limiter(trip_threshold_v=19.0), _second_limiter()])
        )
        self.assertTrue(
            any("never exercises" in note for note in result["advisories"])
        )

    def test_a_duplicate_limiter_id_is_refused(self):
        with self.assertRaises(ValueError):
            limiter_verdicts([_limiter(), _limiter()], _bus())

    def test_an_empty_limiter_population_is_refused(self):
        with self.assertRaises(ValueError):
            limiter_verdicts([], _bus())

    def test_the_coverage_fraction_counts_declared_functions(self):
        verdicts = limiter_verdicts([_limiter(), _second_limiter()], _bus())
        self.assertAlmostEqual(provision_coverage_fraction(verdicts), 1.0, places=12)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_undervoltage_protection_provision(["bus_envelope"])


if __name__ == "__main__":
    unittest.main()
