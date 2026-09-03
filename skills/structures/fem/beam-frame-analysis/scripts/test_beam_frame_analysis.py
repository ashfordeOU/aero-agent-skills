"""Contract test for beam-frame-analysis (wave-28, structures/fem).

Offline, deterministic, stdlib only. Runs via:
    python3 scripts/test_beam_frame_analysis.py

Worked-example anchors (wave-28 spec, exact module values recorded):
  Cantilever E = 70 GPa, A = 0.01 m^2, I = 4e-6 m^4, L = 2 m, P = -1000 N:
    tip v  = -9.523809523809525e-03 m   (closed form P L^3/(3 E I))
    tip th = +7.142857142857143e-03 rad (closed form P L^2/(2 E I))
    reactions R_v0 = +1000 N, R_m0 = -2000 N m
  Simply supported beam, two elements of L = 1.5 m, central -2000 N:
    midspan v = -4.0178571428571425e-03 m (closed form P L^3/(48 E I))
    reactions +1000 N at each support
  Portal frame h = 3 m, span 4 m, E = 200 GPa, A = 0.02, I = 8e-5,
    lateral +5000 N at the top-left corner:
    u_top_left = 5.452772999802004e-04 m  (recorded module value)
    beam I x10  -> u_top_left = 3.767451011463694e-04 m (smaller)
    sum of horizontal reactions = -5000 N, vertical sum = 0,
    equilibrium_ok True.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beam_frame_analysis_logic as bfa

E_AL = 70e9
A_BAR = 0.01
I_BAR = 4e-6
E_STEEL = 200e9
A_PORTAL = 0.02
I_PORTAL = 8e-5


def cantilever_fixture():
    """Spec worked example 1: one element, fixed root, downward tip load."""
    nodes = [(0.0, 0.0), (2.0, 0.0)]
    elements = [{"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR}]
    supports = [(0, ("u", "v", "theta"))]
    loads = {(1, "v"): -1000.0}
    return nodes, elements, supports, loads


def ss_beam_fixture():
    """Spec worked example 2: two elements, pin and roller, central load."""
    nodes = [(0.0, 0.0), (1.5, 0.0), (3.0, 0.0)]
    elements = [
        {"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR},
        {"i": 1, "j": 2, "E": E_AL, "A": A_BAR, "I": I_BAR},
    ]
    supports = [(0, ("u", "v")), (2, ("v",))]
    loads = {(1, "v"): -2000.0}
    return nodes, elements, supports, loads


def portal_fixture(beam_inertia=None):
    """Spec worked example 3: rigid-jointed portal, lateral corner load."""
    nodes = [(0.0, 0.0), (4.0, 0.0), (0.0, 3.0), (4.0, 3.0)]
    if beam_inertia is None:
        beam_inertia = I_PORTAL
    elements = [
        {"i": 0, "j": 2, "E": E_STEEL, "A": A_PORTAL, "I": I_PORTAL},
        {"i": 1, "j": 3, "E": E_STEEL, "A": A_PORTAL, "I": I_PORTAL},
        {"i": 2, "j": 3, "E": E_STEEL, "A": A_PORTAL, "I": beam_inertia},
    ]
    supports = [(0, ("u", "v", "theta")), (1, ("u", "v", "theta"))]
    loads = {(2, "u"): 5000.0}
    return nodes, elements, supports, loads


def sandwich(t, k):
    """Return T^T * k * T for two 6x6 lists of lists."""
    n = 6
    temp = [[0.0] * n for _ in range(n)]
    for r in range(n):
        for col in range(n):
            temp[r][col] = sum(t[m][r] * k[m][col] for m in range(n))
    out = [[0.0] * n for _ in range(n)]
    for r in range(n):
        for col in range(n):
            out[r][col] = sum(temp[r][m] * t[m][col] for m in range(n))
    return out


class BeamFrameLocalTests(unittest.TestCase):
    """Element stiffness and rotation matrix properties."""

    def test_element_stiffness_local_symmetric(self):
        k = bfa.element_stiffness_local(E_AL, A_BAR, I_BAR, 2.0)
        for r in range(6):
            for col in range(6):
                self.assertAlmostEqual(k[r][col], k[col][r], delta=1e-9)

    def test_element_stiffness_local_known_terms(self):
        k = bfa.element_stiffness_local(E_AL, A_BAR, I_BAR, 2.0)
        self.assertAlmostEqual(k[1][1], 12.0 * E_AL * I_BAR / 8.0, delta=1e-6)
        self.assertAlmostEqual(k[4][4], 12.0 * E_AL * I_BAR / 8.0, delta=1e-6)
        self.assertAlmostEqual(k[2][2], 4.0 * E_AL * I_BAR / 2.0, delta=1e-6)
        self.assertAlmostEqual(k[5][5], 4.0 * E_AL * I_BAR / 2.0, delta=1e-6)
        self.assertAlmostEqual(k[1][4], -12.0 * E_AL * I_BAR / 8.0, delta=1e-6)
        self.assertAlmostEqual(k[2][5], 2.0 * E_AL * I_BAR / 2.0, delta=1e-6)
        self.assertAlmostEqual(k[1][2], -6.0 * E_AL * I_BAR / 4.0, delta=1e-6)
        self.assertAlmostEqual(k[0][0], E_AL * A_BAR / 2.0, delta=1e-6)
        self.assertAlmostEqual(k[0][3], -E_AL * A_BAR / 2.0, delta=1e-6)

    def test_element_stiffness_local_rejects_nonphysical(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                bfa.element_stiffness_local(bad, A_BAR, I_BAR, 2.0)
            with self.assertRaises(ValueError):
                bfa.element_stiffness_local(E_AL, bad, I_BAR, 2.0)
            with self.assertRaises(ValueError):
                bfa.element_stiffness_local(E_AL, A_BAR, bad, 2.0)
            with self.assertRaises(ValueError):
                bfa.element_stiffness_local(E_AL, A_BAR, I_BAR, bad)

    def test_rotation_matrix_orthogonal(self):
        t = bfa.rotation_matrix(0.7)
        for r in range(6):
            for col in range(6):
                expected = 1.0 if r == col else 0.0
                prod = sum(t[r][m] * t[col][m] for m in range(6))
                self.assertAlmostEqual(prod, expected, delta=1e-12)

    def test_rotation_matrix_zero_angle_identity(self):
        t = bfa.rotation_matrix(0.0)
        for r in range(6):
            for col in range(6):
                self.assertAlmostEqual(t[r][col], 1.0 if r == col else 0.0, delta=1e-15)

    def test_rotation_matrix_block_form(self):
        angle = math.pi / 4.0
        c = math.cos(angle)
        s = math.sin(angle)
        t = bfa.rotation_matrix(angle)
        block = ((c, s, 0.0), (-s, c, 0.0), (0.0, 0.0, 1.0))
        for r in range(3):
            for col in range(3):
                self.assertAlmostEqual(t[r][col], block[r][col], delta=1e-15)
                self.assertAlmostEqual(t[r + 3][col + 3], block[r][col], delta=1e-15)
                self.assertAlmostEqual(t[r][col + 3], 0.0, delta=1e-15)

    def test_global_stiffness_horizontal_member_equals_local(self):
        kg = bfa.element_stiffness_global(E_AL, A_BAR, I_BAR, 2.0, 0.0)
        kl = bfa.element_stiffness_local(E_AL, A_BAR, I_BAR, 2.0)
        for r in range(6):
            for col in range(6):
                self.assertAlmostEqual(kg[r][col], kl[r][col], delta=1e-9)

    def test_rotated_axial_block_matches_truss_form(self):
        # The axial contribution of a member at 45 deg must rotate into
        # the EA/L * [[c^2, cs], [cs, s^2]] truss form on the u/v dofs.
        angle = math.pi / 4.0
        c = math.cos(angle)
        s = math.sin(angle)
        length = 2.0
        ka = E_AL * A_BAR / length
        axial = [[0.0] * 6 for _ in range(6)]
        axial[0][0] = ka
        axial[0][3] = -ka
        axial[3][0] = -ka
        axial[3][3] = ka
        rotated = sandwich(bfa.rotation_matrix(angle), axial)
        truss = (
            (ka * c * c, ka * c * s, -ka * c * c, -ka * c * s),
            (ka * c * s, ka * s * s, -ka * c * s, -ka * s * s),
            (-ka * c * c, -ka * c * s, ka * c * c, ka * c * s),
            (-ka * c * s, -ka * s * s, ka * c * s, ka * s * s),
        )
        rows = (0, 1, 3, 4)
        for r, gr in enumerate(rows):
            for col, gcol in enumerate(rows):
                self.assertAlmostEqual(rotated[gr][gcol], truss[r][col], delta=1e-6)
            for gcol in (2, 5):
                self.assertAlmostEqual(rotated[gr][gcol], 0.0, delta=1e-9)

    def test_axial_bar_tension_recovery(self):
        # Pure axial bar: a +1000 N pull at the free end stretches it by
        # P L / (E A) and the recovered end actions show tension.
        nodes = [(0.0, 0.0), (2.0, 0.0)]
        elements = [{"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR}]
        supports = [(0, ("u", "v", "theta")), (1, ("v", "theta"))]
        loads = {(1, "u"): 1000.0}
        result = bfa.solve_frame(nodes, elements, supports, loads)
        self.assertAlmostEqual(
            result["displacements"][(1, "u")], 1000.0 * 2.0 / (E_AL * A_BAR), delta=1e-12
        )
        actions = result["member_actions"][0]
        self.assertAlmostEqual(actions["n1"], -1000.0, delta=1e-6)
        self.assertAlmostEqual(actions["n2"], 1000.0, delta=1e-6)
        self.assertAlmostEqual(actions["v1"], 0.0, delta=1e-9)
        self.assertAlmostEqual(actions["m2"], 0.0, delta=1e-9)
        self.assertTrue(result["equilibrium_ok"])


class BeamCantileverTests(unittest.TestCase):
    """Spec worked example 1: cantilever closed forms and reactions."""

    def _solve(self):
        return bfa.solve_frame(*cantilever_fixture())

    def test_cantilever_tip_deflection_closed_form(self):
        result = self._solve()
        tip = result["displacements"][(1, "v")]
        self.assertAlmostEqual(abs(tip), 8000.0 / 840000.0, delta=1e-9)
        self.assertAlmostEqual(tip, -8000.0 / 840000.0, delta=1e-9)

    def test_cantilever_tip_rotation_closed_form(self):
        result = self._solve()
        rotation = result["displacements"][(1, "theta")]
        self.assertAlmostEqual(abs(rotation), 4000.0 / 560000.0, delta=1e-9)
        self.assertAlmostEqual(rotation, 4000.0 / 560000.0, delta=1e-9)

    def test_cantilever_reactions(self):
        result = self._solve()
        reactions = result["reactions"]
        self.assertAlmostEqual(reactions[(0, "u")], 0.0, delta=1e-6)
        self.assertAlmostEqual(reactions[(0, "v")], 1000.0, delta=1e-6)
        self.assertAlmostEqual(reactions[(0, "theta")], -2000.0, delta=1e-6)

    def test_cantilever_member_end_actions(self):
        actions = self._solve()["member_actions"][0]
        self.assertAlmostEqual(actions["n1"], 0.0, delta=1e-9)
        self.assertAlmostEqual(actions["v1"], 1000.0, delta=1e-6)
        self.assertAlmostEqual(actions["m1"], -2000.0, delta=1e-6)
        self.assertAlmostEqual(actions["n2"], 0.0, delta=1e-9)
        self.assertAlmostEqual(actions["v2"], -1000.0, delta=1e-6)
        self.assertAlmostEqual(actions["m2"], 0.0, delta=1e-6)

    def test_cantilever_reactions_match_member_end_actions(self):
        result = self._solve()
        reactions = result["reactions"]
        actions = result["member_actions"][0]
        self.assertAlmostEqual(reactions[(0, "v")], actions["v1"], delta=1e-9)
        self.assertAlmostEqual(reactions[(0, "theta")], actions["m1"], delta=1e-9)
        self.assertTrue(result["equilibrium_ok"])


class BeamSsTests(unittest.TestCase):
    """Spec worked example 2: simply supported beam closed forms."""

    def _solve(self):
        return bfa.solve_frame(*ss_beam_fixture())

    def test_ss_beam_midspan_deflection_closed_form(self):
        result = self._solve()
        mid = result["displacements"][(1, "v")]
        self.assertAlmostEqual(abs(mid), 54000.0 / 13440000.0, delta=1e-9)
        self.assertAlmostEqual(mid, -54000.0 / 13440000.0, delta=1e-9)

    def test_ss_beam_reactions(self):
        result = self._solve()
        reactions = result["reactions"]
        self.assertAlmostEqual(reactions[(0, "v")], 1000.0, delta=1e-6)
        self.assertAlmostEqual(reactions[(2, "v")], 1000.0, delta=1e-6)
        self.assertAlmostEqual(reactions[(0, "u")], 0.0, delta=1e-6)
        self.assertTrue(result["equilibrium_ok"])

    def test_ss_beam_central_joint_member_action_balance(self):
        result = self._solve()
        first = result["member_actions"][0]
        second = result["member_actions"][1]
        # End actions sum to the applied -2000 N at the loaded joint.
        self.assertAlmostEqual(first["v2"] + second["v1"], -2000.0, delta=1e-6)
        self.assertAlmostEqual(first["m2"] + second["m1"], 0.0, delta=1e-6)
        self.assertAlmostEqual(first["n2"] + second["n1"], 0.0, delta=1e-6)

    def test_ss_beam_pin_and_roller_allow_rotation(self):
        result = self._solve()
        left = result["displacements"][(0, "theta")]
        right = result["displacements"][(2, "theta")]
        # |theta| = P L^2 / (16 E I) with L = 3 m total span, opposite signs.
        self.assertAlmostEqual(abs(left), 2000.0 * 9.0 / (16.0 * E_AL * I_BAR), delta=1e-9)
        self.assertAlmostEqual(left + right, 0.0, delta=1e-12)


class PortalFrameTests(unittest.TestCase):
    """Spec worked example 3: rigid-jointed portal frame equilibrium."""

    U_TOP_LEFT = 0.0005452772999802004
    U_STIFF_BEAM = 0.0003767451011463694

    def _solve(self, beam_inertia=None):
        return bfa.solve_frame(*portal_fixture(beam_inertia))

    def test_portal_equilibrium(self):
        result = self._solve()
        reactions = result["reactions"]
        horizontal = sum(v for (node, name), v in reactions.items() if name == "u")
        self.assertAlmostEqual(horizontal, -5000.0, delta=1e-6)
        self.assertTrue(result["equilibrium_ok"])

    def test_portal_vertical_reactions_balance(self):
        reactions = self._solve()["reactions"]
        vertical = sum(v for (node, name), v in reactions.items() if name == "v")
        self.assertAlmostEqual(vertical, 0.0, delta=1e-6)

    def test_portal_top_displacement_positive_and_bounded(self):
        displacement = self._solve()["displacements"][(2, "u")]
        self.assertGreater(displacement, 0.0)
        self.assertLess(displacement, 0.05)

    def test_portal_recorded_value_regression(self):
        displacement = self._solve()["displacements"][(2, "u")]
        self.assertAlmostEqual(displacement, self.U_TOP_LEFT, delta=1e-15)

    def test_portal_determinism(self):
        first = self._solve()
        second = self._solve()
        for (node, name), value in first["displacements"].items():
            self.assertAlmostEqual(
                value, second["displacements"][(node, name)], delta=1e-12
            )

    def test_portal_stiffer_beam_reduces_displacement(self):
        baseline = self._solve()["displacements"][(2, "u")]
        stiffer = self._solve(beam_inertia=10.0 * I_PORTAL)["displacements"][(2, "u")]
        self.assertAlmostEqual(stiffer, self.U_STIFF_BEAM, delta=1e-15)
        self.assertLess(stiffer, baseline)

    def test_portal_joint_member_actions_balance(self):
        result = self._solve()
        column = result["member_actions"][0]   # foot 0 to top-left joint
        beam = result["member_actions"][2]     # top-left joint to top-right
        # Local (n, v) -> global (u, v): column alpha = pi/2, beam alpha = 0.
        sum_u = -column["v2"] + beam["n1"]
        sum_v = column["n2"] + beam["v1"]
        sum_m = column["m2"] + beam["m1"]
        self.assertAlmostEqual(sum_u, 5000.0, delta=1e-6)
        self.assertAlmostEqual(sum_v, 0.0, delta=1e-6)
        self.assertAlmostEqual(sum_m, 0.0, delta=1e-6)

    def test_portal_foot_reactions_match_member_actions(self):
        result = self._solve()
        actions = result["member_actions"][0]
        reactions = result["reactions"]
        self.assertAlmostEqual(reactions[(0, "u")], -actions["v1"], delta=1e-6)
        self.assertAlmostEqual(reactions[(0, "v")], actions["n1"], delta=1e-6)
        self.assertAlmostEqual(reactions[(0, "theta")], actions["m1"], delta=1e-6)


class SolverTests(unittest.TestCase):
    """Linear solver behavior and rejection of invalid models."""

    def test_gaussian_elimination_two_by_two(self):
        x = bfa.gaussian_elimination([[2.0, 1.0], [1.0, 3.0]], [5.0, 10.0])
        self.assertAlmostEqual(x[0], 1.0, delta=1e-12)
        self.assertAlmostEqual(x[1], 3.0, delta=1e-12)

    def test_gaussian_elimination_requires_row_swap(self):
        x = bfa.gaussian_elimination([[0.0, 1.0], [1.0, 0.0]], [2.0, 3.0])
        self.assertAlmostEqual(x[0], 3.0, delta=1e-12)
        self.assertAlmostEqual(x[1], 2.0, delta=1e-12)

    def test_gaussian_elimination_singular_raises(self):
        with self.assertRaises(ValueError):
            bfa.gaussian_elimination([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])

    def test_solve_free_singular_structure_raises(self):
        nodes = [(0.0, 0.0)]
        elements = []
        with self.assertRaises(ValueError) as caught:
            bfa.solve_frame(nodes, elements, [], {(0, "u"): 1.0})
        self.assertIn("singular structure", str(caught.exception))

    def test_unknown_element_node_raises(self):
        nodes = [(0.0, 0.0), (1.0, 0.0)]
        elements = [{"i": 0, "j": 5, "E": E_AL, "A": A_BAR, "I": I_BAR}]
        with self.assertRaises(ValueError):
            bfa.solve_frame(nodes, elements, [(0, ("u", "v", "theta"))], {(1, "u"): 1.0})

    def test_unknown_support_node_raises(self):
        nodes = [(0.0, 0.0), (1.0, 0.0)]
        elements = [{"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR}]
        with self.assertRaises(ValueError):
            bfa.solve_frame(nodes, elements, [(9, ("u",))], {})

    def test_unknown_load_dof_raises(self):
        nodes = [(0.0, 0.0), (1.0, 0.0)]
        elements = [{"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR}]
        with self.assertRaises(ValueError):
            bfa.solve_frame(nodes, elements, [(0, ("u", "v", "theta"))], {(1, "w"): 1.0})

    def test_duplicate_dof_map_raises(self):
        nodes = [(0.0, 0.0), (1.0, 0.0)]
        elements = [{"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR}]
        bad_map = {(0, "u"): 0, (0, "v"): 0, (0, "theta"): 2, (1, "u"): 3}
        with self.assertRaises(ValueError):
            bfa.assemble(nodes, elements, bad_map)

    def test_unknown_node_index_raises_in_assemble(self):
        nodes = [(0.0, 0.0)]
        elements = [{"i": 0, "j": 1, "E": E_AL, "A": A_BAR, "I": I_BAR}]
        with self.assertRaises(ValueError):
            bfa.assemble(nodes, elements)


if __name__ == "__main__":
    unittest.main()
