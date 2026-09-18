#!/usr/bin/env python3
"""Gate 3 contract test for e2007-test-setup-photographic-records.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_test_setup_photographic_records_logic import (
    DEFAULT_PHOTO_SPEC,
    PHOTO_EPS,
    SETUP_ARRANGEMENT,
    audit_photographic_record,
    catalogue_subjects,
    categorize_subject,
    check_coverage,
    check_frame,
    megapixels,
    report_status,
    required_views,
    resolve_spec,
    view_coverage,
)


def nominal_subjects():
    return [
        {"name": "radiated-emission-bench", "kind": "emission-setup",
         "reference_time_minutes": 600.0},
        {"name": "injection-point-a", "kind": "injection-test-point",
         "reference_time_minutes": 640.0},
        {"name": "field-probe-calibration", "kind": "probe-calibration",
         "reference_time_minutes": 540.0},
    ]


def frame(fid, subject, view, **kw):
    base = {
        "id": fid,
        "subject": subject,
        "view": view,
        "width_px": 4000,
        "height_px": 3000,
        "caption": "bench arrangement seen from the front left corner",
        "capture_time_minutes": 600.0,
        "in_report": True,
        "identification_label": True,
        "scale_reference": True,
    }
    base.update(kw)
    return base


def nominal_record():
    return {
        "subjects": nominal_subjects(),
        "frames": [
            frame("f1", "radiated-emission-bench", "front-elevation"),
            frame("f2", "radiated-emission-bench", "plan-view"),
            frame("f3", "injection-point-a", "close-up",
                  capture_time_minutes=640.0, scale_reference=False),
            frame("f4", "field-probe-calibration", "front-elevation",
                  capture_time_minutes=540.0),
        ],
    }


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["min_megapixels"], 2.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_PHOTO_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"min_megapixels": 8.0})
        self.assertAlmostEqual(spec["min_megapixels"], 8.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"min_megapixels": 8.0})
        self.assertAlmostEqual(DEFAULT_PHOTO_SPEC["min_megapixels"], 2.0, places=9)

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_photographers": 2.0})

    def test_negative_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_megapixels": -1.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("min_megapixels", 8.0)])


class TestSubjectCategorization(unittest.TestCase):
    def test_emission_setup_is_a_setup_arrangement(self):
        self.assertEqual(
            categorize_subject({"name": "s", "kind": "emission-setup"}),
            "setup-arrangement",
        )

    def test_injection_point_is_a_test_point(self):
        self.assertEqual(
            categorize_subject({"name": "p", "kind": "injection-test-point"}),
            "test-point",
        )

    def test_antenna_calibration_is_a_calibration_arrangement(self):
        self.assertEqual(
            categorize_subject({"name": "c", "kind": "antenna-calibration"}),
            "calibration-arrangement",
        )

    def test_unrecognized_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_subject({"name": "x", "kind": "team-portrait"})

    def test_subject_without_a_name_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_subject({"kind": "emission-setup"})

    def test_subject_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_subject(["emission-setup"])


class TestCatalogue(unittest.TestCase):
    def test_every_subject_is_catalogued(self):
        catalogue = catalogue_subjects(nominal_subjects())
        self.assertEqual(len(catalogue), 3)
        self.assertEqual(catalogue[0]["category"], SETUP_ARRANGEMENT)

    def test_empty_record_is_rejected(self):
        with self.assertRaises(ValueError):
            catalogue_subjects([])

    def test_duplicate_subject_names_are_rejected(self):
        subjects = nominal_subjects()
        subjects[1]["name"] = subjects[0]["name"]
        with self.assertRaises(ValueError):
            catalogue_subjects(subjects)

    def test_record_without_a_setup_arrangement_is_rejected(self):
        subjects = [s for s in nominal_subjects() if s["kind"] != "emission-setup"]
        with self.assertRaises(ValueError):
            catalogue_subjects(subjects)

    def test_non_numeric_reference_time_is_rejected(self):
        subjects = nominal_subjects()
        subjects[0]["reference_time_minutes"] = "600"
        with self.assertRaises(ValueError):
            catalogue_subjects(subjects)


class TestResolution(unittest.TestCase):
    def test_megapixels_from_pixel_dimensions(self):
        self.assertAlmostEqual(megapixels(4000, 3000), 12.0, places=9)

    def test_resolution_exactly_on_the_floor_is_accepted(self):
        value = megapixels(2000, 1000)
        self.assertAlmostEqual(value, 2.0, places=9)
        record = nominal_record()
        record["frames"][0]["width_px"] = 2000
        record["frames"][0]["height_px"] = 1000
        report = audit_photographic_record(record)
        self.assertTrue(report["frames"][0]["usable"])

    def test_zero_pixel_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            megapixels(0, 3000)

    def test_non_numeric_pixel_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            megapixels("4000", 3000)


class TestRequiredViews(unittest.TestCase):
    def test_a_setup_arrangement_needs_more_than_one_view(self):
        self.assertAlmostEqual(required_views(SETUP_ARRANGEMENT), 2.0, places=9)

    def test_a_test_point_needs_one_view(self):
        self.assertAlmostEqual(required_views("test-point"), 1.0, places=9)

    def test_unrecognized_category_is_rejected(self):
        with self.assertRaises(ValueError):
            required_views("group-photograph")


class TestFrameAudit(unittest.TestCase):
    def setUp(self):
        self.catalogue = catalogue_subjects(nominal_subjects())

    def test_a_compliant_frame_is_usable(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation"), self.catalogue
        )
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])

    def test_low_resolution_is_a_finding(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation",
                  width_px=800, height_px=600),
            self.catalogue,
        )
        self.assertTrue(any("resolution" in f for f in result["findings"]))

    def test_short_caption_is_a_finding(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation", caption="bench"),
            self.catalogue,
        )
        self.assertTrue(any("caption" in f for f in result["findings"]))

    def test_missing_identification_label_is_a_finding(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation",
                  identification_label=False),
            self.catalogue,
        )
        self.assertTrue(any("identification label" in f for f in result["findings"]))

    def test_setup_frame_without_a_scale_reference_is_a_finding(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation",
                  scale_reference=False),
            self.catalogue,
        )
        self.assertTrue(any("scale reference" in f for f in result["findings"]))

    def test_test_point_frame_needs_no_scale_reference(self):
        result = check_frame(
            frame("f3", "injection-point-a", "close-up",
                  capture_time_minutes=640.0, scale_reference=False),
            self.catalogue,
        )
        self.assertTrue(result["usable"])

    def test_capture_offset_outside_the_window_is_a_finding(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation",
                  capture_time_minutes=900.0),
            self.catalogue,
        )
        self.assertTrue(any("validity window" in f for f in result["findings"]))

    def test_capture_offset_exactly_on_the_window_is_accepted(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation",
                  capture_time_minutes=720.0),
            self.catalogue,
        )
        self.assertAlmostEqual(result["capture_offset_minutes"], 120.0, places=9)
        self.assertTrue(result["usable"])

    def test_frame_absent_from_the_report_is_a_finding(self):
        result = check_frame(
            frame("f1", "radiated-emission-bench", "front-elevation", in_report=False),
            self.catalogue,
        )
        self.assertTrue(any("absent from the report" in f for f in result["findings"]))

    def test_frame_naming_an_unlisted_subject_is_rejected(self):
        with self.assertRaises(ValueError):
            check_frame(frame("f9", "canteen", "front-elevation"), self.catalogue)

    def test_non_boolean_in_report_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            check_frame(
                frame("f1", "radiated-emission-bench", "front-elevation", in_report="yes"),
                self.catalogue,
            )

    def test_frame_without_a_view_is_rejected(self):
        bad = frame("f1", "radiated-emission-bench", "front-elevation")
        bad["view"] = "   "
        with self.assertRaises(ValueError):
            check_frame(bad, self.catalogue)


class TestCoverage(unittest.TestCase):
    def test_repeated_view_counts_once(self):
        audited = [
            {"subject": "radiated-emission-bench", "view": "front-elevation", "usable": True},
            {"subject": "radiated-emission-bench", "view": "front-elevation", "usable": True},
        ]
        self.assertEqual(
            view_coverage(audited), {"radiated-emission-bench": ["front-elevation"]}
        )

    def test_unusable_frame_does_not_count_as_coverage(self):
        audited = [
            {"subject": "radiated-emission-bench", "view": "plan-view", "usable": False},
        ]
        self.assertEqual(view_coverage(audited), {})

    def test_coverage_shortfall_is_reported(self):
        catalogue = catalogue_subjects(nominal_subjects())
        result = check_coverage(catalogue, {"radiated-emission-bench": ["front-elevation"]})
        self.assertTrue(any("radiated-emission-bench" in f for f in result["findings"]))
        self.assertEqual(result["shortfalls"][0]["held"], 1)

    def test_coverage_record_without_a_subject_is_rejected(self):
        with self.assertRaises(ValueError):
            view_coverage([{"view": "plan-view", "usable": True}])


class TestEndToEnd(unittest.TestCase):
    def test_a_complete_record_releases_the_report(self):
        report = audit_photographic_record(nominal_record())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "report-photographically-complete")
        self.assertTrue(report["complete"])

    def test_a_single_view_of_a_setup_holds_the_report(self):
        record = nominal_record()
        record["frames"] = [f for f in record["frames"] if f["id"] != "f2"]
        report = audit_photographic_record(record)
        self.assertFalse(report["complete"])
        self.assertEqual(report["status"], "hold-report")

    def test_an_unphotographed_subject_holds_the_report(self):
        record = nominal_record()
        record["frames"] = [f for f in record["frames"] if f["subject"] != "field-probe-calibration"]
        report = audit_photographic_record(record)
        self.assertTrue(any("field-probe-calibration" in f for f in report["findings"]))

    def test_a_frame_left_out_of_the_report_holds_the_report(self):
        record = nominal_record()
        record["frames"][0]["in_report"] = False
        report = audit_photographic_record(record)
        self.assertEqual(report["status"], "hold-report")

    def test_spec_override_can_requalify_a_record(self):
        record = nominal_record()
        record["frames"] = [f for f in record["frames"] if f["id"] != "f2"]
        self.assertFalse(audit_photographic_record(record)["complete"])
        record["spec"] = {"min_views_setup_arrangement": 1.0}
        self.assertTrue(audit_photographic_record(record)["complete"])

    def test_duplicate_frame_ids_are_rejected(self):
        record = nominal_record()
        record["frames"][1]["id"] = record["frames"][0]["id"]
        with self.assertRaises(ValueError):
            audit_photographic_record(record)

    def test_record_without_frames_is_rejected(self):
        record = nominal_record()
        record["frames"] = []
        with self.assertRaises(ValueError):
            audit_photographic_record(record)

    def test_missing_required_key_is_rejected(self):
        record = nominal_record()
        del record["subjects"]
        with self.assertRaises(ValueError):
            audit_photographic_record(record)

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            audit_photographic_record([("subjects", [])])

    def test_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            report_status("hold")

    def test_named_tolerance_is_far_below_any_evidence_floor(self):
        self.assertLess(PHOTO_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
