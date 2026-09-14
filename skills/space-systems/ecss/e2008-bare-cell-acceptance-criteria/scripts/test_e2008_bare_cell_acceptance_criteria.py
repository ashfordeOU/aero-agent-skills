"""Contract tests for the clause 7.3.2.2.3 bare-cell acceptance criteria.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused acceptance
policy, an unreferenced or self-contradictory threshold set, a cell short
on either minimum, and a lot losing more cells than the declared allowance
admits.
"""

import unittest

from e2008_bare_cell_acceptance_criteria_logic import (
    CURRENT_AT_TEST_VOLTAGE,
    DEFAULT_ACCEPTANCE_POLICY,
    LOT_MEETS_DRAWING_LIMITS,
    LOT_REJECT_FRACTION_EXCEEDED,
    REQUIREMENT_NOT_ESTABLISHED,
    SHORT_CIRCUIT_CURRENT,
    assess_bare_cell_acceptance,
    cell_verdict,
    cell_verdicts,
    lot_reject_fraction,
    lot_within_reject_allowance,
    margin_fraction,
    marginal_cell_advisories,
    validate_acceptance_policy,
    validate_cell_record,
    validate_drawing_limits,
    weakest_cell,
)

MIN_SHORT_CIRCUIT = 0.480
MIN_AT_VOLTAGE = 0.460


def _policy(**overrides):
    policy = dict(DEFAULT_ACCEPTANCE_POLICY)
    policy.update(overrides)
    return policy


def _limits(**overrides):
    limits = {
        "drawing_reference": "SCD-8812 issue D",
        "min_short_circuit_current_a": MIN_SHORT_CIRCUIT,
        "min_current_at_test_voltage_a": MIN_AT_VOLTAGE,
        "test_voltage_v": 2.35,
    }
    limits.update(overrides)
    return limits


def _cells():
    return [
        {
            "id": "bc-01",
            "short_circuit_current_a": 0.504,
            "current_at_test_voltage_a": 0.489,
        },
        {
            "id": "bc-02",
            "short_circuit_current_a": 0.498,
            "current_at_test_voltage_a": 0.481,
        },
        {
            "id": "bc-03",
            "short_circuit_current_a": 0.512,
            "current_at_test_voltage_a": 0.495,
        },
    ]


def _case(**overrides):
    case = {"drawing_limits": _limits(), "cells": _cells()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_acceptance_policy(DEFAULT_ACCEPTANCE_POLICY),
            DEFAULT_ACCEPTANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy("max_reject_fraction")

    def test_reject_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(_policy(max_reject_fraction=1.4))

    def test_negative_reject_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(_policy(max_reject_fraction=-0.1))

    def test_a_zero_reject_allowance_is_a_legitimate_policy(self):
        self.assertIsNotNone(validate_acceptance_policy(_policy(max_reject_fraction=0.0)))

    def test_marginal_band_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(_policy(marginal_band_fraction=1.5))


class DrawingLimitTests(unittest.TestCase):
    def test_a_referenced_threshold_set_validates(self):
        checked = validate_drawing_limits(_limits())
        self.assertEqual(checked["drawing_reference"], "SCD-8812 issue D")
        self.assertAlmostEqual(
            checked["min_short_circuit_current_a"], MIN_SHORT_CIRCUIT, places=12
        )

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits("SCD-8812")

    def test_a_non_string_drawing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits(_limits(drawing_reference=8812))

    def test_a_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits(_limits(min_short_circuit_current_a=-0.48))

    def test_an_on_load_threshold_above_short_circuit_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits(_limits(min_current_at_test_voltage_a=0.52))

    def test_equal_thresholds_are_admitted(self):
        checked = validate_drawing_limits(
            _limits(min_current_at_test_voltage_a=MIN_SHORT_CIRCUIT)
        )
        self.assertAlmostEqual(
            checked["min_current_at_test_voltage_a"], MIN_SHORT_CIRCUIT, places=12
        )

    def test_a_blank_drawing_reference_survives_validation(self):
        checked = validate_drawing_limits(_limits(drawing_reference="  "))
        self.assertEqual(checked["drawing_reference"], "")


class CellRecordTests(unittest.TestCase):
    def test_a_cell_record_is_read_back(self):
        identifier, short_circuit, at_voltage = validate_cell_record(_cells()[0])
        self.assertEqual(identifier, "bc-01")
        self.assertAlmostEqual(short_circuit, 0.504, places=12)
        self.assertAlmostEqual(at_voltage, 0.489, places=12)

    def test_a_blank_cell_id_rejected(self):
        cell = _cells()[0]
        cell["id"] = " "
        with self.assertRaises(ValueError):
            validate_cell_record(cell)

    def test_a_missing_on_load_current_rejected(self):
        cell = _cells()[0]
        del cell["current_at_test_voltage_a"]
        with self.assertRaises(ValueError):
            validate_cell_record(cell)

    def test_a_boolean_current_rejected(self):
        cell = _cells()[0]
        cell["short_circuit_current_a"] = True
        with self.assertRaises(ValueError):
            validate_cell_record(cell)


class MarginTests(unittest.TestCase):
    def test_margin_is_the_fractional_excess(self):
        self.assertAlmostEqual(margin_fraction(0.528, 0.480), 0.1, places=9)

    def test_a_cell_on_the_threshold_has_zero_margin(self):
        self.assertAlmostEqual(margin_fraction(0.480, 0.480), 0.0, places=12)

    def test_a_short_cell_has_a_negative_margin(self):
        self.assertLess(margin_fraction(0.432, 0.480), 0.0)

    def test_a_zero_threshold_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            margin_fraction(0.48, 0.0)


class CellVerdictTests(unittest.TestCase):
    def test_a_comfortable_cell_is_accepted(self):
        verdict = cell_verdict(_cells()[0], _limits())
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["shortfalls"], ())

    def test_a_cell_exactly_on_both_thresholds_is_accepted(self):
        verdict = cell_verdict(
            {
                "id": "bc-tie",
                "short_circuit_current_a": MIN_SHORT_CIRCUIT,
                "current_at_test_voltage_a": MIN_AT_VOLTAGE,
            },
            _limits(),
        )
        self.assertTrue(verdict["accepted"])
        self.assertAlmostEqual(verdict["limiting_margin_fraction"], 0.0, places=12)

    def test_a_cell_short_on_load_only_is_refused(self):
        verdict = cell_verdict(
            {
                "id": "bc-04",
                "short_circuit_current_a": 0.500,
                "current_at_test_voltage_a": 0.410,
            },
            _limits(),
        )
        self.assertFalse(verdict["accepted"])
        self.assertEqual(verdict["shortfalls"], (CURRENT_AT_TEST_VOLTAGE,))

    def test_a_cell_short_on_both_names_both_shortfalls(self):
        verdict = cell_verdict(
            {
                "id": "bc-05",
                "short_circuit_current_a": 0.400,
                "current_at_test_voltage_a": 0.390,
            },
            _limits(),
        )
        self.assertEqual(
            verdict["shortfalls"], (SHORT_CIRCUIT_CURRENT, CURRENT_AT_TEST_VOLTAGE)
        )

    def test_the_limiting_margin_is_the_smaller_of_the_two(self):
        verdict = cell_verdict(_cells()[1], _limits())
        self.assertAlmostEqual(
            verdict["limiting_margin_fraction"],
            min(
                verdict["short_circuit_margin_fraction"],
                verdict["current_at_test_voltage_margin_fraction"],
            ),
            places=12,
        )

    def test_a_duplicate_cell_id_rejected(self):
        cells = _cells()
        cells[2]["id"] = "bc-01"
        with self.assertRaises(ValueError):
            cell_verdicts(cells, _limits())

    def test_an_empty_measured_population_rejected(self):
        with self.assertRaises(ValueError):
            cell_verdicts([], _limits())


class LotTests(unittest.TestCase):
    def test_a_clean_lot_rejects_nothing(self):
        verdicts = cell_verdicts(_cells(), _limits())
        self.assertAlmostEqual(lot_reject_fraction(verdicts), 0.0, places=12)

    def test_one_short_cell_in_four_is_a_quarter(self):
        cells = _cells()
        cells.append(
            {
                "id": "bc-04",
                "short_circuit_current_a": 0.400,
                "current_at_test_voltage_a": 0.390,
            }
        )
        verdicts = cell_verdicts(cells, _limits())
        self.assertAlmostEqual(lot_reject_fraction(verdicts), 0.25, places=12)

    def test_a_lot_exactly_on_the_allowance_is_admitted(self):
        cells = _cells()
        cells.append(
            {
                "id": "bc-04",
                "short_circuit_current_a": 0.400,
                "current_at_test_voltage_a": 0.390,
            }
        )
        verdicts = cell_verdicts(cells, _limits())
        self.assertTrue(
            lot_within_reject_allowance(verdicts, _policy(max_reject_fraction=0.25))
        )

    def test_the_weakest_cell_is_the_smallest_limiting_margin(self):
        verdicts = cell_verdicts(_cells(), _limits())
        self.assertEqual(weakest_cell(verdicts)["id"], "bc-02")

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            weakest_cell([])

    def test_a_cell_just_above_the_threshold_raises_an_advisory(self):
        verdicts = cell_verdicts(
            [
                {
                    "id": "bc-06",
                    "short_circuit_current_a": MIN_SHORT_CIRCUIT * 1.005,
                    "current_at_test_voltage_a": MIN_AT_VOLTAGE * 1.005,
                }
            ],
            _limits(),
        )
        advisories = marginal_cell_advisories(verdicts)
        self.assertEqual(len(advisories), 1)
        self.assertIn("bc-06", advisories[0])

    def test_a_comfortable_lot_raises_no_advisory(self):
        verdicts = cell_verdicts(_cells(), _limits())
        self.assertEqual(marginal_cell_advisories(verdicts), ())


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_lot_meets_the_drawing_limits(self):
        result = assess_bare_cell_acceptance(_case())
        self.assertEqual(result["verdict"], LOT_MEETS_DRAWING_LIMITS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["accepted_cells"]), 3)

    def test_a_missing_drawing_record_closes_the_assessment(self):
        case = _case()
        del case["drawing_limits"]
        result = assess_bare_cell_acceptance(case)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_blank_drawing_reference_closes_the_assessment(self):
        result = assess_bare_cell_acceptance(
            _case(drawing_limits=_limits(drawing_reference="   "))
        )
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)

    def test_too_many_short_cells_exceed_the_lot_allowance(self):
        cells = _cells()
        cells[0]["current_at_test_voltage_a"] = 0.400
        result = assess_bare_cell_acceptance(_case(cells=cells))
        self.assertEqual(result["verdict"], LOT_REJECT_FRACTION_EXCEEDED)
        self.assertIn("bc-01", result["rejected_cells"])

    def test_every_short_cell_is_named_not_only_the_first(self):
        cells = _cells()
        cells[0]["current_at_test_voltage_a"] = 0.400
        cells[1]["short_circuit_current_a"] = 0.300
        result = assess_bare_cell_acceptance(_case(cells=cells))
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_the_weakest_cell_travels_with_the_verdict(self):
        result = assess_bare_cell_acceptance(_case())
        self.assertEqual(result["weakest_cell_id"], "bc-02")
        self.assertGreater(result["weakest_cell_margin_fraction"], 0.0)

    def test_advisories_do_not_move_the_verdict(self):
        cells = [
            {
                "id": "bc-07",
                "short_circuit_current_a": MIN_SHORT_CIRCUIT * 1.004,
                "current_at_test_voltage_a": MIN_AT_VOLTAGE * 1.004,
            }
        ]
        result = assess_bare_cell_acceptance(_case(cells=cells))
        self.assertEqual(result["verdict"], LOT_MEETS_DRAWING_LIMITS)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_lot_reject_fraction_is_reported(self):
        result = assess_bare_cell_acceptance(_case())
        self.assertAlmostEqual(result["lot_reject_fraction"], 0.0, places=12)

    def test_a_missing_cell_record_rejected(self):
        case = _case()
        del case["cells"]
        with self.assertRaises(ValueError):
            assess_bare_cell_acceptance(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_acceptance(["drawing_limits"])


if __name__ == "__main__":
    unittest.main()
