#!/usr/bin/env python3
"""Contract test for the ECSS-E-ST-20-06C clause 11.1.2 coverage leaf."""

import unittest

from e2006_electric_propulsion_requirement_coverage_logic import (
    CHARGING_STANDARD,
    JOINT,
    MANDATORY_TOPIC_WEIGHT,
    PROPULSION_STANDARD,
    assess_requirement_coverage,
    delegation_chain,
    meets_threshold,
    missing_mandatory_topics,
    normalize_token,
    ownership_findings,
    topic_owner,
    validate_requirement,
    validate_verification_method,
    weighted_coverage,
)


def req(rid, topic, owner, method="analysis", **over):
    record = {"id": rid, "topic": topic, "owner": owner,
              "verification_method": method}
    record.update(over)
    return record


def full_set():
    owners = [
        ("EP-010", "beam-neutralization-capacity"),
        ("EP-020", "plume-charge-exchange-backflow"),
        ("EP-030", "plume-sputter-erosion"),
        ("EP-040", "neutral-gas-discharge-triggering"),
        ("EP-050", "spacecraft-floating-potential"),
        ("EP-060", "differential-charging-mitigation"),
    ]
    return [req(rid, topic, CHARGING_STANDARD) for rid, topic in owners]


class TokenTests(unittest.TestCase):
    def test_token_is_lowercased_and_stripped(self):
        self.assertEqual(normalize_token("  Beam-Capacity ", "x"),
                         "beam-capacity")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "topic")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(12, "topic")


class TopicOwnerTests(unittest.TestCase):
    def test_charging_topic_owned_by_charging_standard(self):
        self.assertEqual(topic_owner("beam-neutralization-capacity"),
                         CHARGING_STANDARD)

    def test_performance_topic_owned_by_propulsion_standard(self):
        self.assertEqual(topic_owner("thrust-performance"),
                         PROPULSION_STANDARD)

    def test_interface_topic_owned_by_propulsion_standard(self):
        self.assertEqual(topic_owner("thruster-mechanical-interface"),
                         PROPULSION_STANDARD)

    def test_verification_topic_owned_by_propulsion_standard(self):
        self.assertEqual(topic_owner("propulsion-functional-verification"),
                         PROPULSION_STANDARD)

    def test_power_interface_is_jointly_governed(self):
        self.assertEqual(topic_owner("electrical-power-interface"), JOINT)

    def test_owner_lookup_is_case_insensitive(self):
        self.assertEqual(topic_owner(" Thrust-Performance "),
                         PROPULSION_STANDARD)

    def test_uncategorized_topic_rejected(self):
        with self.assertRaises(ValueError):
            topic_owner("crew-comfort")

    def test_every_mandatory_topic_is_owned_by_the_charging_standard(self):
        for topic in MANDATORY_TOPIC_WEIGHT:
            self.assertEqual(topic_owner(topic), CHARGING_STANDARD)


class DelegationTests(unittest.TestCase):
    def test_charging_topic_delegates_supporting_data(self):
        self.assertEqual(delegation_chain("plume-sputter-erosion"),
                         (CHARGING_STANDARD, PROPULSION_STANDARD))

    def test_propulsion_topic_reverses_the_chain(self):
        self.assertEqual(delegation_chain("thrust-performance"),
                         (PROPULSION_STANDARD, CHARGING_STANDARD))

    def test_joint_topic_names_both_standards(self):
        chain = delegation_chain("plume-impingement-envelope")
        self.assertIn(CHARGING_STANDARD, chain)
        self.assertIn(PROPULSION_STANDARD, chain)

    def test_delegation_rejects_unknown_topic(self):
        with self.assertRaises(ValueError):
            delegation_chain("galley-layout")


class VerificationMethodTests(unittest.TestCase):
    def test_analysis_is_accepted(self):
        self.assertEqual(validate_verification_method("Analysis"), "analysis")

    def test_review_of_design_is_accepted(self):
        self.assertEqual(validate_verification_method("review-of-design"),
                         "review-of-design")

    def test_verification_by_testing_is_accepted(self):
        self.assertEqual(validate_verification_method("verification-by-testing"),
                         "verification-by-testing")

    def test_unrecognised_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_method("vibes")

    def test_blank_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_method("")


class ValidateRequirementTests(unittest.TestCase):
    def test_record_is_normalised(self):
        out = validate_requirement(req(" EP-010 ", "Beam-Neutralization-Capacity",
                                       CHARGING_STANDARD, "Analysis"))
        self.assertEqual(out["id"], "ep-010")
        self.assertEqual(out["topic"], "beam-neutralization-capacity")
        self.assertEqual(out["registry_owner"], CHARGING_STANDARD)

    def test_cross_reference_defaults_to_none(self):
        out = validate_requirement(req("EP-010", "beam-neutralization-capacity",
                                       CHARGING_STANDARD))
        self.assertIsNone(out["cross_reference"])

    def test_cross_reference_is_normalised(self):
        out = validate_requirement(req("EP-070", "electrical-power-interface",
                                       JOINT, "analysis",
                                       cross_reference=PROPULSION_STANDARD))
        self.assertEqual(out["cross_reference"], PROPULSION_STANDARD)

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(["EP-010"])

    def test_missing_key_rejected(self):
        record = req("EP-010", "beam-neutralization-capacity", CHARGING_STANDARD)
        del record["verification_method"]
        with self.assertRaises(ValueError):
            validate_requirement(record)

    def test_unrecognised_declared_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(req("EP-010", "beam-neutralization-capacity",
                                     "ecss-q-st-70"))

    def test_blank_requirement_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(req("  ", "beam-neutralization-capacity",
                                     CHARGING_STANDARD))


class OwnershipFindingTests(unittest.TestCase):
    def test_correct_allocation_raises_no_finding(self):
        _, found = ownership_findings(req("EP-010",
                                          "beam-neutralization-capacity",
                                          CHARGING_STANDARD))
        self.assertEqual(found, [])

    def test_misallocated_owner_is_a_finding(self):
        _, found = ownership_findings(req("EP-010",
                                          "beam-neutralization-capacity",
                                          PROPULSION_STANDARD))
        self.assertEqual(len(found), 1)
        self.assertIn("misallocated-ownership", found[0])

    def test_joint_topic_without_cross_reference_is_a_finding(self):
        _, found = ownership_findings(req("EP-070",
                                          "electrical-power-interface", JOINT))
        self.assertTrue(any("missing-cross-reference" in f for f in found))

    def test_joint_topic_with_cross_reference_is_clean(self):
        _, found = ownership_findings(req("EP-070",
                                          "electrical-power-interface", JOINT,
                                          cross_reference=CHARGING_STANDARD))
        self.assertEqual(found, [])

    def test_cross_reference_to_an_unrelated_standard_is_a_finding(self):
        _, found = ownership_findings(req("EP-070",
                                          "electrical-power-interface", JOINT,
                                          cross_reference="ecss-q-st-70"))
        self.assertTrue(any("not-a-governing-standard" in f for f in found))

    def test_similarity_on_a_charging_topic_is_a_finding(self):
        _, found = ownership_findings(req("EP-010",
                                          "beam-neutralization-capacity",
                                          CHARGING_STANDARD, "similarity"))
        self.assertTrue(any("similarity-not-acceptable" in f for f in found))

    def test_similarity_on_a_propulsion_topic_is_allowed(self):
        _, found = ownership_findings(req("EP-100", "thrust-performance",
                                          PROPULSION_STANDARD, "similarity"))
        self.assertEqual(found, [])

    def test_findings_reject_an_unknown_topic(self):
        with self.assertRaises(ValueError):
            ownership_findings(req("EP-999", "hull-paint", CHARGING_STANDARD))


class CoverageMathTests(unittest.TestCase):
    def test_empty_coverage_is_zero(self):
        self.assertAlmostEqual(weighted_coverage([]), 0.0, places=12)

    def test_full_coverage_is_unity(self):
        self.assertAlmostEqual(weighted_coverage(list(MANDATORY_TOPIC_WEIGHT)),
                               1.0, places=12)

    def test_partial_coverage_is_weight_proportional(self):
        ratio = weighted_coverage(["beam-neutralization-capacity",
                                   "plume-sputter-erosion"])
        self.assertAlmostEqual(ratio, 0.5, places=9)

    def test_repeated_topic_counts_once(self):
        ratio = weighted_coverage(["beam-neutralization-capacity",
                                   "beam-neutralization-capacity"])
        self.assertAlmostEqual(ratio, 0.3, places=9)

    def test_non_mandatory_topic_adds_no_coverage(self):
        ratio = weighted_coverage(["thrust-performance"])
        self.assertAlmostEqual(ratio, 0.0, places=12)

    def test_coverage_is_reproducible(self):
        topics = list(MANDATORY_TOPIC_WEIGHT)[:4]
        self.assertEqual(weighted_coverage(topics), weighted_coverage(topics))

    def test_non_sequence_topics_rejected(self):
        with self.assertRaises(ValueError):
            weighted_coverage("beam-neutralization-capacity")

    def test_missing_topics_lists_the_gap(self):
        missing = missing_mandatory_topics(["beam-neutralization-capacity"])
        self.assertIn("plume-sputter-erosion", missing)
        self.assertNotIn("beam-neutralization-capacity", missing)

    def test_missing_topics_is_empty_on_full_coverage(self):
        self.assertEqual(missing_mandatory_topics(list(MANDATORY_TOPIC_WEIGHT)),
                         ())

    def test_missing_topics_is_sorted(self):
        missing = missing_mandatory_topics([])
        self.assertEqual(list(missing), sorted(missing))


class ThresholdTests(unittest.TestCase):
    def test_ratio_above_threshold_passes(self):
        self.assertTrue(meets_threshold(0.95, 0.9))

    def test_ratio_below_threshold_fails(self):
        self.assertFalse(meets_threshold(0.85, 0.9))

    def test_exact_threshold_passes(self):
        self.assertTrue(meets_threshold(0.9, 0.9))

    def test_float_representation_shortfall_is_absorbed(self):
        # 0.7 + 0.1 + 0.1 evaluates a few units in the last place below 0.9;
        # the set is compliant, so the comparison absorbs the error.
        ratio = 0.7 + 0.1 + 0.1
        self.assertLess(ratio, 0.9)
        self.assertTrue(meets_threshold(ratio, 0.9))

    def test_real_shortfall_is_not_absorbed(self):
        self.assertFalse(meets_threshold(0.899999, 0.9))

    def test_threshold_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            meets_threshold(1.0, 1.2)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            meets_threshold(1.0, -0.1)

    def test_negative_ratio_rejected(self):
        with self.assertRaises(ValueError):
            meets_threshold(-0.01, 0.5)


class AssessmentTests(unittest.TestCase):
    def test_complete_set_is_compliant(self):
        out = assess_requirement_coverage(full_set())
        self.assertTrue(out["coverage_compliant"])
        self.assertAlmostEqual(out["coverage_ratio"], 1.0, places=12)
        self.assertEqual(out["missing_topics"], ())
        self.assertEqual(out["findings"], [])

    def test_incomplete_set_reports_the_gap(self):
        out = assess_requirement_coverage(full_set()[:3])
        self.assertFalse(out["coverage_compliant"])
        self.assertAlmostEqual(out["coverage_ratio"], 0.7, places=9)
        self.assertIn("spacecraft-floating-potential", out["missing_topics"])

    def test_incomplete_set_passes_a_lower_threshold(self):
        out = assess_requirement_coverage(full_set()[:3], threshold=0.7)
        self.assertTrue(out["coverage_compliant"])

    def test_method_tally_counts_each_method(self):
        entries = full_set()
        entries[0]["verification_method"] = "verification-by-testing"
        out = assess_requirement_coverage(entries)
        self.assertEqual(out["verification_methods"]["verification-by-testing"], 1)
        self.assertEqual(out["verification_methods"]["analysis"], 5)

    def test_misallocated_entry_blocks_compliance(self):
        entries = full_set()
        entries[1]["owner"] = PROPULSION_STANDARD
        out = assess_requirement_coverage(entries)
        self.assertFalse(out["coverage_compliant"])
        self.assertTrue(any("misallocated-ownership" in f
                            for f in out["findings"]))

    def test_conflicting_ownership_claim_is_a_finding(self):
        entries = full_set()
        entries.append(req("EP-061", "differential-charging-mitigation",
                           PROPULSION_STANDARD))
        out = assess_requirement_coverage(entries)
        self.assertTrue(any("conflicting-ownership-claim" in f
                            for f in out["findings"]))

    def test_propulsion_entries_do_not_raise_coverage(self):
        entries = full_set()[:1] + [req("EP-100", "thrust-performance",
                                        PROPULSION_STANDARD)]
        out = assess_requirement_coverage(entries)
        self.assertAlmostEqual(out["coverage_ratio"], 0.3, places=9)

    def test_below_threshold_adds_an_explicit_finding(self):
        out = assess_requirement_coverage(full_set()[:2])
        self.assertTrue(any("coverage-below-threshold" in f
                            for f in out["findings"]))

    def test_duplicate_requirement_id_rejected(self):
        entries = full_set()
        entries.append(req("EP-010", "plume-sputter-erosion",
                           CHARGING_STANDARD))
        with self.assertRaises(ValueError):
            assess_requirement_coverage(entries)

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_requirement_coverage([])

    def test_non_list_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_requirement_coverage(req("EP-010",
                                            "beam-neutralization-capacity",
                                            CHARGING_STANDARD))

    def test_assessment_is_deterministic(self):
        first = assess_requirement_coverage(full_set())
        second = assess_requirement_coverage(full_set())
        self.assertEqual(first["coverage_ratio"], second["coverage_ratio"])
        self.assertEqual(first["missing_topics"], second["missing_topics"])


if __name__ == "__main__":
    unittest.main()
