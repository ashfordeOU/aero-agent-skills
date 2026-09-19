#!/usr/bin/env python3
"""Unit tests for the hermeticity scanner.

Every rule gets a case that must fire and a neighbouring case that must
not. A scanner that only ever says "clean" is indistinguishable from one
that works, so the negative cases carry as much weight as the positives.

Run: python3 -m unittest discover -s tools/determinism -p 'test_*.py'
(unittest writes its OK line on stderr; capture both streams.)
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hermeticity  # noqa: E402


def rules_hit(text, **kwargs):
    return set(f.rule for f in hermeticity.scan_bytes(text, **kwargs))


class TestPatternRules(unittest.TestCase):

    def test_every_rule_has_a_case_that_fires(self):
        cases = {
            "timestamp-iso8601": "built at 2026-09-19T11:02:33 by the gate",
            "timestamp-date": "corpus wave 2026-09-19 merged",
            "timestamp-ctime": "Fri Sep 19 11:02:33 stamp",
            "timestamp-rfc2822": "Fri, 19 Sep 2026 in the header",
            "timestamp-epoch": "started 1758280953 done",
            "abs-path-posix": "read /var/lib/thing/data.bin",
            "abs-path-windows": r"read C:\\builds\\out.bin",
            "build-id-hex": "commit 9f3a71c2b40 recorded",
            "uuid": "run 123e4567-e89b-12d3-a456-426614174000 done",
            "hostname-suffix": "resolved on buildbox-7.local today",
            "pid": "worker pid=48213 exited",
            "tempdir-token": "/var/folders/q1/abcdefgh1234/T/x",
            "locale-decimal-comma": "score 17,5 recorded",
            "locale-digit-group-space": "total 4\u00a0472 operations",
            "locale-month-name": "Stand: 19. Dezember",
            "python-container-repr": "tags dict_keys(['a', 'b'])",
        }
        declared = set(r["name"] for r in hermeticity.PATTERN_RULES)
        self.assertEqual(declared, set(cases),
                         "a pattern rule has no test case (or vice versa)")
        for rule, text in sorted(cases.items()):
            with self.subTest(rule=rule):
                self.assertIn(rule, rules_hit(text, rules=hermeticity.PATTERN_RULES),
                              "rule %s did not fire on %r" % (rule, text))

    def test_a_clean_verdict_line_produces_no_findings(self):
        clean = (
            "PASS gate5-hit1: w52-e10-changes-nc-1 "
            "top1=space-systems/ecss/e10-changes-nc score=19.0 "
            "expected=space-systems/ecss/e10-changes-nc\n"
        )
        self.assertEqual(
            hermeticity.scan_bytes(clean, rules=hermeticity.PATTERN_RULES), [])

    def test_hex_word_without_a_digit_is_not_a_build_id(self):
        # "effaced" and "defaced" are made only of a-f; a length rule alone
        # would report ordinary English as a commit id.
        for word in ("effaced", "defaced", "facade beefed"):
            with self.subTest(word=word):
                self.assertNotIn("build-id-hex", rules_hit(
                    word, rules=hermeticity.PATTERN_RULES))
        self.assertIn("build-id-hex", rules_hit(
            "0abcdef1", rules=hermeticity.PATTERN_RULES))

    def test_digits_inside_a_real_number_are_not_a_build_id(self):
        # Both of these are live text in the corpus and both were reported
        # as commit ids by the first version of this rule.
        for text in ("edges at the -6.020599913 dB midpoint",
                     "gravitational parameter 3.986004418e14 m^3/s^2",
                     "tolerance 0.00012345678 m"):
            with self.subTest(text=text):
                self.assertNotIn("build-id-hex", rules_hit(
                    text, rules=hermeticity.PATTERN_RULES))

    def test_an_object_id_in_a_path_is_still_reported(self):
        self.assertIn("build-id-hex", rules_hit(
            "objects/9f3a71c2b40", rules=hermeticity.PATTERN_RULES))

    def test_epoch_rule_ignores_numbers_outside_clock_range(self):
        self.assertNotIn("timestamp-epoch", rules_hit(
            "part number 4000000001 shipped", rules=hermeticity.PATTERN_RULES))
        self.assertIn("timestamp-epoch", rules_hit(
            "stamp 1758280953", rules=hermeticity.PATTERN_RULES))

    def test_relative_path_is_not_an_absolute_path(self):
        self.assertNotIn("abs-path-posix", rules_hit(
            "skills/space-systems/ecss/e10-changes-nc",
            rules=hermeticity.PATTERN_RULES))

    def test_score_with_a_decimal_point_is_not_flagged_as_locale_comma(self):
        self.assertNotIn("locale-decimal-comma", rules_hit(
            "score=19.0", rules=hermeticity.PATTERN_RULES))


class TestLiteralRules(unittest.TestCase):

    def test_host_and_account_literals_fire(self):
        findings = hermeticity.scan_bytes(
            "wrote by buildmaster on node-17.example",
            hostname="node-17.example", username="buildmaster",
        )
        names = set(f.rule for f in findings)
        self.assertIn("literal-hostname", names)
        self.assertIn("literal-hostname-short", names)
        self.assertIn("literal-username", names)

    def test_short_literals_are_ignored(self):
        # A two-character account name would match ordinary prose.
        rules = hermeticity.literal_rules(hostname=None, username="ab")
        self.assertEqual(rules, [])

    def test_extra_literals_are_searched(self):
        findings = hermeticity.scan_bytes(
            "output under /scratch/run-9981/out",
            extra_literals=("/scratch/run-9981",),
        )
        self.assertIn("literal-env", set(f.rule for f in findings))


class TestFindingGeometry(unittest.TestCase):

    def test_offset_and_line_are_reported(self):
        text = "line one\nline two\nstamp 2026-09-19T00:00:00 here\n"
        findings = [f for f in hermeticity.scan_bytes(
            text, rules=hermeticity.PATTERN_RULES)
            if f.rule == "timestamp-iso8601"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].line, 3)
        self.assertEqual(text[findings[0].offset:findings[0].offset + 4], "2026")

    def test_findings_are_capped_per_rule(self):
        text = " ".join(["2026-09-19T00:00:0%d" % (i % 10) for i in range(50)])
        findings = hermeticity.scan_bytes(
            text, rules=hermeticity.PATTERN_RULES, max_per_rule=3)
        iso = [f for f in findings if f.rule == "timestamp-iso8601"]
        self.assertEqual(len(iso), 3)

    def test_non_utf8_bytes_scan_instead_of_raising(self):
        findings = hermeticity.scan_bytes(
            b"\xff\xfe stamp 2026-09-19T01:02:03",
            rules=hermeticity.PATTERN_RULES)
        self.assertTrue(findings)


class TestFileAndCli(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hermeticity-test-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_file(self):
        path = Path(self.tmp) / "artefact.txt"
        path.write_text("built 2026-09-19T10:00:00\n", encoding="utf-8")
        findings = hermeticity.scan_file(str(path), rules=hermeticity.PATTERN_RULES)
        self.assertTrue(any(f.rule == "timestamp-iso8601" for f in findings))

    def test_cli_exits_nonzero_on_a_high_severity_finding(self):
        dirty = Path(self.tmp) / "dirty.txt"
        dirty.write_text("stamp 2026-09-19T10:00:00\n", encoding="utf-8")
        clean = Path(self.tmp) / "clean.txt"
        clean.write_text("PASS x top1=a/b score=1.0 expected=a/b\n", encoding="utf-8")
        script = str(Path(__file__).resolve().parent / "hermeticity.py")
        env = dict(os.environ)
        env.pop("TMPDIR", None)

        proc = subprocess.run([sys.executable, script, "--no-literals", str(clean)],
                              capture_output=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"clean (0 findings)", proc.stdout)

        proc = subprocess.run([sys.executable, script, "--no-literals", str(dirty)],
                              capture_output=True, env=env)
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertIn(b"timestamp-iso8601", proc.stdout)



class ContainerReprVsJson(unittest.TestCase):
    """The rule must separate a Python repr from ordinary JSON.

    It did not: the double-quoted alternative matched the opening of any
    minified JSON object, so every JSON artefact scanned as a high finding
    and the scanner could not be attached to a gate.
    """

    RULE = "python-container-repr"

    def test_json_object_is_not_a_container_repr(self):
        self.assertNotIn(self.RULE, rules_hit('{"count":3,"name":"x"}'))

    def test_pretty_json_is_not_a_container_repr(self):
        self.assertNotIn(self.RULE, rules_hit('{\n  "name": "x"\n}'))

    def test_json_literals_are_not_python_literals(self):
        self.assertNotIn(self.RULE,
                         rules_hit('{"ok":true,"bad":false,"gone":null}'))

    def test_single_quoted_repr_is_still_caught(self):
        self.assertIn(self.RULE, rules_hit("{'name': 'x'}"))

    def test_double_quoted_key_with_python_value_is_caught(self):
        # Python reprs a key containing an apostrophe with double quotes.
        self.assertIn(self.RULE, rules_hit('{"it\'s": True}'))

    def test_dict_keys_view_is_still_caught(self):
        self.assertIn(self.RULE, rules_hit("tags dict_keys(['a', 'b'])"))

if __name__ == "__main__":
    unittest.main()
