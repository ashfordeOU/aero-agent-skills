#!/usr/bin/env python3
"""Tests for the clause-obligation binding and the obligations gate.

Every leaf here is built in a temporary directory. The locators are
syntactic test data: the gate never reads ECSS text, and neither do these
tests. Run with `python3 tools/obligations/test_obligations.py`; `make
obligations` runs it after the gate.

stdlib only; PyYAML is used, when importable, as an independent reader to
grade the stdlib one, and the cross-check says SKIP rather than PASS when it
is absent.
"""

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import obligation_binding as binding  # noqa: E402
import obligations_gate as gate  # noqa: E402

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on the host
    HAVE_YAML = False


def _load_by_path(name, rel):
    """Import a sibling reader by FILE PATH, under a name nobody else owns."""
    path = os.path.join(REPO, rel)
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


STD = "ECSS-E-ST-50C Rev.2"
CLAUSE = "5.6.11.8"

GOOD_BINDING = """clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.11.8
    items: [a, b]
    relation: implements
  - standard: ECSS-E-ST-50C Rev.2
    clause: "5.3"
    items: [c]
    relation: verifies
"""

GOOD_TABLE = """## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.11.8a | 1 |
| ECSS-E-ST-50C Rev.2 5.6.11.8b | 2 |
| ECSS-E-ST-50C Rev.2 5.3c | 3 |
"""

WORKFLOW = """## Workflow

1. Do the first thing.
2. Do the second thing.
3. Check the outcome.
"""


def leaf_text(name="fixture-leaf", binding_block="", table="",
              workflow=WORKFLOW, extra_body=""):
    return (
        "---\n"
        "name: %s\n"
        "description: \"Compute a fixture result. Use when testing the "
        "obligations gate. Trigger: fixture, obligations.\"\n"
        "license: Apache-2.0\n"
        "compliance: STANDARDS-REF\n"
        "standards:\n"
        "  - id: ecss\n"
        "    reference-only: true\n"
        "gated: false\n"
        "%s"
        "metadata:\n"
        "  version: 0.1.0\n"
        "  author: Aero Agent Skills\n"
        "---\n"
        "\n"
        "# Fixture leaf\n"
        "\n"
        "%s\n"
        "%s\n"
        "%s"
        "## Pitfalls\n"
        "\n"
        "- None.\n" % (name, binding_block, workflow, table, extra_body))


class TreeCase(unittest.TestCase):
    """A throwaway corpus with a skills/ tree."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="obligations-test-")
        os.makedirs(os.path.join(self.root, "skills"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, text, name="fixture-leaf", family="fam", pack="pack"):
        d = os.path.join(self.root, "skills", family, pack, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return "skills/%s/%s/%s/SKILL.md" % (family, pack, name)

    def grade(self):
        buf = io.StringIO()
        rc = gate.run(self.root, out=buf)
        return rc, buf.getvalue()

    def assertRefused(self, rel, subject, reason_part):
        rc, out = self.grade()
        self.assertEqual(rc, 1, out)
        wanted = "FAIL obligations: %s: %s" % (rel, subject)
        lines = [ln for ln in out.splitlines() if ln.startswith(wanted)]
        self.assertTrue(lines, "no refusal naming %r in:\n%s" % (wanted, out))
        self.assertTrue(any(reason_part in ln for ln in lines),
                        "refusal for %r does not say %r:\n%s"
                        % (subject, reason_part, "\n".join(lines)))
        return out


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------

class GateAcceptsWhatIsRight(TreeCase):
    """A denial gate needs a permissive baseline: prove it passes correct
    bindings, not only that it refuses broken ones."""

    def test_an_anchored_binding_passes_and_is_counted(self):
        self.put(leaf_text(binding_block=GOOD_BINDING, table=GOOD_TABLE))
        self.put(leaf_text(name="unbound-leaf"), name="unbound-leaf")
        rc, out = self.grade()
        self.assertEqual(rc, 0, out)
        self.assertIn("2 SKILL.md read; 1 declare a clause binding, 3 "
                      "declared item(s) anchored", out)

    def test_a_tree_with_no_binding_passes_and_says_so(self):
        self.put(leaf_text())
        rc, out = self.grade()
        self.assertEqual(rc, 0, out)
        self.assertIn("0 declare a clause binding", out)

    def test_doubled_item_letters_backticks_and_procedure_synonym(self):
        block = ("clauses:\n"
                 "- standard: 'ECSS-Q-ST-20C Rev.2 Corr.1'\n"
                 "  # a comment on its own line is accepted\n"
                 "  clause: 5.3.1.2\n"
                 "  items: [aa, bb]\n"
                 "  relation: verifies\n")
        table = ("## Obligations\n\n| Item | Step |\n|:---|---:|\n"
                 "| `ECSS-Q-ST-20C Rev.2 Corr.1 5.3.1.2aa` | 2 |\n"
                 "| ECSS-Q-ST-20C Rev.2 Corr.1 5.3.1.2bb | `1` |\n")
        wf = WORKFLOW.replace("## Workflow", "## Procedure")
        self.put(leaf_text(binding_block=block, table=table, workflow=wf))
        rc, out = self.grade()
        self.assertEqual(rc, 0, out)

    def test_headings_inside_a_code_fence_are_not_sections(self):
        fenced = ("```\n## Obligations\n| Item | Step |\n|---|---|\n"
                  "| ECSS-E-ST-50C Rev.2 9.9z | 9 |\n```\n\n")
        self.put(leaf_text(extra_body=fenced))
        rc, out = self.grade()
        self.assertEqual(rc, 0, out)

    def test_unbound_leaf_with_irregular_numbering_is_not_graded(self):
        wf = "## Workflow\n\n1. One.\n1. Again one.\n3. Three.\n"
        self.put(leaf_text(workflow=wf))
        rc, out = self.grade()
        self.assertEqual(rc, 0, out)


class GateRefusesWhatIsWrong(TreeCase):

    def test_declared_item_with_no_row(self):
        table = GOOD_TABLE.replace(
            "| ECSS-E-ST-50C Rev.2 5.6.11.8b | 2 |\n", "")
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.6.11.8b",
                           "no row in ## Obligations anchors it")

    def test_binding_with_no_obligations_section(self):
        rel = self.put(leaf_text(binding_block=GOOD_BINDING))
        out = self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.6.11.8a",
                                 "no ## Obligations section")
        self.assertIn("ECSS-E-ST-50C Rev.2 5.3c", out)

    def test_row_for_an_undeclared_item(self):
        table = GOOD_TABLE + "| ECSS-E-ST-50C Rev.2 5.6.11.8d | 3 |\n"
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.6.11.8d",
                           "does not declare")

    def test_row_on_an_unbound_leaf(self):
        rel = self.put(leaf_text(table=GOOD_TABLE))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.3c",
                           "declares no clauses")

    def test_row_pointing_at_a_step_that_does_not_exist(self):
        table = GOOD_TABLE.replace("5.3c | 3 |", "5.3c | 7 |")
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.3c",
                           "Step 7 does not exist")

    def test_row_when_the_leaf_has_no_procedure(self):
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=GOOD_TABLE,
                                 workflow="## Method\n\nProse only.\n"))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.6.11.8a",
                           "no numbered procedure")

    def test_bound_leaf_with_irregular_numbering(self):
        wf = "## Workflow\n\n1. One.\n1. Again one.\n3. Three.\n"
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=GOOD_TABLE,
                                 workflow=wf))
        self.assertRefused(rel, "## Workflow", "not 1..3")

    def test_malformed_binding_names_the_items_it_declares(self):
        block = GOOD_BINDING.replace("ECSS-E-ST-50C Rev.2\n    clause: 5.6",
                                     "ECSS-E-ST-50 Rev.2\n    clause: 5.6", 1)
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses[0] (ECSS-E-ST-50 Rev.2 5.6.11.8a, "
                           "ECSS-E-ST-50 Rev.2 5.6.11.8b)",
                           "not an ECSS designation with its issue letter")

    def test_spaced_revision_is_refused_with_the_fix(self):
        block = GOOD_BINDING.replace("ECSS-E-ST-50C Rev.2\n    clause: 5.6",
                                     "ECSS-E-ST-50C Rev. 2\n    clause: 5.6", 1)
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses[0]", "without a space")

    def test_reserved_relation(self):
        block = GOOD_BINDING.replace("relation: verifies",
                                     "relation: cites-clause")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        out = self.assertRefused(rel, "clauses[1] (ECSS-E-ST-50C Rev.2 5.3c)",
                                 "reserved and refused")
        # the reserved relation is the finding; its row is not re-reported
        self.assertNotIn("5.3c: Obligations row", out)

    def test_unknown_relation(self):
        block = GOOD_BINDING.replace("relation: verifies",
                                     "relation: satisfies")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses[1]", "unknown relation 'satisfies'")

    def test_item_declared_twice_across_entries(self):
        block = GOOD_BINDING.replace("items: [c]", "items: [c]") + (
            "  - standard: ECSS-E-ST-50C Rev.2\n"
            "    clause: 5.6.11.8\n"
            "    items: [b]\n"
            "    relation: verifies\n")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.6.11.8b",
                           "declared in clauses[0] and clauses[2]")

    def test_item_listed_twice_in_one_entry(self):
        block = GOOD_BINDING.replace("items: [a, b]", "items: [a, b, a]")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.6.11.8a",
                           "declared twice in clauses[0]")

    def test_row_given_twice(self):
        table = GOOD_TABLE + "| ECSS-E-ST-50C Rev.2 5.3c | 2 |\n"
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.3c",
                           "anchor the same item")

    def test_unquoted_two_part_clause_is_a_number(self):
        block = GOOD_BINDING.replace('clause: "5.3"', "clause: 5.30")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses[1]", "read as the number 5.3")

    def test_item_that_yaml_reads_as_a_boolean(self):
        block = GOOD_BINDING.replace("items: [c]", "items: [c, no]")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses[1]", "read as the boolean False")

    def test_item_that_is_not_an_item_letter(self):
        block = GOOD_BINDING.replace("items: [c]", "items: [c, ab]")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses[1]", "'ab' is not an item letter")

    def test_empty_items_and_missing_key_and_unknown_key(self):
        block = ("clauses:\n"
                 "  - standard: ECSS-E-ST-50C Rev.2\n"
                 "    clause: 5.6.11.8\n"
                 "    items: []\n"
                 "    note: extra\n")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        out = self.assertRefused(rel, "clauses[0]", "items is empty")
        self.assertIn("missing key(s) relation", out)
        self.assertIn("unknown key(s) note", out)

    def test_empty_clauses(self):
        rel = self.put(leaf_text(binding_block="clauses: []\n",
                                 table=GOOD_TABLE))
        self.assertRefused(rel, "clauses", "empty list")

    def test_inline_clauses_is_malformed(self):
        block = ("clauses: [{standard: ECSS-E-ST-50C Rev.2, clause: 5.3, "
                 "items: [c], relation: verifies}]\n")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        out = self.assertRefused(rel, "clauses", "malformed binding")
        # the unreadable binding is the finding, not every row after it
        self.assertNotIn("does not declare", out)

    def test_clauses_declared_twice_in_front_matter(self):
        rel = self.put(leaf_text(binding_block=GOOD_BINDING + GOOD_BINDING,
                                 table=GOOD_TABLE))
        self.assertRefused(rel, "clauses", "declared 2 times")

    def test_clauses_nested_under_another_key(self):
        block = "extra:\n  clauses:\n    - standard: x\n"
        rel = self.put(leaf_text(binding_block=block))
        self.assertRefused(rel, "clauses", "nested under another key")

    def test_block_style_items_is_refused_by_name(self):
        block = GOOD_BINDING.replace("items: [c]", "items:\n      - c")
        rel = self.put(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertRefused(rel, "clauses", "has no value on its line")

    def test_malformed_table_header_and_second_table(self):
        table = GOOD_TABLE.replace("| Item | Step |", "| Item | Where |")
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        self.assertRefused(rel, "## Obligations", "not | Item | Step |")
        table2 = GOOD_TABLE + "\nprose\n\n| Item | Step |\n|---|---|\n"
        self.put(leaf_text(binding_block=GOOD_BINDING, table=table2))
        self.assertRefused(rel, "## Obligations", "carries 2 tables")

    def test_malformed_row(self):
        table = GOOD_TABLE + "| 5.6.11.8c | 1 |\n| ECSS-E-ST-50C Rev.2 5.3c |\n"
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        out = self.assertRefused(rel, "5.6.11.8c", "is not '<standard> "
                                 "<clause><item>'")
        self.assertIn("has 1 cells, not 2", out)

    def test_step_that_is_not_a_number(self):
        table = GOOD_TABLE.replace("5.3c | 3 |", "5.3c | 3, 4 |")
        rel = self.put(leaf_text(binding_block=GOOD_BINDING, table=table))
        self.assertRefused(rel, "ECSS-E-ST-50C Rev.2 5.3c",
                           "is not the number of one step")

    def test_two_obligations_sections(self):
        rel = self.put(leaf_text(binding_block=GOOD_BINDING,
                                 table=GOOD_TABLE + "\n" + GOOD_TABLE))
        self.assertRefused(rel, "## Obligations", "appears 2 times")


class GateRunsOrSaysItCannot(unittest.TestCase):

    def test_no_skills_directory_is_exit_2_not_pass(self):
        root = tempfile.mkdtemp(prefix="obligations-empty-")
        try:
            buf = io.StringIO()
            self.assertEqual(gate.run(root, out=buf), 2)
            self.assertFalse([ln for ln in buf.getvalue().splitlines()
                              if ln.startswith("PASS")], buf.getvalue())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_real_tree_is_read(self):
        """The shipped tree grades without error (bindings are optional)."""
        buf = io.StringIO()
        rc = gate.run(REPO, out=buf)
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])
        self.assertRegex(buf.getvalue(), r"PASS obligations: \d+ SKILL\.md read")


# ---------------------------------------------------------------------------
# one binding, every reader
# ---------------------------------------------------------------------------

AGREEMENT_CASES = [
    GOOD_BINDING,
    "clauses:\n- standard: ECSS-E-ST-70-41C\n  clause: 6.3.1\n"
    "  items: [a, b, c]\n  relation: verifies\n",
    "clauses:\n  - standard: \"ECSS-Q-ST-80C Rev.2\"\n    clause: '5.2.4'\n"
    "    # a whole-line comment\n"
    "    items: ['a', \"b\"]\n    relation: implements\n",
    # the numeric traps: every reader must see a number, so the rule sees it
    "clauses:\n  - standard: ECSS-E-ST-10C Rev.1\n    clause: 5.10\n"
    "    items: [a]\n    relation: implements\n",
    "clauses:\n  - standard: ECSS-E-ST-10C Rev.1\n    clause: 4\n"
    "    items: [a, no]\n    relation: implements\n",
]


class EveryReaderReadsTheSameBinding(unittest.TestCase):

    def front(self, block):
        text = leaf_text(binding_block=block)
        front, _end = binding.front_matter_lines(text)
        return text, front

    def test_stdlib_reader_matches_pyyaml(self):
        if not HAVE_YAML:
            self.skipTest("PyYAML not importable: cross-check UNCHECKED")
        import yaml
        for block in AGREEMENT_CASES:
            _text, front = self.front(block)
            present, mine = binding.read_clauses(front)
            self.assertTrue(present)
            theirs = yaml.safe_load("\n".join(front))["clauses"]
            self.assertEqual(mine, theirs, block)
            self.assertEqual([type(v) for e in mine for v in e.values()],
                             [type(v) for e in theirs for v in e.values()])

    def test_the_other_front_matter_readers_agree(self):
        evidence = _load_by_path("aero_evidence_frontmatter",
                                 "tools/evidence/frontmatter.py")
        subset = _load_by_path("aero_export_yaml_subset",
                               "tools/export/yaml_subset.py")
        if evidence is None or subset is None:
            self.skipTest("a sibling reader is absent from this tree")
        for block in AGREEMENT_CASES[:3]:
            text, front = self.front(block)
            _p, mine = binding.read_clauses(front)
            self.assertEqual(evidence.parse(text)[0]["clauses"], mine, block)
            self.assertEqual(subset.read_frontmatter(text)[0]["clauses"],
                             mine, block)

    def test_shapes_the_reader_refuses_it_refuses_by_name(self):
        for block in ("clauses: [{standard: x}]\n",
                      "clauses:\n  - standard: x\n     clause: 5\n",
                      "clauses:\n  -\n    standard: x\n",
                      "clauses:\n  - standard: x\n    items: [a, [b]]\n",
                      "clauses:\n  - standard: x\n    standard: y\n",
                      # readers disagree about a trailing comment
                      "clauses:\n  - standard: x  # note\n"):
            _text, front = self.front(block)
            with self.assertRaises(binding.BindingSyntaxError, msg=block):
                binding.read_clauses(front)


# ---------------------------------------------------------------------------
# gate 1 reads the key through the same rule
# ---------------------------------------------------------------------------

class SpecLintValidatesTheKey(TreeCase):

    def lint(self, text):
        if not HAVE_YAML:
            self.skipTest("scripts/spec_lint.py needs PyYAML")
        rel = self.put(text)
        return subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts", "spec_lint.py"),
             os.path.join(self.root, rel)],
            capture_output=True, text=True)

    def test_a_valid_binding_lints_clean(self):
        r = self.lint(leaf_text(binding_block=GOOD_BINDING, table=GOOD_TABLE))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_leaf_without_the_key_lints_clean(self):
        r = self.lint(leaf_text())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_reserved_relation_fails_gate_1(self):
        block = GOOD_BINDING.replace("relation: verifies",
                                     "relation: cites-clause")
        r = self.lint(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("clauses[1] (ECSS-E-ST-50C Rev.2 5.3c): relation "
                      "'cites-clause' is reserved", r.stdout)

    def test_a_malformed_standard_fails_gate_1(self):
        block = GOOD_BINDING.replace("ECSS-E-ST-50C Rev.2\n    clause: 5.6",
                                     "E-ST-50C\n    clause: 5.6", 1)
        r = self.lint(leaf_text(binding_block=block, table=GOOD_TABLE))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not an ECSS designation", r.stdout)


if __name__ == "__main__":
    unittest.main()
