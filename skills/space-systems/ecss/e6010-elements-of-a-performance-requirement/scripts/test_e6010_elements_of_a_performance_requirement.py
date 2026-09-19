"""Contract tests for the clause 4.1.2 performance requirement element logic."""

import unittest

from e6010_elements_of_a_performance_requirement_logic import (
    COMPLETE,
    INCOHERENT,
    INCOMPLETE,
    KNOWN_INDICES,
    REQUIRED_ELEMENTS,
    assess_requirement,
    coherence_findings,
    completeness_score,
    group_by_verdict,
    missing_elements,
    normalize_requirement,
    restate_requirement,
    validate_confidence,
    validate_index,
    validate_text_element,
    validate_value,
    validate_window,
)


def statistical(**overrides):
    record = {
        "identifier": "APE-01",
        "parameter": "absolute pointing error",
        "index": "percentile",
        "value": 0.1,
        "unit": "deg",
        "window_s": 600.0,
        "reference_frame": "spacecraft body frame",
        "condition": "nominal science pointing",
        "confidence": 0.997,
    }
    record.update(overrides)
    return record


def deterministic(**overrides):
    record = {
        "identifier": "APE-02",
        "parameter": "absolute pointing error",
        "index": "peak",
        "value": 0.5,
        "unit": "deg",
        "window_s": 600.0,
        "reference_frame": "spacecraft body frame",
        "condition": "slew recovery",
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_known_index_accepted(self):
        self.assertEqual(validate_index("RMS"), "rms")

    def test_unknown_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_index("roughly")

    def test_non_string_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_index(3)

    def test_empty_text_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_text_element("   ", "unit")

    def test_negative_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_value(-0.1)

    def test_zero_bound_accepted(self):
        self.assertAlmostEqual(validate_value(0), 0.0, places=9)

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_value(True)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(0.0)

    def test_infinite_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(float("inf"))

    def test_confidence_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_confidence(1.0)

    def test_confidence_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_confidence(0.0)

    def test_interior_confidence_accepted(self):
        self.assertAlmostEqual(validate_confidence(0.997), 0.997, places=9)

    def test_every_known_index_validates(self):
        for index in KNOWN_INDICES:
            self.assertEqual(validate_index(index), index)


class MissingElementTests(unittest.TestCase):
    def test_a_full_statistical_record_misses_nothing(self):
        self.assertEqual(missing_elements(statistical()), [])

    def test_a_full_deterministic_record_misses_nothing(self):
        self.assertEqual(missing_elements(deterministic()), [])

    def test_each_required_element_is_detected_when_dropped(self):
        for key in REQUIRED_ELEMENTS:
            record = statistical()
            del record[key]
            self.assertIn(key, missing_elements(record))

    def test_a_statistical_index_needs_a_confidence(self):
        record = statistical()
        del record["confidence"]
        self.assertIn("confidence", missing_elements(record))

    def test_a_deterministic_index_does_not_need_a_confidence(self):
        self.assertNotIn("confidence", missing_elements(deterministic()))

    def test_a_blank_element_counts_as_missing(self):
        self.assertIn("unit", missing_elements(statistical(unit="  ")))

    def test_a_none_element_counts_as_missing(self):
        self.assertIn("condition", missing_elements(statistical(condition=None)))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            missing_elements(["parameter", "index"])


class CoherenceTests(unittest.TestCase):
    def test_a_full_statistical_record_is_coherent(self):
        self.assertEqual(coherence_findings(statistical()), [])

    def test_a_peak_bound_carrying_a_confidence_is_flagged(self):
        findings = coherence_findings(deterministic(confidence=0.997))
        self.assertTrue(any("does not apply to it" in f for f in findings))

    def test_an_out_of_range_confidence_is_flagged(self):
        self.assertTrue(coherence_findings(statistical(confidence=1.2)))

    def test_a_negative_bound_is_flagged(self):
        self.assertTrue(coherence_findings(statistical(value=-1.0)))

    def test_an_unknown_index_is_flagged(self):
        self.assertTrue(coherence_findings(statistical(index="approximately")))

    def test_a_negative_window_is_flagged(self):
        self.assertTrue(coherence_findings(statistical(window_s=-5.0)))


class ScoreTests(unittest.TestCase):
    def test_a_full_record_scores_one(self):
        self.assertAlmostEqual(completeness_score(statistical()), 1.0, places=9)

    def test_a_full_deterministic_record_scores_one(self):
        self.assertAlmostEqual(completeness_score(deterministic()), 1.0, places=9)

    def test_dropping_an_element_lowers_the_score(self):
        record = statistical()
        del record["unit"]
        self.assertLess(completeness_score(record), 1.0)

    def test_the_statistical_denominator_includes_confidence(self):
        record = statistical()
        del record["confidence"]
        self.assertAlmostEqual(
            completeness_score(record), 7.0 / 8.0, places=9
        )

    def test_the_deterministic_denominator_does_not(self):
        record = deterministic()
        del record["unit"]
        self.assertAlmostEqual(completeness_score(record), 6.0 / 7.0, places=9)


class NormalizeTests(unittest.TestCase):
    def test_a_full_record_normalizes(self):
        normalized = normalize_requirement(statistical())
        self.assertEqual(normalized["index"], "percentile")
        self.assertAlmostEqual(normalized["confidence"], 0.997, places=9)

    def test_a_deterministic_record_normalizes_with_no_confidence(self):
        self.assertIsNone(normalize_requirement(deterministic())["confidence"])

    def test_an_incomplete_record_will_not_normalize(self):
        record = statistical()
        del record["reference_frame"]
        with self.assertRaises(ValueError):
            normalize_requirement(record)

    def test_an_incoherent_record_will_not_normalize(self):
        with self.assertRaises(ValueError):
            normalize_requirement(deterministic(confidence=0.997))

    def test_restatement_carries_every_element(self):
        line = restate_requirement(statistical())
        for token in ("absolute pointing error", "percentile", "deg", "600",
                      "spacecraft body frame", "nominal science pointing", "0.997"):
            self.assertIn(token, line)

    def test_restatement_omits_confidence_for_a_peak_bound(self):
        self.assertNotIn("confidence", restate_requirement(deterministic()))


class AssessTests(unittest.TestCase):
    def test_a_full_record_is_complete(self):
        result = assess_requirement(statistical())
        self.assertEqual(result["verdict"], COMPLETE)
        self.assertEqual(result["findings"], [])
        self.assertIsNotNone(result["restatement"])

    def test_a_record_missing_a_window_is_incomplete(self):
        record = statistical()
        del record["window_s"]
        result = assess_requirement(record)
        self.assertEqual(result["verdict"], INCOMPLETE)
        self.assertIn("window_s", result["missing"])

    def test_an_incomplete_record_says_why_it_matters(self):
        record = statistical()
        del record["window_s"]
        result = assess_requirement(record)
        self.assertTrue(
            any("verification case for it" in f for f in result["findings"])
        )

    def test_a_peak_bound_with_a_confidence_is_incoherent(self):
        result = assess_requirement(deterministic(confidence=0.997))
        self.assertEqual(result["verdict"], INCOHERENT)
        self.assertEqual(result["missing"], [])

    def test_an_incomplete_record_gets_no_restatement(self):
        record = statistical()
        del record["unit"]
        self.assertIsNone(assess_requirement(record)["restatement"])

    def test_the_identifier_is_carried_through(self):
        self.assertEqual(assess_requirement(statistical())["identifier"], "APE-01")

    def test_a_missing_index_alone_is_incomplete_not_incoherent(self):
        record = statistical()
        del record["index"]
        self.assertEqual(assess_requirement(record)["verdict"], INCOMPLETE)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_requirement("absolute pointing error below 0.1 deg")


class GroupingTests(unittest.TestCase):
    def test_a_set_is_grouped_by_verdict(self):
        incomplete = statistical(identifier="APE-03")
        del incomplete["condition"]
        grouped = group_by_verdict(
            [
                statistical(),
                deterministic(),
                incomplete,
                deterministic(identifier="APE-04", confidence=0.95),
            ]
        )
        self.assertEqual(grouped[COMPLETE], ["APE-01", "APE-02"])
        self.assertEqual(grouped[INCOMPLETE], ["APE-03"])
        self.assertEqual(grouped[INCOHERENT], ["APE-04"])

    def test_an_unnamed_record_gets_a_positional_label(self):
        record = statistical()
        del record["identifier"]
        grouped = group_by_verdict([record])
        self.assertEqual(grouped[COMPLETE], ["record[0]"])

    def test_an_empty_set_groups_to_empty_lists(self):
        grouped = group_by_verdict([])
        self.assertEqual(grouped[COMPLETE], [])
        self.assertEqual(grouped[INCOMPLETE], [])

    def test_a_single_mapping_is_not_a_set(self):
        with self.assertRaises(ValueError):
            group_by_verdict(statistical())


if __name__ == "__main__":
    unittest.main()
