#!/usr/bin/env python3
"""Offline deterministic contract test for airspeed-conversion logic.

Covers the wave-32 spec: worked-example magnitude bounds, ValueError
rejection of every non-physical input, monotonicity, EAS < CAS < TAS
ordering at altitude, sea-level identity, round-trip identities at
0 / 3048 / 9144 m, chain dict shape and the exactly-one-input rule.
Run: python3 scripts/test_airspeed_conversion.py (stdlib only).
"""

import math
import unittest

from airspeed_conversion_logic import (
    GAMMA,
    R_GAS,
    T0_ISA,
    P0_ISA,
    RHO0_ISA,
    A0_ISA,
    G0,
    LAPSE,
    TROPOPAUSE,
    T_TROPOPAUSE,
    KT_TO_MS,
    QC_SONIC_RATIO,
    isa_state,
    impact_pressure_from_mach,
    mach_from_impact_pressure,
    calibrated_from_impact_pressure,
    calibrated_from_true_airspeed,
    true_from_calibrated,
    equivalent_from_true,
    true_from_equivalent,
    mach_from_true_airspeed,
    airspeed_chain,
)

SL = 0.0
ALT_10KFT = 3048.0  # 10,000 ft
ALT_30KFT = 9144.0  # 30,000 ft
TROPO = 11000.0


class TestAirspeedConversion(unittest.TestCase):
    """Contract checks for the compressibility-corrected airspeed chain."""

    def test_module_constants(self):
        """Module constants match the spec values."""
        self.assertEqual(GAMMA, 1.4)
        self.assertEqual(R_GAS, 287.05287)
        self.assertEqual(T0_ISA, 288.15)
        self.assertEqual(P0_ISA, 101325.0)
        self.assertEqual(RHO0_ISA, 1.225)
        self.assertAlmostEqual(A0_ISA, 340.294, places=3)
        self.assertEqual(G0, 9.80665)
        self.assertEqual(LAPSE, 0.0065)
        self.assertEqual(TROPOPAUSE, 11000.0)
        self.assertAlmostEqual(KT_TO_MS, 0.514444, places=6)
        self.assertAlmostEqual(QC_SONIC_RATIO, 0.89293, places=4)

    def test_isa_state_sea_level(self):
        """ISA sea level returns the reference values."""
        s = isa_state(SL)
        self.assertAlmostEqual(s["T"], 288.15, places=6)
        self.assertAlmostEqual(s["p"], 101325.0, places=3)
        self.assertAlmostEqual(s["rho"], 1.225, places=5)
        self.assertAlmostEqual(s["a"], A0_ISA, places=6)
        self.assertEqual(set(s), {"T", "p", "rho", "a"})

    def test_isa_state_30000_ft_values(self):
        """ISA at 9144 m: T 228.71 K, p in 30089-30100 Pa, rho 0.4583, a 303.17."""
        s = isa_state(ALT_30KFT)
        self.assertAlmostEqual(s["T"], 228.71, delta=0.01)
        self.assertGreaterEqual(s["p"], 30089.0)
        self.assertLessEqual(s["p"], 30100.0)
        self.assertAlmostEqual(s["rho"], 0.4583, delta=0.001)
        self.assertAlmostEqual(s["a"], 303.17, delta=0.01)

    def test_isa_state_tropopause_values(self):
        """ISA at the tropopause: T 216.65 K, p about 22632 Pa, a 295.07 m/s."""
        s = isa_state(TROPO)
        self.assertAlmostEqual(s["T"], 216.65, places=9)
        self.assertAlmostEqual(s["p"], 22632.0, delta=1.0)
        self.assertAlmostEqual(s["a"], 295.07, delta=0.01)
        self.assertAlmostEqual(s["rho"], 0.36392, delta=1e-4)

    def test_isa_state_above_tropopause_isothermal_decay(self):
        """Above 11 km the layer is isothermal with exponential pressure decay."""
        s11 = isa_state(TROPO)
        s12 = isa_state(12000.0)
        self.assertEqual(s11["T"], s12["T"])
        self.assertEqual(s12["T"], T_TROPOPAUSE)
        expect = s11["p"] * math.exp(-G0 * 1000.0 / (R_GAS * T_TROPOPAUSE))
        self.assertAlmostEqual(s12["p"], expect, places=6)
        self.assertEqual(s11["a"], s12["a"])
        # pressure and density keep falling with altitude
        self.assertLess(s12["p"], s11["p"])
        self.assertLess(s12["rho"], s11["rho"])

    def test_isa_state_negative_altitude_raises(self):
        """Negative altitude is rejected."""
        for h in (-1.0, -10000.0):
            with self.assertRaises(ValueError):
                isa_state(h)

    def test_impact_pressure_mach_08_at_tropopause(self):
        """qc(M=0.8, p=22632) lands in 11800-11950 Pa, about 11866.9."""
        qc = impact_pressure_from_mach(0.8, 22632.0)
        self.assertGreaterEqual(qc, 11800.0)
        self.assertLessEqual(qc, 11950.0)
        self.assertAlmostEqual(qc, 11866.9, delta=0.5)

    def test_impact_pressure_mach_zero_is_zero(self):
        """M = 0 gives zero impact pressure at any static pressure."""
        self.assertEqual(impact_pressure_from_mach(0.0, 30089.0), 0.0)
        self.assertEqual(impact_pressure_from_mach(0.0, P0_ISA), 0.0)

    def test_impact_pressure_invalid_inputs_raise(self):
        """Negative Mach, supersonic Mach and non-positive pressure reject."""
        with self.assertRaises(ValueError):
            impact_pressure_from_mach(-0.1, 101325.0)
        with self.assertRaises(ValueError):
            impact_pressure_from_mach(1.0, 101325.0)
        with self.assertRaises(ValueError):
            impact_pressure_from_mach(1.2, 101325.0)
        with self.assertRaises(ValueError):
            impact_pressure_from_mach(0.5, 0.0)
        with self.assertRaises(ValueError):
            impact_pressure_from_mach(0.5, -100.0)

    def test_mach_from_impact_pressure_roundtrip(self):
        """qc -> M -> qc is lossless for subsonic Mach numbers."""
        p = 30089.0
        for m in (0.2, 0.5, 0.8, 0.95):
            qc = impact_pressure_from_mach(m, p)
            self.assertAlmostEqual(mach_from_impact_pressure(qc, p), m, places=12)

    def test_mach_from_impact_pressure_supersonic_ratio_raises(self):
        """qc/p at or above the sonic ratio 0.8929 is rejected."""
        p = 101325.0
        with self.assertRaises(ValueError):
            mach_from_impact_pressure(0.9 * p, p)
        with self.assertRaises(ValueError):
            mach_from_impact_pressure(QC_SONIC_RATIO * p, p)
        # just below the ratio stays subsonic and valid
        m = mach_from_impact_pressure(0.5 * p, p)
        self.assertGreater(m, 0.0)
        self.assertLess(m, 1.0)

    def test_mach_from_impact_pressure_invalid_inputs_raise(self):
        """Negative qc and non-positive static pressure reject."""
        with self.assertRaises(ValueError):
            mach_from_impact_pressure(-1.0, 101325.0)
        with self.assertRaises(ValueError):
            mach_from_impact_pressure(1000.0, 0.0)
        with self.assertRaises(ValueError):
            mach_from_impact_pressure(1000.0, -50.0)

    def test_calibrated_from_impact_pressure_250_kcas(self):
        """qc of the 250 KCAS point recovers 250 kt CAS (128.611 m/s)."""
        qc = 10498.2  # Pa, module output for 250 KCAS at 30,000 ft
        cas_ms = calibrated_from_impact_pressure(qc)
        self.assertAlmostEqual(cas_ms, 250.0 * KT_TO_MS, delta=0.01)

    def test_calibrated_from_impact_pressure_zero_and_negative(self):
        """qc = 0 gives CAS 0; negative qc rejects."""
        self.assertEqual(calibrated_from_impact_pressure(0.0), 0.0)
        with self.assertRaises(ValueError):
            calibrated_from_impact_pressure(-0.001)

    def test_calibrated_from_true_airspeed_m08_at_tropopause(self):
        """TAS 236.06 m/s at 11000 m maps to about 265.2 kt CAS."""
        cas_ms = calibrated_from_true_airspeed(236.0556, TROPO)
        self.assertAlmostEqual(cas_ms / KT_TO_MS, 265.21, delta=0.05)
        self.assertGreaterEqual(cas_ms / KT_TO_MS, 265.0)
        self.assertLessEqual(cas_ms / KT_TO_MS, 266.0)

    def test_calibrated_from_true_airspeed_invalid_raises(self):
        """Negative TAS and supersonic TAS reject."""
        with self.assertRaises(ValueError):
            calibrated_from_true_airspeed(-1.0, SL)
        a0 = isa_state(SL)["a"]
        with self.assertRaises(ValueError):
            calibrated_from_true_airspeed(2.0 * a0, SL)

    def test_true_from_calibrated_250kcas_30kft(self):
        """250 KCAS at 9144 m: TAS in 200-205 m/s (about 202.55), M about 0.668."""
        cas_ms = 250.0 * KT_TO_MS
        tas = true_from_calibrated(cas_ms, ALT_30KFT)
        self.assertGreaterEqual(tas, 200.0)
        self.assertLessEqual(tas, 205.0)
        self.assertAlmostEqual(tas, 202.55, delta=0.05)
        self.assertAlmostEqual(tas / KT_TO_MS, 393.73, delta=0.05)
        s = isa_state(ALT_30KFT)
        self.assertAlmostEqual(tas / s["a"], 0.668, delta=0.002)

    def test_true_from_calibrated_sea_level_identity(self):
        """At sea level CAS equals TAS (compressibility at SL conditions)."""
        tas = true_from_calibrated(100.0, SL)
        self.assertAlmostEqual(tas, 100.0, places=9)
        self.assertAlmostEqual(
            true_from_calibrated(250.0 * KT_TO_MS, SL), 250.0 * KT_TO_MS, places=9
        )

    def test_true_from_calibrated_negative_cas_raises(self):
        """Negative CAS rejects."""
        with self.assertRaises(ValueError):
            true_from_calibrated(-1.0, SL)
        with self.assertRaises(ValueError):
            true_from_calibrated(-128.0, ALT_30KFT)

    def test_round_trip_cas_tas_cas_three_altitudes(self):
        """CAS -> TAS -> CAS recovers CAS to < 1e-9 m/s at 0, 3048, 9144 m."""
        for h in (SL, ALT_10KFT, ALT_30KFT):
            for cas in (60.0, 128.611, 170.0):
                back = calibrated_from_true_airspeed(
                    true_from_calibrated(cas, h), h
                )
                self.assertLess(abs(back - cas), 1e-9)

    def test_round_trip_tas_cas_tas_three_altitudes(self):
        """TAS -> CAS -> TAS recovers TAS to < 1e-9 m/s at 0, 3048, 9144 m."""
        for h in (SL, ALT_10KFT, ALT_30KFT):
            for tas in (100.0, 150.0, 202.55):
                back = true_from_calibrated(
                    calibrated_from_true_airspeed(tas, h), h
                )
                self.assertLess(abs(back - tas), 1e-9)

    def test_round_trip_eas_tas_three_altitudes(self):
        """EAS <-> TAS round trips are exact to < 1e-9 at three altitudes."""
        for h in (SL, ALT_10KFT, ALT_30KFT):
            rho = isa_state(h)["rho"]
            for tas in (100.0, 150.0, 202.55):
                eas = equivalent_from_true(tas, rho)
                self.assertLess(abs(true_from_equivalent(eas, rho) - tas), 1e-9)

    def test_equivalent_from_true_10000ft_worked_example(self):
        """TAS 150 m/s at 3048 m gives EAS about 128.9 m/s."""
        rho = isa_state(ALT_10KFT)["rho"]
        self.assertAlmostEqual(rho / RHO0_ISA, 0.7385, delta=0.0005)
        eas = equivalent_from_true(150.0, rho)
        self.assertAlmostEqual(eas, 128.9, delta=0.05)
        self.assertLess(eas, 150.0)

    def test_equivalent_from_true_sea_level_identity(self):
        """At sea-level density EAS equals TAS."""
        eas = equivalent_from_true(150.0, RHO0_ISA)
        self.assertAlmostEqual(eas, 150.0, places=12)

    def test_equivalent_functions_invalid_inputs_raise(self):
        """Negative speeds and non-positive densities reject in both legs."""
        with self.assertRaises(ValueError):
            equivalent_from_true(-1.0, RHO0_ISA)
        with self.assertRaises(ValueError):
            equivalent_from_true(100.0, 0.0)
        with self.assertRaises(ValueError):
            equivalent_from_true(100.0, -1.225)
        with self.assertRaises(ValueError):
            true_from_equivalent(-1.0, RHO0_ISA)
        with self.assertRaises(ValueError):
            true_from_equivalent(100.0, 0.0)

    def test_mach_from_true_airspeed(self):
        """M = TAS / a reproduces the 0.8 tropopause point and rejects bad input."""
        s = isa_state(TROPO)
        tas_at_m08 = 0.8 * s["a"]
        self.assertAlmostEqual(mach_from_true_airspeed(tas_at_m08, s["a"]), 0.8, delta=1e-12)
        self.assertAlmostEqual(tas_at_m08, 236.06, delta=0.01)
        self.assertEqual(mach_from_true_airspeed(0.0, s["a"]), 0.0)
        with self.assertRaises(ValueError):
            mach_from_true_airspeed(-10.0, s["a"])
        with self.assertRaises(ValueError):
            mach_from_true_airspeed(100.0, 0.0)

    def test_ordering_eas_cas_tas_at_altitude(self):
        """At 9144 m for 250 KCAS: EAS < CAS < TAS (compressible inversion)."""
        r = airspeed_chain(ALT_30KFT, cas_kt=250.0)
        self.assertLess(r["eas_kt"], r["cas_kt"])
        self.assertLess(r["cas_kt"], r["tas_ms"] / KT_TO_MS)

    def test_monotonicity_with_qc(self):
        """CAS and Mach both increase with impact pressure."""
        self.assertLess(
            calibrated_from_impact_pressure(10000.0),
            calibrated_from_impact_pressure(20000.0),
        )
        p = 101325.0
        m_low = mach_from_impact_pressure(5000.0, p)
        m_high = mach_from_impact_pressure(15000.0, p)
        self.assertLess(m_low, m_high)

    def test_tas_fixed_cas_increases_with_altitude(self):
        """Lower density at altitude needs higher TAS for the same qc/CAS."""
        cas_ms = 250.0 * KT_TO_MS
        tas_sl = true_from_calibrated(cas_ms, SL)
        tas_30k = true_from_calibrated(cas_ms, ALT_30KFT)
        self.assertGreater(tas_30k, tas_sl)

    def test_chain_worked_example_250kcas_30kft(self):
        """Chain dict for 250 KCAS at 9144 m carries the full air-data set."""
        r = airspeed_chain(ALT_30KFT, cas_kt=250.0)
        self.assertEqual(
            set(r),
            {"altitude_m", "p", "rho", "a", "mach", "cas_kt", "eas_kt",
             "tas_ms", "qc_Pa"},
        )
        self.assertAlmostEqual(r["cas_kt"], 250.0, delta=1e-9)
        self.assertGreaterEqual(r["qc_Pa"], 10400.0)
        self.assertLessEqual(r["qc_Pa"], 10600.0)
        self.assertAlmostEqual(r["qc_Pa"], 10498.2, delta=1.0)
        self.assertGreaterEqual(r["mach"], 0.66)
        self.assertLessEqual(r["mach"], 0.68)
        self.assertGreaterEqual(r["tas_ms"], 200.0)
        self.assertLessEqual(r["tas_ms"], 205.0)
        self.assertGreaterEqual(r["eas_kt"], 239.0)
        self.assertLessEqual(r["eas_kt"], 242.0)
        # deterministic: identical rerun gives bit-identical floats (no RNG)
        self.assertEqual(r, airspeed_chain(ALT_30KFT, cas_kt=250.0))
        self.assertEqual(
            calibrated_from_true_airspeed(150.0, ALT_10KFT),
            calibrated_from_true_airspeed(150.0, ALT_10KFT),
        )

    def test_chain_worked_example_mach_08_tropopause(self):
        """M = 0.8 at 11000 m: qc about 11866, CAS 265.2, EAS 250.1, TAS 236.06."""
        r = airspeed_chain(TROPO, mach=0.8)
        self.assertGreaterEqual(r["qc_Pa"], 11800.0)
        self.assertLessEqual(r["qc_Pa"], 11950.0)
        self.assertAlmostEqual(r["cas_kt"], 265.21, delta=0.1)
        self.assertAlmostEqual(r["eas_kt"], 250.10, delta=0.15)
        self.assertAlmostEqual(r["tas_ms"], 236.06, delta=0.01)
        self.assertAlmostEqual(r["tas_ms"] / KT_TO_MS, 458.86, delta=0.05)

    def test_chain_sea_level_identity_within_0_001_kt(self):
        """Sea level 100 m/s CAS collapses to identity: EAS == TAS == CAS."""
        r = airspeed_chain(SL, cas_kt=100.0 / KT_TO_MS)
        self.assertAlmostEqual(r["tas_ms"], 100.0, delta=1e-6)
        self.assertLess(abs(r["eas_kt"] - r["cas_kt"]), 0.001)
        self.assertLess(abs(r["tas_ms"] / KT_TO_MS - r["cas_kt"]), 0.001)

    def test_chain_eas_input_consistency(self):
        """Feeding the EAS leg output back reproduces the same TAS and CAS."""
        ref = airspeed_chain(ALT_30KFT, cas_kt=250.0)
        r = airspeed_chain(ALT_30KFT, eas_kt=ref["eas_kt"])
        self.assertAlmostEqual(r["tas_ms"], ref["tas_ms"], places=9)
        self.assertAlmostEqual(r["cas_kt"], ref["cas_kt"], places=9)
        self.assertAlmostEqual(r["qc_Pa"], ref["qc_Pa"], places=6)

    def test_chain_exactly_one_input_rule(self):
        """Zero or multiple speed inputs reject."""
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT)
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, cas_kt=250.0, tas_ms=200.0)
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, cas_kt=250.0, mach=0.5, eas_kt=100.0)

    def test_chain_negative_and_supersonic_inputs_raise(self):
        """Negative inputs and supersonic Mach reject through the chain."""
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, cas_kt=-250.0)
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, tas_ms=-1.0)
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, eas_kt=-10.0)
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, mach=-0.1)
        with self.assertRaises(ValueError):
            airspeed_chain(ALT_30KFT, mach=1.0)
        with self.assertRaises(ValueError):
            airspeed_chain(-1.0, mach=0.5)


if __name__ == "__main__":
    unittest.main()
