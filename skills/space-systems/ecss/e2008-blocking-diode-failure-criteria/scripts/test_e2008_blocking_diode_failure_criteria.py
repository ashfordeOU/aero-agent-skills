#!/usr/bin/env python3
"""Contract test for blocking diode failure criteria, clause 12.7.1 (offline)."""

import copy
import unittest

from e2008_blocking_diode_failure_criteria_logic import (
    BIAS_DEPENDENT_PARAMETERS,
    DEFAULT_FAILURE_CRITERIA,
    FORWARD_CONDUCTION_LOST,
    GRADED_PARAMETERS,
    OBSERVABLE_CONDITIONS,
    REVERSE_BLOCKING_LOST,
    SPECIMEN_FAILED,
    SPECIMEN_NOT_EVALUATED,
    SPECIMEN_PASSED,
    SUBGROUP_FAILED,
    SUBGROUP_MEETS_CRITERIA,
    SUBGROUP_NOT_EVALUABLE,
    absolute_limit_respected,
    assess_blocking_diode_specimen,
    assess_blocking_diode_subgroup,
    bias_adequate,
    bias_dependent_parameters,
    degradation_sense,
    drift_within_allowance,
    graded_parameters,
    observable_conditions,
    parameter_drift,
    validate_failure_criteria,
)

BEFORE = {
    "forward-voltage-drop": 0.80,
    "reverse-leakage-current": 1.0e-6,
    "reverse-blocking-voltage": 60.0,
    "thermal-resistance-junction-to-case": 12.0,
}


def _specimen(specimen_id="bd-001", after=None, conditions=None, before=None, bias=None):
    specimen = {
        "specimen_id": specimen_id,
        "before_readings": dict(before if before is not None else BEFORE),
        "after_readings": dict(after if after is not None else BEFORE),
        "observed_conditions": list(conditions or []),
    }
    if bias is not None:
        specimen["measurement_bias_v"] = bias
    return specimen


def _subgroup(specimens=None, **overrides):
    subgroup = {
        "subgroup_id": "sg-blocking-diode-endurance",
        "test_reference": "blocking-diode-endurance-subgroup",
        "specimens": specimens
        if specimens is not None
        else [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)],
    }
    subgroup.update(overrides)
    return subgroup


class CriteriaValidationTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_failure_criteria(DEFAULT_FAILURE_CRITERIA),
            DEFAULT_FAILURE_CRITERIA,
        )

    def test_criteria_without_a_specification_reference_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["specification_reference"] = "   "
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria("fail whatever looks unwell")

    def test_unknown_drift_parameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["drift_allowances"]["diode-mood"] = 0.1
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_drift_allowance_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["drift_allowances"]["forward-voltage-drop"] = 1.8
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_unknown_absolute_limit_parameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["absolute_limits"]["diode-shine"] = 3.0
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_negative_absolute_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["absolute_limits"]["forward-voltage-drop"] = -1.0
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_zero_reference_bias_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["reference_reverse_bias_v"] = 0.0
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_missing_open_circuit_threshold_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        del broken["open_circuit_forward_threshold_v"]
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_empty_condition_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["disqualifying_conditions"] = ()
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_unknown_disqualifying_condition_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["disqualifying_conditions"] = ("diode-looks-tired",)
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_failed_share_allowance_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["max_failed_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)


class VocabularyTests(unittest.TestCase):
    def test_graded_parameters_come_back_as_a_tuple_copy(self):
        parameters = graded_parameters()
        self.assertEqual(parameters, GRADED_PARAMETERS)
        self.assertIsInstance(parameters, tuple)

    def test_observable_conditions_come_back_as_a_tuple_copy(self):
        conditions = observable_conditions()
        self.assertEqual(conditions, OBSERVABLE_CONDITIONS)
        self.assertIsInstance(conditions, tuple)

    def test_bias_dependent_parameters_are_the_reverse_ones(self):
        self.assertEqual(bias_dependent_parameters(), BIAS_DEPENDENT_PARAMETERS)
        self.assertIn("reverse-leakage-current", bias_dependent_parameters())

    def test_a_die_crack_is_an_observable_condition(self):
        self.assertIn("die-crack", observable_conditions())

    def test_leakage_degrades_upwards_and_blocking_voltage_downwards(self):
        self.assertEqual(degradation_sense("reverse-leakage-current"), "increase")
        self.assertEqual(degradation_sense("reverse-blocking-voltage"), "decrease")

    def test_unknown_parameter_has_no_sense(self):
        with self.assertRaises(ValueError):
            degradation_sense("forward-enthusiasm")


class BiasTests(unittest.TestCase):
    def test_a_reading_above_the_reference_bias_is_comparable(self):
        self.assertTrue(bias_adequate(45.0, 30.0))

    def test_a_reading_at_the_reference_bias_is_comparable(self):
        self.assertTrue(bias_adequate(30.0, 30.0))

    def test_a_reading_below_the_reference_bias_is_not_comparable(self):
        self.assertFalse(bias_adequate(5.0, 30.0))

    def test_a_negative_bias_is_rejected(self):
        with self.assertRaises(ValueError):
            bias_adequate(-5.0, 30.0)


class ParameterDriftTests(unittest.TestCase):
    def test_a_rising_forward_drop_reads_as_decay(self):
        drift = parameter_drift("forward-voltage-drop", 0.80, 0.88)
        self.assertAlmostEqual(drift["degradation"], 0.08, places=9)
        self.assertEqual(drift["sense"], "increase")

    def test_a_falling_forward_drop_reads_as_negative_decay(self):
        drift = parameter_drift("forward-voltage-drop", 0.80, 0.76)
        self.assertLess(drift["degradation"], 0.0)

    def test_a_falling_blocking_voltage_reads_as_decay(self):
        drift = parameter_drift("reverse-blocking-voltage", 60.0, 54.0)
        self.assertAlmostEqual(drift["degradation"], 6.0, places=9)
        self.assertEqual(drift["sense"], "decrease")

    def test_relative_drift_is_taken_against_the_before_reading(self):
        drift = parameter_drift("reverse-blocking-voltage", 60.0, 54.0)
        self.assertAlmostEqual(drift["relative_drift"], 0.1, places=9)

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift("diode-charisma", 1.0, 0.9)

    def test_zero_before_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift("forward-voltage-drop", 0.0, 0.9)

    def test_negative_after_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift("forward-voltage-drop", 0.8, -0.1)

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift("forward-voltage-drop", True, 0.9)


class DriftAllowanceTests(unittest.TestCase):
    def test_a_drift_inside_the_allowance_stands(self):
        drift = drift_within_allowance("forward-voltage-drop", 1.0, 1.05, 0.10)
        self.assertTrue(drift["within_allowance"])
        self.assertAlmostEqual(drift["margin"], 0.05, places=9)

    def test_a_drift_landing_on_the_allowance_is_admissible(self):
        drift = drift_within_allowance("forward-voltage-drop", 1.0, 1.10, 0.10)
        self.assertTrue(drift["within_allowance"])
        self.assertAlmostEqual(drift["margin"], 0.0, places=9)

    def test_a_drift_past_the_allowance_fails(self):
        drift = drift_within_allowance("forward-voltage-drop", 1.0, 1.40, 0.10)
        self.assertFalse(drift["within_allowance"])

    def test_an_improvement_is_always_inside_the_allowance(self):
        drift = drift_within_allowance("reverse-leakage-current", 2.0e-6, 1.0e-6, 0.0)
        self.assertTrue(drift["within_allowance"])


class AbsoluteLimitTests(unittest.TestCase):
    def test_a_rising_parameter_under_its_ceiling_is_respected(self):
        self.assertTrue(absolute_limit_respected("forward-voltage-drop", 1.00, 1.10))

    def test_a_rising_parameter_landing_on_its_ceiling_is_respected(self):
        self.assertTrue(absolute_limit_respected("forward-voltage-drop", 1.10, 1.10))

    def test_a_rising_parameter_over_its_ceiling_is_not_respected(self):
        self.assertFalse(absolute_limit_respected("forward-voltage-drop", 1.30, 1.10))

    def test_a_falling_parameter_landing_on_its_floor_is_respected(self):
        self.assertTrue(absolute_limit_respected("reverse-blocking-voltage", 40.0, 40.0))

    def test_a_falling_parameter_under_its_floor_is_not_respected(self):
        self.assertFalse(absolute_limit_respected("reverse-blocking-voltage", 35.0, 40.0))


class SpecimenTests(unittest.TestCase):
    def test_an_unchanged_part_passes(self):
        result = assess_blocking_diode_specimen(_specimen())
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertEqual(result["failure_modes"], [])

    def test_a_leakage_rise_past_its_allowance_fails_the_part(self):
        after = dict(BEFORE)
        after["reverse-leakage-current"] = 2.0e-6
        result = assess_blocking_diode_specimen(_specimen(after=after))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertIn("reverse-leakage-current-drift-exceeded", result["failure_modes"])

    def test_a_small_drift_can_still_break_the_absolute_limit(self):
        before = dict(BEFORE)
        before["forward-voltage-drop"] = 1.08
        after = dict(before)
        after["forward-voltage-drop"] = 1.14
        result = assess_blocking_diode_specimen(_specimen(before=before, after=after))
        self.assertIn(
            "forward-voltage-drop-outside-absolute-limit", result["failure_modes"]
        )
        self.assertNotIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])

    def test_a_large_drift_can_still_sit_inside_the_absolute_limit(self):
        before = dict(BEFORE)
        before["forward-voltage-drop"] = 0.50
        after = dict(before)
        after["forward-voltage-drop"] = 0.90
        result = assess_blocking_diode_specimen(_specimen(before=before, after=after))
        self.assertIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])
        self.assertNotIn(
            "forward-voltage-drop-outside-absolute-limit", result["failure_modes"]
        )

    def test_a_numerically_clean_part_still_fails_on_an_observed_crack(self):
        result = assess_blocking_diode_specimen(_specimen(conditions=["die-crack"]))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertEqual(result["failure_modes"], ["die-crack"])

    def test_a_condition_the_specification_omits_does_not_fail_the_part(self):
        criteria = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        criteria["disqualifying_conditions"] = ("die-crack",)
        result = assess_blocking_diode_specimen(
            _specimen(conditions=["adhering-contamination"]), criteria
        )
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertEqual(result["observed_conditions"], ["adhering-contamination"])

    def test_a_junction_that_stopped_blocking_is_its_own_mode(self):
        after = dict(BEFORE)
        after["reverse-blocking-voltage"] = 0.0
        result = assess_blocking_diode_specimen(_specimen(after=after))
        self.assertIn(REVERSE_BLOCKING_LOST, result["failure_modes"])

    def test_a_diode_that_no_longer_conducts_forward_is_its_own_mode(self):
        after = dict(BEFORE)
        after["forward-voltage-drop"] = 9.0
        result = assess_blocking_diode_specimen(_specimen(after=after))
        self.assertIn(FORWARD_CONDUCTION_LOST, result["failure_modes"])

    def test_the_two_function_losses_are_different_modes(self):
        self.assertNotEqual(REVERSE_BLOCKING_LOST, FORWARD_CONDUCTION_LOST)

    def test_a_forward_drop_on_the_open_circuit_threshold_counts_as_open(self):
        after = dict(BEFORE)
        after["forward-voltage-drop"] = 5.0
        result = assess_blocking_diode_specimen(_specimen(after=after))
        self.assertIn(FORWARD_CONDUCTION_LOST, result["failure_modes"])

    def test_a_reverse_reading_taken_below_the_reference_bias_is_unread(self):
        result = assess_blocking_diode_specimen(_specimen(bias=5.0))
        self.assertEqual(result["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertFalse(result["measurement_bias_adequate"])
        self.assertIn("reverse-leakage-current", result["unread_parameters"])
        self.assertIn("reverse-blocking-voltage", result["unread_parameters"])

    def test_a_low_bias_does_not_make_the_forward_parameters_unread(self):
        result = assess_blocking_diode_specimen(_specimen(bias=5.0))
        self.assertNotIn("forward-voltage-drop", result["unread_parameters"])

    def test_a_reading_at_the_reference_bias_is_graded_normally(self):
        result = assess_blocking_diode_specimen(_specimen(bias=30.0))
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertTrue(result["measurement_bias_adequate"])

    def test_every_mode_is_named_not_only_the_first(self):
        after = dict(BEFORE)
        after["reverse-leakage-current"] = 9.0e-6
        after["reverse-blocking-voltage"] = 30.0
        result = assess_blocking_diode_specimen(
            _specimen(after=after, conditions=["encapsulation-damage"])
        )
        self.assertGreaterEqual(len(result["failure_modes"]), 5)

    def test_a_missing_after_reading_is_not_evaluated_rather_than_passed(self):
        after = dict(BEFORE)
        del after["thermal-resistance-junction-to-case"]
        result = assess_blocking_diode_specimen(_specimen(after=after))
        self.assertEqual(result["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertEqual(
            result["unread_parameters"], ["thermal-resistance-junction-to-case"]
        )
        self.assertFalse(result["failed"])

    def test_a_missing_after_reading_does_not_hide_a_real_failure(self):
        after = dict(BEFORE)
        del after["thermal-resistance-junction-to-case"]
        result = assess_blocking_diode_specimen(
            _specimen(after=after, conditions=["die-crack"])
        )
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)

    def test_a_missing_before_reading_is_also_unread(self):
        before = dict(BEFORE)
        del before["forward-voltage-drop"]
        result = assess_blocking_diode_specimen(_specimen(before=before))
        self.assertIn("forward-voltage-drop", result["unread_parameters"])

    def test_the_limiting_margin_is_the_smallest_one(self):
        after = dict(BEFORE)
        after["forward-voltage-drop"] = 0.86
        result = assess_blocking_diode_specimen(_specimen(after=after))
        self.assertAlmostEqual(
            result["limiting_margin"],
            result["margins"]["forward-voltage-drop"],
            places=9,
        )

    def test_an_unknown_observed_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_specimen(_specimen(conditions=["diode-haunted"]))

    def test_a_specimen_without_an_identifier_rejected(self):
        specimen = _specimen()
        del specimen["specimen_id"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_specimen(specimen)

    def test_a_specimen_without_before_readings_rejected(self):
        specimen = _specimen()
        specimen["before_readings"] = {}
        with self.assertRaises(ValueError):
            assess_blocking_diode_specimen(specimen)

    def test_non_sequence_observed_conditions_rejected(self):
        specimen = _specimen()
        specimen["observed_conditions"] = "die-crack"
        with self.assertRaises(ValueError):
            assess_blocking_diode_specimen(specimen)

    def test_findings_name_the_part(self):
        after = dict(BEFORE)
        after["reverse-leakage-current"] = 8.0e-6
        result = assess_blocking_diode_specimen(_specimen("bd-042", after=after))
        self.assertTrue(any("bd-042" in finding for finding in result["findings"]))


class SubgroupTests(unittest.TestCase):
    def test_a_clean_subgroup_meets_the_criteria(self):
        result = assess_blocking_diode_subgroup(_subgroup())
        self.assertEqual(result["verdict"], SUBGROUP_MEETS_CRITERIA)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["failed_fraction"], 0.0, places=9)

    def test_one_failed_part_fails_a_zero_allowance_subgroup(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["die-crack"]
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_FAILED)
        self.assertEqual(result["failed_specimen_ids"], ["bd-001"])

    def test_the_failed_share_is_reported(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["die-crack"]
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        self.assertAlmostEqual(result["failed_fraction"], 0.25, places=9)

    def test_a_share_landing_on_the_allowance_is_admissible(self):
        criteria = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        criteria["max_failed_fraction"] = 0.25
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["die-crack"]
        result = assess_blocking_diode_subgroup(_subgroup(specimens), criteria)
        self.assertEqual(result["verdict"], SUBGROUP_MEETS_CRITERIA)
        self.assertTrue(result["failed_share_within_allowance"])

    def test_an_unevaluated_part_blocks_the_subgroup_verdict(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        del specimens[2]["after_readings"]["thermal-resistance-junction-to-case"]
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_NOT_EVALUABLE)
        self.assertEqual(result["unevaluated_specimen_ids"], ["bd-003"])

    def test_a_low_bias_part_blocks_the_subgroup_verdict(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[1]["measurement_bias_v"] = 2.0
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_NOT_EVALUABLE)
        self.assertEqual(result["unevaluated_specimen_ids"], ["bd-002"])

    def test_modes_are_grouped_by_specimen(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[1]["observed_conditions"] = ["solder-void-beyond-limit"]
        specimens[3]["observed_conditions"] = ["solder-void-beyond-limit"]
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        self.assertEqual(
            result["modes_by_specimen"]["solder-void-beyond-limit"],
            ["bd-002", "bd-004"],
        )

    def test_assessments_come_back_in_identifier_order(self):
        specimens = [_specimen("bd-00%d" % n) for n in (4, 1, 3, 2)]
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        ids = [entry["specimen_id"] for entry in result["specimen_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_specimen_identifier_rejected(self):
        specimens = [_specimen("bd-001"), _specimen("bd-001")]
        with self.assertRaises(ValueError):
            assess_blocking_diode_subgroup(_subgroup(specimens))

    def test_an_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_subgroup(_subgroup([]))

    def test_a_subgroup_without_a_test_reference_rejected(self):
        subgroup = _subgroup()
        del subgroup["test_reference"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_subgroup(subgroup)

    def test_non_mapping_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_subgroup([_specimen()])

    def test_the_subgroup_carries_every_specimen_finding(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["contact-metallisation-lifted"]
        result = assess_blocking_diode_subgroup(_subgroup(specimens))
        self.assertTrue(
            any(
                "contact-metallisation-lifted" in finding
                for finding in result["findings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
