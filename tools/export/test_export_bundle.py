#!/usr/bin/env python3
"""Behaviour tests for the router evidence bundle. Standard library only.

    python3 -m unittest discover -s tools/export -p "test_*.py" -v

These run against small synthetic fixtures, not the 3,000-skill tree, so they
finish in well under a second and fail for one reason at a time. They cover
the three places where a quiet mistake would produce a confidently wrong
Hit@1 number: the YAML reader, the scoring, and the hashes that are supposed
to notice when the evidence changed.

unittest reports on stderr; capture both streams if you are scripting this.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import case_set
import reference_router
import run_hit1
import yaml_subset


def write(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def skill(name, description, tags, body, block_tags=False):
    if block_tags:
        tag_block = "\n".join("  - %s" % t for t in tags)
        tag_text = "  tags:\n" + tag_block
    else:
        tag_text = "  tags: [%s]" % ", ".join(tags)
    return ("---\n"
            "name: %s\n"
            "description: \"%s\"\n"
            "metadata:\n"
            "  domain: test\n"
            "%s\n"
            "  version: 0.1.0\n"
            "---\n\n%s\n" % (name, description, tag_text, body))


class TokenizerTests(unittest.TestCase):

    def test_lowercases_and_keeps_internal_hyphens(self):
        self.assertEqual(reference_router.tokenize("DO-178C Planning"),
                         ["do-178c", "planning"])

    def test_drops_stop_words(self):
        self.assertEqual(reference_router.tokenize("the plan of the item"),
                         ["plan", "item"])

    def test_punctuation_is_a_separator(self):
        self.assertEqual(reference_router.tokenize("margin/limit (15%)"),
                         ["margin", "limit", "15"])


class FrontMatterTests(unittest.TestCase):

    def test_inline_tag_list(self):
        front, body = yaml_subset.read_frontmatter(
            skill("alpha", "A description.", ["one", "two"], "Body text."))
        self.assertEqual(front["name"], "alpha")
        self.assertEqual(front["metadata"]["tags"], ["one", "two"])
        self.assertEqual(body.strip(), "Body text.")

    def test_block_tag_list(self):
        front, _ = yaml_subset.read_frontmatter(
            skill("beta", "A description.", ["one", "two"], "Body.",
                  block_tags=True))
        self.assertEqual(front["metadata"]["tags"], ["one", "two"])

    def test_block_sequence_at_the_same_column_as_its_key(self):
        front, _ = yaml_subset.read_frontmatter(
            "---\nname: gamma\nstandards:\n- id: ECSS\n  reference-only: true\n"
            "gated: false\n---\nbody\n")
        self.assertEqual(front["standards"], [{"id": "ECSS",
                                               "reference-only": True}])
        self.assertIs(front["gated"], False)

    def test_wrapped_double_quoted_scalar_folds_like_pyyaml(self):
        # A break folds to one space; a break escaped by a trailing backslash
        # folds to nothing, and the following "\ " restores the space.
        text = ('---\nname: delta\ndescription: "alpha beta\\\n  \\ gamma"\n'
                'metadata:\n  tags: [t]\n---\nbody\n')
        front, _ = yaml_subset.read_frontmatter(text)
        self.assertEqual(front["description"], "alpha beta gamma")

    def test_unwrapped_break_folds_to_a_single_space(self):
        text = ('---\nname: eps\ndescription: "alpha\n  beta"\n---\nbody\n')
        front, _ = yaml_subset.read_frontmatter(text)
        self.assertEqual(front["description"], "alpha beta")

    def test_single_quoted_scalar_and_quoted_keys(self):
        text = "---\n\"name\": 'zeta'\n'description': 'it''s fine'\n---\nbody\n"
        front, _ = yaml_subset.read_frontmatter(text)
        self.assertEqual(front["name"], "zeta")
        self.assertEqual(front["description"], "it's fine")

    def test_missing_front_matter_is_reported_not_guessed(self):
        front, body = yaml_subset.read_frontmatter("# just a heading\n")
        self.assertIsNone(front)
        self.assertEqual(body, "")


class TaskFileTests(unittest.TestCase):

    def test_reads_tasks_including_a_wrapped_query(self):
        text = ('# a comment\n'
                'tasks:\n'
                '  - id: t1\n'
                '    query: "size a battery for a\\\n  \\ 12U cubesat"\n'
                '    intent: "power"\n'
                '    expected_skill: "space/power"\n'
                '  - id: t2\n'
                '    query: "second"\n'
                '    intent: "x"\n'
                '    expected_skill: "space/other"\n')
        tasks = yaml_subset.read_tasks(text)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["query"], "size a battery for a 12U cubesat")
        self.assertEqual(tasks[1]["expected_skill"], "space/other")

    def test_a_file_without_tasks_raises(self):
        self.assertRaises(yaml_subset.YamlSubsetError,
                          yaml_subset.read_tasks, "other: 1\n")


class ScoringTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="aero-export-test-")
        write(os.path.join(self.root, "fam/pack/one/SKILL.md"),
              skill("one", "Battery sizing for a cubesat power budget.",
                    ["battery", "power"], "Eclipse depth of discharge."))
        write(os.path.join(self.root, "fam/pack/two/SKILL.md"),
              skill("two", "Thermal radiator sizing.",
                    ["thermal"], "Radiator area and battery mention."))
        self.index = reference_router.SkillIndex.from_tree(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_indexes_every_skill_file(self):
        self.assertEqual(len(self.index), 2)
        self.assertEqual([e.path for e in self.index.entries],
                         ["fam/pack/one", "fam/pack/two"])

    def test_tag_hit_outweighs_a_body_hit(self):
        # "battery eclipse" is not a phrase in either skill, so this isolates
        # the field weights. Skill one: tag 3.0 ("battery") + description 1.0
        # ("battery") + body 0.5 ("eclipse") = 4.5. Skill two mentions
        # "battery" in its body only: 0.5. A tagged skill beats a skill that
        # merely says the word.
        ranked = self.index.rank("battery eclipse", top_k=2)
        self.assertEqual(ranked[0], (4.5, "fam/pack/one"))
        self.assertEqual(ranked[1], (0.5, "fam/pack/two"))

    def test_phrase_bonus_applies_to_name_plus_description(self):
        score, path = self.index.top1("thermal radiator sizing")
        self.assertEqual(path, "fam/pack/two")
        # tag 3.0 ("thermal") + description 3.0 (all three tokens) +
        # body 0.5 ("radiator") + phrase 4.0 = 10.5.
        self.assertEqual(score, 10.5)

    def test_phrase_bonus_is_what_a_single_tag_word_query_wins_on(self):
        # The same query without the phrase bonus would score 4.0; the
        # verbatim occurrence of "battery" in name+description adds 4.0.
        score, path = self.index.top1("battery")
        self.assertEqual((score, path), (8.0, "fam/pack/one"))

    def test_ties_break_on_path_ascending(self):
        write(os.path.join(self.root, "fam/pack/aaa/SKILL.md"),
              skill("one", "Battery sizing for a cubesat power budget.",
                    ["battery", "power"], "Eclipse depth of discharge."))
        index = reference_router.SkillIndex.from_tree(self.root)
        _, path = index.top1("battery")
        self.assertEqual(path, "fam/pack/aaa")

    def test_index_digest_follows_the_body(self):
        before = self.index.digest()
        write(os.path.join(self.root, "fam/pack/two/SKILL.md"),
              skill("two", "Thermal radiator sizing.", ["thermal"],
                    "Radiator area and battery mention. One more sentence."))
        after = reference_router.SkillIndex.from_tree(self.root).digest()
        self.assertNotEqual(before, after)


class CaseSetTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="aero-export-cases-")
        self.path = os.path.join(self.root, "cases.jsonl")
        self.records = [
            {"uid": "s:b", "case_id": "b", "query": "second query",
             "expected_skill": "fam/pack/two", "intent": "why",
             "source": "eval/s.yaml", "gated": False},
            {"uid": "s:a", "case_id": "a", "query": "first query",
             "expected_skill": "fam/pack/one", "intent": "why",
             "source": "eval/s.yaml", "gated": False},
        ]

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_round_trip_is_sorted_by_uid(self):
        case_set.dump_cases(self.records, self.path)
        loaded = case_set.load_cases(self.path)
        self.assertEqual([r["uid"] for r in loaded], ["s:a", "s:b"])

    def test_content_digest_ignores_commentary(self):
        before = case_set.cases_digest(self.records)
        edited = [dict(r) for r in self.records]
        edited[0]["intent"] = "a different explanation"
        self.assertEqual(before, case_set.cases_digest(edited))

    def test_content_digest_follows_the_expected_answer(self):
        before = case_set.cases_digest(self.records)
        edited = [dict(r) for r in self.records]
        edited[0]["expected_skill"] = "fam/pack/elsewhere"
        self.assertNotEqual(before, case_set.cases_digest(edited))

    def test_duplicate_uids_are_rejected_on_load(self):
        case_set.dump_cases(self.records, self.path)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(self.records[0], sort_keys=True) + "\n")
        self.assertRaises(ValueError, case_set.load_cases, self.path)


class RunnerTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="aero-export-runner-")
        self.skills = os.path.join(self.root, "skills")
        write(os.path.join(self.skills, "fam/pack/one/SKILL.md"),
              skill("one", "Battery sizing for a cubesat power budget.",
                    ["battery", "power"], "Eclipse depth of discharge."))
        write(os.path.join(self.skills, "fam/pack/two/SKILL.md"),
              skill("two", "Thermal radiator sizing.",
                    ["thermal"], "Radiator area."))
        self.cases = os.path.join(self.root, "cases.jsonl")
        case_set.dump_cases([
            {"uid": "s:a", "case_id": "a", "query": "battery power budget",
             "expected_skill": "fam/pack/one", "intent": "", "source": "x",
             "gated": True},
            {"uid": "s:b", "case_id": "b", "query": "thermal radiator sizing",
             "expected_skill": "fam/pack/two", "intent": "", "source": "x",
             "gated": True},
        ], self.cases)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _run(self, extra=None):
        argv = ["--cases", self.cases, "--skills", self.skills,
                "--no-manifest", "--quiet"]
        return run_hit1.main(argv + (extra or []))

    def test_all_hits_exits_zero(self):
        self.assertEqual(self._run(), 0)

    def test_a_wrong_expected_answer_exits_non_zero(self):
        records = case_set.load_cases(self.cases)
        records[0]["expected_skill"] = "fam/pack/two"
        case_set.dump_cases(records, self.cases)
        self.assertEqual(self._run(), 1)

    def test_expect_flag_accepts_a_known_miss_count(self):
        records = case_set.load_cases(self.cases)
        records[0]["expected_skill"] = "fam/pack/two"
        case_set.dump_cases(records, self.cases)
        self.assertEqual(self._run(["--expect", "1"]), 0)

    def test_report_records_the_hashes_it_used(self):
        out = os.path.join(self.root, "report.json")
        self._run(["--json", out])
        with open(out, "r", encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertEqual(report["cases"], 2)
        self.assertEqual(report["hits"], 2)
        self.assertEqual(report["sha256_cases_content"],
                         case_set.cases_digest(case_set.load_cases(self.cases)))


if __name__ == "__main__":
    unittest.main()
