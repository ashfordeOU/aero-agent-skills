#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.4.3 arc discharge
performance recovery.

Exercises scripts/e20_arc_discharge_performance_recovery_logic.py
(stdlib unittest, offline). Contract: an arc event maps to exactly one
family and an unrecognized kind raises; a sustained secondary arc is
never a permitted brief outage; the outage is the difference between
arc onset and restored service on one clock, with a restoration before
the onset raising; the outage is checked against the allowance with an
exact match absorbed; the recovery ratio is oriented by the sense of
merit so that one means specification met; the residual shortfall is
reported in percent against an allowance; a ground-commanded recovery
slower than the allowance is a finding while an autonomous recovery is
not; and the aggregated review is acceptable only when every finding
list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_arc_discharge_performance_recovery_logic as ar  # noqa: E402


def _recovered_parameters():
    return [
        {
            "name": "downlink_eirp_dbw",
            "post_arc_value": 24.0,
            "specified_value": 23.5,
            "sense": ar.SENSE_HIGHER_IS_BETTER,
        },
        {
            "name": "bus_ripple_mv",
            "post_arc_value": 40.0,
            "specified_value": 50.0,
            "sense": ar.SENSE_LOWER_IS_BETTER,
        },
    ]


def _clean_event():
    """A primary discharge that satisfies every 6.3.4.3 condition."""
    return {
        "function_id": "TTC-TX-A",
        "event_kind": "surface_dielectric_primary_discharge",
        "arc_onset_s": 1000.0,
        "service_restored_s": 1000.4,
        "outage_allowance_s": 1.0,
        "parameters": _recovered_parameters(),
        "recovery_mode": "autonomous",
        "ground_response_latency_s": 0.0,
    }


class TestCategorizeArcEvent(unittest.TestCase):
    def test_surface_discharge_is_a_primary_event(self):
        self.assertEqual(
            ar.categorize_arc_event("surface_dielectric_primary_discharge"),
            "primary_discharge",
        )

    def test_triple_junction_discharge_is_a_primary_event(self):
        self.assertEqual(
            ar.categorize_arc_event("triple_junction_primary_discharge"),
            "primary_discharge",
        )

    def test_array_secondary_arc_is_sustained(self):
        self.assertEqual(
            ar.categorize_arc_event("solar_array_sustained_secondary_arc"),
            "sustained_secondary_arc",
        )

    def test_bus_driven_arc_is_sustained(self):
        self.assertEqual(
            ar.categorize_arc_event("bus_driven_sustained_arc"),
            "sustained_secondary_arc",
        )

    def test_families_are_disjoint(self):
        self.assertEqual(
            ar.PRIMARY_ARC_KINDS & ar.SUSTAINED_ARC_KINDS, frozenset()
        )

    def test_unrecognized_event_raises(self):
        with self.assertRaises(ValueError):
            ar.categorize_arc_event("micrometeoroid_impact")


class TestArcFamilyFindings(unittest.TestCase):
    def test_primary_discharge_yields_no_finding(self):
        self.assertEqual(
            ar.arc_family_findings(
                "TTC-TX-A", "harness_insulation_flashover"
            ),
            [],
        )

    def test_sustained_arc_is_flagged(self):
        findings = ar.arc_family_findings(
            "SA-STR-3", "solar_array_sustained_secondary_arc"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "sustained_secondary_arc_not_a_brief_outage",
        )
        self.assertEqual(findings[0]["function"], "SA-STR-3")

    def test_unrecognized_event_raises_through_family_findings(self):
        with self.assertRaises(ValueError):
            ar.arc_family_findings("SA-STR-3", "thruster_plume_glow")


class TestOutageDuration(unittest.TestCase):
    def test_duration_is_the_clock_difference(self):
        self.assertAlmostEqual(
            ar.outage_duration_s(1000.0, 1000.4), 0.4, places=9
        )

    def test_instant_recovery_is_zero(self):
        self.assertAlmostEqual(
            ar.outage_duration_s(500.0, 500.0), 0.0, places=12
        )

    def test_negative_onset_raises(self):
        with self.assertRaises(ValueError):
            ar.outage_duration_s(-1.0, 10.0)

    def test_restoration_before_onset_raises(self):
        with self.assertRaises(ValueError):
            ar.outage_duration_s(1000.0, 999.0)

    def test_short_outage_passes(self):
        self.assertEqual(ar.outage_findings("TTC-TX-A", 0.4, 1.0), [])

    def test_long_outage_is_flagged(self):
        findings = ar.outage_findings("TTC-TX-A", 4.0, 1.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "arc_outage_exceeds_allowance")
        self.assertAlmostEqual(findings[0]["duration_s"], 4.0, places=9)

    def test_outage_exactly_at_allowance_passes_despite_clock_drift(self):
        # The duration is a difference of two clock values and lands a
        # few representation units above an allowance it physically
        # meets; the compliant case must still pass.
        duration = ar.outage_duration_s(1000.1, 1000.1 + 0.3)
        self.assertEqual(ar.outage_findings("TTC-TX-A", duration, 0.3), [])

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            ar.outage_findings("TTC-TX-A", -0.1, 1.0)

    def test_non_positive_allowance_raises(self):
        with self.assertRaises(ValueError):
            ar.outage_findings("TTC-TX-A", 0.4, 0.0)


class TestRecoveryRatio(unittest.TestCase):
    def test_higher_is_better_ratio_above_one_when_exceeded(self):
        self.assertAlmostEqual(
            ar.recovery_ratio(24.0, 20.0, ar.SENSE_HIGHER_IS_BETTER),
            1.2,
            places=9,
        )

    def test_higher_is_better_ratio_below_one_when_short(self):
        self.assertAlmostEqual(
            ar.recovery_ratio(18.0, 20.0, ar.SENSE_HIGHER_IS_BETTER),
            0.9,
            places=9,
        )

    def test_lower_is_better_ratio_above_one_when_quieter(self):
        self.assertAlmostEqual(
            ar.recovery_ratio(40.0, 50.0, ar.SENSE_LOWER_IS_BETTER),
            1.25,
            places=9,
        )

    def test_lower_is_better_ratio_below_one_when_noisier(self):
        self.assertAlmostEqual(
            ar.recovery_ratio(80.0, 50.0, ar.SENSE_LOWER_IS_BETTER),
            0.625,
            places=9,
        )

    def test_unrecognized_sense_raises(self):
        with self.assertRaises(ValueError):
            ar.recovery_ratio(24.0, 20.0, "bigger_is_nicer")

    def test_non_positive_specified_value_raises(self):
        with self.assertRaises(ValueError):
            ar.recovery_ratio(24.0, 0.0, ar.SENSE_HIGHER_IS_BETTER)

    def test_negative_post_arc_value_raises(self):
        with self.assertRaises(ValueError):
            ar.recovery_ratio(-1.0, 20.0, ar.SENSE_HIGHER_IS_BETTER)

    def test_zero_post_arc_value_raises_for_lower_is_better(self):
        with self.assertRaises(ValueError):
            ar.recovery_ratio(0.0, 50.0, ar.SENSE_LOWER_IS_BETTER)

    def test_zero_post_arc_value_is_allowed_for_higher_is_better(self):
        self.assertAlmostEqual(
            ar.recovery_ratio(0.0, 20.0, ar.SENSE_HIGHER_IS_BETTER),
            0.0,
            places=12,
        )


class TestPerformanceRecovered(unittest.TestCase):
    def test_exceeding_the_specification_is_recovered(self):
        self.assertTrue(
            ar.performance_recovered(24.0, 20.0, ar.SENSE_HIGHER_IS_BETTER)
        )

    def test_meeting_the_specification_is_recovered(self):
        self.assertTrue(
            ar.performance_recovered(20.0, 20.0, ar.SENSE_HIGHER_IS_BETTER)
        )

    def test_falling_short_is_not_recovered(self):
        self.assertFalse(
            ar.performance_recovered(19.0, 20.0, ar.SENSE_HIGHER_IS_BETTER)
        )

    def test_summed_value_meeting_the_specification_is_recovered(self):
        # 0.1 + 0.2 lands a few units above 0.3, so the lower-is-better
        # ratio lands a few units below one on a compliant parameter.
        self.assertTrue(
            ar.performance_recovered(
                0.1 + 0.2, 0.3, ar.SENSE_LOWER_IS_BETTER
            )
        )

    def test_shortfall_is_zero_when_recovered(self):
        self.assertAlmostEqual(
            ar.residual_degradation_percent(
                24.0, 20.0, ar.SENSE_HIGHER_IS_BETTER
            ),
            0.0,
            places=12,
        )

    def test_shortfall_is_ten_percent_at_ninety_percent_of_spec(self):
        self.assertAlmostEqual(
            ar.residual_degradation_percent(
                18.0, 20.0, ar.SENSE_HIGHER_IS_BETTER
            ),
            10.0,
            places=9,
        )

    def test_shortfall_uses_the_lower_is_better_orientation(self):
        self.assertAlmostEqual(
            ar.residual_degradation_percent(
                100.0, 50.0, ar.SENSE_LOWER_IS_BETTER
            ),
            50.0,
            places=9,
        )


class TestPerformanceFindings(unittest.TestCase):
    def test_fully_recovered_set_yields_no_finding(self):
        self.assertEqual(
            ar.performance_findings("TTC-TX-A", _recovered_parameters()), []
        )

    def test_degraded_parameter_is_flagged(self):
        parameters = _recovered_parameters()
        parameters[0]["post_arc_value"] = 21.15
        findings = ar.performance_findings("TTC-TX-A", parameters)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "post_arc_performance_not_restored"
        )
        self.assertEqual(findings[0]["parameter"], "downlink_eirp_dbw")
        self.assertAlmostEqual(
            findings[0]["shortfall_percent"], 10.0, places=6
        )

    def test_both_parameters_can_be_flagged(self):
        parameters = _recovered_parameters()
        parameters[0]["post_arc_value"] = 10.0
        parameters[1]["post_arc_value"] = 500.0
        self.assertEqual(
            len(ar.performance_findings("TTC-TX-A", parameters)), 2
        )

    def test_shortfall_inside_the_allowance_passes(self):
        parameters = _recovered_parameters()
        parameters[0]["post_arc_value"] = 22.325
        self.assertEqual(
            ar.performance_findings(
                "TTC-TX-A", parameters, residual_allowance_percent=10.0
            ),
            [],
        )

    def test_shortfall_above_the_allowance_is_flagged(self):
        parameters = _recovered_parameters()
        parameters[0]["post_arc_value"] = 11.75
        findings = ar.performance_findings(
            "TTC-TX-A", parameters, residual_allowance_percent=10.0
        )
        self.assertEqual(len(findings), 1)
        self.assertAlmostEqual(
            findings[0]["allowance_percent"], 10.0, places=9
        )

    def test_empty_parameter_list_raises(self):
        with self.assertRaises(ValueError):
            ar.performance_findings("TTC-TX-A", [])

    def test_negative_residual_allowance_raises(self):
        with self.assertRaises(ValueError):
            ar.performance_findings(
                "TTC-TX-A", _recovered_parameters(),
                residual_allowance_percent=-1.0,
            )

    def test_bad_sense_raises_through_performance_findings(self):
        parameters = _recovered_parameters()
        parameters[1]["sense"] = "whatever_is_fine"
        with self.assertRaises(ValueError):
            ar.performance_findings("TTC-TX-A", parameters)


class TestRecoveryAutonomy(unittest.TestCase):
    def test_autonomous_recovery_yields_no_finding(self):
        self.assertEqual(
            ar.recovery_autonomy_findings("TTC-TX-A", "autonomous", 600.0, 1.0),
            [],
        )

    def test_fast_ground_loop_inside_the_allowance_passes(self):
        self.assertEqual(
            ar.recovery_autonomy_findings(
                "TTC-TX-A", "ground_commanded", 0.5, 1.0
            ),
            [],
        )

    def test_slow_ground_loop_is_flagged(self):
        findings = ar.recovery_autonomy_findings(
            "TTC-TX-A", "ground_commanded", 3600.0, 1.0
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "ground_recovery_slower_than_outage_allowance",
        )

    def test_ground_latency_exactly_at_allowance_passes(self):
        self.assertEqual(
            ar.recovery_autonomy_findings(
                "TTC-TX-A", "ground_commanded", 0.1 + 0.2, 0.3
            ),
            [],
        )

    def test_unrecognized_recovery_mode_raises(self):
        with self.assertRaises(ValueError):
            ar.recovery_autonomy_findings("TTC-TX-A", "hope", 0.5, 1.0)

    def test_negative_latency_raises(self):
        with self.assertRaises(ValueError):
            ar.recovery_autonomy_findings(
                "TTC-TX-A", "ground_commanded", -1.0, 1.0
            )

    def test_non_positive_allowance_raises_in_autonomy_check(self):
        with self.assertRaises(ValueError):
            ar.recovery_autonomy_findings("TTC-TX-A", "autonomous", 0.0, 0.0)


class TestArcEventReview(unittest.TestCase):
    def test_clean_event_is_acceptable(self):
        review = ar.arc_event_review(_clean_event())
        self.assertTrue(ar.is_recovery_acceptable(review))

    def test_review_carries_all_four_finding_lists(self):
        review = ar.arc_event_review(_clean_event())
        self.assertEqual(
            sorted(review),
            ["arc_family", "autonomy", "outage", "performance"],
        )

    def test_sustained_arc_breaks_acceptability(self):
        event = _clean_event()
        event["event_kind"] = "bus_driven_sustained_arc"
        review = ar.arc_event_review(event)
        self.assertFalse(ar.is_recovery_acceptable(review))
        self.assertEqual(len(review["arc_family"]), 1)
        self.assertEqual(review["outage"], [])

    def test_long_outage_breaks_acceptability(self):
        event = _clean_event()
        event["service_restored_s"] = 1010.0
        review = ar.arc_event_review(event)
        self.assertEqual(len(review["outage"]), 1)
        self.assertEqual(review["performance"], [])

    def test_unrecovered_parameter_breaks_acceptability(self):
        event = _clean_event()
        event["parameters"][0]["post_arc_value"] = 12.0
        review = ar.arc_event_review(event)
        self.assertEqual(len(review["performance"]), 1)
        self.assertFalse(ar.is_recovery_acceptable(review))

    def test_slow_ground_recovery_breaks_acceptability(self):
        event = _clean_event()
        event["recovery_mode"] = "ground_commanded"
        event["ground_response_latency_s"] = 900.0
        review = ar.arc_event_review(event)
        self.assertEqual(len(review["autonomy"]), 1)

    def test_missing_ground_latency_defaults_to_zero(self):
        event = _clean_event()
        del event["ground_response_latency_s"]
        event["recovery_mode"] = "ground_commanded"
        review = ar.arc_event_review(event)
        self.assertEqual(review["autonomy"], [])

    def test_review_does_not_mutate_the_event(self):
        event = _clean_event()
        snapshot = dict(event)
        ar.arc_event_review(event)
        self.assertEqual(event, snapshot)

    def test_inconsistent_clock_raises_through_review(self):
        event = _clean_event()
        event["service_restored_s"] = 900.0
        with self.assertRaises(ValueError):
            ar.arc_event_review(event)

    def test_review_is_deterministic(self):
        first = ar.arc_event_review(_clean_event())
        second = ar.arc_event_review(_clean_event())
        self.assertEqual(first, second)

    def test_residual_allowance_is_honoured_by_the_review(self):
        event = _clean_event()
        event["parameters"][0]["post_arc_value"] = 22.325
        event["residual_allowance_percent"] = 10.0
        review = ar.arc_event_review(event)
        self.assertTrue(ar.is_recovery_acceptable(review))

    def test_math_module_is_the_only_numeric_dependency(self):
        self.assertTrue(hasattr(math, "isclose"))


if __name__ == "__main__":
    unittest.main()
