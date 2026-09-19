"""Off-the-shelf item evaluation dossier: append-only accumulation and coverage.

Anchor: ECSS-Q-ST-20-10C clause 5.1.3 and its Annex B data-requirement
description (maintain, per candidate, the dossier that accumulates the evidence
of every evaluation performed). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every evaluation entry: which candidate it belongs to, which Annex B
   section it populates, what it concluded, when, and the source reference the
   conclusion rests on. An entry with no source reference is an assertion.
2. Accumulate entries append-only. A later evaluation of the same subject does
   not overwrite the earlier one; it supersedes it by carrying a higher revision,
   and the superseded entry stays in the dossier as history.
3. Report, per candidate, which Annex B sections are covered by a current entry
   and which are still open ground.
4. Grade a current entry older than its validity window as stale rather than
   counting it as coverage, and surface every unresolved outcome as an open
   finding the dossier still owes a closure entry for.
"""

import datetime

__all__ = [
    "OUTCOMES",
    "DEFAULT_DRD_SECTIONS",
    "DEFAULT_VALIDITY_DAYS",
    "parse_iso_date",
    "validate_entry",
    "new_dossier",
    "add_entry",
    "current_entries",
    "superseded_entries",
    "candidates",
    "coverage",
    "stale_entries",
    "open_findings",
    "assess_dossier",
]

OUTCOMES = ("pass", "fail", "open", "not-applicable")

# The Annex B evaluation dossier sections, paraphrased as the subjects an
# off-the-shelf candidate owes evidence on before it can be selected.
DEFAULT_DRD_SECTIONS = (
    "item-identification",
    "functional-evaluation",
    "performance-evaluation",
    "interface-evaluation",
    "quality-and-reliability-evidence",
    "obsolescence-and-supply-assessment",
    "deviation-and-limitation-record",
)

DEFAULT_VALIDITY_DAYS = 730


def parse_iso_date(value, label="date"):
    """Return an ISO-8601 calendar date, refusing anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO-8601 date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO-8601 calendar date: %r" % (label, value))


def validate_entry(entry):
    """Return one normalised evaluation-dossier entry."""
    if not isinstance(entry, dict):
        raise ValueError("a dossier entry must be a mapping")
    ident = entry.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("entry id must be a non-empty string")
    candidate = entry.get("candidate")
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("entry %s must name the candidate it evaluates" % ident)
    section = entry.get("section")
    if not isinstance(section, str) or not section.strip():
        raise ValueError("entry %s must name the dossier section it populates" % ident)
    outcome = entry.get("outcome")
    if outcome not in OUTCOMES:
        raise ValueError("entry %s has outcome %r, expected one of %s"
                         % (ident, outcome, ", ".join(OUTCOMES)))
    evidence = entry.get("evidence_ref")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("entry %s carries no evidence reference; a conclusion "
                         "with no source behind it is an assertion" % ident)
    revision = entry.get("revision", 1)
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise ValueError("entry %s revision must be an integer" % ident)
    if revision < 1:
        raise ValueError("entry %s revision must be 1 or greater" % ident)
    return {
        "id": ident.strip(),
        "candidate": candidate.strip(),
        "section": section.strip(),
        "outcome": outcome,
        "evidence_ref": evidence.strip(),
        "date": parse_iso_date(entry.get("date"), "entry %s date" % ident),
        "revision": revision,
        "superseded_by": None,
        "note": entry.get("note"),
    }


def new_dossier():
    """Return an empty dossier."""
    return {"entries": []}


def add_entry(dossier, entry):
    """Append one entry to the dossier without ever overwriting an earlier one."""
    if not isinstance(dossier, dict) or not isinstance(dossier.get("entries"), list):
        raise ValueError("dossier must be a mapping carrying an 'entries' list")
    record = validate_entry(entry)
    for existing in dossier["entries"]:
        if existing["id"] == record["id"] and existing["revision"] == record["revision"]:
            raise ValueError("entry %s revision %d is already in the dossier; a new "
                             "evaluation supersedes by a higher revision"
                             % (record["id"], record["revision"]))
    predecessors = [e for e in dossier["entries"] if e["id"] == record["id"]]
    if predecessors:
        latest = max(predecessors, key=lambda e: e["revision"])
        if record["revision"] <= latest["revision"]:
            raise ValueError("entry %s revision %d does not supersede the standing "
                             "revision %d" % (record["id"], record["revision"],
                                              latest["revision"]))
        if record["candidate"] != latest["candidate"]:
            raise ValueError("entry %s revision %d moves the entry to a different "
                             "candidate; file a new entry instead"
                             % (record["id"], record["revision"]))
        for older in predecessors:
            if older["superseded_by"] is None:
                older["superseded_by"] = record["revision"]
    dossier["entries"].append(record)
    return record


def current_entries(dossier, candidate=None):
    """Return the entries not superseded by a later revision."""
    if not isinstance(dossier, dict) or not isinstance(dossier.get("entries"), list):
        raise ValueError("dossier must be a mapping carrying an 'entries' list")
    out = [e for e in dossier["entries"] if e["superseded_by"] is None]
    if candidate is not None:
        out = [e for e in out if e["candidate"] == candidate]
    return sorted(out, key=lambda e: (e["candidate"], e["section"], e["id"]))


def superseded_entries(dossier):
    """Return the retained history: entries a later revision replaced."""
    if not isinstance(dossier, dict) or not isinstance(dossier.get("entries"), list):
        raise ValueError("dossier must be a mapping carrying an 'entries' list")
    return sorted((e for e in dossier["entries"] if e["superseded_by"] is not None),
                  key=lambda e: (e["id"], e["revision"]))


def candidates(dossier):
    """Return the candidate names the dossier holds evidence on."""
    return sorted({e["candidate"] for e in dossier.get("entries", [])})


def coverage(dossier, candidate, required_sections=DEFAULT_DRD_SECTIONS):
    """Return the covered and missing dossier sections for one candidate."""
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("candidate must be a non-empty string")
    sections = tuple(required_sections or ())
    if not sections:
        raise ValueError("required_sections must name at least one section")
    held = {e["section"] for e in current_entries(dossier, candidate.strip())}
    covered = [s for s in sections if s in held]
    missing = [s for s in sections if s not in held]
    extra = sorted(held - set(sections))
    return {
        "candidate": candidate.strip(),
        "covered": covered,
        "missing": missing,
        "outside_the_drd": extra,
        "ratio": len(covered) / float(len(sections)),
    }


def stale_entries(dossier, as_of, validity_days=DEFAULT_VALIDITY_DAYS):
    """Return the current entries whose evidence has aged past its validity window."""
    if isinstance(validity_days, bool) or not isinstance(validity_days, int):
        raise ValueError("validity_days must be an integer")
    if validity_days < 1:
        raise ValueError("validity_days must be 1 or greater")
    today = parse_iso_date(as_of, "as_of")
    stale = []
    for entry in current_entries(dossier):
        if entry["date"] > today:
            raise ValueError("entry %s is dated after the as-of date" % entry["id"])
        if (today - entry["date"]).days > validity_days:
            stale.append(entry)
    return stale


def open_findings(dossier, candidate=None):
    """Return the current entries whose outcome is unresolved or negative."""
    return [e for e in current_entries(dossier, candidate)
            if e["outcome"] in ("open", "fail")]


def assess_dossier(spec):
    """Run the full clause 5.1.3 dossier assessment.

    spec keys: entries (list), as_of (ISO date), optional required_sections and
    validity_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("entries", "as_of"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if not isinstance(spec["entries"], (list, tuple)):
        raise ValueError("spec['entries'] must be a sequence of dossier entries")
    sections = tuple(spec.get("required_sections") or DEFAULT_DRD_SECTIONS)
    validity = spec.get("validity_days", DEFAULT_VALIDITY_DAYS)
    as_of = parse_iso_date(spec["as_of"], "as_of")
    dossier = new_dossier()
    for entry in spec["entries"]:
        add_entry(dossier, entry)
    stale = stale_entries(dossier, as_of, validity)
    stale_ids = {e["id"] for e in stale}
    report = {}
    for name in candidates(dossier):
        cover = coverage(dossier, name, sections)
        findings = open_findings(dossier, name)
        stale_here = [e["id"] for e in current_entries(dossier, name)
                      if e["id"] in stale_ids]
        if cover["missing"]:
            verdict = "incomplete"
        elif stale_here:
            verdict = "stale-evidence"
        elif findings:
            verdict = "open-findings"
        else:
            verdict = "complete"
        report[name] = {
            "coverage": cover,
            "open_findings": [e["id"] for e in findings],
            "stale": stale_here,
            "verdict": verdict,
        }
    complete = sorted(n for n, r in report.items() if r["verdict"] == "complete")
    return {
        "as_of": as_of.isoformat(),
        "required_sections": list(sections),
        "candidates": report,
        "history_retained": len(superseded_entries(dossier)),
        "entries_held": len(dossier["entries"]),
        "complete_candidates": complete,
        "any_complete": bool(complete),
    }
