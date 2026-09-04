"""Contract test for the two-way ANOVA Gage R and R estimator.

Offline, deterministic, stdlib unittest. Run with:
    python3 scripts/test_gage_rr_anova.py
"""

import unittest

from gage_rr_anova_logic import (
    anova_grr_study,
    anova_table,
    verdict_for_percent_grr,
)

# Worked-example fixture: operators A, B, C over parts P1..P3 with two
# trials per cell. B sits 0.01 below A's level, C sits 0.04 above A's
# level, so the operator offsets are purely additive.
WORKED = {
    "A": {"P1": [0.30, 0.32], "P2": [0.50, 0.52], "P3": [0.70, 0.72]},
    "B": {"P1": [0.29, 0.31], "P2": [0.49, 0.51], "P3": [0.69, 0.71]},
    "C": {"P1": [0.34, 0.35], "P2": [0.54, 0.55], "P3": [0.74, 0.75]},
}

RESULT_KEYS = {
    "grand_mean",
    "ss_part",
    "ss_operator",
    "ss_interaction",
    "ss_equipment",
    "df_part",
    "df_operator",
    "df_interaction",
    "df_equipment",
    "ms_part",
    "ms_operator",
    "ms_interaction",
    "ms_equipment",
    "var_equipment",
    "var_interaction",
    "var_operator",
    "var_part",
    "ev",
    "av",
    "iv",
    "grr",
    "pv",
    "tv",
    "percent_grr",
    "ndc",
    "f_part",
    "f_interaction",
    "verdict",
    "distinct_categories",
}


class TestGageRrAnovaWorkedExample(unittest.TestCase):
    """Anchor magnitudes for the worked example against the spec bands."""

    @classmethod
    def setUpClass(cls):
        cls.r = anova_grr_study(WORKED)

    def test_grand_mean(self):
        self.assertAlmostEqual(self.r["grand_mean"], 0.5183, places=4)

    def test_degrees_of_freedom(self):
        self.assertEqual(self.r["df_part"], 2)
        self.assertEqual(self.r["df_operator"], 2)
        self.assertEqual(self.r["df_interaction"], 4)
        self.assertEqual(self.r["df_equipment"], 9)

    def test_ev_within_band(self):
        self.assertAlmostEqual(self.r["ev"], 0.01225, places=4)
        self.assertGreaterEqual(self.r["ev"], 0.011)
        self.assertLessEqual(self.r["ev"], 0.014)

    def test_av_within_band(self):
        self.assertAlmostEqual(self.r["av"], 0.02363, places=4)
        self.assertGreaterEqual(self.r["av"], 0.021)
        self.assertLessEqual(self.r["av"], 0.027)

    def test_grr_pv_tv_magnitudes(self):
        self.assertAlmostEqual(self.r["grr"], 0.02661, places=4)
        self.assertAlmostEqual(self.r["pv"], 0.2, places=4)
        self.assertAlmostEqual(self.r["tv"], 0.20176, places=4)

    def test_percent_grr_within_band(self):
        self.assertAlmostEqual(self.r["percent_grr"], 13.19, places=2)
        self.assertGreaterEqual(self.r["percent_grr"], 12.5)
        self.assertLessEqual(self.r["percent_grr"], 14.0)

    def test_ndc_and_distinct_categories(self):
        self.assertEqual(self.r["ndc"], 10)
        self.assertEqual(self.r["distinct_categories"], 10)

    def test_verdict_conditional(self):
        self.assertEqual(self.r["verdict"], "conditional")

    def test_interaction_component_floor(self):
        # The fixture offsets are additive, so the interaction mean
        # square lies below the equipment mean square and the floor
        # clamps the interaction component to zero.
        self.assertEqual(self.r["var_interaction"], 0.0)
        self.assertEqual(self.r["iv"], 0.0)

    def test_f_statistics_signs_and_ordering(self):
        # Part effect F is large, interaction F is tiny; assert signs
        # and ordering only, not exact values.
        self.assertGreater(self.r["f_part"], 1e12)
        self.assertGreaterEqual(self.r["f_interaction"], 0.0)
        self.assertLess(self.r["f_interaction"], 1e-10)
        self.assertGreater(self.r["f_part"], self.r["f_interaction"])

    def test_ms_equals_ss_over_df(self):
        r = self.r
        self.assertAlmostEqual(r["ms_part"], r["ss_part"] / r["df_part"], places=6)
        self.assertAlmostEqual(
            r["ms_operator"], r["ss_operator"] / r["df_operator"], places=6
        )
        self.assertAlmostEqual(
            r["ms_interaction"],
            r["ss_interaction"] / r["df_interaction"],
            places=6,
        )
        self.assertAlmostEqual(
            r["ms_equipment"], r["ss_equipment"] / r["df_equipment"], places=6
        )

    def test_variance_component_relations(self):
        r = self.r
        self.assertEqual(r["var_equipment"], r["ms_equipment"])
        self.assertAlmostEqual(r["var_part"], r["pv"] * r["pv"], places=8)
        self.assertAlmostEqual(r["var_operator"], r["av"] * r["av"], places=8)


class TestGageRrAnovaIdentities(unittest.TestCase):
    """Closed-form identities the spec requires."""

    def test_ss_decomposition_identity(self):
        r = anova_grr_study(WORKED)
        total_ss = sum(
            (reading - r["grand_mean"]) ** 2
            for operator in WORKED
            for part in WORKED[operator]
            for reading in WORKED[operator][part]
        )
        decomposed = (
            r["ss_part"]
            + r["ss_operator"]
            + r["ss_interaction"]
            + r["ss_equipment"]
        )
        self.assertAlmostEqual(decomposed, total_ss, places=6)

    def test_tv_squared_identity(self):
        r = anova_grr_study(WORKED)
        self.assertAlmostEqual(
            r["tv"] * r["tv"],
            r["grr"] * r["grr"] + r["pv"] * r["pv"],
            places=8,
        )

    def test_percent_grr_ratio_identity(self):
        r = anova_grr_study(WORKED)
        self.assertAlmostEqual(r["percent_grr"], 100.0 * r["grr"] / r["tv"], places=6)

    def test_result_keys_exact(self):
        r = anova_grr_study(WORKED)
        self.assertEqual(set(r.keys()), RESULT_KEYS)

    def test_deterministic_rerun(self):
        self.assertEqual(anova_grr_study(WORKED), anova_grr_study(WORKED))


class TestAnovaTable(unittest.TestCase):
    """The five-source table view."""

    def test_table_sources_and_keys(self):
        rows = anova_table(WORKED)
        self.assertEqual(
            [row["source"] for row in rows],
            ["part", "operator", "interaction", "equipment", "total"],
        )
        for row in rows:
            self.assertEqual(set(row.keys()), {"source", "ss", "df", "ms", "F"})

    def test_table_total_row(self):
        rows = anova_table(WORKED)
        effect_ss = sum(row["ss"] for row in rows[:4])
        self.assertAlmostEqual(rows[4]["ss"], effect_ss, places=6)
        self.assertEqual(rows[4]["df"], 17)

    def test_table_f_matches_study(self):
        r = anova_grr_study(WORKED)
        rows = anova_table(WORKED)
        self.assertEqual(rows[0]["F"], r["f_part"])
        self.assertEqual(rows[2]["F"], r["f_interaction"])
        self.assertIsNone(rows[1]["F"])
        self.assertIsNone(rows[3]["F"])
        self.assertIsNone(rows[4]["F"])


class TestVerdictBands(unittest.TestCase):
    """The 10/30 acceptance band edges."""

    def test_verdict_band_edges(self):
        cases = [
            (0.0, "acceptable"),
            (9.99, "acceptable"),
            (10.0, "conditional"),
            (30.0, "conditional"),
            (30.01, "unacceptable"),
            (99.0, "unacceptable"),
        ]
        for pct, expected in cases:
            with self.subTest(pct=pct):
                self.assertEqual(verdict_for_percent_grr(pct), expected)

    def test_study_verdict_acceptable_zero_variation(self):
        data = {
            "A": {"P1": [0.5, 0.5], "P2": [0.5, 0.5]},
            "B": {"P1": [0.5, 0.5], "P2": [0.5, 0.5]},
        }
        r = anova_grr_study(data)
        self.assertEqual(r["percent_grr"], 0.0)
        self.assertEqual(r["verdict"], "acceptable")

    def test_study_verdict_unacceptable_wide_spread(self):
        # Operators A and B sit far apart, so appraiser variation
        # dominates the total and the verdict must be unacceptable.
        data = {
            "A": {"P1": [0.30, 0.32], "P2": [0.50, 0.52]},
            "B": {"P1": [0.90, 0.92], "P2": [1.10, 1.12]},
        }
        r = anova_grr_study(data)
        self.assertGreater(r["percent_grr"], 30.0)
        self.assertEqual(r["verdict"], "unacceptable")


class TestDegenerateAndBoundary(unittest.TestCase):
    """Degenerate layouts and the non-negative floor."""

    def test_zero_variation_dataset(self):
        data = {
            "A": {"P1": [0.5, 0.5], "P2": [0.5, 0.5]},
            "B": {"P1": [0.5, 0.5], "P2": [0.5, 0.5]},
        }
        r = anova_grr_study(data)
        self.assertEqual(r["ev"], 0.0)
        self.assertEqual(r["grr"], 0.0)
        self.assertEqual(r["tv"], 0.0)
        self.assertIsNone(r["ndc"])
        self.assertIsNone(r["f_part"])
        self.assertIsNone(r["f_interaction"])

    def test_perfect_gage_ndc_none(self):
        # Every operator reads each part identically: no measurement
        # error at all, so grr is zero and ndc is undefined.
        data = {
            "A": {"P1": [0.30, 0.30], "P2": [0.50, 0.50]},
            "B": {"P1": [0.30, 0.30], "P2": [0.50, 0.50]},
        }
        r = anova_grr_study(data)
        self.assertEqual(r["grr"], 0.0)
        self.assertEqual(r["percent_grr"], 0.0)
        self.assertEqual(r["verdict"], "acceptable")
        self.assertIsNone(r["ndc"])
        self.assertAlmostEqual(r["tv"], r["pv"], places=8)

    def test_floor_clamps_interaction_2x2(self):
        # A 2x2 layout with additive offsets and noisy trials: the
        # interaction mean square stays under the equipment mean square,
        # exercising the max(0, ...) floor on a different cell grid.
        data = {
            "A": {"P1": [0.30, 0.31], "P2": [0.50, 0.51]},
            "B": {"P1": [0.29, 0.30], "P2": [0.49, 0.50]},
        }
        r = anova_grr_study(data)
        self.assertEqual(r["var_interaction"], 0.0)
        self.assertEqual(r["iv"], 0.0)
        self.assertGreater(r["grr"], 0.0)
        self.assertIn(r["verdict"], ("acceptable", "conditional"))


class TestValueErrorRejection(unittest.TestCase):
    """Non-physical study layouts raise ValueError."""

    def test_one_operator_rejected(self):
        data = {"A": {"P1": [0.30, 0.32], "P2": [0.50, 0.52]}}
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_one_part_rejected(self):
        data = {
            "A": {"P1": [0.30, 0.32]},
            "B": {"P1": [0.29, 0.31]},
        }
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_one_trial_rejected(self):
        data = {
            "A": {"P1": [0.30], "P2": [0.50]},
            "B": {"P1": [0.29], "P2": [0.49]},
        }
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_ragged_parts_rejected(self):
        data = {
            "A": {"P1": [0.30, 0.32], "P2": [0.50, 0.52], "P3": [0.70, 0.72]},
            "B": {"P1": [0.29, 0.31], "P2": [0.49, 0.51]},
        }
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_unequal_trial_counts_rejected(self):
        data = {
            "A": {"P1": [0.30, 0.32], "P2": [0.50, 0.52, 0.51]},
            "B": {"P1": [0.29, 0.31], "P2": [0.49, 0.51]},
        }
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_non_numeric_reading_rejected(self):
        data = {
            "A": {"P1": [0.30, 0.32], "P2": [0.50, "low"]},
            "B": {"P1": [0.29, 0.31], "P2": [0.49, 0.51]},
        }
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_bool_reading_rejected(self):
        data = {
            "A": {"P1": [0.30, 0.32], "P2": [0.50, True]},
            "B": {"P1": [0.29, 0.31], "P2": [0.49, 0.51]},
        }
        with self.assertRaises(ValueError):
            anova_grr_study(data)

    def test_empty_and_non_dict_rejected(self):
        for bad in ({}, None, [1, 2, 3]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    anova_grr_study(bad)


if __name__ == "__main__":
    unittest.main()
