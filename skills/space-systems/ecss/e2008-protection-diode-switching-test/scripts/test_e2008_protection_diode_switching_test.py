"""Contract tests for the clause 9.6.17 switching transient survival logic."""

import unittest

from e2008_protection_diode_switching_test_logic import (
    DEFAULT_SWITCHING_POLICY,
    GROUND_HANDLING,
    IN_ORBIT_SWITCHING,
    SWITCHING_BREAKDOWN_RISK,
    SWITCHING_EVENT_CATEGORIES,
    SWITCHING_EVENT_PLAN_DEFICIENT,
    SWITCHING_EXCURSION_EXCESSIVE,
    SWITCHING_SURVIVAL_ACCEPTED,
    SWITCHING_VERDICTS,
    absorbed_pulse_energy_j,
    assess_switching_survival,
    clamp_duration_s,
    derated_standoff_v,
    event_pulse_counts,
    inductive_overshoot_v,
    junction_excursion_k,
    peak_clamp_power_w,
    standoff_margin_fraction,
    transient_peak_voltage_v,
    validate_switching_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_SWITCHING_POLICY)
    policy.update(overrides)
    return policy


def _circuit(**overrides):
    circuit = {
        "standing_voltage_v": 40.0,
        "stray_inductance_h": 20.0e-6,
        "current_slew_a_per_s": 1.0e6,
        "switched_current_a": 5.0,
        "recovery_interval_s": 2.0,
    }
    circuit.update(overrides)
    return circuit


def _device(**overrides):
    device = {
        "reverse_standoff_v": 100.0,
        "derating_factor": 0.75,
        "transient_thermal_impedance_k_per_w": 0.05,
        "case_temperature_c": 60.0,
    }
    device.update(overrides)
    return device


def _events(ground=12, orbit=60):
    return [
        {"category": GROUND_HANDLING, "pulse_count": ground},
        {"category": IN_ORBIT_SWITCHING, "pulse_count": orbit},
    ]


def _case(**overrides):
    case = {
        "circuit": _circuit(),
        "device": _device(),
        "event_plan": _events(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_switching_policy(DEFAULT_SWITCHING_POLICY),
            DEFAULT_SWITCHING_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_switching_policy("derate it")

    def test_a_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_switching_policy(_policy(max_derating_factor=1.4))

    def test_a_margin_floor_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_switching_policy(_policy(min_standoff_margin_fraction=1.0))

    def test_a_negative_margin_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_switching_policy(_policy(min_standoff_margin_fraction=-0.1))

    def test_a_fractional_pulse_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_switching_policy(_policy(min_ground_handling_pulses=10.5))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(SWITCHING_VERDICTS)), 4)

    def test_both_event_categories_are_declared(self):
        self.assertEqual(len(set(SWITCHING_EVENT_CATEGORIES)), 2)


class TransientTests(unittest.TestCase):
    def test_the_overshoot_is_the_inductance_times_the_slew(self):
        self.assertAlmostEqual(
            _ratio(inductive_overshoot_v(20.0e-6, 1.0e6), 20.0), 1.0, places=12
        )

    def test_a_faster_interruption_throws_a_larger_overshoot(self):
        slow = inductive_overshoot_v(20.0e-6, 1.0e5)
        fast = inductive_overshoot_v(20.0e-6, 1.0e7)
        self.assertGreater(fast, slow)

    def test_the_peak_sits_on_top_of_the_standing_rail(self):
        peak = transient_peak_voltage_v(40.0, 20.0e-6, 1.0e6)
        self.assertAlmostEqual(_ratio(peak, 60.0), 1.0, places=12)

    def test_a_lossless_harness_still_needs_an_inductance(self):
        with self.assertRaises(ValueError):
            inductive_overshoot_v(0.0, 1.0e6)

    def test_a_negative_slew_rejected(self):
        with self.assertRaises(ValueError):
            inductive_overshoot_v(20.0e-6, -1.0e6)

    def test_a_boolean_standing_voltage_rejected(self):
        with self.assertRaises(ValueError):
            transient_peak_voltage_v(True, 20.0e-6, 1.0e6)


class EnergyAndThermalTests(unittest.TestCase):
    def test_absorbed_energy_is_half_the_field(self):
        expected = 0.5 * 20.0e-6 * 25.0
        self.assertAlmostEqual(
            _ratio(absorbed_pulse_energy_j(20.0e-6, 5.0), expected), 1.0, places=12
        )

    def test_absorbed_energy_follows_the_square_of_the_current(self):
        single = absorbed_pulse_energy_j(20.0e-6, 5.0)
        double = absorbed_pulse_energy_j(20.0e-6, 10.0)
        self.assertAlmostEqual(_ratio(double, single), 4.0, places=9)

    def test_peak_clamp_power_is_the_peak_at_the_switched_current(self):
        self.assertAlmostEqual(
            _ratio(peak_clamp_power_w(60.0, 5.0), 300.0), 1.0, places=12
        )

    def test_the_clamp_empties_the_energy_at_that_power(self):
        energy = absorbed_pulse_energy_j(20.0e-6, 5.0)
        power = peak_clamp_power_w(60.0, 5.0)
        expected = 2.0 * energy / power
        self.assertAlmostEqual(
            _ratio(clamp_duration_s(energy, power), expected), 1.0, places=12
        )

    def test_the_excursion_is_the_power_through_the_impedance(self):
        self.assertAlmostEqual(
            _ratio(junction_excursion_k(300.0, 0.05), 15.0), 1.0, places=12
        )

    def test_a_stiffer_package_steps_the_junction_less(self):
        stiff = junction_excursion_k(300.0, 0.01)
        soft = junction_excursion_k(300.0, 0.20)
        self.assertGreater(soft, stiff)

    def test_a_zero_thermal_impedance_rejected(self):
        with self.assertRaises(ValueError):
            junction_excursion_k(300.0, 0.0)

    def test_a_zero_power_clamp_duration_rejected(self):
        with self.assertRaises(ValueError):
            clamp_duration_s(2.5e-4, 0.0)


class StandoffTests(unittest.TestCase):
    def test_derating_cuts_the_face_rating(self):
        self.assertAlmostEqual(
            _ratio(derated_standoff_v(100.0, 0.75), 75.0), 1.0, places=12
        )

    def test_a_derating_factor_of_one_is_the_face_rating(self):
        self.assertAlmostEqual(derated_standoff_v(100.0, 1.0), 100.0, places=9)

    def test_a_derating_factor_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            derated_standoff_v(100.0, 0.0)

    def test_a_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            derated_standoff_v(100.0, 1.2)

    def test_the_margin_is_the_unused_share_of_the_derated_rating(self):
        self.assertAlmostEqual(standoff_margin_fraction(60.0, 75.0), 0.2, places=9)

    def test_a_peak_above_the_derated_rating_gives_a_negative_margin(self):
        self.assertLess(standoff_margin_fraction(90.0, 75.0), 0.0)

    def test_a_peak_exactly_on_the_derated_rating_leaves_no_margin(self):
        self.assertAlmostEqual(standoff_margin_fraction(75.0, 75.0), 0.0, places=12)


class EventPlanTests(unittest.TestCase):
    def test_pulses_are_counted_per_category(self):
        counts = event_pulse_counts(_events(ground=12, orbit=60))
        self.assertEqual(counts[GROUND_HANDLING], 12)
        self.assertEqual(counts[IN_ORBIT_SWITCHING], 60)

    def test_repeated_entries_in_one_category_add_up(self):
        counts = event_pulse_counts(
            [
                {"category": GROUND_HANDLING, "pulse_count": 5},
                {"category": GROUND_HANDLING, "pulse_count": 7},
                {"category": IN_ORBIT_SWITCHING, "pulse_count": 60},
            ]
        )
        self.assertEqual(counts[GROUND_HANDLING], 12)

    def test_a_missing_category_counts_zero(self):
        counts = event_pulse_counts(
            [{"category": IN_ORBIT_SWITCHING, "pulse_count": 60}]
        )
        self.assertEqual(counts[GROUND_HANDLING], 0)

    def test_an_unrecognised_category_rejected(self):
        with self.assertRaises(ValueError):
            event_pulse_counts([{"category": "launch-twang", "pulse_count": 3}])

    def test_an_empty_event_plan_rejected(self):
        with self.assertRaises(ValueError):
            event_pulse_counts([])

    def test_a_fractional_pulse_count_rejected(self):
        with self.assertRaises(ValueError):
            event_pulse_counts([{"category": GROUND_HANDLING, "pulse_count": 2.5}])


class SwitchingAssessmentTests(unittest.TestCase):
    def test_a_nominal_campaign_is_accepted(self):
        result = assess_switching_survival(_case())
        self.assertEqual(result["verdict"], SWITCHING_SURVIVAL_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_derived_transient_quantities_are_reported(self):
        result = assess_switching_survival(_case())
        self.assertAlmostEqual(_ratio(result["transient_peak_v"], 60.0), 1.0, places=12)
        self.assertAlmostEqual(
            _ratio(result["derated_standoff_v"], 75.0), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["junction_excursion_k"], 15.0), 1.0, places=12
        )
        self.assertGreater(result["clamp_duration_s"], 0.0)

    def test_a_margin_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_switching_survival(
            _case(circuit=_circuit(standing_voltage_v=47.5)), policy
        )
        self.assertAlmostEqual(
            result["standoff_margin_fraction"],
            policy["min_standoff_margin_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], SWITCHING_SURVIVAL_ACCEPTED)

    def test_an_uncontrolled_slew_takes_the_diode_into_breakdown(self):
        result = assess_switching_survival(
            _case(circuit=_circuit(current_slew_a_per_s=4.0e6))
        )
        self.assertEqual(result["verdict"], SWITCHING_BREAKDOWN_RISK)
        self.assertLess(result["standoff_margin_fraction"], 0.10)

    def test_a_long_harness_takes_the_diode_into_breakdown(self):
        result = assess_switching_survival(
            _case(circuit=_circuit(stray_inductance_h=60.0e-6))
        )
        self.assertEqual(result["verdict"], SWITCHING_BREAKDOWN_RISK)

    def test_breakdown_outranks_a_thin_event_plan(self):
        result = assess_switching_survival(
            _case(
                circuit=_circuit(current_slew_a_per_s=4.0e6),
                event_plan=_events(ground=1, orbit=1),
            )
        )
        self.assertEqual(result["verdict"], SWITCHING_BREAKDOWN_RISK)

    def test_a_soft_package_makes_the_excursion_excessive(self):
        result = assess_switching_survival(
            _case(device=_device(transient_thermal_impedance_k_per_w=0.40))
        )
        self.assertEqual(result["verdict"], SWITCHING_EXCURSION_EXCESSIVE)
        self.assertGreater(result["junction_excursion_k"], 25.0)

    def test_a_hot_case_pushes_the_peak_junction_past_its_ceiling(self):
        result = assess_switching_survival(
            _case(device=_device(case_temperature_c=118.0))
        )
        self.assertEqual(result["verdict"], SWITCHING_EXCURSION_EXCESSIVE)
        self.assertGreater(result["peak_junction_temperature_c"], 125.0)

    def test_the_excursion_outranks_a_thin_event_plan(self):
        result = assess_switching_survival(
            _case(
                device=_device(transient_thermal_impedance_k_per_w=0.40),
                event_plan=_events(ground=1, orbit=1),
            )
        )
        self.assertEqual(result["verdict"], SWITCHING_EXCURSION_EXCESSIVE)

    def test_too_few_ground_handling_pulses_is_a_plan_deficiency(self):
        result = assess_switching_survival(_case(event_plan=_events(ground=2)))
        self.assertEqual(result["verdict"], SWITCHING_EVENT_PLAN_DEFICIENT)

    def test_in_orbit_pulses_do_not_fill_the_ground_handling_count(self):
        result = assess_switching_survival(
            _case(event_plan=[{"category": IN_ORBIT_SWITCHING, "pulse_count": 400}])
        )
        self.assertEqual(result["verdict"], SWITCHING_EVENT_PLAN_DEFICIENT)
        self.assertEqual(result["pulse_counts"][GROUND_HANDLING], 0)

    def test_too_few_in_orbit_pulses_is_a_plan_deficiency(self):
        result = assess_switching_survival(_case(event_plan=_events(orbit=5)))
        self.assertEqual(result["verdict"], SWITCHING_EVENT_PLAN_DEFICIENT)

    def test_a_pulse_count_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_switching_survival(
            _case(
                event_plan=_events(
                    ground=int(policy["min_ground_handling_pulses"]),
                    orbit=int(policy["min_in_orbit_switching_pulses"]),
                )
            ),
            policy,
        )
        self.assertEqual(result["verdict"], SWITCHING_SURVIVAL_ACCEPTED)

    def test_a_loose_derating_factor_is_a_plan_deficiency(self):
        result = assess_switching_survival(_case(device=_device(derating_factor=0.95)))
        self.assertEqual(result["verdict"], SWITCHING_EVENT_PLAN_DEFICIENT)

    def test_a_short_recovery_interval_is_a_plan_deficiency(self):
        result = assess_switching_survival(
            _case(circuit=_circuit(recovery_interval_s=0.001))
        )
        self.assertEqual(result["verdict"], SWITCHING_EVENT_PLAN_DEFICIENT)

    def test_every_plan_finding_is_reported_not_only_the_first(self):
        result = assess_switching_survival(
            _case(
                circuit=_circuit(recovery_interval_s=0.001),
                event_plan=_events(ground=1, orbit=1),
            )
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_a_missing_circuit_block_rejected(self):
        case = _case()
        del case["circuit"]
        with self.assertRaises(ValueError):
            assess_switching_survival(case)

    def test_a_missing_device_block_rejected(self):
        case = _case()
        del case["device"]
        with self.assertRaises(ValueError):
            assess_switching_survival(case)

    def test_a_missing_event_plan_rejected(self):
        case = _case()
        del case["event_plan"]
        with self.assertRaises(ValueError):
            assess_switching_survival(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_switching_survival(["circuit"])

    def test_a_negative_switched_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_switching_survival(_case(circuit=_circuit(switched_current_a=-5.0)))


if __name__ == "__main__":
    unittest.main()
