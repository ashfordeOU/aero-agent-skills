"""Contract test for the subsonic-inlet-recovery logic module.

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/propulsion/gas-turbine-cycle/subsonic-inlet-recovery/\
        scripts/test_subsonic-inlet-recovery.py

Worked example (spec): mach 0.82, p0 = 101325 Pa, T0 = 216.65 K, duct
efficiency 0.98, engine mass flow 200 kg/s, highlight 0.60 m2. Real
module outputs used as assert targets: ram_recovery(0.82) = 1.0,
ram_recovery(1.5) = 0.9705781, stagnation_pressure_ratio(0.82) =
1.5552097, face_total_pressure = 154429.99 Pa (spec bound 154430 Pa
within 1 Pa), capture_area = 0.5072894 m2 (spec bound 0.5075 m2 within
1e-3), full-capture at 0.60 m2 highlight, spillage at 0.45 m2.
"""

import importlib.util
import math
import os
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "subsonic_inlet_recovery_logic",
    os.path.join(_SCRIPTS, "subsonic-inlet-recovery_logic.py"),
)
logic = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(logic)

# Worked example flight condition (spec).
MACH = 0.82
P0 = 101325.0
T0 = 216.65
DUCT_EFF = 0.98
MASS_FLOW = 200.0
HIGHLIGHT_FULL = 0.60
HIGHLIGHT_SPILL = 0.45
CAPTURE_AREA_WORKED = 0.5072894


class TestRamRecovery(unittest.TestCase):
    def test_subsonic_unity_anchor(self):
        # ram_recovery(0.82) = 1.0, full recovery below Mach 1.
        self.assertEqual(logic.ram_recovery(MACH), 1.0)

    def test_subsonic_unity_up_to_mach_one(self):
        for m in (0.0, 0.3, 0.8, 1.0):
            self.assertEqual(logic.ram_recovery(m), 1.0)

    def test_low_supersonic_rolloff_1_2(self):
        # Truth table: 1 - 0.075 * 0.2 ** 1.35 = 0.9914601.
        expected = 1.0 - logic.RECOVERY_ROLLOFF * 0.2 ** logic.RECOVERY_EXPONENT
        self.assertAlmostEqual(logic.ram_recovery(1.2), expected, places=12)
        self.assertAlmostEqual(logic.ram_recovery(1.2), 0.9914601, places=6)

    def test_mach_two_rolloff_0_925(self):
        # Truth table: 1 - 0.075 * 1.0 ** 1.35 = 0.925 exactly.
        self.assertAlmostEqual(logic.ram_recovery(2.0), 0.925, places=12)

    def test_mach_1_5_spec_bound(self):
        # Prep-verified bound: ram_recovery(1.5) = 0.970578.
        self.assertAlmostEqual(logic.ram_recovery(1.5), 0.970578, delta=1e-5)

    def test_rolloff_monotonic_decreasing_above_mach_one(self):
        values = [logic.ram_recovery(m) for m in (1.01, 1.5, 2.0, 3.0, 4.9)]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertGreater(values[-1], 0.0)

    def test_supersonic_recovery_in_open_unit_interval(self):
        for m in (1.05, 1.5, 2.5, 4.5):
            r = logic.ram_recovery(m)
            self.assertGreater(r, 0.0)
            self.assertLess(r, 1.0)

    def test_negative_mach_raises(self):
        with self.assertRaises(ValueError):
            logic.ram_recovery(-0.5)

    def test_mach_at_and_above_five_raises(self):
        for m in (5.0, 6.0):
            with self.assertRaises(ValueError):
                logic.ram_recovery(m)


class TestStagnationPressureRatio(unittest.TestCase):
    def test_anchor_0_82(self):
        # Spec bound: stagnation_pressure_ratio(0.82) = 1.5552.
        self.assertAlmostEqual(
            logic.stagnation_pressure_ratio(MACH), 1.5552, delta=5e-4
        )

    def test_formula_identity_including_rest(self):
        for m in (0.0, 0.5, 1.3, 2.0):
            self.assertAlmostEqual(
                logic.stagnation_pressure_ratio(m),
                (1.0 + 0.2 * m ** 2) ** 3.5,
                places=12,
            )

    def test_monotonic_in_mach(self):
        self.assertGreater(
            logic.stagnation_pressure_ratio(2.0),
            logic.stagnation_pressure_ratio(0.5),
        )

    def test_negative_mach_raises(self):
        with self.assertRaises(ValueError):
            logic.stagnation_pressure_ratio(-1.0)


class TestFaceTotalPressure(unittest.TestCase):
    def test_anchor_within_one_pa(self):
        # Spec anchor: 154430 Pa within 1 Pa at mach 0.82, duct eff 0.98.
        ftp = logic.face_total_pressure(P0, MACH, DUCT_EFF)
        self.assertAlmostEqual(ftp, 154430.0, delta=1.0)
        self.assertAlmostEqual(ftp, 154429.9896, places=3)

    def test_subsonic_full_recovery_identity(self):
        # With mach <= 1 and duct efficiency 1.0 the face total pressure
        # is exactly p0 * stagnation_pressure_ratio(mach).
        for m in (0.3, 0.6, MACH, 1.0):
            self.assertAlmostEqual(
                logic.face_total_pressure(P0, m, 1.0),
                P0 * logic.stagnation_pressure_ratio(m),
                places=6,
            )

    def test_duct_efficiency_scaling(self):
        self.assertAlmostEqual(
            logic.face_total_pressure(P0, MACH, 1.0) * DUCT_EFF,
            logic.face_total_pressure(P0, MACH, DUCT_EFF),
            places=6,
        )

    def test_zero_and_negative_p0_raises(self):
        for p0 in (0.0, -100.0):
            with self.assertRaises(ValueError):
                logic.face_total_pressure(p0, MACH, DUCT_EFF)

    def test_duct_efficiency_out_of_range_raises(self):
        for eff in (0.0, -0.1, 1.01):
            with self.assertRaises(ValueError):
                logic.face_total_pressure(P0, MACH, eff)

    def test_out_of_domain_mach_raises(self):
        for m in (-0.5, 5.0):
            with self.assertRaises(ValueError):
                logic.face_total_pressure(P0, m, DUCT_EFF)


class TestCaptureArea(unittest.TestCase):
    def test_anchor_within_one_e_minus_three(self):
        # Spec anchor: 0.5075 m2 within 1e-3 at 200 kg/s on the 11 km day.
        ca = logic.capture_area(MASS_FLOW, P0, T0, MACH)
        self.assertAlmostEqual(ca, 0.5075, delta=1e-3)
        self.assertAlmostEqual(ca, CAPTURE_AREA_WORKED, places=6)

    def test_inverse_density_scaling_identity(self):
        # Area scales inversely with density: doubling p0 at fixed T0
        # halves the required capture area.
        ca1 = logic.capture_area(MASS_FLOW, P0, T0, MACH)
        ca2 = logic.capture_area(MASS_FLOW, 2.0 * P0, T0, MACH)
        self.assertAlmostEqual(ca2, 0.5 * ca1, places=10)
        # Doubling mass flow doubles the area; halving mach doubles it.
        self.assertAlmostEqual(
            logic.capture_area(2.0 * MASS_FLOW, P0, T0, MACH),
            2.0 * ca1,
            places=10,
        )
        self.assertAlmostEqual(
            logic.capture_area(MASS_FLOW, P0, T0, 0.5 * MACH),
            2.0 * ca1,
            places=6,
        )

    def test_zero_and_negative_mass_flow_raises(self):
        for mf in (0.0, -50.0):
            with self.assertRaises(ValueError):
                logic.capture_area(mf, P0, T0, MACH)

    def test_zero_and_negative_p0_raises(self):
        for p0 in (0.0, -1000.0):
            with self.assertRaises(ValueError):
                logic.capture_area(MASS_FLOW, p0, T0, MACH)

    def test_zero_and_negative_T0_raises(self):
        for t0 in (0.0, -10.0):
            with self.assertRaises(ValueError):
                logic.capture_area(MASS_FLOW, P0, t0, MACH)

    def test_zero_mach_raises(self):
        with self.assertRaises(ValueError):
            logic.capture_area(MASS_FLOW, P0, T0, 0.0)


class TestCaptureVerdict(unittest.TestCase):
    def test_full_capture_against_0_60(self):
        self.assertEqual(
            logic.capture_verdict(CAPTURE_AREA_WORKED, HIGHLIGHT_FULL),
            "full-capture",
        )

    def test_spillage_against_0_45(self):
        self.assertEqual(
            logic.capture_verdict(CAPTURE_AREA_WORKED, HIGHLIGHT_SPILL),
            "spillage",
        )

    def test_boundary_equal_is_full_capture(self):
        self.assertEqual(logic.capture_verdict(0.60, 0.60), "full-capture")

    def test_nonpositive_area_raises(self):
        for a, h in ((-1.0, 0.60), (0.5, 0.0)):
            with self.assertRaises(ValueError):
                logic.capture_verdict(a, h)


class TestModuleAndEndToEnd(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(logic.GAMMA, 1.4)
        self.assertEqual(logic.R_AIR, 287.0)
        self.assertEqual(logic.RECOVERY_ROLLOFF, 0.075)
        self.assertEqual(logic.RECOVERY_EXPONENT, 1.35)

    def test_worked_example_end_to_end_and_determinism(self):
        # Flight condition mach 0.82 at the 216.65 K standard day,
        # recomputed from the module relations and determinism check.
        spr = logic.stagnation_pressure_ratio(MACH)
        ftp = logic.face_total_pressure(P0, MACH, DUCT_EFF)
        self.assertAlmostEqual(ftp, P0 * spr * 1.0 * DUCT_EFF, places=6)
        rho = P0 / (logic.R_AIR * T0)
        speed = MACH * math.sqrt(logic.GAMMA * logic.R_AIR * T0)
        ca = logic.capture_area(MASS_FLOW, P0, T0, MACH)
        self.assertAlmostEqual(ca, MASS_FLOW / (rho * speed), places=12)
        self.assertEqual(ca, logic.capture_area(MASS_FLOW, P0, T0, MACH))
        self.assertEqual(ftp, logic.face_total_pressure(P0, MACH, DUCT_EFF))


if __name__ == "__main__":
    unittest.main()
