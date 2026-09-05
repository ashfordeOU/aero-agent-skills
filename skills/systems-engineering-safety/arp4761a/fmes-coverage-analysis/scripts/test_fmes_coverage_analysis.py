"""Contract test for fmes-coverage-analysis (systems-engineering-safety/arp4761a).

Offline, deterministic, stdlib unittest only. Exercises the SKILL.md
workflow: step 2 normalize() tokenization, step 3 condition_match_score()
text-match suggestions, step 4 coverage_score() row-to-condition mapping
with the covered and uncovered condition lists, orphan row flags and the
coverage ratio, and step 5 coverage_by_severity() per-severity-class
breakdown, over the ten-condition worked example FC-01..FC-10 with
fourteen FMEA rows R-01..R-14.
"""

import sys
import unittest

sys.path.insert(0, "skills/systems-engineering-safety/arp4761a/fmes-coverage-analysis/scripts")

from fmes_coverage_analysis_logic import (
    normalize,
    condition_match_score,
    coverage_score,
    coverage_by_severity,
)

SEVERITIES = {
    "FC-01": "catastrophic",
    "FC-02": "catastrophic",
    "FC-03": "hazardous",
    "FC-04": "hazardous",
    "FC-05": "major",
    "FC-06": "major",
    "FC-07": "major",
    "FC-08": "minor",
    "FC-09": "minor",
    "FC-10": "minor",
}


def make_conditions():
    """Ten FHA conditions FC-01..FC-10 from the SKILL.md worked example."""
    descriptions = {
        "FC-01": "loss of pitch control",
        "FC-02": "loss of all roll control",
        "FC-03": "flap asymmetry",
        "FC-04": "uncommanded roll excursion",
        "FC-05": "engine thrust loss",
        "FC-06": "autopilot runaway",
        "FC-07": "hydraulic pressure loss",
        "FC-08": "cabin altitude excursion",
        "FC-09": "annunciation loss",
        "FC-10": "galley power loss",
    }
    return [
        {"id": cid, "description": descriptions[cid], "severity": SEVERITIES[cid]}
        for cid in descriptions
    ]


def make_rows():
    """Fourteen FMEA rows R-01..R-14 from the SKILL.md worked example.

    R-01, R-02 to FC-01; R-03, R-04 to FC-02; R-05 to FC-03; R-06, R-07
    to FC-04; R-08, R-09 to FC-05; R-10, R-11 to FC-06; R-12 to FC-07;
    R-13 and R-14 carry no condition link (orphan rows).
    """
    links = [
        ("R-01", "FC-01"), ("R-02", "FC-01"),
        ("R-03", "FC-02"), ("R-04", "FC-02"),
        ("R-05", "FC-03"),
        ("R-06", "FC-04"), ("R-07", "FC-04"),
        ("R-08", "FC-05"), ("R-09", "FC-05"),
        ("R-10", "FC-06"), ("R-11", "FC-06"),
        ("R-12", "FC-07"),
    ]
    rows = [{"row_id": row_id, "condition_id": cid} for row_id, cid in links]
    rows.append({"row_id": "R-13", "condition_id": None})
    rows.append({"row_id": "R-14", "condition_id": None})
    return rows


class NormalizeTests(unittest.TestCase):
    """Workflow step 2, the normalize() token split, is exercised here."""

    def test_normalize_worked_example_tokens(self):
        """Step 2 normalize of the anchor text yields the exact token list."""
        self.assertEqual(
            normalize("Loss of PITCH-control, authority!"),
            ["loss", "of", "pitch", "control", "authority"],
        )

    def test_normalize_strips_case_and_whitespace_runs(self):
        """Step 2 normalize folds case and collapses whitespace runs."""
        self.assertEqual(normalize("  PITCH  Control \t Pitch "), ["pitch", "control", "pitch"])

    def test_normalize_strips_digits_adjacent_punctuation(self):
        """Step 2 normalize keeps alphanumeric runs across punctuation."""
        self.assertEqual(normalize("R-01: v1.2-alpha!"), ["r", "01", "v1", "2", "alpha"])

    def test_normalize_is_idempotent_on_own_output(self):
        """Step 2 normalize of rejoined tokens returns the same token list."""
        text = "Loss of PITCH-control, authority!"
        self.assertEqual(normalize(" ".join(normalize(text))), normalize(text))


class MatchScoreTests(unittest.TestCase):
    """Workflow step 3, the condition_match_score() suggestion helper."""

    def test_identical_texts_score_one(self):
        """Step 3 score of a row text with itself is 1.0, full overlap."""
        self.assertEqual(condition_match_score("loss of pitch control", "loss of pitch control"), 1.0)

    def test_disjoint_texts_score_zero(self):
        """Step 3 disjoint texts share no tokens and score 0.0."""
        self.assertEqual(condition_match_score("flap asymmetry", "galley power loss"), 0.0)

    def test_empty_text_pair_scores_zero(self):
        """Step 3 both token sets empty gives 0.0, no evidence to match on."""
        self.assertEqual(condition_match_score("", "  !  "), 0.0)
        self.assertEqual(condition_match_score("", ""), 0.0)

    def test_anchor_pitch_overlap_two_thirds(self):
        """Step 3 the pitch anchor scores 0.666667 within 1e-6."""
        self.assertAlmostEqual(
            condition_match_score("loss of all pitch control authority", "loss of pitch control"),
            0.666667,
            delta=1e-6,
        )

    def test_anchor_roll_overlap_one_third(self):
        """Step 3 the roll anchor scores 0.333333 within 1e-6."""
        self.assertAlmostEqual(
            condition_match_score("flap asymmetry drives uncommanded roll", "uncommanded roll excursion"),
            0.333333,
            delta=1e-6,
        )

    def test_anchor_autopilot_overlap_one_eighth(self):
        """Step 3 the autopilot anchor scores 0.125 within 1e-6."""
        self.assertAlmostEqual(
            condition_match_score("autopilot disengages without crew annunciation", "loss of autopilot engagement"),
            0.125,
            delta=1e-6,
        )

    def test_match_score_is_symmetric(self):
        """Step 3 the Jaccard score does not depend on argument order."""
        a = "loss of all pitch control authority"
        b = "loss of pitch control"
        self.assertEqual(condition_match_score(a, b), condition_match_score(b, a))


class CoverageScoreTests(unittest.TestCase):
    """Workflow step 4, the coverage_score() row-to-condition mapping."""

    def test_worked_example_coverage_ratio(self):
        """Step 4 the ten-condition worked example reports coverage 0.7 exactly."""
        result = coverage_score(make_conditions(), make_rows())
        self.assertEqual(result["coverage"], 0.7)

    def test_worked_example_covered_list(self):
        """Step 4 covered conditions are FC-01..FC-07 in conditions order."""
        result = coverage_score(make_conditions(), make_rows())
        self.assertEqual(
            result["covered_conditions"],
            ["FC-01", "FC-02", "FC-03", "FC-04", "FC-05", "FC-06", "FC-07"],
        )

    def test_worked_example_uncovered_list(self):
        """Step 4 the three minor conditions FC-08..FC-10 stay uncovered."""
        result = coverage_score(make_conditions(), make_rows())
        self.assertEqual(result["uncovered_conditions"], ["FC-08", "FC-09", "FC-10"])

    def test_worked_example_orphan_rows(self):
        """Step 4 the two unlinked rows R-13 and R-14 are flagged as orphans."""
        result = coverage_score(make_conditions(), make_rows())
        self.assertEqual(result["orphan_rows"], ["R-13", "R-14"])

    def test_output_dict_keys_exact(self):
        """Step 4 the coverage summary dict exposes exactly the documented keys."""
        result = coverage_score(make_conditions(), make_rows())
        self.assertEqual(
            set(result),
            {"covered_conditions", "uncovered_conditions", "orphan_rows", "coverage"},
        )

    def test_full_coverage_ratio_one(self):
        """Step 4 rows for every condition give coverage 1.0 and no uncovered ids."""
        rows = [{"row_id": "R-%02d" % i, "condition_id": cid} for i, cid in enumerate(SEVERITIES, 1)]
        result = coverage_score(make_conditions(), rows)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["uncovered_conditions"], [])
        self.assertEqual(result["orphan_rows"], [])

    def test_empty_rows_all_uncovered_zero_ratio(self):
        """Step 4 an empty rows list is valid: every condition uncovered, 0.0."""
        result = coverage_score(make_conditions(), [])
        self.assertEqual(result["coverage"], 0.0)
        self.assertEqual(result["uncovered_conditions"], list(SEVERITIES))
        self.assertEqual(result["covered_conditions"], [])
        self.assertEqual(result["orphan_rows"], [])

    def test_duplicate_rows_count_once_in_covered(self):
        """Step 4 two rows to one condition still count the condition once."""
        rows = [
            {"row_id": "R-01", "condition_id": "FC-01"},
            {"row_id": "R-02", "condition_id": "FC-01"},
        ]
        result = coverage_score(make_conditions(), rows)
        self.assertEqual(result["covered_conditions"], ["FC-01"])
        self.assertEqual(result["coverage"], 0.1)

    def test_input_order_preserved_for_lists(self):
        """Step 4 covered, uncovered and orphan lists preserve input order."""
        conditions = make_conditions()[::-1]
        rows = make_rows()[::-1]
        result = coverage_score(conditions, rows)
        self.assertEqual(
            result["covered_conditions"],
            ["FC-07", "FC-06", "FC-05", "FC-04", "FC-03", "FC-02", "FC-01"],
        )
        self.assertEqual(result["uncovered_conditions"], ["FC-10", "FC-09", "FC-08"])
        self.assertEqual(result["orphan_rows"], ["R-14", "R-13"])

    def test_unknown_condition_link_raises_valueerror(self):
        """Step 4 a row linking to a mistyped condition id raises ValueError."""
        rows = make_rows() + [{"row_id": "R-15", "condition_id": "FC-00"}]
        with self.assertRaises(ValueError):
            coverage_score(make_conditions(), rows)

    def test_same_row_as_orphan_with_none_is_accepted(self):
        """Step 4 writing the unknown link as condition_id None is an orphan."""
        rows = make_rows() + [{"row_id": "R-15", "condition_id": None}]
        result = coverage_score(make_conditions(), rows)
        self.assertIn("R-15", result["orphan_rows"])

    def test_empty_conditions_raises_valueerror(self):
        """Step 4 an empty condition table raises ValueError, nothing to cover."""
        with self.assertRaises(ValueError):
            coverage_score([], make_rows())

    def test_row_missing_row_id_raises_valueerror(self):
        """Step 4 a row dict without a row_id key raises ValueError."""
        with self.assertRaises(ValueError):
            coverage_score(make_conditions(), [{"condition_id": "FC-01"}])

    def test_row_missing_condition_id_key_raises_valueerror(self):
        """Step 4 a row dict without a condition_id key raises ValueError."""
        with self.assertRaises(ValueError):
            coverage_score(make_conditions(), [{"row_id": "R-01"}])


class CoverageBySeverityTests(unittest.TestCase):
    """Workflow step 5, the coverage_by_severity() class breakdown."""

    def test_worked_example_catastrophic_class(self):
        """Step 5 the catastrophic class covers 2 of 2 conditions at 1.0."""
        result = coverage_by_severity(make_conditions(), make_rows())
        self.assertEqual(result["catastrophic"], {"covered": 2, "uncovered": 0, "coverage": 1.0})

    def test_worked_example_hazardous_class(self):
        """Step 5 the hazardous class covers 2 of 2 conditions at 1.0."""
        result = coverage_by_severity(make_conditions(), make_rows())
        self.assertEqual(result["hazardous"], {"covered": 2, "uncovered": 0, "coverage": 1.0})

    def test_worked_example_major_class(self):
        """Step 5 the major class covers 3 of 3 conditions at 1.0."""
        result = coverage_by_severity(make_conditions(), make_rows())
        self.assertEqual(result["major"], {"covered": 3, "uncovered": 0, "coverage": 1.0})

    def test_worked_example_minor_class_zero_coverage(self):
        """Step 5 the minor class covers 0 of 3 conditions, coverage 0.0."""
        result = coverage_by_severity(make_conditions(), make_rows())
        self.assertEqual(result["minor"], {"covered": 0, "uncovered": 3, "coverage": 0.0})

    def test_severity_order_follows_first_appearance(self):
        """Step 5 the severity dict order follows first appearance in conditions."""
        result = coverage_by_severity(make_conditions(), make_rows())
        self.assertEqual(list(result), ["catastrophic", "hazardous", "major", "minor"])

    def test_severities_without_conditions_omitted(self):
        """Step 5 a severity value held by no condition never appears."""
        result = coverage_by_severity(make_conditions()[:4], make_rows()[:7])
        self.assertEqual(list(result), ["catastrophic", "hazardous"])
        self.assertEqual(result["catastrophic"], {"covered": 2, "uncovered": 0, "coverage": 1.0})
        self.assertNotIn("minor", result)

    def test_empty_rows_all_classes_zero(self):
        """Step 5 with no rows every severity class shows 0.0 coverage."""
        result = coverage_by_severity(make_conditions(), [])
        self.assertEqual(result["catastrophic"]["coverage"], 0.0)
        self.assertEqual(result["catastrophic"], {"covered": 0, "uncovered": 2, "coverage": 0.0})
        self.assertEqual(result["minor"], {"covered": 0, "uncovered": 3, "coverage": 0.0})

    def test_missing_severity_field_raises_valueerror(self):
        """Step 5 a condition without a severity field raises ValueError."""
        conditions = [{"id": "FC-01", "description": "loss of pitch control"}]
        with self.assertRaises(ValueError):
            coverage_by_severity(conditions, make_rows())

    def test_empty_conditions_raises_valueerror(self):
        """Step 5 an empty condition table raises ValueError."""
        with self.assertRaises(ValueError):
            coverage_by_severity([], make_rows())

    def test_unknown_condition_link_raises_valueerror(self):
        """Step 5 applies the same typo guard as the overall mapping."""
        rows = make_rows() + [{"row_id": "R-15", "condition_id": "FC-99"}]
        with self.assertRaises(ValueError):
            coverage_by_severity(make_conditions(), rows)


if __name__ == "__main__":
    unittest.main()
