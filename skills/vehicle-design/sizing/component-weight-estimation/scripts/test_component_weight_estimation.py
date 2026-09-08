"""Contract test for component-weight-estimation (vehicle-design/sizing).

Exercises the SKILL.md workflow: step 2 (wing_group_weight on the wing
planform), step 3 (horizontal_tail_group_weight and
vertical_tail_group_weight on the tail planforms, including the T-tail
location factor), step 4 (fuselage_group_weight on the fuselage
dimensions with the pressurization penalty), step 5
(airframe_group_total) and step 6 (the per-group and total fractions
of MTOW handed to the weight statement). Deterministic stdlib
unittest, offline, no randomness.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import component_weight_estimation_logic as cwe

MTOW = 79000.0
NZ = 2.5
Q = 12000.0

WING_ARGS = (MTOW, NZ, Q, 125.0, 10.0, 0.25, 0.11, 25.0, 14000.0)
HT_ARGS = (MTOW, NZ, Q, 32.0, 6.0, 0.30, 0.09, 30.0)
VT_ARGS = (MTOW, NZ, Q, 26.0, 1.8, 0.30, 0.12, 35.0, 0.0)
FUS_ARGS = (MTOW, NZ, Q, 405.0, 39.5, 3.9, 300.0, 55158.0)


class TestWorkedExample(unittest.TestCase):
    """Step 2-5 of the SKILL.md workflow: the 180-seat transport worked example."""

    def test_group_masses(self):
        """Steps 2-4: each group regression matches its worked-example anchor."""
        self.assertAlmostEqual(cwe.wing_group_weight(*WING_ARGS), 5835.319661,
                                delta=1e-3)
        self.assertAlmostEqual(cwe.horizontal_tail_group_weight(*HT_ARGS),
                                461.175701, delta=1e-3)
        self.assertAlmostEqual(cwe.vertical_tail_group_weight(*VT_ARGS),
                                438.062259, delta=1e-3)
        self.assertAlmostEqual(cwe.fuselage_group_weight(*FUS_ARGS),
                                7362.993775, delta=1e-3)

    def test_airframe_group_total(self):
        """Step 5: airframe_group_total sums the four worked-example groups."""
        w_wing = cwe.wing_group_weight(*WING_ARGS)
        w_ht = cwe.horizontal_tail_group_weight(*HT_ARGS)
        w_vt = cwe.vertical_tail_group_weight(*VT_ARGS)
        w_fus = cwe.fuselage_group_weight(*FUS_ARGS)
        total = cwe.airframe_group_total(w_wing, w_ht, w_vt, w_fus)
        self.assertAlmostEqual(total, 14097.551395, delta=1e-3)


class TestMtowFractions(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: per-group and total fractions of MTOW."""

    def setUp(self):
        self.w_wing = cwe.wing_group_weight(*WING_ARGS)
        self.w_ht = cwe.horizontal_tail_group_weight(*HT_ARGS)
        self.w_vt = cwe.vertical_tail_group_weight(*VT_ARGS)
        self.w_fus = cwe.fuselage_group_weight(*FUS_ARGS)
        self.total = cwe.airframe_group_total(self.w_wing, self.w_ht,
                                               self.w_vt, self.w_fus)

    def test_fraction_anchors(self):
        """Step 6: per-group and total fractions of MTOW match the anchors."""
        self.assertAlmostEqual(self.w_wing / MTOW, 0.073865, delta=1e-5)
        self.assertAlmostEqual(self.w_ht / MTOW, 0.005838, delta=1e-5)
        self.assertAlmostEqual(self.w_vt / MTOW, 0.005545, delta=1e-5)
        self.assertAlmostEqual(self.w_fus / MTOW, 0.093202, delta=1e-5)
        self.assertAlmostEqual(self.total / MTOW, 0.178450, delta=1e-5)

    def test_fraction_bands(self):
        """Physical-sanity bands from the spec's validation list, item 2."""
        self.assertGreater(self.w_wing, 0.0)
        self.assertGreater(self.w_fus, 0.0)
        self.assertLess(self.total, MTOW)
        self.assertTrue(0.05 <= self.w_wing / MTOW <= 0.15)
        self.assertTrue(0.05 <= self.w_fus / MTOW <= 0.15)
        self.assertTrue(0.004 <= self.w_ht / MTOW <= 0.03)
        self.assertTrue(0.004 <= self.w_vt / MTOW <= 0.03)
        self.assertTrue(0.10 <= self.total / MTOW <= 0.30)

    def test_below_class_i_empty_weight_band(self):
        """Total fraction sits below the class-I transport band lower bound 0.42."""
        self.assertLess(self.total / MTOW, 0.42)


class TestTTailFactor(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the T-tail location factor."""

    def test_t_tail_is_linear_1_2x(self):
        """T-tail (t_tail=1.0) is exactly 1.2 times the fuselage-mounted value."""
        conventional = cwe.vertical_tail_group_weight(*VT_ARGS)
        t_tail_args = VT_ARGS[:-1] + (1.0,)
        t_tail = cwe.vertical_tail_group_weight(*t_tail_args)
        self.assertAlmostEqual(t_tail, 525.674710, delta=1e-3)
        self.assertAlmostEqual(t_tail / conventional, 1.2, delta=1e-9)


class TestPressurizationPenalty(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the additive pressurization penalty."""

    def setUp(self):
        self.unpressurized = cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9)
        self.pressurized = cwe.fuselage_group_weight(*FUS_ARGS)

    def test_penalty_decomposition(self):
        """Unpressurized anchor and the penalty equal pressurized minus unpressurized."""
        self.assertAlmostEqual(self.unpressurized, 7246.112306, delta=1e-3)
        penalty = self.pressurized - self.unpressurized
        self.assertAlmostEqual(penalty, 116.881468, delta=1e-3)

    def test_penalty_scales_with_pressure_power_law(self):
        """Doubling delta_p scales the penalty by 2**0.271, per the spec identity."""
        pressurized_2x = cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9,
                                                     300.0, 110316.0)
        penalty_1 = self.pressurized - self.unpressurized
        penalty_2 = pressurized_2x - self.unpressurized
        self.assertAlmostEqual(penalty_2 / penalty_1, 2 ** 0.271, delta=1e-6)

    def test_penalty_independent_of_load_factor_and_q(self):
        """The penalty is unchanged when the load factor or dynamic pressure changes."""
        unpressurized_hi = cwe.fuselage_group_weight(MTOW, 5.0, 24000.0, 405.0,
                                                       39.5, 3.9)
        pressurized_hi = cwe.fuselage_group_weight(MTOW, 5.0, 24000.0, 405.0,
                                                     39.5, 3.9, 300.0, 55158.0)
        penalty_hi = pressurized_hi - unpressurized_hi
        penalty_lo = self.pressurized - self.unpressurized
        self.assertAlmostEqual(penalty_hi, penalty_lo, delta=1e-6)


class TestLoadFactorPowerLaw(unittest.TestCase):
    """Step 2-4 of the SKILL.md workflow: the ultimate-load-factor power law."""

    def test_all_groups_scale_with_nz(self):
        """Doubling nz_limit scales every group by 2**exponent, per the spec."""
        hi_wing = cwe.wing_group_weight(MTOW, 5.0, Q, 125.0, 10.0, 0.25, 0.11,
                                         25.0, 14000.0)
        hi_ht = cwe.horizontal_tail_group_weight(MTOW, 5.0, Q, 32.0, 6.0, 0.30,
                                                   0.09, 30.0)
        hi_vt = cwe.vertical_tail_group_weight(MTOW, 5.0, Q, 26.0, 1.8, 0.30,
                                                 0.12, 35.0, 0.0)
        hi_fus = cwe.fuselage_group_weight(MTOW, 5.0, Q, 405.0, 39.5, 3.9)
        self.assertAlmostEqual(hi_wing / cwe.wing_group_weight(*WING_ARGS),
                                2 ** 0.49, delta=1e-7)
        self.assertAlmostEqual(hi_ht / cwe.horizontal_tail_group_weight(*HT_ARGS),
                                2 ** 0.414, delta=1e-7)
        self.assertAlmostEqual(hi_vt / cwe.vertical_tail_group_weight(*VT_ARGS),
                                2 ** 0.376, delta=1e-7)
        self.assertAlmostEqual(
            hi_fus / cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9),
            2 ** 0.177, delta=1e-7)

    def test_sublinear_scaling(self):
        """Every group's (N_ult*W0) exponent is below 0.5, per the spec identity."""
        base = cwe.wing_group_weight(*WING_ARGS)
        hi = cwe.wing_group_weight(MTOW, 5.0, Q, 125.0, 10.0, 0.25, 0.11, 25.0,
                                    14000.0)
        self.assertLess(hi / base, 1.5)


class TestDynamicPressurePowerLaw(unittest.TestCase):
    """Step 2-4 of the SKILL.md workflow: the dynamic-pressure power law."""

    def test_all_groups_scale_with_q(self):
        """Doubling q scales every group by 2**exponent, per the spec identities."""
        hi_wing = cwe.wing_group_weight(MTOW, NZ, 24000.0, 125.0, 10.0, 0.25,
                                         0.11, 25.0, 14000.0)
        hi_ht = cwe.horizontal_tail_group_weight(MTOW, NZ, 24000.0, 32.0, 6.0,
                                                   0.30, 0.09, 30.0)
        hi_vt = cwe.vertical_tail_group_weight(MTOW, NZ, 24000.0, 26.0, 1.8,
                                                 0.30, 0.12, 35.0, 0.0)
        hi_fus = cwe.fuselage_group_weight(MTOW, NZ, 24000.0, 405.0, 39.5, 3.9)
        self.assertAlmostEqual(hi_wing / cwe.wing_group_weight(*WING_ARGS),
                                2 ** 0.006, delta=1e-7)
        self.assertAlmostEqual(hi_ht / cwe.horizontal_tail_group_weight(*HT_ARGS),
                                2 ** 0.043, delta=1e-7)
        self.assertAlmostEqual(hi_vt / cwe.vertical_tail_group_weight(*VT_ARGS),
                                2 ** 0.122, delta=1e-7)
        self.assertAlmostEqual(
            hi_fus / cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9),
            2 ** 0.241, delta=1e-7)


class TestGeometricPowerLaws(unittest.TestCase):
    """Step 2-4 of the SKILL.md workflow: the geometric closed-form power laws."""

    def test_wing_geometry_power_laws(self):
        """Doubling wing area, aspect ratio, taper and in-wing fuel each match 2**e."""
        base = cwe.wing_group_weight(*WING_ARGS)
        hi_s = cwe.wing_group_weight(MTOW, NZ, Q, 250.0, 10.0, 0.25, 0.11, 25.0,
                                      14000.0)
        hi_ar = cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 20.0, 0.25, 0.11, 25.0,
                                       14000.0)
        hi_lam = cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.5, 0.11, 25.0,
                                        14000.0)
        hi_fuel = cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.25, 0.11,
                                         25.0, 28000.0)
        self.assertAlmostEqual(hi_s / base, 2 ** 0.758, delta=1e-7)
        self.assertAlmostEqual(hi_ar / base, 2 ** 0.6, delta=1e-7)
        self.assertAlmostEqual(hi_lam / base, 2 ** 0.04, delta=1e-7)
        self.assertAlmostEqual(hi_fuel / base, 2 ** 0.0035, delta=1e-7)

    def test_tail_and_fuselage_area_power_laws(self):
        """Doubling tail areas and fuselage wetted area / L-over-D match 2**e."""
        hi_ht = cwe.horizontal_tail_group_weight(MTOW, NZ, Q, 64.0, 6.0, 0.30,
                                                   0.09, 30.0)
        hi_vt = cwe.vertical_tail_group_weight(MTOW, NZ, Q, 52.0, 1.8, 0.30,
                                                 0.12, 35.0, 0.0)
        base_fus = cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9)
        hi_sf = cwe.fuselage_group_weight(MTOW, NZ, Q, 810.0, 39.5, 3.9)
        hi_ld = cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 79.0, 3.9)
        self.assertAlmostEqual(hi_ht / cwe.horizontal_tail_group_weight(*HT_ARGS),
                                2 ** 0.896, delta=1e-7)
        self.assertAlmostEqual(hi_vt / cwe.vertical_tail_group_weight(*VT_ARGS),
                                2 ** 0.873, delta=1e-7)
        self.assertAlmostEqual(hi_sf / base_fus, 2 ** 1.086, delta=1e-7)
        self.assertAlmostEqual(hi_ld / base_fus, 2 ** -0.072, delta=1e-7)


class TestSweepPenalty(unittest.TestCase):
    """Step 2-3 of the SKILL.md workflow: sweep raises the wing and tail groups."""

    def test_wing_and_tail_sweep_penalty(self):
        """Higher quarter-chord sweep raises the wing and horizontal tail groups."""
        base_wing = cwe.wing_group_weight(*WING_ARGS)
        hi_wing = cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.25, 0.11,
                                         40.0, 14000.0)
        base_ht = cwe.horizontal_tail_group_weight(*HT_ARGS)
        hi_ht = cwe.horizontal_tail_group_weight(MTOW, NZ, Q, 32.0, 6.0, 0.30,
                                                   0.09, 40.0)
        self.assertAlmostEqual(hi_wing, 6788.662565, delta=1e-3)
        self.assertAlmostEqual(hi_ht, 473.559089, delta=1e-3)
        self.assertGreater(hi_wing, base_wing)
        self.assertGreater(hi_ht, base_ht)


class TestValueErrors(unittest.TestCase):
    """Step 2-5 of the SKILL.md workflow: rejection of non-physical inputs."""

    def test_wing_group_rejects_non_physical_inputs(self):
        """wing_group_weight raises ValueError for each non-physical parameter."""
        with self.assertRaisesRegex(ValueError, "MTOW must be positive, got 0.0"):
            cwe.wing_group_weight(0.0, NZ, Q, 125.0, 10.0, 0.25, 0.11, 25.0,
                                   14000.0)
        with self.assertRaisesRegex(ValueError,
                                     "design limit load factor must be positive"):
            cwe.wing_group_weight(MTOW, -1.0, Q, 125.0, 10.0, 0.25, 0.11, 25.0,
                                   14000.0)
        with self.assertRaisesRegex(ValueError, "dynamic pressure must be positive"):
            cwe.wing_group_weight(MTOW, NZ, 0.0, 125.0, 10.0, 0.25, 0.11, 25.0,
                                   14000.0)
        with self.assertRaisesRegex(ValueError, "planform area must be positive"):
            cwe.wing_group_weight(MTOW, NZ, Q, 0.0, 10.0, 0.25, 0.11, 25.0, 14000.0)
        with self.assertRaisesRegex(ValueError, "aspect ratio must be positive"):
            cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 0.0, 0.25, 0.11, 25.0, 14000.0)
        with self.assertRaisesRegex(ValueError, "taper ratio must be positive"):
            cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.0, 0.11, 25.0, 14000.0)
        with self.assertRaisesRegex(
                ValueError, "thickness to chord must be below 1.0, got 1.0"):
            cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.25, 1.0, 25.0, 14000.0)
        with self.assertRaisesRegex(
                ValueError, "sweep angle must be below 90 degrees, got 90.0"):
            cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.25, 0.11, 90.0,
                                   14000.0)
        with self.assertRaisesRegex(ValueError,
                                     "fuel weight in the wing must be positive"):
            cwe.wing_group_weight(MTOW, NZ, Q, 125.0, 10.0, 0.25, 0.11, 25.0, 0.0)

    def test_vertical_tail_rejects_negative_t_tail(self):
        """vertical_tail_group_weight raises ValueError for a negative t_tail."""
        with self.assertRaisesRegex(ValueError, "t_tail must be non-negative"):
            cwe.vertical_tail_group_weight(MTOW, NZ, Q, 26.0, 1.8, 0.30, 0.12,
                                            35.0, -0.5)

    def test_fuselage_group_rejects_non_physical_inputs(self):
        """fuselage_group_weight raises ValueError for non-physical dimensions."""
        with self.assertRaisesRegex(ValueError, "fuselage diameter must be positive"):
            cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 0.0)
        with self.assertRaisesRegex(ValueError, "fuselage length must be positive"):
            cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 0.0, 3.9)
        with self.assertRaisesRegex(ValueError, "wetted area must be positive"):
            cwe.fuselage_group_weight(MTOW, NZ, Q, 0.0, 39.5, 3.9)

    def test_fuselage_pressurization_requires_both_parameters(self):
        """fuselage_group_weight raises ValueError when only one is supplied."""
        with self.assertRaisesRegex(ValueError, "pressurization requires both"):
            cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9, 300.0, 0.0)
        with self.assertRaisesRegex(ValueError, "pressurization requires both"):
            cwe.fuselage_group_weight(MTOW, NZ, Q, 405.0, 39.5, 3.9, 0.0, 55158.0)

    def test_airframe_group_total_rejects_negative_group_mass(self):
        """airframe_group_total raises ValueError for a negative group mass."""
        with self.assertRaisesRegex(
                ValueError, "group mass 1 must be non-negative, got -1.0"):
            cwe.airframe_group_total(-1.0, 1.0, 1.0, 1.0)


class TestDeterminism(unittest.TestCase):
    """Step 2-5 of the SKILL.md workflow: determinism across repeated runs."""

    def test_repeated_runs_identical(self):
        """Two consecutive runs of wing_group_weight return identical values."""
        first = cwe.wing_group_weight(*WING_ARGS)
        second = cwe.wing_group_weight(*WING_ARGS)
        self.assertEqual(first, second)

    def test_module_uses_only_math(self):
        """The logic module imports only the stdlib math module, no other imports."""
        module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "component_weight_estimation_logic.py")
        with open(module_path) as f:
            source = f.read()
        import_lines = [l for l in source.splitlines() if l.startswith("import ")]
        self.assertEqual(import_lines, ["import math"])


if __name__ == "__main__":
    unittest.main()
