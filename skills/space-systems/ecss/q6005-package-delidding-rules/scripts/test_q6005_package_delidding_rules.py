#!/usr/bin/env python3
"""Gate 3 contract test for q6005-package-delidding-rules.

Offline, stdlib unittest. Exercises the seal-type and reason validation, the
reopen-cycle allowance, the sealing-land budget, the return-to-stock rule,
the retest set and the three-way disposition of ECSS-Q-ST-60-05C clause
10.5.5 as paraphrased in the logic module. A package whose reseals consume
its land down to exactly the minimum is an ordinary case, so that bound is
asserted with assertAlmostEqual rather than a strict inequality that could
round either way between the build host and the CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_package_delidding_rules_logic import (  # noqa: E402
    BASE_RESEAL_TESTS,
    SEAL_TYPES,
    assess_delidding,
    delid_cycles_remaining,
    projected_seal_land_mm,
    required_reseal_tests,
    returns_to_deliverable_stock,
    seal_land_after_cycles_mm,
    seal_land_headroom_mm,
    validate_package,
    validate_reason,
    validate_seal_type,
)


def package(**overrides):
    record = {
        "package_id": "HYB-114",
        "seal_type": "seam-weld",
        "initial_seal_land_mm": 0.75,
        "prior_delid_cycles": 0,
        "deliverable_stock": True,
    }
    record.update(overrides)
    return record


def delid(**overrides):
    """A first reopening of a weld-sealed unit for an approved repair."""
    spec = {
        "package": package(),
        "reason": "approved-repair",
        "approved_procedure": True,
        "reseal_capability": True,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_unknown_seal_type_is_refused(self):
        with self.assertRaises(ValueError):
            validate_seal_type("epoxy-lid")

    def test_seal_type_is_normalised(self):
        self.assertEqual(validate_seal_type("  Seam-Weld "), "seam-weld")

    def test_unknown_reason_is_refused(self):
        with self.assertRaises(ValueError):
            validate_reason("curiosity")

    def test_missing_package_key_is_refused(self):
        for key in ("package_id", "seal_type", "initial_seal_land_mm"):
            record = package()
            del record[key]
            with self.assertRaises(ValueError):
                validate_package(record)

    def test_non_positive_land_is_refused(self):
        with self.assertRaises(ValueError):
            validate_package(package(initial_seal_land_mm=0.0))

    def test_negative_cycle_history_is_refused_but_history_is_not(self):
        with self.assertRaises(ValueError):
            validate_package(package(prior_delid_cycles=-1))
        self.assertEqual(validate_package(package(prior_delid_cycles=5))["prior_delid_cycles"], 5)

    def test_boolean_cycle_count_is_not_an_integer(self):
        with self.assertRaises(ValueError):
            validate_package(package(prior_delid_cycles=True))


class CycleAndLandTests(unittest.TestCase):
    def test_cycle_allowance_depends_on_the_seal_type(self):
        self.assertEqual(delid_cycles_remaining(package()), 2)
        self.assertEqual(delid_cycles_remaining(package(seal_type="solder-seal")), 2)
        self.assertEqual(delid_cycles_remaining(package(seal_type="glass-frit")), 0)

    def test_cycles_remaining_never_goes_negative(self):
        self.assertEqual(delid_cycles_remaining(package(prior_delid_cycles=7)), 0)

    def test_land_is_consumed_a_fixed_width_per_reseal(self):
        self.assertAlmostEqual(seal_land_after_cycles_mm(package(), 0), 0.75, places=9)
        self.assertAlmostEqual(seal_land_after_cycles_mm(package(), 2), 0.45, places=9)

    def test_projected_land_includes_the_reseal_being_asked_for(self):
        self.assertAlmostEqual(projected_seal_land_mm(package()), 0.60, places=9)
        self.assertAlmostEqual(
            projected_seal_land_mm(package(prior_delid_cycles=1)), 0.45, places=9
        )

    def test_land_consumed_exactly_to_the_minimum_still_has_zero_headroom(self):
        tight = package(initial_seal_land_mm=0.45)
        self.assertAlmostEqual(projected_seal_land_mm(tight), 0.30, places=9)
        self.assertAlmostEqual(seal_land_headroom_mm(tight), 0.0, places=9)

    def test_land_consumed_to_the_minimum_is_not_a_refusal(self):
        result = assess_delidding(delid(package=package(initial_seal_land_mm=0.45)))
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["disposition"], "reopen-permitted")

    def test_land_consumed_below_the_minimum_is_a_refusal(self):
        result = assess_delidding(delid(package=package(initial_seal_land_mm=0.40)))
        self.assertFalse(result["permitted"])
        self.assertTrue(any("sealing land" in b for b in result["blockers"]))


class ReturnRouteTests(unittest.TestCase):
    def test_an_approved_repair_returns_the_unit_to_stock(self):
        self.assertTrue(returns_to_deliverable_stock("approved-repair"))

    def test_analysis_reasons_consume_the_unit(self):
        for reason in (
            "failure-analysis",
            "destructive-physical-analysis",
            "construction-analysis",
        ):
            self.assertFalse(returns_to_deliverable_stock(reason))

    def test_an_analysis_delid_is_permitted_but_non_deliverable(self):
        result = assess_delidding(delid(reason="construction-analysis"))
        self.assertEqual(result["disposition"], "reopen-permitted-non-deliverable")
        self.assertTrue(result["permitted"])
        self.assertFalse(result["returns_to_deliverable_stock"])
        self.assertTrue(any("consumes the unit" in n for n in result["notes"]))

    def test_a_repair_without_reseal_capability_is_refused(self):
        result = assess_delidding(delid(reseal_capability=False))
        self.assertFalse(result["permitted"])

    def test_an_analysis_delid_needs_no_reseal_capability(self):
        result = assess_delidding(
            delid(reason="failure-analysis", reseal_capability=False)
        )
        self.assertTrue(result["permitted"])


class RetestSetTests(unittest.TestCase):
    def test_the_base_retest_set_is_always_present(self):
        tests = required_reseal_tests("seam-weld", "approved-repair")
        for name in BASE_RESEAL_TESTS:
            self.assertIn(name, tests)

    def test_internal_work_adds_pre_seal_verifications(self):
        tests = required_reseal_tests("seam-weld", "approved-repair", internal_work_done=True)
        self.assertIn("internal-visual-inspection-before-reseal", tests)
        self.assertIn("interconnect-verification-after-internal-work", tests)
        self.assertLess(
            tests.index("internal-visual-inspection-before-reseal"),
            tests.index("fine-leak-test"),
        )

    def test_the_seal_type_adds_its_own_check(self):
        self.assertIn("weld-land-dimensional-check", required_reseal_tests("seam-weld", "approved-repair"))
        self.assertIn(
            "seal-fillet-visual-check", required_reseal_tests("solder-seal", "approved-repair")
        )

    def test_only_a_returning_unit_owes_re_screening(self):
        self.assertIn(
            "re-screening-before-return-to-deliverable-stock",
            required_reseal_tests("seam-weld", "approved-repair"),
        )
        self.assertNotIn(
            "re-screening-before-return-to-deliverable-stock",
            required_reseal_tests("seam-weld", "failure-analysis"),
        )

    def test_extra_tests_are_appended_without_duplicates(self):
        tests = required_reseal_tests(
            "seam-weld", "approved-repair", extra=["fine-leak-test", "radiographic-inspection"]
        )
        self.assertEqual(tests.count("fine-leak-test"), 1)
        self.assertEqual(tests[-1], "radiographic-inspection")

    def test_malformed_retest_arguments_are_refused(self):
        with self.assertRaises(ValueError):
            required_reseal_tests("seam-weld", "approved-repair", internal_work_done="yes")
        with self.assertRaises(ValueError):
            required_reseal_tests("seam-weld", "approved-repair", extra="fine-leak-test")


class DispositionTests(unittest.TestCase):
    def test_a_first_repair_delid_is_permitted_with_its_retest_set(self):
        result = assess_delidding(delid())
        self.assertEqual(result["disposition"], "reopen-permitted")
        self.assertTrue(result["returns_to_deliverable_stock"])
        self.assertIn("fine-leak-test", result["reseal_tests"])

    def test_an_unapproved_procedure_refuses_the_delid(self):
        result = assess_delidding(delid(approved_procedure=False))
        self.assertEqual(result["disposition"], "reopen-not-permitted")
        self.assertEqual(result["reseal_tests"], [])

    def test_a_fired_glass_seal_is_not_reopened_for_return(self):
        result = assess_delidding(delid(package=package(seal_type="glass-frit")))
        self.assertFalse(result["permitted"])
        self.assertTrue(any("cannot be reinstated" in b for b in result["blockers"]))

    def test_a_spent_cycle_allowance_refuses_the_delid(self):
        result = assess_delidding(
            delid(package=package(initial_seal_land_mm=2.0, prior_delid_cycles=2))
        )
        self.assertFalse(result["permitted"])
        self.assertTrue(any("reopen cycle" in b for b in result["blockers"]))

    def test_spec_keys_are_required(self):
        for key in ("package", "reason"):
            spec = delid()
            del spec[key]
            with self.assertRaises(ValueError):
                assess_delidding(spec)

    def test_non_boolean_flags_are_refused(self):
        with self.assertRaises(ValueError):
            assess_delidding(delid(approved_procedure="yes"))
        with self.assertRaises(ValueError):
            assess_delidding(delid(reseal_capability="no"))
        with self.assertRaises(ValueError):
            assess_delidding(delid(internal_work_done="maybe"))

    def test_the_seal_table_is_the_single_source_of_the_allowances(self):
        self.assertEqual(sorted(SEAL_TYPES), ["glass-frit", "seam-weld", "solder-seal"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
