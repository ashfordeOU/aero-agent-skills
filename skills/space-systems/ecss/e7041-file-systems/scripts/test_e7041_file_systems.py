"""Contract test for the file-systems leaf (stdlib unittest)."""

import unittest

from e7041_file_systems_logic import (
    DEFAULT_MAX_NAME_OCTETS,
    FINDING_CASE_INSENSITIVE,
    FINDING_DEPTH_CONTRADICTS_KIND,
    FINDING_PATH_CAP_BELOW_NAME_CAP,
    FINDING_PATH_CAP_UNREACHABLE_DEPTH,
    FINDING_SEPARATOR_IN_CHARSET,
    KIND_FLAT,
    KIND_HIERARCHICAL,
    OBJECT_FILE,
    OBJECT_REPOSITORY,
    REJECTED_CHARSET,
    REJECTED_DEPTH,
    REJECTED_NAME_OCTETS,
    REJECTED_PATH_OCTETS,
    REJECTED_SUB_REPOSITORY,
    RESOLVED,
    assess_file_system,
    audit_declaration,
    canonical_name,
    effective_max_depth,
    join_path,
    names_collide,
    resolve_object_identifier,
    split_path,
    supports_sub_repositories,
    validate_declaration,
    validate_name,
)


def hierarchical(**kw):
    declaration = {"kind": KIND_HIERARCHICAL, "max_depth": 4}
    declaration.update(kw)
    return declaration


def flat(**kw):
    declaration = {"kind": KIND_FLAT, "max_depth": 1}
    declaration.update(kw)
    return declaration


class TestDeclarationValidation(unittest.TestCase):
    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration({"kind": "networked"})

    def test_a_multi_character_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(hierarchical(separator="::"))

    def test_a_control_character_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(hierarchical(separator="\t"))

    def test_a_zero_max_depth_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(hierarchical(max_depth=0))

    def test_a_boolean_octet_cap_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(hierarchical(max_name_octets=True))

    def test_an_empty_charset_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(hierarchical(permitted_name_characters=""))

    def test_a_non_boolean_case_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(hierarchical(case_sensitive_names="yes"))

    def test_defaults_are_applied(self):
        decl = validate_declaration({"kind": KIND_HIERARCHICAL})
        self.assertEqual(decl["max_name_octets"], DEFAULT_MAX_NAME_OCTETS)
        self.assertTrue(decl["case_sensitive_names"])


class TestKindAndDepth(unittest.TestCase):
    def test_a_hierarchical_system_supports_sub_repositories(self):
        self.assertTrue(supports_sub_repositories(hierarchical()))

    def test_a_flat_system_does_not(self):
        self.assertFalse(supports_sub_repositories(flat()))

    def test_a_flat_systems_effective_depth_is_one(self):
        self.assertEqual(effective_max_depth(flat(max_depth=6)), 1)

    def test_a_hierarchical_systems_effective_depth_is_the_declared_one(self):
        self.assertEqual(effective_max_depth(hierarchical(max_depth=5)), 5)


class TestDeclarationAudit(unittest.TestCase):
    def test_a_coherent_declaration_has_no_findings(self):
        audit = audit_declaration(hierarchical())
        self.assertTrue(audit["coherent"])
        self.assertEqual(audit["finding_count"], 0)

    def test_flat_with_a_depth_above_one_contradicts_itself(self):
        audit = audit_declaration(flat(max_depth=3))
        self.assertIn(FINDING_DEPTH_CONTRADICTS_KIND, audit["findings"])

    def test_hierarchical_with_a_depth_of_one_contradicts_itself(self):
        audit = audit_declaration(hierarchical(max_depth=1))
        self.assertIn(FINDING_DEPTH_CONTRADICTS_KIND, audit["findings"])

    def test_a_separator_inside_the_charset_is_a_finding(self):
        audit = audit_declaration(
            hierarchical(permitted_name_characters="ABC/", separator="/")
        )
        self.assertIn(FINDING_SEPARATOR_IN_CHARSET, audit["findings"])

    def test_a_path_cap_below_the_name_cap_is_a_finding(self):
        audit = audit_declaration(hierarchical(max_name_octets=64, max_path_octets=32))
        self.assertIn(FINDING_PATH_CAP_BELOW_NAME_CAP, audit["findings"])

    def test_a_depth_unreachable_within_the_path_cap_is_a_finding(self):
        audit = audit_declaration(
            hierarchical(max_depth=8, max_name_octets=1, max_path_octets=4)
        )
        self.assertIn(FINDING_PATH_CAP_UNREACHABLE_DEPTH, audit["findings"])

    def test_a_depth_exactly_reachable_within_the_path_cap_is_clean(self):
        audit = audit_declaration(
            hierarchical(max_depth=4, max_name_octets=1, max_path_octets=7)
        )
        self.assertNotIn(FINDING_PATH_CAP_UNREACHABLE_DEPTH, audit["findings"])

    def test_case_insensitive_names_are_a_finding(self):
        audit = audit_declaration(hierarchical(case_sensitive_names=False))
        self.assertIn(FINDING_CASE_INSENSITIVE, audit["findings"])


class TestNaming(unittest.TestCase):
    def test_a_name_holding_the_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_name(hierarchical(), "logs/archive")

    def test_a_relative_marker_name_raises(self):
        with self.assertRaises(ValueError):
            validate_name(hierarchical(), "..")

    def test_a_name_with_a_control_character_raises(self):
        with self.assertRaises(ValueError):
            validate_name(hierarchical(), "EVT\n001")

    def test_case_sensitive_names_do_not_collide(self):
        self.assertFalse(names_collide(hierarchical(), "Logs", "LOGS"))

    def test_case_insensitive_names_collide(self):
        self.assertTrue(
            names_collide(hierarchical(case_sensitive_names=False), "Logs", "LOGS")
        )

    def test_the_canonical_form_folds_case_only_when_declared(self):
        self.assertEqual(canonical_name(hierarchical(), "Logs"), "Logs")
        self.assertEqual(
            canonical_name(hierarchical(case_sensitive_names=False), "Logs"), "LOGS"
        )

    def test_a_path_with_an_empty_inner_segment_raises(self):
        with self.assertRaises(ValueError):
            split_path(hierarchical(), "mem1//logs")

    def test_split_and_join_round_trip_through_the_declared_separator(self):
        decl = hierarchical(separator=".")
        self.assertEqual(split_path(decl, "mem1.logs"), ["mem1", "logs"])
        self.assertEqual(join_path(decl, ["mem1", "logs"]), "mem1.logs")

    def test_joining_an_empty_segment_list_raises(self):
        with self.assertRaises(ValueError):
            join_path(hierarchical(), [])


class TestObjectIdentifiers(unittest.TestCase):
    def test_a_repository_resolves_without_a_file_name(self):
        result = resolve_object_identifier(hierarchical(), "mem1/logs")
        self.assertEqual(result["outcome"], RESOLVED)
        self.assertEqual(result["object_type"], OBJECT_REPOSITORY)
        self.assertIsNone(result["identifier"]["file_name"])

    def test_a_file_is_addressed_by_path_and_name_together(self):
        result = resolve_object_identifier(hierarchical(), "mem1/logs", "EVT-001.DAT")
        self.assertEqual(result["object_type"], OBJECT_FILE)
        self.assertEqual(result["identifier"]["repository_path"], "mem1/logs")
        self.assertEqual(result["identifier"]["file_name"], "EVT-001.DAT")

    def test_a_flat_system_rejects_a_nested_path(self):
        result = resolve_object_identifier(flat(), "mem1/logs", "EVT-001.DAT")
        self.assertEqual(result["outcome"], REJECTED_SUB_REPOSITORY)

    def test_a_flat_system_accepts_a_single_segment_path(self):
        result = resolve_object_identifier(flat(), "mem1", "EVT-001.DAT")
        self.assertEqual(result["outcome"], RESOLVED)

    def test_a_path_deeper_than_declared_is_rejected(self):
        result = resolve_object_identifier(
            hierarchical(max_depth=2), "mem1/logs/archive"
        )
        self.assertEqual(result["outcome"], REJECTED_DEPTH)
        self.assertEqual(result["depth"], 3)

    def test_a_path_exactly_at_the_declared_depth_resolves(self):
        result = resolve_object_identifier(hierarchical(max_depth=3), "mem1/logs/archive")
        self.assertEqual(result["outcome"], RESOLVED)

    def test_an_over_long_name_is_rejected(self):
        result = resolve_object_identifier(
            hierarchical(max_name_octets=4), "mem1", "EVT-001.DAT"
        )
        self.assertEqual(result["outcome"], REJECTED_NAME_OCTETS)

    def test_a_name_exactly_at_the_octet_cap_resolves(self):
        result = resolve_object_identifier(hierarchical(max_name_octets=4), "mem1", "A.DA")
        self.assertEqual(result["outcome"], RESOLVED)

    def test_an_over_long_path_is_rejected(self):
        result = resolve_object_identifier(hierarchical(max_path_octets=6), "mem1/logs")
        self.assertEqual(result["outcome"], REJECTED_PATH_OCTETS)

    def test_a_name_outside_the_declared_charset_is_rejected(self):
        result = resolve_object_identifier(
            hierarchical(permitted_name_characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-."),
            "mem1",
            "EVT-001.DAT",
        )
        self.assertEqual(result["outcome"], REJECTED_CHARSET)

    def test_an_octet_cap_counts_octets_not_characters(self):
        result = resolve_object_identifier(hierarchical(max_name_octets=3), "mem1", "éé")
        self.assertEqual(result["outcome"], REJECTED_NAME_OCTETS)

    def test_the_five_rejection_reasons_are_distinct(self):
        reasons = {
            REJECTED_SUB_REPOSITORY,
            REJECTED_DEPTH,
            REJECTED_NAME_OCTETS,
            REJECTED_PATH_OCTETS,
            REJECTED_CHARSET,
        }
        self.assertEqual(len(reasons), 5)


class TestAssessment(unittest.TestCase):
    def test_a_case_insensitive_system_reports_aliased_objects(self):
        result = assess_file_system(
            hierarchical(case_sensitive_names=False),
            [
                {"repository_path": "mem1", "file_name": "Report.DAT"},
                {"repository_path": "mem1", "file_name": "REPORT.dat"},
            ],
        )
        self.assertEqual(result["resolved_count"], 2)
        self.assertEqual(result["distinct_object_count"], 1)
        self.assertEqual(result["aliased_object_count"], 1)

    def test_a_case_sensitive_system_keeps_the_two_apart(self):
        result = assess_file_system(
            hierarchical(),
            [
                {"repository_path": "mem1", "file_name": "Report.DAT"},
                {"repository_path": "mem1", "file_name": "REPORT.dat"},
            ],
        )
        self.assertEqual(result["distinct_object_count"], 2)
        self.assertEqual(result["aliased_object_count"], 0)

    def test_rejections_are_grouped_by_reason(self):
        result = assess_file_system(
            flat(),
            [
                {"repository_path": "mem1", "file_name": "A.DAT"},
                {"repository_path": "mem1/logs", "file_name": "B.DAT"},
                {"repository_path": "mem1/logs/archive", "file_name": "C.DAT"},
            ],
        )
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["rejected_count"], 2)
        self.assertEqual(result["rejections_by_reason"][REJECTED_SUB_REPOSITORY], 2)
        self.assertFalse(result["all_resolved"])

    def test_the_audit_travels_with_the_assessment(self):
        result = assess_file_system(flat(max_depth=3), [])
        self.assertIn(FINDING_DEPTH_CONTRADICTS_KIND, result["audit"]["findings"])
        self.assertTrue(result["all_resolved"])

    def test_objects_must_be_a_list(self):
        with self.assertRaises(ValueError):
            assess_file_system(hierarchical(), {"repository_path": "mem1"})


if __name__ == "__main__":
    unittest.main()
