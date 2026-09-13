#!/usr/bin/env python3
"""Gate 3 contract test for e2007-vehicle-ground-reference-point.

Offline, deterministic, stdlib unittest. Exercises reference-point
qualification and designation, geometry-derived lead resistance, lead-offset
substantiation, method resolution against the claimed allowance, terminal
citation, the lead-corrected comparison with the bond-category allowance and
the aggregate clause 4.2.11.2 verdict.
"""

import unittest

import e2007_vehicle_ground_reference_point_logic as logic

REFERENCE_ID = "vgrp-longeron-frame-12"


def nominal_reference_records():
    return [
        {
            "id": REFERENCE_ID,
            "structural_member": "primary-structure",
            "surface_finish": "chemical-conversion-coated",
            "accessible_in_measurement_configuration": True,
            "designated": True,
        },
        {
            "id": "candidate-avionics-shelf",
            "structural_member": "equipment-panel",
            "surface_finish": "painted",
            "accessible_in_measurement_configuration": True,
            "designated": False,
        },
    ]


def nominal_measurements():
    return [
        {
            "id": "bond-power-conditioning-unit",
            "bond_category": "structure-bond-primary",
            "method": "four-terminal-kelvin",
            "reference_terminal": REFERENCE_ID,
            "raw_reading_mohm": 3.4,
            "lead_offset_mohm": 1.7,
            "lead_length_m": 0.15,
            "lead_section_mm2": 1.5,
        },
        {
            "id": "bond-harness-shield-backshell",
            "bond_category": "shield-termination-bond",
            "method": "four-terminal-kelvin",
            "reference_terminal": REFERENCE_ID,
            "raw_reading_mohm": 12.0,
            "lead_offset_mohm": 1.7,
            "lead_length_m": 0.15,
            "lead_section_mm2": 1.5,
        },
        {
            "id": "bond-lightning-downlead",
            "bond_category": "lightning-return-bond",
            "method": "four-terminal-kelvin",
            "reference_terminal": REFERENCE_ID,
            "raw_reading_mohm": 2.4,
            "lead_offset_mohm": 1.7,
            "lead_length_m": 0.15,
            "lead_section_mm2": 1.5,
        },
    ]


class TestTokensAndAllowances(unittest.TestCase):
    def test_allowance_lookup_is_category_specific(self):
        self.assertAlmostEqual(logic.allowance_for("structure-bond-primary"), 2.5)
        self.assertAlmostEqual(logic.allowance_for("lightning-return-bond"), 1.0)
        self.assertAlmostEqual(logic.allowance_for("shield-termination-bond"), 25.0)

    def test_allowance_lookup_canonicalizes_case(self):
        self.assertAlmostEqual(logic.allowance_for(" Structure-Bond-Secondary "), 10.0)

    def test_allowance_lookup_rejects_uncategorized_bond(self):
        with self.assertRaises(ValueError):
            logic.allowance_for("chassis-strap")

    def test_normalize_token_rejects_non_string(self):
        with self.assertRaises(ValueError):
            logic.normalize_token(None, logic.MEASUREMENT_METHODS, "method")


class TestLeadResistance(unittest.TestCase):
    def test_copper_lead_resistance_from_geometry(self):
        self.assertAlmostEqual(logic.lead_resistance_mohm(1.0, 1.0), 17.24)
        self.assertAlmostEqual(logic.lead_resistance_mohm(0.15, 1.5), 1.724)

    def test_resistance_scales_inversely_with_section(self):
        thin = logic.lead_resistance_mohm(0.5, 0.5)
        thick = logic.lead_resistance_mohm(0.5, 2.0)
        self.assertAlmostEqual(thin / thick, 4.0)

    def test_rejects_zero_length(self):
        with self.assertRaises(ValueError):
            logic.lead_resistance_mohm(0.0, 1.5)

    def test_rejects_negative_section(self):
        with self.assertRaises(ValueError):
            logic.lead_resistance_mohm(0.3, -1.5)

    def test_rejects_non_numeric_geometry(self):
        with self.assertRaises(ValueError):
            logic.lead_resistance_mohm("0.3 m", 1.5)


class TestReferenceQualification(unittest.TestCase):
    def test_nominal_reference_point_qualifies(self):
        verdict = logic.qualify_reference_point(nominal_reference_records()[0])
        self.assertTrue(verdict["qualified"])
        self.assertEqual(verdict["findings"], [])
        self.assertEqual(verdict["id"], REFERENCE_ID)

    def test_flags_a_point_off_primary_structure(self):
        record = nominal_reference_records()[0]
        record["structural_member"] = "secondary-structure"
        verdict = logic.qualify_reference_point(record)
        self.assertIn("reference-point-not-on-primary-structure", verdict["findings"])

    def test_flags_a_non_conductive_surface_finish(self):
        record = nominal_reference_records()[0]
        record["surface_finish"] = "hard-anodized"
        verdict = logic.qualify_reference_point(record)
        self.assertIn(
            "reference-point-surface-finish-not-conductive", verdict["findings"]
        )

    def test_flags_an_unreachable_reference_point(self):
        record = nominal_reference_records()[0]
        record["accessible_in_measurement_configuration"] = False
        verdict = logic.qualify_reference_point(record)
        self.assertIn(
            "reference-point-not-reachable-for-measurement", verdict["findings"]
        )

    def test_reports_every_failed_property_separately(self):
        record = {
            "id": "vgrp-bracket",
            "structural_member": "equipment-panel",
            "surface_finish": "painted",
            "accessible_in_measurement_configuration": False,
            "designated": True,
        }
        verdict = logic.qualify_reference_point(record)
        self.assertEqual(len(verdict["findings"]), 3)

    def test_rejects_a_record_without_id(self):
        record = nominal_reference_records()[0]
        del record["id"]
        with self.assertRaises(ValueError):
            logic.qualify_reference_point(record)

    def test_rejects_an_uncategorized_surface_finish(self):
        record = nominal_reference_records()[0]
        record["surface_finish"] = "shiny"
        with self.assertRaises(ValueError):
            logic.qualify_reference_point(record)

    def test_rejects_non_boolean_accessibility(self):
        record = nominal_reference_records()[0]
        record["accessible_in_measurement_configuration"] = "yes"
        with self.assertRaises(ValueError):
            logic.qualify_reference_point(record)

    def test_rejects_a_non_mapping_record(self):
        with self.assertRaises(ValueError):
            logic.qualify_reference_point([REFERENCE_ID])


class TestReferenceDesignation(unittest.TestCase):
    def test_resolves_the_single_designated_point(self):
        verdict = logic.resolve_reference_point(nominal_reference_records())
        self.assertEqual(verdict["id"], REFERENCE_ID)

    def test_rejects_a_campaign_with_no_designated_point(self):
        records = nominal_reference_records()
        records[0]["designated"] = False
        with self.assertRaises(ValueError):
            logic.resolve_reference_point(records)

    def test_rejects_two_designated_points(self):
        records = nominal_reference_records()
        records[1]["designated"] = True
        with self.assertRaises(ValueError):
            logic.resolve_reference_point(records)

    def test_rejects_an_empty_candidate_set(self):
        with self.assertRaises(ValueError):
            logic.resolve_reference_point([])


class TestReadingCorrection(unittest.TestCase):
    def test_subtracts_the_lead_offset(self):
        self.assertAlmostEqual(logic.correct_reading(3.4, 1.7), 1.7)

    def test_zero_offset_leaves_the_reading_unchanged(self):
        self.assertAlmostEqual(logic.correct_reading(2.25, 0.0), 2.25)

    def test_rejects_an_offset_larger_than_the_reading(self):
        with self.assertRaises(ValueError):
            logic.correct_reading(1.2, 1.9)

    def test_rejects_a_negative_raw_reading(self):
        with self.assertRaises(ValueError):
            logic.correct_reading(-0.4, 0.1)

    def test_rejects_a_non_numeric_reading(self):
        with self.assertRaises(ValueError):
            logic.correct_reading("3.4 mohm", 1.7)

    def test_rejects_a_boolean_reading(self):
        with self.assertRaises(ValueError):
            logic.correct_reading(True, 0.0)


class TestLeadOffsetSubstantiation(unittest.TestCase):
    def test_offset_close_to_geometry_is_substantiated(self):
        verdict = logic.check_lead_offset(1.7, 0.15, 1.5)
        self.assertTrue(verdict["substantiated"])
        self.assertAlmostEqual(verdict["computed_mohm"], 1.724)
        self.assertLess(verdict["departure_fraction"], 0.05)

    def test_guessed_offset_is_not_substantiated(self):
        verdict = logic.check_lead_offset(6.0, 0.15, 1.5)
        self.assertFalse(verdict["substantiated"])
        self.assertGreater(verdict["departure_fraction"], 0.25)

    def test_offset_exactly_on_the_substantiation_band_is_accepted(self):
        computed = logic.lead_resistance_mohm(0.15, 1.5)
        verdict = logic.check_lead_offset(computed * 1.25, 0.15, 1.5)
        self.assertTrue(verdict["substantiated"])
        self.assertAlmostEqual(verdict["departure_fraction"], 0.25)

    def test_rejects_a_negative_declared_offset(self):
        with self.assertRaises(ValueError):
            logic.check_lead_offset(-0.2, 0.15, 1.5)


class TestMethodResolution(unittest.TestCase):
    def test_four_terminal_method_resolves_every_allowance(self):
        self.assertTrue(logic.method_resolves("four-terminal-kelvin", 1.0))
        self.assertTrue(logic.method_resolves("four-terminal-kelvin", 25.0))

    def test_two_terminal_method_cannot_resolve_a_low_allowance(self):
        self.assertFalse(logic.method_resolves("two-terminal-ohmmeter", 2.5))

    def test_two_terminal_method_resolves_at_the_floor(self):
        self.assertTrue(
            logic.method_resolves(
                "two-terminal-ohmmeter", logic.TWO_TERMINAL_RESOLUTION_FLOOR_MOHM
            )
        )

    def test_rejects_an_uncategorized_method(self):
        with self.assertRaises(ValueError):
            logic.method_resolves("clamp-meter", 2.5)


class TestMeasurementEvaluation(unittest.TestCase):
    def test_nominal_measurement_is_compliant(self):
        verdict = logic.evaluate_measurement(nominal_measurements()[0], REFERENCE_ID)
        self.assertTrue(verdict["compliant"])
        self.assertAlmostEqual(verdict["corrected_mohm"], 1.7)
        self.assertAlmostEqual(verdict["allowance_mohm"], 2.5)

    def test_flags_a_measurement_taken_to_another_terminal(self):
        record = nominal_measurements()[0]
        record["reference_terminal"] = "nearby-bracket-frame-11"
        verdict = logic.evaluate_measurement(record, REFERENCE_ID)
        self.assertIn(
            "measurement-not-referred-to-designated-reference", verdict["findings"]
        )

    def test_flags_a_method_that_cannot_resolve_the_allowance(self):
        record = nominal_measurements()[0]
        record["method"] = "two-terminal-ohmmeter"
        verdict = logic.evaluate_measurement(record, REFERENCE_ID)
        self.assertIn("measurement-method-cannot-resolve-allowance", verdict["findings"])

    def test_flags_a_corrected_reading_above_the_allowance(self):
        record = nominal_measurements()[2]
        record["raw_reading_mohm"] = 4.2
        verdict = logic.evaluate_measurement(record, REFERENCE_ID)
        self.assertIn("corrected-reading-exceeds-bond-allowance", verdict["findings"])
        self.assertAlmostEqual(verdict["corrected_mohm"], 2.5)

    def test_flags_an_unsubstantiated_lead_offset(self):
        record = nominal_measurements()[1]
        record["lead_offset_mohm"] = 6.0
        verdict = logic.evaluate_measurement(record, REFERENCE_ID)
        self.assertIn("lead-offset-not-substantiated-by-geometry", verdict["findings"])

    def test_corrected_reading_exactly_on_the_allowance_is_compliant(self):
        record = {
            "id": "bond-thruster-bracket",
            "bond_category": "structure-bond-primary",
            "method": "four-terminal-kelvin",
            "reference_terminal": REFERENCE_ID,
            "raw_reading_mohm": 4.15,
            "lead_offset_mohm": 1.65,
        }
        # The subtraction lands a few units in the last place above the 2.5
        # allowance although the bond physically sits on it.
        self.assertGreater(4.15 - 1.65, 2.5)
        verdict = logic.evaluate_measurement(record, REFERENCE_ID)
        self.assertAlmostEqual(verdict["corrected_mohm"], 2.5)
        self.assertEqual(verdict["findings"], [])
        self.assertTrue(verdict["compliant"])

    def test_tolerance_does_not_widen_the_allowance(self):
        self.assertTrue(logic._within(2.5, 2.5))
        self.assertFalse(logic._within(2.51, 2.5))
        self.assertFalse(logic._within(1.0001, 1.0))

    def test_rejects_a_measurement_without_a_cited_terminal(self):
        record = nominal_measurements()[0]
        del record["reference_terminal"]
        with self.assertRaises(ValueError):
            logic.evaluate_measurement(record, REFERENCE_ID)

    def test_rejects_an_uncategorized_bond(self):
        record = nominal_measurements()[0]
        record["bond_category"] = "generic-strap"
        with self.assertRaises(ValueError):
            logic.evaluate_measurement(record, REFERENCE_ID)

    def test_rejects_an_empty_reference_id(self):
        with self.assertRaises(ValueError):
            logic.evaluate_measurement(nominal_measurements()[0], "  ")

    def test_rejects_a_non_mapping_measurement(self):
        with self.assertRaises(ValueError):
            logic.evaluate_measurement("bond-1", REFERENCE_ID)


class TestCampaignAssessment(unittest.TestCase):
    def test_nominal_campaign_is_compliant(self):
        report = logic.assess_bonding_baseline(
            nominal_reference_records(), nominal_measurements()
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["measurement_count"], 3)
        self.assertAlmostEqual(report["worst_corrected_mohm"], 10.3)

    def test_mean_corrected_reading_is_reported(self):
        report = logic.assess_bonding_baseline(
            nominal_reference_records(), nominal_measurements()
        )
        self.assertAlmostEqual(report["mean_corrected_mohm"], (1.7 + 10.3 + 0.7) / 3.0)

    def test_reference_findings_reach_the_campaign_verdict(self):
        records = nominal_reference_records()
        records[0]["surface_finish"] = "painted"
        report = logic.assess_bonding_baseline(records, nominal_measurements())
        self.assertFalse(report["compliant"])
        self.assertIn(
            "reference-point-surface-finish-not-conductive", report["findings"]
        )

    def test_measurement_findings_are_prefixed_with_the_bond_id(self):
        measurements = nominal_measurements()
        measurements[0]["reference_terminal"] = "nearby-bracket-frame-11"
        report = logic.assess_bonding_baseline(
            nominal_reference_records(), measurements
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(
            any(f.startswith("bond-power-conditioning-unit:") for f in report["findings"])
        )

    def test_empty_campaign_reports_no_worst_reading(self):
        report = logic.assess_bonding_baseline(nominal_reference_records(), [])
        self.assertIsNone(report["worst_corrected_mohm"])
        self.assertIsNone(report["mean_corrected_mohm"])
        self.assertTrue(report["compliant"])

    def test_rejects_a_non_sequence_measurement_set(self):
        with self.assertRaises(ValueError):
            logic.assess_bonding_baseline(nominal_reference_records(), "bond-1")


class TestSummary(unittest.TestCase):
    def test_summary_reports_verdict_baseline_and_worst_reading(self):
        report = logic.assess_bonding_baseline(
            nominal_reference_records(), nominal_measurements()
        )
        text = logic.summarize_assessment(report)
        self.assertIn("COMPLIANT", text)
        self.assertIn(REFERENCE_ID, text)
        self.assertIn("3 measurement(s)", text)

    def test_summary_rejects_a_non_report(self):
        with self.assertRaises(ValueError):
            logic.summarize_assessment({"measurements": []})


if __name__ == "__main__":
    unittest.main()
