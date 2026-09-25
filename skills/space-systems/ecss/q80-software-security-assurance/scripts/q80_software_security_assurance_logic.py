"""Software security assurance: the security-sensitivity dimension.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025). Revision 2 added clause 6.2.9
(software security analysis) and clause 6.2.10 (handling of security
sensitive software), plus security items in 5.2.6 (security representative
on the review board), 5.4.5 (security results passed to suppliers), 6.2.4
(integrity and authenticity), 6.2.7.3 (security of existing software) and
the category D exceptions in Annex D for security sensitive software.
Security is transversal: it applies by sensitivity, not by criticality
category. Paraphrased into checks; no requirement text is reproduced.

Procedure implemented here
--------------------------
1. Decide which components are security sensitive from the impacts the
   system security analysis assigns to them, against a project threshold.
2. List the clauses that apply because of sensitivity, including those
   that come back on for category D.
3. Spread sensitivity across links where a failure, deliberate or not, is
   not stopped, and flag pairs where criticality and sensitivity disagree
   so the conflict is analysed.
4. Check the additional measures chosen for sensitive software.
5. Decide, for each change event, whether regression testing is required
   or the need for more verification must be analysed.
6. Check a nonconformance review board for a security representative and a
   supplier package for the security results it must carry.
"""

__all__ = [
    "IMPACT_LEVELS",
    "SECURITY_MEASURES",
    "REGRESSION_TRIGGERS",
    "ANALYSE_TRIGGERS",
    "determine_sensitivity",
    "sensitivity_clauses",
    "propagate_sensitivity",
    "check_security_measures",
    "change_impact",
    "check_board_security",
    "check_supplier_security_package",
]

# Ordered impact scale for confidentiality, integrity and availability.
IMPACT_LEVELS = ("none", "low", "moderate", "high", "severe")

# Measures a project may add for security sensitive software on top of
# those it applies for critical software.
SECURITY_MEASURES = (
    "secure-coding-practice",
    "security-baseline",
    "fuzzing",
    "static-security-testing",
    "dynamic-security-testing",
    "vulnerability-assessment",
    "penetration-testing",
)

# Change events after which sensitive software is regression tested.
REGRESSION_TRIGGERS = (
    "platform-functionality-change",
    "build-tool-change",
    "operating-environment-security-change",
)

# Change events after which the need for more verification is analysed.
ANALYSE_TRIGGERS = (
    "platform-functionality-change",
    "platform-performance-change",
    "operating-environment-change",
    "threat-or-vulnerability-knowledge-change",
    "build-infrastructure-change",
)

_CATEGORIES = ("A", "B", "C", "D")


def _level(value):
    key = str(value or "none").strip().lower()
    if key not in IMPACT_LEVELS:
        raise ValueError("unknown impact level %r" % (value,))
    return IMPACT_LEVELS.index(key)


def determine_sensitivity(components, threshold="moderate"):
    """Decide which software components are security sensitive.

    components: mapping name -> dict with confidentiality, integrity and
        availability impact levels (from IMPACT_LEVELS) as assigned by the
        system security analysis.
    threshold: the level at or above which any single impact makes the
        component sensitive; a project decision agreed with the customer.

    Returns mapping name -> dict(sensitive, driver, level), where driver is
    the property with the highest impact.
    """
    limit = _level(threshold)
    out = {}
    for name, imp in sorted(dict(components).items()):
        best, driver = -1, None
        for prop in ("confidentiality", "integrity", "availability"):
            lvl = _level((imp or {}).get(prop))
            if lvl > best:
                best, driver = lvl, prop
        out[name] = {"sensitive": best >= limit, "driver": driver,
                     "level": IMPACT_LEVELS[best]}
    return out


def sensitivity_clauses(category, sensitive, uses_existing_software=False,
                        has_suppliers=False):
    """List the security clauses that apply for one software product.

    Returns a list of (clause, reason). Security clauses follow the
    sensitivity, not the category. For category D, the review of coding
    standards against security needs and the agreed test coverage goals
    come back on when the software is sensitive.
    """
    cat = str(category).strip().upper()
    if cat not in _CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (category,))
    out = [("6.2.9.1", "the assurance plan covers security assurance")]
    if has_suppliers:
        out.append(("5.4.5", "security results passed down to suppliers"))
    if uses_existing_software:
        out.append(("6.2.7.3", "existing software assessed for security"))
    if sensitive:
        out.extend([
            ("6.2.9.2-6.2.9.7", "software security analysis, updated each milestone"),
            ("6.2.10.1-6.2.10.4", "handling of security sensitive software"),
            ("6.2.4.8-6.2.4.10", "corruption protection, integrity and authenticity"),
            ("5.2.6.1", "security representative on the review board"),
        ])
        if cat == "D":
            out.append(("6.3.4.4", "coding standards reviewed for security despite category D"))
            out.append(("6.3.5.2", "test coverage goals agreed despite category D"))
    return out


def propagate_sensitivity(components, links):
    """Spread sensitivity over unstopped links and flag conflicts.

    components: mapping name -> dict(category, sensitive).
    links: list of dicts source, target, stopped (True when segregation or
        fail-secure isolation stops a failure or a deliberate action from
        crossing).

    A component that can affect a sensitive one over an unstopped link
    becomes sensitive. A conflict is reported for an unstopped pair where
    one side is more critical and the other more sensitive, because the
    security effect of the critical one and the safety effect of the
    sensitive one must both be analysed.

    Returns dict(sensitive: sorted names, added: names made sensitive,
    conflicts: sorted (a, b) pairs).
    """
    comps = {}
    for name, c in dict(components).items():
        cat = str(c.get("category", "")).upper()
        if cat not in _CATEGORIES:
            raise ValueError("component %s has an unknown category" % name)
        comps[name] = {"category": cat, "sensitive": bool(c.get("sensitive"))}
    live = []
    for link in links:
        s, t = link.get("source"), link.get("target")
        if s not in comps or t not in comps:
            raise ValueError("link names an unknown component: %r -> %r" % (s, t))
        if not link.get("stopped"):
            live.append((s, t))
    sensitive = {n for n, c in comps.items() if c["sensitive"]}
    original = set(sensitive)
    changed = True
    while changed:
        changed = False
        for s, t in live:
            if t in sensitive and s not in sensitive:
                sensitive.add(s)
                changed = True
    conflicts = set()
    for s, t in live:
        a, b = comps[s], comps[t]
        more_critical = _CATEGORIES.index(a["category"]) - _CATEGORIES.index(b["category"])
        sens_diff = (s in original) - (t in original)
        if more_critical and sens_diff and (more_critical > 0) == (sens_diff > 0):
            conflicts.add(tuple(sorted((s, t))))
    return {"sensitive": sorted(sensitive), "added": sorted(sensitive - original),
            "conflicts": sorted(conflicts)}


def check_security_measures(measures, sensitive):
    """Check the extra measures for security sensitive software.

    measures: mapping measure -> dict(justification, applied_evidence).
    Returns a dict with verdict ('met', 'not-met', 'not-applicable'),
    unknown, unjustified and not_applied measures.
    """
    if not sensitive:
        return {"verdict": "not-applicable", "unknown": [], "unjustified": [],
                "not_applied": []}
    unknown = sorted(m for m in measures if m not in SECURITY_MEASURES)
    known = {m: v or {} for m, v in measures.items() if m in SECURITY_MEASURES}
    unjustified = sorted(m for m, v in known.items() if not str(v.get("justification") or "").strip())
    not_applied = sorted(m for m, v in known.items() if not str(v.get("applied_evidence") or "").strip())
    ok = bool(known) and not unknown and not unjustified and not not_applied
    return {"verdict": "met" if ok else "not-met", "unknown": unknown,
            "unjustified": unjustified, "not_applied": not_applied}


def change_impact(event, minor_tool_change=False, binary_identical=None):
    """Decide what a change event means for security sensitive software.

    event: one of REGRESSION_TRIGGERS or ANALYSE_TRIGGERS.
    minor_tool_change / binary_identical: for a build tool change, a minor
    change whose output is shown bit-identical by binary comparison can
    stand in for the regression run.

    Returns dict(regression, analyse_more_vv, note).
    """
    known = set(REGRESSION_TRIGGERS) | set(ANALYSE_TRIGGERS)
    if event not in known:
        raise ValueError("unknown change event %r" % (event,))
    regression = event in REGRESSION_TRIGGERS
    note = ""
    if event == "build-tool-change" and minor_tool_change:
        if binary_identical is True:
            regression = False
            note = "binary comparison shows identical executable; record it as the evidence"
        else:
            note = "minor tool change: a binary comparison may replace the regression run"
    return {"regression": regression, "analyse_more_vv": event in ANALYSE_TRIGGERS,
            "note": note}


def check_board_security(item, board_members):
    """Check a nonconformance review board for the right representatives.

    item: dict with id and possible_security_impact (bool).
    board_members: list of dicts with name and role, roles including
        'software-product-assurance', 'software-engineering' and
        'software-security'.
    Returns the list of missing roles.
    """
    roles = {str(m.get("role", "")).lower() for m in board_members}
    need = ["software-product-assurance", "software-engineering"]
    if item.get("possible_security_impact"):
        need.append("software-security")
    return [r for r in need if r not in roles]


def check_supplier_security_package(package, sensitive):
    """Check what a lower-level supplier is told about security.

    package: dict with sensitivity_stated (bool), attack_and_failure_info
        (bool), security_requirements_flowed (bool).
    Returns the list of missing items; empty when the product is not
    sensitive and the sensitivity statement is present.
    """
    missing = []
    if not package.get("sensitivity_stated"):
        missing.append("security sensitivity of the product to be developed")
    if sensitive:
        if not package.get("attack_and_failure_info"):
            missing.append("failures, attacks and their higher-level security impact")
        if not package.get("security_requirements_flowed"):
            missing.append("security assurance requirements flowed down")
    return missing
