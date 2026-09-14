"""Contract tests for the clause 9.4.5.2.3 diode acceptance sentencing logic."""

import unittest

from e2008_diode_characterization_pass_criteria_logic import (
    DEFAULT_SENTENCING_POLICY,
    DIODE_ACCEPT,
    DIODE_ACCEPT_MARGINAL,
    DIODE_LOT_ACCEPTED,
    DIODE_LOT_ACCEPTED_WITH_ADVISORY,
    DIODE_LOT_CONTAINS_REJECTS,
    DIODE_LOT_REJECT_ALLOWANCE_EXCEEDED,
    DIODE_REJECT_BOTH,
    DIODE_REJECT_FORWARD,
    DIODE_REJECT_REVERSE,
    lot_reject_fraction,
    margin_fraction,
    margin_is_marginal,
    refer_forward_voltage,
    sentence_diode,
    sentence_diode_lot,
    validate_sentencing_policy,
    validate_source_control_limits,
    within_limit,
)

LIMITS = {
    "drawing_reference": "SCD-PV-DIODE-0042",
    "drawing_issue": "issue-C",
    "max_forward_voltage_v": 0.800,
    "forward_test_current_a": 1.500,
    "max_reverse_leakage_a": 2.0e-6,
    "reverse_test_voltage_v": 40.0,
    "reference_junction_temperature_c": 25.0,
    "forward_voltage_tempco_v_per_k": -0.002,
}


def _policy(**overrides):
    policy = dict(DEFAULT_SENTENCING_POLICY)
    policy.update(overrides)
    return policy


def _limits(**overrides):
    limits = dict(LIMITS)
    limits.update(overrides)
    return limits


def _record(part_id="D-001", **overrides):
    record = {
        "part_id": part_id,
        "measured_forward_voltage_v": 0.700,
        "junction_temperature_c": 25.0,
        "measured_reverse_leakage_a": 4.0e-7,
    }
    record.update(overrides)
    return record


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_sentencing_policy(DEFAULT_SENTENCING_POLICY),
            DEFAULT_SENTENCING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sentencing_policy("advisory_margin_fraction")

    def test_allowance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_sentencing_policy(_policy(max_lot_reject_fraction=1.0))

    def test_negative_advisory_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_sentencing_policy(_policy(advisory_margin_fraction=-0.01))


class LimitProvenanceTests(unittest.TestCase):
    def test_a_referenced_limit_set_validates(self):
        provenance = validate_source_control_limits(LIMITS)
        self.assertEqual(provenance["drawing_reference"], "SCD-PV-DIODE-0042")
        self.assertEqual(provenance["drawing_issue"], "issue-C")

    def test_limits_without_a_drawing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_source_control_limits(_limits(drawing_reference=""))

    def test_limits_without_a_drawing_issue_rejected(self):
        limits = _limits()
        del limits["drawing_issue"]
        with self.assertRaises(ValueError):
            validate_source_control_limits(limits)

    def test_a_blank_reference_is_not_a_reference(self):
        with self.assertRaises(ValueError):
            validate_source_control_limits(_limits(drawing_reference="   "))

    def test_non_positive_forward_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_source_control_limits(_limits(max_forward_voltage_v=0.0))

    def test_non_positive_leakage_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_source_control_limits(_limits(max_reverse_leakage_a=0.0))

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_source_control_limits(["drawing_reference"])


class TemperatureReferralTests(unittest.TestCase):
    def test_a_reading_at_the_reference_temperature_does_not_move(self):
        self.assertAlmostEqual(
            refer_forward_voltage(0.700, 25.0, -0.002, 25.0), 0.700, places=12
        )

    def test_a_warm_reading_is_referred_upward(self):
        referred = refer_forward_voltage(0.700, 75.0, -0.002, 25.0)
        self.assertAlmostEqual(referred, 0.800, places=12)

    def test_a_cold_reading_is_referred_downward(self):
        referred = refer_forward_voltage(0.700, -25.0, -0.002, 25.0)
        self.assertAlmostEqual(referred, 0.600, places=12)

    def test_a_zero_coefficient_leaves_the_reading_alone(self):
        self.assertAlmostEqual(
            refer_forward_voltage(0.700, 90.0, 0.0, 25.0), 0.700, places=12
        )

    def test_a_non_numeric_junction_temperature_rejected(self):
        with self.assertRaises(ValueError):
            refer_forward_voltage(0.700, "warm", -0.002, 25.0)


class MarginTests(unittest.TestCase):
    def test_margin_is_the_share_left_under_the_limit(self):
        self.assertAlmostEqual(margin_fraction(0.600, 0.800), 0.25, places=12)

    def test_a_value_on_the_limit_has_no_margin(self):
        self.assertAlmostEqual(margin_fraction(0.800, 0.800), 0.0, places=12)

    def test_a_tie_on_the_limit_still_passes(self):
        self.assertTrue(within_limit(0.800, 0.800))

    def test_a_value_over_the_limit_fails(self):
        self.assertFalse(within_limit(0.801, 0.800))

    def test_a_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(0.5, 0.0)

    def test_margin_exactly_on_the_advisory_band_is_not_marginal(self):
        band = float(DEFAULT_SENTENCING_POLICY["advisory_margin_fraction"])
        margin = margin_fraction(0.95, 1.0)
        self.assertAlmostEqual(margin, band, places=9)
        self.assertFalse(margin_is_marginal(margin))

    def test_a_thin_margin_is_marginal(self):
        self.assertTrue(margin_is_marginal(0.01))

    def test_a_negative_margin_is_a_breach_not_an_advisory(self):
        self.assertFalse(margin_is_marginal(-0.10))


class SentenceDiodeTests(unittest.TestCase):
    def test_a_good_part_is_accepted(self):
        result = sentence_diode(_record(), LIMITS)
        self.assertEqual(result["disposition"], DIODE_ACCEPT)
        self.assertEqual(result["notes"], [])

    def test_a_warm_bench_does_not_flatter_a_failing_part(self):
        result = sentence_diode(
            _record(measured_forward_voltage_v=0.760, junction_temperature_c=60.0),
            LIMITS,
        )
        self.assertAlmostEqual(result["referred_forward_voltage_v"], 0.830, places=12)
        self.assertEqual(result["disposition"], DIODE_REJECT_FORWARD)

    def test_a_leaky_part_is_rejected_on_the_reverse_branch(self):
        result = sentence_diode(
            _record(measured_reverse_leakage_a=5.0e-6), LIMITS
        )
        self.assertEqual(result["disposition"], DIODE_REJECT_REVERSE)
        self.assertTrue(result["forward_within_limit"])

    def test_a_part_failing_both_branches_is_grouped_as_both(self):
        result = sentence_diode(
            _record(
                measured_forward_voltage_v=0.900,
                measured_reverse_leakage_a=5.0e-6,
            ),
            LIMITS,
        )
        self.assertEqual(result["disposition"], DIODE_REJECT_BOTH)
        self.assertEqual(len(result["notes"]), 2)

    def test_a_part_sitting_on_the_limit_is_accepted_and_flagged(self):
        result = sentence_diode(
            _record(measured_forward_voltage_v=0.800), LIMITS
        )
        self.assertTrue(result["forward_within_limit"])
        self.assertEqual(result["disposition"], DIODE_ACCEPT_MARGINAL)
        self.assertAlmostEqual(result["forward_margin_fraction"], 0.0, places=12)

    def test_a_part_with_a_thin_leakage_margin_is_flagged(self):
        result = sentence_diode(
            _record(measured_reverse_leakage_a=1.95e-6), LIMITS
        )
        self.assertEqual(result["disposition"], DIODE_ACCEPT_MARGINAL)

    def test_a_record_without_a_part_id_rejected(self):
        record = _record()
        del record["part_id"]
        with self.assertRaises(ValueError):
            sentence_diode(record, LIMITS)

    def test_a_negative_leakage_reading_rejected(self):
        with self.assertRaises(ValueError):
            sentence_diode(_record(measured_reverse_leakage_a=-1.0e-7), LIMITS)

    def test_a_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            sentence_diode(["part_id"], LIMITS)


class LotVerdictTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        records = [_record("D-%03d" % n) for n in range(20)]
        result = sentence_diode_lot(records, LIMITS)
        self.assertEqual(result["verdict"], DIODE_LOT_ACCEPTED)
        self.assertEqual(result["reject_count"], 0)
        self.assertEqual(result["findings"], [])

    def test_a_marginal_part_downgrades_a_clean_lot_to_advisory(self):
        records = [_record("D-%03d" % n) for n in range(20)]
        records[4]["measured_forward_voltage_v"] = 0.800
        result = sentence_diode_lot(records, LIMITS)
        self.assertEqual(result["verdict"], DIODE_LOT_ACCEPTED_WITH_ADVISORY)
        self.assertEqual(result["marginal_count"], 1)

    def test_one_reject_inside_the_allowance_leaves_the_lot_usable(self):
        records = [_record("D-%03d" % n) for n in range(20)]
        records[7]["measured_reverse_leakage_a"] = 5.0e-6
        result = sentence_diode_lot(records, LIMITS)
        self.assertEqual(result["verdict"], DIODE_LOT_CONTAINS_REJECTS)
        self.assertTrue(result["within_reject_allowance"])

    def test_a_reject_share_on_the_allowance_stays_inside_it(self):
        records = [_record("D-%03d" % n) for n in range(20)]
        records[0]["measured_reverse_leakage_a"] = 5.0e-6
        result = sentence_diode_lot(records, LIMITS)
        self.assertAlmostEqual(
            result["lot_reject_fraction"],
            float(DEFAULT_SENTENCING_POLICY["max_lot_reject_fraction"]),
            places=9,
        )
        self.assertTrue(result["within_reject_allowance"])

    def test_too_many_rejects_fail_the_lot_itself(self):
        records = [_record("D-%03d" % n) for n in range(20)]
        for index in range(5):
            records[index]["measured_reverse_leakage_a"] = 5.0e-6
        result = sentence_diode_lot(records, LIMITS)
        self.assertEqual(result["verdict"], DIODE_LOT_REJECT_ALLOWANCE_EXCEEDED)
        self.assertFalse(result["within_reject_allowance"])

    def test_every_breach_is_named_not_only_the_first(self):
        records = [_record("D-%03d" % n) for n in range(20)]
        records[1]["measured_reverse_leakage_a"] = 5.0e-6
        records[2]["measured_forward_voltage_v"] = 0.900
        result = sentence_diode_lot(records, LIMITS)
        self.assertEqual(result["reject_count"], 2)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_the_drawing_provenance_is_carried_into_the_verdict(self):
        result = sentence_diode_lot([_record()], LIMITS)
        self.assertEqual(result["drawing_reference"], "SCD-PV-DIODE-0042")
        self.assertEqual(result["drawing_issue"], "issue-C")

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            sentence_diode_lot([], LIMITS)

    def test_a_duplicate_part_id_rejected(self):
        with self.assertRaises(ValueError):
            sentence_diode_lot([_record("D-001"), _record("D-001")], LIMITS)

    def test_an_untraceable_limit_set_rejected(self):
        with self.assertRaises(ValueError):
            sentence_diode_lot([_record()], _limits(drawing_reference=None))

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            sentence_diode_lot({"part_id": "D-001"}, LIMITS)


class LotFractionTests(unittest.TestCase):
    def test_reject_fraction_is_rejects_over_total(self):
        self.assertAlmostEqual(lot_reject_fraction(3, 60), 0.05, places=12)

    def test_more_rejects_than_parts_rejected(self):
        with self.assertRaises(ValueError):
            lot_reject_fraction(61, 60)

    def test_an_empty_lot_total_rejected(self):
        with self.assertRaises(ValueError):
            lot_reject_fraction(0, 0)

    def test_a_fractional_reject_count_rejected(self):
        with self.assertRaises(ValueError):
            lot_reject_fraction(1.5, 60)


if __name__ == "__main__":
    unittest.main()
