#!/usr/bin/env python3
"""Contract test for the clause 8.3 product-type pre-tailoring matrix leaf.

Offline, deterministic, stdlib unittest. Run: python3 this_file.py
"""

import math
import unittest

from e20_product_type_pre_tailoring_matrix_logic import (
    DISPOSITIONS,
    FEATURE_TYPES,
    PRODUCT_TYPES,
    PROVISION_GROUPS,
    apply_tailoring_request,
    assess_pre_tailoring,
    audit_matrix_completeness,
    build_pre_tailoring_matrix,
    clause_disposition,
    normalize_disposition,
    normalize_feature,
    normalize_product_type,
    summarize_matrix,
)

BARE_SUBSYSTEM = [{"name": "avionics-chain", "product_type": "subsystem"}]

POWER_SUBSYSTEM = [{
    "name": "energy-chain",
    "product_type": "subsystem",
    "features": ["solar-array-generator", "electrochemical-energy-store",
                 "harness-and-cable-network"],
}]


class NormalizeProductTypeTests(unittest.TestCase):
    def test_canonical_tokens_pass_through(self):
        for token in PRODUCT_TYPES:
            self.assertEqual(normalize_product_type(token), token)

    def test_synonyms_resolve(self):
        self.assertEqual(normalize_product_type("unit"), "equipment-unit")
        self.assertEqual(normalize_product_type("Equipment Unit"), "equipment-unit")
        self.assertEqual(normalize_product_type("stage"), "launcher-stage")
        self.assertEqual(normalize_product_type("instrument"), "payload")
        self.assertEqual(normalize_product_type("sub-system"), "subsystem")

    def test_unknown_product_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_type("ground-station")

    def test_non_string_product_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_type(7)

    def test_empty_product_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_type("   ")


class NormalizeFeatureTests(unittest.TestCase):
    def test_canonical_features_pass_through(self):
        for token in FEATURE_TYPES:
            self.assertEqual(normalize_feature(token), token)

    def test_feature_synonyms_resolve(self):
        self.assertEqual(normalize_feature("battery"),
                         "electrochemical-energy-store")
        self.assertEqual(normalize_feature("Solar Array"),
                         "solar-array-generator")
        self.assertEqual(normalize_feature("eed"), "electro-explosive-device")
        self.assertEqual(normalize_feature("harness"),
                         "harness-and-cable-network")

    def test_unknown_feature_rejected(self):
        with self.assertRaises(ValueError):
            normalize_feature("hydraulic-actuator")


class NormalizeDispositionTests(unittest.TestCase):
    def test_aliases_resolve(self):
        self.assertEqual(normalize_disposition("N/A"), "not-applicable")
        self.assertEqual(normalize_disposition("applies"), "applicable")
        self.assertEqual(normalize_disposition("tailorable-with-justification"),
                         "tailorable")

    def test_every_canonical_disposition_round_trips(self):
        for token in DISPOSITIONS:
            self.assertEqual(normalize_disposition(token), token)

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_disposition("waived")


class ClauseDispositionTests(unittest.TestCase):
    def test_compatibility_group_binds_every_product_type(self):
        for ptype in PRODUCT_TYPES:
            cell = clause_disposition("g-electromagnetic-compatibility", ptype)
            self.assertEqual(cell["disposition"], "applicable")
            self.assertEqual(cell["driver"], "product-type-default")

    def test_generation_group_has_no_object_on_a_bare_unit(self):
        cell = clause_disposition("g-power-generation", "equipment-unit")
        self.assertEqual(cell["disposition"], "not-applicable")

    def test_declared_feature_raises_the_disposition(self):
        cell = clause_disposition("g-power-generation", "equipment-unit",
                                  ["solar-array-generator"])
        self.assertEqual(cell["disposition"], "applicable")
        self.assertEqual(cell["driver"], "solar-array-generator")

    def test_feature_never_lowers_a_binding_default(self):
        cell = clause_disposition("g-grounding-and-bonding", "subsystem",
                                  ["harness-and-cable-network"])
        self.assertEqual(cell["disposition"], "applicable")

    def test_antenna_feature_reaches_the_radio_frequency_group(self):
        cell = clause_disposition("g-radio-frequency-chain", "launcher-stage",
                                  ["antenna-subassembly"])
        self.assertEqual(cell["disposition"], "applicable")
        self.assertEqual(cell["driver"], "antenna-subassembly")

    def test_transmitter_also_reaches_the_discharge_group(self):
        cell = clause_disposition("g-high-voltage-and-discharge", "payload",
                                  ["radio-frequency-transmitter"])
        self.assertEqual(cell["disposition"], "applicable")

    def test_unknown_group_rejected(self):
        with self.assertRaises(ValueError):
            clause_disposition("g-thermal-control", "subsystem")

    def test_bare_string_feature_sequence_rejected(self):
        with self.assertRaises(ValueError):
            clause_disposition("g-power-generation", "subsystem",
                               "solar-array-generator")


class BuildMatrixTests(unittest.TestCase):
    def test_row_count_is_items_times_groups(self):
        rows = build_pre_tailoring_matrix(BARE_SUBSYSTEM)
        self.assertEqual(len(rows), len(PROVISION_GROUPS))

    def test_rows_are_ordered_by_item_then_group(self):
        rows = build_pre_tailoring_matrix([
            {"name": "b-item", "product_type": "payload"},
            {"name": "a-item", "product_type": "unit"},
        ])
        keys = [(r["item"], r["group"]) for r in rows]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(rows), 2 * len(PROVISION_GROUPS))

    def test_duplicate_item_name_rejected(self):
        with self.assertRaises(ValueError):
            build_pre_tailoring_matrix([
                {"name": "dup", "product_type": "subsystem"},
                {"name": "dup", "product_type": "payload"},
            ])

    def test_missing_item_name_rejected(self):
        with self.assertRaises(ValueError):
            build_pre_tailoring_matrix([{"product_type": "subsystem"}])

    def test_empty_product_set_rejected(self):
        with self.assertRaises(ValueError):
            build_pre_tailoring_matrix([])

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            build_pre_tailoring_matrix(["subsystem"])


class TailoringRequestTests(unittest.TestCase):
    def setUp(self):
        self.cell = clause_disposition("g-power-generation", "subsystem")

    def test_raise_is_admitted_without_paperwork(self):
        out = apply_tailoring_request(self.cell, "applicable")
        self.assertEqual(out["disposition"], "applicable")
        self.assertEqual(out["tailoring"], "raised")
        self.assertIsNone(out["rejected_reason"])

    def test_same_disposition_is_unchanged(self):
        out = apply_tailoring_request(self.cell, "tailorable")
        self.assertEqual(out["tailoring"], "unchanged")

    def test_downgrade_without_justification_is_rejected(self):
        out = apply_tailoring_request(self.cell, "not-applicable",
                                      approval_authority="chief-engineer")
        self.assertEqual(out["tailoring"], "rejected")
        self.assertEqual(out["disposition"], "tailorable")
        self.assertIn("justification", out["rejected_reason"])

    def test_downgrade_without_authority_is_rejected(self):
        out = apply_tailoring_request(self.cell, "not-applicable",
                                      justification="no generator on board")
        self.assertEqual(out["tailoring"], "rejected")
        self.assertIn("approval-authority", out["rejected_reason"])

    def test_downgrade_with_full_record_is_admitted(self):
        out = apply_tailoring_request(self.cell, "not-applicable",
                                      justification="no generator on board",
                                      approval_authority="chief-engineer")
        self.assertEqual(out["disposition"], "not-applicable")
        self.assertEqual(out["tailoring"], "lowered")
        self.assertEqual(out["approval_authority"], "chief-engineer")

    def test_blank_justification_does_not_count(self):
        out = apply_tailoring_request(self.cell, "not-applicable",
                                      justification="   ",
                                      approval_authority="chief-engineer")
        self.assertEqual(out["tailoring"], "rejected")

    def test_malformed_cell_rejected(self):
        with self.assertRaises(ValueError):
            apply_tailoring_request({"group": "g-power-generation"}, "applicable")

    def test_unknown_requested_disposition_rejected(self):
        with self.assertRaises(ValueError):
            apply_tailoring_request(self.cell, "deleted")


class CompletenessTests(unittest.TestCase):
    def test_full_matrix_has_no_gap(self):
        rows = build_pre_tailoring_matrix(POWER_SUBSYSTEM)
        self.assertEqual(audit_matrix_completeness(rows), [])

    def test_dropped_cell_is_reported(self):
        rows = build_pre_tailoring_matrix(POWER_SUBSYSTEM)
        thinned = [r for r in rows if r["group"] != "g-magnetic-cleanliness"]
        gaps = audit_matrix_completeness(thinned)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["group"], "g-magnetic-cleanliness")
        self.assertEqual(gaps[0]["finding"], "cell-undeclared")

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            audit_matrix_completeness([])

    def test_unknown_group_in_audit_set_rejected(self):
        rows = build_pre_tailoring_matrix(BARE_SUBSYSTEM)
        with self.assertRaises(ValueError):
            audit_matrix_completeness(rows, ["g-propulsion"])


class SummaryTests(unittest.TestCase):
    def test_counts_sum_to_cell_count(self):
        rows = build_pre_tailoring_matrix(BARE_SUBSYSTEM)
        summary = summarize_matrix(rows)
        self.assertEqual(sum(summary["counts"].values()), summary["cells"])

    def test_bare_subsystem_binding_share(self):
        summary = summarize_matrix(build_pre_tailoring_matrix(BARE_SUBSYSTEM))
        self.assertEqual(summary["cells"], 10)
        self.assertEqual(summary["counts"]["not-applicable"], 2)
        self.assertAlmostEqual(summary["binding_share"], 0.8, places=12)

    def test_features_raise_the_applicable_share(self):
        bare = summarize_matrix(build_pre_tailoring_matrix(BARE_SUBSYSTEM))
        rich = summarize_matrix(build_pre_tailoring_matrix(POWER_SUBSYSTEM))
        self.assertGreater(rich["applicable_share"], bare["applicable_share"])

    def test_empty_summary_rejected(self):
        with self.assertRaises(ValueError):
            summarize_matrix([])


class AssessmentTests(unittest.TestCase):
    def test_clean_pass_is_compliant(self):
        out = assess_pre_tailoring(POWER_SUBSYSTEM)
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])
        self.assertEqual(len(out["matrix"]), len(PROVISION_GROUPS))

    def test_rejected_request_becomes_a_finding(self):
        out = assess_pre_tailoring(
            BARE_SUBSYSTEM,
            [{"item": "avionics-chain", "group": "g-power-distribution",
              "requested": "not-applicable"}],
        )
        self.assertFalse(out["compliant"])
        self.assertEqual(out["findings"][0]["finding"], "tailoring-rejected")

    def test_admitted_downgrade_keeps_the_pass_clean(self):
        out = assess_pre_tailoring(
            BARE_SUBSYSTEM,
            [{"item": "avionics-chain", "group": "g-power-distribution",
              "requested": "not-applicable",
              "justification": "no distribution function on this chain",
              "approval_authority": "project-authority"}],
        )
        self.assertTrue(out["compliant"])
        cell = [c for c in out["matrix"]
                if c["group"] == "g-power-distribution"][0]
        self.assertEqual(cell["disposition"], "not-applicable")

    def test_request_against_unknown_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_pre_tailoring(
                BARE_SUBSYSTEM,
                [{"item": "nowhere", "group": "g-power-distribution",
                  "requested": "applicable"}],
            )

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            assess_pre_tailoring(BARE_SUBSYSTEM, ["raise it"])

    def test_share_floor_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_pre_tailoring(BARE_SUBSYSTEM, (), 1.5)

    def test_non_numeric_share_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_pre_tailoring(BARE_SUBSYSTEM, (), "0.8")

    def test_share_below_floor_is_a_finding(self):
        out = assess_pre_tailoring(BARE_SUBSYSTEM, (), 0.9)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["findings"][-1]["finding"],
                         "binding-share-below-floor")

    def test_floor_met_within_representation_error_still_passes(self):
        # The share is exactly 8/10; the declared floor sits one ULP above it.
        # The engineering floor is unchanged -- only the representation error
        # is absorbed, so the physically compliant case stays compliant.
        floor = math.nextafter(0.8, 1.0)
        share = summarize_matrix(
            build_pre_tailoring_matrix(BARE_SUBSYSTEM))["binding_share"]
        self.assertLess(share, floor)
        out = assess_pre_tailoring(BARE_SUBSYSTEM, (), floor)
        self.assertTrue(out["compliant"])


if __name__ == "__main__":
    unittest.main()
