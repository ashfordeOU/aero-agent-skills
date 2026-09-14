"""Contract tests for the clause 9.6.16 human body ESD survival logic."""

import unittest

from e2008_diode_human_body_esd_logic import (
    DEFAULT_HBM_POLICY,
    HBM_NETWORK_DEFICIENT,
    HBM_NOMINAL_CAPACITANCE_F,
    HBM_NOMINAL_RESISTANCE_OHM,
    HBM_STRESS_PLAN_DEFICIENT,
    HBM_SURVIVAL_ACCEPTED,
    HBM_VERDICTS,
    HBM_WITHSTAND_DEFICIENT,
    REQUIRED_POLARITIES,
    assess_hbm_survival,
    hbm_decay_time_constant_s,
    hbm_peak_current_a,
    hbm_stored_energy_j,
    hbm_transferred_charge_c,
    hbm_withstand_band,
    parameter_drift_fraction,
    polarity_coverage,
    step_series_voltages,
    validate_hbm_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_HBM_POLICY)
    policy.update(overrides)
    return policy


def _plan(**overrides):
    plan = {
        "network_capacitance_f": HBM_NOMINAL_CAPACITANCE_F,
        "network_resistance_ohm": HBM_NOMINAL_RESISTANCE_OHM,
        "start_voltage_v": 250.0,
        "step_ratio": 2.0,
        "step_levels": 4,
        "pulses_per_level": 3,
        "recovery_interval_s": 1.0,
        "pulse_polarities": ["positive", "negative"],
    }
    plan.update(overrides)
    return plan


def _response(**overrides):
    response = {
        "withstand_voltage_v": 2000.0,
        "initial_leakage_a": 1.0e-8,
        "final_leakage_a": 1.2e-8,
        "initial_forward_voltage_v": 0.720,
        "final_forward_voltage_v": 0.726,
    }
    response.update(overrides)
    return response


def _case(**overrides):
    case = {"stress_plan": _plan(), "device_response": _response()}
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_hbm_policy(DEFAULT_HBM_POLICY), DEFAULT_HBM_POLICY)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_hbm_policy("human body")

    def test_an_inverted_capacitance_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_hbm_policy(_policy(min_network_capacitance_f=200e-12))

    def test_an_inverted_resistance_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_hbm_policy(_policy(min_network_resistance_ohm=2000.0))

    def test_a_step_ratio_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_hbm_policy(_policy(min_step_ratio=1.0))

    def test_a_fractional_pulse_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_hbm_policy(_policy(min_pulses_per_level=2.5))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(HBM_VERDICTS)), 4)


class NetworkTests(unittest.TestCase):
    def test_peak_current_is_the_step_across_the_body_resistance(self):
        self.assertAlmostEqual(
            _ratio(hbm_peak_current_a(1500.0, 1500.0), 1.0), 1.0, places=12
        )

    def test_a_higher_step_drives_a_higher_peak(self):
        low = hbm_peak_current_a(500.0)
        high = hbm_peak_current_a(4000.0)
        self.assertGreater(high, low)

    def test_the_decay_constant_is_the_resistance_capacitance_product(self):
        expected = HBM_NOMINAL_RESISTANCE_OHM * HBM_NOMINAL_CAPACITANCE_F
        self.assertAlmostEqual(
            _ratio(hbm_decay_time_constant_s(), expected), 1.0, places=12
        )

    def test_stored_energy_follows_the_square_of_the_step(self):
        single = hbm_stored_energy_j(1000.0)
        double = hbm_stored_energy_j(2000.0)
        self.assertAlmostEqual(_ratio(double, single), 4.0, places=9)

    def test_transferred_charge_is_linear_in_the_step(self):
        expected = HBM_NOMINAL_CAPACITANCE_F * 2000.0
        self.assertAlmostEqual(
            _ratio(hbm_transferred_charge_c(2000.0), expected), 1.0, places=12
        )

    def test_a_zero_step_voltage_rejected(self):
        with self.assertRaises(ValueError):
            hbm_peak_current_a(0.0)

    def test_a_negative_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            hbm_stored_energy_j(1000.0, -1.0e-12)

    def test_a_boolean_step_voltage_rejected(self):
        with self.assertRaises(ValueError):
            hbm_peak_current_a(True)


class StepSeriesTests(unittest.TestCase):
    def test_the_ladder_starts_at_the_declared_step(self):
        series = step_series_voltages(250.0, 2.0, 4)
        self.assertAlmostEqual(series[0], 250.0, places=9)

    def test_the_ladder_has_one_entry_per_level(self):
        self.assertEqual(len(step_series_voltages(250.0, 2.0, 5)), 5)

    def test_each_level_climbs_by_the_ratio(self):
        series = step_series_voltages(250.0, 2.0, 4)
        self.assertAlmostEqual(_ratio(series[3], series[2]), 2.0, places=9)

    def test_a_ratio_of_one_rejected(self):
        with self.assertRaises(ValueError):
            step_series_voltages(250.0, 1.0, 4)

    def test_a_zero_level_ladder_rejected(self):
        with self.assertRaises(ValueError):
            step_series_voltages(250.0, 2.0, 0)


class WithstandBandTests(unittest.TestCase):
    def test_a_low_survivor_lands_in_the_first_band(self):
        self.assertEqual(hbm_withstand_band(100.0), "hbm-band-a")

    def test_a_level_exactly_on_a_band_floor_takes_that_band(self):
        self.assertEqual(hbm_withstand_band(1000.0), "hbm-band-d")

    def test_a_level_just_below_a_floor_stays_in_the_band_below(self):
        self.assertEqual(hbm_withstand_band(999.0), "hbm-band-c")

    def test_the_top_band_absorbs_everything_above_it(self):
        self.assertEqual(hbm_withstand_band(9000.0), "hbm-band-f")

    def test_a_negative_withstand_rejected(self):
        with self.assertRaises(ValueError):
            hbm_withstand_band(-10.0)


class DriftAndPolarityTests(unittest.TestCase):
    def test_a_doubled_leakage_is_a_drift_of_one(self):
        self.assertAlmostEqual(parameter_drift_fraction(1.0e-8, 2.0e-8), 1.0, places=9)

    def test_an_unchanged_parameter_has_no_drift(self):
        self.assertAlmostEqual(parameter_drift_fraction(0.72, 0.72), 0.0, places=12)

    def test_drift_is_taken_in_either_direction(self):
        fell = parameter_drift_fraction(0.72, 0.68)
        rose = parameter_drift_fraction(0.72, 0.76)
        self.assertGreater(fell, 0.0)
        self.assertGreater(rose, 0.0)

    def test_a_zero_starting_value_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_fraction(0.0, 1.0e-8)

    def test_both_polarities_are_counted_once_each(self):
        self.assertEqual(polarity_coverage(["positive", "negative", "positive"]), 2)

    def test_a_single_polarity_plan_covers_one(self):
        self.assertEqual(polarity_coverage(["positive"]), 1)

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            polarity_coverage(["positive", "sideways"])

    def test_an_empty_polarity_list_rejected(self):
        with self.assertRaises(ValueError):
            polarity_coverage([])


class SurvivalAssessmentTests(unittest.TestCase):
    def test_a_nominal_campaign_is_accepted(self):
        result = assess_hbm_survival(_case())
        self.assertEqual(result["verdict"], HBM_SURVIVAL_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_network_derived_quantities_are_reported(self):
        result = assess_hbm_survival(_case())
        self.assertAlmostEqual(
            _ratio(
                result["peak_current_a"],
                2000.0 / HBM_NOMINAL_RESISTANCE_OHM,
            ),
            1.0,
            places=12,
        )
        self.assertAlmostEqual(
            _ratio(
                result["stored_energy_j"],
                0.5 * HBM_NOMINAL_CAPACITANCE_F * 2000.0 * 2000.0,
            ),
            1.0,
            places=12,
        )
        self.assertTrue(result["network_in_band"])

    def test_a_withstand_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        floor = float(policy["min_withstand_voltage_v"])
        result = assess_hbm_survival(
            _case(device_response=_response(withstand_voltage_v=floor)), policy
        )
        self.assertAlmostEqual(result["withstand_voltage_v"], floor, places=9)
        self.assertEqual(result["verdict"], HBM_SURVIVAL_ACCEPTED)

    def test_a_short_withstand_is_a_withstand_deficiency(self):
        result = assess_hbm_survival(
            _case(device_response=_response(withstand_voltage_v=250.0))
        )
        self.assertEqual(result["verdict"], HBM_WITHSTAND_DEFICIENT)
        self.assertEqual(result["withstand_band"], "hbm-band-b")

    def test_grown_leakage_is_a_withstand_deficiency(self):
        result = assess_hbm_survival(
            _case(device_response=_response(final_leakage_a=5.0e-8))
        )
        self.assertEqual(result["verdict"], HBM_WITHSTAND_DEFICIENT)
        self.assertGreater(result["leakage_drift_fraction"], 1.0)

    def test_a_shifted_forward_voltage_is_a_withstand_deficiency(self):
        result = assess_hbm_survival(
            _case(device_response=_response(final_forward_voltage_v=0.900))
        )
        self.assertEqual(result["verdict"], HBM_WITHSTAND_DEFICIENT)

    def test_a_leakage_drift_exactly_at_the_limit_is_accepted(self):
        policy = _policy()
        limit = float(policy["max_leakage_drift_fraction"])
        start = 1.0e-8
        result = assess_hbm_survival(
            _case(
                device_response=_response(
                    initial_leakage_a=start, final_leakage_a=start * (1.0 + limit)
                )
            ),
            policy,
        )
        self.assertAlmostEqual(result["leakage_drift_fraction"], limit, places=9)
        self.assertEqual(result["verdict"], HBM_SURVIVAL_ACCEPTED)

    def test_an_out_of_band_capacitance_invalidates_the_campaign(self):
        result = assess_hbm_survival(
            _case(stress_plan=_plan(network_capacitance_f=330e-12))
        )
        self.assertEqual(result["verdict"], HBM_NETWORK_DEFICIENT)
        self.assertFalse(result["network_in_band"])

    def test_an_out_of_band_series_resistance_invalidates_the_campaign(self):
        result = assess_hbm_survival(
            _case(stress_plan=_plan(network_resistance_ohm=330.0))
        )
        self.assertEqual(result["verdict"], HBM_NETWORK_DEFICIENT)

    def test_the_network_outranks_a_short_withstand(self):
        result = assess_hbm_survival(
            _case(
                stress_plan=_plan(network_resistance_ohm=330.0),
                device_response=_response(withstand_voltage_v=250.0),
            )
        )
        self.assertEqual(result["verdict"], HBM_NETWORK_DEFICIENT)

    def test_a_single_pulse_per_level_is_a_plan_deficiency(self):
        result = assess_hbm_survival(_case(stress_plan=_plan(pulses_per_level=1)))
        self.assertEqual(result["verdict"], HBM_STRESS_PLAN_DEFICIENT)

    def test_one_polarity_only_is_a_plan_deficiency(self):
        result = assess_hbm_survival(
            _case(stress_plan=_plan(pulse_polarities=["positive"]))
        )
        self.assertEqual(result["verdict"], HBM_STRESS_PLAN_DEFICIENT)
        self.assertEqual(result["polarity_coverage"], 1)
        self.assertEqual(len(REQUIRED_POLARITIES), 2)

    def test_a_short_ladder_is_a_plan_deficiency(self):
        result = assess_hbm_survival(_case(stress_plan=_plan(step_levels=2)))
        self.assertEqual(result["verdict"], HBM_STRESS_PLAN_DEFICIENT)

    def test_a_shallow_ladder_is_a_plan_deficiency(self):
        result = assess_hbm_survival(_case(stress_plan=_plan(step_ratio=1.05)))
        self.assertEqual(result["verdict"], HBM_STRESS_PLAN_DEFICIENT)

    def test_a_short_recovery_interval_is_a_plan_deficiency(self):
        result = assess_hbm_survival(
            _case(stress_plan=_plan(recovery_interval_s=0.001))
        )
        self.assertEqual(result["verdict"], HBM_STRESS_PLAN_DEFICIENT)

    def test_a_withstand_deficiency_outranks_a_plan_deficiency(self):
        result = assess_hbm_survival(
            _case(
                stress_plan=_plan(pulses_per_level=1),
                device_response=_response(withstand_voltage_v=250.0),
            )
        )
        self.assertEqual(result["verdict"], HBM_WITHSTAND_DEFICIENT)

    def test_every_plan_finding_is_reported_not_only_the_first(self):
        result = assess_hbm_survival(
            _case(
                stress_plan=_plan(
                    pulses_per_level=1, step_levels=2, recovery_interval_s=0.001
                )
            )
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_a_missing_stress_plan_rejected(self):
        case = _case()
        del case["stress_plan"]
        with self.assertRaises(ValueError):
            assess_hbm_survival(case)

    def test_a_missing_device_response_rejected(self):
        case = _case()
        del case["device_response"]
        with self.assertRaises(ValueError):
            assess_hbm_survival(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_hbm_survival(["stress_plan"])

    def test_a_negative_recovery_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_hbm_survival(_case(stress_plan=_plan(recovery_interval_s=-1.0)))


if __name__ == "__main__":
    unittest.main()
