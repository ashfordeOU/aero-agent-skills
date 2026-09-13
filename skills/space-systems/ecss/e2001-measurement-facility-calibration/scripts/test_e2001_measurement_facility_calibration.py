#!/usr/bin/env python3
"""Gate 3 contract test for e2001-measurement-facility-calibration.

stdlib unittest, offline, deterministic. Exercises channel
categorization, date parsing, validity-interval placement, traceability,
instrument-drift, quadrature uncertainty combination, coverage-factor
expansion, delivery checking and the aggregate clause 9.5.2 disposition,
including every ValueError path.
"""

import datetime
import unittest

import e2001_measurement_facility_calibration_logic as logic

RUN_DATE = "2026-06-01"


def channel(name, **overrides):
    entry = {
        "channel": name,
        "calibration_date": "2026-01-15",
        "interval_days": 365,
        "traceable_to": "accredited-calibration-laboratory",
        "pre_run_reading": 100.0,
        "post_run_reading": 100.5,
        "drift_tolerance_percent": 1.0,
        "standard_uncertainty": 0.2,
    }
    entry.update(overrides)
    return entry


def full_channel_set():
    return [channel(name) for name in logic.REQUIRED_CHANNELS]


def good_delivery(channels_covered=None):
    if channels_covered is None:
        channels_covered = list(logic.REQUIRED_CHANNELS)
    return {
        "recipient": "customer-procurement-office",
        "issue_date": "2026-02-01",
        "channels_covered": channels_covered,
    }


class TestNormalizeChannelName(unittest.TestCase):
    def test_folds_case_and_underscores(self):
        self.assertEqual(logic.normalize_channel_name(" Beam_Current "), "beam-current")

    def test_folds_spaces(self):
        self.assertEqual(
            logic.normalize_channel_name("sample temperature"), "sample-temperature"
        )

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_channel_name(3.3)

    def test_blank_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_channel_name("  -- ")


class TestCategorizeChannel(unittest.TestCase):
    def test_required_channel_is_recognized(self):
        self.assertEqual(
            logic.categorize_channel("collector_current"),
            (logic.REQUIRED, "collector-current"),
        )

    def test_supplementary_channel_is_recognized(self):
        self.assertEqual(
            logic.categorize_channel("stage-position"),
            (logic.SUPPLEMENTARY, "stage-position"),
        )

    def test_unknown_channel_is_uncategorized(self):
        category, name = logic.categorize_channel("lab-thermocouple-7")
        self.assertEqual(category, logic.UNCATEGORIZED)
        self.assertEqual(name, "lab-thermocouple-7")

    def test_all_required_channels_round_trip(self):
        for name in logic.REQUIRED_CHANNELS:
            self.assertEqual(logic.categorize_channel(name), (logic.REQUIRED, name))


class TestParseIsoDate(unittest.TestCase):
    def test_parses_iso_string(self):
        self.assertEqual(
            logic.parse_iso_date("2026-03-04"), datetime.date(2026, 3, 4)
        )

    def test_accepts_date_object(self):
        d = datetime.date(2026, 3, 4)
        self.assertEqual(logic.parse_iso_date(d), d)

    def test_accepts_datetime_and_truncates(self):
        dt = datetime.datetime(2026, 3, 4, 11, 30)
        self.assertEqual(logic.parse_iso_date(dt), datetime.date(2026, 3, 4))

    def test_garbage_string_raises(self):
        with self.assertRaises(ValueError):
            logic.parse_iso_date("04/03/2026")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            logic.parse_iso_date(None)


class TestCalibrationAge(unittest.TestCase):
    def test_age_in_whole_days(self):
        self.assertEqual(logic.calibration_age_days("2026-01-01", "2026-01-31"), 30)

    def test_same_day_is_zero(self):
        self.assertEqual(logic.calibration_age_days("2026-01-01", "2026-01-01"), 0)

    def test_calibration_after_run_raises(self):
        with self.assertRaises(ValueError):
            logic.calibration_age_days("2026-06-02", "2026-06-01")


class TestValidityStatus(unittest.TestCase):
    def test_inside_interval(self):
        self.assertEqual(
            logic.validity_status("2026-01-01", 365, "2026-06-01"), logic.IN_VALIDITY
        )

    def test_last_day_of_interval_is_still_valid(self):
        self.assertEqual(
            logic.validity_status("2026-01-01", 30, "2026-01-31"), logic.IN_VALIDITY
        )

    def test_one_day_past_interval_is_out(self):
        self.assertEqual(
            logic.validity_status("2026-01-01", 30, "2026-02-01"),
            logic.OUT_OF_VALIDITY,
        )

    def test_zero_interval_raises(self):
        with self.assertRaises(ValueError):
            logic.validity_status("2026-01-01", 0, "2026-01-01")

    def test_non_integer_interval_raises(self):
        with self.assertRaises(ValueError):
            logic.validity_status("2026-01-01", 30.5, "2026-01-15")


class TestTraceability(unittest.TestCase):
    def test_recognized_chain_is_traceable(self):
        self.assertTrue(logic.is_traceable("national-metrology-institute"))

    def test_chain_is_normalized_before_matching(self):
        self.assertTrue(logic.is_traceable("Certified Transfer Standard"))

    def test_unrecognized_chain_is_not_traceable(self):
        self.assertFalse(logic.is_traceable("in-house-reference-meter"))

    def test_absent_chain_is_not_traceable(self):
        self.assertFalse(logic.is_traceable(None))

    def test_non_string_chain_raises(self):
        with self.assertRaises(ValueError):
            logic.is_traceable(42)


class TestRelativeDrift(unittest.TestCase):
    def test_drift_is_percent_of_pre_run_reading(self):
        self.assertAlmostEqual(
            logic.relative_drift_percent(200.0, 202.0), 1.0, places=9
        )

    def test_drift_is_unsigned(self):
        self.assertAlmostEqual(
            logic.relative_drift_percent(200.0, 198.0), 1.0, places=9
        )

    def test_no_change_is_zero_drift(self):
        self.assertAlmostEqual(logic.relative_drift_percent(5.0, 5.0), 0.0, places=12)

    def test_zero_pre_run_reading_raises(self):
        with self.assertRaises(ValueError):
            logic.relative_drift_percent(0.0, 1.0)

    def test_non_numeric_reading_raises(self):
        with self.assertRaises(ValueError):
            logic.relative_drift_percent("100", 101.0)


class TestDriftWithinTolerance(unittest.TestCase):
    def test_comfortable_drift_passes(self):
        self.assertTrue(logic.drift_within_tolerance(0.4, 1.0))

    def test_drift_on_the_tolerance_passes_despite_representation_error(self):
        # (7.7 - 7.0) / 7.0 * 100 evaluates a few ULPs above 10.0; the
        # physically compliant case must not be failed by that residue.
        drift = logic.relative_drift_percent(7.0, 7.7)
        self.assertGreater(drift, 10.0)
        self.assertTrue(logic.drift_within_tolerance(drift, 10.0))

    def test_drift_beyond_tolerance_fails(self):
        self.assertTrue(not logic.drift_within_tolerance(2.5, 2.0))

    def test_negative_drift_raises(self):
        with self.assertRaises(ValueError):
            logic.drift_within_tolerance(-0.1, 1.0)

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            logic.drift_within_tolerance(0.1, 0.0)


class TestCombineUncertainties(unittest.TestCase):
    def test_quadrature_sum(self):
        self.assertAlmostEqual(logic.combine_uncertainties([0.3, 0.4]), 0.5, places=9)

    def test_single_component_returns_itself(self):
        self.assertAlmostEqual(logic.combine_uncertainties([0.7]), 0.7, places=12)

    def test_quadrature_is_below_the_linear_sum(self):
        combined = logic.combine_uncertainties([0.3, 0.4])
        self.assertLess(combined, 0.3 + 0.4)

    def test_zero_components_combine_to_zero(self):
        self.assertAlmostEqual(logic.combine_uncertainties([0.0, 0.0]), 0.0, places=12)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            logic.combine_uncertainties([])

    def test_negative_component_raises(self):
        with self.assertRaises(ValueError):
            logic.combine_uncertainties([0.2, -0.1])

    def test_non_numeric_component_raises(self):
        with self.assertRaises(ValueError):
            logic.combine_uncertainties([0.2, "0.1"])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            logic.combine_uncertainties(0.2)


class TestUncertaintyWithinBudget(unittest.TestCase):
    def test_quadrature_sum_exactly_on_budget_passes(self):
        # The quadrature sum of these three contributions lands a few ULPs
        # above the 0.15 budget it was built to meet exactly.
        combined = logic.combine_uncertainties([0.02, 0.05, 0.14])
        self.assertGreater(combined, 0.15)
        self.assertTrue(logic.uncertainty_within_budget(combined, 0.15))

    def test_genuine_exceedance_fails(self):
        combined = logic.combine_uncertainties([0.5, 0.5])
        self.assertTrue(not logic.uncertainty_within_budget(combined, 0.5))

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            logic.uncertainty_within_budget(0.1, 0.0)


class TestExpandedUncertainty(unittest.TestCase):
    def test_coverage_factor_scales_the_combined_value(self):
        self.assertAlmostEqual(logic.expanded_uncertainty(0.5, 2.0), 1.0, places=12)

    def test_zero_coverage_factor_raises(self):
        with self.assertRaises(ValueError):
            logic.expanded_uncertainty(0.5, 0.0)

    def test_negative_combined_value_raises(self):
        with self.assertRaises(ValueError):
            logic.expanded_uncertainty(-0.1, 2.0)

    def test_non_numeric_coverage_factor_raises(self):
        with self.assertRaises(ValueError):
            logic.expanded_uncertainty(0.5, "2")


class TestAuditChannel(unittest.TestCase):
    def test_clean_channel_yields_no_findings(self):
        record = logic.audit_channel(channel("beam-current"), RUN_DATE)
        self.assertEqual(record["findings"], [])
        self.assertEqual(record["validity"], logic.IN_VALIDITY)
        self.assertEqual(record["category"], logic.REQUIRED)

    def test_expired_channel_is_flagged(self):
        record = logic.audit_channel(
            channel("beam-current", interval_days=30), RUN_DATE
        )
        self.assertTrue(any("validity interval" in f for f in record["findings"]))

    def test_untraceable_channel_is_flagged(self):
        record = logic.audit_channel(
            channel("beam-energy", traceable_to="in-house-meter"), RUN_DATE
        )
        self.assertTrue(any("traceability" in f for f in record["findings"]))

    def test_excessive_drift_is_flagged(self):
        record = logic.audit_channel(
            channel("base-pressure", post_run_reading=110.0), RUN_DATE
        )
        self.assertTrue(any("drifted" in f for f in record["findings"]))
        self.assertAlmostEqual(record["drift_percent"], 10.0, places=9)

    def test_channel_without_check_readings_skips_drift(self):
        record = logic.audit_channel(
            channel("beam-current", pre_run_reading=None, post_run_reading=None),
            RUN_DATE,
        )
        self.assertIsNone(record["drift_percent"])
        self.assertEqual(record["findings"], [])

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            logic.audit_channel("beam-current", RUN_DATE)


class TestCheckCustomerDelivery(unittest.TestCase):
    def test_clean_delivery_yields_no_findings(self):
        findings = logic.check_customer_delivery(
            good_delivery(), ["2026-01-15"], set(logic.REQUIRED_CHANNELS)
        )
        self.assertEqual(findings, [])

    def test_record_issued_before_calibration_is_flagged(self):
        delivery = good_delivery()
        delivery["issue_date"] = "2026-01-01"
        findings = logic.check_customer_delivery(
            delivery, ["2026-01-15"], set(logic.REQUIRED_CHANNELS)
        )
        self.assertTrue(any("predates" in f for f in findings))

    def test_omitted_required_channel_is_flagged(self):
        delivery = good_delivery(["beam-current", "collector-current"])
        findings = logic.check_customer_delivery(
            delivery, ["2026-01-15"], set(logic.REQUIRED_CHANNELS)
        )
        self.assertTrue(any("beam-energy" in f for f in findings))

    def test_missing_recipient_raises(self):
        delivery = good_delivery()
        delivery["recipient"] = "  "
        with self.assertRaises(ValueError):
            logic.check_customer_delivery(delivery, ["2026-01-15"], set())

    def test_empty_channel_coverage_raises(self):
        delivery = good_delivery([])
        with self.assertRaises(ValueError):
            logic.check_customer_delivery(delivery, ["2026-01-15"], set())

    def test_non_mapping_delivery_raises(self):
        with self.assertRaises(ValueError):
            logic.check_customer_delivery(["recipient"], ["2026-01-15"], set())


class TestAuditFacilityCalibration(unittest.TestCase):
    def test_complete_facility_is_compliant(self):
        result = logic.audit_facility_calibration(
            full_channel_set(), RUN_DATE, good_delivery(), budget=1.0
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing_required"], [])

    def test_missing_required_channel_is_flagged(self):
        channels = [c for c in full_channel_set() if c["channel"] != "beam-energy"]
        result = logic.audit_facility_calibration(
            channels, RUN_DATE, good_delivery(), budget=1.0
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_required"], ["beam-energy"])

    def test_supplementary_channel_does_not_replace_a_required_one(self):
        channels = [c for c in full_channel_set() if c["channel"] != "base-pressure"]
        channels.append(channel("stage-position"))
        result = logic.audit_facility_calibration(
            channels, RUN_DATE, good_delivery(), budget=1.0
        )
        self.assertEqual(result["missing_required"], ["base-pressure"])

    def test_uncategorized_channel_is_reported_separately(self):
        channels = full_channel_set() + [channel("lab-thermocouple-7")]
        result = logic.audit_facility_calibration(
            channels, RUN_DATE, good_delivery(), budget=1.0
        )
        self.assertEqual(result["uncategorized_channels"], ["lab-thermocouple-7"])
        self.assertEqual(result["missing_required"], [])

    def test_combined_uncertainty_is_the_quadrature_sum(self):
        result = logic.audit_facility_calibration(
            full_channel_set(), RUN_DATE, good_delivery(), budget=1.0
        )
        expected = (5 * 0.2 * 0.2) ** 0.5
        self.assertAlmostEqual(
            result["combined_standard_uncertainty"], expected, places=9
        )

    def test_budget_exceedance_is_flagged(self):
        result = logic.audit_facility_calibration(
            full_channel_set(), RUN_DATE, good_delivery(), budget=0.1
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("combined-standard-uncertainty" in f for f in result["findings"])
        )

    def test_budget_may_be_omitted(self):
        result = logic.audit_facility_calibration(
            full_channel_set(), RUN_DATE, good_delivery()
        )
        self.assertTrue(result["compliant"])

    def test_expired_channel_makes_the_facility_non_compliant(self):
        channels = full_channel_set()
        channels[0] = channel("beam-current", interval_days=10)
        result = logic.audit_facility_calibration(
            channels, RUN_DATE, good_delivery(), budget=1.0
        )
        self.assertFalse(result["compliant"])

    def test_undelivered_channel_makes_the_facility_non_compliant(self):
        result = logic.audit_facility_calibration(
            full_channel_set(),
            RUN_DATE,
            good_delivery(["beam-current"]),
            budget=1.0,
        )
        self.assertFalse(result["compliant"])

    def test_empty_channel_list_raises(self):
        with self.assertRaises(ValueError):
            logic.audit_facility_calibration([], RUN_DATE, good_delivery())


if __name__ == "__main__":
    unittest.main()
