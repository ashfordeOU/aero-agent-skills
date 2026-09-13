"""Contract tests for the clause 6.4.3.15.3 ultraviolet acceptance criteria logic."""

import unittest

from e2008_ultraviolet_exposure_test_criteria_logic import (
    DEFAULT_SHORT_CIRCUIT_TEMPERATURE_COEFFICIENT_PER_C,
    REFERENCE_IRRADIANCE_W_M2,
    REFERENCE_TEMPERATURE_C,
    assess_ultraviolet_acceptance,
    correct_short_circuit_current_to_reference,
    evaluate_specimen_set,
    mean_loss_fraction,
    measurement_current_at_reference,
    sequence_findings,
    short_circuit_current_loss_fraction,
    short_circuit_current_retention_ratio,
    within_limit,
    worst_case_loss_fraction,
)


def _reading(current_a, irradiance=REFERENCE_IRRADIANCE_W_M2,
             temperature=REFERENCE_TEMPERATURE_C, **extra):
    reading = {
        "current_a": current_a,
        "irradiance_w_m2": irradiance,
        "cell_temperature_c": temperature,
    }
    reading.update(extra)
    return reading


def _specimen(specimen_id="UV-1", before=0.5, after=0.49):
    return {
        "specimen_id": specimen_id,
        "pre_exposure": _reading(before),
        "post_exposure": _reading(after),
    }


def _spec(**overrides):
    spec = {
        "specimens": [_specimen("UV-1"), _specimen("UV-2", 0.48, 0.474)],
        "max_loss_fraction": 0.03,
        "required_equivalent_sun_hours": 26298.0,
        "accumulated_equivalent_sun_hours": 26298.0,
    }
    spec.update(overrides)
    return spec


def _ratio(value, expected):
    return value / expected


class CorrectionTests(unittest.TestCase):
    def test_at_reference_conditions_the_correction_is_the_identity(self):
        value = correct_short_circuit_current_to_reference(
            0.5, REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C
        )
        self.assertAlmostEqual(_ratio(value, 0.5), 1.0, places=12)

    def test_halving_the_irradiance_doubles_the_corrected_current(self):
        value = correct_short_circuit_current_to_reference(
            0.5, REFERENCE_IRRADIANCE_W_M2 / 2.0, REFERENCE_TEMPERATURE_C
        )
        self.assertAlmostEqual(_ratio(value, 1.0), 1.0, places=12)

    def test_a_warmer_cell_corrects_down_through_the_positive_coefficient(self):
        value = correct_short_circuit_current_to_reference(
            0.5, REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C + 20.0
        )
        expected = 0.5 / (
            1.0 + DEFAULT_SHORT_CIRCUIT_TEMPERATURE_COEFFICIENT_PER_C * 20.0
        )
        self.assertAlmostEqual(_ratio(value, expected), 1.0, places=12)

    def test_a_specimen_coefficient_overrides_the_default(self):
        value = correct_short_circuit_current_to_reference(
            0.5, REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C + 20.0, 0.001
        )
        expected = 0.5 / (1.0 + 0.001 * 20.0)
        self.assertAlmostEqual(_ratio(value, expected), 1.0, places=12)

    def test_zero_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_to_reference(0.5, 0.0, 25.0)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_to_reference(0.0, 1367.0, 25.0)

    def test_a_coefficient_of_one_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_to_reference(0.5, 1367.0, 25.0, 1.0)

    def test_an_inconsistent_coefficient_and_span_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_to_reference(0.5, 1367.0, 30.0, -0.9)

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_to_reference(True, 1367.0, 25.0)


class MeasurementRecordTests(unittest.TestCase):
    def test_a_reference_condition_record_returns_its_own_current(self):
        self.assertAlmostEqual(
            _ratio(measurement_current_at_reference(_reading(0.5)), 0.5),
            1.0,
            places=12,
        )

    def test_a_record_level_reference_irradiance_is_honoured(self):
        value = measurement_current_at_reference(
            _reading(0.5, irradiance=1000.0, reference_irradiance_w_m2=1000.0)
        )
        self.assertAlmostEqual(_ratio(value, 0.5), 1.0, places=12)

    def test_a_record_missing_its_current_rejected(self):
        record = _reading(0.5)
        del record["current_a"]
        with self.assertRaises(ValueError):
            measurement_current_at_reference(record)

    def test_a_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            measurement_current_at_reference([0.5])


class LossTests(unittest.TestCase):
    def test_loss_fraction_is_the_relative_drop(self):
        self.assertAlmostEqual(
            short_circuit_current_loss_fraction(0.5, 0.49), 0.02, places=9
        )

    def test_retention_ratio_complements_the_loss(self):
        loss = short_circuit_current_loss_fraction(0.5, 0.49)
        retention = short_circuit_current_retention_ratio(0.5, 0.49)
        self.assertAlmostEqual(loss + retention, 1.0, places=12)

    def test_a_gain_comes_back_as_a_negative_loss(self):
        self.assertLess(short_circuit_current_loss_fraction(0.5, 0.52), 0.0)

    def test_within_limit_tolerates_an_exact_equality(self):
        self.assertTrue(within_limit(0.03, 0.03))

    def test_within_limit_rejects_a_clear_excess(self):
        self.assertFalse(within_limit(0.09, 0.03))

    def test_zero_pre_exposure_current_rejected(self):
        with self.assertRaises(ValueError):
            short_circuit_current_loss_fraction(0.0, 0.49)

    def test_non_numeric_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(0.02, "three per cent")


class SpecimenSetTests(unittest.TestCase):
    def test_every_specimen_gets_a_record(self):
        records = evaluate_specimen_set(
            [_specimen("UV-1"), _specimen("UV-2", 0.48, 0.474)], 0.03
        )
        self.assertEqual([r["specimen_id"] for r in records], ["UV-1", "UV-2"])

    def test_a_duplicate_specimen_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen_set([_specimen("UV-1"), _specimen("UV-1")], 0.03)

    def test_an_empty_specimen_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen_set([], 0.03)

    def test_a_blank_specimen_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen_set([_specimen("   ")], 0.03)

    def test_a_specimen_without_a_post_exposure_reading_rejected(self):
        specimen = _specimen("UV-1")
        del specimen["post_exposure"]
        with self.assertRaises(ValueError):
            evaluate_specimen_set([specimen], 0.03)

    def test_a_limit_above_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen_set([_specimen("UV-1")], 1.4)

    def test_the_worst_case_picks_the_largest_loss(self):
        records = evaluate_specimen_set(
            [_specimen("UV-1"), _specimen("UV-2", 0.5, 0.45)], 0.2
        )
        self.assertAlmostEqual(worst_case_loss_fraction(records), 0.10, places=9)

    def test_the_mean_averages_the_set(self):
        records = evaluate_specimen_set(
            [_specimen("UV-1", 0.5, 0.45), _specimen("UV-2", 0.5, 0.40)], 0.3
        )
        self.assertAlmostEqual(mean_loss_fraction(records), 0.15, places=9)

    def test_an_empty_record_set_rejected_by_the_worst_case(self):
        with self.assertRaises(ValueError):
            worst_case_loss_fraction([])


class SequenceTests(unittest.TestCase):
    def test_a_completed_sequence_raises_no_finding(self):
        self.assertEqual(sequence_findings(_spec()), [])

    def test_a_sequence_exactly_at_the_required_dose_raises_no_finding(self):
        self.assertEqual(
            sequence_findings(
                _spec(
                    required_equivalent_sun_hours=26298.0,
                    accumulated_equivalent_sun_hours=26298.0,
                )
            ),
            [],
        )

    def test_a_partial_sequence_is_a_finding(self):
        findings = sequence_findings(
            _spec(accumulated_equivalent_sun_hours=1000.0)
        )
        self.assertEqual(len(findings), 1)

    def test_an_unrecorded_accumulated_dose_is_a_finding(self):
        spec = _spec()
        del spec["accumulated_equivalent_sun_hours"]
        self.assertEqual(len(sequence_findings(spec)), 1)

    def test_no_declared_required_dose_means_no_sequence_finding(self):
        spec = _spec()
        del spec["required_equivalent_sun_hours"]
        del spec["accumulated_equivalent_sun_hours"]
        self.assertEqual(sequence_findings(spec), [])


class AcceptanceTests(unittest.TestCase):
    def test_a_compliant_set_is_accepted(self):
        result = assess_ultraviolet_acceptance(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["failing_specimen_ids"], [])

    def test_a_specimen_past_the_limit_is_a_finding(self):
        result = assess_ultraviolet_acceptance(
            _spec(specimens=[_specimen("UV-1", 0.5, 0.40)])
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failing_specimen_ids"], ["UV-1"])

    def test_a_specimen_exactly_at_the_limit_is_accepted(self):
        result = assess_ultraviolet_acceptance(
            _spec(specimens=[_specimen("UV-1", 0.5, 0.49)], max_loss_fraction=0.02)
        )
        self.assertAlmostEqual(
            result["specimens"][0]["loss_fraction"], 0.02, places=9
        )
        self.assertTrue(result["accepted"])

    def test_a_measured_gain_does_not_fail_the_one_sided_criterion(self):
        result = assess_ultraviolet_acceptance(
            _spec(specimens=[_specimen("UV-1", 0.5, 0.52)])
        )
        self.assertTrue(result["accepted"])
        self.assertLess(result["specimens"][0]["loss_fraction"], 0.0)

    def test_an_incomplete_sequence_fails_a_set_whose_currents_pass(self):
        result = assess_ultraviolet_acceptance(
            _spec(accumulated_equivalent_sun_hours=1000.0)
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["failing_specimen_ids"], [])

    def test_every_failing_specimen_is_reported_not_only_the_first(self):
        result = assess_ultraviolet_acceptance(
            _spec(
                specimens=[
                    _specimen("UV-1", 0.5, 0.40),
                    _specimen("UV-2", 0.5, 0.35),
                ]
            )
        )
        self.assertEqual(result["failing_specimen_ids"], ["UV-1", "UV-2"])
        self.assertEqual(len(result["findings"]), 2)

    def test_the_worst_case_and_mean_losses_are_reported(self):
        result = assess_ultraviolet_acceptance(
            _spec(
                specimens=[
                    _specimen("UV-1", 0.5, 0.45),
                    _specimen("UV-2", 0.5, 0.40),
                ],
                max_loss_fraction=0.3,
            )
        )
        self.assertAlmostEqual(result["worst_case_loss_fraction"], 0.20, places=9)
        self.assertAlmostEqual(result["mean_loss_fraction"], 0.15, places=9)

    def test_the_readings_are_corrected_before_the_comparison(self):
        # The same specimen measured at half irradiance after the exposure is
        # not a fifty per cent loss once both readings are referred.
        specimen = {
            "specimen_id": "UV-1",
            "pre_exposure": _reading(0.5),
            "post_exposure": _reading(0.245, irradiance=REFERENCE_IRRADIANCE_W_M2 / 2.0),
        }
        result = assess_ultraviolet_acceptance(_spec(specimens=[specimen]))
        self.assertAlmostEqual(
            result["specimens"][0]["loss_fraction"], 0.02, places=9
        )
        self.assertTrue(result["accepted"])

    def test_missing_specimens_key_rejected(self):
        spec = _spec()
        del spec["specimens"]
        with self.assertRaises(ValueError):
            assess_ultraviolet_acceptance(spec)

    def test_missing_limit_key_rejected(self):
        spec = _spec()
        del spec["max_loss_fraction"]
        with self.assertRaises(ValueError):
            assess_ultraviolet_acceptance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_ultraviolet_acceptance(["specimens"])

    def test_a_negative_accumulated_dose_rejected(self):
        with self.assertRaises(ValueError):
            assess_ultraviolet_acceptance(
                _spec(accumulated_equivalent_sun_hours=-1.0)
            )


if __name__ == "__main__":
    unittest.main()
