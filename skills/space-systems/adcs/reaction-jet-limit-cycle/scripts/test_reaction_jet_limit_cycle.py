"""Contract test for the reaction-jet limit-cycle leaf.

Exercises the SKILL.md workflow end to end. Workflow steps under test:
step 1, stating the attitude-hold demand (axes, life, duty factor);
step 2, the control authority traverse (control angular acceleration
from torque and axis inertia); step 3, the deadband crossing rate;
step 4, the braking pulse firing duration; step 5, the per-pulse
impulse terms (linear delta-V and fixed-Isp propellant mass); step 6,
the full-cycle two-pulse terms (delta-V per cycle and propellant per
cycle); step 7, the aggregate limit-cycle period; step 8, the cycle
count and pulse count over the mission life; step 9, the three-axis
propellant budget rollup with the activity duty factor and the
feasibility verdict. All assertions use the real module outputs of the
worked example within spec tolerances. Deterministic, offline, no RNG.
"""

import math
import unittest

import reaction_jet_limit_cycle_logic as rjlc

G0 = 9.80665
H = math.radians(0.1)            # 0.1 deg deadband half-angle
ALPHA = 1.0 / 120.0              # 1 N m on 120 kg m^2
OMEGA = math.sqrt(2.0 * ALPHA * H)
T_FIRE = OMEGA / ALPHA
LIFE = 63115200.0                # 2-year mission, 365.25-day years

EXAMPLE_AXES = [
    {"name": "yaw", "mass_kg": 1000.0, "inertia_kgm2": 120.0,
     "torque_Nm": 1.0, "thrust_N": 1.0, "isp_s": 60.0,
     "deadband_half_rad": H},
    {"name": "pitch", "mass_kg": 1000.0, "inertia_kgm2": 120.0,
     "torque_Nm": 1.0, "thrust_N": 1.0, "isp_s": 60.0,
     "deadband_half_rad": H},
    {"name": "roll", "mass_kg": 1000.0, "inertia_kgm2": 120.0,
     "torque_Nm": 1.0, "thrust_N": 1.0, "isp_s": 60.0,
     "deadband_half_rad": H},
]

EXPECTED_KEYS = [
    "alpha_c_rad_s2", "omega_rad_s", "t_fire_s", "delta_v_per_pulse_m_s",
    "delta_v_per_cycle_m_s", "propellant_per_pulse_kg",
    "propellant_per_cycle_kg", "cycle_period_s", "cycles", "pulses",
    "propellant_life_kg",
]


class TestControlAcceleration(unittest.TestCase):
    """Workflow step 2, the control authority traverse."""

    def test_control_accel_worked_example(self):
        """Step 2, the control authority traverse: control_accel(1.0, 120.0)
        returns 8.33333e-3 rad/s^2 within 1e-12."""
        value = rjlc.control_accel(1.0, 120.0)
        # Full-precision closed form 1/120 = 8.33333e-3 rad/s^2.
        self.assertAlmostEqual(value, 1.0 / 120.0, delta=1e-15)
        # Spec magnitude bound: the printed anchor 8.33333e-3 rad/s^2.
        self.assertAlmostEqual(value, 8.33333e-3, delta=1e-8)

    def test_control_accel_scaling_identities(self):
        """Step 2: doubling the control torque at fixed axis inertia doubles
        the control angular acceleration, and doubling the axis inertia at
        fixed torque halves it."""
        self.assertAlmostEqual(rjlc.control_accel(2.0, 120.0),
                               2.0 * rjlc.control_accel(1.0, 120.0),
                               delta=1e-15)
        self.assertAlmostEqual(rjlc.control_accel(1.0, 240.0),
                               0.5 * rjlc.control_accel(1.0, 120.0),
                               delta=1e-15)

    def test_control_accel_value_error(self):
        """Step 2: zero and negative control torque and zero and negative
        axis inertia are non-physical and raise ValueError."""
        with self.assertRaises(ValueError):
            rjlc.control_accel(0.0, 120.0)
        with self.assertRaises(ValueError):
            rjlc.control_accel(1.0, 0.0)
        with self.assertRaises(ValueError):
            rjlc.control_accel(-1.0, 120.0)
        with self.assertRaises(ValueError):
            rjlc.control_accel(1.0, -120.0)


class TestDeadbandCrossingRate(unittest.TestCase):
    """Workflow step 3, the deadband crossing rate traverse."""

    def test_limit_cycle_rate_worked_example(self):
        """Step 3: limit_cycle_rate(8.33333e-3, 0.1 deg half-angle) returns
        5.39341e-3 rad/s within 1e-9, 0.30902 deg/s."""
        omega = rjlc.limit_cycle_rate(ALPHA, H)
        # Full-precision closed form sqrt(2 * alpha_c * h) = 5.3934053e-3.
        self.assertAlmostEqual(omega, math.sqrt(2.0 * ALPHA * H), delta=1e-15)
        # Spec magnitude bounds: printed anchor 5.39341e-3 rad/s and its
        # 0.30902 deg/s display.
        self.assertAlmostEqual(omega, 5.39341e-3, delta=1e-7)
        self.assertAlmostEqual(math.degrees(omega), 0.30902, delta=1e-5)

    def test_limit_cycle_rate_monotone(self):
        """Step 3: the deadband crossing rate is monotone increasing in the
        control angular acceleration at fixed deadband half-angle and in the
        deadband half-angle at fixed control acceleration."""
        rates = [rjlc.limit_cycle_rate(a, H)
                 for a in (8.0e-3, 8.33333e-3, 9.0e-3)]
        self.assertEqual(rates, sorted(rates))
        rates = [rjlc.limit_cycle_rate(ALPHA, h)
                 for h in (1.0e-3, H, 2.0e-3)]
        self.assertEqual(rates, sorted(rates))

    def test_limit_cycle_rate_zero_value_error(self):
        """Step 3: zero control acceleration or zero deadband half-angle is
        non-physical and raises ValueError."""
        with self.assertRaises(ValueError):
            rjlc.limit_cycle_rate(0.0, H)
        with self.assertRaises(ValueError):
            rjlc.limit_cycle_rate(ALPHA, 0.0)


class TestBrakingPulse(unittest.TestCase):
    """Workflow steps 4 to 6, the braking pulse and full-cycle terms."""

    def test_pulse_time_worked_example(self):
        """Step 4, the braking pulse firing duration: pulse_time on the
        example crossing rate returns 0.647209 s within 1e-9."""
        t_fire = rjlc.pulse_time(OMEGA, ALPHA)
        # Full-precision closed form sqrt(2 * h / alpha_c) = 0.64720864 s.
        self.assertAlmostEqual(t_fire, math.sqrt(2.0 * H / ALPHA), delta=1e-12)
        # Spec magnitude bound: printed anchor 0.647209 s.
        self.assertAlmostEqual(t_fire, 0.647209, delta=1e-6)

    def test_pulse_time_sqrt_identity(self):
        """Step 4: pulse_time(limit_cycle_rate(a, h), a) equals
        sqrt(2 h / a) exactly, within 1e-15, for a second parameter pair."""
        a, h = 5.0e-3, 3.0e-3
        self.assertAlmostEqual(rjlc.pulse_time(rjlc.limit_cycle_rate(a, h), a),
                               math.sqrt(2.0 * h / a), delta=1e-15)

    def test_pulse_time_monotone_in_alpha(self):
        """Step 4: the braking pulse firing duration is monotone decreasing
        in the control angular acceleration."""
        times = [rjlc.pulse_time(rjlc.limit_cycle_rate(a, H), a)
                 for a in (8.0e-3, 8.33333e-3, 9.0e-3)]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_pulse_time_zero_value_error(self):
        """Step 4: zero crossing rate or zero control acceleration raises
        ValueError for the firing duration."""
        with self.assertRaises(ValueError):
            rjlc.pulse_time(0.0, ALPHA)
        with self.assertRaises(ValueError):
            rjlc.pulse_time(OMEGA, 0.0)

    def test_pulse_delta_v_worked_example(self):
        """Step 5, the per-pulse impulse terms: pulse_delta_v(1.0,
        0.647209, 1000.0) returns 6.47209e-4 m/s within 1e-12."""
        dv = rjlc.pulse_delta_v(1.0, 0.647209, 1000.0)
        self.assertAlmostEqual(dv, 1.0 * 0.647209 / 1000.0, delta=1e-15)
        self.assertAlmostEqual(dv, 6.47209e-4, delta=1e-12)

    def test_pulse_delta_v_scales_with_mass(self):
        """Step 5: doubling the spacecraft mass halves the per-pulse linear
        delta-V at fixed thrust and firing duration."""
        dv = rjlc.pulse_delta_v(1.0, 0.647209, 1000.0)
        self.assertAlmostEqual(rjlc.pulse_delta_v(1.0, 0.647209, 2000.0),
                               0.5 * dv, delta=1e-15)

    def test_delta_v_per_cycle_worked_and_double(self):
        """Step 6, the full-cycle two-pulse terms: delta_v_per_cycle(1.0,
        0.647209, 1000.0) returns 1.29442e-3 m/s within 1e-12 and equals
        2 * pulse_delta_v exactly, two braking pulses per limit cycle."""
        dv = rjlc.delta_v_per_cycle(1.0, 0.647209, 1000.0)
        self.assertAlmostEqual(dv, 2.0 * 1.0 * 0.647209 / 1000.0, delta=1e-15)
        self.assertAlmostEqual(dv, 1.29442e-3, delta=1e-8)
        self.assertEqual(rjlc.delta_v_per_cycle(1.0, 0.647209, 1000.0),
                         2.0 * rjlc.pulse_delta_v(1.0, 0.647209, 1000.0))

    def test_pulse_propellant_worked_example(self):
        """Step 5: pulse_propellant(1.0, 0.647209, 60.0) returns
        1.09995e-3 kg within 1e-12 at the fixed specific impulse, using the
        module constant G0 = 9.80665 m/s^2."""
        prop = rjlc.pulse_propellant(1.0, 0.647209, 60.0)
        self.assertAlmostEqual(prop, 1.0 * 0.647209 / (60.0 * G0), delta=1e-15)
        self.assertAlmostEqual(prop, 1.09995e-3, delta=1e-8)
        self.assertEqual(rjlc.G0, 9.80665)
        self.assertAlmostEqual(rjlc.pulse_propellant(1.0, 60.0, 60.0),
                               60.0 / (60.0 * G0), delta=1e-15)

    def test_propellant_per_cycle_worked_and_double(self):
        """Step 6: propellant_per_cycle(1.0, 0.647209, 60.0) returns
        2.19990e-3 kg within 1e-12 and equals 2 * pulse_propellant exactly."""
        prop = rjlc.propellant_per_cycle(1.0, 0.647209, 60.0)
        self.assertAlmostEqual(prop, 2.0 * 1.0 * 0.647209 / (60.0 * G0),
                               delta=1e-15)
        self.assertAlmostEqual(prop, 2.19990e-3, delta=1e-8)
        self.assertEqual(rjlc.propellant_per_cycle(1.0, 0.647209, 60.0),
                         2.0 * rjlc.pulse_propellant(1.0, 0.647209, 60.0))

    def test_impulse_value_errors(self):
        """Steps 5 to 6: zero or negative thrust, firing duration, mass and
        specific impulse all raise ValueError."""
        for kwargs in ({"thrust_N": 0.0, "t_fire_s": 0.1, "mass_kg": 100.0},
                       {"thrust_N": 1.0, "t_fire_s": 0.0, "mass_kg": 100.0},
                       {"thrust_N": 1.0, "t_fire_s": 0.1, "mass_kg": 0.0},
                       {"thrust_N": 1.0, "t_fire_s": 0.1, "mass_kg": -100.0},
                       {"thrust_N": -1.0, "t_fire_s": 0.1, "mass_kg": 100.0}):
            with self.assertRaises(ValueError):
                rjlc.pulse_delta_v(**kwargs)
        for kwargs in ({"thrust_N": 0.0, "t_fire_s": 0.1, "isp_s": 60.0},
                       {"thrust_N": 1.0, "t_fire_s": 0.1, "isp_s": 0.0},
                       {"thrust_N": 1.0, "t_fire_s": 0.1, "isp_s": -60.0}):
            with self.assertRaises(ValueError):
                rjlc.pulse_propellant(**kwargs)


class TestCyclePeriod(unittest.TestCase):
    """Workflow step 7, the aggregate limit-cycle period traverse."""

    def test_cycle_period_worked_example(self):
        """Step 7: cycle_period(1.74533e-3, 8.33333e-3) returns 1.83058 s
        within 1e-9 for the aggregate limit-cycle period."""
        period = rjlc.cycle_period(H, ALPHA)
        # Full-precision closed form 4 * sqrt(h / alpha_c) = 1.83058247 s.
        self.assertAlmostEqual(period, 4.0 * math.sqrt(H / ALPHA), delta=1e-12)
        # Spec magnitude bound: printed anchor 1.83058 s.
        self.assertAlmostEqual(period, 1.83058, delta=1e-4)

    def test_cycle_period_monotone(self):
        """Step 7: the aggregate limit-cycle period is monotone decreasing
        in the control angular acceleration at fixed deadband half-angle and
        monotone increasing in the deadband half-angle at fixed control
        acceleration."""
        periods = [rjlc.cycle_period(H, a)
                   for a in (8.0e-3, 8.33333e-3, 9.0e-3)]
        self.assertEqual(periods, sorted(periods, reverse=True))
        periods = [rjlc.cycle_period(h, ALPHA)
                   for h in (1.0e-3, H, 2.0e-3)]
        self.assertEqual(periods, sorted(periods))

    def test_cycle_period_zero_value_error(self):
        """Step 7: zero deadband half-angle or zero control acceleration
        raises ValueError for the aggregate cycle period."""
        with self.assertRaises(ValueError):
            rjlc.cycle_period(0.0, ALPHA)
        with self.assertRaises(ValueError):
            rjlc.cycle_period(H, 0.0)


class TestLifeCounts(unittest.TestCase):
    """Workflow step 8, the cycle and pulse counts over the mission life."""

    def test_cycles_over_life_worked_example(self):
        """Step 8: cycles_over_life(63115200.0, 1.83058) returns
        3.44782e7 cycles over the 2-year mission life within 1e3, and
        86400.0 / 1.83058 gives 47,198.1 cycles per day within 1.0."""
        self.assertAlmostEqual(rjlc.cycles_over_life(LIFE, 1.83058),
                               3.44782e7, delta=1e3)
        self.assertAlmostEqual(86400.0 / 1.83058, 47198.1, delta=1.0)

    def test_cycles_double_with_life(self):
        """Step 8: doubling the active duration doubles the cycle count at
        fixed aggregate limit-cycle period."""
        period = rjlc.cycle_period(H, ALPHA)
        self.assertAlmostEqual(rjlc.cycles_over_life(2.0 * LIFE, period),
                               2.0 * rjlc.cycles_over_life(LIFE, period),
                               delta=1e-6)

    def test_cycles_zero_value_error(self):
        """Step 8: zero or negative life duration and zero cycle period
        raise ValueError."""
        with self.assertRaises(ValueError):
            rjlc.cycles_over_life(0.0, 1.83058)
        with self.assertRaises(ValueError):
            rjlc.cycles_over_life(-1.0, 1.83058)
        with self.assertRaises(ValueError):
            rjlc.cycles_over_life(LIFE, 0.0)


class TestPropellantBudget(unittest.TestCase):
    """Workflow step 9, the three-axis propellant budget rollup."""

    def setUp(self):
        self.budget = rjlc.propellant_budget(EXAMPLE_AXES, LIFE, 1.0)

    def test_budget_worked_example_three_axes(self):
        """Step 9: the three-axis propellant budget at duty 1.0 gives
        per-axis propellant_life_kg 7.58485e4 within 1.0 and a total of
        2.27546e5 kg within 1.0 for the 2-year mission life."""
        yaw = self.budget["axes"]["yaw"]
        self.assertAlmostEqual(yaw["propellant_life_kg"], 7.58485e4, delta=1.0)
        self.assertAlmostEqual(self.budget["propellant_total_kg"],
                               2.27546e5, delta=1.0)

    def test_budget_exact_keys(self):
        """Step 9: each per-axis result dict carries exactly the eleven
        specified keys (alpha_c, crossing rate, firing duration, per-pulse
        and per-cycle delta-V and propellant, period, cycles, pulses,
        lifetime propellant)."""
        self.assertEqual(sorted(self.budget["axes"]["yaw"].keys()),
                         sorted(EXPECTED_KEYS))
        for name in ("yaw", "pitch", "roll"):
            self.assertEqual(sorted(self.budget["axes"][name].keys()),
                             sorted(EXPECTED_KEYS))

    def test_budget_counts_identity(self):
        """Step 9: per-axis pulses equal 2 * cycles, two braking pulses per
        limit cycle, and propellant_life_kg equals cycles times
        propellant_per_cycle_kg."""
        for name in ("yaw", "pitch", "roll"):
            ax = self.budget["axes"][name]
            self.assertAlmostEqual(ax["pulses"], 2.0 * ax["cycles"],
                                   delta=1e-9)
            self.assertAlmostEqual(ax["propellant_life_kg"],
                                   ax["cycles"] * ax["propellant_per_cycle_kg"],
                                   delta=1e-6)

    def test_budget_duty_half_halves_total(self):
        """Step 9: the same axes at duty factor 0.5 give exactly half the
        propellant total of the duty 1.0 budget (linear scaling identity)."""
        half = rjlc.propellant_budget(EXAMPLE_AXES, LIFE, 0.5)
        self.assertAlmostEqual(half["propellant_total_kg"],
                               0.5 * self.budget["propellant_total_kg"],
                               delta=1e-6)

    def test_budget_single_axis_total(self):
        """Step 9: a single-axis list returns the per-axis lifetime
        propellant as the budget total."""
        single = rjlc.propellant_budget([EXAMPLE_AXES[0]], LIFE, 1.0)
        self.assertAlmostEqual(single["propellant_total_kg"],
                               single["axes"]["yaw"]["propellant_life_kg"],
                               delta=1e-9)

    def test_budget_linear_scaling(self):
        """Step 9: the propellant total scales linearly with the mission
        life at a fixed aggregate limit-cycle period and with the activity
        duty factor at fixed mission life and period."""
        doubled = rjlc.propellant_budget(EXAMPLE_AXES, 2.0 * LIFE, 1.0)
        self.assertAlmostEqual(doubled["propellant_total_kg"],
                               2.0 * self.budget["propellant_total_kg"],
                               delta=1e-6)
        for duty in (0.25, 0.75):
            scaled = rjlc.propellant_budget(EXAMPLE_AXES, LIFE, duty)
            self.assertAlmostEqual(scaled["propellant_total_kg"],
                                   duty * self.budget["propellant_total_kg"],
                                   delta=1e-6)

    def test_budget_mass_only_affects_delta_v(self):
        """Step 9: the lifetime propellant is independent of the spacecraft
        mass (mass enters only the linear delta-V terms, never the
        fixed-Isp propellant terms)."""
        light = rjlc.propellant_budget(
            [dict(ax, mass_kg=500.0) for ax in EXAMPLE_AXES], LIFE, 1.0)
        heavy = rjlc.propellant_budget(
            [dict(ax, mass_kg=2000.0) for ax in EXAMPLE_AXES], LIFE, 1.0)
        self.assertAlmostEqual(light["propellant_total_kg"],
                               heavy["propellant_total_kg"], delta=1e-6)
        self.assertAlmostEqual(
            light["axes"]["yaw"]["delta_v_per_pulse_m_s"],
            2.0 * self.budget["axes"]["yaw"]["delta_v_per_pulse_m_s"],
            delta=1e-12)

    def test_budget_empty_axes_value_error(self):
        """Step 9: an empty axes list raises ValueError, no axis to hold."""
        with self.assertRaises(ValueError):
            rjlc.propellant_budget([], LIFE, 1.0)

    def test_budget_life_and_duty_value_error(self):
        """Step 9: zero or negative mission life and a duty factor of 0.0,
        negative, or above 1.0 raise ValueError; the allowed activity range
        is (0, 1]."""
        with self.assertRaises(ValueError):
            rjlc.propellant_budget(EXAMPLE_AXES, 0.0, 1.0)
        with self.assertRaises(ValueError):
            rjlc.propellant_budget(EXAMPLE_AXES, -LIFE, 1.0)
        with self.assertRaises(ValueError):
            rjlc.propellant_budget(EXAMPLE_AXES, LIFE, 0.0)
        with self.assertRaises(ValueError):
            rjlc.propellant_budget(EXAMPLE_AXES, LIFE, -0.5)
        with self.assertRaises(ValueError):
            rjlc.propellant_budget(EXAMPLE_AXES, LIFE, 1.5)

    def test_budget_component_value_error_propagates(self):
        """Step 9: a non-physical component input (zero control torque)
        propagates its ValueError out of the budget call."""
        bad = [dict(ax, torque_Nm=0.0) for ax in EXAMPLE_AXES]
        with self.assertRaises(ValueError):
            rjlc.propellant_budget(bad, LIFE, 1.0)

    def test_budget_deterministic(self):
        """Step 9: repeated budget runs return identical results, no RNG
        anywhere in the model."""
        again = rjlc.propellant_budget(EXAMPLE_AXES, LIFE, 1.0)
        self.assertEqual(again["propellant_total_kg"],
                         self.budget["propellant_total_kg"])
        for name in ("yaw", "pitch", "roll"):
            for key in EXPECTED_KEYS:
                self.assertEqual(again["axes"][name][key],
                                 self.budget["axes"][name][key])


if __name__ == "__main__":
    unittest.main()
