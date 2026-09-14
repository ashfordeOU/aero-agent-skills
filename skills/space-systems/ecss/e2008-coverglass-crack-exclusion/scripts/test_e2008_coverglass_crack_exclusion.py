#!/usr/bin/env python3
"""Contract test for the coverglass crack exclusion (offline)."""

import copy
import unittest

from e2008_coverglass_crack_exclusion_logic import (
    ACCEPT,
    CHIP_CLAUSE_ROUTE,
    COVERGLASS_ZONES,
    DEFAULT_CRACK_CRITERIA,
    FAMILY_CRACK,
    FAMILY_OTHER,
    FAMILY_UNRESOLVED,
    GLASS_CRACKED,
    GLASS_CRACK_FREE,
    GLASS_INCONCLUSIVE,
    REFER,
    REJECT,
    SURFACE_QUALITY_ROUTE,
    ZONE_CORNER,
    ZONE_EDGE,
    ZONE_SURFACE,
    assess_coverglass_crack_exclusion,
    assess_indication,
    categorize_indication,
    evidence_coverage,
    is_crack_family,
    normalize_kind,
    route_for_kind,
    validate_crack_criteria,
    validate_inspection_record,
)


def _indication(**overrides):
    indication = {
        "id": "I1",
        "kind": "scratch",
        "zone": ZONE_SURFACE,
        "length_mm": 0.4,
    }
    indication.update(overrides)
    return indication


def _record(indications=None, **overrides):
    record = {
        "coverglass_id": "CG-201",
        "inspector": "QA-14",
        "magnification_x": 20.0,
        "illumination_lux": 1000.0,
        "zones_inspected": list(COVERGLASS_ZONES),
        "indications": copy.deepcopy(indications) if indications else [],
    }
    record.update(overrides)
    return record


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_crack_criteria(DEFAULT_CRACK_CRITERIA), DEFAULT_CRACK_CRITERIA
        )

    def test_no_length_allowance_is_declared_anywhere_in_the_criteria(self):
        for key in DEFAULT_CRACK_CRITERIA:
            self.assertNotIn("length", key)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_crack_criteria("default")

    def test_empty_required_zones_rejected(self):
        broken = dict(DEFAULT_CRACK_CRITERIA, required_zones=[])
        with self.assertRaises(ValueError):
            validate_crack_criteria(broken)

    def test_unknown_required_zone_rejected(self):
        broken = dict(DEFAULT_CRACK_CRITERIA, required_zones=["coverglass-bevel"])
        with self.assertRaises(ValueError):
            validate_crack_criteria(broken)

    def test_repeated_required_zone_rejected(self):
        broken = dict(
            DEFAULT_CRACK_CRITERIA, required_zones=[ZONE_SURFACE, ZONE_SURFACE]
        )
        with self.assertRaises(ValueError):
            validate_crack_criteria(broken)

    def test_non_positive_magnification_floor_rejected(self):
        broken = dict(DEFAULT_CRACK_CRITERIA, min_magnification_x=0.0)
        with self.assertRaises(ValueError):
            validate_crack_criteria(broken)

    def test_non_integer_unresolved_allowance_rejected(self):
        broken = dict(DEFAULT_CRACK_CRITERIA, max_unresolved_indications=0.5)
        with self.assertRaises(ValueError):
            validate_crack_criteria(broken)


class CategorizationTests(unittest.TestCase):
    def test_a_crack_is_in_the_crack_family(self):
        self.assertEqual(categorize_indication("crack"), FAMILY_CRACK)

    def test_cracking_is_caught_under_its_other_names(self):
        for kind in ("fracture", "fissure", "hairline-crack", "star-crack"):
            self.assertEqual(categorize_indication(kind), FAMILY_CRACK)

    def test_a_chip_is_not_cracking(self):
        self.assertEqual(categorize_indication("chip"), FAMILY_OTHER)
        self.assertFalse(is_crack_family("chip"))

    def test_an_unrecognised_mark_is_left_open(self):
        self.assertEqual(categorize_indication("cloudy-patch"), FAMILY_UNRESOLVED)

    def test_kind_is_normalized_before_it_is_matched(self):
        self.assertEqual(normalize_kind("  Hairline Crack "), "hairline-crack")
        self.assertTrue(is_crack_family("  Hairline_Crack "))

    def test_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_indication("   ")

    def test_non_string_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_indication(7)

    def test_a_chip_is_routed_to_the_chip_clauses(self):
        self.assertEqual(route_for_kind("chip"), CHIP_CLAUSE_ROUTE)

    def test_a_scratch_is_routed_to_the_surface_quality_clauses(self):
        self.assertEqual(route_for_kind("scratch"), SURFACE_QUALITY_ROUTE)

    def test_an_unrecognised_mark_has_no_route(self):
        self.assertIsNone(route_for_kind("cloudy-patch"))


class RecordValidationTests(unittest.TestCase):
    def test_a_complete_record_validates(self):
        resolved = validate_inspection_record(_record())
        self.assertEqual(resolved["coverglass_id"], "CG-201")
        self.assertEqual(len(resolved["zones_inspected"]), 3)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record("CG-201 clean")

    def test_record_without_an_inspector_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(_record(inspector="  "))

    def test_record_without_a_coverglass_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(_record(coverglass_id=""))

    def test_non_positive_magnification_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(_record(magnification_x=0.0))

    def test_unknown_zone_in_the_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(_record(zones_inspected=["coverglass-back"]))

    def test_repeated_zone_in_the_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(
                _record(zones_inspected=[ZONE_SURFACE, ZONE_SURFACE])
            )

    def test_non_list_indications_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(_record(indications=_indication()))


class EvidenceTests(unittest.TestCase):
    def test_a_full_look_is_sufficient_evidence(self):
        coverage = evidence_coverage(_record())
        self.assertTrue(coverage["sufficient"])
        self.assertEqual(coverage["gaps"], [])
        self.assertEqual(coverage["zones_missing"], [])

    def test_a_missing_zone_leaves_the_evidence_short(self):
        coverage = evidence_coverage(
            _record(zones_inspected=[ZONE_SURFACE, ZONE_EDGE])
        )
        self.assertFalse(coverage["sufficient"])
        self.assertEqual(coverage["zones_missing"], [ZONE_CORNER])

    def test_magnification_exactly_at_the_floor_is_sufficient(self):
        coverage = evidence_coverage(_record(magnification_x=10.0))
        self.assertTrue(coverage["magnification_sufficient"])
        self.assertTrue(coverage["sufficient"])

    def test_magnification_below_the_floor_is_not_evidence_of_absence(self):
        coverage = evidence_coverage(_record(magnification_x=4.0))
        self.assertFalse(coverage["magnification_sufficient"])
        self.assertFalse(coverage["sufficient"])

    def test_poor_light_leaves_the_evidence_short(self):
        coverage = evidence_coverage(_record(illumination_lux=120.0))
        self.assertFalse(coverage["illumination_sufficient"])
        self.assertFalse(coverage["sufficient"])

    def test_each_shortfall_is_reported_separately(self):
        coverage = evidence_coverage(
            _record(
                magnification_x=4.0,
                illumination_lux=100.0,
                zones_inspected=[ZONE_SURFACE],
            )
        )
        self.assertEqual(len(coverage["gaps"]), 3)


class IndicationDispositionTests(unittest.TestCase):
    def test_a_non_crack_indication_is_accepted_and_routed_on(self):
        result = assess_indication(_indication())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["routed_to"], SURFACE_QUALITY_ROUTE)

    def test_a_surface_crack_rejects(self):
        result = assess_indication(_indication(kind="crack"))
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["family"], FAMILY_CRACK)

    def test_an_edge_crack_rejects(self):
        result = assess_indication(_indication(kind="crack", zone=ZONE_EDGE))
        self.assertEqual(result["disposition"], REJECT)

    def test_a_corner_crack_rejects(self):
        result = assess_indication(_indication(kind="crack", zone=ZONE_CORNER))
        self.assertEqual(result["disposition"], REJECT)

    def test_length_never_changes_a_crack_disposition(self):
        hairline = assess_indication(_indication(kind="crack", length_mm=0.02))
        across = assess_indication(_indication(kind="crack", length_mm=38.0))
        self.assertEqual(hairline["disposition"], across["disposition"])
        self.assertEqual(hairline["disposition"], REJECT)

    def test_a_crack_with_no_recorded_length_still_rejects(self):
        indication = _indication(kind="crack")
        del indication["length_mm"]
        result = assess_indication(indication)
        self.assertEqual(result["disposition"], REJECT)
        self.assertIsNone(result["length_mm"])

    def test_the_disposition_is_marked_as_not_taken_from_length(self):
        result = assess_indication(_indication(kind="crack"))
        self.assertFalse(result["graded_on_length"])

    def test_an_unresolved_indication_is_referred_not_accepted(self):
        result = assess_indication(_indication(kind="cloudy-patch"))
        self.assertEqual(result["disposition"], REFER)
        self.assertEqual(result["family"], FAMILY_UNRESOLVED)

    def test_unknown_zone_on_an_indication_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication(_indication(zone="coverglass-back"))

    def test_non_positive_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication(_indication(length_mm=0.0))

    def test_non_mapping_indication_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication("a crack")


class RecordRollupTests(unittest.TestCase):
    def test_a_full_clean_record_certifies_the_glass(self):
        result = assess_coverglass_crack_exclusion(_record())
        self.assertEqual(result["verdict"], GLASS_CRACK_FREE)
        self.assertTrue(result["evidence_sufficient"])
        self.assertEqual(result["findings"], [])

    def test_an_empty_finding_list_on_a_partial_look_is_inconclusive(self):
        result = assess_coverglass_crack_exclusion(
            _record(zones_inspected=[ZONE_SURFACE, ZONE_EDGE])
        )
        self.assertEqual(result["verdict"], GLASS_INCONCLUSIVE)
        self.assertEqual(result["crack_count"], 0)
        self.assertFalse(result["evidence_sufficient"])

    def test_an_empty_finding_list_under_thin_magnification_is_inconclusive(self):
        result = assess_coverglass_crack_exclusion(_record(magnification_x=3.0))
        self.assertEqual(result["verdict"], GLASS_INCONCLUSIVE)

    def test_one_crack_anywhere_rejects_the_whole_glass(self):
        result = assess_coverglass_crack_exclusion(
            _record([_indication(), _indication(id="I2", kind="crack")])
        )
        self.assertEqual(result["verdict"], GLASS_CRACKED)
        self.assertEqual(result["not_accepted_ids"], ["I2"])

    def test_a_crack_found_under_a_poor_look_is_still_a_rejection(self):
        result = assess_coverglass_crack_exclusion(
            _record(
                [_indication(id="I2", kind="crack")],
                magnification_x=3.0,
                zones_inspected=[ZONE_SURFACE],
            )
        )
        self.assertEqual(result["verdict"], GLASS_CRACKED)
        self.assertFalse(result["evidence_sufficient"])

    def test_cracked_zones_are_reported_for_the_nonconformance(self):
        result = assess_coverglass_crack_exclusion(
            _record(
                [
                    _indication(id="I1", kind="crack", zone=ZONE_EDGE),
                    _indication(id="I2", kind="fissure", zone=ZONE_CORNER),
                ]
            )
        )
        self.assertEqual(result["cracked_zones"], [ZONE_CORNER, ZONE_EDGE])
        self.assertEqual(result["crack_count"], 2)

    def test_the_longest_crack_is_recorded_but_does_not_decide_anything(self):
        result = assess_coverglass_crack_exclusion(
            _record(
                [
                    _indication(id="I1", kind="crack", length_mm=0.05),
                    _indication(id="I2", kind="crack", length_mm=12.0),
                ]
            )
        )
        self.assertAlmostEqual(result["longest_recorded_crack_mm"], 12.0, places=9)
        for indication in result["indications"]:
            self.assertEqual(indication["disposition"], REJECT)

    def test_an_unresolved_mark_blocks_certification(self):
        result = assess_coverglass_crack_exclusion(
            _record([_indication(id="I2", kind="cloudy-patch")])
        )
        self.assertEqual(result["verdict"], GLASS_INCONCLUSIVE)
        self.assertEqual(result["unresolved_count"], 1)

    def test_non_crack_indications_are_listed_for_their_own_clauses(self):
        result = assess_coverglass_crack_exclusion(
            _record(
                [
                    _indication(id="I1", kind="chip", zone=ZONE_EDGE),
                    _indication(id="I2", kind="scratch"),
                ]
            )
        )
        self.assertEqual(result["routed_elsewhere"], ["I1", "I2"])
        self.assertEqual(result["verdict"], GLASS_CRACK_FREE)

    def test_families_are_counted_for_the_record(self):
        result = assess_coverglass_crack_exclusion(
            _record(
                [
                    _indication(id="I1", kind="chip", zone=ZONE_EDGE),
                    _indication(id="I2", kind="crack"),
                    _indication(id="I3", kind="cloudy-patch"),
                ]
            )
        )
        self.assertEqual(result["indications_by_family"][FAMILY_CRACK], 1)
        self.assertEqual(result["indications_by_family"][FAMILY_OTHER], 1)
        self.assertEqual(result["indications_by_family"][FAMILY_UNRESOLVED], 1)

    def test_an_indication_in_an_uninspected_zone_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_crack_exclusion(
                _record(
                    [_indication(id="I1", zone=ZONE_CORNER)],
                    zones_inspected=[ZONE_SURFACE, ZONE_EDGE],
                )
            )

    def test_duplicate_indication_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_crack_exclusion(
                _record([_indication(id="D"), _indication(id="D", kind="chip")])
            )

    def test_input_is_not_mutated_by_the_screen(self):
        record = _record([_indication(), _indication(id="I2", kind="crack")])
        before = copy.deepcopy(record)
        assess_coverglass_crack_exclusion(record)
        self.assertEqual(record, before)


if __name__ == "__main__":
    unittest.main()
