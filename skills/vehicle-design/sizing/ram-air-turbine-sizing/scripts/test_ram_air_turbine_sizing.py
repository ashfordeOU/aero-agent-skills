"""Contract test for the ram air turbine sizing logic (wave-36).

Offline, deterministic, stdlib unittest only. Run from the leaf directory
or repo root:

    python3 scripts/test_ram_air_turbine_sizing.py

Worked example contract: emergency RAT must supply 5000 W at the fixed
emergency descent speed of 100 m/s at ISA sea level (rho 1.225 kg/m3)
with the design power coefficient 0.10. Expected magnitude bounds:
area 0.081633 m2 within 1e-6, diameter 0.3224 m within 1e-4, round-trip
power 5000.00 W within 1e-6.
"""

import math
import unittest

from ram_air_turbine_sizing_logic import (
    BETZ_LIMIT,
    CP_RAT_DEFAULT,
    PI,
    RHO_SL_DEFAULT,
    disk_diameter,
    rat_available_power,
    rat_sizing_summary,
    rat_swept_area,
)

P_REQ = 5000.0
V_EMERGENCY = 100.0
AREA_EXPECTED = 5000.0 / 61250.0  # 0.081632653...
DIAMETER_EXPECTED = math.sqrt(4.0 * AREA_EXPECTED / PI)  # 0.322394...
STOW_LIMIT = 0.40


class TestWorkedExample(unittest.TestCase):
    """The wave-36 reference installation at 5000 W, 100 m/s."""

    def test_worked_example_swept_area_within_spec_bound(self):
        # 0.081633 m2 within 1e-6 absolute per the spec.
        area = rat_swept_area(P_REQ, V_EMERGENCY)
        self.assertAlmostEqual(area, 0.081633, delta=1e-6)
        self.assertAlmostEqual(area, AREA_EXPECTED, delta=1e-12)

    def test_worked_example_diameter_within_spec_bound(self):
        # 0.3224 m within 1e-4 absolute per the spec.
        diameter = disk_diameter(rat_swept_area(P_REQ, V_EMERGENCY))
        self.assertAlmostEqual(diameter, 0.3224, delta=1e-4)
        self.assertAlmostEqual(diameter, DIAMETER_EXPECTED, delta=1e-12)
        self.assertGreater(diameter, 0.32)
        self.assertLess(diameter, 0.33)

    def test_round_trip_power_equals_5000_watts_within_1e_6(self):
        available = rat_available_power(
            rat_swept_area(P_REQ, V_EMERGENCY), V_EMERGENCY
        )
        self.assertAlmostEqual(available, P_REQ, delta=1e-6)
        self.assertAlmostEqual(available, 5000.00, delta=1e-6)

    def test_stowage_verdict_pass_at_0_40_limit(self):
        summary = rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT)
        self.assertEqual(summary["stowage_verdict"], "PASS")
        self.assertLessEqual(summary["diameter_m"], STOW_LIMIT)
        self.assertAlmostEqual(summary["margin_w"], 0.0, delta=1e-6)

    def test_stowage_verdict_fail_at_0_30_limit(self):
        summary = rat_sizing_summary(P_REQ, V_EMERGENCY, 0.30)
        self.assertEqual(summary["stowage_verdict"], "FAIL")
        self.assertGreater(summary["diameter_m"], 0.30)


class TestSizingSummary(unittest.TestCase):
    """Summary dict structure, consistency and determinism."""

    def test_summary_dict_keys_exactly_as_documented(self):
        summary = rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT)
        self.assertEqual(
            list(summary.keys()),
            ["area_m2", "diameter_m", "available_w", "margin_w",
             "stowage_verdict"],
        )

    def test_summary_fields_consistent_with_functions(self):
        summary = rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT)
        self.assertAlmostEqual(
            summary["area_m2"], rat_swept_area(P_REQ, V_EMERGENCY), delta=1e-12
        )
        self.assertAlmostEqual(
            summary["diameter_m"],
            disk_diameter(rat_swept_area(P_REQ, V_EMERGENCY)),
            delta=1e-12,
        )
        self.assertAlmostEqual(
            summary["available_w"],
            rat_available_power(
                rat_swept_area(P_REQ, V_EMERGENCY), V_EMERGENCY
            ),
            delta=1e-9,
        )
        self.assertAlmostEqual(
            summary["margin_w"],
            summary["available_w"] - P_REQ,
            delta=1e-9,
        )

    def test_summary_is_deterministic_across_runs(self):
        first = rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT)
        second = rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT)
        self.assertEqual(first, second)

    def test_summary_verdict_boundary_exact_fit_passes(self):
        # A limit exactly equal to the diameter must pass (<=).
        diameter = disk_diameter(rat_swept_area(P_REQ, V_EMERGENCY))
        summary = rat_sizing_summary(P_REQ, V_EMERGENCY, diameter)
        self.assertEqual(summary["stowage_verdict"], "PASS")


class TestScalingLaws(unittest.TestCase):
    """Wind-power scaling: power goes as V^3 and A, area as 1/V^3."""

    def test_doubling_airspeed_octuples_available_power(self):
        area = rat_swept_area(P_REQ, V_EMERGENCY)
        power_lo = rat_available_power(area, V_EMERGENCY)
        power_hi = rat_available_power(area, 2.0 * V_EMERGENCY)
        self.assertAlmostEqual(power_hi, 8.0 * power_lo, delta=1e-6)
        power_half = rat_available_power(area, 0.5 * V_EMERGENCY)
        self.assertAlmostEqual(power_lo, 8.0 * power_half, delta=1e-6)

    def test_required_area_inversely_proportional_to_v_cubed(self):
        area_hi = rat_swept_area(P_REQ, 2.0 * V_EMERGENCY)
        area_ref = rat_swept_area(P_REQ, V_EMERGENCY)
        self.assertAlmostEqual(area_hi, area_ref / 8.0, delta=1e-12)

    def test_available_power_proportional_to_area(self):
        area = rat_swept_area(P_REQ, V_EMERGENCY)
        power_1x = rat_available_power(area, V_EMERGENCY)
        power_2x = rat_available_power(2.0 * area, V_EMERGENCY)
        self.assertAlmostEqual(power_2x, 2.0 * power_1x, delta=1e-6)

    def test_required_area_proportional_to_power(self):
        area_1x = rat_swept_area(P_REQ, V_EMERGENCY)
        area_2x = rat_swept_area(2.0 * P_REQ, V_EMERGENCY)
        self.assertAlmostEqual(area_2x, 2.0 * area_1x, delta=1e-12)

    def test_density_scales_power_linearly_and_area_inversely(self):
        area = rat_swept_area(P_REQ, V_EMERGENCY)
        power_sl = rat_available_power(area, V_EMERGENCY, rho=1.225)
        power_high = rat_available_power(area, V_EMERGENCY, rho=1.5)
        self.assertAlmostEqual(power_high, power_sl * 1.5 / 1.225, delta=1e-6)
        area_high = rat_swept_area(P_REQ, V_EMERGENCY, rho=1.5)
        self.assertAlmostEqual(area_high, area * 1.225 / 1.5, delta=1e-12)


class TestIdentities(unittest.TestCase):
    """Closed-form round trips required by the spec."""

    def test_disk_diameter_area_round_trip_identity(self):
        # A == pi * D^2 / 4 for any positive area.
        for area in (0.01, AREA_EXPECTED, 0.5, 1.0, 10.0):
            diameter = disk_diameter(area)
            self.assertAlmostEqual(area, PI * diameter ** 2 / 4.0, delta=1e-9)

    def test_swept_area_power_round_trip_identity(self):
        # rat_available_power(rat_swept_area(P)) == P within 1e-6.
        for power in (1000.0, P_REQ, 12000.0, 50000.0):
            available = rat_available_power(
                rat_swept_area(power, V_EMERGENCY), V_EMERGENCY
            )
            self.assertAlmostEqual(available, power, delta=1e-6)


class TestModuleConstants(unittest.TestCase):
    """Default module constants documented in the spec."""

    def test_rho_default_is_isa_sea_level(self):
        self.assertEqual(RHO_SL_DEFAULT, 1.225)

    def test_cp_default_is_design_value(self):
        self.assertEqual(CP_RAT_DEFAULT, 0.10)

    def test_betz_limit_is_16_over_27(self):
        self.assertAlmostEqual(BETZ_LIMIT, 16.0 / 27.0, delta=1e-12)
        self.assertAlmostEqual(BETZ_LIMIT, 0.592593, delta=1e-6)

    def test_defaults_give_worked_example_area(self):
        area = rat_swept_area(P_REQ, V_EMERGENCY)
        manual = 0.5 * 1.225 * V_EMERGENCY ** 3 * area * 0.10
        self.assertAlmostEqual(area, AREA_EXPECTED, delta=1e-12)
        self.assertAlmostEqual(manual, P_REQ, delta=1e-6)


class TestValueErrorRejection(unittest.TestCase):
    """Non-physical inputs must raise ValueError."""

    def test_nonpositive_required_power_raises(self):
        for bad in (0.0, -1.0, -5000.0):
            with self.assertRaises(ValueError):
                rat_swept_area(bad, V_EMERGENCY)

    def test_nonpositive_airspeed_raises(self):
        for bad in (0.0, -10.0):
            with self.assertRaises(ValueError):
                rat_swept_area(P_REQ, bad)

    def test_nonpositive_density_raises(self):
        for bad in (0.0, -1.225):
            with self.assertRaises(ValueError):
                rat_swept_area(P_REQ, V_EMERGENCY, rho=bad)

    def test_nonpositive_power_coefficient_raises(self):
        for bad in (0.0, -0.05):
            with self.assertRaises(ValueError):
                rat_swept_area(P_REQ, V_EMERGENCY, cp=bad)

    def test_cp_at_or_above_betz_limit_raises(self):
        # cp >= 0.592593 must raise; a 0.60 input is the spec example.
        for bad in (BETZ_LIMIT, 0.60, 0.70):
            with self.assertRaises(ValueError):
                rat_swept_area(P_REQ, V_EMERGENCY, cp=bad)
            with self.assertRaises(ValueError):
                rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT, cp=bad)

    def test_nonpositive_area_in_disk_diameter_raises(self):
        for bad in (0.0, -0.5):
            with self.assertRaises(ValueError):
                disk_diameter(bad)

    def test_nonpositive_area_in_available_power_raises(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rat_available_power(bad, V_EMERGENCY)

    def test_available_power_rejects_bad_airspeed_and_cp(self):
        area = rat_swept_area(P_REQ, V_EMERGENCY)
        with self.assertRaises(ValueError):
            rat_available_power(area, 0.0)
        with self.assertRaises(ValueError):
            rat_available_power(area, V_EMERGENCY, cp=0.60)
        with self.assertRaises(ValueError):
            rat_available_power(area, V_EMERGENCY, rho=-1.0)

    def test_summary_rejects_nonphysical_stowage_and_sizing_inputs(self):
        for bad_limit in (0.0, -0.4):
            with self.assertRaises(ValueError):
                rat_sizing_summary(P_REQ, V_EMERGENCY, bad_limit)
        with self.assertRaises(ValueError):
            rat_sizing_summary(0.0, V_EMERGENCY, STOW_LIMIT)
        with self.assertRaises(ValueError):
            rat_sizing_summary(P_REQ, 0.0, STOW_LIMIT)
        with self.assertRaises(ValueError):
            rat_sizing_summary(P_REQ, V_EMERGENCY, STOW_LIMIT, rho=-1.225)


if __name__ == "__main__":
    unittest.main()
