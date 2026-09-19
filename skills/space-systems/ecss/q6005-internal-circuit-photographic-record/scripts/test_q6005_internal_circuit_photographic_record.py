#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.3.4 photographic-record leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_internal_circuit_photographic_record.py
"""

import unittest

from q6005_internal_circuit_photographic_record_logic import (
    ACCEPTANCE_INDEX,
    ARCHIVE_PROVISIONS,
    FRAME_QUALITY_CREDIT,
    MANDATORY_ARCHIVE_PROVISIONS,
    MANDATORY_VIEWS,
    MINIMUM_PIXELS_ACROSS_FEATURE,
    MINIMUM_RETENTION_YEARS,
    PROVISION_STATE_CREDIT,
    RECORD_TOLERANCE,
    REQUIRED_VIEWS,
    VERDICTS,
    assess_photographic_record,
    assess_provision,
    assess_view,
    covered_subjects,
    frame_is_usable,
    frame_quality_credit,
    missing_views,
    normalize_frames,
    pixels_across_feature,
    provision_state_credit,
    provision_weight,
    record_adequacy_index,
    resolution_is_adequate,
    retention_is_sufficient,
    uncovered_subjects,
    under_resolved_frames,
    usable_frames,
    view_weight,
)

FEATURE_UM = 25.0
GOOD_DENSITY = MINIMUM_PIXELS_ACROSS_FEATURE / FEATURE_UM
SUBJECTS = ["die-1", "die-2", "interconnect-region-a", "substrate-attach-1"]
OPTIONAL_PROVISION = "archive-format-openly-readable"
MANDATORY_PROVISION = "images-carry-the-unit-identification"
OPTIONAL_VIEW = "identification-marking-view"


def frame(frame_id, view, subjects=(), quality="sharp-and-evenly-lit", density=None):
    """One captured frame of the open assembly."""
    return {
        "frame_id": frame_id,
        "view": view,
        "quality": quality,
        "subjects": list(subjects),
        "pixels_per_um": GOOD_DENSITY if density is None else density,
    }


def complete_frames():
    """A frame set that supplies every view and covers every subject."""
    return [
        frame("F-1", "overall-interior-view", SUBJECTS),
        frame("F-2", "die-detail-view", ["die-1", "die-2"]),
        frame("F-3", "interconnect-detail-view", ["interconnect-region-a"]),
        frame("F-4", "substrate-attach-detail-view", ["substrate-attach-1"]),
        frame("F-5", OPTIONAL_VIEW),
    ]


def every_provision(state="met-and-evidenced", **overrides):
    """Every archive provision in one state, with named exceptions."""
    states = {name: state for name in ARCHIVE_PROVISIONS}
    states.update(overrides)
    return states


def run(**overrides):
    """Grade one photographic record."""
    case = {
        "unit_id": "HYB-PR-1",
        "declared_subjects": SUBJECTS,
        "frames": complete_frames(),
        "smallest_feature_um": FEATURE_UM,
        "retention_years": MINIMUM_RETENTION_YEARS,
        "provisions": every_provision(),
        "minimum_retention_years": None,
    }
    case.update(overrides)
    return assess_photographic_record(**case)


class ResolutionTests(unittest.TestCase):
    def test_a_feature_spans_its_size_times_the_pixel_density(self):
        self.assertAlmostEqual(pixels_across_feature(FEATURE_UM, 0.4), 10.0, places=9)

    def test_a_denser_frame_puts_more_pixels_on_the_same_feature(self):
        self.assertGreater(
            pixels_across_feature(FEATURE_UM, 0.8), pixels_across_feature(FEATURE_UM, 0.4)
        )

    def test_a_zero_pixel_density_is_rejected(self):
        with self.assertRaises(ValueError):
            pixels_across_feature(FEATURE_UM, 0.0)

    def test_a_frame_exactly_on_the_pixel_floor_is_adequate(self):
        self.assertAlmostEqual(
            pixels_across_feature(FEATURE_UM, GOOD_DENSITY),
            MINIMUM_PIXELS_ACROSS_FEATURE,
            places=9,
        )
        self.assertTrue(resolution_is_adequate(FEATURE_UM, GOOD_DENSITY))

    def test_a_smaller_feature_needs_a_denser_frame(self):
        self.assertFalse(resolution_is_adequate(FEATURE_UM / 5.0, GOOD_DENSITY))


class FrameSetTests(unittest.TestCase):
    def test_an_empty_frame_set_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_frames([])

    def test_a_repeated_frame_identifier_is_rejected(self):
        frames = complete_frames() + [frame("F-1", OPTIONAL_VIEW)]
        with self.assertRaises(ValueError):
            normalize_frames(frames)

    def test_an_unknown_view_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_frames([frame("F-9", "artistic-impression")])

    def test_an_unknown_quality_grade_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_frames([frame("F-9", OPTIONAL_VIEW, quality="looked-alright")])

    def test_an_empty_subject_name_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_frames([frame("F-9", OPTIONAL_VIEW, subjects=["  "])])

    def test_a_readable_frame_is_usable_and_an_unreadable_one_is_not(self):
        self.assertTrue(frame_is_usable("sharp-and-evenly-lit"))
        self.assertTrue(frame_is_usable("soft-focus"))
        self.assertFalse(frame_is_usable("unreadable"))

    def test_an_unreadable_frame_is_left_out_of_the_usable_set(self):
        frames = complete_frames() + [
            frame("F-6", OPTIONAL_VIEW, ["die-3"], quality="unreadable")
        ]
        self.assertEqual(len(usable_frames(frames)), len(complete_frames()))

    def test_an_unknown_frame_quality_has_no_credit(self):
        with self.assertRaises(ValueError):
            frame_quality_credit("fine-I-suppose")


class CoverageTests(unittest.TestCase):
    def test_a_complete_set_covers_every_declared_subject(self):
        self.assertEqual(uncovered_subjects(complete_frames(), SUBJECTS), [])

    def test_a_subject_nobody_photographed_is_named(self):
        self.assertEqual(
            uncovered_subjects(complete_frames(), SUBJECTS + ["die-3"]), ["die-3"]
        )

    def test_a_subject_seen_only_in_an_unreadable_frame_stays_uncovered(self):
        frames = complete_frames() + [
            frame("F-6", "die-detail-view", ["die-3"], quality="unreadable")
        ]
        self.assertIn("die-3", uncovered_subjects(frames, SUBJECTS + ["die-3"]))

    def test_the_covered_set_lists_only_what_a_reader_can_use(self):
        self.assertEqual(covered_subjects(complete_frames()), sorted(SUBJECTS))

    def test_an_empty_declared_subject_list_is_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_subjects(complete_frames(), [])

    def test_a_complete_set_supplies_every_required_view(self):
        self.assertEqual(missing_views(complete_frames()), [])

    def test_a_dropped_view_is_named(self):
        frames = [f for f in complete_frames() if f["view"] != OPTIONAL_VIEW]
        self.assertEqual(missing_views(frames), [OPTIONAL_VIEW])

    def test_a_frame_too_coarse_for_the_feature_is_named(self):
        frames = complete_frames()
        frames[1]["pixels_per_um"] = GOOD_DENSITY / 10.0
        self.assertEqual(under_resolved_frames(frames, FEATURE_UM), ["F-2"])

    def test_a_frame_that_declares_no_density_is_treated_as_unproven(self):
        frames = complete_frames()
        frames[2]["pixels_per_um"] = None
        self.assertIn("F-3", under_resolved_frames(frames, FEATURE_UM))


class ArchiveTests(unittest.TestCase):
    def test_a_retention_exactly_on_the_floor_is_sufficient(self):
        self.assertTrue(retention_is_sufficient(MINIMUM_RETENTION_YEARS))

    def test_a_shorter_retention_is_insufficient(self):
        self.assertFalse(retention_is_sufficient(MINIMUM_RETENTION_YEARS - 1))

    def test_a_programme_may_ask_for_a_longer_retention(self):
        self.assertFalse(
            retention_is_sufficient(MINIMUM_RETENTION_YEARS, MINIMUM_RETENTION_YEARS * 2)
        )

    def test_a_fractional_retention_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_is_sufficient(10.5)

    def test_every_provision_carries_a_positive_weight(self):
        for name in ARCHIVE_PROVISIONS:
            self.assertGreater(provision_weight(name), 0.0)

    def test_every_mandatory_provision_is_a_published_provision(self):
        for name in MANDATORY_ARCHIVE_PROVISIONS:
            self.assertIn(name, ARCHIVE_PROVISIONS)

    def test_an_unknown_provision_state_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_state_credit("we-keep-everything")

    def test_an_unmet_mandatory_provision_is_marked_missing(self):
        record = assess_provision(MANDATORY_PROVISION, "not-met")
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-archive-provision-not-met", record["findings"])


class ViewGradingTests(unittest.TestCase):
    def test_every_view_carries_a_positive_weight(self):
        for name in REQUIRED_VIEWS:
            self.assertGreater(view_weight(name), 0.0)

    def test_every_mandatory_view_is_a_published_view(self):
        for name in MANDATORY_VIEWS:
            self.assertIn(name, REQUIRED_VIEWS)

    def test_a_sharp_frame_gives_a_view_its_full_weight(self):
        record = assess_view("die-detail-view", complete_frames())
        self.assertAlmostEqual(
            record["weighted_credit"], REQUIRED_VIEWS["die-detail-view"], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_the_best_frame_of_a_view_decides_its_credit(self):
        frames = complete_frames() + [
            frame("F-7", "die-detail-view", ["die-1"], quality="soft-focus")
        ]
        record = assess_view("die-detail-view", frames)
        self.assertAlmostEqual(record["credit"], 1.0, places=9)

    def test_a_view_supplied_only_softly_is_a_finding_not_a_miss(self):
        frames = [f for f in complete_frames() if f["view"] != OPTIONAL_VIEW]
        frames.append(frame("F-8", OPTIONAL_VIEW, quality="soft-focus"))
        record = assess_view(OPTIONAL_VIEW, frames)
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("required-view-supplied-below-full-quality", record["findings"])

    def test_a_mandatory_view_supplied_only_unreadably_is_missing(self):
        frames = [f for f in complete_frames() if f["view"] != "die-detail-view"]
        frames.append(frame("F-8", "die-detail-view", ["die-1"], quality="unreadable"))
        record = assess_view("die-detail-view", frames)
        self.assertTrue(record["mandatory_missing"])

    def test_an_empty_graded_set_has_no_index(self):
        with self.assertRaises(ValueError):
            record_adequacy_index([])


class WholeRecordTests(unittest.TestCase):
    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_complete_well_archived_record_is_accepted(self):
        result = run()
        self.assertEqual(result["verdict"], "photographic-record-accepted")
        self.assertTrue(result["record_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["record_adequacy_index"], 1.0, places=9)

    def test_an_uncovered_subject_leaves_the_record_incomplete(self):
        result = run(declared_subjects=SUBJECTS + ["die-3"])
        self.assertEqual(result["verdict"], "photographic-record-incomplete")
        self.assertEqual(result["uncovered_subjects"], ["die-3"])

    def test_a_dropped_mandatory_view_leaves_the_record_incomplete(self):
        frames = [f for f in complete_frames() if f["view"] != "interconnect-detail-view"]
        result = run(frames=frames, declared_subjects=["die-1", "die-2", "substrate-attach-1"])
        self.assertEqual(result["verdict"], "photographic-record-incomplete")

    def test_a_dropped_optional_view_does_not_make_the_record_incomplete(self):
        frames = [f for f in complete_frames() if f["view"] != OPTIONAL_VIEW]
        result = run(frames=frames)
        self.assertNotEqual(result["verdict"], "photographic-record-incomplete")
        self.assertEqual(result["missing_views"], [OPTIONAL_VIEW])

    def test_an_under_resolved_frame_denies_the_record(self):
        frames = complete_frames()
        frames[1]["pixels_per_um"] = GOOD_DENSITY / 10.0
        result = run(frames=frames)
        self.assertEqual(result["verdict"], "photographic-record-not-accepted")
        self.assertEqual(result["under_resolved_frames"], ["F-2"])

    def test_an_unidentified_record_is_denied(self):
        result = run(provisions=every_provision(**{MANDATORY_PROVISION: "not-met"}))
        self.assertEqual(result["verdict"], "photographic-record-not-accepted")
        self.assertFalse(result["record_accepted"])

    def test_a_record_made_after_the_seal_is_denied(self):
        result = run(
            provisions=every_provision(
                **{"record-captured-before-the-package-was-sealed": "not-met"}
            )
        )
        self.assertEqual(result["verdict"], "photographic-record-not-accepted")

    def test_a_short_retention_is_denied_whatever_the_provision_claims(self):
        result = run(retention_years=MINIMUM_RETENTION_YEARS - 5)
        self.assertFalse(result["retention_sufficient"])
        self.assertEqual(result["verdict"], "photographic-record-not-accepted")

    def test_an_unevidenced_optional_provision_leaves_the_record_open(self):
        result = run(provisions=every_provision(**{OPTIONAL_PROVISION: "met-not-evidenced"}))
        self.assertEqual(
            result["verdict"], "photographic-record-accepted-with-open-actions"
        )
        self.assertTrue(result["record_accepted"])

    def test_a_thin_archive_falls_under_the_acceptance_index(self):
        result = run(
            provisions=every_provision(
                **{
                    OPTIONAL_PROVISION: "not-met",
                    "archive-entries-cannot-be-silently-replaced": "not-met",
                }
            )
        )
        self.assertLess(result["record_adequacy_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "photographic-record-not-accepted")

    def test_an_incomplete_record_outranks_a_denied_archive(self):
        result = run(
            declared_subjects=SUBJECTS + ["die-3"],
            provisions=every_provision(**{MANDATORY_PROVISION: "not-met"}),
        )
        self.assertEqual(result["verdict"], "photographic-record-incomplete")

    def test_an_unreadable_frame_is_counted_but_not_credited(self):
        frames = complete_frames() + [
            frame("F-6", OPTIONAL_VIEW, ["die-1"], quality="unreadable")
        ]
        result = run(frames=frames)
        self.assertEqual(result["frame_count"], len(frames))
        self.assertEqual(result["usable_frame_count"], len(frames) - 1)

    def test_an_unknown_provision_in_the_input_is_rejected(self):
        with self.assertRaises(ValueError):
            run(provisions=every_provision(**{"we-burn-a-disc": "met-and-evidenced"}))

    def test_a_blank_unit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(unit_id=" ")

    def test_a_non_mapping_provision_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(provisions=[MANDATORY_PROVISION])


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(RECORD_TOLERANCE, 1e-6)

    def test_the_frame_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(FRAME_QUALITY_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(FRAME_QUALITY_CREDIT.values()), 0.0, places=9)

    def test_the_provision_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(PROVISION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(PROVISION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_complete_record(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)

    def test_the_retention_floor_is_measured_in_years(self):
        self.assertGreaterEqual(MINIMUM_RETENTION_YEARS, 1)


if __name__ == "__main__":
    unittest.main()
