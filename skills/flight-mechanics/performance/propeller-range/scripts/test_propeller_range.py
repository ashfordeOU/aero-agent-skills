"""Contract test for the propeller-range leaf (wave-39).

Exercises the SKILL.md workflow end to end. Step 1 of the workflow
fixes the operating inputs: propeller efficiency, power specific fuel
consumption (PSFC), lift to drag ratio, initial mass and final mass,
with the pounds per horsepower hour unit conversion when the PSFC
arrives in imperial units. Step 2 is the fuel fraction derivation
phase, where final_mass_from_fuel_fraction turns a burned fuel
fraction into the final cruise mass. Step 3 runs the propeller Breguet
range evaluation from the mass ratio and the propeller efficiency.
Step 4 is the physical sanity gate that rejects a propeller efficiency
outside (0, 1], a zero PSFC, a zero lift to drag ratio, and a final
mass at or above the initial mass. Step 5 packages the range report
with the range_m and range_km keys. Step 6 closes with these
deterministic offline checks. The fact anchors (worked example at
eta_p 0.80, c_p 0.55 lb/hp/h converted to 9.293e-8 kg/(W s), L/D 12,
m0 11,500 kg, m1 10,000 kg) are the real module outputs, bounded by
the spec anchors within 1e3 m (1 km). Deterministic, offline, stdlib
unittest.
"""

import unittest

from propeller_range_logic import (
    G0,
    LB_PER_HP_H_TO_KG_PER_W_S,
    final_mass_from_fuel_fraction,
    propeller_range,
    propeller_range_km,
    psfc_lb_per_hp_h_to_kg_per_w_s,
    range_report,
)

M0 = 11500.0      # worked example initial mass, kg
M1 = 10000.0      # worked example final mass, kg
LD = 12.0         # worked example lift to drag ratio
ETA = 0.80        # worked example propeller efficiency


class TestPsfcConversion(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the PSFC unit conversion."""

    def test_conversion_worked_example_anchor(self):
        # 0.55 lb/hp/h must convert to 9.293e-8 kg/(W s) within 1e-10.
        converted = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        self.assertAlmostEqual(converted, 9.293e-8, delta=1e-10)

    def test_conversion_matches_module_constant(self):
        # One lb/hp/h converts to exactly the module constant.
        self.assertEqual(psfc_lb_per_hp_h_to_kg_per_w_s(1.0),
                         LB_PER_HP_H_TO_KG_PER_W_S)

    def test_conversion_scales_linearly(self):
        # Doubling the imperial PSFC doubles the SI value.
        base = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        doubled = psfc_lb_per_hp_h_to_kg_per_w_s(1.1)
        self.assertAlmostEqual(doubled, 2.0 * base, delta=1e-12)

    def test_conversion_rejects_negative(self):
        with self.assertRaises(ValueError):
            psfc_lb_per_hp_h_to_kg_per_w_s(-0.1)


class TestFinalMassFromFuelFraction(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the fuel fraction derivation."""

    def test_worked_example_fuel_fraction(self):
        # A 1500 kg fuel burn on 11,500 kg is fraction 1500/11500 and
        # must give a 10,000 kg final mass.
        m1 = final_mass_from_fuel_fraction(M0, 1500.0 / M0)
        self.assertAlmostEqual(m1, 10000.0, delta=1e-6)

    def test_zero_fuel_fraction_keeps_initial_mass(self):
        self.assertEqual(final_mass_from_fuel_fraction(M0, 0.0), M0)

    def test_round_trip_recovers_the_fraction(self):
        fraction = 0.1304
        m1 = final_mass_from_fuel_fraction(M0, fraction)
        recovered = (M0 - m1) / M0
        self.assertAlmostEqual(recovered, fraction, delta=1e-9)

    def test_fuel_fraction_one_rejected(self):
        with self.assertRaises(ValueError):
            final_mass_from_fuel_fraction(M0, 1.0)

    def test_fuel_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            final_mass_from_fuel_fraction(M0, 1.5)

    def test_negative_fuel_fraction_rejected(self):
        with self.assertRaises(ValueError):
            final_mass_from_fuel_fraction(M0, -0.2)

    def test_non_positive_initial_mass_rejected(self):
        with self.assertRaises(ValueError):
            final_mass_from_fuel_fraction(0.0, 0.1)
        with self.assertRaises(ValueError):
            final_mass_from_fuel_fraction(-500.0, 0.1)


class TestPropellerRange(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the propeller Breguet range."""

    def test_worked_example_range_meters(self):
        # Real module output 1.4722367e6 m, spec anchor 1.4722e6 m
        # within 1e3.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        r = propeller_range(ETA, psfc, LD, M0, M1)
        self.assertAlmostEqual(r, 1472236.704, delta=1.0)
        self.assertAlmostEqual(r, 1.4722e6, delta=1e3)

    def test_worked_example_range_kilometers(self):
        # Real module output 1472.24 km, spec anchor 1472.2 km within
        # 1 km.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        r_km = propeller_range_km(ETA, psfc, LD, M0, M1)
        self.assertAlmostEqual(r_km, 1472.236704, delta=0.01)
        self.assertAlmostEqual(r_km, 1472.2, delta=1.0)

    def test_range_scales_linearly_with_propeller_efficiency(self):
        # Workflow step 4 sanity: eta_p 0.9 must give 1656.27 km,
        # within the spec anchor 1656 km plus 2 km.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        r_km = propeller_range_km(0.90, psfc, LD, M0, M1)
        self.assertAlmostEqual(r_km, 1656.266292, delta=0.01)
        self.assertAlmostEqual(r_km, 1656.0, delta=2.0)

    def test_doubling_efficiency_doubles_range(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        half = propeller_range(0.40, psfc, LD, M0, M1)
        full = propeller_range(0.80, psfc, LD, M0, M1)
        self.assertAlmostEqual(full / half, 2.0, delta=1e-9)

    def test_doubling_psfc_halves_range(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        base = propeller_range(ETA, psfc, LD, M0, M1)
        double_psfc = propeller_range(ETA, 2.0 * psfc, LD, M0, M1)
        self.assertAlmostEqual(double_psfc / base, 0.5, delta=1e-9)

    def test_unit_efficiency_identity(self):
        # eta_p 1.0 equals the eta_p 0.5 result doubled.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        self.assertAlmostEqual(
            propeller_range(1.0, psfc, LD, M0, M1),
            2.0 * propeller_range(0.5, psfc, LD, M0, M1),
            delta=1e-6)

    def test_range_vanishes_as_final_mass_approaches_initial_mass(self):
        # The mass ratio ln(m0/m1) drives the range to zero when the
        # fuel burn goes to zero.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        tiny_burn = propeller_range(ETA, psfc, LD, M0,
                                    M0 * (1.0 - 1e-9))
        self.assertGreater(tiny_burn, 0.0)
        self.assertLess(tiny_burn, 0.02)

    def test_fuel_fraction_profile_matches_direct_form(self):
        # Step 2 plus step 3: the range built from a fuel fraction
        # profile equals the direct m0/m1 form.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        m1 = final_mass_from_fuel_fraction(M0, 1500.0 / M0)
        self.assertEqual(
            propeller_range(ETA, psfc, LD, M0, m1),
            propeller_range(ETA, psfc, LD, M0, M0 * (1.0 - 1500.0 / M0)))

    def test_repeated_calls_are_deterministic(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        first = propeller_range(ETA, psfc, LD, M0, M1)
        second = propeller_range(ETA, psfc, LD, M0, M1)
        self.assertEqual(first, second)

    def test_mass_ratio_ordering(self):
        # Workflow step 4 keeps ln(m0/m1) positive by requiring
        # m1 < m0, so the range of a burn profile is below the range
        # of a lighter burn at the same inputs.
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        heavy = propeller_range(ETA, psfc, LD, M0, 10500.0)
        light = propeller_range(ETA, psfc, LD, M0, 9500.0)
        self.assertGreater(light, heavy)


class TestValueErrorGuards(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the physical sanity gate."""

    def test_zero_efficiency_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(0.0, psfc, LD, M0, M1)

    def test_efficiency_above_one_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(1.05, psfc, LD, M0, M1)

    def test_negative_efficiency_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(-0.5, psfc, LD, M0, M1)

    def test_zero_psfc_rejected(self):
        with self.assertRaises(ValueError):
            propeller_range(ETA, 0.0, LD, M0, M1)

    def test_negative_psfc_rejected(self):
        with self.assertRaises(ValueError):
            propeller_range(ETA, -1e-8, LD, M0, M1)

    def test_zero_lift_to_drag_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(ETA, psfc, 0.0, M0, M1)

    def test_final_mass_equal_to_initial_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(ETA, psfc, LD, M0, M0)

    def test_final_mass_above_initial_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(ETA, psfc, LD, M0, 12500.0)

    def test_non_positive_masses_rejected(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        with self.assertRaises(ValueError):
            propeller_range(ETA, psfc, LD, 0.0, M1)
        with self.assertRaises(ValueError):
            propeller_range(ETA, psfc, LD, M0, 0.0)
        with self.assertRaises(ValueError):
            propeller_range(ETA, psfc, LD, -100.0, M1)

    def test_boundary_efficiency_of_one_accepted(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        self.assertGreater(propeller_range(1.0, psfc, LD, M0, M1), 0.0)


class TestRangeReport(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the range report phase."""

    def test_report_dict_keys_exactly_as_documented(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        rep = range_report(ETA, psfc, LD, M0, M1)
        self.assertEqual(sorted(rep.keys()), ["range_km", "range_m"])

    def test_report_matches_direct_call(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        rep = range_report(ETA, psfc, LD, M0, M1)
        self.assertEqual(rep["range_m"],
                         propeller_range(ETA, psfc, LD, M0, M1))
        self.assertEqual(rep["range_km"],
                         propeller_range_km(ETA, psfc, LD, M0, M1))

    def test_report_km_and_meters_consistent(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        rep = range_report(ETA, psfc, LD, M0, M1)
        self.assertAlmostEqual(rep["range_km"],
                               rep["range_m"] / 1000.0, delta=1e-9)

    def test_worked_example_report_values(self):
        psfc = psfc_lb_per_hp_h_to_kg_per_w_s(0.55)
        rep = range_report(ETA, psfc, LD, M0, M1)
        self.assertAlmostEqual(rep["range_m"], 1.4722e6, delta=1e3)
        self.assertAlmostEqual(rep["range_km"], 1472.2, delta=1.0)


if __name__ == "__main__":
    unittest.main()
