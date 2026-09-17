"""Contract tests for the clause 6.2.3.1 Class 3 evaluation-necessity logic."""

import unittest

from q60_class_3_evaluation_general_requirements_logic import (
    ALWAYS_OWED_ELEMENTS,
    APPLICATION_SEVERITY,
    DECISION_TOLERANCE,
    EVALUATION_NOT_REQUIRED,
    FULL_EVALUATION_REQUIRED,
    FULL_EVALUATION_THRESHOLD,
    REDUCED_EVALUATION_REQUIRED,
    REDUCED_EVALUATION_THRESHOLD,
    TOTAL_TRIGGER_WEIGHT,
    TRIGGER_CONDITIONS,
    TRIGGER_ELEMENTS,
    apply_waivers,
    assess_evaluation_necessity,
    is_hard_trigger,
    necessity_index,
    outstanding_elements,
    severity_multiplier,
    trigger_weight,
    validate_declared_triggers,
    validate_trigger_id,
)

SOFT_TRIGGERS = [
    name for name, entry in TRIGGER_CONDITIONS.items() if not entry["hard"]
]
HARD_TRIGGERS = [name for name, entry in TRIGGER_CONDITIONS.items() if entry["hard"]]


def _case(**overrides):
    case = {
        "manufacturer": "Example Semiconductor",
        "part_number": "EX-4410-C3",
        "application_severity": "standard",
        "declared_triggers": ["technology-new-to-the-project"],
        "waivers": [],
    }
    case.update(overrides)
    return case


class TriggerCatalogueTests(unittest.TestCase):
    def test_every_trigger_carries_a_positive_weight(self):
        for name in TRIGGER_CONDITIONS:
            self.assertGreater(trigger_weight(name), 0.0)

    def test_every_trigger_owes_at_least_one_element(self):
        for name in TRIGGER_CONDITIONS:
            self.assertTrue(TRIGGER_ELEMENTS[name])

    def test_total_weight_matches_the_catalogue(self):
        self.assertAlmostEqual(
            TOTAL_TRIGGER_WEIGHT,
            sum(entry["weight"] for entry in TRIGGER_CONDITIONS.values()),
            places=9,
        )

    def test_hard_and_soft_triggers_both_exist(self):
        self.assertTrue(HARD_TRIGGERS)
        self.assertTrue(SOFT_TRIGGERS)

    def test_missing_qualification_is_a_hard_trigger(self):
        self.assertTrue(
            is_hard_trigger("no-qualification-against-accepted-specification")
        )

    def test_unknown_lot_history_is_a_soft_trigger(self):
        self.assertFalse(is_hard_trigger("single-lot-procurement-with-no-lot-history"))

    def test_unknown_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_trigger_id("part-looks-cheap")

    def test_blank_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_trigger_id("   ")

    def test_duplicate_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_triggers(
                ["radiation-behaviour-unknown", "radiation-behaviour-unknown"]
            )

    def test_non_sequence_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_triggers("radiation-behaviour-unknown")


class SeverityTests(unittest.TestCase):
    def test_standard_application_is_neutral(self):
        self.assertAlmostEqual(severity_multiplier("standard"), 1.0, places=9)

    def test_critical_application_opens_the_index_out(self):
        self.assertGreater(severity_multiplier("mission-critical"), 1.0)

    def test_non_critical_application_pulls_the_index_in(self):
        self.assertLess(severity_multiplier("non-critical"), 1.0)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            severity_multiplier("quite-important")

    def test_every_declared_severity_is_positive(self):
        for value in APPLICATION_SEVERITY.values():
            self.assertGreater(value, 0.0)


class NecessityIndexTests(unittest.TestCase):
    def test_no_unknowns_leave_a_zero_index(self):
        self.assertAlmostEqual(necessity_index([]), 0.0, places=9)

    def test_every_soft_trigger_lands_exactly_on_the_full_threshold(self):
        self.assertAlmostEqual(
            necessity_index(SOFT_TRIGGERS, "standard"),
            FULL_EVALUATION_THRESHOLD,
            places=9,
        )

    def test_index_is_capped_at_unity(self):
        self.assertAlmostEqual(
            necessity_index(list(TRIGGER_CONDITIONS), "mission-critical"),
            1.0,
            places=9,
        )

    def test_severity_scales_the_index(self):
        base = necessity_index(SOFT_TRIGGERS, "standard")
        low = necessity_index(SOFT_TRIGGERS, "non-critical")
        self.assertAlmostEqual(low, base * 0.80, places=9)

    def test_index_grows_with_each_further_unknown(self):
        one = necessity_index(SOFT_TRIGGERS[:1])
        two = necessity_index(SOFT_TRIGGERS[:2])
        self.assertGreater(two, one)

    def test_unknown_trigger_in_the_index_rejected(self):
        with self.assertRaises(ValueError):
            necessity_index(["the-vendor-seems-fine"])

    def test_thresholds_are_ordered(self):
        self.assertGreater(FULL_EVALUATION_THRESHOLD, REDUCED_EVALUATION_THRESHOLD)

    def test_decision_tolerance_is_representation_sized_only(self):
        self.assertLess(DECISION_TOLERANCE, 1e-6)


class WaiverTests(unittest.TestCase):
    def test_justified_waiver_on_a_soft_trigger_is_granted(self):
        result = apply_waivers(
            ["radiation-behaviour-unknown"],
            [
                {
                    "trigger": "radiation-behaviour-unknown",
                    "justification": "the part sits behind a shielded bulkhead",
                }
            ],
        )
        self.assertEqual(result["remaining"], [])
        self.assertEqual(len(result["granted"]), 1)

    def test_waiver_on_a_hard_trigger_is_refused(self):
        result = apply_waivers(
            ["manufacturing-line-not-identified"],
            [
                {
                    "trigger": "manufacturing-line-not-identified",
                    "justification": "the distributor assures us it is one line",
                }
            ],
        )
        self.assertEqual(result["remaining"], ["manufacturing-line-not-identified"])
        self.assertEqual(result["refused"][0]["reason"], "hard-trigger-cannot-be-waived")

    def test_unjustified_waiver_is_refused(self):
        result = apply_waivers(
            ["radiation-behaviour-unknown"],
            [{"trigger": "radiation-behaviour-unknown", "justification": "  "}],
        )
        self.assertEqual(result["remaining"], ["radiation-behaviour-unknown"])
        self.assertEqual(result["refused"][0]["reason"], "no-written-justification")

    def test_waiver_against_an_undeclared_trigger_rejected(self):
        with self.assertRaises(ValueError):
            apply_waivers(
                ["radiation-behaviour-unknown"],
                [{"trigger": "no-traceability-to-a-date-code", "justification": "x"}],
            )

    def test_the_same_trigger_waived_twice_rejected(self):
        with self.assertRaises(ValueError):
            apply_waivers(
                ["radiation-behaviour-unknown"],
                [
                    {"trigger": "radiation-behaviour-unknown", "justification": "a"},
                    {"trigger": "radiation-behaviour-unknown", "justification": "b"},
                ],
            )

    def test_non_mapping_waiver_rejected(self):
        with self.assertRaises(ValueError):
            apply_waivers(["radiation-behaviour-unknown"], ["just trust us"])

    def test_absent_waiver_list_is_allowed(self):
        result = apply_waivers(["radiation-behaviour-unknown"], None)
        self.assertEqual(result["remaining"], ["radiation-behaviour-unknown"])

    def test_every_refusal_is_named_not_only_the_first(self):
        result = apply_waivers(
            ["manufacturing-line-not-identified", "radiation-behaviour-unknown"],
            [
                {"trigger": "manufacturing-line-not-identified", "justification": "a"},
                {"trigger": "radiation-behaviour-unknown", "justification": ""},
            ],
        )
        self.assertEqual(len(result["findings"]), 2)


class OutstandingElementTests(unittest.TestCase):
    def test_no_evaluation_owes_nothing(self):
        self.assertEqual(outstanding_elements([], EVALUATION_NOT_REQUIRED), [])

    def test_reduced_programme_still_owes_the_line_elements(self):
        owed = outstanding_elements(
            ["radiation-behaviour-unknown"], REDUCED_EVALUATION_REQUIRED
        )
        for element in ALWAYS_OWED_ELEMENTS:
            self.assertIn(element, owed)

    def test_reduced_programme_owes_the_element_its_trigger_names(self):
        owed = outstanding_elements(
            ["radiation-behaviour-unknown"], REDUCED_EVALUATION_REQUIRED
        )
        self.assertIn("radiation-behaviour-assessment", owed)

    def test_full_programme_owes_testing_and_lot_homogeneity(self):
        owed = outstanding_elements([], FULL_EVALUATION_REQUIRED)
        self.assertIn("evaluation-testing", owed)
        self.assertIn("lot-homogeneity-check", owed)

    def test_elements_are_returned_without_repeats(self):
        owed = outstanding_elements(SOFT_TRIGGERS, FULL_EVALUATION_REQUIRED)
        self.assertEqual(len(owed), len(set(owed)))

    def test_unknown_decision_rejected(self):
        with self.assertRaises(ValueError):
            outstanding_elements([], "probably-fine")


class DecisionTests(unittest.TestCase):
    def test_no_unknown_means_no_evaluation(self):
        result = assess_evaluation_necessity(_case(declared_triggers=[]))
        self.assertEqual(result["decision"], EVALUATION_NOT_REQUIRED)
        self.assertFalse(result["evaluation_required"])
        self.assertEqual(result["findings"], [])

    def test_one_hard_trigger_forces_the_full_programme(self):
        result = assess_evaluation_necessity(
            _case(declared_triggers=["manufacturing-line-not-identified"])
        )
        self.assertEqual(result["decision"], FULL_EVALUATION_REQUIRED)
        self.assertEqual(result["decision_driver"], "hard-trigger")

    def test_a_hard_trigger_beats_a_low_index(self):
        result = assess_evaluation_necessity(
            _case(
                declared_triggers=["manufacturing-line-not-identified"],
                application_severity="non-critical",
            )
        )
        self.assertLess(result["necessity_index"], FULL_EVALUATION_THRESHOLD)
        self.assertEqual(result["decision"], FULL_EVALUATION_REQUIRED)

    def test_two_soft_unknowns_reach_the_reduced_programme(self):
        result = assess_evaluation_necessity(
            _case(
                declared_triggers=[
                    "technology-new-to-the-project",
                    "package-or-die-change-notified",
                ]
            )
        )
        self.assertEqual(result["decision"], REDUCED_EVALUATION_REQUIRED)

    def test_every_soft_unknown_reaches_the_full_programme(self):
        result = assess_evaluation_necessity(_case(declared_triggers=SOFT_TRIGGERS))
        self.assertEqual(result["decision"], FULL_EVALUATION_REQUIRED)
        self.assertEqual(result["decision_driver"], "necessity-index")

    def test_a_milder_application_can_pull_a_full_programme_back(self):
        result = assess_evaluation_necessity(
            _case(declared_triggers=SOFT_TRIGGERS, application_severity="non-critical")
        )
        self.assertEqual(result["decision"], REDUCED_EVALUATION_REQUIRED)

    def test_a_critical_application_can_push_a_reduced_programme_up(self):
        triggers = SOFT_TRIGGERS[:4]
        standard = assess_evaluation_necessity(_case(declared_triggers=triggers))
        critical = assess_evaluation_necessity(
            _case(declared_triggers=triggers, application_severity="mission-critical")
        )
        self.assertEqual(standard["decision"], REDUCED_EVALUATION_REQUIRED)
        self.assertEqual(critical["decision"], FULL_EVALUATION_REQUIRED)

    def test_a_justified_waiver_can_close_the_last_soft_unknown(self):
        result = assess_evaluation_necessity(
            _case(
                declared_triggers=["technology-new-to-the-project"],
                waivers=[
                    {
                        "trigger": "technology-new-to-the-project",
                        "justification": "the same die flew on the previous build",
                    }
                ],
            )
        )
        self.assertEqual(result["decision"], EVALUATION_NOT_REQUIRED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_refused_waiver_leaves_the_unknown_open(self):
        result = assess_evaluation_necessity(
            _case(
                declared_triggers=["no-qualification-against-accepted-specification"],
                waivers=[
                    {
                        "trigger": "no-qualification-against-accepted-specification",
                        "justification": "the buyer signed it off",
                    }
                ],
            )
        )
        self.assertEqual(result["decision"], FULL_EVALUATION_REQUIRED)
        self.assertEqual(len(result["waivers_refused"]), 1)

    def test_the_outstanding_programme_comes_back_with_the_decision(self):
        result = assess_evaluation_necessity(
            _case(declared_triggers=["radiation-behaviour-unknown",
                                     "package-or-die-change-notified"])
        )
        self.assertIn("radiation-behaviour-assessment", result["outstanding_elements"])
        self.assertIn("constructional-analysis", result["outstanding_elements"])

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_necessity(_case(part_number=""))

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_necessity(_case(manufacturer="   "))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_necessity(["EX-4410-C3"])

    def test_severity_defaults_to_standard(self):
        case = _case()
        del case["application_severity"]
        result = assess_evaluation_necessity(case)
        self.assertEqual(result["application_severity"], "standard")

    def test_open_hard_triggers_are_all_named(self):
        result = assess_evaluation_necessity(_case(declared_triggers=HARD_TRIGGERS))
        self.assertEqual(sorted(result["hard_triggers_open"]), sorted(HARD_TRIGGERS))
        self.assertEqual(len(result["findings"]), len(HARD_TRIGGERS))


if __name__ == "__main__":
    unittest.main()
