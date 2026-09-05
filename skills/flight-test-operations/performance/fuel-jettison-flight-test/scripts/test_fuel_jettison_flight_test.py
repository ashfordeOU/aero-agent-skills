"""Contract test for fuel-jettison-flight-test (wave-41).

Offline, deterministic, stdlib only. Runs via:
    python3 scripts/test_fuel_jettison_flight_test.py

The methods below exercise the SKILL.md Workflow: step 2 (fit the
weight trend with the least-squares lsq_fit over the dump window),
step 3 (read the measured average dump rate from the fitted slope),
step 4 (extrapolate the time to the landing weight), step 5 (judge
the PASS or FAIL verdict against the 900 s limit), step 6 (check the
rate requirement against the required rate), step 7 (summarize the
demonstration reduction with reduce_dump_demonstration) and step 8
(reject non-physical inputs and confirm determinism). Worked-example
assert targets are the REAL module outputs from a prep smoke run,
bounded by the spec anchors (slope -14.1447619, intercept 78999.04762,
r_squared 0.9999978496, rate 14.1447619, time 883.7193644 s, margin
16.2806356 s, rate margin 0.2558730159 kg/s).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fuel_jettison_flight_test_logic as fj

# Worked-example fixture: reference transport, takeoff weight 79000 kg,
# landing weight 66500 kg, six telemetered samples at 60 s spacing over
# a 300 s dump window.
WEIGHTS = [79000.0, 78148.0, 77305.0, 76450.0, 75605.0, 74756.0]
TIMES = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]
W_START = 79000.0
W_LANDING = 66500.0
Q_REQ = (W_START - W_LANDING) / 900.0  # 13.88888888888889 kg/s


class WorkedExampleReductionTests(unittest.TestCase):
    """Workflow steps 2 to 7 on the six-sample worked example."""

    def test_lsq_fit_worked_example_slope_and_intercept(self):
        """Step 2 of the SKILL.md workflow, the least-squares weight-trend
        fit over the dump window, is exercised here: the fitted slope must
        be -14.1447619 kg/s within 1e-6 and the intercept 78999.04762 kg
        within 1e-3."""
        fit = fj.lsq_fit(WEIGHTS, TIMES)
        self.assertAlmostEqual(fit["slope"], -14.1447619, delta=1e-6)
        self.assertAlmostEqual(fit["intercept"], 78999.04762, delta=1e-3)

    def test_lsq_fit_worked_example_r_squared(self):
        """Step 2 of the SKILL.md workflow, the weight-trend fit, reports
        the scatter of the dump-window samples through r_squared: the
        worked example must give 0.9999978496 within 1e-9."""
        fit = fj.lsq_fit(WEIGHTS, TIMES)
        self.assertAlmostEqual(fit["r_squared"], 0.9999978496, delta=1e-9)

    def test_measured_rate_worked_example(self):
        """Step 3 of the SKILL.md workflow, the read of the measured
        average dump rate from the fitted slope, must return 14.1447619
        kg/s within 1e-6 on the worked example."""
        rate = fj.measured_rate(WEIGHTS, TIMES)
        self.assertAlmostEqual(rate, 14.1447619, delta=1e-6)

    def test_measured_rate_equals_negative_slope_identity(self):
        """Step 3 of the SKILL.md workflow, the measured dump rate read,
        is the negative of the step 2 fitted slope by construction; the
        identity holds on the worked example and on a second fixture."""
        self.assertAlmostEqual(
            fj.measured_rate(WEIGHTS, TIMES),
            -fj.lsq_fit(WEIGHTS, TIMES)["slope"],
            delta=1e-12,
        )
        other_w = [90000.0, 89500.0, 89000.0, 88500.0]
        other_t = [0.0, 90.0, 180.0, 270.0]
        self.assertAlmostEqual(
            fj.measured_rate(other_w, other_t),
            -fj.lsq_fit(other_w, other_t)["slope"],
            delta=1e-12,
        )

    def test_time_to_landing_weight_worked_example(self):
        """Step 4 of the SKILL.md workflow, the extrapolation of the time
        to the landing weight at the measured dump rate, gives 883.7193644
        s within 1e-4 on the worked example, inside the 900 s limit."""
        rate = fj.measured_rate(WEIGHTS, TIMES)
        t = fj.time_to_landing_weight(W_START, W_LANDING, rate)
        self.assertAlmostEqual(t, 883.7193644, delta=1e-4)
        self.assertLess(t, fj.JETTISON_LIMIT_S)

    def test_time_to_landing_weight_direct_identity(self):
        """Step 4 of the SKILL.md workflow, the landing-weight time
        extrapolation, equals (w_start - w_landing) / rate exactly at any
        valid inputs."""
        t = fj.time_to_landing_weight(W_START, W_LANDING, 14.1447619)
        self.assertEqual(t, (W_START - W_LANDING) / 14.1447619)
        t2 = fj.time_to_landing_weight(120000.0, 80000.0, 20.0)
        self.assertEqual(t2, (120000.0 - 80000.0) / 20.0)

    def test_verdict_worked_example_pass(self):
        """Step 5 of the SKILL.md workflow, the PASS or FAIL verdict
        against the 900 s limit, rates the worked-example extrapolation
        PASS with margin_s 16.2806356 within 1e-6."""
        v = fj.verdict(fj.time_to_landing_weight(W_START, W_LANDING, 14.1447619))
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["limit_s"], 900.0)
        self.assertAlmostEqual(v["margin_s"], 16.2806356, delta=1e-6)

    def test_reduce_summary_worked_example_values(self):
        """Step 7 of the SKILL.md workflow, the one-call demonstration
        summary, returns the worked-example reduction: measured rate
        14.1447619 kg/s, r_squared 0.9999978496, time 883.7193644 s,
        verdict PASS with margin 16.2806356 s, requirement met with rate
        margin 0.2558730159 kg/s."""
        s = fj.reduce_dump_demonstration(
            WEIGHTS, TIMES, W_START, W_LANDING, Q_REQ
        )
        self.assertAlmostEqual(s["measured_rate_kg_s"], 14.1447619, delta=1e-6)
        self.assertAlmostEqual(s["r_squared"], 0.9999978496, delta=1e-9)
        self.assertAlmostEqual(
            s["time_to_landing_weight_s"], 883.7193644, delta=1e-4
        )
        self.assertEqual(s["verdict"], "PASS")
        self.assertEqual(s["limit_s"], 900.0)
        self.assertAlmostEqual(s["margin_s"], 16.2806356, delta=1e-6)
        self.assertTrue(s["meets_required_rate"])
        self.assertAlmostEqual(s["required_rate_kg_s"], 13.88888889, delta=1e-8)
        self.assertAlmostEqual(s["rate_margin_kg_s"], 0.2558730159, delta=1e-6)

    def test_reduce_summary_keys_exact(self):
        """Step 7 of the SKILL.md workflow, the demonstration summary,
        exposes exactly the nine documented keys."""
        s = fj.reduce_dump_demonstration(
            WEIGHTS, TIMES, W_START, W_LANDING, Q_REQ
        )
        self.assertEqual(
            sorted(s.keys()),
            [
                "limit_s",
                "margin_s",
                "measured_rate_kg_s",
                "meets_required_rate",
                "r_squared",
                "rate_margin_kg_s",
                "required_rate_kg_s",
                "time_to_landing_weight_s",
                "verdict",
            ],
        )

    def test_reduce_summary_agrees_with_chain(self):
        """Step 7 of the SKILL.md workflow, the demonstration summary,
        agrees with chaining steps 3, 4, 5 and 6 on the same inputs."""
        s = fj.reduce_dump_demonstration(
            WEIGHTS, TIMES, W_START, W_LANDING, Q_REQ
        )
        rate = fj.measured_rate(WEIGHTS, TIMES)
        t = fj.time_to_landing_weight(W_START, W_LANDING, rate)
        v = fj.verdict(t)
        rq = fj.rate_meets_requirement(rate, Q_REQ)
        self.assertEqual(s["measured_rate_kg_s"], rate)
        self.assertEqual(s["time_to_landing_weight_s"], t)
        self.assertEqual(s["verdict"], v["verdict"])
        self.assertEqual(s["margin_s"], v["margin_s"])
        self.assertEqual(s["meets_required_rate"], rq["meets"])
        self.assertEqual(s["rate_margin_kg_s"], rq["margin_kg_s"])


class BoundaryAndIdentityTests(unittest.TestCase):
    """Workflow steps 4 to 6 boundary anchors and closed-form identities."""

    def test_verdict_inclusive_at_exact_limit(self):
        """Step 5 of the SKILL.md workflow, the verdict judgement, is
        inclusive at the boundary: a time of exactly 900.0 s is PASS with
        margin_s 0.0."""
        v = fj.verdict(900.0)
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["margin_s"], 0.0)
        self.assertEqual(v["limit_s"], 900.0)

    def test_verdict_just_over_limit_fails(self):
        """Step 5 of the SKILL.md workflow, the verdict judgement, turns
        FAIL just past the limit: 900.001 s gives margin_s -0.001 within
        1e-6."""
        v = fj.verdict(900.001)
        self.assertEqual(v["verdict"], "FAIL")
        self.assertAlmostEqual(v["margin_s"], -0.001, delta=1e-6)

    def test_exact_required_rate_gives_exactly_limit_time(self):
        """Steps 3 to 5 of the SKILL.md workflow: a measured dump rate of
        exactly (MTOW - MLW) / 900 s gives exactly 900.0 s to the landing
        weight and a PASS verdict with zero margin."""
        rate = (W_START - W_LANDING) / 900.0
        t = fj.time_to_landing_weight(W_START, W_LANDING, rate)
        self.assertEqual(t, 900.0)
        v = fj.verdict(t)
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["margin_s"], 0.0)

    def test_slow_dump_rate_fails_with_negative_margin(self):
        """Steps 4 and 5 of the SKILL.md workflow: a slow dump at 13.0
        kg/s needs 961.5384615 s, so the verdict is FAIL with margin_s
        -61.53846154 within 1e-6."""
        t = fj.time_to_landing_weight(W_START, W_LANDING, 13.0)
        self.assertAlmostEqual(t, 961.5384615, delta=1e-6)
        v = fj.verdict(t)
        self.assertEqual(v["verdict"], "FAIL")
        self.assertAlmostEqual(v["margin_s"], -61.53846154, delta=1e-6)

    def test_rate_meets_requirement_clears_q_req(self):
        """Step 6 of the SKILL.md workflow, the rate-requirement check,
        finds the worked-example measured rate 14.1447619 kg/s above the
        required 13.88888889 kg/s: meets True with rate margin
        0.2558730159 kg/s within 1e-6."""
        rq = fj.rate_meets_requirement(14.1447619, 13.88888889)
        self.assertTrue(rq["meets"])
        self.assertAlmostEqual(rq["margin_kg_s"], 0.2558730159, delta=1e-6)

    def test_rate_meets_requirement_inclusive_boundary(self):
        """Step 6 of the SKILL.md workflow, the rate-requirement check, is
        inclusive: measured equal to required is meets True with zero rate
        margin."""
        rq = fj.rate_meets_requirement(Q_REQ, Q_REQ)
        self.assertTrue(rq["meets"])
        self.assertEqual(rq["margin_kg_s"], 0.0)

    def test_rate_meets_requirement_below_required(self):
        """Step 6 of the SKILL.md workflow, the rate-requirement check,
        fails when the measured rate sits 0.5 kg/s below the required
        rate: meets False with rate margin -0.5."""
        rq = fj.rate_meets_requirement(Q_REQ - 0.5, Q_REQ)
        self.assertFalse(rq["meets"])
        self.assertAlmostEqual(rq["margin_kg_s"], -0.5, delta=1e-12)

    def test_perfect_line_samples_recovered_exactly(self):
        """Steps 2 and 3 of the SKILL.md workflow: samples lying exactly
        on W = 79000 - 14.15 * t are recovered by the fit with slope
        -14.15, r_squared exactly 1.0 and measured dump rate 14.15."""
        t_list = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]
        w_list = [79000.0 - 14.15 * t for t in t_list]
        fit = fj.lsq_fit(w_list, t_list)
        self.assertEqual(fit["slope"], -14.15)
        self.assertEqual(fit["r_squared"], 1.0)
        self.assertEqual(fj.measured_rate(w_list, t_list), 14.15)

    def test_constant_weights_fit_r_squared_one(self):
        """Step 2 of the SKILL.md workflow, the weight-trend fit, defines
        r_squared as 1.0 when all weights are equal (ss_tot is zero); the
        slope is 0 and the intercept is the common weight."""
        t_list = [0.0, 60.0, 120.0, 180.0]
        w_list = [70000.0, 70000.0, 70000.0, 70000.0]
        fit = fj.lsq_fit(w_list, t_list)
        self.assertEqual(fit["slope"], 0.0)
        self.assertEqual(fit["intercept"], 70000.0)
        self.assertEqual(fit["r_squared"], 1.0)

    def test_reduce_summary_slow_dump_fails(self):
        """Step 7 of the SKILL.md workflow, the demonstration summary,
        reports FAIL when the measured dump rate is too slow: a fixture
        on a 13.0 kg/s trend is not cleared by the rate-requirement check
        and misses the 900 s limit."""
        t_list = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]
        w_list = [W_START - 13.0 * t for t in t_list]
        s = fj.reduce_dump_demonstration(
            w_list, t_list, W_START, W_LANDING, Q_REQ
        )
        self.assertAlmostEqual(s["measured_rate_kg_s"], 13.0, delta=1e-9)
        self.assertFalse(s["meets_required_rate"])
        self.assertEqual(s["verdict"], "FAIL")
        self.assertLess(s["margin_s"], 0.0)
        self.assertLess(s["rate_margin_kg_s"], 0.0)


class InputValidationTests(unittest.TestCase):
    """Workflow step 8: reject non-physical inputs with ValueError."""

    def test_lsq_fit_unequal_lengths_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects weights and times of unequal length in the step 2 fit."""
        with self.assertRaises(ValueError):
            fj.lsq_fit([79000.0, 78148.0], [0.0, 60.0, 120.0])

    def test_lsq_fit_fewer_than_two_samples_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects fewer than the MIN_SAMPLES = 2 samples in the step 2
        weight-trend fit."""
        with self.assertRaises(ValueError):
            fj.lsq_fit([79000.0], [0.0])
        with self.assertRaises(ValueError):
            fj.lsq_fit([], [])

    def test_lsq_fit_times_not_strictly_increasing_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects non-increasing sample times in the step 2 fit."""
        with self.assertRaises(ValueError):
            fj.lsq_fit([79000.0, 78148.0, 77305.0], [0.0, 60.0, 60.0])
        with self.assertRaises(ValueError):
            fj.lsq_fit([79000.0, 78148.0, 77305.0], [0.0, -60.0, -120.0])

    def test_lsq_fit_zero_fit_denominator_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects duplicate time values that zero the step 2 fit
        denominator."""
        with self.assertRaises(ValueError):
            fj.lsq_fit([79000.0, 78148.0, 77305.0], [0.0, 0.0, 0.0])

    def test_measured_rate_no_dump_observable_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects a non-negative fitted slope in the step 3 measured dump
        rate read: rising weights show no dump, and constant weights are
        degenerate."""
        rising_w = [70000.0, 70100.0, 70200.0, 70300.0]
        t_list = [0.0, 60.0, 120.0, 180.0]
        with self.assertRaises(ValueError):
            fj.measured_rate(rising_w, t_list)
        with self.assertRaises(ValueError):
            fj.measured_rate([70000.0, 70000.0, 70000.0], t_list)

    def test_time_to_landing_weight_non_positive_weights_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects non-positive start and landing weights in the step 4
        extrapolation."""
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(0.0, 66500.0, 14.0)
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(79000.0, 0.0, 14.0)
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(-79000.0, 66500.0, 14.0)

    def test_time_to_landing_weight_nothing_to_jettison_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects w_start <= w_landing in the step 4 extrapolation because
        there is nothing to jettison."""
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(66500.0, 66500.0, 14.0)
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(60000.0, 66500.0, 14.0)

    def test_time_to_landing_weight_non_positive_rate_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects a non-positive dump rate in the step 4 extrapolation."""
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(79000.0, 66500.0, 0.0)
        with self.assertRaises(ValueError):
            fj.time_to_landing_weight(79000.0, 66500.0, -14.0)

    def test_verdict_non_positive_inputs_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects a non-positive time or limit in the step 5 verdict
        judgement."""
        with self.assertRaises(ValueError):
            fj.verdict(0.0)
        with self.assertRaises(ValueError):
            fj.verdict(-1.0)
        with self.assertRaises(ValueError):
            fj.verdict(800.0, limit=0.0)
        with self.assertRaises(ValueError):
            fj.verdict(800.0, limit=-900.0)

    def test_rate_meets_requirement_non_positive_inputs_rejected(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        rejects a non-positive measured or required rate in the step 6
        rate-requirement check."""
        with self.assertRaises(ValueError):
            fj.rate_meets_requirement(0.0, 13.88888889)
        with self.assertRaises(ValueError):
            fj.rate_meets_requirement(14.0, 0.0)
        with self.assertRaises(ValueError):
            fj.rate_meets_requirement(-14.0, 13.88888889)

    def test_reduce_summary_rejects_invalid_inputs(self):
        """Step 8 of the SKILL.md workflow, the non-physical input check,
        propagates through the step 7 summary: bad samples, nothing to
        jettison and a non-positive required rate all raise ValueError."""
        bad_w = [79000.0, 79000.0, 79000.0]  # constant, no dump
        t_list = [0.0, 60.0, 120.0]
        with self.assertRaises(ValueError):
            fj.reduce_dump_demonstration(
                bad_w, t_list, W_START, W_LANDING, Q_REQ
            )
        with self.assertRaises(ValueError):
            fj.reduce_dump_demonstration(
                WEIGHTS, TIMES, 60000.0, 66500.0, Q_REQ
            )
        with self.assertRaises(ValueError):
            fj.reduce_dump_demonstration(
                WEIGHTS, TIMES, W_START, W_LANDING, 0.0
            )


class DeterminismAndConstantsTests(unittest.TestCase):
    """Workflow step 8: deterministic outputs and fixed module constants."""

    def test_determinism_identical_inputs_identical_outputs(self):
        """Step 8 of the SKILL.md workflow, the determinism check, gives
        identical outputs for identical inputs on repeated calls of the
        step 2 fit and the step 7 summary."""
        a = fj.lsq_fit(WEIGHTS, TIMES)
        b = fj.lsq_fit(WEIGHTS, TIMES)
        self.assertEqual(a, b)
        s1 = fj.reduce_dump_demonstration(
            WEIGHTS, TIMES, W_START, W_LANDING, Q_REQ
        )
        s2 = fj.reduce_dump_demonstration(
            WEIGHTS, TIMES, W_START, W_LANDING, Q_REQ
        )
        self.assertEqual(s1, s2)

    def test_module_constants_fixed(self):
        """Step 5 of the SKILL.md workflow judges against the fixed module
        constant JETTISON_LIMIT_S = 900.0 (the FAR 25.1001 15-minute
        limit frame), and step 2 requires MIN_SAMPLES = 2."""
        self.assertEqual(fj.JETTISON_LIMIT_S, 900.0)
        self.assertEqual(fj.MIN_SAMPLES, 2)
        self.assertEqual(
            fj.verdict(850.0)["limit_s"], fj.JETTISON_LIMIT_S
        )
        self.assertEqual(
            fj.verdict(850.0), fj.verdict(850.0, limit=fj.JETTISON_LIMIT_S)
        )


if __name__ == "__main__":
    unittest.main()
