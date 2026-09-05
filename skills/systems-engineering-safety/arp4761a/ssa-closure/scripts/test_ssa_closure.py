"""Contract test for the ssa-closure leaf.

Workflow step 7 of the SKILL.md, the deterministic confirmation pass,
is implemented here: run python3 scripts/test_ssa_closure.py offline to
confirm every severity-class target lookup, per-condition margin and
strict meets verdict, the multi-condition closure rollup with its
closure-gate verdict, and the requirement status rollup produced by the
module over the post-implementation predicted probabilities.

The test docstrings name the SKILL.md workflow steps they exercise so
the value-delta sampler can see which fact terms (severity class,
quantitative probability target per flight hour, predicted probability,
per-condition margin, strict meets verdict, closed and open counts,
open condition ids, per-severity-class closure fraction, closure-gate
verdict, verification statuses, requirement closure list) and procedure
terms (target lookup, per-condition margin pass, multi-condition
closure rollup, requirement status rollup, close-out read) each method
covers.
"""

import unittest

import ssa_closure_logic as ssa

# Six assessed conditions from the SKILL.md worked example, targets per
# flight hour; predicted_q values are post-implementation estimates.
CONDITIONS = [
    {"id": "FC-01", "severity": "catastrophic", "predicted_q": 5e-10},
    {"id": "FC-02", "severity": "catastrophic", "predicted_q": 2e-9},
    {"id": "FC-03", "severity": "hazardous", "predicted_q": 3e-7},
    {"id": "FC-04", "severity": "hazardous", "predicted_q": 2e-8},
    {"id": "FC-05", "severity": "major", "predicted_q": 4e-6},
    {"id": "FC-06", "severity": "minor", "predicted_q": 9e-4},
]

# Five safety requirements from the worked example close-out.
REQUIREMENTS = [
    {"id": "REQ-1", "status": "verified"},
    {"id": "REQ-2", "status": "verified"},
    {"id": "REQ-3", "status": "verified"},
    {"id": "REQ-4", "status": "open"},
    {"id": "REQ-5", "status": "open"},
]


class SeverityTargetLookupTests(unittest.TestCase):
    """Workflow step 2, the severity-class target lookup over the four
    severity classes."""

    def test_spot_values_catastrophic_hazardous_major_minor(self):
        # Workflow step 2: catastrophic 1e-9, hazardous 1e-7, major
        # 1e-5, minor 1e-3 per flight hour.
        self.assertEqual(ssa.severity_target("catastrophic"), 1e-9)
        self.assertEqual(ssa.severity_target("hazardous"), 1e-7)
        self.assertEqual(ssa.severity_target("major"), 1e-5)
        self.assertEqual(ssa.severity_target("minor"), 1e-3)

    def test_targets_match_module_constants(self):
        # Workflow step 2: the lookup returns the module constants
        # TARGET_CATASTROPHIC through TARGET_MINOR unchanged.
        self.assertIs(ssa.severity_target("catastrophic"),
                      ssa.TARGET_CATASTROPHIC)
        self.assertIs(ssa.severity_target("hazardous"),
                      ssa.TARGET_HAZARDOUS)
        self.assertIs(ssa.severity_target("major"), ssa.TARGET_MAJOR)
        self.assertIs(ssa.severity_target("minor"), ssa.TARGET_MINOR)

    def test_no_target_classes_raise(self):
        # Workflow step 2: "no safety effect" and "none" carry no
        # quantitative target per flight hour and cannot be closed
        # against a number, so the lookup rejects both.
        with self.assertRaises(ValueError):
            ssa.severity_target("no safety effect")
        with self.assertRaises(ValueError):
            ssa.severity_target("none")

    def test_unknown_severity_raises(self):
        # Workflow step 2: a severity class outside the four accepted
        # strings, here "Severe", is rejected by the target lookup.
        with self.assertRaises(ValueError):
            ssa.severity_target("Severe")

    def test_empty_severity_string_raises(self):
        # Workflow step 2: an empty severity string fails the target
        # lookup.
        with self.assertRaises(ValueError):
            ssa.severity_target("")

    def test_whitespace_severity_raises(self):
        # Workflow step 2: the lookup match is exact, so "catastrophic "
        # with trailing whitespace is rejected.
        with self.assertRaises(ValueError):
            ssa.severity_target("catastrophic ")


class ConditionMarginPassTests(unittest.TestCase):
    """Workflow step 3, the per-condition margin pass over the assessed
    conditions with the strict meets verdict."""

    def test_fc01_catastrophic_meets_margin_two(self):
        # Workflow step 3: FC-01 at 5e-10 against the catastrophic
        # target 1e-9 meets with margin 2.0.
        out = ssa.condition_margin(5e-10, "catastrophic")
        self.assertTrue(out["meets"])
        self.assertAlmostEqual(out["margin"], 2.0, delta=1e-12)

    def test_fc02_catastrophic_misses_margin_half(self):
        # Workflow step 3: FC-02 at 2e-9 against 1e-9 misses with
        # margin 0.5.
        out = ssa.condition_margin(2e-9, "catastrophic")
        self.assertFalse(out["meets"])
        self.assertAlmostEqual(out["margin"], 0.5, delta=1e-12)

    def test_fc03_hazardous_margin_one_third(self):
        # Workflow step 3: FC-03 at 3e-7 against the hazardous target
        # 1e-7 gives margin 0.333333 within 1e-6 and misses.
        out = ssa.condition_margin(3e-7, "hazardous")
        self.assertFalse(out["meets"])
        self.assertAlmostEqual(out["margin"], 0.333333, delta=1e-6)

    def test_fc04_hazardous_meets_margin_five(self):
        # Workflow step 3: FC-04 at 2e-8 against 1e-7 gives margin 5.0.
        out = ssa.condition_margin(2e-8, "hazardous")
        self.assertTrue(out["meets"])
        self.assertAlmostEqual(out["margin"], 5.0, delta=1e-6)

    def test_fc05_major_meets_margin_two_point_five(self):
        # Workflow step 3: FC-05 at 4e-6 against the major target 1e-5
        # gives margin 2.5 within 1e-6.
        out = ssa.condition_margin(4e-6, "major")
        self.assertTrue(out["meets"])
        self.assertAlmostEqual(out["margin"], 2.5, delta=1e-6)

    def test_fc06_minor_meets_margin_ten_ninths(self):
        # Workflow step 3: FC-06 at 9e-4 against the minor target 1e-3
        # gives margin 1.11111 within 1e-6 of 10/9.
        out = ssa.condition_margin(9e-4, "minor")
        self.assertTrue(out["meets"])
        self.assertAlmostEqual(out["margin"], 10.0 / 9.0, delta=1e-6)
        self.assertGreater(out["margin"], 1.11111)

    def test_strict_boundary_equality_fails_and_just_below_meets(self):
        # Workflow step 3 strict-target rule: at predicted_q equal to
        # the target the meets verdict is False with margin exactly 1.0
        # (1e-3 does not meet a minor target), while 9.999e-4, strictly
        # below, meets.
        out = ssa.condition_margin(1e-3, "minor")
        self.assertFalse(out["meets"])
        self.assertEqual(out["margin"], 1.0)
        below = ssa.condition_margin(9.999e-4, "minor")
        self.assertTrue(below["meets"])
        self.assertGreater(below["margin"], 1.0)

    def test_margin_identity_target_over_predicted(self):
        # Workflow step 3: the margin is target / predicted_q, verified
        # at a quarter of the catastrophic target, which gives 4.0.
        out = ssa.condition_margin(2.5e-10, "catastrophic")
        self.assertAlmostEqual(out["margin"], 4.0, delta=1e-12)

    def test_meets_is_monotone_in_predicted_q(self):
        # Workflow step 3: lowering a predicted probability never flips
        # a meet to a miss, checked across hazardous magnitudes from
        # 5e-8 down to 1e-12.
        for q in (5e-8, 2e-8, 1e-9, 1e-12):
            self.assertTrue(ssa.condition_margin(q, "hazardous")["meets"])

    def test_non_physical_margins_raise(self):
        # Workflow step 3: a zero predicted probability leaves the
        # margin undefined, a negative one is non-physical, and an
        # unknown severity class fails the target lookup; all raise
        # ValueError.
        with self.assertRaises(ValueError):
            ssa.condition_margin(0.0, "major")
        with self.assertRaises(ValueError):
            ssa.condition_margin(-1e-6, "major")
        with self.assertRaises(ValueError):
            ssa.condition_margin(1e-6, "minor-ish")


class MultiConditionClosureRollupTests(unittest.TestCase):
    """Workflow step 4, the multi-condition closure rollup of the
    per-condition margins into the closure-gate verdict dict."""

    def test_worked_example_totals_and_gate(self):
        # Workflow step 4: the six worked-example conditions roll up to
        # total 6, closed 4, open 2 and overall_gate OPEN because two
        # conditions miss their targets.
        out = ssa.closure_rollup(CONDITIONS)
        self.assertEqual(out["total"], 6)
        self.assertEqual(out["closed"], 4)
        self.assertEqual(out["open"], 2)
        self.assertEqual(out["overall_gate"], "OPEN")

    def test_worked_example_open_condition_ids_in_input_order(self):
        # Workflow step 4: the open condition ids FC-02 and FC-03
        # appear in input order in open_conditions.
        out = ssa.closure_rollup(CONDITIONS)
        self.assertEqual(out["open_conditions"], ["FC-02", "FC-03"])

    def test_worked_example_per_severity_closure_fractions(self):
        # Workflow step 4: the per-severity-class closure fraction is
        # catastrophic 0.5, hazardous 0.5, major 1.0, minor 1.0.
        out = ssa.closure_rollup(CONDITIONS)
        frac = out["meets_by_severity"]
        self.assertAlmostEqual(frac["catastrophic"], 0.5, delta=1e-12)
        self.assertAlmostEqual(frac["hazardous"], 0.5, delta=1e-12)
        self.assertEqual(frac["major"], 1.0)
        self.assertEqual(frac["minor"], 1.0)

    def test_all_meeting_rollup_closes_the_gate(self):
        # Workflow step 4: when every condition meets its target the
        # rollup reports gate CLOSED with empty open_conditions, which
        # step 6 of the SKILL.md close-out read declares as the closed
        # verdict.
        conds = [
            {"id": "FC-A", "severity": "catastrophic", "predicted_q": 1e-10},
            {"id": "FC-B", "severity": "major", "predicted_q": 1e-6},
        ]
        out = ssa.closure_rollup(conds)
        self.assertEqual(out["overall_gate"], "CLOSED")
        self.assertEqual(out["open_conditions"], [])
        self.assertEqual(out["open"], 0)
        self.assertEqual(out["closed"], 2)

    def test_all_failing_rollup_stays_open(self):
        # Workflow step 4: an all-failing rollup reports gate OPEN with
        # open equal to total and closed zero.
        conds = [
            {"id": "FC-A", "severity": "catastrophic", "predicted_q": 2e-9},
            {"id": "FC-B", "severity": "minor", "predicted_q": 2e-3},
        ]
        out = ssa.closure_rollup(conds)
        self.assertEqual(out["overall_gate"], "OPEN")
        self.assertEqual(out["open"], 2)
        self.assertEqual(out["total"], 2)
        self.assertEqual(out["closed"], 0)

    def test_meets_by_severity_only_present_classes_in_order(self):
        # Workflow step 4: meets_by_severity contains only severity
        # classes present in the input, in catastrophic, hazardous,
        # major, minor order.
        conds = [
            {"id": "FC-A", "severity": "major", "predicted_q": 1e-6},
            {"id": "FC-B", "severity": "catastrophic", "predicted_q": 1e-10},
            {"id": "FC-C", "severity": "catastrophic", "predicted_q": 2e-9},
        ]
        out = ssa.closure_rollup(conds)
        self.assertEqual(list(out["meets_by_severity"].keys()),
                         ["catastrophic", "major"])
        self.assertAlmostEqual(out["meets_by_severity"]["catastrophic"],
                               0.5, delta=1e-12)
        self.assertEqual(out["meets_by_severity"]["major"], 1.0)

    def test_fractions_and_open_counts_balance_class_totals(self):
        # Workflow step 4 identity: closed plus open equals total, and
        # each per-severity-class closure fraction times its class total
        # recovers the closed count for that class.
        out = ssa.closure_rollup(CONDITIONS)
        self.assertEqual(out["closed"] + out["open"], out["total"])
        class_totals = {"catastrophic": 2, "hazardous": 2, "major": 1,
                        "minor": 1}
        for severity, class_total in class_totals.items():
            closed_n = out["meets_by_severity"][severity] * class_total
            self.assertAlmostEqual(closed_n, round(closed_n), delta=1e-9)

    def test_gate_closed_iff_open_conditions_empty(self):
        # Workflow step 6 close-out read: across several condition sets
        # the overall gate is CLOSED exactly when open_conditions is
        # empty.
        sets = [
            CONDITIONS,
            [{"id": "X", "severity": "minor", "predicted_q": 1e-6}],
            [{"id": "X", "severity": "minor", "predicted_q": 5e-3}],
        ]
        for conds in sets:
            out = ssa.closure_rollup(conds)
            self.assertEqual(
                out["overall_gate"] == "CLOSED",
                out["open_conditions"] == [],
            )

    def test_invalid_condition_sets_raise(self):
        # Workflow steps 1 and 4: an empty condition set leaves nothing
        # to close, an unknown severity class fails validation, and a
        # zero or negative predicted probability cannot be closed
        # against a target; all raise ValueError.
        with self.assertRaises(ValueError):
            ssa.closure_rollup([])
        with self.assertRaises(ValueError):
            ssa.closure_rollup(
                [{"id": "FC-A", "severity": "severe",
                  "predicted_q": 1e-6}]
            )
        with self.assertRaises(ValueError):
            ssa.closure_rollup(
                [{"id": "FC-A", "severity": "major",
                  "predicted_q": 0.0}]
            )
        with self.assertRaises(ValueError):
            ssa.closure_rollup(
                [{"id": "FC-A", "severity": "major",
                  "predicted_q": -1e-6}]
            )

    def test_condition_row_missing_id_raises(self):
        # Workflow step 1: the assessed condition set is assembled with
        # an id, severity class and predicted probability per row; a row
        # missing the id key fails validation.
        with self.assertRaises(ValueError):
            ssa.closure_rollup(
                [{"severity": "major", "predicted_q": 1e-6}]
            )


class RequirementStatusRollupTests(unittest.TestCase):
    """Workflow step 5, the requirement status rollup of the safety
    requirement verification statuses into the requirement closure
    list."""

    def test_worked_example_requirement_counts(self):
        # Workflow step 5: REQ-1 through REQ-5 roll up to total 5,
        # verified 3 and open 2 for the close-out statement.
        out = ssa.requirement_closure(REQUIREMENTS)
        self.assertEqual(out["total"], 5)
        self.assertEqual(out["verified"], 3)
        self.assertEqual(out["open"], 2)

    def test_worked_example_open_requirements_in_input_order(self):
        # Workflow step 5: open_requirements lists REQ-4 then REQ-5 in
        # input order.
        out = ssa.requirement_closure(REQUIREMENTS)
        self.assertEqual(out["open_requirements"], ["REQ-4", "REQ-5"])

    def test_empty_requirement_list_is_valid(self):
        # Workflow step 5: an empty requirement list is valid and rolls
        # up to zeros with an empty open_requirements.
        out = ssa.requirement_closure([])
        self.assertEqual(out,
                         {"total": 0, "verified": 0, "open": 0,
                          "open_requirements": []})

    def test_all_verified_requirements_close(self):
        # Workflow step 5: when every verification status is verified
        # the requirement closure list has no open items.
        reqs = [
            {"id": "REQ-A", "status": "verified"},
            {"id": "REQ-B", "status": "verified"},
        ]
        out = ssa.requirement_closure(reqs)
        self.assertEqual(out["verified"], 2)
        self.assertEqual(out["open"], 0)
        self.assertEqual(out["open_requirements"], [])

    def test_unclosable_statuses_raise(self):
        # Workflow step 5: statuses outside {"verified", "open"}, here
        # "closed" and "in review", raise ValueError.
        with self.assertRaises(ValueError):
            ssa.requirement_closure(
                [{"id": "REQ-A", "status": "closed"}]
            )
        with self.assertRaises(ValueError):
            ssa.requirement_closure(
                [{"id": "REQ-A", "status": "in review"}]
            )

    def test_rollup_dict_keys_exactly_as_documented(self):
        # Workflow steps 4 and 5: the closure dicts expose exactly the
        # documented keys (total, closed/open counts, open ids,
        # per-severity fractions or verification statuses, gate) with
        # no extras.
        rollup = ssa.closure_rollup(CONDITIONS)
        self.assertEqual(
            set(rollup.keys()),
            {"total", "closed", "open", "open_conditions",
             "meets_by_severity", "overall_gate"},
        )
        req_out = ssa.requirement_closure(REQUIREMENTS)
        self.assertEqual(set(req_out.keys()),
                         {"total", "verified", "open",
                          "open_requirements"})


if __name__ == "__main__":
    unittest.main()
