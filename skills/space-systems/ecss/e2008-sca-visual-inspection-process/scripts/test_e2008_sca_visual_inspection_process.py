#!/usr/bin/env python3
"""Contract test for the cell assembly inspection adequacy check (offline)."""

import copy
import unittest

from e2008_sca_visual_inspection_process_logic import (
    CAPABLE,
    DEFAULT_INSPECTION_POLICY,
    MARGINAL,
    NOT_CAPABLE,
    PROCESS_ADEQUATE,
    PROCESS_INADEQUATE,
    REFER,
    STATION_KINDS,
    assess_inspection_station,
    qualify_inspection_process,
    sampled_resolved_feature_mm,
    station_resolved_feature_mm,
    unaided_resolved_feature_mm,
    validate_inspection_policy,
)

CRITERION_MM = 0.5
UNAIDED_300 = unaided_resolved_feature_mm(300.0)

BASE_STATION = {
    "station_id": "ST-FRONT",
    "kind": "unaided-visual",
    "working_distance_mm": 300.0,
    "magnification": 1.0,
    "illuminance_lux": 1200.0,
    "incidence_angle_deg": 0.0,
    "faces_examined": ["front"],
}

CAMERA_STATION = {
    "station_id": "ST-CAM",
    "kind": "imaging-camera",
    "field_of_view_mm": 100.0,
    "pixel_count": 4000,
    "illuminance_lux": 1500.0,
    "incidence_angle_deg": 0.0,
    "faces_examined": ["rear"],
}


def _station(**overrides):
    station = copy.deepcopy(BASE_STATION)
    station.update(overrides)
    return station


def _camera(**overrides):
    station = copy.deepcopy(CAMERA_STATION)
    station.update(overrides)
    return station


def _process(stations=None, **overrides):
    process = {
        "assembly_id": "SCA-001",
        "smallest_criterion_mm": CRITERION_MM,
        "declared_faces": ["front", "rear"],
        "stations": stations if stations is not None else [_station(), _camera()],
    }
    process.update(overrides)
    return process


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_inspection_policy(DEFAULT_INSPECTION_POLICY),
            DEFAULT_INSPECTION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_policy("default")

    def test_detection_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        broken["detection_margin"] = 0.5
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)

    def test_single_sample_per_feature_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        broken["samples_per_feature"] = 1.0
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)

    def test_grazing_incidence_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        broken["max_incidence_angle_deg"] = 90.0
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)

    def test_missing_illuminance_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        del broken["min_illuminance_lux"]
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)


class ResolutionTests(unittest.TestCase):
    def test_unaided_resolution_at_a_working_distance(self):
        self.assertAlmostEqual(UNAIDED_300, 0.087266463, places=8)

    def test_unaided_resolution_scales_with_the_working_distance(self):
        self.assertAlmostEqual(
            unaided_resolved_feature_mm(600.0), 2.0 * UNAIDED_300, places=9
        )

    def test_magnification_divides_the_resolved_feature(self):
        station = _station(kind="magnified-visual", magnification=4.0)
        self.assertAlmostEqual(
            station_resolved_feature_mm(station), UNAIDED_300 / 4.0, places=12
        )

    def test_a_magnified_station_at_unity_is_rejected(self):
        station = _station(kind="magnified-visual", magnification=1.0)
        with self.assertRaises(ValueError):
            station_resolved_feature_mm(station)

    def test_an_unaided_station_with_a_lens_is_rejected(self):
        station = _station(kind="unaided-visual", magnification=6.0)
        with self.assertRaises(ValueError):
            station_resolved_feature_mm(station)

    def test_sampling_sets_the_imaging_resolution(self):
        self.assertAlmostEqual(
            sampled_resolved_feature_mm(100.0, 4000), 0.05, places=12
        )

    def test_more_pixels_over_the_same_field_resolve_finer(self):
        coarse = sampled_resolved_feature_mm(100.0, 1000)
        fine = sampled_resolved_feature_mm(100.0, 4000)
        self.assertAlmostEqual(coarse, 4.0 * fine, places=12)

    def test_a_single_sample_per_feature_is_rejected(self):
        with self.assertRaises(ValueError):
            sampled_resolved_feature_mm(100.0, 4000, samples_per_feature=1.0)

    def test_zero_pixel_count_rejected(self):
        with self.assertRaises(ValueError):
            sampled_resolved_feature_mm(100.0, 0)

    def test_unknown_station_kind_rejected(self):
        with self.assertRaises(ValueError):
            station_resolved_feature_mm(_station(kind="x-ray-bench"))

    def test_every_declared_station_kind_is_handled(self):
        self.assertEqual(len(STATION_KINDS), 3)


class StationAdequacyTests(unittest.TestCase):
    def test_a_close_unaided_station_is_capable(self):
        result = assess_inspection_station(_station(), CRITERION_MM)
        self.assertEqual(result["verdict"], CAPABLE)
        self.assertTrue(result["credited"])
        self.assertTrue(result["conditions_met"])

    def test_resolution_exactly_on_the_required_feature_is_capable(self):
        criterion = 3.0 * UNAIDED_300
        result = assess_inspection_station(_station(), criterion)
        self.assertAlmostEqual(
            result["effective_resolved_feature_mm"],
            result["required_feature_mm"],
            places=12,
        )
        self.assertEqual(result["verdict"], CAPABLE)

    def test_a_station_with_no_margin_is_marginal(self):
        result = assess_inspection_station(
            _camera(field_of_view_mm=100.0, pixel_count=800), CRITERION_MM
        )
        self.assertAlmostEqual(
            result["effective_resolved_feature_mm"], 0.25, places=12
        )
        self.assertEqual(result["verdict"], MARGINAL)
        self.assertFalse(result["credited"])

    def test_off_normal_viewing_can_cost_a_station_its_margin(self):
        square = assess_inspection_station(_station(), CRITERION_MM)
        tilted = assess_inspection_station(
            _station(incidence_angle_deg=60.0), CRITERION_MM
        )
        self.assertEqual(square["verdict"], CAPABLE)
        self.assertEqual(tilted["verdict"], MARGINAL)
        self.assertTrue(tilted["conditions_met"])

    def test_a_station_coarser_than_the_criterion_is_not_capable(self):
        result = assess_inspection_station(
            _camera(field_of_view_mm=100.0, pixel_count=200), CRITERION_MM
        )
        self.assertEqual(result["verdict"], NOT_CAPABLE)

    def test_off_normal_viewing_coarsens_the_station(self):
        result = assess_inspection_station(
            _station(incidence_angle_deg=60.0), CRITERION_MM
        )
        self.assertAlmostEqual(result["foreshortening_factor"], 2.0, places=9)
        self.assertAlmostEqual(
            result["effective_resolved_feature_mm"], 2.0 * UNAIDED_300, places=9
        )

    def test_normal_viewing_does_not_coarsen_the_station(self):
        result = assess_inspection_station(_station(), CRITERION_MM)
        self.assertAlmostEqual(result["foreshortening_factor"], 1.0, places=12)
        self.assertAlmostEqual(
            result["effective_resolved_feature_mm"], UNAIDED_300, places=12
        )

    def test_incidence_exactly_on_the_limit_still_meets_the_condition(self):
        result = assess_inspection_station(
            _station(incidence_angle_deg=60.0), CRITERION_MM
        )
        self.assertTrue(result["conditions_met"])

    def test_incidence_past_the_limit_sends_the_station_to_review(self):
        result = assess_inspection_station(
            _station(incidence_angle_deg=75.0), CRITERION_MM
        )
        self.assertFalse(result["conditions_met"])
        self.assertEqual(result["verdict"], REFER)

    def test_illuminance_exactly_on_the_floor_still_counts(self):
        result = assess_inspection_station(
            _station(illuminance_lux=1000.0), CRITERION_MM
        )
        self.assertTrue(result["conditions_met"])
        self.assertEqual(result["verdict"], CAPABLE)

    def test_a_dim_station_is_not_credited_even_when_it_resolves(self):
        result = assess_inspection_station(
            _station(illuminance_lux=150.0), CRITERION_MM
        )
        self.assertFalse(result["credited"])
        self.assertEqual(result["verdict"], REFER)

    def test_standing_off_past_the_working_distance_is_a_condition_failure(self):
        result = assess_inspection_station(
            _station(working_distance_mm=900.0), CRITERION_MM
        )
        self.assertFalse(result["conditions_met"])

    def test_a_camera_needs_no_working_distance(self):
        station = _camera()
        self.assertNotIn("working_distance_mm", station)
        result = assess_inspection_station(station, CRITERION_MM)
        self.assertEqual(result["verdict"], CAPABLE)

    def test_a_station_with_no_face_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_station(_station(faces_examined=[]), CRITERION_MM)

    def test_a_station_repeating_a_face_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_station(
                _station(faces_examined=["front", "front"]), CRITERION_MM
            )

    def test_grazing_incidence_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_station(
                _station(incidence_angle_deg=90.0), CRITERION_MM
            )

    def test_negative_illuminance_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_station(_station(illuminance_lux=-5.0), CRITERION_MM)

    def test_zero_criterion_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_station(_station(), 0.0)


class ProcessTests(unittest.TestCase):
    def test_a_covered_assembly_with_capable_stations_is_adequate(self):
        result = qualify_inspection_process(_process())
        self.assertEqual(result["verdict"], PROCESS_ADEQUATE)
        self.assertTrue(result["process_adequate"])
        self.assertEqual(result["uncovered_faces"], [])

    def test_the_bound_follows_the_coarsest_credited_face(self):
        result = qualify_inspection_process(_process())
        self.assertAlmostEqual(
            result["statement_bounded_at_mm"], UNAIDED_300, places=12
        )
        self.assertAlmostEqual(result["face_bound_mm"]["rear"], 0.05, places=12)

    def test_an_unreached_face_leaves_the_process_inadequate(self):
        result = qualify_inspection_process(_process([_station()]))
        self.assertEqual(result["verdict"], PROCESS_INADEQUATE)
        self.assertEqual(result["uncovered_faces"], ["rear"])

    def test_a_marginal_station_does_not_cover_its_face(self):
        stations = [_station(incidence_angle_deg=60.0), _camera()]
        result = qualify_inspection_process(_process(stations))
        self.assertEqual(result["uncovered_faces"], ["front"])
        self.assertEqual(result["not_credited_ids"], ["ST-FRONT"])

    def test_a_second_station_can_recover_a_face(self):
        stations = [
            _station(incidence_angle_deg=60.0),
            _station(station_id="ST-FRONT-B"),
            _camera(),
        ]
        result = qualify_inspection_process(_process(stations))
        self.assertEqual(result["uncovered_faces"], [])
        self.assertEqual(result["verdict"], PROCESS_INADEQUATE)

    def test_a_station_examining_an_undeclared_face_rejected(self):
        stations = [_station(faces_examined=["edge"]), _camera()]
        with self.assertRaises(ValueError):
            qualify_inspection_process(_process(stations))

    def test_duplicate_station_ids_rejected(self):
        stations = [_station(), _station(faces_examined=["rear"])]
        with self.assertRaises(ValueError):
            qualify_inspection_process(_process(stations))

    def test_a_setup_with_no_stations_rejected(self):
        with self.assertRaises(ValueError):
            qualify_inspection_process(_process([]))

    def test_an_assembly_with_no_declared_faces_rejected(self):
        with self.assertRaises(ValueError):
            qualify_inspection_process(_process(declared_faces=[]))

    def test_non_mapping_process_rejected(self):
        with self.assertRaises(ValueError):
            qualify_inspection_process("SCA-001")

    def test_station_verdict_counts_add_up(self):
        result = qualify_inspection_process(_process())
        self.assertEqual(sum(result["station_verdict_counts"].values()), 2)

    def test_a_tighter_criterion_can_break_an_adequate_setup(self):
        result = qualify_inspection_process(
            _process(smallest_criterion_mm=0.05)
        )
        self.assertFalse(result["process_adequate"])
        self.assertIn("ST-FRONT", result["not_credited_ids"])


if __name__ == "__main__":
    unittest.main()
