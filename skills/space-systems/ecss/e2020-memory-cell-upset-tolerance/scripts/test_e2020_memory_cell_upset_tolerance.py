"""Contract tests for the clause 5.2.18.2.1 memory-cell upset tolerance.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a population with no
retrigger or status cell in it, a load-losing cell whose mitigation falls
short of the floor, a residual rate that outruns the mission allowance,
and the coverage claims that are refused before any rate is computed.
"""

import unittest

from e2020_memory_cell_upset_tolerance_logic import (
    CELL_POPULATION_NOT_ESTABLISHED,
    DEFAULT_UPSET_POLICY,
    LOAD_LOSS_PATH_UNMITIGATED,
    LOAD_LOSS_RATE_EXCEEDED,
    UPSET_TOLERANCE_DEMONSTRATED,
    assess_memory_cell_upset_tolerance,
    cell_records,
    costs_the_load,
    dominant_cell,
    group_by_scope,
    load_losing_cells,
    mission_load_loss_events,
    residual_upset_rate,
    undercovered_cells,
    upset_advisories,
    validate_cell_record,
    validate_upset_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_UPSET_POLICY)
    policy.update(overrides)
    return policy


def _cell(identifier, **overrides):
    cell = {
        "id": identifier,
        "function": "retrigger-enable",
        "upset_effect": "retrigger-inhibited",
        "upset_rate_per_day": 1e-6,
        "mitigation": "triple-redundant",
        "mitigation_coverage": 1.0,
    }
    cell.update(overrides)
    return cell


def _cells():
    return [
        _cell("retrig-arm"),
        _cell(
            "switch-state",
            function="status",
            upset_effect="status-misreported",
            mitigation="edac",
            mitigation_coverage=0.99,
        ),
        _cell(
            "cmd-latch",
            function="command-latch",
            upset_effect="load-switched-off",
            mitigation="none",
            mitigation_coverage=0.0,
        ),
    ]


def _case(**overrides):
    case = {"cells": _cells()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_upset_policy(DEFAULT_UPSET_POLICY), DEFAULT_UPSET_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_upset_policy("mission_days")

    def test_coverage_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_upset_policy(_policy(min_mitigation_coverage=1.2))

    def test_negative_event_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_upset_policy(_policy(max_load_loss_events=-1.0))

    def test_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_upset_policy(_policy(mission_days=0.0))

    def test_zero_dominance_advisory_rejected(self):
        with self.assertRaises(ValueError):
            validate_upset_policy(_policy(dominant_share_advisory=0.0))


class CellValidationTests(unittest.TestCase):
    def test_good_cell_validates(self):
        record = validate_cell_record(_cell("retrig-arm"))
        self.assertEqual(record["function"], "retrigger-enable")
        self.assertAlmostEqual(record["mitigation_coverage"], 1.0, places=9)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(["retrig-arm"])

    def test_blank_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell("  "))

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell("retrig-arm", function="shift-register"))

    def test_unknown_upset_effect_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell("retrig-arm", upset_effect="probably-fine"))

    def test_negative_upset_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell("retrig-arm", upset_rate_per_day=-1e-9))

    def test_coverage_claimed_without_a_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(
                _cell("retrig-arm", mitigation="none", mitigation_coverage=0.9)
            )

    def test_full_coverage_from_a_detect_only_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(
                _cell(
                    "retrig-arm",
                    mitigation="parity-detect",
                    mitigation_coverage=1.0,
                )
            )

    def test_partial_coverage_from_detection_is_allowed(self):
        record = validate_cell_record(
            _cell("retrig-arm", mitigation="parity-detect", mitigation_coverage=0.4)
        )
        self.assertAlmostEqual(record["mitigation_coverage"], 0.4, places=9)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            cell_records([])

    def test_duplicate_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            cell_records([_cell("retrig-arm"), _cell("retrig-arm")])


class ScopeTests(unittest.TestCase):
    def test_population_splits_into_scope_and_the_rest(self):
        in_scope, out_of_scope = group_by_scope(cell_records(_cells()))
        self.assertEqual(
            tuple(record["id"] for record in in_scope),
            ("retrig-arm", "switch-state"),
        )
        self.assertEqual(
            tuple(record["id"] for record in out_of_scope), ("cmd-latch",)
        )

    def test_a_retrigger_inhibit_costs_the_load(self):
        self.assertTrue(costs_the_load(validate_cell_record(_cell("retrig-arm"))))

    def test_a_status_misreport_does_not_cost_the_load_directly(self):
        record = validate_cell_record(
            _cell("switch-state", function="status", upset_effect="status-misreported")
        )
        self.assertFalse(costs_the_load(record))

    def test_an_out_of_scope_cell_is_not_counted_as_load_losing(self):
        losing = load_losing_cells(cell_records(_cells()))
        self.assertEqual(tuple(record["id"] for record in losing), ("retrig-arm",))


class RateTests(unittest.TestCase):
    def test_full_coverage_leaves_no_residual_rate(self):
        record = validate_cell_record(_cell("retrig-arm"))
        self.assertAlmostEqual(residual_upset_rate(record), 0.0, places=15)

    def test_partial_coverage_leaves_the_uncovered_share(self):
        record = validate_cell_record(
            _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9)
        )
        self.assertAlmostEqual(residual_upset_rate(record), 1e-7, places=15)

    def test_a_cell_that_cannot_cost_the_load_has_no_residual(self):
        record = validate_cell_record(
            _cell("switch-state", function="status", upset_effect="no-output-effect")
        )
        self.assertAlmostEqual(residual_upset_rate(record), 0.0, places=15)

    def test_mission_projection_multiplies_the_daily_residual(self):
        cells = _cells()
        cells[0] = _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9)
        events = mission_load_loss_events(
            cell_records(cells), _policy(mission_days=1000.0)
        )
        self.assertAlmostEqual(events, 1e-4, places=12)

    def test_undercovered_cells_are_named(self):
        cells = _cells()
        cells[0] = _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9)
        self.assertEqual(undercovered_cells(cell_records(cells)), ("retrig-arm",))

    def test_a_relaxed_floor_admits_partial_coverage(self):
        cells = _cells()
        cells[0] = _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9)
        self.assertEqual(
            undercovered_cells(
                cell_records(cells), _policy(min_mitigation_coverage=0.9)
            ),
            (),
        )

    def test_a_coverage_exactly_on_the_floor_is_not_undercovered(self):
        cells = _cells()
        cells[0] = _cell(
            "retrig-arm", mitigation="edac", mitigation_coverage=0.3 + 0.3 + 0.3
        )
        self.assertEqual(
            undercovered_cells(
                cell_records(cells), _policy(min_mitigation_coverage=0.9)
            ),
            (),
        )

    def test_the_dominant_cell_is_the_largest_residual(self):
        cells = [
            _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9),
            _cell(
                "retrig-arm-b",
                mitigation="edac",
                mitigation_coverage=0.5,
                upset_rate_per_day=2e-6,
            ),
        ]
        self.assertEqual(dominant_cell(cell_records(cells))[0], "retrig-arm-b")

    def test_no_dominant_cell_on_a_fully_covered_population(self):
        self.assertIsNone(dominant_cell(cell_records(_cells())))


class AdvisoryTests(unittest.TestCase):
    def test_a_status_cell_upset_is_named(self):
        advisories = upset_advisories(cell_records(_cells()))
        self.assertEqual(len(advisories), 1)
        self.assertIn("switch-state", advisories[0])

    def test_a_dominating_residual_is_named(self):
        cells = _cells()
        cells[0] = _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.5)
        advisories = upset_advisories(cell_records(cells))
        self.assertTrue(any("really one cell" in item for item in advisories))

    def test_scrub_derived_coverage_is_named(self):
        cells = _cells()
        cells[0] = _cell(
            "retrig-arm", mitigation="periodic-scrub", mitigation_coverage=1.0
        )
        advisories = upset_advisories(cell_records(cells))
        self.assertTrue(any("periodic scrubbing" in item for item in advisories))

    def test_a_population_with_nothing_out_of_scope_is_named(self):
        cells = _cells()[:2]
        advisories = upset_advisories(cell_records(cells))
        self.assertTrue(any("filtered before it was recorded" in item for item in advisories))


class AssessmentTests(unittest.TestCase):
    def test_a_tolerant_population_passes(self):
        result = assess_memory_cell_upset_tolerance(_case())
        self.assertEqual(result["verdict"], UPSET_TOLERANCE_DEMONSTRATED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_population_split_is_reported(self):
        result = assess_memory_cell_upset_tolerance(_case())
        self.assertEqual(result["in_scope_cells"], ("retrig-arm", "switch-state"))
        self.assertEqual(result["out_of_scope_cells"], ("cmd-latch",))
        self.assertEqual(result["load_losing_cells"], ("retrig-arm",))

    def test_a_population_with_no_in_scope_cell_closes_the_assessment(self):
        cells = [_cells()[2]]
        result = assess_memory_cell_upset_tolerance(_case(cells=cells))
        self.assertEqual(result["verdict"], CELL_POPULATION_NOT_ESTABLISHED)

    def test_an_unmitigated_load_losing_cell_fails(self):
        cells = _cells()
        cells[0] = _cell(
            "retrig-arm",
            upset_effect="load-switched-off",
            mitigation="none",
            mitigation_coverage=0.0,
        )
        result = assess_memory_cell_upset_tolerance(_case(cells=cells))
        self.assertEqual(result["verdict"], LOAD_LOSS_PATH_UNMITIGATED)
        self.assertEqual(result["undercovered_cells"], ("retrig-arm",))

    def test_every_undercovered_cell_is_named_not_only_the_first(self):
        cells = [
            _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.8),
            _cell("retrig-arm-b", mitigation="edac", mitigation_coverage=0.7),
        ]
        result = assess_memory_cell_upset_tolerance(_case(cells=cells))
        self.assertEqual(result["verdict"], LOAD_LOSS_PATH_UNMITIGATED)
        self.assertEqual(len(result["findings"]), 2)

    def test_a_residual_rate_over_the_allowance_fails(self):
        cells = _cells()
        cells[0] = _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9)
        result = assess_memory_cell_upset_tolerance(
            _case(cells=cells),
            _policy(min_mitigation_coverage=0.5, max_load_loss_events=1e-4),
        )
        self.assertEqual(result["verdict"], LOAD_LOSS_RATE_EXCEEDED)
        self.assertAlmostEqual(
            result["mission_load_loss_events"], 1e-7 * 5475.0, places=12
        )

    def test_a_projection_exactly_on_the_allowance_passes(self):
        cells = [_cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9)]
        result = assess_memory_cell_upset_tolerance(
            _case(cells=cells),
            _policy(
                min_mitigation_coverage=0.5,
                mission_days=1000.0,
                max_load_loss_events=1e-4,
            ),
        )
        self.assertAlmostEqual(result["mission_load_loss_events"], 1e-4, places=12)
        self.assertEqual(result["verdict"], UPSET_TOLERANCE_DEMONSTRATED)

    def test_the_dominant_cell_is_reported_on_a_passing_case(self):
        cells = [
            _cell("retrig-arm", mitigation="edac", mitigation_coverage=0.9),
            _cell(
                "retrig-arm-b",
                mitigation="edac",
                mitigation_coverage=0.5,
                upset_rate_per_day=4e-6,
            ),
        ]
        result = assess_memory_cell_upset_tolerance(
            _case(cells=cells),
            _policy(min_mitigation_coverage=0.5, max_load_loss_events=1.0),
        )
        self.assertEqual(result["dominant_cell"], "retrig-arm-b")
        self.assertAlmostEqual(result["dominant_residual_rate"], 2e-6, places=15)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_memory_cell_upset_tolerance(["cells"])

    def test_missing_cells_rejected(self):
        case = _case()
        del case["cells"]
        with self.assertRaises(ValueError):
            assess_memory_cell_upset_tolerance(case)


if __name__ == "__main__":
    unittest.main()
