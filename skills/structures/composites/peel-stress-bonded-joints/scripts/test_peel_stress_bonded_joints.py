"""Offline contract test for peel_stress_bonded_joints_logic.

Runs with the stdlib only: python3 test_peel_stress_bonded_joints.py
Covers the peel-stress-bonded-joints worked example anchors from the
leaf spec, the Goland-Reissner bending moment factor traverse
(workflow step 2), the peel decay coefficient traverse (workflow step
3), the peel stress at the overlap end resolved from the edge moment
and the adhesive Winkler-foundation beam model (workflow step 4), the
peel margin rating against the peel strength allowable (workflow step
5), boundary behaviour, ValueError rejection of non-physical inputs
and round-trip identities. Deterministic, no network, exits 0.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peel_stress_bonded_joints_logic as ps

# Worked example constants: aluminum adherends E 70 GPa, nu 0.33,
# t 1.6 mm; epoxy adhesive E_a 1.5 GPa, t_a 0.25 mm; overlap 25 mm
# (half length c 12.5 mm); load P 4000 N over a 25 mm width gives
# P_pw 1.6e5 N/m.
E_ALU = 70e9
NU = 0.33
T_ADHEREND = 1.6e-3
E_ADHESIVE = 1.5e9
T_ADHESIVE = 0.25e-3
HALF_LENGTH = 0.0125
P_PW = 1.6e5
K_WORKED = 0.518201
PEEL_WORKED = 31.3768e6
ALLOW_35 = 35e6
ALLOW_25 = 25e6


def peel_at(load_per_unit_width):
    """Peel dict for a load at the worked-example geometry."""
    k = ps.bending_moment_factor(load_per_unit_width, T_ADHEREND, E_ALU,
                                 NU, HALF_LENGTH)
    return ps.peel_stress_at_overlap_end(load_per_unit_width, T_ADHEREND,
                                         E_ALU, NU, E_ADHESIVE,
                                         T_ADHESIVE, k)


class TestBendingMomentFactor(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the Goland-Reissner bending
    moment factor traverse from the load per unit width, the adherend
    thickness, modulus and Poisson ratio, and the overlap half length.
    """

    def test_worked_example_moment_factor_anchor(self):
        # Workflow step 2 anchor: k = 0.518201 at the 100 MPa average
        # adherend stress level of the worked example.
        k = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)
        self.assertAlmostEqual(k, K_WORKED, delta=1e-5)

    def test_no_bending_limit_at_zero_load(self):
        # Workflow step 2 identity: k goes to 1 as the load goes to 0,
        # the no-bending limit of the moment factor traverse.
        k = ps.bending_moment_factor(0.0, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)
        self.assertEqual(k, 1.0)

    def test_no_bending_limit_near_zero_load_anchor(self):
        # Workflow step 2 anchor: a tiny load leaves k at 0.999924,
        # still at the no-bending limit.
        k = ps.bending_moment_factor(1e-3, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)
        self.assertAlmostEqual(k, 0.999924, delta=1e-5)

    def test_long_overlap_classical_floor_anchor(self):
        # Workflow step 2 floor: at a very long overlap half length of
        # 1 m the moment factor approaches the classical 0.261 limit.
        k = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU, 1.0)
        self.assertAlmostEqual(k, 0.261204, delta=1e-5)

    def test_monotone_decreasing_in_overlap_half_length(self):
        # Workflow step 2 traverse: k is monotone decreasing in the
        # overlap half length, 0.928308 at 1 mm down to 0.287155 at
        # 50 mm (the 10 mm station sits between at 0.570182).
        k_1mm = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                         0.001)
        k_10mm = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                          0.01)
        k_50mm = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                          0.05)
        self.assertAlmostEqual(k_1mm, 0.928308, delta=1e-5)
        self.assertAlmostEqual(k_10mm, 0.570182, delta=1e-5)
        self.assertAlmostEqual(k_50mm, 0.287155, delta=1e-5)
        self.assertGreater(k_1mm, k_10mm)
        self.assertGreater(k_10mm, k_50mm)

    def test_monotone_decreasing_in_load_per_unit_width(self):
        # Workflow step 2 traverse: k is monotone decreasing in the
        # load per unit width, 0.805922 at 10 N/mm, 0.598868 at the
        # 80 N/mm level, 0.518201 at 160 N/mm and 0.417725 at 400
        # N/mm.
        k_10 = ps.bending_moment_factor(1e4, T_ADHEREND, E_ALU, NU,
                                        HALF_LENGTH)
        k_80 = ps.bending_moment_factor(8e4, T_ADHEREND, E_ALU, NU,
                                        HALF_LENGTH)
        k_160 = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                         HALF_LENGTH)
        k_400 = ps.bending_moment_factor(4e5, T_ADHEREND, E_ALU, NU,
                                         HALF_LENGTH)
        self.assertAlmostEqual(k_10, 0.805922, delta=1e-5)
        self.assertAlmostEqual(k_80, 0.598868, delta=1e-5)
        self.assertAlmostEqual(k_160, K_WORKED, delta=1e-5)
        self.assertAlmostEqual(k_400, 0.417725, delta=1e-5)
        self.assertGreater(k_10, k_80)
        self.assertGreater(k_80, k_160)
        self.assertGreater(k_160, k_400)

    def test_negative_load_rejected(self):
        # Workflow step 2 rejects a negative load per unit width.
        with self.assertRaises(ValueError):
            ps.bending_moment_factor(-1.0, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)

    def test_zero_adherend_thickness_or_modulus_rejected(self):
        # Workflow step 2 rejects non-positive adherend geometry and
        # stiffness inputs.
        with self.assertRaises(ValueError):
            ps.bending_moment_factor(P_PW, 0.0, E_ALU, NU, HALF_LENGTH)
        with self.assertRaises(ValueError):
            ps.bending_moment_factor(P_PW, T_ADHEREND, 0.0, NU,
                                     HALF_LENGTH)

    def test_zero_overlap_half_length_rejected(self):
        # Workflow step 2 rejects a zero overlap half length.
        with self.assertRaises(ValueError):
            ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU, 0.0)

    def test_poisson_ratio_out_of_range_rejected(self):
        # Workflow step 2 rejects Poisson ratios outside (-1, 0.5);
        # the elastic floor 0.5 and below -1 are non-physical for the
        # moment factor traverse.
        for nu in (0.6, 0.5, -1.0, -2.0):
            with self.assertRaises(ValueError):
                ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, nu,
                                         HALF_LENGTH)
        k = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, -0.4,
                                     HALF_LENGTH)
        self.assertGreater(k, 0.0)
        self.assertLessEqual(k, 1.0)


class TestPeelDecayCoefficient(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the peel decay coefficient
    traverse that sets the exponential decay of the peel stress away
    from the overlap end.
    """

    def test_worked_example_decay_anchor(self):
        # Workflow step 3 anchor: beta = 566.947 1/m for the epoxy
        # adhesive on the aluminum adherends.
        beta = ps.peel_decay_coefficient(E_ADHESIVE, T_ADHESIVE, E_ALU,
                                         T_ADHEREND)
        self.assertAlmostEqual(beta, 566.947, delta=0.01)

    def test_decay_faster_with_stiffer_adhesive(self):
        # Workflow step 3: a stiffer adhesive raises the peel decay
        # coefficient, so the peel decays over a shorter length.
        beta = ps.peel_decay_coefficient(E_ADHESIVE, T_ADHESIVE, E_ALU,
                                         T_ADHEREND)
        beta_stiff = ps.peel_decay_coefficient(2.0 * E_ADHESIVE,
                                               T_ADHESIVE, E_ALU,
                                               T_ADHEREND)
        self.assertAlmostEqual(beta_stiff / beta, math.sqrt(2.0),
                               delta=1e-9)
        self.assertGreater(beta_stiff, beta)

    def test_decay_slower_with_thicker_bondline_or_stiffer_adherend(self):
        # Workflow step 3: doubling the adhesive thickness or the
        # adherend modulus slows the exponential peel decay.
        beta = ps.peel_decay_coefficient(E_ADHESIVE, T_ADHESIVE, E_ALU,
                                         T_ADHEREND)
        beta_thick = ps.peel_decay_coefficient(E_ADHESIVE,
                                               2.0 * T_ADHESIVE, E_ALU,
                                               T_ADHEREND)
        beta_stiff_adherend = ps.peel_decay_coefficient(E_ADHESIVE,
                                                        T_ADHESIVE,
                                                        2.0 * E_ALU,
                                                        T_ADHEREND)
        self.assertLess(beta_thick, beta)
        self.assertLess(beta_stiff_adherend, beta)

    def test_nonpositive_inputs_rejected(self):
        # Workflow step 3 rejects non-positive adhesive or adherend
        # moduli and thicknesses.
        with self.assertRaises(ValueError):
            ps.peel_decay_coefficient(0.0, T_ADHESIVE, E_ALU,
                                      T_ADHEREND)
        with self.assertRaises(ValueError):
            ps.peel_decay_coefficient(E_ADHESIVE, 0.0, E_ALU,
                                      T_ADHEREND)
        with self.assertRaises(ValueError):
            ps.peel_decay_coefficient(E_ADHESIVE, T_ADHESIVE, 0.0,
                                      T_ADHEREND)
        with self.assertRaises(ValueError):
            ps.peel_decay_coefficient(E_ADHESIVE, T_ADHESIVE, E_ALU,
                                      0.0)


class TestPeelStressAtOverlapEnd(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the peel stress at the overlap
    end resolved from the edge moment M0 = k P_pw t / 2 and the
    adhesive Winkler-foundation beam model of the adherend.
    """

    def test_worked_example_peel_stress_anchor(self):
        # Workflow step 4 anchor: 31.3768 MPa peel stress at the
        # overlap end for the 100 MPa average adherend stress case.
        res = peel_at(P_PW)
        self.assertAlmostEqual(res["peel_stress"] / 1e6, 31.3768,
                               delta=1e-3)

    def test_worked_example_edge_moment_anchor(self):
        # Workflow step 4 anchor: the edge moment is 66.3298 N m/m
        # from the moment factor 0.518201 and the load 160 N/mm.
        res = peel_at(P_PW)
        self.assertAlmostEqual(res["edge_moment"], 66.3298, delta=1e-3)

    def test_worked_example_lambda_anchor(self):
        # Workflow step 4 anchor: lambda is 486.335 1/m from the
        # adhesive Winkler-foundation beam stiffness.
        res = peel_at(P_PW)
        self.assertAlmostEqual(res["lambda"], 486.335, delta=0.01)

    def test_dict_keys_exact(self):
        # Workflow step 4 returns exactly the peel_stress, edge_moment
        # and lambda keys.
        res = peel_at(P_PW)
        self.assertEqual(sorted(res.keys()),
                         ["edge_moment", "lambda", "peel_stress"])

    def test_lower_load_case_50_mpa_anchor(self):
        # Workflow step 4 anchor at the 50 MPa average adherend stress
        # level: peel 18.1306 MPa, edge moment 38.3275 N m/m.
        res = peel_at(8e4)
        self.assertAlmostEqual(res["peel_stress"] / 1e6, 18.1306,
                               delta=1e-3)
        self.assertAlmostEqual(res["edge_moment"], 38.3275, delta=1e-3)

    def test_peel_stress_monotone_in_load(self):
        # Workflow step 4 traverse: the peel stress grows with the
        # load per unit width, 18.1306, 31.3768 and 63.23 MPa at 80,
        # 160 and 400 N/mm.
        peel_80 = peel_at(8e4)["peel_stress"]
        peel_160 = peel_at(P_PW)["peel_stress"]
        peel_400 = peel_at(4e5)["peel_stress"]
        self.assertAlmostEqual(peel_400 / 1e6, 63.23, delta=0.01)
        self.assertLess(peel_80, peel_160)
        self.assertLess(peel_160, peel_400)

    def test_doubled_adhesive_modulus_raises_peel_by_sqrt2(self):
        # Workflow step 4 sensitivity: doubling the adhesive modulus
        # raises the peel stress by about sqrt(2) to 44.37 MPa.
        k = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)
        base = ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU,
                                             NU, E_ADHESIVE,
                                             T_ADHESIVE, k)
        stiff = ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU,
                                              NU, 2.0 * E_ADHESIVE,
                                              T_ADHESIVE, k)
        self.assertAlmostEqual(stiff["peel_stress"] / 1e6, 44.37,
                               delta=0.02)
        self.assertAlmostEqual(stiff["peel_stress"]
                               / base["peel_stress"], math.sqrt(2.0),
                               delta=1e-9)

    def test_doubled_adhesive_thickness_lowers_peel_by_sqrt2(self):
        # Workflow step 4 sensitivity: doubling the adhesive thickness
        # lowers the peel stress to 22.19 MPa, again by the sqrt(2)
        # factor.
        k = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)
        base = ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU,
                                             NU, E_ADHESIVE,
                                             T_ADHESIVE, k)
        thick = ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU,
                                              NU, E_ADHESIVE,
                                              2.0 * T_ADHESIVE, k)
        self.assertAlmostEqual(thick["peel_stress"] / 1e6, 22.19,
                               delta=0.02)
        self.assertAlmostEqual(base["peel_stress"]
                               / thick["peel_stress"], math.sqrt(2.0),
                               delta=1e-9)

    def test_negative_load_rejected(self):
        # Workflow step 4 rejects a negative load per unit width.
        with self.assertRaises(ValueError):
            ps.peel_stress_at_overlap_end(-1.0, T_ADHEREND, E_ALU, NU,
                                          E_ADHESIVE, T_ADHESIVE,
                                          K_WORKED)

    def test_zero_adhesive_modulus_rejected(self):
        # Workflow step 4 rejects a zero adhesive modulus.
        with self.assertRaises(ValueError):
            ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU, NU,
                                          0.0, T_ADHESIVE, K_WORKED)

    def test_zero_adhesive_thickness_rejected(self):
        # Workflow step 4 rejects a zero adhesive thickness.
        with self.assertRaises(ValueError):
            ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU, NU,
                                          E_ADHESIVE, 0.0, K_WORKED)

    def test_zero_adherend_thickness_or_modulus_rejected(self):
        # Workflow step 4 rejects non-positive adherend inputs.
        with self.assertRaises(ValueError):
            ps.peel_stress_at_overlap_end(P_PW, 0.0, E_ALU, NU,
                                          E_ADHESIVE, T_ADHESIVE,
                                          K_WORKED)
        with self.assertRaises(ValueError):
            ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, 0.0, NU,
                                          E_ADHESIVE, T_ADHESIVE,
                                          K_WORKED)

    def test_poisson_ratio_out_of_range_rejected(self):
        # Workflow step 4 rejects Poisson ratios outside (-1, 0.5).
        with self.assertRaises(ValueError):
            ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU, 0.6,
                                          E_ADHESIVE, T_ADHESIVE,
                                          K_WORKED)


class TestPeelMargin(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the peel margin rating against
    the peel strength allowable that gates the peel-critical joint
    check.
    """

    def test_worked_example_margin_35mpa(self):
        # Workflow step 5 anchor: the 35 MPa allowable gives a peel
        # margin of 1.11547 against the 31.3768 MPa peel stress.
        margin = ps.peel_margin(PEEL_WORKED, ALLOW_35)
        self.assertAlmostEqual(margin, 1.11547, delta=1e-3)

    def test_worked_example_margin_25mpa_below_one(self):
        # Workflow step 5 anchor: the 25 MPa allowable gives a peel
        # margin of 0.796767, below one, so the joint fails the
        # peel-critical check.
        margin = ps.peel_margin(PEEL_WORKED, ALLOW_25)
        self.assertAlmostEqual(margin, 0.796767, delta=1e-3)
        self.assertLess(margin, 1.0)

    def test_equal_stress_and_allowable_margin_one(self):
        # Workflow step 5 boundary: a peel stress equal to the
        # allowable gives a margin of exactly one.
        margin = ps.peel_margin(ALLOW_35, ALLOW_35)
        self.assertEqual(margin, 1.0)

    def test_nonpositive_stress_or_allowable_rejected(self):
        # Workflow step 5 rejects a non-positive peel stress or peel
        # strength allowable.
        with self.assertRaises(ValueError):
            ps.peel_margin(0.0, ALLOW_35)
        with self.assertRaises(ValueError):
            ps.peel_margin(PEEL_WORKED, 0.0)
        with self.assertRaises(ValueError):
            ps.peel_margin(PEEL_WORKED, -1.0)


class TestDeterminismAndIdentity(unittest.TestCase):
    """Determinism and round-trip identities across the SKILL.md
    workflow steps.
    """

    def test_repeated_calls_deterministic(self):
        # The peel stress traverse is deterministic: repeated calls
        # with the worked-example inputs return identical results.
        first = peel_at(P_PW)
        second = peel_at(P_PW)
        self.assertEqual(first["peel_stress"], second["peel_stress"])
        self.assertEqual(first["edge_moment"], second["edge_moment"])
        self.assertEqual(first["lambda"], second["lambda"])

    def test_edge_moment_scales_with_load_at_fixed_moment_factor(self):
        # Workflow step 4 identity: M0 = k P_pw t / 2 is linear in
        # the load per unit width at a fixed moment factor.
        k = ps.bending_moment_factor(P_PW, T_ADHEREND, E_ALU, NU,
                                     HALF_LENGTH)
        low = ps.peel_stress_at_overlap_end(P_PW, T_ADHEREND, E_ALU,
                                            NU, E_ADHESIVE,
                                            T_ADHESIVE, k)
        high = ps.peel_stress_at_overlap_end(2.0 * P_PW, T_ADHEREND,
                                             E_ALU, NU, E_ADHESIVE,
                                             T_ADHESIVE, k)
        self.assertAlmostEqual(high["edge_moment"],
                               2.0 * low["edge_moment"], delta=1e-9)

    def test_peel_margin_round_trip_recovers_allowable(self):
        # Workflow step 5 round trip: margin times the peel stress
        # recovers the peel strength allowable.
        margin = ps.peel_margin(PEEL_WORKED, ALLOW_35)
        self.assertAlmostEqual(margin * PEEL_WORKED, ALLOW_35,
                               delta=1e-3)


if __name__ == "__main__":
    unittest.main()
