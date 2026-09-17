#!/usr/bin/env python3
"""Contract test for class 2 removable contact sourcing (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_2_connector_contacts_logic import (  # noqa: E402
    CONTACT_ADMISSIBLE,
    CONTACT_APPLICATION_NONCONFORMING,
    CONTACT_SIZES,
    CONTACT_SOURCE_NOT_APPROVED,
    CONTACT_TRACEABILITY_OUTSTANDING,
    DEFAULT_CONTACT_SOURCING_POLICY,
    REQUIRED_TRACEABILITY_RECORDS,
    approved_source_match,
    assess_class2_contact_sourcing,
    bundle_derating_factor,
    conductor_fit,
    current_utilisation,
    derated_current_allowance_a,
    fold_manufacturer_name,
    intermix_evidence_required,
    traceability_gaps,
    validate_contact_case,
    validate_contact_sourcing_policy,
)

APPROVED = ("Meridian Contact Systems", "Northline Interconnect Ltd")

CLEAN_CASE = {
    "contact_manufacturer": "Meridian Contact Systems GmbH",
    "shell_manufacturer": "Meridian Contact Systems",
    "contact_size": "20",
    "conductor_mm2": 0.5,
    "energised_contacts": 8,
    "applied_current_a": 2.0,
    "approved_sources": APPROVED,
    "traceability_records": list(REQUIRED_TRACEABILITY_RECORDS),
}


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


class FoldTests(unittest.TestCase):
    def test_legal_suffix_is_folded_away(self):
        self.assertEqual(
            fold_manufacturer_name("Northline Interconnect Ltd"),
            "northline-interconnect",
        )

    def test_case_and_punctuation_are_folded_away(self):
        self.assertEqual(
            fold_manufacturer_name("NORTHLINE  INTERCONNECT, LTD."),
            fold_manufacturer_name("Northline Interconnect Ltd"),
        )

    def test_stacked_suffixes_are_folded_away(self):
        self.assertEqual(
            fold_manufacturer_name("Orbex Contacts Co Ltd"), "orbex-contacts"
        )

    def test_a_distinguishing_word_survives_the_fold(self):
        self.assertNotEqual(
            fold_manufacturer_name("Meridian Contact Systems"),
            fold_manufacturer_name("Meridian Contact Devices"),
        )

    def test_a_name_of_suffixes_only_is_rejected(self):
        with self.assertRaises(ValueError):
            fold_manufacturer_name("GmbH")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            fold_manufacturer_name(4103)


class ApprovedSourceTests(unittest.TestCase):
    def test_exact_name_reaches_the_approved_source(self):
        match = approved_source_match("Meridian Contact Systems", APPROVED)
        self.assertTrue(match["matched"])
        self.assertFalse(match["matched_through_alias"])

    def test_a_differing_legal_suffix_still_reaches_the_source(self):
        match = approved_source_match("Meridian Contact Systems GmbH", APPROVED)
        self.assertTrue(match["matched"])

    def test_an_unlisted_maker_does_not_match(self):
        match = approved_source_match("Backstreet Contacts Ltd", APPROVED)
        self.assertFalse(match["matched"])
        self.assertIsNone(match["approved_source"])

    def test_a_recorded_alias_reaches_the_source(self):
        match = approved_source_match(
            "Meridian Connector Division",
            APPROVED,
            {"Meridian Connector Division": "Meridian Contact Systems"},
        )
        self.assertTrue(match["matched"])
        self.assertTrue(match["matched_through_alias"])

    def test_an_alias_is_ignored_when_policy_refuses_aliases(self):
        match = approved_source_match(
            "Meridian Connector Division",
            APPROVED,
            {"Meridian Connector Division": "Meridian Contact Systems"},
            {"accept_recorded_aliases": False},
        )
        self.assertFalse(match["matched"])

    def test_an_alias_onto_an_unlisted_target_does_not_match(self):
        match = approved_source_match(
            "Meridian Connector Division",
            APPROVED,
            {"Meridian Connector Division": "Backstreet Contacts"},
        )
        self.assertFalse(match["matched"])

    def test_an_empty_approved_list_rejected(self):
        with self.assertRaises(ValueError):
            approved_source_match("Meridian Contact Systems", ())

    def test_a_non_sequence_approved_list_rejected(self):
        with self.assertRaises(ValueError):
            approved_source_match("Meridian Contact Systems", "Meridian")


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(
            validate_contact_sourcing_policy(None), DEFAULT_CONTACT_SOURCING_POLICY
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_sourcing_policy({"max_current": 1.0})

    def test_utilisation_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_sourcing_policy({"max_current_utilisation": 1.2})

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_sourcing_policy({"contact_current_derating_factor": 1.5})

    def test_non_boolean_intermix_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_sourcing_policy({"require_intermix_qualification": "yes"})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_sourcing_policy("default")


class ConductorFitTests(unittest.TestCase):
    def test_a_mid_range_conductor_fits(self):
        self.assertTrue(conductor_fit("20", 0.5)["fits"])

    def test_a_conductor_exactly_at_the_lower_bound_fits(self):
        fit = conductor_fit("20", CONTACT_SIZES["20"]["min_mm2"])
        self.assertTrue(fit["fits"])
        self.assertAlmostEqual(fit["min_mm2"], 0.38, places=9)

    def test_a_conductor_exactly_at_the_upper_bound_fits(self):
        fit = conductor_fit("20", CONTACT_SIZES["20"]["max_mm2"])
        self.assertTrue(fit["fits"])
        self.assertAlmostEqual(fit["max_mm2"], 0.62, places=9)

    def test_a_thin_conductor_is_below_the_range(self):
        fit = conductor_fit("20", 0.25)
        self.assertFalse(fit["fits"])
        self.assertTrue(fit["below_range"])

    def test_a_thick_conductor_is_above_the_range(self):
        fit = conductor_fit("20", 1.5)
        self.assertFalse(fit["fits"])
        self.assertTrue(fit["above_range"])

    def test_unknown_contact_size_rejected(self):
        with self.assertRaises(ValueError):
            conductor_fit("18", 0.5)

    def test_non_positive_conductor_area_rejected(self):
        with self.assertRaises(ValueError):
            conductor_fit("20", 0.0)


class BundleDeratingTests(unittest.TestCase):
    def test_a_lightly_loaded_shell_takes_no_bundle_derating(self):
        self.assertAlmostEqual(bundle_derating_factor(2), 1.00, places=9)

    def test_a_moderately_loaded_shell_derates(self):
        self.assertAlmostEqual(bundle_derating_factor(8), 0.85, places=9)

    def test_the_band_edge_moves_the_factor(self):
        self.assertAlmostEqual(bundle_derating_factor(9), 0.70, places=9)

    def test_a_dense_shell_takes_the_heaviest_derating(self):
        self.assertAlmostEqual(bundle_derating_factor(100), 0.50, places=9)

    def test_an_empty_shell_is_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(0)

    def test_a_boolean_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(True)

    def test_a_fractional_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(8.5)


class CurrentTests(unittest.TestCase):
    def test_allowance_folds_both_derating_terms(self):
        self.assertAlmostEqual(
            derated_current_allowance_a("20", 8), 3.1875, places=9
        )

    def test_policy_may_relax_the_class_derating(self):
        self.assertAlmostEqual(
            derated_current_allowance_a(
                "20", 8, {"contact_current_derating_factor": 1.0}
            ),
            6.375,
            places=9,
        )

    def test_utilisation_at_the_allowance_is_one(self):
        allowance = derated_current_allowance_a("20", 8)
        self.assertAlmostEqual(current_utilisation(allowance, allowance), 1.0, places=9)

    def test_zero_current_is_zero_utilisation(self):
        self.assertAlmostEqual(current_utilisation(0.0, 3.1875), 0.0, places=9)

    def test_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            current_utilisation(2.0, 0.0)

    def test_negative_applied_current_rejected(self):
        with self.assertRaises(ValueError):
            current_utilisation(-2.0, 3.1875)


class TraceabilityTests(unittest.TestCase):
    def test_a_complete_delivery_has_no_gap(self):
        self.assertEqual(traceability_gaps(REQUIRED_TRACEABILITY_RECORDS), ())

    def test_missing_records_are_named(self):
        gaps = traceability_gaps(["lot-code", "date-code"])
        self.assertIn("certificate-of-conformance", gaps)
        self.assertIn("detail-specification", gaps)

    def test_record_names_are_matched_case_insensitively(self):
        self.assertEqual(
            traceability_gaps([name.upper() for name in REQUIRED_TRACEABILITY_RECORDS]),
            (),
        )

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps("lot-code")

    def test_non_string_record_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps(["lot-code", 7])


class IntermixTests(unittest.TestCase):
    def test_same_maker_under_two_suffixes_needs_no_pair_evidence(self):
        self.assertFalse(
            intermix_evidence_required(
                "Meridian Contact Systems GmbH", "Meridian Contact Systems"
            )
        )

    def test_different_makers_need_pair_evidence(self):
        self.assertTrue(
            intermix_evidence_required(
                "Meridian Contact Systems", "Northline Interconnect Ltd"
            )
        )

    def test_policy_may_waive_pair_evidence(self):
        self.assertFalse(
            intermix_evidence_required(
                "Meridian Contact Systems",
                "Northline Interconnect Ltd",
                {"require_intermix_qualification": False},
            )
        )


class DispositionTests(unittest.TestCase):
    def test_a_clean_delivery_is_admissible(self):
        result = assess_class2_contact_sourcing(CLEAN_CASE)
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])

    def test_an_unapproved_maker_stops_the_contact(self):
        result = assess_class2_contact_sourcing(
            _case(contact_manufacturer="Backstreet Contacts Ltd")
        )
        self.assertEqual(result["disposition"], CONTACT_SOURCE_NOT_APPROVED)
        self.assertFalse(result["admissible"])

    def test_a_missing_record_leaves_traceability_outstanding(self):
        result = assess_class2_contact_sourcing(
            _case(traceability_records=["lot-code", "date-code"])
        )
        self.assertEqual(result["disposition"], CONTACT_TRACEABILITY_OUTSTANDING)
        self.assertIn("certificate-of-conformance", result["traceability_gaps"])

    def test_an_intermixed_pair_without_evidence_is_outstanding(self):
        result = assess_class2_contact_sourcing(
            _case(shell_manufacturer="Northline Interconnect Ltd")
        )
        self.assertEqual(result["disposition"], CONTACT_TRACEABILITY_OUTSTANDING)
        self.assertIn(
            "contact-shell-intermateability-qualification",
            result["evidence_outstanding"],
        )

    def test_an_intermixed_pair_with_evidence_is_admissible(self):
        result = assess_class2_contact_sourcing(
            _case(
                shell_manufacturer="Northline Interconnect Ltd",
                intermateability_evidence="pair-qualification-report",
            )
        )
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)

    def test_a_conductor_outside_the_crimp_range_is_nonconforming(self):
        result = assess_class2_contact_sourcing(_case(conductor_mm2=1.5))
        self.assertEqual(result["disposition"], CONTACT_APPLICATION_NONCONFORMING)
        self.assertFalse(result["conductor_fits"])

    def test_an_overloaded_contact_is_nonconforming(self):
        result = assess_class2_contact_sourcing(_case(applied_current_a=6.0))
        self.assertEqual(result["disposition"], CONTACT_APPLICATION_NONCONFORMING)
        self.assertFalse(result["current_ok"])

    def test_a_current_exactly_on_the_allowance_passes(self):
        allowance = derated_current_allowance_a("20", 8)
        result = assess_class2_contact_sourcing(_case(applied_current_a=allowance))
        self.assertAlmostEqual(result["current_utilisation"], 1.0, places=9)
        self.assertTrue(result["current_ok"])
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)

    def test_an_unapproved_source_outranks_an_application_finding(self):
        result = assess_class2_contact_sourcing(
            _case(contact_manufacturer="Backstreet Contacts Ltd", conductor_mm2=1.5)
        )
        self.assertEqual(result["disposition"], CONTACT_SOURCE_NOT_APPROVED)

    def test_an_application_finding_outranks_a_traceability_gap(self):
        result = assess_class2_contact_sourcing(
            _case(conductor_mm2=1.5, traceability_records=["lot-code"])
        )
        self.assertEqual(result["disposition"], CONTACT_APPLICATION_NONCONFORMING)

    def test_a_denser_shell_lowers_the_allowance(self):
        sparse = assess_class2_contact_sourcing(_case(energised_contacts=2))
        dense = assess_class2_contact_sourcing(_case(energised_contacts=100))
        self.assertGreater(
            sparse["derated_allowance_a"], dense["derated_allowance_a"]
        )

    def test_case_missing_a_field_rejected(self):
        case = _case()
        del case["applied_current_a"]
        with self.assertRaises(ValueError):
            assess_class2_contact_sourcing(case)

    def test_unknown_contact_size_rejected_by_the_case(self):
        with self.assertRaises(ValueError):
            assess_class2_contact_sourcing(_case(contact_size="18"))

    def test_case_validation_accepts_the_reference_case(self):
        self.assertIs(validate_contact_case(CLEAN_CASE), CLEAN_CASE)

    def test_every_contact_size_is_routable(self):
        for size, spec in CONTACT_SIZES.items():
            result = assess_class2_contact_sourcing(
                _case(
                    contact_size=size,
                    conductor_mm2=(spec["min_mm2"] + spec["max_mm2"]) / 2.0,
                    applied_current_a=0.5,
                )
            )
            self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)


if __name__ == "__main__":
    unittest.main()
