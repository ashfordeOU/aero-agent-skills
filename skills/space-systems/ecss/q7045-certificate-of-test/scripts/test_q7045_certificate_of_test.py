"""Contract tests for the certificate-of-test issue decision."""

import unittest

from q7045_certificate_of_test_logic import (
    BASE_SPECIMENS_PER_HEAT,
    MASS_INCREMENT_KG,
    MAX_SPECIMENS_PER_HEAT,
    MARGIN_TOLERANCE_MPA,
    assess_certificate_issue,
    assess_heat,
    certificate_reference,
    group_specimens_by_heat,
    heat_statistics,
    product_forms,
    required_specimen_count,
    valid_specimens,
)

ISSUE_DATE = (2026, 9, 18)


def _specimen(identifier, heat, value, valid=True):
    return {"id": identifier, "heat": heat, "value_mpa": value, "valid": valid}


class SamplingTests(unittest.TestCase):
    def test_small_bar_release_owes_the_base_number(self):
        self.assertEqual(
            required_specimen_count("bar", 400.0), BASE_SPECIMENS_PER_HEAT
        )

    def test_mass_uplift_adds_one_per_started_increment(self):
        self.assertEqual(
            required_specimen_count("bar", MASS_INCREMENT_KG * 2.5),
            BASE_SPECIMENS_PER_HEAT + 2,
        )

    def test_exact_increment_boundary_does_not_double_count(self):
        self.assertEqual(
            required_specimen_count("bar", MASS_INCREMENT_KG),
            BASE_SPECIMENS_PER_HEAT,
        )

    def test_forging_owes_more_than_bar_for_the_same_mass(self):
        self.assertEqual(
            required_specimen_count("forging", 400.0),
            required_specimen_count("bar", 400.0) + 2,
        )

    def test_sampling_is_capped(self):
        self.assertEqual(
            required_specimen_count("casting", MASS_INCREMENT_KG * 50),
            MAX_SPECIMENS_PER_HEAT,
        )

    def test_unknown_product_form_rejected(self):
        with self.assertRaises(ValueError):
            required_specimen_count("wire", 400.0)

    def test_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            required_specimen_count("bar", 0.0)

    def test_product_forms_are_sorted(self):
        self.assertEqual(product_forms(), sorted(product_forms()))


class GroupingTests(unittest.TestCase):
    def test_single_heat_gives_one_group(self):
        grouped = group_specimens_by_heat(
            [_specimen("a", "h1", 500.0), _specimen("b", "h1", 510.0)]
        )
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0][0], "h1")

    def test_two_heats_are_kept_apart_in_first_seen_order(self):
        grouped = group_specimens_by_heat(
            [_specimen("a", "h2", 500.0), _specimen("b", "h1", 510.0)]
        )
        self.assertEqual([heat for heat, _ in grouped], ["h2", "h1"])

    def test_heat_token_is_case_folded(self):
        grouped = group_specimens_by_heat(
            [_specimen("a", "H1", 500.0), _specimen("b", "h1", 510.0)]
        )
        self.assertEqual(len(grouped), 1)

    def test_duplicate_specimen_identifier_rejected(self):
        with self.assertRaises(ValueError):
            group_specimens_by_heat([_specimen("a", "h1", 500.0), _specimen("a", "h1", 510.0)])

    def test_empty_specimen_set_rejected(self):
        with self.assertRaises(ValueError):
            group_specimens_by_heat([])

    def test_missing_heat_key_rejected(self):
        with self.assertRaises(ValueError):
            group_specimens_by_heat([{"id": "a", "value_mpa": 500.0}])

    def test_non_boolean_validity_rejected(self):
        with self.assertRaises(ValueError):
            group_specimens_by_heat([{"id": "a", "heat": "h1", "value_mpa": 500.0, "valid": "yes"}])


class StatisticsTests(unittest.TestCase):
    def test_voided_specimen_is_dropped(self):
        entries = [_specimen("a", "h1", 500.0), _specimen("b", "h1", 300.0, valid=False)]
        self.assertEqual(len(valid_specimens(entries)), 1)

    def test_statistics_use_only_valid_specimens(self):
        entries = [
            _specimen("a", "h1", 500.0),
            _specimen("b", "h1", 520.0),
            _specimen("c", "h1", 100.0, valid=False),
        ]
        stats = heat_statistics(entries)
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["minimum_mpa"], 500.0)
        self.assertAlmostEqual(stats["mean_mpa"], 510.0)

    def test_governing_specimen_is_the_lowest(self):
        entries = [_specimen("a", "h1", 520.0), _specimen("b", "h1", 495.0)]
        self.assertEqual(heat_statistics(entries)["governing_id"], "b")

    def test_all_specimens_voided_is_rejected(self):
        with self.assertRaises(ValueError):
            heat_statistics([_specimen("a", "h1", 500.0, valid=False)])


class ReferenceTests(unittest.TestCase):
    def test_reference_is_deterministic(self):
        first = certificate_reference("lab7", "h-1", ISSUE_DATE)
        second = certificate_reference("LAB7", "H-1", ISSUE_DATE)
        self.assertEqual(first, second)

    def test_reference_carries_the_heat_and_date(self):
        self.assertEqual(
            certificate_reference("lab7", "k4491", (2026, 1, 5)), "COT-LAB7-K4491-20260105"
        )

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            certificate_reference("lab7", "h1", (2026, 13, 1))

    def test_non_triple_date_rejected(self):
        with self.assertRaises(ValueError):
            certificate_reference("lab7", "h1", (2026, 9))

    def test_punctuation_only_heat_rejected(self):
        with self.assertRaises(ValueError):
            certificate_reference("lab7", "---", ISSUE_DATE)


class HeatAssessmentTests(unittest.TestCase):
    def test_sufficient_heat_is_issuable(self):
        entries = [_specimen("a", "h1", 520.0), _specimen("b", "h1", 515.0)]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertTrue(record["issuable"])
        self.assertEqual(record["findings"], [])

    def test_undersampled_heat_is_blocked(self):
        entries = [_specimen("a", "h1", 520.0)]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertFalse(record["issuable"])

    def test_one_specimen_below_the_minimum_blocks_a_passing_mean(self):
        entries = [_specimen("a", "h1", 700.0), _specimen("b", "h1", 400.0)]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertGreater(record["statistics"]["mean_mpa"], 480.0)
        self.assertFalse(record["issuable"])

    def test_specimen_exactly_on_the_minimum_passes(self):
        entries = [_specimen("a", "h1", 480.0), _specimen("b", "h1", 520.0)]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertTrue(record["issuable"])
        self.assertAlmostEqual(
            record["statistics"]["minimum_mpa"], 480.0, places=9
        )

    def test_tolerance_absorbs_a_representation_shortfall(self):
        entries = [
            _specimen("a", "h1", 480.0 - MARGIN_TOLERANCE_MPA / 2.0),
            _specimen("b", "h1", 520.0),
        ]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertTrue(record["issuable"])

    def test_voided_specimens_are_counted_separately(self):
        entries = [
            _specimen("a", "h1", 520.0),
            _specimen("b", "h1", 515.0),
            _specimen("c", "h1", 100.0, valid=False),
        ]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertEqual(record["voided_specimens"], 1)
        self.assertTrue(record["issuable"])

    def test_fully_voided_heat_has_no_reference(self):
        entries = [_specimen("a", "h1", 520.0, valid=False)]
        record = assess_heat("h1", entries, "bar", 400.0, 480.0, "lab7", ISSUE_DATE)
        self.assertIsNone(record["reference"])
        self.assertFalse(record["issuable"])

    def test_non_positive_specified_minimum_rejected(self):
        entries = [_specimen("a", "h1", 520.0)]
        with self.assertRaises(ValueError):
            assess_heat("h1", entries, "bar", 400.0, -10.0, "lab7", ISSUE_DATE)


class ReleaseAssessmentTests(unittest.TestCase):
    def _release(self, **overrides):
        release = {
            "specimens": [_specimen("a", "h1", 520.0), _specimen("b", "h1", 515.0)],
            "product_form": "bar",
            "released_mass_kg": 400.0,
            "specified_minimum_mpa": 480.0,
            "laboratory_code": "lab7",
            "issue_date": ISSUE_DATE,
        }
        release.update(overrides)
        return release

    def test_single_heat_release_issues_one_certificate(self):
        result = assess_certificate_issue(self._release())
        self.assertEqual(result["certificate_count"], 1)
        self.assertTrue(result["all_issuable"])

    def test_mixed_heat_release_owes_one_certificate_each(self):
        specimens = [
            _specimen("a", "h1", 520.0),
            _specimen("b", "h1", 515.0),
            _specimen("c", "h2", 530.0),
            _specimen("d", "h2", 525.0),
        ]
        result = assess_certificate_issue(self._release(specimens=specimens))
        self.assertEqual(result["certificate_count"], 2)
        self.assertTrue(result["all_issuable"])
        self.assertTrue(result["findings"])

    def test_mixed_heat_release_names_the_split_first(self):
        specimens = [
            _specimen("a", "h1", 520.0),
            _specimen("b", "h1", 515.0),
            _specimen("c", "h2", 530.0),
            _specimen("d", "h2", 525.0),
        ]
        result = assess_certificate_issue(self._release(specimens=specimens))
        self.assertIn("spans 2 heats", result["findings"][0])

    def test_each_certificate_carries_its_own_reference(self):
        specimens = [
            _specimen("a", "h1", 520.0),
            _specimen("b", "h1", 515.0),
            _specimen("c", "h2", 530.0),
            _specimen("d", "h2", 525.0),
        ]
        result = assess_certificate_issue(self._release(specimens=specimens))
        references = [c["reference"] for c in result["certificates"]]
        self.assertEqual(len(set(references)), 2)

    def test_mass_uplift_reaches_the_heat_verdict(self):
        result = assess_certificate_issue(
            self._release(released_mass_kg=MASS_INCREMENT_KG * 3.2)
        )
        self.assertFalse(result["all_issuable"])

    def test_missing_key_rejected(self):
        release = self._release()
        del release["product_form"]
        with self.assertRaises(ValueError):
            assess_certificate_issue(release)

    def test_non_mapping_release_rejected(self):
        with self.assertRaises(ValueError):
            assess_certificate_issue(["specimens"])


if __name__ == "__main__":
    unittest.main()
