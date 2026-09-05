"""Contract test for the vehicle-design/sizing/v-tail-sizing leaf.

Exercises the numbered SKILL.md Workflow: gathering the aircraft
reference data and the target volume coefficients of the light-aircraft
worked example (step 1), converting each target volume coefficient
into the required equivalent area on the wing reference chord and span
with the tail arm (step 2), resolving the two equivalent areas onto
the canted V-tail pair, the total V-tail area vector sum, the dihedral
angle from the horizontal, the equal panel split and the per-surface
span and chord at the surface aspect ratio (step 3), sizing the
ruddervator control area as a fraction of the total V-tail area
(step 4), and verifying the effective volume coefficient round trip
with the projected equivalent areas and the met verdicts under the
module tolerance (step 5).

Every numeric expectation below is a REAL module output from a local
run of v_tail_sizing_logic.py on the worked example, checked against
the prep-verified spec anchors and the leaf identities: the projection
identity s_h_eff^2 + s_v_eff^2 = s_vt^2, the exact vector-sum and
atan2 inversion, the 45 degree symmetric case, the halving of the
required equivalent area when the tail arm doubles, the met flags
turning False for a 10% undersized total V-tail area, and ValueError
rejection of every non-physical input.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import v_tail_sizing_logic as vtl

# Worked example constants of the leaf spec: light aircraft with
# S_ref = 16 m2, c_bar = 1.5 m, b = 11 m, l_h = l_v = 4.5 m, and
# targets V_h = 0.7, V_v = 0.04.
S_REF = 16.0
C_BAR = 1.5
B = 11.0
L_H = 4.5
L_V = 4.5
V_H = 0.7
V_V = 0.04

# Prep-verified anchors for the worked example (module real outputs).
S_H_EXP = 3.7333333333333325
S_V_EXP = 1.5644444444444445
S_VT_EXP = 4.047871563863021
GAMMA_RAD_EXP = 0.3968181439505532
GAMMA_DEG_EXP = 22.736004882581458
AREA_PER_SURF_EXP = 2.0239357819315105
SPAN_PER_SURF_EXP = 2.8453019396412116
CHORD_PER_SURF_EXP = 0.711325484910303
RUD_TOTAL_EXP = 1.4167550473520572
RUD_PER_SURF_EXP = 0.7083775236760286


class TestEquivalentAreaConversion(unittest.TestCase):
    """Workflow step 2, equivalent area from a volume coefficient."""

    def test_horizontal_equivalent_area_worked_example(self):
        # Step 2 on the V_h target: 0.7 * 16 * 1.5 / 4.5 = 3.73333 m2.
        self.assertAlmostEqual(
            vtl.tail_area_from_volume_coefficient(V_H, C_BAR, L_H, S_REF),
            S_H_EXP, delta=1e-6)

    def test_vertical_equivalent_area_worked_example(self):
        # Step 2 on the V_v target: 0.04 * 16 * 11 / 4.5 = 1.56444 m2.
        self.assertAlmostEqual(
            vtl.tail_area_from_volume_coefficient(V_V, B, L_V, S_REF),
            S_V_EXP, delta=1e-6)

    def test_doubled_arm_halves_required_equivalent_area(self):
        # Step 2 scaling identity: doubling the tail arm halves the area.
        self.assertAlmostEqual(
            vtl.tail_area_from_volume_coefficient(V_H, C_BAR, 2 * L_H, S_REF),
            S_H_EXP / 2.0, delta=1e-6)

    def test_area_scales_with_reference_area(self):
        # Step 2 linearity: doubling the wing reference area doubles S_h.
        self.assertAlmostEqual(
            vtl.tail_area_from_volume_coefficient(V_H, C_BAR, L_H,
                                                  2 * S_REF),
            2.0 * S_H_EXP, delta=1e-6)

    def test_zero_volume_coefficient_raises(self):
        # Step 2 non-physical rejection: a zero target coefficient.
        with self.assertRaises(ValueError):
            vtl.tail_area_from_volume_coefficient(0.0, C_BAR, L_H, S_REF)

    def test_negative_volume_coefficient_raises(self):
        # Step 2 non-physical rejection: a negative target coefficient.
        with self.assertRaises(ValueError):
            vtl.tail_area_from_volume_coefficient(-0.7, C_BAR, L_H, S_REF)

    def test_zero_reference_length_or_arm_raises(self):
        # Step 2 non-physical rejection: zero reference length or arm.
        with self.assertRaises(ValueError):
            vtl.tail_area_from_volume_coefficient(V_H, 0.0, L_H, S_REF)
        with self.assertRaises(ValueError):
            vtl.tail_area_from_volume_coefficient(V_H, C_BAR, 0.0, S_REF)

    def test_non_positive_reference_area_raises(self):
        # Step 2 non-physical rejection: zero or negative S_ref.
        with self.assertRaises(ValueError):
            vtl.tail_area_from_volume_coefficient(V_H, C_BAR, L_H, 0.0)
        with self.assertRaises(ValueError):
            vtl.tail_area_from_volume_coefficient(V_H, C_BAR, L_H, -S_REF)


class TestVtailCantedPairResolution(unittest.TestCase):
    """Workflow step 3, canted pair resolution and panel geometry."""

    def test_total_vtail_area_vector_sum_worked_example(self):
        # Step 3 vector sum: sqrt(3.73333^2 + 1.56444^2) = 4.04787 m2.
        self.assertAlmostEqual(
            vtl.vtail_geometry(S_H_EXP, S_V_EXP)["s_vt"],
            S_VT_EXP, delta=1e-4)

    def test_dihedral_radians_worked_example(self):
        # Step 3 dihedral from atan2(S_v, S_h): 0.396818 rad.
        self.assertAlmostEqual(
            vtl.vtail_geometry(S_H_EXP, S_V_EXP)["gamma_rad"],
            GAMMA_RAD_EXP, delta=1e-9)

    def test_dihedral_degrees_worked_example(self):
        # Step 3 dihedral in degrees: 22.7360 deg from the horizontal.
        self.assertAlmostEqual(
            vtl.vtail_geometry(S_H_EXP, S_V_EXP)["gamma_deg"],
            GAMMA_DEG_EXP, delta=1e-9)

    def test_per_surface_area_equal_split_worked_example(self):
        # Step 3 equal panel split: S_vt / 2 = 2.02394 m2 per panel.
        self.assertAlmostEqual(
            vtl.vtail_geometry(S_H_EXP, S_V_EXP)["area_per_surface"],
            AREA_PER_SURF_EXP, delta=1e-4)

    def test_per_surface_span_worked_example(self):
        # Step 3 span at the aspect ratio: sqrt(4 * 2.02394) = 2.84530 m.
        self.assertAlmostEqual(
            vtl.vtail_geometry(S_H_EXP, S_V_EXP)["span_per_surface"],
            SPAN_PER_SURF_EXP, delta=1e-4)

    def test_per_surface_chord_worked_example(self):
        # Step 3 mean panel chord: 2.02394 / 2.84530 = 0.711325 m.
        self.assertAlmostEqual(
            vtl.vtail_geometry(S_H_EXP, S_V_EXP)["chord_per_surface"],
            CHORD_PER_SURF_EXP, delta=1e-4)

    def test_result_dict_keys_exact(self):
        # Step 3 output contract: the documented dict keys only.
        self.assertEqual(
            set(vtl.vtail_geometry(S_H_EXP, S_V_EXP).keys()),
            {"s_vt", "gamma_rad", "gamma_deg", "area_per_surface",
             "span_per_surface", "chord_per_surface"})

    def test_equal_requirements_give_45_degree_dihedral(self):
        # Step 3 symmetric identity: equal areas give Gamma = 45 deg.
        self.assertAlmostEqual(
            vtl.vtail_geometry(1.0, 1.0)["gamma_deg"], 45.0, delta=1e-9)

    def test_equal_requirements_give_sqrt2_total_area(self):
        # Step 3 symmetric identity: S_vt = sqrt(2) * S_h.
        self.assertAlmostEqual(
            vtl.vtail_geometry(1.0, 1.0)["s_vt"], math.sqrt(2.0),
            delta=1e-12)

    def test_span_grows_with_required_area(self):
        # Step 3 monotonicity: a larger requirement gives a longer span.
        small = vtl.vtail_geometry(1.0, 1.0)["span_per_surface"]
        large = vtl.vtail_geometry(2.0, 1.0)["span_per_surface"]
        self.assertGreater(large, small)

    def test_dihedral_lies_in_first_quadrant(self):
        # Step 3 range: gamma in [0, pi/2) for positive requirements.
        gamma_rad = vtl.vtail_geometry(S_H_EXP, S_V_EXP)["gamma_rad"]
        self.assertGreaterEqual(gamma_rad, 0.0)
        self.assertLess(gamma_rad, math.pi / 2.0)

    def test_non_positive_areas_or_aspect_ratio_raise(self):
        # Step 3 non-physical rejection of the resolution inputs.
        with self.assertRaises(ValueError):
            vtl.vtail_geometry(0.0, S_V_EXP)
        with self.assertRaises(ValueError):
            vtl.vtail_geometry(S_H_EXP, 0.0)
        with self.assertRaises(ValueError):
            vtl.vtail_geometry(S_H_EXP, S_V_EXP, 0.0)
        with self.assertRaises(ValueError):
            vtl.vtail_geometry(S_H_EXP, S_V_EXP, -4.0)


class TestRuddervatorSizing(unittest.TestCase):
    """Workflow step 4, ruddervator control area fraction."""

    def test_total_ruddervator_area_worked_example(self):
        # Step 4 at 0.35 of S_vt: 0.35 * 4.04787 = 1.41676 m2.
        self.assertAlmostEqual(
            vtl.ruddervator_sizing(S_VT_EXP)["ruddervator_area_total"],
            RUD_TOTAL_EXP, delta=1e-4)

    def test_per_surface_ruddervator_area_worked_example(self):
        # Step 4 equal split: half on each panel, 0.708378 m2.
        self.assertAlmostEqual(
            vtl.ruddervator_sizing(S_VT_EXP)[
                "ruddervator_area_per_surface"],
            RUD_PER_SURF_EXP, delta=1e-4)

    def test_half_fraction_scales_area_linearly(self):
        # Step 4 fraction scaling: 0.5 gives exactly half of S_vt.
        self.assertAlmostEqual(
            vtl.ruddervator_sizing(S_VT_EXP, 0.5)[
                "ruddervator_area_total"],
            0.5 * S_VT_EXP, delta=1e-12)

    def test_control_fraction_echoed_in_result(self):
        # Step 4 output contract: the applied fraction is returned.
        self.assertEqual(
            vtl.ruddervator_sizing(S_VT_EXP)["control_fraction"],
            vtl.RUDDERVATOR_FRACTION)

    def test_default_fraction_matches_module_constant(self):
        # Step 4 default: the documented 0.35 engineering default.
        self.assertEqual(vtl.RUDDERVATOR_FRACTION, 0.35)

    def test_zero_or_negative_total_area_raises(self):
        # Step 4 non-physical rejection: S_vt must be positive.
        with self.assertRaises(ValueError):
            vtl.ruddervator_sizing(0.0)
        with self.assertRaises(ValueError):
            vtl.ruddervator_sizing(-S_VT_EXP)

    def test_out_of_range_fraction_raises(self):
        # Step 4 non-physical rejection: fraction outside (0, 1).
        with self.assertRaises(ValueError):
            vtl.ruddervator_sizing(S_VT_EXP, 0.0)
        with self.assertRaises(ValueError):
            vtl.ruddervator_sizing(S_VT_EXP, -0.35)
        with self.assertRaises(ValueError):
            vtl.ruddervator_sizing(S_VT_EXP, 1.0)
        with self.assertRaises(ValueError):
            vtl.ruddervator_sizing(S_VT_EXP, 1.35)


class TestEffectiveVolumeRoundTrip(unittest.TestCase):
    """Workflow step 5, effective volume coefficient verification."""

    def test_round_trip_equivalent_areas_worked_example(self):
        # Step 5 projections recover the required equivalent areas.
        chk = vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP,
                                         V_H, V_V, S_REF, C_BAR, B,
                                         L_H, L_V)
        self.assertAlmostEqual(chk["s_h_eff"], S_H_EXP, delta=1e-9)
        self.assertAlmostEqual(chk["s_v_eff"], S_V_EXP, delta=1e-9)

    def test_round_trip_coefficients_worked_example(self):
        # Step 5 round trip recovers V_h = 0.7 and V_v = 0.04.
        chk = vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP,
                                         V_H, V_V, S_REF, C_BAR, B,
                                         L_H, L_V)
        self.assertAlmostEqual(chk["v_h_eff"], V_H, delta=1e-9)
        self.assertAlmostEqual(chk["v_v_eff"], V_V, delta=1e-12)

    def test_met_verdicts_true_for_sized_geometry(self):
        # Step 5 verdicts: both met flags True under the tolerance.
        chk = vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP,
                                         V_H, V_V, S_REF, C_BAR, B,
                                         L_H, L_V)
        self.assertTrue(chk["v_h_met"])
        self.assertTrue(chk["v_v_met"])

    def test_undersized_vtail_fails_met_verdicts(self):
        # Step 5 verdict flip: a 10% smaller S_vt fails both flags.
        chk = vtl.effective_volume_check(0.9 * S_VT_EXP, GAMMA_RAD_EXP,
                                         V_H, V_V, S_REF, C_BAR, B,
                                         L_H, L_V)
        self.assertAlmostEqual(chk["v_h_eff"], 0.63, delta=1e-9)
        self.assertFalse(chk["v_h_met"])
        self.assertFalse(chk["v_v_met"])

    def test_projection_identity_squares_sum_to_total(self):
        # Step 5 identity: s_h_eff^2 + s_v_eff^2 = s_vt^2 within 1e-12.
        chk = vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP,
                                         V_H, V_V, S_REF, C_BAR, B,
                                         L_H, L_V)
        self.assertAlmostEqual(
            chk["s_h_eff"] ** 2 + chk["s_v_eff"] ** 2,
            S_VT_EXP ** 2, delta=1e-12)

    def test_deterministic_repeat_call(self):
        # Step 5 determinism: identical inputs give identical outputs.
        first = vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP,
                                           V_H, V_V, S_REF, C_BAR, B,
                                           L_H, L_V)
        second = vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP,
                                            V_H, V_V, S_REF, C_BAR, B,
                                            L_H, L_V)
        self.assertEqual(first, second)

    def test_non_positive_inputs_raise(self):
        # Step 5 non-physical rejection of the verification inputs.
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(0.0, GAMMA_RAD_EXP, V_H, V_V,
                                       S_REF, C_BAR, B, L_H, L_V)
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(S_VT_EXP, 0.0, V_H, V_V,
                                       S_REF, C_BAR, B, L_H, L_V)
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP, 0.0,
                                       V_V, S_REF, C_BAR, B, L_H, L_V)
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP, V_H,
                                       V_V, 0.0, C_BAR, B, L_H, L_V)
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP, V_H,
                                       V_V, S_REF, C_BAR, 0.0, L_H, L_V)
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP, V_H,
                                       V_V, S_REF, C_BAR, B, 0.0, L_V)
        with self.assertRaises(ValueError):
            vtl.effective_volume_check(S_VT_EXP, GAMMA_RAD_EXP, V_H,
                                       V_V, S_REF, C_BAR, B, L_H, 0.0)


if __name__ == "__main__":
    unittest.main()
