"""
Offline deterministic unit tests for e1009_responsibility_logic.py.

Run: python3 test_e1009_responsibility.py
Expected output: OK (all tests pass).
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1009_responsibility_logic import (
    VALID_ENTRY_TYPES,
    CSDEntryError,
    validate_csd_entry,
    is_owner_assigned,
    check_responsibility,
    find_unassigned_entries,
    find_entries_by_owner,
    assign_owner,
    generate_responsibility_report,
)


def make_entry(name="CS_BODY", entry_type="coordinate_system", owner="Nav Team"):
    return {"name": name, "entry_type": entry_type, "owner": owner}


class TestValidateCSDEntry(unittest.TestCase):

    def test_valid_coordinate_system_entry_passes(self):
        entry = make_entry()
        result = validate_csd_entry(entry)
        self.assertIs(result, entry)

    def test_valid_transformation_entry_passes(self):
        entry = make_entry(entry_type="transformation", owner="GNC")
        result = validate_csd_entry(entry)
        self.assertIs(result, entry)

    def test_valid_entry_with_none_owner_passes(self):
        entry = make_entry(owner=None)
        result = validate_csd_entry(entry)
        self.assertIs(result, entry)

    def test_non_dict_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry("not a dict")

    def test_missing_name_key_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"entry_type": "coordinate_system", "owner": "A"})

    def test_missing_entry_type_key_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"name": "CS_A", "owner": "A"})

    def test_missing_owner_key_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"name": "CS_A", "entry_type": "coordinate_system"})

    def test_empty_name_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"name": "", "entry_type": "coordinate_system", "owner": "A"})

    def test_whitespace_name_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"name": "   ", "entry_type": "coordinate_system", "owner": "A"})

    def test_invalid_entry_type_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"name": "CS_A", "entry_type": "unknown_type", "owner": "A"})

    def test_integer_owner_raises(self):
        with self.assertRaises(CSDEntryError):
            validate_csd_entry({"name": "CS_A", "entry_type": "coordinate_system", "owner": 42})


class TestIsOwnerAssigned(unittest.TestCase):

    def test_string_owner_is_assigned(self):
        self.assertTrue(is_owner_assigned(make_entry(owner="Nav Team")))

    def test_none_owner_is_not_assigned(self):
        self.assertFalse(is_owner_assigned(make_entry(owner=None)))

    def test_empty_string_owner_is_not_assigned(self):
        self.assertFalse(is_owner_assigned(make_entry(owner="")))

    def test_whitespace_only_owner_is_not_assigned(self):
        self.assertFalse(is_owner_assigned(make_entry(owner="   \t  ")))

    def test_single_space_owner_is_not_assigned(self):
        self.assertFalse(is_owner_assigned(make_entry(owner=" ")))


class TestCheckResponsibility(unittest.TestCase):

    def test_all_assigned_returns_empty_issues(self):
        entries = [
            make_entry("CS_BODY", "coordinate_system", "Nav Team"),
            make_entry("T_BODY_TO_ECF", "transformation", "GNC"),
        ]
        issues = check_responsibility(entries)
        self.assertEqual(issues, [])

    def test_one_unassigned_entry_flagged(self):
        entries = [
            make_entry("CS_BODY", "coordinate_system", "Nav Team"),
            make_entry("CS_PAYLOAD", "coordinate_system", None),
        ]
        issues = check_responsibility(entries)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["entry_name"], "CS_PAYLOAD")
        self.assertIn("no owner assigned", issues[0]["issue"])

    def test_all_unassigned_all_flagged(self):
        entries = [
            make_entry("CS_A", owner=None),
            make_entry("CS_B", owner=""),
            make_entry("CS_C", owner="   "),
        ]
        issues = check_responsibility(entries)
        self.assertEqual(len(issues), 3)

    def test_duplicate_name_flagged(self):
        entries = [
            make_entry("CS_BODY", owner="Nav Team"),
            make_entry("CS_BODY", owner="GNC"),
        ]
        issues = check_responsibility(entries)
        self.assertEqual(len(issues), 1)
        self.assertIn("duplicate name", issues[0]["issue"])

    def test_empty_entry_list_returns_no_issues(self):
        self.assertEqual(check_responsibility([]), [])

    def test_structurally_invalid_entry_flagged(self):
        entries = [{"name": "CS_A", "entry_type": "bad_type", "owner": "X"}]
        issues = check_responsibility(entries)
        self.assertEqual(len(issues), 1)
        self.assertIn("structural validation failure", issues[0]["issue"])


class TestFindUnassignedEntries(unittest.TestCase):

    def test_returns_only_unassigned(self):
        entries = [
            make_entry("CS_A", owner="Nav Team"),
            make_entry("CS_B", owner=None),
            make_entry("CS_C", owner="GNC"),
            make_entry("CS_D", owner=""),
        ]
        unassigned = find_unassigned_entries(entries)
        names = [e["name"] for e in unassigned]
        self.assertIn("CS_B", names)
        self.assertIn("CS_D", names)
        self.assertNotIn("CS_A", names)
        self.assertNotIn("CS_C", names)

    def test_all_assigned_returns_empty(self):
        entries = [make_entry("CS_A", owner="X"), make_entry("CS_B", owner="Y")]
        self.assertEqual(find_unassigned_entries(entries), [])

    def test_does_not_mutate_input(self):
        entries = [make_entry("CS_A", owner=None)]
        original_len = len(entries)
        find_unassigned_entries(entries)
        self.assertEqual(len(entries), original_len)


class TestFindEntriesByOwner(unittest.TestCase):

    def test_returns_correct_entries(self):
        entries = [
            make_entry("CS_A", owner="Nav Team"),
            make_entry("CS_B", owner="GNC"),
            make_entry("T_AB", entry_type="transformation", owner="Nav Team"),
        ]
        result = find_entries_by_owner(entries, "Nav Team")
        names = [e["name"] for e in result]
        self.assertIn("CS_A", names)
        self.assertIn("T_AB", names)
        self.assertNotIn("CS_B", names)

    def test_strip_normalised_match(self):
        entries = [make_entry("CS_A", owner="Nav Team")]
        result = find_entries_by_owner(entries, "  Nav Team  ")
        self.assertEqual(len(result), 1)

    def test_no_match_returns_empty(self):
        entries = [make_entry("CS_A", owner="Nav Team")]
        result = find_entries_by_owner(entries, "Unknown Owner")
        self.assertEqual(result, [])

    def test_empty_owner_arg_raises(self):
        with self.assertRaises(ValueError):
            find_entries_by_owner([], "")

    def test_whitespace_owner_arg_raises(self):
        with self.assertRaises(ValueError):
            find_entries_by_owner([], "   ")


class TestAssignOwner(unittest.TestCase):

    def test_returns_new_entry_with_owner(self):
        original = make_entry("CS_A", owner=None)
        updated = assign_owner(original, "Nav Team")
        self.assertEqual(updated["owner"], "Nav Team")

    def test_does_not_mutate_original(self):
        original = make_entry("CS_A", owner=None)
        assign_owner(original, "Nav Team")
        self.assertIsNone(original["owner"])

    def test_returned_entry_preserves_other_fields(self):
        original = make_entry("CS_A", "transformation", None)
        updated = assign_owner(original, "GNC")
        self.assertEqual(updated["name"], "CS_A")
        self.assertEqual(updated["entry_type"], "transformation")

    def test_empty_owner_raises(self):
        original = make_entry("CS_A", owner=None)
        with self.assertRaises(CSDEntryError):
            assign_owner(original, "")

    def test_whitespace_owner_raises(self):
        original = make_entry("CS_A", owner=None)
        with self.assertRaises(CSDEntryError):
            assign_owner(original, "   ")


class TestGenerateResponsibilityReport(unittest.TestCase):

    def test_fully_assigned_csd_is_compliant(self):
        entries = [
            make_entry("CS_BODY", "coordinate_system", "Nav Team"),
            make_entry("CS_ECF", "coordinate_system", "Nav Team"),
            make_entry("T_BODY_ECF", "transformation", "GNC"),
        ]
        report = generate_responsibility_report(entries)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["assigned"], 3)
        self.assertEqual(report["unassigned"], 0)
        self.assertEqual(report["issues"], [])

    def test_partially_assigned_csd_is_not_compliant(self):
        entries = [
            make_entry("CS_BODY", owner="Nav Team"),
            make_entry("CS_ECF", owner=None),
        ]
        report = generate_responsibility_report(entries)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["unassigned"], 1)
        self.assertEqual(len(report["issues"]), 1)

    def test_owners_dict_groups_entries_by_owner(self):
        entries = [
            make_entry("CS_A", owner="Nav Team"),
            make_entry("CS_B", owner="GNC"),
            make_entry("T_AB", entry_type="transformation", owner="Nav Team"),
        ]
        report = generate_responsibility_report(entries)
        self.assertIn("Nav Team", report["owners"])
        self.assertIn("GNC", report["owners"])
        self.assertEqual(sorted(report["owners"]["Nav Team"]), ["CS_A", "T_AB"])
        self.assertEqual(report["owners"]["GNC"], ["CS_B"])

    def test_empty_csd_returns_compliant_report(self):
        report = generate_responsibility_report([])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["owners"], {})

    def test_duplicate_name_makes_report_non_compliant(self):
        entries = [
            make_entry("CS_BODY", owner="Nav Team"),
            make_entry("CS_BODY", owner="GNC"),
        ]
        report = generate_responsibility_report(entries)
        self.assertFalse(report["compliant"])

    def test_valid_entry_types_set_is_correct(self):
        self.assertIn("coordinate_system", VALID_ENTRY_TYPES)
        self.assertIn("transformation", VALID_ENTRY_TYPES)
        self.assertEqual(len(VALID_ENTRY_TYPES), 2)


if __name__ == "__main__":
    unittest.main()
