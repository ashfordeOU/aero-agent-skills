"""Contract tests for the clause 7.3.7 layout review item logic."""

import unittest

from q6012_layout_review_item_logic import (
    GEOMETRY_TOLERANCE_UM,
    assess_layout_review,
    drawing_findings,
    minimum_pad_separation,
    pad_separation,
    pad_set_findings,
    pads_outside_outline,
    rule_check_findings,
    validate_outline,
    validate_pad,
)

OUTLINE = (0.0, 0.0, 1000.0, 800.0)
REQUIRED_PADS = ["rf-in", "rf-out", "vdd", "gnd"]


def pads():
    return [
        {"name": "rf-in", "x": 100.0, "y": 100.0},
        {"name": "rf-out", "x": 900.0, "y": 100.0},
        {"name": "vdd", "x": 100.0, "y": 700.0},
        {"name": "gnd", "x": 900.0, "y": 700.0},
    ]


def drawings():
    return [
        {"kind": "assembly", "id": "DRW-001", "issue": 3, "released": True},
        {"kind": "pad-layout", "id": "DRW-002", "issue": 3, "released": True},
        {"kind": "cross-section", "id": "DRW-003", "issue": 3, "released": True},
    ]


def checks():
    return [
        {"check": "drc", "error_count": 0},
        {"check": "lvs", "error_count": 0},
    ]


class ValidateOutlineTests(unittest.TestCase):
    def test_returns_float_quadruple(self):
        self.assertEqual(validate_outline((0, 0, 10, 20)), (0.0, 0.0, 10.0, 20.0))

    def test_collapsed_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_outline((5.0, 0.0, 5.0, 20.0))

    def test_inverted_height_rejected(self):
        with self.assertRaises(ValueError):
            validate_outline((0.0, 30.0, 10.0, 20.0))

    def test_wrong_arity_rejected(self):
        with self.assertRaises(ValueError):
            validate_outline((0.0, 0.0, 10.0))


class ValidatePadTests(unittest.TestCase):
    def test_returns_name_and_coordinates(self):
        self.assertEqual(
            validate_pad({"name": " rf-in ", "x": 1, "y": 2}), ("rf-in", 1.0, 2.0)
        )

    def test_missing_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            validate_pad({"name": "rf-in", "x": 1.0})

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_pad({"name": "  ", "x": 1.0, "y": 2.0})

    def test_boolean_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            validate_pad({"name": "rf-in", "x": True, "y": 2.0})


class SeparationTests(unittest.TestCase):
    def test_three_four_five_triangle(self):
        first = {"name": "a", "x": 0.0, "y": 0.0}
        second = {"name": "b", "x": 3.0, "y": 4.0}
        self.assertAlmostEqual(pad_separation(first, second), 5.0, places=9)

    def test_separation_is_symmetric(self):
        first = {"name": "a", "x": 2.0, "y": 7.0}
        second = {"name": "b", "x": -5.0, "y": 1.0}
        self.assertAlmostEqual(
            pad_separation(first, second), pad_separation(second, first), places=9
        )

    def test_minimum_picks_the_closest_pair(self):
        layout = pads() + [{"name": "bias", "x": 910.0, "y": 100.0}]
        closest = minimum_pad_separation(layout)
        self.assertAlmostEqual(closest["distance"], 10.0, places=9)
        self.assertEqual(set(closest["pair"]), {"rf-out", "bias"})

    def test_single_pad_cannot_be_searched(self):
        with self.assertRaises(ValueError):
            minimum_pad_separation([pads()[0]])


class OutlineContainmentTests(unittest.TestCase):
    def test_all_pads_inside_reports_nothing(self):
        self.assertEqual(pads_outside_outline(pads(), OUTLINE), [])

    def test_pad_beyond_the_edge_is_reported(self):
        layout = pads() + [{"name": "stray", "x": 1200.0, "y": 100.0}]
        self.assertEqual(pads_outside_outline(layout, OUTLINE), ["stray"])

    def test_pad_exactly_on_the_keep_out_line_stays_inside(self):
        layout = [{"name": "edge", "x": 50.0, "y": 400.0}, {"name": "mid", "x": 500.0, "y": 400.0}]
        self.assertEqual(pads_outside_outline(layout, OUTLINE, keep_out=50.0), [])

    def test_pad_inside_the_keep_out_is_reported(self):
        layout = [{"name": "edge", "x": 20.0, "y": 400.0}]
        self.assertEqual(pads_outside_outline(layout, OUTLINE, keep_out=50.0), ["edge"])

    def test_keep_out_wider_than_the_die_rejected(self):
        with self.assertRaises(ValueError):
            pads_outside_outline(pads(), OUTLINE, keep_out=600.0)

    def test_negative_keep_out_rejected(self):
        with self.assertRaises(ValueError):
            pads_outside_outline(pads(), OUTLINE, keep_out=-1.0)


class PadSetTests(unittest.TestCase):
    def test_complete_set_has_no_findings(self):
        result = pad_set_findings(pads(), REQUIRED_PADS)
        self.assertEqual(result, {"missing": [], "repeated": [], "unexpected": []})

    def test_missing_interface_pad_is_reported(self):
        layout = [p for p in pads() if p["name"] != "gnd"]
        self.assertEqual(pad_set_findings(layout, REQUIRED_PADS)["missing"], ["gnd"])

    def test_repeated_pad_name_is_reported(self):
        layout = pads() + [{"name": "vdd", "x": 500.0, "y": 400.0}]
        self.assertEqual(pad_set_findings(layout, REQUIRED_PADS)["repeated"], ["vdd"])

    def test_pad_outside_the_interface_definition_is_reported(self):
        layout = pads() + [{"name": "test-probe", "x": 500.0, "y": 400.0}]
        self.assertEqual(
            pad_set_findings(layout, REQUIRED_PADS)["unexpected"], ["test-probe"]
        )

    def test_non_sequence_required_names_rejected(self):
        with self.assertRaises(ValueError):
            pad_set_findings(pads(), "rf-in")


class DrawingSetTests(unittest.TestCase):
    REQUIRED = ["assembly", "pad-layout", "cross-section"]

    def test_complete_released_set_at_baseline_is_clean(self):
        result = drawing_findings(drawings(), self.REQUIRED, 3)
        self.assertEqual(result["missing_kinds"], [])
        self.assertEqual(result["behind_baseline"], [])
        self.assertEqual(result["ahead_of_baseline"], [])
        self.assertEqual(result["unreleased"], [])

    def test_missing_kind_is_reported(self):
        subset = drawings()[:2]
        self.assertEqual(
            drawing_findings(subset, self.REQUIRED, 3)["missing_kinds"], ["cross-section"]
        )

    def test_drawing_behind_the_baseline_is_reported(self):
        stale = drawings()
        stale[1]["issue"] = 2
        self.assertEqual(drawing_findings(stale, self.REQUIRED, 3)["behind_baseline"], ["DRW-002"])

    def test_drawing_ahead_of_the_baseline_is_reported(self):
        ahead = drawings()
        ahead[0]["issue"] = 4
        self.assertEqual(drawing_findings(ahead, self.REQUIRED, 3)["ahead_of_baseline"], ["DRW-001"])

    def test_unreleased_drawing_is_reported(self):
        draft = drawings()
        draft[2]["released"] = False
        self.assertEqual(drawing_findings(draft, self.REQUIRED, 3)["unreleased"], ["DRW-003"])

    def test_duplicate_kind_is_reported(self):
        doubled = drawings() + [
            {"kind": "assembly", "id": "DRW-009", "issue": 3, "released": True}
        ]
        self.assertEqual(drawing_findings(doubled, self.REQUIRED, 3)["duplicate_kinds"], ["assembly"])

    def test_zero_issue_rejected(self):
        bad = drawings()
        bad[0]["issue"] = 0
        with self.assertRaises(ValueError):
            drawing_findings(bad, self.REQUIRED, 3)

    def test_non_boolean_release_flag_rejected(self):
        bad = drawings()
        bad[0]["released"] = "yes"
        with self.assertRaises(ValueError):
            drawing_findings(bad, self.REQUIRED, 3)

    def test_empty_required_kinds_rejected(self):
        with self.assertRaises(ValueError):
            drawing_findings(drawings(), [], 3)


class RuleCheckTests(unittest.TestCase):
    REQUIRED = ["drc", "lvs"]

    def test_clean_checks_leave_nothing_open(self):
        result = rule_check_findings(checks(), self.REQUIRED)
        self.assertEqual(result["not_run"], [])
        self.assertEqual(result["residual"], [])

    def test_check_never_run_is_reported(self):
        result = rule_check_findings(checks()[:1], self.REQUIRED)
        self.assertEqual(result["not_run"], ["lvs"])

    def test_errors_fully_waived_leave_no_residual(self):
        run = [
            {
                "check": "drc",
                "error_count": 4,
                "waivers": [{"id": "W-01", "approved": True, "covers": 4}],
            },
            {"check": "lvs", "error_count": 0},
        ]
        self.assertEqual(rule_check_findings(run, self.REQUIRED)["residual"], [])

    def test_partly_waived_errors_leave_a_residual(self):
        run = [
            {
                "check": "drc",
                "error_count": 5,
                "waivers": [{"id": "W-01", "approved": True, "covers": 2}],
            },
            {"check": "lvs", "error_count": 0},
        ]
        residual = rule_check_findings(run, self.REQUIRED)["residual"]
        self.assertEqual(residual, [{"check": "drc", "errors": 3}])

    def test_unapproved_waiver_does_not_clear_and_is_named(self):
        run = [
            {
                "check": "drc",
                "error_count": 2,
                "waivers": [{"id": "W-07", "approved": False, "covers": 2}],
            },
            {"check": "lvs", "error_count": 0},
        ]
        result = rule_check_findings(run, self.REQUIRED)
        self.assertEqual(result["unapproved_waivers"], ["W-07"])
        self.assertEqual(result["residual"], [{"check": "drc", "errors": 2}])

    def test_over_waiving_is_a_bookkeeping_error(self):
        run = [
            {
                "check": "drc",
                "error_count": 1,
                "waivers": [{"id": "W-01", "approved": True, "covers": 3}],
            }
        ]
        with self.assertRaises(ValueError):
            rule_check_findings(run, self.REQUIRED)

    def test_repeated_check_rejected(self):
        run = checks() + [{"check": "drc", "error_count": 0}]
        with self.assertRaises(ValueError):
            rule_check_findings(run, self.REQUIRED)

    def test_negative_error_count_rejected(self):
        run = [{"check": "drc", "error_count": -1}]
        with self.assertRaises(ValueError):
            rule_check_findings(run, self.REQUIRED)


class AssessLayoutReviewTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "drawings": drawings(),
            "required_drawing_kinds": ["assembly", "pad-layout", "cross-section"],
            "baseline_issue": 3,
            "pads": pads(),
            "required_pads": list(REQUIRED_PADS),
            "outline": OUTLINE,
            "minimum_pitch_um": 100.0,
            "keep_out_um": 50.0,
            "checks": checks(),
            "required_checks": ["drc", "lvs"],
        }
        spec.update(overrides)
        return spec

    def test_clean_layout_item_closes(self):
        result = assess_layout_review(self._spec())
        self.assertEqual(result["disposition"], "closed")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["pitch_met"])

    def test_pitch_met_exactly_on_the_minimum(self):
        layout = [
            {"name": "rf-in", "x": 100.0, "y": 100.0},
            {"name": "rf-out", "x": 200.0, "y": 100.0},
            {"name": "vdd", "x": 100.0, "y": 700.0},
            {"name": "gnd", "x": 900.0, "y": 700.0},
        ]
        result = assess_layout_review(self._spec(pads=layout))
        self.assertAlmostEqual(result["closest_pad_pair"]["distance"], 100.0, places=9)
        self.assertTrue(result["pitch_met"])
        self.assertEqual(result["disposition"], "closed")

    def test_pitch_violation_opens_the_item(self):
        layout = pads() + [{"name": "bias", "x": 910.0, "y": 100.0}]
        spec = self._spec(pads=layout, required_pads=REQUIRED_PADS + ["bias"])
        result = assess_layout_review(spec)
        self.assertFalse(result["pitch_met"])
        self.assertEqual(result["disposition"], "open")

    def test_tolerance_absorbs_a_pitch_landing_on_the_bound(self):
        layout = [
            {"name": "rf-in", "x": 0.0 + 50.0, "y": 400.0},
            {"name": "rf-out", "x": 50.0 + 100.0 - GEOMETRY_TOLERANCE_UM / 4.0, "y": 400.0},
            {"name": "vdd", "x": 500.0, "y": 700.0},
            {"name": "gnd", "x": 900.0, "y": 700.0},
        ]
        result = assess_layout_review(self._spec(pads=layout))
        self.assertTrue(result["pitch_met"])

    def test_stale_drawing_opens_the_item(self):
        stale = drawings()
        stale[0]["issue"] = 2
        result = assess_layout_review(self._spec(drawings=stale))
        self.assertEqual(result["disposition"], "open")
        self.assertTrue(any("behind the design baseline" in f for f in result["findings"]))

    def test_missing_pad_opens_the_item(self):
        layout = [p for p in pads() if p["name"] != "gnd"]
        result = assess_layout_review(self._spec(pads=layout))
        self.assertEqual(result["disposition"], "open")
        self.assertIn("gnd", result["pad_set"]["missing"])

    def test_unwaived_rule_errors_open_the_item(self):
        run = [{"check": "drc", "error_count": 3}, {"check": "lvs", "error_count": 0}]
        result = assess_layout_review(self._spec(checks=run))
        self.assertEqual(result["disposition"], "open")
        self.assertEqual(result["rule_checks"]["residual"], [{"check": "drc", "errors": 3}])

    def test_every_finding_is_reported_not_just_the_first(self):
        stale = drawings()
        stale[0]["issue"] = 2
        layout = [p for p in pads() if p["name"] != "gnd"]
        run = [{"check": "drc", "error_count": 2}]
        result = assess_layout_review(self._spec(drawings=stale, pads=layout, checks=run))
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_non_positive_pitch_rejected(self):
        with self.assertRaises(ValueError):
            assess_layout_review(self._spec(minimum_pitch_um=0.0))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["outline"]
        with self.assertRaises(ValueError):
            assess_layout_review(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_layout_review(["drawings"])


if __name__ == "__main__":
    unittest.main()
