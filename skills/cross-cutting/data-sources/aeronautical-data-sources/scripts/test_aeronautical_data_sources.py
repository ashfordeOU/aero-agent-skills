#!/usr/bin/env python3
"""Gate 3 contract test: aeronautical data source registry and citation.

Exercises scripts/aeronautical_data_sources_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 - the
registry check (authoritative data type, publisher class, edition,
review status), the approved or review-required verdict, the
credibility score heuristic (regulatory highest, then industry, then
vendor, then community), and the citation line format for the report
(publisher, edition, access date). Analytic checks:

- register_source builds the entry with all seven fields; unknown
  source_type, publisher_class, or review_status raise ValueError
- authoritative_type_ok: regulatory-data passes, "other" fails
- review_status_ok: approved passes, "draft" fails
- source_verdict: approved -> approved; in-review, unreviewed, and
  superseded -> review-required
- credibility_score: regulatory approved 10 (highest), industry 7,
  vendor 4, community 2; vendor in-review 2; regulatory superseded 1
- format_citation: "ESDU 72018, Edition 3, ESDU International,
  accessed 2026-09-01."
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aeronautical_data_sources_logic as ads  # noqa: E402


def make_source(review_status="approved", publisher_class="regulatory"):
    return ads.register_source(
        "ESDU 72018",
        "aerodynamic-database",
        "ESDU International",
        publisher_class,
        "Edition 3",
        review_status,
        "2026-09-01",
    )


class RegisterSourceTest(unittest.TestCase):
    def test_entry_fields(self):
        s = make_source()
        self.assertEqual(
            s,
            {
                "name": "ESDU 72018",
                "source_type": "aerodynamic-database",
                "publisher": "ESDU International",
                "publisher_class": "regulatory",
                "edition": "Edition 3",
                "review_status": "approved",
                "access_date": "2026-09-01",
            },
        )

    def test_regulatory_data_type_registers(self):
        s = ads.register_source(
            "14 CFR Part 25",
            "regulatory-data",
            "FAA",
            "regulatory",
            "Amendment 25-146",
            "approved",
            "2026-09-01",
        )
        self.assertEqual(s["source_type"], "regulatory-data")
        self.assertTrue(ads.authoritative_type_ok(s["source_type"]))

    def test_unknown_source_type_raises(self):
        with self.assertRaises(ValueError):
            ads.register_source(
                "X", "social-media-post", "X Corp", "vendor",
                "1", "approved", "2026-09-01",
            )

    def test_unknown_publisher_class_raises(self):
        with self.assertRaises(ValueError):
            ads.register_source(
                "X", "other", "X Corp", "friend",
                "1", "approved", "2026-09-01",
            )

    def test_unknown_review_status_raises(self):
        with self.assertRaises(ValueError):
            ads.register_source(
                "X", "other", "X Corp", "vendor",
                "1", "draft", "2026-09-01",
            )

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            ads.register_source(
                "", "other", "X Corp", "vendor",
                "1", "approved", "2026-09-01",
            )


class AuthoritativeTypeTest(unittest.TestCase):
    def test_all_authoritative_types_ok(self):
        for t in (
            "atmospheric-model",
            "aerodynamic-database",
            "materials-properties",
            "standard-part-library",
            "regulatory-data",
        ):
            self.assertTrue(ads.authoritative_type_ok(t), t)

    def test_other_is_not_authoritative(self):
        self.assertFalse(ads.authoritative_type_ok("other"))

    def test_unknown_type_not_ok(self):
        self.assertFalse(ads.authoritative_type_ok("blog-post"))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ads.authoritative_type_ok(7)


class ReviewStatusOkTest(unittest.TestCase):
    def test_recognized_statuses(self):
        for st in ("approved", "in-review", "unreviewed", "superseded"):
            self.assertTrue(ads.review_status_ok(st), st)

    def test_unrecognized_status_fails(self):
        self.assertFalse(ads.review_status_ok("draft"))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ads.review_status_ok(None)


class SourceVerdictTest(unittest.TestCase):
    def test_approved_source_passes(self):
        self.assertEqual(ads.source_verdict(make_source("approved")), "approved")

    def test_in_review_requires_review(self):
        self.assertEqual(ads.source_verdict(make_source("in-review")), "review-required")

    def test_unreviewed_requires_review(self):
        self.assertEqual(ads.source_verdict(make_source("unreviewed")), "review-required")

    def test_superseded_requires_review(self):
        self.assertEqual(ads.source_verdict(make_source("superseded")), "review-required")

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ads.source_verdict({"publisher_class": "vendor"})


class CredibilityScoreTest(unittest.TestCase):
    def test_regulatory_scores_highest(self):
        # Regulatory approved 10 beats every other class.
        regulatory = ads.credibility_score(make_source("approved", "regulatory"))
        for cls, expected in (
            ("industry", 7),
            ("vendor", 4),
            ("community", 2),
        ):
            other = ads.credibility_score(make_source("approved", cls))
            self.assertGreater(regulatory, other)
            self.assertEqual(other, expected)
        self.assertEqual(regulatory, 10)

    def test_vendor_in_review_reduced_with_floor(self):
        # 4 - 2 = 2, floor at 1.
        self.assertEqual(
            ads.credibility_score(make_source("in-review", "vendor")), 2
        )
        self.assertEqual(
            ads.credibility_score(make_source("unreviewed", "community")), 1
        )

    def test_superseded_capped_at_one(self):
        # Even a regulatory source scores 1 once superseded.
        self.assertEqual(
            ads.credibility_score(make_source("superseded", "regulatory")), 1
        )

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ads.credibility_score({"name": "X"})


class CitationFormatTest(unittest.TestCase):
    def test_citation_line_format(self):
        # Name, Edition, Publisher, accessed ACCESS_DATE.
        self.assertEqual(
            ads.format_citation(make_source()),
            "ESDU 72018, Edition 3, ESDU International, accessed 2026-09-01.",
        )

    def test_citation_carries_publisher_edition_access_date(self):
        line = ads.format_citation(make_source())
        self.assertIn("ESDU International", line)
        self.assertIn("Edition 3", line)
        self.assertIn("2026-09-01", line)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ads.format_citation({"name": "X"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
