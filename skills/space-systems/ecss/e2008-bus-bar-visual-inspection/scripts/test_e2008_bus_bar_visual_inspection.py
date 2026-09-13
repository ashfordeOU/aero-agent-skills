#!/usr/bin/env python3
"""Contract test for the bus bar visual inspection (offline)."""

import copy
import unittest

from e2008_bus_bar_visual_inspection_logic import (
    ACCEPT,
    BUS_BAR_DEFECT_KINDS,
    BUS_BAR_ZONES,
    DEFAULT_BUS_BAR_CRITERIA,
    NOT_TOLERATED_KINDS,
    REJECT,
    REWORK,
    assess_bus_bar_defect,
    clear_opening_fraction,
    group_defects_by_kind,
    inspect_bus_bar,
    is_bridged,
    residual_conductor_gap_mm,
    validate_bus_bar_criteria,
    zone_severity_factor,
)

SPLASH = {
    "id": "BB-1",
    "kind": "solder-splash",
    "zone": "conductor-run",
    "area_mm2": 0.3,
}

CLEAN_BAR = {
    "bus_bar_id": "SA-BUSBAR-01",
    "defects": [],
}


def _defect(**overrides):
    item = copy.deepcopy(SPLASH)
    item.update(overrides)
    return item


def _bridge(**overrides):
    item = {
        "id": "BB-BR",
        "kind": "solder-bridging",
        "zone": "termination-pad",
        "designed_gap_mm": 1.0,
        "solder_spread_mm": 0.2,
    }
    item.update(overrides)
    return item


def _opening(**overrides):
    item = {
        "id": "BB-OP",
        "kind": "blocked-opening",
        "zone": "opening-margin",
        "nominal_opening_area_mm2": 100.0,
        "obstructed_area_mm2": 1.0,
    }
    item.update(overrides)
    return item


def _bar(defects, **overrides):
    bar = copy.deepcopy(CLEAN_BAR)
    bar["defects"] = defects
    bar.update(overrides)
    return bar


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_bus_bar_criteria(DEFAULT_BUS_BAR_CRITERIA),
            DEFAULT_BUS_BAR_CRITERIA,
        )

    def test_criteria_cover_every_zone(self):
        for zone in BUS_BAR_ZONES:
            self.assertIn(zone, DEFAULT_BUS_BAR_CRITERIA["zone_severity_factor"])

    def test_not_tolerated_kinds_are_real_kinds(self):
        for kind in NOT_TOLERATED_KINDS:
            self.assertIn(kind, BUS_BAR_DEFECT_KINDS)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_bar_criteria("default")

    def test_criteria_missing_a_graded_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_BUS_BAR_CRITERIA)
        del broken["accept_area_mm2"]["solder-void"]
        with self.assertRaises(ValueError):
            validate_bus_bar_criteria(broken)

    def test_rework_area_below_accept_area_rejected(self):
        broken = copy.deepcopy(DEFAULT_BUS_BAR_CRITERIA)
        broken["rework_area_mm2"]["solder-splash"] = 0.1
        with self.assertRaises(ValueError):
            validate_bus_bar_criteria(broken)

    def test_zero_isolation_gap_rejected(self):
        broken = copy.deepcopy(DEFAULT_BUS_BAR_CRITERIA)
        broken["min_isolation_gap_mm"] = 0.0
        with self.assertRaises(ValueError):
            validate_bus_bar_criteria(broken)

    def test_clear_opening_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_BUS_BAR_CRITERIA)
        broken["accept_clear_opening_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_bus_bar_criteria(broken)

    def test_rework_clear_fraction_above_accept_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_BUS_BAR_CRITERIA)
        broken["rework_clear_opening_fraction"] = 0.99
        with self.assertRaises(ValueError):
            validate_bus_bar_criteria(broken)

    def test_termination_pad_is_stricter_than_the_conductor_run(self):
        self.assertLess(
            zone_severity_factor("termination-pad"),
            zone_severity_factor("conductor-run"),
        )

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_severity_factor("somewhere-on-the-bar")


class GapTests(unittest.TestCase):
    def test_residual_gap_is_the_design_gap_less_the_spread(self):
        self.assertAlmostEqual(
            residual_conductor_gap_mm(1.0, 0.25), 0.75, places=9
        )

    def test_solder_touching_across_the_gap_counts_as_bridged(self):
        self.assertTrue(is_bridged(1.0, 1.0))

    def test_spread_short_of_the_gap_is_not_bridged(self):
        self.assertFalse(is_bridged(1.0, 0.2))

    def test_zero_design_gap_rejected(self):
        with self.assertRaises(ValueError):
            residual_conductor_gap_mm(0.0, 0.1)

    def test_negative_spread_rejected(self):
        with self.assertRaises(ValueError):
            residual_conductor_gap_mm(1.0, -0.1)


class OpeningTests(unittest.TestCase):
    def test_clear_fraction_is_the_unobstructed_share(self):
        self.assertAlmostEqual(clear_opening_fraction(100.0, 20.0), 0.80, places=9)

    def test_untouched_opening_is_fully_clear(self):
        self.assertAlmostEqual(clear_opening_fraction(100.0, 0.0), 1.0, places=9)

    def test_obstruction_larger_than_the_opening_rejected(self):
        with self.assertRaises(ValueError):
            clear_opening_fraction(100.0, 140.0)

    def test_zero_opening_area_rejected(self):
        with self.assertRaises(ValueError):
            clear_opening_fraction(0.0, 1.0)


class BridgingTests(unittest.TestCase):
    def test_a_bridge_rejects_whatever_its_size(self):
        result = assess_bus_bar_defect(_bridge(solder_spread_mm=1.4))
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])
        self.assertTrue(any("bridge" in reason for reason in result["reasons"]))

    def test_encroaching_solder_reworks_rather_than_rejects(self):
        result = assess_bus_bar_defect(_bridge(solder_spread_mm=0.7))
        self.assertEqual(result["disposition"], REWORK)
        self.assertTrue(result["tolerated"])
        self.assertAlmostEqual(
            result["measurements"]["residual_gap_mm"], 0.30, places=9
        )

    def test_gap_exactly_on_the_isolation_minimum_is_accepted(self):
        result = assess_bus_bar_defect(_bridge(solder_spread_mm=0.6))
        self.assertAlmostEqual(
            result["measurements"]["residual_gap_mm"], 0.40, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_bridging_indication_without_a_gap_measurement_rejected(self):
        broken = _bridge()
        del broken["designed_gap_mm"]
        with self.assertRaises(ValueError):
            assess_bus_bar_defect(broken)


class BlockedOpeningTests(unittest.TestCase):
    def test_an_almost_clear_opening_is_accepted(self):
        result = assess_bus_bar_defect(_opening(obstructed_area_mm2=1.0))
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(
            result["measurements"]["clear_opening_fraction"], 0.99, places=9
        )

    def test_clear_fraction_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_bus_bar_defect(_opening(obstructed_area_mm2=2.0))
        self.assertAlmostEqual(
            result["measurements"]["clear_opening_fraction"], 0.98, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_partly_filled_opening_is_reworkable(self):
        result = assess_bus_bar_defect(_opening(obstructed_area_mm2=30.0))
        self.assertEqual(result["disposition"], REWORK)

    def test_clear_fraction_exactly_on_the_rework_limit_stays_reworkable(self):
        result = assess_bus_bar_defect(_opening(obstructed_area_mm2=60.0))
        self.assertAlmostEqual(
            result["measurements"]["clear_opening_fraction"], 0.40, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_an_opening_filled_solid_rejects(self):
        result = assess_bus_bar_defect(_opening(obstructed_area_mm2=95.0))
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])

    def test_blocked_opening_without_an_area_measurement_rejected(self):
        broken = _opening()
        del broken["obstructed_area_mm2"]
        with self.assertRaises(ValueError):
            assess_bus_bar_defect(broken)


class GradedDefectTests(unittest.TestCase):
    def test_a_small_splash_is_accepted(self):
        result = assess_bus_bar_defect(SPLASH)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_area_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_bus_bar_defect(_defect(area_mm2=0.5))
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 0.5, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_splash_on_a_termination_pad_loses_its_margin(self):
        result = assess_bus_bar_defect(
            _defect(area_mm2=0.5, zone="termination-pad")
        )
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 0.25, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_area_beyond_the_rework_limit_rejects(self):
        result = assess_bus_bar_defect(_defect(area_mm2=9.0))
        self.assertEqual(result["disposition"], REJECT)

    def test_a_thin_fillet_is_never_accepted_as_found(self):
        result = assess_bus_bar_defect(
            _defect(kind="insufficient-solder-fillet", area_mm2=0.2)
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_bus_bar_defect(_defect(area_mm2=-1.0))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_bus_bar_defect(_defect(kind="smudge"))

    def test_non_mapping_defect_rejected(self):
        with self.assertRaises(ValueError):
            assess_bus_bar_defect("solder-splash")


class NotToleratedTests(unittest.TestCase):
    def test_a_crack_rejects_on_presence(self):
        result = assess_bus_bar_defect(
            _defect(kind="bus-bar-crack", area_mm2=0.01)
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])

    def test_a_lifted_segment_rejects_on_presence(self):
        result = assess_bus_bar_defect(
            _defect(kind="lifted-bus-bar-segment", area_mm2=0.01)
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("not-tolerated" in reason for reason in result["reasons"])
        )

    def test_a_not_tolerated_kind_ignores_the_zone_factor(self):
        strict = assess_bus_bar_defect(
            _defect(kind="bus-bar-crack", zone="termination-pad")
        )
        loose = assess_bus_bar_defect(
            _defect(kind="bus-bar-crack", zone="conductor-run")
        )
        self.assertEqual(strict["disposition"], loose["disposition"])


class GroupingTests(unittest.TestCase):
    def test_defects_group_by_kind(self):
        result = group_defects_by_kind(
            [_defect(), _defect(), _defect(kind="solder-void", area_mm2=0.1)]
        )
        self.assertEqual(result["counts"]["solder-splash"], 2)
        self.assertEqual(result["counts"]["solder-void"], 1)
        self.assertEqual(result["not_tolerated_count"], 0)

    def test_not_tolerated_defects_are_counted_apart(self):
        result = group_defects_by_kind(
            [_defect(), _defect(kind="bus-bar-crack", area_mm2=0.1)]
        )
        self.assertEqual(result["not_tolerated_count"], 1)

    def test_grouping_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            group_defects_by_kind([_defect(kind="smudge")])

    def test_grouping_a_non_list_rejected(self):
        with self.assertRaises(ValueError):
            group_defects_by_kind("none")


class BusBarInspectionTests(unittest.TestCase):
    def test_clean_bar_is_accepted_with_a_record(self):
        result = inspect_bus_bar(CLEAN_BAR)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["reject_count"], 0)
        self.assertTrue(any("clean" in finding for finding in result["findings"]))

    def test_bar_verdict_takes_the_worst_indication(self):
        result = inspect_bus_bar(
            _bar([_defect(id="A"), _defect(id="B", area_mm2=9.0)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_one_bridge_condemns_an_otherwise_clean_bar(self):
        result = inspect_bus_bar(
            _bar([_defect(id="A"), _bridge(id="B", solder_spread_mm=1.5)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_tolerated_ids"], ["B"])
        self.assertTrue(
            any("not-tolerated" in finding for finding in result["findings"])
        )

    def test_a_rework_verdict_demands_reinspection(self):
        result = inspect_bus_bar(_bar([_defect(id="A", area_mm2=3.0)]))
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["reinspection_required"])

    def test_accepted_bar_needs_no_reinspection(self):
        self.assertFalse(inspect_bus_bar(CLEAN_BAR)["reinspection_required"])

    def test_duplicate_defect_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bus_bar(_bar([_defect(id="A"), _defect(id="A")]))

    def test_bar_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bus_bar(_bar([], bus_bar_id="  "))

    def test_bar_with_a_non_list_survey_rejected(self):
        bar = copy.deepcopy(CLEAN_BAR)
        bar["defects"] = "none"
        with self.assertRaises(ValueError):
            inspect_bus_bar(bar)

    def test_non_mapping_bar_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bus_bar("SA-BUSBAR-01")


if __name__ == "__main__":
    unittest.main()
