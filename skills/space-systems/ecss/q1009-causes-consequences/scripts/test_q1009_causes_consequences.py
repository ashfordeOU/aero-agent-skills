"""Contract tests for the clause 5.2.2.3 cause and consequence analysis logic."""

import unittest

from q1009_causes_consequences_logic import (
    CAPA_PRIORITY_THRESHOLD,
    CONSEQUENCE_DIMENSIONS,
    MAX_PRIORITY_NUMBER,
    MIN_CAUSE_DEPTH,
    affected_dimensions,
    assess_causes_consequences,
    chain_findings,
    corrective_action_required,
    normalize_token,
    priority_number,
    priority_ratio,
    suspect_population,
    validate_cause_category,
    validate_cause_chain,
    validate_consequences,
    validate_rating,
    worst_severity,
)


def chain(category="process-control", controllable=True, evidenced=True):
    return [
        {"statement": "bracket hole position outside drawing tolerance", "evidenced": True},
        {"statement": "drill jig located on the wrong datum face", "evidenced": True},
        {
            "statement": "jig setting sheet does not call the datum face",
            "evidenced": evidenced,
            "category": category,
            "controllable": controllable,
        },
    ]


def consequences(**over):
    base = {d: 0 for d in CONSEQUENCE_DIMENSIONS}
    base["function-or-performance"] = 1
    base.update({k.replace("_", "-"): v for k, v in over.items()})
    return base


def units(*extra):
    base = [{"id": "sn-004", "shares_root_condition": True, "raising": True}]
    base.extend(extra)
    return base


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_spacing_normalised(self):
        self.assertEqual(normalize_token("Process Control"), "process-control")

    def test_underscores_normalised(self):
        self.assertEqual(normalize_token("test_or_inspection"), "test-or-inspection")

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("  ")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(3.5)


class CauseCategoryTests(unittest.TestCase):
    def test_taxonomy_member_accepted(self):
        self.assertEqual(validate_cause_category("Supplier"), "supplier")

    def test_person_blame_root_rejected(self):
        with self.assertRaises(ValueError):
            validate_cause_category("operator-error")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_cause_category("bad-luck")


class CauseChainTests(unittest.TestCase):
    def test_valid_chain_returns_one_record_per_level(self):
        levels = validate_cause_chain(chain())
        self.assertEqual(len(levels), MIN_CAUSE_DEPTH)

    def test_root_level_carries_category_and_reach(self):
        root = validate_cause_chain(chain())[-1]
        self.assertEqual(root["category"], "process-control")
        self.assertTrue(root["systemic"])

    def test_item_specific_root_is_not_systemic(self):
        root = validate_cause_chain(chain(category="manufacturing-workmanship"))[-1]
        self.assertFalse(root["systemic"])

    def test_shallow_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_cause_chain(chain()[:2])

    def test_empty_statement_rejected(self):
        bad = chain()
        bad[1]["statement"] = "   "
        with self.assertRaises(ValueError):
            validate_cause_chain(bad)

    def test_non_boolean_evidence_flag_rejected(self):
        bad = chain()
        bad[0]["evidenced"] = "yes"
        with self.assertRaises(ValueError):
            validate_cause_chain(bad)

    def test_root_without_category_rejected(self):
        bad = chain()
        del bad[-1]["category"]
        with self.assertRaises(ValueError):
            validate_cause_chain(bad)

    def test_non_sequence_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_cause_chain({"statement": "x"})

    def test_clean_chain_has_no_findings(self):
        self.assertEqual(chain_findings(validate_cause_chain(chain())), ())

    def test_uncontrollable_root_reported(self):
        findings = chain_findings(validate_cause_chain(chain(controllable=False)))
        self.assertIn("root-cause-not-controllable", findings)

    def test_unevidenced_level_reported_by_index(self):
        findings = chain_findings(validate_cause_chain(chain(evidenced=False)))
        self.assertIn("unevidenced-cause-levels:2", findings)

    def test_empty_level_list_rejected(self):
        with self.assertRaises(ValueError):
            chain_findings([])


class ConsequenceTests(unittest.TestCase):
    def test_full_assessment_accepted(self):
        self.assertEqual(len(validate_consequences(consequences())), len(CONSEQUENCE_DIMENSIONS))

    def test_unassessed_dimension_rejected(self):
        partial = consequences()
        del partial["schedule"]
        with self.assertRaises(ValueError):
            validate_consequences(partial)

    def test_unknown_dimension_rejected(self):
        bad = consequences()
        bad["paperwork-tidiness"] = 1
        with self.assertRaises(ValueError):
            validate_consequences(bad)

    def test_severity_above_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_consequences(consequences(safety=9))

    def test_non_integer_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_consequences(consequences(safety=1.5))

    def test_boolean_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_consequences(consequences(safety=True))

    def test_affected_dimensions_follow_reporting_order(self):
        result = affected_dimensions(consequences(safety=2, schedule=1))
        self.assertEqual(result, ("function-or-performance", "safety", "schedule"))

    def test_worst_severity_is_the_maximum(self):
        self.assertEqual(worst_severity(consequences(safety=3, schedule=2)), 3)

    def test_all_zero_assessment_has_no_affected_dimensions(self):
        clean = {d: 0 for d in CONSEQUENCE_DIMENSIONS}
        self.assertEqual(affected_dimensions(clean), ())
        self.assertEqual(worst_severity(clean), 0)


class RatingAndPriorityTests(unittest.TestCase):
    def test_rating_in_scale_accepted(self):
        self.assertEqual(validate_rating(3, "recurrence"), 3)

    def test_rating_below_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(0, "recurrence")

    def test_rating_above_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(6, "detection")

    def test_boolean_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(True, "detection")

    def test_priority_is_the_integral_product(self):
        self.assertEqual(priority_number(3, 4, 2), 24)

    def test_zero_severity_gives_zero_priority(self):
        self.assertEqual(priority_number(0, 5, 5), 0)

    def test_worst_case_priority_is_the_scale_maximum(self):
        self.assertEqual(priority_number(4, 5, 5), MAX_PRIORITY_NUMBER)

    def test_priority_rejects_severity_off_scale(self):
        with self.assertRaises(ValueError):
            priority_number(5, 1, 1)

    def test_priority_ratio_is_the_share_of_the_worst_case(self):
        self.assertAlmostEqual(priority_ratio(MAX_PRIORITY_NUMBER), 1.0, places=9)

    def test_half_scale_priority_ratio(self):
        self.assertAlmostEqual(priority_ratio(25), 25 / MAX_PRIORITY_NUMBER, places=9)

    def test_priority_ratio_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            priority_ratio(MAX_PRIORITY_NUMBER + 1)


class SuspectPopulationTests(unittest.TestCase):
    def test_item_specific_root_suspects_only_the_raising_unit(self):
        population = units({"id": "sn-005", "shares_root_condition": True, "raising": False})
        self.assertEqual(suspect_population(population, False), ("sn-004",))

    def test_systemic_root_reaches_every_sharing_unit(self):
        population = units({"id": "sn-005", "shares_root_condition": True, "raising": False})
        self.assertEqual(suspect_population(population, True), ("sn-004", "sn-005"))

    def test_systemic_root_spares_a_unit_built_differently(self):
        population = units({"id": "sn-006", "shares_root_condition": False, "raising": False})
        self.assertEqual(suspect_population(population, True), ("sn-004",))

    def test_raising_unit_always_suspect(self):
        population = [{"id": "sn-004", "shares_root_condition": False, "raising": True}]
        self.assertEqual(suspect_population(population, True), ("sn-004",))

    def test_missing_raising_unit_rejected(self):
        population = [{"id": "sn-005", "shares_root_condition": True, "raising": False}]
        with self.assertRaises(ValueError):
            suspect_population(population, True)

    def test_two_raising_units_rejected(self):
        population = units({"id": "sn-005", "shares_root_condition": True, "raising": True})
        with self.assertRaises(ValueError):
            suspect_population(population, True)

    def test_duplicate_unit_rejected(self):
        population = units({"id": "SN 004", "shares_root_condition": True, "raising": False})
        with self.assertRaises(ValueError):
            suspect_population(population, True)

    def test_non_boolean_reach_flag_rejected(self):
        with self.assertRaises(ValueError):
            suspect_population(units(), "yes")

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            suspect_population([], True)


class CorrectiveActionTests(unittest.TestCase):
    def test_quiet_departure_owes_no_corrective_action(self):
        result = corrective_action_required(4, consequences(), False)
        self.assertFalse(result["required"])

    def test_any_safety_consequence_owes_corrective_action(self):
        result = corrective_action_required(4, consequences(safety=1), False)
        self.assertIn("safety-consequence", result["reasons"])

    def test_priority_at_the_threshold_owes_corrective_action(self):
        result = corrective_action_required(CAPA_PRIORITY_THRESHOLD, consequences(), False)
        self.assertIn("priority-at-or-above-threshold", result["reasons"])

    def test_priority_below_the_threshold_alone_does_not(self):
        result = corrective_action_required(CAPA_PRIORITY_THRESHOLD - 1, consequences(), False)
        self.assertFalse(result["required"])

    def test_systemic_root_reaching_other_units_owes_corrective_action(self):
        result = corrective_action_required(2, consequences(other_units=2), True)
        self.assertIn("systemic-root-reaching-other-units", result["reasons"])

    def test_item_specific_root_reaching_other_units_does_not(self):
        result = corrective_action_required(2, consequences(other_units=2), False)
        self.assertFalse(result["required"])

    def test_non_boolean_reach_rejected(self):
        with self.assertRaises(ValueError):
            corrective_action_required(2, consequences(), 1)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "cause_chain": chain(),
            "consequences": consequences(),
            "recurrence": 2,
            "detection": 2,
            "units": units(),
        }
        spec.update(over)
        return spec

    def test_clean_analysis_is_complete(self):
        result = assess_causes_consequences(self._spec())
        self.assertTrue(result["analysis_complete"])
        self.assertEqual(result["chain_findings"], ())

    def test_root_category_and_reach_reported(self):
        result = assess_causes_consequences(self._spec())
        self.assertEqual(result["root_category"], "process-control")
        self.assertTrue(result["root_systemic"])

    def test_priority_follows_the_worst_dimension(self):
        result = assess_causes_consequences(
            self._spec(consequences=consequences(schedule=3), recurrence=3, detection=4)
        )
        self.assertEqual(result["worst_severity"], 3)
        self.assertEqual(result["priority_number"], 36)

    def test_unevidenced_root_leaves_the_analysis_incomplete(self):
        result = assess_causes_consequences(self._spec(cause_chain=chain(evidenced=False)))
        self.assertFalse(result["analysis_complete"])

    def test_systemic_root_widens_the_suspect_population(self):
        population = units({"id": "sn-005", "shares_root_condition": True, "raising": False})
        result = assess_causes_consequences(self._spec(units=population))
        self.assertEqual(result["suspect_units"], ("sn-004", "sn-005"))
        self.assertTrue(
            any(f.startswith("suspect-population-beyond") for f in result["chain_findings"])
        )

    def test_corrective_action_reported_with_reasons(self):
        result = assess_causes_consequences(self._spec(consequences=consequences(safety=2)))
        self.assertTrue(result["corrective_action"]["required"])
        self.assertIn("safety-consequence", result["corrective_action"]["reasons"])

    def test_priority_ratio_matches_the_priority_number(self):
        result = assess_causes_consequences(self._spec())
        self.assertAlmostEqual(
            result["priority_ratio"],
            result["priority_number"] / MAX_PRIORITY_NUMBER,
            places=9,
        )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["units"]
        with self.assertRaises(ValueError):
            assess_causes_consequences(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_causes_consequences(["cause_chain"])


if __name__ == "__main__":
    unittest.main()
