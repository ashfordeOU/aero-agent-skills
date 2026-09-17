"""Contract tests for the Table 8-15 legacy class 3 lot acceptance logic.

The cases follow the workflow one step at a time: the split between the core
groups run on the delivered lot and the remainder heritage evidence may stand
in for, the accept numbers a non-consuming group may carry while a consuming
one stays accept-on-zero, the conditions that make evidence transferable, the
cap on how much of the set may be credited, and the disposition that carries
them. Each step is exercised on both sides of its limit, so a review of the
record shows what was judged and not only the verdict.
"""

import unittest

from q6013_legacy_class_3_acceptance_table_logic import (
    CLASS_3_GROUPS,
    CORE_GROUPS,
    CREDIT_VALIDITY_MONTHS,
    GROUP_RULES,
    LIMIT_TOLERANCE,
    MAX_CREDITED_FRACTION,
    SATISFACTION_ROUTES,
    assess_legacy_class_3_acceptance,
    credit_admissibility,
    credit_budget,
    group_verdict,
    validate_group,
)


def _evidence(**overrides):
    record = {"same_part_type": True, "same_site": True, "age_months": 12.0}
    record.update(overrides)
    return record


def _tested(name, **extra):
    record = {"group": name, "satisfied_by": "test", "required_sample": 8,
              "sample_size": 8}
    record.update(extra)
    return record


def _credited(name, **overrides):
    return {
        "group": name,
        "satisfied_by": "credit",
        "evidence": _evidence(**overrides),
    }


def _spec(**overrides):
    spec = {"groups": [_tested(name) for name in CLASS_3_GROUPS]}
    spec.update(overrides)
    return spec


class GroupValidationTests(unittest.TestCase):
    def test_a_tested_group_is_normalised(self):
        record = validate_group(_tested("external-visual", accept_number=1))
        self.assertEqual(record["satisfied_by"], "test")
        self.assertEqual(record["accept_number"], 1)

    def test_a_group_defaults_to_the_test_route(self):
        record = validate_group({"group": "external-visual"})
        self.assertEqual(record["satisfied_by"], "test")

    def test_the_core_flag_comes_from_the_group_table(self):
        self.assertTrue(validate_group(_tested("electrical-end-points"))["core"])
        self.assertFalse(validate_group(_tested("solderability"))["core"])

    def test_a_non_consuming_group_may_carry_an_accept_number(self):
        record = validate_group(_tested("electrical-end-points", accept_number=1))
        self.assertEqual(record["accept_number"], 1)

    def test_a_consuming_group_stays_accept_on_zero(self):
        with self.assertRaises(ValueError):
            validate_group(_tested("endurance-life-test", accept_number=1))

    def test_a_group_outside_the_table_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(_tested("radiation-acceptance"))

    def test_an_unknown_satisfaction_route_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group({"group": "solderability", "satisfied_by": "waiver"})

    def test_a_credited_group_without_evidence_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group({"group": "solderability", "satisfied_by": "credit"})

    def test_more_failures_than_devices_sampled_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(_tested("external-visual", sample_size=4, failures=5))

    def test_an_accept_number_above_the_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(
                _tested("external-visual", sample_size=4, accept_number=5)
            )

    def test_non_mapping_entry_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(["solderability"])


class CreditAdmissibilityTests(unittest.TestCase):
    def test_matching_recent_evidence_from_the_same_site_is_admissible(self):
        result = credit_admissibility("solderability", _evidence())
        self.assertTrue(result["admissible"])

    def test_evidence_exactly_on_the_validity_window_is_admissible(self):
        result = credit_admissibility(
            "solderability", _evidence(age_months=CREDIT_VALIDITY_MONTHS)
        )
        self.assertAlmostEqual(
            result["age_months"], CREDIT_VALIDITY_MONTHS, places=9
        )
        self.assertTrue(result["within_window"])
        self.assertTrue(result["admissible"])

    def test_evidence_past_the_window_is_refused(self):
        result = credit_admissibility(
            "solderability", _evidence(age_months=CREDIT_VALIDITY_MONTHS + 6.0)
        )
        self.assertFalse(result["admissible"])

    def test_evidence_from_another_part_type_is_refused(self):
        result = credit_admissibility(
            "solderability", _evidence(same_part_type=False)
        )
        self.assertFalse(result["admissible"])

    def test_evidence_from_another_site_is_refused(self):
        result = credit_admissibility("solderability", _evidence(same_site=False))
        self.assertFalse(result["admissible"])

    def test_a_core_group_cannot_be_credited_at_all(self):
        result = credit_admissibility("external-visual", _evidence())
        self.assertFalse(result["admissible"])
        self.assertTrue(
            any("delivered lot" in reason for reason in result["reasons"])
        )

    def test_a_negative_evidence_age_is_refused(self):
        with self.assertRaises(ValueError):
            credit_admissibility("solderability", _evidence(age_months=-1.0))

    def test_a_non_boolean_match_flag_is_refused(self):
        with self.assertRaises(ValueError):
            credit_admissibility("solderability", _evidence(same_site="yes"))

    def test_missing_evidence_key_is_refused(self):
        evidence = _evidence()
        del evidence["age_months"]
        with self.assertRaises(ValueError):
            credit_admissibility("solderability", evidence)


class GroupVerdictTests(unittest.TestCase):
    def test_a_clean_tested_group_is_accepted(self):
        self.assertTrue(group_verdict(_tested("external-visual"))["accepted"])

    def test_a_sample_shortfall_rejects_a_tested_group(self):
        record = group_verdict(
            _tested("external-visual", required_sample=8, sample_size=5)
        )
        self.assertEqual(record["sample_shortfall"], 3)
        self.assertFalse(record["accepted"])

    def test_failures_within_the_accept_number_are_accepted(self):
        record = group_verdict(
            _tested("electrical-end-points", accept_number=2, failures=2)
        )
        self.assertTrue(record["accepted"])

    def test_an_admissible_credit_accepts_the_group(self):
        record = group_verdict(_credited("solderability"))
        self.assertTrue(record["accepted"])
        self.assertIsNone(record["sample_met"])

    def test_an_inadmissible_credit_rejects_the_group(self):
        record = group_verdict(_credited("solderability", same_site=False))
        self.assertFalse(record["accepted"])


class CreditBudgetTests(unittest.TestCase):
    def test_a_fully_tested_set_uses_none_of_the_budget(self):
        records = [group_verdict(_tested(name)) for name in CLASS_3_GROUPS]
        budget = credit_budget(records)
        self.assertEqual(budget["credited"], 0)
        self.assertTrue(budget["accepted"])

    def test_a_credited_share_landing_exactly_on_the_cap_is_accepted(self):
        records = [group_verdict(_tested(name)) for name in CORE_GROUPS]
        records.append(group_verdict(_tested("thermal-shock-and-seal")))
        records += [
            group_verdict(_credited(name))
            for name in (
                "mechanical-shock-and-vibration",
                "solderability",
                "endurance-life-test",
            )
        ]
        budget = credit_budget(records)
        self.assertAlmostEqual(
            budget["credited_fraction"], MAX_CREDITED_FRACTION, places=9
        )
        self.assertTrue(budget["accepted"])

    def test_a_credited_share_past_the_cap_is_refused(self):
        records = [group_verdict(_tested(name)) for name in CORE_GROUPS]
        records += [
            group_verdict(_credited(name))
            for name in (
                "thermal-shock-and-seal",
                "mechanical-shock-and-vibration",
                "solderability",
                "endurance-life-test",
            )
        ]
        budget = credit_budget(records)
        self.assertFalse(budget["accepted"])
        self.assertEqual(budget["tested"], len(CORE_GROUPS))

    def test_an_empty_record_list_is_refused(self):
        with self.assertRaises(ValueError):
            credit_budget([])


class AssessmentTests(unittest.TestCase):
    def test_a_fully_tested_campaign_accepts_the_lot(self):
        result = assess_legacy_class_3_acceptance(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-class-3-lot")
        self.assertEqual(result["findings"], [])

    def test_a_campaign_within_the_credit_cap_accepts_the_lot(self):
        groups = [_tested(name) for name in CORE_GROUPS]
        groups.append(_tested("thermal-shock-and-seal"))
        groups += [
            _credited(name)
            for name in (
                "mechanical-shock-and-vibration",
                "solderability",
                "endurance-life-test",
            )
        ]
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["credited_groups"]), 3)

    def test_crediting_past_the_cap_holds_the_lot(self):
        groups = [_tested(name) for name in CORE_GROUPS]
        groups += [
            _credited(name)
            for name in (
                "thermal-shock-and-seal",
                "mechanical-shock-and-vibration",
                "solderability",
                "endurance-life-test",
            )
        ]
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("past the" in item for item in result["findings"]))

    def test_crediting_a_core_group_is_refused_by_name(self):
        groups = [_credited("external-visual")] + [
            _tested(name) for name in CLASS_3_GROUPS if name != "external-visual"
        ]
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertIn("external-visual", result["rejecting_groups"])
        self.assertEqual(result["disposition"], "hold-class-3-lot")

    def test_an_absent_core_group_is_named_as_such(self):
        groups = [
            _tested(name)
            for name in CLASS_3_GROUPS
            if name != "electrical-end-points"
        ]
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertIn("electrical-end-points", result["absent_core_groups"])
        self.assertTrue(
            any("core group" in item for item in result["findings"])
        )

    def test_an_absent_non_core_group_is_reported_as_coverage(self):
        groups = [
            _tested(name) for name in CLASS_3_GROUPS if name != "solderability"
        ]
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertEqual(result["absent_core_groups"], ())
        self.assertIn("solderability", result["absent_groups"])
        self.assertFalse(result["accepted"])

    def test_stale_evidence_holds_an_otherwise_clean_campaign(self):
        groups = [_tested(name) for name in CLASS_3_GROUPS if name != "solderability"]
        groups.append(
            _credited("solderability", age_months=CREDIT_VALIDITY_MONTHS + 12.0)
        )
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("validity window" in item for item in result["findings"])
        )

    def test_a_failing_tested_group_is_reported_by_name(self):
        groups = [_tested(name) for name in CLASS_3_GROUPS if name != "solderability"]
        groups.append(_tested("solderability", failures=1))
        result = assess_legacy_class_3_acceptance(_spec(groups=groups))
        self.assertEqual(result["rejecting_groups"], ["solderability"])

    def test_a_repeated_group_is_refused(self):
        spec = _spec()
        spec["groups"].append(_tested("solderability"))
        with self.assertRaises(ValueError):
            assess_legacy_class_3_acceptance(spec)

    def test_an_empty_group_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_3_acceptance(_spec(groups=[]))

    def test_missing_groups_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_3_acceptance({})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_3_acceptance(["not", "a", "mapping"])

    def test_named_constants_are_representation_sized_or_bounded(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertLess(MAX_CREDITED_FRACTION, 1.0)
        self.assertGreater(CREDIT_VALIDITY_MONTHS, 0.0)
        self.assertEqual(len(CLASS_3_GROUPS), len(GROUP_RULES))
        self.assertEqual(SATISFACTION_ROUTES, ("test", "credit"))
        self.assertTrue(set(CORE_GROUPS).issubset(set(CLASS_3_GROUPS)))


if __name__ == "__main__":
    unittest.main()
