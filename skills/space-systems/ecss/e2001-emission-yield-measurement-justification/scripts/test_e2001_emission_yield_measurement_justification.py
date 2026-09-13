#!/usr/bin/env python3
"""Gate 3 contract test for e2001-emission-yield-measurement-justification."""

import unittest

from e2001_emission_yield_measurement_justification_logic import (
    COATING_THICKNESS_TOL_UM,
    DECISION_NOT_TRIGGERED,
    DECISION_REMEASURE,
    DECISION_REUSE,
    DEFAULT_CRITICAL_MARGIN_DB,
    FD_BAND_MAX_GHZ_MM,
    FD_BAND_MIN_GHZ_MM,
    assess_gap_criticality,
    categorize_attribute,
    compare_provenance,
    format_justification,
    frequency_gap_product,
    justify_measurement,
    measurement_record_age_days,
    meets_or_exceeds,
    normalize_provenance,
    parse_iso_date,
    validate_measurement_record,
    within_limit,
    yield_affecting_differences,
)


def baseline_provenance(**overrides):
    record = {
        "base_material": "aluminium 6061-T6",
        "surface_finish": "machined Ra 0.8",
        "coating_process": "silver plating, cyanide-free",
        "cleaning_route": "solvent degrease then ultrasonic rinse",
        "manufacturing_route": "milled housing, brazed flange",
        "coating_thickness_um": 6.0,
        "lot_id": "LOT-1147",
    }
    record.update(overrides)
    return record


def critical_gap(**overrides):
    gap = {"frequency_ghz": 12.0, "gap_mm": 0.5, "design_margin_db": 3.0}
    gap.update(overrides)
    return gap


def sound_record(**overrides):
    record = {
        "facility": "ESA reference emission-yield bench",
        "instrument": "hemispherical collector, pulsed gun",
        "sample_id": "SAMP-0042",
        "conditioning": "as-received",
        "measured_on": "2025-03-01",
        "energy_span_ev": (5.0, 2000.0),
    }
    record.update(overrides)
    return record


ASSESSMENT_DAY = "2026-03-01"


class TestAttributeCategorization(unittest.TestCase):
    def test_base_material_is_yield_affecting(self):
        self.assertEqual(categorize_attribute("base_material"), "yield-affecting")

    def test_coating_process_is_yield_affecting(self):
        self.assertEqual(categorize_attribute("coating_process"), "yield-affecting")

    def test_lot_id_is_administrative(self):
        self.assertEqual(categorize_attribute("lot_id"), "administrative")

    def test_unknown_attribute_raises(self):
        with self.assertRaises(ValueError):
            categorize_attribute("paint_colour")


class TestProvenanceNormalisation(unittest.TestCase):
    def test_text_is_case_and_space_normalised(self):
        record = normalize_provenance(baseline_provenance(
            base_material="  ALUMINIUM   6061-T6 "))
        self.assertEqual(record["base_material"], "aluminium 6061-t6")

    def test_numeric_attribute_becomes_float(self):
        record = normalize_provenance(baseline_provenance(coating_thickness_um=6))
        self.assertAlmostEqual(record["coating_thickness_um"], 6.0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            normalize_provenance(["base_material"])

    def test_missing_required_attribute_raises(self):
        record = baseline_provenance()
        del record["cleaning_route"]
        with self.assertRaises(ValueError):
            normalize_provenance(record)

    def test_blank_text_attribute_raises(self):
        with self.assertRaises(ValueError):
            normalize_provenance(baseline_provenance(surface_finish="   "))

    def test_non_positive_thickness_raises(self):
        with self.assertRaises(ValueError):
            normalize_provenance(baseline_provenance(coating_thickness_um=0.0))

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            normalize_provenance(baseline_provenance(mystery_field="x"))


class TestProvenanceComparison(unittest.TestCase):
    def test_identical_records_show_no_difference(self):
        self.assertEqual(compare_provenance(baseline_provenance(),
                                            baseline_provenance()), [])

    def test_casing_difference_is_not_a_change(self):
        diffs = compare_provenance(
            baseline_provenance(),
            baseline_provenance(base_material="Aluminium 6061-T6"))
        self.assertEqual(diffs, [])

    def test_plating_bath_change_is_yield_affecting(self):
        diffs = compare_provenance(
            baseline_provenance(),
            baseline_provenance(coating_process="silver plating, cyanide bath"))
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["category"], "yield-affecting")
        self.assertEqual(diffs[0]["attribute"], "coating_process")

    def test_lot_change_is_administrative_only(self):
        diffs = compare_provenance(baseline_provenance(),
                                   baseline_provenance(lot_id="LOT-2200"))
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["category"], "administrative")
        self.assertEqual(yield_affecting_differences(diffs), [])

    def test_thickness_change_inside_tolerance_is_not_a_change(self):
        diffs = compare_provenance(
            baseline_provenance(),
            baseline_provenance(coating_thickness_um=6.0 + COATING_THICKNESS_TOL_UM))
        self.assertEqual(diffs, [])

    def test_thickness_change_beyond_tolerance_is_yield_affecting(self):
        diffs = compare_provenance(baseline_provenance(),
                                   baseline_provenance(coating_thickness_um=9.0))
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["category"], "yield-affecting")

    def test_attribute_present_on_one_side_only_is_a_difference(self):
        candidate = baseline_provenance()
        del candidate["lot_id"]
        diffs = compare_provenance(baseline_provenance(), candidate)
        self.assertEqual(len(diffs), 1)
        self.assertIsNone(diffs[0]["candidate"])

    def test_multiple_changes_are_sorted_by_attribute(self):
        diffs = compare_provenance(
            baseline_provenance(),
            baseline_provenance(base_material="copper C101",
                                surface_finish="electropolished"))
        self.assertEqual([d["attribute"] for d in diffs],
                         ["base_material", "surface_finish"])


class TestGapCriticality(unittest.TestCase):
    def test_frequency_gap_product(self):
        self.assertAlmostEqual(frequency_gap_product(12.0, 0.5), 6.0)

    def test_in_band_low_margin_is_critical(self):
        result = assess_gap_criticality(critical_gap())
        self.assertTrue(result["critical"])
        self.assertTrue(result["in_susceptibility_band"])

    def test_margin_exactly_at_threshold_is_not_critical(self):
        result = assess_gap_criticality(
            critical_gap(design_margin_db=DEFAULT_CRITICAL_MARGIN_DB))
        self.assertTrue(result["margin_meets_threshold"])
        self.assertFalse(result["critical"])

    def test_margin_from_summed_decibels_at_threshold_is_not_critical(self):
        margin = 3.76 + 2.11 + 0.13  # three contributions, lands 1 ULP under 6.0
        self.assertLess(margin, DEFAULT_CRITICAL_MARGIN_DB)  # a bare >= would fail
        result = assess_gap_criticality(critical_gap(design_margin_db=margin))
        self.assertTrue(result["margin_meets_threshold"])
        self.assertFalse(result["critical"])

    def test_product_above_band_is_not_critical(self):
        result = assess_gap_criticality(
            critical_gap(frequency_ghz=40.0, gap_mm=20.0))
        self.assertFalse(result["in_susceptibility_band"])
        self.assertFalse(result["critical"])

    def test_product_exactly_at_band_edges_stays_in_band(self):
        low = assess_gap_criticality(
            critical_gap(frequency_ghz=FD_BAND_MIN_GHZ_MM, gap_mm=1.0))
        high = assess_gap_criticality(
            critical_gap(frequency_ghz=FD_BAND_MAX_GHZ_MM, gap_mm=1.0))
        self.assertTrue(low["in_susceptibility_band"])
        self.assertTrue(high["in_susceptibility_band"])

    def test_declared_critical_overrides_the_numbers(self):
        result = assess_gap_criticality(
            critical_gap(frequency_ghz=40.0, gap_mm=20.0,
                         design_margin_db=20.0, declared_critical=True))
        self.assertTrue(result["critical"])

    def test_missing_gap_key_raises(self):
        gap = critical_gap()
        del gap["gap_mm"]
        with self.assertRaises(ValueError):
            assess_gap_criticality(gap)

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            assess_gap_criticality(critical_gap(gap_mm=-0.5))

    def test_boolean_frequency_raises(self):
        with self.assertRaises(ValueError):
            assess_gap_criticality(critical_gap(frequency_ghz=True))

    def test_non_boolean_declaration_raises(self):
        with self.assertRaises(ValueError):
            assess_gap_criticality(critical_gap(declared_critical="yes"))

    def test_gap_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_gap_criticality([12.0, 0.5, 3.0])


class TestMeasurementRecord(unittest.TestCase):
    def test_age_in_whole_days(self):
        self.assertEqual(measurement_record_age_days("2026-01-01", "2026-03-01"), 59)

    def test_future_measurement_raises(self):
        with self.assertRaises(ValueError):
            measurement_record_age_days("2026-04-01", "2026-03-01")

    def test_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            parse_iso_date("01/03/2026", "measured_on")

    def test_impossible_calendar_date_raises(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-02-30", "measured_on")

    def test_sound_record_is_valid(self):
        result = validate_measurement_record(sound_record(), ASSESSMENT_DAY)
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_aged_out_record_is_flagged(self):
        result = validate_measurement_record(
            sound_record(measured_on="2019-01-01"), ASSESSMENT_DAY)
        self.assertFalse(result["valid"])
        self.assertTrue(any("validity window" in f for f in result["findings"]))

    def test_record_age_exactly_at_validity_window_stays_valid(self):
        result = validate_measurement_record(
            sound_record(measured_on="2026-01-01"), "2026-03-01",
            validity_days=59)
        self.assertTrue(result["valid"])

    def test_narrow_energy_span_is_flagged(self):
        result = validate_measurement_record(
            sound_record(energy_span_ev=(50.0, 400.0)), ASSESSMENT_DAY)
        self.assertFalse(result["valid"])
        self.assertTrue(any("does not cover" in f for f in result["findings"]))

    def test_span_exactly_matching_the_requirement_is_valid(self):
        result = validate_measurement_record(
            sound_record(energy_span_ev=(10.0, 1000.0)), ASSESSMENT_DAY)
        self.assertTrue(result["valid"])

    def test_unstated_conditioning_is_flagged(self):
        result = validate_measurement_record(
            sound_record(conditioning="unstated"), ASSESSMENT_DAY)
        self.assertFalse(result["valid"])

    def test_missing_facility_is_flagged(self):
        result = validate_measurement_record(
            sound_record(facility=""), ASSESSMENT_DAY)
        self.assertFalse(result["valid"])

    def test_missing_measured_on_raises(self):
        record = sound_record()
        del record["measured_on"]
        with self.assertRaises(ValueError):
            validate_measurement_record(record, ASSESSMENT_DAY)

    def test_decreasing_energy_span_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement_record(
                sound_record(energy_span_ev=(900.0, 20.0)), ASSESSMENT_DAY)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement_record("SAMP-0042", ASSESSMENT_DAY)


class TestClauseDecision(unittest.TestCase):
    def _justify(self, candidate, gap=None, record=None):
        return justify_measurement(baseline_provenance(), candidate,
                                   gap or critical_gap(),
                                   record or sound_record(), ASSESSMENT_DAY)

    def test_unchanged_critical_gap_supports_reuse(self):
        result = self._justify(baseline_provenance())
        self.assertEqual(result["decision"], DECISION_REUSE)
        self.assertTrue(result["drivers"])

    def test_cleaning_route_change_demands_remeasurement(self):
        result = self._justify(baseline_provenance(
            cleaning_route="plasma clean only"))
        self.assertEqual(result["decision"], DECISION_REMEASURE)
        self.assertEqual(result["yield_affecting_count"], 1)

    def test_administrative_change_alone_keeps_reuse(self):
        result = self._justify(baseline_provenance(lot_id="LOT-9001"))
        self.assertEqual(result["decision"], DECISION_REUSE)
        self.assertEqual(result["administrative_count"], 1)

    def test_aged_record_alone_demands_remeasurement(self):
        result = self._justify(baseline_provenance(),
                               record=sound_record(measured_on="2018-06-01"))
        self.assertEqual(result["decision"], DECISION_REMEASURE)
        self.assertTrue(any("held record defect" in d for d in result["drivers"]))

    def test_non_critical_gap_does_not_fire_the_trigger(self):
        result = self._justify(baseline_provenance(base_material="copper C101"),
                               gap=critical_gap(design_margin_db=12.0))
        self.assertEqual(result["decision"], DECISION_NOT_TRIGGERED)
        self.assertEqual(result["yield_affecting_count"], 1)

    def test_declared_critical_non_conformant_gap_still_remeasures(self):
        result = self._justify(
            baseline_provenance(surface_finish="electropolished"),
            gap=critical_gap(design_margin_db=12.0, declared_critical=True))
        self.assertEqual(result["decision"], DECISION_REMEASURE)

    def test_formatted_record_reports_decision_and_drivers(self):
        lines = format_justification(self._justify(
            baseline_provenance(coating_process="gold over nickel")))
        self.assertTrue(lines[0].startswith("ECSS-E-ST-20-01C clause 9.2"))
        self.assertIn("decision: %s" % DECISION_REMEASURE, lines)
        self.assertTrue(any(line.startswith("  driver:") for line in lines))

    def test_format_rejects_a_non_result(self):
        with self.assertRaises(ValueError):
            format_justification({"verdict": "ok"})


class TestToleranceHelpers(unittest.TestCase):
    def test_meets_or_exceeds_absorbs_representation_error(self):
        self.assertTrue(meets_or_exceeds(0.1 + 0.2, 0.3))

    def test_within_limit_absorbs_representation_error(self):
        self.assertTrue(within_limit(0.1 + 0.2, 0.3))

    def test_meets_or_exceeds_still_rejects_a_real_shortfall(self):
        self.assertFalse(meets_or_exceeds(5.9, 6.0))


if __name__ == "__main__":
    unittest.main()
