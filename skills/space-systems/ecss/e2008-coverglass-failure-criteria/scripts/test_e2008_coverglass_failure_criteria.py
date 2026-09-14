#!/usr/bin/env python3
"""Contract test for coverglass failure criteria, clause 8.8.1 (offline)."""

import copy
import unittest

from e2008_coverglass_failure_criteria_logic import (
    COATING_CONDUCTION_LOST,
    DEFAULT_FAILURE_CRITERIA,
    MEASURED_PROPERTIES,
    OBSERVABLE_CONDITIONS,
    SPECIMEN_FAILED,
    SPECIMEN_NOT_EVALUATED,
    SPECIMEN_PASSED,
    SUBGROUP_FAILED,
    SUBGROUP_MEETS_CRITERIA,
    SUBGROUP_NOT_EVALUABLE,
    assess_coverglass_specimen,
    assess_subgroup,
    measured_properties,
    observable_conditions,
    property_change,
    property_within_allowance,
    validate_failure_criteria,
)

BEFORE = {
    "solar-transmittance": 0.960,
    "surface-conductivity": 1.0e-8,
    "solar-absorptance": 0.080,
}


def _specimen(specimen_id="cg-001", after=None, conditions=None, before=None):
    return {
        "specimen_id": specimen_id,
        "before_readings": dict(before if before is not None else BEFORE),
        "after_readings": dict(after if after is not None else BEFORE),
        "observed_conditions": list(conditions or []),
    }


def _subgroup(specimens=None, **overrides):
    subgroup = {
        "subgroup_id": "sg-thermal-cycling",
        "test_reference": "coverglass-thermal-cycling-subgroup",
        "specimens": specimens
        if specimens is not None
        else [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)],
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
        broken["specification_reference"] = "  "
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_criteria("fail anything that looks bad")

    def test_unknown_graded_property_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["property_allowances"]["coverglass-taste"] = 0.1
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_allowance_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["property_allowances"]["solar-transmittance"] = 1.4
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_empty_condition_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["disqualifying_conditions"] = ()
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)

    def test_unknown_disqualifying_condition_rejected(self):
        broken = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        broken["disqualifying_conditions"] = ("coating-smells-odd",)
        with self.assertRaises(ValueError):
            validate_failure_criteria(broken)


class VocabularyTests(unittest.TestCase):
    def test_measured_properties_come_back_as_a_tuple_copy(self):
        props = measured_properties()
        self.assertEqual(props, MEASURED_PROPERTIES)
        self.assertIsInstance(props, tuple)

    def test_observable_conditions_come_back_as_a_tuple_copy(self):
        conditions = observable_conditions()
        self.assertEqual(conditions, OBSERVABLE_CONDITIONS)
        self.assertIsInstance(conditions, tuple)

    def test_crack_is_an_observable_condition(self):
        self.assertIn("coverglass-crack", observable_conditions())


class PropertyChangeTests(unittest.TestCase):
    def test_a_transmittance_drop_reads_as_decay(self):
        change = property_change("solar-transmittance", 0.96, 0.94)
        self.assertAlmostEqual(change["degradation"], 0.02, places=9)
        self.assertEqual(change["sense"], "decrease")

    def test_a_transmittance_rise_reads_as_negative_decay(self):
        change = property_change("solar-transmittance", 0.96, 0.97)
        self.assertLess(change["degradation"], 0.0)

    def test_an_absorptance_rise_reads_as_decay(self):
        change = property_change("solar-absorptance", 0.08, 0.09)
        self.assertAlmostEqual(change["degradation"], 0.01, places=9)
        self.assertEqual(change["sense"], "increase")

    def test_relative_decay_is_taken_against_the_before_reading(self):
        change = property_change("solar-transmittance", 0.80, 0.76)
        self.assertAlmostEqual(change["relative_degradation"], 0.05, places=9)

    def test_unknown_property_rejected(self):
        with self.assertRaises(ValueError):
            property_change("coverglass-mood", 1.0, 0.9)

    def test_zero_before_reading_rejected(self):
        with self.assertRaises(ValueError):
            property_change("solar-transmittance", 0.0, 0.9)

    def test_negative_after_reading_rejected(self):
        with self.assertRaises(ValueError):
            property_change("solar-transmittance", 0.9, -0.1)

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            property_change("solar-transmittance", True, 0.9)


class AllowanceTests(unittest.TestCase):
    def test_a_decay_inside_the_allowance_stands(self):
        change = property_within_allowance("solar-transmittance", 1.0, 0.99, 0.02)
        self.assertTrue(change["within_allowance"])
        self.assertAlmostEqual(change["margin"], 0.01, places=9)

    def test_a_decay_landing_on_the_allowance_is_admissible(self):
        change = property_within_allowance("solar-transmittance", 1.0, 0.98, 0.02)
        self.assertTrue(change["within_allowance"])
        self.assertAlmostEqual(change["margin"], 0.0, places=9)

    def test_a_decay_past_the_allowance_fails(self):
        change = property_within_allowance("solar-transmittance", 1.0, 0.90, 0.02)
        self.assertFalse(change["within_allowance"])

    def test_an_improvement_is_always_inside_the_allowance(self):
        change = property_within_allowance("solar-transmittance", 0.90, 0.95, 0.0)
        self.assertTrue(change["within_allowance"])


class SpecimenTests(unittest.TestCase):
    def test_an_unchanged_piece_passes(self):
        result = assess_coverglass_specimen(_specimen())
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertEqual(result["failure_modes"], [])

    def test_a_transmittance_loss_past_its_allowance_fails_the_piece(self):
        after = dict(BEFORE)
        after["solar-transmittance"] = 0.80
        result = assess_coverglass_specimen(_specimen(after=after))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertIn("solar-transmittance-degradation-exceeded", result["failure_modes"])

    def test_a_measured_clean_piece_still_fails_on_an_observed_crack(self):
        result = assess_coverglass_specimen(_specimen(conditions=["coverglass-crack"]))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertEqual(result["failure_modes"], ["coverglass-crack"])

    def test_an_observed_condition_the_specification_omits_does_not_fail_the_piece(self):
        criteria = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        criteria["disqualifying_conditions"] = ("coverglass-crack",)
        result = assess_coverglass_specimen(
            _specimen(conditions=["adhering-contamination"]), criteria
        )
        self.assertEqual(result["verdict"], SPECIMEN_PASSED)
        self.assertEqual(result["observed_conditions"], ["adhering-contamination"])

    def test_every_mode_is_named_not_only_the_first(self):
        after = dict(BEFORE)
        after["solar-transmittance"] = 0.70
        after["solar-absorptance"] = 0.20
        result = assess_coverglass_specimen(
            _specimen(after=after, conditions=["coating-delamination"])
        )
        self.assertEqual(len(result["failure_modes"]), 3)

    def test_a_coating_that_stopped_conducting_is_its_own_mode(self):
        after = dict(BEFORE)
        after["surface-conductivity"] = 0.0
        result = assess_coverglass_specimen(_specimen(after=after))
        self.assertIn(COATING_CONDUCTION_LOST, result["failure_modes"])

    def test_a_missing_after_reading_is_not_evaluated_rather_than_passed(self):
        after = dict(BEFORE)
        del after["solar-transmittance"]
        result = assess_coverglass_specimen(_specimen(after=after))
        self.assertEqual(result["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertEqual(result["unread_properties"], ["solar-transmittance"])
        self.assertFalse(result["failed"])

    def test_a_missing_after_reading_does_not_hide_a_real_failure(self):
        after = dict(BEFORE)
        del after["solar-transmittance"]
        result = assess_coverglass_specimen(
            _specimen(after=after, conditions=["coverglass-crack"])
        )
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)

    def test_the_limiting_margin_is_the_smallest_one(self):
        after = dict(BEFORE)
        after["solar-transmittance"] = 0.950
        result = assess_coverglass_specimen(_specimen(after=after))
        self.assertAlmostEqual(
            result["limiting_margin"], result["margins"]["solar-transmittance"], places=9
        )

    def test_an_unknown_observed_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_specimen(_specimen(conditions=["coverglass-haunted"]))

    def test_a_specimen_without_an_identifier_rejected(self):
        specimen = _specimen()
        del specimen["specimen_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_specimen(specimen)

    def test_a_specimen_without_before_readings_rejected(self):
        specimen = _specimen()
        specimen["before_readings"] = {}
        with self.assertRaises(ValueError):
            assess_coverglass_specimen(specimen)

    def test_non_sequence_observed_conditions_rejected(self):
        specimen = _specimen()
        specimen["observed_conditions"] = "coverglass-crack"
        with self.assertRaises(ValueError):
            assess_coverglass_specimen(specimen)

    def test_findings_name_the_piece(self):
        after = dict(BEFORE)
        after["solar-transmittance"] = 0.50
        result = assess_coverglass_specimen(_specimen("cg-042", after=after))
        self.assertTrue(any("cg-042" in finding for finding in result["findings"]))


class SubgroupTests(unittest.TestCase):
    def test_a_clean_subgroup_meets_the_criteria(self):
        result = assess_subgroup(_subgroup())
        self.assertEqual(result["verdict"], SUBGROUP_MEETS_CRITERIA)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["failed_fraction"], 0.0, places=9)

    def test_one_failed_piece_fails_a_zero_allowance_subgroup(self):
        specimens = [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["coverglass-crack"]
        result = assess_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_FAILED)
        self.assertEqual(result["failed_specimen_ids"], ["cg-001"])

    def test_the_failed_share_is_reported(self):
        specimens = [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["coverglass-crack"]
        result = assess_subgroup(_subgroup(specimens))
        self.assertAlmostEqual(result["failed_fraction"], 0.25, places=9)

    def test_a_share_landing_on_the_allowance_is_admissible(self):
        criteria = copy.deepcopy(DEFAULT_FAILURE_CRITERIA)
        criteria["max_failed_fraction"] = 0.25
        specimens = [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["coverglass-crack"]
        result = assess_subgroup(_subgroup(specimens), criteria)
        self.assertEqual(result["verdict"], SUBGROUP_MEETS_CRITERIA)
        self.assertTrue(result["failed_share_within_allowance"])

    def test_an_unevaluated_piece_blocks_the_subgroup_verdict(self):
        specimens = [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)]
        del specimens[2]["after_readings"]["solar-absorptance"]
        result = assess_subgroup(_subgroup(specimens))
        self.assertEqual(result["verdict"], SUBGROUP_NOT_EVALUABLE)
        self.assertEqual(result["unevaluated_specimen_ids"], ["cg-003"])

    def test_modes_are_grouped_by_specimen(self):
        specimens = [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[1]["observed_conditions"] = ["coating-blistering"]
        specimens[3]["observed_conditions"] = ["coating-blistering"]
        result = assess_subgroup(_subgroup(specimens))
        self.assertEqual(
            result["modes_by_specimen"]["coating-blistering"], ["cg-002", "cg-004"]
        )

    def test_assessments_come_back_in_identifier_order(self):
        specimens = [_specimen("cg-00%d" % n) for n in (4, 1, 3, 2)]
        result = assess_subgroup(_subgroup(specimens))
        ids = [entry["specimen_id"] for entry in result["specimen_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_specimen_identifier_rejected(self):
        specimens = [_specimen("cg-001"), _specimen("cg-001")]
        with self.assertRaises(ValueError):
            assess_subgroup(_subgroup(specimens))

    def test_an_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup(_subgroup([]))

    def test_a_subgroup_without_a_test_reference_rejected(self):
        subgroup = _subgroup()
        del subgroup["test_reference"]
        with self.assertRaises(ValueError):
            assess_subgroup(subgroup)

    def test_non_mapping_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup([_specimen()])

    def test_the_subgroup_carries_every_specimen_finding(self):
        specimens = [_specimen("cg-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["coating-delamination"]
        result = assess_subgroup(_subgroup(specimens))
        self.assertTrue(
            any("coating-delamination" in finding for finding in result["findings"])
        )


if __name__ == "__main__":
    unittest.main()
