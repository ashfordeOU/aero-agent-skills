"""Software product assurance programme and its plan (SPAP).

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 5 (the software product
assurance programme: organisation and responsibility, programme management,
risk and critical items, supplier selection and control, procurement, tools
and supporting environment, assessment and improvement) and Annex B, the
document requirements definition (DRD) of the software product assurance
plan. The DRD outline is held here as section numbers and short topics of our
own wording; no requirement text is reproduced.

Procedure implemented here
--------------------------
1. Hold the plan outline as section ids with a topic, the clause groups each
   section answers, and whether the section is conditional.
2. Grade a draft plan against the outline: missing sections, sections too
   thin to answer their clauses, conditional sections that are in scope, and
   a coverage fraction.
3. Check the organisation the plan describes: a named assurance lead, a
   reporting line that does not run through the development lead, no dual
   role, and supplier delegation that is backed by the supplier's own plan.
4. Check the control of each supplier: category flowed down, assurance
   requirements flowed down, supplier plan received, pre-award assessment,
   and monitoring proportionate to the category.
5. Check the methods and tools: which tools can change or hide a defect in
   the executable, and the evidence each needs for the category.
6. Say what maturity the plan owes at each review.
"""

__all__ = [
    "CATEGORIES",
    "SPAP_OUTLINE",
    "MIN_WORDS_PER_SECTION",
    "PLAN_MATURITY_BY_REVIEW",
    "normalise_category",
    "normalise_section_id",
    "outline_section",
    "assess_spap",
    "check_organisation",
    "check_supplier_control",
    "assess_tools",
    "plan_maturity_due",
]

CATEGORIES = ("A", "B", "C", "D")

# (section id, topic in our words, clause groups answered, condition or None)
SPAP_OUTLINE = (
    ("1", "purpose, objective and reason for the plan", ("5.2.1",), None),
    ("2", "applicable and reference documents", ("5.2.1",), None),
    ("3", "terms and abbreviations used", (), None),
    ("4", "the system and the software products covered", ("5.4.4",), None),
    ("5", "assurance programme implementation", ("5",), None),
    ("5.1", "organisation of the assurance function and its independence", ("5.1.1", "5.1.2"), None),
    ("5.2", "responsibilities of the assurance function", ("5.1.2",), None),
    ("5.3", "resources, people, skills and facilities", ("5.1.3", "5.1.4", "5.1.5"), None),
    ("5.4", "assurance reporting: content, recipients and cadence", ("5.2.2",), None),
    ("5.5", "quality model and quality characteristics chosen", ("5.2.7",), None),
    ("5.6", "risk management and critical item control", ("5.3",), None),
    ("5.7", "supplier selection, flow-down and monitoring", ("5.4", "5.5"), "suppliers"),
    ("5.8", "methods and tools and their justification", ("5.6",), None),
    ("5.9", "process assessment and improvement", ("5.7",), None),
    ("5.10", "operations and maintenance assurance", ("6.3.8", "6.3.9"), "operations"),
    ("6", "software process assurance", ("6",), None),
    ("6.1", "the development life cycle and its reviews", ("6.1",), None),
    ("6.2", "project plans the assurance function relies on", ("6.2.1",), None),
    ("6.3", "dependability and safety of the software", ("6.2.2", "6.2.3"), None),
    ("6.4", "software security", ("6.2.9", "6.2.10"), "security"),
    ("6.5", "documentation, configuration management and problem handling", ("6.2.4", "5.2.5", "5.2.6"), None),
    ("6.6", "process metrics", ("6.2.5",), None),
    ("6.7", "reuse of existing software", ("6.2.7",), "reuse"),
    ("6.8", "assurance of each engineering process", ("6.3",), None),
    ("6.9", "procedures and standards applied", ("6.2.1", "6.3.3", "6.3.4"), None),
    ("7", "software product quality assurance", ("7",), None),
    ("8", "compliance matrix against the standard", ("5.2.1",), None),
)

CONDITIONS = ("suppliers", "operations", "security", "reuse")

# A section with fewer words than this cannot answer its clauses.
MIN_WORDS_PER_SECTION = 40

# Maturity the plan owes at each review of the software life cycle.
PLAN_MATURITY_BY_REVIEW = {
    "srr": "issued",
    "pdr": "updated",
    "cdr": "updated",
    "qr": "maintained",
    "ar": "maintained",
    "orr": "maintained",
}

_REVIEW_ALIASES = {
    "system-requirements-review": "srr",
    "preliminary-design-review": "pdr",
    "critical-design-review": "cdr",
    "qualification-review": "qr",
    "acceptance-review": "ar",
    "operational-readiness-review": "orr",
}


def normalise_category(value):
    """Return the category letter A to D; raise ValueError otherwise."""
    if not isinstance(value, str) or value.strip().upper() not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return value.strip().upper()


def normalise_section_id(value):
    """Return a DRD section id such as '5.3' from '<5.3>', '5.3.' or 5."""
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        raise ValueError("section id must be a string, got %r" % (value,))
    text = value.strip().strip("<>").strip().rstrip(".")
    parts = text.split(".")
    if not text or not all(p.isdigit() for p in parts):
        raise ValueError("not a section id: %r" % (value,))
    return ".".join(str(int(p)) for p in parts)


def outline_section(section_id):
    """Return the outline entry of one section as a dict."""
    sid = normalise_section_id(section_id)
    for sec, topic, clauses, cond in SPAP_OUTLINE:
        if sec == sid:
            return {"id": sec, "topic": topic, "clauses": clauses, "condition": cond}
    raise ValueError("section %r is not in the plan outline" % (section_id,))


def _is_parent(sid):
    return any(s.startswith(sid + ".") for s, _, _, _ in SPAP_OUTLINE)


def assess_spap(sections, scope=(), min_words=MIN_WORDS_PER_SECTION):
    """Grade a draft plan against the DRD outline.

    sections: mapping section id -> section text (str) or None when absent.
    scope: the conditions that hold for the project, any of 'suppliers',
        'operations', 'security', 'reuse'. A conditional section outside the
        scope is not owed.
    min_words: word count under which a present leaf section is 'thin'.

    Parent sections (those with numbered children) are owed only as headings
    and are graded through their children. Returns a dict: owed, present,
    missing, thin, not_owed, unknown (ids not in the outline), coverage (the
    fraction of owed leaf sections present and not thin) and the verdict
    'complete' or 'incomplete'.
    """
    scope_set = set()
    for flag in scope:
        key = str(flag).strip().lower()
        if key not in CONDITIONS:
            raise ValueError("unknown scope condition %r" % (flag,))
        scope_set.add(key)
    given = {}
    for key, text in dict(sections).items():
        sid = normalise_section_id(key)
        if sid in given:
            raise ValueError("section %s given twice" % sid)
        given[sid] = text
    known = {s for s, _, _, _ in SPAP_OUTLINE}
    owed, missing, thin, not_owed, present = [], [], [], [], []
    for sid, topic, _, cond in SPAP_OUTLINE:
        if _is_parent(sid):
            continue
        if cond is not None and cond not in scope_set:
            not_owed.append(sid)
            continue
        owed.append(sid)
        text = given.get(sid)
        if text is None or not str(text).strip():
            missing.append(sid)
            continue
        present.append(sid)
        if len(str(text).split()) < min_words:
            thin.append(sid)
    unknown = sorted(s for s in given if s not in known)
    good = len(owed) - len(missing) - len(thin)
    coverage = round(good / len(owed), 4) if owed else 1.0
    return {
        "owed": owed,
        "present": present,
        "missing": missing,
        "thin": thin,
        "not_owed": not_owed,
        "unknown": unknown,
        "coverage": coverage,
        "verdict": "complete" if not missing and not thin else "incomplete",
    }


def check_organisation(org):
    """Check the assurance organisation a plan describes.

    org: dict with keys
        spa_lead: name of the software product assurance manager or engineer
        reports_to: role the lead reports to
        development_lead: name of the software development lead
        delegated_to_suppliers: list of supplier names assurance tasks are
            delegated to (optional)
        supplier_plans: list of supplier names whose own plan is held
            (optional)

    Returns a list of findings (dicts with 'code' and 'detail'); empty means
    the organisation reads as sound.
    """
    findings = []
    lead = str(org.get("spa_lead") or "").strip()
    dev = str(org.get("development_lead") or "").strip()
    reports_to = str(org.get("reports_to") or "").strip().lower()
    if not lead:
        findings.append({"code": "no-lead", "detail": "no named software product assurance lead"})
    if lead and dev and lead.lower() == dev.lower():
        findings.append({"code": "dual-role", "detail": "the assurance lead is also the development lead"})
    if not reports_to:
        findings.append({"code": "no-reporting-line", "detail": "reporting line not stated"})
    elif "development" in reports_to or (dev and reports_to == dev.lower()):
        findings.append({
            "code": "reporting-through-development",
            "detail": "the assurance lead reports through the development line; "
                      "the line should reach the project manager, via product "
                      "assurance where one exists",
        })
    delegated = [str(s) for s in (org.get("delegated_to_suppliers") or [])]
    plans = {str(s) for s in (org.get("supplier_plans") or [])}
    for sup in sorted(delegated):
        if sup not in plans:
            findings.append({
                "code": "delegation-without-plan",
                "detail": "assurance delegated to %s without its own plan held" % sup,
            })
    return findings


def check_supplier_control(suppliers, prime_category):
    """Check the control of each supplier that delivers software.

    suppliers: list of dicts with
        name, category (the category of what it delivers),
        category_flowed (bool), requirements_flowed (bool),
        plan_received (bool), pre_award_assessed (bool),
        monitoring (one of 'none', 'reports', 'reviews', 'audits')
    prime_category: category of the product the supplies go into.

    Returns a dict name -> list of findings. A supplier delivering to a
    category stricter than its own declared category is flagged, because the
    flow-down is what fixes the supplier's obligations.
    """
    prime = normalise_category(prime_category)
    needed = {"A": "audits", "B": "reviews", "C": "reviews", "D": "reports"}
    rank = {"none": 0, "reports": 1, "reviews": 2, "audits": 3}
    out = {}
    for sup in suppliers:
        name = str(sup.get("name") or "").strip()
        if not name:
            raise ValueError("supplier without a name")
        if name in out:
            raise ValueError("supplier %s given twice" % name)
        cat = normalise_category(sup.get("category", prime))
        found = []
        if CATEGORIES.index(cat) > CATEGORIES.index(prime):
            found.append("declared category %s is less strict than the product's %s" % (cat, prime))
        for key, text in (
            ("category_flowed", "criticality category not flowed down"),
            ("requirements_flowed", "assurance requirements not flowed down"),
            ("plan_received", "supplier assurance plan not received"),
        ):
            if not sup.get(key):
                found.append(text)
        if not sup.get("pre_award_assessed") and cat != "D":
            found.append("no pre-award assessment of the supplier")
        mon = str(sup.get("monitoring") or "none").strip().lower()
        if mon not in rank:
            raise ValueError("unknown monitoring level %r" % (mon,))
        want = needed[cat]
        if rank[mon] < rank[want]:
            found.append("monitoring '%s' is below '%s' for category %s" % (mon, want, cat))
        out[name] = found
    return out


def assess_tools(tools, category):
    """Grade methods and tools against the category.

    tools: list of dicts with name, role (one of 'generates-code',
        'compiles', 'verifies', 'manages', 'documents'), previously_used (bool),
        qualified (bool), justified (bool).
    category: software category A to D.

    A tool whose output enters the executable, or whose verdict replaces a
    verification step, needs qualification evidence for categories A and B
    and a written justification for C. Category D keeps a lighter bar: the
    tool must have a prior successful use. Every tool needs a justification
    in the plan. Returns a list of dicts: name, impact, findings.
    """
    cat = normalise_category(category)
    impact_of = {
        "generates-code": "executable",
        "compiles": "executable",
        "verifies": "verification",
        "manages": "indirect",
        "documents": "indirect",
    }
    out = []
    seen = set()
    for tool in tools:
        name = str(tool.get("name") or "").strip()
        if not name or name in seen:
            raise ValueError("tool name missing or duplicated: %r" % (name,))
        seen.add(name)
        role = str(tool.get("role") or "").strip().lower()
        if role not in impact_of:
            raise ValueError("unknown tool role %r" % (role,))
        impact = impact_of[role]
        found = []
        if not tool.get("justified"):
            found.append("no justification of suitability in the plan")
        if cat == "D":
            if not tool.get("previously_used"):
                found.append("no prior successful use recorded")
        elif impact in ("executable", "verification"):
            if cat in ("A", "B") and not tool.get("qualified"):
                found.append("qualification evidence needed for category %s" % cat)
            if cat == "C" and not (tool.get("qualified") or tool.get("previously_used")):
                found.append("needs qualification or a prior successful use")
        out.append({"name": name, "impact": impact, "findings": found})
    return out


def plan_maturity_due(review):
    """Return the maturity the plan owes at a review (srr, pdr, ...)."""
    key = str(review).strip().lower().replace(" ", "-")
    key = _REVIEW_ALIASES.get(key, key)
    if key not in PLAN_MATURITY_BY_REVIEW:
        raise ValueError("unknown review %r" % (review,))
    return PLAN_MATURITY_BY_REVIEW[key]
