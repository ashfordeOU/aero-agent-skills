#!/usr/bin/env python3
"""Contract test for the grounding resistance test (offline).

Walks the clause workflow step by step: the grounding plan and the one
structural reference it names, the window each point category has to sit
in, the repeat-reading statistics and the measurement-quality screen,
the fixture compensation, the four verdicts a point can take, the
coverage accounting and the campaign roll-up. This is the gate 3 review
evidence for the leaf.
"""

import copy
import unittest

from e2008_grounding_resistance_test_logic import (
    BOND_ABOVE_WINDOW,
    BOND_BELOW_WINDOW,
    BOND_NOT_EVALUATED,
    BOND_NOT_MEASURED,
    BOND_OPEN,
    BOND_WITHIN_WINDOW,
    DEFAULT_GROUNDING_POLICY,
    DEFAULT_POINT_WINDOWS_OHM,
    GROUNDING_NOT_EVALUATED,
    GROUNDING_NOT_VERIFIED,
    GROUNDING_VERIFIED,
    POINT_CATEGORIES,
    compensated_bond_ohm,
    evaluate_grounding_campaign,
    evaluate_grounding_point,
    grounding_point_coverage,
    measurement_quality_findings,
    point_window_ohm,
    reading_statistics,
    validate_grounding_plan,
    validate_grounding_policy,
)

REFERENCE = "panel-root-fitting"

PLAN = {
    "structural_reference": REFERENCE,
    "points": [
        {"id": "substrate-bond-1", "category": "bonding-point"},
        {"id": "substrate-bond-2", "category": "bonding-point"},
        {"id": "coverglass-dissipative-path", "category": "dissipative-point"},
    ],
}


def _measurement(point_id, readings, technique="four-wire", current_a=0.5,
                 measured_to=REFERENCE, **extra):
    record = {
        "point_id": point_id,
        "readings": readings,
        "probe_technique": technique,
        "test_current_a": current_a,
        "measured_to": measured_to,
    }
    record.update(extra)
    return record


SOUND_MEASUREMENTS = [
    _measurement("substrate-bond-1", [0.0042, 0.0043, 0.0042]),
    _measurement("substrate-bond-2", [0.0051, 0.0050, 0.0051]),
    _measurement("coverglass-dissipative-path", [4.0e6, 4.1e6, 4.0e6]),
]


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIn(
            "min_test_current_a", validate_grounding_policy(dict(DEFAULT_GROUNDING_POLICY))
        )

    def test_zero_repeat_requirement_rejected(self):
        policy = dict(DEFAULT_GROUNDING_POLICY)
        policy["min_repeat_readings"] = 0
        with self.assertRaises(ValueError):
            validate_grounding_policy(policy)

    def test_relative_spread_above_one_rejected(self):
        policy = dict(DEFAULT_GROUNDING_POLICY)
        policy["max_relative_spread"] = 1.5
        with self.assertRaises(ValueError):
            validate_grounding_policy(policy)

    def test_non_positive_test_current_rejected(self):
        policy = dict(DEFAULT_GROUNDING_POLICY)
        policy["min_test_current_a"] = 0.0
        with self.assertRaises(ValueError):
            validate_grounding_policy(policy)


class WindowTests(unittest.TestCase):
    def test_bonding_point_takes_the_default_ceiling(self):
        window = point_window_ohm({"id": "b", "category": "bonding-point"})
        self.assertEqual(window, DEFAULT_POINT_WINDOWS_OHM["bonding-point"])

    def test_dissipative_point_has_a_floor_as_well(self):
        window = point_window_ohm({"id": "d", "category": "dissipative-point"})
        self.assertGreater(window[0], 0.0)
        self.assertIn("dissipative-point", POINT_CATEGORIES)

    def test_declared_window_overrides_the_default(self):
        window = point_window_ohm(
            {"id": "b", "category": "bonding-point", "max_resistance_ohm": 0.025}
        )
        self.assertAlmostEqual(window[1], 0.025, places=12)

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            point_window_ohm(
                {
                    "id": "b",
                    "category": "bonding-point",
                    "min_resistance_ohm": 0.5,
                    "max_resistance_ohm": 0.1,
                }
            )

    def test_unknown_point_category_rejected(self):
        with self.assertRaises(ValueError):
            point_window_ohm({"id": "b", "category": "wishful-point"})


class PlanTests(unittest.TestCase):
    def test_sound_plan_validates(self):
        self.assertEqual(len(validate_grounding_plan(copy.deepcopy(PLAN))["points"]), 3)

    def test_empty_point_list_rejected(self):
        plan = copy.deepcopy(PLAN)
        plan["points"] = []
        with self.assertRaises(ValueError):
            validate_grounding_plan(plan)

    def test_duplicate_point_id_rejected(self):
        plan = copy.deepcopy(PLAN)
        plan["points"][1]["id"] = "substrate-bond-1"
        with self.assertRaises(ValueError):
            validate_grounding_plan(plan)

    def test_reference_listed_as_its_own_point_rejected(self):
        plan = copy.deepcopy(PLAN)
        plan["points"][0]["id"] = REFERENCE
        with self.assertRaises(ValueError):
            validate_grounding_plan(plan)

    def test_plan_without_a_reference_rejected(self):
        plan = copy.deepcopy(PLAN)
        del plan["structural_reference"]
        with self.assertRaises(ValueError):
            validate_grounding_plan(plan)


class ReadingStatisticsTests(unittest.TestCase):
    def test_repeat_readings_reduce_to_a_mean_and_a_spread(self):
        stats = reading_statistics([0.010, 0.012, 0.011])
        self.assertAlmostEqual(stats["mean_ohm"], 0.011, places=12)
        self.assertAlmostEqual(stats["spread_ohm"], 0.002, places=12)
        self.assertEqual(stats["count"], 3)

    def test_relative_spread_is_referred_to_the_mean(self):
        stats = reading_statistics([0.9, 1.1])
        self.assertAlmostEqual(stats["relative_spread"], 0.2, places=12)

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            reading_statistics([])

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            reading_statistics([0.01, -0.01])


class QualityScreenTests(unittest.TestCase):
    def test_sound_measurement_raises_no_quality_finding(self):
        window = point_window_ohm(PLAN["points"][0])
        self.assertEqual(
            measurement_quality_findings(SOUND_MEASUREMENTS[0], window), []
        )

    def test_single_reading_is_reported(self):
        window = point_window_ohm(PLAN["points"][0])
        findings = measurement_quality_findings(
            _measurement("substrate-bond-1", [0.0042]), window
        )
        self.assertTrue(any("stable" in item for item in findings))

    def test_unstable_contact_is_reported(self):
        window = point_window_ohm(PLAN["points"][0])
        findings = measurement_quality_findings(
            _measurement("substrate-bond-1", [0.002, 0.009]), window
        )
        self.assertTrue(any("moved under the probe" in item for item in findings))

    def test_weak_test_current_is_reported(self):
        window = point_window_ohm(PLAN["points"][0])
        findings = measurement_quality_findings(
            _measurement("substrate-bond-1", [0.0042, 0.0043], current_a=0.001), window
        )
        self.assertTrue(any("film" in item for item in findings))


class CompensationTests(unittest.TestCase):
    def test_four_wire_mean_passes_through(self):
        self.assertAlmostEqual(
            compensated_bond_ohm(_measurement("p", [0.004, 0.004]), 0.010),
            0.004,
            places=12,
        )

    def test_two_wire_fixture_is_subtracted(self):
        reading = _measurement(
            "p", [2.0e6, 2.0e6], technique="two-wire", fixture_resistance_ohm=1.0e5
        )
        self.assertAlmostEqual(compensated_bond_ohm(reading, 1.0e9), 1.9e6, places=6)

    def test_two_wire_without_a_fixture_value_on_a_milliohm_window_rejected(self):
        reading = _measurement("p", [0.004, 0.004], technique="two-wire")
        with self.assertRaises(ValueError):
            compensated_bond_ohm(reading, 0.010)

    def test_fixture_larger_than_the_reading_rejected(self):
        reading = _measurement(
            "p", [0.004, 0.004], technique="two-wire", fixture_resistance_ohm=0.02
        )
        with self.assertRaises(ValueError):
            compensated_bond_ohm(reading, 5.0)


class PointVerdictTests(unittest.TestCase):
    def test_sound_bond_is_within_its_window(self):
        record = evaluate_grounding_point(
            PLAN["points"][0], SOUND_MEASUREMENTS[0], REFERENCE
        )
        self.assertEqual(record["verdict"], BOND_WITHIN_WINDOW)
        self.assertTrue(record["within_window"])

    def test_bond_exactly_on_the_ceiling_is_within_its_window(self):
        record = evaluate_grounding_point(
            PLAN["points"][0],
            _measurement("substrate-bond-1", [0.010, 0.010, 0.010]),
            REFERENCE,
        )
        self.assertAlmostEqual(record["bond_resistance_ohm"], 0.010, places=12)
        self.assertEqual(record["verdict"], BOND_WITHIN_WINDOW)

    def test_resistive_bond_is_above_its_window(self):
        record = evaluate_grounding_point(
            PLAN["points"][0],
            _measurement("substrate-bond-1", [0.040, 0.040, 0.040]),
            REFERENCE,
        )
        self.assertEqual(record["verdict"], BOND_ABOVE_WINDOW)

    def test_over_conductive_dissipative_path_is_below_its_window(self):
        record = evaluate_grounding_point(
            PLAN["points"][2],
            _measurement("coverglass-dissipative-path", [12.0, 12.0, 12.0]),
            REFERENCE,
        )
        self.assertEqual(record["verdict"], BOND_BELOW_WINDOW)
        self.assertFalse(record["within_window"])

    def test_no_reading_is_an_open_bond(self):
        record = evaluate_grounding_point(
            PLAN["points"][0], _measurement("substrate-bond-1", None), REFERENCE
        )
        self.assertEqual(record["verdict"], BOND_OPEN)

    def test_unmeasured_point_is_not_measured(self):
        record = evaluate_grounding_point(PLAN["points"][0], None, REFERENCE)
        self.assertEqual(record["verdict"], BOND_NOT_MEASURED)
        self.assertIsNone(record["within_window"])

    def test_reading_taken_to_a_neighbour_point_is_not_evaluated(self):
        record = evaluate_grounding_point(
            PLAN["points"][0],
            _measurement(
                "substrate-bond-1", [0.004, 0.004], measured_to="substrate-bond-2"
            ),
            REFERENCE,
        )
        self.assertEqual(record["verdict"], BOND_NOT_EVALUATED)
        self.assertTrue(any("declared reference" in item for item in record["findings"]))

    def test_unresolvable_two_wire_reading_is_not_evaluated(self):
        record = evaluate_grounding_point(
            PLAN["points"][0],
            _measurement("substrate-bond-1", [0.004, 0.004], technique="two-wire"),
            REFERENCE,
        )
        self.assertEqual(record["verdict"], BOND_NOT_EVALUATED)
        self.assertTrue(record["findings"])


class CoverageTests(unittest.TestCase):
    def test_full_coverage_is_complete(self):
        coverage = grounding_point_coverage(
            copy.deepcopy(PLAN), copy.deepcopy(SOUND_MEASUREMENTS)
        )
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["measured_count"], 3)

    def test_unmeasured_point_is_listed(self):
        coverage = grounding_point_coverage(
            copy.deepcopy(PLAN), copy.deepcopy(SOUND_MEASUREMENTS[:2])
        )
        self.assertEqual(coverage["unmeasured_ids"], ["coverglass-dissipative-path"])

    def test_repeated_point_is_listed(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements.append(_measurement("substrate-bond-1", [0.004, 0.004]))
        coverage = grounding_point_coverage(copy.deepcopy(PLAN), measurements)
        self.assertEqual(coverage["duplicate_ids"], ["substrate-bond-1"])

    def test_reading_at_an_undeclared_point_is_listed(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements.append(_measurement("bracket-nobody-declared", [0.004, 0.004]))
        coverage = grounding_point_coverage(copy.deepcopy(PLAN), measurements)
        self.assertEqual(coverage["unknown_ids"], ["bracket-nobody-declared"])


class CampaignTests(unittest.TestCase):
    def _campaign(self, measurements):
        return {
            "plan": copy.deepcopy(PLAN),
            "measurements": copy.deepcopy(measurements),
        }

    def test_sound_campaign_is_verified(self):
        result = evaluate_grounding_campaign(self._campaign(SOUND_MEASUREMENTS))
        self.assertEqual(result["verdict"], GROUNDING_VERIFIED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["failing_ids"], [])

    def test_resistive_bond_fails_the_campaign(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements[0]["readings"] = [0.05, 0.05, 0.05]
        result = evaluate_grounding_campaign(self._campaign(measurements))
        self.assertEqual(result["verdict"], GROUNDING_NOT_VERIFIED)
        self.assertIn("substrate-bond-1", result["failing_ids"])

    def test_unmeasured_point_leaves_the_campaign_unevaluated(self):
        result = evaluate_grounding_campaign(self._campaign(SOUND_MEASUREMENTS[:2]))
        self.assertEqual(result["verdict"], GROUNDING_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])

    def test_campaign_reports_the_reference_it_graded_against(self):
        result = evaluate_grounding_campaign(self._campaign(SOUND_MEASUREMENTS))
        self.assertEqual(result["structural_reference"], REFERENCE)

    def test_campaign_without_measurements_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_grounding_campaign({"plan": copy.deepcopy(PLAN)})

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_grounding_campaign("all bonds measured low")


if __name__ == "__main__":
    unittest.main()
