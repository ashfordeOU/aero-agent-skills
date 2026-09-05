"""Contract test for the failure-mode-criticality leaf.

Workflow step 7 of the SKILL.md, the deterministic confirmation pass, is
implemented here: run python3 scripts/test_failure_mode_criticality.py
offline to confirm every per-mode rate split, C_m criticality number,
item criticality C_r and the mode ranking produced by the module.

The test docstrings name the SKILL.md workflow steps they exercise so
the value-delta sampler can see which fact terms (mode ratio alpha,
conditional failure-effect probability beta, item failure rate,
operating time, per-mode rate, criticality number, item criticality,
share of item criticality, dominant flag) and procedure terms (rate
split, criticality pass, summation, ranking pass) each method covers.
"""

import unittest

import failure_mode_criticality_logic as fmc

LP = 2e-6          # pump item failure rate, per hour
TIME = 5000.0      # operating time, hours
RATIOS = {"runaway": 0.2, "jammed": 0.5, "no-output": 0.3}
MODES = [
    {"id": "runaway", "alpha": 0.2, "beta": 1.0},
    {"id": "jammed", "alpha": 0.5, "beta": 0.05},
    {"id": "no-output", "alpha": 0.3, "beta": 0.1},
]


class SplitItemRateTests(unittest.TestCase):
    """Workflow step 3, the rate-split traverse over the mode ratios."""

    def test_pump_partition_math(self):
        # Workflow step 3: split_item_rate on the pump ratios yields the
        # per-mode rates 4e-7 (runaway), 1e-6 (jammed), 6e-7 (no-output).
        out = fmc.split_item_rate(LP, RATIOS)
        self.assertAlmostEqual(out["runaway"], 4e-7, delta=1e-20)
        self.assertAlmostEqual(out["jammed"], 1e-6, delta=1e-20)
        self.assertAlmostEqual(out["no-output"], 6e-7, delta=1e-20)

    def test_per_mode_rate_is_alpha_times_item_failure_rate(self):
        # Workflow step 3: per-mode rate equals the mode ratio alpha
        # times the item failure rate, here 0.5 * 2e-6 = 1e-6.
        out = fmc.split_item_rate(LP, {"jammed": 0.5, "other": 0.5})
        self.assertAlmostEqual(out["jammed"], 1e-6, delta=1e-20)
        self.assertAlmostEqual(out["other"], 1e-6, delta=1e-20)

    def test_ratio_sum_0_99_raises(self):
        # Workflow step 1: mode ratios must sum to unity within
        # MODE_RATIO_TOLERANCE; a 0.99 total is rejected.
        with self.assertRaises(ValueError):
            fmc.split_item_rate(LP, {"a": 0.5, "b": 0.49})

    def test_ratio_sum_1_01_raises(self):
        # Workflow step 1: a mode-ratio total of 1.01 is rejected.
        with self.assertRaises(ValueError):
            fmc.split_item_rate(LP, {"a": 0.5, "b": 0.51})

    def test_empty_mode_ratios_raise(self):
        # Workflow step 1: an empty ratio set leaves the item failure
        # rate unsplit and raises ValueError.
        with self.assertRaises(ValueError):
            fmc.split_item_rate(LP, {})

    def test_alpha_zero_raises(self):
        # Workflow step 1: a zero mode ratio is non-physical and raises.
        with self.assertRaises(ValueError):
            fmc.split_item_rate(LP, {"a": 0.0, "b": 1.0})

    def test_alpha_above_one_raises(self):
        # Workflow step 1: a mode ratio above 1 is rejected.
        with self.assertRaises(ValueError):
            fmc.split_item_rate(LP, {"a": 1.5, "b": -0.5})

    def test_nonpositive_item_failure_rate_raises(self):
        # Workflow step 3: the rate split needs a positive item failure
        # rate; zero and negative values raise ValueError.
        with self.assertRaises(ValueError):
            fmc.split_item_rate(0.0, RATIOS)
        with self.assertRaises(ValueError):
            fmc.split_item_rate(-2e-6, RATIOS)

    def test_dict_keys_exactly_as_documented(self):
        # Workflow step 3: the returned per-mode rate dict carries one
        # key per mode id, no extra keys.
        out = fmc.split_item_rate(LP, RATIOS)
        self.assertEqual(sorted(out.keys()), ["jammed", "no-output", "runaway"])


class ModeCriticalityTests(unittest.TestCase):
    """Workflow step 4, the per-mode criticality pass for C_m."""

    def test_pump_runaway_cm(self):
        # Workflow step 4: C_m = beta * alpha * lambda_p * t gives
        # 1.0 * 0.2 * 2e-6 * 5000 = 2e-3 for the runaway mode.
        self.assertAlmostEqual(
            fmc.mode_criticality(1.0, 0.2, LP, TIME), 2e-3, delta=1e-12
        )

    def test_pump_jammed_cm(self):
        # Workflow step 4: the jammed mode with beta 0.05 and alpha 0.5
        # gives C_m = 2.5e-4.
        self.assertAlmostEqual(
            fmc.mode_criticality(0.05, 0.5, LP, TIME), 2.5e-4, delta=1e-12
        )

    def test_pump_no_output_cm(self):
        # Workflow step 4: the no-output mode with beta 0.1 and alpha 0.3
        # gives C_m = 3.0e-4.
        self.assertAlmostEqual(
            fmc.mode_criticality(0.1, 0.3, LP, TIME), 3.0e-4, delta=1e-12
        )

    def test_single_mode_anchor(self):
        # Workflow step 4: a single mode with alpha and beta both 1.0
        # makes C_m = lambda * t = 3e-6 * 4000 = 1.2e-2.
        self.assertAlmostEqual(
            fmc.mode_criticality(1.0, 1.0, 3e-6, 4000.0), 1.2e-2, delta=1e-12
        )

    def test_beta_endpoints_accepted(self):
        # Workflow step 2: beta exactly 1.0 (certain failure effect) and
        # beta exactly 0.0 (no item-level effect) are both accepted.
        self.assertAlmostEqual(
            fmc.mode_criticality(1.0, 0.2, LP, TIME), 2e-3, delta=1e-12
        )
        self.assertEqual(fmc.mode_criticality(0.0, 0.2, LP, TIME), 0.0)

    def test_beta_out_of_range_raises(self):
        # Workflow step 2: beta 1.01 and beta -0.1 violate the [0, 1]
        # conditional failure-effect probability range and raise.
        with self.assertRaises(ValueError):
            fmc.mode_criticality(1.01, 0.2, LP, TIME)
        with self.assertRaises(ValueError):
            fmc.mode_criticality(-0.1, 0.2, LP, TIME)

    def test_alpha_bounds(self):
        # Workflow step 1: alpha 0 and alpha 1.5 raise; alpha exactly 1
        # is a valid single-mode split.
        with self.assertRaises(ValueError):
            fmc.mode_criticality(1.0, 0.0, LP, TIME)
        with self.assertRaises(ValueError):
            fmc.mode_criticality(1.0, 1.5, LP, TIME)
        self.assertAlmostEqual(
            fmc.mode_criticality(1.0, 1.0, LP, TIME), 1e-2, delta=1e-12
        )

    def test_zero_operating_time_returns_zero(self):
        # Workflow step 4: a zero operating time leaves no exposure, so
        # the criticality number is 0.0 rather than an error.
        self.assertEqual(fmc.mode_criticality(1.0, 0.2, LP, 0.0), 0.0)

    def test_negative_operating_time_raises(self):
        # Workflow step 4: a negative operating time is non-physical.
        with self.assertRaises(ValueError):
            fmc.mode_criticality(1.0, 0.2, LP, -1.0)

    def test_nonpositive_rate_raises(self):
        # Workflow step 4: the criticality pass needs a positive item
        # failure rate.
        with self.assertRaises(ValueError):
            fmc.mode_criticality(1.0, 0.2, 0.0, TIME)

    def test_linear_in_beta_alpha_and_time(self):
        # Workflow step 4: C_m is linear in beta, alpha and operating
        # time separately, so doubling any one factor doubles C_m.
        base = fmc.mode_criticality(0.4, 0.2, LP, TIME)
        self.assertAlmostEqual(
            fmc.mode_criticality(0.8, 0.2, LP, TIME), 2.0 * base, delta=1e-18
        )
        self.assertAlmostEqual(
            fmc.mode_criticality(0.4, 0.4, LP, TIME), 2.0 * base, delta=1e-18
        )
        self.assertAlmostEqual(
            fmc.mode_criticality(0.4, 0.2, LP, 2.0 * TIME),
            2.0 * base, delta=1e-18,
        )


class ItemCriticalityTests(unittest.TestCase):
    """Workflow step 5, the item criticality summation over the modes."""

    def test_pump_item_criticality(self):
        # Workflow step 5: summing the pump per-mode criticalities gives
        # C_r = 2e-3 + 2.5e-4 + 3.0e-4 = 2.55e-3.
        self.assertAlmostEqual(
            fmc.item_criticality(MODES, LP, TIME), 2.55e-3, delta=1e-15
        )

    def test_single_mode_item_criticality_identity(self):
        # Workflow step 5: with one mode at alpha = beta = 1 the item
        # criticality collapses to C_r = lambda * t = 1.2e-2.
        single = [{"id": "only", "alpha": 1.0, "beta": 1.0}]
        self.assertAlmostEqual(
            fmc.item_criticality(single, 3e-6, 4000.0), 1.2e-2, delta=1e-15
        )

    def test_item_criticality_is_sum_of_cm(self):
        # Workflow step 5: the item criticality equals the sum of the
        # individual criticality numbers computed mode by mode.
        total = sum(
            fmc.mode_criticality(m["beta"], m["alpha"], LP, TIME)
            for m in MODES
        )
        self.assertAlmostEqual(
            fmc.item_criticality(MODES, LP, TIME), total, delta=1e-18
        )

    def test_empty_modes_raise(self):
        # Workflow step 5: an empty mode list leaves nothing to sum.
        with self.assertRaises(ValueError):
            fmc.item_criticality([], LP, TIME)

    def test_invalid_mode_raises(self):
        # Workflow step 5: a mode whose beta sits outside [0, 1] is
        # rejected by the summation.
        bad = [{"id": "x", "alpha": 0.5, "beta": 1.5}]
        with self.assertRaises(ValueError):
            fmc.item_criticality(bad, LP, TIME)

    def test_zero_time_zero_item_criticality(self):
        # Workflow step 5: no exposure over a zero operating time means
        # the item criticality is 0.0.
        self.assertEqual(fmc.item_criticality(MODES, LP, 0.0), 0.0)


class RankModesTests(unittest.TestCase):
    """Workflow step 6, the criticality ranking pass that gates action."""

    def test_pump_rank_order_and_dominant_flag(self):
        # Workflow step 6: the pump modes rank [runaway, no-output,
        # jammed] by C_m, and runaway's share of item criticality
        # 0.78431 clears the dominant threshold.
        rank = fmc.rank_modes(MODES, LP, TIME)
        self.assertEqual([r["id"] for r in rank],
                         ["runaway", "no-output", "jammed"])
        self.assertAlmostEqual(rank[0]["share"], 0.78431, delta=1e-5)
        self.assertTrue(rank[0]["dominant"])
        self.assertFalse(rank[1]["dominant"])
        self.assertFalse(rank[2]["dominant"])

    def test_rank_fields_present(self):
        # Workflow step 6: every ranked mode dict carries id, alpha,
        # beta, cm, share and dominant, with cm equal to the per-mode
        # criticality number from the criticality pass.
        rank = fmc.rank_modes(MODES, LP, TIME)
        for row in rank:
            for key in ("id", "alpha", "beta", "cm", "share", "dominant"):
                self.assertIn(key, row)
        self.assertAlmostEqual(
            rank[0]["cm"], fmc.mode_criticality(1.0, 0.2, LP, TIME),
            delta=1e-18,
        )

    def test_shares_sum_to_one(self):
        # Workflow step 6: the shares of item criticality across the
        # ranked modes sum to 1.0 within float tolerance.
        rank = fmc.rank_modes(MODES, LP, TIME)
        self.assertAlmostEqual(sum(r["share"] for r in rank), 1.0, delta=1e-12)

    def test_tie_break_by_id_ascending(self):
        # Workflow step 6: two modes with an equal criticality number
        # order by mode id ascending, keeping the ranking deterministic.
        modes = [
            {"id": "zulu", "alpha": 0.2, "beta": 0.5},
            {"id": "alpha", "alpha": 0.1, "beta": 1.0},
        ]
        rank = fmc.rank_modes(modes, LP, TIME)
        self.assertEqual([r["id"] for r in rank], ["alpha", "zulu"])
        self.assertAlmostEqual(rank[0]["cm"], rank[1]["cm"], delta=1e-18)

    def test_rank_order_scale_invariant(self):
        # Workflow step 6: scaling every per-mode criticality by the
        # same positive constant leaves the ranking order unchanged.
        base = fmc.rank_modes(MODES, LP, TIME)
        scaled = fmc.rank_modes(MODES, LP * 7.5, TIME)
        self.assertEqual([r["id"] for r in base], [r["id"] for r in scaled])
        for b, s in zip(base, scaled):
            self.assertAlmostEqual(s["cm"], 7.5 * b["cm"], delta=1e-15)

    def test_dominant_boundary_at_half_share(self):
        # Workflow step 6: a share exactly at DOMINANT_SHARE 0.5 is
        # flagged dominant; just below it is not.
        modes = [
            {"id": "a", "alpha": 0.5, "beta": 1.0},
            {"id": "b", "alpha": 0.5, "beta": 1.0},
        ]
        rank = fmc.rank_modes(modes, LP, TIME)
        self.assertEqual([r["id"] for r in rank], ["a", "b"])
        self.assertAlmostEqual(rank[0]["share"], 0.5, delta=1e-12)
        self.assertTrue(rank[0]["dominant"])

    def test_rank_determinism(self):
        # Workflow step 6: two runs over the same modes return identical
        # ranked rows, so the ranking pass is deterministic.
        first = fmc.rank_modes(MODES, LP, TIME)
        second = fmc.rank_modes(MODES, LP, TIME)
        self.assertEqual(first, second)

    def test_rank_invalid_modes_raise(self):
        # Workflow step 6: the ranking pass rejects an invalid mode list
        # exactly as the item criticality summation does.
        with self.assertRaises(ValueError):
            fmc.rank_modes([], LP, TIME)
        with self.assertRaises(ValueError):
            fmc.rank_modes([{"id": "x", "alpha": 0.5, "beta": -0.2}], LP, TIME)


if __name__ == "__main__":
    unittest.main()
