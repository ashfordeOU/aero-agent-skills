#!/usr/bin/env python3
"""Unit tests for the perturbation harness.

These exercise the harness, not the corpus: the pipeline under test here
is the tiny built-in `selftest` job, so the suite runs in seconds and does
not depend on the skills tree being present.

The important tests are the ones that would catch a harness that reports
green by accident: a byte comparator that cannot see a difference, a
corpus slicer that silently truncates a case, a variant that moved more
than one thing, and a run whose artefact files were created by the parent
(which would have made the umask axis measure nothing).

Run: python3 -m unittest discover -s tools/determinism -p 'test_*.py'
(unittest writes its OK line on stderr; capture both streams.)
"""

import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import perturb  # noqa: E402


CORPUS = """# a header comment
# mentioning tasks: in prose
meta:
  note: "not the task list"
tasks:
  - id: alpha-1
    query: "first query"
    intent: "first intent"
    expected_skill: "domain/pack/alpha"
# a wave comment sitting between two task blocks
  - id: beta-1
    query: "second query that wraps across a line because it is long\\
  \\ and continues here"
    expected_skill: "domain/pack/beta"
  - id: gamma-1
    query: "third query"
    expected_skill: "domain/pack/gamma"

  - id: delta-1
    query: "fourth query"
    expected_skill: "domain/pack/delta"
future_pins:
  - id: pinned-1
    query: "not a task"
"""


class TestSliceTasks(unittest.TestCase):

    def test_all_blocks_are_found_and_the_next_key_ends_the_list(self):
        text, selected, total = perturb.slice_tasks(CORPUS, None)
        self.assertEqual(total, 4)
        self.assertEqual(selected, 4)
        self.assertNotIn("future_pins", text)
        self.assertNotIn("pinned-1", text)
        self.assertTrue(text.startswith("tasks:\n"))

    def test_a_wrapped_double_quoted_scalar_stays_with_its_block(self):
        text, _, _ = perturb.slice_tasks(CORPUS, None)
        self.assertIn("and continues here", text)

    def test_stride_sample_is_spread_and_deterministic(self):
        first, selected, total = perturb.slice_tasks(CORPUS, 2)
        second, _, _ = perturb.slice_tasks(CORPUS, 2)
        self.assertEqual(first, second)
        self.assertEqual(selected, 2)
        self.assertEqual(total, 4)
        self.assertIn("alpha-1", first)
        self.assertIn("gamma-1", first)
        self.assertNotIn("beta-1", first)

    def test_a_sample_larger_than_the_corpus_returns_the_corpus(self):
        _, selected, total = perturb.slice_tasks(CORPUS, 999)
        self.assertEqual(selected, total)

    def test_a_truncated_block_is_rejected_not_silently_shipped(self):
        broken = "tasks:\n  - id: alpha-1\n    query: \"q\"\n"
        with self.assertRaises(ValueError):
            perturb.slice_tasks(broken, None)

    def test_a_corpus_without_a_tasks_key_is_rejected(self):
        with self.assertRaises(ValueError):
            perturb.slice_tasks("other:\n  - 1\n", None)


class TestFirstDiff(unittest.TestCase):

    def test_equal_inputs_report_no_difference(self):
        self.assertIsNone(perturb.first_diff(b"abc", b"abc"))

    def test_difference_at_the_first_byte(self):
        offset, left, right = perturb.first_diff(b"xbc", b"abc")
        self.assertEqual(offset, 0)
        self.assertIn("xbc", left)
        self.assertIn("abc", right)

    def test_difference_in_the_middle(self):
        left = b"score=19.0 expected=a"
        right = b"score=19,0 expected=a"
        offset, _, _ = perturb.first_diff(left, right)
        self.assertEqual(offset, 8)

    def test_a_pure_prefix_differs_at_the_shorter_length(self):
        offset, _, _ = perturb.first_diff(b"abc", b"abcdef")
        self.assertEqual(offset, 3)

    def test_empty_against_nonempty(self):
        self.assertIsNotNone(perturb.first_diff(b"", b"a"))


class TestExtractVerdict(unittest.TestCase):

    def test_only_per_case_lines_are_kept(self):
        stdout = (
            b"PASS gate5-hit1: a top1=x/y score=1.0 expected=x/y\n"
            b"FAIL gate5-hit1: b top1=x/z score=2.0 expected=x/q\n"
            b"PASS gate5-hit1: 2/2 tasks Hit@1 (deterministic offline router)\n"
        )
        kept = perturb.extract_verdict(stdout)
        self.assertEqual(len(kept.splitlines()), 2)
        self.assertNotIn(b"tasks Hit@1", kept)

    def test_order_is_preserved_so_ordering_leakage_stays_visible(self):
        stdout = (b"PASS gate5-hit1: b top1=x/z score=2.0 expected=x/z\n"
                  b"PASS gate5-hit1: a top1=x/y score=1.0 expected=x/y\n")
        kept = perturb.extract_verdict(stdout)
        self.assertTrue(kept.splitlines()[0].startswith(b"PASS gate5-hit1: b"))


class TestBaselineEnv(unittest.TestCase):

    def test_the_baseline_pins_the_variables_the_axes_move(self):
        env = perturb.baseline_env()
        for key in ("LC_ALL", "LANG", "TZ", "PYTHONHASHSEED", "TERM",
                    "COLUMNS", "USER", "SOURCE_DATE_EPOCH", "HOSTNAME",
                    "TMPDIR", "PYTHONUTF8"):
            self.assertIn(key, env, "%s is unpinned; it would be an unmeasured input" % key)

    def test_the_baseline_is_not_the_parent_environment(self):
        os.environ["AERO_DET_LEAK_PROBE"] = "1"
        try:
            self.assertNotIn("AERO_DET_LEAK_PROBE", perturb.baseline_env())
        finally:
            os.environ.pop("AERO_DET_LEAK_PROBE", None)


class TestVariantsMoveOneThing(unittest.TestCase):

    def test_a_plain_env_variant_moves_exactly_one_key(self):
        v = perturb.Variant("tz", "Europe/Berlin", env={"TZ": "Europe/Berlin"})
        moved, structural = perturb.check_one_thing_moved(v)
        self.assertEqual(moved, {"TZ"})
        self.assertEqual(structural, 0)

    def test_the_locale_axis_moves_its_declared_pair_and_nothing_else(self):
        v = perturb.Variant("locale", "de_DE.UTF-8",
                            env={"LC_ALL": "de_DE.UTF-8", "LANG": "de_DE.UTF-8"})
        moved, structural = perturb.check_one_thing_moved(v)
        self.assertEqual(moved, {"LC_ALL", "LANG"})
        self.assertEqual(structural, 0)

    def test_a_structural_variant_changes_no_environment_key(self):
        v = perturb.Variant("cwd", "root-/", cwd=Path("/"))
        moved, structural = perturb.check_one_thing_moved(v)
        self.assertEqual(moved, set())
        self.assertEqual(structural, 1)


def make_selftest_config(tmp):
    repo = Path(tmp) / "repo"
    (repo / "skills").mkdir(parents=True)
    (repo / "Makefile").write_text("all:\n", encoding="utf-8")
    corpus = Path(tmp) / "corpus.yaml"
    corpus.write_text("tasks: []\n", encoding="utf-8")
    return perturb.Config(
        repo=repo, run_root=Path(tmp), interpreter=sys.executable,
        corpus_path=corpus, skills_root=repo / "skills",
        pipeline=perturb.SelfTest(), tasks_selected=2, tasks_total=2,
        timeout=120,
    )


class TestRunOnce(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="perturb-test-")
        self.cfg = make_selftest_config(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_run_produces_every_artefact(self):
        res = perturb.run_once(self.cfg, perturb.Variant("baseline", "0"),
                               Path(self.tmp) / "r0")
        self.assertEqual(res.returncode, 0)
        for name in perturb.ARTEFACT_NAMES:
            self.assertIn(name, res.artefacts)
        self.assertEqual(len(res.artefacts["verdict.txt"].splitlines()), 2)
        self.assertEqual(res.artefacts["exit_code.txt"], b"0\n")

    def test_two_identical_runs_compare_identical(self):
        a = perturb.run_once(self.cfg, perturb.Variant("baseline", "0"),
                             Path(self.tmp) / "ra")
        b = perturb.run_once(self.cfg, perturb.Variant("repeat", "run-2"),
                             Path(self.tmp) / "rb")
        verdict, rows = perturb.compare(a, b)
        self.assertEqual(verdict, perturb.IDENTICAL)
        self.assertTrue(all(r["identical"] for r in rows))

    def test_a_real_difference_is_caught_and_located(self):
        a = perturb.run_once(self.cfg, perturb.Variant("baseline", "0"),
                             Path(self.tmp) / "rc")
        b = perturb.run_once(
            self.cfg,
            perturb.Variant("env", "echo", env={"AERO_DET_SELFTEST_ECHO": "moved"}),
            Path(self.tmp) / "rd")
        verdict, rows = perturb.compare(a, b)
        self.assertEqual(verdict, perturb.DIFFERS)
        bad = [r for r in rows if not r["identical"]]
        self.assertEqual([r["artefact"] for r in bad], ["stderr.txt"])
        self.assertEqual(bad[0]["offset"], 0)
        self.assertNotEqual(bad[0]["baseline_sha256"], bad[0]["variant_sha256"])

    def test_the_child_creates_the_artefacts_so_umask_has_power(self):
        # If the parent opened these files, the parent's mask would decide
        # their mode and the umask axis would be measuring nothing.
        res = perturb.run_once(self.cfg,
                               perturb.Variant("umask", "077", umask=0o077),
                               Path(self.tmp) / "re")
        mode = res.modes["stdout.txt"]
        self.assertEqual(mode & 0o077, 0, "group/other bits survived umask 077")
        res2 = perturb.run_once(self.cfg,
                                perturb.Variant("umask", "000", umask=0o000),
                                Path(self.tmp) / "rf")
        self.assertTrue(res2.modes["stdout.txt"] & stat.S_IROTH,
                        "umask 000 did not widen the mode")

    def test_the_working_directory_is_honoured(self):
        probe = perturb.Config(
            repo=self.cfg.repo, run_root=self.cfg.run_root,
            interpreter=sys.executable, corpus_path=self.cfg.corpus_path,
            skills_root=self.cfg.skills_root, pipeline=CwdEcho(),
            tasks_selected=0, tasks_total=0, timeout=120)
        res = perturb.run_once(probe, perturb.Variant("cwd", "tmp",
                                                      cwd=Path(self.tmp)),
                               Path(self.tmp) / "rg")
        self.assertEqual(res.artefacts["stdout.txt"].decode().strip(),
                         os.path.realpath(self.tmp))

    def test_a_nonexistent_working_directory_is_reported_not_silently_ignored(self):
        res = perturb.run_once(
            self.cfg,
            perturb.Variant("cwd", "missing", cwd=Path(self.tmp) / "no-such-dir"),
            Path(self.tmp) / "rh")
        self.assertEqual(res.returncode, 97)


class CwdEcho(perturb.Pipeline):
    name = "cwd-echo"

    def argv(self, cfg, variant):
        return [variant.interpreter or cfg.interpreter, "-c",
                "import os;print(os.path.realpath(os.getcwd()))"]


class TestFileOrdering(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="perturb-order-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copy_takes_only_skill_files_and_preserves_layout(self):
        src = Path(self.tmp) / "src"
        (src / "a" / "b").mkdir(parents=True)
        (src / "a" / "b" / "SKILL.md").write_text("x", encoding="utf-8")
        (src / "a" / "b" / "notes.md").write_text("y", encoding="utf-8")
        dst = Path(self.tmp) / "dst"
        count = perturb.copy_skill_files(src, dst)
        self.assertEqual(count, 1)
        self.assertTrue((dst / "a" / "b" / "SKILL.md").is_file())
        self.assertFalse((dst / "a" / "b" / "notes.md").exists())

    def test_readdir_signature_reports_raw_order_not_sorted_order(self):
        d = Path(self.tmp) / "d"
        d.mkdir()
        for name in ("zz", "aa", "mm"):
            (d / name).write_text("x", encoding="utf-8")
        sig = perturb.readdir_signature(d)
        self.assertEqual(sorted(sig), ["aa", "mm", "zz"])
        self.assertEqual(len(sig), 3)

    def test_readdir_signature_of_a_missing_directory_is_empty(self):
        self.assertEqual(perturb.readdir_signature(Path(self.tmp) / "nope"), [])

    def test_busiest_dir_finds_the_directory_with_the_most_entries(self):
        root = Path(self.tmp) / "tree"
        (root / "thin").mkdir(parents=True)
        (root / "thin" / "one").write_text("x", encoding="utf-8")
        (root / "fat").mkdir()
        for i in range(12):
            (root / "fat" / ("f%02d" % i)).write_text("x", encoding="utf-8")
        rel, count = perturb.busiest_dir(root)
        self.assertEqual(rel, "fat")
        self.assertEqual(count, 12)

    def test_busiest_dir_of_an_empty_tree_does_not_raise(self):
        root = Path(self.tmp) / "empty"
        root.mkdir()
        rel, count = perturb.busiest_dir(root)
        self.assertEqual((rel, count), (".", 0))


class TestInputFreezing(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="perturb-freeze-")
        self.root = Path(self.tmp) / "skills"
        for name in ("alpha", "beta"):
            d = self.root / "fam" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("body of %s\n" % name, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_digest_counts_the_files_and_covers_their_content(self):
        digest, count = perturb.tree_digest(self.root)
        self.assertEqual(count, 2)
        again, _ = perturb.tree_digest(self.root)
        self.assertEqual(digest, again)

    def test_digest_moves_when_content_moves(self):
        before, _ = perturb.tree_digest(self.root)
        (self.root / "fam" / "alpha" / "SKILL.md").write_text(
            "body of alpha changed\n", encoding="utf-8")
        after, _ = perturb.tree_digest(self.root)
        self.assertNotEqual(before, after)

    def test_digest_moves_when_a_file_is_renamed_without_content_change(self):
        before, _ = perturb.tree_digest(self.root)
        (self.root / "fam" / "gamma").mkdir()
        shutil.move(str(self.root / "fam" / "alpha" / "SKILL.md"),
                    str(self.root / "fam" / "gamma" / "SKILL.md"))
        after, _ = perturb.tree_digest(self.root)
        self.assertNotEqual(before, after)

    def test_first_expected_skill_reads_the_first_case(self):
        text, _, _ = perturb.slice_tasks(CORPUS, None)
        self.assertEqual(perturb.first_expected_skill(text), "domain/pack/alpha")

    def test_first_expected_skill_returns_none_when_absent(self):
        self.assertIsNone(perturb.first_expected_skill("tasks:\n  - id: x\n"))


class TestRedaction(unittest.TestCase):

    def test_machine_specific_paths_are_replaced(self):
        cfg = perturb.Config(
            repo=Path("/some/deep/checkout"), run_root=Path("/scratch/run-1"),
            interpreter="python3", corpus_path=Path("/x"),
            skills_root=Path("/y"), pipeline=perturb.SelfTest(),
            tasks_selected=0, tasks_total=0, timeout=1)
        redact = perturb.build_redactor(cfg)
        text = redact("ran /some/deep/checkout/scripts/x from /scratch/run-1/a")
        self.assertIn("<REPO>", text)
        self.assertIn("<RUN>", text)
        self.assertNotIn("/some/deep/checkout", text)

    def test_redaction_can_be_switched_off(self):
        cfg = perturb.Config(
            repo=Path("/some/deep/checkout"), run_root=Path("/scratch/run-1"),
            interpreter="python3", corpus_path=Path("/x"),
            skills_root=Path("/y"), pipeline=perturb.SelfTest(),
            tasks_selected=0, tasks_total=0, timeout=1)
        redact = perturb.build_redactor(cfg, enabled=False)
        self.assertIn("/some/deep/checkout", redact("/some/deep/checkout"))


class TestArgs(unittest.TestCase):

    def test_the_invocation_is_recorded_for_the_report(self):
        args = perturb.parse_args(["--tasks", "8", "--ramdisk"])
        self.assertEqual(args.invocation, ["--tasks", "8", "--ramdisk"])
        self.assertEqual(args.tasks, 8)
        self.assertTrue(args.ramdisk)

    def test_output_destinations_are_stripped_from_the_reproduce_line(self):
        # A committed report must not carry one operator's scratch paths.
        keep = perturb.measurement_args([
            "--tasks", "64", "--report", "/scratch/out.md",
            "--json=/scratch/out.json", "--ramdisk", "--keep",
            "--scan", "docs/metrics.json", "--repo", "/somewhere/checkout",
        ])
        self.assertEqual(keep, ["--tasks", "64", "--ramdisk",
                                "--scan", "docs/metrics.json"])

    def test_stripping_does_not_swallow_the_following_flag(self):
        self.assertEqual(
            perturb.measurement_args(["--quiet", "--tasks", "8"]),
            ["--tasks", "8"])

    def test_scan_targets_accumulate(self):
        args = perturb.parse_args(["--scan", "a.json", "--scan", "b.json"])
        self.assertEqual(args.scan, ["a.json", "b.json"])

    def test_defaults(self):
        args = perturb.parse_args([])
        self.assertEqual(args.tasks, 64)
        self.assertEqual(args.pipeline, "hit1-router")
        self.assertFalse(args.ramdisk)
        self.assertEqual(args.scan, [])


class TestRepoDiscovery(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="perturb-repo-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_walks_up_to_the_marker_directory(self):
        repo = Path(self.tmp) / "checkout"
        (repo / "skills").mkdir(parents=True)
        (repo / "Makefile").write_text("all:\n", encoding="utf-8")
        deep = repo / "tools" / "determinism"
        deep.mkdir(parents=True)
        self.assertEqual(perturb.find_repo(deep).resolve(), repo.resolve())

    def test_raises_when_there_is_no_repository_above(self):
        lonely = Path(self.tmp) / "lonely"
        lonely.mkdir()
        with self.assertRaises(SystemExit):
            perturb.find_repo(lonely)


if __name__ == "__main__":
    unittest.main()
