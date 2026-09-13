#!/usr/bin/env python3
"""Gate 3 contract test for e20-power-handling-design-and-verification.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e20_power_handling_design_and_verification.py
"""

import math
import unittest

import e20_power_handling_design_and_verification_logic as logic


def substantiation(**overrides):
    base = {
        "method": "verification-by-test",
        "applied_level_w": 400.0,
        "dwell_minutes": 45.0,
    }
    base.update(overrides)
    return base


def element(**overrides):
    """A compliant baseline chain element, overridable field by field."""
    base = {
        "id": "FLT-01",
        "category": "filter-or-diplexer",
        "max_operating_w": 100.0,
        "design_capability_w": 400.0,
        "substantiation": substantiation(),
    }
    base.update(overrides)
    return base


class TestNormalization(unittest.TestCase):
    def test_category_normalizes(self):
        self.assertEqual(logic.normalize_category(" Antenna-Feed "), "antenna-feed")

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_category("gearbox")

    def test_non_string_category_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_category(4)

    def test_method_alias_measurement(self):
        self.assertEqual(logic.normalize_method("measurement"), "verification-by-test")

    def test_method_alias_heritage(self):
        self.assertEqual(logic.normalize_method("heritage"), "verification-by-similarity")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_method("engineering-judgement")

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_method("   ")


class TestMarginResolution(unittest.TestCase):
    def test_field_governed_category_carries_the_larger_allowance(self):
        self.assertAlmostEqual(
            logic.resolve_margin_db("filter-or-diplexer", "verification-by-test"),
            6.0,
            places=9,
        )

    def test_thermally_governed_category_carries_the_smaller_allowance(self):
        self.assertAlmostEqual(
            logic.resolve_margin_db("waveguide-run", "verification-by-test"),
            3.0,
            places=9,
        )

    def test_analysis_route_adds_model_uncertainty(self):
        self.assertAlmostEqual(
            logic.resolve_margin_db("waveguide-run", "verification-by-analysis"),
            6.0,
            places=9,
        )

    def test_similarity_route_adds_the_most(self):
        self.assertAlmostEqual(
            logic.resolve_margin_db("coaxial-line", "similarity"), 7.0, places=9
        )

    def test_programme_override_replaces_the_category_allowance(self):
        value = logic.resolve_margin_db(
            "filter-or-diplexer",
            "verification-by-analysis",
            {"filter-or-diplexer": 4.5},
        )
        self.assertAlmostEqual(value, 7.5, places=9)

    def test_override_for_another_category_is_ignored(self):
        value = logic.resolve_margin_db(
            "antenna-feed", "verification-by-test", {"coaxial-line": 1.0}
        )
        self.assertAlmostEqual(value, 6.0, places=9)

    def test_negative_agreed_margin_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_margin_db(
                "antenna-feed", "verification-by-test", {"antenna-feed": -1.0}
            )

    def test_non_numeric_agreed_margin_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_margin_db(
                "antenna-feed", "verification-by-test", {"antenna-feed": "6 dB"}
            )

    def test_non_mapping_agreed_margins_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_margin_db("antenna-feed", "verification-by-test", [6.0])


class TestRequiredLevel(unittest.TestCase):
    def test_three_decibels_doubles_the_level(self):
        value = logic.required_design_level_w(100.0, 3.0102999566398121)
        self.assertAlmostEqual(value, 200.0, places=6)

    def test_six_decibels_quadruples_the_level(self):
        value = logic.required_design_level_w(100.0, 2 * 3.0102999566398121)
        self.assertAlmostEqual(value, 400.0, places=6)

    def test_zero_margin_leaves_the_level(self):
        self.assertAlmostEqual(logic.required_design_level_w(75.0, 0.0), 75.0, places=9)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            logic.required_design_level_w(100.0, -1.0)

    def test_zero_operating_level_raises(self):
        with self.assertRaises(ValueError):
            logic.required_design_level_w(0.0, 3.0)

    def test_non_numeric_margin_raises(self):
        with self.assertRaises(ValueError):
            logic.required_design_level_w(100.0, "3 dB")

    def test_boolean_operating_level_raises(self):
        with self.assertRaises(ValueError):
            logic.required_design_level_w(True, 3.0)

    def test_demonstrated_margin_of_a_quadrupled_capability(self):
        self.assertAlmostEqual(
            logic.demonstrated_margin_db(400.0, 100.0), 10.0 * math.log10(4.0), places=9
        )

    def test_demonstrated_margin_is_zero_at_the_operating_level(self):
        self.assertAlmostEqual(logic.demonstrated_margin_db(50.0, 50.0), 0.0, places=12)

    def test_demonstrated_margin_rejects_zero_capability(self):
        with self.assertRaises(ValueError):
            logic.demonstrated_margin_db(0.0, 50.0)


class TestLevelComparison(unittest.TestCase):
    def test_exact_equality_meets_the_level(self):
        self.assertTrue(logic.meets_required_level(398.0, 398.0))

    def test_representation_shortfall_is_absorbed(self):
        required = 0.1 + 0.2  # a sum of carrier powers, one place over 0.3
        self.assertGreater(required, 0.3)
        self.assertTrue(logic.meets_required_level(0.3, required))

    def test_real_shortfall_is_rejected(self):
        self.assertFalse(logic.meets_required_level(397.0, 398.0))

    def test_surplus_meets_the_level(self):
        self.assertTrue(logic.meets_required_level(500.0, 398.0))


class TestSubstantiation(unittest.TestCase):
    def test_measured_substantiation_at_level_has_no_findings(self):
        method, findings = logic.substantiation_findings(substantiation(), 398.0)
        self.assertEqual(method, "verification-by-test")
        self.assertEqual(findings, [])

    def test_measured_substantiation_without_applied_level_is_flagged(self):
        block = substantiation()
        block.pop("applied_level_w")
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertIn("substantiation-missing-applied-level", findings)

    def test_measured_substantiation_without_dwell_is_flagged(self):
        block = substantiation()
        block.pop("dwell_minutes")
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertIn("substantiation-missing-dwell", findings)

    def test_short_dwell_is_flagged(self):
        _, findings = logic.substantiation_findings(
            substantiation(dwell_minutes=5.0), 398.0
        )
        self.assertTrue(any(f.startswith("dwell-below-agreed-minimum") for f in findings))

    def test_dwell_exactly_at_the_minimum_passes(self):
        _, findings = logic.substantiation_findings(
            substantiation(dwell_minutes=logic.MIN_DWELL_MINUTES), 398.0
        )
        self.assertEqual(findings, [])

    def test_applied_level_below_required_is_flagged(self):
        _, findings = logic.substantiation_findings(
            substantiation(applied_level_w=300.0), 398.0
        )
        self.assertTrue(
            any(
                f.startswith("applied-level-below-required-design-level")
                for f in findings
            )
        )

    def test_negative_dwell_raises(self):
        with self.assertRaises(ValueError):
            logic.substantiation_findings(substantiation(dwell_minutes=-1.0), 398.0)

    def test_zero_applied_level_raises(self):
        with self.assertRaises(ValueError):
            logic.substantiation_findings(substantiation(applied_level_w=0.0), 398.0)

    def test_correlated_model_at_level_has_no_findings(self):
        block = {
            "method": "verification-by-analysis",
            "model_reference": "MOD-0031",
            "model_correlated": True,
            "predicted_capability_w": 500.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertEqual(findings, [])

    def test_uncorrelated_model_is_flagged(self):
        block = {
            "method": "verification-by-analysis",
            "model_reference": "MOD-0031",
            "model_correlated": False,
            "predicted_capability_w": 500.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertTrue(
            any(f.startswith("analysis-model-not-correlated") for f in findings)
        )

    def test_model_without_reference_is_flagged(self):
        block = {
            "method": "analysis",
            "model_correlated": True,
            "predicted_capability_w": 500.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertIn("substantiation-missing-model-reference", findings)

    def test_predicted_capability_below_required_is_flagged(self):
        block = {
            "method": "analysis",
            "model_reference": "MOD-0031",
            "model_correlated": True,
            "predicted_capability_w": 100.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertTrue(
            any(
                f.startswith("predicted-capability-below-required-design-level")
                for f in findings
            )
        )

    def test_missing_predicted_capability_is_flagged(self):
        block = {
            "method": "analysis",
            "model_reference": "MOD-0031",
            "model_correlated": True,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertIn("substantiation-missing-predicted-capability", findings)

    def test_heritage_argument_with_delta_environment_has_no_findings(self):
        block = {
            "method": "verification-by-similarity",
            "heritage_reference": "HER-0009",
            "delta_environment": "same vented waveguide-run, orbit altitude raised",
            "heritage_capability_w": 600.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertEqual(findings, [])

    def test_heritage_argument_without_delta_environment_is_flagged(self):
        block = {
            "method": "similarity",
            "heritage_reference": "HER-0009",
            "heritage_capability_w": 600.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertTrue(
            any(f.startswith("similarity-without-delta-environment") for f in findings)
        )

    def test_heritage_argument_without_reference_is_flagged(self):
        block = {
            "method": "similarity",
            "delta_environment": "identical feed geometry",
            "heritage_capability_w": 600.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertIn("substantiation-missing-heritage-reference", findings)

    def test_heritage_capability_below_required_is_flagged(self):
        block = {
            "method": "similarity",
            "heritage_reference": "HER-0009",
            "delta_environment": "identical feed geometry",
            "heritage_capability_w": 120.0,
        }
        _, findings = logic.substantiation_findings(block, 398.0)
        self.assertTrue(
            any(
                f.startswith("heritage-capability-below-required-design-level")
                for f in findings
            )
        )

    def test_non_mapping_substantiation_raises(self):
        with self.assertRaises(ValueError):
            logic.substantiation_findings("tested at 400 W", 398.0)

    def test_unknown_substantiation_method_raises(self):
        with self.assertRaises(ValueError):
            logic.substantiation_findings({"method": "vibes"}, 398.0)


class TestElementEvaluation(unittest.TestCase):
    def test_baseline_element_is_compliant(self):
        result = logic.evaluate_element(element())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["agreed_margin_db"], 6.0, places=9)
        self.assertAlmostEqual(result["required_design_level_w"], 398.1071705534972, places=6)
        self.assertAlmostEqual(result["margin_shortfall_db"], 0.0, places=9)

    def test_design_capability_shortfall_is_flagged(self):
        result = logic.evaluate_element(element(design_capability_w=200.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any(
                f.startswith("design-capability-below-required-design-level")
                for f in result["findings"]
            )
        )
        self.assertGreater(result["margin_shortfall_db"], 2.9)

    def test_analysis_route_raises_the_required_level(self):
        result = logic.evaluate_element(
            element(
                substantiation={
                    "method": "verification-by-analysis",
                    "model_reference": "MOD-0031",
                    "model_correlated": True,
                    "predicted_capability_w": 400.0,
                }
            )
        )
        self.assertAlmostEqual(result["agreed_margin_db"], 9.0, places=9)
        self.assertFalse(result["compliant"])

    def test_demonstrated_margin_is_reported(self):
        result = logic.evaluate_element(element())
        self.assertAlmostEqual(
            result["demonstrated_margin_db"], 10.0 * math.log10(4.0), places=9
        )

    def test_thermally_governed_element_needs_less_capability(self):
        result = logic.evaluate_element(
            element(
                id="WG-02",
                category="waveguide-run",
                design_capability_w=200.0,
                substantiation=substantiation(applied_level_w=200.0),
            )
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["agreed_margin_db"], 3.0, places=9)

    def test_element_without_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_element(element(id="  "))

    def test_element_with_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_element(element(category="flange"))

    def test_element_with_zero_operating_level_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_element(element(max_operating_w=0.0))

    def test_element_without_substantiation_raises(self):
        item = dict(element())
        item.pop("substantiation")
        with self.assertRaises(ValueError):
            logic.evaluate_element(item)

    def test_non_mapping_element_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_element("FLT-01")

    def test_agreed_override_can_make_an_element_compliant(self):
        item = element(design_capability_w=200.0, substantiation=substantiation(applied_level_w=200.0))
        self.assertFalse(logic.evaluate_element(item)["compliant"])
        relaxed = logic.evaluate_element(item, {"filter-or-diplexer": 3.0})
        self.assertTrue(relaxed["compliant"])
        self.assertAlmostEqual(relaxed["agreed_margin_db"], 3.0, places=9)


class TestChainAssessment(unittest.TestCase):
    def _chain(self):
        return [
            element(id="FLT-01"),
            element(
                id="WG-01",
                category="waveguide-run",
                design_capability_w=250.0,
                substantiation=substantiation(applied_level_w=220.0),
            ),
            element(
                id="FEED-01",
                category="antenna-feed",
                max_operating_w=50.0,
                design_capability_w=600.0,
                substantiation={
                    "method": "verification-by-similarity",
                    "heritage_reference": "HER-0009",
                    "delta_environment": "same feed geometry, higher operating level",
                    "heritage_capability_w": 700.0,
                },
            ),
        ]

    def test_clean_chain_is_compliant(self):
        report = logic.assess_power_handling_design_and_verification(self._chain())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["finding_total"], 0)

    def test_worst_element_is_the_tightest_against_its_own_margin(self):
        report = logic.assess_power_handling_design_and_verification(self._chain())
        self.assertEqual(report["worst_element_id"], "FLT-01")
        self.assertAlmostEqual(report["worst_margin_shortfall_db"], 0.0, places=9)

    def test_findings_are_grouped_by_code(self):
        chain = self._chain()
        chain[0]["design_capability_w"] = 150.0
        chain[1]["design_capability_w"] = 120.0
        report = logic.assess_power_handling_design_and_verification(chain)
        self.assertEqual(
            report["finding_counts"]["design-capability-below-required-design-level"], 2
        )
        self.assertFalse(report["compliant"])

    def test_shortfall_is_quantified_in_decibels(self):
        chain = self._chain()
        chain[0]["design_capability_w"] = 100.0
        report = logic.assess_power_handling_design_and_verification(chain)
        self.assertEqual(report["worst_element_id"], "FLT-01")
        self.assertAlmostEqual(report["worst_margin_shortfall_db"], 6.0, places=9)

    def test_agreed_margins_propagate_to_every_element(self):
        chain = self._chain()
        chain[0]["design_capability_w"] = 250.0
        chain[0]["substantiation"] = substantiation(applied_level_w=250.0)
        report = logic.assess_power_handling_design_and_verification(
            chain, {"filter-or-diplexer": 3.0}
        )
        self.assertTrue(report["compliant"])

    def test_duplicate_identifier_raises(self):
        chain = self._chain()
        chain[1]["id"] = "FLT-01"
        with self.assertRaises(ValueError):
            logic.assess_power_handling_design_and_verification(chain)

    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_power_handling_design_and_verification([])

    def test_non_list_chain_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_power_handling_design_and_verification(element())

    def test_evidence_failure_alone_makes_the_chain_non_compliant(self):
        chain = self._chain()
        chain[2]["substantiation"].pop("delta_environment")
        report = logic.assess_power_handling_design_and_verification(chain)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["finding_total"], 1)


if __name__ == "__main__":
    unittest.main()
