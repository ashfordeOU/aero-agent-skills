"""Contract test for the final-support-maintenance-plan leaf (stdlib unittest)."""

import unittest

from e2040_final_support_maintenance_plan_logic import (
    COMMITMENT_APPLICABILITY,
    COVERAGE_TOLERANCE,
    DEVICE_TYPES,
    DISPOSITIONS,
    OBSOLESCENCE_MITIGATIONS,
    assess_final_support_maintenance_plan,
    binding_constraint,
    coverage_shortfalls,
    effective_support_months,
    obsolescence_assessment,
    owed_commitments,
    response_time_shortfall,
    validate_commitment,
    validate_device_type,
    validate_support_period,
)

PERIOD = 120.0


def commitment(name, months=PERIOD, **kw):
    record = {"name": name, "coverage_months": months, "customer_agreed": True}
    if name == "anomaly-response":
        record["response_time_days"] = 10.0
    record.update(kw)
    return record


def full_commitments(device_type="asic", **overrides):
    records = [commitment(name) for name in owed_commitments(device_type)]
    for key, changes in overrides.items():
        target = key.replace("_", "-")
        for record in records:
            if record["name"] == target:
                record.update(changes)
    return records


def clean_spec(device_type="asic", **kw):
    spec = {
        "device_type": device_type,
        "required_support_months": PERIOD,
        "commitments": full_commitments(device_type),
        "obsolescence_horizon_months": 180.0,
        "maximum_response_days": 15.0,
    }
    spec.update(kw)
    return spec


class TestValidateDeviceType(unittest.TestCase):
    def test_mixed_case_is_normalised(self):
        self.assertEqual(validate_device_type("ASIC"), "asic")

    def test_every_declared_type_round_trips(self):
        for dtype in DEVICE_TYPES:
            self.assertEqual(validate_device_type(dtype), dtype)

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            validate_device_type("microprocessor")

    def test_non_string_type_raises(self):
        with self.assertRaises(ValueError):
            validate_device_type(None)


class TestOwedCommitments(unittest.TestCase):
    def test_an_asic_owes_every_commitment(self):
        self.assertEqual(len(owed_commitments("asic")), len(COMMITMENT_APPLICABILITY))

    def test_an_ip_core_owes_no_test_equipment_retention(self):
        self.assertNotIn("test-equipment-retention", owed_commitments("ip-core"))

    def test_an_ip_core_owes_no_spares(self):
        self.assertNotIn("spares-availability", owed_commitments("ip-core"))

    def test_every_type_owes_anomaly_response(self):
        for dtype in DEVICE_TYPES:
            self.assertIn("anomaly-response", owed_commitments(dtype))


class TestValidateCommitment(unittest.TestCase):
    def test_name_is_lower_cased(self):
        record = validate_commitment(
            {"name": "Competence-Retention", "coverage_months": 12, "customer_agreed": True}
        )
        self.assertEqual(record["name"], "competence-retention")

    def test_unknown_commitment_raises(self):
        with self.assertRaises(ValueError):
            validate_commitment({"name": "free-coffee", "coverage_months": 12})

    def test_negative_coverage_raises(self):
        with self.assertRaises(ValueError):
            validate_commitment(commitment("competence-retention", months=-1))

    def test_anomaly_response_without_a_response_time_raises(self):
        with self.assertRaises(ValueError):
            validate_commitment(
                {"name": "anomaly-response", "coverage_months": 12, "customer_agreed": True}
            )

    def test_non_positive_response_time_raises(self):
        with self.assertRaises(ValueError):
            validate_commitment(commitment("anomaly-response", response_time_days=0))

    def test_non_boolean_agreement_raises(self):
        with self.assertRaises(ValueError):
            validate_commitment(commitment("competence-retention", customer_agreed="yes"))


class TestValidateSupportPeriod(unittest.TestCase):
    def test_positive_period_is_returned_as_float(self):
        self.assertAlmostEqual(validate_support_period(60), 60.0, places=9)

    def test_zero_period_raises(self):
        with self.assertRaises(ValueError):
            validate_support_period(0)

    def test_boolean_period_raises(self):
        with self.assertRaises(ValueError):
            validate_support_period(True)


class TestCoverageShortfalls(unittest.TestCase):
    def test_full_coverage_has_no_shortfall(self):
        report = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        self.assertEqual(report["shortfall_months"], {})
        self.assertEqual(report["missing"], [])

    def test_short_commitment_reports_the_gap_in_months(self):
        report = coverage_shortfalls(
            full_commitments("asic", spares_availability={"coverage_months": 90.0}),
            PERIOD,
            "asic",
        )
        self.assertAlmostEqual(report["shortfall_months"]["spares-availability"], 30.0, places=9)

    def test_absent_commitment_is_named(self):
        records = [c for c in full_commitments("asic") if c["name"] != "competence-retention"]
        report = coverage_shortfalls(records, PERIOD, "asic")
        self.assertEqual(report["missing"], ["competence-retention"])

    def test_commitment_not_owed_by_an_ip_core_is_reported(self):
        records = full_commitments("ip-core") + [commitment("spares-availability")]
        report = coverage_shortfalls(records, PERIOD, "ip-core")
        self.assertEqual(report["declared_but_not_owed"], ["spares-availability"])

    def test_unagreed_commitment_is_named(self):
        report = coverage_shortfalls(
            full_commitments("asic", competence_retention={"customer_agreed": False}),
            PERIOD,
            "asic",
        )
        self.assertEqual(report["unagreed"], ["competence-retention"])

    def test_duplicate_commitment_raises(self):
        records = full_commitments("asic") + [commitment("competence-retention")]
        with self.assertRaises(ValueError):
            coverage_shortfalls(records, PERIOD, "asic")

    def test_coverage_exactly_equal_to_the_period_is_not_a_shortfall(self):
        report = coverage_shortfalls(
            full_commitments("asic", competence_retention={"coverage_months": PERIOD}),
            PERIOD,
            "asic",
        )
        self.assertNotIn("competence-retention", report["shortfall_months"])


class TestBindingConstraint(unittest.TestCase):
    def test_shortest_commitment_binds(self):
        report = coverage_shortfalls(
            full_commitments("asic", tool_and_licence_retention={"coverage_months": 72.0}),
            PERIOD,
            "asic",
        )
        binding = binding_constraint(report)
        self.assertEqual(binding["commitment"], "tool-and-licence-retention")
        self.assertAlmostEqual(binding["coverage_months"], 72.0, places=9)

    def test_malformed_report_raises(self):
        with self.assertRaises(ValueError):
            binding_constraint({"owed": []})


class TestObsolescenceAssessment(unittest.TestCase):
    def test_horizon_beyond_the_period_needs_no_mitigation(self):
        report = obsolescence_assessment(180.0, PERIOD)
        self.assertFalse(report["mitigation_required"])
        self.assertFalse(report["caps_support"])

    def test_horizon_inside_the_period_needs_mitigation(self):
        report = obsolescence_assessment(60.0, PERIOD)
        self.assertTrue(report["mitigation_required"])
        self.assertTrue(report["caps_support"])

    def test_declared_mitigation_lifts_the_cap(self):
        report = obsolescence_assessment(60.0, PERIOD, ["last-time-buy"])
        self.assertTrue(report["mitigation_required"])
        self.assertFalse(report["caps_support"])

    def test_horizon_exactly_at_the_period_is_not_an_exposure(self):
        report = obsolescence_assessment(PERIOD, PERIOD)
        self.assertAlmostEqual(report["horizon_months"], PERIOD, places=9)
        self.assertFalse(report["horizon_below_support_period"])

    def test_unknown_mitigation_raises(self):
        with self.assertRaises(ValueError):
            obsolescence_assessment(60.0, PERIOD, ["hope"])

    def test_repeated_mitigation_raises(self):
        with self.assertRaises(ValueError):
            obsolescence_assessment(60.0, PERIOD, ["last-time-buy", "last-time-buy"])

    def test_every_declared_mitigation_is_accepted(self):
        for name in OBSOLESCENCE_MITIGATIONS:
            report = obsolescence_assessment(60.0, PERIOD, [name])
            self.assertFalse(report["caps_support"])


class TestResponseTimeShortfall(unittest.TestCase):
    def test_response_inside_the_limit_is_zero(self):
        report = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        self.assertAlmostEqual(response_time_shortfall(report, 15.0), 0.0, places=9)

    def test_response_exactly_at_the_limit_is_zero(self):
        report = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        self.assertAlmostEqual(response_time_shortfall(report, 10.0), 0.0, places=9)

    def test_response_beyond_the_limit_returns_the_gap(self):
        report = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        self.assertAlmostEqual(response_time_shortfall(report, 7.0), 3.0, places=9)

    def test_absent_anomaly_commitment_returns_none(self):
        records = [c for c in full_commitments("asic") if c["name"] != "anomaly-response"]
        report = coverage_shortfalls(records, PERIOD, "asic")
        self.assertIsNone(response_time_shortfall(report, 7.0))

    def test_non_positive_limit_raises(self):
        report = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        with self.assertRaises(ValueError):
            response_time_shortfall(report, 0.0)


class TestEffectiveSupportMonths(unittest.TestCase):
    def test_full_plan_delivers_the_whole_period(self):
        coverage = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        obsolescence = obsolescence_assessment(180.0, PERIOD)
        self.assertAlmostEqual(
            effective_support_months(coverage, obsolescence), PERIOD, places=9
        )

    def test_unmitigated_horizon_caps_the_effective_period(self):
        coverage = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        obsolescence = obsolescence_assessment(48.0, PERIOD)
        self.assertAlmostEqual(effective_support_months(coverage, obsolescence), 48.0, places=9)

    def test_a_missing_commitment_leaves_nothing_to_rely_on(self):
        records = [c for c in full_commitments("asic") if c["name"] != "competence-retention"]
        coverage = coverage_shortfalls(records, PERIOD, "asic")
        obsolescence = obsolescence_assessment(180.0, PERIOD)
        self.assertAlmostEqual(effective_support_months(coverage, obsolescence), 0.0, places=9)

    def test_malformed_obsolescence_report_raises(self):
        coverage = coverage_shortfalls(full_commitments("asic"), PERIOD, "asic")
        with self.assertRaises(ValueError):
            effective_support_months(coverage, {"horizon_months": 12.0})


class TestAssessment(unittest.TestCase):
    def test_clean_plan_is_agreed(self):
        report = assess_final_support_maintenance_plan(clean_spec())
        self.assertEqual(report["disposition"], "agreed")
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["coverage_ratio"], 1.0, places=9)

    def test_short_commitment_makes_the_plan_not_agreeable(self):
        spec = clean_spec()
        spec["commitments"] = full_commitments(
            "asic", spares_availability={"coverage_months": 90.0}
        )
        report = assess_final_support_maintenance_plan(spec)
        self.assertEqual(report["disposition"], "not-agreeable")
        self.assertAlmostEqual(report["coverage_ratio"], 0.75, places=9)

    def test_unmitigated_obsolescence_horizon_caps_the_plan(self):
        spec = clean_spec(obsolescence_horizon_months=60.0)
        report = assess_final_support_maintenance_plan(spec)
        self.assertAlmostEqual(report["effective_support_months"], 60.0, places=9)
        self.assertEqual(report["disposition"], "not-agreeable")

    def test_mitigated_obsolescence_horizon_keeps_the_plan_agreed(self):
        spec = clean_spec(
            obsolescence_horizon_months=60.0, obsolescence_mitigations=["last-time-buy"]
        )
        report = assess_final_support_maintenance_plan(spec)
        self.assertAlmostEqual(report["effective_support_months"], PERIOD, places=9)
        self.assertEqual(report["disposition"], "agreed")

    def test_slow_response_time_is_a_shortfall_not_a_refusal(self):
        spec = clean_spec(maximum_response_days=7.0)
        report = assess_final_support_maintenance_plan(spec)
        self.assertEqual(report["disposition"], "agreed-with-shortfall")
        self.assertAlmostEqual(report["response_time_shortfall_days"], 3.0, places=9)

    def test_ip_core_plan_without_spares_is_agreed(self):
        report = assess_final_support_maintenance_plan(clean_spec("ip-core"))
        self.assertEqual(report["disposition"], "agreed")

    def test_unagreed_commitment_makes_the_plan_not_agreeable(self):
        spec = clean_spec()
        spec["commitments"] = full_commitments(
            "asic", obsolescence_monitoring={"customer_agreed": False}
        )
        report = assess_final_support_maintenance_plan(spec)
        self.assertEqual(report["disposition"], "not-agreeable")

    def test_every_disposition_returned_is_declared(self):
        report = assess_final_support_maintenance_plan(clean_spec())
        self.assertIn(report["disposition"], DISPOSITIONS)

    def test_missing_spec_key_raises(self):
        spec = clean_spec()
        del spec["maximum_response_days"]
        with self.assertRaises(ValueError):
            assess_final_support_maintenance_plan(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_final_support_maintenance_plan([clean_spec()])

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
