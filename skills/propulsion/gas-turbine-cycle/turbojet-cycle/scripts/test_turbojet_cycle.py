"""Contract test for the turbojet-cycle leaf (propulsion/gas-turbine-cycle).

Exercises SKILL.md workflow steps 2 through 8 of the turbojet-cycle leaf:
step 2 freestream stagnation temperature, step 3 compressor exit
temperature, step 4 fuel-to-air ratio from the combustor energy balance,
step 5 turbine exit temperature from the compressor-turbine work balance,
step 6 nozzle exit temperature and exit velocity from the nozzle total
pressure ratio chain, step 7 net specific thrust, turbojet TSFC and
propulsive efficiency, and step 8 the cycle report dict.  Asserts the
spec worked-example anchors (Tt0 334.8 K, T03 764.7 K, f 0.0197, Tt5
1224.4 K, v9 1195.5 m/s, F/mdot 889.3 N/(kg/s), TSFC 2.22e-5 kg/(N s),
propulsive efficiency 0.408), the round-trip identity TSFC times specific
thrust equals the fuel-to-air ratio, the ram-drag trend, the zero-Mach
degenerate thermal-expansion identity, and every ValueError guard from
the validation list.  Offline deterministic stdlib unittest.
"""

import math
import unittest

import turbojet_cycle_logic as tjc

T0 = 288.15
MACH = 0.9
PR = 18.0
T04 = 1600.0


class TurbojetCycleContract(unittest.TestCase):
    """Worked-example anchors, identities, trends and ValueError guards."""

    # ---- workflow step 2: freestream stagnation temperature ----

    def test_step2_freestream_stagnation_temperature_anchor(self):
        """Workflow step 2, the freestream stagnation temperature traverse:
        Tt0 must read 334.8 K within 0.2 K at mach 0.9."""
        tt0 = tjc.freestream_stagnation_temperature(T0, MACH)
        self.assertAlmostEqual(tt0, 334.8303, places=3)
        self.assertTrue(abs(tt0 - 334.8) <= 0.2)

    def test_step2_freestream_stagnation_hand_formula(self):
        """Workflow step 2 closed form: Tt0 equals t0 times (1 + 0.5 *
        (gamma - 1) * mach^2) computed inline."""
        tt0 = tjc.freestream_stagnation_temperature(T0, MACH)
        expect = T0 * (1.0 + 0.5 * (tjc.GAMMA - 1.0) * MACH * MACH)
        self.assertAlmostEqual(tt0, expect, places=9)

    def test_step2_zero_mach_recovers_static_temperature(self):
        """Workflow step 2 boundary: at zero Mach the stagnation
        temperature equals the static temperature and mach 0 is accepted."""
        self.assertAlmostEqual(
            tjc.freestream_stagnation_temperature(T0, 0.0), T0, places=9)
        self.assertEqual(tjc.propulsive_efficiency(0.0, 500.0), 0.0)

    # ---- workflow step 3: compressor exit temperature ----

    def test_step3_compressor_exit_temperature_anchor(self):
        """Workflow step 3, the compression traverse: T03 must read 764.7 K
        within 0.5 K at pressure ratio 18."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        self.assertAlmostEqual(t03, 764.6700, places=2)
        self.assertTrue(abs(t03 - 764.7) <= 0.5)

    def test_step3_compressor_exit_hand_formula(self):
        """Workflow step 3 closed form: T03 equals Tt0 times
        pr^((gamma-1)/gamma) with Tt0 from workflow step 2."""
        tt0 = tjc.freestream_stagnation_temperature(T0, MACH)
        expect = tt0 * PR ** ((tjc.GAMMA - 1.0) / tjc.GAMMA)
        self.assertAlmostEqual(
            tjc.compressor_exit_temperature(T0, MACH, PR), expect, places=9)

    # ---- workflow step 4: fuel-to-air ratio ----

    def test_step4_fuel_air_ratio_anchor(self):
        """Workflow step 4, the combustor energy balance: the fuel-to-air
        ratio must read 0.0197 within 1e-4 at a 1600 kelvin turbine inlet
        temperature."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        f = tjc.fuel_air_ratio(t03, T04)
        self.assertAlmostEqual(f, 0.0197206, places=6)
        self.assertTrue(abs(f - 0.0197) <= 1e-4)

    def test_step4_fuel_air_hand_formula(self):
        """Workflow step 4 closed form: f equals cp_c times (t04 - t03)
        over the product of combustor efficiency and lower heating value."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        expect = tjc.CP_C * (T04 - t03) / (tjc.ETA_B * tjc.LHV)
        self.assertAlmostEqual(
            tjc.fuel_air_ratio(t03, T04), expect, places=12)

    # ---- workflow step 5: turbine exit temperature (work balance) ----

    def test_step5_turbine_exit_temperature_work_balance_anchor(self):
        """Workflow step 5, the compressor-turbine matching step: the
        turbine exit temperature from the work balance must read 1224.4 K
        within 0.5 K."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        t05 = tjc.turbine_exit_temperature(t03, T04, T0, MACH)
        self.assertAlmostEqual(t05, 1224.3575, places=2)
        self.assertTrue(abs(t05 - 1224.4) <= 0.5)

    def test_step5_work_balance_t05_falls_when_t03_rises(self):
        """Workflow step 5 trend: the turbine exit temperature falls when
        the compressor exit temperature rises at fixed turbine inlet
        temperature, the signature of the work balance."""
        low = tjc.compressor_exit_temperature(T0, MACH, PR)
        high = tjc.compressor_exit_temperature(T0, MACH, 30.0)
        self.assertTrue(
            tjc.turbine_exit_temperature(low, T04, T0, MACH) >
            tjc.turbine_exit_temperature(high, T04, T0, MACH))
        self.assertTrue(
            tjc.cycle_report(T0, MACH, 30.0, T04)["t05"] <
            tjc.cycle_report(T0, MACH, PR, T04)["t05"])

    # ---- workflow step 6: nozzle expansion ----

    def test_step6_nozzle_exit_temperature_anchor(self):
        """Workflow step 6, the nozzle expansion: the nozzle exit
        temperature sits near 603 K for the worked example state."""
        t9 = tjc.nozzle_exit_temperature(T0, MACH, PR, T04)
        self.assertAlmostEqual(t9, 602.9268, places=3)
        self.assertTrue(550.0 < t9 < 700.0)

    def test_step6_nozzle_total_pressure_ratio_chain(self):
        """Workflow step 6 closed form: T9 equals Tt5 times (p0/pt5)
        raised to (gamma-1)/gamma, with pt5/p0 rebuilt from the ram
        factor, the pressure ratio and the Tt5/Tt4 turbine factor."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        t05 = tjc.turbine_exit_temperature(t03, T04, T0, MACH)
        g = tjc.GAMMA
        ram = (1.0 + 0.5 * (g - 1.0) * MACH * MACH) ** (g / (g - 1.0))
        pt5_over_p0 = ram * PR * (t05 / T04) ** (g / (g - 1.0))
        expect = t05 * (1.0 / pt5_over_p0) ** ((g - 1.0) / g)
        t9 = tjc.nozzle_exit_temperature(T0, MACH, PR, T04)
        self.assertAlmostEqual(t9, expect, places=9)

    def test_step6_nozzle_defaults_to_work_balance_state(self):
        """Workflow step 6 consistency: the nozzle exit temperature with
        the default turbine exit state equals the explicit t05 call."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        t05 = tjc.turbine_exit_temperature(t03, T04, T0, MACH)
        self.assertAlmostEqual(
            tjc.nozzle_exit_temperature(T0, MACH, PR, T04),
            tjc.nozzle_exit_temperature(T0, MACH, PR, T04, t05), places=9)

    def test_step6_zero_mach_degenerate_thermal_expansion_identity(self):
        """Workflow step 6 degenerate identity: at zero Mach the flight
        velocity vanishes, so the net specific thrust equals the nozzle
        exit velocity, the thermal expansion of the added heat; the
        near-unity pressure ratio limit stays defined and consistent."""
        rz = tjc.cycle_report(T0, 0.0, PR, T04)
        self.assertAlmostEqual(rz["specific_thrust"], rz["v9"], places=9)
        self.assertAlmostEqual(
            rz["v9"], math.sqrt(2.0 * tjc.CP_G * (rz["t05"] - rz["t9"])),
            places=9)
        rp = tjc.cycle_report(T0, 0.0, 1.001, T04)
        self.assertAlmostEqual(rp["tsfc"] * rp["specific_thrust"],
                               rp["fuel_air"], places=12)

    # ---- workflow step 7: velocities, thrust, TSFC, efficiency ----

    def test_step7_exit_velocity_anchor(self):
        """Workflow step 7, the exit velocity from the nozzle thermal
        drop: v9 must read 1195.5 m/s within 1 m/s."""
        t05 = tjc.cycle_report(T0, MACH, PR, T04)["t05"]
        t9 = tjc.cycle_report(T0, MACH, PR, T04)["t9"]
        v9 = tjc.exit_velocity(t05, t9)
        self.assertAlmostEqual(v9, 1195.5295, places=2)
        self.assertTrue(abs(v9 - 1195.5) <= 1.0)

    def test_step7_exit_velocity_closed_form_identity(self):
        """Workflow step 7 closed form: v9 equals sqrt(2 * cp_g * (Tt5 -
        T9)), the thermal expansion velocity across the nozzle."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        expect = math.sqrt(2.0 * tjc.CP_G * (rep["t05"] - rep["t9"]))
        self.assertAlmostEqual(rep["v9"], expect, places=9)

    def test_step7_flight_velocity_value(self):
        """Workflow step 7 ram term: v0 equals mach times sqrt(gamma * R *
        t0), 306.2 m/s within 0.5 m/s at mach 0.9."""
        v0 = MACH * math.sqrt(tjc.GAMMA * tjc.R * T0)
        self.assertAlmostEqual(v0, 306.2364, places=2)
        self.assertTrue(abs(v0 - 306.2) <= 0.5)

    def test_step7_net_specific_thrust_anchor(self):
        """Workflow step 7, the net specific thrust: F/mdot must read
        889.3 N/(kg/s) within 1, the exit velocity minus the flight
        velocity."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        f_m = tjc.net_specific_thrust(T0, MACH, rep["t05"], rep["t9"])
        self.assertAlmostEqual(f_m, 889.2931, places=2)
        self.assertTrue(abs(f_m - 889.3) <= 1.0)

    def test_step7_turbojet_tsfc_anchor(self):
        """Workflow step 7, the turbojet TSFC: 2.22e-5 kg/(N s) within
        1e-7, about 22.2 mg/(N s) at the worked example."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        tsfc = tjc.turbojet_tsfc(rep["fuel_air"], rep["specific_thrust"])
        self.assertAlmostEqual(tsfc, 2.21756e-5, places=10)
        self.assertTrue(abs(tsfc - 2.22e-5) <= 1e-7)
        self.assertTrue(15.0 < tsfc * 1e6 < 30.0)

    def test_step7_tsfc_times_specific_thrust_round_trip(self):
        """Workflow step 7 round-trip identity: TSFC times the net
        specific thrust equals the fuel-to-air ratio within float
        tolerance."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        self.assertAlmostEqual(rep["tsfc"] * rep["specific_thrust"],
                               rep["fuel_air"], places=12)

    def test_step7_propulsive_efficiency_anchor(self):
        """Workflow step 7, the propulsive efficiency: 0.408 within 0.002
        at the worked example."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        v0 = MACH * math.sqrt(tjc.GAMMA * tjc.R * T0)
        eta = tjc.propulsive_efficiency(v0, rep["v9"])
        self.assertAlmostEqual(eta, 0.40784, places=4)
        self.assertTrue(abs(eta - 0.408) <= 0.002)

    def test_step7_specific_thrust_decreases_with_mach_ram_drag(self):
        """Workflow step 7 ram-drag trend: the net specific thrust
        decreases as the Mach number rises at fixed turbine inlet
        temperature."""
        f03 = tjc.cycle_report(T0, 0.3, PR, T04)["specific_thrust"]
        f06 = tjc.cycle_report(T0, 0.6, PR, T04)["specific_thrust"]
        f09 = tjc.cycle_report(T0, 0.9, PR, T04)["specific_thrust"]
        f12 = tjc.cycle_report(T0, 1.2, PR, T04)["specific_thrust"]
        self.assertTrue(f03 > f06 > f09 > f12)

    def test_step7_propulsive_efficiency_below_one_rising_with_mach(self):
        """Workflow step 7 efficiency bounds: the propulsive efficiency
        stays below 1 and rises with the Mach number as the exit velocity
        approaches the flight velocity."""
        eta03 = tjc.cycle_report(T0, 0.3, PR, T04)["propulsive_efficiency"]
        eta09 = tjc.cycle_report(T0, 0.9, PR, T04)["propulsive_efficiency"]
        eta12 = tjc.cycle_report(T0, 1.2, PR, T04)["propulsive_efficiency"]
        for eta in (eta03, eta09, eta12):
            self.assertTrue(0.0 < eta < 1.0)
        self.assertTrue(eta03 < eta09 < eta12)

    # ---- workflow step 8: cycle report ----

    def test_step8_cycle_report_keys_exact(self):
        """Workflow step 8, the cycle report dict: the keys are exactly
        tt0, t03, fuel_air, t05, t9, v9, specific_thrust, tsfc and
        propulsive_efficiency."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        self.assertEqual(list(rep.keys()),
                         ["tt0", "t03", "fuel_air", "t05", "t9", "v9",
                          "specific_thrust", "tsfc",
                          "propulsive_efficiency"])

    def test_step8_cycle_report_matches_component_chain(self):
        """Workflow step 8 chain consistency: every report field equals
        the component function recomputed in workflow step order."""
        rep = tjc.cycle_report(T0, MACH, PR, T04)
        tt0 = tjc.freestream_stagnation_temperature(T0, MACH)
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        f = tjc.fuel_air_ratio(t03, T04)
        t05 = tjc.turbine_exit_temperature(t03, T04, T0, MACH)
        t9 = tjc.nozzle_exit_temperature(T0, MACH, PR, T04)
        v9 = tjc.exit_velocity(t05, t9)
        f_m = tjc.net_specific_thrust(T0, MACH, t05, t9)
        v0 = MACH * math.sqrt(tjc.GAMMA * tjc.R * T0)
        self.assertAlmostEqual(rep["tt0"], tt0, places=9)
        self.assertAlmostEqual(rep["t03"], t03, places=9)
        self.assertAlmostEqual(rep["fuel_air"], f, places=12)
        self.assertAlmostEqual(rep["t05"], t05, places=9)
        self.assertAlmostEqual(rep["t9"], t9, places=9)
        self.assertAlmostEqual(rep["v9"], v9, places=9)
        self.assertAlmostEqual(rep["specific_thrust"], f_m, places=9)
        self.assertAlmostEqual(rep["tsfc"], f / f_m, places=12)
        self.assertAlmostEqual(rep["propulsive_efficiency"],
                               2.0 * v0 / (v0 + v9), places=12)

    def test_step8_cycle_report_deterministic(self):
        """Workflow step 8 determinism: two identical report runs return
        identical station temperatures, thrust and TSFC values."""
        a = tjc.cycle_report(T0, MACH, PR, T04)
        b = tjc.cycle_report(T0, MACH, PR, T04)
        for key in a:
            self.assertEqual(a[key], b[key])

    # ---- ValueError guards (validation list) ----

    def test_valueerror_pressure_ratio_at_one(self):
        """ValueError guard: pressure ratio 1 is rejected because the
        cycle degenerates below a real compression ratio."""
        with self.assertRaises(ValueError):
            tjc.compressor_exit_temperature(T0, MACH, 1.0)
        with self.assertRaises(ValueError):
            tjc.cycle_report(T0, MACH, 1.0, T04)

    def test_valueerror_pressure_ratio_below_one(self):
        """ValueError guard: pressure ratio below 1 is non-physical for
        the compression traverse."""
        with self.assertRaises(ValueError):
            tjc.compressor_exit_temperature(T0, MACH, 0.9)
        with self.assertRaises(ValueError):
            tjc.nozzle_exit_temperature(T0, MACH, 0.9, T04)

    def test_valueerror_turbine_inlet_below_compressor_exit(self):
        """ValueError guard: a turbine inlet temperature at or below the
        compressor exit temperature is rejected by the combustor energy
        balance and the cycle report."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        with self.assertRaises(ValueError):
            tjc.fuel_air_ratio(t03, t03 - 100.0)
        with self.assertRaises(ValueError):
            tjc.cycle_report(T0, MACH, PR, 600.0)

    def test_valueerror_negative_mach(self):
        """ValueError guard: a negative Mach number is rejected by the
        stagnation traverse and the cycle report."""
        with self.assertRaises(ValueError):
            tjc.freestream_stagnation_temperature(T0, -0.1)
        with self.assertRaises(ValueError):
            tjc.cycle_report(T0, -0.5, PR, T04)

    def test_valueerror_nonpositive_static_temperature(self):
        """ValueError guard: a non-positive freestream static temperature
        is rejected."""
        with self.assertRaises(ValueError):
            tjc.freestream_stagnation_temperature(0.0, MACH)
        with self.assertRaises(ValueError):
            tjc.cycle_report(0.0, MACH, PR, T04)
        with self.assertRaises(ValueError):
            tjc.compressor_exit_temperature(-300.0, MACH, PR)

    def test_valueerror_combustor_efficiency_out_of_range(self):
        """ValueError guard: a combustor efficiency above 1 or at zero is
        rejected by the fuel-to-air ratio and the cycle report."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        with self.assertRaises(ValueError):
            tjc.fuel_air_ratio(t03, T04, eta_b=1.5)
        with self.assertRaises(ValueError):
            tjc.fuel_air_ratio(t03, T04, eta_b=0.0)
        with self.assertRaises(ValueError):
            tjc.cycle_report(T0, MACH, PR, T04, eta_b=1.5)

    def test_valueerror_nonpositive_lhv_and_temperatures(self):
        """ValueError guard: a non-positive lower heating value or turbine
        inlet temperature is rejected."""
        t03 = tjc.compressor_exit_temperature(T0, MACH, PR)
        with self.assertRaises(ValueError):
            tjc.fuel_air_ratio(t03, T04, lhv=0.0)
        with self.assertRaises(ValueError):
            tjc.fuel_air_ratio(t03, T04, lhv=-1.0)
        with self.assertRaises(ValueError):
            tjc.cycle_report(T0, MACH, PR, -1600.0)
        with self.assertRaises(ValueError):
            tjc.fuel_air_ratio(-t03, T04)

    def test_valueerror_nonfinite_inputs(self):
        """ValueError guard: NaN and infinite inputs are rejected by the
        finite-input checks in every traverse."""
        with self.assertRaises(ValueError):
            tjc.freestream_stagnation_temperature(float("nan"), MACH)
        with self.assertRaises(ValueError):
            tjc.compressor_exit_temperature(T0, float("inf"), PR)
        with self.assertRaises(ValueError):
            tjc.cycle_report(T0, MACH, float("nan"), T04)
        with self.assertRaises(ValueError):
            tjc.turbojet_tsfc(float("nan"), 889.0)

    def test_valueerror_nozzle_state_guards(self):
        """ValueError guard: the exit velocity rejects a state without a
        thermal drop and the nozzle rejects a state that does not expand
        to ambient."""
        with self.assertRaises(ValueError):
            tjc.exit_velocity(1224.0, 1400.0)
        with self.assertRaises(ValueError):
            tjc.exit_velocity(0.0, 500.0)
        with self.assertRaises(ValueError):
            tjc.turbojet_tsfc(0.02, 0.0)
        with self.assertRaises(ValueError):
            tjc.propulsive_efficiency(-5.0, 1000.0)


if __name__ == "__main__":
    unittest.main()
