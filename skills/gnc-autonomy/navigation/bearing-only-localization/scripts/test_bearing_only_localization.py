"""Contract test for gnc-autonomy/navigation/bearing-only-localization.

Exercises the SKILL.md workflow of the leaf, whose numbered steps are:
1. Assemble the bearing-line measurement set (observer positions, measured
   bearing per line, per-line 1-sigma bearing error; at least two
   observers with distinct lines), 2. Form the linearized bearing
   equations and solve the equal-angle first pass with weights
   1/sigma^2 (wls_fix pass 1), 3. Run the Stansfield distance-weighted
   second pass with weights 1/(sigma^2 * r^2) for the final fix and the
   fix covariance (wls_fix pass 2), 4. Read the 1-sigma error ellipse of
   the fix covariance (error_ellipse), 5. Compute the per-bearing
   residual angles and their RMS (residual_angles_deg,
   residual_rms_deg), 6. Assess the observer geometry and the
   observer-geometry dilution verdict (geometry_dilution_factor,
   dilution_verdict), 7. Optionally refine the fix in three dimensions
   with azimuth and elevation lines (refine_3d_gauss_newton), 8. Close
   out with this deterministic contract test.

Worked geometry: three observers on a 1 km right triangle at (0, 0),
(1000, 0) and (0, 1000) m localize a stationary emitter near (300, 400)
m. Measured bearings are the exact observer-to-emitter bearings corrupted
by fixed offsets (+0.5, -0.3, +0.2 deg), sigma 0.5 deg per line. All
numeric asserts are order-safe tolerances (assertAlmostEqual delta or
math.isclose); exact equality is used only for literal constants and
deterministic round-trips. Offline, deterministic, stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bearing_only_localization_logic as bol


class BearingOnlyLocalizationContractTest(unittest.TestCase):
    """Contract assertions for the bearing-only-localization leaf module."""

    def setUp(self):
        """Workflow step 1 data: observer triangle, truth and noisy bearings."""
        self.observers = [(0.0, 0.0), (1000.0, 0.0), (0.0, 1000.0)]
        self.truth = (300.0, 400.0)
        self.offsets_deg = [0.5, -0.3, 0.2]
        self.exact_bearings = [
            bol.bearing_deg(ox, oy, self.truth[0], self.truth[1])
            for (ox, oy) in self.observers
        ]
        self.bearings_deg = [
            exact + off
            for exact, off in zip(self.exact_bearings, self.offsets_deg)
        ]
        self.sigma_deg = [0.5, 0.5, 0.5]

    # ------------------------------------------------------------------
    # Workflow step 1: bearing angles and wrappers
    # ------------------------------------------------------------------
    def test_bearing_deg_angles_and_range(self):
        """Step 1 bearing_deg maps the four cardinal directions to
        0/90/180/270 degrees and the diagonal to 45 degrees, always in
        [0, 360): a point below the +x axis yields a value just under
        360 degrees, never a negative angle."""
        self.assertAlmostEqual(bol.bearing_deg(0.0, 0.0, 1.0, 0.0), 0.0, delta=1e-12)
        self.assertAlmostEqual(bol.bearing_deg(0.0, 0.0, 0.0, 1.0), 90.0, delta=1e-12)
        self.assertAlmostEqual(bol.bearing_deg(0.0, 0.0, -1.0, 0.0), 180.0, delta=1e-12)
        self.assertAlmostEqual(bol.bearing_deg(0.0, 0.0, 0.0, -1.0), 270.0, delta=1e-12)
        self.assertAlmostEqual(bol.bearing_deg(0.0, 0.0, 1.0, 1.0), 45.0, delta=1e-12)
        west_below = bol.bearing_deg(0.0, 0.0, 1.0, -1e-9)
        self.assertGreaterEqual(west_below, 0.0)
        self.assertLess(west_below, 360.0)
        self.assertAlmostEqual(west_below, 360.0, delta=1e-6)
        south_west = bol.bearing_deg(0.0, 0.0, -1.0, -1.0)
        self.assertAlmostEqual(south_west, 225.0, delta=1e-12)

    def test_bearing_deg_raises_on_non_finite(self):
        """Step 1 bearing_deg rejects non-finite coordinates with
        ValueError, protecting the measurement set assembly."""
        for args in ((float("nan"), 0.0, 1.0, 0.0), (0.0, 0.0, 1.0, float("inf"))):
            with self.assertRaises(ValueError):
                bol.bearing_deg(*args)

    def test_wrap180_deg_bounds(self):
        """Step 5 wrappers: wrap180_deg folds angles into [-180, 180),
        mapping 180 to -180 and multiples of 360 to zero."""
        self.assertAlmostEqual(bol.wrap180_deg(190.0), -170.0, delta=1e-12)
        self.assertAlmostEqual(bol.wrap180_deg(-190.0), 170.0, delta=1e-12)
        self.assertAlmostEqual(bol.wrap180_deg(180.0), -180.0, delta=1e-12)
        self.assertAlmostEqual(bol.wrap180_deg(-180.0), -180.0, delta=1e-12)
        self.assertAlmostEqual(bol.wrap180_deg(360.0), 0.0, delta=1e-12)

    # ------------------------------------------------------------------
    # Workflow steps 2 and 3: Stansfield weighted least squares fix
    # ------------------------------------------------------------------
    def test_worked_example_pass1_fix(self):
        """Step 2, the equal-angle first pass (wls_fix pass 1) on the
        noisy 1 km triangle, returns the anchor fix (299.178622,
        405.821689) m within 1e-6 m."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        self.assertAlmostEqual(fix["pass1_x_m"], 299.178622, delta=1e-6)
        self.assertAlmostEqual(fix["pass1_y_m"], 405.821689, delta=1e-6)

    def test_worked_example_final_fix_and_iterations(self):
        """Step 3, the Stansfield distance-weighted second pass, moves
        the fix to the anchor (299.150033, 405.988514) m within 1e-6 m
        and reports exactly two passes."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        self.assertAlmostEqual(fix["x_m"], 299.150033, delta=1e-6)
        self.assertAlmostEqual(fix["y_m"], 405.988514, delta=1e-6)
        self.assertEqual(fix["iterations"], 2)

    def test_worked_example_fix_errors_under_50m(self):
        """Steps 2-3 fix errors against the truth (300, 400) match the
        anchors 5.879347 m (pass 1) and 6.048532 m (pass 2) within 1e-6
        and stay below the 50 m ceiling for sub-degree noise on 1 km
        baselines."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        err1 = math.hypot(fix["pass1_x_m"] - 300.0, fix["pass1_y_m"] - 400.0)
        err2 = math.hypot(fix["x_m"] - 300.0, fix["y_m"] - 400.0)
        self.assertAlmostEqual(err1, 5.879347, delta=1e-6)
        self.assertAlmostEqual(err2, 6.048532, delta=1e-6)
        self.assertLess(err1, 50.0)
        self.assertLess(err2, 50.0)

    def test_worked_example_pass1_ranges(self):
        """Step 3 pass-1 observer-to-fix ranges r_i match the printed
        values 504.182, 809.841 and 665.249 m within 1e-3 m."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        self.assertEqual(len(fix["ranges_m"]), 3)
        for actual, expected in zip(fix["ranges_m"], (504.182, 809.841, 665.249)):
            self.assertAlmostEqual(actual, expected, delta=1e-3)

    def test_worked_example_covariance_entries(self):
        """Step 3 fix covariance C = (A^T W A)^-1 carries the anchor
        entries 16.195587, 1.677004 and 25.693501 m^2 within 1e-6."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        cov = fix["covariance"]
        self.assertAlmostEqual(cov[0][0], 16.195587, delta=1e-6)
        self.assertAlmostEqual(cov[0][1], 1.677004, delta=1e-6)
        self.assertAlmostEqual(cov[1][0], 1.677004, delta=1e-6)
        self.assertAlmostEqual(cov[1][1], 25.693501, delta=1e-6)

    def test_weighting_pull_high_sigma(self):
        """Step 3 range re-weighting sanity: raising sigma of line 1 to
        10 deg with the others at 0.5 pulls the fix toward the
        intersection of the remaining lines, anchor (300.194425,
        404.784548) m within 1e-6 m."""
        sigma = [10.0, 0.5, 0.5]
        fix = bol.wls_fix(self.observers, self.bearings_deg, sigma)
        self.assertAlmostEqual(fix["x_m"], 300.194425, delta=1e-6)
        self.assertAlmostEqual(fix["y_m"], 404.784548, delta=1e-6)
        err = math.hypot(fix["x_m"] - 300.0, fix["y_m"] - 400.0)
        self.assertAlmostEqual(err, 4.788497, delta=1e-6)

    def test_unweighted_fix_fields(self):
        """Steps 2-3 without sigma_deg the solver runs the geometry-only
        unweighted pass once, reports iterations 1, ranges_m None, and
        matches the equal-angle pass-1 fix of the weighted call."""
        fix_u = bol.wls_fix(self.observers, self.bearings_deg)
        fix_w = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        self.assertEqual(fix_u["iterations"], 1)
        self.assertIsNone(fix_u["ranges_m"])
        self.assertAlmostEqual(fix_u["x_m"], fix_u["pass1_x_m"], delta=1e-12)
        self.assertAlmostEqual(fix_u["x_m"], fix_w["pass1_x_m"], delta=1e-9)
        self.assertAlmostEqual(fix_u["y_m"], fix_w["pass1_y_m"], delta=1e-9)
        cov = fix_u["covariance"]
        self.assertAlmostEqual(cov[0][1], cov[1][0], delta=1e-15)

    def test_noiseless_exactness(self):
        """Steps 2 and 5 closed-form identity: on exact bearings the fix
        recovers the emitter (300, 400) within 1e-6 m and every
        per-bearing residual at the truth is zero within 1e-12 deg."""
        fix = bol.wls_fix(self.observers, self.exact_bearings, self.sigma_deg)
        self.assertAlmostEqual(fix["x_m"], 300.0, delta=1e-6)
        self.assertAlmostEqual(fix["y_m"], 400.0, delta=1e-6)
        residuals = bol.residual_angles_deg(
            self.observers, self.exact_bearings, 300.0, 400.0
        )
        for residual in residuals:
            self.assertAlmostEqual(residual, 0.0, delta=1e-12)
        self.assertAlmostEqual(
            bol.residual_rms_deg(self.observers, self.exact_bearings, 300.0, 400.0),
            0.0,
            delta=1e-12,
        )

    def test_pass_invariance_on_equal_ranges(self):
        """Steps 2-3 identity: observers equidistant from the noiseless
        fix with equal sigma give identical pass-1 and pass-2 fixes,
        because the range weights become a constant factor of the angle
        weights. Four observers on an exact 1000 m circle around
        (300, 400) localize the center."""
        cx, cy = 300.0, 400.0
        circle = [(cx + 1000.0, cy), (cx, cy + 1000.0), (cx - 1000.0, cy), (cx, cy - 1000.0)]
        exact = [bol.bearing_deg(ox, oy, cx, cy) for (ox, oy) in circle]
        fix = bol.wls_fix(circle, exact, [0.5, 0.5, 0.5, 0.5])
        self.assertAlmostEqual(fix["x_m"], cx, delta=1e-6)
        self.assertAlmostEqual(fix["y_m"], cy, delta=1e-6)
        self.assertAlmostEqual(fix["x_m"], fix["pass1_x_m"], delta=1e-6)
        self.assertAlmostEqual(fix["y_m"], fix["pass1_y_m"], delta=1e-6)
        for r in fix["ranges_m"]:
            self.assertAlmostEqual(r, 1000.0, delta=1e-6)

    # ------------------------------------------------------------------
    # Workflow step 4: 1-sigma error ellipse of the fix covariance
    # ------------------------------------------------------------------
    def test_worked_example_error_ellipse(self):
        """Step 4 error_ellipse on the pass-2 covariance returns the
        anchor semi-major 5.097147 m, semi-minor 3.988506 m and
        orientation 80.275145 deg within 1e-6."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        ellipse = bol.error_ellipse(fix["covariance"])
        self.assertAlmostEqual(ellipse["semi_major_m"], 5.097147, delta=1e-6)
        self.assertAlmostEqual(ellipse["semi_minor_m"], 3.988506, delta=1e-6)
        self.assertAlmostEqual(ellipse["orientation_deg"], 80.275145, delta=1e-6)
        self.assertGreaterEqual(ellipse["orientation_deg"], -180.0)
        self.assertLess(ellipse["orientation_deg"], 180.0)

    def test_ellipse_trace_and_det_identity(self):
        """Step 4 eigenvalue identities for the pass-2 covariance:
        trace(C) = a^2 + b^2 and det(C) = a^2 * b^2 within 1e-12
        relative, keeping the error ellipse consistent with the fix
        covariance."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        cov = fix["covariance"]
        ellipse = bol.error_ellipse(cov)
        a_sq = ellipse["semi_major_m"] ** 2
        b_sq = ellipse["semi_minor_m"] ** 2
        trace_c = cov[0][0] + cov[1][1]
        det_c = cov[0][0] * cov[1][1] - cov[0][1] * cov[1][0]
        self.assertTrue(math.isclose(trace_c, a_sq + b_sq, rel_tol=1e-12))
        self.assertTrue(math.isclose(det_c, a_sq * b_sq, rel_tol=1e-12))
        self.assertLessEqual(b_sq, a_sq + 1e-12)

    def test_sigma_scaling_doubles_semi_axes(self):
        """Step 4 scaling identity: multiplying every sigma by the common
        factor 2 divides all weights by 4, so the covariance scales by 4
        and both 1-sigma ellipse semi-axes scale by exactly 2.000000
        within 1e-9 relative."""
        fix1 = bol.wls_fix(self.observers, self.bearings_deg, [0.5, 0.5, 0.5])
        fix2 = bol.wls_fix(self.observers, self.bearings_deg, [1.0, 1.0, 1.0])
        el1 = bol.error_ellipse(fix1["covariance"])
        el2 = bol.error_ellipse(fix2["covariance"])
        self.assertTrue(
            math.isclose(el2["semi_major_m"] / el1["semi_major_m"], 2.0, rel_tol=1e-9)
        )
        self.assertTrue(
            math.isclose(el2["semi_minor_m"] / el1["semi_minor_m"], 2.0, rel_tol=1e-9)
        )

    def test_error_ellipse_axis_aligned_cases(self):
        """Step 4 orientation convention: a diagonal covariance with the
        larger entry on x gives orientation 0 deg, on y gives 90 deg, and
        the rotated matrix [[3, 1], [1, 3]] gives a major axis of 2 m at
        45 deg with semi-minor sqrt(2) m."""
        el_x = bol.error_ellipse([[4.0, 0.0], [0.0, 1.0]])
        self.assertAlmostEqual(el_x["semi_major_m"], 2.0, delta=1e-12)
        self.assertAlmostEqual(el_x["semi_minor_m"], 1.0, delta=1e-12)
        self.assertAlmostEqual(el_x["orientation_deg"], 0.0, delta=1e-12)
        el_y = bol.error_ellipse([[1.0, 0.0], [0.0, 4.0]])
        self.assertAlmostEqual(el_y["orientation_deg"], 90.0, delta=1e-12)
        el_45 = bol.error_ellipse([[3.0, 1.0], [1.0, 3.0]])
        self.assertAlmostEqual(el_45["semi_major_m"], 2.0, delta=1e-12)
        self.assertAlmostEqual(el_45["semi_minor_m"], math.sqrt(2.0), delta=1e-12)
        self.assertAlmostEqual(el_45["orientation_deg"], 45.0, delta=1e-12)

    def test_error_ellipse_indefinite_valueerror(self):
        """Step 4 ValueError rejection: error_ellipse on the indefinite
        matrix [[1, 2], [2, 1]] (negative eigenvalue) raises."""
        with self.assertRaises(ValueError):
            bol.error_ellipse([[1.0, 2.0], [2.0, 1.0]])

    # ------------------------------------------------------------------
    # Workflow step 5: per-bearing residual angles and RMS
    # ------------------------------------------------------------------
    def test_worked_example_residual_angles(self):
        """Step 5 per-bearing residuals, measured minus the bearing
        predicted at the final fix, match the anchors +0.014509,
        +0.037982 and +0.034776 deg within 1e-6, and each wrapped
        residual lies in [-180, 180) degrees."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        residuals = bol.residual_angles_deg(
            self.observers, self.bearings_deg, fix["x_m"], fix["y_m"]
        )
        for actual, expected in zip(residuals, (0.014509, 0.037982, 0.034776)):
            self.assertAlmostEqual(actual, expected, delta=1e-6)
            self.assertGreaterEqual(actual, -180.0)
            self.assertLess(actual, 180.0)

    def test_worked_example_residual_rms(self):
        """Step 5 the RMS of the wrapped per-bearing residual angles is
        the anchor 0.030890 deg within 1e-6, well below the 0.5 deg
        sigma: after the fix every line keeps only a small angular
        leftover."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        rms = bol.residual_rms_deg(self.observers, self.bearings_deg, fix["x_m"], fix["y_m"])
        self.assertAlmostEqual(rms, 0.030890, delta=1e-6)

    def test_residual_functions_valueerrors(self):
        """Step 5 ValueError rejections shared with wls_fix: fewer than
        two observers, count mismatch and non-finite bearings all raise
        in residual_angles_deg and residual_rms_deg."""
        fix = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        with self.assertRaises(ValueError):
            bol.residual_angles_deg([(0.0, 0.0)], [10.0], fix["x_m"], fix["y_m"])
        with self.assertRaises(ValueError):
            bol.residual_angles_deg(
                self.observers, [10.0, 20.0], fix["x_m"], fix["y_m"]
            )
        with self.assertRaises(ValueError):
            bol.residual_rms_deg(
                self.observers, [10.0, float("nan"), 30.0], fix["x_m"], fix["y_m"]
            )

    # ------------------------------------------------------------------
    # Workflow step 6: observer-geometry dilution
    # ------------------------------------------------------------------
    def test_worked_example_dilution_and_verdict(self):
        """Step 6 the observer-geometry dilution factor of the three-line
        worked set is the anchor 0.957062 within 1e-6, below 1 because
        the normals spread around the emitter beat the orthogonal
        two-line baseline, with the good observer spread verdict."""
        d = bol.geometry_dilution_factor(self.observers, self.bearings_deg)
        self.assertAlmostEqual(d, 0.957062, delta=1e-6)
        self.assertLess(d, 1.0)
        self.assertEqual(bol.dilution_verdict(d), "good observer spread")

    def test_dilution_orthogonal_pair_equals_one(self):
        """Step 6 identity: any orthogonal pair of bearing lines gives
        d = 1 exactly within 1e-12 (an orthogonal pair is the two-line
        baseline the dilution factor is measured against)."""
        orthogonal = [(0.0, 0.0), (1000.0, 0.0)]
        bearings = [0.0, 90.0]
        d = bol.geometry_dilution_factor(orthogonal, bearings)
        self.assertAlmostEqual(d, 1.0, delta=1e-12)

    def test_dilution_verdict_thresholds(self):
        """Step 6 dilution verdict thresholds: d <= 1.05 is good observer
        spread, d < 2.5 is moderate, and d >= 2.5 is poor (near-parallel
        bearing lines)."""
        self.assertEqual(bol.dilution_verdict(1.0), "good observer spread")
        self.assertEqual(bol.dilution_verdict(1.05), "good observer spread")
        self.assertEqual(bol.dilution_verdict(1.1), "moderate")
        self.assertEqual(bol.dilution_verdict(2.49), "moderate")
        self.assertEqual(bol.dilution_verdict(2.5), "poor (near-parallel bearing lines)")
        self.assertEqual(bol.dilution_verdict(100.0), "poor (near-parallel bearing lines)")

    def test_dilution_valueerror_parallel_lines(self):
        """Step 6 ValueError rejection: all-parallel bearing lines give a
        singular normal Gram matrix and geometry_dilution_factor raises."""
        with self.assertRaises(ValueError):
            bol.geometry_dilution_factor([(0.0, 0.0), (1000.0, 0.0)], [45.0, 45.0])

    # ------------------------------------------------------------------
    # Workflow step 7: bounded 3-D Gauss-Newton refinement
    # ------------------------------------------------------------------
    def test_refine3d_worked_example(self):
        """Step 7 the bounded Gauss-Newton refinement of exact azimuth
        and elevation lines from three observers at z = 0 recovers the
        emitter (300, 400, 50) m within 1e-6 m from the start
        (280, 380, 60) in at most 30 iterations with a small residual
        norm."""
        observers = [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (0.0, 1000.0, 0.0)]
        azimuths = [
            math.degrees(math.atan2(400.0 - oy, 300.0 - ox)) for (ox, oy, _) in observers
        ]
        elevations = [
            math.degrees(math.atan2(50.0, math.hypot(300.0 - ox, 400.0 - oy)))
            for (ox, oy, _) in observers
        ]
        result = bol.refine_3d_gauss_newton(
            observers, azimuths, elevations, 280.0, 380.0, 60.0
        )
        self.assertAlmostEqual(result["x_m"], 300.0, delta=1e-6)
        self.assertAlmostEqual(result["y_m"], 400.0, delta=1e-6)
        self.assertAlmostEqual(result["z_m"], 50.0, delta=1e-6)
        self.assertLessEqual(result["iterations"], 30)
        self.assertLess(result["residual_norm"], 1e-6)

    def test_refine3d_valueerrors(self):
        """Step 7 ValueError rejections of the 3-D refinement: fewer than
        three observers, azimuth count mismatch, an elevation outside
        [-90, 90] and max_iters below 1 all raise."""
        observers = [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (0.0, 1000.0, 0.0)]
        az = [10.0, 20.0, 30.0]
        el = [5.0, 5.0, 5.0]
        with self.assertRaises(ValueError):
            bol.refine_3d_gauss_newton(observers[:2], az[:2], el[:2], 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            bol.refine_3d_gauss_newton(observers, az[:2], el, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            bol.refine_3d_gauss_newton(observers, az, [5.0, 95.0, 5.0], 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            bol.refine_3d_gauss_newton(observers, az, [-95.0, 5.0, 5.0], 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            bol.refine_3d_gauss_newton(observers, az, el, 0.0, 0.0, 0.0, max_iters=0)

    def test_refine3d_no_convergence_within_max_iters(self):
        """Step 7 bounded refinement: a single Gauss-Newton iteration
        from a start far from the emitter cannot reach the 1e-9 step
        tolerance, so max_iters=1 raises the non-convergence ValueError
        instead of iterating unbounded."""
        observers = [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (0.0, 1000.0, 0.0)]
        az = [53.13010235415598, 150.25511870305738, 296.565051177078]
        el = [5.710593137499643, 3.5486705345395554, 4.262916633073113]
        with self.assertRaises(ValueError):
            bol.refine_3d_gauss_newton(
                observers, az, el, 0.0, 0.0, 0.0, max_iters=1
            )

    # ------------------------------------------------------------------
    # Workflow step 8: ValueError contract and determinism
    # ------------------------------------------------------------------
    def test_wls_valueerror_few_observers(self):
        """Step 1 ValueError rejection: fewer than two observers cannot
        form a bearing-line fix."""
        with self.assertRaises(ValueError):
            bol.wls_fix([(0.0, 0.0)], [10.0], [0.5])
        with self.assertRaises(ValueError):
            bol.wls_fix([], [], [])

    def test_wls_valueerror_length_mismatch(self):
        """Step 1 ValueError rejection: a bearing count or sigma count
        that disagrees with the observer list raises."""
        with self.assertRaises(ValueError):
            bol.wls_fix(self.observers, [10.0, 20.0], self.sigma_deg)
        with self.assertRaises(ValueError):
            bol.wls_fix(self.observers, self.bearings_deg, [0.5, 0.5])

    def test_wls_valueerror_nonfinite_inputs(self):
        """Step 1 ValueError rejection: non-finite observer coordinates
        or bearing angles raise before any solve."""
        with self.assertRaises(ValueError):
            bol.wls_fix(
                [(0.0, float("nan")), (1000.0, 0.0), (0.0, 1000.0)],
                self.bearings_deg,
                self.sigma_deg,
            )
        with self.assertRaises(ValueError):
            bol.wls_fix(
                self.observers, [10.0, float("inf"), 30.0], self.sigma_deg
            )

    def test_wls_valueerror_sigma_invalid(self):
        """Step 1 ValueError rejection: a zero, negative or non-finite
        sigma (1-sigma bearing error) raises."""
        for sigma in ([0.0, 0.5, 0.5], [-0.5, 0.5, 0.5], [0.5, float("nan"), 0.5]):
            with self.assertRaises(ValueError):
                bol.wls_fix(self.observers, self.bearings_deg, sigma)

    def test_wls_valueerror_parallel_bearing_lines(self):
        """Step 2 ValueError rejection: all-parallel bearing lines give a
        singular normal matrix and wls_fix raises."""
        with self.assertRaises(ValueError):
            bol.wls_fix([(0.0, 0.0), (1000.0, 0.0)], [45.0, 45.0], [0.5, 0.5])

    def test_wls_valueerror_duplicate_observers_identical_bearings(self):
        """Step 2 ValueError rejection: duplicate observer positions
        reporting identical bearings stack identical rows and the
        singular normal matrix raises."""
        with self.assertRaises(ValueError):
            bol.wls_fix([(0.0, 0.0), (0.0, 0.0)], [30.0, 30.0], [0.5, 0.5])

    def test_wls_valueerror_observer_at_pass1_fix(self):
        """Step 3 ValueError rejection: an observer within 1e-9 m of the
        pass-1 fix makes the pass-2 range weight undefined, so the two
        lines intersecting exactly on the observer raise."""
        observers = [(0.0, 0.0), (1000.0, 0.0)]
        with self.assertRaises(ValueError):
            bol.wls_fix(observers, [60.0, 180.0], [0.5, 0.5])

    def test_determinism_repeated_runs_identical(self):
        """Step 8 determinism: the closed-form solve uses no RNG, so
        repeated runs return byte-identical floats."""
        first = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        second = bol.wls_fix(self.observers, self.bearings_deg, self.sigma_deg)
        self.assertEqual(first, second)
        ellipse_first = bol.error_ellipse(first["covariance"])
        ellipse_second = bol.error_ellipse(second["covariance"])
        self.assertEqual(ellipse_first, ellipse_second)


if __name__ == "__main__":
    unittest.main()
