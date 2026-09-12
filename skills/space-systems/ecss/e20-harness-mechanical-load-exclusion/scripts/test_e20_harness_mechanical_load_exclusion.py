#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.8.2 harness mechanical
load exclusion.

Exercises scripts/e20_harness_mechanical_load_exclusion_logic.py
(stdlib unittest, offline). Contract: every attachment kind maps to
exactly one category and an unrecognized kind raises; the distributed
transverse load is mass per metre times acceleration times standard
gravity; span tension and sag are exact inverses of each other and the
longest permitted spacing reproduces the allowable tension at the
boundary; a span is flagged for tension above the allowable, sag above
the clearance, spacing above the routing limit and a bend radius below
the minimum; a moving interface needs slack equal to the summed
relative displacement times the slack factor and is flagged when the
installed slack is short or one side is unanchored; a connector is
flagged when it reacts more than its allowable, when the first support
is too far away, or when strain relief is absent; and the aggregated
review is compliant only when all four lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_harness_mechanical_load_exclusion_logic as hx  # noqa: E402


def _clean_span():
    """A clamped span that satisfies every clause 5.8.2 span check."""
    return {
        "span_id": "HRN-SPAN-01",
        "bundle_mass_per_m_kg": 0.25,
        "quasi_static_accel_g": 20.0,
        "span_length_m": 0.20,
        "installed_sag_m": 0.010,
        "allowable_tension_n": 400.0,
        "clearance_to_structure_m": 0.030,
        "max_clamp_spacing_m": 0.25,
        "bundle_diameter_m": 0.012,
        "installed_bend_radius_m": 0.090,
    }


def _clean_crossing():
    return {
        "crossing_id": "HRN-XING-01",
        "attachment_kind": "p_clamp_on_structure_standoff",
        "thermal_displacement_m": 0.002,
        "mechanism_stroke_m": 0.004,
        "assembly_tolerance_m": 0.001,
        "installed_slack_m": 0.020,
        "supported_both_sides": True,
    }


def _clean_termination():
    return {
        "termination_id": "HRN-TERM-01",
        "unsupported_mass_kg": 0.05,
        "quasi_static_accel_g": 20.0,
        "allowable_connector_load_n": 25.0,
        "first_support_distance_m": 0.040,
        "max_first_support_distance_m": 0.075,
        "strain_relief_present": True,
    }


class CategorizeHarnessAttachmentTest(unittest.TestCase):
    def test_p_clamp_is_a_restraint(self):
        self.assertEqual(
            hx.categorize_harness_attachment("p_clamp_on_structure_standoff"),
            "restraint",
        )

    def test_cable_tray_tie_is_a_restraint(self):
        self.assertEqual(
            hx.categorize_harness_attachment("cable_tray_tie"), "restraint"
        )

    def test_adhesive_tie_base_is_a_restraint(self):
        self.assertEqual(
            hx.categorize_harness_attachment("adhesive_tie_base_on_panel"),
            "restraint",
        )

    def test_structural_tie_is_a_load_path(self):
        self.assertEqual(
            hx.categorize_harness_attachment("harness_as_structural_tie"),
            "load_path",
        )

    def test_connector_as_sole_support_is_a_load_path(self):
        self.assertEqual(
            hx.categorize_harness_attachment("connector_as_sole_bundle_support"),
            "load_path",
        )

    def test_trapped_in_faying_surface_is_a_load_path(self):
        self.assertEqual(
            hx.categorize_harness_attachment(
                "harness_trapped_in_bolted_joint_faying_surface"
            ),
            "load_path",
        )

    def test_every_kind_is_categorized_exactly_once(self):
        overlap = (
            hx.RESTRAINT_ATTACHMENT_KINDS & hx.LOAD_PATH_ATTACHMENT_KINDS
        )
        self.assertEqual(overlap, frozenset())

    def test_unrecognized_kind_raises(self):
        with self.assertRaises(ValueError):
            hx.categorize_harness_attachment("zip_tie_to_a_wish")

    def test_empty_kind_raises(self):
        with self.assertRaises(ValueError):
            hx.categorize_harness_attachment("")


class DistributedTransverseLoadTest(unittest.TestCase):
    def test_load_is_mass_times_acceleration(self):
        self.assertAlmostEqual(
            hx.distributed_transverse_load(0.25, 20.0),
            0.25 * 20.0 * hx.STANDARD_GRAVITY_M_S2,
            places=9,
        )

    def test_zero_acceleration_gives_zero_load(self):
        self.assertAlmostEqual(
            hx.distributed_transverse_load(0.25, 0.0), 0.0, places=12
        )

    def test_non_positive_mass_raises(self):
        with self.assertRaises(ValueError):
            hx.distributed_transverse_load(0.0, 20.0)

    def test_negative_acceleration_raises(self):
        with self.assertRaises(ValueError):
            hx.distributed_transverse_load(0.25, -1.0)


class SpanMechanicsTest(unittest.TestCase):
    def test_tension_follows_the_shallow_sag_relation(self):
        self.assertAlmostEqual(
            hx.span_tension(50.0, 0.4, 0.01),
            50.0 * 0.16 / 0.08,
            places=9,
        )

    def test_sag_is_the_inverse_of_tension(self):
        tension = hx.span_tension(50.0, 0.4, 0.01)
        self.assertAlmostEqual(hx.span_sag(50.0, 0.4, tension), 0.01, places=12)

    def test_zero_load_gives_zero_tension(self):
        self.assertAlmostEqual(hx.span_tension(0.0, 0.4, 0.01), 0.0, places=12)

    def test_max_spacing_reproduces_the_allowable_tension(self):
        span_m = hx.max_support_spacing(50.0, 0.01, 400.0)
        self.assertAlmostEqual(
            hx.span_tension(50.0, span_m, 0.01), 400.0, places=6
        )

    def test_zero_sag_raises(self):
        with self.assertRaises(ValueError):
            hx.span_tension(50.0, 0.4, 0.0)

    def test_non_positive_span_raises_in_tension(self):
        with self.assertRaises(ValueError):
            hx.span_tension(50.0, 0.0, 0.01)

    def test_negative_load_raises_in_sag(self):
        with self.assertRaises(ValueError):
            hx.span_sag(-1.0, 0.4, 400.0)

    def test_non_positive_tension_raises_in_sag(self):
        with self.assertRaises(ValueError):
            hx.span_sag(50.0, 0.4, 0.0)

    def test_non_positive_allowable_raises_in_max_spacing(self):
        with self.assertRaises(ValueError):
            hx.max_support_spacing(50.0, 0.01, 0.0)

    def test_non_positive_sag_raises_in_max_spacing(self):
        with self.assertRaises(ValueError):
            hx.max_support_spacing(50.0, 0.0, 400.0)

    def test_minimum_bend_radius_is_a_diameter_multiple(self):
        self.assertAlmostEqual(hx.minimum_bend_radius(0.012, 6.0), 0.072, places=9)

    def test_bend_radius_ratio_below_one_raises(self):
        with self.assertRaises(ValueError):
            hx.minimum_bend_radius(0.012, 0.5)

    def test_non_positive_diameter_raises(self):
        with self.assertRaises(ValueError):
            hx.minimum_bend_radius(0.0)


class SpanFindingsTest(unittest.TestCase):
    def test_clean_span_has_no_findings(self):
        self.assertEqual(hx.span_findings(_clean_span()), [])

    def test_tension_exactly_at_the_allowable_passes(self):
        span = _clean_span()
        load = hx.distributed_transverse_load(
            span["bundle_mass_per_m_kg"], span["quasi_static_accel_g"]
        )
        span["span_length_m"] = hx.max_support_spacing(
            load, span["installed_sag_m"], span["allowable_tension_n"]
        )
        span["max_clamp_spacing_m"] = span["span_length_m"]
        self.assertEqual(hx.span_findings(span), [])

    def test_excess_tension_is_flagged(self):
        span = _clean_span()
        span["allowable_tension_n"] = 1.0
        findings = hx.span_findings(span)
        self.assertEqual(len(findings), 1)
        self.assertIn("tension", findings[0])

    def test_sag_beyond_clearance_is_flagged(self):
        span = _clean_span()
        span["clearance_to_structure_m"] = 0.005
        findings = hx.span_findings(span)
        self.assertTrue(any("clearance" in f for f in findings))

    def test_sag_exactly_at_the_clearance_passes(self):
        span = _clean_span()
        span["clearance_to_structure_m"] = span["installed_sag_m"]
        self.assertEqual(hx.span_findings(span), [])

    def test_spacing_beyond_the_routing_limit_is_flagged(self):
        span = _clean_span()
        span["max_clamp_spacing_m"] = 0.10
        findings = hx.span_findings(span)
        self.assertTrue(any("clamp spacing" in f for f in findings))

    def test_bend_radius_below_the_minimum_is_flagged(self):
        span = _clean_span()
        span["installed_bend_radius_m"] = 0.030
        findings = hx.span_findings(span)
        self.assertTrue(any("bend radius" in f for f in findings))

    def test_bend_radius_exactly_at_the_minimum_passes(self):
        span = _clean_span()
        span["installed_bend_radius_m"] = hx.minimum_bend_radius(
            span["bundle_diameter_m"]
        )
        self.assertEqual(hx.span_findings(span), [])

    def test_bend_radius_without_a_diameter_raises(self):
        span = _clean_span()
        del span["bundle_diameter_m"]
        with self.assertRaises(ValueError):
            hx.span_findings(span)

    def test_missing_required_key_raises(self):
        span = _clean_span()
        del span["allowable_tension_n"]
        with self.assertRaises(ValueError):
            hx.span_findings(span)

    def test_negative_clearance_raises(self):
        span = _clean_span()
        span["clearance_to_structure_m"] = -0.001
        with self.assertRaises(ValueError):
            hx.span_findings(span)


class ServiceLoopTest(unittest.TestCase):
    def test_required_length_applies_the_slack_factor(self):
        self.assertAlmostEqual(
            hx.required_service_loop_length(0.002, 0.004, 0.001, 1.25),
            0.007 * 1.25,
            places=12,
        )

    def test_default_slack_factor_is_used(self):
        self.assertAlmostEqual(
            hx.required_service_loop_length(0.002, 0.004, 0.001),
            0.007 * hx.DEFAULT_SLACK_FACTOR,
            places=12,
        )

    def test_zero_displacement_needs_no_slack(self):
        self.assertAlmostEqual(
            hx.required_service_loop_length(0.0, 0.0, 0.0), 0.0, places=12
        )

    def test_slack_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            hx.required_service_loop_length(0.002, 0.004, 0.001, 0.9)

    def test_negative_thermal_displacement_raises(self):
        with self.assertRaises(ValueError):
            hx.required_service_loop_length(-0.001, 0.004, 0.001)

    def test_negative_mechanism_stroke_raises(self):
        with self.assertRaises(ValueError):
            hx.required_service_loop_length(0.002, -0.004, 0.001)


class InterfaceCrossingFindingsTest(unittest.TestCase):
    def test_clean_crossing_has_no_findings(self):
        self.assertEqual(hx.interface_crossing_findings(_clean_crossing()), [])

    def test_slack_exactly_at_the_requirement_passes(self):
        crossing = _clean_crossing()
        crossing["installed_slack_m"] = hx.required_service_loop_length(
            crossing["thermal_displacement_m"],
            crossing["mechanism_stroke_m"],
            crossing["assembly_tolerance_m"],
        )
        self.assertEqual(hx.interface_crossing_findings(crossing), [])

    def test_short_slack_is_flagged(self):
        crossing = _clean_crossing()
        crossing["installed_slack_m"] = 0.001
        findings = hx.interface_crossing_findings(crossing)
        self.assertTrue(any("slack" in f for f in findings))

    def test_unanchored_side_is_flagged(self):
        crossing = _clean_crossing()
        crossing["supported_both_sides"] = False
        findings = hx.interface_crossing_findings(crossing)
        self.assertTrue(any("both sides" in f for f in findings))

    def test_load_path_attachment_is_flagged(self):
        crossing = _clean_crossing()
        crossing["attachment_kind"] = "harness_bridging_moving_joint_without_slack"
        findings = hx.interface_crossing_findings(crossing)
        self.assertTrue(any("load path" in f for f in findings))

    def test_unrecognized_attachment_kind_raises(self):
        crossing = _clean_crossing()
        crossing["attachment_kind"] = "hope"
        with self.assertRaises(ValueError):
            hx.interface_crossing_findings(crossing)

    def test_missing_crossing_key_raises(self):
        crossing = _clean_crossing()
        del crossing["installed_slack_m"]
        with self.assertRaises(ValueError):
            hx.interface_crossing_findings(crossing)


class ConnectorTerminationTest(unittest.TestCase):
    def test_reaction_force_is_mass_times_acceleration(self):
        self.assertAlmostEqual(
            hx.connector_reaction_force(0.05, 20.0),
            0.05 * 20.0 * hx.STANDARD_GRAVITY_M_S2,
            places=9,
        )

    def test_zero_unsupported_mass_gives_zero_force(self):
        self.assertAlmostEqual(
            hx.connector_reaction_force(0.0, 20.0), 0.0, places=12
        )

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            hx.connector_reaction_force(-0.1, 20.0)

    def test_clean_termination_has_no_findings(self):
        self.assertEqual(
            hx.connector_termination_findings(_clean_termination()), []
        )

    def test_force_exactly_at_the_allowable_passes(self):
        termination = _clean_termination()
        termination["allowable_connector_load_n"] = hx.connector_reaction_force(
            termination["unsupported_mass_kg"],
            termination["quasi_static_accel_g"],
        )
        self.assertEqual(hx.connector_termination_findings(termination), [])

    def test_overloaded_connector_is_flagged(self):
        termination = _clean_termination()
        termination["allowable_connector_load_n"] = 1.0
        findings = hx.connector_termination_findings(termination)
        self.assertTrue(any("reacts" in f for f in findings))

    def test_distant_first_support_is_flagged(self):
        termination = _clean_termination()
        termination["first_support_distance_m"] = 0.200
        findings = hx.connector_termination_findings(termination)
        self.assertTrue(any("first support" in f for f in findings))

    def test_first_support_exactly_at_the_limit_passes(self):
        termination = _clean_termination()
        termination["first_support_distance_m"] = termination[
            "max_first_support_distance_m"
        ]
        self.assertEqual(hx.connector_termination_findings(termination), [])

    def test_missing_strain_relief_is_flagged(self):
        termination = _clean_termination()
        termination["strain_relief_present"] = False
        findings = hx.connector_termination_findings(termination)
        self.assertTrue(any("strain relief" in f for f in findings))

    def test_missing_termination_key_raises(self):
        termination = _clean_termination()
        del termination["strain_relief_present"]
        with self.assertRaises(ValueError):
            hx.connector_termination_findings(termination)

    def test_non_positive_allowable_load_raises(self):
        termination = _clean_termination()
        termination["allowable_connector_load_n"] = 0.0
        with self.assertRaises(ValueError):
            hx.connector_termination_findings(termination)


class AggregateReviewTest(unittest.TestCase):
    def _clean_harness(self):
        return {
            "harness_id": "HRN-A",
            "attachments": [
                {
                    "attachment_id": "CL-01",
                    "attachment_kind": "p_clamp_on_structure_standoff",
                },
                {"attachment_id": "CL-02", "attachment_kind": "cable_tray_tie"},
            ],
            "spans": [_clean_span()],
            "crossings": [_clean_crossing()],
            "terminations": [_clean_termination()],
        }

    def test_clean_harness_is_compliant(self):
        review = hx.aggregate_harness_load_exclusion_review(self._clean_harness())
        self.assertTrue(review["compliant"])
        self.assertEqual(review["harness_id"], "HRN-A")

    def test_empty_harness_is_compliant(self):
        review = hx.aggregate_harness_load_exclusion_review({"harness_id": "HRN-B"})
        self.assertTrue(review["compliant"])
        self.assertEqual(review["span_findings"], [])

    def test_load_path_attachment_breaks_compliance(self):
        harness = self._clean_harness()
        harness["attachments"][1]["attachment_kind"] = (
            "harness_tensioned_between_hardpoints"
        )
        review = hx.aggregate_harness_load_exclusion_review(harness)
        self.assertFalse(review["compliant"])
        self.assertEqual(len(review["attachment_findings"]), 1)

    def test_span_failure_breaks_compliance(self):
        harness = self._clean_harness()
        harness["spans"][0]["allowable_tension_n"] = 0.5
        review = hx.aggregate_harness_load_exclusion_review(harness)
        self.assertFalse(review["compliant"])
        self.assertTrue(review["span_findings"])

    def test_crossing_failure_breaks_compliance(self):
        harness = self._clean_harness()
        harness["crossings"][0]["supported_both_sides"] = False
        review = hx.aggregate_harness_load_exclusion_review(harness)
        self.assertFalse(review["compliant"])
        self.assertTrue(review["crossing_findings"])

    def test_termination_failure_breaks_compliance(self):
        harness = self._clean_harness()
        harness["terminations"][0]["strain_relief_present"] = False
        review = hx.aggregate_harness_load_exclusion_review(harness)
        self.assertFalse(review["compliant"])
        self.assertTrue(review["termination_findings"])

    def test_missing_harness_id_raises(self):
        with self.assertRaises(ValueError):
            hx.aggregate_harness_load_exclusion_review({"spans": []})

    def test_missing_attachment_key_raises(self):
        harness = self._clean_harness()
        del harness["attachments"][0]["attachment_kind"]
        with self.assertRaises(ValueError):
            hx.aggregate_harness_load_exclusion_review(harness)


if __name__ == "__main__":
    unittest.main()
