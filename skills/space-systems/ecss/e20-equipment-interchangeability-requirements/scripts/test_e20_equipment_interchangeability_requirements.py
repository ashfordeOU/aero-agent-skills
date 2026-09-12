#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.2.6 equipment
interchangeability.

Exercises the sibling logic module (stdlib unittest, offline).
Contract: an attribute is categorized as exactly form, fit or function
and an uncategorized attribute raises; relative deviation is
100 * |candidate - reference| / |reference| with a zero reference or a
non-numeric value raising; a discrete attribute must match exactly and
ignores any tolerance, a numeric attribute is graded against the
declared tolerance, and an attribute with no declared tolerance is
reported rather than passed; a different part number ends the
interchangeability claim and a different revision passes only when
declared form-fit-function neutral; a candidate ranking below the
qualification status the slot requires is reported and an unrecognized
status raises; matched-set pairing, on-installation adjustment and
unit-specific calibration data each disqualify a candidate; and a
fleet screen returns exactly the candidates whose every finding group
is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_equipment_interchangeability_requirements_logic as ix  # noqa: E402


BASELINE_ATTRIBUTES = {
    "mass_kg": 3.40,
    "envelope_x_mm": 220.0,
    "mounting_hole_pattern": "4xM4-100x80",
    "connector_pinout": "J1-PINOUT-REV-C",
    "power_consumption_w": 12.0,
    "data_protocol": "milbus-1553b",
}

TOLERANCES = {
    "mass_kg": 2.0,
    "envelope_x_mm": 0.5,
    "power_consumption_w": 5.0,
}


def make_unit(unit_id="SN-002", **overrides):
    """A baseline unit record interchangeable with the reference."""
    unit = {
        "unit_id": unit_id,
        "part_number": "AAS-1234-567",
        "revision": "C",
        "qualification_status": "flight_model",
        "attributes": dict(BASELINE_ATTRIBUTES),
    }
    unit.update(overrides)
    return unit


def reference_unit():
    return make_unit(unit_id="SN-001")


class CategorizeAttributeTest(unittest.TestCase):
    def test_mass_is_form(self):
        self.assertEqual(ix.categorize_attribute("mass_kg"), "form")

    def test_envelope_is_form(self):
        self.assertEqual(ix.categorize_attribute("envelope_x_mm"), "form")

    def test_mounting_hole_pattern_is_fit(self):
        self.assertEqual(ix.categorize_attribute("mounting_hole_pattern"), "fit")

    def test_connector_pinout_is_fit(self):
        self.assertEqual(ix.categorize_attribute("connector_pinout"), "fit")

    def test_power_consumption_is_function(self):
        self.assertEqual(ix.categorize_attribute("power_consumption_w"), "function")

    def test_firmware_baseline_is_function(self):
        self.assertEqual(ix.categorize_attribute("firmware_baseline"), "function")

    def test_unknown_attribute_raises(self):
        with self.assertRaises(ValueError):
            ix.categorize_attribute("paint_colour")


class RelativeDeviationTest(unittest.TestCase):
    def test_identical_values_have_no_deviation(self):
        self.assertAlmostEqual(ix.relative_deviation_percent(3.40, 3.40), 0.0)

    def test_deviation_is_symmetric_in_sign(self):
        high = ix.relative_deviation_percent(100.0, 105.0)
        low = ix.relative_deviation_percent(100.0, 95.0)
        self.assertAlmostEqual(high, 5.0)
        self.assertAlmostEqual(low, 5.0)

    def test_negative_reference_uses_magnitude(self):
        self.assertAlmostEqual(ix.relative_deviation_percent(-10.0, -11.0), 10.0)

    def test_zero_reference_raises(self):
        with self.assertRaises(ValueError):
            ix.relative_deviation_percent(0.0, 1.0)

    def test_non_numeric_candidate_raises(self):
        with self.assertRaises(ValueError):
            ix.relative_deviation_percent(1.0, "one")

    def test_boolean_value_is_not_numeric(self):
        with self.assertRaises(ValueError):
            ix.relative_deviation_percent(1.0, True)


class AttributeFindingsTest(unittest.TestCase):
    def test_numeric_attribute_inside_tolerance_is_clean(self):
        self.assertEqual(
            ix.attribute_findings("mass_kg", 3.40, 3.44, 2.0), []
        )

    def test_numeric_attribute_exactly_at_tolerance_is_clean(self):
        self.assertEqual(ix.attribute_findings("mass_kg", 100.0, 102.0, 2.0), [])

    def test_numeric_attribute_outside_tolerance_reports_the_deviation(self):
        findings = ix.attribute_findings("mass_kg", 100.0, 104.0, 2.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "numeric_attribute_outside_tolerance")
        self.assertAlmostEqual(findings[0]["deviation_percent"], 4.0)
        self.assertEqual(findings[0]["dimension"], "form")

    def test_undeclared_tolerance_is_a_finding_not_a_pass(self):
        findings = ix.attribute_findings("mass_kg", 3.40, 3.40, None)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "undeclared_interchangeability_tolerance"
        )

    def test_discrete_attribute_matching_is_clean(self):
        self.assertEqual(
            ix.attribute_findings(
                "connector_pinout", "J1-PINOUT-REV-C", "J1-PINOUT-REV-C", None
            ),
            [],
        )

    def test_discrete_attribute_mismatch_is_flagged(self):
        findings = ix.attribute_findings(
            "connector_pinout", "J1-PINOUT-REV-C", "J1-PINOUT-REV-D", 50.0
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "discrete_attribute_mismatch")
        self.assertEqual(findings[0]["dimension"], "fit")

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            ix.attribute_findings("mass_kg", 3.40, 3.40, -1.0)

    def test_uncategorized_attribute_raises(self):
        with self.assertRaises(ValueError):
            ix.attribute_findings("serial_sticker", "a", "b", None)


class IdentityFindingsTest(unittest.TestCase):
    def test_same_part_number_and_revision_is_clean(self):
        self.assertEqual(ix.identity_findings(reference_unit(), make_unit()), [])

    def test_different_part_number_is_flagged(self):
        findings = ix.identity_findings(
            reference_unit(), make_unit(part_number="AAS-1234-568")
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "distinct_part_number_breaks_interchangeability"
        )

    def test_different_revision_without_neutrality_is_flagged(self):
        findings = ix.identity_findings(reference_unit(), make_unit(revision="D"))
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "revision_change_not_declared_neutral"
        )

    def test_declared_neutral_revision_is_accepted(self):
        candidate = make_unit(
            revision="D", revision_form_fit_function_neutral=True
        )
        self.assertEqual(ix.identity_findings(reference_unit(), candidate), [])

    def test_missing_part_number_raises(self):
        candidate = make_unit()
        del candidate["part_number"]
        with self.assertRaises(ValueError):
            ix.identity_findings(reference_unit(), candidate)


class QualificationFindingsTest(unittest.TestCase):
    def test_equal_status_is_clean(self):
        self.assertEqual(
            ix.qualification_findings("flight_model", "flight_model"), []
        )

    def test_higher_status_is_clean(self):
        self.assertEqual(
            ix.qualification_findings("flight_model", "qualification_model"), []
        )

    def test_lower_status_is_flagged(self):
        findings = ix.qualification_findings("engineering_model", "flight_model")
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "qualification_status_below_slot_requirement"
        )

    def test_unknown_candidate_status_raises(self):
        with self.assertRaises(ValueError):
            ix.qualification_findings("looks_fine", "flight_model")

    def test_unknown_required_status_raises(self):
        with self.assertRaises(ValueError):
            ix.qualification_findings("flight_model", "space_rated_ish")


class InstallationFindingsTest(unittest.TestCase):
    def test_drop_in_unit_is_clean(self):
        self.assertEqual(ix.installation_findings(make_unit()), [])

    def test_matched_set_pairing_is_flagged(self):
        findings = ix.installation_findings(
            make_unit(requires_matched_set_pairing=True)
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "requires_matched_set_pairing")

    def test_all_three_constraints_are_reported(self):
        findings = ix.installation_findings(
            make_unit(
                requires_matched_set_pairing=True,
                requires_on_installation_adjustment=True,
                requires_unit_specific_calibration_data=True,
            )
        )
        self.assertEqual(len(findings), 3)


class InterchangeabilityReviewTest(unittest.TestCase):
    def test_equivalent_unit_is_interchangeable(self):
        review = ix.interchangeability_review(
            reference_unit(), make_unit(), TOLERANCES, "flight_model"
        )
        self.assertTrue(ix.is_interchangeable(review))

    def test_out_of_tolerance_mass_lands_in_the_form_group(self):
        candidate = make_unit()
        candidate["attributes"]["mass_kg"] = 3.60
        review = ix.interchangeability_review(
            reference_unit(), candidate, TOLERANCES, "flight_model"
        )
        self.assertFalse(ix.is_interchangeable(review))
        self.assertEqual(len(review["form"]), 1)
        self.assertEqual(review["fit"], [])

    def test_pinout_change_lands_in_the_fit_group(self):
        candidate = make_unit()
        candidate["attributes"]["connector_pinout"] = "J1-PINOUT-REV-D"
        review = ix.interchangeability_review(
            reference_unit(), candidate, TOLERANCES, "flight_model"
        )
        self.assertEqual(len(review["fit"]), 1)
        self.assertFalse(ix.is_interchangeable(review))

    def test_protocol_change_lands_in_the_function_group(self):
        candidate = make_unit()
        candidate["attributes"]["data_protocol"] = "spacewire"
        review = ix.interchangeability_review(
            reference_unit(), candidate, TOLERANCES, "flight_model"
        )
        self.assertEqual(len(review["function"]), 1)

    def test_missing_tolerance_is_reported_against_its_dimension(self):
        review = ix.interchangeability_review(
            reference_unit(), make_unit(), {"mass_kg": 2.0}, "flight_model"
        )
        issues = [f["issue"] for f in review["form"] + review["function"]]
        self.assertIn("undeclared_interchangeability_tolerance", issues)
        self.assertFalse(ix.is_interchangeable(review))

    def test_attribute_absent_from_the_candidate_is_reported(self):
        candidate = make_unit()
        del candidate["attributes"]["mass_kg"]
        review = ix.interchangeability_review(
            reference_unit(), candidate, TOLERANCES, "flight_model"
        )
        self.assertEqual(
            review["form"][0]["issue"], "attribute_not_recorded_on_candidate"
        )

    def test_low_qualification_status_blocks_an_otherwise_equal_unit(self):
        review = ix.interchangeability_review(
            reference_unit(),
            make_unit(qualification_status="engineering_model"),
            TOLERANCES,
            "flight_model",
        )
        self.assertFalse(ix.is_interchangeable(review))
        self.assertEqual(len(review["qualification"]), 1)

    def test_missing_attributes_key_raises(self):
        candidate = make_unit()
        del candidate["attributes"]
        with self.assertRaises(ValueError):
            ix.interchangeability_review(
                reference_unit(), candidate, TOLERANCES, "flight_model"
            )

    def test_uncategorized_attribute_on_the_reference_raises(self):
        reference = reference_unit()
        reference["attributes"]["paint_colour"] = "white"
        with self.assertRaises(ValueError):
            ix.interchangeability_review(
                reference, make_unit(), TOLERANCES, "flight_model"
            )


class ScreenCandidatesTest(unittest.TestCase):
    def test_screen_keeps_only_the_interchangeable_units(self):
        good = make_unit(unit_id="SN-002")
        heavy = make_unit(unit_id="SN-003")
        heavy["attributes"]["mass_kg"] = 3.80
        wrong_part = make_unit(unit_id="SN-004", part_number="AAS-1234-568")
        accepted = ix.screen_candidates(
            reference_unit(), [good, heavy, wrong_part], TOLERANCES, "flight_model"
        )
        self.assertEqual(accepted, ["SN-002"])

    def test_empty_fleet_screens_to_nothing(self):
        self.assertEqual(
            ix.screen_candidates(reference_unit(), [], TOLERANCES, "flight_model"),
            [],
        )

    def test_screen_propagates_a_bad_record(self):
        broken = make_unit(unit_id="SN-009", qualification_status="probably_fine")
        with self.assertRaises(ValueError):
            ix.screen_candidates(
                reference_unit(), [broken], TOLERANCES, "flight_model"
            )


if __name__ == "__main__":
    unittest.main()
