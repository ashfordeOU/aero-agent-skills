"""Contract test for the rough-wall-skin-friction leaf (wave-40).

Exercises the numbered SKILL.md workflow for estimating the turbulent
skin-friction of a rough flat plate: step 1 fixes the flow state and the
fetch station, step 2 computes the smooth-wall turbulent baseline cf, step
3 converts the baseline into a friction velocity, step 4 forms the
sand-roughness reynolds number k+, step 5 classifies the k-plus-regime,
step 6 evaluates the fully-rough-cf correlation for the fetch, step 7
selects the operative coefficient without iteration and step 8 runs the
trip-criterion test on the roughness element, and step 9 confirms with
this deterministic contract test. All methods are offline, stdlib only,
deterministic and assert the prep-verified anchors of the leaf spec.
"""

import math
import unittest

from rough_wall_skin_friction_logic import (
    FULLY_ROUGH_K_PLUS,
    ROUGH_MIN_X_OVER_KS,
    SMOOTH_K_PLUS,
    TRIP_RE_K,
    _transitional_blend,
    cf_with_roughness,
    classify_regime,
    friction_velocity,
    rough_wall_cf,
    sand_roughness_reynolds,
    smooth_turbulent_cf,
    trip_criterion,
)

# Worked-example flow state from the spec: standard air at 60 m/s.
RHO = 1.225
U_INF = 60.0
MU = 1.81e-5
NU = 1.47755e-5
X_STATION = 2.0
RE_X = RHO * U_INF * X_STATION / MU  # 8.12155e6
CF_SMOOTH_ANCHOR = 2.45694e-3
U_TAU_ANCHOR = 2.10297


class ModuleConstantsTest(unittest.TestCase):
    """Step 9 of the SKILL.md workflow: module constant checks."""

    def test_kplus_band_constants_from_spec(self):
        """The k-plus-regime band constants of step 5 sit at the classic
        hydraulically smooth and fully rough thresholds of the spec."""
        self.assertEqual(SMOOTH_K_PLUS, 5.0)
        self.assertEqual(FULLY_ROUGH_K_PLUS, 70.0)

    def test_fetch_floor_and_trip_critical_constants(self):
        """The fully-rough-cf correlation floor and the trip-criterion
        critical value match the module constants of the spec."""
        self.assertEqual(ROUGH_MIN_X_OVER_KS, 100.0)
        self.assertEqual(TRIP_RE_K, 600.0)


class ClassifyRegimeTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: classify the surface regime."""

    def test_smooth_below_kplus_5(self):
        """A k-plus of 4.999 stays in the smooth regime of the step-5 band
        traverse, keeping the smooth-wall baseline operative."""
        self.assertEqual(classify_regime(4.999), "smooth")
        self.assertEqual(classify_regime(0.0), "smooth")

    def test_transitional_band_includes_boundaries(self):
        """The transitional band of the step-5 classification includes
        k-plus 5.0 and 70.0 inclusive, with 70.001 fully rough."""
        self.assertEqual(classify_regime(5.0), "transitional")
        self.assertEqual(classify_regime(70.0), "transitional")
        self.assertEqual(classify_regime(70.001), "fully-rough")

    def test_negative_kplus_raises_valueerror(self):
        """A negative roughness reynolds number is non-physical and is
        rejected by the step-5 classifier with ValueError."""
        with self.assertRaises(ValueError):
            classify_regime(-1.0)


class SmoothTurbulentCfTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: smooth-wall baseline traverse."""

    def test_worked_example_anchor(self):
        """The step-2 smooth-wall baseline at the example Reynolds number
        8.12155e6 returns the spec anchor 2.45694e-3 within 1e-8."""
        cf = smooth_turbulent_cf(RE_X)
        self.assertAlmostEqual(cf, CF_SMOOTH_ANCHOR, delta=1e-8)

    def test_monotone_decreasing_in_reynolds(self):
        """The step-2 1/7 power law is monotone decreasing: a higher local
        Reynolds number gives a smaller smooth-wall baseline."""
        cf_low = smooth_turbulent_cf(1e5)
        cf_high = smooth_turbulent_cf(1e7)
        self.assertGreater(cf_low, cf_high)

    def test_nonpositive_reynolds_rejected(self):
        """The step-2 baseline rejects a zero or negative local Reynolds
        number with ValueError."""
        with self.assertRaises(ValueError):
            smooth_turbulent_cf(0.0)
        with self.assertRaises(ValueError):
            smooth_turbulent_cf(-100.0)


class FrictionVelocityTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: convert baseline to u_tau."""

    def test_worked_example_anchor(self):
        """The step-3 friction velocity on the baseline 2.45694e-3 at 60
        m/s returns the spec anchor 2.10297 within 1e-5."""
        u_tau = friction_velocity(U_INF, CF_SMOOTH_ANCHOR)
        self.assertAlmostEqual(u_tau, U_TAU_ANCHOR, delta=1e-5)

    def test_closed_form_sqrt_identity(self):
        """The step-3 conversion obeys u_tau = u_inf * sqrt(cf / 2), the
        closed-form identity behind the friction velocity."""
        for cf in (1e-4, 2.45694e-3, 6.0e-3):
            expected = U_INF * math.sqrt(cf / 2.0)
            self.assertAlmostEqual(friction_velocity(U_INF, cf), expected,
                                   delta=1e-12)

    def test_nonphysical_inputs_rejected(self):
        """The step-3 conversion rejects a zero or negative speed and a
        zero coefficient with ValueError."""
        with self.assertRaises(ValueError):
            friction_velocity(0.0, CF_SMOOTH_ANCHOR)
        with self.assertRaises(ValueError):
            friction_velocity(U_INF, 0.0)
        with self.assertRaises(ValueError):
            friction_velocity(U_INF, -1.0)


class SandRoughnessReynoldsTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: form the roughness reynolds number."""

    def test_worked_example_anchors(self):
        """The step-4 sand-roughness reynolds number on the example flow
        returns k-plus 42.6984 for the 0.3 mm grain and 426.984 for the
        3 mm grain, each within 1e-3 of the spec anchors."""
        k_plus_a = sand_roughness_reynolds(RHO, U_TAU_ANCHOR, 3e-4, MU)
        k_plus_b = sand_roughness_reynolds(RHO, U_TAU_ANCHOR, 3e-3, MU)
        self.assertAlmostEqual(k_plus_a, 42.6984, delta=1e-3)
        self.assertAlmostEqual(k_plus_b, 426.984, delta=1e-3)

    def test_linearity_identity_tenfold_height(self):
        """The step-4 product is linear in the sand-roughness height: a
        10x k_s at fixed flow returns exactly 10x k-plus (identity)."""
        base = sand_roughness_reynolds(RHO, U_TAU_ANCHOR, 1e-4, MU)
        ten = sand_roughness_reynolds(RHO, U_TAU_ANCHOR, 1e-3, MU)
        self.assertAlmostEqual(ten, 10.0 * base, delta=1e-12)

    def test_nonphysical_inputs_rejected(self):
        """The step-4 product rejects non-positive density, friction
        velocity, sand-roughness height or viscosity with ValueError."""
        for kwargs in (
            dict(rho=0.0, u_tau=2.0, k_s=1e-4, mu=MU),
            dict(rho=RHO, u_tau=0.0, k_s=1e-4, mu=MU),
            dict(rho=RHO, u_tau=2.0, k_s=0.0, mu=MU),
            dict(rho=RHO, u_tau=2.0, k_s=-1e-4, mu=MU),
            dict(rho=RHO, u_tau=2.0, k_s=1e-4, mu=0.0),
        ):
            with self.assertRaises(ValueError):
                sand_roughness_reynolds(**kwargs)


class RoughWallCfTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: fully-rough-cf for the fetch."""

    def test_short_fetch_anchor(self):
        """The step-6 fully-rough-cf correlation at x = 2 m on the 3 mm
        grain (x / k_s 666.7) returns 6.87032e-3 within 1e-7."""
        self.assertAlmostEqual(rough_wall_cf(2.0, 3e-3), 6.87032e-3,
                               delta=1e-7)

    def test_longer_fetch_anchors(self):
        """The step-6 correlation falls as the fetch grows: 4.21783e-3 at
        x / k_s 6666.7 (x = 2 m on 0.3 mm), 5.37918e-3 at x = 6 m and
        4.21783e-3 at x = 20 m on the 3 mm grain, each within 1e-7."""
        self.assertAlmostEqual(rough_wall_cf(2.0, 3e-4), 4.21783e-3,
                               delta=1e-7)
        self.assertAlmostEqual(rough_wall_cf(6.0, 3e-3), 5.37918e-3,
                               delta=1e-7)
        self.assertAlmostEqual(rough_wall_cf(20.0, 3e-3), 4.21783e-3,
                               delta=1e-7)

    def test_monotone_decreasing_in_fetch_ratio(self):
        """The step-6 correlation is monotone decreasing in x / k_s, the
        fetch over the sand-roughness height."""
        self.assertGreater(rough_wall_cf(6.0, 3e-3), rough_wall_cf(20.0, 3e-3))
        self.assertGreater(rough_wall_cf(2.0, 3e-3), rough_wall_cf(2.0, 3e-4))

    def test_valueerror_below_fetch_floor_and_bad_inputs(self):
        """The step-6 correlation rejects a fetch ratio below the 100.0
        floor and zero or negative station or grain inputs."""
        with self.assertRaises(ValueError):
            rough_wall_cf(0.2997, 3e-3)  # x / k_s = 99.9
        with self.assertRaises(ValueError):
            rough_wall_cf(2.0, 0.0)
        with self.assertRaises(ValueError):
            rough_wall_cf(0.0, 3e-3)
        with self.assertRaises(ValueError):
            rough_wall_cf(2.0, -3e-3)


class CfWithRoughnessTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: select the operative coefficient."""

    def test_transitional_case_full_report(self):
        """The step-7 selection on the 0.3 mm grain classifies the
        k-plus-regime transitional and blends to cf_used 3.81178e-3,
        between the smooth baseline and the fully-rough-cf value."""
        report = cf_with_roughness(RE_X, X_STATION, 3e-4, RHO, U_INF, MU)
        self.assertEqual(report["regime"], "transitional")
        self.assertAlmostEqual(report["k_s_plus"], 42.6984, delta=1e-3)
        self.assertAlmostEqual(report["cf_smooth"], CF_SMOOTH_ANCHOR,
                               delta=1e-8)
        self.assertAlmostEqual(report["cf_used"], 3.81178e-3, delta=1e-7)

    def test_fully_rough_case_uses_correlation_directly(self):
        """The step-7 selection on the 3 mm grain is fully rough and uses
        the fully-rough-cf correlation value 6.87032e-3 directly."""
        report = cf_with_roughness(RE_X, X_STATION, 3e-3, RHO, U_INF, MU)
        self.assertEqual(report["regime"], "fully-rough")
        self.assertAlmostEqual(report["cf_used"], 6.87032e-3, delta=1e-7)
        self.assertEqual(report["cf_used"], report["cf_rough_or_iterated"])

    def test_smooth_case_keeps_smooth_baseline(self):
        """The step-7 selection on the 1e-5 m grain is hydraulically
        smooth and keeps cf_used equal to the smooth-wall baseline."""
        report = cf_with_roughness(RE_X, X_STATION, 1e-5, RHO, U_INF, MU)
        self.assertEqual(report["regime"], "smooth")
        self.assertAlmostEqual(report["k_s_plus"], 1.42328, delta=1e-4)
        self.assertEqual(report["cf_used"], report["cf_smooth"])

    def test_report_keys_exact(self):
        """The step-7 report dict exposes exactly the six documented keys
        regime, k_s_plus, cf_smooth, cf_rough_or_iterated, cf_used, note."""
        report = cf_with_roughness(RE_X, X_STATION, 3e-4, RHO, U_INF, MU)
        self.assertEqual(
            set(report.keys()),
            {"regime", "k_s_plus", "cf_smooth", "cf_rough_or_iterated",
             "cf_used", "note"},
        )

    def test_determinism_and_fixed_note_strings(self):
        """The step-7 chain is deterministic and each regime carries its
        fixed treatment note string on repeat runs."""
        first = cf_with_roughness(RE_X, X_STATION, 3e-4, RHO, U_INF, MU)
        second = cf_with_roughness(RE_X, X_STATION, 3e-4, RHO, U_INF, MU)
        self.assertEqual(first, second)
        rough = cf_with_roughness(RE_X, X_STATION, 3e-3, RHO, U_INF, MU)
        self.assertEqual(first["note"], second["note"])
        self.assertIn("blend", first["note"])
        self.assertIn("fully-rough", rough["note"])


class TransitionalBlendTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: blend endpoint identities."""

    def test_blend_endpoints_recover_anchors_exactly(self):
        """The step-7 log-linear blend returns the smooth baseline at
        k-plus 5.0 and the fully-rough-cf value at k-plus 70.0 exactly,
        the endpoint identity of the spec."""
        cf_smooth = 2.45694e-3
        cf_rough = 6.87032e-3
        self.assertAlmostEqual(
            _transitional_blend(cf_smooth, cf_rough, SMOOTH_K_PLUS),
            cf_smooth, delta=1e-15)
        self.assertAlmostEqual(
            _transitional_blend(cf_smooth, cf_rough, FULLY_ROUGH_K_PLUS),
            cf_rough, delta=1e-15)

    def test_blend_monotone_between_anchors(self):
        """The step-7 blend is monotone across the transitional band: a
        mid-band k-plus of 10 blends strictly between the anchors."""
        cf_smooth = 2.45694e-3
        cf_rough = 6.87032e-3
        mid = _transitional_blend(cf_smooth, cf_rough, 10.0)
        self.assertGreater(mid, cf_smooth)
        self.assertLess(mid, cf_rough)


class TripCriterionTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: trip-criterion verdict."""

    def test_rough_element_trips_the_layer(self):
        """The step-8 trip-criterion on the 0.3 mm element gives re_k
        1218.23, past the 600 critical value, so trip is expected."""
        verdict = trip_criterion(U_INF, 3e-4, NU)
        self.assertAlmostEqual(verdict["re_k"], 1218.23, delta=5e-3)
        self.assertTrue(verdict["trip_expected"])

    def test_small_element_stays_subcritical(self):
        """The step-8 trip-criterion on the 3e-5 m element gives re_k
        121.823, below the 600 critical value, so no trip is expected."""
        verdict = trip_criterion(U_INF, 3e-5, NU)
        self.assertAlmostEqual(verdict["re_k"], 121.823, delta=5e-3)
        self.assertFalse(verdict["trip_expected"])

    def test_critical_boundary_inclusive(self):
        """The step-8 comparison is inclusive: re_k exactly at the 600
        critical value still reports trip expected."""
        nu_chosen = 1.0e-4
        k_chosen = 1.0e-3  # u * k / nu = 600.0 exactly at u = 60
        verdict = trip_criterion(U_INF, k_chosen, nu_chosen)
        self.assertEqual(verdict["re_k"], 600.0)
        self.assertTrue(verdict["trip_expected"])

    def test_default_critical_constant_used(self):
        """The step-8 trip-criterion defaults re_k_crit to the module
        constant TRIP_RE_K of 600.0 when no critical value is passed."""
        verdict = trip_criterion(U_INF, 3e-4, NU)
        self.assertEqual(verdict["re_k_crit"], TRIP_RE_K)

    def test_nonphysical_inputs_rejected(self):
        """The step-8 trip-criterion rejects non-positive speed, element
        height, kinematic viscosity or critical value with ValueError."""
        for args in (
            (0.0, 3e-4, NU),
            (U_INF, 0.0, NU),
            (U_INF, 3e-4, 0.0),
            (U_INF, 3e-4, -NU),
        ):
            with self.assertRaises(ValueError):
                trip_criterion(*args)
        with self.assertRaises(ValueError):
            trip_criterion(U_INF, 3e-4, NU, re_k_crit=0.0)


if __name__ == "__main__":
    unittest.main()
