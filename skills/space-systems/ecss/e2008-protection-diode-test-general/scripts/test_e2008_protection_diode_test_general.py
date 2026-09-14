"""Contract tests for the clause 9.6.1 protection diode test general provisions."""

import unittest

from e2008_protection_diode_test_general_logic import (
    ACCEPT,
    AGREED,
    CAPTURE_CONTRADICTED,
    CAPTURE_MISSING,
    CAPTURE_STALE,
    CAPTURED,
    CUSTOMER_ONLY,
    DEFAULT_SPIKE_TEST_CRITERIA,
    FORWARD,
    NOT_ESTABLISHED,
    REFER_FOR_REVIEW,
    REJECT,
    REVERSE,
    SUPPLIER_ONLY,
    UNAGREED,
    agreement_state,
    applied_stress_fraction,
    assess_applied_spike,
    assess_diode_spike_programme,
    assess_protection_diode_test_general,
    assess_spike_allowance,
    capture_state,
    captured_spike_level,
    levels_match,
    spike_stress_v_us,
    validate_control_drawing,
    validate_spike_agreement,
    validate_spike_level,
    validate_spike_test_criteria,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_SPIKE_TEST_CRITERIA)
    criteria.update(overrides)
    return criteria


def _level(**overrides):
    level = {
        "polarity": REVERSE,
        "amplitude_v": 200.0,
        "duration_us": 5.0,
        "repetitions": 10,
    }
    level.update(overrides)
    return level


def _agreement(**overrides):
    agreement = {
        "level": _level(),
        "customer_accepted": True,
        "supplier_accepted": True,
        "agreed_on_day": 30,
    }
    agreement.update(overrides)
    return agreement


def _drawing(**overrides):
    drawing = {
        "id": "PD-4471",
        "issue": "C",
        "issue_day": 40,
        "spike_level": _level(),
    }
    drawing.update(overrides)
    return drawing


def _case(**overrides):
    case = {
        "id": "diode-type-a",
        "agreement": _agreement(),
        "control_drawing": _drawing(),
        "applied_spikes": [_level()],
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_spike_test_criteria(DEFAULT_SPIKE_TEST_CRITERIA),
            DEFAULT_SPIKE_TEST_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_test_criteria("whatever the drawing says")

    def test_a_ceiling_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_test_criteria(
                _criteria(min_applied_stress_fraction=1.0,
                          max_applied_stress_fraction=0.5)
            )

    def test_a_negative_drawing_lead_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_test_criteria(_criteria(max_drawing_lead_days=-2))


class SpikeLevelTests(unittest.TestCase):
    def test_the_stress_is_the_amplitude_duration_product(self):
        self.assertAlmostEqual(_ratio(spike_stress_v_us(_level()), 1000.0), 1.0,
                               places=12)

    def test_a_short_pulse_at_the_right_volts_carries_less_stress(self):
        self.assertAlmostEqual(
            _ratio(spike_stress_v_us(_level(duration_us=1.0)), 200.0), 1.0,
            places=12,
        )

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_level(_level(polarity="either way"))

    def test_a_zero_amplitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_level(_level(amplitude_v=0.0))

    def test_a_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_level(_level(duration_us=-5.0))

    def test_a_fractional_repetition_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_level(_level(repetitions=2.5))

    def test_a_non_boolean_survival_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_level(_level(survived="probably"))

    def test_a_level_with_no_survival_flag_is_taken_as_survived(self):
        self.assertTrue(validate_spike_level(_level())["survived"])


class AgreementTests(unittest.TestCase):
    def test_both_parties_accepting_is_agreed(self):
        self.assertEqual(agreement_state(_agreement()), AGREED)

    def test_a_customer_instruction_alone_is_not_agreement(self):
        self.assertEqual(
            agreement_state(_agreement(supplier_accepted=False)), CUSTOMER_ONLY
        )

    def test_a_supplier_proposal_alone_is_not_agreement(self):
        self.assertEqual(
            agreement_state(_agreement(customer_accepted=False)), SUPPLIER_ONLY
        )

    def test_neither_party_accepting_is_unagreed(self):
        self.assertEqual(
            agreement_state(
                _agreement(customer_accepted=False, supplier_accepted=False)
            ),
            UNAGREED,
        )

    def test_a_non_boolean_acceptance_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_agreement(_agreement(customer_accepted="yes"))

    def test_a_non_integer_agreement_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_spike_agreement(_agreement(agreed_on_day="week 4"))


class ControlDrawingTests(unittest.TestCase):
    def test_a_blank_drawing_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(_drawing(id="   "))

    def test_a_drawing_carrying_no_spike_level_normalises_to_none(self):
        self.assertIsNone(
            validate_control_drawing(_drawing(spike_level=None))["spike_level"]
        )

    def test_a_non_mapping_drawing_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_drawing("PD-4471 issue C")


class LevelMatchTests(unittest.TestCase):
    def test_an_identical_level_matches(self):
        self.assertTrue(levels_match(_level(), _level(), 0.02))

    def test_drift_inside_the_tolerance_matches(self):
        self.assertTrue(levels_match(_level(amplitude_v=202.0), _level(), 0.02))

    def test_drift_exactly_on_the_tolerance_matches(self):
        drifted = _level(amplitude_v=204.0)
        self.assertAlmostEqual(
            abs(drifted["amplitude_v"] - 200.0) / 200.0, 0.02, places=9
        )
        self.assertTrue(levels_match(drifted, _level(), 0.02))

    def test_drift_past_the_tolerance_does_not_match(self):
        self.assertFalse(levels_match(_level(amplitude_v=260.0), _level(), 0.02))

    def test_a_different_polarity_does_not_match(self):
        self.assertFalse(levels_match(_level(polarity=FORWARD), _level(), 0.02))

    def test_a_different_repetition_count_does_not_match(self):
        self.assertFalse(levels_match(_level(repetitions=3), _level(), 0.02))


class CaptureStateTests(unittest.TestCase):
    def test_a_level_on_a_later_issue_is_captured(self):
        self.assertEqual(
            capture_state(_agreement(), _drawing(), _criteria()), CAPTURED
        )

    def test_a_drawing_with_no_spike_level_is_capture_missing(self):
        self.assertEqual(
            capture_state(_agreement(), _drawing(spike_level=None), _criteria()),
            CAPTURE_MISSING,
        )

    def test_a_drawing_carrying_another_figure_is_contradicted(self):
        self.assertEqual(
            capture_state(
                _agreement(), _drawing(spike_level=_level(amplitude_v=260.0)),
                _criteria(),
            ),
            CAPTURE_CONTRADICTED,
        )

    def test_a_drawing_issued_before_the_agreement_is_stale(self):
        self.assertEqual(
            capture_state(_agreement(), _drawing(issue_day=20), _criteria()),
            CAPTURE_STALE,
        )

    def test_a_drawing_issued_on_the_day_of_agreement_is_captured(self):
        self.assertEqual(
            capture_state(_agreement(), _drawing(issue_day=30), _criteria()),
            CAPTURED,
        )

    def test_a_contradicting_figure_outranks_a_stale_issue(self):
        self.assertEqual(
            capture_state(
                _agreement(),
                _drawing(issue_day=20, spike_level=_level(amplitude_v=260.0)),
                _criteria(),
            ),
            CAPTURE_CONTRADICTED,
        )


class AllowanceDispositionTests(unittest.TestCase):
    def test_an_agreed_and_captured_level_is_accepted(self):
        disposition, _reason = assess_spike_allowance(
            _agreement(), _drawing(), _criteria()
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_one_sided_level_leaves_the_allowance_unestablished(self):
        disposition, reason = assess_spike_allowance(
            _agreement(supplier_accepted=False), _drawing(), _criteria()
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("nothing to test", reason)

    def test_a_level_never_captured_leaves_the_allowance_unestablished(self):
        disposition, reason = assess_spike_allowance(
            _agreement(), _drawing(spike_level=None), _criteria()
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("never captured", reason)

    def test_a_drawing_contradicting_the_agreement_rejects(self):
        disposition, reason = assess_spike_allowance(
            _agreement(), _drawing(spike_level=_level(duration_us=9.0)), _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("contradicting", reason)

    def test_a_stale_drawing_issue_goes_to_review(self):
        disposition, reason = assess_spike_allowance(
            _agreement(), _drawing(issue_day=20), _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("later issue", reason)

    def test_no_level_is_returned_while_the_allowance_is_unestablished(self):
        self.assertIsNone(
            captured_spike_level(
                _agreement(), _drawing(spike_level=None), _criteria()
            )
        )

    def test_a_captured_level_is_returned_for_sentencing(self):
        level = captured_spike_level(_agreement(), _drawing(), _criteria())
        self.assertAlmostEqual(_ratio(level["amplitude_v"], 200.0), 1.0, places=12)


class AppliedSpikeTests(unittest.TestCase):
    def test_a_bench_matching_the_level_is_accepted(self):
        disposition, _reason = assess_applied_spike(_level(), _level(), _criteria())
        self.assertEqual(disposition, ACCEPT)

    def test_the_stress_fraction_is_the_ratio_of_the_products(self):
        self.assertAlmostEqual(
            applied_stress_fraction(_level(amplitude_v=240.0), _level()), 1.2,
            places=9,
        )

    def test_a_bench_exactly_on_the_floor_is_accepted(self):
        self.assertAlmostEqual(
            applied_stress_fraction(_level(), _level()),
            DEFAULT_SPIKE_TEST_CRITERIA["min_applied_stress_fraction"],
            places=9,
        )
        disposition, _reason = assess_applied_spike(_level(), _level(), _criteria())
        self.assertEqual(disposition, ACCEPT)

    def test_an_under_stressed_bench_demonstrates_nothing(self):
        disposition, reason = assess_applied_spike(
            _level(amplitude_v=150.0), _level(), _criteria()
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("under-stressed", reason)

    def test_a_short_pulse_at_the_right_volts_still_under_stresses(self):
        disposition, _reason = assess_applied_spike(
            _level(duration_us=1.0), _level(), _criteria()
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)

    def test_a_bench_of_the_wrong_polarity_says_nothing(self):
        disposition, reason = assess_applied_spike(
            _level(polarity=FORWARD), _level(), _criteria()
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("says nothing", reason)

    def test_too_few_repetitions_leave_the_duty_undemonstrated(self):
        disposition, reason = assess_applied_spike(
            _level(repetitions=4), _level(), _criteria()
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("duty", reason)

    def test_a_bench_exactly_on_the_ceiling_is_accepted(self):
        bench = _level(amplitude_v=240.0)
        self.assertAlmostEqual(
            applied_stress_fraction(bench, _level()),
            DEFAULT_SPIKE_TEST_CRITERIA["max_applied_stress_fraction"],
            places=9,
        )
        disposition, _reason = assess_applied_spike(bench, _level(), _criteria())
        self.assertEqual(disposition, ACCEPT)

    def test_an_over_stressed_bench_goes_to_review(self):
        disposition, reason = assess_applied_spike(
            _level(amplitude_v=300.0), _level(), _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("beyond what was bought", reason)

    def test_a_diode_that_did_not_survive_rejects(self):
        disposition, reason = assess_applied_spike(
            _level(survived=False), _level(), _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("did not survive", reason)


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(
            worst_disposition([REFER_FOR_REVIEW, REJECT, ACCEPT]), REJECT
        )

    def test_an_unestablished_allowance_outranks_a_review(self):
        self.assertEqual(
            worst_disposition([REFER_FOR_REVIEW, NOT_ESTABLISHED]), NOT_ESTABLISHED
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "looks fine"])


class DiodeCaseTests(unittest.TestCase):
    def test_an_agreed_captured_and_tested_diode_is_accepted(self):
        result = assess_protection_diode_test_general(_case(), _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["spikes_sentenced"], 1)

    def test_the_captured_stress_is_reported(self):
        result = assess_protection_diode_test_general(_case(), _criteria())
        self.assertAlmostEqual(
            _ratio(result["captured_stress_v_us"], 1000.0), 1.0, places=12
        )

    def test_a_bench_cannot_be_sentenced_without_a_captured_level(self):
        result = assess_protection_diode_test_general(
            _case(control_drawing=_drawing(spike_level=None)), _criteria()
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["spikes_sentenced"], 0)
        self.assertEqual(len(result["advisories"]), 1)
        self.assertIsNone(result["captured_stress_v_us"])

    def test_a_bench_spike_is_still_validated_when_it_cannot_be_sentenced(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_test_general(
                _case(
                    control_drawing=_drawing(spike_level=None),
                    applied_spikes=[_level(amplitude_v=0.0)],
                ),
                _criteria(),
            )

    def test_a_contradicting_drawing_governs_the_diode(self):
        result = assess_protection_diode_test_general(
            _case(control_drawing=_drawing(spike_level=_level(duration_us=9.0))),
            _criteria(),
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["capture_state"], CAPTURE_CONTRADICTED)

    def test_an_under_stressed_bench_is_named_by_index(self):
        result = assess_protection_diode_test_general(
            _case(applied_spikes=[_level(), _level(amplitude_v=100.0)]), _criteria()
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["spikes_not_accepted"], (1,))

    def test_a_case_missing_the_control_drawing_rejected(self):
        case = _case()
        del case["control_drawing"]
        with self.assertRaises(ValueError):
            assess_protection_diode_test_general(case, _criteria())

    def test_a_non_sequence_bench_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_test_general(
                _case(applied_spikes="one spike"), _criteria()
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_test_general(["PD-4471"], _criteria())


class ProgrammeRollupTests(unittest.TestCase):
    def test_a_clean_programme_is_accepted(self):
        result = assess_diode_spike_programme(
            [_case(), _case(id="diode-type-b")], _criteria()
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["diodes_assessed"], 2)

    def test_one_uncaptured_diode_governs_the_programme(self):
        result = assess_diode_spike_programme(
            [
                _case(),
                _case(id="diode-type-b", control_drawing=_drawing(spike_level=None)),
            ],
            _criteria(),
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["diodes_without_a_captured_level"], ("diode-type-b",))
        self.assertEqual(result["diodes_not_accepted"], ("diode-type-b",))

    def test_a_duplicate_diode_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_spike_programme([_case(), _case()], _criteria())

    def test_an_empty_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_spike_programme([], _criteria())

    def test_a_non_sequence_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_spike_programme({"id": "diode-type-a"}, _criteria())


if __name__ == "__main__":
    unittest.main()
