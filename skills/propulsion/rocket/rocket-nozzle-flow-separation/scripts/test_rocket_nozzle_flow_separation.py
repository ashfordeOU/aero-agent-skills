"""Contract test for rocket_nozzle_flow_separation_logic (wave-38).

Offline, deterministic, stdlib unittest only. Run from the repo root:

    python3 skills/propulsion/rocket/rocket-nozzle-flow-separation/scripts/test_rocket_nozzle_flow_separation.py

Covers the spec worked example (pc = 10 MPa, pa = 101325 Pa sea level,
gamma = 1.2, Ae_At = 40, pe_design = 40 kPa), the prep-verified anchors,
the closed-form identities, the ISA pressure relation, the verdict truth
table, the side-load regime flag, the separated thrust correction, and
ValueError rejection of every non-physical input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rocket_nozzle_flow_separation_logic as rnfs

PC = 10e6          # chamber pressure, Pa (worked example)
PA = 101325.0      # sea-level ambient pressure, Pa
GAMMA = 1.2
AE_AT = 40.0       # exit-to-throat area ratio (worked example)
PE_DESIGN = 40000.0  # design exit pressure, Pa (worked example)
TC = 3500.0        # chamber temperature, K (thrust-loss scale input)
AT = 0.1           # throat area, m^2 (thrust-loss scale input)


class TestModuleConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(rnfs.K_SEP, 0.4)
        self.assertEqual(rnfs.GAMMA_DEFAULT, 1.2)
        self.assertEqual(rnfs.R, 287.0)
        self.assertEqual(rnfs.G0, 9.80665)
        self.assertEqual(rnfs.ISA_SEA_LEVEL_PRESSURE, 101325.0)


class TestSeparationPressureRatio(unittest.TestCase):
    def test_anchor_sea_level(self):
        self.assertAlmostEqual(rnfs.separation_pressure_ratio(PA), 40530.0,
                               delta=1e-9)
        self.assertAlmostEqual(rnfs.separation_pressure_ratio(PA), 0.4 * PA,
                               delta=1e-9)

    def test_custom_k_sep_scaling(self):
        self.assertAlmostEqual(rnfs.separation_pressure_ratio(50000.0), 20000.0,
                               delta=1e-9)
        self.assertAlmostEqual(rnfs.separation_pressure_ratio(50000.0, 0.6),
                               30000.0, delta=1e-9)

    def test_raises_on_non_physical(self):
        with self.assertRaises(ValueError):
            rnfs.separation_pressure_ratio(0.0)
        with self.assertRaises(ValueError):
            rnfs.separation_pressure_ratio(-101325.0)
        with self.assertRaises(ValueError):
            rnfs.separation_pressure_ratio(PA, 0.0)
        with self.assertRaises(ValueError):
            rnfs.separation_pressure_ratio(PA, -0.4)


class TestSeparationMach(unittest.TestCase):
    def test_anchor_close_to_spec(self):
        # Spec: Mach at pc/p_sep = 246.7 and gamma 1.2 is 3.8787 within 1e-3.
        m = rnfs.separation_mach(246.7, 1.0, 1.2)
        self.assertAlmostEqual(m, 3.8787, delta=1e-3)

    def test_matches_closed_form(self):
        pc, p_sep, gamma = 1e7, 40530.0, 1.2
        expected = ((pc / p_sep) ** ((gamma - 1.0) / gamma) - 1.0) * 2.0 / (
            gamma - 1.0)
        self.assertAlmostEqual(rnfs.separation_mach(pc, p_sep, gamma),
                               expected ** 0.5, delta=1e-12)

    def test_raises_on_non_physical(self):
        for args in [(0.0, 1.0, 1.2), (-1e7, 1.0, 1.2), (1e7, 0.0, 1.2),
                     (1e7, -1.0, 1.2), (1e7, 1.0, 1.0), (1e7, 1.0, 0.8),
                     (1e7, 1e7, 1.2), (1e7, 2e7, 1.2)]:
            with self.assertRaises(ValueError):
                rnfs.separation_mach(*args)


class TestAreaRatioFromMach(unittest.TestCase):
    def test_identity_at_throat_gamma_1_2(self):
        self.assertAlmostEqual(rnfs.area_ratio_from_mach(1.0, 1.2), 1.0,
                               places=12)

    def test_identity_at_throat_gamma_1_4(self):
        self.assertAlmostEqual(rnfs.area_ratio_from_mach(1.0, 1.4), 1.0,
                               places=12)

    def test_raises_on_non_physical(self):
        with self.assertRaises(ValueError):
            rnfs.area_ratio_from_mach(0.0, 1.2)
        with self.assertRaises(ValueError):
            rnfs.area_ratio_from_mach(-2.0, 1.2)
        with self.assertRaises(ValueError):
            rnfs.area_ratio_from_mach(3.0, 1.0)
        with self.assertRaises(ValueError):
            rnfs.area_ratio_from_mach(3.0, 0.8)


class TestSeparationStationAreaRatio(unittest.TestCase):
    def test_anchor_value(self):
        # Spec: A_sep/At = 23.797 at pc = 10 MPa, pa = 101325 Pa, gamma 1.2.
        self.assertAlmostEqual(rnfs.separation_station_area_ratio(PC, PA, GAMMA),
                               23.797, delta=0.01)

    def test_grows_as_ambient_pressure_falls(self):
        # Lower ambient pressure means a deeper expansion before the wall
        # pressure reaches p_sep, so the separation station moves downstream.
        r_sea = rnfs.separation_station_area_ratio(PC, 101325.0, GAMMA)
        r_mid = rnfs.separation_station_area_ratio(PC, 50000.0, GAMMA)
        r_hi = rnfs.separation_station_area_ratio(PC, 20000.0, GAMMA)
        self.assertLess(r_sea, r_mid)
        self.assertLess(r_mid, r_hi)
        self.assertGreater(r_hi, 60.0)

    def test_raises_on_non_physical(self):
        with self.assertRaises(ValueError):
            rnfs.separation_station_area_ratio(0.0, PA, GAMMA)
        with self.assertRaises(ValueError):
            rnfs.separation_station_area_ratio(PC, 0.0, GAMMA)
        with self.assertRaises(ValueError):
            rnfs.separation_station_area_ratio(PC, PA, 1.0)
        # Ambient so high that p_sep reaches the chamber pressure.
        with self.assertRaises(ValueError):
            rnfs.separation_station_area_ratio(PC, 1e8, GAMMA)


class TestSeparatedVerdict(unittest.TestCase):
    def test_truth_table_across_area_ratios(self):
        a_sep = rnfs.separation_station_area_ratio(PC, PA, GAMMA)
        self.assertTrue(rnfs.separated_verdict(40.0, a_sep))    # Ae above
        self.assertTrue(rnfs.separated_verdict(25.0, a_sep))
        self.assertFalse(rnfs.separated_verdict(20.0, a_sep))   # Ae below
        self.assertFalse(rnfs.separated_verdict(10.0, a_sep))

    def test_boundary_exact_equality_is_attached(self):
        # Spec: attached (False) when Ae_At does not exceed A_sep/At.
        a_sep = rnfs.separation_station_area_ratio(PC, PA, GAMMA)
        self.assertFalse(rnfs.separated_verdict(a_sep, a_sep))
        self.assertFalse(rnfs.separated_verdict(23.79741837155888, a_sep))

    def test_raises_on_non_physical(self):
        with self.assertRaises(ValueError):
            rnfs.separated_verdict(1.0, 23.797)
        with self.assertRaises(ValueError):
            rnfs.separated_verdict(0.5, 23.797)
        with self.assertRaises(ValueError):
            rnfs.separated_verdict(40.0, 0.5)


class TestIsaPressure(unittest.TestCase):
    def test_sea_level_and_spec_altitude_anchors(self):
        self.assertEqual(rnfs.isa_pressure(0.0), 101325.0)
        # Spec: 30741 Pa at 9000 m, 26435 Pa at 10000 m, near 22632 Pa at
        # 11000 m (standard atmosphere closed form with exponent 5.2561).
        self.assertAlmostEqual(rnfs.isa_pressure(9000.0), 30741.0, delta=1.0)
        self.assertAlmostEqual(rnfs.isa_pressure(10000.0), 26435.0, delta=1.0)
        self.assertAlmostEqual(rnfs.isa_pressure(11000.0), 22632.0, delta=5.0)

    def test_isothermal_layer_above_tropopause(self):
        p_tropo = rnfs.isa_pressure(11000.0)
        self.assertLess(rnfs.isa_pressure(15000.0), p_tropo)
        self.assertLess(rnfs.isa_pressure(20000.0), rnfs.isa_pressure(15000.0))
        p_top = rnfs.isa_pressure(20000.0)
        self.assertGreater(p_top, 5400.0)
        self.assertLess(p_top, 5550.0)
        # Continuity at the tropopause boundary.
        self.assertAlmostEqual(rnfs.isa_pressure(11000.0),
                               rnfs.ISA_TROPOPAUSE_PRESSURE, delta=1e-6)

    def test_raises_on_negative_altitude(self):
        with self.assertRaises(ValueError):
            rnfs.isa_pressure(-1.0)


class TestSeparationAltitude(unittest.TestCase):
    def test_anchor_value(self):
        # Spec: separation_altitude(40000) near 7185 m within 1 percent.
        h = rnfs.separation_altitude(PE_DESIGN)
        self.assertAlmostEqual(h, 7185.0, delta=71.85)
        self.assertAlmostEqual(h, 7185.156765131445, delta=1e-6)

    def test_round_trip_isa_pressure(self):
        for pe in (60000.0, PE_DESIGN, 25000.0, 8000.0):
            h = rnfs.separation_altitude(pe)
            self.assertAlmostEqual(rnfs.isa_pressure(h), pe, delta=pe * 1e-6)

    def test_bracket_clamping(self):
        # pe_design at or above sea level un-separates at or below 0 m.
        self.assertEqual(rnfs.separation_altitude(101325.0), 0.0)
        self.assertEqual(rnfs.separation_altitude(200000.0), 0.0)
        # pe_design at or below the 20 km pressure stays separated to 20 km.
        self.assertEqual(rnfs.separation_altitude(5000.0), 20000.0)
        self.assertEqual(rnfs.separation_altitude(1000.0), 20000.0)

    def test_bisection_between_isa_bounds(self):
        # isa(9000) = 30741 Pa above 30000 Pa, isa(10000) = 26435 below it.
        h = rnfs.separation_altitude(30000.0)
        self.assertGreater(h, 9000.0)
        self.assertLess(h, 10000.0)

    def test_raises_on_non_physical(self):
        with self.assertRaises(ValueError):
            rnfs.separation_altitude(0.0)
        with self.assertRaises(ValueError):
            rnfs.separation_altitude(-40000.0)


class TestVerdictFlipAtSeparationAltitude(unittest.TestCase):
    def test_flow_un_separates_by_the_separation_altitude(self):
        # The design nozzle (Ae_At = 40) is separated at sea level.
        a_sep_sea = rnfs.separation_station_area_ratio(PC, PA, GAMMA)
        self.assertTrue(rnfs.separated_verdict(AE_AT, a_sep_sea))
        # At the separation altitude the ambient pressure has fallen to the
        # design exit pressure and the flow stays attached.
        h = rnfs.separation_altitude(PE_DESIGN)
        a_sep_alt = rnfs.separation_station_area_ratio(
            PC, rnfs.isa_pressure(h), GAMMA)
        self.assertFalse(rnfs.separated_verdict(AE_AT, a_sep_alt))


class TestSideLoadFlag(unittest.TestCase):
    def test_anchor_sea_level(self):
        # Spec: side-load flag True at sea level (separated and pe_design < pa).
        self.assertTrue(rnfs.side_load_flag(True, PC, PA, PE_DESIGN))
        self.assertTrue(rnfs.side_load_flag(True, PC, PA))

    def test_unseparated_flow_never_flags(self):
        # Spec: the un-separated case gives attached flow and no side-load flag.
        self.assertFalse(rnfs.side_load_flag(False, PC, PA, PE_DESIGN))
        self.assertFalse(rnfs.side_load_flag(False, PC, PA))

    def test_design_pressure_above_ambient_is_not_overexpanded(self):
        # Separated but running at or above design point: no side-load regime.
        self.assertFalse(rnfs.side_load_flag(True, PC, PA, 150000.0))
        self.assertFalse(rnfs.side_load_flag(True, PC, PA, PA))

    def test_pe_design_omitted_follows_separation_verdict(self):
        self.assertTrue(rnfs.side_load_flag(True, PC, PA))
        self.assertFalse(rnfs.side_load_flag(False, PC, PA))

    def test_raises_on_non_physical(self):
        with self.assertRaises(ValueError):
            rnfs.side_load_flag(1, PC, PA, PE_DESIGN)   # not a bool
        with self.assertRaises(ValueError):
            rnfs.side_load_flag("yes", PC, PA, PE_DESIGN)
        with self.assertRaises(ValueError):
            rnfs.side_load_flag(True, 0.0, PA, PE_DESIGN)
        with self.assertRaises(ValueError):
            rnfs.side_load_flag(True, PC, 0.0, PE_DESIGN)
        with self.assertRaises(ValueError):
            rnfs.side_load_flag(True, PC, PA, 0.0)
        with self.assertRaises(ValueError):
            rnfs.side_load_flag(True, PC, PA, -40000.0)


class TestSeparatedThrustLoss(unittest.TestCase):
    def test_separated_anchor_values(self):
        # Real module outputs for pc = 10 MPa, Tc = 3500 K, At = 0.1 m^2,
        # pa = 101325 Pa, gamma 1.2, Ae_At = 40 (spec magnitude bounds).
        res = rnfs.separated_thrust_loss(PC, TC, AT, PA, GAMMA, AE_AT)
        self.assertTrue(res["separated"])
        self.assertAlmostEqual(res["uncorrected_thrust"], 1800778.0883,
                               delta=0.01)
        self.assertAlmostEqual(res["corrected_thrust"], 1596534.4277,
                               delta=0.01)
        self.assertAlmostEqual(res["thrust_loss"], 204243.6606, delta=0.01)
        self.assertAlmostEqual(res["relative_loss"], 0.11341967, delta=1e-6)
        # Spec: the uncorrected thrust exceeds the corrected thrust when
        # separated, and the loss is positive.
        self.assertGreater(res["uncorrected_thrust"], res["corrected_thrust"])
        self.assertGreater(res["thrust_loss"], 0.0)
        self.assertAlmostEqual(
            res["thrust_loss"],
            res["uncorrected_thrust"] - res["corrected_thrust"], delta=1e-6)
        self.assertAlmostEqual(
            res["relative_loss"],
            res["thrust_loss"] / res["uncorrected_thrust"], delta=1e-9)

    def test_attached_case_has_no_loss(self):
        # Ae_At = 10 stays below the sea-level separation station (23.8),
        # so the flow is attached and no correction applies.
        res = rnfs.separated_thrust_loss(PC, TC, AT, PA, GAMMA, 10.0)
        self.assertFalse(res["separated"])
        self.assertEqual(res["thrust_loss"], 0.0)
        self.assertEqual(res["relative_loss"], 0.0)
        self.assertAlmostEqual(res["corrected_thrust"],
                               res["uncorrected_thrust"], delta=1e-9)

    def test_pa_sweep_separated_versus_attached(self):
        # Below about 52 kPa ambient the worked-example nozzle un-separates;
        # every separated point shows corrected below uncorrected, every
        # attached point shows equal thrusts.
        for pa, expect_separated in [(101325.0, True), (80000.0, True),
                                     (60000.0, True), (45000.0, False),
                                     (30000.0, False)]:
            res = rnfs.separated_thrust_loss(PC, TC, AT, pa, GAMMA, AE_AT)
            self.assertEqual(res["separated"], expect_separated)
            if expect_separated:
                self.assertGreater(res["thrust_loss"], 0.0)
                self.assertLess(res["corrected_thrust"],
                                res["uncorrected_thrust"])
            else:
                self.assertEqual(res["thrust_loss"], 0.0)

    def test_raises_on_non_physical(self):
        for kwargs in [dict(pc=0.0), dict(pc=-1e7), dict(Tc=0.0),
                       dict(At=0.0), dict(pa=0.0), dict(gamma=1.0),
                       dict(Ae_At=1.0), dict(Ae_At=0.5), dict(k_sep=0.0)]:
            args = dict(pc=PC, Tc=TC, At=AT, pa=PA, gamma=GAMMA, Ae_At=AE_AT)
            args.update(kwargs)
            with self.assertRaises(ValueError):
                rnfs.separated_thrust_loss(**args)
        # Ambient above the chamber-to-K_SEP threshold makes p_sep reach the
        # chamber pressure, which is non-physical for separation.
        with self.assertRaises(ValueError):
            rnfs.separated_thrust_loss(PC, TC, AT, 1e8, GAMMA, AE_AT)


class TestDeterminism(unittest.TestCase):
    def test_repeat_calls_identical(self):
        calls_a = [
            rnfs.separation_mach(PC, 40530.0, GAMMA),
            rnfs.separation_station_area_ratio(PC, PA, GAMMA),
            rnfs.isa_pressure(9000.0),
            rnfs.separation_altitude(PE_DESIGN),
            rnfs.separated_thrust_loss(PC, TC, AT, PA, GAMMA, AE_AT),
            rnfs.side_load_flag(True, PC, PA, PE_DESIGN),
        ]
        calls_b = [
            rnfs.separation_mach(PC, 40530.0, GAMMA),
            rnfs.separation_station_area_ratio(PC, PA, GAMMA),
            rnfs.isa_pressure(9000.0),
            rnfs.separation_altitude(PE_DESIGN),
            rnfs.separated_thrust_loss(PC, TC, AT, PA, GAMMA, AE_AT),
            rnfs.side_load_flag(True, PC, PA, PE_DESIGN),
        ]
        for a, b in zip(calls_a, calls_b):
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
