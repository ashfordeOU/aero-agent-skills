#!/usr/bin/env python3
"""Self-test for the sampled mutation scorer (stdlib unittest, offline).

This suite must pin down the properties the number depends on:

  * every family in the catalogue actually fires on a source that contains
    a site for it, and each mutant is exactly one change;
  * a strong suite kills the mutants and a deliberately weak suite does not,
    so the scorer can tell them apart at all;
  * the run happens on a copy and the corpus on disk is byte-identical
    afterwards;
  * the wall-clock limit really bounds an endless run;
  * the same seed picks the same leaves and the same mutants, and a
    different seed picks different ones.

Run it directly:  python3 tools/mutation/test_mutation_score.py
"""

import ast
import hashlib
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mutation_score as ms  # noqa: E402


SAMPLE_SOURCE = textwrap.dedent(
    '''\
    """A module with one site for every family in the catalogue."""


    LIMIT = 10
    SCALE = 2.5
    ENABLED = True


    def classify(n):
        """Bucket n against the limit."""
        if n < LIMIT and not n == 0:
            return "low"
        return "high"


    def combine(a, b):
        total = a + b
        while total > LIMIT:
            total = total - 1
        return total * SCALE
    '''
)


STRONG_LOGIC = textwrap.dedent(
    '''\
    """Tiny logic module used by the self-test."""


    def bucket(n):
        """Return the bucket label for n."""
        if n < 10:
            return "low"
        if n < 20:
            return "mid"
        return "high"


    def scaled(n):
        """Return n scaled by three."""
        return n * 3
    '''
)


STRONG_SUITE = textwrap.dedent(
    '''\
    """Strong suite: pins every boundary and the exact scale factor."""

    import os
    import sys
    import unittest

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import tiny_logic  # noqa: E402


    class BucketTest(unittest.TestCase):
        def test_boundaries(self):
            for n, want in (
                (-1, "low"), (0, "low"), (9, "low"),
                (10, "mid"), (19, "mid"),
                (20, "high"), (21, "high"),
            ):
                self.assertEqual(tiny_logic.bucket(n), want)


    class ScaledTest(unittest.TestCase):
        def test_exact(self):
            for n in (-2, -1, 0, 1, 2, 7):
                self.assertEqual(tiny_logic.scaled(n), n * 3)


    if __name__ == "__main__":
        unittest.main(verbosity=2)
    '''
)


WEAK_SUITE = textwrap.dedent(
    '''\
    """Weak suite: many test methods, almost no behaviour pinned."""

    import os
    import sys
    import unittest

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import tiny_logic  # noqa: E402


    class ShapeTest(unittest.TestCase):
        def test_bucket_returns_text_a(self):
            self.assertIsInstance(tiny_logic.bucket(5), str)

        def test_bucket_returns_text_b(self):
            self.assertIsInstance(tiny_logic.bucket(50), str)

        def test_bucket_returns_text_c(self):
            self.assertTrue(len(tiny_logic.bucket(5)) > 0)

        def test_bucket_callable(self):
            self.assertTrue(callable(tiny_logic.bucket))

        def test_scaled_callable(self):
            self.assertTrue(callable(tiny_logic.scaled))

        def test_scaled_returns_number_a(self):
            self.assertIsInstance(tiny_logic.scaled(2), int)

        def test_scaled_returns_number_b(self):
            self.assertIsInstance(tiny_logic.scaled(3), int)

        def test_scaled_zero(self):
            self.assertEqual(tiny_logic.scaled(0), 0)


    if __name__ == "__main__":
        unittest.main(verbosity=2)
    '''
)


SKILL_MD = "---\nname: tiny\n---\n\nA stand-in leaf used only by the scorer self-test.\n"


def make_leaf(root, name, suite_source, logic_source=STRONG_LOGIC):
    leaf = os.path.join(root, "skills", "selftest", "group", name)
    scripts = os.path.join(leaf, "scripts")
    os.makedirs(scripts)
    with open(os.path.join(leaf, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(SKILL_MD)
    with open(os.path.join(scripts, "tiny_logic.py"), "w", encoding="utf-8") as fh:
        fh.write(logic_source)
    with open(os.path.join(scripts, "test_tiny.py"), "w", encoding="utf-8") as fh:
        fh.write(suite_source)
    return leaf


def tree_digest(root):
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            digest.update(os.path.relpath(path, root).encode("utf-8"))
            with open(path, "rb") as fh:
                digest.update(fh.read())
    return digest.hexdigest()


class CatalogueTest(unittest.TestCase):
    def setUp(self):
        self.specs = ms.enumerate_mutants(SAMPLE_SOURCE)

    def test_every_family_fires(self):
        seen = {s["op"] for s in self.specs}
        for family in ms.OPERATOR_FAMILIES:
            self.assertIn(family, seen, "family %s produced no mutant" % family)

    def test_ids_are_dense_and_ordered(self):
        self.assertEqual([s["id"] for s in self.specs], list(range(len(self.specs))))

    def test_catalogue_is_deterministic(self):
        again = ms.enumerate_mutants(SAMPLE_SOURCE)
        self.assertEqual(
            [(s["op"], s["i"], s["detail"]) for s in self.specs],
            [(s["op"], s["i"], s["detail"]) for s in again],
        )

    def test_every_mutant_parses_and_differs(self):
        control = ms.roundtrip(SAMPLE_SOURCE)
        changed = 0
        for spec in self.specs:
            mutated = ms.apply_mutant(SAMPLE_SOURCE, spec)
            ast.parse(mutated)  # a mutant must still be a valid program
            if mutated != control:
                changed += 1
        self.assertEqual(changed, len(self.specs))

    def test_mutant_is_a_single_change(self):
        control = ms.roundtrip(SAMPLE_SOURCE).splitlines()
        for spec in self.specs:
            mutated = ms.apply_mutant(SAMPLE_SOURCE, spec).splitlines()
            if spec["op"] == "early-return":
                self.assertEqual(len(mutated), len(control) + 1)
                continue
            self.assertEqual(len(mutated), len(control))
            differing = sum(1 for a, b in zip(control, mutated) if a != b)
            self.assertEqual(
                differing, 1, "spec %r changed %d lines" % (spec, differing)
            )

    def test_comparison_swap_direction(self):
        details = {
            s["detail"] for s in self.specs if s["op"] == "comparison-swap"
        }
        self.assertIn("Lt -> LtE", details)
        self.assertIn("Eq -> NotEq", details)
        self.assertIn("Gt -> GtE", details)

    def test_boundary_offsets_go_both_ways(self):
        details = {s["detail"] for s in self.specs if s["op"] == "boundary-offset"}
        self.assertIn("bound +1", details)
        self.assertIn("bound -1", details)

    def test_roundtrip_is_stable(self):
        once = ms.roundtrip(SAMPLE_SOURCE)
        self.assertEqual(once, ms.roundtrip(once))


class SelectionTest(unittest.TestCase):
    def setUp(self):
        self.population = [
            {"leaf": "skills/d/g/leaf-%03d" % i, "logic": "x_logic.py", "suite": "test_x.py"}
            for i in range(300)
        ]

    def test_same_seed_same_leaves(self):
        a = ms.select_leaves(self.population, 4242, 25)
        b = ms.select_leaves(self.population, 4242, 25)
        self.assertEqual([e["leaf"] for e in a], [e["leaf"] for e in b])
        self.assertEqual(len(a), 25)

    def test_different_seed_different_leaves(self):
        a = {e["leaf"] for e in ms.select_leaves(self.population, 1, 25)}
        b = {e["leaf"] for e in ms.select_leaves(self.population, 2, 25)}
        self.assertNotEqual(a, b)

    def test_sample_larger_than_population_returns_all(self):
        everything = ms.select_leaves(self.population, 7, 10_000)
        self.assertEqual(len(everything), len(self.population))

    def test_fingerprint_changes_with_the_population(self):
        first = ms.corpus_fingerprint(self.population)
        self.assertEqual(first, ms.corpus_fingerprint(list(self.population)))
        shorter = ms.corpus_fingerprint(self.population[:-1])
        self.assertNotEqual(first, shorter)


class MutantSelectionTest(unittest.TestCase):
    def setUp(self):
        self.specs = ms.enumerate_mutants(SAMPLE_SOURCE)

    def test_same_seed_same_mutants(self):
        a = ms.select_mutants(self.specs, 5, "skills/d/g/leaf", 12)
        b = ms.select_mutants(self.specs, 5, "skills/d/g/leaf", 12)
        self.assertEqual([s["id"] for s in a], [s["id"] for s in b])
        self.assertEqual(len(a), 12)

    def test_different_seed_different_mutants(self):
        a = [s["id"] for s in ms.select_mutants(self.specs, 5, "skills/d/g/leaf", 12)]
        c = [s["id"] for s in ms.select_mutants(self.specs, 6, "skills/d/g/leaf", 12)]
        self.assertNotEqual(a, c)

    def test_leaf_path_is_folded_into_the_sub_seed(self):
        a = [s["id"] for s in ms.select_mutants(self.specs, 5, "skills/a/b/one", 12)]
        b = [s["id"] for s in ms.select_mutants(self.specs, 5, "skills/a/b/two", 12)]
        self.assertNotEqual(a, b)

    def test_cap_above_the_catalogue_returns_all_in_order(self):
        everything = ms.select_mutants(self.specs, 5, "skills/d/g/leaf", 10_000)
        self.assertEqual([s["id"] for s in everything], [s["id"] for s in self.specs])

    def test_selection_is_returned_in_catalogue_order(self):
        picked = ms.select_mutants(self.specs, 5, "skills/d/g/leaf", 12)
        self.assertEqual([s["id"] for s in picked], sorted(s["id"] for s in picked))


class StatisticsTest(unittest.TestCase):
    def test_wilson_brackets_the_point_estimate(self):
        lo, hi = ms.wilson_interval(80, 100)
        self.assertLess(lo, 0.8)
        self.assertGreater(hi, 0.8)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_wilson_narrows_as_n_grows(self):
        small = ms.wilson_interval(8, 10)
        large = ms.wilson_interval(800, 1000)
        self.assertLess(large[1] - large[0], small[1] - small[0])

    def test_wilson_needs_a_denominator(self):
        self.assertIsNone(ms.wilson_interval(0, 0))

    def test_bootstrap_is_seeded_and_reproducible(self):
        pairs = [(7, 10), (9, 10), (4, 10), (10, 10), (6, 10)]
        a = ms.cluster_bootstrap(pairs, 99, 500, ms._pooled)
        b = ms.cluster_bootstrap(pairs, 99, 500, ms._pooled)
        c = ms.cluster_bootstrap(pairs, 100, 500, ms._pooled)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertLessEqual(a[0], 0.72)
        self.assertGreaterEqual(a[1], 0.72)


class ScrubTest(unittest.TestCase):
    # The home-directory prefix is assembled at run time rather than written
    # out, so this source file itself contains no machine-local path.
    HOME_PREFIX = "/" + "Users" + "/someone"

    def test_absolute_paths_are_removed(self):
        noisy = (
            'File "%s/work/repo/skills/a/b/scripts/test_x.py", ' % self.HOME_PREFIX
            + "line 12, in test\n  /var/folders/ab/cd/T/aero-mutation-1/leaf\n"
        )
        clean = ms.scrub_paths(noisy)
        self.assertNotIn(self.HOME_PREFIX, clean)
        self.assertNotIn("/var/folders", clean)
        self.assertIn("<path>", clean)
        self.assertIn("line 12", clean)

    def test_ordinary_text_survives(self):
        self.assertEqual(ms.scrub_paths("AssertionError: 3 != 4"), "AssertionError: 3 != 4")

    def test_tail_scrubs_and_truncates(self):
        noisy = "x" * 50 + " " + self.HOME_PREFIX + "/private/place"
        out = ms._tail(noisy, limit=1000)
        self.assertNotIn(self.HOME_PREFIX, out)
        self.assertEqual(len(ms._tail("y" * 900, limit=100)), 100)


class SandboxTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="mutation-selftest-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_time_limit_bounds_an_endless_run(self):
        leaf = make_leaf(self.root, "endless", STRONG_SUITE)
        with open(
            os.path.join(leaf, "scripts", "test_tiny.py"), "w", encoding="utf-8"
        ) as fh:
            fh.write("while True:\n    pass\n")
        box = ms.Sandbox(self.root, leaf)
        self.addCleanup(box.close)
        run = box.run_suite("test_tiny.py", 1.0)
        self.assertEqual(run["status"], ms.RUN_TIMEOUT)
        self.assertLess(run["seconds"], 20.0)

    def test_sandbox_lives_outside_the_repo(self):
        leaf = make_leaf(self.root, "outside", STRONG_SUITE)
        box = ms.Sandbox(self.root, leaf)
        self.addCleanup(box.close)
        self.assertFalse(
            os.path.realpath(box.leaf).startswith(os.path.realpath(self.root) + os.sep)
        )

    def test_both_streams_are_captured(self):
        leaf = make_leaf(self.root, "streams", STRONG_SUITE)
        box = ms.Sandbox(self.root, leaf)
        self.addCleanup(box.close)
        run = box.run_suite("test_tiny.py", 30.0)
        self.assertEqual(run["status"], ms.RUN_PASS)
        # the stdlib runner reports on stderr; a stdout-only read would
        # see an empty string and could be mistaken for a failure
        self.assertIn("OK", run["stderr"])


class ScoreLeafTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="mutation-selftest-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def _entry(self, name):
        return {
            "leaf": os.path.join("skills", "selftest", "group", name),
            "logic": "tiny_logic.py",
            "suite": "test_tiny.py",
        }

    def test_strong_suite_kills_everything(self):
        make_leaf(self.root, "strong", STRONG_SUITE)
        res = ms.score_leaf(self.root, self._entry("strong"), 11, 60, 30.0)
        self.assertEqual(res["status"], "scored")
        self.assertGreater(res["mutants_run"], 10)
        self.assertEqual(res["survived"], 0, res["survivors"])
        self.assertEqual(res["score"], 1.0)

    def test_weak_suite_leaks_survivors(self):
        make_leaf(self.root, "weak", WEAK_SUITE)
        res = ms.score_leaf(self.root, self._entry("weak"), 11, 60, 30.0)
        self.assertEqual(res["status"], "scored")
        self.assertGreater(res["survived"], 0)
        self.assertLess(res["score"], 0.75)

    def test_scorer_separates_strong_from_weak(self):
        make_leaf(self.root, "strong2", STRONG_SUITE)
        make_leaf(self.root, "weak2", WEAK_SUITE)
        strong = ms.score_leaf(self.root, self._entry("strong2"), 11, 60, 30.0)
        weak = ms.score_leaf(self.root, self._entry("weak2"), 11, 60, 30.0)
        self.assertGreater(strong["score"], weak["score"])

    def test_red_suite_is_excluded_not_scored(self):
        broken = STRONG_SUITE.replace('(9, "low")', '(9, "definitely-not-low")')
        make_leaf(self.root, "red", broken)
        res = ms.score_leaf(self.root, self._entry("red"), 11, 20, 30.0)
        self.assertEqual(res["status"], "excluded:suite-red-before-mutation")
        self.assertIsNone(res["score"])

    def test_the_corpus_on_disk_is_untouched(self):
        make_leaf(self.root, "pristine", WEAK_SUITE)
        before = tree_digest(self.root)
        ms.score_leaf(self.root, self._entry("pristine"), 11, 40, 30.0)
        self.assertEqual(tree_digest(self.root), before)

    def test_two_runs_at_one_seed_agree(self):
        make_leaf(self.root, "repeat", WEAK_SUITE)
        a = ms.score_leaf(self.root, self._entry("repeat"), 5, 12, 30.0)
        b = ms.score_leaf(self.root, self._entry("repeat"), 5, 12, 30.0)
        self.assertEqual(a["survivors"], b["survivors"])
        self.assertEqual(a["killed"], b["killed"])
        self.assertEqual(a["mutants_run"], b["mutants_run"])


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="mutation-selftest-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_modules_are_sorted_by_content_not_by_name(self):
        leaf = make_leaf(self.root, "oddnames", STRONG_SUITE)
        scripts = os.path.join(leaf, "scripts")
        # a logic module whose name begins with test_, as a few real leaves have
        os.rename(
            os.path.join(scripts, "tiny_logic.py"),
            os.path.join(scripts, "test_bench_logic.py"),
        )
        suite_path = os.path.join(scripts, "test_tiny.py")
        with open(suite_path, "r", encoding="utf-8") as fh:
            body = fh.read()
        with open(suite_path, "w", encoding="utf-8") as fh:
            fh.write(body.replace("tiny_logic", "test_bench_logic"))
        found = ms.discover_leaves(self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["logic"], "test_bench_logic.py")
        self.assertEqual(found[0]["suite"], "test_tiny.py")

    def test_report_holds_no_absolute_path(self):
        make_leaf(self.root, "relative", STRONG_SUITE)
        found = ms.discover_leaves(self.root)
        self.assertTrue(found)
        for entry in found:
            self.assertFalse(os.path.isabs(entry["leaf"]))
            self.assertNotIn(self.root, entry["leaf"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
