#!/usr/bin/env python3
"""Gate 5: deterministic offline Hit@1 eval for the skill router.

Router model (flat + tags, per research/briefs/03-router-design.md section 5
and docs/harness-contract.md gate 5): token-overlap scoring over tags
(weight 3), name (2), description (1), body (0.5), plus a phrase bonus (+4)
when a normalized query phrase appears verbatim in name+description. Top-1
by (score desc, skill path asc). Fully deterministic; no network.

What this gate executes
-----------------------
A single corpus file, or EVERY corpus file in a directory. eval/ holds
eval/hit1-corpus.yaml plus one eval/hit1-<slug>.yaml fragment per leaf. For a
long time this gate read only the first of those, so the per-leaf fragments --
the majority of the authored cases, and the only cases naming most leaves --
were graded by nothing at all. Pointing the gate at the directory executes all
of them, which is the whole point of authoring them.

Case ids are unique only within a fragment (504 ids are reused across files),
so every verdict is reported as `<file>#<id>`. Nothing has to be renamed for a
failure to be identifiable.

Performance note: the skill fields and each query are tokenized ONCE, not once
per (case, skill) pair. The arithmetic is unchanged -- the same four set
intersections against the same four token sets -- but the body of every skill
is no longer re-tokenized for every case, which is what made a full-corpus run
impractical before.

Usage: router_eval.py <corpus.yaml | eval_dir> <skills_dir>
Exit 0 = every task's top-1 equals expected_skill; 1 otherwise.
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
    """Index every SKILL.md, pre-tokenized into the four scoring sets."""
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
        name = fm.get("name", "") or ""
        description = fm.get("description", "") or ""
        skills[rel] = {
            "tags": set(str(t).lower() for t in (meta.get("tags") or [])),
            "name": set(tokens(name)),
            "description": set(tokens(description)),
            "body": set(tokens(parts[2] if len(parts) >= 3 else "")),
            "haystack": (name + " " + description).lower(),
        }
    return skills


def score(skill, query_tokens, phrase):
    """Score one skill against a pre-tokenized query."""
    s = 0.0
    s += 3.0 * len(query_tokens & skill["tags"])
    s += 2.0 * len(query_tokens & skill["name"])
    s += 1.0 * len(query_tokens & skill["description"])
    s += 0.5 * len(query_tokens & skill["body"])
    if phrase and phrase in skill["haystack"]:
        s += 4.0
    return s


def load_tasks(target):
    """[(label, task)] from one corpus file or every fragment in a directory."""
    path = pathlib.Path(target)
    if path.is_dir():
        files = sorted(path.glob("hit1-*.yaml"))
        if not files:
            print("FAIL gate5-hit1: no hit1-*.yaml under %s" % path, file=sys.stderr)
            sys.exit(1)
    else:
        files = [path]
    out = []
    for f in files:
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        tasks = doc.get("tasks") if isinstance(doc, dict) else None
        if not isinstance(tasks, list) or not tasks:
            print("FAIL gate5-hit1: %s has no non-empty 'tasks' list" % f.name,
                  file=sys.stderr)
            sys.exit(1)
        for t in tasks:
            if isinstance(t, dict):
                out.append(("%s#%s" % (f.name, t.get("id", "?")), t))
    if not out:
        print("FAIL gate5-hit1: no tasks found", file=sys.stderr)
        sys.exit(1)
    return out


def main():
    target = sys.argv[1]
    skills_root = pathlib.Path(sys.argv[2])
    labelled = load_tasks(target)
    skills = load_skills(skills_root)
    if not skills:
        print("FAIL gate5-hit1: no skills indexed under skills/", file=sys.stderr)
        sys.exit(1)

    items = list(skills.items())
    fail = 0
    for label, t in labelled:
        q = t.get("query", "")
        exp = t.get("expected_skill", "")
        if exp not in skills:
            print(
                "FAIL gate5-hit1: %s expected_skill '%s' not in skills tree"
                % (label, exp),
                file=sys.stderr,
            )
            fail = 1
            continue
        qt = set(tokens(q))
        phrase = " ".join(tokens(q))
        scored = [(score(s, qt, phrase), path) for path, s in items]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        top_score, top_path = scored[0]
        ok = top_path == exp
        print(
            "%s gate5-hit1: %s top1=%s score=%.1f expected=%s"
            % ("PASS" if ok else "FAIL", label, top_path, top_score, exp)
        )
        if not ok:
            fail = 1
    if fail:
        sys.exit(1)
    print(
        "PASS gate5-hit1: %d/%d tasks Hit@1 (deterministic offline router)"
        % (len(labelled), len(labelled))
    )


if __name__ == "__main__":
    main()
