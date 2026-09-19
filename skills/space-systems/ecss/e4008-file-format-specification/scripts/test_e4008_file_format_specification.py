"""Contract tests for the clause 5.7.2.1 exchange file format declaration."""

import unittest

from e4008_file_format_specification_logic import (
    FORMAT_IDENTIFIER,
    MAX_SUPPORTED_MINOR,
    MIN_SUPPORTED_MINOR,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    REQUIRED_KEYS,
    REQUIRED_SECTIONS,
    SUPPORTED_ENCODINGS,
    SUPPORTED_LINE_ENDINGS,
    SUPPORTED_MAJOR,
    assess_file_format,
    parse_declaration_block,
    parse_version,
    validate_sections,
    version_support,
)


def clean_text(**overrides):
    """A declaration block that satisfies the normative item."""
    fields = {
        "format": FORMAT_IDENTIFIER,
        "version": "2.1",
        "encoding": "utf-8",
        "line_ending": "lf",
        "sections": "header, catalogue, assembly, schedule",
    }
    fields.update(overrides)
    lines = ["#%format-begin"]
    for key in REQUIRED_KEYS:
        if fields.get(key) is not None:
            lines.append("%s: %s" % (key, fields[key]))
    lines.append("#%format-end")
    lines.append("header")
    return "\n".join(lines) + "\n"


class VersionTests(unittest.TestCase):
    def test_two_part_version_parsed(self):
        self.assertEqual(parse_version("2.3"), (2, 3))

    def test_three_part_version_rejected(self):
        with self.assertRaises(ValueError):
            parse_version("2.3.1")

    def test_non_numeric_part_rejected(self):
        with self.assertRaises(ValueError):
            parse_version("2.x")

    def test_zero_padded_part_rejected(self):
        with self.assertRaises(ValueError):
            parse_version("2.01")

    def test_blank_version_rejected(self):
        with self.assertRaises(ValueError):
            parse_version("   ")

    def test_non_string_version_rejected(self):
        with self.assertRaises(ValueError):
            parse_version(2.1)

    def test_supported_version_accepted(self):
        result = version_support("%d.%d" % (SUPPORTED_MAJOR, MIN_SUPPORTED_MINOR))
        self.assertTrue(result["supported"])

    def test_top_of_the_range_accepted(self):
        result = version_support("%d.%d" % (SUPPORTED_MAJOR, MAX_SUPPORTED_MINOR))
        self.assertTrue(result["supported"])

    def test_newer_minor_is_unsupported_but_forward_readable(self):
        result = version_support("%d.%d" % (SUPPORTED_MAJOR, MAX_SUPPORTED_MINOR + 1))
        self.assertFalse(result["supported"])
        self.assertTrue(result["forward_readable"])

    def test_other_major_is_not_forward_readable(self):
        result = version_support("%d.0" % (SUPPORTED_MAJOR + 1))
        self.assertFalse(result["supported"])
        self.assertFalse(result["forward_readable"])


class DeclarationBlockTests(unittest.TestCase):
    def test_clean_block_parses(self):
        parsed = parse_declaration_block(clean_text())
        self.assertEqual(parsed["block"]["format"], FORMAT_IDENTIFIER)
        self.assertEqual(parsed["repeated"], [])

    def test_leading_blank_lines_tolerated(self):
        parsed = parse_declaration_block("\n\n" + clean_text())
        self.assertIn("version", parsed["block"])

    def test_crlf_input_parses(self):
        parsed = parse_declaration_block(clean_text().replace("\n", "\r\n"))
        self.assertIn("encoding", parsed["block"])

    def test_comment_line_is_skipped(self):
        text = clean_text().replace("format:", "# a note\nformat:")
        parsed = parse_declaration_block(text)
        self.assertIn("format", parsed["block"])

    def test_repeated_key_is_reported(self):
        text = clean_text().replace("encoding: utf-8", "encoding: utf-8\nencoding: utf-16")
        parsed = parse_declaration_block(text)
        self.assertEqual(parsed["repeated"], ["encoding"])

    def test_file_not_opening_with_the_marker_rejected(self):
        with self.assertRaises(ValueError):
            parse_declaration_block("header\n" + clean_text())

    def test_unclosed_block_rejected(self):
        with self.assertRaises(ValueError):
            parse_declaration_block(clean_text().replace("#%format-end\n", ""))

    def test_line_without_a_separator_rejected(self):
        with self.assertRaises(ValueError):
            parse_declaration_block(clean_text().replace("encoding: utf-8", "encoding utf-8"))

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_declaration_block("   ")

    def test_non_string_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_declaration_block(["#%format-begin"])


class SectionTests(unittest.TestCase):
    def test_comma_separated_string_accepted(self):
        result = validate_sections("header, catalogue, assembly, schedule")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["declared"], list(REQUIRED_SECTIONS))

    def test_sequence_accepted(self):
        result = validate_sections(list(REQUIRED_SECTIONS))
        self.assertTrue(result["compliant"])

    def test_extra_section_is_allowed_after_the_required_ones(self):
        result = validate_sections(list(REQUIRED_SECTIONS) + ["annex"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["extra"], ["annex"])

    def test_missing_section_is_a_finding(self):
        result = validate_sections(["header", "catalogue", "assembly"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing"], ["schedule"])

    def test_repeated_section_is_a_finding(self):
        result = validate_sections(list(REQUIRED_SECTIONS) + ["header"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["repeated"], ["header"])

    def test_out_of_order_sections_are_a_finding(self):
        result = validate_sections(["catalogue", "header", "assembly", "schedule"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("orders them" in f for f in result["findings"]))

    def test_empty_section_list_is_a_finding(self):
        result = validate_sections([])
        self.assertFalse(result["compliant"])

    def test_non_sequence_sections_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(42)


class AssessmentTests(unittest.TestCase):
    def test_item_catalogue_has_one_entry(self):
        self.assertEqual(len(NORMATIVE_ITEMS), NORMATIVE_ITEM_COUNT)

    def test_clean_file_is_compliant(self):
        result = assess_file_format(clean_text())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_wrong_identifier_is_a_violation(self):
        result = assess_file_format(clean_text(format="some-other-format"))
        self.assertFalse(result["compliant"])
        self.assertIn("FF-01", result["violations"])

    def test_missing_key_is_a_violation(self):
        result = assess_file_format(clean_text(encoding=None))
        self.assertEqual(result["missing_keys"], ["encoding"])
        self.assertFalse(result["compliant"])

    def test_unsupported_encoding_is_a_violation(self):
        result = assess_file_format(clean_text(encoding="latin-1"))
        self.assertFalse(result["compliant"])

    def test_unsupported_line_ending_is_a_violation(self):
        result = assess_file_format(clean_text(line_ending="cr"))
        self.assertFalse(result["compliant"])

    def test_unsupported_version_is_a_violation(self):
        result = assess_file_format(clean_text(version="%d.0" % (SUPPORTED_MAJOR + 1)))
        self.assertFalse(result["compliant"])

    def test_malformed_version_is_a_violation_not_an_exception(self):
        result = assess_file_format(clean_text(version="two.one"))
        self.assertFalse(result["compliant"])

    def test_missing_section_is_a_violation(self):
        result = assess_file_format(clean_text(sections="header, catalogue, assembly"))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["sections"]["missing"], ["schedule"])

    def test_declaration_values_are_returned(self):
        result = assess_file_format(clean_text())
        self.assertEqual(sorted(result["declaration"]), sorted(REQUIRED_KEYS))

    def test_supported_sets_are_lower_case(self):
        for name in SUPPORTED_ENCODINGS + SUPPORTED_LINE_ENDINGS:
            self.assertEqual(name, name.lower())

    def test_case_is_folded_on_values(self):
        result = assess_file_format(clean_text(encoding="UTF-8", line_ending="LF"))
        self.assertTrue(result["compliant"])

    def test_broken_file_raises_rather_than_grading(self):
        with self.assertRaises(ValueError):
            assess_file_format("no declaration here\n")


if __name__ == "__main__":
    unittest.main()
