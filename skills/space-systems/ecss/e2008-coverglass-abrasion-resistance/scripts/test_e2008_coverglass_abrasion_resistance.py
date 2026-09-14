#!/usr/bin/env python3
"""Contract test for the coverglass abrasion resistance leaf (offline)."""

import copy
import math
import unittest

from e2008_coverglass_abrasion_resistance_logic import (
    COATED_FACE,
    ERASER_FRICTION_COEFFICIENT,
    LOAD_TOLERANCE_FRACTION,
    MAX_COATING_REMOVAL_FRACTION,
    MAX_CONTACT_PRESSURE_KPA,
    MAX_HAZE_INCREASE_FRACTION,
    MAX_TRANSMITTANCE_LOSS_FRACTION,
    MIN_CONTACT_PRESSURE_KPA,
    NOMINAL_ERASER_LOAD_N,
    REQUIRED_RUN_EVIDENCE,
    RUN_ACCEPTED,
    RUN_NOT_ACCEPTED,
    RUN_VOID,
    SPECIFIED_STROKES,
    UNCOATED_FACE,
    abraded_track_area_mm2,
    abrasion_work_j,
    assess_abrasion_resistance,
    coating_removal_fraction,
    contact_pressure_kpa,
    face_is_the_coated_one,
    haze_increase_fraction,
    load_within_band,
    missing_run_evidence,
    stroke_count_matches,
    total_travel_mm,
    transmittance_loss_fraction,
)

GOOD_RUN = {
    "abraded_face": COATED_FACE,
    "delivered_strokes": SPECIFIED_STROKES,
    "eraser_load_n": 4.45,
    "eraser_tip_diameter_mm": 6.0,
    "stroke_length_mm": 20.0,
    "transmittance_before_fraction": 0.965,
    "transmittance_after_fraction": 0.963,
    "haze_before_fraction": 0.002,
    "haze_after_fraction": 0.003,
    "removed_coating_area_mm2": 0.0,
}


def _run(**overrides):
    run = copy.deepcopy(GOOD_RUN)
    run.update(overrides)
    return run


class RunEvidenceTests(unittest.TestCase):
    def test_the_specified_stroke_count_is_twenty(self):
        self.assertEqual(SPECIFIED_STROKES, 20)

    def test_a_complete_run_owes_nothing_further(self):
        self.assertEqual(missing_run_evidence(GOOD_RUN), ())

    def test_absent_evidence_is_named_rather_than_defaulted(self):
        run = _run()
        del run["eraser_load_n"]
        del run["haze_after_fraction"]
        self.assertEqual(
            set(missing_run_evidence(run)), {"eraser_load_n", "haze_after_fraction"}
        )

    def test_every_required_key_is_asked_for_in_a_stable_order(self):
        self.assertEqual(list(REQUIRED_RUN_EVIDENCE), sorted(REQUIRED_RUN_EVIDENCE))

    def test_a_run_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            missing_run_evidence(["abraded_face"])


class FaceAndDoseTests(unittest.TestCase):
    def test_the_coated_face_is_the_face_the_clause_is_about(self):
        self.assertTrue(face_is_the_coated_one(COATED_FACE))
        self.assertFalse(face_is_the_coated_one(UNCOATED_FACE))

    def test_an_unknown_face_is_refused(self):
        with self.assertRaises(ValueError):
            face_is_the_coated_one("edge-bevel")

    def test_the_specified_stroke_count_matches_only_itself(self):
        self.assertTrue(stroke_count_matches(20))
        self.assertFalse(stroke_count_matches(19))
        self.assertFalse(stroke_count_matches(21))

    def test_a_non_integer_stroke_count_is_refused(self):
        with self.assertRaises(ValueError):
            stroke_count_matches(20.0)

    def test_a_boolean_stroke_count_is_refused(self):
        with self.assertRaises(ValueError):
            stroke_count_matches(True)

    def test_a_negative_stroke_count_is_refused(self):
        with self.assertRaises(ValueError):
            stroke_count_matches(-3)

    def test_the_nominal_load_sits_inside_its_own_band(self):
        self.assertTrue(load_within_band(NOMINAL_ERASER_LOAD_N))

    def test_a_load_on_the_band_edge_is_inside_it(self):
        edge = NOMINAL_ERASER_LOAD_N * (1.0 + LOAD_TOLERANCE_FRACTION)
        self.assertTrue(load_within_band(edge))

    def test_a_load_well_outside_the_band_is_refused(self):
        self.assertFalse(load_within_band(NOMINAL_ERASER_LOAD_N * 2.0))
        self.assertFalse(load_within_band(NOMINAL_ERASER_LOAD_N * 0.5))

    def test_a_zero_load_is_not_a_run(self):
        with self.assertRaises(ValueError):
            load_within_band(0.0)


class GeometryTests(unittest.TestCase):
    def test_pressure_is_the_load_over_the_tip_area(self):
        pressure = contact_pressure_kpa(4.45, 6.0)
        expected = 4.45 / (math.pi * 36.0 / 4.0) * 1000.0
        self.assertAlmostEqual(pressure, expected, places=9)

    def test_a_tip_worn_to_twice_the_diameter_quarters_the_pressure(self):
        sharp = contact_pressure_kpa(4.45, 6.0)
        worn = contact_pressure_kpa(4.45, 12.0)
        self.assertAlmostEqual(sharp / worn, 4.0, places=9)

    def test_a_worn_flat_tip_falls_under_the_pressure_floor(self):
        self.assertLess(contact_pressure_kpa(4.45, 18.0), MIN_CONTACT_PRESSURE_KPA)

    def test_a_cut_down_tip_rises_over_the_pressure_ceiling(self):
        self.assertGreater(contact_pressure_kpa(4.45, 3.0), MAX_CONTACT_PRESSURE_KPA)

    def test_the_track_is_a_rectangle_with_two_end_caps(self):
        area = abraded_track_area_mm2(6.0, 20.0)
        self.assertAlmostEqual(area, 120.0 + math.pi * 9.0, places=9)

    def test_travel_is_the_stroke_length_times_the_stroke_count(self):
        self.assertAlmostEqual(total_travel_mm(20.0, 20), 400.0, places=9)

    def test_a_run_of_no_strokes_covers_no_path(self):
        self.assertAlmostEqual(total_travel_mm(20.0, 0), 0.0, places=9)

    def test_the_work_follows_load_travel_and_friction(self):
        work = abrasion_work_j(4.45, 400.0)
        expected = ERASER_FRICTION_COEFFICIENT * 4.45 * 0.4
        self.assertAlmostEqual(work, expected, places=9)

    def test_a_negative_tip_diameter_is_refused(self):
        with self.assertRaises(ValueError):
            abraded_track_area_mm2(-6.0, 20.0)


class OpticalChangeTests(unittest.TestCase):
    def test_a_small_drop_reads_as_a_small_relative_loss(self):
        loss = transmittance_loss_fraction(0.965, 0.963)
        self.assertAlmostEqual(loss, (0.965 - 0.963) / 0.965, places=12)

    def test_an_unchanged_face_lost_nothing(self):
        self.assertAlmostEqual(transmittance_loss_fraction(0.96, 0.96), 0.0, places=12)

    def test_a_brighter_face_reads_as_a_negative_loss(self):
        self.assertLess(transmittance_loss_fraction(0.90, 0.95), 0.0)

    def test_a_transmittance_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            transmittance_loss_fraction(1.4, 0.9)

    def test_a_zero_before_reading_cannot_be_a_reference(self):
        with self.assertRaises(ValueError):
            transmittance_loss_fraction(0.0, 0.0)

    def test_haze_change_is_the_plain_difference(self):
        self.assertAlmostEqual(haze_increase_fraction(0.002, 0.005), 0.003, places=12)

    def test_removal_is_the_share_of_the_rubbed_track(self):
        track = abraded_track_area_mm2(6.0, 20.0)
        self.assertAlmostEqual(
            coating_removal_fraction(track / 4.0, track), 0.25, places=12
        )

    def test_a_removed_area_needs_a_track_to_belong_to(self):
        with self.assertRaises(ValueError):
            coating_removal_fraction(1.0, 0.0)


class RunAssessmentTests(unittest.TestCase):
    def test_a_specified_run_on_an_adherent_coating_is_accepted(self):
        result = assess_abrasion_resistance(GOOD_RUN)
        self.assertEqual(result["verdict"], RUN_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["void_reasons"], [])

    def test_the_accepted_run_reports_its_own_dose(self):
        result = assess_abrasion_resistance(GOOD_RUN)
        self.assertEqual(result["delivered_strokes"], 20)
        self.assertTrue(result["stroke_count_matches"])
        self.assertTrue(result["load_within_band"])
        self.assertTrue(result["contact_pressure_within_band"])
        self.assertAlmostEqual(result["total_travel_mm"], 400.0, places=9)

    def test_strokes_on_the_uncoated_face_void_the_run(self):
        result = assess_abrasion_resistance(_run(abraded_face=UNCOATED_FACE))
        self.assertEqual(result["verdict"], RUN_VOID)
        self.assertTrue(result["run_void"])
        self.assertTrue(any("uncoated face" in r for r in result["void_reasons"]))

    def test_a_short_run_voids_rather_than_passing_easily(self):
        result = assess_abrasion_resistance(_run(delivered_strokes=12))
        self.assertEqual(result["verdict"], RUN_VOID)
        self.assertTrue(any("12 strokes" in r for r in result["void_reasons"]))

    def test_a_long_run_voids_rather_than_counting_as_conservative(self):
        result = assess_abrasion_resistance(_run(delivered_strokes=40))
        self.assertEqual(result["verdict"], RUN_VOID)
        self.assertTrue(any("40 strokes" in r for r in result["void_reasons"]))

    def test_a_hand_applied_load_voids_the_run(self):
        result = assess_abrasion_resistance(_run(eraser_load_n=9.0))
        self.assertEqual(result["verdict"], RUN_VOID)
        self.assertTrue(any("eraser load" in r for r in result["void_reasons"]))

    def test_a_worn_flat_tip_voids_the_run_at_the_correct_load(self):
        result = assess_abrasion_resistance(_run(eraser_tip_diameter_mm=18.0))
        self.assertEqual(result["verdict"], RUN_VOID)
        self.assertTrue(result["load_within_band"])
        self.assertFalse(result["contact_pressure_within_band"])

    def test_a_transmittance_collapse_is_a_finding_not_a_void(self):
        result = assess_abrasion_resistance(_run(transmittance_after_fraction=0.90))
        self.assertEqual(result["verdict"], RUN_NOT_ACCEPTED)
        self.assertFalse(result["run_void"])
        self.assertTrue(any("transmittance fell" in f for f in result["findings"]))

    def test_a_haze_rise_over_the_ceiling_is_a_finding(self):
        result = assess_abrasion_resistance(_run(haze_after_fraction=0.05))
        self.assertEqual(result["verdict"], RUN_NOT_ACCEPTED)
        self.assertGreater(result["haze_increase_fraction"], MAX_HAZE_INCREASE_FRACTION)
        self.assertTrue(any("haze rose" in f for f in result["findings"]))

    def test_coating_lifted_off_the_track_is_a_finding(self):
        track = abraded_track_area_mm2(6.0, 20.0)
        result = assess_abrasion_resistance(
            _run(removed_coating_area_mm2=track * 0.2)
        )
        self.assertEqual(result["verdict"], RUN_NOT_ACCEPTED)
        self.assertGreater(
            result["coating_removal_fraction"], MAX_COATING_REMOVAL_FRACTION
        )
        self.assertTrue(any("rubbed track" in f for f in result["findings"]))

    def test_a_face_reading_brighter_afterwards_is_called_out(self):
        result = assess_abrasion_resistance(
            _run(transmittance_before_fraction=0.90, transmittance_after_fraction=0.96)
        )
        self.assertEqual(result["verdict"], RUN_NOT_ACCEPTED)
        self.assertTrue(any("brighter after" in f for f in result["findings"]))

    def test_a_loss_exactly_on_the_ceiling_is_still_accepted(self):
        before = 1.0
        after = before * (1.0 - MAX_TRANSMITTANCE_LOSS_FRACTION)
        result = assess_abrasion_resistance(
            _run(
                transmittance_before_fraction=before,
                transmittance_after_fraction=after,
            )
        )
        self.assertAlmostEqual(
            result["transmittance_loss_fraction"],
            MAX_TRANSMITTANCE_LOSS_FRACTION,
            places=9,
        )
        self.assertEqual(result["verdict"], RUN_ACCEPTED)

    def test_a_void_run_is_never_reported_as_merely_not_accepted(self):
        result = assess_abrasion_resistance(
            _run(abraded_face=UNCOATED_FACE, transmittance_after_fraction=0.5)
        )
        self.assertEqual(result["verdict"], RUN_VOID)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["findings"])

    def test_missing_evidence_stops_the_assessment(self):
        run = _run()
        del run["stroke_length_mm"]
        with self.assertRaises(ValueError):
            assess_abrasion_resistance(run)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_abrasion_resistance(COATED_FACE)


if __name__ == "__main__":
    unittest.main()
