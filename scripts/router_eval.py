#!/usr/bin/env python3
"""Gate 5: deterministic offline Hit@1 eval for the skill router.

Router model (flat + tags, per research/briefs/03-router-design.md section 5
and docs/harness-contract.md gate 5): token-overlap scoring over tags
(weight 3), name (2), description (1), body (0.5), plus a phrase bonus (+4)
when a normalized query phrase appears verbatim in name+description. Top-1
by (score desc, skill path asc). Fully deterministic; no network.

Usage: router_eval.py <corpus.yaml> <skills_dir>
Exit 0 = every corpus task's top-1 equals expected_skill; 1 otherwise.
"""

import pathlib
import re
import sys

import yaml

STOP = {
    "a", "an", "the", "for", "or", "and", "of", "to", "in", "on", "with",
    "is", "are", "was", "be", "at", "by", "from", "as", "into", "onto",
    "under", "over", "per", "via", "it", "its", "this", "that", "these",
    "those", "their", "our", "we", "you", "your", "do", "does", "did",
    "can", "could", "should", "would", "will", "shall", "must", "not", "no",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def tokens(text):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


def load_skills(root):
    skills = {}
    for p in sorted(pathlib.Path(root).rglob("SKILL.md")):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        try:
            fm = yaml.safe_load(parts[1])
        except Exception:  # noqa: BLE001
            fm = None
        if not isinstance(fm, dict):
            continue
        rel = str(p.parent.relative_to(root))
        meta = fm.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        skills[rel] = {
            "name": fm.get("name", "") or "",
            "description": fm.get("description", "") or "",
            "tags": [str(t).lower() for t in (meta.get("tags") or [])],
            "body": parts[2] if len(parts) >= 3 else "",
        }
    return skills


def score(skill, query):
    s = 0.0
    q = set(tokens(query))
    if not q:
        return 0.0
    name_t = set(tokens(skill["name"]))
    desc_t = set(tokens(skill["description"]))
    body_t = set(tokens(skill["body"]))
    tag_t = set(skill["tags"])
    s += 3.0 * len(q & tag_t)
    s += 2.0 * len(q & name_t)
    s += 1.0 * len(q & desc_t)
    s += 0.5 * len(q & body_t)
    phrase = " ".join(tokens(query))
    haystack = (skill["name"] + " " + skill["description"]).lower()
    if phrase and phrase in haystack:
        s += 4.0
    return s


def main():
    corpus_path = pathlib.Path(sys.argv[1])
    skills_root = pathlib.Path(sys.argv[2])
    corpus = yaml.safe_load(corpus_path.read_text(encoding="utf-8"))
    tasks = corpus.get("tasks") if isinstance(corpus, dict) else None
    if not isinstance(tasks, list) or not tasks:
        print("FAIL gate5-hit1: corpus has no non-empty 'tasks' list", file=sys.stderr)
        sys.exit(1)
    skills = load_skills(skills_root)
    if not skills:
        print("FAIL gate5-hit1: no skills indexed under skills/", file=sys.stderr)
        sys.exit(1)
    fail = 0
    for t in tasks:
        q = t.get("query", "")
        exp = t.get("expected_skill", "")
        if exp not in skills:
            print(
                "FAIL gate5-hit1: %s expected_skill '%s' not in skills tree"
                % (t.get("id", "?"), exp),
                file=sys.stderr,
            )
            fail = 1
            continue
        scored = [(score(s, q), path) for path, s in skills.items()]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        top_score, top_path = scored[0]
        ok = top_path == exp
        print(
            "%s gate5-hit1: %s top1=%s score=%.1f expected=%s"
            % ("PASS" if ok else "FAIL", t.get("id", "?"), top_path, top_score, exp)
        )
        if not ok:
            fail = 1
    if fail:
        sys.exit(1)
    print(
        "PASS gate5-hit1: %d/%d tasks Hit@1 (deterministic offline router)"
        % (len(tasks), len(tasks))
    )


if __name__ == "__main__":
    main()
