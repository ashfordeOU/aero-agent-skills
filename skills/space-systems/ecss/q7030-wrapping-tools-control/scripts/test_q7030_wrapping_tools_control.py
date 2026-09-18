"""Contract tests for the wrapping tool control logic."""

import unittest

from q7030_wrapping_tools_control_logic import (
    BOUND_TOLERANCE,
    DEFAULT_CALIBRATION_INTERVAL_DAYS,
    DEFAULT_GRACE_DAYS,
    TENSION_BAND,
    WEAR_WARNING_FRACTION,
    assess_tool_control,
    bit_coverage_findings,
    calibration_findings,
    calibration_status,
    setup_sample_findings,
    tension_findings,
    tension_ratio,
    tool_disposition,
    wear_findings,
    wear_fraction,
)


def _bit(**over):
    base = {
        "part_number": "bit-26-063",
        "gauge_span": (24, 28),
        "post_diagonal_span_mm": (0.7, 1.1),
        "certified": True,
    }
    base.update(over)
    return base


def _sample(**over):
    base = {
        "turns": 6,
        "overlapping_turns": False,
        "end_play_mm": 0.10,
        "allowable_end_play_mm": 0.25,
    }
    base.update(over)
    return base


def _spec(**over):
    base = {
        "bit": _bit(),
        "gauge_awg": 26,
        "post_diagonal_mm": 0.898,
        "days_since_calibration": 40.0,
        "wraps_since_change": 4000,
        "life_limit_wraps": 20000,
        "sample": _sample(),
        "required_turns": 6,
        "measured_tension_n": 10.0,
        "nominal_tension_n": 10.0,
    }
    base.update(over)
    return base


class BitCoverageTests(unittest.TestCase):
    def test_a_covering_certified_bit_raises_nothing(self):
        self.assertEqual(bit_coverage_findings(_bit(), 26, 0.898), [])

    def test_a_wire_thicker_than_the_bit_span_is_critical(self):
        findings = bit_coverage_findings(_bit(), 20, 0.898)
        self.assertEqual(findings[0]["control"], "bit-gauge-coverage")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_wire_thinner_than_the_bit_span_is_critical(self):
        self.assertEqual(len(bit_coverage_findings(_bit(), 32, 0.898)), 1)

    def test_both_gauge_span_edges_are_covered(self):
        self.assertEqual(bit_coverage_findings(_bit(), 24, 0.898), [])
        self.assertEqual(bit_coverage_findings(_bit(), 28, 0.898), [])

    def test_a_post_outside_the_diagonal_span_is_critical(self):
        findings = bit_coverage_findings(_bit(), 26, 1.6)
        self.assertEqual(findings[0]["control"], "bit-post-coverage")

    def test_a_post_exactly_on_the_span_edge_is_covered(self):
        self.assertEqual(bit_coverage_findings(_bit(), 26, 0.7), [])
        self.assertEqual(bit_coverage_findings(_bit(), 26, 1.1), [])

    def test_an_uncertified_bit_is_critical_even_when_it_covers(self):
        findings = bit_coverage_findings(_bit(certified=False), 26, 0.898)
        self.assertEqual(findings[0]["control"], "bit-certification")

    def test_an_inverted_gauge_span_is_rejected(self):
        with self.assertRaises(ValueError):
            bit_coverage_findings(_bit(gauge_span=(28, 24)), 26, 0.898)

    def test_a_missing_bit_key_is_rejected(self):
        bit = _bit()
        del bit["certified"]
        with self.assertRaises(ValueError):
            bit_coverage_findings(bit, 26, 0.898)

    def test_a_non_boolean_certification_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            bit_coverage_findings(_bit(certified="yes"), 26, 0.898)


class CalibrationTests(unittest.TestCase):
    def test_a_fresh_tool_is_in_calibration(self):
        self.assertEqual(calibration_status(10.0, 180.0, 5.0), "in-calibration")

    def test_a_tool_on_its_interval_is_still_in_calibration(self):
        self.assertEqual(calibration_status(180.0, 180.0, 5.0), "in-calibration")

    def test_a_tool_inside_the_grace_is_due(self):
        self.assertEqual(calibration_status(183.0, 180.0, 5.0), "due")

    def test_a_tool_on_the_last_grace_day_is_still_only_due(self):
        self.assertEqual(calibration_status(185.0, 180.0, 5.0), "due")

    def test_a_tool_past_the_grace_is_out_of_calibration(self):
        self.assertEqual(calibration_status(200.0, 180.0, 5.0), "out-of-calibration")

    def test_an_in_calibration_tool_raises_nothing(self):
        self.assertEqual(calibration_findings(10.0, DEFAULT_CALIBRATION_INTERVAL_DAYS), [])

    def test_a_due_tool_is_a_major_finding(self):
        findings = calibration_findings(
            DEFAULT_CALIBRATION_INTERVAL_DAYS + 1.0,
            DEFAULT_CALIBRATION_INTERVAL_DAYS,
            DEFAULT_GRACE_DAYS,
        )
        self.assertEqual(findings[0]["severity"], "major")

    def test_an_expired_tool_is_critical(self):
        findings = calibration_findings(500.0, DEFAULT_CALIBRATION_INTERVAL_DAYS)
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_negative_calibration_age_is_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(-1.0, 180.0)

    def test_a_zero_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(1.0, 0.0)


class WearTests(unittest.TestCase):
    def test_wear_is_wraps_done_over_the_life_limit(self):
        self.assertAlmostEqual(wear_fraction(5000, 20000), 0.25, places=9)

    def test_a_fresh_bit_has_consumed_nothing(self):
        self.assertAlmostEqual(wear_fraction(0, 20000), 0.0, places=9)

    def test_a_bit_inside_its_warning_band_raises_nothing(self):
        self.assertEqual(wear_findings(1000, 20000), [])

    def test_a_bit_on_the_warning_fraction_owes_a_change(self):
        limit = 20000
        findings = wear_findings(int(WEAR_WARNING_FRACTION * limit), limit)
        self.assertEqual(findings[0]["severity"], "major")

    def test_a_bit_at_its_full_life_is_withdrawn(self):
        findings = wear_findings(20000, 20000)
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[0]["control"], "bit-life")

    def test_a_zero_life_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            wear_fraction(10, 0)

    def test_a_fractional_wrap_count_is_rejected(self):
        with self.assertRaises(ValueError):
            wear_fraction(10.5, 20000)


class SetupSampleTests(unittest.TestCase):
    def test_a_conforming_sample_raises_nothing(self):
        self.assertEqual(setup_sample_findings(_sample(), 6), [])

    def test_a_short_sample_is_critical(self):
        findings = setup_sample_findings(_sample(turns=4), 6)
        self.assertEqual(findings[0]["control"], "sample-turn-count")

    def test_extra_sample_turns_are_not_a_finding(self):
        self.assertEqual(setup_sample_findings(_sample(turns=8), 6), [])

    def test_overlapping_turns_are_critical(self):
        findings = setup_sample_findings(_sample(overlapping_turns=True), 6)
        self.assertEqual(findings[0]["control"], "sample-overlap")

    def test_end_play_exactly_on_its_allowance_is_accepted(self):
        self.assertEqual(
            setup_sample_findings(_sample(end_play_mm=0.25), 6), []
        )

    def test_end_play_above_its_allowance_is_major(self):
        findings = setup_sample_findings(_sample(end_play_mm=0.40), 6)
        self.assertEqual(findings[0]["severity"], "major")

    def test_a_non_boolean_overlap_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            setup_sample_findings(_sample(overlapping_turns="no"), 6)

    def test_a_missing_sample_key_is_rejected(self):
        sample = _sample()
        del sample["end_play_mm"]
        with self.assertRaises(ValueError):
            setup_sample_findings(sample, 6)


class TensionTests(unittest.TestCase):
    def test_tension_ratio_is_measured_over_nominal(self):
        self.assertAlmostEqual(tension_ratio(9.0, 10.0), 0.9, places=9)

    def test_a_tool_on_nominal_raises_nothing(self):
        self.assertEqual(tension_findings(10.0, 10.0), [])

    def test_a_tool_on_the_lower_band_edge_is_accepted(self):
        self.assertEqual(tension_findings(TENSION_BAND[0] * 10.0, 10.0), [])

    def test_a_tool_below_the_band_is_critical(self):
        findings = tension_findings(5.0, 10.0)
        self.assertEqual(findings[0]["control"], "wrap-tension")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_tool_above_the_band_is_critical(self):
        self.assertEqual(len(tension_findings(20.0, 10.0)), 1)

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            tension_findings(10.0, 10.0, (1.2, 0.8))


class DispositionTests(unittest.TestCase):
    def test_no_findings_release_the_tool(self):
        self.assertEqual(tool_disposition([]), "release-for-use")

    def test_a_major_finding_releases_with_actions(self):
        self.assertEqual(
            tool_disposition([{"severity": "major", "control": "x", "detail": "y"}]),
            "release-with-actions",
        )

    def test_a_critical_finding_withdraws_the_tool(self):
        self.assertEqual(
            tool_disposition([{"severity": "critical", "control": "x", "detail": "y"}]),
            "withdraw-from-service",
        )

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            tool_disposition([{"severity": "urgent"}])


class AssessmentTests(unittest.TestCase):
    def test_a_controlled_tool_set_is_released(self):
        result = assess_tool_control(_spec())
        self.assertEqual(result["disposition"], "release-for-use")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["calibration_status"], "in-calibration")

    def test_a_worn_bit_alone_releases_with_actions(self):
        result = assess_tool_control(_spec(wraps_since_change=19000))
        self.assertEqual(result["disposition"], "release-with-actions")
        self.assertGreater(result["wear_fraction"], WEAR_WARNING_FRACTION)

    def test_an_expired_calibration_withdraws_the_tool(self):
        result = assess_tool_control(_spec(days_since_calibration=400.0))
        self.assertEqual(result["disposition"], "withdraw-from-service")
        self.assertEqual(result["calibration_status"], "out-of-calibration")

    def test_a_failed_set_up_sample_withdraws_the_tool(self):
        result = assess_tool_control(_spec(sample=_sample(overlapping_turns=True)))
        self.assertEqual(result["disposition"], "withdraw-from-service")

    def test_a_tool_outside_its_tension_band_is_withdrawn(self):
        result = assess_tool_control(_spec(measured_tension_n=4.0))
        self.assertEqual(result["disposition"], "withdraw-from-service")
        self.assertAlmostEqual(result["tension_ratio"], 0.4, places=9)

    def test_a_bit_fitted_for_the_wrong_gauge_is_withdrawn(self):
        result = assess_tool_control(_spec(gauge_awg=20))
        controls = [f["control"] for f in result["findings"]]
        self.assertIn("bit-gauge-coverage", controls)

    def test_findings_are_ranked_critical_first(self):
        result = assess_tool_control(
            _spec(days_since_calibration=400.0, wraps_since_change=19000)
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["sample"]
        with self.assertRaises(ValueError):
            assess_tool_control(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_tool_control([_spec()])

    def test_bound_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
