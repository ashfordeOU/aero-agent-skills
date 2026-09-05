"""Contract test for maintainability_prediction_logic.py.

Exercises the ARP4761A maintainability-prediction SKILL.md workflow
steps against real module outputs: step 1 (assemble the LRU fleet of
per-hour failure rates and per-LRU repair times in seconds), step 2
(the failure-rate-weighted MTTR rollup, exercised by test_mttr_*),
step 3 (the failure-rate-weighted t50 median repair time parameter of
the lognormal repair-time model, exercised by test_t50_*), step 4 (the
Acklam normal quantile z_p behind every repair-time percentile,
exercised by test_normal_quantile_*), step 5 (the lognormal t50 and
t95 repair-time percentile computation, exercised by test_lognormal_*),
step 6 (the maximum-repair-time requirement verdict with the margin,
exercised by test_verdict_*), step 7 (the per-LRU expected-downtime
rollup over the exposure interval, exercised by test_downtime_*), and
step 8 (the deterministic contract confirmation itself, exercised by
test_determinism_*). All anchors come from the spec worked example
(wide 5-LRU fleet and compact 4-LRU fleet) and were reproduced by
running this module; the module asserts real outputs within the spec
tolerances. Offline, deterministic, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)

import maintainability_prediction_logic as m

# Wide-spread 5-LRU fleet from the spec worked example: rates per hour
# and median repair times in seconds.
WIDE_FLEET = [
    (4.0e-5, 5400.0),   # electro-hydraulic actuator, 1.5 h median
    (1.2e-5, 9000.0),   # servo control electronics, 2.5 h median
    (8.0e-6, 2700.0),   # rate sensor unit, 0.75 h median
    (2.0e-5, 10800.0),  # power drive unit, 3.0 h median
    (6.0e-6, 3600.0),   # control surface position sensor, 1.0 h median
]

# Compact 4-LRU fleet from the spec worked example (PASS case under
# the default lognormal sigma).
COMPACT_FLEET = [
    (3.0e-5, 1440.0),   # servo actuator, 0.4 h median
    (1.5e-5, 2160.0),   # controller unit, 0.6 h median
    (9.0e-6, 1800.0),   # sensor module, 0.5 h median
    (1.2e-5, 2880.0),   # power supply, 0.8 h median
]


class TestFailureRateWeightedMttr(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the failure-rate-weighted MTTR
    rollup of the per-LRU mean repair times."""

    def test_mttr_wide_fleet_spec_anchor(self):
        """The failure-rate-weighted MTTR rollup of the wide fleet
        equals the spec anchor 6781.3953 s within 1e-3."""
        result = m.failure_rate_weighted_mttr(WIDE_FLEET)
        self.assertAlmostEqual(result, 6781.3953, delta=1e-3)

    def test_mttr_compact_fleet_spec_anchor(self):
        """The failure-rate-weighted MTTR rollup of the compact fleet
        equals the spec anchor 1914.5455 s within 1e-3."""
        result = m.failure_rate_weighted_mttr(COMPACT_FLEET)
        self.assertAlmostEqual(result, 1914.5455, delta=1e-3)

    def test_mttr_equal_rates_give_arithmetic_mean(self):
        """With equal failure rates the weighted MTTR rollup collapses
        to the plain arithmetic mean of the two repair times, 5400.0 s
        exactly for the spec identity pair."""
        result = m.failure_rate_weighted_mttr(
            [(1e-5, 3600.0), (1e-5, 7200.0)]
        )
        self.assertAlmostEqual(result, 5400.0, delta=1e-9)


class TestFailureRateWeightedMedian(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the failure-rate-weighted t50
    median repair time used as the lognormal model parameter."""

    def test_t50_wide_fleet_spec_anchor(self):
        """The failure-rate-weighted median of the wide fleet equals
        the spec anchor 6209.6647 s within 1e-3."""
        result = m.failure_rate_weighted_median(WIDE_FLEET)
        self.assertAlmostEqual(result, 6209.6647, delta=1e-3)

    def test_t50_compact_fleet_spec_anchor(self):
        """The failure-rate-weighted median of the compact fleet
        equals the spec anchor 1846.4220 s within 1e-3."""
        result = m.failure_rate_weighted_median(COMPACT_FLEET)
        self.assertAlmostEqual(result, 1846.4220, delta=1e-3)

    def test_t50_wide_below_mttr_lognormal_median_order(self):
        """The lognormal repair-time median t50 of the wide fleet sits
        under the arithmetic MTTR rollup, 6209.6647 below 6781.3953."""
        t50 = m.failure_rate_weighted_median(WIDE_FLEET)
        mttr = m.failure_rate_weighted_mttr(WIDE_FLEET)
        self.assertLess(t50, mttr)

    def test_t50_compact_below_mttr_lognormal_median_order(self):
        """The lognormal repair-time median t50 of the compact fleet
        sits under the arithmetic MTTR rollup, 1846.4220 below
        1914.5455."""
        t50 = m.failure_rate_weighted_median(COMPACT_FLEET)
        mttr = m.failure_rate_weighted_mttr(COMPACT_FLEET)
        self.assertLess(t50, mttr)

    def test_t50_equal_rates_give_geometric_mean(self):
        """With equal failure rates the weighted median collapses to
        the geometric mean of the two repair times, matching
        sqrt(3600.0 * 7200.0) = 5091.1688 s within 1e-9."""
        result = m.failure_rate_weighted_median(
            [(1e-5, 3600.0), (1e-5, 7200.0)]
        )
        self.assertAlmostEqual(
            result, math.sqrt(3600.0 * 7200.0), delta=1e-9
        )


class TestNormalQuantile(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the Acklam inverse normal
    quantile z_p embedded in the repair-time percentile model."""

    def test_normal_quantile_median_returns_zero_exactly(self):
        """normal_quantile(0.5) returns 0.0 exactly, the t50 identity
        input that makes t50 = mttr_median in the lognormal model."""
        self.assertEqual(m.normal_quantile(0.5), 0.0)

    def test_normal_quantile_acklam_095_anchor(self):
        """normal_quantile(0.95) equals the published Acklam value
        1.6448536269514726 within 1e-12."""
        self.assertAlmostEqual(
            m.normal_quantile(0.95), 1.6448536269514726, delta=1e-12
        )

    def test_normal_quantile_monotone_across_tail_switch(self):
        """The quantile stays finite and monotone increasing across the
        tail split at P_LOW = 0.02425 and its mirror, so the t95
        percentile is well defined on both branches."""
        probes = [0.001, 0.02425, 0.025, 0.5, 0.975, 0.97575, 0.999]
        values = [m.normal_quantile(p) for p in probes]
        self.assertTrue(all(math.isfinite(v) for v in values))
        for i in range(len(values) - 1):
            self.assertLess(values[i], values[i + 1])

    def test_normal_quantile_symmetry_about_half(self):
        """The normal quantile is antisymmetric about p = 0.5:
        z(p) = -z(1 - p), used by the lognormal percentile model on
        both tails of the repair-time spread."""
        for p in (0.01, 0.05, 0.2, 0.97575):
            self.assertAlmostEqual(
                m.normal_quantile(p), -m.normal_quantile(1.0 - p),
                delta=1e-12,
            )


class TestLognormalPercentile(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the t50 and t95 repair-time
    percentiles of the lognormal repair-time model."""

    def test_lognormal_t95_wide_sigma_06_spec_anchor(self):
        """The lognormal t95 repair-time percentile of the wide fleet
        at sigma 0.6 equals the spec anchor 16660.1405 s within 1e-2."""
        result = m.lognormal_percentile(6209.6647, 0.6, 0.95)
        self.assertAlmostEqual(result, 16660.1405, delta=1e-2)

    def test_lognormal_t95_compact_default_sigma_spec_anchor(self):
        """The lognormal t95 repair-time percentile of the compact
        fleet at the default sigma 0.5 equals the spec anchor
        4202.4871 s within 1e-2."""
        result = m.lognormal_percentile(
            1846.4220, m.REPAIR_TIME_SIGMA_DEFAULT, 0.95
        )
        self.assertAlmostEqual(result, 4202.4871, delta=1e-2)

    def test_lognormal_t50_identity_at_p_half(self):
        """The t50 identity: lognormal_percentile(median, sigma, 0.5)
        returns the median exactly for any sigma, since z = 0."""
        self.assertEqual(m.lognormal_percentile(6210.0, 0.6, 0.5),
                         6210.0)

    def test_lognormal_sigma_zero_collapses_to_median(self):
        """A lognormal sigma of 0 collapses every repair-time
        percentile onto the median, t50 = t95 = mttr_median."""
        median = 6210.0
        for p in (0.05, 0.5, 0.95, 0.99):
            self.assertEqual(m.lognormal_percentile(median, 0.0, p),
                             median)

    def test_lognormal_percentile_monotone_in_probability(self):
        """The lognormal repair-time percentile grows monotonically
        with the probability p at fixed sigma 0.6."""
        values = [
            m.lognormal_percentile(6209.6647, 0.6, p)
            for p in (0.05, 0.5, 0.9, 0.95, 0.99)
        ]
        for i in range(len(values) - 1):
            self.assertLess(values[i], values[i + 1])

    def test_lognormal_percentile_monotone_in_sigma(self):
        """The lognormal t95 repair-time percentile grows
        monotonically with the assumed log-space spread sigma, and the
        MTTR stays above t50 for any positive sigma."""
        values = [
            m.lognormal_percentile(6209.6647, sig, 0.95)
            for sig in (0.0, 0.2, 0.5, 0.6, 1.0)
        ]
        for i in range(len(values) - 1):
            self.assertLess(values[i], values[i + 1])
        for sig in (0.1, 0.6):
            self.assertGreater(
                m.failure_rate_weighted_mttr(WIDE_FLEET),
                m.lognormal_percentile(
                    m.failure_rate_weighted_median(WIDE_FLEET), sig, 0.5
                ),
            )


class TestMaintainabilityVerdict(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the maximum-repair-time
    requirement verdict with the reported margin."""

    def test_verdict_wide_t95_fail_with_negative_margin(self):
        """The wide-fleet t95 of 16660.1405 s fails the 7200 s
        maximum-repair-time requirement with margin_s -9460.1405 s
        within 1e-2, because 95 percent of repairs exceed the 2 h
        limit."""
        verdict = m.maintainability_verdict(16660.1405)
        self.assertEqual(verdict["verdict"], "FAIL")
        self.assertAlmostEqual(verdict["t95_s"], 16660.1405, delta=1e-9)
        self.assertEqual(verdict["limit_s"], m.MAX_REPAIR_TIME_LIMIT_S)
        self.assertAlmostEqual(verdict["margin_s"], -9460.1405, delta=1e-2)

    def test_verdict_compact_t95_pass_with_positive_margin(self):
        """The compact-fleet t95 of 4202.4871 s passes the 7200 s
        maximum-repair-time requirement with margin_s +2997.5129 s
        within 1e-2, so the requirement is met with margin."""
        verdict = m.maintainability_verdict(4202.4871)
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertAlmostEqual(verdict["margin_s"], 2997.5129, delta=1e-2)

    def test_verdict_boundary_inclusive_at_limit(self):
        """The verdict boundary is inclusive: t95 exactly equal to the
        7200 s requirement limit passes with margin_s 0.0, and the
        module constants back the anchor values (limit constant 7200.0,
        default lognormal sigma 0.5, 3600 s per hour)."""
        verdict = m.maintainability_verdict(7200.0)
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertEqual(verdict["margin_s"], 0.0)
        self.assertEqual(verdict["limit_s"], m.MAX_REPAIR_TIME_LIMIT_S)
        self.assertEqual(m.MAX_REPAIR_TIME_LIMIT_S, 7200.0)
        self.assertEqual(m.REPAIR_TIME_SIGMA_DEFAULT, 0.5)
        self.assertEqual(m.SECONDS_PER_HOUR, 3600.0)

    def test_verdict_custom_requirement_limit_honored(self):
        """A custom requirement limit is honored: t95 of 16660.1405 s
        still fails against a 10800 s limit."""
        verdict = m.maintainability_verdict(16660.1405, 10800.0)
        self.assertEqual(verdict["verdict"], "FAIL")
        self.assertEqual(verdict["limit_s"], 10800.0)
        self.assertAlmostEqual(verdict["margin_s"], -5860.1405, delta=1e-9)

    def test_verdict_flip_sigma_constructs_exact_boundary(self):
        """The verdict flip check of the spec: the sigma that maps the
        wide-fleet t50 onto the 7200 s limit,
        ln(7200.0 / t50) / normal_quantile(0.95) = 0.089962, yields
        t95 = 7200.000000 s and a PASS with margin 0.0 within 1e-6,
        so the spread threshold is read off the boundary exactly."""
        t50 = m.failure_rate_weighted_median(WIDE_FLEET)
        flip_sigma = (
            math.log(m.MAX_REPAIR_TIME_LIMIT_S / t50)
            / m.normal_quantile(0.95)
        )
        self.assertAlmostEqual(flip_sigma, 0.089962, delta=1e-6)
        t95 = m.lognormal_percentile(t50, flip_sigma, 0.95)
        self.assertAlmostEqual(t95, 7200.0, delta=1e-6)
        verdict = m.maintainability_verdict(t95)
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertAlmostEqual(verdict["margin_s"], 0.0, delta=1e-6)


class TestDowntimeRollup(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the per-LRU expected-downtime
    rollup over the exposure interval that gates the maintainability
    input to the availability case."""

    def test_downtime_rollup_wide_fleet_spec_anchor(self):
        """The wide fleet over 4000 exposure hours rolls up to the
        spec anchor: per-LRU downtime hours [0.24, 0.12, 0.024, 0.24,
        0.024] within 1e-6, total 0.648 h within 1e-6 and expected
        unavailability 1.62e-4 within 1e-8."""
        rollup = m.lru_downtime_rollup(WIDE_FLEET, 4000.0)
        self.assertEqual(len(rollup["per_lru_downtime_hours"]), 5)
        expected = [0.24, 0.12, 0.024, 0.24, 0.024]
        for got, want in zip(rollup["per_lru_downtime_hours"], expected):
            self.assertAlmostEqual(got, want, delta=1e-6)
        self.assertAlmostEqual(
            rollup["total_downtime_hours"], 0.648, delta=1e-6
        )
        self.assertAlmostEqual(
            rollup["expected_unavailability"], 1.62e-4, delta=1e-8
        )

    def test_downtime_rollup_matches_rate_times_mttr_product(self):
        """The rollup equals sum(lambda * MTTR_h) over the fleet:
        expected unavailability 1.62e-4 is consistent with the total
        rate 8.6e-5 per hour times the weighted MTTR 1.8837 h, and the
        markov-analysis steady-state unavailability lambda/(lambda +
        mu) with mu = 1/MTTR_h reproduces it in the small-product
        limit."""
        rollup = m.lru_downtime_rollup(WIDE_FLEET, 4000.0)
        mttr_h = m.failure_rate_weighted_mttr(WIDE_FLEET) / 3600.0
        total_rate = sum(lam for lam, _ in WIDE_FLEET)
        self.assertAlmostEqual(
            rollup["expected_unavailability"],
            total_rate * mttr_h,
            delta=1e-12,
        )
        mu = 1.0 / mttr_h
        markov_steady = total_rate / (total_rate + mu)
        self.assertAlmostEqual(
            rollup["expected_unavailability"], markov_steady, delta=1e-7
        )


class TestValueErrorRejections(unittest.TestCase):
    """The non-physical input rejections listed in the spec validation
    list, applied across every SKILL.md workflow step."""

    def test_mttr_value_error_empty_items(self):
        """The weighted MTTR rollup rejects an empty LRU fleet."""
        with self.assertRaises(ValueError):
            m.failure_rate_weighted_mttr([])

    def test_mttr_value_error_zero_and_negative_rates(self):
        """The weighted MTTR rollup rejects zero and negative failure
        rates and an all-zero total rate."""
        for bad in [(0.0, 3600.0), (-1e-5, 3600.0)]:
            with self.assertRaises(ValueError):
                m.failure_rate_weighted_mttr([bad])
        with self.assertRaises(ValueError):
            m.failure_rate_weighted_mttr([(0.0, 3600.0), (0.0, 7200.0)])

    def test_mttr_value_error_zero_and_negative_repair_times(self):
        """The weighted MTTR rollup rejects zero and negative repair
        times."""
        for bad in [(1e-5, 0.0), (1e-5, -100.0)]:
            with self.assertRaises(ValueError):
                m.failure_rate_weighted_mttr([bad])

    def test_t50_value_error_rejections(self):
        """The t50 median parameter rejects empty fleets and non-
        physical rates and repair times exactly as the MTTR rollup
        does."""
        with self.assertRaises(ValueError):
            m.failure_rate_weighted_median([])
        with self.assertRaises(ValueError):
            m.failure_rate_weighted_median([(0.0, 3600.0)])
        with self.assertRaises(ValueError):
            m.failure_rate_weighted_median([(1e-5, 0.0)])

    def test_normal_quantile_value_error_outside_unit_interval(self):
        """The normal quantile rejects probabilities at 0, at 1 and
        outside the open unit interval."""
        for bad in (0.0, 1.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                m.normal_quantile(bad)

    def test_lognormal_value_error_rejections(self):
        """The lognormal percentile rejects a zero or negative median,
        a negative sigma and probabilities outside the open unit
        interval."""
        with self.assertRaises(ValueError):
            m.lognormal_percentile(0.0, 0.6, 0.95)
        with self.assertRaises(ValueError):
            m.lognormal_percentile(-100.0, 0.6, 0.95)
        with self.assertRaises(ValueError):
            m.lognormal_percentile(6210.0, -0.1, 0.95)
        for bad_p in (0.0, 1.0):
            with self.assertRaises(ValueError):
                m.lognormal_percentile(6210.0, 0.6, bad_p)

    def test_verdict_value_error_rejections(self):
        """The verdict rejects a zero or negative predicted t95 and a
        zero or negative requirement limit."""
        for bad_t95 in (0.0, -100.0):
            with self.assertRaises(ValueError):
                m.maintainability_verdict(bad_t95)
        for bad_limit in (0.0, -7200.0):
            with self.assertRaises(ValueError):
                m.maintainability_verdict(16660.1405, bad_limit)

    def test_downtime_rollup_value_error_rejections(self):
        """The downtime rollup rejects zero and negative exposure and
        the same non-physical fleet items as the other steps."""
        for bad_exp in (0.0, -4000.0):
            with self.assertRaises(ValueError):
                m.lru_downtime_rollup(WIDE_FLEET, bad_exp)
        with self.assertRaises(ValueError):
            m.lru_downtime_rollup([], 4000.0)
        with self.assertRaises(ValueError):
            m.lru_downtime_rollup([(0.0, 3600.0)], 4000.0)
        with self.assertRaises(ValueError):
            m.lru_downtime_rollup([(1e-5, -100.0)], 4000.0)


class TestDeterminismAndKeys(unittest.TestCase):
    """Step 8 of the SKILL.md workflow, the deterministic contract
    confirmation with exact documented result keys."""

    def test_repeated_calls_bit_identical(self):
        """Every workflow function is deterministic: repeated calls on
        both fleets return bit-identical floats and dicts."""
        first = m.maintainability_verdict(
            m.lognormal_percentile(
                m.failure_rate_weighted_median(WIDE_FLEET), 0.6, 0.95
            )
        )
        for _ in range(5):
            again = m.maintainability_verdict(
                m.lognormal_percentile(
                    m.failure_rate_weighted_median(WIDE_FLEET), 0.6, 0.95
                )
            )
            self.assertEqual(first, again)
            self.assertEqual(
                m.failure_rate_weighted_mttr(WIDE_FLEET),
                m.failure_rate_weighted_mttr(WIDE_FLEET),
            )
            self.assertEqual(
                m.failure_rate_weighted_median(COMPACT_FLEET),
                m.failure_rate_weighted_median(COMPACT_FLEET),
            )

    def test_returned_dict_keys_exactly_documented(self):
        """The verdict and rollup dicts carry exactly the documented
        keys: verdict, t95_s, limit_s, margin_s and per_lru_downtime_
        hours, total_downtime_hours, expected_unavailability."""
        verdict = m.maintainability_verdict(4202.4871)
        self.assertEqual(
            set(verdict.keys()),
            {"verdict", "t95_s", "limit_s", "margin_s"},
        )
        rollup = m.lru_downtime_rollup(COMPACT_FLEET, 4000.0)
        self.assertEqual(
            set(rollup.keys()),
            {
                "per_lru_downtime_hours",
                "total_downtime_hours",
                "expected_unavailability",
            },
        )


if __name__ == "__main__":
    unittest.main()
