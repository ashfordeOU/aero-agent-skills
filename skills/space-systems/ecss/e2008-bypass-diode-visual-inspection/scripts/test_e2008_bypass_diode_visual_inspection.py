#!/usr/bin/env python3
"""Contract test for the bypass diode visual examination (offline)."""

import copy
import unittest

from e2008_bypass_diode_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_DIODE_CRITERIA,
    DIODE_OBSERVATION_KINDS,
    EXAMINATION_INVALID,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    assess_observation,
    body_geometry,
    inspect_bypass_diode,
    inspect_bypass_diode_set,
    validate_diode_criteria,
)

BODY = body_geometry(3.0, 4.0)


def _diode(diode_id="BD-001", observations=None, **overrides):
    record = {
        "diode_id": diode_id,
        "string_id": "S1",
        "protected_cell_count": 4,
        "magnification": 20.0,
        "body_length_mm": 3.0,
        "body_width_mm": 4.0,
        "observations": copy.deepcopy(observations) if observations else [],
    }
    record.update(overrides)
    return record


def _crack(**overrides):
    observation = {
        "id": "O1",
        "kind": "body-crack",
        "extent_mm": 0.8,
        "through_body": False,
    }
    observation.update(overrides)
    return observation


def _separation(**overrides):
    observation = {
        "id": "O1",
        "kind": "body-separation",
        "separated_length_mm": 0.5,
        "bonded_length_mm": 4.0,
    }
    observation.update(overrides)
    return observation


def _mark(**overrides):
    observation = {"id": "O1", "kind": "unresolved-surface-mark", "length_mm": 0.05}
    observation.update(overrides)
    return observation


def _assembly(records, declared=None, assembly_id="PVA-01"):
    return {
        "assembly_id": assembly_id,
        "declared_diode_count": declared if declared is not None else len(records),
        "diodes": records,
    }


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_diode_criteria(DEFAULT_DIODE_CRITERIA), DEFAULT_DIODE_CRITERIA
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_criteria("default")

    def test_missing_magnification_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_CRITERIA)
        del broken["min_inspection_magnification"]
        with self.assertRaises(ValueError):
            validate_diode_criteria(broken)

    def test_non_boolean_crack_rule_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_CRITERIA)
        broken["crack_always_rejects"] = "yes"
        with self.assertRaises(ValueError):
            validate_diode_criteria(broken)

    def test_negative_unprotected_cell_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_CRITERIA)
        broken["max_unprotected_cells_per_string"] = -1
        with self.assertRaises(ValueError):
            validate_diode_criteria(broken)


class BodyGeometryTests(unittest.TestCase):
    def test_smallest_side_and_diagonal(self):
        body = body_geometry(3.0, 4.0)
        self.assertAlmostEqual(body["smallest_side_mm"], 3.0, places=9)
        self.assertAlmostEqual(body["diagonal_mm"], 5.0, places=9)
        self.assertAlmostEqual(body["footprint_mm2"], 12.0, places=9)

    def test_zero_side_rejected(self):
        with self.assertRaises(ValueError):
            body_geometry(0.0, 4.0)

    def test_implausibly_small_body_rejected(self):
        with self.assertRaises(ValueError):
            body_geometry(0.1, 4.0)

    def test_non_numeric_side_rejected(self):
        with self.assertRaises(ValueError):
            body_geometry("3 mm", 4.0)


class ObservationTests(unittest.TestCase):
    def test_every_kind_is_gradeable(self):
        self.assertEqual(len(DIODE_OBSERVATION_KINDS), 4)

    def test_body_crack_rejects(self):
        result = assess_observation(_crack(), BODY)
        self.assertEqual(result["disposition"], REJECT)
        self.assertAlmostEqual(result["severity_fraction"], 0.8 / 3.0, places=9)

    def test_through_body_crack_names_the_string_consequence(self):
        result = assess_observation(_crack(through_body=True), BODY)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("carry the string" in r for r in result["reasons"]))

    def test_crack_longer_than_the_body_diagonal_rejected(self):
        with self.assertRaises(ValueError):
            assess_observation(_crack(extent_mm=6.0), BODY)

    def test_crack_exactly_on_the_diagonal_is_graded(self):
        result = assess_observation(_crack(extent_mm=5.0), BODY)
        self.assertAlmostEqual(result["severity_fraction"], 5.0 / 3.0, places=9)

    def test_body_separation_reports_its_fraction(self):
        result = assess_observation(_separation(), BODY)
        self.assertEqual(result["disposition"], REJECT)
        self.assertAlmostEqual(result["severity_fraction"], 0.125, places=9)

    def test_terminal_interface_separation_rejects(self):
        result = assess_observation(
            _separation(kind="terminal-interface-separation"), BODY
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("terminal interface" in r for r in result["reasons"]))

    def test_separation_longer_than_the_bond_rejected(self):
        with self.assertRaises(ValueError):
            assess_observation(_separation(separated_length_mm=5.0), BODY)

    def test_full_separation_is_graded_at_one(self):
        result = assess_observation(_separation(separated_length_mm=4.0), BODY)
        self.assertAlmostEqual(result["severity_fraction"], 1.0, places=9)

    def test_unresolved_mark_refers_for_re_examination(self):
        result = assess_observation(_mark(), BODY)
        self.assertEqual(result["disposition"], REFER)
        self.assertTrue(result["needs_re_examination"])

    def test_long_unresolved_mark_still_refers_rather_than_guessing(self):
        result = assess_observation(_mark(length_mm=0.6), BODY)
        self.assertEqual(result["disposition"], REFER)
        self.assertTrue(any("higher magnification" in r for r in result["reasons"]))

    def test_unknown_observation_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_observation({"id": "O1", "kind": "burn-mark"}, BODY)

    def test_missing_required_field_rejected(self):
        with self.assertRaises(ValueError):
            assess_observation({"id": "O1", "kind": "body-crack", "extent_mm": 0.4}, BODY)

    def test_body_argument_must_come_from_body_geometry(self):
        with self.assertRaises(ValueError):
            assess_observation(_crack(), {"length_mm": 3.0})

    def test_relaxed_criteria_downgrade_a_crack_to_review(self):
        relaxed = copy.deepcopy(DEFAULT_DIODE_CRITERIA)
        relaxed["crack_always_rejects"] = False
        result = assess_observation(_crack(), BODY, relaxed)
        self.assertEqual(result["disposition"], REFER)


class SingleDiodeTests(unittest.TestCase):
    def test_clean_diode_accepts(self):
        result = inspect_bypass_diode(_diode())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["magnification_adequate"])
        self.assertAlmostEqual(result["max_severity_fraction"], 0.0, places=9)

    def test_magnification_exactly_on_the_minimum_is_adequate(self):
        result = inspect_bypass_diode(_diode(magnification=10.0))
        self.assertTrue(result["magnification_adequate"])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_clean_look_at_low_magnification_is_not_an_acceptance(self):
        result = inspect_bypass_diode(_diode(magnification=4.0))
        self.assertEqual(result["verdict"], EXAMINATION_INVALID)
        self.assertFalse(result["magnification_adequate"])

    def test_a_crack_seen_at_low_magnification_still_rejects(self):
        result = inspect_bypass_diode(
            _diode(observations=[_crack()], magnification=4.0)
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("still stands" in f for f in result["findings"]))

    def test_worst_observation_drives_the_diode_verdict(self):
        result = inspect_bypass_diode(
            _diode(observations=[_mark(), _crack(id="O2")])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(result["re_examination_required"])

    def test_duplicate_observation_id_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bypass_diode(_diode(observations=[_mark(), _mark()]))

    def test_diode_protecting_no_cells_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bypass_diode(_diode(protected_cell_count=0))

    def test_missing_string_id_rejected(self):
        record = _diode()
        del record["string_id"]
        with self.assertRaises(ValueError):
            inspect_bypass_diode(record)

    def test_missing_diode_id_rejected(self):
        record = _diode()
        del record["diode_id"]
        with self.assertRaises(ValueError):
            inspect_bypass_diode(record)

    def test_observations_not_a_list_rejected(self):
        record = _diode()
        record["observations"] = "one crack"
        with self.assertRaises(ValueError):
            inspect_bypass_diode(record)


class AssemblyRollupTests(unittest.TestCase):
    def test_clean_assembly_accepts(self):
        records = [_diode("BD-%03d" % n) for n in range(6)]
        result = inspect_bypass_diode_set(_assembly(records))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["unprotected_cells_by_string"], {})

    def test_rejected_diode_leaves_its_string_cells_unprotected(self):
        records = [_diode("BD-%03d" % n) for n in range(6)]
        records[2]["observations"] = [_crack(through_body=True)]
        records[2]["string_id"] = "S3"
        result = inspect_bypass_diode_set(_assembly(records))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["unprotected_cells_by_string"], {"S3": 4})
        self.assertEqual(result["strings_over_allowance"], ["S3"])
        self.assertEqual(result["not_accepted_ids"], ["BD-002"])

    def test_unprotected_cells_add_up_across_one_string(self):
        records = [_diode("BD-%03d" % n) for n in range(4)]
        for n in (0, 1):
            records[n]["observations"] = [_separation()]
        result = inspect_bypass_diode_set(_assembly(records))
        self.assertEqual(result["unprotected_cells_by_string"], {"S1": 8})

    def test_invalid_examination_also_counts_as_unestablished_protection(self):
        records = [_diode("BD-%03d" % n) for n in range(4)]
        records[1]["magnification"] = 3.0
        result = inspect_bypass_diode_set(_assembly(records))
        self.assertEqual(result["verdict"], EXAMINATION_INVALID)
        self.assertEqual(result["unprotected_cells_by_string"], {"S1": 4})

    def test_re_examination_ids_are_listed(self):
        records = [_diode("BD-%03d" % n) for n in range(4)]
        records[3]["observations"] = [_mark()]
        result = inspect_bypass_diode_set(_assembly(records))
        self.assertEqual(result["re_examination_ids"], ["BD-003"])
        self.assertEqual(result["verdict"], REFER)

    def test_short_record_set_leaves_the_assembly_open(self):
        records = [_diode("BD-%03d" % n) for n in range(4)]
        result = inspect_bypass_diode_set(_assembly(records, declared=6))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)

    def test_more_records_than_declared_rejected(self):
        records = [_diode("BD-%03d" % n) for n in range(5)]
        with self.assertRaises(ValueError):
            inspect_bypass_diode_set(_assembly(records, declared=4))

    def test_duplicate_diode_ids_rejected(self):
        records = [_diode("BD-001"), _diode("BD-001")]
        with self.assertRaises(ValueError):
            inspect_bypass_diode_set(_assembly(records))

    def test_non_integer_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bypass_diode_set(_assembly([_diode()], declared="six"))

    def test_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            inspect_bypass_diode_set("PVA-01")

    def test_disposition_counts_cover_every_diode(self):
        records = [_diode("BD-%03d" % n) for n in range(5)]
        records[0]["observations"] = [_crack()]
        records[1]["observations"] = [_mark()]
        result = inspect_bypass_diode_set(_assembly(records))
        self.assertEqual(result["disposition_counts"][REJECT], 1)
        self.assertEqual(result["disposition_counts"][REFER], 1)
        self.assertEqual(result["disposition_counts"][ACCEPT], 3)
        self.assertEqual(sum(result["disposition_counts"].values()), 5)


if __name__ == "__main__":
    unittest.main()
