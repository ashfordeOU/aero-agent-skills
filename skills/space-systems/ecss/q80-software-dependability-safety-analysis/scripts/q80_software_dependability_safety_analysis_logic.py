"""Software dependability and safety analysis: the software contribution.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 6.2.2 (software
dependability and safety analysis feeding and fed by the system analyses,
the hardware-software interaction analysis, failure propagation between
components of different criticality) and clause 5.3.2 (critical item
control). Paraphrased into checks; no requirement text is reproduced.

Procedure implemented here
--------------------------
1. Grade a software failure modes and effects worksheet: every row names an
   effect and a severity; severe rows carry a mitigation traced to a
   requirement; the worst severity per component suggests its category.
2. Propagate criticality across interactions that are not prevented by
   segregation or partitioning: every component in a connected group takes
   the highest category in the group.
3. Check the hardware-software interaction analysis: every hardware failure
   is answered by a software requirement and that requirement is verified.
4. Track the analysis recommendations: which are open at a milestone, and
   which belong to the system level and must be exported upward.
5. Check that the analysis report was issued or updated at every milestone
   that owes it.
6. Propose candidates for the critical item list from the results.
"""

__all__ = [
    "CATEGORIES",
    "SEVERITY_TO_CATEGORY",
    "REPORT_MILESTONES",
    "normalise_category",
    "normalise_severity",
    "grade_sfmea",
    "propagate_criticality",
    "check_hsia_coverage",
    "track_recommendations",
    "check_analysis_currency",
    "critical_item_candidates",
]

CATEGORIES = ("A", "B", "C", "D")

# Severity of a failure consequence (I catastrophic .. IV minor) and the
# category software takes when it is involved in a function of that severity
# with no compensating provision in place.
SEVERITY_TO_CATEGORY = {"I": "A", "II": "B", "III": "C", "IV": "D"}

_SEVERITY_ALIASES = {
    "1": "I", "2": "II", "3": "III", "4": "IV",
    "catastrophic": "I", "critical": "II", "major": "III", "minor": "IV",
    "negligible": "IV",
}

# Milestones at which the software dependability and safety analysis report
# is owed: first issue at PDR, then an update at each later review.
REPORT_MILESTONES = ("pdr", "cdr", "qr", "ar")
_MILESTONE_ORDER = ("srr", "pdr", "cdr", "qr", "ar")


def normalise_category(value):
    """Return the category letter A to D; raise ValueError otherwise."""
    if not isinstance(value, str) or value.strip().upper() not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return value.strip().upper()


def normalise_severity(value):
    """Return the severity as a roman numeral I to IV; raise ValueError."""
    key = str(value).strip()
    if key.upper() in SEVERITY_TO_CATEGORY:
        return key.upper()
    key = key.lower()
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    raise ValueError("unknown severity %r" % (value,))


def _worse(cat_a, cat_b):
    """Return the stricter of two categories (A is the strictest)."""
    return min(cat_a, cat_b, key=CATEGORIES.index)


def grade_sfmea(rows):
    """Grade a software FMEA worksheet.

    rows: list of dicts with id, component, failure_mode, effect, severity
        (I-IV or alias), mitigation (text or empty) and requirement (the
        requirement that implements the mitigation, or empty).

    Severity I and II rows need a mitigation, and a mitigation needs a
    requirement that carries it into the specification. Returns a dict with
    findings (list of (row id, text)), worst severity per component and the
    category each component would take with no compensating provision,
    plus row_component (row id -> component) for later cross-reference.
    """
    findings = []
    worst = {}
    row_component = {}
    seen = set()
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if not rid or rid in seen:
            raise ValueError("row id missing or duplicated: %r" % (rid,))
        seen.add(rid)
        comp = str(row.get("component") or "").strip()
        if not comp:
            findings.append((rid, "no component named"))
            continue
        row_component[rid] = comp
        if not str(row.get("failure_mode") or "").strip():
            findings.append((rid, "no failure mode described"))
        if not str(row.get("effect") or "").strip():
            findings.append((rid, "no effect stated, so the severity is unsupported"))
        try:
            sev = normalise_severity(row.get("severity"))
        except ValueError:
            findings.append((rid, "severity missing or unknown"))
            continue
        mitigation = str(row.get("mitigation") or "").strip()
        requirement = str(row.get("requirement") or "").strip()
        if sev in ("I", "II") and not mitigation:
            findings.append((rid, "severity %s failure mode without a mitigation" % sev))
        if mitigation and not requirement:
            findings.append((rid, "mitigation not traced to a requirement"))
        prev = worst.get(comp)
        if prev is None or ("I", "II", "III", "IV").index(sev) < ("I", "II", "III", "IV").index(prev):
            worst[comp] = sev
    return {
        "findings": findings,
        "worst_severity": dict(sorted(worst.items())),
        "suggested_category": {c: SEVERITY_TO_CATEGORY[s] for c, s in sorted(worst.items())},
        "row_component": row_component,
    }


def propagate_criticality(components, interactions):
    """Raise components that can cause failures in more critical ones.

    components: mapping name -> category.
    interactions: list of dicts with source, target, mechanism
        ('failure-propagation' or 'shared-resource') and prevented (True when
        segregation or partitioning is shown to stop the failure crossing).

    Components linked by interactions that are not prevented form a group;
    every member of the group takes the strictest category in it. Returns a
    dict with effective (name -> category) and raised (list of (name, from,
    to, via)) where via is the sorted group.
    """
    cats = {name: normalise_category(c) for name, c in dict(components).items()}
    parent = {name: name for name in cats}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for link in interactions:
        src, dst = link.get("source"), link.get("target")
        if src not in cats or dst not in cats:
            raise ValueError("interaction names an unknown component: %r -> %r" % (src, dst))
        mech = link.get("mechanism", "failure-propagation")
        if mech not in ("failure-propagation", "shared-resource"):
            raise ValueError("unknown interaction mechanism %r" % (mech,))
        if link.get("prevented"):
            continue
        ra, rb = find(src), find(dst)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for name in cats:
        groups.setdefault(find(name), []).append(name)
    effective, raised = {}, []
    for members in groups.values():
        top = cats[members[0]]
        for m in members:
            top = _worse(top, cats[m])
        for m in members:
            effective[m] = top
            if top != cats[m]:
                raised.append((m, cats[m], top, sorted(members)))
    return {"effective": dict(sorted(effective.items())), "raised": sorted(raised)}


def check_hsia_coverage(hardware_failures, requirement_map, verification):
    """Check the software side of the hardware-software interaction analysis.

    hardware_failures: iterable of hardware failure ids in the HSIA.
    requirement_map: mapping failure id -> list of software requirement ids
        that state how the software behaves when that failure occurs.
    verification: mapping requirement id -> 'pass', 'fail' or 'not-run'.

    Returns a dict with uncovered failures (no requirement), unverified
    requirements (no result or not run), failed requirements and a verdict
    'complete' or 'incomplete'.
    """
    uncovered, unverified, failed = [], set(), set()
    for hf in hardware_failures:
        reqs = [r for r in (requirement_map.get(hf) or []) if str(r).strip()]
        if not reqs:
            uncovered.append(hf)
            continue
        for r in reqs:
            result = str(verification.get(r, "not-run")).lower()
            if result == "fail":
                failed.add(r)
            elif result != "pass":
                unverified.add(r)
    complete = not uncovered and not unverified and not failed
    return {
        "uncovered": sorted(uncovered),
        "unverified": sorted(unverified),
        "failed": sorted(failed),
        "verdict": "complete" if complete else "incomplete",
    }


def track_recommendations(recommendations, milestone):
    """Report the status of analysis recommendations at a milestone.

    recommendations: list of dicts with id, level ('software' or 'system'),
        status ('open', 'implemented', 'verified', 'rejected'), due (the
        milestone by which it must be verified) and rationale (needed when
        rejected).

    A recommendation is overdue when its due milestone is at or before the
    given one and it is not verified (or rejected with a rationale).
    System-level recommendations are listed for export to the system
    dependability and safety analyses.
    """
    ms = str(milestone).strip().lower()
    if ms not in _MILESTONE_ORDER:
        raise ValueError("unknown milestone %r" % (milestone,))
    now = _MILESTONE_ORDER.index(ms)
    overdue, export, bad_reject = [], [], []
    counts = {}
    for rec in recommendations:
        rid = rec.get("id")
        status = str(rec.get("status", "open")).lower()
        if status not in ("open", "implemented", "verified", "rejected"):
            raise ValueError("recommendation %s has unknown status %r" % (rid, status))
        counts[status] = counts.get(status, 0) + 1
        if rec.get("level") == "system":
            export.append(rid)
        if status == "rejected" and not str(rec.get("rationale") or "").strip():
            bad_reject.append(rid)
        due = str(rec.get("due", "")).lower()
        if due in _MILESTONE_ORDER and _MILESTONE_ORDER.index(due) <= now:
            if status not in ("verified", "rejected"):
                overdue.append(rid)
    return {
        "counts": dict(sorted(counts.items())),
        "overdue": sorted(overdue),
        "export_to_system": sorted(export),
        "rejected_without_rationale": sorted(bad_reject),
    }


def check_analysis_currency(issues, milestone):
    """Check the analysis report was issued or updated at each review due.

    issues: mapping milestone -> report issue identifier (or empty).
    milestone: the review now being prepared.

    Returns the list of owed milestones up to and including the given one
    that have no report issue, plus 'stale' when the same issue identifier
    is presented at two milestones (an update was not made).
    """
    ms = str(milestone).strip().lower()
    if ms not in _MILESTONE_ORDER:
        raise ValueError("unknown milestone %r" % (milestone,))
    now = _MILESTONE_ORDER.index(ms)
    norm = {str(k).lower(): str(v or "").strip() for k, v in dict(issues).items()}
    missing, stale = [], []
    previous = None
    for m in REPORT_MILESTONES:
        if _MILESTONE_ORDER.index(m) > now:
            break
        issue = norm.get(m, "")
        if not issue:
            missing.append(m)
        elif previous is not None and issue == previous:
            stale.append(m)
        if issue:
            previous = issue
    return {"missing": missing, "stale": stale, "current": not missing and not stale}


def critical_item_candidates(effective_categories, sfmea_result=None, hsia_result=None,
                             new_technology=()):
    """Propose software items for the critical item list.

    A component is proposed when its effective category is A or B, when it
    carries an unmitigated severity I or II failure mode, when an HSIA
    requirement tracing to it failed or is unverified, or when it relies on
    a technology new to the supplier. The criteria are the supplier's to
    state; these defaults are a starting point for the human reviewer.

    effective_categories: mapping component -> category.
    sfmea_result: output of grade_sfmea, optional.
    hsia_result: output of check_hsia_coverage plus an optional
        'requirement_owner' mapping requirement -> component.
    new_technology: components using a technology new to the supplier.

    Returns a sorted list of (component, [reasons]).
    """
    reasons = {}

    def add(comp, why):
        reasons.setdefault(comp, []).append(why)

    for comp, cat in dict(effective_categories).items():
        if normalise_category(cat) in ("A", "B"):
            add(comp, "effective category %s" % normalise_category(cat))
    if sfmea_result:
        rows_without = {rid for rid, text in sfmea_result.get("findings", [])
                        if "without a mitigation" in text}
        comp_of = sfmea_result.get("row_component", {})
        for rid in sorted(rows_without):
            if rid in comp_of:
                add(comp_of[rid], "unmitigated severe failure mode %s" % rid)
    if hsia_result:
        owner = hsia_result.get("requirement_owner", {})
        for req in list(hsia_result.get("failed", [])) + list(hsia_result.get("unverified", [])):
            if req in owner:
                add(owner[req], "HSIA requirement %s not shown to pass" % req)
    for comp in new_technology:
        add(comp, "technology new to the supplier")
    return sorted((c, sorted(set(r))) for c, r in reasons.items())
