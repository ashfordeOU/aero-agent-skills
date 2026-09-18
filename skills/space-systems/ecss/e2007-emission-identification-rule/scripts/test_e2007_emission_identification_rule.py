#!/usr/bin/env python3
"""Contract test for the emission identification rule leaf."""

import unittest

from e2007_emission_identification_rule_logic import (
    RECOGNIZED_CHARACTERS,
    assess_emission_survey,
    bandwidth_level_error_db,
    character_neutrality_audit,
    evaluate_emission,
    exceeds_limit,
    is_prescribed_bandwidth,
    normalize_character,
    reportable_emissions,
)


def good_emission(**overrides):
    emission = {
        "id": "E-1",
        "frequency_hz": 1.0e8,
        "character": "narrowband",
        "prescribed_bandwidth_hz": 1.0e5,
        "applied_bandwidth_hz": 1.0e5,
        "level_dbuv": 30.0,
        "limit_dbuv": 40.0,
    }
    emission.update(overrides)
    return emission


def survey():
    return [
        good_emission(id="E-1", character="narrowband"),
        good_emission(id="E-2", character="broadband", frequency_hz=1.1e8),
        good_emission(id="E-3", character="impulsive", frequency_hz=1.2e8),
    ]


class TestNormalizeCharacter(unittest.TestCase):
    def test_canonical_spelling_survives(self):
        self.assertEqual(normalize_character("broadband"), "broadband")

    def test_hyphenated_spelling_is_folded(self):
        self.assertEqual(normalize_character("Broad-Band"), "broadband")

    def test_spaced_spelling_is_folded(self):
        self.assertEqual(normalize_character(" narrow band "), "narrowband")

    def test_unknown_folds_to_undetermined(self):
        self.assertEqual(normalize_character("unknown"), "undetermined")

    def test_every_recognized_character_round_trips(self):
        for character in RECOGNIZED_CHARACTERS:
            self.assertEqual(normalize_character(character), character)

    def test_unrecognized_character_raises(self):
        with self.assertRaises(ValueError):
            normalize_character("spurious")

    def test_blank_character_raises(self):
        with self.assertRaises(ValueError):
            normalize_character("   ")

    def test_non_string_character_raises(self):
        with self.assertRaises(ValueError):
            normalize_character(7)


class TestBandwidthComparison(unittest.TestCase):
    def test_equal_bandwidth_is_prescribed(self):
        self.assertTrue(is_prescribed_bandwidth(1.0e5, 1.0e5))

    def test_last_place_difference_is_still_prescribed(self):
        self.assertTrue(is_prescribed_bandwidth(1.0e5 * (1.0 + 1.0e-13), 1.0e5))

    def test_wider_bandwidth_is_not_prescribed(self):
        self.assertFalse(is_prescribed_bandwidth(1.0e6, 1.0e5))

    def test_zero_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            is_prescribed_bandwidth(0.0, 1.0e5)

    def test_decade_wider_bandwidth_costs_twenty_decibels(self):
        self.assertAlmostEqual(bandwidth_level_error_db(1.0e5, 1.0e4), 20.0, places=9)

    def test_decade_narrower_bandwidth_costs_minus_twenty(self):
        self.assertAlmostEqual(bandwidth_level_error_db(1.0e3, 1.0e4), -20.0, places=9)

    def test_matched_bandwidth_carries_no_level_error(self):
        self.assertAlmostEqual(bandwidth_level_error_db(1.0e4, 1.0e4), 0.0, places=12)

    def test_negative_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            bandwidth_level_error_db(-1.0e4, 1.0e4)


class TestExceedsLimit(unittest.TestCase):
    def test_level_below_limit_does_not_exceed(self):
        self.assertFalse(exceeds_limit(30.0, 40.0))

    def test_level_above_limit_exceeds(self):
        self.assertTrue(exceeds_limit(50.0, 40.0))

    def test_level_exactly_at_limit_does_not_exceed(self):
        self.assertFalse(exceeds_limit(40.0, 40.0))

    def test_last_place_overshoot_does_not_exceed(self):
        self.assertFalse(exceeds_limit(40.0 + 1.0e-12, 40.0))

    def test_non_numeric_level_raises(self):
        with self.assertRaises(ValueError):
            exceeds_limit("40", 40.0)


class TestEvaluateEmission(unittest.TestCase):
    def test_conforming_emission_has_no_finding(self):
        record = evaluate_emission(good_emission())
        self.assertTrue(record["conforming"])
        self.assertTrue(record["as_prescribed"])

    def test_character_does_not_change_the_bandwidth_verdict(self):
        narrow = evaluate_emission(good_emission(character="narrowband"))
        broad = evaluate_emission(good_emission(character="broadband"))
        self.assertEqual(narrow["as_prescribed"], broad["as_prescribed"])
        self.assertAlmostEqual(
            narrow["bandwidth_level_error_db"],
            broad["bandwidth_level_error_db"],
            places=12,
        )

    def test_character_does_not_change_the_limit_verdict(self):
        narrow = evaluate_emission(
            good_emission(character="narrowband", level_dbuv=50.0)
        )
        broad = evaluate_emission(
            good_emission(character="broadband", level_dbuv=50.0)
        )
        self.assertTrue(narrow["exceeds_limit"])
        self.assertEqual(narrow["exceeds_limit"], broad["exceeds_limit"])

    def test_substituted_bandwidth_is_a_finding(self):
        record = evaluate_emission(good_emission(applied_bandwidth_hz=1.0e6))
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("bandwidth-not-as-prescribed", codes)
        self.assertAlmostEqual(record["bandwidth_level_error_db"], 20.0, places=9)

    def test_omission_on_character_grounds_is_a_finding(self):
        record = evaluate_emission(
            good_emission(omitted_reason="judged broadband", reported=False)
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("character-based-omission", codes)

    def test_unreported_exceedance_is_a_finding(self):
        record = evaluate_emission(good_emission(level_dbuv=55.0, reported=False))
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("emission-not-reported", codes)

    def test_reported_exceedance_is_not_a_finding(self):
        record = evaluate_emission(good_emission(level_dbuv=55.0, reported=True))
        self.assertTrue(record["exceeds_limit"])
        self.assertEqual(record["findings"], [])

    def test_limit_is_optional_and_leaves_the_grade_open(self):
        emission = good_emission()
        del emission["limit_dbuv"]
        record = evaluate_emission(emission)
        self.assertIsNone(record["exceeds_limit"])
        self.assertTrue(record["conforming"])

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            evaluate_emission(good_emission(detector="quasi-peak"))

    def test_missing_required_key_raises(self):
        emission = good_emission()
        del emission["applied_bandwidth_hz"]
        with self.assertRaises(ValueError):
            evaluate_emission(emission)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_emission(good_emission(id="  "))

    def test_non_boolean_reported_raises(self):
        with self.assertRaises(ValueError):
            evaluate_emission(good_emission(reported="no"))

    def test_blank_omitted_reason_raises(self):
        with self.assertRaises(ValueError):
            evaluate_emission(good_emission(omitted_reason="  "))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            evaluate_emission(["E-1"])

    def test_findings_carry_code_subject_and_detail(self):
        record = evaluate_emission(good_emission(applied_bandwidth_hz=1.0e6))
        for finding in record["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


class TestCharacterNeutralityAudit(unittest.TestCase):
    def test_uniform_survey_is_neutral(self):
        audit = character_neutrality_audit(
            [evaluate_emission(e) for e in survey()]
        )
        self.assertTrue(audit["neutral"])
        self.assertEqual(audit["character_count"], 3)

    def test_character_driven_bandwidth_is_caught(self):
        emissions = [
            good_emission(id="E-1", character="narrowband"),
            good_emission(id="E-2", character="narrowband"),
            good_emission(
                id="E-3", character="broadband", applied_bandwidth_hz=1.0e6
            ),
            good_emission(
                id="E-4", character="broadband", applied_bandwidth_hz=1.0e6
            ),
        ]
        audit = character_neutrality_audit(
            [evaluate_emission(e) for e in emissions]
        )
        codes = [finding["code"] for finding in audit["findings"]]
        self.assertIn("character-dependent-bandwidth", codes)
        self.assertFalse(audit["neutral"])

    def test_a_survey_that_deviates_everywhere_is_not_character_driven(self):
        emissions = [
            good_emission(id="E-1", character="narrowband", applied_bandwidth_hz=1.0e6),
            good_emission(id="E-2", character="broadband", applied_bandwidth_hz=1.0e6),
        ]
        audit = character_neutrality_audit(
            [evaluate_emission(e) for e in emissions]
        )
        self.assertEqual(audit["findings"], [])

    def test_scattered_ratios_are_not_character_driven(self):
        emissions = [
            good_emission(id="E-1", character="narrowband"),
            good_emission(id="E-2", character="broadband", applied_bandwidth_hz=1.0e6),
            good_emission(id="E-3", character="broadband", applied_bandwidth_hz=3.0e5),
        ]
        audit = character_neutrality_audit(
            [evaluate_emission(e) for e in emissions]
        )
        self.assertEqual(audit["findings"], [])

    def test_groups_count_their_members(self):
        audit = character_neutrality_audit(
            [evaluate_emission(e) for e in survey()]
        )
        self.assertEqual(sum(group["count"] for group in audit["groups"]), 3)

    def test_groups_are_ordered_by_character(self):
        audit = character_neutrality_audit(
            [evaluate_emission(e) for e in survey()]
        )
        names = [group["character"] for group in audit["groups"]]
        self.assertEqual(names, sorted(names))

    def test_empty_survey_raises(self):
        with self.assertRaises(ValueError):
            character_neutrality_audit([])

    def test_raw_record_raises(self):
        with self.assertRaises(ValueError):
            character_neutrality_audit([{"id": "E-1"}])


class TestReportableEmissions(unittest.TestCase):
    def test_exceedances_are_named_whatever_their_character(self):
        emissions = [
            good_emission(id="E-1", character="narrowband", level_dbuv=55.0),
            good_emission(id="E-2", character="broadband", level_dbuv=55.0),
            good_emission(id="E-3", character="impulsive", level_dbuv=10.0),
        ]
        names = reportable_emissions([evaluate_emission(e) for e in emissions])
        self.assertEqual(names, ["E-1", "E-2"])

    def test_ungraded_emission_is_not_reportable(self):
        emission = good_emission(level_dbuv=99.0)
        del emission["limit_dbuv"]
        self.assertEqual(reportable_emissions([evaluate_emission(emission)]), [])

    def test_string_survey_raises(self):
        with self.assertRaises(ValueError):
            reportable_emissions("E-1")


class TestAssessEmissionSurvey(unittest.TestCase):
    def test_clean_survey_is_character_neutral(self):
        report = assess_emission_survey(survey())
        self.assertEqual(report["verdict"], "character-neutral")
        self.assertTrue(report["accepted"])
        self.assertAlmostEqual(report["as_prescribed_fraction"], 1.0, places=12)

    def test_substitution_shows_in_the_prescribed_fraction(self):
        emissions = survey()
        emissions[1]["applied_bandwidth_hz"] = 1.0e6
        report = assess_emission_survey(emissions)
        self.assertAlmostEqual(
            report["as_prescribed_fraction"], 2.0 / 3.0, places=12
        )
        self.assertFalse(report["accepted"])

    def test_character_driven_survey_is_refused(self):
        emissions = [
            good_emission(id="E-1", character="narrowband"),
            good_emission(id="E-2", character="broadband", applied_bandwidth_hz=1.0e6),
        ]
        report = assess_emission_survey(emissions)
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("character-dependent-bandwidth", codes)
        self.assertEqual(report["verdict"], "non-conforming")

    def test_graded_count_ignores_unlimited_emissions(self):
        emissions = survey()
        del emissions[2]["limit_dbuv"]
        report = assess_emission_survey(emissions)
        self.assertEqual(report["graded_count"], 2)
        self.assertEqual(report["emission_count"], 3)

    def test_reportable_ids_are_carried_up(self):
        emissions = survey()
        emissions[0]["level_dbuv"] = 60.0
        report = assess_emission_survey(emissions)
        self.assertEqual(report["reportable_ids"], ["E-1"])

    def test_repeated_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_emission_survey([good_emission(), good_emission()])

    def test_empty_survey_raises(self):
        with self.assertRaises(ValueError):
            assess_emission_survey([])

    def test_string_survey_raises(self):
        with self.assertRaises(ValueError):
            assess_emission_survey("E-1")

    def test_character_audit_is_carried_up(self):
        report = assess_emission_survey(survey())
        self.assertEqual(report["character_audit"]["character_count"], 3)


if __name__ == "__main__":
    unittest.main()
