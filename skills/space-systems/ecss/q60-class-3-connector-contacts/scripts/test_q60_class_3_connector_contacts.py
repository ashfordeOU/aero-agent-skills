#!/usr/bin/env python3
"""Contract test for Class 3 removable contact sourcing (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_3_connector_contacts_logic import (  # noqa: E402
    BUNDLE_DERATING_BANDS,
    CONTACT_ADMISSIBLE,
    CONTACT_APPLICATION_NONCONFORMING,
    CONTACT_EVIDENCE_OUTSTANDING,
    CONTACT_SIZES,
    CONTACT_SOURCE_NOT_APPROVED,
    DEFAULT_CLASS3_CONTACT_POLICY,
    PLATING_FINISHES,
    REQUIRED_TRACEABILITY_RECORDS,
    approved_source_route,
    assess_class3_contact_sourcing,
    bundle_derating_factor,
    crimp_range_fit,
    current_utilisation,
    derated_current_allowance_a,
    fold_manufacturer_name,
    intermix_evidence_required,
    plating_pair_assessment,
    traceability_gaps,
    validate_class3_contact_policy,
    validate_contact_case,
)

APPROVED = ("Meridian Contact Systems", "Northline Interconnect Ltd")

CLEAN_CASE = {
    "contact_manufacturer": "Meridian Contact Systems GmbH",
    "shell_manufacturer": "Meridian Contact Systems",
    "contact_size": "20",
    "conductor_mm2": 0.5,
    "energised_contacts": 8,
    "applied_current_a": 2.0,
    "contact_plating": "gold-over-nickel",
    "mating_plating": "palladium-nickel",
    "approved_sources": APPROVED,
    "traceability_records": list(REQUIRED_TRACEABILITY_RECORDS),
}


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


class FoldTests(unittest.TestCase):
    def test_legal_wrapper_is_folded_away(self):
        self.assertEqual(
            fold_manufacturer_name("Northline Interconnect Ltd"),
            "northline-interconnect",
        )

    def test_case_and_punctuation_fold_to_one_key(self):
        self.assertEqual(
            fold_manufacturer_name("NORTHLINE  INTERCONNECT, LTD."),
            fold_manufacturer_name("Northline Interconnect Ltd"),
        )

    def test_stacked_wrappers_are_folded_away(self):
        self.assertEqual(
            fold_manufacturer_name("Orbex Contacts Co Ltd"), "orbex-contacts"
        )

    def test_a_distinguishing_word_survives_the_fold(self):
        self.assertNotEqual(
            fold_manufacturer_name("Meridian Contact Systems"),
            fold_manufacturer_name("Meridian Contact Devices"),
        )

    def test_a_name_of_wrappers_only_is_rejected(self):
        with self.assertRaises(ValueError):
            fold_manufacturer_name("GmbH")

    def test_non_string_manufacturer_name_rejected(self):
        with self.assertRaises(ValueError):
            fold_manufacturer_name(17)


class RouteTests(unittest.TestCase):
    def test_a_listed_source_matches_on_the_list_route(self):
        route = approved_source_route("Meridian Contact Systems", APPROVED)
        self.assertTrue(route["matched"])
        self.assertEqual(route["route"], "approved-source-list")

    def test_a_recorded_alias_reaches_a_listed_source(self):
        route = approved_source_route(
            "Meridian Space Interconnect",
            APPROVED,
            aliases={"Meridian Space Interconnect": "Meridian Contact Systems"},
        )
        self.assertTrue(route["matched"])
        self.assertEqual(route["route"], "recorded-alias")

    def test_an_unrecorded_name_reaches_nothing(self):
        route = approved_source_route("Halcyon Contact Works", APPROVED)
        self.assertFalse(route["matched"])
        self.assertEqual(route["route"], "no-route")

    def test_a_complete_project_addition_is_approved(self):
        route = approved_source_route(
            "Halcyon Contact Works",
            APPROVED,
            project_additions={
                "Halcyon Contact Works": {
                    "justification": "second-source for the size 20 socket",
                    "qualification-reference": "PCB-2026-041",
                }
            },
        )
        self.assertTrue(route["matched"])
        self.assertEqual(route["route"], "project-approved-addition")

    def test_a_project_addition_without_justification_is_not_approved(self):
        route = approved_source_route(
            "Halcyon Contact Works",
            APPROVED,
            project_additions={
                "Halcyon Contact Works": {"qualification-reference": "PCB-2026-041"}
            },
        )
        self.assertFalse(route["matched"])
        self.assertEqual(route["addition_record_gaps"], ("justification",))

    def test_a_project_addition_without_either_record_names_both(self):
        route = approved_source_route(
            "Halcyon Contact Works",
            APPROVED,
            project_additions={"Halcyon Contact Works": {}},
        )
        self.assertEqual(
            route["addition_record_gaps"],
            ("justification", "qualification-reference"),
        )

    def test_a_blank_justification_does_not_count_as_written_down(self):
        route = approved_source_route(
            "Halcyon Contact Works",
            APPROVED,
            project_additions={
                "Halcyon Contact Works": {
                    "justification": "   ",
                    "qualification-reference": "PCB-2026-041",
                }
            },
        )
        self.assertFalse(route["matched"])

    def test_policy_can_close_the_project_addition_route(self):
        route = approved_source_route(
            "Halcyon Contact Works",
            APPROVED,
            project_additions={
                "Halcyon Contact Works": {
                    "justification": "second source",
                    "qualification-reference": "PCB-2026-041",
                }
            },
            policy={"accept_project_additions": False},
        )
        self.assertFalse(route["matched"])

    def test_an_alias_onto_an_unlisted_target_does_not_match(self):
        route = approved_source_route(
            "Halcyon Contact Works",
            APPROVED,
            aliases={"Halcyon Contact Works": "Halcyon Group"},
        )
        self.assertFalse(route["matched"])

    def test_an_empty_approved_list_is_rejected(self):
        with self.assertRaises(ValueError):
            approved_source_route("Meridian Contact Systems", ())

    def test_a_non_sequence_approved_list_is_rejected(self):
        with self.assertRaises(ValueError):
            approved_source_route("Meridian Contact Systems", "Meridian")


class PolicyTests(unittest.TestCase):
    def test_defaults_are_returned_when_no_policy_is_given(self):
        self.assertEqual(
            validate_class3_contact_policy(), DEFAULT_CLASS3_CONTACT_POLICY
        )

    def test_an_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_contact_policy({"max_temperature": 85.0})

    def test_a_derating_factor_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_contact_policy({"contact_current_derating_factor": 1.2})

    def test_a_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_contact_policy({"accept_recorded_aliases": "yes"})

    def test_class_3_derates_less_hard_than_a_half_share(self):
        self.assertGreater(
            DEFAULT_CLASS3_CONTACT_POLICY["contact_current_derating_factor"], 0.5
        )


class TraceabilityTests(unittest.TestCase):
    def test_a_full_set_leaves_no_gap(self):
        self.assertEqual(traceability_gaps(REQUIRED_TRACEABILITY_RECORDS), ())

    def test_a_missing_record_is_named(self):
        held = [r for r in REQUIRED_TRACEABILITY_RECORDS if r != "date-code"]
        self.assertEqual(traceability_gaps(held), ("date-code",))

    def test_records_are_matched_case_insensitively(self):
        held = [r.upper() for r in REQUIRED_TRACEABILITY_RECORDS]
        self.assertEqual(traceability_gaps(held), ())

    def test_a_non_string_record_is_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps(["lot-code", 4])


class PlatingTests(unittest.TestCase):
    def test_two_noble_finishes_are_acceptable(self):
        result = plating_pair_assessment("gold-over-nickel", "palladium-nickel")
        self.assertTrue(result["acceptable"])

    def test_a_dissimilar_family_pair_is_a_finding(self):
        result = plating_pair_assessment("gold-over-nickel", "tin-lead")
        self.assertFalse(result["acceptable"])
        self.assertTrue(result["dissimilar_family"])

    def test_a_pure_tin_finish_is_restricted(self):
        result = plating_pair_assessment("pure-tin", "tin-lead")
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["restricted_finishes"], ("pure-tin",))

    def test_policy_can_allow_a_dissimilar_family_pair(self):
        result = plating_pair_assessment(
            "gold-over-nickel", "tin-lead", {"require_matched_plating_family": False}
        )
        self.assertTrue(result["acceptable"])

    def test_a_restricted_finish_survives_a_relaxed_family_policy(self):
        result = plating_pair_assessment(
            "pure-tin", "pure-tin", {"require_matched_plating_family": False}
        )
        self.assertFalse(result["acceptable"])

    def test_an_unknown_finish_is_rejected(self):
        with self.assertRaises(ValueError):
            plating_pair_assessment("anodised", "tin-lead")

    def test_every_catalogued_finish_is_gradeable(self):
        for finish in PLATING_FINISHES:
            result = plating_pair_assessment(finish, finish)
            self.assertIsInstance(result["acceptable"], bool)


class CrimpTests(unittest.TestCase):
    def test_a_conductor_inside_the_range_fits(self):
        self.assertTrue(crimp_range_fit("20", 0.5)["fits"])

    def test_a_conductor_below_the_range_does_not_fit(self):
        result = crimp_range_fit("20", 0.25)
        self.assertFalse(result["fits"])
        self.assertTrue(result["below_range"])

    def test_a_conductor_above_the_range_does_not_fit(self):
        result = crimp_range_fit("20", 0.9)
        self.assertFalse(result["fits"])
        self.assertTrue(result["above_range"])

    def test_a_conductor_exactly_on_the_lower_bound_fits(self):
        bound = CONTACT_SIZES["16"]["min_mm2"]
        self.assertTrue(crimp_range_fit("16", bound)["fits"])

    def test_a_conductor_exactly_on_the_upper_bound_fits(self):
        bound = CONTACT_SIZES["16"]["max_mm2"]
        self.assertTrue(crimp_range_fit("16", bound)["fits"])

    def test_a_zero_conductor_is_rejected(self):
        with self.assertRaises(ValueError):
            crimp_range_fit("20", 0.0)

    def test_an_unknown_contact_size_is_rejected(self):
        with self.assertRaises(ValueError):
            crimp_range_fit("18", 0.5)


class DeratingTests(unittest.TestCase):
    def test_a_lone_pair_of_contacts_takes_the_full_factor(self):
        self.assertAlmostEqual(bundle_derating_factor(2), 1.0, places=9)

    def test_the_factor_never_rises_with_more_energised_contacts(self):
        previous = 1.0
        for count in (1, 2, 8, 24, 60, 200):
            factor = bundle_derating_factor(count)
            self.assertLessEqual(factor, previous + 1e-12)
            previous = factor

    def test_a_count_exactly_on_a_band_edge_takes_that_band(self):
        self.assertAlmostEqual(bundle_derating_factor(8), 0.85, places=9)

    def test_a_zero_count_is_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(0)

    def test_a_boolean_count_is_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(True)

    def test_the_allowance_matches_rating_times_both_factors(self):
        expected = (
            CONTACT_SIZES["16"]["rated_current_a"]
            * DEFAULT_CLASS3_CONTACT_POLICY["contact_current_derating_factor"]
            * BUNDLE_DERATING_BANDS[1][1]
        )
        self.assertAlmostEqual(
            derated_current_allowance_a("16", 8), expected, places=9
        )

    def test_a_dense_shell_allows_less_than_a_sparse_one(self):
        self.assertLess(
            derated_current_allowance_a("16", 40),
            derated_current_allowance_a("16", 4),
        )

    def test_utilisation_is_applied_over_allowance(self):
        self.assertAlmostEqual(current_utilisation(3.0, 6.0), 0.5, places=9)

    def test_a_zero_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            current_utilisation(1.0, 0.0)

    def test_a_negative_applied_current_is_rejected(self):
        with self.assertRaises(ValueError):
            current_utilisation(-1.0, 6.0)


class IntermixTests(unittest.TestCase):
    def test_one_maker_owes_no_pair_evidence(self):
        self.assertFalse(
            intermix_evidence_required(
                "Meridian Contact Systems GmbH", "Meridian Contact Systems"
            )
        )

    def test_two_makers_owe_pair_evidence(self):
        self.assertTrue(
            intermix_evidence_required(
                "Meridian Contact Systems", "Northline Interconnect Ltd"
            )
        )

    def test_policy_can_drop_the_pair_evidence_requirement(self):
        self.assertFalse(
            intermix_evidence_required(
                "Meridian Contact Systems",
                "Northline Interconnect Ltd",
                {"require_intermix_qualification": False},
            )
        )


class AssessmentTests(unittest.TestCase):
    def test_the_reference_case_is_admissible(self):
        result = assess_class3_contact_sourcing(CLEAN_CASE)
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])

    def test_an_unapproved_maker_outranks_every_other_finding(self):
        result = assess_class3_contact_sourcing(
            _case(
                contact_manufacturer="Halcyon Contact Works",
                conductor_mm2=0.9,
                traceability_records=[],
            )
        )
        self.assertEqual(result["disposition"], CONTACT_SOURCE_NOT_APPROVED)

    def test_an_incomplete_project_addition_is_reported_as_a_record_gap(self):
        result = assess_class3_contact_sourcing(
            _case(
                contact_manufacturer="Halcyon Contact Works",
                shell_manufacturer="Halcyon Contact Works",
                project_additions={"Halcyon Contact Works": {"justification": "x"}},
            )
        )
        self.assertEqual(result["disposition"], CONTACT_SOURCE_NOT_APPROVED)
        self.assertEqual(
            result["addition_record_gaps"], ("qualification-reference",)
        )

    def test_a_complete_project_addition_reaches_admissible(self):
        result = assess_class3_contact_sourcing(
            _case(
                contact_manufacturer="Halcyon Contact Works",
                shell_manufacturer="Halcyon Contact Works",
                project_additions={
                    "Halcyon Contact Works": {
                        "justification": "second source for size 20",
                        "qualification-reference": "PCB-2026-041",
                    }
                },
            )
        )
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)
        self.assertEqual(result["source_route"], "project-approved-addition")

    def test_an_overcurrent_application_outranks_a_paperwork_gap(self):
        result = assess_class3_contact_sourcing(
            _case(applied_current_a=40.0, traceability_records=["lot-code"])
        )
        self.assertEqual(result["disposition"], CONTACT_APPLICATION_NONCONFORMING)

    def test_a_restricted_finish_makes_the_application_nonconforming(self):
        result = assess_class3_contact_sourcing(_case(contact_plating="pure-tin"))
        self.assertEqual(result["disposition"], CONTACT_APPLICATION_NONCONFORMING)
        self.assertFalse(result["plating_acceptable"])

    def test_a_paperwork_gap_alone_leaves_evidence_outstanding(self):
        result = assess_class3_contact_sourcing(
            _case(traceability_records=["lot-code", "date-code"])
        )
        self.assertEqual(result["disposition"], CONTACT_EVIDENCE_OUTSTANDING)
        self.assertIn("certificate-of-conformance", result["traceability_gaps"])

    def test_an_intermixed_pair_without_evidence_is_outstanding(self):
        result = assess_class3_contact_sourcing(
            _case(shell_manufacturer="Northline Interconnect Ltd")
        )
        self.assertEqual(result["disposition"], CONTACT_EVIDENCE_OUTSTANDING)
        self.assertIn(
            "contact-shell-intermateability-qualification",
            result["evidence_outstanding"],
        )

    def test_recorded_pair_evidence_clears_the_intermix_finding(self):
        result = assess_class3_contact_sourcing(
            _case(
                shell_manufacturer="Northline Interconnect Ltd",
                intermateability_evidence="QR-2026-118",
            )
        )
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)

    def test_an_application_exactly_on_its_allowance_is_admissible(self):
        allowance = derated_current_allowance_a("20", 8)
        result = assess_class3_contact_sourcing(_case(applied_current_a=allowance))
        self.assertAlmostEqual(result["current_utilisation"], 1.0, places=9)
        self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)

    def test_a_case_missing_a_field_is_rejected(self):
        case = _case()
        del case["applied_current_a"]
        with self.assertRaises(ValueError):
            assess_class3_contact_sourcing(case)

    def test_an_unknown_size_is_rejected_by_the_case(self):
        with self.assertRaises(ValueError):
            assess_class3_contact_sourcing(_case(contact_size="18"))

    def test_case_validation_returns_the_reference_case(self):
        self.assertIs(validate_contact_case(CLEAN_CASE), CLEAN_CASE)

    def test_every_contact_size_routes_to_a_disposition(self):
        for size, spec in CONTACT_SIZES.items():
            result = assess_class3_contact_sourcing(
                _case(
                    contact_size=size,
                    conductor_mm2=(spec["min_mm2"] + spec["max_mm2"]) / 2.0,
                    applied_current_a=0.5,
                )
            )
            self.assertEqual(result["disposition"], CONTACT_ADMISSIBLE)


if __name__ == "__main__":
    unittest.main()
