"""Contract tests for the ECSS-Q-ST-70-21C failed-screening disposition logic."""

import unittest

from q7021_failed_material_handling_logic import (
    FAILURE_SEVERITY,
    MITIGATION_EXCEEDANCE_CEILING,
    SEVERE_MODES,
    assess_failed_material,
    decide_disposition,
    governing_mode,
    observed_pass_fraction,
    required_retest_specimens,
    validate_failure_record,
)


def record(**over):
    base = {
        "material": "silicone-foam-grade-c",
        "modes": ["burn-length-exceeded"],
        "total_specimens": 5,
        "failed_specimens": 1,
        "exceedance_ratio": 0.05,
        "configuration_changeable": False,
        "mitigation_available": False,
        "use_as_is_requested": False,
    }
    base.update(over)
    return base


class ValidateFailureRecordTests(unittest.TestCase):
    def test_normalises_a_good_record(self):
        entry = validate_failure_record(record())
        self.assertEqual(entry["material"], "silicone-foam-grade-c")
        self.assertEqual(entry["modes"], ["burn-length-exceeded"])

    def test_duplicate_modes_are_collapsed(self):
        entry = validate_failure_record(record(modes=["flaming-drips", "flaming-drips"]))
        self.assertEqual(entry["modes"], ["flaming-drips"])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(modes=["smelled-bad"]))

    def test_empty_mode_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(modes=[]))

    def test_more_failures_than_specimens_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(total_specimens=3, failed_specimens=4))

    def test_zero_failures_rejected_because_this_is_a_failure_record(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(failed_specimens=0))

    def test_negative_exceedance_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(exceedance_ratio=-0.1))

    def test_non_boolean_configuration_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(configuration_changeable="maybe"))

    def test_blank_rationale_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(record(use_as_is_rationale_ref="   "))

    def test_missing_material_rejected(self):
        bad = record()
        del bad["material"]
        with self.assertRaises(ValueError):
            validate_failure_record(bad)


class GoverningModeTests(unittest.TestCase):
    def test_the_most_severe_mode_governs(self):
        self.assertEqual(
            governing_mode(["after-flame-exceeded", "drip-ignition", "flaming-drips"]),
            "drip-ignition")

    def test_a_single_mode_governs_itself(self):
        self.assertEqual(governing_mode(["flaming-drips"]), "flaming-drips")

    def test_severe_modes_outrank_every_other_mode(self):
        for severe in SEVERE_MODES:
            for other in FAILURE_SEVERITY:
                if other in SEVERE_MODES:
                    continue
                self.assertGreater(FAILURE_SEVERITY[severe], FAILURE_SEVERITY[other])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            governing_mode(["something-else"])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            governing_mode([])


class RetestSizingTests(unittest.TestCase):
    def test_pass_fraction_is_the_surviving_share(self):
        self.assertAlmostEqual(observed_pass_fraction(5, 1), 0.8, places=9)

    def test_pass_fraction_of_a_wholly_failed_set_is_zero(self):
        self.assertAlmostEqual(observed_pass_fraction(4, 4), 0.0, places=9)

    def test_extended_set_grows_as_the_pass_fraction_falls(self):
        self.assertEqual(required_retest_specimens(5, 1), 4)
        self.assertEqual(required_retest_specimens(5, 2), 5)

    def test_a_near_clean_set_still_owes_more_than_the_class_minimum(self):
        self.assertEqual(required_retest_specimens(100, 1, 3), 4)

    def test_a_wholly_failed_set_gives_no_extended_set(self):
        self.assertIsNone(required_retest_specimens(4, 4))

    def test_an_impractical_extended_set_is_refused(self):
        self.assertIsNone(required_retest_specimens(10, 9, 3))

    def test_zero_class_minimum_rejected(self):
        with self.assertRaises(ValueError):
            required_retest_specimens(5, 1, 0)

    def test_more_failures_than_specimens_rejected(self):
        with self.assertRaises(ValueError):
            observed_pass_fraction(3, 5)


class DispositionTests(unittest.TestCase):
    def test_isolated_burn_length_failure_goes_to_an_extended_set(self):
        result = decide_disposition(record())
        self.assertEqual(result["disposition"], "retest-extended-set")
        self.assertEqual(result["retest_specimens"], 4)

    def test_drip_ignition_rejects_when_the_installation_is_fixed(self):
        result = decide_disposition(record(modes=["drip-ignition"]))
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(result["severe"])

    def test_drip_ignition_redesigns_when_the_installation_can_change(self):
        result = decide_disposition(record(modes=["drip-ignition"],
                                           configuration_changeable=True))
        self.assertEqual(result["disposition"], "redesign-installation")

    def test_full_consumption_is_severe_even_with_one_failing_specimen(self):
        result = decide_disposition(record(modes=["full-consumption"]))
        self.assertEqual(result["disposition"], "reject")

    def test_the_severe_mode_governs_a_mixed_failure(self):
        result = decide_disposition(record(modes=["after-flame-exceeded", "drip-ignition"]))
        self.assertEqual(result["governing_mode"], "drip-ignition")

    def test_use_as_is_is_refused_behind_a_severe_mode(self):
        result = decide_disposition(record(modes=["drip-ignition"],
                                           use_as_is_requested=True,
                                           use_as_is_rationale_ref="RAT-001"))
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("use-as-is refused" in f for f in result["findings"]))

    def test_use_as_is_without_a_rationale_reference_is_a_finding(self):
        result = decide_disposition(record(use_as_is_requested=True))
        self.assertTrue(any("no rationale reference" in f for f in result["findings"]))

    def test_a_wholly_failed_set_rejects_when_the_installation_is_fixed(self):
        self.assertEqual(decide_disposition(record(failed_specimens=5))["disposition"],
                         "reject")

    def test_a_wholly_failed_set_can_go_to_a_configuration_change(self):
        result = decide_disposition(record(failed_specimens=5,
                                           configuration_changeable=True))
        self.assertEqual(result["disposition"], "configuration-change-and-retest")

    def test_a_majority_failure_is_not_sent_to_an_extended_set(self):
        result = decide_disposition(record(failed_specimens=4))
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["isolated_failure"])
        self.assertTrue(result["findings"])

    def test_a_marginal_majority_failure_may_be_carried_on_a_mitigation(self):
        result = decide_disposition(record(failed_specimens=4,
                                           mitigation_available=True,
                                           exceedance_ratio=0.05))
        self.assertEqual(result["disposition"], "accept-with-mitigation")

    def test_a_mitigation_does_not_carry_an_exceedance_past_the_ceiling(self):
        result = decide_disposition(record(failed_specimens=4,
                                           mitigation_available=True,
                                           exceedance_ratio=0.40))
        self.assertEqual(result["disposition"], "reject")

    def test_an_exceedance_exactly_on_the_ceiling_is_still_carried(self):
        result = decide_disposition(record(
            failed_specimens=4, mitigation_available=True,
            exceedance_ratio=MITIGATION_EXCEEDANCE_CEILING))
        self.assertEqual(result["disposition"], "accept-with-mitigation")

    def test_a_configuration_change_outranks_a_mitigation(self):
        result = decide_disposition(record(failed_specimens=4,
                                           configuration_changeable=True,
                                           mitigation_available=True))
        self.assertEqual(result["disposition"], "configuration-change-and-retest")

    def test_every_disposition_names_actions_and_evidence(self):
        for over in ({}, {"modes": ["drip-ignition"]}, {"failed_specimens": 5},
                     {"failed_specimens": 4, "mitigation_available": True}):
            result = decide_disposition(record(**over))
            self.assertTrue(result["actions"])
            self.assertTrue(result["evidence_required"])


class AssessFailedMaterialTests(unittest.TestCase):
    def test_a_rejection_closes_the_case(self):
        result = assess_failed_material({"record": record(modes=["drip-ignition"])})
        self.assertTrue(result["closed"])

    def test_a_retest_does_not_close_the_case(self):
        result = assess_failed_material({"record": record()})
        self.assertFalse(result["closed"])

    def test_a_larger_class_minimum_grows_the_extended_set(self):
        result = assess_failed_material({"record": record(), "min_specimens": 5})
        self.assertEqual(result["retest_specimens"], 7)

    def test_missing_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_material({"min_specimens": 3})

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_failed_material(record())


if __name__ == "__main__":
    unittest.main()
