"""Contract tests for the clause 6.3.10 class 3 relifing of stored parts.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused relifing policy,
an unregistered store or package family, a lot still inside the period it
earned, an exhausted cumulative life cap, a record short of the attribute
sample, a record missing an owed test, a defect count over the acceptance
number, the repeatable re-tinning allowance and its ceiling, the flat grant
trimmed to the cap headroom, and a grant too small to be worth taking.
"""

import unittest

from q6013_class_3_relifing_logic import (
    BASE_STORAGE_MONTHS,
    DEFAULT_RELIFE_POLICY,
    ELECTRICAL_RE_VERIFICATION,
    EXTERNAL_VISUAL,
    HERMETIC_FAMILIES,
    MOISTURE_PRECONDITIONING,
    PACKAGE_SEAL,
    RELIFE_GRANTED,
    RELIFE_NOT_REQUIRED,
    RELIFE_REFUSED_LIFE_CAP_REACHED,
    RELIFE_REFUSED_NO_USEFUL_EXTENSION,
    RELIFE_REFUSED_SAMPLE_DEFECTIVE,
    RELIFE_REFUSED_SAMPLE_SHORT,
    RELIFE_REFUSED_TESTS_INCOMPLETE,
    REOPENING_GRADES,
    RETINNING_PERMITTED,
    SOLDERABILITY,
    STORAGE_GRADES,
    assess_relifing,
    base_storage_months,
    cumulative_life_cap_months,
    earned_storage_months,
    failing_relife_tests,
    granted_extension_months,
    relife_sample_size,
    required_relife_tests,
    storage_grade_factor,
    storage_period_expired,
    validate_relife_policy,
    validate_sample_record,
)


def _policy(**overrides):
    policy = dict(DEFAULT_RELIFE_POLICY)
    policy.update(overrides)
    return policy


def _clean(required):
    return {name: 0 for name in required}


def _case(**overrides):
    required = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
    case = {
        "package_family": "hermetic-ceramic",
        "storage_environment": "dry-nitrogen-cabinet",
        "elapsed_storage_months": 60.0,
        "lot_size": 100,
        "units_inspected": 10,
        "moisture_sensitive": False,
        "sample_results": _clean(required),
        "relifed_months_to_date": 0.0,
        "retins_used": 0,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_relife_policy(DEFAULT_RELIFE_POLICY), DEFAULT_RELIFE_POLICY
        )

    def test_policy_missing_a_key_is_refused(self):
        policy = dict(DEFAULT_RELIFE_POLICY)
        del policy["extension_fraction"]
        with self.assertRaises(ValueError):
            validate_relife_policy(policy)

    def test_an_extension_fraction_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(extension_fraction=1.2))

    def test_a_zero_extension_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(extension_fraction=0.0))

    def test_a_zero_life_multiple_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(cumulative_life_multiple=0.0))

    def test_a_sample_ceiling_under_the_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(sample_floor=10, sample_ceiling=4))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(["extension_fraction"])


class StoragePeriodTests(unittest.TestCase):
    def test_every_registered_store_credits_a_known_fraction(self):
        for name, factor in STORAGE_GRADES.items():
            self.assertAlmostEqual(storage_grade_factor(name), factor, places=9)

    def test_an_unregistered_store_is_refused(self):
        with self.assertRaises(ValueError):
            storage_grade_factor("a shelf in the lab")

    def test_an_unregistered_package_family_is_refused(self):
        with self.assertRaises(ValueError):
            base_storage_months("ceramic-ish")

    def test_the_hermetic_families_are_registered_families(self):
        self.assertTrue(HERMETIC_FAMILIES.issubset(set(BASE_STORAGE_MONTHS)))

    def test_a_graded_store_scales_the_baseline_period(self):
        self.assertAlmostEqual(
            earned_storage_months("plastic-encapsulated", "humidity-controlled-store"),
            14.4,
            places=9,
        )

    def test_an_uncontrolled_store_still_earns_a_short_period_here(self):
        earned = earned_storage_months("plastic-encapsulated", "uncontrolled-store")
        self.assertAlmostEqual(earned, 6.0, places=9)

    def test_a_lot_sitting_exactly_on_its_period_is_inside_it(self):
        self.assertFalse(storage_period_expired(48.0, 48.0))

    def test_a_lot_past_its_period_is_expired(self):
        self.assertTrue(storage_period_expired(49.0, 48.0))

    def test_a_negative_elapsed_storage_is_refused(self):
        with self.assertRaises(ValueError):
            storage_period_expired(-1.0, 48.0)


class SamplePlanTests(unittest.TestCase):
    def test_the_plan_is_the_integer_root_of_the_lot(self):
        self.assertEqual(relife_sample_size(100), 10)

    def test_a_small_lot_is_lifted_to_the_sample_floor(self):
        self.assertEqual(relife_sample_size(9), DEFAULT_RELIFE_POLICY["sample_floor"])

    def test_a_lot_smaller_than_the_floor_is_inspected_entirely(self):
        self.assertEqual(relife_sample_size(3), 3)

    def test_a_large_lot_is_held_at_the_sample_ceiling(self):
        self.assertEqual(
            relife_sample_size(4000), DEFAULT_RELIFE_POLICY["sample_ceiling"]
        )

    def test_a_zero_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            relife_sample_size(0)

    def test_a_non_integer_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            relife_sample_size(100.0)


class TestSetTests(unittest.TestCase):
    def test_a_hermetic_family_owes_a_seal_test(self):
        tests = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
        self.assertIn(PACKAGE_SEAL, tests)
        self.assertNotIn(MOISTURE_PRECONDITIONING, tests)

    def test_a_moisture_sensitive_plastic_family_owes_preconditioning(self):
        tests = required_relife_tests(
            "plastic-encapsulated", "dry-nitrogen-cabinet", True
        )
        self.assertIn(MOISTURE_PRECONDITIONING, tests)
        self.assertNotIn(PACKAGE_SEAL, tests)

    def test_visual_and_solderability_are_owed_by_every_family(self):
        for family in BASE_STORAGE_MONTHS:
            tests = required_relife_tests(family, "dry-nitrogen-cabinet", False)
            self.assertIn(EXTERNAL_VISUAL, tests)
            self.assertIn(SOLDERABILITY, tests)

    def test_an_uncontrolled_store_reopens_the_fuller_test_set(self):
        graded = required_relife_tests(
            "plastic-encapsulated", "dry-cabinet-low-humidity", False
        )
        reopened = required_relife_tests(
            "plastic-encapsulated", "uncontrolled-store", False
        )
        self.assertNotIn(ELECTRICAL_RE_VERIFICATION, graded)
        self.assertIn(ELECTRICAL_RE_VERIFICATION, reopened)
        self.assertIn(MOISTURE_PRECONDITIONING, reopened)

    def test_a_hermetic_lot_in_an_uncontrolled_store_owes_no_preconditioning(self):
        tests = required_relife_tests("hermetic-metal", "uncontrolled-store", False)
        self.assertIn(ELECTRICAL_RE_VERIFICATION, tests)
        self.assertNotIn(MOISTURE_PRECONDITIONING, tests)

    def test_the_reopening_grades_are_registered_stores(self):
        self.assertTrue(REOPENING_GRADES.issubset(set(STORAGE_GRADES)))

    def test_a_hermetic_family_declared_moisture_sensitive_is_refused(self):
        with self.assertRaises(ValueError):
            required_relife_tests("hermetic-metal", "dry-nitrogen-cabinet", True)


class SampleRecordTests(unittest.TestCase):
    def test_a_record_carrying_an_unowed_test_is_refused(self):
        required = required_relife_tests(
            "plastic-encapsulated", "dry-nitrogen-cabinet", False
        )
        record = _clean(required)
        record[PACKAGE_SEAL] = 0
        with self.assertRaises(ValueError):
            validate_sample_record(record, required, 10)

    def test_a_missing_owed_test_is_reported_not_assumed(self):
        required = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
        record = _clean(required)
        del record[PACKAGE_SEAL]
        checked = validate_sample_record(record, required, 10)
        self.assertFalse(checked["complete"])
        self.assertEqual(checked["missing"], [PACKAGE_SEAL])

    def test_more_defects_than_units_inspected_is_refused(self):
        required = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
        record = _clean(required)
        record[SOLDERABILITY] = 11
        with self.assertRaises(ValueError):
            validate_sample_record(record, required, 10)

    def test_a_non_integer_defect_count_is_refused(self):
        required = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
        record = _clean(required)
        record[SOLDERABILITY] = "none"
        with self.assertRaises(ValueError):
            validate_sample_record(record, required, 10)

    def test_failures_are_reported_in_the_owed_order(self):
        required = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
        record = _clean(required)
        record[SOLDERABILITY] = 1
        record[PACKAGE_SEAL] = 2
        self.assertEqual(
            failing_relife_tests(record, required, 10), [SOLDERABILITY, PACKAGE_SEAL]
        )

    def test_a_defect_count_inside_a_relaxed_acceptance_number_passes(self):
        required = required_relife_tests("hermetic-ceramic", "dry-nitrogen-cabinet", False)
        record = _clean(required)
        record[EXTERNAL_VISUAL] = 1
        self.assertEqual(
            failing_relife_tests(record, required, 10, _policy(accept_defects=1)), []
        )


class ExtensionTests(unittest.TestCase):
    def test_the_cap_is_a_multiple_of_the_earned_period(self):
        self.assertAlmostEqual(
            cumulative_life_cap_months("hermetic-ceramic", "dry-nitrogen-cabinet"),
            96.0,
            places=9,
        )

    def test_a_cycle_grants_a_flat_share_of_the_earned_period(self):
        self.assertAlmostEqual(
            granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 0.0),
            12.0,
            places=9,
        )

    def test_the_grant_does_not_decay_between_cycles(self):
        first = granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 0.0)
        second = granted_extension_months(
            "hermetic-ceramic", "dry-nitrogen-cabinet", 12.0
        )
        self.assertAlmostEqual(first, second, places=9)

    def test_the_grant_is_trimmed_to_the_cap_headroom(self):
        self.assertAlmostEqual(
            granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 90.0),
            6.0,
            places=9,
        )

    def test_an_exhausted_cap_grants_nothing(self):
        self.assertAlmostEqual(
            granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 96.0),
            0.0,
            places=9,
        )

    def test_a_negative_relifed_total_is_refused(self):
        with self.assertRaises(ValueError):
            granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", -1.0)


class AssessmentTests(unittest.TestCase):
    def test_an_expired_lot_with_a_clean_sample_is_relifed(self):
        result = assess_relifing(_case())
        self.assertEqual(result["verdict"], RELIFE_GRANTED)
        self.assertTrue(result["relifed"])
        self.assertAlmostEqual(result["granted_extension_months"], 12.0, places=9)
        self.assertAlmostEqual(result["renewed_period_months"], 72.0, places=9)

    def test_a_lot_still_inside_its_period_is_not_relifed(self):
        result = assess_relifing(_case(elapsed_storage_months=30.0))
        self.assertEqual(result["verdict"], RELIFE_NOT_REQUIRED)
        self.assertFalse(result["relifed"])

    def test_a_lot_exactly_on_its_period_is_not_relifed(self):
        result = assess_relifing(_case(elapsed_storage_months=48.0))
        self.assertEqual(result["verdict"], RELIFE_NOT_REQUIRED)

    def test_an_exhausted_cap_sends_the_lot_for_re_screening(self):
        result = assess_relifing(_case(relifed_months_to_date=96.0))
        self.assertEqual(result["verdict"], RELIFE_REFUSED_LIFE_CAP_REACHED)

    def test_a_record_short_of_the_attribute_sample_is_refused(self):
        result = assess_relifing(_case(units_inspected=8))
        self.assertEqual(result["verdict"], RELIFE_REFUSED_SAMPLE_SHORT)
        self.assertEqual(result["sample_size"], 10)

    def test_a_record_missing_an_owed_test_is_not_a_pass(self):
        case = _case()
        del case["sample_results"][PACKAGE_SEAL]
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_TESTS_INCOMPLETE)
        self.assertEqual(result["missing_tests"], [PACKAGE_SEAL])

    def test_a_lone_solderability_defect_permits_a_re_tin(self):
        case = _case()
        case["sample_results"][SOLDERABILITY] = 1
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RETINNING_PERMITTED)

    def test_the_re_tinning_allowance_is_repeatable_up_to_its_ceiling(self):
        case = _case(retins_used=1)
        case["sample_results"][SOLDERABILITY] = 1
        self.assertEqual(assess_relifing(case)["verdict"], RETINNING_PERMITTED)

    def test_the_re_tinning_allowance_stops_at_its_ceiling(self):
        case = _case(retins_used=2)
        case["sample_results"][SOLDERABILITY] = 1
        self.assertEqual(
            assess_relifing(case)["verdict"], RELIFE_REFUSED_SAMPLE_DEFECTIVE
        )

    def test_a_seal_defect_is_never_re_tinned(self):
        case = _case()
        case["sample_results"][PACKAGE_SEAL] = 1
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_SAMPLE_DEFECTIVE)
        self.assertEqual(result["failed_tests"], [PACKAGE_SEAL])

    def test_a_trimmed_grant_is_still_taken_where_it_is_useful(self):
        result = assess_relifing(_case(relifed_months_to_date=90.0))
        self.assertEqual(result["verdict"], RELIFE_GRANTED)
        self.assertAlmostEqual(result["granted_extension_months"], 6.0, places=9)

    def test_a_trimmed_grant_under_the_minimum_sends_the_lot_for_re_screening(self):
        result = assess_relifing(_case(relifed_months_to_date=95.0))
        self.assertEqual(result["verdict"], RELIFE_REFUSED_NO_USEFUL_EXTENSION)
        self.assertAlmostEqual(result["granted_extension_months"], 1.0, places=9)

    def test_a_flat_share_too_small_to_be_useful_is_refused(self):
        required = required_relife_tests(
            "bare-die-in-waffle-pack", "uncontrolled-store", False
        )
        case = _case(
            package_family="bare-die-in-waffle-pack",
            storage_environment="uncontrolled-store",
            elapsed_storage_months=9.0,
            sample_results=_clean(required),
        )
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_NO_USEFUL_EXTENSION)
        self.assertAlmostEqual(result["granted_extension_months"], 0.75, places=9)

    def test_an_uncontrolled_lot_owing_the_fuller_set_can_still_be_relifed(self):
        required = required_relife_tests(
            "tape-and-reel-passive", "uncontrolled-store", False
        )
        case = _case(
            package_family="tape-and-reel-passive",
            storage_environment="uncontrolled-store",
            elapsed_storage_months=12.0,
            sample_results=_clean(required),
        )
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_GRANTED)
        self.assertAlmostEqual(result["granted_extension_months"], 2.25, places=9)
        self.assertIn(ELECTRICAL_RE_VERIFICATION, result["required_tests"])
        self.assertIn(MOISTURE_PRECONDITIONING, result["required_tests"])

    def test_a_case_missing_a_required_key_is_refused(self):
        case = _case()
        del case["retins_used"]
        with self.assertRaises(ValueError):
            assess_relifing(case)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_relifing(["package_family"])

    def test_every_verdict_carries_at_least_one_finding(self):
        for case in (
            _case(),
            _case(elapsed_storage_months=30.0),
            _case(relifed_months_to_date=96.0),
            _case(units_inspected=8),
        ):
            self.assertTrue(assess_relifing(case)["findings"])


if __name__ == "__main__":
    unittest.main()
