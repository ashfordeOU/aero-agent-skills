#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.2 marking-provisions leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_hybrid_marking_provisions.py
"""

import unittest

from q6005_hybrid_marking_provisions_logic import (
    ACCEPTANCE_INDEX,
    CHARACTER_WIDTH_RATIO,
    EXPOSURE_PERMANENCE_DEMAND,
    LINE_PITCH_RATIO,
    MANDATORY_PROVISION_ELEMENTS,
    MARKING_LOCATIONS,
    MARKING_MARGIN_MM,
    MARKING_METHOD_PERMANENCE,
    MARKING_TOLERANCE,
    METHOD_SURFACES,
    PROVISION_ELEMENT_WEIGHTS,
    PROVISION_STATE_CREDIT,
    VERDICTS,
    assess_marking_provisions,
    assess_placement,
    assess_provision,
    face_dimensions,
    marking_fits_face,
    marking_provision_index,
    method_permanence_grade,
    method_suits_surface,
    normalize_provision,
    permanence_is_sufficient,
    provision_element_weight,
    provision_state_credit,
    required_marking_footprint_mm,
    required_permanence_grade,
    traceability_findings,
)

SPARE_PROVISION = "remarking-and-rework-rule"
MARKING_LINES = ["HYB-1234-01", "2614 A", "SN 00042"]


def scheme(**overrides):
    """A laser mark on the ceramic body of a unit with a welded lid."""
    record = {
        "method": "laser-engraving",
        "surface": "ceramic-body",
        "location": "package-body",
        "lid_is_removable": False,
        "character_height_mm": 1.0,
        "marking_lines": list(MARKING_LINES),
    }
    record.update(overrides)
    return record


def face(**overrides):
    """A package body face with room for the mark."""
    record = {"width_mm": 10.0, "height_mm": 8.0}
    record.update(overrides)
    return record


def traceability(**overrides):
    """A mark bound to the lot record, the serial register and the container."""
    record = {
        "lot_record_linked": True,
        "serial_register_maintained": True,
        "container_record_maintained": True,
    }
    record.update(overrides)
    return record


def defined_provisions(**states):
    """Every provision element defined, with named exceptions."""
    provisions = []
    for name in sorted(PROVISION_ELEMENT_WEIGHTS):
        entry = {"element": name, "state": "defined"}
        if name in states:
            entry["state"] = states[name]
        provisions.append(entry)
    return provisions


def run(**overrides):
    """Grade one marking scheme."""
    case = {
        "product_id": "HYB-1234",
        "scheme": scheme(),
        "exposures": ["solvent-cleaning"],
        "body_face": face(),
        "traceability": traceability(),
        "provisions": defined_provisions(),
    }
    case.update(overrides)
    return assess_marking_provisions(**case)


class PermanenceTests(unittest.TestCase):
    def test_an_engraved_mark_outranks_an_adhesive_label(self):
        self.assertGreater(
            method_permanence_grade("laser-engraving"),
            method_permanence_grade("adhesive-label"),
        )

    def test_an_unknown_marking_method_is_rejected(self):
        with self.assertRaises(ValueError):
            method_permanence_grade("felt-tip-pen")

    def test_solvent_cleaning_demands_the_highest_permanence(self):
        self.assertEqual(
            EXPOSURE_PERMANENCE_DEMAND["solvent-cleaning"],
            max(EXPOSURE_PERMANENCE_DEMAND.values()),
        )

    def test_the_hardest_exposure_ahead_sets_the_demand(self):
        self.assertEqual(
            required_permanence_grade(["handling-and-storage-only", "solvent-cleaning"]),
            EXPOSURE_PERMANENCE_DEMAND["solvent-cleaning"],
        )

    def test_an_undeclared_downstream_process_is_rejected(self):
        with self.assertRaises(ValueError):
            required_permanence_grade([])

    def test_an_unknown_downstream_exposure_is_rejected(self):
        with self.assertRaises(ValueError):
            required_permanence_grade(["dropped-in-a-drawer"])

    def test_a_label_does_not_survive_solvent_cleaning(self):
        self.assertFalse(permanence_is_sufficient("adhesive-label", ["solvent-cleaning"]))

    def test_a_label_is_sufficient_when_nothing_but_handling_follows(self):
        self.assertTrue(
            permanence_is_sufficient("adhesive-label", ["handling-and-storage-only"])
        )

    def test_a_method_meeting_the_demand_exactly_is_sufficient(self):
        self.assertTrue(permanence_is_sufficient("cured-epoxy-ink-stamp", ["conformal-coating"]))


class SurfaceTests(unittest.TestCase):
    def test_every_method_names_at_least_one_surface(self):
        for method in MARKING_METHOD_PERMANENCE:
            self.assertGreaterEqual(len(METHOD_SURFACES[method]), 1, method)

    def test_engraving_a_polymer_body_is_refused(self):
        self.assertFalse(method_suits_surface("mechanical-engraving", "polymer-body"))

    def test_a_laser_mark_on_a_ceramic_body_is_allowed(self):
        self.assertTrue(method_suits_surface("laser-engraving", "ceramic-body"))

    def test_an_unknown_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            method_suits_surface("laser-engraving", "wooden-lid")

    def test_an_unknown_method_is_rejected_by_the_surface_check(self):
        with self.assertRaises(ValueError):
            method_suits_surface("chisel", "metal-lid")


class FootprintTests(unittest.TestCase):
    def test_the_footprint_grows_with_the_longest_line(self):
        narrow = required_marking_footprint_mm(["AB"], 1.0)
        wide = required_marking_footprint_mm(["ABCDEFGH"], 1.0)
        self.assertGreater(wide["width_mm"], narrow["width_mm"])

    def test_the_footprint_grows_with_the_line_count(self):
        one = required_marking_footprint_mm(["AB"], 1.0)
        three = required_marking_footprint_mm(["AB", "CD", "EF"], 1.0)
        self.assertGreater(three["height_mm"], one["height_mm"])

    def test_the_width_follows_the_published_character_geometry(self):
        footprint = required_marking_footprint_mm(["ABCDE"], 2.0)
        self.assertAlmostEqual(
            footprint["width_mm"],
            5 * 2.0 * CHARACTER_WIDTH_RATIO + 2.0 * MARKING_MARGIN_MM,
            places=9,
        )

    def test_the_height_follows_the_published_line_pitch(self):
        footprint = required_marking_footprint_mm(["AB", "CD"], 1.5)
        self.assertAlmostEqual(
            footprint["height_mm"],
            2 * 1.5 * LINE_PITCH_RATIO + 2.0 * MARKING_MARGIN_MM,
            places=9,
        )

    def test_a_mark_with_no_lines_is_rejected(self):
        with self.assertRaises(ValueError):
            required_marking_footprint_mm([], 1.0)

    def test_a_blank_marking_line_is_rejected(self):
        with self.assertRaises(ValueError):
            required_marking_footprint_mm(["HYB-1", "   "], 1.0)

    def test_a_non_positive_character_height_is_rejected(self):
        with self.assertRaises(ValueError):
            required_marking_footprint_mm(["HYB-1"], 0.0)

    def test_a_face_without_dimensions_is_rejected(self):
        with self.assertRaises(ValueError):
            face_dimensions({"width_mm": 4.0})

    def test_a_mark_inside_the_face_fits(self):
        result = marking_fits_face(MARKING_LINES, 1.0, face())
        self.assertTrue(result["fits"])
        self.assertEqual(result["findings"], [])

    def test_a_face_exactly_the_size_of_the_footprint_still_fits(self):
        footprint = required_marking_footprint_mm(MARKING_LINES, 1.0)
        exact = {"width_mm": footprint["width_mm"], "height_mm": footprint["height_mm"]}
        self.assertTrue(marking_fits_face(MARKING_LINES, 1.0, exact)["fits"])

    def test_a_narrow_face_names_the_short_dimension(self):
        result = marking_fits_face(MARKING_LINES, 1.0, face(width_mm=3.0))
        self.assertFalse(result["fits"])
        self.assertIn("face-too-narrow-for-mark", result["findings"])

    def test_a_short_face_names_the_short_dimension(self):
        result = marking_fits_face(MARKING_LINES, 1.0, face(height_mm=2.0))
        self.assertIn("face-too-short-for-mark", result["findings"])


class PlacementTests(unittest.TestCase):
    def test_a_body_mark_raises_nothing(self):
        self.assertEqual(assess_placement("package-body", False, True), [])

    def test_a_mark_on_a_removable_lid_identifies_the_lid(self):
        self.assertIn(
            "identification-on-removable-lid",
            assess_placement("package-lid", True, True),
        )

    def test_a_mark_on_a_welded_lid_is_not_a_finding(self):
        self.assertEqual(assess_placement("package-lid", False, True), [])

    def test_container_identification_is_refused_when_the_body_had_room(self):
        self.assertIn(
            "body-marking-omitted-although-the-face-had-room",
            assess_placement("carrier-or-container-only", False, True),
        )

    def test_container_identification_is_open_to_a_unit_with_no_usable_face(self):
        self.assertEqual(assess_placement("carrier-or-container-only", False, False), [])

    def test_an_unknown_marking_location_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_placement("inside-the-package", False, True)

    def test_every_published_location_is_accepted(self):
        for location in MARKING_LOCATIONS:
            assess_placement(location, False, False)


class TraceabilityTests(unittest.TestCase):
    def test_a_fully_bound_mark_raises_nothing(self):
        self.assertEqual(traceability_findings(traceability(), "package-body"), [])

    def test_a_mark_with_no_lot_link_is_reported(self):
        self.assertIn(
            "mark-not-linked-to-the-lot-record",
            traceability_findings(traceability(lot_record_linked=False), "package-body"),
        )

    def test_a_mark_with_no_serial_register_is_reported(self):
        self.assertIn(
            "no-serial-register-behind-the-mark",
            traceability_findings(
                traceability(serial_register_maintained=False), "package-body"
            ),
        )

    def test_container_identification_without_a_container_record_is_reported(self):
        self.assertIn(
            "container-identification-without-a-container-record",
            traceability_findings(
                traceability(container_record_maintained=False), "carrier-or-container-only"
            ),
        )

    def test_a_missing_container_record_is_silent_for_a_body_mark(self):
        self.assertEqual(
            traceability_findings(
                traceability(container_record_maintained=False), "package-body"
            ),
            [],
        )

    def test_a_traceability_flag_that_is_not_a_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            traceability_findings(traceability(lot_record_linked="yes"), "package-body")


class ProvisionTests(unittest.TestCase):
    def test_every_mandatory_provision_carries_a_published_weight(self):
        for name in MANDATORY_PROVISION_ELEMENTS:
            self.assertIn(name, PROVISION_ELEMENT_WEIGHTS)

    def test_an_unknown_provision_element_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_element_weight("nice-font")

    def test_an_unknown_provision_state_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_state_credit("mostly-there")

    def test_a_provision_nobody_mentioned_defaults_to_not_defined(self):
        self.assertEqual(
            normalize_provision({"element": SPARE_PROVISION})["state"], "not-defined"
        )

    def test_a_defined_provision_earns_its_full_weight(self):
        record = assess_provision({"element": SPARE_PROVISION, "state": "defined"})
        self.assertAlmostEqual(
            record["weighted_credit"], PROVISION_ELEMENT_WEIGHTS[SPARE_PROVISION], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_a_missing_mandatory_provision_is_marked_missing(self):
        record = assess_provision({"element": "marking-permanence-demonstration"})
        self.assertTrue(record["mandatory_missing"])

    def test_a_deficient_mandatory_provision_is_flagged_separately(self):
        record = assess_provision(
            {"element": "marking-legibility-verification", "state": "deficient"}
        )
        self.assertTrue(record["mandatory_deficient"])
        self.assertFalse(record["mandatory_missing"])

    def test_a_fully_defined_scheme_reaches_a_full_index(self):
        records = [assess_provision(entry) for entry in defined_provisions()]
        self.assertAlmostEqual(marking_provision_index(records), 1.0, places=9)

    def test_an_empty_provision_set_is_rejected(self):
        with self.assertRaises(ValueError):
            marking_provision_index([])


class WholeSchemeTests(unittest.TestCase):
    def test_a_sound_scheme_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "marking-provisions-adequate")
        self.assertTrue(result["scheme_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["marking_provision_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_scheme_missing_a_mandatory_provision_is_incomplete(self):
        result = run(
            provisions=defined_provisions(**{"marking-method-qualification": "not-defined"})
        )
        self.assertEqual(result["verdict"], "marking-provisions-assessment-incomplete")

    def test_a_label_on_a_unit_facing_solvent_cleaning_is_inadequate(self):
        result = run(scheme=scheme(method="adhesive-label"))
        self.assertEqual(result["verdict"], "marking-provisions-inadequate")
        self.assertFalse(result["scheme_accepted"])

    def test_a_method_the_surface_will_not_take_is_inadequate(self):
        result = run(scheme=scheme(method="mechanical-engraving", surface="polymer-body"))
        self.assertEqual(result["verdict"], "marking-provisions-inadequate")
        self.assertFalse(result["method_suits_surface"])

    def test_a_mark_that_does_not_fit_the_body_is_inadequate(self):
        result = run(body_face=face(width_mm=2.0))
        self.assertEqual(result["verdict"], "marking-provisions-inadequate")
        self.assertIn(
            "face-too-narrow-for-mark", [f["finding"] for f in result["findings"]]
        )

    def test_a_mark_on_a_removable_lid_is_inadequate(self):
        result = run(scheme=scheme(location="package-lid", lid_is_removable=True))
        self.assertEqual(result["verdict"], "marking-provisions-inadequate")

    def test_a_welded_lid_mark_is_accepted_when_the_body_has_no_room(self):
        result = run(
            scheme=scheme(location="package-lid"), body_face=face(width_mm=2.0, height_mm=2.0)
        )
        self.assertEqual(result["verdict"], "marking-provisions-adequate")

    def test_container_identification_is_accepted_for_a_unit_with_no_usable_face(self):
        result = run(
            scheme=scheme(location="carrier-or-container-only"),
            body_face=face(width_mm=1.5, height_mm=1.5),
        )
        self.assertEqual(result["verdict"], "marking-provisions-adequate")

    def test_a_broken_lot_link_is_inadequate_however_permanent_the_mark(self):
        result = run(traceability=traceability(lot_record_linked=False))
        self.assertEqual(result["verdict"], "marking-provisions-inadequate")

    def test_an_observation_on_an_optional_provision_leaves_open_actions(self):
        result = run(
            provisions=defined_provisions(**{SPARE_PROVISION: "defined-with-observation"})
        )
        self.assertEqual(result["verdict"], "marking-provisions-adequate-with-open-actions")
        self.assertTrue(result["scheme_accepted"])

    def test_a_provision_nobody_listed_is_graded_as_not_defined(self):
        result = run(provisions=[{"element": SPARE_PROVISION, "state": "defined"}])
        states = {r["element"]: r["state"] for r in result["provision_records"]}
        self.assertEqual(states["marking-placement-definition"], "not-defined")
        self.assertEqual(len(result["provision_records"]), len(PROVISION_ELEMENT_WEIGHTS))

    def test_a_repeated_provision_element_is_rejected(self):
        provisions = defined_provisions() + [{"element": SPARE_PROVISION, "state": "defined"}]
        with self.assertRaises(ValueError):
            run(provisions=provisions)

    def test_a_blank_product_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(product_id="  ")

    def test_a_scheme_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            run(scheme=["laser-engraving"])

    def test_a_scheme_that_never_says_whether_the_lid_comes_off_is_rejected(self):
        broken = scheme()
        del broken["lid_is_removable"]
        with self.assertRaises(ValueError):
            run(scheme=broken)


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(MARKING_TOLERANCE, 1e-6)

    def test_the_provision_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(PROVISION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(PROVISION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_fully_defined_scheme(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)

    def test_the_line_pitch_leaves_room_between_the_lines(self):
        self.assertGreater(LINE_PITCH_RATIO, 1.0)

    def test_a_character_is_narrower_than_it_is_tall(self):
        self.assertLess(CHARACTER_WIDTH_RATIO, 1.0)


if __name__ == "__main__":
    unittest.main()
