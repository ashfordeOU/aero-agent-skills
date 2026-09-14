"""Contract tests for the clause 12.6.11.1.2 ionising irradiation pass criteria."""

import unittest

from e2008_ionising_irradiation_pass_criteria_logic import (
    DEFAULT_SENTENCING_POLICY,
    LOT_ACCEPTED,
    LOT_ACCEPTED_WITH_ADVISORY,
    LOT_CONTAINS_REJECTS,
    LOT_REJECT_ALLOWANCE_EXCEEDED,
    MAXIMUM_LIMIT,
    MINIMUM_LIMIT,
    PART_ACCEPTED,
    PART_ACCEPTED_WITH_ADVISORY,
    PART_REJECTED_BOTH_READINGS,
    PART_REJECTED_POST_ANNEAL,
    PART_REJECTED_POST_IRRADIATION,
    annealing_recovery_fraction,
    assess_irradiated_lot,
    assess_parameter,
    assess_part,
    irradiation_shift,
    is_rejected,
    is_reverse_annealing,
    limit_margin_fraction,
    meets_limit,
    residual_shift,
    validate_drawing_limit,
    validate_reading,
    validate_sentencing_policy,
    worst_reading,
)

FORWARD_LIMIT = {
    "parameter": "forward_voltage_drop_v",
    "drawing_reference": "SCD-4471",
    "drawing_issue": "C",
    "condition": "one ampere forward, reference junction temperature",
    "direction": MAXIMUM_LIMIT,
    "limit_value": 0.95,
}

LEAKAGE_LIMIT = {
    "parameter": "reverse_leakage_ua",
    "drawing_reference": "SCD-4471",
    "drawing_issue": "C",
    "condition": "two hundred volts reverse, reference junction temperature",
    "direction": MAXIMUM_LIMIT,
    "limit_value": 5.0,
}

BREAKDOWN_LIMIT = {
    "parameter": "reverse_breakdown_v",
    "drawing_reference": "SCD-4471",
    "drawing_issue": "C",
    "condition": "one hundred microamperes reverse",
    "direction": MINIMUM_LIMIT,
    "limit_value": 250.0,
}

LIMITS = [FORWARD_LIMIT, LEAKAGE_LIMIT]

GOOD_READINGS = {
    "forward_voltage_drop_v": {
        "pre_irradiation": 0.72,
        "post_irradiation": 0.86,
        "post_anneal": 0.80,
    },
    "reverse_leakage_ua": {
        "pre_irradiation": 0.5,
        "post_irradiation": 3.0,
        "post_anneal": 1.5,
    },
}


def _limit(**overrides):
    limit = dict(FORWARD_LIMIT)
    limit.update(overrides)
    return limit


def _policy(**overrides):
    policy = dict(DEFAULT_SENTENCING_POLICY)
    policy.update(overrides)
    return policy


def _readings(**overrides):
    readings = {name: dict(value) for name, value in GOOD_READINGS.items()}
    for name, value in overrides.items():
        readings[name] = dict(value)
    return readings


def _part(serial="SN-001", **overrides):
    return {"serial": serial, "readings": _readings(**overrides)}


def _lot(parts):
    return {"drawing_limits": list(LIMITS), "parts": list(parts)}


class PolicyAndProvenanceTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_sentencing_policy(DEFAULT_SENTENCING_POLICY),
            DEFAULT_SENTENCING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sentencing_policy("advisory")

    def test_an_advisory_band_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_sentencing_policy(_policy(advisory_margin_fraction=1.4))

    def test_a_negative_reject_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_sentencing_policy(_policy(lot_reject_allowance_fraction=-0.1))

    def test_a_limit_without_a_drawing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limit(_limit(drawing_reference="   "))

    def test_a_limit_without_a_drawing_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limit(_limit(drawing_issue=""))

    def test_a_limit_without_its_test_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limit(_limit(condition=""))

    def test_an_unknown_limit_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limit(_limit(direction="about"))

    def test_a_zero_limit_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limit(_limit(limit_value=0.0))

    def test_a_reading_missing_the_annealed_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading({"pre_irradiation": 0.7, "post_irradiation": 0.8})

    def test_a_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(
                {
                    "pre_irradiation": 0.7,
                    "post_irradiation": "high",
                    "post_anneal": 0.8,
                }
            )


class ComparisonTests(unittest.TestCase):
    def test_a_reading_on_a_maximum_limit_meets_it(self):
        self.assertTrue(meets_limit(0.95, FORWARD_LIMIT))

    def test_a_reading_above_a_maximum_limit_fails(self):
        self.assertFalse(meets_limit(1.05, FORWARD_LIMIT))

    def test_a_reading_on_a_minimum_limit_meets_it(self):
        self.assertTrue(meets_limit(250.0, BREAKDOWN_LIMIT))

    def test_a_reading_below_a_minimum_limit_fails(self):
        self.assertFalse(meets_limit(240.0, BREAKDOWN_LIMIT))

    def test_a_margin_on_the_limit_is_zero(self):
        self.assertAlmostEqual(limit_margin_fraction(0.95, FORWARD_LIMIT), 0.0, places=9)

    def test_a_breach_gives_a_negative_margin(self):
        self.assertLess(limit_margin_fraction(1.90, FORWARD_LIMIT), 0.0)

    def test_a_minimum_limit_margin_counts_upward(self):
        self.assertAlmostEqual(
            limit_margin_fraction(300.0, BREAKDOWN_LIMIT), 0.2, places=9
        )


class ShiftAndRecoveryTests(unittest.TestCase):
    def test_the_irradiation_shift_is_measured_from_the_baseline(self):
        self.assertAlmostEqual(
            irradiation_shift(GOOD_READINGS["reverse_leakage_ua"]), 2.5, places=9
        )

    def test_the_residual_shift_is_what_the_mission_carries(self):
        self.assertAlmostEqual(
            residual_shift(GOOD_READINGS["reverse_leakage_ua"]), 1.0, places=9
        )

    def test_the_recovery_fraction_is_the_share_the_soak_gave_back(self):
        self.assertAlmostEqual(
            annealing_recovery_fraction(GOOD_READINGS["reverse_leakage_ua"]),
            0.6,
            places=9,
        )

    def test_a_full_return_to_baseline_recovers_everything(self):
        reading = {
            "pre_irradiation": 0.5,
            "post_irradiation": 3.0,
            "post_anneal": 0.5,
        }
        self.assertAlmostEqual(annealing_recovery_fraction(reading), 1.0, places=9)

    def test_an_unshifted_parameter_has_no_recovery_denominator(self):
        reading = {
            "pre_irradiation": 0.8,
            "post_irradiation": 0.8,
            "post_anneal": 0.8,
        }
        with self.assertRaises(ValueError):
            annealing_recovery_fraction(reading)

    def test_a_soak_that_made_things_worse_is_flagged(self):
        reading = {
            "pre_irradiation": 0.5,
            "post_irradiation": 2.0,
            "post_anneal": 3.5,
        }
        self.assertTrue(is_reverse_annealing(reading))

    def test_a_soak_that_recovered_is_not_flagged(self):
        self.assertFalse(is_reverse_annealing(GOOD_READINGS["forward_voltage_drop_v"]))

    def test_both_post_exposure_states_are_reported_together(self):
        self.assertEqual(
            worst_reading(GOOD_READINGS["forward_voltage_drop_v"]), (0.86, 0.80)
        )


class ParameterDispositionTests(unittest.TestCase):
    def test_a_healthy_parameter_is_accepted(self):
        outcome = assess_parameter(
            FORWARD_LIMIT, GOOD_READINGS["forward_voltage_drop_v"]
        )
        self.assertEqual(outcome["disposition"], PART_ACCEPTED)
        self.assertEqual(outcome["findings"], [])

    def test_a_breach_on_the_irradiated_reading_alone_is_named_as_such(self):
        reading = {
            "pre_irradiation": 0.72,
            "post_irradiation": 1.05,
            "post_anneal": 0.80,
        }
        outcome = assess_parameter(FORWARD_LIMIT, reading)
        self.assertEqual(outcome["disposition"], PART_REJECTED_POST_IRRADIATION)

    def test_a_breach_on_the_annealed_reading_alone_is_named_as_such(self):
        reading = {
            "pre_irradiation": 0.72,
            "post_irradiation": 0.80,
            "post_anneal": 1.02,
        }
        outcome = assess_parameter(FORWARD_LIMIT, reading)
        self.assertEqual(outcome["disposition"], PART_REJECTED_POST_ANNEAL)
        self.assertTrue(outcome["reverse_annealing"])

    def test_a_part_breaching_both_readings_is_grouped_apart(self):
        reading = {
            "pre_irradiation": 0.72,
            "post_irradiation": 1.10,
            "post_anneal": 1.05,
        }
        outcome = assess_parameter(FORWARD_LIMIT, reading)
        self.assertEqual(outcome["disposition"], PART_REJECTED_BOTH_READINGS)
        self.assertTrue(any("irradiated reading" in t for t in outcome["findings"]))
        self.assertTrue(any("annealed reading" in t for t in outcome["findings"]))

    def test_a_margin_inside_the_advisory_band_is_flagged_not_failed(self):
        limit = _limit(limit_value=1.0)
        reading = {
            "pre_irradiation": 0.5,
            "post_irradiation": 0.96,
            "post_anneal": 0.70,
        }
        outcome = assess_parameter(limit, reading)
        self.assertEqual(outcome["disposition"], PART_ACCEPTED_WITH_ADVISORY)

    def test_a_margin_exactly_on_the_advisory_band_is_not_marginal(self):
        limit = _limit(limit_value=1.0)
        reading = {
            "pre_irradiation": 0.5,
            "post_irradiation": 0.95,
            "post_anneal": 0.70,
        }
        outcome = assess_parameter(limit, reading)
        self.assertEqual(outcome["disposition"], PART_ACCEPTED)

    def test_a_poor_recovery_is_reported_without_failing_the_part(self):
        reading = {
            "pre_irradiation": 0.5,
            "post_irradiation": 3.0,
            "post_anneal": 2.9,
        }
        outcome = assess_parameter(LEAKAGE_LIMIT, reading)
        self.assertEqual(outcome["disposition"], PART_ACCEPTED_WITH_ADVISORY)
        self.assertTrue(any("recovered" in text for text in outcome["findings"]))


class PartAndLotTests(unittest.TestCase):
    def test_a_healthy_part_is_accepted(self):
        self.assertEqual(assess_part(_part(), LIMITS)["disposition"], PART_ACCEPTED)

    def test_a_part_missing_a_measured_parameter_is_refused(self):
        part = _part()
        del part["readings"]["reverse_leakage_ua"]
        with self.assertRaises(ValueError):
            assess_part(part, LIMITS)

    def test_a_part_without_a_serial_is_refused(self):
        with self.assertRaises(ValueError):
            assess_part({"readings": _readings()}, LIMITS)

    def test_one_breached_parameter_sentences_the_whole_part(self):
        part = _part(
            reverse_leakage_ua={
                "pre_irradiation": 0.5,
                "post_irradiation": 9.0,
                "post_anneal": 1.5,
            }
        )
        self.assertEqual(
            assess_part(part, LIMITS)["disposition"], PART_REJECTED_POST_IRRADIATION
        )

    def test_separate_branch_failures_on_one_part_group_as_both(self):
        part = _part(
            forward_voltage_drop_v={
                "pre_irradiation": 0.72,
                "post_irradiation": 1.20,
                "post_anneal": 0.80,
            },
            reverse_leakage_ua={
                "pre_irradiation": 0.5,
                "post_irradiation": 3.0,
                "post_anneal": 9.0,
            },
        )
        self.assertEqual(
            assess_part(part, LIMITS)["disposition"], PART_REJECTED_BOTH_READINGS
        )

    def test_a_clean_lot_is_accepted(self):
        lot = _lot([_part("SN-%03d" % index) for index in range(1, 11)])
        outcome = assess_irradiated_lot(lot)
        self.assertEqual(outcome["verdict"], LOT_ACCEPTED)
        self.assertEqual(outcome["rejected_serials"], ())

    def test_an_advisory_part_moves_the_lot_to_advisory(self):
        parts = [_part("SN-%03d" % index) for index in range(1, 10)]
        parts.append(
            _part(
                "SN-010",
                reverse_leakage_ua={
                    "pre_irradiation": 0.5,
                    "post_irradiation": 3.0,
                    "post_anneal": 2.9,
                },
            )
        )
        self.assertEqual(
            assess_irradiated_lot(_lot(parts))["verdict"], LOT_ACCEPTED_WITH_ADVISORY
        )

    def test_a_reject_share_on_the_allowance_still_only_contains_rejects(self):
        parts = [_part("SN-%03d" % index) for index in range(1, 10)]
        parts.append(
            _part(
                "SN-010",
                forward_voltage_drop_v={
                    "pre_irradiation": 0.72,
                    "post_irradiation": 1.30,
                    "post_anneal": 1.20,
                },
            )
        )
        outcome = assess_irradiated_lot(_lot(parts))
        self.assertAlmostEqual(outcome["reject_share"], 0.1, places=9)
        self.assertEqual(outcome["verdict"], LOT_CONTAINS_REJECTS)

    def test_a_reject_share_above_the_allowance_fails_the_lot(self):
        parts = [_part("SN-%03d" % index) for index in range(1, 9)]
        for serial in ("SN-009", "SN-010"):
            parts.append(
                _part(
                    serial,
                    forward_voltage_drop_v={
                        "pre_irradiation": 0.72,
                        "post_irradiation": 1.30,
                        "post_anneal": 1.20,
                    },
                )
            )
        outcome = assess_irradiated_lot(_lot(parts))
        self.assertEqual(outcome["verdict"], LOT_REJECT_ALLOWANCE_EXCEEDED)
        self.assertEqual(len(outcome["rejected_serials"]), 2)

    def test_every_finding_is_carried_to_the_lot_record(self):
        parts = [
            _part(
                "SN-001",
                forward_voltage_drop_v={
                    "pre_irradiation": 0.72,
                    "post_irradiation": 1.30,
                    "post_anneal": 1.20,
                },
            )
        ]
        outcome = assess_irradiated_lot(_lot(parts))
        self.assertTrue(all(text.startswith("SN-001: ") for text in outcome["findings"]))
        self.assertGreaterEqual(len(outcome["findings"]), 2)

    def test_a_lot_without_drawing_limits_is_refused(self):
        with self.assertRaises(ValueError):
            assess_irradiated_lot({"parts": [_part()]})

    def test_an_empty_lot_is_not_an_accepted_lot(self):
        with self.assertRaises(ValueError):
            assess_irradiated_lot({"drawing_limits": list(LIMITS), "parts": []})

    def test_is_rejected_refuses_a_non_string(self):
        with self.assertRaises(ValueError):
            is_rejected(7)

    def test_is_rejected_recognises_every_reject_branch(self):
        self.assertTrue(is_rejected(PART_REJECTED_POST_IRRADIATION))
        self.assertTrue(is_rejected(PART_REJECTED_POST_ANNEAL))
        self.assertTrue(is_rejected(PART_REJECTED_BOTH_READINGS))
        self.assertFalse(is_rejected(PART_ACCEPTED_WITH_ADVISORY))


if __name__ == "__main__":
    unittest.main()
