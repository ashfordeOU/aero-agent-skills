#!/usr/bin/env python3
"""Gate 3 contract test: numerical optimization algorithms.

Exercises scripts/optimization_algorithms_logic.py (stdlib unittest,
offline). Contract: golden-section search on a unimodal bracket
(interval shrinks by 1/PHI per step, step tolerance b - a < tol,
ValueError for an empty or non-unimodal bracket), gradient descent
with an Armijo backtracking line search (sufficient decrease
f(x - s*g) <= f(x) - 1e-4*s*||g||**2, gradient tolerance
||grad(x)|| < tol), the derivative-free Nelder-Mead simplex method
(reflection, expansion, contraction, shrink; deterministic initial
simplex; function-spread tolerance max(f) - min(f) < tol), and
Newton's method applied to the derivative x_{k+1} = x_k -
fp(x_k)/fpp(x_k) (derivative tolerance abs(fp(x)) < tol). Analytic
anchors: golden section on f(x) = (x - 3)**2 + 2 over [0, 10] gives
x = 3.0, f = 2.0 in 34 interval updates; gradient descent on
f(x, y) = x**2 + 2*y**2 from (1, 1) reaches (0, 0); Nelder-Mead on
f(x) = (x - 2)**2 + 1 from 0.0 reaches x = 2.0 and on the Rosenbrock
function reaches (1, 1); Newton on the derivative from x0 = 10.0
lands on x = 3.0 in one step. ValueError when the bracket is empty or
not unimodal, when a learning rate is non-positive, when the Armijo
line search fails or the gradient tolerance is not reached within
max_iter, when the second derivative is zero at a Newton step, when
an objective value or iterate is not finite, and when tol <= 0 or
max_iter < 1.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import optimization_algorithms_logic as oa  # noqa: E402


def f_quad_1d(x):
    """f(x) = (x - 3)**2 + 2, minimum 2 at x = 3."""
    return (x - 3.0) ** 2 + 2.0


def f_quad_2d(x):
    """f(x, y) = x**2 + 2*y**2, minimum 0 at (0, 0)."""
    return x[0] ** 2 + 2.0 * x[1] ** 2


def grad_quad_2d(x):
    """Gradient (2x, 4y) of the 2D quadratic."""
    return (2.0 * x[0], 4.0 * x[1])


def f_rosenbrock(x):
    """Rosenbrock f = (x-1)**2 + 100*(y - x**2)**2, minimum 0 at (1, 1)."""
    return (x[0] - 1.0) ** 2 + 100.0 * (x[1] - x[0] ** 2) ** 2


def grad_rosenbrock(x):
    """Analytic gradient of the Rosenbrock function."""
    return (
        2.0 * (x[0] - 1.0) - 400.0 * x[0] * (x[1] - x[0] ** 2),
        200.0 * (x[1] - x[0] ** 2),
    )


class GoldenSectionTest(unittest.TestCase):
    def test_quadratic_anchor(self):
        # f(x) = (x - 3)**2 + 2 on [0, 10]: minimum at x = 3, f = 2;
        # tol = 1e-6 gives x accurate to about 1e-6 in 34 interval
        # updates (interval shrinks by 1/PHI per step).
        x_min, f_min, iterations = oa.golden_section_minimize(
            f_quad_1d, 0.0, 10.0, tol=1e-6, max_iter=200
        )
        self.assertAlmostEqual(x_min, 3.0, places=4)
        self.assertAlmostEqual(f_min, 2.0, delta=1e-6)
        self.assertEqual(iterations, 34)

    def test_left_interior_minimum(self):
        # f(x) = (x + 5)**2 + 1 on [-10, 0]: interior minimum at -5.
        x_min, f_min, iterations = oa.golden_section_minimize(
            lambda x: (x + 5.0) ** 2 + 1.0, -10.0, 0.0, tol=1e-6
        )
        self.assertAlmostEqual(x_min, -5.0, places=4)
        self.assertAlmostEqual(f_min, 1.0, delta=1e-6)
        self.assertEqual(iterations, 34)

    def test_reversed_bracket_swapped(self):
        # a > b is swapped, not rejected: same minimum as [0, 10].
        x_min, _, _ = oa.golden_section_minimize(f_quad_1d, 10.0, 0.0)
        self.assertAlmostEqual(x_min, 3.0, places=4)

    def test_tight_tolerance(self):
        # tol = 1e-9 needs more halvings: the interval widens the
        # iteration count. Near the flat minimum the function values
        # at the trial points round to the same double (f is 2.0 to
        # within 1e-16), so comparisons tie and the bracket drifts;
        # the accuracy floor is about 1e-8 for this anchor.
        x_min, f_min, iterations = oa.golden_section_minimize(
            f_quad_1d, 0.0, 10.0, tol=1e-9, max_iter=200
        )
        self.assertAlmostEqual(x_min, 3.0, delta=1e-7)
        self.assertAlmostEqual(f_min, 2.0, delta=1e-8)
        self.assertGreaterEqual(iterations, 40)

    def test_empty_bracket_raises(self):
        with self.assertRaises(ValueError):
            oa.golden_section_minimize(f_quad_1d, 2.0, 2.0)

    def test_non_unimodal_bracket_raises(self):
        # f(x) = x is monotonic: the midpoint is not a local low point.
        with self.assertRaises(ValueError):
            oa.golden_section_minimize(lambda x: x, 0.0, 10.0)
        # Minimum at the endpoint x = 0 of [-1, 0] is not bracketed.
        with self.assertRaises(ValueError):
            oa.golden_section_minimize(lambda x: x * x, -1.0, 0.0)

    def test_bad_tolerance_and_max_iter_raise(self):
        for bad_tol in (0.0, -1e-8, True, "1e-6"):
            with self.subTest(tol=bad_tol):
                with self.assertRaises(ValueError):
                    oa.golden_section_minimize(f_quad_1d, 0.0, 10.0, tol=bad_tol)
        for bad_n in (0, -3, 2.5, True):
            with self.subTest(max_iter=bad_n):
                with self.assertRaises(ValueError):
                    oa.golden_section_minimize(f_quad_1d, 0.0, 10.0, max_iter=bad_n)

    def test_convergence_failure_raises(self):
        # tol = 1e-15 needs about 80 halvings of [0, 10]; max_iter = 5
        # cannot reach it.
        with self.assertRaises(ValueError):
            oa.golden_section_minimize(
                f_quad_1d, 0.0, 10.0, tol=1e-15, max_iter=5
            )

    def test_non_finite_and_bad_callable_raise(self):
        for bad in (float("nan"), float("inf")):
            with self.subTest(endpoint=bad):
                with self.assertRaises(ValueError):
                    oa.golden_section_minimize(f_quad_1d, bad, 10.0)
                with self.assertRaises(ValueError):
                    oa.golden_section_minimize(f_quad_1d, 0.0, bad)
        with self.assertRaises(ValueError):
            oa.golden_section_minimize("not callable", 0.0, 10.0)


class GradientDescentTest(unittest.TestCase):
    def test_quadratic_2d_anchor(self):
        # f(x, y) = x**2 + 2*y**2 from (1, 1) with the backtracking
        # line search converges to the minimum (0, 0) with f = 0.
        x_min, f_min, iterations = oa.gradient_descent(
            f_quad_2d, grad_quad_2d, (1.0, 1.0), lr=1.0, tol=1e-6
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertAlmostEqual(x_min[0], 0.0, places=6)
        self.assertAlmostEqual(x_min[1], 0.0, places=6)
        self.assertLess(f_min, 1e-12)
        self.assertLessEqual(iterations, 10)

    def test_scalar_1d_mode(self):
        # Scalar x0 and a scalar objective f(x) = x**2 from x = 3 with
        # a fixed learning rate 0.1 converge to 0.
        x_min, f_min, iterations = oa.gradient_descent(
            lambda x: x * x, lambda x: 2.0 * x, 3.0, lr=0.1,
            tol=1e-8, max_iter=10000
        )
        assert not isinstance(x_min, tuple)  # scalar mode returns a float
        self.assertLess(abs(x_min), 1e-5)
        self.assertLess(f_min, 1e-10)
        self.assertGreater(iterations, 10)  # linear fixed-step convergence

    def test_1d_input_shape_modes(self):
        # A length-1 vector x0 selects tuple calling (f(x) uses x[0]),
        # and a 1D grad may return a length-1 sequence instead of a
        # scalar; both converge to 0 on f = x**2 from x = 3.
        x_min, f_min, _ = oa.gradient_descent(
            lambda x: x[0] ** 2, lambda x: (2.0 * x[0],), (3.0,),
            lr=0.1, tol=1e-8, max_iter=10000
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertLess(abs(x_min[0]), 1e-5)
        self.assertLess(f_min, 1e-10)
        x_min, _, _ = oa.gradient_descent(
            lambda x: x * x, lambda x: [2.0 * x], 3.0, lr=0.1,
            tol=1e-8, max_iter=10000
        )
        assert not isinstance(x_min, tuple)  # scalar mode returns a float
        self.assertLess(abs(x_min), 1e-5)

    def test_stationary_start_returns_immediately(self):
        # Zero gradient at the start is converged with zero iterations.
        x_min, f_min, iterations = oa.gradient_descent(
            f_quad_2d, lambda x: (0.0, 0.0), (5.0, -2.0), lr=0.5
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertEqual(x_min, (5.0, -2.0))
        self.assertEqual(f_min, f_quad_2d((5.0, -2.0)))
        self.assertEqual(iterations, 0)

    def test_rosenbrock_anchor(self):
        # Steepest descent with backtracking from (0, 0) reaches the
        # Rosenbrock minimum (1, 1): the narrow curved valley makes it
        # slow (about 15000 steps at tol = 1e-6), so the budget is
        # raised explicitly.
        x_min, f_min, iterations = oa.gradient_descent(
            f_rosenbrock, grad_rosenbrock, (0.0, 0.0), lr=1.0,
            tol=1e-6, max_iter=20000
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertLess(abs(x_min[0] - 1.0), 1e-3)
        self.assertLess(abs(x_min[1] - 1.0), 1e-3)
        self.assertLess(f_min, 1e-6)
        self.assertLess(iterations, 20000)

    def test_bad_learning_rate_raises(self):
        for bad_lr in (0.0, -0.5, True, float("nan"), float("inf")):
            with self.subTest(lr=bad_lr):
                with self.assertRaises(ValueError):
                    oa.gradient_descent(f_quad_2d, grad_quad_2d, (1.0, 1.0),
                                        lr=bad_lr)

    def test_bad_x0_raises(self):
        for bad_x0 in ((), "ab", True, (1.0, float("nan")), (1.0, float("inf"))):
            with self.subTest(x0=bad_x0):
                with self.assertRaises(ValueError):
                    oa.gradient_descent(f_quad_2d, grad_quad_2d, bad_x0, lr=0.1)

    def test_gradient_contract_raises(self):
        # Gradient length must match x, entries must be finite.
        with self.assertRaises(ValueError):
            oa.gradient_descent(f_quad_2d, lambda x: (1.0,), (1.0, 1.0), lr=0.1)
        with self.assertRaises(ValueError):
            oa.gradient_descent(lambda x: x[0], lambda x: (float("nan"),),
                                (1.0,), lr=0.1)
        with self.assertRaises(ValueError):
            oa.gradient_descent(f_quad_2d, None, (1.0, 1.0), lr=0.1)

    def test_convergence_failure_raises(self):
        # tol = 1e-15 with max_iter = 5 cannot be reached from x = 3.
        with self.assertRaises(ValueError):
            oa.gradient_descent(lambda x: x * x, lambda x: 2.0 * x, 3.0,
                                lr=0.1, tol=1e-15, max_iter=5)
        # A non-finite objective value at a trial point raises too.
        with self.assertRaises(ValueError):
            oa.gradient_descent(lambda x: float("nan"), lambda x: (1.0, 1.0),
                                (1.0, 1.0), lr=0.1)


class NelderMeadTest(unittest.TestCase):
    def test_quadratic_1d_anchor(self):
        # f(x) = (x - 2)**2 + 1 from x0 = 0: the 2-vertex simplex
        # converges to x = 2, f = 1 (function-spread tolerance
        # max(f) - min(f) < 1e-6 puts x within about 1e-3).
        x_min, f_min, iterations = oa.nelder_mead(
            lambda x: (x - 2.0) ** 2 + 1.0, 0.0, tol=1e-6
        )
        assert not isinstance(x_min, tuple)  # scalar mode returns a float
        self.assertLess(abs(x_min - 2.0), 1e-3)
        self.assertLess(abs(f_min - 1.0), 1e-5)
        self.assertLess(iterations, 1000)

    def test_deterministic_and_seed_ignored(self):
        # No randomness: identical results across calls and seeds.
        first = oa.nelder_mead(lambda x: (x - 2.0) ** 2 + 1.0, 0.0)
        second = oa.nelder_mead(lambda x: (x - 2.0) ** 2 + 1.0, 0.0)
        seeded = oa.nelder_mead(lambda x: (x - 2.0) ** 2 + 1.0, 0.0, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(first, seeded)

    def test_vector_length_one_mode(self):
        # A length-1 vector x0 selects tuple calling: f(x) uses x[0].
        x_min, f_min, iterations = oa.nelder_mead(
            lambda x: (x[0] - 2.0) ** 2 + 1.0, (0.0,)
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertLess(abs(x_min[0] - 2.0), 1e-3)
        self.assertLess(abs(f_min - 1.0), 1e-5)
        self.assertLess(iterations, 1000)

    def test_quadratic_2d_anchor(self):
        # f(x, y) = x**2 + 2*y**2 from (1, 1) converges to (0, 0).
        x_min, f_min, iterations = oa.nelder_mead(f_quad_2d, (1.0, 1.0))
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertLess(abs(x_min[0]), 2e-3)
        self.assertLess(abs(x_min[1]), 2e-3)
        self.assertLess(f_min, 1e-5)
        self.assertLess(iterations, 1000)

    def test_rosenbrock_anchor(self):
        # Nelder-Mead needs no derivatives and handles the curved
        # Rosenbrock valley from (0, 0), converging near (1, 1).
        x_min, f_min, iterations = oa.nelder_mead(
            f_rosenbrock, (0.0, 0.0), tol=1e-6
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertLess(abs(x_min[0] - 1.0), 2e-3)
        self.assertLess(abs(x_min[1] - 1.0), 2e-3)
        self.assertLess(f_min, 1e-5)
        self.assertLess(iterations, 1000)

    def test_constant_objective_returns_immediately(self):
        # Zero function spread is converged with zero iterations.
        x_min, f_min, iterations = oa.nelder_mead(
            lambda x: 5.0, (1.0, 2.0)
        )
        assert isinstance(x_min, tuple)  # vector mode returns a tuple
        self.assertEqual(x_min, (1.0, 2.0))
        self.assertEqual(f_min, 5.0)
        self.assertEqual(iterations, 0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            oa.nelder_mead(lambda x: x * x, ())
        with self.assertRaises(ValueError):
            oa.nelder_mead(lambda x: x * x, 0.0, tol=0.0)
        with self.assertRaises(ValueError):
            oa.nelder_mead(lambda x: x * x, 0.0, max_iter=0)
        with self.assertRaises(ValueError):
            oa.nelder_mead(None, 0.0)

    def test_non_finite_objective_raises(self):
        with self.assertRaises(ValueError):
            oa.nelder_mead(lambda x: float("nan"), 0.0)

    def test_convergence_failure_raises(self):
        # A linear objective has no interior minimum; the simplex never
        # collapses to the function-spread tolerance within max_iter.
        with self.assertRaises(ValueError):
            oa.nelder_mead(lambda x: x, 0.0, tol=1e-12, max_iter=3)


class NewtonMinimizeTest(unittest.TestCase):
    def test_quadratic_anchor(self):
        # Newton on f' for f(x) = (x - 3)**2 + 2 from x0 = 10 lands
        # exactly on x = 3 in one step (the update is exact for a
        # quadratic).
        x_min, f_min, iterations = oa.newton_1d_minimize(
            f_quad_1d, lambda x: 2.0 * (x - 3.0), lambda x: 2.0, 10.0
        )
        self.assertAlmostEqual(x_min, 3.0, places=9)
        self.assertAlmostEqual(f_min, 2.0, places=9)
        self.assertEqual(iterations, 1)

    def test_quadratic_from_any_start(self):
        # The same quadratic from x0 = 0 (left of the minimum) and from
        # x0 = -7 also reach x = 3 in one step: Newton on a quadratic
        # derivative is exact from any start.
        for start in (0.0, -7.0):
            with self.subTest(x0=start):
                x_min, _, iterations = oa.newton_1d_minimize(
                    f_quad_1d, lambda x: 2.0 * (x - 3.0), lambda x: 2.0, start
                )
                self.assertAlmostEqual(x_min, 3.0, places=9)
                self.assertEqual(iterations, 1)

    def test_cubic_minimum_anchor(self):
        # f(x) = x**3/3 - x has f' = x**2 - 1, stationary at +-1; from
        # x0 = 2 the iteration converges to the minimum x = 1
        # (f''(1) = 2 > 0) with f = -2/3.
        def f_cubic(x):
            return x ** 3 / 3.0 - x

        def fp_cubic(x):
            return x * x - 1.0

        def fpp_cubic(x):
            return 2.0 * x

        x_min, f_min, iterations = oa.newton_1d_minimize(
            f_cubic, fp_cubic, fpp_cubic, 2.0, tol=1e-10
        )
        self.assertAlmostEqual(x_min, 1.0, places=5)
        self.assertAlmostEqual(f_min, -2.0 / 3.0, places=6)
        self.assertLessEqual(iterations, 6)

    def test_stationary_start_returns_immediately(self):
        # fp(3) = 0 already: converged with zero iterations.
        x_min, f_min, iterations = oa.newton_1d_minimize(
            f_quad_1d, lambda x: 2.0 * (x - 3.0), lambda x: 2.0, 3.0
        )
        self.assertEqual(x_min, 3.0)
        self.assertEqual(f_min, 2.0)
        self.assertEqual(iterations, 0)

    def test_negative_curvature_converges_to_maximum(self):
        # The method locates a stationary point of f; with f'' < 0 at
        # the solution (x = -1 for x**3/3 - x) it is a maximum, so
        # confirm fpp > 0 at the solution before accepting a minimum.
        def f_cubic(x):
            return x ** 3 / 3.0 - x

        def fp_cubic(x):
            return x * x - 1.0

        def fpp_cubic(x):
            return 2.0 * x

        x_min, f_min, iterations = oa.newton_1d_minimize(
            f_cubic, fp_cubic, fpp_cubic, -2.0, tol=1e-10
        )
        self.assertAlmostEqual(x_min, -1.0, places=5)
        self.assertAlmostEqual(f_min, 2.0 / 3.0, places=6)
        self.assertLessEqual(iterations, 6)
        self.assertLess(fpp_cubic(x_min), 0.0)  # curvature check

    def test_zero_second_derivative_raises(self):
        # From x0 = 0 of x**3/3 - x, f''(0) = 0: the step is undefined.
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(
                lambda x: x ** 3 / 3.0 - x,
                lambda x: x * x - 1.0,
                lambda x: 2.0 * x,
                0.0,
            )

    def test_bad_inputs_raise(self):
        f_quad = f_quad_1d
        fp_quad = lambda x: 2.0 * (x - 3.0)  # noqa: E731
        fpp_quad = lambda x: 2.0  # noqa: E731
        for bad_x0 in (float("nan"), float("inf"), True, "3"):
            with self.subTest(x0=bad_x0):
                with self.assertRaises(ValueError):
                    oa.newton_1d_minimize(f_quad, fp_quad, fpp_quad, bad_x0)
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(f_quad, fp_quad, fpp_quad, 1.0, tol=0.0)
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(f_quad, fp_quad, fpp_quad, 1.0, max_iter=0)
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(f_quad, None, fpp_quad, 1.0)
        # Non-finite derivative values raise ValueError.
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(f_quad_1d, lambda x: float("nan"),
                                  lambda x: 2.0, 1.0)
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(f_quad_1d, lambda x: 2.0 * (x - 3.0),
                                  lambda x: float("inf"), 1.0)

    def test_convergence_failure_raises(self):
        # f(x) = exp(x) has no stationary point; fp(x) = exp(x) never
        # drops below tol, and every step shifts by exactly 1, so the
        # iteration exhausts max_iter.
        with self.assertRaises(ValueError):
            oa.newton_1d_minimize(
                math.exp, math.exp, math.exp, 0.0, tol=1e-6, max_iter=5
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
