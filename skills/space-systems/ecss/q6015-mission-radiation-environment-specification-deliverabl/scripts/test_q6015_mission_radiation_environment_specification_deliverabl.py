"""Contract test for the radiation environment specification leaf."""

import unittest

from q6015_mission_radiation_environment_specification_deliverabl_logic import (
    FINDING_CONFIDENCE_MISPLACED,
    FINDING_ITEM_MISSING,
    FINDING_LOW_CONFIDENCE,
    FINDING_NO_ACTIVITY,
    FINDING_NO_CONFIDENCE,
    FINDING_NO_MODEL,
    FINDING_NO_STANDARD,
    FINDING_NO_VERSION,
    FINDING_SPAN_TOO_THICK,
    MINIMUM_CONFIDENCE_PERCENT,
    REQUIRED_CONTENT,
    assess_environment_specification,
    completeness_ratio,
    entry_findings,
    missing_required_items,
    shielding_coverage_findings,
    validate_entry,
    validate_specification,
)


def modelled(item, **kw):
    record = {
        "item": item,
        "model_identifier": "reference-model",
        "model_version": "3.1",
        "reference_standard": "ecss-e-st-10-04",
    }
    record.update(kw)
    return record


def contents():
    return [
        {"item": "mission-and-orbit-definition"},
        modelled("trapped-proton-environment", solar_activity_condition="solar-minimum"),
        modelled(
            "trapped-electron-environment", solar_activity_condition="solar-maximum"
        ),
        modelled("solar-particle-event-environment", confidence_level_percent=95.0),
        modelled(
            "galactic-cosmic-ray-environment",
            solar_activity_condition="mission-averaged",
        ),
        {"item": "ionising-dose-depth-curve", "shielding_span_mm": [0.5, 20.0]},
        {"item": "displacement-damage-fluence", "shielding_span_mm": [0.5, 20.0]},
        {"item": "linear-energy-transfer-spectra"},
        {"item": "shielding-assumptions"},
    ]


def spec(**kw):
    record = {"contents": contents(), "thinnest_equipment_shielding_mm": 1.0}
    record.update(kw)
    return record


class TestEntryValidation(unittest.TestCase):
    def test_unknown_item_raises(self):
        with self.assertRaises(ValueError):
            validate_entry({"item": "astrology-environment"})

    def test_confidence_at_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(
                modelled(
                    "solar-particle-event-environment", confidence_level_percent=100.0
                )
            )

    def test_confidence_at_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(
                modelled(
                    "solar-particle-event-environment", confidence_level_percent=0.0
                )
            )

    def test_unknown_activity_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(
                modelled(
                    "trapped-proton-environment",
                    solar_activity_condition="solar-whenever",
                )
            )

    def test_descending_shielding_span_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(
                {"item": "ionising-dose-depth-curve", "shielding_span_mm": [20.0, 0.5]}
            )

    def test_blank_model_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(
                modelled("trapped-proton-environment", model_identifier="  ")
            )

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_entry("trapped-proton-environment")


class TestSpecificationValidation(unittest.TestCase):
    def test_valid_specification_normalizes(self):
        normalized = validate_specification(spec())
        self.assertEqual(len(normalized["contents"]), len(REQUIRED_CONTENT))

    def test_duplicate_item_raises(self):
        records = contents() + [{"item": "shielding-assumptions"}]
        with self.assertRaises(ValueError):
            validate_specification(spec(contents=records))

    def test_empty_contents_raises(self):
        with self.assertRaises(ValueError):
            validate_specification({"contents": []})

    def test_non_positive_thinnest_shielding_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(thinnest_equipment_shielding_mm=0.0))


class TestMissingContent(unittest.TestCase):
    def test_full_document_is_missing_nothing(self):
        self.assertEqual(missing_required_items(spec()), [])

    def test_dropped_item_is_reported(self):
        records = [c for c in contents() if c["item"] != "shielding-assumptions"]
        self.assertEqual(
            missing_required_items(spec(contents=records)), ["shielding-assumptions"]
        )

    def test_completeness_ratio_is_one_when_full(self):
        self.assertAlmostEqual(completeness_ratio(spec()), 1.0, places=9)

    def test_completeness_ratio_drops_with_a_missing_item(self):
        records = [c for c in contents() if c["item"] != "shielding-assumptions"]
        expected = (len(REQUIRED_CONTENT) - 1) / float(len(REQUIRED_CONTENT))
        self.assertAlmostEqual(
            completeness_ratio(spec(contents=records)), expected, places=9
        )

    def test_optional_items_do_not_change_the_ratio(self):
        records = contents() + [
            modelled(
                "secondary-particle-environment",
            )
        ]
        self.assertAlmostEqual(
            completeness_ratio(spec(contents=records)), 1.0, places=9
        )


class TestEntryFindings(unittest.TestCase):
    def test_a_well_declared_model_has_no_findings(self):
        self.assertEqual(
            entry_findings(
                modelled(
                    "trapped-proton-environment",
                    solar_activity_condition="solar-minimum",
                )
            ),
            [],
        )

    def test_missing_model_identifier_is_a_finding(self):
        record = modelled(
            "trapped-proton-environment", solar_activity_condition="solar-minimum"
        )
        record["model_identifier"] = None
        self.assertIn(
            "%s:trapped-proton-environment" % FINDING_NO_MODEL,
            entry_findings(record),
        )

    def test_missing_model_version_is_a_finding(self):
        record = modelled(
            "trapped-electron-environment", solar_activity_condition="solar-maximum"
        )
        record["model_version"] = None
        self.assertIn(
            "%s:trapped-electron-environment" % FINDING_NO_VERSION,
            entry_findings(record),
        )

    def test_missing_reference_standard_is_a_finding(self):
        record = modelled(
            "galactic-cosmic-ray-environment",
            solar_activity_condition="mission-averaged",
        )
        record["reference_standard"] = None
        self.assertIn(
            "%s:galactic-cosmic-ray-environment" % FINDING_NO_STANDARD,
            entry_findings(record),
        )

    def test_statistical_model_without_confidence_is_a_finding(self):
        record = modelled("solar-particle-event-environment")
        self.assertIn(
            "%s:solar-particle-event-environment" % FINDING_NO_CONFIDENCE,
            entry_findings(record),
        )

    def test_confidence_exactly_at_the_minimum_is_accepted(self):
        record = modelled(
            "solar-particle-event-environment",
            confidence_level_percent=MINIMUM_CONFIDENCE_PERCENT,
        )
        self.assertEqual(entry_findings(record), [])

    def test_confidence_below_the_minimum_is_a_finding(self):
        record = modelled(
            "solar-particle-event-environment", confidence_level_percent=50.0
        )
        self.assertIn(
            "%s:solar-particle-event-environment" % FINDING_LOW_CONFIDENCE,
            entry_findings(record),
        )

    def test_confidence_on_a_deterministic_model_is_a_finding(self):
        record = modelled(
            "trapped-proton-environment",
            solar_activity_condition="solar-minimum",
            confidence_level_percent=95.0,
        )
        self.assertIn(
            "%s:trapped-proton-environment" % FINDING_CONFIDENCE_MISPLACED,
            entry_findings(record),
        )

    def test_missing_solar_activity_condition_is_a_finding(self):
        record = modelled("trapped-proton-environment")
        self.assertIn(
            "%s:trapped-proton-environment" % FINDING_NO_ACTIVITY,
            entry_findings(record),
        )

    def test_a_non_modelled_item_owes_no_model(self):
        self.assertEqual(entry_findings({"item": "shielding-assumptions"}), [])


class TestShieldingCoverage(unittest.TestCase):
    def test_a_span_reaching_below_the_equipment_is_clean(self):
        self.assertEqual(shielding_coverage_findings(spec()), [])

    def test_a_span_starting_above_the_equipment_is_a_finding(self):
        records = contents()
        for record in records:
            if record["item"] == "ionising-dose-depth-curve":
                record["shielding_span_mm"] = [2.0, 20.0]
        findings = shielding_coverage_findings(spec(contents=records))
        self.assertIn(
            "%s:ionising-dose-depth-curve" % FINDING_SPAN_TOO_THICK, findings
        )

    def test_a_span_starting_exactly_at_the_equipment_reaches_it(self):
        records = contents()
        for record in records:
            if record["item"] == "ionising-dose-depth-curve":
                record["shielding_span_mm"] = [1.0, 20.0]
        self.assertEqual(shielding_coverage_findings(spec(contents=records)), [])

    def test_no_declared_equipment_shielding_skips_the_check(self):
        records = contents()
        for record in records:
            if record["item"] == "ionising-dose-depth-curve":
                record["shielding_span_mm"] = [5.0, 20.0]
        self.assertEqual(
            shielding_coverage_findings(
                {"contents": records, "thinnest_equipment_shielding_mm": None}
            ),
            [],
        )


class TestAssessment(unittest.TestCase):
    def test_a_complete_document_is_compliant(self):
        report = assess_environment_specification(spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["missing_items"], [])
        self.assertAlmostEqual(report["completeness_ratio"], 1.0, places=9)

    def test_a_missing_item_appears_as_a_finding(self):
        records = [
            c for c in contents() if c["item"] != "linear-energy-transfer-spectra"
        ]
        report = assess_environment_specification(spec(contents=records))
        self.assertIn(
            "%s:linear-energy-transfer-spectra" % FINDING_ITEM_MISSING,
            report["findings"],
        )
        self.assertFalse(report["compliant"])

    def test_declared_items_are_listed_in_document_order(self):
        report = assess_environment_specification(spec())
        self.assertEqual(report["declared_items"][0], "mission-and-orbit-definition")

    def test_an_undeclared_confidence_level_fails_the_document(self):
        records = contents()
        for record in records:
            if record["item"] == "solar-particle-event-environment":
                del record["confidence_level_percent"]
        report = assess_environment_specification(spec(contents=records))
        self.assertFalse(report["compliant"])

    def test_non_mapping_specification_raises(self):
        with self.assertRaises(ValueError):
            assess_environment_specification(["contents"])


if __name__ == "__main__":
    unittest.main()
