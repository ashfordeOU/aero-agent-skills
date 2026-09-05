"""Contract test for the rocket-gravity-loss leaf (propulsion/rocket).

Exercises SKILL.md workflow steps 2 through 6 of the rocket-gravity-loss
leaf: step 2 the burn time traverse, step 3 the launch thrust-to-weight
traverse, step 4 the gravity-loss traverse (vertical ascent and pitched
ascent at a constant mean flight-path angle), step 5 the ascent delta-v
bookkeeping (effective delta-v and required ideal delta-v), and step 6 the
ascent report dict. Step 7 of the workflow, the verification run, is this
file: it confirms the spec worked-example anchors (burn time 160.0 s,
launch thrust-to-weight 1.071, vertical gravity loss 1569.1 m/s, pitched
gravity loss at 45 degrees 1109.5 m/s, effective delta-v 1383.2 m/s), and
verifies the identity that effective delta-v plus the gravity and drag
losses equals the ideal delta-v, the required-ideal round trip, the
pitched-below-vertical loss ordering, and every ValueError guard from the
validation list. Run offline as a deterministic stdlib unittest.
"""

import math
import unittest

import rocket_gravity_loss_logic as rgl

M_PROP = 400000.0   # propellant load, kg
M_DOT = 2500.0      # propellant flow rate, kg/s
M0 = 700000.0       # initial mass, kg
THRUST = 7354987.5  # sea-level thrust, N (m_dot * 300 s * g0)
DV_IDEAL = 2492.7460687698513  # ideal delta-v input, m/s


class RocketGravityLossContract(unittest.TestCase):
    """Worked-example anchors, identities, loss ordering and ValueError
    guards for the gravity-loss accounting workflow."""

    # ---- workflow step 2: burn time traverse ----

    def test_step2_burn_time_anchor(self):
        """Workflow step 2, the burn time traverse: a 400000 kg propellant
        load at 2500 kg/s burns for 160.0 s within 0.1 s."""
        t_b = rgl.burn_time(M_PROP, M_DOT)
        self.assertAlmostEqual(t_b, 160.0, places=6)
        self.assertTrue(abs(t_b - 160.0) <= 0.1)

    def test_step2_burn_time_propellant_scaling(self):
        """Workflow step 2 closed form: the burn time scales linearly with
        the propellant load at a fixed flow rate."""
        self.assertAlmostEqual(
            rgl.burn_time(2.0 * M_PROP, M_DOT), 2.0 * rgl.burn_time(M_PROP, M_DOT),
            places=9)

    def test_step2_burn_time_flow_scaling(self):
        """Workflow step 2 closed form: doubling the propellant flow rate
        halves the burn time for the same propellant load."""
        self.assertAlmostEqual(
            rgl.burn_time(M_PROP, 2.0 * M_DOT), 0.5 * rgl.burn_time(M_PROP, M_DOT),
            places=9)

    # ---- workflow step 3: launch thrust-to-weight traverse ----

    def test_step3_thrust_to_weight_anchor(self):
        """Workflow step 3, the launch thrust-to-weight traverse: 7.355e6 N
        on a 700000 kg initial mass gives a launch thrust-to-weight ratio
        of 1.071 within 0.002."""
        twr = rgl.thrust_to_weight(THRUST, M0)
        self.assertAlmostEqual(twr, 1.0714285714285714, places=9)
        self.assertTrue(abs(twr - 1.071) <= 0.002)

    def test_step3_thrust_to_weight_hand_formula(self):
        """Workflow step 3 closed form: the launch thrust-to-weight ratio
        equals the sea-level thrust divided by the initial mass times g0."""
        twr = rgl.thrust_to_weight(THRUST, M0)
        self.assertAlmostEqual(twr, THRUST / (M0 * rgl.G0), places=12)

    def test_step3_thrust_to_weight_thrust_scaling(self):
        """Workflow step 3 trend: doubling the sea-level thrust doubles the
        launch thrust-to-weight ratio at fixed initial mass."""
        twr1 = rgl.thrust_to_weight(THRUST, M0)
        twr2 = rgl.thrust_to_weight(2.0 * THRUST, M0)
        self.assertAlmostEqual(twr2, 2.0 * twr1, places=12)

    def test_step3_thrust_to_weight_mass_scaling(self):
        """Workflow step 3 trend: doubling the initial mass halves the
        launch thrust-to-weight ratio at fixed sea-level thrust."""
        twr1 = rgl.thrust_to_weight(THRUST, M0)
        twr2 = rgl.thrust_to_weight(THRUST, 2.0 * M0)
        self.assertAlmostEqual(twr2, 0.5 * twr1, places=12)

    # ---- workflow step 4: gravity-loss traverse ----

    def test_step4_vertical_loss_anchor(self):
        """Workflow step 4, the vertical ascent gravity loss: a 160.0 s
        burn loses 1569.1 m/s within 0.5 m/s."""
        dv_g = rgl.gravity_loss_vertical(160.0)
        self.assertAlmostEqual(dv_g, 1569.064, places=6)
        self.assertTrue(abs(dv_g - 1569.1) <= 0.5)

    def test_step4_vertical_loss_equals_g0_times_burn_time(self):
        """Workflow step 4 identity: the vertical ascent gravity loss
        equals g0 times the burn time, the spec identity anchor."""
        t_b = rgl.burn_time(M_PROP, M_DOT)
        dv_g = rgl.gravity_loss_vertical(t_b)
        self.assertAlmostEqual(dv_g, rgl.G0 * t_b, places=12)

    def test_step4_pitched_loss_anchor_45(self):
        """Workflow step 4, the pitched ascent gravity loss at a constant
        mean flight-path angle of 45 degrees: 1109.5 m/s within 0.5 m/s."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        self.assertAlmostEqual(dv_gp, 1109.4957945156889, places=9)
        self.assertTrue(abs(dv_gp - 1109.5) <= 0.5)

    def test_step4_pitched_loss_hand_formula(self):
        """Workflow step 4 closed form: the pitched ascent gravity loss is
        g0 times the burn time times the sine of the constant mean
        flight-path angle converted to radians."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        expect = rgl.G0 * 160.0 * math.sin(math.radians(45.0))
        self.assertAlmostEqual(dv_gp, expect, places=12)

    def test_step4_pitched_below_vertical_at_45(self):
        """Workflow step 4 ordering: at 45 degrees the pitched ascent
        gravity loss sits below the vertical ascent gravity loss for the
        same burn time."""
        dv_g = rgl.gravity_loss_vertical(160.0)
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        self.assertLess(dv_gp, dv_g)

    def test_step4_pitched_equals_vertical_at_90(self):
        """Workflow step 4 boundary: at 90 degrees the pitched ascent
        gravity loss equals the vertical ascent gravity loss (sine of 90
        degrees is 1)."""
        dv_g = rgl.gravity_loss_vertical(160.0)
        dv_gp = rgl.gravity_loss_pitched(160.0, 90.0)
        self.assertAlmostEqual(dv_gp, dv_g, places=12)

    def test_step4_pitched_zero_at_0(self):
        """Workflow step 4 boundary: at 0 degrees the pitched ascent
        gravity loss is zero (horizontal flight feels no gravity loss)."""
        self.assertAlmostEqual(rgl.gravity_loss_pitched(160.0, 0.0), 0.0,
                               places=12)

    # ---- workflow step 5: ascent delta-v bookkeeping ----

    def test_step5_effective_delta_v_anchor(self):
        """Workflow step 5, the ascent delta-v bookkeeping: the effective
        delta-v after the pitched gravity loss is 1383.2 m/s within
        0.5 m/s."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        dv_eff = rgl.effective_delta_v(DV_IDEAL, dv_gp)
        self.assertAlmostEqual(dv_eff, 1383.2502742541624, places=9)
        self.assertTrue(abs(dv_eff - 1383.2) <= 0.5)

    def test_step5_effective_plus_losses_equals_ideal(self):
        """Workflow step 5 identity: the effective delta-v plus the gravity
        and drag losses equals the ideal delta-v input."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        dv_eff = rgl.effective_delta_v(DV_IDEAL, dv_gp, 50.0)
        self.assertAlmostEqual(dv_eff + dv_gp + 50.0, DV_IDEAL, places=12)

    def test_step5_drag_loss_reduces_effective(self):
        """Workflow step 5 trend: a positive drag loss lowers the effective
        delta-v below the no-drag value for the same gravity loss."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        dv_no_drag = rgl.effective_delta_v(DV_IDEAL, dv_gp)
        dv_with_drag = rgl.effective_delta_v(DV_IDEAL, dv_gp, 100.0)
        self.assertAlmostEqual(dv_with_drag, dv_no_drag - 100.0, places=9)
        self.assertLess(dv_with_drag, dv_no_drag)

    def test_step5_required_ideal_round_trip(self):
        """Workflow step 5 round trip: required_ideal_delta_v inverts
        effective_delta_v, recovering the ideal delta-v input when the
        target is the effective delta-v and the loss is unchanged."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        dv_eff = rgl.effective_delta_v(DV_IDEAL, dv_gp)
        dv_req = rgl.required_ideal_delta_v(dv_eff, dv_gp)
        self.assertAlmostEqual(dv_req, DV_IDEAL, places=9)

    def test_step5_required_ideal_adds_losses_to_target(self):
        """Workflow step 5 closed form: the required ideal delta-v equals
        the target net delta-v plus the gravity and drag losses."""
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        dv_req = rgl.required_ideal_delta_v(1500.0, dv_gp, 50.0)
        self.assertAlmostEqual(dv_req, 1500.0 + dv_gp + 50.0, places=9)

    # ---- workflow step 6: ascent report ----

    def test_step6_report_keys_exact(self):
        """Workflow step 6, the ascent report: the dict carries exactly the
        keys burn_time, thrust_to_weight, gravity_loss, effective_delta_v
        and required_ideal_delta_v, in the documented order."""
        rep = rgl.ascent_report(M_PROP, M_DOT, THRUST, M0, DV_IDEAL, 9000.0)
        self.assertEqual(list(rep.keys()), [
            "burn_time", "thrust_to_weight", "gravity_loss",
            "effective_delta_v", "required_ideal_delta_v"])

    def test_step6_report_vertical_default(self):
        """Workflow step 6 default: with no mean flight-path angle given,
        the ascent report uses 90 degrees and the gravity loss equals the
        vertical ascent value for the 160.0 s burn."""
        rep = rgl.ascent_report(M_PROP, M_DOT, THRUST, M0, DV_IDEAL, 9000.0)
        self.assertAlmostEqual(rep["burn_time"], 160.0, places=9)
        self.assertAlmostEqual(rep["gravity_loss"],
                               rgl.gravity_loss_vertical(160.0), places=9)

    def test_step6_report_pitched_values(self):
        """Workflow step 6 pitched case: at a constant mean flight-path
        angle of 45 degrees the ascent report gravity loss, effective
        delta-v and required ideal delta-v agree with the step 4 and step 5
        functions."""
        rep = rgl.ascent_report(M_PROP, M_DOT, THRUST, M0, DV_IDEAL,
                                1383.2502742541624, mean_path_angle_deg=45.0)
        dv_gp = rgl.gravity_loss_pitched(160.0, 45.0)
        self.assertAlmostEqual(rep["thrust_to_weight"],
                               rgl.thrust_to_weight(THRUST, M0), places=12)
        self.assertAlmostEqual(rep["gravity_loss"], dv_gp, places=9)
        self.assertAlmostEqual(rep["effective_delta_v"],
                               DV_IDEAL - dv_gp, places=9)
        self.assertAlmostEqual(rep["required_ideal_delta_v"],
                               DV_IDEAL, places=9)

    def test_step6_report_determinism(self):
        """Workflow step 6 determinism: two identical ascent report calls
        return identical dicts, so the workflow is repeatable."""
        a = rgl.ascent_report(M_PROP, M_DOT, THRUST, M0, DV_IDEAL, 9000.0)
        b = rgl.ascent_report(M_PROP, M_DOT, THRUST, M0, DV_IDEAL, 9000.0)
        self.assertEqual(a, b)

    # ---- workflow step 7: verification guards (ValueError rejection) ----

    def test_valueerror_nonpositive_propellant_load(self):
        """Verification guard: a zero or negative propellant load rejects
        the burn time traverse with ValueError."""
        for bad in (0.0, -400000.0):
            with self.assertRaises(ValueError):
                rgl.burn_time(bad, M_DOT)

    def test_valueerror_nonpositive_flow_rate(self):
        """Verification guard: a zero or negative propellant flow rate
        rejects the burn time traverse with ValueError."""
        for bad in (0.0, -2500.0):
            with self.assertRaises(ValueError):
                rgl.burn_time(M_PROP, bad)

    def test_valueerror_nonpositive_thrust(self):
        """Verification guard: a zero or negative sea-level thrust rejects
        the launch thrust-to-weight traverse with ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rgl.thrust_to_weight(bad, M0)

    def test_valueerror_nonpositive_initial_mass(self):
        """Verification guard: a zero or negative initial mass rejects the
        launch thrust-to-weight traverse with ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rgl.thrust_to_weight(THRUST, bad)

    def test_valueerror_negative_burn_time(self):
        """Verification guard: a negative burn time rejects both legs of
        the gravity-loss traverse with ValueError."""
        with self.assertRaises(ValueError):
            rgl.gravity_loss_vertical(-5.0)
        with self.assertRaises(ValueError):
            rgl.gravity_loss_pitched(-5.0, 45.0)

    def test_valueerror_path_angle_out_of_range(self):
        """Verification guard: mean flight-path angles of 95 or -5 degrees
        reject the pitched ascent gravity-loss traverse with ValueError,
        while the [0, 90] degree envelope accepts 0, 45 and 90."""
        for bad in (95.0, -5.0):
            with self.assertRaises(ValueError):
                rgl.gravity_loss_pitched(160.0, bad)
        for ok in (0.0, 45.0, 90.0):
            rgl.gravity_loss_pitched(160.0, ok)

    def test_valueerror_losses_exceed_ideal_delta_v(self):
        """Verification guard: gravity and drag losses summing past the
        ideal delta-v reject the effective delta-v bookkeeping with
        ValueError."""
        with self.assertRaises(ValueError):
            rgl.effective_delta_v(DV_IDEAL, 3000.0)
        with self.assertRaises(ValueError):
            rgl.effective_delta_v(DV_IDEAL, 1500.0, 1500.0)

    def test_valueerror_losses_exceed_target(self):
        """Verification guard: losses summing past the target net delta-v
        reject the required ideal delta-v bookkeeping with ValueError."""
        with self.assertRaises(ValueError):
            rgl.required_ideal_delta_v(1000.0, 1500.0)

    def test_valueerror_negative_losses(self):
        """Verification guard: a negative gravity or drag loss rejects the
        ascent delta-v bookkeeping with ValueError."""
        with self.assertRaises(ValueError):
            rgl.effective_delta_v(DV_IDEAL, -1.0)
        with self.assertRaises(ValueError):
            rgl.effective_delta_v(DV_IDEAL, 500.0, -1.0)
        with self.assertRaises(ValueError):
            rgl.required_ideal_delta_v(1500.0, -1.0)

    def test_module_g0_constant(self):
        """Module constant check: g0 is 9.80665 m/s^2, the standard gravity
        used by every gravity-loss relation in the quick reference."""
        self.assertAlmostEqual(rgl.G0, 9.80665, places=12)


if __name__ == "__main__":
    unittest.main()
