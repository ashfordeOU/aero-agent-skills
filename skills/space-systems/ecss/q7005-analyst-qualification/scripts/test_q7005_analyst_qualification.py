"""Contract test for the IR spectral-interpretation qualification leaf."""

import datetime
import unittest

from q7005_analyst_qualification_logic import (
    NOT_QUALIFIED,
    OUTCOME_CORRECT,
    OUTCOME_MISIDENTIFIED,
    OUTCOME_MISSED,
    PROVISIONAL,
    QUALIFIED,
    add_calendar_months,
    assess_analyst,
    assign_interpretation,
    currency_expiry,
    parse_date,
    proficiency_rates,
    resolved_policy,
    validate_analyst,
    validate_round,
)

RUN_DAY = "2026-06-15"
SILICONE = "silicone-oil"
FLUORINATED = "fluorinated-lubricant"


def rounds(family=SILICONE, correct=9, missed=1, wrong=0):
    entries = []
    for _ in range(correct):
        entries.append({"family": family, "outcome": OUTCOME_CORRECT})
    for _ in range(missed):
        entries.append({"family": family, "outcome": OUTCOME_MISSED})
    for _ in range(wrong):
        entries.append({"family": family, "outcome": OUTCOME_MISIDENTIFIED})
    return entries


def analyst(name="analyst-one", **kw):
    record = {
        "name": name,
        "training_reference": "TRN-2201",
        "endorsed_families": [SILICONE],
        "supervised_interpretations": 14,
        "proficiency_rounds": rounds(),
        "last_qualifying_activity": "2025-09-01",
    }
    record.update(kw)
    return record


class TestDatesAndPolicy(unittest.TestCase):
    def test_an_iso_date_parses(self):
        self.assertEqual(parse_date("2026-06-15"), datetime.date(2026, 6, 15))

    def test_a_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            parse_date("June 2026")

    def test_calendar_months_clamp_to_the_month_end(self):
        self.assertEqual(
            add_calendar_months("2026-01-31", 1), datetime.date(2026, 2, 28)
        )

    def test_defaults_are_returned_when_nothing_is_passed(self):
        self.assertEqual(resolved_policy()["currency_months"], 24)

    def test_an_unknown_policy_key_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"currency_years": 2})

    def test_a_rate_outside_the_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"minimum_correct_rate": 1.4})


class TestValidateRound(unittest.TestCase):
    def test_a_valid_round_normalizes(self):
        entry = validate_round({"family": SILICONE, "outcome": OUTCOME_CORRECT})
        self.assertEqual(entry["family"], SILICONE)

    def test_an_unknown_outcome_raises(self):
        with self.assertRaises(ValueError):
            validate_round({"family": SILICONE, "outcome": "about-right"})

    def test_an_empty_family_raises(self):
        with self.assertRaises(ValueError):
            validate_round({"family": "  ", "outcome": OUTCOME_CORRECT})


class TestProficiencyRates(unittest.TestCase):
    def test_rates_are_taken_over_the_named_family_only(self):
        mixed = rounds(SILICONE, 8, 2, 0) + rounds(FLUORINATED, 0, 0, 4)
        stats = proficiency_rates(mixed, SILICONE)
        self.assertEqual(stats["rounds"], 10)
        self.assertAlmostEqual(stats["correct_rate"], 0.8, places=9)

    def test_misidentification_is_counted_apart_from_a_miss(self):
        stats = proficiency_rates(rounds(SILICONE, 8, 1, 1), SILICONE)
        self.assertEqual(stats["missed"], 1)
        self.assertEqual(stats["misidentified"], 1)
        self.assertAlmostEqual(stats["misidentification_rate"], 0.1, places=9)

    def test_a_family_with_no_rounds_raises_rather_than_scoring_zero(self):
        with self.assertRaises(ValueError):
            proficiency_rates(rounds(SILICONE), FLUORINATED)

    def test_a_non_list_raises(self):
        with self.assertRaises(ValueError):
            proficiency_rates("all correct", SILICONE)


class TestValidateAnalyst(unittest.TestCase):
    def test_a_valid_analyst_normalizes(self):
        norm = validate_analyst(analyst())
        self.assertEqual(norm["name"], "analyst-one")
        self.assertEqual(norm["endorsed_families"], (SILICONE,))

    def test_an_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_analyst(analyst(name=" "))

    def test_an_empty_endorsement_list_raises(self):
        with self.assertRaises(ValueError):
            validate_analyst(analyst(endorsed_families=[]))

    def test_a_duplicate_endorsed_family_raises(self):
        with self.assertRaises(ValueError):
            validate_analyst(analyst(endorsed_families=[SILICONE, SILICONE]))

    def test_a_fractional_supervised_count_raises(self):
        with self.assertRaises(ValueError):
            validate_analyst(analyst(supervised_interpretations=9.5))

    def test_a_missing_proficiency_list_raises(self):
        with self.assertRaises(ValueError):
            validate_analyst(analyst(proficiency_rounds=None))


class TestCurrency(unittest.TestCase):
    def test_currency_runs_in_whole_calendar_months(self):
        self.assertEqual(
            currency_expiry(analyst()), datetime.date(2027, 9, 1)
        )

    def test_a_shorter_window_pulls_the_expiry_in(self):
        self.assertEqual(
            currency_expiry(analyst(), {"currency_months": 6}),
            datetime.date(2026, 3, 1),
        )

    def test_an_analyst_with_no_activity_has_no_expiry(self):
        self.assertIsNone(currency_expiry(analyst(last_qualifying_activity=None)))


class TestAssessAnalyst(unittest.TestCase):
    def test_a_current_endorsed_proficient_analyst_is_qualified(self):
        row = assess_analyst(analyst(), SILICONE, RUN_DAY)
        self.assertEqual(row["verdict"], QUALIFIED)
        self.assertEqual(row["blocking_findings"], [])
        self.assertFalse(row["independent_check_required"])

    def test_an_endorsement_in_another_family_does_not_carry_over(self):
        row = assess_analyst(analyst(), FLUORINATED, RUN_DAY)
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn("family-outside-the-endorsement", row["blocking_findings"])

    def test_a_missing_training_record_blocks(self):
        row = assess_analyst(analyst(training_reference=None), SILICONE, RUN_DAY)
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn("no-training-record-on-file", row["blocking_findings"])

    def test_too_few_rounds_blocks_rather_than_scoring_zero(self):
        row = assess_analyst(
            analyst(proficiency_rounds=rounds(SILICONE, 2, 0, 0)),
            SILICONE,
            RUN_DAY,
        )
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn(
            "too-few-proficiency-rounds-to-support-a-rate",
            row["blocking_findings"],
        )

    def test_a_correct_rate_exactly_on_the_threshold_passes(self):
        row = assess_analyst(
            analyst(proficiency_rounds=rounds(SILICONE, 8, 2, 0)),
            SILICONE,
            RUN_DAY,
        )
        self.assertAlmostEqual(row["proficiency"]["correct_rate"], 0.8, places=9)
        self.assertEqual(row["verdict"], QUALIFIED)

    def test_a_correct_rate_below_the_threshold_blocks(self):
        row = assess_analyst(
            analyst(proficiency_rounds=rounds(SILICONE, 5, 5, 0)),
            SILICONE,
            RUN_DAY,
        )
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn(
            "correct-reading-rate-below-the-threshold", row["blocking_findings"]
        )

    def test_naming_the_wrong_species_too_often_blocks_on_its_own_axis(self):
        row = assess_analyst(
            analyst(proficiency_rounds=rounds(SILICONE, 8, 0, 2)),
            SILICONE,
            RUN_DAY,
        )
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn(
            "misidentification-rate-above-the-ceiling", row["blocking_findings"]
        )
        self.assertNotIn(
            "correct-reading-rate-below-the-threshold", row["blocking_findings"]
        )

    def test_a_misidentification_rate_exactly_on_the_ceiling_passes(self):
        row = assess_analyst(
            analyst(proficiency_rounds=rounds(SILICONE, 9, 0, 1)),
            SILICONE,
            RUN_DAY,
        )
        self.assertAlmostEqual(
            row["proficiency"]["misidentification_rate"], 0.1, places=9
        )
        self.assertEqual(row["verdict"], QUALIFIED)

    def test_a_short_supervised_count_is_provisional_not_refused(self):
        row = assess_analyst(
            analyst(supervised_interpretations=4), SILICONE, RUN_DAY
        )
        self.assertEqual(row["verdict"], PROVISIONAL)
        self.assertTrue(row["independent_check_required"])

    def test_currency_lapsed_inside_the_grace_window_is_provisional(self):
        row = assess_analyst(
            analyst(last_qualifying_activity="2024-05-01"), SILICONE, RUN_DAY
        )
        self.assertEqual(row["verdict"], PROVISIONAL)
        self.assertIn(
            "currency-lapsed-inside-the-grace-window", row["provisional_findings"]
        )

    def test_currency_lapsed_beyond_the_grace_window_blocks(self):
        row = assess_analyst(
            analyst(last_qualifying_activity="2022-01-01"), SILICONE, RUN_DAY
        )
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn(
            "currency-lapsed-beyond-the-grace-window", row["blocking_findings"]
        )

    def test_no_qualifying_activity_at_all_blocks(self):
        row = assess_analyst(
            analyst(last_qualifying_activity=None), SILICONE, RUN_DAY
        )
        self.assertEqual(row["verdict"], NOT_QUALIFIED)
        self.assertIn("no-qualifying-activity-on-record", row["blocking_findings"])

    def test_an_empty_family_argument_raises(self):
        with self.assertRaises(ValueError):
            assess_analyst(analyst(), "  ", RUN_DAY)


class TestAssignInterpretation(unittest.TestCase):
    def test_a_qualified_analyst_is_assigned_without_a_check(self):
        report = assign_interpretation([analyst()], SILICONE, RUN_DAY)
        self.assertEqual(report["assigned_analyst"], "analyst-one")
        self.assertTrue(report["interpretation_may_proceed"])
        self.assertFalse(report["independent_check_required"])

    def test_a_provisional_analyst_alone_cannot_proceed(self):
        report = assign_interpretation(
            [analyst(supervised_interpretations=2)], SILICONE, RUN_DAY
        )
        self.assertFalse(report["interpretation_may_proceed"])
        self.assertTrue(report["independent_check_required"])
        self.assertIn(
            "provisional-analyst-with-no-qualified-checker-available",
            report["findings"],
        )

    def test_a_qualified_analyst_is_preferred_over_a_provisional_one(self):
        report = assign_interpretation(
            [analyst("trainee", supervised_interpretations=2), analyst("lead")],
            SILICONE,
            RUN_DAY,
        )
        self.assertEqual(report["assigned_analyst"], "lead")
        self.assertEqual(report["provisional"], ["trainee"])

    def test_nobody_endorsed_for_the_family_refuses_the_work(self):
        report = assign_interpretation([analyst()], FLUORINATED, RUN_DAY)
        self.assertIsNone(report["assigned_analyst"])
        self.assertIn(
            "no-endorsed-analyst-available-for-this-family", report["findings"]
        )

    def test_duplicate_analyst_raises(self):
        with self.assertRaises(ValueError):
            assign_interpretation([analyst(), analyst()], SILICONE, RUN_DAY)

    def test_an_empty_roster_raises(self):
        with self.assertRaises(ValueError):
            assign_interpretation([], SILICONE, RUN_DAY)


if __name__ == "__main__":
    unittest.main()
