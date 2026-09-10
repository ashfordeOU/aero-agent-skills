#!/usr/bin/env python3
"""verify-independence.py — enforce VERIFIER INDEPENDENCE across artifacts.

Rule (founder 2026-09-10, from the OpenAI Navier-Stokes drop): the agent or
process that VERIFIES an artifact must be independent of the one that
GENERATED it. No bot grades its own output. A verifier may be a different
model, a different agent, or (best) a deterministic non-LLM check.

This is the mechanical form of that rule. It inspects the two artifact kinds
that carry generator/verifier metadata today:

  1. CLAIMS LEDGERS (*.md with a pipe table containing generator|verification|
     verifier columns) — see knowledge/claims/claims.md.
  2. EVIDENCE BUNDLES (a directory holding model.json + gates.json) — the
     roles protocol (docs/PROTOCOL.md). gates.checker is the verifier;
     model.generator / provenance.generator is the generator.

Fails when:
  * a generator or verifier is missing from a record
  * verifier == generator, or one names the other (not independent)
  * the verifier is a self-reference ("self", "own output", ...)
  * the verifier names an LLM model while the generator names the same model
    (correlated error: an LLM cannot independently check its own output)

Deterministic verifiers (a script, test, hash, count) always pass — they are
independent of any model by construction.

Exit 0 = clean (or nothing to check), 1 = violation(s).
Usage:
  python3 verify-independence.py <file-or-dir> [<file-or-dir> ...]
  python3 verify-independence.py --quiet <path>
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

SELF_WORDS = ("self", "same model", "same bot", "own output", "author",
              "generator itself", "itself")
DETERMINISTIC_HINTS = ("test", "audit", "hash", "count", "byte", "clock",
                       "parity", "gate", "checker.py", "lint", "schema",
                       "compile", "sandbox", "verify.sh", "ci.sh")
ARTIFACT_RE = re.compile(r"\.(py|sh|md|json|yaml|yml|lean|txt|csv|npz|parquet)\b")
# a token that looks like a model id (llm-ish), used for correlated-error check
MODEL_RE = re.compile(r"\b(gpt|claude|gemini|deepseek|llama|qwen|mistral|sonnet|opus|haiku|grok|kimi)[\w.\-]*\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def check_pair(generator: str, verifier: str, label: str) -> list[str]:
    """Core independence rules for one (generator, verifier) pair."""
    out: list[str] = []
    g, v = norm(generator), norm(verifier)
    if not g:
        out.append(f"{label}: missing generator")
    if not v:
        out.append(f"{label}: missing verifier")
        return out
    if g and v:
        if v == g:
            out.append(f"{label}: verifier == generator ('{generator}') — not independent")
        elif g in v or v in g:
            out.append(f"{label}: verifier names the generator — not independent")
    if any(w in v for w in SELF_WORDS):
        out.append(f"{label}: verifier is a self-reference ('{verifier}')")
    # correlated-error guard: same model family on both sides
    gm, vm = MODEL_RE.findall(str(generator)), MODEL_RE.findall(str(verifier))
    if gm and vm and any(a.lower() == b.lower() for a in gm for b in vm):
        out.append(f"{label}: verifier is the same LLM family as the generator "
                   f"('{generator}' vs '{verifier}') — correlated error")
    return out


def check_claims_md(path: str) -> tuple[int, list[str]]:
    """Validate a claims ledger's generator/verifier pairs.

    Columns are resolved BY NAME from the header row, so any ledger layout
    (the veda 10-column ledger, the ECSS 9-column ledger, reordered columns)
    is handled the same way. A ledger with no generator/verifier columns is
    not a claims ledger and is skipped.
    """
    text = open(path, encoding="utf-8").read()
    rows, probs = 0, []
    idx = None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip().lower() for c in s.strip("|").split("|")]
        if idx is None:
            if "verifier" in cells and "generator" in cells:
                idx = {"generator": cells.index("generator"),
                       "verifier": cells.index("verifier"),
                       "id": cells.index("id") if "id" in cells else 0}
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        raw = [c.strip() for c in s.strip("|").split("|")]
        if len(raw) <= max(idx.values()):
            continue
        rows += 1
        label = f"{os.path.basename(path)}:{raw[idx['id']]}"
        probs += check_pair(raw[idx["generator"]], raw[idx["verifier"]], label)
    return rows, probs


def check_evidence_dir(d: str) -> tuple[int, list[str]]:
    model_p, gates_p = os.path.join(d, "model.json"), os.path.join(d, "gates.json")
    if not (os.path.exists(model_p) and os.path.exists(gates_p)):
        return 0, []
    try:
        model = json.load(open(model_p))
        gates = json.load(open(gates_p))
    except Exception as e:
        return 0, [f"{d}: unreadable evidence bundle ({e})"]
    gen = model.get("generator") or model.get("generated_by") or model.get("role") or ""
    vfy = gates.get("checker") or ""
    return 1, check_pair(gen, vfy, os.path.relpath(d))


def walk(paths: list[str]) -> tuple[int, list[str]]:
    records, probs = 0, []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".md") and "claim" in p.lower():
            r, pr = check_claims_md(p)
            records += r
            probs += pr
        elif os.path.isdir(p):
            if os.path.exists(os.path.join(p, "gates.json")):
                r, pr = check_evidence_dir(p)
                records += r
                probs += pr
            for root, dirs, files in os.walk(p):
                dirs[:] = [x for x in dirs if x not in {".git", "__pycache__", "node_modules"}]
                if "gates.json" in files and "model.json" in files:
                    r, pr = check_evidence_dir(root)
                    records += r
                    probs += pr
                for f in files:
                    if f.endswith(".md") and "claim" in f.lower():
                        r, pr = check_claims_md(os.path.join(root, f))
                        records += r
                        probs += pr
        elif os.path.isfile(p) and p.endswith(".md"):
            r, pr = check_claims_md(p)
            records += r
            probs += pr
    return records, probs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    records, problems = walk(args.paths)
    if not args.quiet:
        print(f"verify-independence: {records} record(s) checked")
        for p in problems:
            print(f"  - {p}")
        print("VERDICT: " + ("PASS — verifiers independent" if not problems
                             else f"FAIL — {len(problems)} violation(s)"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
