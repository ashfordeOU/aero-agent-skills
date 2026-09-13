#!/usr/bin/env python3
"""Gate 3 contract test for e2001-sample-cleanliness-policy.

stdlib unittest, offline, deterministic. Run: python3 test_e2001_sample_cleanliness_policy.py
"""

import math
import unittest

from e2001_sample_cleanliness_policy_logic import (
    BASE_OBSCURATION_PERCENT_PER_DAY,
    HANDLING_FAMILIES,
    UNCONTROLLED_EQUIVALENT_CLASS,
    accrued_obscuration_percent,
    assess_sample_cleanliness_policy,
    categorize_handling_step,
    check_contact_controls,
    check_environment_conformance,
    effective_iso_class,
    obscuration_rate_percent_per_day,
    required_iso_class,
    step_obscuration_percent,
    validate_environment,
)


def near(test, got, want, rel=1e-9):
    test.assertAlmostEqual(got, want, delta=abs(want) * rel + 1e-18)


def clean_chain():
    return [
        {
            "name": "solvent clean of coupon",
            "environment": {"id": "prep-bench", "iso_class": 5},
            "duration_h": 2.0,
            "contact": True,
            "tooling_control": "cleanroom-tweezers",
        },
        {
            "name": "transfer to facility",
            "environment": {"id": "airlock", "iso_class": 6, "purge": "dry-nitrogen"},
            "duration_h": 0.5,
        },
        {
            "name": "storage in desiccator",
            "environment": {"id": "desiccator", "iso_class": 6, "purge": "vacuum"},
            "duration_h": 48.0,
        },
        {
            "name": "mount on sample holder",
            "environment": {"id": "prep-bench", "iso_class": 5},
            "duration_h": 1.0,
            "contact": True,
            "tooling_control": "powder-free-gloves",
        },
        {
            "name": "yield measurement scan",
            "environment": {"id": "chamber", "iso_class": 5, "purge": "vacuum"},
            "duration_h": 6.0,
        },
    ]


def clean_sample(**over):
    sample = {
        "id": "SEY-COUPON-014",
        "sensitivity": "high",
        "policy_reference": "project contamination-control plan, issue 3",
        "allowable_obscuration_percent": 1.0e-3,
        "steps": clean_chain(),
    }
    sample.update(over)
    return sample


class TestStepCategorization(unittest.TestCase):
    def test_declared_family_wins(self):
        step = {"name": "unrecognisable label", "family": "storage"}
        self.assertEqual(categorize_handling_step(step), "storage")

    def test_every_family_is_derivable_from_a_name(self):
        names = {
            "preparation": "solvent rinse",
            "transfer": "transfer to airlock",
            "storage": "desiccator storage",
            "mounting": "mount on holder",
            "measurement": "beam scan",
        }
        for family in HANDLING_FAMILIES:
            self.assertEqual(categorize_handling_step({"name": names[family]}), family)

    def test_unknown_declared_family_raises(self):
        with self.assertRaises(ValueError):
            categorize_handling_step({"name": "solvent rinse", "family": "washing"})

    def test_uncategorized_step_name_raises(self):
        with self.assertRaises(ValueError):
            categorize_handling_step({"name": "zzz unknown activity"})

    def test_missing_name_raises(self):
        with self.assertRaises(ValueError):
            categorize_handling_step({"family": "storage"})

    def test_non_mapping_step_raises(self):
        with self.assertRaises(ValueError):
            categorize_handling_step(["solvent rinse"])


class TestRequiredClass(unittest.TestCase):
    def test_sensitivity_ladder(self):
        self.assertEqual(required_iso_class("high"), 5)
        self.assertEqual(required_iso_class("moderate"), 7)
        self.assertEqual(required_iso_class("low"), 8)

    def test_unknown_sensitivity_raises(self):
        with self.assertRaises(ValueError):
            required_iso_class("extreme")


class TestEnvironment(unittest.TestCase):
    def test_purge_defaults_to_none(self):
        env = validate_environment({"iso_class": 7})
        self.assertEqual(env["purge"], "none")
        self.assertFalse(env["uncontrolled"])

    def test_uncontrolled_takes_worst_class(self):
        env = validate_environment({"uncontrolled": True})
        self.assertEqual(env["iso_class"], UNCONTROLLED_EQUIVALENT_CLASS)

    def test_unknown_purge_raises(self):
        with self.assertRaises(ValueError):
            validate_environment({"iso_class": 5, "purge": "argon"})

    def test_missing_iso_class_raises(self):
        with self.assertRaises(ValueError):
            validate_environment({"id": "bench"})

    def test_bool_iso_class_raises(self):
        with self.assertRaises(ValueError):
            validate_environment({"iso_class": True})

    def test_out_of_range_iso_class_raises(self):
        with self.assertRaises(ValueError):
            validate_environment({"iso_class": 12})

    def test_non_mapping_environment_raises(self):
        with self.assertRaises(ValueError):
            validate_environment("iso-5")

    def test_nitrogen_purge_credits_one_class(self):
        self.assertEqual(effective_iso_class({"iso_class": 6, "purge": "dry-nitrogen"}), 5)

    def test_vacuum_purge_credits_two_classes(self):
        self.assertEqual(effective_iso_class({"iso_class": 7, "purge": "vacuum"}), 5)

    def test_credit_floors_at_class_one(self):
        self.assertEqual(effective_iso_class({"iso_class": 2, "purge": "vacuum"}), 1)

    def test_uncontrolled_gets_no_purge_credit(self):
        env = {"uncontrolled": True, "purge": "vacuum"}
        self.assertEqual(effective_iso_class(env), UNCONTROLLED_EQUIVALENT_CLASS)


class TestObscurationRate(unittest.TestCase):
    def test_one_decade_per_class(self):
        near(self, obscuration_rate_percent_per_day(5), BASE_OBSCURATION_PERCENT_PER_DAY)
        near(
            self,
            obscuration_rate_percent_per_day(6),
            BASE_OBSCURATION_PERCENT_PER_DAY * 10.0,
        )
        near(
            self,
            obscuration_rate_percent_per_day(4),
            BASE_OBSCURATION_PERCENT_PER_DAY / 10.0,
        )

    def test_vacuum_purge_stops_settling(self):
        near(self, obscuration_rate_percent_per_day(8, "vacuum"), 0.0)

    def test_nitrogen_purge_is_one_tenth(self):
        near(
            self,
            obscuration_rate_percent_per_day(7, "dry-nitrogen"),
            obscuration_rate_percent_per_day(7) * 0.1,
        )

    def test_uncontrolled_penalty_applies(self):
        near(
            self,
            obscuration_rate_percent_per_day(9, "none", True),
            obscuration_rate_percent_per_day(9) * 10.0,
        )

    def test_bad_class_raises(self):
        with self.assertRaises(ValueError):
            obscuration_rate_percent_per_day(0)

    def test_bad_purge_raises(self):
        with self.assertRaises(ValueError):
            obscuration_rate_percent_per_day(5, "helium")


class TestStepAccrual(unittest.TestCase):
    def test_obscuration_scales_with_duration(self):
        base = {"name": "desiccator storage", "environment": {"iso_class": 6}}
        one = dict(base, duration_h=24.0)
        two = dict(base, duration_h=48.0)
        near(self, step_obscuration_percent(two), 2.0 * step_obscuration_percent(one))

    def test_one_day_at_class_five_matches_base_rate(self):
        step = {
            "name": "desiccator storage",
            "environment": {"iso_class": 5},
            "duration_h": 24.0,
        }
        near(self, step_obscuration_percent(step), BASE_OBSCURATION_PERCENT_PER_DAY)

    def test_zero_duration_contributes_nothing(self):
        step = {
            "name": "transfer to airlock",
            "environment": {"iso_class": 8},
            "duration_h": 0.0,
        }
        near(self, step_obscuration_percent(step), 0.0)

    def test_negative_duration_raises(self):
        step = {
            "name": "desiccator storage",
            "environment": {"iso_class": 5},
            "duration_h": -1.0,
        }
        with self.assertRaises(ValueError):
            step_obscuration_percent(step)

    def test_non_numeric_duration_raises(self):
        step = {
            "name": "desiccator storage",
            "environment": {"iso_class": 5},
            "duration_h": "2h",
        }
        with self.assertRaises(ValueError):
            step_obscuration_percent(step)

    def test_infinite_duration_raises(self):
        step = {
            "name": "desiccator storage",
            "environment": {"iso_class": 5},
            "duration_h": math.inf,
        }
        with self.assertRaises(ValueError):
            step_obscuration_percent(step)

    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            accrued_obscuration_percent([])

    def test_non_sequence_chain_raises(self):
        with self.assertRaises(ValueError):
            accrued_obscuration_percent({"name": "solvent rinse"})

    def test_chain_total_is_the_sum_of_steps(self):
        chain = clean_chain()
        total = accrued_obscuration_percent(chain)
        expected = math.fsum(step_obscuration_percent(s) for s in chain)
        near(self, total, expected)


class TestConformanceChecks(unittest.TestCase):
    def test_clean_chain_has_no_environment_finding(self):
        self.assertEqual(check_environment_conformance(clean_chain(), "high"), [])

    def test_dirty_step_is_flagged_for_a_sensitive_sample(self):
        chain = clean_chain()
        chain[1]["environment"] = {"id": "corridor", "iso_class": 8}
        codes = [f["code"] for f in check_environment_conformance(chain, "high")]
        self.assertIn("environment-below-required-class", codes)

    def test_same_step_passes_for_a_low_sensitivity_sample(self):
        chain = clean_chain()
        chain[1]["environment"] = {"id": "corridor", "iso_class": 8}
        self.assertEqual(check_environment_conformance(chain, "low"), [])

    def test_uncontrolled_environment_is_always_flagged(self):
        chain = clean_chain()
        chain[2]["environment"] = {"id": "shop-floor", "uncontrolled": True}
        codes = [f["code"] for f in check_environment_conformance(chain, "low")]
        self.assertIn("uncontrolled-environment", codes)

    def test_contact_step_without_control_is_flagged(self):
        chain = clean_chain()
        del chain[0]["tooling_control"]
        codes = [f["code"] for f in check_contact_controls(chain)]
        self.assertEqual(codes, ["contact-without-tooling-control"])

    def test_blank_control_is_flagged(self):
        chain = clean_chain()
        chain[0]["tooling_control"] = "   "
        self.assertEqual(len(check_contact_controls(chain)), 1)

    def test_non_contact_steps_need_no_control(self):
        chain = [s for s in clean_chain() if not s.get("contact")]
        self.assertEqual(check_contact_controls(chain), [])

    def test_unknown_tooling_control_raises(self):
        chain = clean_chain()
        chain[0]["tooling_control"] = "bare-hands"
        with self.assertRaises(ValueError):
            check_contact_controls(chain)


class TestAssessment(unittest.TestCase):
    def test_clean_sample_is_compliant(self):
        report = assess_sample_cleanliness_policy(clean_sample())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["required_iso_class"], 5)

    def test_report_counts_step_families(self):
        report = assess_sample_cleanliness_policy(clean_sample())
        self.assertEqual(report["step_families"]["preparation"], 1)
        self.assertEqual(report["step_families"]["measurement"], 1)
        self.assertEqual(sum(report["step_families"].values()), 5)

    def test_missing_policy_reference_is_a_finding(self):
        report = assess_sample_cleanliness_policy(clean_sample(policy_reference=""))
        self.assertIn("policy-reference-missing", report["finding_codes"])
        self.assertFalse(report["compliant"])

    def test_absent_budget_is_a_finding_not_a_pass(self):
        report = assess_sample_cleanliness_policy(
            clean_sample(allowable_obscuration_percent=None)
        )
        self.assertIn("obscuration-budget-not-on-record", report["finding_codes"])
        self.assertFalse(report["compliant"])

    def test_budget_exceedance_is_flagged(self):
        report = assess_sample_cleanliness_policy(
            clean_sample(allowable_obscuration_percent=1.0e-6)
        )
        self.assertIn("obscuration-budget-exceeded", report["finding_codes"])

    def test_exact_budget_boundary_stays_compliant(self):
        chain = [
            {
                "name": "desiccator storage leg %d" % i,
                "environment": {"iso_class": 5},
                "duration_h": 8.0,
            }
            for i in range(3)
        ]
        budget = BASE_OBSCURATION_PERCENT_PER_DAY
        sample = clean_sample(steps=chain, allowable_obscuration_percent=budget)
        report = assess_sample_cleanliness_policy(sample)
        self.assertNotIn("obscuration-budget-exceeded", report["finding_codes"])
        self.assertTrue(report["compliant"])
        near(self, report["accrued_obscuration_percent"], budget)

    def test_non_positive_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_sample_cleanliness_policy(
                clean_sample(allowable_obscuration_percent=0.0)
            )

    def test_non_numeric_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_sample_cleanliness_policy(
                clean_sample(allowable_obscuration_percent="1e-3")
            )

    def test_missing_sample_id_raises(self):
        with self.assertRaises(ValueError):
            assess_sample_cleanliness_policy(clean_sample(id=""))

    def test_unknown_sensitivity_raises(self):
        with self.assertRaises(ValueError):
            assess_sample_cleanliness_policy(clean_sample(sensitivity="critical"))

    def test_non_mapping_sample_raises(self):
        with self.assertRaises(ValueError):
            assess_sample_cleanliness_policy(["SEY-COUPON-014"])

    def test_findings_accumulate_across_categories(self):
        chain = clean_chain()
        chain[1]["environment"] = {"id": "shop-floor", "uncontrolled": True}
        del chain[3]["tooling_control"]
        sample = clean_sample(steps=chain, policy_reference=None)
        report = assess_sample_cleanliness_policy(sample)
        for code in (
            "policy-reference-missing",
            "uncontrolled-environment",
            "contact-without-tooling-control",
        ):
            self.assertIn(code, report["finding_codes"])
        self.assertFalse(report["compliant"])


if __name__ == "__main__":
    unittest.main()
