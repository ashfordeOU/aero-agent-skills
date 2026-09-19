#!/usr/bin/env python3
"""Contract test for contamination nonconformance disposition (offline)."""

import copy
import unittest

from q7001_contamination_nonconformance_logic import (
    CONTAMINANT_KINDS,
    CRITICALITY_CRITICAL,
    CRITICALITY_LEVELS,
    CRITICALITY_SENSITIVE,
    CRITICALITY_STANDARD,
    CRITICAL_EXTRA_METHOD,
    DISPOSITION_ESCALATE,
    DISPOSITION_NO_ACTION,
    DISPOSITION_RECLEAN,
    DISPOSITION_USE_AS_IS,
    MINOR_EXCEEDANCE_RATIO,
    MOLECULAR,
    PARTICULATE,
    REVERIFICATION_METHODS,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    SEVERITY_NONE,
    contaminant_unit,
    exceedance,
    handle_contamination_nonconformance,
    performance_penalty,
    reclean_budget,
    required_records,
    reverification_methods,
    severity_of,
)

CASE = {
    "item": "radiator-panel-osr",
    "kind": MOLECULAR,
    "criticality": CRITICALITY_SENSITIVE,
    "measured": 2.0,
    "limit": 1.0,
    "sensitivity": 0.01,
    "allowance": 0.05,
    "cycles_used": 1,
    "max_cycles": 3,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class LedgerTests(unittest.TestCase):
    def test_molecular_is_an_areal_mass(self):
        self.assertEqual(contaminant_unit(MOLECULAR), "mg/m2")

    def test_particulate_is_an_obscuration(self):
        self.assertEqual(contaminant_unit(PARTICULATE), "percent-area-coverage")

    def test_unknown_contaminant_rejected(self):
        with self.assertRaises(ValueError):
            contaminant_unit("biological")

    def test_every_kind_has_a_unit_and_a_method_set(self):
        for kind in CONTAMINANT_KINDS:
            self.assertTrue(contaminant_unit(kind))
            self.assertTrue(REVERIFICATION_METHODS[kind])


class ExceedanceTests(unittest.TestCase):
    def test_a_level_below_the_limit_is_compliant(self):
        result = exceedance(0.8, 1.0)
        self.assertFalse(result["exceeded"])
        self.assertAlmostEqual(result["over_by"], 0.0, places=9)

    def test_a_level_exactly_on_the_limit_is_not_an_exceedance(self):
        result = exceedance(1.0, 1.0)
        self.assertFalse(result["exceeded"])
        self.assertAlmostEqual(result["ratio"], 1.0, places=9)

    def test_a_summed_level_landing_on_the_limit_is_not_an_exceedance(self):
        level = 0.1 + 0.2 + 0.7
        self.assertFalse(exceedance(level, 1.0)["exceeded"])

    def test_the_overrun_is_reported_absolutely_and_as_a_ratio(self):
        result = exceedance(2.5, 2.0)
        self.assertAlmostEqual(result["over_by"], 0.5, places=9)
        self.assertAlmostEqual(result["ratio"], 1.25, places=9)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            exceedance(1.0, 0.0)

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            exceedance(-0.1, 1.0)

    def test_boolean_measurement_rejected(self):
        with self.assertRaises(ValueError):
            exceedance(True, 1.0)


class PenaltyTests(unittest.TestCase):
    def test_the_penalty_follows_the_declared_sensitivity(self):
        result = performance_penalty(2.0, 0.01, 0.05, 1.0)
        self.assertAlmostEqual(result["penalty_at_measured"], 0.02, places=9)

    def test_the_penalty_at_the_limit_is_what_cleaning_can_reach(self):
        result = performance_penalty(2.0, 0.01, 0.05, 1.0)
        self.assertAlmostEqual(result["penalty_at_limit"], 0.01, places=9)
        self.assertAlmostEqual(result["recoverable_penalty"], 0.01, places=9)

    def test_a_penalty_exactly_on_the_allowance_still_fits(self):
        result = performance_penalty(2.0, 0.01, 0.02, 1.0)
        self.assertAlmostEqual(result["margin_at_measured"], 0.0, places=9)
        self.assertTrue(result["within_allowance"])

    def test_the_same_level_costs_more_on_a_more_sensitive_surface(self):
        blunt = performance_penalty(2.0, 0.001, 0.05, 1.0)
        sharp = performance_penalty(2.0, 0.05, 0.05, 1.0)
        self.assertLess(blunt["penalty_at_measured"], sharp["penalty_at_measured"])

    def test_an_unrecoverable_case_is_flagged_at_the_limit(self):
        result = performance_penalty(2.0, 0.1, 0.05, 1.0)
        self.assertFalse(result["recoverable_by_cleaning"])

    def test_negative_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            performance_penalty(2.0, -0.01, 0.05, 1.0)

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            performance_penalty(2.0, 0.01, -0.05, 1.0)


class SeverityTests(unittest.TestCase):
    def test_no_exceedance_has_no_severity(self):
        over = exceedance(0.8, 1.0)
        penalty = performance_penalty(0.8, 0.01, 0.05, 1.0)
        self.assertEqual(severity_of(over, penalty), SEVERITY_NONE)

    def test_a_small_overrun_inside_the_allowance_is_minor(self):
        over = exceedance(1.1, 1.0)
        penalty = performance_penalty(1.1, 0.01, 0.05, 1.0)
        self.assertEqual(severity_of(over, penalty), SEVERITY_MINOR)

    def test_an_overrun_exactly_on_the_minor_ratio_is_still_minor(self):
        over = exceedance(MINOR_EXCEEDANCE_RATIO, 1.0)
        penalty = performance_penalty(MINOR_EXCEEDANCE_RATIO, 0.01, 0.05, 1.0)
        self.assertAlmostEqual(over["ratio"], MINOR_EXCEEDANCE_RATIO, places=9)
        self.assertEqual(severity_of(over, penalty), SEVERITY_MINOR)

    def test_a_large_overrun_is_major(self):
        over = exceedance(3.0, 1.0)
        penalty = performance_penalty(3.0, 0.001, 0.5, 1.0)
        self.assertEqual(severity_of(over, penalty), SEVERITY_MAJOR)

    def test_a_small_overrun_that_breaks_the_allowance_is_major(self):
        over = exceedance(1.1, 1.0)
        penalty = performance_penalty(1.1, 0.1, 0.05, 1.0)
        self.assertEqual(severity_of(over, penalty), SEVERITY_MAJOR)


class CycleBudgetTests(unittest.TestCase):
    def test_a_fresh_item_has_its_whole_budget(self):
        result = reclean_budget(0, 3)
        self.assertEqual(result["cycles_remaining"], 3)
        self.assertTrue(result["cycles_available"])

    def test_a_spent_budget_leaves_no_cycle(self):
        result = reclean_budget(3, 3)
        self.assertEqual(result["cycles_remaining"], 0)
        self.assertFalse(result["cycles_available"])

    def test_a_surface_that_tolerates_no_cleaning_has_no_cycle(self):
        self.assertFalse(reclean_budget(0, 0)["cycles_available"])

    def test_more_cycles_used_than_permitted_rejected(self):
        with self.assertRaises(ValueError):
            reclean_budget(4, 3)

    def test_negative_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            reclean_budget(-1, 3)

    def test_boolean_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            reclean_budget(True, 3)


class ReverificationTests(unittest.TestCase):
    def test_a_molecular_case_gets_a_residue_method(self):
        methods = reverification_methods(MOLECULAR, CRITICALITY_STANDARD)
        self.assertIn("solvent-rinse-gravimetric-residue", methods)

    def test_a_particulate_case_gets_an_obscuration_method(self):
        methods = reverification_methods(PARTICULATE, CRITICALITY_STANDARD)
        self.assertIn("tape-lift-obscuration-count", methods)

    def test_the_two_contaminants_do_not_share_a_method_set(self):
        self.assertNotEqual(
            set(reverification_methods(MOLECULAR, CRITICALITY_STANDARD)),
            set(reverification_methods(PARTICULATE, CRITICALITY_STANDARD)),
        )

    def test_critical_hardware_adds_a_direct_surface_reading(self):
        for kind in CONTAMINANT_KINDS:
            methods = reverification_methods(kind, CRITICALITY_CRITICAL)
            self.assertIn(CRITICAL_EXTRA_METHOD[kind], methods)

    def test_criticality_never_shrinks_the_method_set(self):
        for kind in CONTAMINANT_KINDS:
            base = set(reverification_methods(kind, CRITICALITY_STANDARD))
            for level in CRITICALITY_LEVELS:
                self.assertTrue(base.issubset(set(reverification_methods(kind, level))))

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            reverification_methods(MOLECULAR, "mission-critical")


class DispositionTests(unittest.TestCase):
    def test_a_compliant_surface_needs_no_action(self):
        result = handle_contamination_nonconformance(_case(measured=0.9))
        self.assertEqual(result["disposition"], DISPOSITION_NO_ACTION)
        self.assertEqual(result["severity"], SEVERITY_NONE)

    def test_a_small_overrun_inside_the_allowance_goes_use_as_is(self):
        result = handle_contamination_nonconformance(_case(measured=1.1))
        self.assertEqual(result["disposition"], DISPOSITION_USE_AS_IS)
        self.assertIn("cleanliness-concession-approval", result["required_records"])

    def test_a_recoverable_overrun_with_budget_left_is_re_cleaned(self):
        result = handle_contamination_nonconformance(CASE)
        self.assertEqual(result["disposition"], DISPOSITION_RECLEAN)
        self.assertIn(
            "re-verification-measurement-record", result["required_records"]
        )

    def test_a_re_clean_names_a_method_that_can_see_the_contaminant(self):
        result = handle_contamination_nonconformance(CASE)
        self.assertIn("solvent-rinse-gravimetric-residue", result["reverification_methods"])

    def test_a_particulate_re_clean_names_a_particulate_method(self):
        result = handle_contamination_nonconformance(_case(kind=PARTICULATE))
        self.assertIn("tape-lift-obscuration-count", result["reverification_methods"])
        self.assertNotIn(
            "solvent-rinse-gravimetric-residue", result["reverification_methods"]
        )

    def test_a_spent_cleaning_budget_escalates_instead_of_re_cleaning(self):
        result = handle_contamination_nonconformance(_case(cycles_used=3))
        self.assertEqual(result["disposition"], DISPOSITION_ESCALATE)
        self.assertTrue(any("budget" in r for r in result["rationale"]))

    def test_a_case_cleaning_cannot_recover_escalates_with_budget_left(self):
        result = handle_contamination_nonconformance(_case(sensitivity=0.1))
        self.assertEqual(result["disposition"], DISPOSITION_ESCALATE)
        self.assertTrue(any("requirement or design" in r for r in result["rationale"]))

    def test_an_unrecoverable_case_spends_no_cleaning_cycle(self):
        result = handle_contamination_nonconformance(_case(sensitivity=0.1))
        self.assertEqual(result["reverification_methods"], ())

    def test_a_surface_within_its_limit_can_still_fail_on_performance(self):
        result = handle_contamination_nonconformance(
            _case(measured=0.9, sensitivity=0.1, allowance=0.05)
        )
        self.assertEqual(result["disposition"], DISPOSITION_ESCALATE)

    def test_an_escalation_owes_the_impact_analysis(self):
        result = handle_contamination_nonconformance(_case(cycles_used=3))
        self.assertIn("performance-impact-analysis", result["required_records"])

    def test_every_route_owes_the_nonconformance_report(self):
        for disposition in (
            DISPOSITION_NO_ACTION,
            DISPOSITION_USE_AS_IS,
            DISPOSITION_RECLEAN,
            DISPOSITION_ESCALATE,
        ):
            self.assertIn(
                "contamination-nonconformance-report", required_records(disposition)
            )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            required_records("quietly-ignore")

    def test_a_major_case_calls_the_board(self):
        result = handle_contamination_nonconformance(_case(measured=3.0))
        self.assertEqual(result["severity"], SEVERITY_MAJOR)
        self.assertTrue(result["board_required"])

    def test_a_use_as_is_does_not_call_the_board(self):
        result = handle_contamination_nonconformance(_case(measured=1.1))
        self.assertFalse(result["board_required"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            handle_contamination_nonconformance("radiator-panel-osr")

    def test_missing_item_rejected(self):
        case = _case()
        del case["item"]
        with self.assertRaises(ValueError):
            handle_contamination_nonconformance(case)

    def test_missing_limit_rejected(self):
        case = _case()
        del case["limit"]
        with self.assertRaises(ValueError):
            handle_contamination_nonconformance(case)


if __name__ == "__main__":
    unittest.main()
