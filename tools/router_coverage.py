#!/usr/bin/env python3
"""Honest router-coverage instrument for the Hit@1 evidence.

Why this exists
---------------
`make hit1` reads exactly one file, eval/hit1-corpus.yaml, and reports a
Hit@1 rate over the cases in it. eval/ also holds one fragment per leaf,
eval/hit1-<slug>.yaml, carrying two more cases each. No gate executes those.
So the published Hit@1 is a true number measured on a strict subset of the
authored cases, and the leaves that only have a fragment are graded by
nothing at all.

This tool measures the whole picture and prints it in one block:

  * how many leaf skills exist, how many are named by at least one case
    anywhere, and how many are named by no case at all;
  * how many leaves have a per-leaf fragment;
  * the case count and the Hit@1 rate of the EXECUTED set and of the
    UNEXECUTED set, separately, never merged into one flattering figure;
  * which leaves miss on both of their fragment cases.

It also asserts the structure of eval/hit1-corpus.yaml. That file had its
`future_pins` entry come apart -- the pin's id, intent and query leaked out
to the document root as top-level keys and the pin itself was left holding
one key. PyYAML accepts that silently and the gate reads only `tasks`, so
nothing went red and the pin stopped being a pin. A structural defect in the
corpus now exits non-zero here.

This tool CHANGES NOTHING IN THE REPOSITORY and DECIDES NOTHING. It reads
eval/ and skills/; the only files it writes are the report paths you pass on
the command line. It does not touch what `make hit1` reads; which set should
gate a release is a founder call.

Usage
-----
    python3 tools/router_coverage.py                    # summary block
    python3 tools/router_coverage.py --structure-only   # fast: assertions only
    python3 tools/router_coverage.py --per-leaf FILE    # TSV, one row per leaf
    python3 tools/router_coverage.py --json FILE        # machine-readable
    python3 tools/router_coverage.py --selftest         # prove the ranker
    python3 tools/router_coverage.py \
        --expect-executed-hits 1754 --expect-unexecuted-hits 2856
                                                        # regression ratchet

Exit status
-----------
    0  structure clean
    1  eval/hit1-corpus.yaml is structurally malformed, or --expect-* was
       given and not met, or the self-test failed

Only the STRUCTURE of eval/hit1-corpus.yaml reds by default. Coverage and
Hit@1 are reported and never failed on unless you opt in with
--max-uncovered, --min-hit1-unexecuted or the --expect-*-hits ratchets: the
instrument must be safe to run before anyone has decided what the policy is,
and a number nobody has adopted yet must not block a build.

Standard library only; no network; deterministic. The YAML subset reader and
the router definition are imported from tools/export/ (yaml_subset.py,
reference_router.py) so this instrument scores with the same expression the
published evidence bundle does rather than a second, drifting copy. Those two
modules are owned elsewhere; if they move, this fails loudly at import.
"""

import argparse
import collections
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXPORT_DIR = os.path.join(_HERE, "export")
if _EXPORT_DIR not in sys.path:
    sys.path.insert(0, _EXPORT_DIR)

try:
    import yaml_subset
    import reference_router
except ImportError as exc:  # pragma: no cover - environment problem, not data
    sys.stderr.write(
        "FAIL router-coverage: cannot import the stdlib YAML reader / router "
        "from tools/export (%s). Expected tools/export/yaml_subset.py and "
        "tools/export/reference_router.py.\n" % exc)
    raise SystemExit(1)

CORPUS_NAME = "hit1-corpus.yaml"
CASE_KEYS = ("id", "query", "intent", "expected_skill")


# --------------------------------------------------------------------------
# reading


def repo_root(explicit=None):
    return os.path.abspath(explicit) if explicit else os.path.dirname(_HERE)


def leaf_dirs(skills_root):
    """Leaf skills: skills/<domain>/<subdomain>/<leaf>/SKILL.md.

    Same definition scripts/corpus_naming_check.py (gate 9) uses, so the two
    instruments are counting the same population.
    """
    leaves = set()
    if not os.path.isdir(skills_root):
        return leaves
    for domain in sorted(os.listdir(skills_root)):
        d1 = os.path.join(skills_root, domain)
        if not os.path.isdir(d1):
            continue
        for sub in sorted(os.listdir(d1)):
            d2 = os.path.join(d1, sub)
            if not os.path.isdir(d2):
                continue
            for leaf in sorted(os.listdir(d2)):
                d3 = os.path.join(d2, leaf)
                if os.path.isfile(os.path.join(d3, "SKILL.md")):
                    leaves.add("%s/%s/%s" % (domain, sub, leaf))
    return leaves


def all_skill_dirs(skills_root):
    """Every indexed SKILL.md directory, leaf or router, as a relative path."""
    found = set()
    for dirpath, dirnames, filenames in os.walk(skills_root):
        dirnames.sort()
        if "SKILL.md" in filenames:
            rel = os.path.relpath(dirpath, skills_root).replace(os.sep, "/")
            found.add(rel)
    found.discard(".")
    return found


def read_case_file(path):
    """Return the `tasks` list of one eval file, or raise YamlSubsetError."""
    with open(path, "r", encoding="utf-8") as handle:
        return yaml_subset.load_mapping(handle.read())


GATE_SCRIPT = os.path.join("scripts", "gate-hit1-corpus.sh")


def gate_executes_all(root):
    """Does gate 5 run every fragment, or only eval/hit1-corpus.yaml?

    Read from the gate script itself rather than tracked as a second constant
    here. A duplicated definition is exactly how this instrument would come to
    report a gap that had been closed, or miss one that had reopened: the whole
    point of the executed/unexecuted split is that it describes what the build
    actually grades.
    """
    path = os.path.join(root, GATE_SCRIPT)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except IOError:
        return False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("corpus=") and "#" not in line.split("=", 1)[0]:
            return not line.rstrip('"').endswith(CORPUS_NAME)
    return False


def collect(eval_dir):
    """Split eval/ into the executed corpus and the unexecuted fragments."""
    corpus_path = os.path.join(eval_dir, CORPUS_NAME)
    names = sorted(n for n in os.listdir(eval_dir)
                   if n.startswith("hit1-") and n.endswith(".yaml")
                   and n != CORPUS_NAME)
    return corpus_path, [os.path.join(eval_dir, n) for n in names]


# --------------------------------------------------------------------------
# structural assertions on eval/hit1-corpus.yaml  (defect (c))


def check_case(where, case, problems, index):
    if not isinstance(case, dict):
        problems.append("%s[%d] is a %s, not a mapping"
                        % (where, index, type(case).__name__))
        return
    keys = set(case)
    missing = [k for k in CASE_KEYS if k not in keys]
    extra = sorted(keys - set(CASE_KEYS))
    ident = case.get("id") if isinstance(case.get("id"), str) else "?"
    if missing:
        problems.append("%s[%d] (id=%s) is missing %s"
                        % (where, index, ident, ", ".join(missing)))
    if extra:
        problems.append("%s[%d] (id=%s) has unexpected key(s) %s"
                        % (where, index, ident, ", ".join(extra)))
    for key in CASE_KEYS:
        value = case.get(key)
        if key in keys and (not isinstance(value, str) or not value.strip()):
            problems.append("%s[%d] (id=%s) %s is not a non-empty string"
                            % (where, index, ident, key))


def check_corpus_structure(doc):
    """Assert eval/hit1-corpus.yaml holds the shape the gate assumes.

    The leak this catches: a pin's keys escaping to the document root. The
    gate reads doc['tasks'] and nothing else, so extra root keys and a
    one-key pin are invisible to it. They are not invisible here.
    """
    problems = []
    if not isinstance(doc, dict):
        return ["corpus document is a %s, not a mapping" % type(doc).__name__]

    allowed = {"tasks", "future_pins"}
    stray = sorted(set(doc) - allowed)
    if stray:
        problems.append(
            "unexpected top-level key(s) %s -- a future_pins/tasks entry has "
            "leaked to the document root; the only permitted root keys are "
            "tasks and future_pins" % ", ".join(stray))

    tasks = doc.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        problems.append("tasks: must be a non-empty sequence")
        tasks = []
    for i, case in enumerate(tasks):
        check_case("tasks", case, problems, i)

    if "future_pins" in doc:
        pins = doc.get("future_pins")
        if not isinstance(pins, list) or not pins:
            problems.append("future_pins: must be a non-empty sequence when "
                            "present")
            pins = []
        for i, pin in enumerate(pins):
            check_case("future_pins", pin, problems, i)
    else:
        pins = []

    seen = {}
    for label, group in (("tasks", tasks), ("future_pins", pins)):
        for i, case in enumerate(group):
            if not isinstance(case, dict):
                continue
            ident = case.get("id")
            if not isinstance(ident, str):
                continue
            if ident in seen:
                problems.append("duplicate id %r in %s[%d]; already used in %s"
                                % (ident, label, i, seen[ident]))
            else:
                seen[ident] = "%s[%d]" % (label, i)
    return problems


# --------------------------------------------------------------------------
# ranking


def top1(index, query):
    """Winner for one query: highest score, ties broken by path ascending.

    `index.entries` is sorted by path ascending, so scanning and keeping only
    a STRICTLY greater score yields the lexicographically first path among
    ties -- the same winner as sorting on (-score, path) and taking [0].
    `--selftest` proves that against reference_router's own rank().
    """
    tokens = frozenset(reference_router.tokenize(query))
    phrase = " ".join(reference_router.tokenize(query))
    best_score = None
    best_path = None
    for entry in index.entries:
        score = entry.score(tokens, phrase)
        if best_score is None or score > best_score:
            best_score = score
            best_path = entry.path
    return best_score, best_path


def score_set(index, cases, known_skills):
    """Run one case set. Returns (records, hits, unresolved)."""
    records = []
    hits = 0
    unresolved = []
    for source, case in cases:
        expected = case.get("expected_skill") or ""
        query = case.get("query") or ""
        if expected not in known_skills:
            unresolved.append((source, case.get("id"), expected))
        score, winner = top1(index, query)
        ok = winner == expected
        hits += 1 if ok else 0
        records.append({
            "source": source,
            "id": case.get("id"),
            "expected": expected,
            "top1": winner,
            "score": score,
            "hit": ok,
        })
    return records, hits, unresolved


# --------------------------------------------------------------------------
# reporting


def pct(num, den):
    return 0.0 if not den else 100.0 * num / den


def domain_of(path):
    return path.split("/", 1)[0] if path else "(none)"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Router coverage and Hit@1 over the executed and the "
                    "unexecuted case sets, measured separately.")
    ap.add_argument("--repo", default=None,
                    help="repository root (default: the parent of tools/)")
    ap.add_argument("--structure-only", action="store_true",
                    help="run the corpus structural assertions and stop")
    ap.add_argument("--no-score", action="store_true",
                    help="census only; skip the (slow) routing run")
    ap.add_argument("--per-leaf", default=None,
                    help="write a TSV row per leaf to this path")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="write a machine-readable report to this path")
    ap.add_argument("--list-uncovered", action="store_true",
                    help="print every leaf that no case names")
    ap.add_argument("--list-misses", action="store_true",
                    help="print every miss in the unexecuted set")
    ap.add_argument("--max-uncovered", type=int, default=None,
                    help="exit 1 if more leaves than this have no case")
    ap.add_argument("--min-hit1-unexecuted", type=float, default=None,
                    help="exit 1 if the unexecuted set scores below this "
                         "percentage")
    ap.add_argument("--expect-executed-hits", type=int, default=None,
                    help="ratchet: exit 1 if the executed set scores fewer "
                         "hits than this")
    ap.add_argument("--expect-unexecuted-hits", type=int, default=None,
                    help="ratchet: exit 1 if the unexecuted set scores fewer "
                         "hits than this. Pin it to today measured figure and "
                         "a regression reds even while the absolute number is "
                         "still short of every case passing")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the fast ranker agrees with reference_router")
    args = ap.parse_args(argv)

    # A threshold that is never evaluated is worse than no threshold: the run
    # exits 0 and looks like the bar was met. Refuse the combination.
    scored_thresholds = [
        ("--min-hit1-unexecuted", args.min_hit1_unexecuted),
        ("--expect-executed-hits", args.expect_executed_hits),
        ("--expect-unexecuted-hits", args.expect_unexecuted_hits),
    ]
    given = [name for name, value in scored_thresholds if value is not None]
    if given and (args.no_score or args.structure_only):
        ap.error("%s need the routing run; drop --no-score/--structure-only"
                 % ", ".join(given))

    # --max-uncovered is answered by the census, not the routing run, so it
    # composes with --no-score. --structure-only returns before the census,
    # which would leave the threshold unevaluated and the run green.
    if args.max_uncovered is not None and args.structure_only:
        ap.error("--max-uncovered needs the coverage census; "
                 "drop --structure-only")

    root = repo_root(args.repo)
    eval_dir = os.path.join(root, "eval")
    skills_root = os.path.join(root, "skills")
    for needed in (eval_dir, skills_root):
        if not os.path.isdir(needed):
            print("FAIL router-coverage: %s is not a directory"
                  % os.path.relpath(needed, root), file=sys.stderr)
            return 1

    corpus_path, fragment_paths = collect(eval_dir)
    if not os.path.isfile(corpus_path):
        print("FAIL router-coverage: eval/%s missing" % CORPUS_NAME,
              file=sys.stderr)
        return 1

    # ---- structure -------------------------------------------------------
    try:
        corpus_doc = read_case_file(corpus_path)
    except yaml_subset.YamlSubsetError as exc:
        print("FAIL router-coverage: eval/%s does not parse: %s"
              % (CORPUS_NAME, exc), file=sys.stderr)
        return 1
    problems = check_corpus_structure(corpus_doc)

    frag_problems = []
    fragments = []
    for path in fragment_paths:
        rel = "eval/" + os.path.basename(path)
        try:
            doc = read_case_file(path)
        except yaml_subset.YamlSubsetError as exc:
            frag_problems.append("%s does not parse: %s" % (rel, exc))
            continue
        stray = sorted(set(doc) - {"tasks"})
        if stray:
            frag_problems.append("%s has unexpected top-level key(s) %s"
                                 % (rel, ", ".join(stray)))
        tasks = doc.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            frag_problems.append("%s has no non-empty tasks: sequence" % rel)
            continue
        local = []
        for i, case in enumerate(tasks):
            check_case("%s tasks" % rel, case, local, i)
        frag_problems.extend(local)
        fragments.append((rel, tasks))

    if problems:
        print("FAIL router-coverage: eval/%s is structurally malformed "
              "(%d problem(s))" % (CORPUS_NAME, len(problems)))
        for line in problems:
            print("  - %s" % line)
        print("  The gate reads only the tasks: key, so none of this reds "
              "there. Fix the file; do not relax this check.")
        return 1
    print("PASS router-coverage-structure: eval/%s root keys %s, %d task(s), "
          "%d future pin(s), all four case keys present, ids unique"
          % (CORPUS_NAME, "+".join(sorted(corpus_doc)),
             len(corpus_doc.get("tasks") or []),
             len(corpus_doc.get("future_pins") or [])))
    if frag_problems:
        print("WARN router-coverage-structure: %d problem(s) in the per-leaf "
              "fragments (reported, not failed):" % len(frag_problems))
        for line in frag_problems[:40]:
            print("  - %s" % line)
        if len(frag_problems) > 40:
            print("  ... %d more" % (len(frag_problems) - 40))
    if args.structure_only:
        return 0

    # ---- census ----------------------------------------------------------
    leaves = leaf_dirs(skills_root)
    known = all_skill_dirs(skills_root)

    corpus_cases = [("eval/" + CORPUS_NAME, c) for c in corpus_doc["tasks"]]
    fragment_cases = [(rel, c) for rel, tasks in fragments for c in tasks]
    # "executed" means what gate 5 actually runs, read from the gate script.
    if gate_executes_all(root):
        executed, unexecuted = corpus_cases + fragment_cases, []
    else:
        executed, unexecuted = corpus_cases, fragment_cases

    exec_by_leaf = collections.defaultdict(list)
    for src, case in executed:
        exec_by_leaf[case.get("expected_skill") or ""].append(case)
    frag_by_leaf = collections.defaultdict(list)
    for src, case in unexecuted:
        frag_by_leaf[case.get("expected_skill") or ""].append(case)
    # Census, not a scoring set: which leaves a per-leaf fragment targets at
    # all. Deriving this from `unexecuted` made it read 0 the moment gate 5
    # started executing the fragments -- the instrument reporting that 3,189
    # leaves had no fragment while 2,277 fragment files sat on disk.
    fragment_targets = collections.defaultdict(list)
    for src, case in fragment_cases:
        fragment_targets[case.get("expected_skill") or ""].append(case)

    named_executed = set(exec_by_leaf) & leaves
    named_fragment = set(fragment_targets) & leaves
    covered = named_executed | named_fragment
    uncovered = leaves - covered

    # Gate 9 attributes a fragment to a leaf by FILENAME -- the longest leaf
    # slug contained in the stem. A fragment whose filename does not carry
    # the slug of the leaf its CONTENT targets is attributed to nobody, or
    # worse to some other leaf, which then looks graded when it is not.
    slugs = {p.rsplit("/", 1)[-1]: p for p in leaves}
    name_mapped = set()
    miscredited = []
    for rel, tasks in fragments:
        stem = os.path.basename(rel)[:-len(".yaml")]
        hit = max((s for s in slugs if s in stem), key=len, default=None)
        targets = sorted({c.get("expected_skill") or "" for c in tasks})
        if hit:
            name_mapped.add(slugs[hit])
            if slugs[hit] not in targets:
                miscredited.append((rel, slugs[hit], targets))
        else:
            miscredited.append((rel, None, targets))
    filename_blind = sorted(named_fragment - name_mapped)

    # ---- scoring ---------------------------------------------------------
    report = {
        "leaves": len(leaves),
        "indexed_skill_dirs": len(known),
        "covered": len(covered),
        "uncovered": len(uncovered),
        "with_fragment": len(named_fragment),
        "without_fragment": len(leaves) - len(named_fragment),
        "named_by_executed": len(named_executed),
        "not_named_by_executed": len(leaves) - len(named_executed),
        "executed_cases": len(executed),
        "unexecuted_cases": len(unexecuted),
        "fragment_files": len(fragments),
        "fragments_misattributed_by_filename": len(miscredited),
        "leaves_with_a_fragment_gate9_cannot_see": len(filename_blind),
    }

    exec_rec = frag_rec = []
    exec_hits = frag_hits = 0
    both_miss = []
    misses_by_domain = {}
    index = None
    if not args.no_score:
        index = reference_router.SkillIndex.from_tree(skills_root)
        if args.selftest:
            rc = selftest(index, executed + unexecuted)
            if rc:
                return rc
        exec_rec, exec_hits, exec_unresolved = score_set(index, executed, known)
        frag_rec, frag_hits, frag_unresolved = score_set(index, unexecuted, known)

        per_leaf_miss = collections.Counter()
        per_leaf_cases = collections.Counter()
        for rec in frag_rec:
            per_leaf_cases[rec["expected"]] += 1
            if not rec["hit"]:
                per_leaf_miss[rec["expected"]] += 1
        both_miss = sorted(leaf for leaf, n in per_leaf_miss.items()
                           if n == per_leaf_cases[leaf])
        misses_by_domain = collections.Counter(
            domain_of(r["expected"]) for r in frag_rec if not r["hit"])

        report.update({
            "executed_hits": exec_hits,
            "executed_hit1_pct": round(pct(exec_hits, len(executed)), 4),
            "unexecuted_hits": frag_hits,
            "unexecuted_hit1_pct": round(pct(frag_hits, len(unexecuted)), 4),
            "combined_cases": len(executed) + len(unexecuted),
            "combined_hits": exec_hits + frag_hits,
            "combined_hit1_pct": round(
                pct(exec_hits + frag_hits, len(executed) + len(unexecuted)), 4),
            "leaves_missing_both_fragment_cases": len(both_miss),
            "unexecuted_misses_by_domain": dict(sorted(misses_by_domain.items())),
            "executed_expected_not_in_tree": len(exec_unresolved),
            "unexecuted_expected_not_in_tree": len(frag_unresolved),
        })

    # ---- the single summary block ---------------------------------------
    out = []
    out.append("================== router coverage ==================")
    out.append("leaf skills  skills/*/*/*/SKILL.md          %6d"
               % report["leaves"])
    out.append("  covered by >=1 case anywhere             %6d  (%5.2f%%)"
               % (report["covered"], pct(report["covered"], report["leaves"])))
    out.append("  uncovered, no case anywhere              %6d  (%5.2f%%)"
               % (report["uncovered"], pct(report["uncovered"], report["leaves"])))
    out.append("  with a per-leaf fragment                 %6d  (%5.2f%%)"
               % (report["with_fragment"],
                  pct(report["with_fragment"], report["leaves"])))
    out.append("  without a per-leaf fragment              %6d  (%5.2f%%)"
               % (report["without_fragment"],
                  pct(report["without_fragment"], report["leaves"])))
    out.append("  named by an executed case                %6d  (%5.2f%%)"
               % (report["named_by_executed"],
                  pct(report["named_by_executed"], report["leaves"])))
    out.append("  NOT named by any executed case           %6d  (%5.2f%%)"
               % (report["not_named_by_executed"],
                  pct(report["not_named_by_executed"], report["leaves"])))
    out.append("-----------------------------------------------------")
    if report["unexecuted_cases"] == 0 and report["fragment_files"]:
        out.append("EXECUTED    eval/  (corpus + %d fragments)  (make hit1)"
                   % report["fragment_files"])
    else:
        out.append("EXECUTED    eval/%s  (make hit1)" % CORPUS_NAME)
    out.append("  cases                                    %6d"
               % report["executed_cases"])
    if not args.no_score:
        out.append("  Hit@1                                    %6d  (%5.2f%%)"
                   % (exec_hits, pct(exec_hits, report["executed_cases"])))
    if report["unexecuted_cases"] == 0 and report["fragment_files"]:
        out.append("UNEXECUTED  none: gate 5 runs every case in eval/")
    else:
        out.append("UNEXECUTED  eval/hit1-<slug>.yaml x%d  (no gate runs these)"
                   % report["fragment_files"])
    out.append("  cases                                    %6d"
               % report["unexecuted_cases"])
    if not args.no_score:
        out.append("  Hit@1                                    %6d  (%5.2f%%)"
                   % (frag_hits, pct(frag_hits, report["unexecuted_cases"])))
        out.append("  leaves missing on BOTH their cases       %6d"
                   % len(both_miss))
        for dom, n in sorted(misses_by_domain.items(),
                             key=lambda kv: (-kv[1], kv[0])):
            out.append("    miss  %-34s %6d" % (dom, n))
        out.append("-----------------------------------------------------")
        out.append("BOTH SETS (reported together, never merged into one claim)")
        out.append("  cases                                    %6d"
                   % report["combined_cases"])
        out.append("  Hit@1                                    %6d  (%5.2f%%)"
                   % (report["combined_hits"],
                      report["combined_hit1_pct"]))
    out.append("-----------------------------------------------------")
    out.append("skill dirs indexed by the router            %6d"
               % report["indexed_skill_dirs"])
    out.append("fragments misattributed by filename (gate 9)%6d"
               % len(miscredited))
    out.append("leaves with a fragment gate 9 cannot see    %6d"
               % len(filename_blind))
    out.append("=====================================================")
    print("\n".join(out))

    if args.list_uncovered:
        print("\n-- leaves with no case anywhere (%d) --" % len(uncovered))
        for leaf in sorted(uncovered):
            print("  %s" % leaf)
    if args.list_misses and not args.no_score:
        print("\n-- unexecuted-set misses (%d) --"
              % (len(frag_rec) - frag_hits))
        for rec in frag_rec:
            if not rec["hit"]:
                print("  %s  %s  expected=%s top1=%s score=%.1f"
                      % (rec["source"], rec["id"], rec["expected"],
                         rec["top1"], rec["score"]))
    if miscredited:
        print("\n-- fragment filename against fragment content (%d) --"
              % len(miscredited))
        for rel, credited, targets in miscredited:
            print("  %s" % rel)
            print("     gate 9 credits : %s"
                  % (credited or "(no leaf slug in the filename; it graded "
                                 "nothing)"))
            print("     content targets: %s" % ", ".join(targets))
    if filename_blind:
        print("\n-- leaves whose only fragment gate 9 cannot see (%d) --"
              % len(filename_blind))
        for leaf in filename_blind:
            print("  %s" % leaf)

    if args.per_leaf:
        write_per_leaf(args.per_leaf, leaves, exec_by_leaf, frag_by_leaf,
                       exec_rec, frag_rec, args.no_score, fragment_targets)
        print("\nwrote per-leaf TSV: %s" % args.per_leaf)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print("wrote JSON report: %s" % args.json_out)

    rc = 0
    if args.max_uncovered is not None and report["uncovered"] > args.max_uncovered:
        print("FAIL router-coverage: %d uncovered leaves exceeds the "
              "--max-uncovered limit of %d"
              % (report["uncovered"], args.max_uncovered), file=sys.stderr)
        rc = 1
    if (args.min_hit1_unexecuted is not None
            and pct(frag_hits, len(unexecuted)) < args.min_hit1_unexecuted):
        print("FAIL router-coverage: unexecuted-set Hit@1 %.2f%% is below the "
              "--min-hit1-unexecuted floor of %.2f%%"
              % (pct(frag_hits, len(unexecuted)), args.min_hit1_unexecuted),
              file=sys.stderr)
        rc = 1
    for label, expect, hits, total in (
            ("executed", args.expect_executed_hits, exec_hits, len(executed)),
            ("unexecuted", args.expect_unexecuted_hits, frag_hits,
             len(unexecuted))):
        if expect is None:
            continue
        if hits < expect:
            print("FAIL router-coverage: %s set scored %d/%d hits, below the "
                  "--expect-%s-hits ratchet of %d -- this is a REGRESSION"
                  % (label, hits, total, label, expect), file=sys.stderr)
            rc = 1
        elif hits > expect:
            print("NOTE router-coverage: %s set scored %d/%d hits, ABOVE the "
                  "--expect-%s-hits ratchet of %d -- tighten the ratchet to "
                  "%d so the gain cannot be lost again"
                  % (label, hits, total, label, expect, hits))
    return rc


def write_per_leaf(path, leaves, exec_by_leaf, frag_by_leaf, exec_rec,
                   frag_rec, no_score, fragment_targets):
    hit_exec = collections.Counter()
    hit_frag = collections.Counter()
    for rec in exec_rec:
        if rec["hit"]:
            hit_exec[rec["expected"]] += 1
    for rec in frag_rec:
        if rec["hit"]:
            hit_frag[rec["expected"]] += 1
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("leaf\thas_fragment\tin_executed_set\tfragment_cases\t"
                     "fragment_hits\texecuted_cases\texecuted_hits\n")
        for leaf in sorted(leaves):
            # has_fragment / fragment_cases are census facts: a fragment
            # exists whether or not a gate executes it.
            fc = len(fragment_targets.get(leaf, ()))
            uc = len(frag_by_leaf.get(leaf, ()))
            ec = len(exec_by_leaf.get(leaf, ()))
            handle.write("%s\t%s\t%s\t%d\t%s\t%d\t%s\n" % (
                leaf,
                "yes" if fc else "no",
                "yes" if ec else "no",
                fc,
                "-" if (no_score or not uc) else hit_frag[leaf],
                ec,
                "-" if no_score else hit_exec[leaf],
            ))


def selftest(index, cases, sample=200):
    """Prove the fast scan picks the same winner as reference_router.rank()."""
    step = max(1, len(cases) // sample)
    checked = bad = 0
    for _src, case in cases[::step]:
        query = case.get("query") or ""
        mine = top1(index, query)
        theirs = index.top1(query)
        checked += 1
        if mine[1] != theirs[1] or abs(mine[0] - theirs[0]) > 1e-12:
            bad += 1
            print("SELFTEST MISMATCH %s: scan=%s ref=%s"
                  % (case.get("id"), mine, theirs), file=sys.stderr)
    if bad:
        print("FAIL router-coverage selftest: %d/%d rankings disagree"
              % (bad, checked), file=sys.stderr)
        return 1
    print("PASS router-coverage selftest: %d sampled rankings identical to "
          "reference_router.rank()" % checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
