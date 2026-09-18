#!/usr/bin/env python3
"""Gate 3 contract test for e2007-susceptibility-data-presentation.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_susceptibility_data_presentation.py
"""

import unittest

from e2007_susceptibility_data_presentation_logic import (
    DEFAULT_MARGINAL_BAND_FRACTION,
    DIRECTION_NOT_TO_EXCEED,
    DIRECTION_NOT_TO_FALL_BELOW,
    OUTCOME_FAIL,
    OUTCOME_PASS,
    RECOGNIZED_DIRECTIONS,
    RECOGNIZED_MODULATIONS,
    REQUIRED_RESULT_FIELDS,
    TOL,
    assess_susceptibility_presentation,
    at_least,
    at_most,
    build_criteria_register,
    evaluate_result,
    group_by_function,
    normalize_criterion,
    normalize_direction,
    normalize_modulation,
    normalize_result,
    presentation_gaps,
    restate_criterion,
    result_margin,
)


def ceiling_criterion(**over):
    record = {
        "criterion_id": "PC-01",
        "function": "reaction wheel speed loop",
        "parameter": "speed error during injection",
        "limit_value": 12.0,
        "unit": "rpm",
        "direction": DIRECTION_NOT_TO_EXCEED,
        "agreement_reference": "EMC-TSPEC-R3 minute 14",
        "agreed": True,
    }
    record.update(over)
    return record


def floor_criterion(**over):
    record = {
        "criterion_id": "PC-02",
        "function": "telemetry downlink",
        "parameter": "frame lock margin during injection",
        "limit_value": 3.0,
        "unit": "dB",
        "direction": DIRECTION_NOT_TO_FALL_BELOW,
        "agreement_reference": "EMC-TSPEC-R3 minute 15",
        "agreed": True,
    }
    record.update(over)
    return record


def ceiling_result(**over):
    record = {
        "criterion_id": "PC-01",
        "frequency_hz": 2.0e6,
        "injected_level_dbuv": 134.0,
        "modulation": "pulse-modulated",
        "observed_value": 4.0,
    }
    record.update(over)
    return record


def floor_result(**over):
    record = {
        "criterion_id": "PC-02",
        "frequency_hz": 5.0e6,
        "injected_level_dbuv": 134.0,
        "modulation": "pulse-modulated",
        "observed_value": 6.0,
    }
    record.update(over)
    return record


class TestVocabulary(unittest.TestCase):
    def test_every_recognized_direction_normalizes(self):
        for name in RECOGNIZED_DIRECTIONS:
            self.assertEqual(normalize_direction(name.upper()), name)

    def test_unrecognized_direction_rejected(self):
        with self.assertRaises(ValueError):
            normalize_direction("about-equal-to")

    def test_non_string_direction_rejected(self):
        with self.assertRaises(ValueError):
            normalize_direction(12.0)

    def test_every_recognized_modulation_normalizes(self):
        for name in RECOGNIZED_MODULATIONS:
            self.assertEqual(normalize_modulation(" %s " % name), name)

    def test_unrecognized_modulation_rejected(self):
        with self.assertRaises(ValueError):
            normalize_modulation("stepped-noise")


class TestCriterionValidation(unittest.TestCase):
    def test_agreed_criterion_normalizes(self):
        criterion = normalize_criterion(ceiling_criterion())
        self.assertEqual(criterion["criterion_id"], "PC-01")
        self.assertAlmostEqual(criterion["limit_value"], 12.0)

    def test_unagreed_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion(ceiling_criterion(agreed=False))

    def test_missing_agreement_reference_rejected(self):
        record = ceiling_criterion()
        del record["agreement_reference"]
        with self.assertRaises(ValueError):
            normalize_criterion(record)

    def test_blank_function_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion(ceiling_criterion(function="  "))

    def test_missing_limit_rejected(self):
        record = ceiling_criterion()
        del record["limit_value"]
        with self.assertRaises(ValueError):
            normalize_criterion(record)

    def test_non_mapping_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion("speed error under 12 rpm")

    def test_register_rejects_duplicate_identifiers(self):
        with self.assertRaises(ValueError):
            build_criteria_register([ceiling_criterion(), ceiling_criterion()])

    def test_register_rejects_an_empty_list(self):
        with self.assertRaises(ValueError):
            build_criteria_register([])

    def test_register_keys_on_the_identifier(self):
        register = build_criteria_register([ceiling_criterion(), floor_criterion()])
        self.assertEqual(sorted(register), ["PC-01", "PC-02"])

    def test_restatement_carries_limit_and_agreement(self):
        line = restate_criterion(normalize_criterion(ceiling_criterion()))
        self.assertIn("12", line)
        self.assertIn("not-to-exceed", line)
        self.assertIn("EMC-TSPEC-R3 minute 14", line)


class TestResultValidation(unittest.TestCase):
    def test_complete_result_normalizes(self):
        result = normalize_result(ceiling_result())
        self.assertAlmostEqual(result["frequency_hz"], 2.0e6)
        self.assertEqual(result["modulation"], "pulse-modulated")

    def test_every_required_field_is_enforced(self):
        for field in REQUIRED_RESULT_FIELDS:
            record = ceiling_result()
            del record[field]
            with self.assertRaises(ValueError):
                normalize_result(record)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            normalize_result(ceiling_result(frequency_hz=0.0))

    def test_blank_criterion_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalize_result(ceiling_result(criterion_id="   "))

    def test_non_mapping_result_rejected(self):
        with self.assertRaises(ValueError):
            normalize_result(["4 rpm at 2 MHz"])


class TestEvaluation(unittest.TestCase):
    def test_observation_under_a_ceiling_passes(self):
        entry = evaluate_result(
            normalize_result(ceiling_result()), normalize_criterion(ceiling_criterion())
        )
        self.assertEqual(entry["outcome"], OUTCOME_PASS)
        self.assertAlmostEqual(entry["margin"], 8.0)

    def test_observation_over_a_ceiling_fails(self):
        entry = evaluate_result(
            normalize_result(ceiling_result(observed_value=15.0)),
            normalize_criterion(ceiling_criterion()),
        )
        self.assertEqual(entry["outcome"], OUTCOME_FAIL)

    def test_observation_above_a_floor_passes(self):
        entry = evaluate_result(
            normalize_result(floor_result()), normalize_criterion(floor_criterion())
        )
        self.assertEqual(entry["outcome"], OUTCOME_PASS)
        self.assertAlmostEqual(entry["margin"], 3.0)

    def test_observation_below_a_floor_fails(self):
        entry = evaluate_result(
            normalize_result(floor_result(observed_value=1.0)),
            normalize_criterion(floor_criterion()),
        )
        self.assertEqual(entry["outcome"], OUTCOME_FAIL)

    def test_margin_sense_follows_the_direction(self):
        ceiling = normalize_criterion(ceiling_criterion())
        floor = normalize_criterion(floor_criterion())
        self.assertAlmostEqual(
            result_margin(normalize_result(ceiling_result()), ceiling), 8.0
        )
        self.assertAlmostEqual(
            result_margin(normalize_result(floor_result()), floor), 3.0
        )

    def test_observation_exactly_on_the_limit_passes_despite_float_error(self):
        # 1.1 * 3 is 3.3000000000000003, so an observation that physically sits
        # exactly on a 3.3 unit ceiling reads a whisker over it.
        observed = 1.1 * 3
        self.assertAlmostEqual(observed, 3.3, places=9)
        entry = evaluate_result(
            normalize_result(ceiling_result(observed_value=observed)),
            normalize_criterion(ceiling_criterion(limit_value=3.3)),
        )
        self.assertEqual(entry["outcome"], OUTCOME_PASS)

    def test_passing_result_near_the_limit_is_flagged_close(self):
        entry = evaluate_result(
            normalize_result(ceiling_result(observed_value=11.8)),
            normalize_criterion(ceiling_criterion()),
        )
        self.assertEqual(entry["outcome"], OUTCOME_PASS)
        self.assertTrue(entry["close_to_limit"])

    def test_comfortable_result_is_not_flagged_close(self):
        entry = evaluate_result(
            normalize_result(ceiling_result()), normalize_criterion(ceiling_criterion())
        )
        self.assertFalse(entry["close_to_limit"])

    def test_zero_band_fraction_flags_nothing_but_an_exact_match(self):
        entry = evaluate_result(
            normalize_result(ceiling_result(observed_value=11.8)),
            normalize_criterion(ceiling_criterion()),
            marginal_band_fraction=0.0,
        )
        self.assertFalse(entry["close_to_limit"])

    def test_band_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_result(
                normalize_result(ceiling_result()),
                normalize_criterion(ceiling_criterion()),
                marginal_band_fraction=1.0,
            )

    def test_entry_carries_the_restated_criterion(self):
        entry = evaluate_result(
            normalize_result(ceiling_result()), normalize_criterion(ceiling_criterion())
        )
        self.assertIn("agreed:", entry["restated_criterion"])

    def test_comparison_helpers_absorb_float_error_only(self):
        self.assertTrue(at_least(0.0, 0.0))
        self.assertTrue(at_least(-TOL / 2.0, 0.0))
        self.assertFalse(at_least(-0.5, 0.0))
        self.assertTrue(at_most(1.0, 1.0))
        self.assertFalse(at_most(2.0, 1.0))


class TestCoverage(unittest.TestCase):
    def test_full_coverage_has_no_gaps(self):
        register = build_criteria_register([ceiling_criterion(), floor_criterion()])
        results = [normalize_result(ceiling_result()), normalize_result(floor_result())]
        orphans, uncovered = presentation_gaps(register, results)
        self.assertEqual(orphans, [])
        self.assertEqual(uncovered, [])

    def test_result_citing_an_unknown_criterion_is_an_orphan(self):
        register = build_criteria_register([ceiling_criterion()])
        results = [normalize_result(ceiling_result(criterion_id="PC-09"))]
        orphans, _uncovered = presentation_gaps(register, results)
        self.assertEqual(orphans, ["PC-09"])

    def test_criterion_with_no_result_is_uncovered(self):
        register = build_criteria_register([ceiling_criterion(), floor_criterion()])
        results = [normalize_result(ceiling_result())]
        _orphans, uncovered = presentation_gaps(register, results)
        self.assertEqual(uncovered, ["PC-02"])

    def test_grouping_collects_results_under_their_function(self):
        entries = [
            evaluate_result(
                normalize_result(ceiling_result()),
                normalize_criterion(ceiling_criterion()),
            ),
            evaluate_result(
                normalize_result(floor_result()), normalize_criterion(floor_criterion())
            ),
        ]
        grouped = group_by_function(entries)
        self.assertEqual(sorted(grouped), ["reaction wheel speed loop", "telemetry downlink"])


class TestPresentationAudit(unittest.TestCase):
    def test_complete_package_is_accepted(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion(), floor_criterion()],
            [ceiling_result(), floor_result()],
        )
        self.assertEqual(report["verdict"], "report-complete")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["counts"][OUTCOME_PASS], 2)

    def test_failed_result_makes_the_package_incomplete(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion(), floor_criterion()],
            [ceiling_result(observed_value=20.0), floor_result()],
        )
        self.assertEqual(report["verdict"], "report-incomplete")
        self.assertTrue(any("misses criterion" in f for f in report["findings"]))
        self.assertEqual(report["counts"][OUTCOME_FAIL], 1)

    def test_uncovered_criterion_is_a_finding(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion(), floor_criterion()], [ceiling_result()]
        )
        self.assertEqual(report["uncovered_criterion_ids"], ["PC-02"])
        self.assertTrue(
            any("restated by no presented result" in f for f in report["findings"])
        )

    def test_orphan_result_is_a_finding(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion()],
            [ceiling_result(), ceiling_result(criterion_id="PC-77")],
        )
        self.assertEqual(report["orphan_criterion_ids"], ["PC-77"])
        self.assertEqual(report["verdict"], "report-incomplete")

    def test_close_result_is_a_limitation_not_a_finding(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion(), floor_criterion()],
            [ceiling_result(observed_value=11.7), floor_result()],
        )
        self.assertEqual(report["verdict"], "report-complete")
        self.assertTrue(any("sits" in l for l in report["limitations"]))

    def test_entries_are_ordered_by_criterion_then_frequency(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion(), floor_criterion()],
            [
                floor_result(),
                ceiling_result(frequency_hz=9.0e6),
                ceiling_result(frequency_hz=1.0e6),
            ],
        )
        self.assertEqual(
            [(e["criterion_id"], e["frequency_hz"]) for e in report["entries"]],
            [("PC-01", 1.0e6), ("PC-01", 9.0e6), ("PC-02", 5.0e6)],
        )

    def test_report_groups_entries_by_function(self):
        report = assess_susceptibility_presentation(
            [ceiling_criterion(), floor_criterion()],
            [ceiling_result(), floor_result()],
        )
        self.assertEqual(len(report["by_function"]["telemetry downlink"]), 1)

    def test_unagreed_criterion_rejects_the_package(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_presentation(
                [ceiling_criterion(agreed=False)], [ceiling_result()]
            )

    def test_empty_result_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_presentation([ceiling_criterion()], [])

    def test_non_list_results_rejected(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_presentation([ceiling_criterion()], ceiling_result())

    def test_default_band_fraction_is_five_percent(self):
        self.assertAlmostEqual(DEFAULT_MARGINAL_BAND_FRACTION, 0.05, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=1)
