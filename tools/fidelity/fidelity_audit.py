#!/usr/bin/env python3
"""Measure whether a leaf faithfully renders the clause it cites.

Everything else in this repository checks that the corpus is internally
consistent: that a calculator matches its own contract, that a count matches
the tree, that a gate can go red. None of it touches the one claim the whole
stack rests on -- that a leaf faithfully renders the clause it derives from.
That claim is a human judgement about a document this repository deliberately
does not contain, and until it is measured it is an assumption wearing the
clothes of a fact.

This tool measures it in three separable layers. They are reported apart and
never summed, because they are evidence of different kinds:

  L1  CITATION RESOLVABILITY  -- mechanical, census over every leaf.
      Does the document the leaf names exist in the source set, and does the
      clause number it cites exist in that document? Catches the gross
      failure: a citation pointing at nothing.

  L2  LEXICAL OVERLAP         -- mechanical, census over resolved citations.
      Do the content-bearing terms of the clause appear in the leaf's
      rendering of it? A weak signal and an honest one: high overlap proves
      nothing, but near-zero overlap on a resolved citation is a leaf talking
      about something else. It is a SCREEN, not a verdict.

  L3  SEMANTIC FIDELITY       -- judged, sampled, blind.
      Does the leaf's rendering say what the clause says? This needs a reader.
      The tool prepares a blind worksheet and scores the returned verdicts; it
      does not grade. A tool that both prepares and grades its own worksheet
      is the circularity this repository exists to refuse.

The worksheet carries PLANTED CONTROLS: a fraction of items pair a clause with
a paraphrase drawn from a different clause. The grader is not told which. If
the grader does not catch them, the run reports VOID rather than a score --
a grader nobody has seen fail would report FAITHFUL forever, which is the same
defect the negative-control doctrine exists to prevent, one level up.

SOURCE TEXT NEVER LEAVES THE MACHINE. The worksheet holds clause text so a
reader can judge; the RESULT holds only counts, rates and opaque item ids.
Write the worksheet outside the repository and delete it when the grading is
done.

Usage
    tools/fidelity/fidelity_audit.py census  --sources <dir>
    tools/fidelity/fidelity_audit.py worksheet --sources <dir> --sample 100 \
        --seed 20260921 --out /somewhere/outside/the/repo/worksheet.json
    tools/fidelity/fidelity_audit.py score   --worksheet <w.json> \
        --verdicts <v.json> --out tools/fidelity/results/run-<tag>.json

Offline. Deterministic given a seed. Standard library only, except that
reading a PDF needs an extractor: pdftotext if it is on PATH, otherwise
PyMuPDF or pdfminer if importable. Which one was used is recorded in every
result, because a different extractor is a different measurement.
"""

import argparse
import collections
import hashlib
import json
import math
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys

TOOL = "tools/fidelity/fidelity_audit.py"
TOOL_VERSION = "1.0.0"

# ─────────────────────────────────────────────────────────── citations ──

# An ECSS document identifier as the corpus writes it.
DOC_RE = re.compile(
    r"\bECSS-[EQMUS]-(?:ST|HB|AS)-\d{2}[A-Z]?(?:-\d{2}[A-Z]?)?(?:-Rev\.\d+)?[A-Z]?\b")

# A document identifier followed by a clause number, in any of the forms the
# corpus actually uses. Anchored on the document so a bare "5.2" in prose --
# a version number, a tolerance, a Cpk target -- is never mistaken for a
# clause reference. That mistake would inflate every number this tool reports.
CITE_RE = re.compile(
    DOC_RE.pattern.strip("\\b") +
    r"\s*(?:§|§§|Section|section|Clause|clause|cl\.)\s*"
    r"(\d+(?:\.\d+){1,4})")

STOP = set("""a an and are as at be been but by can clause does each for from has have
if in is it its may must not of on or shall should so such that the their then there
these this those to under use used using when where which while with within would you
your ecss section requirement requirements applicable""".split())


def normalise_doc(s):
    """Strip edition noise so a citation and a filename can be compared."""
    s = s.strip()
    s = re.sub(r"\.pdf$|\.txt$", "", s, flags=re.I)
    s = re.sub(r"\(.*?\)", "", s)                 # (31July2008)
    s = re.sub(r"\+.*$", "", s)                   # +Corrigendum1, +Corr.1
    # Editions are written four ways across the file set and the prose:
    # "-Rev.1", "_Rev.1", " Rev.1", "Rev1". None of them identifies a
    # different standard, and treating them as different was a real defect
    # here: 84 citations to one document resolved to nothing because its
    # filename used an underscore.
    s = re.sub(r"[-_ ]?Rev\.?\s*\d+", "", s, flags=re.I)
    s = re.sub(r"[-_ ]?Corr(?:igendum)?\.?\s*\d*", "", s, flags=re.I)
    return s.strip(" -_.").upper()


def find_sources(root):
    """Map a normalised document id to the file that holds it."""
    out = {}
    for p in sorted(pathlib.Path(root).rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".pdf", ".txt"):
            continue
        out.setdefault(normalise_doc(p.name), p)
    return out


def resolve_doc(doc, src):
    """(path, how) for a cited document id.

    'exact' means the citation named the edition. 'no-edition-letter' means it
    did not -- "ECSS-E-ST-32" where the standard is "ECSS-E-ST-32C". That is a
    real defect in the citation, because it does not identify which edition the
    leaf was written against, and it is a DIFFERENT defect from citing a clause
    that does not exist. Counting them together would hide both.
    """
    if doc in src:
        return src[doc], "exact"
    if doc and not doc[-1].isalpha():
        for letter in "ABCDEF":
            if doc + letter in src:
                return src[doc + letter], "no-edition-letter"
    return None, "unresolved"


# ──────────────────────────────────────────────────────────── extract ──

def _extractor():
    """Return (name, callable). Recorded in the result: a different extractor
    is a different measurement, and a silent fallback would hide that."""
    exe = shutil.which("pdftotext")
    if exe:
        def f(path):
            r = subprocess.run([exe, "-q", "-enc", "UTF-8", str(path), "-"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               check=False)
            return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
        return "pdftotext", f
    try:
        import fitz  # PyMuPDF
        def f(path):
            with fitz.open(str(path)) as d:
                return "\n".join(pg.get_text() for pg in d)
        return "pymupdf-%s" % getattr(fitz, "VersionBind", "?"), f
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text as _pm
        return "pdfminer", (lambda path: _pm(str(path)))
    except Exception:
        pass
    return None, None


def text_of(path, cache_dir, extract):
    """Extracted text for one source document, cached by content digest."""
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    cache = pathlib.Path(cache_dir) / (digest + ".txt")
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")
    t = extract(path)
    if t is None:
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(t, encoding="utf-8")
    return t


# ───────────────────────────────────────────────────────── clause index ──

# A clause heading. In every ECSS PDF checked, the extractor puts the clause
# NUMBER alone on one line and its TITLE on the next -- only 2 to 41 headings
# per document carry both on one line. An index that required both on one line
# found 3% of citations and looked like a finding about the corpus. It was a
# finding about the index.
NUM_LINE = re.compile(r"^[ \t]*(\d+(?:\.\d+){1,4})[ \t]*(.*)$")


def clause_index(text):
    """Map clause number -> (start, end) over the body of the document.

    The LAST occurrence wins. The same number appears in the table of contents
    at the front and, in a revised standard, in the list of changes; the clause
    itself comes after both.
    """
    lines = text.splitlines(keepends=True)
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln)

    cands = []
    for i, ln in enumerate(lines):
        m = NUM_LINE.match(ln)
        if not m:
            continue
        num, rest = m.group(1), m.group(2).strip()
        title = rest
        if not title:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                title = lines[j].strip()
        if not title or len(title) > 120:
            continue
        if title.count(".") > 6:                       # a contents dot leader
            continue
        if re.fullmatch(r"[\d\s.\-]+", title):          # a bare page number
            continue
        if not re.match(r"[A-Z(\"\u201c]", title):       # headings are capitalised;
            continue                                   # "where former Table 4-11..."
        cands.append((num, offs[i]))                   # is a change-log line

    last = {}
    for num, off in cands:
        last[num] = off
    ordered = sorted(last.items(), key=lambda kv: kv[1])
    out = {}
    for i, (num, s) in enumerate(ordered):
        e = ordered[i + 1][1] if i + 1 < len(ordered) else len(text)
        out[num] = (s, e)
    return out


def clause_text(text, span, limit=2600):
    """The clause as a reader should see it.

    ECSS PDFs are laid out with non-breaking spaces between almost every word,
    so a naive whitespace collapse leaves the text looking corrupted to a human
    grader and splits nothing for a term extractor.
    """
    s, e = span
    t = text[s:e].replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ")
    return re.sub(r"[ \t]+", " ", t).strip()[:limit]


# ──────────────────────────────────────────────────────────────── leaves ──

def leaves(skills_root):
    return sorted(pathlib.Path(skills_root).glob("*/*/*/SKILL.md"))


def split_leaf(path):
    t = path.read_text(encoding="utf-8", errors="replace")
    if t.startswith("---") and t.count("---") >= 2:
        _, fm, body = t.split("---", 2)
    else:
        fm, body = "", t
    m = re.search(r'(?m)^description:\s*"?(.*?)"?\s*$', fm)
    desc = m.group(1) if m else ""
    return fm, body, desc, t


def citations(path):
    """Every (doc, clause, rendering) the leaf asserts.

    The rendering is the paragraph the citation sits in plus the leaf's own
    description -- the description is the contract-bearing text a host reads to
    decide whether to invoke the leaf at all, so a description that misstates
    the clause is the most consequential kind of infidelity here.
    """
    fm, body, desc, whole = split_leaf(path)
    out = []
    paras = re.split(r"\n\s*\n", body)
    for para in paras:
        for m in CITE_RE.finditer(para):
            doc = normalise_doc(m.group(0).split("§")[0]
                                .split("Section")[0].split("section")[0]
                                .split("Clause")[0].split("clause")[0]
                                .split("cl.")[0])
            out.append({
                "doc": doc,
                "clause": m.group(1),
                "rendering": re.sub(r"\s+", " ", para).strip()[:2200],
                "description": re.sub(r"\s+", " ", desc)[:1200],
            })
    # de-duplicate (doc, clause) within a leaf, keeping the longest rendering
    best = {}
    for c in out:
        k = (c["doc"], c["clause"])
        if k not in best or len(c["rendering"]) > len(best[k]["rendering"]):
            best[k] = c
    return list(best.values())


def terms(s):
    return {w for w in re.findall(r"[a-z]{4,}", s.lower()) if w not in STOP}


# ──────────────────────────────────────────────────────────── statistics ──

def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - r) / d, 4), round((c + r) / d, 4)]


# ─────────────────────────────────────────────────────────────── census ──

def cmd_census(a):
    ext_name, extract = _extractor()
    if extract is None:
        sys.exit("FAIL: no PDF extractor. Install poppler (pdftotext) or PyMuPDF.")
    src = find_sources(a.sources)
    ls = leaves(a.skills)
    if not ls:
        sys.exit("FAIL: no leaves under %s" % a.skills)

    idx_cache, res = {}, []
    n_leaf_cited = 0
    for p in ls:
        cs = citations(p)
        if cs:
            n_leaf_cited += 1
        for c in cs:
            doc_path, how = resolve_doc(c["doc"], src)
            row = {"leaf": str(p.relative_to(a.skills)), "doc": c["doc"],
                   "clause": c["clause"], "doc_found": doc_path is not None,
                   "how": how, "clause_found": False, "overlap": None}
            if doc_path is not None:
                if doc_path not in idx_cache:
                    t = text_of(doc_path, a.cache, extract)
                    idx_cache[doc_path] = (t, clause_index(t) if t else {})
                t, idx = idx_cache[doc_path]
                span = idx.get(c["clause"])
                if span:
                    row["clause_found"] = True
                    ct = clause_text(t, span)
                    ours = c["rendering"] + " " + c["description"]
                    ta, tb = terms(ct), terms(ours)
                    row["overlap"] = (round(len(ta & tb) / len(ta), 4) if ta else None)
            res.append(row)

    n = len(res)
    docf = sum(1 for r in res if r["doc_found"])
    clf = sum(1 for r in res if r["clause_found"])
    ov = [r["overlap"] for r in res if r["overlap"] is not None]
    ov.sort()
    low = [r for r in res if r["overlap"] is not None and r["overlap"] < 0.10]

    out = {
        "tool": TOOL, "tool_version": TOOL_VERSION, "layer": "L1+L2 census",
        "generated_utc": a.now, "python": sys.version.split()[0],
        "extractor": ext_name,
        "corpus": {"root": a.skills, "leaves": len(ls),
                   "leaves_with_a_resolvable_citation_form": n_leaf_cited},
        "sources": {"root": str(a.sources), "documents": len(src)},
        "L1": {
            "citations": n,
            "document_resolved": docf,
            "document_resolved_rate": round(docf / n, 4) if n else 0,
            "cited_without_an_edition_letter":
                sum(1 for r in res if r["how"] == "no-edition-letter"),
            "clause_resolved": clf,
            "clause_resolved_rate": round(clf / n, 4) if n else 0,
            "clause_resolved_ci95": wilson(clf, n),
        },
        "L2": {
            "scored": len(ov),
            "median_overlap": round(ov[len(ov) // 2], 4) if ov else None,
            "p10_overlap": round(ov[int(len(ov) * 0.10)], 4) if ov else None,
            "below_0_10": len(low),
            "below_0_10_rate": round(len(low) / len(ov), 4) if ov else None,
            "note": ("Overlap is a screen, not a verdict. High overlap does not "
                     "establish fidelity; near-zero overlap on a resolved clause "
                     "marks a leaf worth reading by hand."),
        },
        "unresolved_documents": sorted(collections.Counter(
            r["doc"] for r in res if not r["doc_found"]).items(),
            key=lambda kv: -kv[1])[:25],
        "lowest_overlap_examples": [
            {"leaf": r["leaf"], "doc": r["doc"], "clause": r["clause"],
             "overlap": r["overlap"]}
            for r in sorted(low, key=lambda r: r["overlap"])[:25]],
    }
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    json.dump(out, sys.stdout, indent=1)
    print()


# ──────────────────────────────────────────────────────────── worksheet ──

def cmd_worksheet(a):
    ext_name, extract = _extractor()
    if extract is None:
        sys.exit("FAIL: no PDF extractor available.")
    src = find_sources(a.sources)
    rows = []
    for p in leaves(a.skills):
        for c in citations(p):
            c["leaf"] = str(p.relative_to(a.skills))
            rows.append(c)

    rnd = random.Random(a.seed)
    rnd.shuffle(rows)

    idx_cache, items, used = {}, [], 0
    n_controls = max(1, round(a.sample * a.control_rate))
    want = a.sample + n_controls

    resolved = []
    for c in rows:
        if len(resolved) >= want * 3:
            break
        dp, _how = resolve_doc(c["doc"], src)
        if dp is None:
            continue
        if dp not in idx_cache:
            t = text_of(dp, a.cache, extract)
            idx_cache[dp] = (t, clause_index(t) if t else {})
        t, idx = idx_cache[dp]
        span = idx.get(c["clause"])
        if not span:
            continue
        c["clause_text"] = clause_text(t, span)
        if len(c["clause_text"]) < 120:
            continue
        resolved.append(c)

    if len(resolved) < want:
        sys.exit("FAIL: only %d resolvable citations, need %d. Widen the sample "
                 "or check the source set." % (len(resolved), want))

    real = resolved[:a.sample]
    pool = resolved[a.sample:]
    for i, c in enumerate(real):
        items.append({"item": "F%04d" % (i + 1), "clause_text": c["clause_text"],
                      "leaf_rendering": c["rendering"],
                      "leaf_description": c["description"]})
    # planted controls: a real clause paired with another clause's rendering.
    for j in range(n_controls):
        cl = pool[j]
        other = pool[(j + len(pool) // 2) % len(pool)]
        items.append({"item": "F%04d" % (a.sample + j + 1),
                      "clause_text": cl["clause_text"],
                      "leaf_rendering": other["rendering"],
                      "leaf_description": other["description"]})
    # Control ids are fixed before the shuffle, so the order the grader sees
    # carries no signal about which items are planted.
    control_ids = {("F%04d" % (a.sample + j + 1)) for j in range(n_controls)}
    rnd.shuffle(items)

    worksheet = {
        "tool": TOOL, "tool_version": TOOL_VERSION, "layer": "L3 worksheet",
        "generated_utc": a.now, "seed": a.seed, "extractor": ext_name,
        "sample": a.sample, "planted_controls": n_controls,
        "instruction": (
            "For each item you are given the text of one standard clause and a "
            "rendering of it taken from a procedure library. Decide ONLY whether "
            "the rendering faithfully represents what that clause requires. "
            "faithful = a practitioner following the rendering would satisfy the "
            "clause and would not be led outside it. partial = correct as far as "
            "it goes but omits a requirement the clause imposes. unfaithful = it "
            "states something the clause does not require, contradicts it, or "
            "describes a different subject. unjudgeable = the clause text is too "
            "damaged by extraction to read. Return {item, verdict, reason}. Some "
            "pairs are deliberately mismatched; you are not told which."),
        "items": items,
    }
    keyfile = {"controls": sorted(control_ids), "seed": a.seed,
               "leaf_of": {("F%04d" % (i + 1)): c["leaf"] for i, c in enumerate(real)}}

    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(worksheet, indent=1), encoding="utf-8")
    kp = str(a.out).replace(".json", "") + ".key.json"
    pathlib.Path(kp).write_text(json.dumps(keyfile, indent=1), encoding="utf-8")
    print("worksheet %s   %d items (%d graded + %d planted controls)"
          % (a.out, len(items), a.sample, n_controls))
    print("key       %s   keep this away from the grader" % kp)
    print("SOURCE TEXT IS IN THE WORKSHEET. Do not commit it. Delete it after grading.")


# ──────────────────────────────────────────────────────────────── score ──

# "contested" is not a grade a reader gives. It is what the SCORER records when
# independent readers did not converge -- three passes, three different answers.
# Folding it into any of the other four would be inventing a verdict nobody
# reached, and folding it into "faithful" would be inventing the flattering one.
VERDICTS = ("faithful", "partial", "unfaithful", "unjudgeable", "contested")


def cmd_score(a):
    w = json.loads(pathlib.Path(a.worksheet).read_text(encoding="utf-8"))
    key = json.loads(pathlib.Path(a.key).read_text(encoding="utf-8"))
    v = json.loads(pathlib.Path(a.verdicts).read_text(encoding="utf-8"))
    got = {r["item"]: r["verdict"] for r in (v["verdicts"] if isinstance(v, dict) else v)}

    controls = set(key["controls"])
    bad = [k for k, val in got.items() if val not in VERDICTS]
    if bad:
        sys.exit("FAIL: %d verdict(s) outside %s: %s" % (len(bad), VERDICTS, bad[:5]))
    missing = [i["item"] for i in w["items"] if i["item"] not in got]
    if missing:
        sys.exit("FAIL: %d item(s) ungraded: %s" % (len(missing), missing[:5]))

    # The grader's own red-capability, measured before anything it says is used.
    c_caught = sum(1 for c in controls if got.get(c) in ("unfaithful", "partial"))
    c_total = len(controls)
    c_rate = c_caught / c_total if c_total else 0.0
    void = c_rate < a.control_floor

    graded = [i["item"] for i in w["items"] if i["item"] not in controls]
    counts = collections.Counter(got[i] for i in graded)
    judged = sum(counts[k] for k in ("faithful", "partial", "unfaithful"))
    faithful = counts["faithful"]
    # Worst case: every excluded item resolves against us. Reported alongside
    # the point estimate so the exclusions cannot quietly flatter it.
    excluded = counts["unjudgeable"] + counts["contested"]
    floor_den = judged + excluded

    out = {
        "tool": TOOL, "tool_version": TOOL_VERSION, "layer": "L3 fidelity",
        "generated_utc": a.now, "worksheet_seed": w.get("seed"),
        "extractor": w.get("extractor"),
        "grader": a.grader,
        "control": {
            "planted": c_total, "caught": c_caught, "catch_rate": round(c_rate, 4),
            "floor": a.control_floor,
            "verdict": "RED-CAPABLE" if not void else "VOID",
            "note": ("A grader that does not catch a deliberately mismatched pair "
                     "has not measured anything. Below the floor the run reports "
                     "VOID and says nothing about the corpus."),
        },
        "result": None if void else {
            "sampled": len(graded),
            "judged": judged,
            "unjudgeable": counts["unjudgeable"],
            "contested": counts["contested"],
            "faithful": faithful,
            "partial": counts["partial"],
            "unfaithful": counts["unfaithful"],
            "fidelity_rate": round(faithful / judged, 4) if judged else None,
            "fidelity_ci95": wilson(faithful, judged),
            "worst_case_rate": round(faithful / floor_den, 4) if floor_den else None,
            "worst_case_note": ("every excluded item counted as a miss -- the number "
                                "to quote if someone argues the exclusions are "
                                "self-serving"),
            "strict_note": ("fidelity_rate counts only 'faithful' as a pass. "
                            "'partial' is a miss: a rendering that omits a "
                            "requirement the clause imposes is how a supplier "
                            "ends up non-compliant while believing otherwise."),
        },
        "excluded_from_denominator": ["unjudgeable", "contested"],
    }
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    json.dump(out, sys.stdout, indent=1)
    print()
    if void:
        print("\nVOID -- control catch rate %.2f below floor %.2f. No fidelity "
              "number is reported." % (c_rate, a.control_floor), file=sys.stderr)
        sys.exit(2)


# ───────────────────────────────────────────────────────────────── main ──

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--now", default="", help="ISO timestamp, supplied by the caller "
                    "so the tool itself stays clock-free and reproducible")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--skills", default="skills")
        p.add_argument("--sources", required=True)
        p.add_argument("--cache", default=".fidelity-cache")

    c = sub.add_parser("census"); common(c); c.add_argument("--out")
    c.set_defaults(fn=cmd_census)

    w = sub.add_parser("worksheet"); common(w)
    w.add_argument("--sample", type=int, default=100)
    w.add_argument("--seed", type=int, required=True)
    w.add_argument("--control-rate", type=float, default=0.15)
    w.add_argument("--out", required=True)
    w.set_defaults(fn=cmd_worksheet)

    s = sub.add_parser("score")
    s.add_argument("--worksheet", required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--verdicts", required=True)
    s.add_argument("--grader", required=True, help="who or what graded it")
    s.add_argument("--control-floor", type=float, default=0.80)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_score)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
