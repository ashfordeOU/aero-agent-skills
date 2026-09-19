#!/usr/bin/env python3
"""Regenerate the router evidence bundle from the repository's own eval files.

    python3 export_cases.py            # rebuild cases/ + manifest.json
    python3 export_cases.py --check    # fail if either is stale, write nothing
    python3 export_cases.py --no-run   # skip the router replay (hashes only)

Run this after any change under eval/. It reads the corpus and the per-leaf
fragments, writes one JSON Lines case set for each, replays both through the
reference router, and records counts, hashes and results in manifest.json.

Standard library only; no network. The YAML it reads is parsed by the narrow
reader in yaml_subset.py, not by PyYAML, so the bundle stays installable-free.
"""

import argparse
import datetime
import json
import os
import sys

import case_set
import reference_router
import yaml_subset

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
EVAL_DIR = os.path.join(REPO_ROOT, "eval")
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
CASES_DIR = os.path.join(HERE, "cases")
MANIFEST = os.path.join(HERE, "manifest.json")

GATED_FILE = os.path.join(CASES_DIR, "hit1-gated-cases.jsonl")
UNGATED_FILE = os.path.join(CASES_DIR, "hit1-ungated-cases.jsonl")

CORPUS_NAME = "hit1-corpus.yaml"
BUNDLE_VERSION = "1.0.0"


def _read_case_file(path, gated):
    """Turn one eval YAML file into case records."""
    stem = os.path.basename(path)
    if stem.endswith(".yaml"):
        stem = stem[:-len(".yaml")]
    if stem.startswith("hit1-"):
        stem = stem[len("hit1-"):]
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    tasks = yaml_subset.read_tasks(text)
    source = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
    records = []
    seen = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("%s: a task is not a mapping" % source)
        case_id = str(task.get("id", "")).strip()
        query = task.get("query")
        expected = task.get("expected_skill")
        if not case_id or not query or not expected:
            raise ValueError("%s: task %r is missing id/query/expected_skill"
                             % (source, case_id or task))
        if case_id in seen:
            raise ValueError("%s: duplicate case id %r inside one file"
                             % (source, case_id))
        seen.add(case_id)
        records.append({
            "uid": "%s:%s" % (stem, case_id),
            "case_id": case_id,
            "query": query,
            "expected_skill": expected,
            "intent": task.get("intent") or "",
            "source": source,
            "gated": gated,
        })
    return records


def collect():
    """Read every eval case file. Returns (gated records, ungated records)."""
    corpus_path = os.path.join(EVAL_DIR, CORPUS_NAME)
    if not os.path.exists(corpus_path):
        raise SystemExit("eval/%s not found; run this from inside the repo"
                         % CORPUS_NAME)
    gated = _read_case_file(corpus_path, True)

    ungated = []
    for name in sorted(os.listdir(EVAL_DIR)):
        if not name.startswith("hit1-") or not name.endswith(".yaml"):
            continue
        if name == CORPUS_NAME:
            continue
        ungated.extend(_read_case_file(os.path.join(EVAL_DIR, name), False))

    for label, records in (("gated", gated), ("ungated", ungated)):
        uids = [r["uid"] for r in records]
        if len(set(uids)) != len(uids):
            raise ValueError("%s set has duplicate uids" % label)
    return gated, ungated


def replay(index, records):
    """Route every case. Returns (hits, misses list)."""
    hits = 0
    misses = []
    for record in records:
        score, top1 = index.top1(record["query"])
        if top1 == record["expected_skill"]:
            hits += 1
        else:
            misses.append({
                "uid": record["uid"],
                "expected_skill": record["expected_skill"],
                "top1": top1,
                "top1_score": score,
            })
    return hits, misses


def _set_entry(path, records, index, run, extra):
    entry = {
        "path": os.path.relpath(path, HERE).replace(os.sep, "/"),
        "cases": len(records),
        "distinct_expected_skills": len(set(r["expected_skill"] for r in records)),
        "source_files": len(set(r["source"] for r in records)),
        "sha256_file": case_set.file_digest(path),
        "sha256_cases": case_set.cases_digest(records),
    }
    entry.update(extra)
    if run:
        hits, misses = replay(index, records)
        entry["result"] = {
            "cases": len(records),
            "hits": hits,
            "misses": len(misses),
            "hit1_rate": round(hits / float(len(records)), 6) if records else 0.0,
            "miss_uids": [m["uid"] for m in misses][:200],
        }
    return entry


def build(run=True):
    gated, ungated = collect()
    if not os.path.isdir(CASES_DIR):
        os.makedirs(CASES_DIR)
    case_set.dump_cases(gated, GATED_FILE)
    case_set.dump_cases(ungated, UNGATED_FILE)

    index = reference_router.SkillIndex.from_tree(SKILLS_DIR)
    leaf_paths = set()
    for entry in index.entries:
        if os.path.isdir(os.path.join(SKILLS_DIR, entry.path, "scripts")):
            leaf_paths.add(entry.path)

    manifest = {
        "bundle": "aero-agent-skills-router-evidence",
        "bundle_version": BUNDLE_VERSION,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                                 .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "tools/export/export_cases.py",
        "claim": ("Every case in the gated set resolves to its expected skill "
                  "as rank 1 of the deterministic offline router."),
        "router": {
            "implementation": "tools/export/reference_router.py",
            "repository_implementation": "scripts/router_eval.py",
            "weights": {
                "tags": reference_router.WEIGHT_TAGS,
                "name": reference_router.WEIGHT_NAME,
                "description": reference_router.WEIGHT_DESCRIPTION,
                "body": reference_router.WEIGHT_BODY,
                "phrase_bonus": reference_router.PHRASE_BONUS,
            },
            "tokenizer": "[a-z0-9][a-z0-9-]* over lowercased text, stop words removed",
            "stop_words": len(reference_router.STOP_WORDS),
            "sha256_stop_words": reference_router.stopwords_digest(),
            "tie_break": "score descending, then skill path ascending",
            "network": "none",
            "dependencies": "python3 standard library only",
        },
        "skill_index": {
            "root": "skills",
            "skills_indexed": len(index),
            "leaf_skills": len(leaf_paths),
            "sha256": index.digest(),
            "note": ("sha256 covers path, name, description, tags and a hash of "
                     "the body of every indexed skill, in path order."),
        },
        "case_sets": {
            "gated": _set_entry(
                GATED_FILE, gated, index, run,
                {
                    "sources": ["eval/%s" % CORPUS_NAME],
                    "executed_by_repository_gate": True,
                    "gate": "make hit1 -> scripts/gate-hit1-corpus.sh -> "
                            "scripts/router_eval.py",
                    "note": "This set, and only this set, backs the published "
                            "Hit@1 figure.",
                }),
            "ungated": _set_entry(
                UNGATED_FILE, ungated, index, run,
                {
                    "sources": ["eval/hit1-*.yaml except %s" % CORPUS_NAME],
                    "executed_by_repository_gate": False,
                    "gate": None,
                    "note": "Per-leaf fragments that exist in eval/ but that no "
                            "gate executes. Published as evidence of what is NOT "
                            "yet proven, not as part of the claim.",
                }),
        },
    }
    for name in sorted(manifest["case_sets"]):
        if manifest["case_sets"][name]["cases"] == 0:
            print("WARNING: the %s case set is empty - eval/ held no cases for "
                  "it. An empty set cannot fail, so do not read it as green."
                  % name)
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def check():
    """Rebuild into memory and compare hashes with what is on disk."""
    if not os.path.exists(MANIFEST):
        print("STALE: manifest.json missing")
        return 1
    with open(MANIFEST, "r", encoding="utf-8") as handle:
        recorded = json.load(handle)
    gated, ungated = collect()
    problems = []
    for name, records, path in (("gated", gated, GATED_FILE),
                                ("ungated", ungated, UNGATED_FILE)):
        entry = (recorded.get("case_sets") or {}).get(name) or {}
        if entry.get("cases") != len(records):
            problems.append("%s: manifest says %s cases, eval/ holds %d"
                            % (name, entry.get("cases"), len(records)))
        if entry.get("sha256_cases") != case_set.cases_digest(records):
            problems.append("%s: case content hash differs from eval/" % name)
        if not os.path.exists(path):
            problems.append("%s: %s missing" % (name, path))
        elif entry.get("sha256_file") != case_set.file_digest(path):
            problems.append("%s: exported file does not match its recorded hash"
                            % name)
    index = reference_router.SkillIndex.from_tree(SKILLS_DIR)
    if (recorded.get("skill_index") or {}).get("sha256") != index.digest():
        problems.append("skill index hash differs from skills/")
    if problems:
        for problem in problems:
            print("STALE: %s" % problem)
        print("Run: python3 export_cases.py")
        return 1
    print("export bundle is current (%d gated + %d ungated cases, index %d skills)"
          % (len(gated), len(ungated), len(index)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="verify the bundle is current; write nothing")
    parser.add_argument("--no-run", action="store_true",
                        help="do not replay the router while exporting")
    args = parser.parse_args(argv)
    if args.check:
        return check()
    manifest = build(run=not args.no_run)
    for name in sorted(manifest["case_sets"]):
        entry = manifest["case_sets"][name]
        result = entry.get("result")
        if result:
            print("%-8s %5d cases  %5d hits  %5d misses  Hit@1 %.4f"
                  % (name, entry["cases"], result["hits"], result["misses"],
                     result["hit1_rate"]))
        else:
            print("%-8s %5d cases (not replayed)" % (name, entry["cases"]))
    print("wrote %s, %s, %s"
          % (os.path.relpath(GATED_FILE, HERE),
             os.path.relpath(UNGATED_FILE, HERE),
             os.path.relpath(MANIFEST, HERE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
