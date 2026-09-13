#!/usr/bin/env python3
"""Gate 3 contract test for e2001-measurement-temperature-range.

stdlib unittest, offline, deterministic. Run: python3 test_e2001_measurement_temperature_range.py
"""

import datetime
import math
import unittest

from e2001_measurement_temperature_range_logic import (
    APPROVAL_STATES,
    DEFAULT_THERMOMETRY_FRACTION,
    KELVIN_AT_ZERO_CELSIUS,
    approval_state,
    assess_temperature_range,
    envelops_service_range,
    range_margins_k,
    range_span_k,
    setpoint_coverage,
    thermometry_adequate,
    to_kelvin,
    validate_temperature_range,
)


def near(test, got, want, rel=1e-9):
    test.assertAlmostEqual(got, want, delta=abs(want) * rel + 1e-12)


DECLARED = {"min": -50.0, "max": 120.0, "unit": "degC"}
SERVICE = {"min": -30.0, "max": 95.0, "unit": "degC"}
SETPOINTS = [223.15, 248.15, 273.15, 298.15, 323.15, 348.15, 373.15, 393.15]


def good_record(**over):
    record = {
        "id": "WR75-IRIS-COUPON",
        "declared_range": dict(DECLARED),
        "predicted_service_range": dict(SERVICE),
        "setpoints_k": list(SETPOINTS),
        "max_setpoint_gap_k": 25.0,
        "supplier_declaration_date": "2026-03-02",
        "revision_date": "2026-04-10",
        "customer_approval_date": "2026-04-18",
        "thermometry_uncertainty_k": 1.0,
        "range_justification": "brackets the predicted service extremes",
    }
    record.update(over)
    return record


class TestUnitNormalisation(unittest.TestCase):
    def test_kelvin_passes_through(self):
        near(self, to_kelvin(300.0), 300.0)

    def test_celsius_is_offset(self):
        near(self, to_kelvin(20.0, "degC"), 20.0 + KELVIN_AT_ZERO_CELSIUS)

    def test_absolute_zero_is_accepted(self):
        near(self, to_kelvin(-KELVIN_AT_ZERO_CELSIUS, "degC"), 0.0)

    def test_below_absolute_zero_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin(-300.0, "degC")

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin(20.0, "degF")

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin("20C", "degC")

    def test_non_finite_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin(math.nan)


class TestRangeRecord(unittest.TestCase):
    def test_celsius_range_is_normalised(self):
        low, high = validate_temperature_range(DECLARED)
        near(self, low, -50.0 + KELVIN_AT_ZERO_CELSIUS)
        near(self, high, 120.0 + KELVIN_AT_ZERO_CELSIUS)

    def test_kelvin_range_is_kept(self):
        low, high = validate_temperature_range({"min": 200.0, "max": 400.0})
        near(self, low, 200.0)
        near(self, high, 400.0)

    def test_missing_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_temperature_range({"min": 200.0})

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            validate_temperature_range({"min": 400.0, "max": 200.0})

    def test_degenerate_range_raises(self):
        with self.assertRaises(ValueError):
            validate_temperature_range({"min": 300.0, "max": 300.0})

    def test_non_mapping_range_raises(self):
        with self.assertRaises(ValueError):
            validate_temperature_range((200.0, 400.0))

    def test_span_is_the_width(self):
        near(self, range_span_k(DECLARED), 170.0)


class TestEnvelopment(unittest.TestCase):
    def test_margins_at_both_ends(self):
        margins = range_margins_k(DECLARED, SERVICE)
        near(self, margins["cold_margin_k"], 20.0)
        near(self, margins["hot_margin_k"], 25.0)

    def test_enveloping_range_passes(self):
        self.assertTrue(envelops_service_range(DECLARED, SERVICE))

    def test_cold_shortfall_is_negative(self):
        service = {"min": -70.0, "max": 95.0, "unit": "degC"}
        margins = range_margins_k(DECLARED, service)
        near(self, margins["cold_margin_k"], -20.0)
        self.assertFalse(envelops_service_range(DECLARED, service))

    def test_hot_shortfall_is_negative(self):
        service = {"min": -30.0, "max": 150.0, "unit": "degC"}
        self.assertFalse(envelops_service_range(DECLARED, service))

    def test_coincident_endpoints_still_envelop(self):
        service = {"min": -50.0, "max": 120.0, "unit": "degC"}
        self.assertTrue(envelops_service_range(DECLARED, service))

    def test_endpoint_reached_by_arithmetic_still_envelops(self):
        drifted = math.fsum([KELVIN_AT_ZERO_CELSIUS, 120.0])
        service = {"min": 240.0, "max": drifted}
        self.assertTrue(envelops_service_range(DECLARED, service))


class TestApprovalState(unittest.TestCase):
    def test_approved_after_revision(self):
        self.assertEqual(approval_state(good_record()), "approved")

    def test_pending_without_customer_date(self):
        record = good_record()
        del record["customer_approval_date"]
        self.assertEqual(approval_state(record), "pending-customer-approval")

    def test_approval_before_revision_is_superseded(self):
        record = good_record(customer_approval_date="2026-03-15")
        self.assertEqual(approval_state(record), "approval-superseded")

    def test_approval_on_the_revision_date_is_valid(self):
        record = good_record(customer_approval_date="2026-04-10")
        self.assertEqual(approval_state(record), "approved")

    def test_state_is_one_of_the_declared_states(self):
        self.assertIn(approval_state(good_record()), APPROVAL_STATES)

    def test_date_objects_are_accepted(self):
        record = good_record(
            supplier_declaration_date=datetime.date(2026, 3, 2),
            revision_date=datetime.date(2026, 4, 10),
            customer_approval_date=datetime.date(2026, 4, 18),
        )
        self.assertEqual(approval_state(record), "approved")

    def test_missing_supplier_declaration_raises(self):
        record = good_record()
        del record["supplier_declaration_date"]
        with self.assertRaises(ValueError):
            approval_state(record)

    def test_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            approval_state(good_record(customer_approval_date="18/04/2026"))

    def test_revision_before_declaration_raises(self):
        with self.assertRaises(ValueError):
            approval_state(good_record(revision_date="2026-01-05"))

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            approval_state("approved")


class TestSetpointCoverage(unittest.TestCase):
    def test_good_ladder_is_covered(self):
        report = setpoint_coverage(SETPOINTS, DECLARED, 25.0)
        self.assertTrue(report["covered"])
        self.assertEqual(report["count"], len(SETPOINTS))
        self.assertEqual(report["wide_gaps"], [])

    def test_gap_exactly_at_the_limit_is_not_wide(self):
        low = to_kelvin(DECLARED["min"], "degC")
        points = [low + 25.0 * i for i in range(7)] + [
            to_kelvin(DECLARED["max"], "degC")
        ]
        report = setpoint_coverage(points, DECLARED, 25.0)
        self.assertEqual(report["wide_gaps"], [])
        self.assertTrue(report["covered"])

    def test_wide_gap_is_flagged(self):
        points = [223.15, 300.0, 393.15]
        report = setpoint_coverage(points, DECLARED, 25.0)
        self.assertEqual(len(report["wide_gaps"]), 2)
        self.assertFalse(report["covered"])

    def test_setpoint_outside_the_range_is_flagged(self):
        points = SETPOINTS + [420.0]
        report = setpoint_coverage(points, DECLARED, 25.0)
        self.assertEqual(len(report["setpoints_outside_range"]), 1)
        self.assertFalse(report["covered"])

    def test_unanchored_cold_endpoint_is_reported(self):
        points = [p for p in SETPOINTS if p > 240.0]
        report = setpoint_coverage(points, DECLARED, 60.0)
        self.assertFalse(report["cold_endpoint_anchored"])
        self.assertTrue(report["hot_endpoint_anchored"])

    def test_largest_gap_is_reported(self):
        report = setpoint_coverage([223.15, 260.0, 393.15], DECLARED, 200.0)
        near(self, report["largest_gap_k"], 133.15)

    def test_setpoints_are_sorted_and_deduplicated(self):
        report = setpoint_coverage([393.15, 223.15, 223.15, 300.0], DECLARED, 200.0)
        self.assertEqual(report["count"], 3)
        self.assertEqual(report["setpoints_k"], sorted(report["setpoints_k"]))

    def test_single_setpoint_raises(self):
        with self.assertRaises(ValueError):
            setpoint_coverage([300.0], DECLARED)

    def test_duplicate_only_setpoints_raise(self):
        with self.assertRaises(ValueError):
            setpoint_coverage([300.0, 300.0], DECLARED)

    def test_non_sequence_setpoints_raise(self):
        with self.assertRaises(ValueError):
            setpoint_coverage({"a": 300.0}, DECLARED)

    def test_non_numeric_setpoint_raises(self):
        with self.assertRaises(ValueError):
            setpoint_coverage([223.15, "300K"], DECLARED)

    def test_non_positive_gap_limit_raises(self):
        with self.assertRaises(ValueError):
            setpoint_coverage(SETPOINTS, DECLARED, 0.0)

    def test_negative_endpoint_tolerance_raises(self):
        with self.assertRaises(ValueError):
            setpoint_coverage(SETPOINTS, DECLARED, 25.0, -1.0)


class TestThermometry(unittest.TestCase):
    def test_small_uncertainty_is_adequate(self):
        self.assertTrue(thermometry_adequate(1.0, 170.0))

    def test_large_uncertainty_is_not_adequate(self):
        self.assertFalse(thermometry_adequate(8.0, 170.0))

    def test_exact_share_is_adequate(self):
        span = 170.0
        self.assertTrue(
            thermometry_adequate(span * DEFAULT_THERMOMETRY_FRACTION, span)
        )

    def test_tighter_fraction_can_reject(self):
        self.assertFalse(thermometry_adequate(3.0, 170.0, 0.01))

    def test_zero_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            thermometry_adequate(0.0, 170.0)

    def test_non_positive_span_raises(self):
        with self.assertRaises(ValueError):
            thermometry_adequate(1.0, 0.0)

    def test_fraction_outside_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            thermometry_adequate(1.0, 170.0, 1.5)


class TestAssessment(unittest.TestCase):
    def test_good_record_is_compliant(self):
        report = assess_temperature_range(good_record())
        self.assertTrue(report["compliant"], report["findings"])
        self.assertEqual(report["approval_state"], "approved")
        self.assertTrue(report["envelops_service_range"])
        near(self, report["declared_span_k"], 170.0)

    def test_cold_shortfall_is_flagged(self):
        record = good_record(
            predicted_service_range={"min": -80.0, "max": 95.0, "unit": "degC"}
        )
        report = assess_temperature_range(record)
        self.assertIn("cold-end-not-enveloped", report["finding_codes"])
        self.assertFalse(report["envelops_service_range"])

    def test_hot_shortfall_is_flagged(self):
        record = good_record(
            predicted_service_range={"min": -30.0, "max": 160.0, "unit": "degC"}
        )
        report = assess_temperature_range(record)
        self.assertIn("hot-end-not-enveloped", report["finding_codes"])

    def test_coincident_service_endpoint_stays_compliant(self):
        record = good_record(
            predicted_service_range={
                "min": -50.0,
                "max": 120.0,
                "unit": "degC",
            }
        )
        report = assess_temperature_range(record)
        self.assertTrue(report["compliant"], report["findings"])
        near(self, report["margins_k"]["hot_margin_k"], 0.0)

    def test_missing_approval_is_flagged(self):
        record = good_record()
        del record["customer_approval_date"]
        report = assess_temperature_range(record)
        self.assertIn("customer-approval-missing", report["finding_codes"])

    def test_superseded_approval_is_flagged(self):
        report = assess_temperature_range(
            good_record(customer_approval_date="2026-03-15")
        )
        self.assertIn("customer-approval-superseded", report["finding_codes"])

    def test_wide_setpoint_gap_is_flagged(self):
        report = assess_temperature_range(
            good_record(setpoints_k=[223.15, 320.0, 393.15])
        )
        self.assertIn("setpoint-gap-exceeds-limit", report["finding_codes"])

    def test_setpoint_outside_range_is_flagged(self):
        report = assess_temperature_range(
            good_record(setpoints_k=SETPOINTS + [430.0], max_setpoint_gap_k=40.0)
        )
        self.assertIn("setpoint-outside-declared-range", report["finding_codes"])

    def test_unmeasured_endpoint_is_flagged(self):
        report = assess_temperature_range(
            good_record(
                setpoints_k=[260.0, 280.0, 300.0, 320.0, 340.0, 360.0],
                max_setpoint_gap_k=25.0,
            )
        )
        self.assertIn("range-endpoint-not-measured", report["finding_codes"])

    def test_excessive_thermometry_uncertainty_is_flagged(self):
        report = assess_temperature_range(good_record(thermometry_uncertainty_k=9.0))
        self.assertIn("thermometry-uncertainty-excessive", report["finding_codes"])

    def test_absent_thermometry_record_is_a_finding(self):
        record = good_record()
        del record["thermometry_uncertainty_k"]
        report = assess_temperature_range(record)
        self.assertIn("thermometry-uncertainty-not-on-record", report["finding_codes"])
        self.assertIsNone(report["thermometry_adequate"])

    def test_missing_justification_is_flagged(self):
        report = assess_temperature_range(good_record(range_justification="  "))
        self.assertIn("range-justification-missing", report["finding_codes"])

    def test_missing_declared_range_raises(self):
        record = good_record()
        del record["declared_range"]
        with self.assertRaises(ValueError):
            assess_temperature_range(record)

    def test_missing_service_range_raises(self):
        record = good_record()
        del record["predicted_service_range"]
        with self.assertRaises(ValueError):
            assess_temperature_range(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_temperature_range(["WR75-IRIS-COUPON"])

    def test_findings_accumulate(self):
        record = good_record(
            predicted_service_range={"min": -80.0, "max": 160.0, "unit": "degC"},
            range_justification=None,
        )
        del record["customer_approval_date"]
        report = assess_temperature_range(record)
        for code in (
            "cold-end-not-enveloped",
            "hot-end-not-enveloped",
            "customer-approval-missing",
            "range-justification-missing",
        ):
            self.assertIn(code, report["finding_codes"])
        self.assertFalse(report["compliant"])

    def test_report_carries_the_derived_quantities(self):
        report = assess_temperature_range(good_record())
        for key in (
            "item",
            "declared_range_k",
            "declared_span_k",
            "margins_k",
            "envelops_service_range",
            "approval_state",
            "coverage",
            "thermometry_adequate",
            "findings",
            "finding_codes",
            "compliant",
        ):
            self.assertIn(key, report)


if __name__ == "__main__":
    unittest.main()
