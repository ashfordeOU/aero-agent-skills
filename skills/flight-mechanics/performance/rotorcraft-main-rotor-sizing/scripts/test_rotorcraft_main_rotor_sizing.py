"""Contract test for flight-mechanics/performance/rotorcraft-main-rotor-sizing.

Exercises the SKILL.md workflow of the leaf, whose numbered steps are:
1. Fix the design point: takeoff mass m and the design ceilings, the
   main-rotor-disk-loading ceiling, the ct-over-sigma hover design
   point, the blade count and the rotor tip speed, with the weight-borne
   hover thrust T = m * G0, 2. Size the disk from the weight against the
   ceiling with disk_area_and_radius and confirm the disk sits exactly at
   the main-rotor-disk-loading ceiling (thrust over area round trip and
   PI * radius**2 recovering the area), 3. Compute the rotor-thrust-
   coefficient at the rotor tip speed with hover_thrust_coefficient and
   cross-check the ceiling identity CT = disk_loading_max / (rho *
   tip_speed**2), 4. Close the rotor solidity from the ct-over-sigma
   design point with solidity_closure and check the design-point round
   trip CT / sigma, 5. Lay out the rectangular blades with
   blade_area_chord, total blade area and constant blade chord from the
   blade count, verifying the solidity identity sigma = b * c * R / A,
   6. Check the rotor-tip-mach number with tip_mach against the speed of
   sound, subcritical at sea level so no compressibility correction
   enters, 7. Close out with this deterministic contract test.

Worked example: takeoff mass 4500 kg at the 350 Pa ceiling, ct-over-
sigma design point 0.12, 4 blades, 210 m/s tip speed (rho 1.225 kg/m3,
speed of sound 340.3 m/s), plus the 3000 kg / 300 Pa / 0.10 secondary
state. All numeric asserts are order-safe tolerances (assertAlmostEqual
delta or math.isclose); exact equality is used only for literal module
constants, deterministic bit-identical repeats and round trips exact by
construction. Offline, deterministic, stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rotorcraft_main_rotor_sizing_logic as m

MASS_PRIMARY = 4500.0
THRUST_PRIMARY = MASS_PRIMARY * m.G0
CEILING_PRIMARY = 350.0
CT_SIGMA_PRIMARY = 0.12
BLADES_PRIMARY = 4
TIP_SPEED = 210.0

MASS_SECONDARY = 3000.0
THRUST_SECONDARY = MASS_SECONDARY * m.G0
CEILING_SECONDARY = 300.0
CT_SIGMA_SECONDARY = 0.10


class TestDiskAreaAndRadius(unittest.TestCase):
    """Workflow step 2 of the SKILL.md, sizing the disk from the takeoff
    weight against the main-rotor-disk-loading ceiling: the inversion
    A = T / DL_max and R = sqrt(A / PI)."""

    def test_primary_anchor_area_and_radius(self):
        """Step 2 disk sizing at the 350 Pa ceiling for the 4500-kg
        takeoff mass: area 126.0855 m2 and radius 6.3352 m within 1e-4,
        inside the 115-140 m2 and 6.0-6.7 m bounds."""
        area, radius = m.disk_area_and_radius(THRUST_PRIMARY, CEILING_PRIMARY)
        self.assertAlmostEqual(area, 126.0855, delta=1e-4)
        self.assertAlmostEqual(radius, 6.3352, delta=1e-4)
        self.assertGreater(area, 115.0)
        self.assertLess(area, 140.0)
        self.assertGreater(radius, 6.0)
        self.assertLess(radius, 6.7)

    def test_disk_sized_exactly_at_the_ceiling(self):
        """Step 2 ceiling round trip: the achieved thrust over area from
        disk_area_and_radius equals the 350 Pa main-rotor-disk-loading
        ceiling."""
        area, _ = m.disk_area_and_radius(THRUST_PRIMARY, CEILING_PRIMARY)
        self.assertTrue(math.isclose(THRUST_PRIMARY / area, CEILING_PRIMARY,
                                     rel_tol=1e-12))

    def test_radius_round_trip_recovers_area(self):
        """Step 2 radius round trip: PI * radius**2 recovers the disk
        area to float precision."""
        area, radius = m.disk_area_and_radius(THRUST_PRIMARY, CEILING_PRIMARY)
        self.assertTrue(math.isclose(m.PI * radius ** 2, area, rel_tol=1e-12))
        self.assertEqual(m.PI, math.pi)

    def test_secondary_state_anchor(self):
        """Step 2 disk sizing at the 300 Pa ceiling for the 3000-kg
        mass: area 98.0665 m2 and radius 5.5871 m within 1e-4."""
        area, radius = m.disk_area_and_radius(THRUST_SECONDARY,
                                              CEILING_SECONDARY)
        self.assertAlmostEqual(area, 98.0665, delta=1e-4)
        self.assertAlmostEqual(radius, 5.5871, delta=1e-4)

    def test_radius_scales_with_square_root_of_mass(self):
        """Step 2 scaling identity at a fixed ceiling: the sized disk
        radius scales with the square root of the takeoff mass, so the
        4500-kg rotor is sqrt(1.5) times the 3000-kg radius."""
        _, r_big = m.disk_area_and_radius(THRUST_PRIMARY, 350.0)
        _, r_small = m.disk_area_and_radius(THRUST_SECONDARY, 350.0)
        self.assertTrue(math.isclose(r_big / r_small,
                                     math.sqrt(MASS_PRIMARY / MASS_SECONDARY),
                                     rel_tol=1e-12))
        self.assertGreater(r_big, r_small)

    def test_disk_area_inversely_proportional_to_ceiling(self):
        """Step 2 ceiling scaling: at one thrust the disk area halves
        when the main-rotor-disk-loading ceiling doubles, and the
        radius falls by sqrt(2)."""
        a_lo, r_lo = m.disk_area_and_radius(THRUST_PRIMARY, 250.0)
        a_hi, r_hi = m.disk_area_and_radius(THRUST_PRIMARY, 500.0)
        self.assertTrue(math.isclose(a_lo / a_hi, 2.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(r_lo / r_hi, math.sqrt(2.0),
                                     rel_tol=1e-12))

    def test_anti_torque_rotor_sibling_inversion_cross_check(self):
        """Step 2 convention cross-check: disk_area_and_radius on the
        sibling anti-torque leaf thrust 1851.8519 N at its 300 Pa
        ceiling returns (6.1728, 1.4017) within 1e-4, the shared
        A = T / DL_max inversion applied to different inputs."""
        area, radius = m.disk_area_and_radius(1851.8519, 300.0)
        self.assertAlmostEqual(area, 6.1728, delta=1e-4)
        self.assertAlmostEqual(radius, 1.4017, delta=1e-4)

    def test_zero_or_negative_thrust_rejected(self):
        """Step 2 rejection: a non-positive weight-borne thrust raises
        ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.disk_area_and_radius(bad, 350.0)

    def test_zero_or_negative_disk_loading_rejected(self):
        """Step 2 rejection: a non-positive main-rotor-disk-loading
        ceiling raises ValueError."""
        for bad in (0.0, -50.0):
            with self.assertRaises(ValueError):
                m.disk_area_and_radius(44129.925, bad)


class TestHoverThrustCoefficient(unittest.TestCase):
    """Workflow step 3 of the SKILL.md, the rotor-thrust-coefficient
    from momentum theory at the rotor tip speed, with the ceiling
    identity cross-check."""

    def test_primary_anchor_thrust_coefficient(self):
        """Step 3 thrust coefficient of the 4500-kg sized rotor at the
        210 m/s rotor tip speed: 0.006479 within 1e-6, inside the
        0.0055-0.0075 bound."""
        ct = m.hover_thrust_coefficient(THRUST_PRIMARY, m.RHO_SL, 6.3352,
                                        TIP_SPEED)
        self.assertAlmostEqual(ct, 0.006479, delta=1e-6)
        self.assertGreater(ct, 0.0055)
        self.assertLess(ct, 0.0075)

    def test_ceiling_identity_independent_of_rotor_size(self):
        """Step 3 ceiling identity: at the sized disk the thrust
        coefficient equals CEILING / (rho * tip_speed**2) whether the
        takeoff mass is 4500 kg or 3000 kg, so CT is independent of the
        rotor size."""
        _, r1 = m.disk_area_and_radius(THRUST_PRIMARY, 350.0)
        _, r2 = m.disk_area_and_radius(THRUST_SECONDARY, 350.0)
        identity = 350.0 / (m.RHO_SL * TIP_SPEED ** 2)
        ct1 = m.hover_thrust_coefficient(THRUST_PRIMARY, m.RHO_SL, r1,
                                         TIP_SPEED)
        ct2 = m.hover_thrust_coefficient(THRUST_SECONDARY, m.RHO_SL, r2,
                                         TIP_SPEED)
        self.assertTrue(math.isclose(ct1, identity, rel_tol=1e-12))
        self.assertTrue(math.isclose(ct2, identity, rel_tol=1e-12))

    def test_matches_definition_with_pi_radius_squared(self):
        """Step 3 definition check: the coefficient equals thrust over
        (rho * PI * radius**2 * tip_speed**2) computed by hand."""
        area, radius = m.disk_area_and_radius(THRUST_PRIMARY, CEILING_PRIMARY)
        ct = m.hover_thrust_coefficient(THRUST_PRIMARY, m.RHO_SL, radius,
                                        TIP_SPEED)
        manual = THRUST_PRIMARY / (m.RHO_SL * m.PI * radius ** 2 *
                                   TIP_SPEED ** 2)
        self.assertTrue(math.isclose(ct, manual, rel_tol=1e-12))

    def test_secondary_state_anchor_thrust_coefficient(self):
        """Step 3 thrust coefficient of the secondary 3000-kg state at
        the 300 Pa ceiling: 0.005553 within 1e-6 at the 210 m/s tip
        speed."""
        ct = m.hover_thrust_coefficient(THRUST_SECONDARY, m.RHO_SL, 5.5871,
                                        TIP_SPEED)
        self.assertAlmostEqual(ct, 0.005553, delta=1e-6)

    def test_zero_thrust_rejected(self):
        """Step 3 rejection: zero weight-borne thrust raises
        ValueError."""
        with self.assertRaises(ValueError):
            m.hover_thrust_coefficient(0.0, m.RHO_SL, 6.0, TIP_SPEED)

    def test_zero_rho_radius_or_tip_speed_rejected(self):
        """Step 3 rejection: zero air density, zero rotor radius or zero
        rotor tip speed each raise ValueError."""
        with self.assertRaises(ValueError):
            m.hover_thrust_coefficient(44129.925, 0.0, 6.0, TIP_SPEED)
        with self.assertRaises(ValueError):
            m.hover_thrust_coefficient(44129.925, m.RHO_SL, 0.0, TIP_SPEED)
        with self.assertRaises(ValueError):
            m.hover_thrust_coefficient(44129.925, m.RHO_SL, 6.0, 0.0)


class TestSolidityClosure(unittest.TestCase):
    """Workflow step 4 of the SKILL.md, closing the rotor solidity from
    the ct-over-sigma hover design point."""

    def test_primary_anchor_solidity(self):
        """Step 4 solidity closure of the module's own thrust
        coefficient at the 0.12 ct-over-sigma design point: 0.053990
        within 1e-6, inside the 0.045-0.065 bound."""
        _, radius = m.disk_area_and_radius(THRUST_PRIMARY, CEILING_PRIMARY)
        ct = m.hover_thrust_coefficient(THRUST_PRIMARY, m.RHO_SL, radius,
                                        TIP_SPEED)
        sigma = m.solidity_closure(ct, CT_SIGMA_PRIMARY)
        self.assertAlmostEqual(sigma, 0.053990, delta=1e-6)
        self.assertGreater(sigma, 0.045)
        self.assertLess(sigma, 0.065)

    def test_closure_round_trip_returns_design_point(self):
        """Step 4 closure round trip: sigma times the ct-over-sigma
        design point returns the input thrust coefficient and the
        design-point check CT / sigma equals the 0.12 design value."""
        sigma = m.solidity_closure(0.006479, 0.12)
        self.assertTrue(math.isclose(sigma * 0.12, 0.006479, rel_tol=1e-12))
        self.assertTrue(math.isclose(0.006479 / sigma, 0.12, rel_tol=1e-12))

    def test_secondary_state_anchor_solidity(self):
        """Step 4 solidity closure of the secondary state at the 0.10
        ct-over-sigma design point: 0.055532 within 1e-6."""
        _, radius = m.disk_area_and_radius(THRUST_SECONDARY,
                                           CEILING_SECONDARY)
        ct = m.hover_thrust_coefficient(THRUST_SECONDARY, m.RHO_SL, radius,
                                        TIP_SPEED)
        sigma = m.solidity_closure(ct, CT_SIGMA_SECONDARY)
        self.assertAlmostEqual(sigma, 0.055532, delta=1e-6)
        self.assertTrue(math.isclose(ct / sigma, 0.10, rel_tol=1e-9))

    def test_sigma_scales_linearly_with_disk_loading_ceiling(self):
        """Step 4 linear scaling at a fixed rotor tip speed and design
        point: sigma = DL_max / (rho * Vtip**2 * (CT/sigma)_design), so
        raising the main-rotor-disk-loading ceiling from 350 to 600 Pa
        scales sigma by 600/350 to about 0.092."""
        ct_lo = 350.0 / (m.RHO_SL * TIP_SPEED ** 2)
        sigma_lo = m.solidity_closure(ct_lo, 0.12)
        ct_hi = 600.0 / (m.RHO_SL * TIP_SPEED ** 2)
        sigma_hi = m.solidity_closure(ct_hi, 0.12)
        self.assertTrue(math.isclose(sigma_hi / sigma_lo, 600.0 / 350.0,
                                     rel_tol=1e-12))
        self.assertAlmostEqual(sigma_hi, 0.092, delta=1e-3)

    def test_non_positive_ct_or_design_point_rejected(self):
        """Step 4 rejection: a non-positive thrust coefficient or a
        non-positive ct-over-sigma design point raises ValueError."""
        with self.assertRaises(ValueError):
            m.solidity_closure(0.0, 0.12)
        with self.assertRaises(ValueError):
            m.solidity_closure(0.006479, 0.0)


class TestBladeAreaChord(unittest.TestCase):
    """Workflow step 5 of the SKILL.md, laying out the rectangular
    blades: total blade area from the closed solidity and the constant
    blade chord from the blade count."""

    def test_primary_anchor_blade_area_and_chord(self):
        """Step 5 blade layout of the primary rotor: blade area 6.8073
        m2 and chord 0.2686 m within 1e-4 at the 4-blade count, chord
        inside the 0.22-0.32 m bound with blade aspect ratio about
        23.6."""
        blade_area, chord = m.blade_area_chord(0.053990, 126.0855, 4, 6.3352)
        self.assertAlmostEqual(blade_area, 6.8073, delta=1e-4)
        self.assertAlmostEqual(chord, 0.2686, delta=1e-4)
        self.assertGreater(chord, 0.22)
        self.assertLess(chord, 0.32)
        self.assertTrue(math.isclose(6.3352 / chord, 23.6, rel_tol=1e-2))

    def test_solidity_identity_from_blade_count_chord_radius(self):
        """Step 5 solidity identity: b * c * R / A recovers the input
        solidity of the primary rotor."""
        blade_area, chord = m.blade_area_chord(0.053990, 126.0855, 4, 6.3352)
        recovered = 4 * chord * 6.3352 / 126.0855
        self.assertTrue(math.isclose(recovered, 0.053990, rel_tol=1e-12))
        self.assertTrue(math.isclose(chord * 4 * 6.3352, blade_area,
                                     rel_tol=1e-12))

    def test_secondary_state_anchor_blade_area_and_chord(self):
        """Step 5 blade layout of the secondary 3000-kg rotor: blade
        area 5.4459 m2 and chord 0.2437 m within 1e-4."""
        blade_area, chord = m.blade_area_chord(0.055532, 98.0665, 4, 5.5871)
        self.assertAlmostEqual(blade_area, 5.4459, delta=1e-4)
        self.assertAlmostEqual(chord, 0.2437, delta=1e-4)

    def test_blade_area_scales_linearly_with_solidity(self):
        """Step 5 linear scaling: doubling the solidity doubles the
        total blade area and the chord at a fixed disk and blade
        count."""
        area_lo, chord_lo = m.blade_area_chord(0.05, 100.0, 4, 6.0)
        area_hi, chord_hi = m.blade_area_chord(0.10, 100.0, 4, 6.0)
        self.assertTrue(math.isclose(area_hi / area_lo, 2.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(chord_hi / chord_lo, 2.0,
                                     rel_tol=1e-12))

    def test_float_blade_count_matches_integer_count(self):
        """Step 5 blade count handling: a float 4.0 blade count gives
        the same chord as the integer 4, and the disk area times the
        solidity sets the blade area either way."""
        a_int, c_int = m.blade_area_chord(0.053990, 126.0855, 4, 6.3352)
        a_flt, c_flt = m.blade_area_chord(0.053990, 126.0855, 4.0, 6.3352)
        self.assertTrue(math.isclose(a_int, a_flt, rel_tol=1e-15))
        self.assertTrue(math.isclose(c_int, c_flt, rel_tol=1e-15))

    def test_zero_solidity_area_or_radius_rejected(self):
        """Step 5 rejection: a zero solidity, zero disk area or zero
        radius raises ValueError."""
        with self.assertRaises(ValueError):
            m.blade_area_chord(0.0, 126.0855, 4, 6.3352)
        with self.assertRaises(ValueError):
            m.blade_area_chord(0.053990, 0.0, 4, 6.3352)
        with self.assertRaises(ValueError):
            m.blade_area_chord(0.053990, 126.0855, 4, 0.0)

    def test_fractional_or_non_positive_blade_count_rejected(self):
        """Step 5 rejection: a zero, negative or fractional blade count
        (2.5) raises ValueError, the count must be a positive
        integer."""
        for bad in (0, -2, 2.5):
            with self.assertRaises(ValueError):
                m.blade_area_chord(0.053990, 126.0855, bad, 6.3352)


class TestTipMach(unittest.TestCase):
    """Workflow step 6 of the SKILL.md, the rotor-tip-mach check of the
    rotor tip speed against the speed of sound."""

    def test_primary_anchor_tip_mach(self):
        """Step 6 tip mach of the 210 m/s rotor tip speed against the
        340.3 m/s sea-level speed of sound: 0.61710 within 1e-5, inside
        the 0.55-0.70 bound, subcritical so no compressibility
        correction enters."""
        mach = m.tip_mach(TIP_SPEED, m.A0_SL)
        self.assertAlmostEqual(mach, 0.61710, delta=1e-5)
        self.assertGreater(mach, 0.55)
        self.assertLess(mach, 0.70)

    def test_definition_and_other_tip_speed(self):
        """Step 6 definition check: M_tip = tip_speed / speed_of_sound
        holds at any tip speed, for example 200 m/s over 340.3 m/s."""
        mach = m.tip_mach(200.0, 340.3)
        self.assertTrue(math.isclose(mach, 200.0 / 340.3, rel_tol=1e-15))
        self.assertEqual(m.A0_SL, 340.3)

    def test_tip_mach_unchanged_when_only_mass_or_ceiling_changes(self):
        """Step 6 invariance: the tip mach stays 0.61710 across the two
        worked states because only the takeoff mass and the disk-loading
        ceiling change, never the 210 m/s rotor tip speed."""
        m1 = m.tip_mach(210.0, 340.3)
        m2 = m.tip_mach(210.0, m.A0_SL)
        self.assertTrue(math.isclose(m1, m2, rel_tol=1e-15))
        self.assertAlmostEqual(m2, 0.61710, delta=1e-5)

    def test_zero_tip_speed_returns_zero_mach(self):
        """Step 6 edge case: a stationary rotor at zero rotor tip speed
        has zero tip mach, allowed by the validation."""
        self.assertEqual(m.tip_mach(0.0, 340.3), 0.0)

    def test_negative_tip_speed_or_zero_speed_of_sound_rejected(self):
        """Step 6 rejection: a negative rotor tip speed or a non-positive
        speed of sound raises ValueError."""
        with self.assertRaises(ValueError):
            m.tip_mach(-1.0, 340.3)
        with self.assertRaises(ValueError):
            m.tip_mach(210.0, 0.0)


class TestChainDeterminism(unittest.TestCase):
    """Workflow steps 1-7 of the SKILL.md closed together: the full
    sizing chain, determinism of the module and the magnitude bounds."""

    def test_full_chain_reproduces_primary_worked_example(self):
        """Steps 1-6 chain for the 4500-kg takeoff mass at 350 Pa, 0.12,
        4 blades and 210 m/s: weight-borne thrust, disk area and radius,
        thrust coefficient, solidity, blade area and chord all match the
        spec anchors within tolerance."""
        thrust = MASS_PRIMARY * m.G0
        self.assertAlmostEqual(thrust, 44129.925, delta=1e-9)
        area, radius = m.disk_area_and_radius(thrust, 350.0)
        self.assertAlmostEqual(area, 126.0855, delta=1e-4)
        self.assertAlmostEqual(radius, 6.3352, delta=1e-4)
        ct = m.hover_thrust_coefficient(thrust, m.RHO_SL, radius, TIP_SPEED)
        self.assertAlmostEqual(ct, 0.006479, delta=1e-6)
        sigma = m.solidity_closure(ct, 0.12)
        self.assertAlmostEqual(sigma, 0.053990, delta=1e-6)
        blade_area, chord = m.blade_area_chord(sigma, area, 4, radius)
        self.assertAlmostEqual(blade_area, 6.8073, delta=1e-4)
        self.assertAlmostEqual(chord, 0.2686, delta=1e-4)
        self.assertAlmostEqual(m.tip_mach(TIP_SPEED, m.A0_SL), 0.61710,
                               delta=1e-5)

    def test_secondary_chain_disk_shrinks_with_mass(self):
        """Steps 1-6 chain for the 3000-kg mass at the 300 Pa ceiling
        and 0.10 design point: the disk radius shrinks to 5.5871 m
        against the primary 6.3352 m and the solidity closes at
        0.055532."""
        thrust = MASS_SECONDARY * m.G0
        self.assertAlmostEqual(thrust, 29419.950, delta=1e-9)
        area, radius = m.disk_area_and_radius(thrust, 300.0)
        self.assertAlmostEqual(area, 98.0665, delta=1e-4)
        self.assertAlmostEqual(radius, 5.5871, delta=1e-4)
        ct = m.hover_thrust_coefficient(thrust, m.RHO_SL, radius, TIP_SPEED)
        self.assertAlmostEqual(ct, 0.005553, delta=1e-6)
        sigma = m.solidity_closure(ct, 0.10)
        self.assertAlmostEqual(sigma, 0.055532, delta=1e-6)
        blade_area, chord = m.blade_area_chord(sigma, area, 4, radius)
        self.assertAlmostEqual(blade_area, 5.4459, delta=1e-4)
        self.assertAlmostEqual(chord, 0.2437, delta=1e-4)

    def test_repeated_calls_are_bit_identical(self):
        """Step 7 determinism: no RNG anywhere, so identical calls
        return bit-identical floats run to run."""
        first = m.disk_area_and_radius(44129.925, 350.0)
        second = m.disk_area_and_radius(44129.925, 350.0)
        self.assertEqual(first, second)
        self.assertEqual(m.hover_thrust_coefficient(44129.925, m.RHO_SL,
                                                    6.3352, 210.0),
                         m.hover_thrust_coefficient(44129.925, m.RHO_SL,
                                                    6.3352, 210.0))


if __name__ == "__main__":
    unittest.main()
