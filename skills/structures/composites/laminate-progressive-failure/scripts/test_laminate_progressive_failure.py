"""Contract test for laminate-progressive-failure.

Exercises the SKILL.md Workflow steps: step 1 (build the plane-stress
ply stiffness and the intact laminate A block with laminate_a_matrix),
step 2 (recover the mid-plane strains and the per-ply Tsai-Wu indices
of the intact laminate with per_ply_failure_indices, the
sibling-parity oracle surface), step 3 (run the ply-discount
progressive-failure march with progressive_failure_march to the
last-ply-failure ultimate load), step 4 (read the failure sequence,
the degraded laminate stiffness after each event, the
first-ply-failure load and the post-FPF reserve factor from the report
dict), step 5 (the [0]8 unidirectional reduction identity and the
optional strain-limit termination), and step 6 (ValueError rejection
of non-physical inputs). Stdlib unittest, offline, deterministic, no
RNG. Portable import: locate the sibling logic module by file path, no
machine-local sys.path.
"""

import importlib.util
import math
import os
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "laminate_progressive_failure_logic",
    os.path.join(_SCRIPTS, "laminate_progressive_failure_logic.py"),
)
lpf = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(lpf)


QI_ANGLES = lpf.QI_ANGLES
PLY_T_MM = lpf.PLY_T_MM
HC_ALLOW = (lpf.HC_XT, lpf.HC_XC, lpf.HC_YT, lpf.HC_YC, lpf.HC_S)
T300_ALLOW = (lpf.T300_XT, lpf.T300_XC, lpf.T300_YT, lpf.T300_YC, lpf.T300_S)


class TestLaminateProgressiveFailureWorkedExample(unittest.TestCase):
    """Step 1-4 of the workflow: the QI ply-discount march (SKILL.md
    Worked example), asserted within 1e-6 relative on the real module
    outputs (the sequential-ply-failure event loads, the degraded
    laminate stiffness, the ultimate-laminate-load and the post-FPF
    reserve factor of the post-fpf-load-redistribution analysis).
    """

    def setUp(self):
        self.report = lpf.progressive_failure_march(
            QI_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
            lpf.HC_G12, HC_ALLOW, 1.0, 0.0, 0.0
        )

    def test_step1_intact_a_matrix(self):
        """Step 1: laminate_a_matrix assembles the intact QI a_initial."""
        a = self.report["a_initial"]
        self.assertAlmostEqual(a[0], 76368.2177014268, delta=1e-3)
        self.assertAlmostEqual(a[1], 22607.3555300421, delta=1e-3)
        self.assertAlmostEqual(a[3], 76368.2177014268, delta=1e-3)
        self.assertAlmostEqual(a[5], 26880.4310856924, delta=1e-3)

    def test_step1_balanced_symmetric_coupling_vanishes(self):
        """Step 1: A16 and A26 vanish to machine precision (never
        asserted equal to 0.0, only bounded absolute)."""
        a = self.report["a_initial"]
        self.assertLess(abs(a[2]), 1e-6)
        self.assertLess(abs(a[4]), 1e-6)

    def test_step3_termination_last_ply_failure(self):
        """Step 3: the march terminates by last-ply-failure."""
        self.assertEqual(self.report["termination_reason"], "last-ply-failure")

    def test_step4_fpf_load(self):
        """Step 4: first-ply-failure load from the Tsai-Wu index at unity."""
        self.assertAlmostEqual(self.report["fpf_load_nx"], 276.697868003,
                               delta=1e-3)

    def test_step4_ultimate_load(self):
        """Step 4: last-ply-failure ultimate laminate load."""
        self.assertAlmostEqual(self.report["ultimate_load_nx"], 925.680039438,
                               delta=1e-3)

    def test_step4_post_fpf_reserve_factor(self):
        """Step 4: post-FPF reserve factor = ultimate / FPF."""
        self.assertAlmostEqual(self.report["post_fpf_reserve_factor"],
                               3.34545418119, delta=1e-6)

    def test_step4_qi_magnitude_gate(self):
        """Step 4: the FPF matrix event sits roughly a third of the
        0-ply fiber-failure ultimate load (receipt gate d band)."""
        ratio = self.report["fpf_load_nx"] / self.report["ultimate_load_nx"]
        self.assertGreaterEqual(ratio, 0.20)
        self.assertLessEqual(ratio, 0.35)
        self.assertAlmostEqual(ratio, 0.298913076025, delta=1e-6)

    def test_step4_event_sequence(self):
        """Step 4: the four sequential-ply-failure events, their loads,
        failed plies and matrix/fiber modes."""
        events = self.report["events"]
        self.assertEqual(len(events), 4)
        expected = [
            (276.697868003, [1, 6], ["matrix", "matrix"]),
            (347.807280322, [2, 3, 4, 5], ["matrix"] * 4),
            (925.680039438, [0, 7], ["fiber", "fiber"]),
            (925.680039438, [1, 2, 3, 4, 5, 6], ["fiber"] * 6),
        ]
        for event, (load_nx, plies, modes) in zip(events, expected):
            self.assertAlmostEqual(event["load_nx"], load_nx, delta=1e-3)
            self.assertEqual(event["failed_plies"], plies)
            self.assertEqual(event["modes"], modes)

    def test_step4_ply_discount_semantics(self):
        """Step 4: a matrix-mode event retains E1, the failed ply still
        stiffens the laminate as a tape; degraded a_after within
        1e-6 relative on the nonzero entries."""
        a_after1 = self.report["events"][0]["a_after"]
        self.assertAlmostEqual(a_after1[0], 73781.6780189717,
                               delta=1e-6 * 73781.6780189717)
        self.assertAlmostEqual(a_after1[3], 76165.4329903224,
                               delta=1e-6 * 76165.4329903224)

    def test_step4_final_cascade_zeroes_stiffness(self):
        """Step 4: the fiber-mode cascade of event 4 leaves zero
        laminate stiffness (no load-bearing tapes remain)."""
        a_after4 = self.report["events"][3]["a_after"]
        for value in a_after4:
            self.assertAlmostEqual(value, 0.0, delta=1e-6)

    def test_step4_degraded_stiffness_monotone(self):
        """Step 4: A11, A22 and A66 are non-increasing event to event
        (each is a sum of non-negative rotated-ply terms)."""
        prev = self.report["a_initial"]
        for event in self.report["events"]:
            a_after = event["a_after"]
            for idx in (0, 3, 5):
                self.assertLessEqual(a_after[idx], prev[idx] * (1.0 + 1e-9) + 1e-9)
            prev = a_after

    def test_report_key_set(self):
        """Report dict exposes exactly the documented keys."""
        expected_keys = {
            "ply_angles_deg", "ply_thickness_mm", "nx_ref", "ny_ref",
            "nxy_ref", "a_initial", "events", "fpf_event_index",
            "fpf_load_nx", "fpf_plies", "fpf_modes", "ultimate_event_index",
            "ultimate_load_nx", "post_fpf_reserve_factor", "termination_reason",
        }
        self.assertEqual(set(self.report.keys()), expected_keys)
        expected_event_keys = {
            "event", "load_multiplier", "load_nx", "failed_plies",
            "failed_angles_deg", "modes", "a_after",
        }
        for event in self.report["events"]:
            self.assertEqual(set(event.keys()), expected_event_keys)

    def test_determinism(self):
        """Two consecutive marches on the same inputs return identical
        dicts; no randomness anywhere."""
        report_b = lpf.progressive_failure_march(
            QI_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
            lpf.HC_G12, HC_ALLOW, 1.0, 0.0, 0.0
        )
        self.assertEqual(self.report, report_b)


class TestLaminateProgressiveFailureReductionIdentities(unittest.TestCase):
    """Step 5 of the workflow: the [0]8 unidirectional reduction
    identity and the optional strain-limit termination branch."""

    def test_ud8_single_fiber_event(self):
        """[0]8 under Nx reduces to the FPF identity: a single fiber
        event at Nx = Xt * h with FPF = last-ply = ultimate."""
        report = lpf.progressive_failure_march(
            lpf.UD8_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
            lpf.HC_G12, HC_ALLOW, 1.0, 0.0, 0.0
        )
        self.assertEqual(len(report["events"]), 1)
        self.assertEqual(report["events"][0]["modes"], ["fiber"] * 8)
        self.assertAlmostEqual(report["ultimate_load_nx"], 2700.0, delta=1e-3)
        self.assertAlmostEqual(report["fpf_load_nx"], 2700.0, delta=1e-3)
        self.assertAlmostEqual(report["post_fpf_reserve_factor"], 1.0, delta=1e-9)
        self.assertEqual(report["termination_reason"], "last-ply-failure")

    def test_ud8_strain_limit_branch(self):
        """Step 5: a strain limit at Xt / (2 E1) halts the [0]8 march
        before any ply event, at Nx = Xt h / 2."""
        strain_half = lpf.HC_XT / (2.0 * lpf.HC_E1)
        report = lpf.progressive_failure_march(
            lpf.UD8_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
            lpf.HC_G12, HC_ALLOW, 1.0, 0.0, 0.0, strain_limit=strain_half
        )
        self.assertEqual(len(report["events"]), 0)
        self.assertAlmostEqual(report["ultimate_load_nx"], 1350.0, delta=1e-3)
        self.assertEqual(report["termination_reason"], "strain-limit")

    def test_ud8_strain_limit_honored_only_when_binding(self):
        """Step 5: without a strain limit the same [0]8 inputs give the
        full fiber event, not the strain-limit termination."""
        report = lpf.progressive_failure_march(
            lpf.UD8_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
            lpf.HC_G12, HC_ALLOW, 1.0, 0.0, 0.0
        )
        self.assertEqual(report["termination_reason"], "last-ply-failure")
        self.assertEqual(len(report["events"]), 1)


class TestLaminateProgressiveFailureSiblingOracleParity(unittest.TestCase):
    """Step 2 of the workflow: per_ply_failure_indices on the intact
    T300/5208 QI laminate reproduces the sibling's published worked
    example, and the event-convention fence (this leaf's march event
    is where the index actually reaches unity, never the sibling's
    linearized k* scale)."""

    def test_step2_intact_per_ply_indices(self):
        """Step 2: per-ply Tsai-Wu indices at Nx = 100 N/mm on the
        T300/5208 QI stack, the sibling-parity surface."""
        a_t300 = lpf.laminate_a_matrix(
            QI_ANGLES, PLY_T_MM, lpf.T300_E1, lpf.T300_E2, lpf.T300_NU12,
            lpf.T300_G12
        )
        indices = lpf.per_ply_failure_indices(
            QI_ANGLES, a_t300, lpf.T300_E1, lpf.T300_E2, lpf.T300_NU12,
            lpf.T300_G12, T300_ALLOW, 100.0, 0.0, 0.0
        )
        expected = [0.025414833832501437, 0.31300691879363685,
                    0.1827462378567907, 0.1827462378567907,
                    0.1827462378567907, 0.1827462378567907,
                    0.31300691879363685, 0.025414833832501437]
        for got, want in zip(indices, expected):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(max(indices), 0.313006918794, delta=1e-6)

    def test_step2_event_convention_fence(self):
        """Step 2: the march's first event is NOT the sibling's
        linearized k* load (319.48175582 N/mm); instead the index of
        the intact laminate re-evaluated at the march FPF load reaches
        unity, the index-oracle equivalence check."""
        report = lpf.progressive_failure_march(
            QI_ANGLES, PLY_T_MM, lpf.T300_E1, lpf.T300_E2, lpf.T300_NU12,
            lpf.T300_G12, T300_ALLOW, 1.0, 0.0, 0.0
        )
        self.assertAlmostEqual(report["fpf_load_nx"], 276.119022337, delta=1e-3)
        self.assertNotAlmostEqual(report["fpf_load_nx"], 319.48175582, delta=1.0)

        a_t300 = lpf.laminate_a_matrix(
            QI_ANGLES, PLY_T_MM, lpf.T300_E1, lpf.T300_E2, lpf.T300_NU12,
            lpf.T300_G12
        )
        indices_at_fpf = lpf.per_ply_failure_indices(
            QI_ANGLES, a_t300, lpf.T300_E1, lpf.T300_E2, lpf.T300_NU12,
            lpf.T300_G12, T300_ALLOW, report["fpf_load_nx"], 0.0, 0.0
        )
        self.assertAlmostEqual(max(indices_at_fpf), 1.0, delta=1e-6)


class TestLaminateProgressiveFailureModeDiscrimination(unittest.TestCase):
    """Step 3 of the workflow: ply_discount_mode classifies fiber vs
    matrix mode at the event stress state."""

    def test_fiber_tension_boundary(self):
        self.assertEqual(
            lpf.ply_discount_mode(2700.0, 0.0, 0.0, 2700.0, 2000.0), "fiber"
        )

    def test_fiber_compression_boundary(self):
        self.assertEqual(
            lpf.ply_discount_mode(-2000.0, 0.0, 0.0, 2700.0, 2000.0), "fiber"
        )

    def test_matrix_mode_below_fiber_boundary(self):
        self.assertEqual(
            lpf.ply_discount_mode(-73.0, 13.6, 0.0, 2700.0, 2000.0), "matrix"
        )


class TestLaminateProgressiveFailureValueErrors(unittest.TestCase):
    """Step 6 of the workflow: ValueError rejection of non-physical
    inputs, with the real message prefixes."""

    def test_nonpositive_engineering_constant(self):
        with self.assertRaisesRegex(
            ValueError, "engineering constants E1, E2, G12, nu12 must be positive"
        ):
            lpf.laminate_a_matrix([0.0], PLY_T_MM, 0.0, lpf.HC_E2, lpf.HC_NU12,
                                  lpf.HC_G12)

    def test_singular_poisson_product(self):
        with self.assertRaisesRegex(
            ValueError, "nu12 nu21 >= 1 makes the plane-stress stiffness singular"
        ):
            lpf.q_matrix_from_constants(lpf.HC_E1, 1e12, 0.9, lpf.HC_G12)

    def test_empty_ply_stack(self):
        with self.assertRaisesRegex(
            ValueError, "plies_deg must contain at least one ply angle"
        ):
            lpf.laminate_a_matrix([], PLY_T_MM, lpf.HC_E1, lpf.HC_E2,
                                  lpf.HC_NU12, lpf.HC_G12)

    def test_nonpositive_ply_thickness(self):
        with self.assertRaisesRegex(
            ValueError, "ply thickness must be a positive number, got -0.125"
        ):
            lpf.laminate_a_matrix([0.0], -0.125, lpf.HC_E1, lpf.HC_E2,
                                  lpf.HC_NU12, lpf.HC_G12)

    def test_nonpositive_allowable(self):
        with self.assertRaisesRegex(
            ValueError, "allowables Xt, Xc, Yt, Yc, S must be positive"
        ):
            lpf.progressive_failure_march(
                QI_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
                lpf.HC_G12, (lpf.HC_XT, lpf.HC_XC, 0.0, lpf.HC_YC, lpf.HC_S),
                1.0, 0.0, 0.0
            )

    def test_zero_reference_resultant(self):
        with self.assertRaisesRegex(
            ValueError, "the reference resultant \\(Nx, Ny, Nxy\\) must be nonzero"
        ):
            lpf.progressive_failure_march(
                QI_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
                lpf.HC_G12, HC_ALLOW, 0.0, 0.0, 0.0
            )

    def test_nonpositive_strain_limit(self):
        with self.assertRaisesRegex(
            ValueError, "strain limit must be a positive number, got 0.0"
        ):
            lpf.progressive_failure_march(
                QI_ANGLES, PLY_T_MM, lpf.HC_E1, lpf.HC_E2, lpf.HC_NU12,
                lpf.HC_G12, HC_ALLOW, 1.0, 0.0, 0.0, strain_limit=0.0
            )

    def test_midplane_strains_non_positive_definite(self):
        with self.assertRaisesRegex(
            ValueError, "the laminate A block is not positive definite"
        ):
            lpf.midplane_strains((0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 1.0, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
