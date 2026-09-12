#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 6.3.4 contained/restrained compliance.

Exercises scripts/contained_restrained_compliance_logic.py (stdlib unittest, offline).
Contract: item categorization for four recognized types (container, restrained,
latched, tethered) and rejection of unknown types; FoS gate against limit (>=1.0)
and ultimate (>=1.5) minimums; restraint margin-of-safety as allowable/applied - 1
returning math.inf for zero applied load; failure-mode documentation requiring
a non-empty text field and a recognized consequence category; redundancy requirement
for catastrophic and critical consequence items only; full per-item compliance
evaluator that accumulates all violations; batch evaluator returning all_compliant
flag and non_compliant_count. Invalid inputs raise ContainedRestrainedError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import contained_restrained_compliance_logic as cr


class TestCategorizeItem(unittest.TestCase):
    def test_container_valid(self):
        self.assertEqual(cr.categorize_item('container'), 'container')

    def test_restrained_valid(self):
        self.assertEqual(cr.categorize_item('restrained'), 'restrained')

    def test_latched_valid(self):
        self.assertEqual(cr.categorize_item('latched'), 'latched')

    def test_tethered_valid(self):
        self.assertEqual(cr.categorize_item('tethered'), 'tethered')

    def test_unknown_type_raises(self):
        with self.assertRaises(cr.ContainedRestrainedError):
            cr.categorize_item('bolt')

    def test_empty_string_raises(self):
        with self.assertRaises(cr.ContainedRestrainedError):
            cr.categorize_item('')


class TestFactorOfSafety(unittest.TestCase):
    def test_both_pass_at_minimums(self):
        self.assertEqual(cr.check_factor_of_safety(1.0, 1.5), [])

    def test_excess_fos_passes(self):
        self.assertEqual(cr.check_factor_of_safety(1.2, 2.0), [])

    def test_limit_fos_too_low(self):
        violations = cr.check_factor_of_safety(0.9, 1.5)
        self.assertEqual(len(violations), 1)
        self.assertIn('limit', violations[0])

    def test_ultimate_fos_too_low(self):
        violations = cr.check_factor_of_safety(1.0, 1.4)
        self.assertEqual(len(violations), 1)
        self.assertIn('ultimate', violations[0])

    def test_both_fos_too_low_two_violations(self):
        violations = cr.check_factor_of_safety(0.8, 1.2)
        self.assertEqual(len(violations), 2)

    def test_exactly_at_minimum_passes(self):
        self.assertEqual(cr.check_factor_of_safety(1.0, 1.5), [])


class TestRestraintMarginOfSafety(unittest.TestCase):
    def test_positive_margin(self):
        ms = cr.restraint_margin_of_safety(1000.0, 800.0)
        self.assertAlmostEqual(ms, 0.25)

    def test_negative_margin(self):
        ms = cr.restraint_margin_of_safety(800.0, 1000.0)
        self.assertAlmostEqual(ms, -0.2)

    def test_zero_applied_returns_inf(self):
        self.assertEqual(cr.restraint_margin_of_safety(1000.0, 0.0), math.inf)

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(cr.ContainedRestrainedError):
            cr.restraint_margin_of_safety(0.0, 100.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(cr.ContainedRestrainedError):
            cr.restraint_margin_of_safety(-200.0, 100.0)

    def test_negative_applied_raises(self):
        with self.assertRaises(cr.ContainedRestrainedError):
            cr.restraint_margin_of_safety(500.0, -50.0)

    def test_equal_allowable_and_applied_zero_ms(self):
        ms = cr.restraint_margin_of_safety(750.0, 750.0)
        self.assertAlmostEqual(ms, 0.0)


class TestFailureModeDoc(unittest.TestCase):
    def test_valid_doc_and_consequence_marginal(self):
        self.assertEqual(
            cr.check_failure_mode_doc('bracket yields under dynamic load', 'marginal'),
            []
        )

    def test_valid_doc_and_consequence_catastrophic(self):
        self.assertEqual(
            cr.check_failure_mode_doc('tether severs under shock', 'catastrophic'),
            []
        )

    def test_empty_doc_fails(self):
        violations = cr.check_failure_mode_doc('', 'negligible')
        self.assertEqual(len(violations), 1)
        self.assertIn('missing', violations[0])

    def test_whitespace_only_doc_fails(self):
        violations = cr.check_failure_mode_doc('   ', 'critical')
        self.assertEqual(len(violations), 1)

    def test_invalid_consequence_fails(self):
        violations = cr.check_failure_mode_doc('shear failure of clip', 'unknown')
        self.assertEqual(len(violations), 1)
        self.assertIn('consequence', violations[0])

    def test_both_invalid_two_violations(self):
        violations = cr.check_failure_mode_doc('', 'invalid')
        self.assertEqual(len(violations), 2)


class TestRedundancyRequirement(unittest.TestCase):
    def test_catastrophic_with_redundancy_passes(self):
        self.assertEqual(
            cr.check_redundancy_requirement('catastrophic', True), []
        )

    def test_catastrophic_without_redundancy_fails(self):
        violations = cr.check_redundancy_requirement('catastrophic', False)
        self.assertEqual(len(violations), 1)
        self.assertIn('catastrophic', violations[0])

    def test_critical_without_redundancy_fails(self):
        violations = cr.check_redundancy_requirement('critical', False)
        self.assertEqual(len(violations), 1)
        self.assertIn('critical', violations[0])

    def test_critical_with_redundancy_passes(self):
        self.assertEqual(
            cr.check_redundancy_requirement('critical', True), []
        )

    def test_marginal_no_redundancy_required(self):
        self.assertEqual(
            cr.check_redundancy_requirement('marginal', False), []
        )

    def test_negligible_no_redundancy_required(self):
        self.assertEqual(
            cr.check_redundancy_requirement('negligible', False), []
        )


class TestEvaluateItemCompliance(unittest.TestCase):
    def _make_item(self, **overrides):
        base = {
            'item_id': 'ITEM-001',
            'item_type': 'tethered',
            'load_path_defined': True,
            'fos_limit_actual': 1.05,
            'fos_ult_actual': 1.6,
            'failure_mode_doc': 'tether frays under fatigue loading',
            'consequence': 'marginal',
            'has_redundant_restraint': False,
        }
        base.update(overrides)
        return base

    def test_fully_compliant_item(self):
        result = cr.evaluate_item_compliance(self._make_item())
        self.assertTrue(result['compliant'])
        self.assertEqual(result['violations'], [])
        self.assertEqual(result['item_id'], 'ITEM-001')

    def test_load_path_not_defined_fails(self):
        result = cr.evaluate_item_compliance(self._make_item(load_path_defined=False))
        self.assertFalse(result['compliant'])
        self.assertTrue(any('load path' in v for v in result['violations']))

    def test_invalid_item_type_fails(self):
        result = cr.evaluate_item_compliance(self._make_item(item_type='spring'))
        self.assertFalse(result['compliant'])

    def test_ultimate_fos_violation(self):
        result = cr.evaluate_item_compliance(self._make_item(fos_ult_actual=1.3))
        self.assertFalse(result['compliant'])
        self.assertTrue(any('ultimate' in v for v in result['violations']))

    def test_critical_consequence_needs_redundancy(self):
        result = cr.evaluate_item_compliance(
            self._make_item(consequence='critical', has_redundant_restraint=False)
        )
        self.assertFalse(result['compliant'])
        self.assertTrue(any('redundant' in v for v in result['violations']))

    def test_critical_consequence_with_redundancy_compliant(self):
        result = cr.evaluate_item_compliance(
            self._make_item(consequence='critical', has_redundant_restraint=True)
        )
        self.assertTrue(result['compliant'])

    def test_multiple_violations_accumulated(self):
        result = cr.evaluate_item_compliance(self._make_item(
            load_path_defined=False,
            fos_ult_actual=1.2,
            failure_mode_doc='',
        ))
        self.assertFalse(result['compliant'])
        self.assertGreaterEqual(len(result['violations']), 3)


class TestEvaluateBatch(unittest.TestCase):
    def _good_item(self, item_id):
        return {
            'item_id': item_id,
            'item_type': 'container',
            'load_path_defined': True,
            'fos_limit_actual': 1.1,
            'fos_ult_actual': 1.6,
            'failure_mode_doc': 'vessel wall cracks under overpressure event',
            'consequence': 'negligible',
            'has_redundant_restraint': False,
        }

    def test_all_compliant(self):
        items = [self._good_item('A'), self._good_item('B')]
        summary = cr.evaluate_batch(items)
        self.assertTrue(summary['all_compliant'])
        self.assertEqual(summary['non_compliant_count'], 0)
        self.assertEqual(len(summary['results']), 2)

    def test_mixed_compliance(self):
        bad = dict(self._good_item('C'))
        bad['load_path_defined'] = False
        items = [self._good_item('D'), bad]
        summary = cr.evaluate_batch(items)
        self.assertFalse(summary['all_compliant'])
        self.assertEqual(summary['non_compliant_count'], 1)

    def test_empty_batch(self):
        summary = cr.evaluate_batch([])
        self.assertTrue(summary['all_compliant'])
        self.assertEqual(summary['non_compliant_count'], 0)
        self.assertEqual(summary['results'], [])


if __name__ == "__main__":
    unittest.main()
