"""Contract test for the mpd-thruster SKILL.md workflow.

Covers the seven workflow steps of the mpd-thruster skill: step 1
fixes the operating point (discharge current, anode-to-cathode radius
ratio, propellant mass flow), step 2 is the self-field electromagnetic
thrust traverse with the current-squared thrust law, step 3 is the
exhaust-velocity and specific-impulse traverse from the mass flow,
step 4 is the jet-power and thrust-to-power traverse on the jet-power
basis, step 5 is the band-verdict traverse with the reference-only
class bands, step 6 is the single-point operating-point summary
traverse, and step 7 is the deterministic contract-test confirmation.
The worked example is the steady self-field MPD point at 10 kA with a
10 to 1 radius ratio and a 0.1 g/s argon mass flow; the companion
point runs at 5 kA. All numeric asserts are order-safe with
math.isclose tolerances; no exact-float equality on computed products
or sums.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)

import mpd_thruster_logic as mpd

# Worked-example point: J = 10 kA, r_a/r_c = 10, m_dot = 0.1 g/s argon.
J10 = 10000.0
RATIO = 10.0
MDOT = 1.0e-4


class MpdConstantsTest(unittest.TestCase):
    """Step 1 input pins: the module constants that fix the traverse."""

    def test_mu0_matches_si_value(self):
        # Step 1 of the workflow fixes the physics inputs; MU0 is the
        # exact SI vacuum permeability constant.
        self.assertTrue(math.isclose(mpd.MU0, 1.2566370614359173e-06, rel_tol=1e-12))

    def test_mu0_over_4pi_is_law_coefficient(self):
        # Step 2 of the workflow, the self-field thrust traverse, uses
        # the 1e-7 N/A^2 coefficient; never assert exact equality on
        # this computed constant.
        self.assertTrue(math.isclose(mpd.MU0_OVER_4PI, 1e-7, rel_tol=1e-6))

    def test_g0_and_scale_constants(self):
        # Step 3 of the workflow, the specific-impulse traverse, divides
        # by the standard gravity literal.
        self.assertEqual(mpd.G0, 9.80665)
        self.assertEqual(mpd.MN_PER_KW, 1e6)

    def test_reference_band_tuples(self):
        # Step 5 of the workflow, the band-verdict traverse, pins the
        # published reference-only class bands for the steady self-field
        # MPD class.
        self.assertEqual(mpd.ISP_BAND_S, (1000.0, 4000.0))
        self.assertEqual(mpd.TP_BAND_MN_PER_KW, (10.0, 40.0))


class MpdWorkedExampleTest(unittest.TestCase):
    """Steps 2-4 of the SKILL.md workflow at the 10 kA worked point."""

    def test_worked_thrust_at_10ka(self):
        # Step 2 of the SKILL.md workflow, the self-field electromagnetic
        # thrust traverse, at 10 kA and ratio 10. The receipt target is
        # 23.0 N within one percent, and the magnitude stays in the
        # 20-26 N band.
        thrust = mpd.self_field_thrust(J10, RATIO)
        self.assertTrue(math.isclose(thrust, 23.02585092994046, rel_tol=1e-9))
        self.assertTrue(math.isclose(thrust, 23.0, rel_tol=0.01))
        self.assertTrue(20.0 < thrust < 26.0)

    def test_worked_exhaust_velocity(self):
        # Step 3 of the workflow, the exhaust-velocity traverse from the
        # 0.1 g/s argon mass flow.
        ve = mpd.exhaust_velocity(mpd.self_field_thrust(J10, RATIO), MDOT)
        self.assertTrue(math.isclose(ve, 230258.5092994046, rel_tol=1e-9))

    def test_worked_specific_impulse(self):
        # Step 3 of the workflow, the specific-impulse traverse dividing
        # the exhaust velocity by g0.
        isp = mpd.specific_impulse(230258.5092994046)
        self.assertTrue(math.isclose(isp, 23479.833510873195, rel_tol=1e-9))

    def test_worked_jet_power(self):
        # Step 4 of the workflow, the jet-power traverse from thrust
        # squared over twice the mass flow, about 2.65 MW.
        thrust = mpd.self_field_thrust(J10, RATIO)
        pj = mpd.jet_power(thrust, MDOT)
        self.assertTrue(math.isclose(pj, 2650949.0552391997, rel_tol=1e-9))
        self.assertTrue(2.0e6 < pj < 3.5e6)

    def test_worked_thrust_to_power(self):
        # Step 4 of the workflow, the thrust-to-power traverse on the
        # jet-power basis, reported in mN/kW.
        thrust = mpd.self_field_thrust(J10, RATIO)
        pj = mpd.jet_power(thrust, MDOT)
        ttp = mpd.thrust_to_power(thrust, pj)
        self.assertTrue(math.isclose(ttp, 8.685889638065036e-06, rel_tol=1e-9))
        self.assertTrue(
            math.isclose(ttp * mpd.MN_PER_KW, 8.685889638065037, rel_tol=1e-9)
        )


class MpdScalingIdentityTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the current-squared law."""

    def test_thrust_scales_with_current_squared(self):
        # Step 2 thrust traverse: doubling the discharge current from
        # 10 kA to 20 kA quadruples the electromagnetic thrust, and
        # 5 kA gives exactly one quarter by the J-squared law.
        t10 = mpd.self_field_thrust(J10, RATIO)
        t20 = mpd.self_field_thrust(20000.0, RATIO)
        t5 = mpd.self_field_thrust(5000.0, RATIO)
        self.assertTrue(math.isclose(t20, 4.0 * t10, rel_tol=1e-12))
        self.assertTrue(math.isclose(t5, t10 / 4.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(t5, 5.756462732485115, rel_tol=1e-9))

    def test_log_geometry_scaling(self):
        # Step 2 thrust traverse: ratio 100 doubles and ratio 1000
        # triples the ln(r_a/r_c) geometry factor against ratio 10.
        t10 = mpd.self_field_thrust(J10, RATIO)
        self.assertTrue(
            math.isclose(mpd.self_field_thrust(J10, 100.0), 2.0 * t10, rel_tol=1e-12)
        )
        self.assertTrue(
            math.isclose(mpd.self_field_thrust(J10, 1000.0), 3.0 * t10, rel_tol=1e-12)
        )

    def test_law_coefficient_identity(self):
        # Step 2 thrust traverse: T/J^2 equals 1e-7 * ln(10) N/A^2 at
        # the worked point.
        ratio = mpd.self_field_thrust(J10, RATIO) / (J10 * J10)
        self.assertTrue(math.isclose(ratio, 2.302585093e-7, rel_tol=1e-9))
        self.assertTrue(math.isclose(ratio, 1e-7 * math.log(10.0), rel_tol=1e-12))

    def test_zero_current_gives_zero_thrust(self):
        # Step 2 boundary: no discharge current means no self-field and
        # no electromagnetic thrust at any valid radius ratio.
        self.assertEqual(mpd.self_field_thrust(0.0, RATIO), 0.0)
        self.assertEqual(mpd.self_field_thrust(0.0, 100.0), 0.0)
        self.assertEqual(mpd.self_field_thrust(0.0, 1000.0), 0.0)


class MpdDefinitionIdentityTest(unittest.TestCase):
    """Steps 3-4 of the SKILL.md workflow: definition identities."""

    def test_exhaust_velocity_definition_identity(self):
        # Step 3 exhaust-velocity traverse: v_e equals thrust over the
        # argon mass flow by definition.
        thrust = mpd.self_field_thrust(J10, RATIO)
        ve = mpd.exhaust_velocity(thrust, MDOT)
        self.assertTrue(math.isclose(ve, thrust / MDOT, rel_tol=1e-15))

    def test_specific_impulse_definition_identity(self):
        # Step 3 specific-impulse traverse: Isp equals v_e over g0.
        ve = mpd.exhaust_velocity(mpd.self_field_thrust(J10, RATIO), MDOT)
        self.assertTrue(math.isclose(mpd.specific_impulse(ve), ve / mpd.G0,
                                     rel_tol=1e-15))

    def test_jet_power_definition_identity(self):
        # Step 4 jet-power traverse: P_j from T^2/(2 m_dot) equals the
        # kinetic form 0.5 * m_dot * v_e^2.
        thrust = mpd.self_field_thrust(J10, RATIO)
        ve = mpd.exhaust_velocity(thrust, MDOT)
        pj = mpd.jet_power(thrust, MDOT)
        self.assertTrue(math.isclose(pj, 0.5 * MDOT * ve * ve, rel_tol=1e-12))
        self.assertTrue(math.isclose(pj, thrust * thrust / (2.0 * MDOT),
                                     rel_tol=1e-12))

    def test_thrust_to_power_identity(self):
        # Step 4 thrust-to-power traverse: T/P_j equals 2 m_dot / T.
        thrust = mpd.self_field_thrust(J10, RATIO)
        pj = mpd.jet_power(thrust, MDOT)
        ttp = mpd.thrust_to_power(thrust, pj)
        self.assertTrue(math.isclose(ttp, 2.0 * MDOT / thrust, rel_tol=1e-12))


class MpdBandVerdictTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the band-verdict traverse."""

    def test_anchor_point_verdict(self):
        # Step 5 band-verdict traverse: the anchor point is above the
        # 1000-4000 s band on impulse and below the 10-40 mN/kW band on
        # thrust-to-power, never enforced.
        verdict = mpd.mpd_band_verdict(23479.833510873195, 8.685889638065037)
        self.assertEqual(verdict["isp_position"], "above")
        self.assertEqual(verdict["thrust_to_power_position"], "below")
        self.assertFalse(verdict["enforced"])

    def test_inside_point_verdict(self):
        # Step 5 band-verdict traverse: 2000 s and 20 mN/kW are inside
        # both published class bands.
        verdict = mpd.mpd_band_verdict(2000.0, 20.0)
        self.assertEqual(verdict["isp_position"], "inside")
        self.assertEqual(verdict["thrust_to_power_position"], "inside")
        self.assertFalse(verdict["enforced"])

    def test_companion_5ka_verdict(self):
        # Step 5 band-verdict traverse at the 5 kA companion point: the
        # impulse stays above the class band while thrust-to-power moves
        # inside the 10-40 mN/kW band.
        verdict = mpd.mpd_band_verdict(5869.958377718299, 34.74355855226015)
        self.assertEqual(verdict["isp_position"], "above")
        self.assertEqual(verdict["thrust_to_power_position"], "inside")

    def test_out_of_band_points_never_raise(self):
        # Step 5 band-verdict traverse: out-of-band points are reported,
        # never enforced, and never raise.
        high = mpd.mpd_band_verdict(1e6, 1e6)
        self.assertEqual(high["isp_position"], "above")
        self.assertEqual(high["thrust_to_power_position"], "above")
        self.assertFalse(high["enforced"])
        low = mpd.mpd_band_verdict(0.0, 0.0)
        self.assertEqual(low["isp_position"], "below")
        self.assertEqual(low["thrust_to_power_position"], "below")


class MpdOperatingPointTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the single-point summary."""

    def test_operating_point_summary_keys(self):
        # Step 6 single-point summary traverse: one call returns the
        # full operating-point dict.
        point = mpd.mpd_operating_point(J10, RATIO, MDOT)
        for key in ("current_j", "radius_ratio", "mass_flow", "thrust",
                    "exhaust_velocity", "specific_impulse", "jet_power",
                    "thrust_to_power_n_per_w", "thrust_to_power_mn_per_kw",
                    "band_verdict"):
            self.assertIn(key, point)

    def test_operating_point_worked_values(self):
        # Step 6 summary traverse reproduces the worked-example values.
        point = mpd.mpd_operating_point(J10, RATIO, MDOT)
        self.assertTrue(math.isclose(point["thrust"], 23.02585092994046,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(point["specific_impulse"],
                                     23479.833510873195, rel_tol=1e-9))
        self.assertTrue(math.isclose(point["thrust_to_power_mn_per_kw"],
                                     8.685889638065037, rel_tol=1e-9))

    def test_operating_point_companion_5ka(self):
        # Step 6 summary traverse at 5 kA: thrust quarters and the
        # thrust-to-power quadruples back inside the band.
        point = mpd.mpd_operating_point(5000.0, RATIO, MDOT)
        self.assertTrue(math.isclose(point["thrust"], 5.756462732485115,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(point["specific_impulse"],
                                     5869.958377718299, rel_tol=1e-9))
        self.assertTrue(math.isclose(point["thrust_to_power_mn_per_kw"],
                                     34.74355855226015, rel_tol=1e-9))
        self.assertEqual(point["band_verdict"]["isp_position"], "above")
        self.assertEqual(point["band_verdict"]["thrust_to_power_position"],
                         "inside")

    def test_operating_point_self_consistent(self):
        # Step 6 summary traverse: the dict fields satisfy the model
        # identities across the discharge-current scaling.
        p10 = mpd.mpd_operating_point(J10, RATIO, MDOT)
        p5 = mpd.mpd_operating_point(5000.0, RATIO, MDOT)
        self.assertTrue(math.isclose(p10["thrust"], 4.0 * p5["thrust"],
                                     rel_tol=1e-12))
        self.assertTrue(
            math.isclose(p10["thrust_to_power_mn_per_kw"],
                         p5["thrust_to_power_mn_per_kw"] / 4.0, rel_tol=1e-12)
        )


class MpdValueErrorTest(unittest.TestCase):
    """Step 7 confirmation: non-physical inputs raise ValueError."""

    def test_self_field_thrust_rejects_bad_inputs(self):
        # Step 2 thrust traverse: negative discharge current, radius
        # ratio at or below 1, and nan inputs are not physical.
        with self.assertRaises(ValueError):
            mpd.self_field_thrust(-100.0, RATIO)
        with self.assertRaises(ValueError):
            mpd.self_field_thrust(J10, 1.0)
        with self.assertRaises(ValueError):
            mpd.self_field_thrust(J10, 0.5)
        with self.assertRaises(ValueError):
            mpd.self_field_thrust(float("nan"), RATIO)
        with self.assertRaises(ValueError):
            mpd.self_field_thrust(J10, float("nan"))

    def test_exhaust_velocity_rejects_bad_inputs(self):
        # Step 3 exhaust-velocity traverse: a zero or negative argon
        # mass flow and a negative thrust raise ValueError.
        with self.assertRaises(ValueError):
            mpd.exhaust_velocity(23.0, 0.0)
        with self.assertRaises(ValueError):
            mpd.exhaust_velocity(23.0, -1e-4)
        with self.assertRaises(ValueError):
            mpd.exhaust_velocity(-1.0, MDOT)

    def test_specific_impulse_rejects_negative_velocity(self):
        # Step 3 specific-impulse traverse: negative exhaust velocity is
        # rejected.
        with self.assertRaises(ValueError):
            mpd.specific_impulse(-1.0)

    def test_jet_power_and_thrust_to_power_reject_bad_inputs(self):
        # Step 4 jet-power and thrust-to-power traverse: negative mass
        # flow, negative thrust and zero jet power raise ValueError.
        with self.assertRaises(ValueError):
            mpd.jet_power(23.0, -1e-4)
        with self.assertRaises(ValueError):
            mpd.jet_power(-1.0, MDOT)
        with self.assertRaises(ValueError):
            mpd.thrust_to_power(23.0, 0.0)

    def test_band_verdict_rejects_negative_impulse(self):
        # Step 5 band-verdict traverse: negative impulse is not
        # physical; out-of-band never raises but negative always does.
        with self.assertRaises(ValueError):
            mpd.mpd_band_verdict(-1.0, 20.0)

    def test_operating_point_propagates_value_errors(self):
        # Step 6 summary traverse: ValueErrors propagate from the chained
        # functions.
        with self.assertRaises(ValueError):
            mpd.mpd_operating_point(-1.0, RATIO, MDOT)
        with self.assertRaises(ValueError):
            mpd.mpd_operating_point(J10, RATIO, 0.0)


class MpdDeterminismTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: deterministic confirmation."""

    def test_repeated_runs_identical(self):
        # Step 7 contract-test confirmation: the module is deterministic
        # with no RNG, so repeated runs give identical operating points.
        first = mpd.mpd_operating_point(J10, RATIO, MDOT)
        second = mpd.mpd_operating_point(J10, RATIO, MDOT)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
