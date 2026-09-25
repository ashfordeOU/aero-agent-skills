"""Contract tests for the software product quality metrics logic."""

import unittest

from q80_software_product_quality_metrics_logic import (
    DEFAULT_THRESHOLDS,
    METRICS,
    comment_density,
    cyclomatic_estimate,
    evaluate_metrics,
    evaluate_modules,
    maturity_trend,
    normalise_category,
    thresholds_for,
)

C_SOURCE = """
/* compute mode */
int mode(int a, int b) {
    // guard
    if (a > 0 && b > 0) {
        return 1;
    } else if (a < 0) {
        return 2;
    }
    for (int i = 0; i < b; i++) { a++; }
    return a > b ? 3 : 4;
}
"""


class CatalogueTests(unittest.TestCase):
    def test_defaults_name_only_known_metrics(self):
        for cat, table in DEFAULT_THRESHOLDS.items():
            self.assertEqual(set(table), set(METRICS), cat)

    def test_category_rejects_unknown(self):
        with self.assertRaises(ValueError):
            normalise_category("Z")

    def test_overrides_and_sources(self):
        lim = thresholds_for("B", {"cyclomatic_complexity": 12, "mcdc_coverage": 0.9,
                                   "comment_density": None})
        self.assertEqual(lim["cyclomatic_complexity"], (12, "project"))
        self.assertEqual(lim["mcdc_coverage"], (0.9, "project"))
        self.assertNotIn("comment_density", lim)
        self.assertEqual(lim["decision_coverage"], (1.0, "default"))

    def test_unknown_override_rejected(self):
        with self.assertRaises(ValueError):
            thresholds_for("A", {"happiness": 1})


class SourceMetricTests(unittest.TestCase):
    def test_comment_density(self):
        self.assertEqual(comment_density("a = 1\n# note\n\nb = 2\n# more"), 0.5)
        self.assertEqual(comment_density(""), 0.0)

    def test_block_comment_counts_all_lines(self):
        src = "/* one\n two\n three */\ncode();"
        self.assertEqual(comment_density(src), 0.75)

    def test_language_prefixes(self):
        src = "#include <x.h>\n// note\nint a;"
        self.assertAlmostEqual(comment_density(src), 0.6667, places=4)
        self.assertAlmostEqual(comment_density(src, ("//", "/*", "*", "*/")), 0.3333, places=4)

    def test_cyclomatic_estimate(self):
        # if, &&, else if, for, ternary -> 5 decisions
        self.assertEqual(cyclomatic_estimate(C_SOURCE), 6)
        self.assertEqual(cyclomatic_estimate("return 0;"), 1)


class EvaluationTests(unittest.TestCase):
    def _good_b(self):
        return {"cyclomatic_complexity": 8, "nesting_depth": 3, "function_size_loc": 50,
                "comment_density": 0.3, "requirement_coverage": 1.0,
                "requirement_test_coverage": 1.0, "statement_coverage": 1.0,
                "decision_coverage": 1.0, "open_major_nonconformances": 0,
                "coding_standard_violations": 0}

    def test_pass(self):
        self.assertEqual(evaluate_metrics(self._good_b(), "B")["verdict"], "pass")

    def test_fail_with_margin(self):
        m = self._good_b()
        m["decision_coverage"] = 0.97
        res = evaluate_metrics(m, "B")
        self.assertEqual(res["failing"], ["decision_coverage"])
        row = [r for r in res["rows"] if r["metric"] == "decision_coverage"][0]
        self.assertAlmostEqual(row["margin"], -0.03, places=4)

    def test_missing_is_not_a_pass(self):
        m = self._good_b()
        del m["statement_coverage"]
        res = evaluate_metrics(m, "B")
        self.assertEqual(res["missing"], ["statement_coverage"])
        self.assertEqual(res["verdict"], "fail")

    def test_boundary_passes(self):
        m = self._good_b()
        m["cyclomatic_complexity"] = 10
        m["comment_density"] = 0.2
        self.assertEqual(evaluate_metrics(m, "B")["verdict"], "pass")

    def test_open_major_ncr_fails(self):
        m = self._good_b()
        m["open_major_nonconformances"] = 1
        self.assertIn("open_major_nonconformances", evaluate_metrics(m, "B")["failing"])

    def test_unknown_metrics_reported(self):
        m = self._good_b()
        m["vibes"] = 5
        self.assertEqual(evaluate_metrics(m, "B")["unknown"], ["vibes"])


class ModuleTests(unittest.TestCase):
    def test_offenders_and_fraction(self):
        mods = [
            {"name": "tc_handler", "cyclomatic_complexity": 14, "comment_density": 0.3},
            {"name": "fdir", "cyclomatic_complexity": 7, "comment_density": 0.1},
            {"name": "hk", "cyclomatic_complexity": 5, "comment_density": 0.4},
        ]
        res = evaluate_modules(mods, "B")
        self.assertEqual(res["offenders"], {"tc_handler": ["cyclomatic_complexity"],
                                            "fdir": ["comment_density"]})
        self.assertAlmostEqual(res["compliant_fraction"], 0.3333, places=4)
        self.assertEqual(res["worst"]["cyclomatic_complexity"], "tc_handler")

    def test_duplicate_module_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_modules([{"name": "a"}, {"name": "a"}], "C")


class MaturityTests(unittest.TestCase):
    def test_maturing(self):
        hist = [("w1", 20, 5), ("w2", 12, 15), ("w3", 6, 12), ("w4", 3, 8)]
        res = maturity_trend(hist, "B")
        self.assertEqual(res["trend"], "decreasing")
        self.assertEqual(res["verdict"], "maturing")
        self.assertEqual(res["backlog"][-1], ("w4", 1))

    def test_not_maturing_when_discovery_rises(self):
        hist = [("w1", 2, 2), ("w2", 4, 1), ("w3", 9, 2)]
        self.assertEqual(maturity_trend(hist, "A")["verdict"], "not-maturing")

    def test_category_d_and_short_history(self):
        self.assertEqual(maturity_trend([], "D")["verdict"], "not-required")
        self.assertEqual(maturity_trend([("w1", 1, 0)], "C")["verdict"], "insufficient-data")

    def test_impossible_history_rejected(self):
        with self.assertRaises(ValueError):
            maturity_trend([("w1", 1, 3)], "B")


if __name__ == "__main__":
    unittest.main()
