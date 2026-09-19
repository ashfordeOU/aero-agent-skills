"""Contract tests for the cleanliness verification-record traceability logic."""

import unittest

from q7001_cleanliness_verification_records_logic import (
    COVERAGE_TOLERANCE,
    MOLECULAR_LEVELS,
    PARTICULATE_LEVELS,
    acceptable_records,
    assess_verification_records,
    coverage_gaps,
    level_family,
    level_rank,
    meets_level,
    orphan_record_ids,
    record_findings,
    superseded_record_ids,
    traceable_coverage,
    validate_inventory,
    validate_record,
)

INVENTORY = [
    {"hardware_id": "OPT-BENCH", "surfaces": ["mirror-face", "baffle-interior"]},
    {"hardware_id": "RAD-PANEL", "surfaces": ["coated-face"]},
]


def _record(**overrides):
    record = {
        "record_id": "VR-001",
        "hardware_id": "OPT-BENCH",
        "surface": "mirror-face",
        "area_m2": 0.25,
        "method": "witness-plate-microscopy",
        "verified_level": "PCL-100",
        "required_level": "PCL-200",
        "instrument_id": "MIC-7",
        "calibration_valid_until_day": 40,
        "verification_day": 30,
        "operator": "cleanroom-tech-2",
    }
    record.update(overrides)
    return record


def _full_dossier(**overrides):
    dossier = {
        "inventory": INVENTORY,
        "records": [
            _record(),
            _record(
                record_id="VR-002",
                surface="baffle-interior",
                verified_level="NVR-A/2",
                required_level="NVR-A",
                method="solvent-rinse-gravimetry",
                instrument_id="BAL-3",
            ),
            _record(
                record_id="VR-003",
                hardware_id="RAD-PANEL",
                surface="coated-face",
                verified_level="PCL-300",
                required_level="PCL-500",
            ),
        ],
    }
    dossier.update(overrides)
    return dossier


class LevelLadderTests(unittest.TestCase):
    def test_particulate_family_recognised(self):
        self.assertEqual(level_family("PCL-100"), "particulate")

    def test_molecular_family_recognised(self):
        self.assertEqual(level_family("NVR-A/2"), "molecular")

    def test_cleanest_particulate_level_ranks_first(self):
        self.assertEqual(level_rank(PARTICULATE_LEVELS[0]), 0)

    def test_dirtiest_molecular_level_ranks_last(self):
        self.assertEqual(level_rank(MOLECULAR_LEVELS[-1]), len(MOLECULAR_LEVELS) - 1)

    def test_cleaner_than_required_meets_the_level(self):
        self.assertTrue(meets_level("PCL-100", "PCL-300"))

    def test_equal_level_meets_the_level(self):
        self.assertTrue(meets_level("NVR-A", "NVR-A"))

    def test_dirtier_than_required_fails_the_level(self):
        self.assertFalse(meets_level("PCL-500", "PCL-200"))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            level_rank("PCL-42")

    def test_mixed_families_cannot_be_graded(self):
        with self.assertRaises(ValueError):
            meets_level("PCL-100", "NVR-A")


class RecordValidationTests(unittest.TestCase):
    def test_valid_record_normalizes(self):
        normalized = validate_record(_record())
        self.assertEqual(normalized["hardware_id"], "OPT-BENCH")
        self.assertAlmostEqual(normalized["area_m2"], 0.25)

    def test_level_family_is_carried_on_the_record(self):
        self.assertEqual(validate_record(_record())["level_family"], "particulate")

    def test_missing_key_rejected(self):
        broken = _record()
        del broken["operator"]
        with self.assertRaises(ValueError):
            validate_record(broken)

    def test_blank_hardware_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(hardware_id="   "))

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(area_m2=0.0))

    def test_non_integer_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(verification_day=30.5))

    def test_negative_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(verification_day=-1))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(["VR-001"])


class InventoryTests(unittest.TestCase):
    def test_inventory_flattens_to_surface_pairs(self):
        self.assertEqual(len(validate_inventory(INVENTORY)), 3)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            validate_inventory([])

    def test_item_without_surfaces_rejected(self):
        with self.assertRaises(ValueError):
            validate_inventory([{"hardware_id": "X", "surfaces": []}])

    def test_duplicate_surface_rejected(self):
        with self.assertRaises(ValueError):
            validate_inventory([{"hardware_id": "X", "surfaces": ["a", "a"]}])


class RecordFindingTests(unittest.TestCase):
    def test_clean_record_has_no_findings(self):
        self.assertEqual(record_findings(_record()), [])

    def test_lapsed_calibration_is_a_finding(self):
        findings = record_findings(_record(calibration_valid_until_day=29))
        self.assertEqual(len(findings), 1)
        self.assertIn("calibration lapsed", findings[0])

    def test_calibration_expiring_on_the_measurement_day_is_still_valid(self):
        self.assertEqual(record_findings(_record(calibration_valid_until_day=30)), [])

    def test_level_shortfall_is_a_finding(self):
        findings = record_findings(_record(verified_level="PCL-500"))
        self.assertEqual(len(findings), 1)
        self.assertIn("was required", findings[0])

    def test_two_defects_give_two_findings(self):
        findings = record_findings(
            _record(verified_level="PCL-500", calibration_valid_until_day=1)
        )
        self.assertEqual(len(findings), 2)


class SupersessionTests(unittest.TestCase):
    def test_later_handling_supersedes_the_record(self):
        events = [{"hardware_id": "OPT-BENCH", "surface": "mirror-face", "day": 35}]
        self.assertEqual(superseded_record_ids([_record()], events), ["VR-001"])

    def test_handling_before_the_measurement_does_not_supersede(self):
        events = [{"hardware_id": "OPT-BENCH", "surface": "mirror-face", "day": 20}]
        self.assertEqual(superseded_record_ids([_record()], events), [])

    def test_handling_of_a_different_surface_does_not_supersede(self):
        events = [{"hardware_id": "OPT-BENCH", "surface": "baffle-interior", "day": 99}]
        self.assertEqual(superseded_record_ids([_record()], events), [])

    def test_malformed_handling_event_rejected(self):
        with self.assertRaises(ValueError):
            superseded_record_ids([_record()], [{"hardware_id": "OPT-BENCH"}])

    def test_superseded_record_is_not_acceptable_evidence(self):
        events = [{"hardware_id": "OPT-BENCH", "surface": "mirror-face", "day": 35}]
        self.assertEqual(acceptable_records([_record()], events), [])


class CoverageTests(unittest.TestCase):
    def test_full_dossier_covers_every_surface(self):
        self.assertEqual(coverage_gaps(INVENTORY, _full_dossier()["records"]), [])

    def test_missing_record_leaves_a_gap(self):
        records = _full_dossier()["records"][:2]
        self.assertEqual(coverage_gaps(INVENTORY, records), [("RAD-PANEL", "coated-face")])

    def test_orphan_record_is_reported(self):
        records = _full_dossier()["records"] + [
            _record(record_id="VR-009", hardware_id="GSE-CART", surface="tray")
        ]
        self.assertEqual(orphan_record_ids(INVENTORY, records), ["VR-009"])

    def test_orphan_record_does_not_close_a_gap(self):
        records = [_record(record_id="VR-009", hardware_id="GSE-CART", surface="tray")]
        self.assertEqual(len(coverage_gaps(INVENTORY, records)), 3)

    def test_full_coverage_is_one(self):
        coverage = traceable_coverage(INVENTORY, _full_dossier()["records"])
        self.assertAlmostEqual(coverage, 1.0, places=9)

    def test_partial_coverage_is_the_surface_fraction(self):
        coverage = traceable_coverage(INVENTORY, _full_dossier()["records"][:2])
        self.assertAlmostEqual(coverage, 2.0 / 3.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_complete_dossier_is_complete(self):
        result = assess_verification_records(_full_dossier())
        self.assertEqual(result["disposition"], "records-complete")
        self.assertEqual(result["findings"], [])

    def test_complete_dossier_reports_unit_coverage(self):
        result = assess_verification_records(_full_dossier())
        self.assertAlmostEqual(result["traceable_coverage"], 1.0, places=9)
        self.assertLessEqual(abs(result["traceable_coverage"] - 1.0), COVERAGE_TOLERANCE)

    def test_surface_count_is_reported(self):
        self.assertEqual(assess_verification_records(_full_dossier())["surface_count"], 3)

    def test_level_shortfall_makes_the_dossier_incomplete(self):
        dossier = _full_dossier()
        dossier["records"] = list(dossier["records"])
        dossier["records"][0] = _record(verified_level="PCL-500")
        result = assess_verification_records(dossier)
        self.assertEqual(result["disposition"], "records-incomplete")
        self.assertFalse(result["records"][0]["usable"])

    def test_superseded_record_opens_a_gap(self):
        dossier = _full_dossier(
            handling_events=[
                {"hardware_id": "RAD-PANEL", "surface": "coated-face", "day": 44}
            ]
        )
        result = assess_verification_records(dossier)
        self.assertIn(("RAD-PANEL", "coated-face"), result["gaps"])
        self.assertEqual(result["disposition"], "records-incomplete")

    def test_duplicate_record_id_rejected(self):
        dossier = _full_dossier()
        dossier["records"] = list(dossier["records"]) + [_record()]
        with self.assertRaises(ValueError):
            assess_verification_records(dossier)

    def test_missing_dossier_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_records({"inventory": INVENTORY})

    def test_non_mapping_dossier_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_records(["inventory"])

    def test_empty_record_set_gives_zero_coverage(self):
        result = assess_verification_records(_full_dossier(records=[]))
        self.assertAlmostEqual(result["traceable_coverage"], 0.0, places=9)
        self.assertEqual(len(result["gaps"]), 3)


if __name__ == "__main__":
    unittest.main()
