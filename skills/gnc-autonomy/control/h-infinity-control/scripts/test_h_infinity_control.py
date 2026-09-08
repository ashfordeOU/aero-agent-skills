"""Contract test for the h-infinity-control leaf.

Exercises the SKILL.md Workflow steps 1-8: fixing the loop under
review, plant G and candidate controller K as given inputs (step 1),
the closed-loop channel assembly over the common characteristic
polynomial with the S + T = 1 identity (step 2), the Routh-Hurwitz
first-column stability verdict of the loop (step 3), the sensitivity
weight and control-effort weight built from their corner parameters
(step 4), the H-infinity norm gamma-iteration search over the
imaginary-axis frequency response (step 5), the weighted norms W1 S
and W2 KS and the achieved gamma and bound verdict of the
mixed-sensitivity weighting (step 6), the worst-case bound semantics,
the velocity asymptote and the flat band (step 7), and this
deterministic contract test itself (step 8). Tolerant asserts only:
no exact-float equality on computed sums, math.isclose and
assertAlmostEqual everywhere.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h_infinity_control_logic as h

G_NUM = [1.0]
G_DEN = [1.0, 1.0, 0.0]
K_NUM = [8.0, 8.0]
K_DEN = [1.0, 10.0, 16.0]
KV = 0.5


def worked_channels():
    """loop_channels of the worked loop G = 1/(s(s+1)), K = 8(s+1)/((s+2)(s+8))."""
    return h.loop_channels(G_NUM, G_DEN, K_NUM, K_DEN)


def worked_weights():
    """sensitivity_weight(2.5, 0.3, 1e-3) and control_weight(0.1, 2.0, 1.0)."""
    return h.sensitivity_weight(2.5, 0.3, 1e-3), h.control_weight(0.1, 2.0, 1.0)


def rel_err(got, want):
    return abs(got - want) / abs(want)


class TestModuleConstants(unittest.TestCase):
    """Steps 5 and 8 of the SKILL.md workflow: the module constants that pin
    the gamma-iteration search over the imaginary-axis frequency response."""

    def test_pinned_constants(self):
        self.assertEqual(h.ROUTH_PIVOT_EPS, 1e-12)
        self.assertEqual(h.ROUTH_ROW_EPS, 1e-14)
        self.assertEqual(h.SWEEP_X_MIN, 1e-8)
        self.assertEqual(h.SWEEP_X_MAX, 1e8)
        self.assertEqual(h.SWEEP_POINTS, 801)
        self.assertEqual(h.BISECT_ITER, 200)
        self.assertEqual(h.ROOT_TOL_REL, 1e-13)

    def test_sweep_bounds_ordering(self):
        # The imaginary-axis sweep in x = w^2 spans SWEEP_X_MIN to
        # SWEEP_X_MAX, i.e. w in [1e-4, 1e4] rad/s.
        self.assertTrue(h.SWEEP_X_MIN < h.SWEEP_X_MAX)
        self.assertEqual(h.SWEEP_X_MIN ** 0.5, 1e-4)
        self.assertEqual(h.SWEEP_X_MAX ** 0.5, 1e4)


class TestRouthStability(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the Routh-Hurwitz first-column
    stability verdict of the loop on the characteristic polynomial."""

    def test_worked_char_stable(self):
        self.assertTrue(h.routh_stable([1.0, 11.0, 26.0, 24.0, 8.0]))

    def test_cubic_triple_root_stable(self):
        self.assertTrue(h.routh_stable([1.0, 3.0, 3.0, 1.0]))

    def test_jw_axis_poles_unstable(self):
        self.assertFalse(h.routh_stable([1.0, 0.0, 1.0]))

    def test_mixed_unstable(self):
        self.assertFalse(h.routh_stable([1.0, 1.0, 1.0, 1.0]))

    def test_negative_leading_normalization_and_edges(self):
        # Sign normalization makes (-1)(s+1)^3 stable; a constant
        # polynomial with a positive coefficient is stable and with a
        # non-positive one is not; an empty list is not stable.
        self.assertTrue(h.routh_stable([-1.0, -3.0, -3.0, -1.0]))
        self.assertTrue(h.routh_stable([5.0]))
        self.assertFalse(h.routh_stable([0.0]))
        self.assertFalse(h.routh_stable([-5.0]))
        self.assertFalse(h.routh_stable([]))


class TestLoopChannelsAndIdentity(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the channel assembly over the common
    characteristic polynomial and the S + T = 1 identity."""

    def test_worked_char_poly(self):
        ch = worked_channels()
        for got, want in zip(ch["char_poly"], [1.0, 11.0, 26.0, 24.0, 8.0]):
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_channel_keys_denominators_and_s_num(self):
        ch = worked_channels()
        self.assertEqual(
            sorted(ch.keys()),
            ["char_poly", "ks_den", "ks_num", "s_den", "s_num", "t_den", "t_num"],
        )
        for den_key in ("s_den", "t_den", "ks_den"):
            for got, want in zip(ch[den_key], ch["char_poly"]):
                self.assertAlmostEqual(got, want, delta=1e-12)
        # s_num = g_den k_den by the defining relation.
        gd_kd = h._poly_mul(G_DEN, K_DEN)
        for got, want in zip(ch["s_num"], gd_kd):
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_ks_num_equals_k_num_g_den(self):
        ch = worked_channels()
        ks = h._poly_mul(K_NUM, G_DEN)
        for got, want in zip(ch["ks_num"], ks):
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_st_identity_polynomial(self):
        ch = worked_channels()
        s_plus_t = h._poly_add(ch["s_num"], ch["t_num"])
        for got, want in zip(s_plus_t, ch["char_poly"]):
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_st_identity_pointwise(self):
        ch = worked_channels()
        for w in (0.1, 1.0, 5.0):
            s_val = h.eval_transfer(ch["s_num"], ch["s_den"], complex(0.0, w))
            t_val = h.eval_transfer(ch["t_num"], ch["t_den"], complex(0.0, w))
            self.assertTrue(abs(s_val + t_val - 1.0) < 1e-9, f"w={w}")


class TestEvalTransfer(unittest.TestCase):
    """Steps 1 and 2 of the SKILL.md workflow: Horner evaluation of a
    transfer function numerator over denominator at a complex frequency."""

    def test_denominator_zero_raises(self):
        with self.assertRaises(ValueError) as ctx:
            h.eval_transfer([1.0], [1.0, -1.0], complex(1.0, 0.0))
        self.assertIn("transfer function denominator is zero at s = (1+0j)", str(ctx.exception))

    def test_eval_dc_gain(self):
        val = h.eval_transfer([1.0, 2.0], [1.0, 1.0], complex(0.0, 0.0))
        self.assertAlmostEqual(val.real, 2.0, delta=1e-12)
        self.assertAlmostEqual(val.imag, 0.0, delta=1e-12)


class TestWeightClosedForms(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the sensitivity weight and the
    control-effort weight built from their corner parameters, with the
    closed-form magnitudes at the DC point, the corner and the
    high-frequency limit."""

    def test_weight_coefficients(self):
        w1, w2 = worked_weights()
        for got, want in zip(w1[0], [0.4, 0.3]):
            self.assertAlmostEqual(got, want, delta=1e-12)
        for got, want in zip(w1[1], [1.0, 0.0003]):
            self.assertAlmostEqual(got, want, delta=1e-12)
        for got, want in zip(w2[0], [1.0, 0.2]):
            self.assertAlmostEqual(got, want, delta=1e-12)
        for got, want in zip(w2[1], [1.0, 2.0]):
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_w1_dc_level(self):
        w1, _ = worked_weights()
        mag = abs(h.eval_transfer(w1[0], w1[1], complex(0.0, 0.0)))
        self.assertAlmostEqual(mag, 1000.0, delta=1e-6)

    def test_w1_high_frequency_level(self):
        w1, _ = worked_weights()
        mag = abs(h.eval_transfer(w1[0], w1[1], complex(0.0, 1e8)))
        self.assertAlmostEqual(mag, 0.4, delta=1e-9)

    def test_w2_dc_and_high_frequency_levels(self):
        _, w2 = worked_weights()
        mag_dc = abs(h.eval_transfer(w2[0], w2[1], complex(0.0, 0.0)))
        mag_hf = abs(h.eval_transfer(w2[0], w2[1], complex(0.0, 1e8)))
        self.assertAlmostEqual(mag_dc, 0.1, delta=1e-12)
        self.assertAlmostEqual(mag_hf, 1.0, delta=1e-9)

    def test_w1_corner_magnitude_formula(self):
        # |W1(j wb)| = sqrt(1 + 1/ms^2)/sqrt(1 + as_^2) at ms = 2.5, as_ = 1e-3.
        formula = math.sqrt(1.0 + 1.0 / 2.5 ** 2) / math.sqrt(1.0 + 1e-3 ** 2)
        w1, _ = worked_weights()
        mag = abs(h.eval_transfer(w1[0], w1[1], complex(0.0, 0.3)))
        self.assertAlmostEqual(mag, formula, delta=1e-9)
        # The spec-printed decimal 1.0770329614269009 is sqrt(1 + 1/ms^2)
        # alone; the true corner magnitude divides by sqrt(1 + as_^2) and
        # equals 1.077032422910824 within 1e-9 relative.
        self.assertAlmostEqual(mag, 1.077032422910824, delta=1e-9)


class TestHinfinityNormMachinery(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the gamma-iteration H-infinity norm
    search on the stationary equation of the imaginary-axis response,
    checked against closed-form identity cases."""

    def test_first_order_dc_carry(self):
        norm = h.hinfinity_norm([1.0], [1.0, 1.0])
        self.assertAlmostEqual(norm, 1.0, delta=1e-9)

    def test_first_order_zero_at_origin(self):
        norm = h.hinfinity_norm([1.0, 2.0], [1.0, 1.0])
        self.assertAlmostEqual(norm, 2.0, delta=1e-9)

    def test_resonant_peak_closed_form(self):
        norm = h.hinfinity_norm([1.0], [1.0, 0.2, 1.0])
        closed_form = 1.0 / (2.0 * 0.1 * math.sqrt(1.0 - 0.1 ** 2))
        self.assertAlmostEqual(norm, closed_form, delta=1e-9)
        self.assertAlmostEqual(norm, 5.025189076296056, delta=1e-9)

    def test_properness_rejection(self):
        with self.assertRaises(ValueError) as ctx:
            h.hinfinity_norm([1.0, 0.0, 0.0], [1.0, 1.0])
        self.assertIn("transfer function must be proper", str(ctx.exception))

    def test_unstable_denominator_rejection(self):
        with self.assertRaises(ValueError) as ctx:
            h.hinfinity_norm([1.0], [1.0, 0.0, -1.0])
        self.assertIn(
            "H-infinity norm requires a strictly stable denominator", str(ctx.exception)
        )


class TestWorkedLoopNorms(unittest.TestCase):
    """Steps 5 and 6 of the SKILL.md workflow: the weighted norms of the
    worked loop and the achieved gamma and bound verdict of the
    mixed-sensitivity weighting."""

    def test_worked_weighted_and_unweighted_norms(self):
        # Step 5: ||W1 S||_inf and ||W2 KS||_inf of the worked loop,
        # plus the unweighted ||S||_inf and ||T||_inf for context.
        ch = worked_channels()
        w1, w2 = worked_weights()
        w1s_norm = h.hinfinity_norm(
            h._poly_mul(w1[0], ch["s_num"]), h._poly_mul(w1[1], ch["s_den"])
        )
        self.assertAlmostEqual(w1s_norm, 0.6210716713301313, delta=1e-9)
        w2ks_norm = h.hinfinity_norm(
            h._poly_mul(w2[0], ch["ks_num"]), h._poly_mul(w2[1], ch["ks_den"])
        )
        self.assertAlmostEqual(w2ks_norm, 0.7779822129233023, delta=1e-9)
        s_norm = h.hinfinity_norm(ch["s_num"], ch["s_den"])
        self.assertAlmostEqual(s_norm, 1.2187761291690518, delta=1e-9)
        # The type-1 tracking identity |T(j0)| = 1 carries the norm of T.
        t_norm = h.hinfinity_norm(ch["t_num"], ch["t_den"])
        self.assertAlmostEqual(t_norm, 1.0, delta=1e-9)

    def test_mixed_sensitivity_gamma_pass(self):
        ch = worked_channels()
        w1, w2 = worked_weights()
        res = h.mixed_sensitivity_gamma(ch, w1, w2)
        self.assertAlmostEqual(res["w1s_norm"], 0.6210716713301313, delta=1e-9)
        self.assertAlmostEqual(res["w2ks_norm"], 0.7779822129233023, delta=1e-9)
        self.assertAlmostEqual(res["gamma"], 0.7779822129233023, delta=1e-9)
        self.assertTrue(res["verdict"])

    def test_fail_sibling_gamma_false(self):
        # Demanding weight wb = 1.0 drives the flat band to wb/Kv = 2.0:
        # the weighted sensitivity violates the unit bound.
        ch = worked_channels()
        _, w2 = worked_weights()
        w1_fail = h.sensitivity_weight(2.5, 1.0, 1e-3)
        res = h.mixed_sensitivity_gamma(ch, w1_fail, w2)
        self.assertAlmostEqual(res["w1s_norm"], 1.9979285867334802, delta=1e-9)
        self.assertAlmostEqual(res["w2ks_norm"], 0.7779822129233023, delta=1e-9)
        self.assertAlmostEqual(res["gamma"], 1.9979285867334802, delta=1e-9)
        self.assertFalse(res["verdict"])
        self.assertAlmostEqual(2.0 - res["gamma"], 2.0 - 1.9979285867334802, delta=0.005)


class TestWorstCaseBoundSemantics(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the computed norm never
    underestimates the imaginary-axis response of the weighted
    sensitivity channel, and the low-frequency asymptotes hold."""

    @staticmethod
    def coarse_max(ch, w1):
        wd = h._poly_mul(w1[1], ch["s_den"])
        wn = h._poly_mul(w1[0], ch["s_num"])
        mx = 0.0
        for k in range(101):
            w = 1e-4 * (1e8) ** (k / 100.0)
            mag = abs(h.eval_transfer(wn, wd, complex(0.0, w)))
            mx = max(mx, mag)
        dc_mag = abs(h.eval_transfer(wn, wd, complex(0.0, 0.0)))
        return max(mx, dc_mag)

    def test_coarse_sweep_below_norm_both_loops(self):
        # Step 7: on a 101-point geometric sweep of |W1S(jw)| from 1e-4
        # to 1e4 rad/s the sweep maximum is at most the computed norm,
        # for the pass loop and the fail sibling alike.
        ch = worked_channels()
        for w1 in (worked_weights()[0], h.sensitivity_weight(2.5, 1.0, 1e-3)):
            norm = h.hinfinity_norm(
                h._poly_mul(w1[0], ch["s_num"]), h._poly_mul(w1[1], ch["s_den"])
            )
            self.assertTrue(norm >= self.coarse_max(ch, w1) * (1.0 - 1e-9))
        # Real anchor: the pass-loop sweep maximum 0.6210695376871158
        # sits below the norm 0.6210716713301313.
        w1_pass, _ = worked_weights()
        self.assertAlmostEqual(self.coarse_max(ch, w1_pass), 0.6210695376871158, delta=1e-9)

    def test_velocity_asymptote(self):
        # |S(jw)| Kv/w tends to 1 as w tends to 0 with the type-1 velocity
        # constant Kv = k z/(p1 p2) = 0.5.
        ch = worked_channels()
        for w, want in ((1e-3, 0.9999993828127061), (1e-2, 0.999938283310422)):
            s_val = h.eval_transfer(ch["s_num"], ch["s_den"], complex(0.0, w))
            ratio = abs(s_val) * KV / w
            self.assertAlmostEqual(ratio, want, delta=1e-9)

    def test_flat_band_samples(self):
        # Where |W1| ~ wb/w and S ~ jw/Kv the product |W1S| is flat at
        # wb/Kv = 0.6 and the computed norm sits just above the band.
        ch = worked_channels()
        w1, _ = worked_weights()
        wd = h._poly_mul(w1[1], ch["s_den"])
        wn = h._poly_mul(w1[0], ch["s_num"])
        for w, want in (
            (0.01, 0.5997464724424371),
            (0.05, 0.6003939878705405),
            (0.1, 0.601583811863733),
        ):
            mag = abs(h.eval_transfer(wn, wd, complex(0.0, w)))
            self.assertAlmostEqual(mag, want, delta=1e-9)
            self.assertAlmostEqual(mag, 0.6, delta=5e-3)
        norm = h.hinfinity_norm(wn, wd)
        self.assertTrue(norm > 0.601583811863733)


class TestValueErrors(unittest.TestCase):
    """Steps 1 and 4 of the SKILL.md workflow: ValueError rejection of
    non-positive weight corner parameters naming the parameter."""

    def test_sensitivity_weight_rejections(self):
        with self.assertRaises(ValueError) as ctx:
            h.sensitivity_weight(0.0, 0.3, 1e-3)
        self.assertIn("ms", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            h.sensitivity_weight(2.5, -1.0, 1e-3)
        self.assertIn("wb", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            h.sensitivity_weight(2.5, 0.3, 0.0)
        self.assertIn("as_", str(ctx.exception))

    def test_control_weight_rejections(self):
        with self.assertRaises(ValueError) as ctx:
            h.control_weight(0.0, 2.0, 1.0)
        self.assertIn("a2", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            h.control_weight(0.1, 0.0, 1.0)
        self.assertIn("wbc", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            h.control_weight(0.1, 2.0, -1.0)
        self.assertIn("mu2", str(ctx.exception))


class TestDeterminism(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the mixed-sensitivity review is
    deterministic, identical run to run."""

    def test_gamma_identical_across_runs(self):
        ch = worked_channels()
        w1, w2 = worked_weights()
        first = h.mixed_sensitivity_gamma(ch, w1, w2)
        second = h.mixed_sensitivity_gamma(ch, w1, w2)
        self.assertEqual(first, second)

    def test_norm_identical_across_runs(self):
        ch = worked_channels()
        w1, _ = worked_weights()
        first = h.hinfinity_norm(h._poly_mul(w1[0], ch["s_num"]), h._poly_mul(w1[1], ch["s_den"]))
        second = h.hinfinity_norm(h._poly_mul(w1[0], ch["s_num"]), h._poly_mul(w1[1], ch["s_den"]))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
