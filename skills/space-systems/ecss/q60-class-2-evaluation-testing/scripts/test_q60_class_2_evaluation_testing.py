"""Contract test for the ECSS-Q-ST-60C clause 5.2.3.4 Class 2 test-programme leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_2_evaluation_testing.py
"""

import unittest

from q60_class_2_evaluation_testing_logic import (
    ACTIVE_FAMILIES,
    ALWAYS_REQUIRED_TESTS,
    CONDITION_TOLERANCE,
    CONDITIONAL_TESTS,
    LIFE_TEST_MISSION_MONTHS,
    PRIOR_TEST_VALIDITY_MONTHS,
    TEST_CATALOGUE,
    TID_TRIGGER_KRAD,
    determine_class_2_test_programme,
    normalize_prior_tests,
    normalize_use_context,
    not_required_tests,
    prior_test_credit,
    required_test_programme,
    triggered_tests,
)


def benign_context(**overrides):
    """A short benign mission that triggers as little as possible."""
    context = {
        "part_family": "passive-component",
        "package_type": "bare-die-or-chip-scale",
        "termination_finish": "tin-lead-solder-coated",
        "mission_duration_months": 12.0,
        "required_operating_span_k": 80.0,
        "characterised_operating_span_k": 125.0,
        "mission_total_dose_krad": 0.5,
        "particle_environment": False,
        "covered_by_higher_level_assembly_test": True,
    }
    context.update(overrides)
    return context


def triggered_names(context):
    return [name for name, _ in triggered_tests(context)]


def run_case(context=None, prior_tests=None, part_id="u22-op27", lot="lot-2431"):
    return determine_class_2_test_programme(
        part_id,
        lot,
        benign_context() if context is None else context,
        [] if prior_tests is None else prior_tests,
    )


class CatalogueTests(unittest.TestCase):
    def test_the_core_and_the_conditional_items_do_not_overlap(self):
        self.assertEqual(set(ALWAYS_REQUIRED_TESTS) & set(CONDITIONAL_TESTS), set())

    def test_the_catalogue_is_the_core_plus_the_conditional_items(self):
        self.assertEqual(
            set(TEST_CATALOGUE), set(ALWAYS_REQUIRED_TESTS) | set(CONDITIONAL_TESTS)
        )

    def test_the_catalogue_has_no_repeated_entry(self):
        self.assertEqual(len(TEST_CATALOGUE), len(set(TEST_CATALOGUE)))

    def test_every_active_family_is_a_known_family(self):
        for family in ACTIVE_FAMILIES:
            normalize_use_context(benign_context(part_family=family))


class CoreProgrammeTests(unittest.TestCase):
    def test_the_core_is_owed_even_by_the_most_benign_part(self):
        programme = required_test_programme(benign_context())
        names = [item["test"] for item in programme]
        for name in ALWAYS_REQUIRED_TESTS:
            self.assertIn(name, names)

    def test_every_core_item_is_marked_as_always_required(self):
        programme = required_test_programme(benign_context())
        for item in programme:
            if item["test"] in ALWAYS_REQUIRED_TESTS:
                self.assertEqual(item["basis"], "always-required")

    def test_every_triggered_item_carries_the_condition_that_asked_for_it(self):
        programme = required_test_programme(
            benign_context(package_type="plastic-encapsulated")
        )
        triggered = [i for i in programme if i["basis"] == "condition-triggered"]
        self.assertTrue(triggered)
        for item in triggered:
            self.assertTrue(item["reason"])


class TriggerTests(unittest.TestCase):
    def test_a_benign_short_mission_triggers_nothing(self):
        self.assertEqual(triggered_names(benign_context()), [])

    def test_a_mission_on_the_endurance_trigger_does_not_ask_for_a_life_test(self):
        duration = LIFE_TEST_MISSION_MONTHS
        self.assertAlmostEqual(duration, LIFE_TEST_MISSION_MONTHS, places=9)
        self.assertNotIn(
            "endurance-life-test",
            triggered_names(benign_context(mission_duration_months=duration)),
        )

    def test_a_mission_past_the_endurance_trigger_asks_for_a_life_test(self):
        self.assertIn(
            "endurance-life-test",
            triggered_names(
                benign_context(
                    mission_duration_months=LIFE_TEST_MISSION_MONTHS + 12.0
                )
            ),
        )

    def test_a_dose_on_the_radiation_trigger_asks_for_nothing(self):
        dose = TID_TRIGGER_KRAD
        self.assertAlmostEqual(dose, TID_TRIGGER_KRAD, places=9)
        self.assertNotIn(
            "total-ionising-dose-characterisation",
            triggered_names(benign_context(mission_total_dose_krad=dose)),
        )

    def test_a_dose_above_the_radiation_trigger_asks_for_characterisation(self):
        self.assertIn(
            "total-ionising-dose-characterisation",
            triggered_names(
                benign_context(mission_total_dose_krad=TID_TRIGGER_KRAD + 9.0)
            ),
        )

    def test_a_particle_environment_only_reaches_an_active_technology(self):
        passive = benign_context(particle_environment=True)
        active = benign_context(
            particle_environment=True, part_family="monolithic-integrated-circuit"
        )
        self.assertNotIn(
            "single-event-effects-characterisation", triggered_names(passive)
        )
        self.assertIn("single-event-effects-characterisation", triggered_names(active))

    def test_an_operating_span_inside_what_was_characterised_asks_for_nothing(self):
        self.assertNotIn(
            "electrical-characterisation-over-temperature-extremes",
            triggered_names(benign_context()),
        )

    def test_an_operating_span_equal_to_the_characterised_one_asks_for_nothing(self):
        span = 125.0
        context = benign_context(
            required_operating_span_k=span, characterised_operating_span_k=span
        )
        self.assertAlmostEqual(span, 125.0, places=9)
        self.assertNotIn(
            "electrical-characterisation-over-temperature-extremes",
            triggered_names(context),
        )

    def test_an_operating_span_beyond_the_characterised_one_asks_for_extremes(self):
        self.assertIn(
            "electrical-characterisation-over-temperature-extremes",
            triggered_names(
                benign_context(
                    required_operating_span_k=175.0,
                    characterised_operating_span_k=125.0,
                )
            ),
        )

    def test_a_sealed_cavity_package_asks_for_a_seal_test(self):
        self.assertIn(
            "hermeticity-and-seal-test",
            triggered_names(benign_context(package_type="hermetic-metal-or-ceramic")),
        )

    def test_a_plastic_package_asks_for_moisture_preconditioning_instead(self):
        names = triggered_names(benign_context(package_type="plastic-encapsulated"))
        self.assertIn("moisture-sensitivity-and-preconditioning-bake", names)
        self.assertNotIn("hermeticity-and-seal-test", names)

    def test_a_pure_tin_finish_asks_for_whisker_mitigation(self):
        self.assertIn(
            "tin-whisker-mitigation-assessment",
            triggered_names(benign_context(termination_finish="pure-tin")),
        )

    def test_a_gold_finish_asks_for_an_embrittlement_assessment_instead(self):
        names = triggered_names(benign_context(termination_finish="gold-plated"))
        self.assertIn("gold-embrittlement-assessment", names)
        self.assertNotIn("tin-whisker-mitigation-assessment", names)

    def test_a_hybrid_asks_for_internal_interconnect_strength(self):
        self.assertIn(
            "wire-bond-and-die-shear-strength-test",
            triggered_names(benign_context(part_family="hybrid-microcircuit")),
        )

    def test_a_mechanical_environment_nobody_covered_higher_up_is_owed_here(self):
        self.assertIn(
            "mechanical-shock-and-vibration-test",
            triggered_names(
                benign_context(covered_by_higher_level_assembly_test=False)
            ),
        )

    def test_what_nothing_triggered_is_reported_as_not_required(self):
        absent = not_required_tests(benign_context())
        self.assertIn("endurance-life-test", absent)
        self.assertIn("hermeticity-and-seal-test", absent)

    def test_the_triggered_and_not_required_sets_partition_the_conditional_items(self):
        context = benign_context(package_type="plastic-encapsulated")
        asked = set(triggered_names(context))
        absent = set(not_required_tests(context))
        self.assertEqual(asked & absent, set())
        self.assertEqual(asked | absent, set(CONDITIONAL_TESTS))


class UseContextValidationTests(unittest.TestCase):
    def test_an_unknown_part_family_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context(benign_context(part_family="widget"))

    def test_an_unknown_package_type_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context(benign_context(package_type="a-black-blob"))

    def test_an_unknown_termination_finish_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context(benign_context(termination_finish="shiny"))

    def test_a_negative_mission_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context(benign_context(mission_duration_months=-1.0))

    def test_a_non_positive_operating_span_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context(benign_context(required_operating_span_k=0.0))

    def test_a_negative_mission_dose_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context(benign_context(mission_total_dose_krad=-0.1))

    def test_a_missing_particle_environment_flag_is_rejected(self):
        context = benign_context()
        del context["particle_environment"]
        with self.assertRaises(ValueError):
            normalize_use_context(context)

    def test_a_non_mapping_context_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_use_context("a resistor in low earth orbit")


class PriorTestCreditTests(unittest.TestCase):
    def test_a_same_lot_record_inside_validity_carries(self):
        records = normalize_prior_tests(
            [
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2431",
                    "age_months": 6.0,
                }
            ]
        )
        carries, reasons = prior_test_credit(records[0], "lot-2431")
        self.assertTrue(carries)
        self.assertEqual(reasons, [])

    def test_a_record_on_the_validity_limit_still_carries(self):
        records = normalize_prior_tests(
            [
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2431",
                    "age_months": PRIOR_TEST_VALIDITY_MONTHS,
                }
            ]
        )
        carries, reasons = prior_test_credit(records[0], "lot-2431")
        self.assertTrue(carries)

    def test_a_record_past_the_validity_limit_falls(self):
        records = normalize_prior_tests(
            [
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2431",
                    "age_months": PRIOR_TEST_VALIDITY_MONTHS + 1.0,
                }
            ]
        )
        carries, reasons = prior_test_credit(records[0], "lot-2431")
        self.assertFalse(carries)
        self.assertIn("prior-test-outside-validity-window", reasons)

    def test_a_record_from_another_lot_never_carries(self):
        records = normalize_prior_tests(
            [
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2299",
                    "age_months": 1.0,
                }
            ]
        )
        carries, reasons = prior_test_credit(records[0], "lot-2431")
        self.assertFalse(carries)
        self.assertIn("prior-test-from-another-procurement-lot", reasons)

    def test_every_broken_credit_rule_is_named_at_once(self):
        records = normalize_prior_tests(
            [
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2299",
                    "age_months": PRIOR_TEST_VALIDITY_MONTHS + 24.0,
                }
            ]
        )
        carries, reasons = prior_test_credit(records[0], "lot-2431")
        self.assertEqual(len(reasons), 2)

    def test_an_unknown_test_name_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_prior_tests(
                [{"test": "we-plugged-it-in", "procurement_lot": "lot-2431", "age_months": 1.0}]
            )

    def test_a_negative_record_age_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_prior_tests(
                [
                    {
                        "test": "external-visual-inspection",
                        "procurement_lot": "lot-2431",
                        "age_months": -1.0,
                    }
                ]
            )

    def test_a_non_sequence_prior_test_list_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_prior_tests({"test": "external-visual-inspection"})


class ProgrammeReportTests(unittest.TestCase):
    def test_a_benign_part_still_owes_the_core(self):
        report = run_case()
        self.assertEqual(report["programme_size"], len(ALWAYS_REQUIRED_TESTS))
        self.assertEqual(report["outstanding_tests"], list(ALWAYS_REQUIRED_TESTS))
        self.assertFalse(report["evaluation_testing_complete"])

    def test_a_demanding_mission_grows_the_programme(self):
        report = run_case(
            benign_context(
                part_family="monolithic-integrated-circuit",
                package_type="plastic-encapsulated",
                termination_finish="pure-tin",
                mission_duration_months=84.0,
                required_operating_span_k=175.0,
                mission_total_dose_krad=30.0,
                particle_environment=True,
                covered_by_higher_level_assembly_test=False,
            )
        )
        self.assertGreater(report["programme_size"], len(ALWAYS_REQUIRED_TESTS))
        for name in (
            "endurance-life-test",
            "total-ionising-dose-characterisation",
            "single-event-effects-characterisation",
            "tin-whisker-mitigation-assessment",
            "mechanical-shock-and-vibration-test",
        ):
            self.assertIn(name, report["required_test_names"])

    def test_a_carrying_prior_test_leaves_the_item_covered(self):
        report = run_case(
            prior_tests=[
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2431",
                    "age_months": 3.0,
                }
            ]
        )
        self.assertIn("external-visual-inspection", report["covered_by_prior_testing"])
        self.assertNotIn("external-visual-inspection", report["outstanding_tests"])

    def test_a_record_from_another_lot_leaves_the_item_outstanding(self):
        report = run_case(
            prior_tests=[
                {
                    "test": "external-visual-inspection",
                    "procurement_lot": "lot-2299",
                    "age_months": 3.0,
                }
            ]
        )
        self.assertIn("external-visual-inspection", report["outstanding_tests"])
        self.assertIn(
            "prior-test-does-not-carry-credit",
            [f["finding"] for f in report["findings"]],
        )

    def test_credit_offered_for_an_item_nobody_asked_for_is_a_finding(self):
        report = run_case(
            prior_tests=[
                {
                    "test": "hermeticity-and-seal-test",
                    "procurement_lot": "lot-2431",
                    "age_months": 1.0,
                }
            ]
        )
        self.assertIn(
            "prior-test-not-in-the-required-programme",
            [f["finding"] for f in report["findings"]],
        )
        self.assertNotIn("hermeticity-and-seal-test", report["covered_by_prior_testing"])

    def test_a_fully_covered_programme_reports_itself_complete(self):
        prior = [
            {"test": name, "procurement_lot": "lot-2431", "age_months": 2.0}
            for name in ALWAYS_REQUIRED_TESTS
        ]
        report = run_case(prior_tests=prior)
        self.assertEqual(report["outstanding_tests"], [])
        self.assertTrue(report["evaluation_testing_complete"])

    def test_delegating_the_mechanical_programme_upward_is_recorded(self):
        report = run_case()
        self.assertIn(
            "mechanical-programme-delegated-to-higher-level-assembly",
            [f["finding"] for f in report["findings"]],
        )

    def test_an_empty_part_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run_case(part_id="   ")

    def test_an_empty_procurement_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            run_case(lot="")

    def test_tolerance_is_small_enough_to_separate_the_triggers(self):
        self.assertLess(CONDITION_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
