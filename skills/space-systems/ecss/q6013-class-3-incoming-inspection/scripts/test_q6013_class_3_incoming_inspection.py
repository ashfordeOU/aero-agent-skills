"""Contract tests for the clause 6.3.7 class 3 incoming inspection logic.

The cases follow the receiving workflow one step at a time: the surveillance
audit behind the supplier, the coverage of the source inspection report, the
families the category keeps at the dock, the integer sample plan, the accept
number the source defects are judged against, the residual duties no
delegation removes, and the three dispositions a delivery can end in. Each
step is exercised on both sides of its limit.
"""

import unittest

from q6013_class_3_incoming_inspection_logic import (
    DEFAULT_SURVEILLANCE_VALIDITY_MONTHS,
    REQUIRED_SOURCE_CRITERIA,
    RESIDUAL_DOCK_DUTIES,
    assess_class3_incoming_inspection,
    delegation_decision,
    family_is_delegable,
    residual_dock_findings,
    source_criteria_gaps,
    source_sample_size,
    source_sample_verdict,
    surveillance_currency,
)

FULL_CRITERIA = {item: True for item in REQUIRED_SOURCE_CRITERIA}
CLEAN_DOCK = {item: True for item in RESIDUAL_DOCK_DUTIES}


def _spec(**overrides):
    spec = {
        "part_family": "cmos-digital-logic",
        "audit_age_months": 6.0,
        "source_report_present": True,
        "source_report_signed": True,
        "covered_criteria": dict(FULL_CRITERIA),
        "received_quantity": 1000,
        "source_defects": 0,
        "dock_observations": dict(CLEAN_DOCK),
    }
    spec.update(overrides)
    return spec


class SurveillanceTests(unittest.TestCase):
    def test_recent_audit_is_current(self):
        self.assertTrue(surveillance_currency(6.0)["current"])

    def test_audit_exactly_on_the_validity_limit_is_current(self):
        result = surveillance_currency(DEFAULT_SURVEILLANCE_VALIDITY_MONTHS)
        self.assertAlmostEqual(result["months_remaining"], 0.0, places=9)
        self.assertTrue(result["current"])

    def test_audit_past_the_validity_limit_is_not_current(self):
        self.assertFalse(surveillance_currency(36.0, 24.0)["current"])

    def test_negative_audit_age_rejected(self):
        with self.assertRaises(ValueError):
            surveillance_currency(-1.0)

    def test_zero_validity_window_rejected(self):
        with self.assertRaises(ValueError):
            surveillance_currency(1.0, 0.0)


class SourceReportCoverageTests(unittest.TestCase):
    def test_full_coverage_leaves_no_gap(self):
        self.assertEqual(source_criteria_gaps(FULL_CRITERIA), [])

    def test_absent_criterion_reported_as_a_gap(self):
        covered = dict(FULL_CRITERIA)
        del covered["marking-legibility"]
        self.assertEqual(source_criteria_gaps(covered), ["marking-legibility"])

    def test_criterion_marked_not_covered_reported(self):
        covered = dict(FULL_CRITERIA)
        covered["external-visual"] = False
        self.assertIn("external-visual", source_criteria_gaps(covered))

    def test_sequence_of_criterion_names_accepted(self):
        self.assertEqual(source_criteria_gaps(list(REQUIRED_SOURCE_CRITERIA)), [])

    def test_non_boolean_coverage_value_rejected(self):
        with self.assertRaises(ValueError):
            source_criteria_gaps({"external-visual": "partly"})


class DelegableFamilyTests(unittest.TestCase):
    def test_ordinary_family_may_be_inspected_at_the_supplier(self):
        self.assertTrue(family_is_delegable("cmos-digital-logic"))

    def test_hybrid_family_stays_at_the_dock(self):
        self.assertFalse(family_is_delegable("hybrid"))

    def test_family_match_ignores_case_and_space(self):
        self.assertFalse(family_is_delegable("  High-Voltage "))

    def test_blank_family_rejected(self):
        with self.assertRaises(ValueError):
            family_is_delegable("   ")


class DelegationTests(unittest.TestCase):
    def _claim(self, **overrides):
        claim = {
            "part_family": "sram-memory",
            "audit_age_months": 4.0,
            "source_report_present": True,
            "source_report_signed": True,
            "covered_criteria": dict(FULL_CRITERIA),
        }
        claim.update(overrides)
        return claim

    def test_complete_claim_is_granted(self):
        result = delegation_decision(self._claim())
        self.assertTrue(result["granted"])
        self.assertEqual(result["reasons"], [])

    def test_stale_audit_refuses_delegation(self):
        result = delegation_decision(self._claim(audit_age_months=40.0))
        self.assertFalse(result["granted"])
        self.assertTrue(any("surveillance" in item for item in result["reasons"]))

    def test_unsigned_report_refuses_delegation(self):
        self.assertFalse(delegation_decision(self._claim(source_report_signed=False))["granted"])

    def test_absent_report_refuses_delegation(self):
        result = delegation_decision(
            self._claim(source_report_present=False, source_report_signed=False)
        )
        self.assertFalse(result["granted"])

    def test_non_delegable_family_refuses_delegation(self):
        self.assertFalse(delegation_decision(self._claim(part_family="custom-asic"))["granted"])

    def test_uncovered_criterion_refuses_delegation(self):
        covered = dict(FULL_CRITERIA)
        covered["lead-and-terminal-condition"] = False
        result = delegation_decision(self._claim(covered_criteria=covered))
        self.assertFalse(result["granted"])
        self.assertEqual(result["uncovered_criteria"], ["lead-and-terminal-condition"])

    def test_every_refusal_reason_is_named_not_just_the_first(self):
        result = delegation_decision(
            self._claim(
                part_family="hybrid",
                audit_age_months=40.0,
                source_report_present=False,
                source_report_signed=False,
            )
        )
        self.assertGreaterEqual(len(result["reasons"]), 3)

    def test_missing_claim_key_rejected(self):
        claim = self._claim()
        del claim["audit_age_months"]
        with self.assertRaises(ValueError):
            delegation_decision(claim)


class SampleSizeTests(unittest.TestCase):
    def test_proportional_sample_for_a_round_lot(self):
        self.assertEqual(source_sample_size(1000), 20)

    def test_proportional_sample_rounds_up(self):
        self.assertEqual(source_sample_size(1051), 22)

    def test_small_lot_raised_to_the_floor(self):
        self.assertEqual(source_sample_size(50), 3)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(source_sample_size(2), 2)

    def test_large_lot_limited_by_the_cap(self):
        self.assertEqual(source_sample_size(1000000), 50)

    def test_sample_is_reproducible_for_the_same_lot(self):
        self.assertEqual(source_sample_size(777), source_sample_size(777))

    def test_percent_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            source_sample_size(1000, percent=0)

    def test_cap_below_floor_rejected(self):
        with self.assertRaises(ValueError):
            source_sample_size(1000, floor=10, cap=5)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            source_sample_size(0)


class SourceVerdictTests(unittest.TestCase):
    def test_clean_sample_accepts(self):
        self.assertTrue(source_sample_verdict(20, 0)["accepted"])

    def test_one_defect_against_accept_on_zero_rejects(self):
        self.assertFalse(source_sample_verdict(20, 1)["accepted"])

    def test_defects_equal_to_a_declared_accept_number_accept(self):
        self.assertTrue(source_sample_verdict(20, 2, accept_number=2)["accepted"])

    def test_defect_fraction_reported(self):
        self.assertAlmostEqual(
            source_sample_verdict(20, 1, accept_number=1)["defect_fraction"], 0.05, places=9
        )

    def test_more_defects_than_units_rejected(self):
        with self.assertRaises(ValueError):
            source_sample_verdict(5, 6)


class ResidualDutyTests(unittest.TestCase):
    def test_clean_arrival_has_no_residual_finding(self):
        self.assertEqual(residual_dock_findings(CLEAN_DOCK), [])

    def test_unsatisfied_duty_reported(self):
        observations = dict(CLEAN_DOCK)
        observations["package-integrity"] = False
        self.assertEqual(residual_dock_findings(observations), ["package-integrity"])

    def test_omitted_duty_counts_as_unsatisfied(self):
        observations = dict(CLEAN_DOCK)
        del observations["quantity-reconciliation"]
        self.assertIn("quantity-reconciliation", residual_dock_findings(observations))

    def test_unknown_duty_rejected(self):
        observations = dict(CLEAN_DOCK)
        observations["paint-colour"] = True
        with self.assertRaises(ValueError):
            residual_dock_findings(observations)


class AssessmentTests(unittest.TestCase):
    def test_sound_delegation_releases_to_stores(self):
        result = assess_class3_incoming_inspection(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-to-stores")
        self.assertEqual(result["findings"], [])

    def test_refused_delegation_sends_the_delivery_to_a_dock_inspection(self):
        result = assess_class3_incoming_inspection(_spec(source_report_signed=False))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "dock-inspection-required")

    def test_residual_failure_quarantines_even_with_sound_delegation(self):
        observations = dict(CLEAN_DOCK)
        observations["package-integrity"] = False
        result = assess_class3_incoming_inspection(_spec(dock_observations=observations))
        self.assertEqual(result["disposition"], "quarantine")

    def test_source_defects_beyond_the_accept_number_quarantine(self):
        result = assess_class3_incoming_inspection(_spec(source_defects=3))
        self.assertEqual(result["disposition"], "quarantine")

    def test_residual_failure_outranks_a_refused_delegation(self):
        observations = dict(CLEAN_DOCK)
        observations["delivery-documentation"] = False
        result = assess_class3_incoming_inspection(
            _spec(part_family="hybrid", dock_observations=observations)
        )
        self.assertEqual(result["disposition"], "quarantine")

    def test_sample_follows_the_received_quantity(self):
        result = assess_class3_incoming_inspection(_spec(received_quantity=2000))
        self.assertEqual(result["source_sample"]["sample_size"], 40)

    def test_every_reason_is_named_not_just_the_first(self):
        observations = dict(CLEAN_DOCK)
        observations["identity-reconciliation"] = False
        result = assess_class3_incoming_inspection(
            _spec(part_family="hybrid", audit_age_months=40.0, dock_observations=observations)
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["dock_observations"]
        with self.assertRaises(ValueError):
            assess_class3_incoming_inspection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_incoming_inspection(["not", "a", "mapping"])

    def test_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_incoming_inspection(_spec(received_quantity=0))


if __name__ == "__main__":
    unittest.main()
