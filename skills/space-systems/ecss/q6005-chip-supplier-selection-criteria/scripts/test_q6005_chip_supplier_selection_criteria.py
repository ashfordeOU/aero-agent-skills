#!/usr/bin/env python3
"""Gate 3 contract test for q6005-chip-supplier-selection-criteria.

Offline, stdlib unittest. Exercises the source categorization, the audit
validity window, every veto criterion, the merit score and the three-way
disposition of ECSS-Q-ST-60-05C clause 8.1.2 as paraphrased in the logic
module. Boundary values are compared with assertAlmostEqual: the weights are
decimal fractions whose binary sum differs in the last bits between libm
implementations, so a strict inequality at the bound is not portable.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_chip_supplier_selection_criteria_logic import (  # noqa: E402
    CATEGORY_WEIGHT,
    DEFAULT_ACCEPT_THRESHOLD,
    DEFAULT_AUDIT_VALIDITY_MONTHS,
    SOURCE_FRANCHISED,
    SOURCE_INDEPENDENT,
    SOURCE_ORIGINAL,
    assess_source_acceptability,
    audit_is_current,
    categorize_source,
    chain_depth,
    outstanding_conditions,
    validate_source_record,
    veto_findings,
    weighted_score,
)


def source(**overrides):
    """A fully compliant direct source, overridable field by field."""
    record = {
        "name": "wafer line A",
        "chain": [],
        "audit_age_months": 12.0,
        "quality_system_approved": True,
        "traceable_to_wafer_lot": True,
        "franchise_agreement": False,
        "pcn_commitment": True,
        "supplies_single_wafer_lot": True,
        "upscreening_evidence": False,
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_non_mapping_record_is_refused(self):
        for bad in ([], "wafer line A", None, 7):
            with self.assertRaises(ValueError):
                validate_source_record(bad)

    def test_blank_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_record(source(name="   "))

    def test_missing_chain_key_is_refused(self):
        record = source()
        del record["chain"]
        with self.assertRaises(ValueError):
            validate_source_record(record)

    def test_string_chain_is_not_a_sequence_of_links(self):
        with self.assertRaises(ValueError):
            validate_source_record(source(chain="broker one"))

    def test_negative_audit_age_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_record(source(audit_age_months=-1.0))

    def test_boolean_audit_age_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_record(source(audit_age_months=True))

    def test_non_boolean_evidence_field_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_record(source(pcn_commitment="yes"))

    def test_validated_chain_is_stripped_and_counted(self):
        normalised = validate_source_record(source(chain=[" distributor B "]))
        self.assertEqual(normalised["chain"], ("distributor B",))
        self.assertEqual(chain_depth(source(chain=["d1", "d2"])), 2)


class CategorizationTests(unittest.TestCase):
    def test_direct_source_is_the_original_manufacturer(self):
        self.assertEqual(categorize_source(source()), SOURCE_ORIGINAL)

    def test_intermediary_under_franchise_is_a_distributor(self):
        record = source(chain=["distributor B"], franchise_agreement=True)
        self.assertEqual(categorize_source(record), SOURCE_FRANCHISED)

    def test_intermediary_without_franchise_is_an_independent_reseller(self):
        record = source(chain=["stockist C"], franchise_agreement=False)
        self.assertEqual(categorize_source(record), SOURCE_INDEPENDENT)

    def test_franchise_flag_alone_does_not_demote_a_direct_source(self):
        self.assertEqual(categorize_source(source(franchise_agreement=True)), SOURCE_ORIGINAL)


class AuditWindowTests(unittest.TestCase):
    def test_audit_inside_the_window_is_current(self):
        self.assertTrue(audit_is_current(12.0, DEFAULT_AUDIT_VALIDITY_MONTHS))

    def test_audit_exactly_at_the_window_edge_is_still_current(self):
        # The age equals the bound; assert the equality itself, not a rounding
        # direction, then assert the behaviour that equality produces.
        self.assertAlmostEqual(
            DEFAULT_AUDIT_VALIDITY_MONTHS, 36.0, places=9
        )
        self.assertTrue(audit_is_current(36.0, 36.0))

    def test_audit_past_the_window_is_not_current(self):
        self.assertFalse(audit_is_current(48.0, DEFAULT_AUDIT_VALIDITY_MONTHS))

    def test_zero_validity_window_is_refused(self):
        with self.assertRaises(ValueError):
            audit_is_current(1.0, 0.0)


class VetoTests(unittest.TestCase):
    def test_compliant_direct_source_fails_no_veto(self):
        self.assertEqual(veto_findings(source()), [])

    def test_unapproved_quality_system_vetoes(self):
        findings = veto_findings(source(quality_system_approved=False))
        self.assertEqual(len(findings), 1)
        self.assertIn("quality system", findings[0])

    def test_untraceable_die_vetoes(self):
        findings = veto_findings(source(traceable_to_wafer_lot=False))
        self.assertTrue(any("wafer lot" in f for f in findings))

    def test_aged_out_audit_vetoes(self):
        findings = veto_findings(source(audit_age_months=40.0))
        self.assertTrue(any("audit" in f for f in findings))

    def test_chain_deeper_than_the_auditable_limit_vetoes(self):
        record = source(chain=["d1", "d2", "d3"], franchise_agreement=True)
        findings = veto_findings(record)
        self.assertTrue(any("intermediaries deep" in f for f in findings))

    def test_chain_exactly_at_the_limit_does_not_veto(self):
        record = source(chain=["d1", "d2"], franchise_agreement=True)
        self.assertEqual(veto_findings(record), [])

    def test_independent_reseller_without_upscreening_vetoes(self):
        record = source(chain=["stockist C"], upscreening_evidence=False)
        self.assertTrue(any("upscreening" in f for f in veto_findings(record)))

    def test_independent_reseller_with_upscreening_clears_that_veto(self):
        record = source(chain=["stockist C"], upscreening_evidence=True)
        self.assertEqual(veto_findings(record), [])

    def test_several_failures_are_all_named_not_just_the_first(self):
        record = source(
            quality_system_approved=False,
            traceable_to_wafer_lot=False,
            audit_age_months=99.0,
        )
        self.assertEqual(len(veto_findings(record)), 3)

    def test_negative_chain_limit_is_refused(self):
        with self.assertRaises(ValueError):
            veto_findings(source(), DEFAULT_AUDIT_VALIDITY_MONTHS, -1)


class ScoreTests(unittest.TestCase):
    def test_full_direct_source_scores_the_top_of_the_range(self):
        self.assertAlmostEqual(weighted_score(source()), 1.0, places=9)

    def test_category_weight_alone_is_the_floor_for_a_bare_source(self):
        record = source(pcn_commitment=False, supplies_single_wafer_lot=False)
        self.assertAlmostEqual(
            weighted_score(record), CATEGORY_WEIGHT[SOURCE_ORIGINAL], places=9
        )

    def test_franchised_route_scores_below_the_direct_route(self):
        direct = weighted_score(source())
        franchised = weighted_score(
            source(chain=["distributor B"], franchise_agreement=True)
        )
        # 1.00 against 0.85: far outside any rounding question.
        self.assertLess(franchised, direct)

    def test_missing_single_lot_commitment_costs_its_weight(self):
        full = weighted_score(source())
        without = weighted_score(source(supplies_single_wafer_lot=False))
        self.assertAlmostEqual(full - without, 0.30, places=9)


class DispositionTests(unittest.TestCase):
    def test_compliant_direct_source_is_acceptable(self):
        result = assess_source_acceptability({"source": source()})
        self.assertEqual(result["decision"], "acceptable")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["conditions"], [])

    def test_vetoed_source_is_refused_whatever_its_merit(self):
        record = source(traceable_to_wafer_lot=False)
        result = assess_source_acceptability({"source": record})
        self.assertEqual(result["decision"], "refused")
        self.assertFalse(result["acceptable"])
        self.assertAlmostEqual(result["score"], 1.0, places=9)

    def test_merit_below_the_threshold_returns_named_conditions(self):
        record = source(pcn_commitment=False)
        result = assess_source_acceptability({"source": record})
        self.assertEqual(result["decision"], "acceptable-with-conditions")
        self.assertTrue(
            any("process-change-notification" in c for c in result["conditions"])
        )

    def test_franchised_route_with_full_evidence_clears_the_threshold(self):
        record = source(chain=["distributor B"], franchise_agreement=True)
        result = assess_source_acceptability({"source": record})
        self.assertEqual(result["decision"], "acceptable")
        self.assertAlmostEqual(result["score"], 0.85, places=9)

    def test_threshold_met_exactly_is_acceptable_not_conditional(self):
        # An exact equality at the threshold is a representation question, so
        # assert the equality and then the disposition it must produce.
        record = source(chain=["distributor B"], franchise_agreement=True)
        result = assess_source_acceptability(
            {"source": record, "accept_threshold": 0.85}
        )
        self.assertAlmostEqual(result["score"], result["threshold"], places=9)
        self.assertEqual(result["decision"], "acceptable")

    def test_conditions_name_the_chain_evidence_for_an_indirect_route(self):
        record = source(
            chain=["stockist C"],
            upscreening_evidence=True,
            pcn_commitment=False,
            supplies_single_wafer_lot=False,
        )
        conditions = outstanding_conditions(record)
        self.assertEqual(len(conditions), 3)
        self.assertTrue(any("through the chain" in c for c in conditions))

    def test_report_carries_category_depth_and_audit_state(self):
        record = source(chain=["distributor B"], franchise_agreement=True)
        result = assess_source_acceptability({"source": record})
        self.assertEqual(result["category"], SOURCE_FRANCHISED)
        self.assertEqual(result["chain_depth"], 1)
        self.assertTrue(result["audit_current"])
        self.assertEqual(result["source"], "wafer line A")

    def test_missing_source_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_source_acceptability({})

    def test_threshold_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            assess_source_acceptability({"source": source(), "accept_threshold": 1.5})

    def test_tightened_audit_window_can_refuse_a_previously_acceptable_source(self):
        spec = {"source": source(audit_age_months=24.0), "audit_validity_months": 12.0}
        result = assess_source_acceptability(spec)
        self.assertEqual(result["decision"], "refused")
        self.assertFalse(result["audit_current"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
