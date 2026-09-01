#!/usr/bin/env python3
"""Gate 3 contract test: magnetic particle inspection.

Exercises scripts/magnetic_particle_inspection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (magnetizing current
for circular and longitudinal magnetization, effective L/D and coil
ampere-turns, field strength verdict and coverage overlap, particle
size class and sensitivity, bath concentration, indication linearity
and acceptance verdict, residual field check, defect to magnetization
direction mapping; invalid inputs raise ValueError).

Anchors (verified by running the logic module):
- head_shot_current(2.0, 800.0) = 1600.0 A and 600.0 A at 300 A/in
- central_conductor_current(1.0, 800.0) = 800.0 A
- effective_diameter_hollow(2.0, 1.0) = 1.7320508 in and
  effective_ld_ratio(8.0, 1.7320508) = 4.6188
- coil_ampere_turns_low_fill(4.0) = 11250.0 and
  coil_ampere_turns_high_fill(4.0) = 5833.33 A-turns
- coil_current_from_turns(11250.0, 250) = 45.0 A
- solenoid_field_strength(1000.0, 0.25) = 4000.0 A/m
- tangential_field_verdict(4000.0) = 'adequate', (2000.0) = 'low',
  (5000.0) = 'high', visible band (4000.0, False) = 'high'
- coverage_step(0.2, 0.15) = 0.17 m
- particle_size_class(8.0) = 'extra-fine', (45.0) = 'coarse';
  particle_sensitivity(25.0) = 'standard'
- bath_concentration_check(0.2, 'fluorescent') = 'within-range',
  (1.5, 'visible') = 'within-range'
- indication_linear_ratio(6.0, 1.5) = 4.0; indication_is_linear(4.0, 2.0) = False
- acceptance_verdict(True, 4.0, 3.0) = 'reject', (True, 2.0, 3.0) = 'accept',
  (False, 9.0, 3.0) = 'evaluate'
- residual_field_verdict(5.0) = 'demagnetize', (2.0) = 'acceptable'
- magnetization_for_defect('longitudinal') = 'circular',
  ('transverse') = 'longitudinal'
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import magnetic_particle_inspection_logic as mt  # noqa: E402


class HeadShotCurrentTest(unittest.TestCase):
    def test_anchor_two_inch_shaft_at_800(self):
        self.assertAlmostEqual(mt.head_shot_current(2.0, 800.0), 1600.0)

    def test_anchor_two_inch_shaft_at_300(self):
        self.assertAlmostEqual(mt.head_shot_current(2.0, 300.0), 600.0)

    def test_current_scales_with_diameter(self):
        small = mt.head_shot_current(1.0, 800.0)
        large = mt.head_shot_current(2.0, 800.0)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.head_shot_current(0.0, 800.0)
        with self.assertRaises(ValueError):
            mt.head_shot_current(-2.0, 800.0)
        with self.assertRaises(ValueError):
            mt.head_shot_current(2.0, 0.0)


class CentralConductorTest(unittest.TestCase):
    def test_anchor_one_inch_conductor(self):
        self.assertAlmostEqual(mt.central_conductor_current(1.0, 800.0), 800.0)

    def test_conductor_rule_uses_conductor_diameter(self):
        # Same current for the conductor regardless of part OD, because
        # the bore field is set by the conductor radius.
        thin = mt.central_conductor_current(0.5, 800.0)
        self.assertAlmostEqual(thin, 400.0)
        self.assertAlmostEqual(
            mt.central_conductor_current(1.0, 800.0), 2.0 * thin, places=9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.central_conductor_current(0.0, 800.0)
        with self.assertRaises(ValueError):
            mt.central_conductor_current(1.0, -5.0)


class EffectiveDiameterTest(unittest.TestCase):
    def test_anchor_hollow_two_over_one(self):
        self.assertAlmostEqual(
            mt.effective_diameter_hollow(2.0, 1.0), math.sqrt(3.0), places=9
        )

    def test_solid_equivalent_larger_than_hollow(self):
        hollow = mt.effective_diameter_hollow(2.0, 1.0)
        self.assertLess(hollow, 2.0)

    def test_inner_diameter_must_be_smaller(self):
        with self.assertRaises(ValueError):
            mt.effective_diameter_hollow(2.0, 2.0)
        with self.assertRaises(ValueError):
            mt.effective_diameter_hollow(2.0, 3.0)
        with self.assertRaises(ValueError):
            mt.effective_diameter_hollow(0.0, 1.0)


class LdRatioTest(unittest.TestCase):
    def test_anchor_eight_inch_hollow_part(self):
        d_eff = mt.effective_diameter_hollow(2.0, 1.0)
        self.assertAlmostEqual(mt.effective_ld_ratio(8.0, d_eff), 4.6188, places=4)

    def test_longer_part_higher_ratio(self):
        short = mt.effective_ld_ratio(4.0, 2.0)
        long_part = mt.effective_ld_ratio(8.0, 2.0)
        self.assertAlmostEqual(long_part, 2.0 * short, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.effective_ld_ratio(0.0, 2.0)
        with self.assertRaises(ValueError):
            mt.effective_ld_ratio(8.0, 0.0)


class CoilAmpereTurnsTest(unittest.TestCase):
    def test_anchor_low_fill_ld_four(self):
        self.assertAlmostEqual(mt.coil_ampere_turns_low_fill(4.0), 11250.0)

    def test_anchor_high_fill_ld_four(self):
        self.assertAlmostEqual(
            mt.coil_ampere_turns_high_fill(4.0), 5833.3333, places=4
        )

    def test_low_fill_hollow_part_example(self):
        # 8 in long hollow part, 2 in OD, 1 in ID: L/D = 4.62, so the
        # low fill coil needs about 9743 ampere-turns.
        d_eff = mt.effective_diameter_hollow(2.0, 1.0)
        ld = mt.effective_ld_ratio(8.0, d_eff)
        self.assertAlmostEqual(mt.coil_ampere_turns_low_fill(ld), 9742.8, places=1)

    def test_high_fill_needs_fewer_turns_than_low_fill(self):
        low = mt.coil_ampere_turns_low_fill(4.0)
        high = mt.coil_ampere_turns_high_fill(4.0)
        self.assertLess(high, low)

    def test_ampere_turns_fall_with_ld(self):
        short = mt.coil_ampere_turns_low_fill(3.0)
        long_part = mt.coil_ampere_turns_low_fill(6.0)
        self.assertLess(long_part, short)

    def test_ld_below_two_raises(self):
        with self.assertRaises(ValueError):
            mt.coil_ampere_turns_low_fill(1.5)
        with self.assertRaises(ValueError):
            mt.coil_ampere_turns_high_fill(1.9)

    def test_ld_at_or_above_fifteen_raises(self):
        with self.assertRaises(ValueError):
            mt.coil_ampere_turns_low_fill(15.0)
        with self.assertRaises(ValueError):
            mt.coil_ampere_turns_high_fill(20.0)


class CoilCurrentTest(unittest.TestCase):
    def test_anchor_250_turns(self):
        self.assertAlmostEqual(mt.coil_current_from_turns(11250.0, 250), 45.0)

    def test_more_turns_less_current(self):
        few = mt.coil_current_from_turns(11250.0, 100)
        many = mt.coil_current_from_turns(11250.0, 250)
        self.assertLess(many, few)
        self.assertAlmostEqual(few, 2.5 * many, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.coil_current_from_turns(0.0, 250)
        with self.assertRaises(ValueError):
            mt.coil_current_from_turns(11250.0, 0)
        with self.assertRaises(ValueError):
            mt.coil_current_from_turns(11250.0, -5)
        with self.assertRaises(ValueError):
            mt.coil_current_from_turns(11250.0, 2.5)


class FieldStrengthTest(unittest.TestCase):
    def test_anchor_adequate_fluorescent(self):
        self.assertEqual(mt.tangential_field_verdict(4000.0), "adequate")

    def test_anchor_low(self):
        self.assertEqual(mt.tangential_field_verdict(2000.0), "low")

    def test_anchor_high_fluorescent(self):
        self.assertEqual(mt.tangential_field_verdict(5000.0), "high")

    def test_visible_band_is_narrower(self):
        # 4000 A/m is adequate for fluorescent but high for visible.
        self.assertEqual(mt.tangential_field_verdict(4000.0, False), "high")
        self.assertEqual(mt.tangential_field_verdict(3000.0, False), "adequate")

    def test_solenoid_field_inside_band(self):
        # 1000 A-turns over a 0.25 m coil gives 4000 A/m, adequate for
        # the wet fluorescent method.
        h = mt.solenoid_field_strength(1000.0, 0.25)
        self.assertAlmostEqual(h, 4000.0)
        self.assertEqual(mt.tangential_field_verdict(h), "adequate")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.tangential_field_verdict(-1.0)
        with self.assertRaises(ValueError):
            mt.solenoid_field_strength(0.0, 0.25)
        with self.assertRaises(ValueError):
            mt.solenoid_field_strength(1000.0, 0.0)


class CoverageTest(unittest.TestCase):
    def test_anchor_fifteen_percent_overlap(self):
        self.assertAlmostEqual(mt.coverage_step(0.2, 0.15), 0.17)

    def test_ten_percent_overlap_example(self):
        self.assertAlmostEqual(mt.coverage_step(0.2, 0.10), 0.18)

    def test_zero_overlap_full_width_step(self):
        self.assertAlmostEqual(mt.coverage_step(0.2, 0.0), 0.2)

    def test_more_overlap_smaller_step(self):
        wide = mt.coverage_step(0.2, 0.10)
        tight = mt.coverage_step(0.2, 0.20)
        self.assertLess(tight, wide)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.coverage_step(0.0, 0.15)
        with self.assertRaises(ValueError):
            mt.coverage_step(0.2, -0.1)
        with self.assertRaises(ValueError):
            mt.coverage_step(0.2, 1.0)
        with self.assertRaises(ValueError):
            mt.coverage_step(0.2, 1.5)


class ParticleClassTest(unittest.TestCase):
    def test_anchor_extra_fine(self):
        self.assertEqual(mt.particle_size_class(8.0), "extra-fine")

    def test_anchor_fine_and_medium(self):
        self.assertEqual(mt.particle_size_class(15.0), "fine")
        self.assertEqual(mt.particle_size_class(25.0), "medium")

    def test_anchor_coarse(self):
        self.assertEqual(mt.particle_size_class(45.0), "coarse")

    def test_sensitivity_finer_is_higher(self):
        self.assertEqual(mt.particle_sensitivity(8.0), "high")
        self.assertEqual(mt.particle_sensitivity(25.0), "standard")
        self.assertEqual(mt.particle_sensitivity(45.0), "low")

    def test_high_sensitivity_particles_are_fine(self):
        # A high sensitivity particle must be extra-fine or fine.
        self.assertIn(mt.particle_size_class(8.0), ("extra-fine", "fine"))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.particle_size_class(0.0)
        with self.assertRaises(ValueError):
            mt.particle_sensitivity(-5.0)


class BathConcentrationTest(unittest.TestCase):
    def test_anchor_fluorescent_within(self):
        self.assertEqual(
            mt.bath_concentration_check(0.2, "fluorescent"), "within-range"
        )

    def test_anchor_fluorescent_below(self):
        self.assertEqual(
            mt.bath_concentration_check(0.05, "fluorescent"), "below-range"
        )

    def test_anchor_fluorescent_above(self):
        self.assertEqual(
            mt.bath_concentration_check(0.5, "fluorescent"), "above-range"
        )

    def test_anchor_visible_within(self):
        self.assertEqual(mt.bath_concentration_check(1.5, "visible"), "within-range")

    def test_visible_band_is_higher_than_fluorescent(self):
        # 1.5 mL/100 mL is far above the fluorescent band.
        self.assertEqual(
            mt.bath_concentration_check(1.5, "fluorescent"), "above-range"
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.bath_concentration_check(-0.1, "fluorescent")
        with self.assertRaises(ValueError):
            mt.bath_concentration_check(0.2, "dry")


class IndicationTest(unittest.TestCase):
    def test_anchor_linear_ratio(self):
        self.assertAlmostEqual(mt.indication_linear_ratio(6.0, 1.5), 4.0)

    def test_anchor_linear_flag(self):
        self.assertTrue(mt.indication_is_linear(6.0, 1.5))
        self.assertFalse(mt.indication_is_linear(4.0, 2.0))

    def test_ratio_boundary_three_is_linear(self):
        self.assertTrue(mt.indication_is_linear(3.0, 1.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.indication_linear_ratio(0.0, 1.5)
        with self.assertRaises(ValueError):
            mt.indication_linear_ratio(6.0, 0.0)
        with self.assertRaises(ValueError):
            mt.indication_is_linear(-1.0, 1.0)


class AcceptanceTest(unittest.TestCase):
    def test_anchor_reject_over_limit(self):
        self.assertEqual(mt.acceptance_verdict(True, 4.0, 3.0), "reject")

    def test_anchor_accept_under_limit(self):
        self.assertEqual(mt.acceptance_verdict(True, 2.0, 3.0), "accept")

    def test_anchor_non_relevant_evaluate(self):
        self.assertEqual(mt.acceptance_verdict(False, 9.0, 3.0), "evaluate")

    def test_at_limit_accept(self):
        self.assertEqual(mt.acceptance_verdict(True, 3.0, 3.0), "accept")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.acceptance_verdict(True, 0.0, 3.0)
        with self.assertRaises(ValueError):
            mt.acceptance_verdict(True, 4.0, 0.0)


class ResidualFieldTest(unittest.TestCase):
    def test_anchor_demagnetize(self):
        self.assertEqual(mt.residual_field_verdict(5.0), "demagnetize")

    def test_anchor_acceptable(self):
        self.assertEqual(mt.residual_field_verdict(2.0), "acceptable")

    def test_at_limit_acceptable(self):
        self.assertEqual(mt.residual_field_verdict(3.0), "acceptable")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mt.residual_field_verdict(-1.0)
        with self.assertRaises(ValueError):
            mt.residual_field_verdict(5.0, limit_am=0.0)


class DirectionMappingTest(unittest.TestCase):
    def test_anchor_longitudinal_defect_circular(self):
        self.assertEqual(mt.magnetization_for_defect("longitudinal"), "circular")

    def test_anchor_transverse_defect_longitudinal(self):
        self.assertEqual(mt.magnetization_for_defect("transverse"), "longitudinal")

    def test_synonyms(self):
        self.assertEqual(mt.magnetization_for_defect("axial"), "circular")
        self.assertEqual(mt.magnetization_for_defect("circumferential"), "longitudinal")

    def test_invalid_orientation_raises(self):
        with self.assertRaises(ValueError):
            mt.magnetization_for_defect("oblique")
        with self.assertRaises(ValueError):
            mt.magnetization_for_defect("")


class EndToEndScenarioTest(unittest.TestCase):
    def test_hollow_shaft_inspection_setup(self):
        # 8 in long hollow shaft, 2 in OD, 1 in ID, low fill coil of
        # 250 turns: NI ~ 9743 A-turns, so the coil runs near 39 A.
        d_eff = mt.effective_diameter_hollow(2.0, 1.0)
        ld = mt.effective_ld_ratio(8.0, d_eff)
        ni = mt.coil_ampere_turns_low_fill(ld)
        current = mt.coil_current_from_turns(ni, 250)
        self.assertAlmostEqual(current, 38.97, places=2)
        self.assertAlmostEqual(ld, 4.62, places=2)

    def test_head_shot_plus_coverage_covers_part(self):
        # A 2 in shaft needs 1600 A head shot; a 0.2 m magnetization
        # zone advances 0.17 m per pass at 15 percent overlap, so a
        # 0.5 m shaft needs 3 passes to cover 0.51 m.
        self.assertAlmostEqual(mt.head_shot_current(2.0, 800.0), 1600.0)
        step = mt.coverage_step(0.2, 0.15)
        passes_needed = math.ceil(0.5 / step)
        self.assertEqual(passes_needed, 3)

    def test_indication_disposition_flow(self):
        # A 4 mm relevant linear indication on a part whose limit is
        # 3 mm is rejected; the same indication recorded as
        # non-relevant (magnetic writing) is evaluated, not rejected.
        self.assertEqual(mt.acceptance_verdict(True, 4.0, 3.0), "reject")
        self.assertEqual(mt.acceptance_verdict(False, 4.0, 3.0), "evaluate")
        self.assertTrue(mt.indication_is_linear(4.0, 1.0))

    def test_particle_sensitivity_to_defect_match(self):
        # A tight fatigue crack needs high sensitivity particles; the
        # extra-fine 8 um particle is classified high sensitivity.
        self.assertEqual(mt.particle_size_class(8.0), "extra-fine")
        self.assertEqual(mt.particle_sensitivity(8.0), "high")


if __name__ == "__main__":
    unittest.main(verbosity=2)
