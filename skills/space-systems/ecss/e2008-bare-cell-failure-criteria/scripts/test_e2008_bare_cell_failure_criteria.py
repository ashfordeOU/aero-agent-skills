"""Contract tests for the clause 7.6.1 bare-cell failure criteria.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: an unreferenced criteria
set, a cell that lost more than an allowance, a cell that stopped
conducting, a cell failed on an observed condition alone, and a subgroup
carrying a cell nobody finished measuring.
"""

import unittest

from e2008_bare_cell_failure_criteria_logic import (
    CELL_FAILED,
    CELL_NOT_EVALUATED,
    CELL_PASSED,
    CURRENT_DEGRADATION,
    DEFAULT_FAILURE_POLICY,
    DISQUALIFYING_CONDITION,
    ELECTRICAL_OPEN_CIRCUIT,
    MAXIMUM_POWER,
    POWER_DEGRADATION,
    REQUIREMENT_NOT_ESTABLISHED,
    SHORT_CIRCUIT_CURRENT,
    SUBGROUP_FAILURE_ALLOWANCE_EXCEEDED,
    SUBGROUP_NOT_EVALUABLE,
    SUBGROUP_WITHIN_FAILURE_ALLOWANCE,
    VOLTAGE_DEGRADATION,
    assess_bare_cell_failures,
    cell_disposition,
    cell_failure_modes,
    degradation_fraction,
    marginal_cell_advisories,
    subgroup_dispositions,
    subgroup_failed_fraction,
    subgroup_within_allowance,
    validate_cell_record,
    validate_failure_criteria,
    validate_failure_policy,
)

POWER_ALLOWANCE = 0.05
CURRENT_ALLOWANCE = 0.03
VOLTAGE_ALLOWANCE = 0.02
CONDITIONS = ("cracked cell", "delaminated contact", "burn mark")


def _policy(**overrides):
    policy = dict(DEFAULT_FAILURE_POLICY)
    policy.update(overrides)
    return policy


def _criteria(**overrides):
    criteria = {
        "criteria_reference": "TS-2044 issue C subgroup screen",
        "max_power_loss_fraction": POWER_ALLOWANCE,
        "max_short_circuit_loss_fraction": CURRENT_ALLOWANCE,
        "max_open_circuit_voltage_loss_fraction": VOLTAGE_ALLOWANCE,
        "disqualifying_conditions": list(CONDITIONS),
    }
    criteria.update(overrides)
    return criteria


def _cell(identifier="bc-01", power_loss=0.01, current_loss=0.01, voltage_loss=0.004,
          conditions=None):
    record = {
        "id": identifier,
        "power_before_w": 1.200,
        "power_after_w": 1.200 * (1.0 - power_loss),
        "short_circuit_current_before_a": 0.500,
        "short_circuit_current_after_a": 0.500 * (1.0 - current_loss),
        "open_circuit_voltage_before_v": 2.700,
        "open_circuit_voltage_after_v": 2.700 * (1.0 - voltage_loss),
    }
    if conditions is not None:
        record["observed_conditions"] = list(conditions)
    return record


def _subgroup():
    return [_cell("bc-01"), _cell("bc-02", power_loss=0.02), _cell("bc-03")]


def _case(**overrides):
    case = {"failure_criteria": _criteria(), "cells": _subgroup()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_failure_policy(DEFAULT_FAILURE_POLICY), DEFAULT_FAILURE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy("max_failed_fraction")

    def test_a_failed_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(max_failed_fraction=1.2))

    def test_a_negative_failed_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(max_failed_fraction=-0.1))

    def test_a_zero_failed_share_is_a_legitimate_policy(self):
        self.assertIsNotNone(validate_failure_policy(_policy(max_failed_fraction=0.0)))

    def test_a_marginal_band_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(marginal_band_fraction=1.4))


class CriteriaTests(unittest.TestCase):
    def test_a_referenced_criteria_set_validates(self):
        checked = validate_failure_criteria(_criteria())
        self.assertEqual(checked["criteria_reference"], "TS-2044 issue C subgroup screen")
        self.assertEqual(len(checked["disqualifying_conditions"]), 3)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria("TS-2044")

    def test_a_non_string_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria(_criteria(criteria_reference=2044))

    def test_a_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria(_criteria(max_power_loss_fraction=0.0))

    def test_an_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria(_criteria(max_power_loss_fraction=1.5))

    def test_a_condition_list_that_is_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria(_criteria(disqualifying_conditions="cracked cell"))

    def test_a_repeated_disqualifying_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria(
                _criteria(disqualifying_conditions=["cracked cell", "cracked cell"])
            )

    def test_an_unnamed_disqualifying_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria(_criteria(disqualifying_conditions=["  "]))

    def test_a_blank_reference_survives_validation(self):
        checked = validate_failure_criteria(_criteria(criteria_reference="   "))
        self.assertEqual(checked["criteria_reference"], "")


class DegradationTests(unittest.TestCase):
    def test_degradation_is_the_share_lost(self):
        self.assertAlmostEqual(degradation_fraction(1.200, 1.080), 0.1, places=9)

    def test_an_unchanged_parameter_lost_nothing(self):
        self.assertAlmostEqual(degradation_fraction(1.200, 1.200), 0.0, places=12)

    def test_a_higher_after_reading_is_a_negative_loss(self):
        self.assertLess(degradation_fraction(1.200, 1.230), 0.0)

    def test_a_zero_before_reading_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            degradation_fraction(0.0, 1.100)


class CellRecordTests(unittest.TestCase):
    def test_a_cell_record_is_read_back(self):
        record = validate_cell_record(_cell(), _criteria())
        self.assertEqual(record["id"], "bc-01")
        self.assertAlmostEqual(record["readings"][MAXIMUM_POWER]["loss"], 0.01, places=9)

    def test_a_blank_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell(identifier=" "), _criteria())

    def test_a_missing_before_reading_rejected(self):
        cell = _cell()
        del cell["power_before_w"]
        with self.assertRaises(ValueError):
            validate_cell_record(cell, _criteria())

    def test_a_negative_after_reading_rejected(self):
        cell = _cell()
        cell["power_after_w"] = -0.2
        with self.assertRaises(ValueError):
            validate_cell_record(cell, _criteria())

    def test_a_missing_after_reading_is_recorded_not_assumed(self):
        cell = _cell()
        del cell["power_after_w"]
        record = validate_cell_record(cell, _criteria())
        self.assertEqual(record["missing_parameters"], (MAXIMUM_POWER,))

    def test_an_implausible_gain_is_a_setup_defect(self):
        cell = _cell(power_loss=-0.30)
        with self.assertRaises(ValueError):
            validate_cell_record(cell, _criteria())

    def test_a_condition_the_criteria_never_listed_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_record(_cell(conditions=["scratched busbar"]), _criteria())

    def test_a_non_list_condition_field_rejected(self):
        cell = _cell()
        cell["observed_conditions"] = "cracked cell"
        with self.assertRaises(ValueError):
            validate_cell_record(cell, _criteria())

    def test_a_repeated_observed_condition_is_recorded_once(self):
        record = validate_cell_record(
            _cell(conditions=["cracked cell", "cracked cell"]), _criteria()
        )
        self.assertEqual(record["observed_conditions"], ("cracked cell",))


class FailureModeTests(unittest.TestCase):
    def test_a_clean_cell_shows_no_mode(self):
        self.assertEqual(cell_failure_modes(_cell(), _criteria())["modes"], ())

    def test_a_power_loss_past_its_allowance_is_a_mode(self):
        modes = cell_failure_modes(_cell(power_loss=0.09), _criteria())["modes"]
        self.assertEqual(modes, (POWER_DEGRADATION,))

    def test_a_loss_exactly_on_the_allowance_is_admitted(self):
        modes = cell_failure_modes(_cell(power_loss=POWER_ALLOWANCE), _criteria())["modes"]
        self.assertEqual(modes, ())

    def test_every_mode_is_named_not_only_the_first(self):
        modes = cell_failure_modes(
            _cell(power_loss=0.09, current_loss=0.08, voltage_loss=0.07), _criteria()
        )["modes"]
        self.assertIn(POWER_DEGRADATION, modes)
        self.assertIn(CURRENT_DEGRADATION, modes)
        self.assertIn(VOLTAGE_DEGRADATION, modes)

    def test_a_cell_that_stopped_conducting_is_an_open_circuit(self):
        modes = cell_failure_modes(_cell(current_loss=0.99), _criteria())["modes"]
        self.assertIn(ELECTRICAL_OPEN_CIRCUIT, modes)

    def test_an_observed_condition_alone_fails_a_measured_clean_cell(self):
        detected = cell_failure_modes(_cell(conditions=["burn mark"]), _criteria())
        self.assertEqual(detected["modes"], (DISQUALIFYING_CONDITION,))
        self.assertTrue(detected["findings"])

    def test_a_cell_failing_measurement_and_inspection_names_both(self):
        modes = cell_failure_modes(
            _cell(power_loss=0.09, conditions=["cracked cell"]), _criteria()
        )["modes"]
        self.assertIn(POWER_DEGRADATION, modes)
        self.assertIn(DISQUALIFYING_CONDITION, modes)


class DispositionTests(unittest.TestCase):
    def test_a_clean_cell_passes(self):
        self.assertEqual(cell_disposition(_cell(), _criteria())["state"], CELL_PASSED)

    def test_a_degraded_cell_fails(self):
        self.assertEqual(
            cell_disposition(_cell(power_loss=0.09), _criteria())["state"], CELL_FAILED
        )

    def test_an_unfinished_cell_is_neither_passed_nor_failed(self):
        cell = _cell()
        del cell["short_circuit_current_after_a"]
        disposition = cell_disposition(cell, _criteria())
        self.assertEqual(disposition["state"], CELL_NOT_EVALUATED)
        self.assertEqual(disposition["missing_parameters"], (SHORT_CIRCUIT_CURRENT,))

    def test_a_failed_cell_is_failed_even_with_a_reading_missing(self):
        cell = _cell(power_loss=0.09)
        del cell["open_circuit_voltage_after_v"]
        self.assertEqual(cell_disposition(cell, _criteria())["state"], CELL_FAILED)

    def test_the_share_of_an_allowance_spent_is_reported(self):
        disposition = cell_disposition(_cell(power_loss=0.045), _criteria())
        self.assertAlmostEqual(
            disposition["allowance_used_fraction"], 0.9, places=9
        )


class SubgroupTests(unittest.TestCase):
    def test_a_clean_subgroup_fails_nothing(self):
        dispositions = subgroup_dispositions(_subgroup(), _criteria())
        self.assertAlmostEqual(subgroup_failed_fraction(dispositions), 0.0, places=12)

    def test_a_duplicate_cell_id_rejected(self):
        cells = _subgroup()
        cells[2]["id"] = "bc-01"
        with self.assertRaises(ValueError):
            subgroup_dispositions(cells, _criteria())

    def test_an_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_dispositions([], _criteria())

    def test_one_failed_cell_in_three_is_a_third(self):
        cells = _subgroup()
        cells[0]["power_after_w"] = 1.200 * 0.80
        dispositions = subgroup_dispositions(cells, _criteria())
        self.assertAlmostEqual(
            subgroup_failed_fraction(dispositions), 1.0 / 3.0, places=12
        )

    def test_a_subgroup_exactly_on_its_allowance_is_admitted(self):
        cells = _subgroup()
        cells[0]["power_after_w"] = 1.200 * 0.80
        dispositions = subgroup_dispositions(cells, _criteria())
        self.assertTrue(
            subgroup_within_allowance(dispositions, _policy(max_failed_fraction=1.0 / 3.0))
        )

    def test_a_cell_that_grazed_an_allowance_raises_an_advisory(self):
        dispositions = subgroup_dispositions([_cell(power_loss=0.048)], _criteria())
        advisories = marginal_cell_advisories(dispositions)
        self.assertEqual(len(advisories), 1)
        self.assertIn("bc-01", advisories[0])

    def test_a_comfortable_subgroup_raises_no_advisory(self):
        dispositions = subgroup_dispositions(_subgroup(), _criteria())
        self.assertEqual(marginal_cell_advisories(dispositions), ())


class AssessmentTests(unittest.TestCase):
    def test_a_clean_subgroup_stays_inside_the_allowance(self):
        result = assess_bare_cell_failures(_case())
        self.assertEqual(result["verdict"], SUBGROUP_WITHIN_FAILURE_ALLOWANCE)
        self.assertEqual(result["failed_cells"], [])
        self.assertEqual(result["findings"], [])

    def test_a_missing_criteria_set_closes_the_assessment(self):
        case = _case()
        del case["failure_criteria"]
        result = assess_bare_cell_failures(case)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_an_unreferenced_criteria_set_closes_the_assessment(self):
        result = assess_bare_cell_failures(
            _case(failure_criteria=_criteria(criteria_reference="   "))
        )
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)

    def test_one_failed_cell_fails_a_zero_allowance_subgroup(self):
        cells = _subgroup()
        cells[1]["power_after_w"] = 1.200 * 0.80
        result = assess_bare_cell_failures(_case(cells=cells))
        self.assertEqual(result["verdict"], SUBGROUP_FAILURE_ALLOWANCE_EXCEEDED)
        self.assertIn("bc-02", result["failed_cells"])

    def test_an_unfinished_cell_leaves_the_subgroup_unevaluable(self):
        cells = _subgroup()
        del cells[2]["power_after_w"]
        result = assess_bare_cell_failures(_case(cells=cells))
        self.assertEqual(result["verdict"], SUBGROUP_NOT_EVALUABLE)
        self.assertIn("bc-03", result["not_evaluated_cells"])

    def test_an_inspection_failure_reaches_the_subgroup_verdict(self):
        cells = _subgroup()
        cells[0]["observed_conditions"] = ["delaminated contact"]
        result = assess_bare_cell_failures(_case(cells=cells))
        self.assertEqual(result["verdict"], SUBGROUP_FAILURE_ALLOWANCE_EXCEEDED)
        self.assertIn(DISQUALIFYING_CONDITION, result["modes_seen"])

    def test_the_modes_seen_across_the_subgroup_are_gathered(self):
        cells = _subgroup()
        cells[0]["power_after_w"] = 1.200 * 0.80
        cells[1]["observed_conditions"] = ["burn mark"]
        result = assess_bare_cell_failures(_case(cells=cells))
        self.assertIn(POWER_DEGRADATION, result["modes_seen"])
        self.assertIn(DISQUALIFYING_CONDITION, result["modes_seen"])

    def test_the_failed_fraction_travels_with_the_verdict(self):
        result = assess_bare_cell_failures(_case())
        self.assertAlmostEqual(result["failed_fraction"], 0.0, places=12)
        self.assertEqual(result["cell_count"], 3)

    def test_the_criteria_reference_travels_with_the_verdict(self):
        result = assess_bare_cell_failures(_case())
        self.assertEqual(result["criteria_reference"], "TS-2044 issue C subgroup screen")

    def test_advisories_do_not_move_the_verdict(self):
        result = assess_bare_cell_failures(_case(cells=[_cell(power_loss=0.048)]))
        self.assertEqual(result["verdict"], SUBGROUP_WITHIN_FAILURE_ALLOWANCE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_missing_cells_list_rejected(self):
        case = _case()
        del case["cells"]
        with self.assertRaises(ValueError):
            assess_bare_cell_failures(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_failures(["failure_criteria"])


if __name__ == "__main__":
    unittest.main()
