"""Offline deterministic contract test for the torsion shear flow module.

Runs with stdlib unittest only (no network, no external processes):

    python3 scripts/test_torsion_shear_flow.py

Covers the wave-38 spec anchors: solid shaft r = 0.05 m J = 9.817e-6 m4,
tube ro = 0.05, ri = 0.04 J = 5.796e-6 m4 (ri = 0 degenerates to the
solid value), open rectangle 0.1 x 0.003 m J = 9.0e-10 m4; box
0.5 x 0.3 m (A_m = 0.15 m2), uniform wall 0.002 m, G = 27e9 Pa,
T = 100 kN m giving q = 333333 N/m, twist 0.03292 rad/m, tau 1.667e8 Pa,
margin 0.2; two-cell box with A1 = 0.06, A2 = 0.12, S1 = 350, S2 = 550,
S12 = 150, G = 27e9 Pa, T = 50 kN m giving q1 = 126263, q2 = 145202 N/m
and twist 0.012763 rad/m. Also covers the Bredt uniform-wall identity,
doubling and scaling laws, symmetric two-cell degeneracy, torque
reconstruction, twist compatibility to 1e-6, dict key exactness,
run-to-run determinism and ValueError rejection of every non-physical
input.
"""

import unittest

from torsion_shear_flow_logic import (
    bredt_shear_flow,
    closed_twist_rate,
    multi_cell_shear_flow,
    polar_j_solid,
    polar_j_tube,
    saint_venant_j_open,
    saint_venant_j_rectangle,
    torsion_margin,
)

# Real module outputs for the wave-38 anchors (prep-verified bounds).
J_SOLID_ANCHOR = 9.817477042468105e-06
J_TUBE_ANCHOR = 5.79623844587317e-06
J_RECT_ANCHOR = 9.000000000000001e-10
Q_BOX_ANCHOR = 333333.3333333334
TWIST_BOX_ANCHOR = 0.03292181069958848
TAU_BOX_ANCHOR = 166666666.6666667
MARGIN_BOX_ANCHOR = 0.19999999999999996
Q1_ANCHOR = 126262.62626262628
Q2_ANCHOR = 145202.0202020202
TWIST_TWOCELL_ANCHOR = 0.012762657438583366


def rel_error(actual, expected):
    """Relative error magnitude between actual and expected values."""
    return abs(actual - expected) / abs(expected)


class TestPolarJ(unittest.TestCase):
    def test_solid_worked_anchor(self):
        # Solid shaft r = 0.05 m: J near the prep bound 9.817e-6 m4.
        self.assertLess(rel_error(polar_j_solid(0.05), J_SOLID_ANCHOR), 1e-9)
        self.assertAlmostEqual(polar_j_solid(0.05) / 9.817e-6, 1.0, delta=0.01)

    def test_solid_scales_with_r4(self):
        # Doubling the radius multiplies J by 16.
        j1 = polar_j_solid(0.05)
        j2 = polar_j_solid(0.10)
        self.assertAlmostEqual(j2 / j1, 16.0, delta=1e-9)

    def test_tube_worked_anchor(self):
        # Tube ro = 0.05, ri = 0.04: J near the prep bound 5.796e-6 m4.
        self.assertLess(rel_error(polar_j_tube(0.05, 0.04), J_TUBE_ANCHOR), 1e-9)
        self.assertAlmostEqual(polar_j_tube(0.05, 0.04) / 5.796e-6, 1.0, delta=0.01)

    def test_tube_zero_inner_radius_degeneracy(self):
        # Identity: a tube with ri = 0 is the solid shaft.
        self.assertAlmostEqual(polar_j_tube(0.05, 0.0), polar_j_solid(0.05), places=12)
        # A near-zero-wall tube carries almost no J.
        self.assertGreater(polar_j_tube(0.05, 0.0499), 0.0)
        self.assertLess(polar_j_tube(0.05, 0.0499), polar_j_tube(0.05, 0.04))

    def test_solid_value_errors(self):
        with self.assertRaises(ValueError):
            polar_j_solid(0.0)
        with self.assertRaises(ValueError):
            polar_j_solid(-0.1)

    def test_tube_value_errors(self):
        with self.assertRaises(ValueError):
            polar_j_tube(0.0, 0.01)
        with self.assertRaises(ValueError):
            polar_j_tube(-0.05, 0.01)
        with self.assertRaises(ValueError):
            polar_j_tube(0.05, -0.01)
        with self.assertRaises(ValueError):
            polar_j_tube(0.05, 0.05)
        with self.assertRaises(ValueError):
            polar_j_tube(0.05, 0.06)


class TestSaintVenantJ(unittest.TestCase):
    def test_rectangle_worked_anchor(self):
        # Open rectangle 0.1 x 0.003 m: J = 9.0e-10 m4.
        self.assertAlmostEqual(
            saint_venant_j_rectangle(0.1, 0.003), J_RECT_ANCHOR, places=14)

    def test_rectangle_scales_with_t3(self):
        # Halving the thickness divides J by 8.
        j1 = saint_venant_j_rectangle(0.1, 0.004)
        j2 = saint_venant_j_rectangle(0.1, 0.002)
        self.assertAlmostEqual(j2 / j1, 0.125, delta=1e-12)

    def test_open_channel_sums_rectangles(self):
        # An open channel of two flanges matches the per-rectangle sum.
        elements = [(0.1, 0.002), (0.05, 0.002)]
        expected = (saint_venant_j_rectangle(0.1, 0.002)
                    + saint_venant_j_rectangle(0.05, 0.002))
        self.assertAlmostEqual(saint_venant_j_open(elements), expected, places=15)
        # A single-element section matches the plain rectangle formula.
        self.assertAlmostEqual(
            saint_venant_j_open([(0.1, 0.003)]),
            saint_venant_j_rectangle(0.1, 0.003), places=15)

    def test_open_value_errors(self):
        with self.assertRaises(ValueError):
            saint_venant_j_open([])
        with self.assertRaises(ValueError):
            saint_venant_j_open([(0.0, 0.002)])
        with self.assertRaises(ValueError):
            saint_venant_j_open([(0.1, 0.002), (0.05, -0.002)])


class TestBredt(unittest.TestCase):
    def test_worked_anchor_within_one_percent(self):
        # Box A_m = 0.15 m2, T = 100 kN m: q = 333333 N/m within 1%.
        q = bredt_shear_flow(1e5, 0.15)
        self.assertAlmostEqual(q, Q_BOX_ANCHOR, delta=Q_BOX_ANCHOR * 1e-9)
        self.assertAlmostEqual(q / 333333.0, 1.0, delta=0.01)

    def test_doubling_T_and_zero_T(self):
        # Doubling T doubles q; zero torque gives zero flow.
        q1 = bredt_shear_flow(1e5, 0.15)
        q2 = bredt_shear_flow(2e5, 0.15)
        self.assertAlmostEqual(q2 / q1, 2.0, places=10)
        self.assertEqual(bredt_shear_flow(0.0, 0.15), 0.0)

    def test_inverse_area_scaling(self):
        # Doubling the enclosed area halves the shear flow.
        q1 = bredt_shear_flow(1e5, 0.15)
        q2 = bredt_shear_flow(1e5, 0.30)
        self.assertAlmostEqual(q2 / q1, 0.5, places=10)

    def test_value_errors(self):
        with self.assertRaises(ValueError):
            bredt_shear_flow(-1.0, 0.15)
        with self.assertRaises(ValueError):
            bredt_shear_flow(1e5, 0.0)
        with self.assertRaises(ValueError):
            bredt_shear_flow(1e5, -0.15)


class TestClosedTwistRate(unittest.TestCase):
    def test_worked_anchor_within_one_percent(self):
        # Box 0.5 x 0.3 m, wall 0.002 m, G = 27e9 Pa, T = 100 kN m.
        twist = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3], [0.002] * 4)
        self.assertAlmostEqual(twist, TWIST_BOX_ANCHOR, delta=TWIST_BOX_ANCHOR * 1e-9)
        self.assertAlmostEqual(twist / 0.03292, 1.0, delta=0.01)

    def test_bredt_uniform_wall_identity(self):
        # Uniform-wall identity: the closed twist rate equals the Bredt
        # relation q / (2 A_m G) times the closed integral of ds / t.
        q = bredt_shear_flow(1e5, 0.15)
        bredt_twist = q / (2.0 * 0.15 * 27e9) * (1.6 / 0.002)
        twist = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3], [0.002] * 4)
        self.assertAlmostEqual(twist, bredt_twist, places=12)

    def test_doubling_T_doubles_twist_rate(self):
        t1 = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3], [0.002] * 4)
        t2 = closed_twist_rate(2e5, 27e9, [0.5, 0.3, 0.5, 0.3], [0.002] * 4)
        self.assertAlmostEqual(t2 / t1, 2.0, places=10)

    def test_zero_T_zero_twist(self):
        self.assertEqual(
            closed_twist_rate(0.0, 27e9, [0.5, 0.3, 0.5, 0.3], [0.002] * 4), 0.0)

    def test_auto_am_rectangular_outline_matches_explicit(self):
        # A_m omitted on a (a, b, a, b) outline is computed as a * b.
        explicit = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3],
                                     [0.002] * 4, A_m=0.15)
        automatic = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3],
                                      [0.002] * 4, A_m=None)
        self.assertAlmostEqual(automatic, explicit, places=12)

    def test_thinner_wall_increases_twist(self):
        # Weakening one side of the box raises the twist rate.
        uniform = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3], [0.002] * 4)
        weakened = closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3],
                                     [0.001, 0.002, 0.002, 0.002])
        self.assertGreater(weakened, uniform)

    def test_value_errors(self):
        sides = [0.5, 0.3, 0.5, 0.3]
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 0.0, sides, [0.002] * 4)
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, -27e9, sides, [0.002] * 4)
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 27e9, sides, [0.002, 0.002])
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 27e9, [], [])
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3], [0.0, 0.002, 0.002, 0.002])
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 27e9, [0.0, 0.3, 0.5, 0.3], [0.002] * 4)
        with self.assertRaises(ValueError):
            closed_twist_rate(-1e5, 27e9, sides, [0.002] * 4)
        # Non-rectangular outline without an explicit A_m is rejected.
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.4, 0.3], [0.002] * 4)
        with self.assertRaises(ValueError):
            closed_twist_rate(1e5, 27e9, sides, [0.002] * 4, A_m=0.0)


class TestMultiCell(unittest.TestCase):
    def test_worked_anchors_within_one_percent(self):
        # Two-cell box: A1 = 0.06, A2 = 0.12, S1 = 350, S2 = 550,
        # S12 = 150, G = 27e9 Pa, T = 50 kN m.
        res = multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        self.assertAlmostEqual(res["q1"], Q1_ANCHOR, delta=abs(Q1_ANCHOR) * 1e-9)
        self.assertAlmostEqual(res["q2"], Q2_ANCHOR, delta=abs(Q2_ANCHOR) * 1e-9)
        self.assertAlmostEqual(res["q1"] / 126263.0, 1.0, delta=0.01)
        self.assertAlmostEqual(res["q2"] / 145202.0, 1.0, delta=0.01)

    def test_torque_balance_reconstructs_T(self):
        # 2 A1 q1 + 2 A2 q2 must recover the applied 50000 N m.
        res = multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        rebuilt = 2.0 * 0.06 * res["q1"] + 2.0 * 0.12 * res["q2"]
        self.assertAlmostEqual(rebuilt, 5e4, places=6)

    def test_twist_compatibility_agrees(self):
        # Both cell twist computations must agree within 1e-6.
        res = multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        q1, q2 = res["q1"], res["q2"]
        t1 = (q1 * (350.0 + 150.0) - q2 * 150.0) / (2.0 * 0.06 * 27e9)
        t2 = (q2 * (550.0 + 150.0) - q1 * 150.0) / (2.0 * 0.12 * 27e9)
        self.assertLess(abs(t1 - t2), 1e-6)
        self.assertAlmostEqual(res["twist_rate"], 0.5 * (t1 + t2), places=12)

    def test_twist_anchor_within_one_percent(self):
        res = multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        self.assertAlmostEqual(res["twist_rate"], TWIST_TWOCELL_ANCHOR,
                               delta=abs(TWIST_TWOCELL_ANCHOR) * 1e-9)
        self.assertAlmostEqual(res["twist_rate"] / 0.012763, 1.0, delta=0.01)

    def test_symmetric_cells_degenerate_to_single_cell(self):
        # Equal cells and equal wall paths give q1 = q2 = T / (4 A), the
        # single-cell value for the combined 2 A section, and the twist of
        # the equivalent single cell with outer integral 2 S.
        A, S, S12 = 0.09, 400.0, 150.0
        res = multi_cell_shear_flow(5e4, [A, A], [S, S], S12, 27e9)
        self.assertAlmostEqual(res["q1"], res["q2"], places=10)
        self.assertAlmostEqual(res["q1"], 5e4 / (4.0 * A), places=10)
        single_twist = 5e4 * S / (8.0 * A ** 2 * 27e9)
        self.assertAlmostEqual(res["twist_rate"], single_twist, places=10)

    def test_dict_keys_exact(self):
        res = multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        self.assertEqual(sorted(res.keys()), ["q1", "q2", "twist_rate"])

    def test_determinism_repeat_calls(self):
        args = (5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        first = multi_cell_shear_flow(*args)
        second = multi_cell_shear_flow(*args)
        self.assertEqual(first, second)
        self.assertAlmostEqual(closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3],
                                                 [0.002] * 4),
                               closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3],
                                                 [0.002] * 4), places=15)

    def test_value_errors(self):
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(-5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 27e9)
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 150.0, 0.0)
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(5e4, [0.06], [350.0, 550.0], 150.0, 27e9)
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(5e4, [0.0, 0.12], [350.0, 550.0], 150.0, 27e9)
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, -550.0], 150.0, 27e9)
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], 0.0, 27e9)
        with self.assertRaises(ValueError):
            multi_cell_shear_flow(5e4, [0.06, 0.12], [350.0, 550.0], [150.0, 40.0], 27e9)


class TestMargin(unittest.TestCase):
    def test_worked_anchor(self):
        # tau = 1.667e8 Pa against 2.0e8 Pa gives margin 0.2.
        self.assertAlmostEqual(torsion_margin(TAU_BOX_ANCHOR, 2.0e8),
                               MARGIN_BOX_ANCHOR, places=10)

    def test_sign_behavior(self):
        # Margin is 0 at the allowable, positive below, negative above.
        self.assertAlmostEqual(torsion_margin(2.0e8, 2.0e8), 0.0, places=12)
        self.assertGreater(torsion_margin(1.0e8, 2.0e8), 0.0)
        self.assertLess(torsion_margin(3.0e8, 2.0e8), 0.0)
        self.assertAlmostEqual(torsion_margin(1.0e8, 2.0e8), 1.0, places=12)
        self.assertAlmostEqual(torsion_margin(4.0e8, 2.0e8), -0.5, places=12)

    def test_margin_decreases_as_stress_increases(self):
        # Raising the running shear stress erodes the margin.
        low = torsion_margin(1.5e8, 2.0e8)
        high = torsion_margin(3.0e8, 2.0e8)
        self.assertGreater(low, high)
        # Doubling T doubles tau for a fixed section, so margin falls.
        q1 = bredt_shear_flow(1e5, 0.15)
        q2 = bredt_shear_flow(2e5, 0.15)
        m1 = torsion_margin(q1 / 0.002, 2.0e8)
        m2 = torsion_margin(q2 / 0.002, 2.0e8)
        self.assertGreater(m1, m2)

    def test_value_errors(self):
        with self.assertRaises(ValueError):
            torsion_margin(0.0, 2.0e8)
        with self.assertRaises(ValueError):
            torsion_margin(-1.0e8, 2.0e8)
        with self.assertRaises(ValueError):
            torsion_margin(1.0e8, 0.0)
        with self.assertRaises(ValueError):
            torsion_margin(1.0e8, -2.0e8)


if __name__ == "__main__":
    unittest.main()
