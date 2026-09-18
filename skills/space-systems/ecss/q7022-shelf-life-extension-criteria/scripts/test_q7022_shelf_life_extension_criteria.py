"""Contract test for the shelf-life-extension-criteria leaf (stdlib unittest)."""

import unittest

from q7022_shelf_life_extension_criteria_logic import (
    MAX_EXTENSION_COUNT,
    assess_shelf_life_extension,
    blocking_criteria,
    evidence_basis,
    granted_extension_days,
    increment_cap_days,
    total_life_cap_days,
    validate_request,
)


def request(rid="R-1", family="sealant", **kw):
    record = {
        "id": rid,
        "family": family,
        "original_shelf_life_days": 730,
        "requested_days": 180,
        "storage_record_complete": True,
        "exposure_within_allowance": True,
        "evidence_sources": ["re-test-report"],
        "re_test_passed": True,
    }
    record.update(kw)
    return record


def names(criteria):
    return {item["name"]: item["met"] for item in criteria}


class TestValidateRequest(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_request(request())
        self.assertEqual(norm["prior_extension_count"], 0)
        self.assertEqual(norm["previously_granted_days"], 0)
        self.assertEqual(norm["manufacturer_statement_covers_days"], 0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["R-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(""))

    def test_zero_original_shelf_life_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(original_shelf_life_days=0))

    def test_zero_requested_days_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(requested_days=0))

    def test_boolean_requested_days_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(requested_days=True))

    def test_unknown_evidence_source_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(evidence_sources=["a-phone-call"]))

    def test_non_sequence_evidence_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(evidence_sources="re-test-report"))

    def test_non_boolean_storage_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(storage_record_complete="yes"))

    def test_negative_prior_count_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(prior_extension_count=-1))


class TestEvidenceBasis(unittest.TestCase):
    def test_a_passed_re_test_is_a_basis(self):
        self.assertEqual(evidence_basis(request()), "passed-re-test")

    def test_a_failed_re_test_is_not_a_basis(self):
        self.assertIsNone(evidence_basis(request(re_test_passed=False)))

    def test_a_statement_covering_the_period_is_a_basis(self):
        self.assertEqual(
            evidence_basis(request(evidence_sources=["manufacturer-statement"],
                                   manufacturer_statement_covers_days=180,
                                   re_test_passed=False)),
            "manufacturer-statement")

    def test_a_statement_too_short_for_the_request_is_not_a_basis(self):
        self.assertIsNone(
            evidence_basis(request(evidence_sources=["manufacturer-statement"],
                                   manufacturer_statement_covers_days=90,
                                   re_test_passed=False)))

    def test_qualification_data_alone_is_not_a_basis(self):
        self.assertIsNone(
            evidence_basis(request(evidence_sources=["qualification-data"],
                                   re_test_passed=False)))


class TestBlockingCriteria(unittest.TestCase):
    def test_a_complete_request_meets_every_criterion(self):
        self.assertTrue(all(names(blocking_criteria(request())).values()))

    def test_a_non_extendable_family_is_blocked(self):
        met = names(blocking_criteria(request(family="pyrotechnic-composition")))
        self.assertFalse(met["family-extendable"])

    def test_an_incomplete_storage_record_is_blocked(self):
        met = names(blocking_criteria(request(storage_record_complete=False)))
        self.assertFalse(met["storage-record-complete"])

    def test_exposure_over_allowance_is_blocked(self):
        met = names(blocking_criteria(request(exposure_within_allowance=False)))
        self.assertFalse(met["exposure-within-allowance"])

    def test_the_extension_count_ceiling_is_blocking(self):
        met = names(blocking_criteria(request(prior_extension_count=MAX_EXTENSION_COUNT)))
        self.assertFalse(met["extension-count"])

    def test_one_extension_already_used_still_passes(self):
        met = names(blocking_criteria(request(prior_extension_count=1)))
        self.assertTrue(met["extension-count"])


class TestCaps(unittest.TestCase):
    def test_increment_cap_is_half_the_original_life(self):
        self.assertEqual(increment_cap_days(request()), 365)

    def test_increment_cap_floors_an_odd_day_count(self):
        self.assertEqual(increment_cap_days(request(original_shelf_life_days=365)), 182)

    def test_total_life_cap_starts_at_the_full_original_life(self):
        self.assertEqual(total_life_cap_days(request()), 730)

    def test_previously_granted_days_eat_the_total_headroom(self):
        self.assertEqual(total_life_cap_days(request(previously_granted_days=600)), 130)

    def test_total_headroom_never_goes_negative(self):
        self.assertEqual(total_life_cap_days(request(previously_granted_days=900)), 0)

    def test_a_request_inside_both_caps_is_granted_whole(self):
        grant = granted_extension_days(request())
        self.assertEqual(grant["granted_days"], 180)
        self.assertIsNone(grant["limited_by"])

    def test_the_step_cap_cuts_an_over_long_request(self):
        grant = granted_extension_days(request(requested_days=500))
        self.assertEqual(grant["granted_days"], 365)
        self.assertEqual(grant["limited_by"], "per-step-increment-cap")

    def test_the_total_life_cap_outranks_the_step_cap(self):
        grant = granted_extension_days(request(requested_days=300,
                                               previously_granted_days=650))
        self.assertEqual(grant["granted_days"], 80)
        self.assertEqual(grant["limited_by"], "total-life-cap")

    def test_a_request_exactly_at_the_step_cap_is_not_cut(self):
        grant = granted_extension_days(request(requested_days=365))
        self.assertEqual(grant["granted_days"], 365)
        self.assertIsNone(grant["limited_by"])


class TestAssess(unittest.TestCase):
    def test_a_supported_request_is_granted(self):
        report = assess_shelf_life_extension(request())
        self.assertEqual(report["disposition"], "extension-granted")
        self.assertEqual(report["granted_days"], 180)
        self.assertTrue(report["eligible"])
        self.assertEqual(report["findings"], [])

    def test_a_capped_request_is_granted_reduced_and_says_why(self):
        report = assess_shelf_life_extension(request(requested_days=500))
        self.assertEqual(report["disposition"], "extension-granted-reduced")
        self.assertEqual(report["granted_days"], 365)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_missing_evidence_basis_refuses_the_request(self):
        report = assess_shelf_life_extension(request(re_test_passed=False))
        self.assertEqual(report["disposition"], "extension-refused")
        self.assertEqual(report["granted_days"], 0)
        self.assertIn("evidence-basis", report["unmet_criteria"])

    def test_a_non_extendable_family_is_refused_whatever_the_evidence(self):
        report = assess_shelf_life_extension(request(family="catalysed-premix"))
        self.assertFalse(report["eligible"])
        self.assertIn("family-extendable", report["unmet_criteria"])

    def test_exhausted_total_life_is_refused_even_with_criteria_met(self):
        report = assess_shelf_life_extension(request(previously_granted_days=730))
        self.assertEqual(report["disposition"], "extension-refused")
        self.assertEqual(report["unmet_criteria"], [])
        self.assertEqual(report["granted_days"], 0)

    def test_several_unmet_criteria_are_all_named(self):
        report = assess_shelf_life_extension(
            request(storage_record_complete=False, exposure_within_allowance=False,
                    re_test_passed=False))
        self.assertEqual(len(report["unmet_criteria"]), 3)

    def test_the_evidence_basis_is_reported_back(self):
        report = assess_shelf_life_extension(
            request(evidence_sources=["manufacturer-statement", "qualification-data"],
                    manufacturer_statement_covers_days=200, re_test_passed=False))
        self.assertEqual(report["evidence_basis"], "manufacturer-statement")

    def test_non_mapping_request_raises(self):
        with self.assertRaises(ValueError):
            assess_shelf_life_extension("R-1")


if __name__ == "__main__":
    unittest.main()
