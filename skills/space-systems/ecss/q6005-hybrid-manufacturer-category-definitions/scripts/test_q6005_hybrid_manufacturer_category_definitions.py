"""Contract tests for the clause 5.2 hybrid procurement category boundary."""

import datetime
import unittest

from q6005_hybrid_manufacturer_category_definitions_logic import (
    CATEGORIES,
    CATEGORY_APPROVED_LINE,
    CATEGORY_LABELS,
    CATEGORY_NO_APPROVED_LINE,
    EXCLUSION_REASONS,
    TECHNOLOGIES,
    approval_covers_line,
    approval_covers_site,
    approval_covers_technology,
    approval_exclusions,
    approval_in_force,
    categorize_manufacturer,
    category_label,
    matching_approvals,
    near_miss_approvals,
    normalize_identifier,
    normalize_standing,
    normalize_technology,
    parse_date,
    validate_approval,
    validate_build,
)

DECISION_DATE = "2026-09-18"

BUILD = {"site": "toulouse-plant", "line": "hybrid-line-2", "technology": "thick-film"}


def approval(
    approval_id="ap-1",
    site="toulouse-plant",
    line="hybrid-line-2",
    technologies=("thick-film",),
    issued="2024-03-01",
    valid_until="2028-03-01",
    standing="valid",
):
    return {
        "id": approval_id,
        "site": site,
        "line": line,
        "technologies": list(technologies),
        "issued": issued,
        "valid_until": valid_until,
        "standing": standing,
    }


class NormalisationTests(unittest.TestCase):
    def test_technology_alias_resolves(self):
        self.assertEqual(normalize_technology("Thick Film"), "thick-film")

    def test_acronym_technology_resolves(self):
        self.assertEqual(normalize_technology("MCM"), "multi-chip-module")

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            normalize_technology("printed-circuit")

    def test_non_string_technology_rejected(self):
        with self.assertRaises(ValueError):
            normalize_technology(3)

    def test_identifier_is_canonicalised(self):
        self.assertEqual(normalize_identifier(" Hybrid Line 2 ", "line"), "hybrid-line-2")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_identifier("   ", "site")

    def test_standing_is_canonicalised(self):
        self.assertEqual(normalize_standing("Withdrawn"), "withdrawn")

    def test_unknown_standing_rejected(self):
        with self.assertRaises(ValueError):
            normalize_standing("provisional")

    def test_iso_date_is_parsed(self):
        self.assertEqual(parse_date(DECISION_DATE), datetime.date(2026, 9, 18))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2026/09/18")

    def test_impossible_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2026-13-01")

    def test_every_technology_is_canonical(self):
        for technology in TECHNOLOGIES:
            self.assertEqual(normalize_technology(technology), technology)


class RecordValidationTests(unittest.TestCase):
    def test_build_is_canonicalised(self):
        self.assertEqual(validate_build(BUILD)["technology"], "thick-film")

    def test_build_missing_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_build({"site": "toulouse-plant", "technology": "thick-film"})

    def test_non_mapping_build_rejected(self):
        with self.assertRaises(ValueError):
            validate_build(["toulouse-plant"])

    def test_approval_technologies_are_deduplicated(self):
        record = validate_approval(approval(technologies=["thick-film", "Thick Film"]))
        self.assertEqual(record["technologies"], ("thick-film",))

    def test_approval_with_no_technology_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval(approval(technologies=[]))

    def test_approval_missing_expiry_rejected(self):
        record = approval()
        del record["valid_until"]
        with self.assertRaises(ValueError):
            validate_approval(record)

    def test_approval_expiring_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval(approval(issued="2027-01-01", valid_until="2026-01-01"))

    def test_non_mapping_approval_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval("ap-1")


class CoverageTests(unittest.TestCase):
    def test_matching_approval_covers_the_site(self):
        self.assertTrue(approval_covers_site(approval(), BUILD))

    def test_other_site_does_not_cover(self):
        self.assertFalse(approval_covers_site(approval(site="milan-plant"), BUILD))

    def test_matching_approval_covers_the_line(self):
        self.assertTrue(approval_covers_line(approval(), BUILD))

    def test_same_site_other_line_does_not_cover(self):
        self.assertFalse(approval_covers_line(approval(line="hybrid-line-1"), BUILD))

    def test_same_line_name_at_another_site_does_not_cover(self):
        self.assertFalse(approval_covers_line(approval(site="milan-plant"), BUILD))

    def test_technology_coverage_is_per_technology(self):
        self.assertTrue(approval_covers_technology(approval(), BUILD))
        self.assertFalse(
            approval_covers_technology(approval(technologies=["thin-film"]), BUILD)
        )

    def test_multi_technology_approval_covers_each_listed_one(self):
        record = approval(technologies=["thin-film", "thick-film"])
        self.assertTrue(approval_covers_technology(record, BUILD))

    def test_in_force_on_a_normal_date(self):
        self.assertTrue(approval_in_force(approval(), DECISION_DATE))

    def test_in_force_on_the_expiry_date_itself(self):
        self.assertTrue(approval_in_force(approval(valid_until=DECISION_DATE), DECISION_DATE))

    def test_not_in_force_the_day_after_expiry(self):
        self.assertFalse(
            approval_in_force(approval(valid_until="2026-09-17"), DECISION_DATE)
        )

    def test_suspension_defeats_a_distant_expiry(self):
        record = approval(valid_until="2033-01-01", standing="suspended")
        self.assertFalse(approval_in_force(record, DECISION_DATE))


class ExclusionTests(unittest.TestCase):
    def test_a_covering_approval_has_no_exclusion(self):
        self.assertEqual(approval_exclusions(approval(), BUILD, DECISION_DATE), ())

    def test_wrong_site_is_a_single_named_reason(self):
        reasons = approval_exclusions(approval(site="milan-plant"), BUILD, DECISION_DATE)
        self.assertEqual(reasons, ("different-site",))

    def test_wrong_line_at_the_right_site_is_reported_as_a_line_miss(self):
        reasons = approval_exclusions(approval(line="hybrid-line-9"), BUILD, DECISION_DATE)
        self.assertEqual(reasons, ("different-line",))

    def test_wrong_technology_is_reported_alone(self):
        reasons = approval_exclusions(
            approval(technologies=["thin-film"]), BUILD, DECISION_DATE
        )
        self.assertEqual(reasons, ("technology-not-covered",))

    def test_lapsed_approval_is_reported(self):
        reasons = approval_exclusions(
            approval(valid_until="2025-01-01"), BUILD, DECISION_DATE
        )
        self.assertEqual(reasons, ("lapsed",))

    def test_not_yet_in_force_approval_is_reported(self):
        reasons = approval_exclusions(
            approval(issued="2027-01-01", valid_until="2031-01-01"), BUILD, DECISION_DATE
        )
        self.assertEqual(reasons, ("not-yet-in-force",))

    def test_suspended_approval_is_reported_rather_than_lapsed(self):
        reasons = approval_exclusions(
            approval(valid_until="2025-01-01", standing="suspended"), BUILD, DECISION_DATE
        )
        self.assertEqual(reasons, ("suspended",))

    def test_several_misses_are_all_reported(self):
        reasons = approval_exclusions(
            approval(site="milan-plant", technologies=["thin-film"], valid_until="2025-01-01"),
            BUILD,
            DECISION_DATE,
        )
        self.assertEqual(len(reasons), 3)

    def test_every_reason_is_a_declared_reason(self):
        reasons = approval_exclusions(
            approval(site="milan-plant", technologies=["thin-film"], standing="withdrawn"),
            BUILD,
            DECISION_DATE,
        )
        for reason in reasons:
            self.assertIn(reason, EXCLUSION_REASONS)


class MatchingTests(unittest.TestCase):
    def test_matching_returns_the_covering_approval_id(self):
        self.assertEqual(matching_approvals([approval()], BUILD, DECISION_DATE), ("ap-1",))

    def test_matching_ignores_an_approval_for_another_line(self):
        records = [approval("ap-1", line="hybrid-line-1")]
        self.assertEqual(matching_approvals(records, BUILD, DECISION_DATE), ())

    def test_matching_finds_the_one_covering_approval_among_several(self):
        records = [
            approval("ap-1", site="milan-plant"),
            approval("ap-2", technologies=["thin-film"]),
            approval("ap-3"),
        ]
        self.assertEqual(matching_approvals(records, BUILD, DECISION_DATE), ("ap-3",))

    def test_matching_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            matching_approvals(approval(), BUILD, DECISION_DATE)

    def test_near_miss_names_the_single_reason(self):
        records = [approval("ap-1", technologies=["thin-film"])]
        self.assertEqual(
            near_miss_approvals(records, BUILD, DECISION_DATE),
            (("ap-1", "technology-not-covered"),),
        )

    def test_a_double_miss_is_not_a_near_miss(self):
        records = [approval("ap-1", site="milan-plant", technologies=["thin-film"])]
        self.assertEqual(near_miss_approvals(records, BUILD, DECISION_DATE), ())

    def test_a_covering_approval_is_not_a_near_miss(self):
        self.assertEqual(near_miss_approvals([approval()], BUILD, DECISION_DATE), ())


class CategoryTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "build": dict(BUILD),
            "approvals": [approval()],
            "decision_date": DECISION_DATE,
        }
        spec.update(overrides)
        return spec

    def test_covering_approval_gives_the_approved_line_category(self):
        result = categorize_manufacturer(self._spec())
        self.assertEqual(result["category"], CATEGORY_APPROVED_LINE)
        self.assertEqual(result["findings"], [])

    def test_no_approval_gives_the_other_category(self):
        result = categorize_manufacturer(self._spec(approvals=[]))
        self.assertEqual(result["category"], CATEGORY_NO_APPROVED_LINE)
        self.assertEqual(len(result["findings"]), 1)

    def test_approval_for_a_sister_line_does_not_promote_the_maker(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval(line="hybrid-line-1")])
        )
        self.assertEqual(result["category"], CATEGORY_NO_APPROVED_LINE)
        self.assertEqual(result["near_misses"], (("ap-1", "different-line"),))

    def test_approval_for_another_technology_does_not_promote_the_maker(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval(technologies=["microwave-hybrid"])])
        )
        self.assertEqual(result["category"], CATEGORY_NO_APPROVED_LINE)
        self.assertTrue(any("technology-not-covered" in f for f in result["findings"]))

    def test_lapsed_approval_drops_the_maker_into_the_other_category(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval(valid_until="2026-09-17")])
        )
        self.assertEqual(result["category"], CATEGORY_NO_APPROVED_LINE)

    def test_approval_expiring_on_the_decision_date_still_counts(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval(valid_until=DECISION_DATE)])
        )
        self.assertEqual(result["category"], CATEGORY_APPROVED_LINE)

    def test_suspended_approval_drops_the_maker_into_the_other_category(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval(standing="suspended")])
        )
        self.assertEqual(result["category"], CATEGORY_NO_APPROVED_LINE)

    def test_exclusions_are_reported_per_approval(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval("ap-1", site="milan-plant"), approval("ap-2")])
        )
        self.assertEqual(result["exclusions"], {"ap-1": ("different-site",)})

    def test_one_covering_approval_is_enough(self):
        result = categorize_manufacturer(
            self._spec(
                approvals=[approval("ap-1", site="milan-plant"), approval("ap-2")]
            )
        )
        self.assertEqual(result["category"], CATEGORY_APPROVED_LINE)
        self.assertEqual(result["matching_approvals"], ("ap-2",))

    def test_repeated_approval_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize_manufacturer(
                self._spec(approvals=[approval("ap-1"), approval("ap-1", line="hybrid-line-4")])
            )

    def test_approval_count_is_reported(self):
        result = categorize_manufacturer(
            self._spec(approvals=[approval("ap-1"), approval("ap-2", site="milan-plant")])
        )
        self.assertEqual(result["approval_count"], 2)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["decision_date"]
        with self.assertRaises(ValueError):
            categorize_manufacturer(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            categorize_manufacturer(["build"])

    def test_non_sequence_approvals_rejected(self):
        with self.assertRaises(ValueError):
            categorize_manufacturer(self._spec(approvals=approval()))

    def test_label_is_returned_with_the_category(self):
        result = categorize_manufacturer(self._spec())
        self.assertEqual(result["category_label"], CATEGORY_LABELS[CATEGORY_APPROVED_LINE])

    def test_only_two_categories_exist(self):
        self.assertEqual(len(CATEGORIES), 2)
        self.assertEqual(sorted(CATEGORY_LABELS), sorted(CATEGORIES))

    def test_unknown_category_label_rejected(self):
        with self.assertRaises(ValueError):
            category_label("category-3")


if __name__ == "__main__":
    unittest.main()
