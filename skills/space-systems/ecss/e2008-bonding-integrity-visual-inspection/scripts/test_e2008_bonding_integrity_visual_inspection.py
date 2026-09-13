#!/usr/bin/env python3
"""Contract test for the coupon bond integrity inspection (offline)."""

import copy
import unittest

from e2008_bonding_integrity_visual_inspection_logic import (
    ACCEPT,
    BOND_ANOMALY_KINDS,
    DEFAULT_BOND_CRITERIA,
    POPULATION_INCOMPLETE,
    REFER,
    REJECT,
    REWORK,
    assess_bond_anomaly,
    bond_footprint,
    inspect_bond_population,
    inspect_cell_bond,
    validate_bond_criteria,
)

BARE_CELL = {
    "cell_id": "SC-001",
    "cell_length_mm": 40.0,
    "cell_width_mm": 40.0,
    "anomalies": [],
}


def _cell(anomalies=None, **overrides):
    record = copy.deepcopy(BARE_CELL)
    record["anomalies"] = copy.deepcopy(anomalies) if anomalies else []
    record.update(overrides)
    return record


def _footprint(length=40.0, width=40.0):
    return bond_footprint(length, width)


def _void(**overrides):
    anomaly = {
        "id": "A1",
        "kind": "adhesive-void",
        "area_mm2": 8.0,
        "distance_from_corner_mm": 15.0,
    }
    anomaly.update(overrides)
    return anomaly


def _coupon(records, declared=None, **overrides):
    coupon = {
        "coupon_id": "CPN-01",
        "declared_cell_count": declared if declared is not None else len(records),
        "cells": records,
    }
    coupon.update(overrides)
    return coupon


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_bond_criteria(DEFAULT_BOND_CRITERIA), DEFAULT_BOND_CRITERIA
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_bond_criteria("default")

    def test_missing_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_BOND_CRITERIA)
        del broken["min_bonded_area_fraction"]
        with self.assertRaises(ValueError):
            validate_bond_criteria(broken)

    def test_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_BOND_CRITERIA)
        broken["max_edge_disbond_fraction_of_span"] = 1.4
        with self.assertRaises(ValueError):
            validate_bond_criteria(broken)

    def test_corner_peel_weight_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_BOND_CRITERIA)
        broken["corner_peel_weight"] = 0.5
        with self.assertRaises(ValueError):
            validate_bond_criteria(broken)

    def test_non_integer_anomaly_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_BOND_CRITERIA)
        broken["max_accepted_anomalies_per_cell"] = 2.5
        with self.assertRaises(ValueError):
            validate_bond_criteria(broken)


class FootprintTests(unittest.TestCase):
    def test_square_cell_footprint(self):
        footprint = _footprint()
        self.assertAlmostEqual(footprint["bond_area_mm2"], 1600.0, places=9)
        self.assertAlmostEqual(footprint["perimeter_mm"], 160.0, places=9)
        self.assertAlmostEqual(footprint["min_span_mm"], 40.0, places=9)
        self.assertAlmostEqual(footprint["corner_zone_mm"], 4.0, places=9)

    def test_span_follows_the_shortest_side(self):
        footprint = _footprint(60.0, 20.0)
        self.assertAlmostEqual(footprint["min_span_mm"], 20.0, places=9)
        self.assertAlmostEqual(footprint["bond_area_mm2"], 1200.0, places=9)

    def test_zero_dimension_rejected(self):
        with self.assertRaises(ValueError):
            bond_footprint(0.0, 40.0)

    def test_non_numeric_dimension_rejected(self):
        with self.assertRaises(ValueError):
            bond_footprint("40", 40.0)


class VoidTests(unittest.TestCase):
    def test_small_mid_footprint_void_accepts(self):
        result = assess_bond_anomaly(_void(), _footprint())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["peel_weight"], 1.0, places=9)

    def test_same_void_at_a_corner_is_weighted_up(self):
        middle = assess_bond_anomaly(
            _void(area_mm2=16.0, distance_from_corner_mm=15.0), _footprint()
        )
        corner = assess_bond_anomaly(
            _void(area_mm2=16.0, distance_from_corner_mm=1.0), _footprint()
        )
        self.assertEqual(middle["disposition"], ACCEPT)
        self.assertEqual(corner["disposition"], REFER)
        self.assertAlmostEqual(
            corner["disbonded_area_mm2"], middle["disbonded_area_mm2"], places=9
        )

    def test_void_exactly_on_the_allowance_accepts(self):
        footprint = _footprint()
        area = footprint["bond_area_mm2"] * DEFAULT_BOND_CRITERIA[
            "max_single_void_area_fraction"
        ]
        result = assess_bond_anomaly(
            _void(area_mm2=area, distance_from_corner_mm=20.0), footprint
        )
        self.assertAlmostEqual(area / footprint["bond_area_mm2"], 0.02, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_large_void_rejects(self):
        result = assess_bond_anomaly(
            _void(area_mm2=120.0, distance_from_corner_mm=20.0), _footprint()
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_void_needs_a_corner_distance(self):
        anomaly = _void()
        del anomaly["distance_from_corner_mm"]
        with self.assertRaises(ValueError):
            assess_bond_anomaly(anomaly, _footprint())

    def test_void_larger_than_the_footprint_rejected(self):
        with self.assertRaises(ValueError):
            assess_bond_anomaly(_void(area_mm2=5000.0), _footprint())


class EdgeAndCornerTests(unittest.TestCase):
    def test_shallow_edge_disbond_accepts(self):
        anomaly = {
            "id": "A2",
            "kind": "edge-disbond",
            "inward_extent_mm": 2.0,
            "along_edge_length_mm": 6.0,
        }
        result = assess_bond_anomaly(anomaly, _footprint())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["disbonded_area_mm2"], 12.0, places=9)

    def test_edge_disbond_exactly_on_the_allowance_accepts(self):
        footprint = _footprint()
        allowed = footprint["min_span_mm"] * DEFAULT_BOND_CRITERIA[
            "max_edge_disbond_fraction_of_span"
        ]
        anomaly = {
            "id": "A2",
            "kind": "edge-disbond",
            "inward_extent_mm": allowed,
            "along_edge_length_mm": 2.0,
        }
        self.assertAlmostEqual(allowed, 4.0, places=9)
        self.assertEqual(assess_bond_anomaly(anomaly, footprint)["disposition"], ACCEPT)

    def test_deep_edge_disbond_refers_then_rejects(self):
        base = {"id": "A2", "kind": "edge-disbond", "along_edge_length_mm": 2.0}
        refer = dict(base, inward_extent_mm=6.0)
        reject = dict(base, inward_extent_mm=12.0)
        self.assertEqual(assess_bond_anomaly(refer, _footprint())["disposition"], REFER)
        self.assertEqual(
            assess_bond_anomaly(reject, _footprint())["disposition"], REJECT
        )

    def test_corner_allowance_is_tighter_than_the_edge_allowance(self):
        anomaly = {"id": "A3", "kind": "corner-disbond", "inward_extent_mm": 2.0}
        edge = {
            "id": "A4",
            "kind": "edge-disbond",
            "inward_extent_mm": 2.0,
            "along_edge_length_mm": 2.0,
        }
        self.assertEqual(assess_bond_anomaly(anomaly, _footprint())["disposition"], REFER)
        self.assertEqual(assess_bond_anomaly(edge, _footprint())["disposition"], ACCEPT)

    def test_corner_disbond_carries_the_peel_weight(self):
        anomaly = {"id": "A3", "kind": "corner-disbond", "inward_extent_mm": 1.0}
        result = assess_bond_anomaly(anomaly, _footprint())
        self.assertAlmostEqual(
            result["peel_weight"], DEFAULT_BOND_CRITERIA["corner_peel_weight"], places=9
        )
        self.assertAlmostEqual(result["disbonded_area_mm2"], 0.5, places=9)

    def test_deep_corner_disbond_rejects(self):
        anomaly = {"id": "A3", "kind": "corner-disbond", "inward_extent_mm": 9.0}
        self.assertEqual(assess_bond_anomaly(anomaly, _footprint())["disposition"], REJECT)


class OtherAnomalyTests(unittest.TestCase):
    def test_short_missing_fillet_accepts(self):
        anomaly = {"id": "A5", "kind": "missing-fillet", "along_edge_length_mm": 4.0}
        self.assertEqual(assess_bond_anomaly(anomaly, _footprint())["disposition"], ACCEPT)

    def test_long_missing_fillet_goes_to_rework(self):
        anomaly = {"id": "A5", "kind": "missing-fillet", "along_edge_length_mm": 30.0}
        result = assess_bond_anomaly(anomaly, _footprint())
        self.assertEqual(result["disposition"], REWORK)
        self.assertAlmostEqual(result["disbonded_area_mm2"], 0.0, places=9)

    def test_removable_bridge_goes_to_rework(self):
        anomaly = {"id": "A6", "kind": "adhesive-bridge", "removable": True}
        self.assertEqual(assess_bond_anomaly(anomaly, _footprint())["disposition"], REWORK)

    def test_fixed_bridge_goes_to_review(self):
        anomaly = {"id": "A6", "kind": "adhesive-bridge", "removable": False}
        self.assertEqual(assess_bond_anomaly(anomaly, _footprint())["disposition"], REFER)

    def test_bridge_needs_a_boolean_removable(self):
        anomaly = {"id": "A6", "kind": "adhesive-bridge", "removable": "yes"}
        with self.assertRaises(ValueError):
            assess_bond_anomaly(anomaly, _footprint())

    def test_lifted_cell_rejects_and_takes_the_whole_footprint(self):
        anomaly = {"id": "A7", "kind": "cell-lift"}
        result = assess_bond_anomaly(anomaly, _footprint())
        self.assertEqual(result["disposition"], REJECT)
        self.assertAlmostEqual(result["disbonded_area_mm2"], 1600.0, places=9)

    def test_unknown_anomaly_kind_rejected(self):
        anomaly = {"id": "A8", "kind": "scorch-mark"}
        with self.assertRaises(ValueError):
            assess_bond_anomaly(anomaly, _footprint())

    def test_every_declared_kind_is_dispositioned(self):
        self.assertEqual(len(BOND_ANOMALY_KINDS), 6)


class CellRollupTests(unittest.TestCase):
    def test_clean_cell_accepts_with_a_full_bond(self):
        result = inspect_cell_bond(_cell())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["bonded_area_fraction"], 1.0, places=9)

    def test_many_small_voids_drop_the_bonded_fraction(self):
        voids = [
            _void(id="A%d" % n, area_mm2=30.0, distance_from_corner_mm=18.0)
            for n in range(6)
        ]
        result = inspect_cell_bond(_cell(voids))
        self.assertAlmostEqual(result["bonded_area_fraction"], 0.8875, places=9)
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("still bonded" in finding for finding in result["findings"])
        )

    def test_bonded_fraction_exactly_on_the_minimum_is_not_rejected_for_area(self):
        area = 1600.0 * (1.0 - DEFAULT_BOND_CRITERIA["min_bonded_area_fraction"])
        voids = [
            _void(id="A%d" % n, area_mm2=area / 8.0, distance_from_corner_mm=18.0)
            for n in range(8)
        ]
        result = inspect_cell_bond(_cell(voids))
        self.assertAlmostEqual(
            result["bonded_area_fraction"],
            DEFAULT_BOND_CRITERIA["min_bonded_area_fraction"],
            places=9,
        )
        self.assertFalse(
            any("still bonded" in finding for finding in result["findings"])
        )

    def test_too_many_accepted_anomalies_go_to_review(self):
        voids = [
            _void(id="A%d" % n, area_mm2=4.0, distance_from_corner_mm=18.0)
            for n in range(5)
        ]
        result = inspect_cell_bond(_cell(voids))
        self.assertEqual(result["accepted_anomaly_count"], 5)
        self.assertEqual(result["verdict"], REFER)

    def test_worst_anomaly_sets_the_cell_verdict(self):
        anomalies = [_void(), {"id": "A9", "kind": "cell-lift"}]
        self.assertEqual(inspect_cell_bond(_cell(anomalies))["verdict"], REJECT)

    def test_a_lifted_cell_has_no_bond_left_to_add_voids_to(self):
        anomalies = [_void(area_mm2=40.0), {"id": "A9", "kind": "cell-lift"}]
        result = inspect_cell_bond(_cell(anomalies))
        self.assertAlmostEqual(result["bonded_area_fraction"], 0.0, places=9)
        self.assertAlmostEqual(result["disbonded_area_mm2"], 1600.0, places=9)

    def test_duplicate_anomaly_ids_rejected(self):
        anomalies = [_void(id="A1"), _void(id="A1")]
        with self.assertRaises(ValueError):
            inspect_cell_bond(_cell(anomalies))

    def test_missing_cell_id_rejected(self):
        record = _cell()
        record["cell_id"] = "   "
        with self.assertRaises(ValueError):
            inspect_cell_bond(record)

    def test_non_list_anomalies_rejected(self):
        record = _cell()
        record["anomalies"] = "none"
        with self.assertRaises(ValueError):
            inspect_cell_bond(record)


class PopulationTests(unittest.TestCase):
    def test_full_population_of_clean_cells_accepts(self):
        records = [_cell(cell_id="SC-%d" % n) for n in range(4)]
        result = inspect_bond_population(_coupon(records))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["population_complete"])
        self.assertEqual(result["disposition_counts"][ACCEPT], 4)

    def test_a_short_record_set_leaves_the_coupon_open(self):
        records = [_cell(cell_id="SC-%d" % n) for n in range(3)]
        result = inspect_bond_population(_coupon(records, declared=5))
        self.assertEqual(result["verdict"], POPULATION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertFalse(result["population_complete"])

    def test_worst_cell_drives_the_coupon_verdict(self):
        bad = _cell([{"id": "A9", "kind": "cell-lift"}], cell_id="SC-9")
        records = [_cell(cell_id="SC-0"), bad]
        result = inspect_bond_population(_coupon(records))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["SC-9"])

    def test_worst_bonded_fraction_is_reported(self):
        voids = [_void(id="A1", area_mm2=32.0, distance_from_corner_mm=18.0)]
        records = [_cell(cell_id="SC-0"), _cell(voids, cell_id="SC-1")]
        result = inspect_bond_population(_coupon(records))
        self.assertAlmostEqual(result["worst_bonded_area_fraction"], 0.98, places=9)

    def test_more_records_than_declared_rejected(self):
        records = [_cell(cell_id="SC-%d" % n) for n in range(3)]
        with self.assertRaises(ValueError):
            inspect_bond_population(_coupon(records, declared=2))

    def test_duplicate_cell_ids_rejected(self):
        records = [_cell(cell_id="SC-0") for _ in range(2)]
        with self.assertRaises(ValueError):
            inspect_bond_population(_coupon(records))

    def test_non_integer_declared_count_rejected(self):
        records = [_cell(cell_id="SC-0")]
        with self.assertRaises(ValueError):
            inspect_bond_population(_coupon(records, declared="four"))

    def test_non_mapping_coupon_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bond_population("CPN-01")


if __name__ == "__main__":
    unittest.main()
