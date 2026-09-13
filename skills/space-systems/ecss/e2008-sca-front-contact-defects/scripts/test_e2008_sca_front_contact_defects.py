#!/usr/bin/env python3
"""Contract test for the front contact continuity screen (offline)."""

import copy
import unittest

from e2008_sca_front_contact_defects_logic import (
    ACCEPT,
    CONDUCTOR_ROLES,
    DEFAULT_FRONT_CONTACT_POLICY,
    DETECTION_INSUFFICIENT,
    FRONT_CONTACT_DEFECT_KINDS,
    INSPECTION_INCOMPLETE,
    REJECT,
    assess_conductor,
    assess_front_contact,
    connected_span,
    validate_front_contact_policy,
)

BUSBAR_LENGTH = 40.0
GRIDLINE_LENGTH = 20.0


def _break_at(position, extent=0.1, marker="B1"):
    return {
        "id": marker,
        "kind": "metallisation-interruption",
        "position_mm": position,
        "extent_mm": extent,
    }


def _lift_at(position, extent=0.4, marker="L1"):
    return {
        "id": marker,
        "kind": "metallisation-delamination",
        "position_mm": position,
        "extent_mm": extent,
    }


def _busbar(conductor_id="BB1", defects=None):
    return {
        "conductor_id": conductor_id,
        "role": "front-busbar",
        "length_mm": BUSBAR_LENGTH,
        "feed_position_mm": 0.0,
        "defects": copy.deepcopy(defects) if defects else [],
    }


def _gridline(conductor_id, feeds_at_mm, defects=None, busbar_id="BB1"):
    return {
        "conductor_id": conductor_id,
        "role": "front-gridline",
        "length_mm": GRIDLINE_LENGTH,
        "feed_position_mm": 0.0,
        "feeds_busbar_id": busbar_id,
        "feeds_at_mm": feeds_at_mm,
        "defects": copy.deepcopy(defects) if defects else [],
    }


def _cell(conductors, declared=None, cell_id="SCA-001", resolution=0.02):
    record = {
        "cell_id": cell_id,
        "declared_conductor_count": (
            declared if declared is not None else len(conductors)
        ),
        "conductors": conductors,
    }
    if resolution is not None:
        record["min_detectable_feature_mm"] = resolution
    return record


def _clean_cell(gridline_count=4, declared=None, resolution=0.02):
    conductors = [_busbar()]
    for n in range(gridline_count):
        conductors.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
    return _cell(conductors, declared, resolution=resolution)


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_front_contact_policy(DEFAULT_FRONT_CONTACT_POLICY),
            DEFAULT_FRONT_CONTACT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_front_contact_policy("default")

    def test_zero_required_detection_rejected(self):
        broken = dict(DEFAULT_FRONT_CONTACT_POLICY)
        broken["required_detection_mm"] = 0.0
        with self.assertRaises(ValueError):
            validate_front_contact_policy(broken)

    def test_non_boolean_report_flag_rejected(self):
        broken = dict(DEFAULT_FRONT_CONTACT_POLICY)
        broken["report_collection_loss"] = "yes"
        with self.assertRaises(ValueError):
            validate_front_contact_policy(broken)

    def test_declared_kinds_and_roles_are_the_two_the_clause_names(self):
        self.assertEqual(len(FRONT_CONTACT_DEFECT_KINDS), 2)
        self.assertEqual(len(CONDUCTOR_ROLES), 2)


class ConnectedSpanTests(unittest.TestCase):
    def test_unbroken_conductor_stays_whole(self):
        lower, upper, length = connected_span(20.0, 0.0, [])
        self.assertAlmostEqual(lower, 0.0, places=9)
        self.assertAlmostEqual(upper, 20.0, places=9)
        self.assertAlmostEqual(length, 20.0, places=9)

    def test_break_beyond_the_feed_orphans_the_far_side(self):
        gap = {"start_mm": 12.0, "end_mm": 12.2}
        _, _, length = connected_span(20.0, 0.0, [gap])
        self.assertAlmostEqual(length, 12.0, places=9)

    def test_break_on_the_feed_point_severs_everything(self):
        gap = {"start_mm": 0.0, "end_mm": 0.3}
        _, _, length = connected_span(20.0, 0.1, [gap])
        self.assertAlmostEqual(length, 0.0, places=9)

    def test_feed_between_two_breaks_keeps_only_the_middle(self):
        gaps = [
            {"start_mm": 4.0, "end_mm": 4.2},
            {"start_mm": 16.0, "end_mm": 16.2},
        ]
        lower, upper, length = connected_span(20.0, 10.0, gaps)
        self.assertAlmostEqual(lower, 4.2, places=9)
        self.assertAlmostEqual(upper, 16.0, places=9)
        self.assertAlmostEqual(length, 11.8, places=9)

    def test_feed_past_the_conductor_length_rejected(self):
        with self.assertRaises(ValueError):
            connected_span(20.0, 24.0, [])


class ConductorRecordTests(unittest.TestCase):
    def test_clean_conductor_reports_no_defects(self):
        result = assess_conductor(_busbar())
        self.assertEqual(result["interruption_count"], 0)
        self.assertEqual(result["delamination_count"], 0)
        self.assertAlmostEqual(
            result["connected_length_mm"], BUSBAR_LENGTH, places=9
        )
        self.assertAlmostEqual(result["orphaned_length_mm"], 0.0, places=9)

    def test_delamination_length_is_summed_not_counted(self):
        conductor = _busbar(defects=[_lift_at(10.0, 0.4), _lift_at(20.0, 0.6, "L2")])
        result = assess_conductor(conductor)
        self.assertEqual(result["delamination_count"], 2)
        self.assertAlmostEqual(result["delaminated_length_mm"], 1.0, places=9)

    def test_delamination_over_an_interruption_is_named(self):
        conductor = _busbar(defects=[_break_at(10.0, 0.2), _lift_at(10.05, 0.4)])
        result = assess_conductor(conductor)
        self.assertEqual(result["delamination_over_interruption"], ["L1"])

    def test_unknown_defect_kind_rejected(self):
        conductor = _busbar(defects=[{"kind": "scratch", "position_mm": 1.0}])
        with self.assertRaises(ValueError):
            assess_conductor(conductor)

    def test_unknown_conductor_role_rejected(self):
        conductor = _busbar()
        conductor["role"] = "rear-busbar"
        with self.assertRaises(ValueError):
            assess_conductor(conductor)

    def test_duplicate_defect_id_rejected(self):
        conductor = _busbar(defects=[_break_at(5.0), _break_at(9.0)])
        with self.assertRaises(ValueError):
            assess_conductor(conductor)

    def test_defect_past_the_conductor_end_rejected(self):
        conductor = _busbar(defects=[_break_at(BUSBAR_LENGTH + 1.0)])
        with self.assertRaises(ValueError):
            assess_conductor(conductor)

    def test_missing_conductor_id_rejected(self):
        conductor = _busbar()
        del conductor["conductor_id"]
        with self.assertRaises(ValueError):
            assess_conductor(conductor)

    def test_zero_length_conductor_rejected(self):
        conductor = _busbar()
        conductor["length_mm"] = 0.0
        with self.assertRaises(ValueError):
            assess_conductor(conductor)


class FrontContactVerdictTests(unittest.TestCase):
    def test_continuous_front_contact_accepts(self):
        result = assess_front_contact(_clean_cell())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertTrue(result["detection_adequate"])
        self.assertAlmostEqual(result["collection_loss_fraction"], 0.0, places=9)

    def test_one_gridline_break_rejects_and_is_quantified(self):
        conductors = [_busbar()]
        for n in range(4):
            conductors.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
        conductors[1]["defects"] = [_break_at(10.0, 0.2)]
        result = assess_front_contact(_cell(conductors))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["interruption_count"], 1)
        self.assertAlmostEqual(result["gridline_length_lost_mm"], 10.1, places=9)
        self.assertAlmostEqual(
            result["collection_loss_fraction"], 10.1 / 80.0, places=9
        )

    def test_busbar_break_orphans_every_gridline_beyond_it(self):
        conductors = [_busbar(defects=[_break_at(12.0, 0.2)])]
        for n in range(4):
            conductors.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
        result = assess_front_contact(_cell(conductors))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["orphaned_gridline_ids"], ["G01", "G02", "G03"])
        self.assertAlmostEqual(result["collection_loss_fraction"], 0.75, places=9)

    def test_short_busbar_break_costs_more_than_a_long_gridline_break(self):
        near = [_busbar(defects=[_break_at(2.0, 0.1)])]
        far = [_busbar()]
        for n in range(4):
            near.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
            far.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
        far[1]["defects"] = [_break_at(1.0, 0.1)]
        busbar_case = assess_front_contact(_cell(near))
        gridline_case = assess_front_contact(_cell(far))
        self.assertAlmostEqual(
            busbar_case["collection_loss_fraction"], 1.0, places=9
        )
        self.assertLess(
            gridline_case["collection_loss_fraction"],
            busbar_case["collection_loss_fraction"],
        )

    def test_delamination_alone_rejects_with_no_break_present(self):
        conductors = [_busbar(defects=[_lift_at(18.0, 0.5)])]
        for n in range(4):
            conductors.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
        result = assess_front_contact(_cell(conductors))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["interruption_count"], 0)
        self.assertEqual(result["delamination_count"], 1)
        self.assertAlmostEqual(result["collection_loss_fraction"], 0.0, places=9)
        self.assertAlmostEqual(result["delaminated_length_mm"], 0.5, places=9)

    def test_short_record_set_leaves_the_cell_open(self):
        result = assess_front_contact(_clean_cell(declared=7))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertFalse(result["inspection_complete"])
        self.assertEqual(result["missing_record_count"], 2)

    def test_coarse_inspection_cannot_support_a_clean_reading(self):
        result = assess_front_contact(_clean_cell(resolution=0.2))
        self.assertEqual(result["verdict"], DETECTION_INSUFFICIENT)
        self.assertFalse(result["detection_adequate"])

    def test_resolution_exactly_on_the_requirement_is_adequate(self):
        required = float(DEFAULT_FRONT_CONTACT_POLICY["required_detection_mm"])
        result = assess_front_contact(_clean_cell(resolution=required))
        self.assertAlmostEqual(
            result["conductors"][0]["length_mm"], BUSBAR_LENGTH, places=9
        )
        self.assertTrue(result["detection_adequate"])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_found_defect_outranks_an_unresolved_inspection(self):
        conductors = [_busbar(defects=[_break_at(12.0, 0.2)])]
        for n in range(4):
            conductors.append(_gridline("G%02d" % n, 5.0 + 8.0 * n))
        result = assess_front_contact(_cell(conductors, declared=9, resolution=0.5))
        self.assertEqual(result["verdict"], REJECT)

    def test_unreported_resolution_leaves_detection_unknown_not_adequate(self):
        result = assess_front_contact(_clean_cell(resolution=None))
        self.assertIsNone(result["detection_adequate"])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_gridline_feeding_an_unknown_busbar_rejected(self):
        conductors = [_busbar(), _gridline("G00", 5.0, busbar_id="BB9")]
        with self.assertRaises(ValueError):
            assess_front_contact(_cell(conductors))

    def test_gridline_feeding_a_gridline_rejected(self):
        conductors = [
            _busbar(),
            _gridline("G00", 5.0),
            _gridline("G01", 5.0, busbar_id="G00"),
        ]
        with self.assertRaises(ValueError):
            assess_front_contact(_cell(conductors))

    def test_feed_point_past_the_busbar_length_rejected(self):
        conductors = [_busbar(), _gridline("G00", BUSBAR_LENGTH + 3.0)]
        with self.assertRaises(ValueError):
            assess_front_contact(_cell(conductors))

    def test_more_records_than_declared_rejected(self):
        with self.assertRaises(ValueError):
            assess_front_contact(_clean_cell(gridline_count=4, declared=3))

    def test_duplicate_conductor_ids_rejected(self):
        conductors = [_busbar(), _gridline("G00", 5.0), _gridline("G00", 13.0)]
        with self.assertRaises(ValueError):
            assess_front_contact(_cell(conductors))

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_front_contact("SCA-001")

    def test_conductors_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_front_contact(
                {
                    "cell_id": "SCA-001",
                    "declared_conductor_count": 3,
                    "conductors": "three",
                }
            )

    def test_non_integer_declared_count_rejected(self):
        conductors = [_busbar()]
        with self.assertRaises(ValueError):
            assess_front_contact(_cell(conductors, declared="five"))

    def test_stricter_project_policy_is_honoured(self):
        strict = dict(DEFAULT_FRONT_CONTACT_POLICY)
        strict["required_detection_mm"] = 0.01
        cell = _clean_cell(resolution=0.02)
        loose = assess_front_contact(copy.deepcopy(cell))
        tight = assess_front_contact(copy.deepcopy(cell), strict)
        self.assertEqual(loose["verdict"], ACCEPT)
        self.assertEqual(tight["verdict"], DETECTION_INSUFFICIENT)


if __name__ == "__main__":
    unittest.main()
