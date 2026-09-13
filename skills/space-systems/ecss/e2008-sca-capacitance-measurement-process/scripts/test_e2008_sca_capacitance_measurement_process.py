"""Contract tests for the clause 6.4.3.16.2 capacitance measurement logic."""

import math
import unittest

from e2008_sca_capacitance_measurement_process_logic import (
    CAPACITANCE_METHODS,
    DEFAULT_METHOD_POLICY,
    METHOD_ACCEPTED,
    METHOD_INADEQUATE,
    METHOD_NOT_NOMINATED,
    MORE_THAN_ONE_METHOD_OPEN,
    assess_capacitance_measurement_method,
    combined_uncertainty_percent,
    decay_time_constant_s,
    dissipation_factor,
    method_domain,
    method_inventory,
    nominate_single_method,
    ramp_slope_v_per_s,
    reactance_ohm,
    samples_in_window,
    stray_fraction,
    time_domain_observation,
    validate_method_policy,
)

ARTICLE_F = 2.0e-7


def _policy(**overrides):
    policy = dict(DEFAULT_METHOD_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "nominated_methods": ["frequency-domain-lcr-bridge"],
        "article": {
            "capacitance_f": ARTICLE_F,
            "stray_capacitance_f": 1.0e-8,
        },
        "frequency-domain": {
            "test_frequency_hz": 1.0e3,
            "leakage_resistance_ohm": 1.0e6,
        },
        "uncertainty_components_percent": [2.0, 1.5, 1.0],
    }
    case.update(overrides)
    return case


def _decay_case(**overrides):
    case = _case(
        nominated_methods=["time-domain-resistive-discharge-decay"],
    )
    case["time-domain"] = {
        "discharge_resistance_ohm": 1.0e5,
        "sample_rate_hz": 1.0e6,
    }
    case.update(overrides)
    return case


def _ramp_case(**overrides):
    case = _case(nominated_methods=["time-domain-constant-current-ramp"])
    case["time-domain"] = {
        "ramp_current_a": 1.0e-6,
        "ramp_span_v": 10.0,
        "sample_rate_hz": 1.0e3,
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_method_policy(DEFAULT_METHOD_POLICY), DEFAULT_METHOD_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_policy("bridge")

    def test_inverted_instrument_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_policy(
                _policy(meter_min_reactance_ohm=1.0e7, meter_max_reactance_ohm=10.0)
            )

    def test_a_stray_allowance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_policy(_policy(max_stray_fraction=1.0))

    def test_zero_dissipation_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_policy(_policy(max_dissipation_factor=0.0))

    def test_zero_minimum_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_policy(_policy(min_samples_in_window=0.0))


class MethodNominationTests(unittest.TestCase):
    def test_every_recognised_method_reports_a_domain(self):
        for method in CAPACITANCE_METHODS:
            self.assertIn(
                method_domain(method), ("frequency-domain", "time-domain")
            )

    def test_the_bridge_is_a_frequency_domain_method(self):
        self.assertEqual(
            method_domain("frequency-domain-lcr-bridge"), "frequency-domain"
        )

    def test_the_discharge_decay_is_a_time_domain_method(self):
        self.assertEqual(
            method_domain("time-domain-resistive-discharge-decay"), "time-domain"
        )

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            method_domain("charge-transfer-coulometer")

    def test_a_repeated_nomination_is_grouped_once(self):
        grouped = method_inventory(
            ["frequency-domain-lcr-bridge", "frequency-domain-lcr-bridge"]
        )
        self.assertEqual(grouped, ("frequency-domain-lcr-bridge",))

    def test_a_bare_string_is_not_a_method_collection(self):
        with self.assertRaises(ValueError):
            method_inventory("frequency-domain-lcr-bridge")

    def test_exactly_one_nomination_is_returned(self):
        self.assertEqual(
            nominate_single_method(["frequency-domain-lcr-bridge"]),
            "frequency-domain-lcr-bridge",
        )

    def test_an_empty_nomination_is_rejected(self):
        with self.assertRaises(ValueError):
            nominate_single_method([])

    def test_two_nominations_are_rejected(self):
        with self.assertRaises(ValueError):
            nominate_single_method(
                [
                    "frequency-domain-lcr-bridge",
                    "time-domain-resistive-discharge-decay",
                ]
            )


class FrequencyDomainTests(unittest.TestCase):
    def test_reactance_follows_the_standard_expression(self):
        expected = 1.0 / (2.0 * math.pi * 1.0e3 * ARTICLE_F)
        self.assertAlmostEqual(
            _ratio(reactance_ohm(ARTICLE_F, 1.0e3), expected), 1.0, places=12
        )

    def test_raising_the_frequency_lowers_the_reactance(self):
        low = reactance_ohm(ARTICLE_F, 1.0e3)
        high = reactance_ohm(ARTICLE_F, 1.0e5)
        self.assertAlmostEqual(_ratio(low, 100.0 * high), 1.0, places=12)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            reactance_ohm(ARTICLE_F, 0.0)

    def test_dissipation_is_reactance_over_leakage_resistance(self):
        expected = reactance_ohm(ARTICLE_F, 1.0e3) / 1.0e6
        self.assertAlmostEqual(
            _ratio(dissipation_factor(ARTICLE_F, 1.0e3, 1.0e6), expected),
            1.0,
            places=12,
        )

    def test_a_leakier_assembly_dissipates_more(self):
        tight = dissipation_factor(ARTICLE_F, 1.0e3, 1.0e6)
        leaky = dissipation_factor(ARTICLE_F, 1.0e3, 1.0e4)
        self.assertAlmostEqual(_ratio(leaky, 100.0 * tight), 1.0, places=12)

    def test_zero_leakage_resistance_rejected(self):
        with self.assertRaises(ValueError):
            dissipation_factor(ARTICLE_F, 1.0e3, 0.0)


class TimeDomainTests(unittest.TestCase):
    def test_the_decay_constant_is_the_rc_product(self):
        self.assertAlmostEqual(
            _ratio(decay_time_constant_s(ARTICLE_F, 1.0e5), 2.0e-2), 1.0, places=12
        )

    def test_the_ramp_slope_is_current_over_capacitance(self):
        self.assertAlmostEqual(
            _ratio(ramp_slope_v_per_s(1.0e-6, ARTICLE_F), 5.0), 1.0, places=12
        )

    def test_a_bigger_capacitance_ramps_more_slowly(self):
        small = ramp_slope_v_per_s(1.0e-6, ARTICLE_F)
        large = ramp_slope_v_per_s(1.0e-6, 4.0 * ARTICLE_F)
        self.assertAlmostEqual(_ratio(small, 4.0 * large), 1.0, places=12)

    def test_samples_are_window_times_rate(self):
        self.assertAlmostEqual(
            _ratio(samples_in_window(2.0e-2, 1.0e6), 2.0e4), 1.0, places=12
        )

    def test_the_decay_observation_window_is_the_time_constant(self):
        observation = time_domain_observation(
            "time-domain-resistive-discharge-decay",
            ARTICLE_F,
            {"discharge_resistance_ohm": 1.0e5, "sample_rate_hz": 1.0e6},
        )
        self.assertAlmostEqual(
            _ratio(observation["observation_window_s"], 2.0e-2), 1.0, places=12
        )
        self.assertIsNone(observation["ramp_slope_v_per_s"])

    def test_the_ramp_observation_window_is_the_span_over_the_slope(self):
        observation = time_domain_observation(
            "time-domain-constant-current-ramp",
            ARTICLE_F,
            {"ramp_current_a": 1.0e-6, "ramp_span_v": 10.0,
             "sample_rate_hz": 1.0e3},
        )
        self.assertAlmostEqual(
            _ratio(observation["observation_window_s"], 2.0), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(observation["ramp_slope_v_per_s"], 5.0), 1.0, places=12
        )

    def test_a_frequency_domain_method_has_no_time_domain_observation(self):
        with self.assertRaises(ValueError):
            time_domain_observation(
                "frequency-domain-lcr-bridge", ARTICLE_F, {"sample_rate_hz": 1.0e6}
            )

    def test_a_missing_sample_rate_rejected(self):
        with self.assertRaises(ValueError):
            time_domain_observation(
                "time-domain-resistive-discharge-decay",
                ARTICLE_F,
                {"discharge_resistance_ohm": 1.0e5},
            )


class FixtureAndUncertaintyTests(unittest.TestCase):
    def test_the_stray_fraction_is_fixture_over_article(self):
        self.assertAlmostEqual(
            _ratio(stray_fraction(1.0e-8, ARTICLE_F), 0.05), 1.0, places=12
        )

    def test_a_guarded_fixture_may_contribute_nothing(self):
        self.assertAlmostEqual(stray_fraction(0.0, ARTICLE_F), 0.0, places=12)

    def test_a_negative_stray_rejected(self):
        with self.assertRaises(ValueError):
            stray_fraction(-1.0e-9, ARTICLE_F)

    def test_the_budget_is_a_root_sum_square(self):
        self.assertAlmostEqual(
            _ratio(combined_uncertainty_percent([3.0, 4.0]), 5.0), 1.0, places=12
        )

    def test_an_empty_budget_is_rejected_not_treated_as_zero(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_percent([])

    def test_a_negative_contribution_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_percent([2.0, -1.0])


class AssessmentTests(unittest.TestCase):
    def test_an_adequate_bridge_plan_is_accepted(self):
        result = assess_capacitance_measurement_method(_case())
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["domain"], "frequency-domain")

    def test_an_adequate_decay_plan_is_accepted(self):
        result = assess_capacitance_measurement_method(_decay_case())
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)
        self.assertEqual(result["domain"], "time-domain")

    def test_an_adequate_ramp_plan_is_accepted(self):
        result = assess_capacitance_measurement_method(_ramp_case())
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)
        self.assertAlmostEqual(
            _ratio(result["observation"]["ramp_slope_v_per_s"], 5.0),
            1.0,
            places=12,
        )

    def test_no_nomination_is_its_own_verdict(self):
        result = assess_capacitance_measurement_method(_case(nominated_methods=[]))
        self.assertEqual(result["verdict"], METHOD_NOT_NOMINATED)
        self.assertIsNone(result["method"])

    def test_two_domains_left_open_is_its_own_verdict(self):
        result = assess_capacitance_measurement_method(
            _case(
                nominated_methods=[
                    "frequency-domain-lcr-bridge",
                    "time-domain-resistive-discharge-decay",
                ]
            )
        )
        self.assertEqual(result["verdict"], MORE_THAN_ONE_METHOD_OPEN)
        self.assertEqual(len(result["nominated_methods"]), 2)

    def test_an_unresolvable_reactance_is_inadequate(self):
        case = _case()
        case["frequency-domain"]["test_frequency_hz"] = 1.0e-3
        result = assess_capacitance_measurement_method(case)
        self.assertEqual(result["verdict"], METHOD_INADEQUATE)

    def test_a_lossy_article_is_inadequate(self):
        case = _case()
        case["frequency-domain"]["leakage_resistance_ohm"] = 1.0e3
        result = assess_capacitance_measurement_method(case)
        self.assertEqual(result["verdict"], METHOD_INADEQUATE)
        self.assertAlmostEqual(
            _ratio(
                result["dissipation_factor"],
                dissipation_factor(ARTICLE_F, 1.0e3, 1.0e3),
            ),
            1.0,
            places=12,
        )

    def test_a_recorder_too_slow_for_the_decay_is_inadequate(self):
        case = _decay_case()
        case["time-domain"]["sample_rate_hz"] = 1.0e2
        result = assess_capacitance_measurement_method(case)
        self.assertEqual(result["verdict"], METHOD_INADEQUATE)
        self.assertAlmostEqual(
            _ratio(result["observation"]["samples_in_window"], 2.0), 1.0, places=12
        )

    def test_a_sample_count_exactly_at_the_minimum_is_accepted(self):
        case = _decay_case()
        case["time-domain"]["sample_rate_hz"] = 1.0e3
        policy = _policy(min_samples_in_window=20.0)
        result = assess_capacitance_measurement_method(case, policy)
        self.assertAlmostEqual(
            result["observation"]["samples_in_window"],
            policy["min_samples_in_window"],
            places=9,
        )
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)

    def test_a_dominant_fixture_is_inadequate(self):
        case = _case()
        case["article"]["stray_capacitance_f"] = 1.0e-7
        result = assess_capacitance_measurement_method(case)
        self.assertEqual(result["verdict"], METHOD_INADEQUATE)
        self.assertAlmostEqual(_ratio(result["stray_fraction"], 0.5), 1.0,
                               places=12)

    def test_an_open_uncertainty_budget_is_inadequate(self):
        result = assess_capacitance_measurement_method(
            _case(uncertainty_components_percent=[10.0])
        )
        self.assertEqual(result["verdict"], METHOD_INADEQUATE)

    def test_a_stray_fraction_exactly_at_the_allowance_is_accepted(self):
        case = _case()
        case["article"]["stray_capacitance_f"] = 2.0e-8
        policy = _policy(max_stray_fraction=0.1)
        result = assess_capacitance_measurement_method(case, policy)
        self.assertAlmostEqual(
            result["stray_fraction"], policy["max_stray_fraction"], places=9
        )
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        case = _case(uncertainty_components_percent=[10.0])
        case["frequency-domain"]["test_frequency_hz"] = 1.0e-3
        case["frequency-domain"]["leakage_resistance_ohm"] = 1.0e3
        case["article"]["stray_capacitance_f"] = 1.0e-7
        result = assess_capacitance_measurement_method(case)
        self.assertEqual(len(result["findings"]), 4)

    def test_absent_nomination_key_rejected(self):
        case = _case()
        del case["nominated_methods"]
        with self.assertRaises(ValueError):
            assess_capacitance_measurement_method(case)

    def test_missing_article_block_rejected(self):
        case = _case()
        del case["article"]
        with self.assertRaises(ValueError):
            assess_capacitance_measurement_method(case)

    def test_a_missing_settings_block_for_the_nominated_domain_rejected(self):
        case = _case()
        del case["frequency-domain"]
        with self.assertRaises(ValueError):
            assess_capacitance_measurement_method(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_capacitance_measurement_method(["nominated_methods"])

    def test_an_unrecognised_nomination_rejected(self):
        with self.assertRaises(ValueError):
            assess_capacitance_measurement_method(
                _case(nominated_methods=["charge-transfer-coulometer"])
            )


if __name__ == "__main__":
    unittest.main()
