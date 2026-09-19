"""Contract tests for the clause 10.2.1 wafer screening baseline logic."""

import unittest

from q6012_wafer_screening_general_provisions_logic import (
    COMPLIANT,
    INCOMPLETE,
    NON_COMPLIANT,
    assess_campaign,
    condition_findings,
    coverage_fraction,
    coverage_gap,
    meets_minimum,
    normalize_wafer_ids,
    record_findings,
    retention_shortfall_years,
    untraceable_wafers,
    validate_duration_hours,
    validate_identifier,
    validate_retention_years,
    validate_temperature_c,
)

LOT = ("W01", "W02", "W03", "W04")
BASELINE = {"min_soak_temperature_c": 125.0, "min_soak_duration_h": 168.0}
CONDITIONS = {
    "soak_temperature_c": 125.0,
    "soak_duration_h": 168.0,
    "bias_condition": "static forward bias at rated supply",
    "measurement_temperature_c": 22.0,
}


def _record(wafer):
    return {
        "lot_id": "LOT-A",
        "operator": "op-14",
        "equipment_id": "oven-3",
        "start_timestamp": "2026-02-01T08:00",
        "measured_data_reference": "dataset/%s" % wafer,
    }


def _campaign(**overrides):
    base = {
        "lot_id": "LOT-A",
        "lot_wafers": LOT,
        "screened_wafers": LOT,
        "conditions": dict(CONDITIONS),
        "baseline": dict(BASELINE),
        "records": {w: _record(w) for w in LOT},
        "record_retention_years": 10.0,
        "required_retention_years": 10.0,
    }
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ", "lot_id")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(7, "lot_id")

    def test_identifier_is_stripped(self):
        self.assertEqual(validate_identifier("  W01 "), "W01")

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_c(-300.0)

    def test_boolean_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_c(True)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration_hours(0.0)

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_retention_years(-1.0)

    def test_repeated_wafer_rejected(self):
        with self.assertRaises(ValueError):
            normalize_wafer_ids(["W01", "W01"])

    def test_string_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            normalize_wafer_ids("W01")


class BoundTests(unittest.TestCase):
    def test_value_on_the_bound_meets_it(self):
        self.assertTrue(meets_minimum(168.0, 168.0))

    def test_value_below_the_bound_does_not(self):
        self.assertFalse(meets_minimum(160.0, 168.0))

    def test_value_above_the_bound_does(self):
        self.assertTrue(meets_minimum(200.0, 168.0))


class CoverageTests(unittest.TestCase):
    def test_full_lot_leaves_no_gap(self):
        self.assertEqual(coverage_gap(LOT, LOT), ())

    def test_missing_wafer_is_reported_in_lot_order(self):
        self.assertEqual(coverage_gap(LOT, ("W03", "W01")), ("W02", "W04"))

    def test_stray_wafer_is_a_traceability_break(self):
        self.assertEqual(untraceable_wafers(LOT, ("W01", "W99")), ("W99",))

    def test_full_coverage_fraction(self):
        self.assertAlmostEqual(coverage_fraction(LOT, LOT), 1.0, places=9)

    def test_half_coverage_fraction(self):
        self.assertAlmostEqual(coverage_fraction(LOT, ("W01", "W02")), 0.5, places=9)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction((), ())


class ConditionTests(unittest.TestCase):
    def test_declared_baseline_conditions_pass(self):
        self.assertEqual(condition_findings(CONDITIONS, BASELINE), ())

    def test_undeclared_bias_is_a_finding(self):
        conditions = dict(CONDITIONS)
        conditions["bias_condition"] = "  "
        self.assertTrue(
            any("bias_condition" in f for f in condition_findings(conditions, BASELINE))
        )

    def test_absent_measurement_temperature_is_a_finding(self):
        conditions = dict(CONDITIONS)
        del conditions["measurement_temperature_c"]
        self.assertTrue(
            any(
                "measurement_temperature_c" in f
                for f in condition_findings(conditions, BASELINE)
            )
        )

    def test_short_soak_is_a_finding(self):
        conditions = dict(CONDITIONS, soak_duration_h=100.0)
        self.assertTrue(
            any("soak duration" in f for f in condition_findings(conditions, BASELINE))
        )

    def test_cool_soak_is_a_finding(self):
        conditions = dict(CONDITIONS, soak_temperature_c=85.0)
        self.assertTrue(
            any("soak temperature" in f for f in condition_findings(conditions, BASELINE))
        )

    def test_soak_exactly_on_the_bound_is_accepted(self):
        conditions = dict(CONDITIONS, soak_duration_h=168.0)
        self.assertAlmostEqual(conditions["soak_duration_h"], 168.0, places=9)
        self.assertEqual(condition_findings(conditions, BASELINE), ())


class RecordTests(unittest.TestCase):
    def test_complete_record_has_no_gap(self):
        self.assertEqual(record_findings(_record("W01")), ())

    def test_blank_operator_is_a_gap(self):
        record = _record("W01")
        record["operator"] = ""
        self.assertEqual(record_findings(record), ("operator",))

    def test_absent_data_reference_is_a_gap(self):
        record = _record("W01")
        del record["measured_data_reference"]
        self.assertEqual(record_findings(record), ("measured_data_reference",))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            record_findings(["lot_id"])

    def test_met_retention_owes_nothing(self):
        self.assertAlmostEqual(retention_shortfall_years(10.0, 10.0), 0.0, places=9)

    def test_short_retention_owes_the_difference(self):
        self.assertAlmostEqual(retention_shortfall_years(6.0, 10.0), 4.0, places=9)


class CampaignTests(unittest.TestCase):
    def test_baseline_campaign_is_compliant(self):
        result = assess_campaign(_campaign())
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertTrue(result["baseline_met"])
        self.assertEqual(result["findings"], ())

    def test_uncovered_wafer_makes_it_incomplete(self):
        result = assess_campaign(_campaign(screened_wafers=("W01", "W02", "W03")))
        self.assertEqual(result["verdict"], INCOMPLETE)
        self.assertEqual(result["uncovered_wafers"], ("W04",))

    def test_coverage_fraction_is_carried(self):
        result = assess_campaign(_campaign(screened_wafers=("W01", "W02")))
        self.assertAlmostEqual(result["coverage_fraction"], 0.5, places=9)

    def test_stray_wafer_is_reported_separately(self):
        result = assess_campaign(
            _campaign(
                screened_wafers=LOT + ("W99",),
                records={w: _record(w) for w in LOT + ("W99",)},
            )
        )
        self.assertEqual(result["untraceable_wafers"], ("W99",))
        self.assertEqual(result["verdict"], INCOMPLETE)

    def test_absent_record_is_reported_for_the_wafer(self):
        records = {w: _record(w) for w in LOT}
        del records["W02"]
        result = assess_campaign(_campaign(records=records))
        self.assertEqual(result["record_findings"]["W02"], ("record absent",))

    def test_condition_defect_outranks_a_record_gap(self):
        result = assess_campaign(
            _campaign(conditions=dict(CONDITIONS, soak_duration_h=24.0))
        )
        self.assertEqual(result["verdict"], NON_COMPLIANT)

    def test_retention_shortfall_alone_is_incomplete(self):
        result = assess_campaign(_campaign(record_retention_years=2.0))
        self.assertEqual(result["verdict"], INCOMPLETE)
        self.assertAlmostEqual(result["retention_shortfall_years"], 8.0, places=9)

    def test_lot_size_and_screened_count_are_reported(self):
        result = assess_campaign(_campaign())
        self.assertEqual(result["lot_size"], 4)
        self.assertEqual(result["screened_count"], 4)

    def test_every_finding_is_a_sentence(self):
        result = assess_campaign(_campaign(screened_wafers=("W01",), records={"W01": _record("W01")}))
        self.assertTrue(all(isinstance(f, str) and f for f in result["findings"]))

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(_campaign(lot_id=""))

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(_campaign(lot_wafers=()))

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(["LOT-A"])


if __name__ == "__main__":
    unittest.main()
