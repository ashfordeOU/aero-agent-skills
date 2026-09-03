"""Contract tests for the Vmc (minimum control speed) prediction module.

Deterministic, offline, stdlib only. Run: python3 test_vmc_determination.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vmc_determination_logic as vmc

ENGINES_TWIN = [
    {"thrust_N": 65000.0, "y_m": 8.0},
    {"thrust_N": 65000.0, "y_m": -8.0},
]


def base_inputs(**overrides):
    """Worked-example twin jet inputs (power-boosted rudder)."""
    data = dict(
        engines=ENGINES_TWIN,
        failed_engine_index=0,
        windmilling_drag_area_m2=0.0,
        vertical_tail_area_m2=25.0,
        tail_arm_m=16.0,
        rudder_effectiveness_per_rad=0.8,
        rudder_deflection_max_deg=30.0,
        rudder_area_m2=8.5,
        rudder_chord_m=1.3,
        hinge_moment_coefficient_per_rad=-0.045,
        pedal_arm_m=0.35,
        boost_factor=0.15,
        v_s1g=66.0,
        pedal_force_limit_N=667.0,
        stall_guard=1.05,
    )
    data.update(overrides)
    return data


class CriticalEngineTests(unittest.TestCase):
    def test_critical_engine_tie_lower_index(self):
        self.assertEqual(vmc.critical_engine_index(ENGINES_TWIN), 0)

    def test_critical_engine_three_engine_outboard(self):
        engines = [
            {"thrust_N": 40000.0, "y_m": 10.0},
            {"thrust_N": 65000.0, "y_m": 0.0},
            {"thrust_N": 40000.0, "y_m": -10.0},
        ]
        self.assertEqual(vmc.critical_engine_index(engines), 0)

    def test_critical_engine_left_side_higher_thrust(self):
        engines = [
            {"thrust_N": 30000.0, "y_m": 8.0},
            {"thrust_N": 65000.0, "y_m": -8.0},
        ]
        self.assertEqual(vmc.critical_engine_index(engines), 1)

    def test_critical_engine_negative_y_magnitude_used(self):
        engines = [
            {"thrust_N": 65000.0, "y_m": -9.0},
            {"thrust_N": 30000.0, "y_m": 12.0},
        ]
        # |65000*-9| = 585000 > |30000*12| = 360000
        self.assertEqual(vmc.critical_engine_index(engines), 0)

    def test_critical_engine_empty_raises(self):
        with self.assertRaises(ValueError):
            vmc.critical_engine_index([])

    def test_critical_engine_zero_thrust_raises(self):
        engines = [{"thrust_N": 0.0, "y_m": 8.0}]
        with self.assertRaises(ValueError):
            vmc.critical_engine_index(engines)


class AsymmetricMomentTests(unittest.TestCase):
    def test_asymmetric_moment_worked_twin(self):
        # T_op * y_fail = 65000 * 8.0 = 520000 N m, windmilling neglected.
        m = vmc.asymmetric_yaw_moment_Nm(98.79, ENGINES_TWIN, 0, 0.0)
        self.assertAlmostEqual(m, 520000.0, places=1)

    def test_asymmetric_moment_negative_side_failure(self):
        # Left engine fails: y_fail = -8.0, moment sign flips.
        m = vmc.asymmetric_yaw_moment_Nm(70.0, ENGINES_TWIN, 1, 0.0)
        self.assertAlmostEqual(m, -520000.0, places=1)

    def test_asymmetric_moment_windmilling_contribution(self):
        v_speed = 73.87
        wm = 1.5
        base = vmc.asymmetric_yaw_moment_Nm(v_speed, ENGINES_TWIN, 0, 0.0)
        with_drag = vmc.asymmetric_yaw_moment_Nm(v_speed, ENGINES_TWIN, 0, wm)
        expected = 0.5 * vmc.RHO_SL * v_speed * v_speed * wm * 8.0
        self.assertAlmostEqual(with_drag - base, expected, places=1)

    def test_asymmetric_moment_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            vmc.asymmetric_yaw_moment_Nm(-1.0, ENGINES_TWIN, 0, 0.0)


class DeflectionRequiredTests(unittest.TestCase):
    def test_deflection_required_worked_speed(self):
        d = base_inputs()
        delta = vmc.rudder_deflection_required_rad(520000.0, 98.79, d)
        self.assertAlmostEqual(delta, 0.2718, places=3)

    def test_deflection_required_inverse_q_scaling(self):
        d = base_inputs()
        hi = vmc.rudder_deflection_required_rad(520000.0, 100.0, d)
        lo = vmc.rudder_deflection_required_rad(520000.0, 50.0, d)
        self.assertAlmostEqual(hi / lo, (50.0 / 100.0) ** 2, places=4)

    def test_deflection_round_trip_moment(self):
        d = base_inputs()
        n_asym = 520000.0
        v_speed = 90.0
        q = 0.5 * vmc.RHO_SL * v_speed * v_speed
        delta = vmc.rudder_deflection_required_rad(n_asym, v_speed, d)
        recovered = delta * q * 25.0 * 16.0 * 0.8
        self.assertAlmostEqual(recovered, n_asym, places=1)

    def test_deflection_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            vmc.rudder_deflection_required_rad(520000.0, 0.0, base_inputs())


class AuthorityLimitTests(unittest.TestCase):
    def test_authority_limited_speed_anchor(self):
        v_auth = vmc.authority_limited_speed(base_inputs())
        self.assertIsNotNone(v_auth)
        self.assertAlmostEqual(v_auth, 71.18, delta=0.05)

    def test_authority_limited_never_limited_returns_none(self):
        # Large windmilling drag removes the authority limit.
        d = base_inputs(windmilling_drag_area_m2=50.0)
        self.assertIsNone(vmc.authority_limited_speed(d))

    def test_authority_limited_no_operating_engine_raises(self):
        # Single engine that fails: no operating thrust remains.
        d = base_inputs(
            engines=[{"thrust_N": 65000.0, "y_m": 0.0}],
            failed_engine_index=0,
        )
        with self.assertRaises(ValueError):
            vmc.authority_limited_speed(d)

    def test_authority_limited_larger_fin_lowers_speed(self):
        base = vmc.authority_limited_speed(base_inputs())
        bigger = vmc.authority_limited_speed(
            base_inputs(vertical_tail_area_m2=35.0))
        self.assertIsNotNone(base)
        self.assertIsNotNone(bigger)
        self.assertGreater(base, bigger)


class PedalForceTests(unittest.TestCase):
    def test_pedal_force_at_vmc_anchor(self):
        d = base_inputs()
        r = vmc.vmc_predict(d)
        self.assertAlmostEqual(r["force_at_vmc_N"], 346.2, delta=2.0)

    def test_pedal_force_capped_at_rudder_limit(self):
        d = base_inputs()
        delta_max_rad = 30.0 * vmc.D2R
        f_capped = vmc.pedal_force_at_speed_N(60.0, d)
        q = 0.5 * vmc.RHO_SL * 60.0 * 60.0
        expected = (q * 8.5 * 1.3 * abs(-0.045) * delta_max_rad * 0.15
                    / 0.35)
        self.assertAlmostEqual(f_capped, expected, places=2)

    def test_pedal_force_scales_with_boost(self):
        boosted = vmc.pedal_force_at_speed_N(90.0, base_inputs(boost_factor=0.15))
        manual = vmc.pedal_force_at_speed_N(90.0, base_inputs(boost_factor=1.0))
        self.assertAlmostEqual(boosted, manual * 0.15, places=2)

    def test_pedal_force_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            vmc.pedal_force_at_speed_N(-5.0, base_inputs())


class VmcPredictTests(unittest.TestCase):
    def test_vmc_anchor_and_governing(self):
        r = vmc.vmc_predict(base_inputs())
        self.assertAlmostEqual(r["vmc_m_s"], 98.79, delta=0.05)
        self.assertEqual(r["governing"], "pedal-force")
        self.assertAlmostEqual(r["v_auth_m_s"], 71.18, delta=0.05)
        self.assertAlmostEqual(r["v_force_m_s"], 98.79, delta=0.05)

    def test_knots_anchor(self):
        r = vmc.vmc_predict(base_inputs())
        self.assertAlmostEqual(r["vmc_kt"], 192.0, delta=0.2)

    def test_force_ok_boosted_true(self):
        r = vmc.vmc_predict(base_inputs())
        self.assertTrue(r["force_ok"])
        self.assertTrue(r["flight_test_go"])

    def test_stall_guard_ok_verdict(self):
        r = vmc.vmc_predict(base_inputs())
        self.assertEqual(r["stall_guard_speed_m_s"], 69.3)
        self.assertEqual(r["guard_verdict"], "stall-guard-ok")

    def test_moment_at_vmc(self):
        r = vmc.vmc_predict(base_inputs())
        self.assertAlmostEqual(r["asymmetric_moment_at_vmc"], 520000.0,
                               places=1)

    def test_critical_engine_in_result(self):
        r = vmc.vmc_predict(base_inputs())
        self.assertEqual(r["critical_engine"], 0)


class ManualRudderTests(unittest.TestCase):
    def test_manual_rudder_force_fails_criterion(self):
        r = vmc.vmc_predict(base_inputs(boost_factor=1.0))
        self.assertAlmostEqual(r["force_at_vmc_N"], 2308.6, delta=5.0)
        self.assertFalse(r["force_ok"])
        self.assertFalse(r["flight_test_go"])

    def test_manual_rudder_authority_governs(self):
        r = vmc.vmc_predict(base_inputs(boost_factor=1.0))
        self.assertAlmostEqual(r["vmc_m_s"], 71.18, delta=0.05)
        self.assertEqual(r["governing"], "rudder-authority")
        self.assertAlmostEqual(r["v_force_m_s"], 38.26, delta=0.05)


class StallGuardTests(unittest.TestCase):
    def test_stall_guard_governs_verdict(self):
        # v_s1g 100 gives guard speed 105 above the 98.79 control limit.
        r = vmc.vmc_predict(base_inputs(v_s1g=100.0))
        self.assertEqual(r["stall_guard_speed_m_s"], 105.0)
        self.assertEqual(r["guard_verdict"], "stall-guard-governs")
        self.assertAlmostEqual(r["vmc_m_s"], 98.79, delta=0.05)
        self.assertFalse(r["flight_test_go"])

    def test_stall_guard_just_below_vmc_ok(self):
        r = vmc.vmc_predict(base_inputs(v_s1g=94.0))
        self.assertEqual(r["stall_guard_speed_m_s"], 98.7)
        self.assertEqual(r["guard_verdict"], "stall-guard-ok")
        self.assertTrue(r["flight_test_go"])


class WindmillingTests(unittest.TestCase):
    def test_windmilling_increases_v_auth(self):
        clean = vmc.vmc_predict(base_inputs())
        windmill = vmc.vmc_predict(base_inputs(windmilling_drag_area_m2=1.5))
        self.assertAlmostEqual(windmill["v_auth_m_s"], 73.87, delta=0.1)
        self.assertGreater(windmill["v_auth_m_s"], clean["v_auth_m_s"])
        # V_force still binds, so the reported Vmc is unchanged.
        self.assertAlmostEqual(windmill["vmc_m_s"], 98.79, delta=0.05)


class ValidationTests(unittest.TestCase):
    def test_zero_thrust_raises(self):
        d = base_inputs(engines=[{"thrust_N": 0.0, "y_m": 8.0},
                                 {"thrust_N": 65000.0, "y_m": -8.0}])
        with self.assertRaises(ValueError):
            vmc.vmc_predict(d)

    def test_zero_tail_area_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(vertical_tail_area_m2=0.0))

    def test_boost_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(boost_factor=1.5))

    def test_boost_zero_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(boost_factor=0.0))

    def test_deflection_over_60_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(rudder_deflection_max_deg=90.0))

    def test_deflection_zero_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(rudder_deflection_max_deg=0.0))

    def test_zero_vs1g_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(v_s1g=0.0))

    def test_negative_windmilling_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(windmilling_drag_area_m2=-1.0))

    def test_zero_hinge_moment_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(
                base_inputs(hinge_moment_coefficient_per_rad=0.0))

    def test_failed_index_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(failed_engine_index=5))

    def test_empty_engines_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(engines=[]))

    def test_zero_pedal_arm_raises(self):
        with self.assertRaises(ValueError):
            vmc.vmc_predict(base_inputs(pedal_arm_m=0.0))

    def test_missing_input_raises(self):
        d = base_inputs()
        del d["stall_guard"]
        with self.assertRaises(ValueError):
            vmc.vmc_predict(d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
