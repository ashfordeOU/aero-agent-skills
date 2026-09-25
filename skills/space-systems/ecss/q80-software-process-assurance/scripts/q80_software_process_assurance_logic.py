"""Software process assurance: life cycle, verification, critical software.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 6: the software life cycle
and its reviews (6.1), the requirements that hold for every engineering
process (6.2: documentation, dependability and safety, handling of critical
software, configuration management, process metrics, verification, reuse of
existing software, automatic code generation, security) and the assurance of
each individual process (6.3). Nonconformance handling is anchored in 5.2.5
and 5.2.6. Paraphrased into checks; no requirement text is reproduced.

Procedure implemented here
--------------------------
1. Walk the life cycle reviews in order and find the first one not closed,
   and any work that ran ahead of it.
2. Check the handling of critical software for a category: the fixed
   obligations that apply to the category plus at least one justified
   project measure from the candidate list.
3. Check verification independence for the category.
4. Grade a reuse candidate: a reuse file, the delta between the original
   and the new context, and the re-verification that delta triggers.
5. Grade an automatic code generator: modelling standards, model
   verification, generator qualification or verification of the output.
6. Triage nonconformances and software problem reports: open major items,
   items without a review board decision, boards without a software expert.
"""

__all__ = [
    "CATEGORIES",
    "LIFECYCLE",
    "CANDIDATE_MEASURES",
    "FIXED_CRITICAL_OBLIGATIONS",
    "normalise_category",
    "normalise_review",
    "check_lifecycle",
    "critical_software_obligations",
    "check_critical_software",
    "check_verification_independence",
    "assess_reuse",
    "assess_autocode",
    "triage_nonconformances",
]

CATEGORIES = ("A", "B", "C", "D")

# Life cycle reviews in order with the phase each one closes.
LIFECYCLE = (
    ("srr", "requirements baseline"),
    ("pdr", "technical specification and architecture"),
    ("cdr", "detailed design, code and unit tests"),
    ("qr", "qualification and validation"),
    ("ar", "acceptance"),
)

_REVIEW_ALIASES = {
    "system-requirements-review": "srr",
    "preliminary-design-review": "pdr",
    "critical-design-review": "cdr",
    "qualification-review": "qr",
    "acceptance-review": "ar",
}

# Measures a project may choose from to assure critical software. The plan
# must choose, justify and apply some; which ones is a project decision.
CANDIDATE_MEASURES = (
    "proven-design-or-method",
    "failure-isolation-and-handling",
    "defensive-programming",
    "language-safe-subset",
    "formal-methods",
    "full-branch-coverage-unit-level",
    "full-code-inspection",
    "independent-or-witnessed-testing",
    "failure-statistics-analysis",
    "deactivated-code-control",
    "dynamic-code-verification",
)

# Obligations the handling of critical software fixes regardless of the
# measures chosen, with the categories each applies to (clause 6.2.3).
FIXED_CRITICAL_OBLIGATIONS = (
    ("measures-verified", "6.2.3.3", ("A", "B", "C")),
    ("regression-after-platform-or-tool-change", "6.2.3.4", ("A", "B", "C")),
    ("vv-need-analysed-after-environment-change", "6.2.3.5", ("A", "B", "C")),
    ("unreachable-code-removed", "6.2.3.6", ("A", "B", "C")),
    ("unit-integration-rerun-uninstrumented", "6.2.3.7", ("A", "B")),
    ("validation-rerun-uninstrumented", "6.2.3.8", ("A", "B", "C")),
)


def normalise_category(value):
    """Return the category letter A to D; raise ValueError otherwise."""
    if not isinstance(value, str) or value.strip().upper() not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return value.strip().upper()


def normalise_review(value):
    """Return the short review name (srr, pdr, cdr, qr, ar)."""
    key = str(value).strip().lower().replace(" ", "-")
    key = _REVIEW_ALIASES.get(key, key)
    if key not in [r for r, _ in LIFECYCLE]:
        raise ValueError("unknown review %r" % (value,))
    return key


def check_lifecycle(reviews, work_started=()):
    """Find the first open gate and any work that ran ahead of it.

    reviews: mapping review -> dict(held: bool, closed: bool,
        open_actions: int). A review is closed when held, marked closed and
        with no open actions.
    work_started: phases (review names) whose work has begun, meaning the
        work the review AFTER the named one closes.

    Returns a dict with first_open (review or None), closed (list),
    ahead_of_gate (reviews whose phase work started while an earlier gate is
    still open) and inconsistent (closed while actions remain open).
    """
    status = {}
    for key, val in dict(reviews).items():
        status[normalise_review(key)] = dict(val or {})
    closed, inconsistent = [], []
    first_open = None
    for name, _ in LIFECYCLE:
        st = status.get(name, {})
        actions = int(st.get("open_actions", 0) or 0)
        if st.get("closed") and actions > 0:
            inconsistent.append(name)
        is_closed = bool(st.get("held")) and bool(st.get("closed")) and actions == 0
        if is_closed and first_open is None:
            closed.append(name)
        elif first_open is None:
            first_open = name
    order = [r for r, _ in LIFECYCLE]
    ahead = []
    if first_open is not None:
        gate = order.index(first_open)
        for phase in work_started:
            idx = order.index(normalise_review(phase))
            if idx >= gate:
                ahead.append(order[idx])
    return {
        "first_open": first_open,
        "closed": closed,
        "ahead_of_gate": sorted(set(ahead), key=order.index),
        "inconsistent": inconsistent,
    }


def critical_software_obligations(category):
    """Return the fixed critical-software obligations for a category."""
    cat = normalise_category(category)
    return [(key, clause) for key, clause, cats in FIXED_CRITICAL_OBLIGATIONS if cat in cats]


def check_critical_software(category, measures, obligations_met=()):
    """Check the handling of critical software for one category.

    measures: mapping measure -> justification text (chosen project
        measures from CANDIDATE_MEASURES).
    obligations_met: keys of FIXED_CRITICAL_OBLIGATIONS with evidence.

    Category D carries no critical-software obligations. For A to C the
    result lists the missing fixed obligations, measures chosen without a
    justification, unknown measures, and whether at least one justified
    measure exists. Verdict is 'met', 'not-met' or 'not-applicable'.
    """
    cat = normalise_category(category)
    if cat == "D":
        return {"category": cat, "verdict": "not-applicable", "missing_obligations": [],
                "unjustified": [], "unknown": [], "justified_measures": []}
    unknown = sorted(m for m in measures if m not in CANDIDATE_MEASURES)
    justified = sorted(m for m, why in measures.items()
                       if m in CANDIDATE_MEASURES and str(why or "").strip())
    unjustified = sorted(m for m, why in measures.items()
                         if m in CANDIDATE_MEASURES and not str(why or "").strip())
    met = set(obligations_met)
    missing = [key for key, _ in critical_software_obligations(cat) if key not in met]
    ok = not missing and not unknown and not unjustified and bool(justified)
    return {
        "category": cat,
        "verdict": "met" if ok else "not-met",
        "missing_obligations": missing,
        "unjustified": unjustified,
        "unknown": unknown,
        "justified_measures": justified,
    }


def check_verification_independence(category, author, verifier, same_organisation,
                                    isvv_waived_by_customer=False):
    """Check that verification of an item is independent enough.

    For categories A and B an independent verification and validation by
    another organisation is expected unless the customer has recorded a
    less rigorous choice; for every category the author may not verify
    their own item. Returns a list of findings.
    """
    cat = normalise_category(category)
    found = []
    if str(author).strip().lower() == str(verifier).strip().lower():
        found.append("author verifies own item")
    if cat in ("A", "B") and same_organisation and not isvv_waived_by_customer:
        found.append("category %s expects verification by an independent organisation "
                     "unless the customer records a lighter choice" % cat)
    return found


def assess_reuse(component, target_category):
    """Grade a candidate for reuse in a new context.

    component: dict with name, original_category (A-D or None when unknown),
        has_reuse_file, requirements_changed, platform_changed,
        environment_changed, open_problems (int), documentation_complete,
        configuration_known.
    target_category: category in the new product.

    Returns a dict with the actions the reuse triggers and a verdict
    'reuse-as-is', 'reuse-with-delta' or 'not-reusable-yet'.
    """
    cat = normalise_category(target_category)
    actions = []
    blocking = False
    if not component.get("has_reuse_file"):
        actions.append("prepare the software reuse file")
        blocking = True
    if not component.get("configuration_known"):
        actions.append("establish the configuration of the reused item")
        blocking = True
    orig = component.get("original_category")
    if orig is None:
        actions.append("no original category known; re-verify to category %s" % cat)
        delta = True
    else:
        orig = normalise_category(orig)
        delta = CATEGORIES.index(orig) > CATEGORIES.index(cat)
        if delta:
            actions.append("developed to %s, used at %s: close the evidence gap" % (orig, cat))
    for key, text in (
        ("requirements_changed", "re-verify against the changed requirements"),
        ("platform_changed", "regression test on the new platform"),
        ("environment_changed", "analyse the need for extra verification in the new environment"),
    ):
        if component.get(key):
            actions.append(text)
            delta = True
    problems = int(component.get("open_problems", 0) or 0)
    if problems:
        actions.append("assess the %d open problem report(s) in the new context" % problems)
        delta = True
    if not component.get("documentation_complete"):
        actions.append("complete the documentation needed for maintenance")
        delta = True
    if blocking:
        verdict = "not-reusable-yet"
    elif delta:
        verdict = "reuse-with-delta"
    else:
        verdict = "reuse-as-is"
    return {"name": component.get("name"), "actions": actions, "verdict": verdict}


def assess_autocode(generator, category):
    """Grade automatic code generation for one category.

    generator: dict with name, modelling_standard (bool), model_verified
        (bool), generator_qualified (bool), output_verified (bool),
        output_under_cm (bool).

    The generated code is part of the product: either the generator is
    qualified for the category or its output is verified as if hand
    written. Returns a list of findings.
    """
    cat = normalise_category(category)
    found = []
    if not generator.get("modelling_standard"):
        found.append("no modelling standard defined")
    if not generator.get("model_verified"):
        found.append("model not verified")
    if not generator.get("output_under_cm"):
        found.append("generated code not under configuration management")
    if cat != "D" and not (generator.get("generator_qualified") or generator.get("output_verified")):
        found.append("neither the generator is qualified nor its output verified")
    return found


def triage_nonconformances(items, board_members=()):
    """Triage software nonconformances and problem reports.

    items: list of dicts with id, kind ('ncr' or 'spr'), severity ('major'
        or 'minor'), status ('open', 'dispositioned', 'closed'),
        board_decision (bool).
    board_members: list of dicts with name and software_expert (bool).

    Returns a dict: counts by kind, severity and status; open_major ids;
    major items without a board decision; and whether the review board
    includes a software expert (a major software nonconformance cannot be
    dispositioned without one).
    """
    counts = {}
    open_major, undecided = [], []
    seen = set()
    for it in items:
        iid = str(it.get("id") or "").strip()
        if not iid or iid in seen:
            raise ValueError("item id missing or duplicated: %r" % (iid,))
        seen.add(iid)
        kind = str(it.get("kind", "")).lower()
        sev = str(it.get("severity", "")).lower()
        st = str(it.get("status", "")).lower()
        if kind not in ("ncr", "spr") or sev not in ("major", "minor") or \
                st not in ("open", "dispositioned", "closed"):
            raise ValueError("item %s has an unknown kind, severity or status" % iid)
        key = "%s/%s/%s" % (kind, sev, st)
        counts[key] = counts.get(key, 0) + 1
        if sev == "major" and st == "open":
            open_major.append(iid)
        if sev == "major" and st != "open" and not it.get("board_decision"):
            undecided.append(iid)
    expert = any(m.get("software_expert") for m in board_members)
    return {
        "counts": dict(sorted(counts.items())),
        "open_major": sorted(open_major),
        "major_without_board_decision": sorted(undecided),
        "board_has_software_expert": expert,
        "board_gap": bool(open_major or undecided) and not expert,
    }
