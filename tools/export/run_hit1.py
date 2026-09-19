#!/usr/bin/env python3
"""Re-execute the Aero Agent Skills router evidence. Standard library only.

    python3 run_hit1.py                       # the gated case set
    python3 run_hit1.py --cases cases/hit1-ungated-cases.jsonl
    python3 run_hit1.py --verbose             # print every case, not just misses
    python3 run_hit1.py --json report.json    # machine-readable report

Exit status is 0 when every case in the set is a Hit@1 and the recorded
hashes match, 1 otherwise. `--expect N` instead requires exactly N hits,
which is how a set with known misses is re-executed as a regression check.

Nothing here reaches the network, and nothing is installed: the whole
dependency list is CPython itself.
"""

import argparse
import json
import os
import sys
import time

import case_set
import reference_router

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CASES = os.path.join(HERE, "cases", "hit1-gated-cases.jsonl")
DEFAULT_MANIFEST = os.path.join(HERE, "manifest.json")
DEFAULT_SKILLS = os.path.normpath(os.path.join(HERE, "..", "..", "skills"))


def _load_manifest(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _manifest_entry(manifest, cases_path):
    """Find the manifest record for this case file, by file name."""
    if not manifest:
        return None, None
    wanted = os.path.basename(cases_path)
    for name, entry in sorted((manifest.get("case_sets") or {}).items()):
        if os.path.basename(entry.get("path", "")) == wanted:
            return name, entry
    return None, None


def _check(label, actual, expected):
    """Render a MATCH / MISMATCH / not recorded line for one hash."""
    head = "sha256 %-6s : %s" % (label, actual)
    if expected is None:
        return "%s  [not recorded in manifest]" % head, None
    if actual == expected:
        return "%s  [manifest: MATCH]" % head, True
    return "%s  [manifest: MISMATCH, recorded %s]" % (head, expected), False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Re-execute the Aero Agent Skills Hit@1 router evidence.")
    parser.add_argument("--cases", default=DEFAULT_CASES,
                        help="case-set .jsonl file (default: the gated set)")
    parser.add_argument("--skills", default=DEFAULT_SKILLS,
                        help="root of the skills tree to route over")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST,
                        help="manifest.json to check hashes against")
    parser.add_argument("--no-manifest", action="store_true",
                        help="skip the manifest check entirely")
    parser.add_argument("--verbose", action="store_true",
                        help="print a line per case, not only misses")
    parser.add_argument("--quiet", action="store_true",
                        help="print the summary only")
    parser.add_argument("--expect", type=int, default=None,
                        help="require exactly this many hits (default: all)")
    parser.add_argument("--json", dest="json_out", default=None,
                        help="write a machine-readable report to this path")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.skills):
        parser.error("skills root not found: %s\n"
                     "Pass --skills <dir>: the bundle routes over a skills "
                     "tree and cannot score without one (see README.md)."
                     % args.skills)

    records = case_set.load_cases(args.cases)
    manifest = None if args.no_manifest else _load_manifest(args.manifest)
    set_name, entry = _manifest_entry(manifest, args.cases)

    file_sha = case_set.file_digest(args.cases)
    cases_sha = case_set.cases_digest(records)
    file_line, file_ok = _check("file", file_sha, (entry or {}).get("sha256_file"))
    cases_line, cases_ok = _check("cases", cases_sha, (entry or {}).get("sha256_cases"))

    started = time.time()
    index = reference_router.SkillIndex.from_tree(args.skills)
    index_sha = index.digest()
    recorded_index = ((manifest or {}).get("skill_index") or {}).get("sha256")
    index_line, index_ok = _check("index", index_sha, recorded_index)
    indexed_at = time.time()

    hits = 0
    misses = []
    for record in records:
        score, top1 = index.top1(record["query"])
        hit = top1 == record["expected_skill"]
        if hit:
            hits += 1
        else:
            misses.append({
                "uid": record["uid"],
                "expected_skill": record["expected_skill"],
                "top1": top1,
                "top1_score": score,
                "source": record.get("source", ""),
            })
        if args.verbose and not args.quiet:
            print("%s %s top1=%s score=%.1f expected=%s"
                  % ("HIT " if hit else "MISS", record["uid"], top1, score,
                     record["expected_skill"]))
    finished = time.time()

    total = len(records)
    rate = (100.0 * hits / total) if total else 0.0

    if not args.quiet:
        print("Aero Agent Skills - router evidence, reference runner")
        print("-----------------------------------------------------")
        print("case set       : %s%s"
              % (os.path.basename(args.cases),
                 "" if set_name is None else "  (manifest: %s)" % set_name))
        print("cases          : %d" % total)
        print(file_line)
        print(cases_line)
        print("skills root    : %s" % args.skills)
        print("skills indexed : %d" % len(index))
        print(index_line)
        print("router         : tags x%.1f  name x%.1f  description x%.1f  "
              "body x%.1f  phrase +%.1f"
              % (reference_router.WEIGHT_TAGS, reference_router.WEIGHT_NAME,
                 reference_router.WEIGHT_DESCRIPTION, reference_router.WEIGHT_BODY,
                 reference_router.PHRASE_BONUS))
        print("stop words     : %d (sha256 %s)"
              % (len(reference_router.STOP_WORDS),
                 reference_router.stopwords_digest()))
        print("timing         : index %.1fs, route %.1fs"
              % (indexed_at - started, finished - indexed_at))
        print("")
        if misses and not args.verbose:
            for miss in misses[:50]:
                print("MISS %s expected=%s top1=%s score=%.1f"
                      % (miss["uid"], miss["expected_skill"], miss["top1"],
                         miss["top1_score"]))
            if len(misses) > 50:
                print("... and %d more misses (use --json for the full list)"
                      % (len(misses) - 50))
            print("")
        print("Hit@1          : %d / %d = %.2f%%" % (hits, total, rate))

    expected_hits = args.expect if args.expect is not None else total
    hashes_ok = False not in (file_ok, cases_ok, index_ok)
    passed = hits == expected_hits and hashes_ok

    if not args.quiet:
        if hits != expected_hits:
            print("RESULT         : FAIL (%d hits, expected %d)"
                  % (hits, expected_hits))
        elif not hashes_ok:
            print("RESULT         : FAIL (Hit@1 reproduced, but a recorded hash "
                  "does not match - the evidence is not the same evidence)")
        else:
            print("RESULT         : PASS")

    if args.json_out:
        report = {
            "case_set": os.path.basename(args.cases),
            "manifest_case_set": set_name,
            "cases": total,
            "hits": hits,
            "misses": len(misses),
            "hit1_rate": rate / 100.0,
            "sha256_cases_file": file_sha,
            "sha256_cases_content": cases_sha,
            "sha256_skill_index": index_sha,
            "skills_indexed": len(index),
            "hashes_match_manifest": hashes_ok,
            "passed": passed,
            "miss_detail": misses,
        }
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
