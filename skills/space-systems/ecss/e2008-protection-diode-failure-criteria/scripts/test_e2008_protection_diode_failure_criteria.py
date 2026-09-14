#!/usr/bin/env python3
"""Contract test for protection diode failure criteria, clause 9.7.1 (offline)."""

import copy
import unittest

from e2008_protection_diode_failure_criteria_logic import (
    BLOCKING_FUNCTION_LOST,
    DEFAULT_FAILURE_CRITERIA,
    MEASURED_PARAMETERS,
    OBSERVABLE_CONDITIONS,
    SPECIMEN_FAILED,
    SPECIMEN_NOT_EVALUATED,
    SPECIMEN_PASSED,
    SUBGROUP_FAILED,
    SUBGROUP_MEETS_CRITERIA,
    SUBGROUP_NOT_EVALUABLE,
    absolute_limit_respected,
    assess_diode_specimen,
    assess_diode_subgroup,
    degradation_sense,
    drift_within_allowance,
    measured_parameters,
    observable_conditions,
    parameter_drift,
    validate_failure_criteria,
)

BEFORE = {
    "forward-voltage-drop": 0.80,
    "reverse-leakage-current": 1.0e-6,
    "reverse-breakdown-voltage": 60.0,
    "junction-thermal-resistance": 12.0,
}


def _specimen(specimen_id="pd-001", after=None, conditions=None, before=None):
    return {
        "specimen_id": specimen_id,
        "before_readings": dict(before if before is not None else BEFORE),
        "after_readings": dict(after if after is not None else BEFORE),
        "observed_conditions": list(conditions or []),
    }


def _subgroup(specimens=None, **overrides):
    subgroup = {
        "subgroup_id": "sg-diode-thermal-cycling",
        "test_reference": "protection-diode-thermal-cycling-subgroup",
        "specimens": specimens
        if specimens is not None
        else [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)],
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
            validate_failure_criteria("fail anything that looks unwell")

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
    def test_measured_parameters_come_back_as_a_tuple_copy(self):
        parameters = measured_parameters()
        self.assertEqual(parameters, MEASURED_PARAMETERS)
        self.assertIsInstance(parameters, tuple)

    def test_observable_conditions_come_back_as_a_tuple_copy(self):
        conditions = observable_conditions()
        self.assertEqual(conditions, OBSERVABLE_CONDITIONS)
        self.assertIsInstance(conditions, tuple)

    def test_a_body_crack_is_an_observable_condition(self):
        self.assertIn("diode-body-crack", observable_conditions())

    def test_leakage_degrades_upwards_and_breakdown_downwards(self):
        self.assertEqual(degradation_sense("reverse-leakage-current"), "increase")
        self.assertEqual(degradation_sense("reverse-breakdown-voltage"), "decrease")

    def test_unknown_parameter_has_no_sense(self):
        with self.assertRaises(ValueError):
            degradation_sense("forward-enthusiasm")


class ParameterDriftTests(unittest.TestCase):
    def test_a_rising_forward_drop_reads_as_decay(self):
        drift = parameter_drift("forward-voltage-drop", 0.80, 0.88)
        self.assertAlmostEqual(drift["degradation"], 0.08, places=9)
        self.assertEqual(drift["sense"], "increase")

    def test_a_falling_forward_drop_reads_as_negative_decay(self):
        drift = parameter_drift("forward-voltage-drop", 0.80, 0.76)
        self.assertLess(drift["degradation"], 0.0)

    def test_a_falling_breakdown_voltage_reads_as_decay(self):
        drift = parameter_drift("reverse-breakdown-voltage", 60.0, 54.0)
        self.assertAlmostEqual(drift["degradation"], 6.0, places=9)
        self.assertEqual(drift["sense"], "decrease")

    def test_relative_drift_is_taken_against_the_before_reading(self):
        drift = parameter_drift("reverse-breakdown-voltage", 60.0, 54.0)
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
        self.assertTrue(
            absolute_limit_respected("reverse-breakdown-voltage", 40.0, 40.0)
        )

    def test_a_falling_parameter_under_its_floor_is_not_respected(self):
        self.assertFalse(
            absolute_limit_respected("reverse-breakdown-voltage", 35.0, 40.0)
        )


class SpecimenTests(unittest.TestCase):
    def test_an_unchanged_part_passes(self):
        result = assess_diode_specimen(_specimen())
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertEqual(result["failure_modes"], [])

    def test_a_leakage_rise_past_its_allowance_fails_the_part(self):
        after = dict(BEFORE)
        after["reverse-leakage-current"] = 2.0e-6
        result = assess_diode_specimen(_specimen(after=after))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertIn(
            "reverse-leakage-current-drift-exceeded", result["failure_modes"]
        )

    def test_a_small_drift_can_still_break_the_absolute_limit(self):
        before = dict(BEFORE)
        before["forward-voltage-drop"] = 1.08
        after = dict(before)
        after["forward-voltage-drop"] = 1.14
        result = assess_diode_specimen(_specimen(before=before, after=after))
        self.assertIn(
            "forward-voltage-drop-outside-absolute-limit", result["failure_modes"]
        )
        self.assertNotIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])

    def test_a_large_drift_can_still_sit_inside_the_absolute_limit(self):
        before = dict(BEFORE)
        before["forward-voltage-drop"] = 0.50
        after = dict(before)
        after["forward-voltage-drop"] = 0.90
        result = assess_diode_specimen(_specimen(before=before, after=after))
        self.assertIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])
        self.assertNotIn(
            "forward-voltage-drop-outside-absolute-limit", result["failure_modes"]
        )

    def test_a_numerically_clean_part_still_fails_on_an_observed_crack(self):
        result = assess_diode_specimen(_specimen(conditions=["diode-body-crack"]))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertEqual(result["failure_modes"], ["diode-body-crack"])

    def test_an_observed_condition_the_specification_omits_does_not_fail_the_part(self):
        criteria = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        criteria["disqualifying_conditions"] = ("diode-body-crack",)
        result = assess_diode_specimen(
            _specimen(conditions=["adhering-contamination"]), criteria
        )
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertEqual(result["observed_conditions"], ["adhering-contamination"])

    def test_every_mode_is_named_not_only_the_first(self):
        after = dict(BEFORE)
        after["reverse-leakage-current"] = 9.0e-6
        after["reverse-breakdown-voltage"] = 30.0
        result = assess_diode_specimen(
            _specimen(after=after, conditions=["encapsulation-damage"])
        )
        self.assertGreaterEqual(len(result["failure_modes"]), 5)

    def test_a_junction_that_stopped_blocking_is_its_own_mode(self):
        after = dict(BEFORE)
        after["reverse-breakdown-voltage"] = 0.0
        result = assess_diode_specimen(_specimen(after=after))
        self.assertIn(BLOCKING_FUNCTION_LOST, result["failure_modes"])

    def test_a_missing_after_reading_is_not_evaluated_rather_than_passed(self):
        after = dict(BEFORE)
        del after["junction-thermal-resistance"]
        result = assess_diode_specimen(_specimen(after=after))
        self.assertEqual(result["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertEqual(
            result["unread_parameters"], ["junction-thermal-resistance"]
        )
        self.assertFalse(result["failed"])

    def test_a_missing_after_reading_does_not_hide_a_real_failure(self):
        after = dict(BEFORE)
        del after["junction-thermal-resistance"]
        result = assess_diode_specimen(
            _specimen(after=after, conditions=["diode-body-crack"])
        )
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)

    def test_a_missing_before_reading_is_also_unread(self):
        before = dict(BEFORE)
        del before["forward-voltage-drop"]
        result = assess_diode_specimen(_specimen(before=before))
        self.assertIn("forward-voltage-drop", result["unread_parameters"])

    def test_the_limiting_margin_is_the_smallest_one(self):
        after = dict(BEFORE)
        after["forward-voltage-drop"] = 0.86
        result = assess_diode_specimen(_specimen(after=after))
        self.assertAlmostEqual(
            result["limiting_margin"],
            result["margins"]["forward-voltage-drop"],
            places=9,
        )

    def test_an_unknown_observed_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_specimen(_specimen(conditions=["diode-haunted"]))

    def test_a_specimen_without_an_identifier_rejected(self):
        specimen = _specimen()
        del specimen["specimen_id"]
        with self.assertRaises(ValueError):
            assess_diode_specimen(specimen)

    def test_a_specimen_without_before_readings_rejected(self):
        specimen = _specimen()
        specimen["before_readings"] = {}
        with self.assertRaises(ValueError):
            assess_diode_specimen(specimen)

    def test_non_sequence_observed_conditions_rejected(self):
        specimen = _specimen()
        specimen["observed_conditions"] = "diode-body-crack"
        with self.assertRaises(ValueError):
            assess_diode_specimen(specimen)

    def test_findings_name_the_part(self):
        after = dict(BEFORE)
        after["reverse-leakage-current"] = 8.0e-6
        result = assess_diode_specimen(_specimen("pd-042", after=after))
        self.assertTrue(any("pd-042" in finding for finding in result["findings"]))


class SubgroupTests(unittest.TestCase):
    def test_a_clean_subgroup_meets_the_criteria(self):
        result = assess_diode_subgroup(_subgroup())
        self.assertEqual(result["verdict"], SUBGROUP_MEETS_CRITERIA)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["failed_fraction"], 0.0, places=9)

    def test_one_failed_part_fails_a_zero_allowance_subgroup(self):
        specimens = [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["diode-body-crack"]
        result = assess_diode_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_FAILED)
        self.assertEqual(result["failed_specimen_ids"], ["pd-001"])

    def test_the_failed_share_is_reported(self):
        specimens = [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["diode-body-crack"]
        result = assess_diode_subgroup(_subgroup(specimens))
        self.assertAlmostEqual(result["failed_fraction"], 0.25, places=9)

    def test_a_share_landing_on_the_allowance_is_admissible(self):
        criteria = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        criteria["max_failed_fraction"] = 0.25
        specimens = [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["diode-body-crack"]
        result = assess_diode_subgroup(_subgroup(specimens), criteria)
        self.assertEqual(result["verdict"], SUBGROUP_MEETS_CRITERIA)
        self.assertTrue(result["failed_share_within_allowance"])

    def test_an_unevaluated_part_blocks_the_subgroup_verdict(self):
        specimens = [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)]
        del specimens[2]["after_readings"]["junction-thermal-resistance"]
        result = assess_diode_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_NOT_EVALUABLE)
        self.assertEqual(result["unevaluated_specimen_ids"], ["pd-003"])

    def test_modes_are_grouped_by_specimen(self):
        specimens = [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[1]["observed_conditions"] = ["solder-void-beyond-limit"]
        specimens[3]["observed_conditions"] = ["solder-void-beyond-limit"]
        result = assess_diode_subgroup(_subgroup(specimens))
        self.assertEqual(
            result["modes_by_specimen"]["solder-void-beyond-limit"],
            ["pd-002", "pd-004"],
        )

    def test_assessments_come_back_in_identifier_order(self):
        specimens = [_specimen("pd-00%d" % n) for n in (4, 1, 3, 2)]
        result = assess_diode_subgroup(_subgroup(specimens))
        ids = [entry["specimen_id"] for entry in result["specimen_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_specimen_identifier_rejected(self):
        specimens = [_specimen("pd-001"), _specimen("pd-001")]
        with self.assertRaises(ValueError):
            assess_diode_subgroup(_subgroup(specimens))

    def test_an_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_subgroup(_subgroup([]))

    def test_a_subgroup_without_a_test_reference_rejected(self):
        subgroup = _subgroup()
        del subgroup["test_reference"]
        with self.assertRaises(ValueError):
            assess_diode_subgroup(subgroup)

    def test_non_mapping_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_subgroup([_specimen()])

    def test_the_subgroup_carries_every_specimen_finding(self):
        specimens = [_specimen("pd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["contact-metallisation-lifted"]
        result = assess_diode_subgroup(_subgroup(specimens))
        self.assertTrue(
            any(
                "contact-metallisation-lifted" in finding
                for finding in result["findings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
