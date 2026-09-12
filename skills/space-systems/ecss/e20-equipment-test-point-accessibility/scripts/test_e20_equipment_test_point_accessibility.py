#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.2.4 test stimulus point
accessibility.

Exercises the sibling logic module (stdlib unittest, offline).
Contract: an access provision is categorized as exactly non-intrusive
or intrusive and an unrecognized provision raises; instrument loading
error is 100 * Zs / (Zs + Zin) with a negative source impedance or a
non-positive input impedance raising; the minimum input impedance
that meets an allowable inverts that expression exactly and an
allowable outside (0, 100) raises; an intrusive provision and a
provision needing a flight connector demated are both reported;
series isolation is graded against the node criticality and an
unrecognized criticality or negative isolation raises; a required
stimulus signal reachable only through an intrusive or demate-gated
point counts as uncovered; and the aggregated point and equipment
reviews are compliant only when every finding list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_equipment_test_point_accessibility_logic as tp  # noqa: E402


def make_point(**overrides):
    """A compliant baseline point record; overrides replace fields."""
    point = {
        "point_id": "TP-01",
        "access_method": "dedicated_test_connector",
        "node_criticality": "mission_critical",
        "source_impedance_ohm": 50.0,
        "instrument_input_impedance_ohm": 1.0e6,
        "allowable_loading_error_percent": 1.0,
        "series_isolation_ohm": 4700.0,
        "requires_flight_connector_demate": False,
        "signals": ["bus_voltage_monitor"],
    }
    point.update(overrides)
    return point


class CategorizeAccessMethodTest(unittest.TestCase):
    def test_dedicated_test_connector_is_non_intrusive(self):
        self.assertEqual(
            tp.categorize_access_method("dedicated_test_connector"), "non_intrusive"
        )

    def test_buffered_monitor_pin_is_non_intrusive(self):
        self.assertEqual(
            tp.categorize_access_method("buffered_monitor_pin"), "non_intrusive"
        )

    def test_harness_breakout_box_is_non_intrusive(self):
        self.assertEqual(
            tp.categorize_access_method("harness_breakout_box"), "non_intrusive"
        )

    def test_connector_demate_is_intrusive(self):
        self.assertEqual(
            tp.categorize_access_method("connector_demate"), "intrusive"
        )

    def test_wire_cut_splice_is_intrusive(self):
        self.assertEqual(
            tp.categorize_access_method("wire_cut_splice"), "intrusive"
        )

    def test_solder_lug_tap_is_intrusive(self):
        self.assertEqual(tp.categorize_access_method("solder_lug_tap"), "intrusive")

    def test_unknown_access_method_raises(self):
        with self.assertRaises(ValueError):
            tp.categorize_access_method("hold_a_probe_near_it")


class LoadingErrorTest(unittest.TestCase):
    def test_high_impedance_instrument_has_small_error(self):
        self.assertAlmostEqual(
            tp.loading_error_percent(50.0, 1.0e6), 0.00499975, places=6
        )

    def test_equal_impedances_halve_the_signal(self):
        self.assertAlmostEqual(tp.loading_error_percent(1000.0, 1000.0), 50.0)

    def test_ideal_source_is_not_loaded(self):
        self.assertAlmostEqual(tp.loading_error_percent(0.0, 1000.0), 0.0)

    def test_negative_source_impedance_raises(self):
        with self.assertRaises(ValueError):
            tp.loading_error_percent(-1.0, 1000.0)

    def test_zero_input_impedance_raises(self):
        with self.assertRaises(ValueError):
            tp.loading_error_percent(50.0, 0.0)

    def test_negative_input_impedance_raises(self):
        with self.assertRaises(ValueError):
            tp.loading_error_percent(50.0, -1000.0)


class RequiredInputImpedanceTest(unittest.TestCase):
    def test_one_percent_allowable_needs_ninety_nine_times_source(self):
        self.assertAlmostEqual(tp.required_input_impedance_ohm(100.0, 1.0), 9900.0)

    def test_result_round_trips_to_the_allowable(self):
        required = tp.required_input_impedance_ohm(220.0, 2.5)
        self.assertAlmostEqual(tp.loading_error_percent(220.0, required), 2.5)

    def test_ideal_source_needs_no_input_impedance(self):
        self.assertAlmostEqual(tp.required_input_impedance_ohm(0.0, 5.0), 0.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            tp.required_input_impedance_ohm(100.0, 0.0)

    def test_allowable_of_one_hundred_percent_raises(self):
        with self.assertRaises(ValueError):
            tp.required_input_impedance_ohm(100.0, 100.0)

    def test_negative_source_impedance_raises(self):
        with self.assertRaises(ValueError):
            tp.required_input_impedance_ohm(-5.0, 1.0)


class AccessFindingsTest(unittest.TestCase):
    def test_non_intrusive_point_is_clean(self):
        self.assertEqual(
            tp.access_findings("TP-01", "dedicated_test_connector", False), []
        )

    def test_intrusive_point_is_flagged(self):
        findings = tp.access_findings("TP-02", "wire_cut_splice", False)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "access_alters_electrical_configuration"
        )

    def test_demate_requirement_is_flagged_on_a_non_intrusive_method(self):
        findings = tp.access_findings("TP-03", "harness_breakout_box", True)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "flight_connector_demate_required_for_access"
        )

    def test_intrusive_and_demate_report_both(self):
        findings = tp.access_findings("TP-04", "connector_demate", True)
        self.assertEqual(len(findings), 2)


class LoadingFindingsTest(unittest.TestCase):
    def test_within_allowable_is_clean(self):
        self.assertEqual(tp.loading_findings("TP-01", 50.0, 1.0e6, 1.0), [])

    def test_error_exactly_at_allowable_is_clean(self):
        required = tp.required_input_impedance_ohm(100.0, 2.0)
        self.assertEqual(tp.loading_findings("TP-01", 100.0, required, 2.0), [])

    def test_excessive_loading_reports_required_impedance(self):
        findings = tp.loading_findings("TP-05", 1000.0, 1000.0, 1.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "instrument_loading_error_exceeded")
        self.assertAlmostEqual(findings[0]["loading_error_percent"], 50.0)
        self.assertAlmostEqual(findings[0]["required_input_impedance_ohm"], 99000.0)


class IsolationFindingsTest(unittest.TestCase):
    def test_routine_node_needs_no_isolation(self):
        self.assertEqual(tp.isolation_findings("TP-01", "routine", 0.0), [])

    def test_mission_critical_node_at_the_minimum_is_clean(self):
        self.assertEqual(
            tp.isolation_findings("TP-01", "mission_critical", 1000.0), []
        )

    def test_mission_critical_node_below_the_minimum_is_flagged(self):
        findings = tp.isolation_findings("TP-06", "mission_critical", 100.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "insufficient_test_point_series_isolation"
        )
        self.assertAlmostEqual(findings[0]["required_isolation_ohm"], 1000.0)

    def test_catastrophic_node_demands_more_than_mission_critical(self):
        self.assertEqual(tp.isolation_findings("TP-07", "catastrophic", 4700.0)[0][
            "issue"
        ], "insufficient_test_point_series_isolation")

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            tp.isolation_findings("TP-01", "somewhat_important", 1000.0)

    def test_negative_isolation_raises(self):
        with self.assertRaises(ValueError):
            tp.isolation_findings("TP-01", "routine", -1.0)


class StimulusCoverageTest(unittest.TestCase):
    def test_non_intrusive_point_covers_its_signals(self):
        points = [make_point(signals=["bus_voltage_monitor", "sync_pulse"])]
        self.assertEqual(
            tp.stimulus_coverage_findings(
                ["bus_voltage_monitor", "sync_pulse"], points
            ),
            [],
        )

    def test_signal_only_on_an_intrusive_point_is_uncovered(self):
        points = [make_point(access_method="solder_lug_tap", signals=["sync_pulse"])]
        findings = tp.stimulus_coverage_findings(["sync_pulse"], points)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["signal"], "sync_pulse")

    def test_signal_behind_a_demate_is_uncovered(self):
        points = [make_point(requires_flight_connector_demate=True)]
        findings = tp.stimulus_coverage_findings(["bus_voltage_monitor"], points)
        self.assertEqual(len(findings), 1)

    def test_missing_signals_are_reported_in_sorted_order(self):
        points = [make_point(signals=["bus_voltage_monitor"])]
        findings = tp.stimulus_coverage_findings(
            ["zeta_clock", "alpha_reset", "bus_voltage_monitor"], points
        )
        self.assertEqual(
            [f["signal"] for f in findings], ["alpha_reset", "zeta_clock"]
        )

    def test_point_without_signals_key_raises(self):
        bad = make_point()
        del bad["signals"]
        with self.assertRaises(ValueError):
            tp.stimulus_coverage_findings(["sync_pulse"], [bad])


class ReviewTestPointTest(unittest.TestCase):
    def test_compliant_point_has_no_findings(self):
        review = tp.review_test_point(make_point())
        self.assertTrue(tp.is_test_point_compliant(review))

    def test_intrusive_point_is_not_compliant(self):
        review = tp.review_test_point(make_point(access_method="board_probe_removal"))
        self.assertFalse(tp.is_test_point_compliant(review))
        self.assertEqual(len(review["access"]), 1)

    def test_loading_and_isolation_findings_are_reported_together(self):
        review = tp.review_test_point(
            make_point(
                instrument_input_impedance_ohm=1000.0,
                source_impedance_ohm=1000.0,
                series_isolation_ohm=0.0,
            )
        )
        self.assertEqual(len(review["loading"]), 1)
        self.assertEqual(len(review["isolation"]), 1)
        self.assertFalse(tp.is_test_point_compliant(review))

    def test_missing_required_key_raises(self):
        bad = make_point()
        del bad["series_isolation_ohm"]
        with self.assertRaises(ValueError):
            tp.review_test_point(bad)


class ReviewEquipmentTest(unittest.TestCase):
    def test_compliant_equipment(self):
        equipment = {
            "equipment_id": "PCDU-A",
            "test_points": [make_point()],
            "required_stimuli": ["bus_voltage_monitor"],
        }
        review = tp.review_equipment(equipment)
        self.assertTrue(tp.is_equipment_compliant(review))
        self.assertEqual(review["equipment_id"], "PCDU-A")

    def test_uncovered_stimulus_fails_the_equipment(self):
        equipment = {
            "equipment_id": "PCDU-B",
            "test_points": [make_point()],
            "required_stimuli": ["bus_voltage_monitor", "heater_command_echo"],
        }
        review = tp.review_equipment(equipment)
        self.assertFalse(tp.is_equipment_compliant(review))
        self.assertEqual(len(review["coverage"]), 1)

    def test_duplicate_point_id_raises(self):
        equipment = {
            "equipment_id": "PCDU-C",
            "test_points": [make_point(), make_point()],
            "required_stimuli": [],
        }
        with self.assertRaises(ValueError):
            tp.review_equipment(equipment)

    def test_equipment_without_test_points_key_raises(self):
        with self.assertRaises(ValueError):
            tp.review_equipment({"equipment_id": "PCDU-D"})


if __name__ == "__main__":
    unittest.main()
