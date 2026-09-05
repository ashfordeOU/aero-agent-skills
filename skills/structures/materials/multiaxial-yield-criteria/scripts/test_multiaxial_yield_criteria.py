"""Contract test for the multiaxial-yield-criteria leaf (wave-40).

Exercises the numbered SKILL.md workflow for hand-checking an isotropic
metal stress state against the classical yield criteria: step 1 collects
the plane-stress state and the yield strength, step 2 computes the von
Mises equivalent stress in plane stress (and in full 3D), step 3
resolves the plane-stress principal stresses from the Mohr circle, step
4 computes the Tresca equivalent stress including the zero out-of-plane
principal, step 5 forms the yield margins of yield strength over each
equivalent stress, step 6 runs the von Mises combined bending-plus-
torsion margin for a shaft section, step 7 issues the von Mises yield
envelope verdict for the biaxial point, and step 8 confirms every
computed number with this deterministic contract test. All methods are
offline, stdlib only, deterministic, and assert the prep-verified
worked-example anchors of the leaf spec.
"""

import math
import unittest

from multiaxial_yield_criteria_logic import (
    combined_bending_torsion_margin,
    is_within_von_mises_envelope,
    plane_stress_principals,
    tresca_equivalent,
    tresca_plane_stress,
    von_mises_3d,
    von_mises_plane_stress,
    yield_margin,
)

# Worked example of the leaf spec: plane stress sx = 200 MPa,
# sy = -50 MPa, txy = 60 MPa against Sy = 400 MPa.
SX = 200.0
SY = -50.0
TXY = 60.0
SY_YIELD = 400.0

VM_ANCHOR = 251.594913  # von Mises, prep-verified within 1e-4
P1_ANCHOR = 213.654246  # sigma_1, prep-verified within 1e-4
P2_ANCHOR = -63.654246  # sigma_2, prep-verified within 1e-4
TRESCA_ANCHOR = 277.308492  # Tresca, prep-verified within 1e-4
MARGIN_VM_ANCHOR = 0.589857  # within 1e-5
MARGIN_TRESCA_ANCHOR = 0.442437  # within 1e-5
CB_EQUIV_ANCHOR = 249.799920  # sqrt(180^2 + 3*100^2), within 1e-4
CB_MARGIN_ANCHOR = 0.401121  # within 1e-5
TAU_EDGE = 230.940108  # Sy/sqrt(3), pure shear envelope edge


class WorkedExampleVonMisesTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: compute the von Mises equivalent
    stress for the worked plane-stress state."""

    def test_worked_plane_stress_von_mises_anchor(self):
        """The von Mises equivalent stress of the step-2 evaluation is
        251.594913 MPa, inside the 1e-4 spec bound for the biaxial
        plane-stress state with the in-plane shear."""
        self.assertAlmostEqual(
            von_mises_plane_stress(SX, SY, TXY), VM_ANCHOR, delta=1e-4
        )

    def test_worked_principals_anchor(self):
        """The Mohr circle of step 3 resolves principals (213.654246,
        -63.654246) MPa for the worked plane-stress state, sigma_1
        ordered above sigma_2."""
        s1, s2 = plane_stress_principals(SX, SY, TXY)
        self.assertAlmostEqual(s1, P1_ANCHOR, delta=1e-4)
        self.assertAlmostEqual(s2, P2_ANCHOR, delta=1e-4)
        self.assertGreaterEqual(s1, s2)

    def test_worked_tresca_anchor(self):
        """Step 4 of the SKILL.md workflow gives the Tresca equivalent
        stress 277.308492 MPa for the worked plane-stress state."""
        self.assertAlmostEqual(
            tresca_plane_stress(SX, SY, TXY), TRESCA_ANCHOR, delta=1e-4
        )

    def test_worked_von_mises_margin_anchor(self):
        """The step-5 yield margin on the von Mises equivalent stress is
        0.589857 for the worked example."""
        self.assertAlmostEqual(
            yield_margin(von_mises_plane_stress(SX, SY, TXY), SY_YIELD),
            MARGIN_VM_ANCHOR,
            delta=1e-5,
        )

    def test_worked_tresca_margin_anchor(self):
        """The step-5 yield margin on the Tresca equivalent stress is
        0.442437 for the worked example."""
        self.assertAlmostEqual(
            yield_margin(tresca_plane_stress(SX, SY, TXY), SY_YIELD),
            MARGIN_TRESCA_ANCHOR,
            delta=1e-5,
        )

    def test_worked_envelope_verdict_inside(self):
        """The step-7 envelope verdict is True: the biaxial point (200,
        -50) MPa lies inside the von Mises yield envelope at Sy 400 MPa."""
        self.assertTrue(
            is_within_von_mises_envelope(SX, SY, SY_YIELD)
        )


class CombinedBendingTorsionTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: run the von Mises combined
    bending-plus-torsion margin for a shaft section."""

    def test_combined_equivalent_anchor(self):
        """The shaft von Mises equivalent of sigma_b 180 MPa with tau
        100 MPa is 249.799920 MPa, sqrt(sigma_b^2 + 3*tau^2)."""
        self.assertAlmostEqual(
            math.sqrt(180.0 ** 2 + 3.0 * 100.0 ** 2),
            CB_EQUIV_ANCHOR,
            delta=1e-4,
        )
        self.assertAlmostEqual(
            combined_bending_torsion_margin(180.0, 100.0, 350.0),
            yield_margin(math.sqrt(180.0 ** 2 + 3.0 * 100.0 ** 2), 350.0),
            places=12,
        )

    def test_combined_margin_anchor(self):
        """The combined bending-plus-torsion yield margin against Sy 350
        MPa is 0.401121 for the shaft section."""
        self.assertAlmostEqual(
            combined_bending_torsion_margin(180.0, 100.0, 350.0),
            CB_MARGIN_ANCHOR,
            delta=1e-5,
        )


class UniaxialAndPureShearIdentityTest(unittest.TestCase):
    """Closed-form identities of the SKILL.md domain quick reference:
    uniaxial tension reduces von Mises to |sigma| and pure shear to
    sqrt(3)*tau."""

    def test_uniaxial_von_mises_positive(self):
        """A uniaxial tension s reduces the step-2 von Mises equivalent
        to s itself for a positive normal stress."""
        self.assertAlmostEqual(
            von_mises_plane_stress(120.0, 0.0, 0.0), 120.0, places=12
        )

    def test_uniaxial_von_mises_negative(self):
        """Uniaxial compression -s reduces the von Mises equivalent to
        |s|, so compression and tension of equal magnitude agree."""
        self.assertAlmostEqual(
            von_mises_plane_stress(-150.0, 0.0, 0.0), 150.0, places=12
        )

    def test_pure_shear_von_mises(self):
        """Pure shear tau gives the von Mises equivalent sqrt(3)*tau."""
        self.assertAlmostEqual(
            von_mises_plane_stress(0.0, 0.0, 100.0),
            math.sqrt(3.0) * 100.0,
            places=12,
        )

    def test_pure_shear_tresca_is_two_tau(self):
        """Plane-stress pure shear tau gives a Tresca equivalent of
        2*tau, the classical ratio 2/sqrt(3) over von Mises."""
        tau = 100.0
        self.assertAlmostEqual(tresca_plane_stress(0.0, 0.0, tau), 2.0 * tau, places=12)
        self.assertAlmostEqual(
            2.0 / math.sqrt(3.0), 1.1547005383792515, places=12
        )

    def test_uniaxial_tresca_equals_sigma(self):
        """A uniaxial tension s gives a Tresca equivalent of s through
        the zero out-of-plane principal pair of step 4."""
        self.assertAlmostEqual(tresca_plane_stress(120.0, 0.0, 0.0), 120.0, places=12)

    def test_biaxial_equal_opposite_identity(self):
        """Biaxial tension and compression of equal magnitude s gives
        sqrt(3)*s by von Mises and 2*s by Tresca."""
        s = 100.0
        self.assertAlmostEqual(
            von_mises_plane_stress(s, -s, 0.0), math.sqrt(3.0) * s, places=12
        )
        self.assertAlmostEqual(tresca_plane_stress(s, -s, 0.0), 2.0 * s, places=12)


class ThreeDimensionalConsistencyTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow in full 3D: the von_mises_3d form
    must reduce to the plane-stress form and vanish under hydrostatic
    pressure."""

    def test_3d_reduces_to_plane_stress(self):
        """The 3D von Mises equivalent with sigma_z, tau_yz and tau_zx
        all zero equals the plane-stress von Mises equivalent to float
        precision."""
        self.assertEqual(
            von_mises_3d(SX, SY, 0.0, TXY, 0.0, 0.0),
            von_mises_plane_stress(SX, SY, TXY),
        )

    def test_3d_hydrostatic_state_zero_equivalent(self):
        """A hydrostatic normal stress state with equal sigma_x, sigma_y,
        sigma_z and no shear has zero von Mises equivalent stress."""
        self.assertEqual(von_mises_3d(200.0, 200.0, 200.0, 0.0, 0.0, 0.0), 0.0)
        self.assertLess(von_mises_3d(150.0, 80.0, 40.0, 30.0, 20.0, 10.0), 400.0)


class TrescaVersusVonMisesTest(unittest.TestCase):
    """Step 4 versus step 2 of the SKILL.md workflow: the Tresca
    equivalent never falls below the von Mises equivalent for the same
    plane-stress state."""

    def test_tresca_never_below_von_mises_grid(self):
        """Across a signed grid of plane-stress states the Tresca
        equivalent of step 4 stays at or above the von Mises equivalent
        of step 2."""
        for sx in range(-400, 401, 40):
            for sy in range(-400, 401, 40):
                for txy in range(-300, 301, 60):
                    vm = von_mises_plane_stress(sx, sy, txy)
                    tresca = tresca_plane_stress(sx, sy, txy)
                    self.assertGreaterEqual(tresca, vm - 1e-9)

    def test_tresca_over_von_mises_ratio_capped(self):
        """The Tresca over von Mises ratio stays within the classical
        bound 2/sqrt(3) for shearing states, and equals 1.0 for the
        uniaxial tension direction."""
        self.assertAlmostEqual(
            tresca_plane_stress(100.0, 0.0, 0.0)
            / von_mises_plane_stress(100.0, 0.0, 0.0),
            1.0,
            places=12,
        )
        ratio = tresca_plane_stress(0.0, 0.0, 100.0) / von_mises_plane_stress(
            0.0, 0.0, 100.0
        )
        self.assertAlmostEqual(ratio, 2.0 / math.sqrt(3.0), places=12)


class EnvelopeVerdictTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: issue the von Mises yield
    envelope verdict for a biaxial point, with the boundary counted as
    within."""

    def test_envelope_uniaxial_yield_point_on_boundary(self):
        """The uniaxial point (Sy, 0) sits on the envelope boundary, and
        the boundary counts as within."""
        self.assertTrue(is_within_von_mises_envelope(400.0, 0.0, 400.0))

    def test_envelope_biaxial_corner_outside(self):
        """The biaxial corner (Sy, -Sy) lies outside the von Mises
        envelope."""
        self.assertFalse(is_within_von_mises_envelope(400.0, -400.0, 400.0))

    def test_envelope_origin_and_moderate_points_inside(self):
        """The origin, the worked point, and moderate biaxial points sit
        inside the von Mises envelope, symmetric under flipping both
        normal stress signs."""
        self.assertTrue(is_within_von_mises_envelope(0.0, 0.0, 400.0))
        self.assertTrue(is_within_von_mises_envelope(200.0, -50.0, 400.0))
        self.assertTrue(is_within_von_mises_envelope(350.0, 100.0, 400.0))
        self.assertEqual(
            is_within_von_mises_envelope(250.0, -100.0, 400.0),
            is_within_von_mises_envelope(-250.0, 100.0, 400.0),
        )

    def test_envelope_pure_shear_edge_on_boundary(self):
        """The pure shear envelope edge at tau = Sy/sqrt(3) =
        230.940108 MPa keeps the shear von Mises equivalent exactly at
        the yield strength."""
        self.assertAlmostEqual(
            von_mises_plane_stress(0.0, 0.0, TAU_EDGE), 400.0, delta=1e-4
        )


class YieldMarginSignTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: yield margin zero at yield,
    positive below yield, negative past yield."""

    def test_margin_zero_at_yield(self):
        """The yield margin is exactly zero when the equivalent stress
        equals the yield strength."""
        self.assertAlmostEqual(yield_margin(400.0, 400.0), 0.0, places=12)

    def test_margin_positive_below_yield(self):
        """The yield margin is positive when the equivalent stress sits
        below the yield strength."""
        self.assertAlmostEqual(yield_margin(200.0, 400.0), 1.0, places=12)
        self.assertGreater(yield_margin(300.0, 400.0), 0.0)

    def test_margin_negative_above_yield(self):
        """The yield margin is negative when the equivalent stress
        exceeds the yield strength."""
        self.assertAlmostEqual(yield_margin(500.0, 400.0), -0.2, places=12)
        self.assertLess(yield_margin(600.0, 400.0), 0.0)

    def test_margin_scales_linearly_with_yield_strength(self):
        """Doubling the yield strength doubles the margin plus one,
        since margin = Sy/equivalent - 1."""
        m1 = yield_margin(200.0, 400.0)
        m2 = yield_margin(200.0, 800.0)
        self.assertAlmostEqual(m2, 2.0 * (m1 + 1.0) - 1.0, places=12)


class ValueRejectionTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the contract test confirms that
    non-physical inputs are rejected with ValueError."""

    def test_yield_margin_rejects_zero_equivalent(self):
        """yield_margin rejects a zero equivalent stress, where the
        margin would divide by zero."""
        with self.assertRaises(ValueError):
            yield_margin(0.0, 400.0)

    def test_yield_margin_rejects_negative_equivalent(self):
        """yield_margin rejects a negative equivalent stress as
        non-physical."""
        with self.assertRaises(ValueError):
            yield_margin(-1.0, 400.0)

    def test_yield_margin_rejects_nonpositive_yield(self):
        """yield_margin rejects a zero or negative yield strength."""
        with self.assertRaises(ValueError):
            yield_margin(200.0, 0.0)
        with self.assertRaises(ValueError):
            yield_margin(200.0, -400.0)

    def test_tresca_equivalent_rejects_unordered_principals(self):
        """tresca_equivalent rejects principal inputs where sigma_1 sits
        below sigma_3 because the principals must be ordered."""
        with self.assertRaises(ValueError):
            tresca_equivalent(100.0, 200.0)

    def test_envelope_rejects_nonpositive_yield(self):
        """is_within_von_mises_envelope rejects a non-positive yield
        strength."""
        with self.assertRaises(ValueError):
            is_within_von_mises_envelope(100.0, 100.0, 0.0)

    def test_combined_margin_rejects_zero_loads(self):
        """The combined bending-plus-torsion margin rejects a zero
        bending and torsional stress state through yield_margin."""
        with self.assertRaises(ValueError):
            combined_bending_torsion_margin(0.0, 0.0, 350.0)


class ReturnTypeAndDeterminismTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: return types and determinism are
    part of the contract."""

    def test_principals_return_tuple_of_two(self):
        """plane_stress_principals returns a two-element tuple with the
        ordered principal stresses."""
        result = plane_stress_principals(SX, SY, TXY)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_envelope_returns_bool(self):
        """is_within_von_mises_envelope returns a plain bool verdict."""
        verdict = is_within_von_mises_envelope(200.0, -50.0, 400.0)
        self.assertIsInstance(verdict, bool)

    def test_determinism_repeat_calls(self):
        """Repeated calls with the same plane-stress state return bitwise
        identical float equivalents, so the step-2 and step-4 numbers are
        reproducible."""
        vm_a = von_mises_plane_stress(SX, SY, TXY)
        vm_b = von_mises_plane_stress(SX, SY, TXY)
        tr_a = tresca_plane_stress(SX, SY, TXY)
        tr_b = tresca_plane_stress(SX, SY, TXY)
        self.assertEqual(vm_a, vm_b)
        self.assertEqual(tr_a, tr_b)
        self.assertIsInstance(vm_a, float)
        self.assertIsInstance(tr_a, float)


if __name__ == "__main__":
    unittest.main()
