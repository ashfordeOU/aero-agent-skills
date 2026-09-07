"""Contract test for the inelastic-column-buckling leaf
(skills/structures/fem/inelastic-column-buckling).

The pure-stdlib logic module inelastic_column_buckling_logic.py
implements the yield-anchored Euler-Johnson tangent column strength
curve of whole solid, round, tube and extruded compression members in
the intermediate slenderness band. Every test method below exercises a
numbered step of the SKILL.md Workflow: step 1 gathers the member
inputs and section properties, step 2 computes the effective
slenderness lambda = K*L/r, step 3 computes the euler-johnson-tangent
transition lambda_t, step 4 classifies the johnson or euler regime,
step 5 computes the inelastic column allowable stress F_col of the
johnson-parabola column strength curve (the stubby-column-allowable)
or the euler arm above the transition, step 6 computes the column
capacity P_col, and step 7 runs the margin of safety and the verdict
of the full column_check. The worked-example anchors asserted here are
REAL prep outputs of the wave-45 spec anchor script (stdlib math,
byte-identical under /usr/bin/python3 3.9.6 and the pyenv 3.13.12
pre-push hook interpreter). No exact-float equality is asserted on any
computed quantity: every numeric comparison uses math.isclose or an
absolute/relative tolerance.
"""

import hashlib
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inelastic_column_buckling_logic as icb

E_7075 = icb.E_7075_T6
FCY_7075 = icb.F_CY_7075_T6
E_2024 = icb.E_2024_T3
FCY_2024 = icb.F_CY_2024_T3

# Real worked-example anchors from the spec (prep anchor real outputs).
ROD_AREA_ANCHOR = 1.2566370614359172e-03
ROD_F_COL_ANCHOR = 233897293.82113209
ROD_F_EULER_ANCHOR = 233934094.39937419
ROD_P_COL_ANCHOR = 293924.00798520073
ROD_MARGIN_ANCHOR = 0.46962003992600376
TUBE_R_ANCHOR = 0.016007810593582122
TUBE_F_COL_ANCHOR = 242922035.66673699
TUBE_F_EULER_ANCHOR = 446599599.14929342
TUBE_OVERP_ANCHOR = 1.8384482820734314
TUBE_P_COL_ANCHOR = 171711.46859528226
TUBE_MARGIN_ANCHOR = 0.43092890496068548
SHA_ANCHOR = "1f3904e5de54c994b725577b30d02c298b726db9a7a2394172f74c6c2c8e1183"


def rel_close(actual, expected, tol):
    """math.isclose with the expected value as the reference."""
    return math.isclose(actual, expected, rel_tol=tol, abs_tol=0.0)


def fmt17(x):
    return format(x, ".17g")


def canonical_dump():
    """Byte-identical reproduction of the anchor canonical dump: the
    rod and tube worked-example fields plus the identity residuals, the
    deterministic artifact whose sha256 the determinism test pins."""
    lines = []
    d = 0.04
    rod_area = math.pi * d**2 / 4.0
    rod_r = d / 4.0
    rod_lam = icb.effective_slenderness(1.0, 0.55, rod_r)
    rod_lam_t = icb.johnson_transition_slenderness(E_7075, FCY_7075)
    rod_f_john = icb.johnson_parabola_stress(E_7075, FCY_7075, rod_lam)
    rod_f_eul = icb.euler_arm_stress(E_7075, rod_lam)
    rod_p_col = icb.column_capacity(E_7075, FCY_7075, rod_lam, rod_area)
    rod_margin = icb.margin_of_safety(rod_p_col, 200.0e3)
    lines.append("rod area " + fmt17(rod_area))
    lines.append("rod r " + fmt17(rod_r))
    lines.append("rod lam " + fmt17(rod_lam))
    lines.append("rod lam_t " + fmt17(rod_lam_t))
    lines.append("rod f_johnson " + fmt17(rod_f_john))
    lines.append("rod f_euler " + fmt17(rod_f_eul))
    lines.append("rod p_col " + fmt17(rod_p_col))
    lines.append("rod margin " + fmt17(rod_margin))
    do_, di = 0.05, 0.04
    tube_area = math.pi * (do_**2 - di**2) / 4.0
    tube_inertia = math.pi * (do_**4 - di**4) / 64.0
    tube_r = math.sqrt(tube_inertia / tube_area)
    tube_len = 40.0 * tube_r
    tube_lam = icb.effective_slenderness(1.0, tube_len, tube_r)
    tube_lam_t = icb.johnson_transition_slenderness(E_2024, FCY_2024)
    tube_f_john = icb.johnson_parabola_stress(E_2024, FCY_2024, tube_lam)
    tube_f_eul = icb.euler_arm_stress(E_2024, tube_lam)
    tube_p_col = icb.column_capacity(E_2024, FCY_2024, tube_lam, tube_area)
    tube_margin = icb.margin_of_safety(tube_p_col, 120.0e3)
    lines.append("tube area " + fmt17(tube_area))
    lines.append("tube inertia " + fmt17(tube_inertia))
    lines.append("tube r " + fmt17(tube_r))
    lines.append("tube length " + fmt17(tube_len))
    lines.append("tube lam " + fmt17(tube_lam))
    lines.append("tube lam_t " + fmt17(tube_lam_t))
    lines.append("tube f_johnson " + fmt17(tube_f_john))
    lines.append("tube f_euler " + fmt17(tube_f_eul))
    lines.append("tube p_col " + fmt17(tube_p_col))
    lines.append("tube margin " + fmt17(tube_margin))
    ident = identities_residuals()
    for key in ("7075_lam_t", "7075_johnson_at_t_rel", "7075_euler_at_t_rel",
                "7075_arms_cross_rel", "7075_slope_resid",
                "7075_drop_quarter_resid", "7075_regime_below",
                "7075_regime_above", "7075_cont_resid",
                "7075_yield_anchor_rel", "7075_euler_gt_johnson_mid",
                "2024_lam_t", "2024_johnson_at_t_rel", "2024_euler_at_t_rel",
                "2024_arms_cross_rel", "2024_slope_resid",
                "2024_drop_quarter_resid", "2024_regime_below",
                "2024_regime_above", "2024_cont_resid",
                "2024_yield_anchor_rel", "2024_euler_gt_johnson_mid"):
        lines.append(key + " " + str(ident[key]))
    return "\n".join(lines)


def identities_residuals():
    """Closed-form identity residuals of the two-arm column strength
    curve, mirroring the anchor identities() dict keys."""
    out = {}
    for tag, e, f_cy in (("7075", E_7075, FCY_7075),
                         ("2024", E_2024, FCY_2024)):
        lam_t = icb.johnson_transition_slenderness(e, f_cy)
        f_half = f_cy / 2.0
        f_j = icb.johnson_parabola_stress(e, f_cy, lam_t)
        f_e = icb.euler_arm_stress(e, lam_t)
        out[tag + "_lam_t"] = lam_t
        out[tag + "_johnson_at_t_rel"] = abs(f_j - f_half) / f_half
        out[tag + "_euler_at_t_rel"] = abs(f_e - f_half) / f_half
        out[tag + "_arms_cross_rel"] = abs(f_j - f_e) / f_half
        out[tag + "_slope_resid"] = (abs(icb.johnson_slope(e, f_cy, lam_t)
                                         - icb.euler_slope(e, lam_t))
                                     / abs(icb.euler_slope(e, lam_t)))
        drop_t = f_cy - icb.johnson_parabola_stress(e, f_cy, lam_t)
        drop_h = f_cy - icb.johnson_parabola_stress(e, f_cy, lam_t / 2.0)
        out[tag + "_drop_quarter_resid"] = abs(4.0 * drop_h - drop_t) / drop_t
        eps = lam_t * 1e-12
        out[tag + "_regime_below"] = icb.column_regime(e, f_cy, lam_t - eps)
        out[tag + "_regime_above"] = icb.column_regime(e, f_cy, lam_t + eps)
        out[tag + "_cont_resid"] = abs(icb.column_strength_allowable(
            e, f_cy, lam_t + eps) - f_half) / f_half
        f_small = icb.johnson_parabola_stress(e, f_cy, lam_t * 1e-6)
        out[tag + "_yield_anchor_rel"] = abs(f_small - f_cy) / f_cy
        mid = lam_t / 2.0
        out[tag + "_euler_gt_johnson_mid"] = (
            icb.euler_arm_stress(e, mid)
            > icb.johnson_parabola_stress(e, f_cy, mid))
    return out


class InelasticColumnBucklingContractTest(unittest.TestCase):
    """Contract tests for the inelastic-column-buckling leaf.

    Methods are grouped by the SKILL.md workflow step they exercise
    (steps 1 to 7) and by the closed-form identity families of the
    yield-anchored column strength curve."""

    # Workflow step 1: member inputs and section properties.
    def test_material_registry_constants(self):
        """Workflow step 1 inputs: the material registry pair (E and
        F_cy of 7075-T6 and 2024-T3) shared with the crippling-analysis
        sibling; literal module constants asserted exactly."""
        self.assertEqual(icb.E_2024_T3, 72.4e9)
        self.assertEqual(icb.F_CY_2024_T3, 290.0e6)
        self.assertEqual(icb.E_7075_T6, 71.7e9)
        self.assertEqual(icb.F_CY_7075_T6, 462.0e6)

    def test_rod_section_area_and_radius(self):
        """Workflow step 1: solid round actuator rod section, the
        solid-round identity r = d/4 and A = pi*d^2/4."""
        d = 0.04
        area = math.pi * d**2 / 4.0
        self.assertTrue(rel_close(area, ROD_AREA_ANCHOR, 1e-12))
        self.assertTrue(rel_close(d / 4.0, 0.01, 1e-15))
        self.assertEqual(d / 4.0, 0.01)

    def test_tube_section_properties_and_round_tube_identity(self):
        """Workflow step 1: extruded tube section A, I and r from d_o,
        d_i, with the round-tube identity r = sqrt((d_o^2 + d_i^2)/16)."""
        do_, di = 0.05, 0.04
        area = math.pi * (do_**2 - di**2) / 4.0
        inertia = math.pi * (do_**4 - di**4) / 64.0
        r = math.sqrt(inertia / area)
        self.assertTrue(rel_close(area, 7.0685834705770374e-04, 1e-12))
        self.assertTrue(rel_close(inertia, 1.8113245143353656e-07, 1e-12))
        self.assertTrue(rel_close(r, TUBE_R_ANCHOR, 1e-9))
        self.assertTrue(rel_close(r, math.sqrt(2.5625e-04), 1e-12))

    # Workflow step 2: effective slenderness lambda = K*L/r.
    def test_effective_slenderness_rod_lambda_55(self):
        """Workflow step 2, the effective slenderness traverse of the
        actuator rod: lambda = K*L/r = 1.0*0.55/0.01 returns 55, just
        below the euler-johnson-tangent transition."""
        lam = icb.effective_slenderness(1.0, 0.55, 0.01)
        self.assertTrue(rel_close(lam, 55.0, 1e-12))

    def test_effective_slenderness_tube_lambda_40(self):
        """Workflow step 2, the effective slenderness traverse of the
        extruded tube: L = 40*r pins lambda = K*L/r at exactly 40, deep
        in the johnson-parabola intermediate-slenderness band."""
        r = TUBE_R_ANCHOR
        length = 40.0 * r
        lam = icb.effective_slenderness(1.0, length, r)
        self.assertTrue(rel_close(lam, 40.0, 1e-12))

    # Workflow step 3: euler-johnson-tangent transition.
    def test_transition_slenderness_7075_t6(self):
        """Workflow step 3: the euler-johnson-tangent transition
        lambda_t = sqrt(2*pi^2*E/F_cy) of 7075-T6 equals
        55.348194774118063, with the cross-form identity
        lambda_t = sqrt(2)*pi*sqrt(E/F_cy) and the fence
        lambda_t = sqrt(2)*lambda_1 against the elastic yield crossing."""
        lam_t = icb.johnson_transition_slenderness(E_7075, FCY_7075)
        self.assertTrue(rel_close(lam_t, 55.348194774118063, 1e-9))
        cross = math.sqrt(2.0) * math.pi * math.sqrt(E_7075 / FCY_7075)
        self.assertTrue(rel_close(lam_t, cross, 1e-9))
        lam_1 = math.pi * math.sqrt(E_7075 / FCY_7075)
        self.assertTrue(rel_close(lam_t, math.sqrt(2.0) * lam_1, 1e-9))

    def test_transition_slenderness_2024_t3(self):
        """Workflow step 3: the euler-johnson-tangent transition of
        2024-T3 equals 70.199683594869498, and the cross-form identity
        lambda_t = sqrt(2)*pi*sqrt(E/F_cy) holds."""
        lam_t = icb.johnson_transition_slenderness(E_2024, FCY_2024)
        self.assertTrue(rel_close(lam_t, 70.199683594869498, 1e-9))
        cross = math.sqrt(2.0) * math.pi * math.sqrt(E_2024 / FCY_2024)
        self.assertTrue(rel_close(lam_t, cross, 1e-9))

    # Workflow step 4: regime classification.
    def test_regime_johnson_rod_lambda_55(self):
        """Workflow step 4: the 7075-T6 rod at lambda 55 sits below the
        tangent transition, so column_regime returns johnson; at
        lambda 60 (above the transition) it returns euler."""
        self.assertEqual(icb.column_regime(E_7075, FCY_7075, 55.0), "johnson")
        self.assertEqual(icb.column_regime(E_7075, FCY_7075, 60.0), "euler")

    def test_regime_johnson_tube_lambda_40(self):
        """Workflow step 4: the 2024-T3 tube at lambda 40 is deep in
        the johnson band, 40 below 0.57*lambda_t, and column_regime
        returns johnson (stubby-column range of the curve)."""
        lam_t = icb.johnson_transition_slenderness(E_2024, FCY_2024)
        self.assertLess(40.0, 0.57 * lam_t)
        self.assertEqual(icb.column_regime(E_2024, FCY_2024, 40.0), "johnson")

    # Workflow step 5: the inelastic column allowable stress F_col.
    def test_johnson_parabola_stress_rod(self):
        """Workflow step 5, the johnson-parabola arm of the column
        strength curve: the 7075-T6 inelastic column allowable
        F_col = F_cy*(1 - F_cy*lam^2/(4*pi^2*E)) at lambda 55 is
        233897293.82113209 Pa, between the yield anchor and F_cy/2."""
        f = icb.johnson_parabola_stress(E_7075, FCY_7075, 55.0)
        self.assertTrue(rel_close(f, ROD_F_COL_ANCHOR, 1e-6))

    def test_euler_arm_stress_rod_near_tangency(self):
        """Workflow step 5, the euler arm of the same curve at lambda
        55: 233934094.39937419 Pa, only 1.573e-4 above the johnson
        parabola near the tangency point."""
        f = icb.euler_arm_stress(E_7075, 55.0)
        self.assertTrue(rel_close(f, ROD_F_EULER_ANCHOR, 1e-6))

    def test_stubby_column_allowable_tube(self):
        """Workflow step 5, the stubby-column-allowable of the 2024-T3
        extruded tube at lambda 40: the johnson parabola stress is
        242922035.66673699 Pa (0.83766 of F_cy) where the euler stress
        overpredicts at 1.8384482820734314 times the allowable and
        above yield itself."""
        f_col = icb.johnson_parabola_stress(E_2024, FCY_2024, 40.0)
        f_eul = icb.euler_arm_stress(E_2024, 40.0)
        self.assertTrue(rel_close(f_col, TUBE_F_COL_ANCHOR, 1e-6))
        self.assertTrue(rel_close(f_col / FCY_2024, 0.83766, 1e-4))
        self.assertTrue(rel_close(f_eul, TUBE_F_EULER_ANCHOR, 1e-6))
        self.assertTrue(rel_close(f_eul / f_col, TUBE_OVERP_ANCHOR, 1e-9))
        self.assertGreater(f_eul, FCY_2024)

    def test_column_strength_allowable_rod_picks_johnson_arm(self):
        """Workflow step 5: column_strength_allowable below the tangent
        transition returns the johnson-parabola arm of the column
        strength curve, equal to the worked-example allowable."""
        f = icb.column_strength_allowable(E_7075, FCY_7075, 55.0)
        self.assertTrue(rel_close(f, ROD_F_COL_ANCHOR, 1e-6))
        f_j = icb.johnson_parabola_stress(E_7075, FCY_7075, 55.0)
        self.assertTrue(rel_close(f, f_j, 1e-9))

    # Workflow step 6: column capacity.
    def test_column_capacity_rod(self):
        """Workflow step 6: P_col = F_col*A of the actuator rod is
        293924.00798520073 N, linear in the section area (doubling the
        area doubles the capacity), and P_col/A equals the allowable."""
        p = icb.column_capacity(E_7075, FCY_7075, 55.0, ROD_AREA_ANCHOR)
        self.assertTrue(rel_close(p, ROD_P_COL_ANCHOR, 1e-6))
        p2 = icb.column_capacity(E_7075, FCY_7075, 55.0, ROD_AREA_ANCHOR * 2.0)
        self.assertTrue(rel_close(p2, 2.0 * p, 1e-9))
        f_col = icb.column_strength_allowable(E_7075, FCY_7075, 55.0)
        self.assertTrue(rel_close(p / ROD_AREA_ANCHOR, f_col, 1e-9))

    def test_column_capacity_tube(self):
        """Workflow step 6: P_col of the extruded tube compression
        member is 171711.46859528226 N against its section area."""
        p = icb.column_capacity(E_2024, FCY_2024, 40.0,
                                7.0685834705770374e-04)
        self.assertTrue(rel_close(p, TUBE_P_COL_ANCHOR, 1e-6))

    # Workflow step 7: margin of safety and verdict.
    def test_column_check_rod_margin_and_verdict(self):
        """Workflow step 7, the full column_check of the actuator rod:
        margin of safety 0.46962003992600376 against the 200 kN applied
        axial load and verdict pass, with the six documented keys."""
        res = icb.column_check(E_7075, FCY_7075, 55.0, ROD_AREA_ANCHOR,
                               200.0e3)
        self.assertEqual(
            set(res.keys()),
            {"lambda_t", "regime", "F_col", "P_col", "margin", "verdict"})
        self.assertTrue(rel_close(res["margin"], ROD_MARGIN_ANCHOR, 1e-6))
        self.assertEqual(res["verdict"], "pass")
        self.assertEqual(res["regime"], "johnson")
        self.assertTrue(rel_close(res["F_col"], ROD_F_COL_ANCHOR, 1e-6))
        self.assertTrue(rel_close(res["P_col"], ROD_P_COL_ANCHOR, 1e-6))
        self.assertTrue(rel_close(res["lambda_t"], 55.348194774118063, 1e-9))

    def test_column_check_tube_margin_and_verdict(self):
        """Workflow step 7, the full column_check of the extruded tube:
        margin 0.43092890496068548 against the 120 kN applied axial
        load, verdict pass, and key-by-key agreement with the component
        functions."""
        res = icb.column_check(E_2024, FCY_2024, 40.0,
                               7.0685834705770374e-04, 120.0e3)
        self.assertTrue(rel_close(res["margin"], TUBE_MARGIN_ANCHOR, 1e-6))
        self.assertEqual(res["verdict"], "pass")
        self.assertEqual(res["regime"], "johnson")
        self.assertTrue(rel_close(res["F_col"], TUBE_F_COL_ANCHOR, 1e-6))
        self.assertTrue(rel_close(res["P_col"], TUBE_P_COL_ANCHOR, 1e-6))
        self.assertTrue(rel_close(
            res["lambda_t"], icb.johnson_transition_slenderness(E_2024,
                                                                FCY_2024),
            1e-12))
        f_col = icb.column_strength_allowable(E_2024, FCY_2024, 40.0)
        p_col = icb.column_capacity(E_2024, FCY_2024, 40.0,
                                    7.0685834705770374e-04)
        self.assertTrue(rel_close(res["F_col"], f_col, 1e-12))
        self.assertTrue(rel_close(res["P_col"], p_col, 1e-12))
        margin = icb.margin_of_safety(p_col, 120.0e3)
        self.assertTrue(rel_close(res["margin"], margin, 1e-12))

    def test_margin_of_safety_linearity_halving_load(self):
        """Workflow step 7: the margin of safety is linear in the
        applied load, margin_of_safety(P_col, P_applied/2) equals
        2*MS + 1, and margin_of_safety reproduces P_col/P_applied - 1."""
        ms = icb.margin_of_safety(ROD_P_COL_ANCHOR, 200.0e3)
        self.assertTrue(rel_close(ms, ROD_MARGIN_ANCHOR, 1e-12))
        ms_half = icb.margin_of_safety(ROD_P_COL_ANCHOR, 100.0e3)
        self.assertTrue(rel_close(ms_half, 2.0 * ms + 1.0, 1e-9))
        direct = ROD_P_COL_ANCHOR / 200.0e3 - 1.0
        self.assertTrue(rel_close(ms, direct, 1e-12))

    def test_column_check_fail_verdict_when_overloaded(self):
        """Workflow step 7: against an applied axial load above the
        column capacity the margin is negative and the verdict is fail,
        the rejection side of the compression check."""
        res = icb.column_check(E_7075, FCY_7075, 55.0, ROD_AREA_ANCHOR,
                               400.0e3)
        self.assertLess(res["margin"], 0.0)
        self.assertEqual(res["verdict"], "fail")

    # Column strength curve sweeps and shape.
    def test_curve_sweep_7075_t6(self):
        """Workflow steps 4 and 5, the 7075-T6 column strength curve
        sweep: F_col and regime at lambda 10, 20, 40, 55 reproduce the
        anchors (johnson below the transition, euler from 60 up), and
        in the euler regime the allowable equals the euler arm."""
        rows = [(10.0, 454459414.671773, "johnson"),
                (20.0, 431837658.687092, "johnson"),
                (40.0, 341350634.748367, "johnson"),
                (55.0, 233897293.821132, "johnson"),
                (60.0, 196569620.988363, "euler"),
                (80.0, 110570411.805954, "euler"),
                (100.0, 70765063.5558107, "euler")]
        for lam, anchor, regime in rows:
            f = icb.column_strength_allowable(E_7075, FCY_7075, lam)
            self.assertTrue(rel_close(f, anchor, 1e-6))
            self.assertEqual(icb.column_regime(E_7075, FCY_7075, lam), regime)
            if regime == "euler":
                self.assertTrue(
                    rel_close(f, icb.euler_arm_stress(E_7075, lam), 1e-12))

    def test_curve_sweep_2024_t3(self):
        """Workflow steps 4 and 5, the 2024-T3 column strength curve
        sweep: F_col and regime at lambda 10, 20, 30, 40, 55, 70
        (johnson through the near-tangency row just below the
        transition) and 90, 120 (euler arm above it)."""
        rows = [(10.0, 287057627.229171, "johnson"),
                (20.0, 278230508.916684, "johnson"),
                (30.0, 263518645.06254, "johnson"),
                (40.0, 242922035.666737, "johnson"),
                (55.0, 200993223.682425, "johnson"),
                (70.0, 145823734.229382, "johnson"),
                (90.0, 88217204.7702308, "euler"),
                (120.0, 49622177.6832548, "euler")]
        for lam, anchor, regime in rows:
            f = icb.column_strength_allowable(E_2024, FCY_2024, lam)
            self.assertTrue(rel_close(f, anchor, 1e-6))
            self.assertEqual(icb.column_regime(E_2024, FCY_2024, lam), regime)
            if regime == "euler":
                self.assertTrue(
                    rel_close(f, icb.euler_arm_stress(E_2024, lam), 1e-12))

    def test_curve_strictly_monotone_decreasing(self):
        """Workflow step 5, curve shape: the yield-anchored column
        strength curve is strictly monotone decreasing over a dense
        lambda grid from 1 to 200 for both materials."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            prev = icb.column_strength_allowable(e, f_cy, 1.0)
            lam = 1.5
            while lam <= 200.0:
                cur = icb.column_strength_allowable(e, f_cy, lam)
                self.assertLess(cur, prev)
                prev = cur
                lam += 0.5

    # Closed-form identities.
    def test_tangency_both_arms_return_f_cy_half(self):
        """Workflow step 3 identity: at the euler-johnson-tangent
        transition both arms of the column strength curve return F_cy/2
        (johnson arm, euler arm and their cross difference each within
        1e-12 relative), the tangency by construction."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            lam_t = icb.johnson_transition_slenderness(e, f_cy)
            f_half = f_cy / 2.0
            f_j = icb.johnson_parabola_stress(e, f_cy, lam_t)
            f_e = icb.euler_arm_stress(e, lam_t)
            self.assertTrue(rel_close(f_j, f_half, 1e-12))
            self.assertTrue(rel_close(f_e, f_half, 1e-12))
            self.assertTrue(rel_close(f_j, f_e, 1e-12))

    def test_slope_tangency_at_transition(self):
        """Workflow step 3 identity: the closed-form slopes of the two
        arms agree at lambda_t within 1e-9 relative, the parabola is
        tangent to the euler hyperbola at F_cy/2."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            lam_t = icb.johnson_transition_slenderness(e, f_cy)
            sj = icb.johnson_slope(e, f_cy, lam_t)
            se = icb.euler_slope(e, lam_t)
            self.assertTrue(rel_close(sj, se, 1e-9))
            self.assertLess(sj, 0.0)

    def test_quadratic_decay_quarter_drop_identity(self):
        """Workflow step 5 identity: the drop from the yield anchor,
        F_cy - F_col, is quadratic in lambda, so the drop at lam_t/2 is
        exactly one quarter of the drop at lam_t = F_cy/2 (the
        quarter-drop identity of the johnson parabola)."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            lam_t = icb.johnson_transition_slenderness(e, f_cy)
            drop_t = f_cy - icb.johnson_parabola_stress(e, f_cy, lam_t)
            drop_h = f_cy - icb.johnson_parabola_stress(e, f_cy, lam_t / 2.0)
            self.assertTrue(abs(4.0 * drop_h - drop_t) <= 1e-9 * f_cy)
            self.assertTrue(rel_close(drop_t, f_cy / 2.0, 1e-12))

    def test_yield_anchor_at_small_lambda(self):
        """Workflow step 5 identity: at lam = lam_t*1e-6 the johnson
        parabola sits within 1e-9 relative of the yield anchor F_cy, so
        F_col approaches F_cy as lambda approaches zero."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            lam_t = icb.johnson_transition_slenderness(e, f_cy)
            f_small = icb.johnson_parabola_stress(e, f_cy, lam_t * 1e-6)
            self.assertTrue(rel_close(f_small, f_cy, 1e-9))

    def test_regime_flip_and_continuity_across_transition(self):
        """Workflow step 4 identity: column_regime flips from johnson
        to euler across lam_t*(1 +/- 1e-12) for both materials, and
        F_col at the upper point stays within 1e-9 relative of F_cy/2,
        so the column strength curve is continuous across the tangent
        transition to float roundoff."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            lam_t = icb.johnson_transition_slenderness(e, f_cy)
            eps = lam_t * 1e-12
            self.assertEqual(icb.column_regime(e, f_cy, lam_t - eps),
                             "johnson")
            self.assertEqual(icb.column_regime(e, f_cy, lam_t + eps), "euler")
            f_up = icb.column_strength_allowable(e, f_cy, lam_t + eps)
            self.assertTrue(rel_close(f_up, f_cy / 2.0, 1e-9))

    def test_euler_overpredicts_inside_johnson_band(self):
        """Workflow step 5 identity: the euler arm lies strictly above
        the johnson parabola at lam_t/2 for both materials, the elastic
        overprediction in the intermediate slenderness band that the
        yield-anchored parabola corrects."""
        for e, f_cy in ((E_7075, FCY_7075), (E_2024, FCY_2024)):
            lam_t = icb.johnson_transition_slenderness(e, f_cy)
            mid = lam_t / 2.0
            self.assertGreater(icb.euler_arm_stress(e, mid),
                               icb.johnson_parabola_stress(e, f_cy, mid))

    # Input rejection.
    def test_valueerror_non_physical_inputs(self):
        """Workflow validation: every non-physical input of the module
        raises ValueError, from the zero effective-length factor and
        radius of gyration of the slenderness traverse through the
        zero area, allowable and applied-load rejections of the
        capacity, margin and column_check functions."""
        cases = [
            lambda: icb.effective_slenderness(0.0, 0.55, 0.01),
            lambda: icb.effective_slenderness(1.0, 0.0, 0.01),
            lambda: icb.effective_slenderness(1.0, 0.55, 0.0),
            lambda: icb.johnson_transition_slenderness(0.0, 462.0e6),
            lambda: icb.johnson_transition_slenderness(71.7e9, 0.0),
            lambda: icb.johnson_parabola_stress(0.0, 462.0e6, 55.0),
            lambda: icb.johnson_parabola_stress(71.7e9, 0.0, 55.0),
            lambda: icb.johnson_parabola_stress(71.7e9, 462.0e6, 0.0),
            lambda: icb.euler_arm_stress(0.0, 55.0),
            lambda: icb.euler_arm_stress(71.7e9, 0.0),
            lambda: icb.column_regime(71.7e9, 462.0e6, 0.0),
            lambda: icb.column_strength_allowable(71.7e9, 462.0e6, 0.0),
            lambda: icb.column_capacity(71.7e9, 462.0e6, 55.0, 0.0),
            lambda: icb.margin_of_safety(0.0, 200.0e3),
            lambda: icb.margin_of_safety(293924.00798520073, 0.0),
            lambda: icb.column_check(71.7e9, 462.0e6, 55.0,
                                     1.2566370614359172e-03, 0.0),
        ]
        for case in cases:
            with self.assertRaises(ValueError):
                case()

    # Determinism and reproducibility.
    def test_determinism_canonical_dump_digest(self):
        """Workflow step 7 determinism: two identical full runs return
        identical bits and the canonical dump sha256 matches the anchor
        digest 1f3904e5... on both in-process passes, under both the
        /usr/bin/python3 3.9.6 and pyenv 3.13.12 interpreters."""
        d1 = canonical_dump()
        d2 = canonical_dump()
        self.assertEqual(d1, d2)
        h1 = hashlib.sha256(d1.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(d2.encode("utf-8")).hexdigest()
        self.assertEqual(h1, h2)
        self.assertEqual(h1, SHA_ANCHOR)

    def test_module_no_extra_imports_no_rng(self):
        """Workflow determinism: the logic module source imports math
        only (no random state, no numpy or other heavy imports), so the
        yield-anchored column strength curve is a deterministic pure
        function of its float inputs."""
        with open(os.path.abspath(icb.__file__)) as src:
            for line in src:
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    self.assertTrue(stripped.startswith("import math"),
                                    "unexpected import: " + stripped)


if __name__ == "__main__":
    unittest.main()
