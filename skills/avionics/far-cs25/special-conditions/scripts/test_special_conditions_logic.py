#!/usr/bin/env python3
"""Gate 3 contract test: special conditions determination.

Exercises scripts/special_conditions_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (FAR-25.17 /
CS-25.17 special-conditions verdicts from the novelty / coverage /
safety rule table, special-condition scope drafting, and
invalid-input raises.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import special_conditions_logic as sc  # noqa: E402


class ClassifyTest(unittest.TestCase):
    def test_fly_by_wire_novel_needs_special_condition(self):
        # Known certification-history case: full fly-by-wire flight
        # control with envelope protection was not covered by the
        # transport standards as written, so special conditions were
        # issued (novel safety-related behavior).
        feature = {
            "feature": "fly-by-wire flight control with envelope protection",
            "novel": True,
            "existing_standard": False,
            "safety_significant": True,
        }
        self.assertEqual(
            sc.classify_feature(feature),
            ("special-condition-required", "novel-safety-behavior"),
        )

    def test_new_technology_with_existing_standard_covered(self):
        # Boundary: novel technology that an existing standard already
        # covers needs no special condition.
        feature = {
            "feature": "digital autopilot within 25.1329 scope",
            "novel": True,
            "existing_standard": True,
            "safety_significant": True,
        }
        self.assertEqual(
            sc.classify_feature(feature),
            ("covered-by-existing", "covered-by-existing-standard"),
        )

    def test_conventional_application_covered(self):
        feature = {
            "feature": "conventional hydraulic flap actuation",
            "novel": False,
            "existing_standard": True,
            "safety_significant": False,
        }
        self.assertEqual(
            sc.classify_feature(feature),
            ("covered-by-existing", "covered-by-existing-standard"),
        )

    def test_uncovered_conventional_feature_requires(self):
        # Design feature outside existing compliance paths still
        # requires a special condition even when not novel.
        feature = {
            "feature": "unconventional cargo restraint layout",
            "novel": False,
            "existing_standard": False,
            "safety_significant": True,
        }
        self.assertEqual(
            sc.classify_feature(feature),
            ("special-condition-required", "uncovered-safety-significant"),
        )

    def test_equivalent_safety_finding_requires(self):
        feature = {
            "feature": "proprietary seat belt anchorage geometry",
            "novel": True,
            "existing_standard": False,
            "safety_significant": True,
            "esf_needed": True,
        }
        self.assertEqual(
            sc.classify_feature(feature),
            ("special-condition-required", "equivalent-safety-finding"),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sc.classify_feature("not a dict")
        with self.assertRaises(ValueError):
            sc.classify_feature({"novel": True})
        with self.assertRaises(ValueError):
            sc.classify_feature(
                {"feature": "", "novel": True, "existing_standard": False,
                 "safety_significant": True}
            )
        with self.assertRaises(ValueError):
            sc.classify_feature(
                {"feature": "x", "novel": 1, "existing_standard": False,
                 "safety_significant": True}
            )
        with self.assertRaises(ValueError):
            sc.classify_feature(
                {"feature": "x", "novel": True, "existing_standard": False,
                 "safety_significant": "yes"}
            )


class DraftScopesTest(unittest.TestCase):
    def test_scopes_required_feature(self):
        feature = {
            "feature": "novel composite wing structure",
            "novel": True,
            "existing_standard": False,
            "safety_significant": True,
        }
        scope = sc.draft_scopes(feature)
        self.assertEqual(scope["subject_area"], "novel composite wing structure")
        self.assertIn("not covered", scope["issue"])
        self.assertIn("analysis", scope["means_of_compliance"])
        self.assertIn("test", scope["means_of_compliance"])

    def test_scope_means_of_compliance_vary_by_category(self):
        uncovered = {
            "feature": "layout not covered by existing standards",
            "novel": False,
            "existing_standard": False,
            "safety_significant": False,
        }
        self.assertEqual(
            sc.draft_scopes(uncovered)["means_of_compliance"], "analysis only"
        )
        novel = {
            "feature": "new sensor technology",
            "novel": True,
            "existing_standard": False,
            "safety_significant": False,
        }
        self.assertEqual(
            sc.draft_scopes(novel)["means_of_compliance"],
            "analysis + test + simulation",
        )

    def test_covered_feature_cannot_be_scoped(self):
        feature = {
            "feature": "conventional hydraulic flap actuation",
            "novel": False,
            "existing_standard": True,
            "safety_significant": False,
        }
        with self.assertRaises(ValueError):
            sc.draft_scopes(feature)


if __name__ == "__main__":
    unittest.main(verbosity=2)
