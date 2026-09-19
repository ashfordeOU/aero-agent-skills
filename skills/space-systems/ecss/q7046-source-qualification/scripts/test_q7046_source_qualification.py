"""Contract tests for the ECSS-Q-ST-70-46C fastener source-qualification logic."""

import unittest
from datetime import date

from q7046_source_qualification_logic import (
    INDEX_TOLERANCE,
    SEVERITY_WEIGHTS,
    assess_source_qualification,
    audit_currency,
    audit_demerit_score,
    capability_index,
    characteristic_capability,
    governing_capability,
    parse_iso_date,
    qualification_expiry,
    sample_statistics,
)

THREAD_PITCH = {
    "name": "thread-pitch-diameter",
    "measurements": [5.00, 5.01, 4.99, 5.00, 5.02, 4.98],
    "lower_limit": 4.90,
    "upper_limit": 5.10,
}

HEAD_HEIGHT = {
    "name": "head-height",
    "measurements": [3.00, 3.04, 2.96, 3.02, 2.98, 3.00],
    "lower_limit": 2.80,
    "upper_limit": 3.20,
}


def spec(**overrides):
    base = {
        "manufacturer": "Fastener Works",
        "characteristics": [dict(THREAD_PITCH), dict(HEAD_HEIGHT)],
        "required_index": 1.33,
        "audit_date": "2026-01-15",
        "reference_date": "2026-05-12",
        "validity_days": 730,
        "audit_findings": [{"severity": "minor", "reference": "F-01"}],
    }
    base.update(overrides)
    return base


class StatisticsTests(unittest.TestCase):
    def test_mean_of_a_symmetric_sample(self):
        mean, _ = sample_statistics([1.0, 2.0, 3.0])
        self.assertAlmostEqual(mean, 2.0, places=9)

    def test_sample_standard_deviation_uses_n_minus_one(self):
        _, sigma = sample_statistics([1.0, 2.0, 3.0])
        self.assertAlmostEqual(sigma, 1.0, places=9)

    def test_identical_measurements_give_zero_sigma(self):
        _, sigma = sample_statistics([4.0, 4.0, 4.0, 4.0])
        self.assertAlmostEqual(sigma, 0.0, places=12)

    def test_single_measurement_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([4.0])

    def test_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([4.0, "4.1"])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics(4.0)


class CapabilityIndexTests(unittest.TestCase):
    def test_centred_process_index(self):
        self.assertAlmostEqual(capability_index(5.0, 0.05, 4.7, 5.3), 2.0, places=9)

    def test_offset_process_takes_the_near_side(self):
        self.assertAlmostEqual(capability_index(5.2, 0.05, 4.7, 5.3), 2.0 / 3.0, places=9)

    def test_index_scales_inversely_with_sigma(self):
        wide = capability_index(5.0, 0.10, 4.7, 5.3)
        tight = capability_index(5.0, 0.05, 4.7, 5.3)
        self.assertAlmostEqual(tight, 2.0 * wide, places=9)

    def test_zero_sigma_rejected(self):
        with self.assertRaises(ValueError):
            capability_index(5.0, 0.0, 4.7, 5.3)

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            capability_index(5.0, 0.05, 5.3, 4.7)

    def test_boolean_mean_rejected(self):
        with self.assertRaises(ValueError):
            capability_index(True, 0.05, 4.7, 5.3)

    def test_characteristic_record_carries_sample_size(self):
        record = characteristic_capability(THREAD_PITCH)
        self.assertEqual(record["sample_size"], 6)
        self.assertGreater(record["capability_index"], 1.0)

    def test_characteristic_missing_key_rejected(self):
        bad = dict(THREAD_PITCH)
        del bad["upper_limit"]
        with self.assertRaises(ValueError):
            characteristic_capability(bad)

    def test_weakest_characteristic_governs(self):
        result = governing_capability([THREAD_PITCH, HEAD_HEIGHT])
        indices = [r["capability_index"] for r in result["records"]]
        self.assertAlmostEqual(
            result["governing"]["capability_index"], min(indices), places=12
        )

    def test_empty_characteristic_set_rejected(self):
        with self.assertRaises(ValueError):
            governing_capability([])


class AuditScoreTests(unittest.TestCase):
    def test_empty_audit_scores_zero(self):
        self.assertAlmostEqual(audit_demerit_score([])["score"], 0.0, places=12)

    def test_weights_accumulate(self):
        findings = [{"severity": "major"}, {"severity": "minor"}, {"severity": "minor"}]
        expected = SEVERITY_WEIGHTS["major"] + 2.0 * SEVERITY_WEIGHTS["minor"]
        self.assertAlmostEqual(audit_demerit_score(findings)["score"], expected, places=9)

    def test_counts_are_grouped_by_severity(self):
        findings = [{"severity": "minor"}, {"severity": "minor"}, {"severity": "observation"}]
        counts = audit_demerit_score(findings)["counts"]
        self.assertEqual(counts["minor"], 2)
        self.assertEqual(counts["observation"], 1)

    def test_critical_finding_is_reported_as_blocking(self):
        result = audit_demerit_score([{"severity": "critical", "reference": "F-09"}])
        self.assertEqual(result["blocking"], ["F-09"])

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            audit_demerit_score([{"severity": "cosmetic"}])

    def test_non_mapping_finding_rejected(self):
        with self.assertRaises(ValueError):
            audit_demerit_score(["major"])

    def test_empty_weight_table_rejected(self):
        with self.assertRaises(ValueError):
            audit_demerit_score([], weights={})


class CurrencyTests(unittest.TestCase):
    def test_elapsed_days_is_the_calendar_difference(self):
        result = audit_currency("2026-01-15", "2026-01-25", 730)
        self.assertEqual(result["elapsed_days"], 10)
        self.assertEqual(result["remaining_days"], 720)
        self.assertTrue(result["current"])

    def test_audit_exactly_at_the_validity_edge_is_still_current(self):
        result = audit_currency("2026-01-15", "2026-01-25", 10)
        self.assertEqual(result["remaining_days"], 0)
        self.assertTrue(result["current"])

    def test_lapsed_audit_is_not_current(self):
        result = audit_currency("2024-01-15", "2026-05-12", 365)
        self.assertFalse(result["current"])
        self.assertLess(result["remaining_days"], 0)

    def test_audit_after_the_reference_date_rejected(self):
        with self.assertRaises(ValueError):
            audit_currency("2026-06-01", "2026-05-12", 730)

    def test_zero_validity_rejected(self):
        with self.assertRaises(ValueError):
            audit_currency("2026-01-15", "2026-05-12", 0)

    def test_expiry_is_the_audit_date_plus_validity(self):
        self.assertEqual(qualification_expiry("2026-01-15", 30), date(2026, 2, 14))

    def test_iso_parse_rejects_nonsense(self):
        with self.assertRaises(ValueError):
            parse_iso_date("15 Jan 2026")


class AssessmentTests(unittest.TestCase):
    def test_capable_and_clean_audit_qualifies(self):
        result = assess_source_qualification(spec())
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["reasons"], [])

    def test_expiry_is_reported(self):
        result = assess_source_qualification(spec(audit_date="2026-01-15", validity_days=365))
        self.assertEqual(result["expiry"], date(2027, 1, 15))

    def test_critical_finding_blocks_qualification(self):
        result = assess_source_qualification(
            spec(audit_findings=[{"severity": "critical", "reference": "F-09"}])
        )
        self.assertEqual(result["status"], "not-qualified")

    def test_insufficient_capability_blocks_qualification(self):
        result = assess_source_qualification(spec(required_index=25.0))
        self.assertEqual(result["status"], "not-qualified")
        self.assertIn("governing characteristic", result["reasons"][0])

    def test_demerit_total_over_the_limit_is_conditional(self):
        findings = [{"severity": "major"} for _ in range(3)]
        result = assess_source_qualification(spec(audit_findings=findings, demerit_limit=20.0))
        self.assertEqual(result["status"], "conditionally-qualified")

    def test_demerit_total_exactly_on_the_limit_still_qualifies(self):
        findings = [{"severity": "major"}, {"severity": "major"}]
        result = assess_source_qualification(spec(audit_findings=findings, demerit_limit=20.0))
        self.assertEqual(result["status"], "qualified")

    def test_index_exactly_on_the_requirement_is_capable(self):
        base = spec()
        achieved = assess_source_qualification(base)["achieved_index"]
        tight = assess_source_qualification(spec(required_index=achieved))
        self.assertEqual(tight["status"], "qualified")
        self.assertAlmostEqual(
            tight["achieved_index"], tight["required_index"], places=9
        )
        self.assertLessEqual(
            abs(tight["achieved_index"] - tight["required_index"]), INDEX_TOLERANCE
        )

    def test_lapsed_audit_downgrades_to_conditional(self):
        result = assess_source_qualification(spec(validity_days=30))
        self.assertEqual(result["status"], "conditionally-qualified")
        self.assertTrue(any("lapsed" in r for r in result["reasons"]))

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["audit_findings"]
        with self.assertRaises(ValueError):
            assess_source_qualification(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_qualification("Fastener Works")

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_qualification(spec(manufacturer="  "))

    def test_negative_required_index_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_qualification(spec(required_index=-1.0))


if __name__ == "__main__":
    unittest.main()
