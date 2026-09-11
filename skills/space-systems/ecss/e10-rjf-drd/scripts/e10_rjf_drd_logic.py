"""ECSS-E-ST-10C Annex O requirements justification file DRD (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex O
Document Requirements Definition governs the Requirements Justification File --
the record of WHY each requirement reads as it does. Every requirement carries
a derivation basis (a parent requirement, an analysis, an applicable standard,
heritage, or a stated mission need), a rationale in its own words, and an
attributed author. A requirement derived from a parent must name that parent;
a top-level requirement cannot be derived from one, because there is nothing
above it. A rationale that merely restates the requirement justifies nothing
and is the characteristic way this file degrades.
"""

DERIVATION_BASES = ("parent_requirement", "analysis", "applicable_standard",
                    "heritage", "mission_need")
TOP_LEVEL_BASES = ("applicable_standard", "mission_need")
MIN_RATIONALE_WORDS = 4


def validate_basis(basis):
    """Return basis if it is an Annex O derivation basis, else raise."""
    if basis not in DERIVATION_BASES:
        raise ValueError("unknown derivation basis: %r" % (basis,))
    return basis


def _norm(text):
    return " ".join((text or "").lower().split())


def rationale_is_restatement(requirement_text, rationale):
    """True when the rationale adds nothing to the requirement -- identical
    once normalized, or wholly contained in the requirement's own wording.
    This is the way an RJF degrades: every field filled, nothing explained."""
    req, rat = _norm(requirement_text), _norm(rationale)
    if not rat:
        return False
    return rat == req or (len(rat) > 0 and rat in req)


def rationale_violations(requirement):
    """Findings for the rationale of one requirement: absent, too short to
    carry an argument, or a restatement of the requirement itself."""
    rid = requirement.get("requirement_id")
    rationale = requirement.get("rationale")
    out = []
    if not rationale or not rationale.strip():
        out.append({"requirement_id": rid, "issue": "no_rationale"})
        return out
    if len(rationale.split()) < MIN_RATIONALE_WORDS:
        out.append({"requirement_id": rid, "issue": "rationale_too_short"})
    if rationale_is_restatement(requirement.get("text", ""), rationale):
        out.append({"requirement_id": rid, "issue": "rationale_restates_requirement"})
    return out


def basis_violations(requirement):
    """Findings for the derivation basis of one requirement.

    A parent_requirement basis must name the parent. A top-level requirement
    must rest on a standard or a mission need -- it cannot derive from a
    parent, and claiming it does hides an unjustified requirement behind a
    trace that cannot exist.
    """
    validate_basis(requirement.get("basis"))
    rid = requirement.get("requirement_id")
    basis = requirement["basis"]
    top = bool(requirement.get("is_top_level"))
    out = []
    if basis == "parent_requirement":
        if top:
            out.append({"requirement_id": rid, "issue": "top_level_derived_from_parent"})
        elif not requirement.get("parent_id"):
            out.append({"requirement_id": rid, "issue": "parent_basis_without_parent"})
    # A parent may legitimately be recorded alongside a non-parent basis
    # (an analysis that refined an inherited requirement), so that is not a
    # finding -- only the basis/level contradictions below are.
    if top and basis not in TOP_LEVEL_BASES and basis != "parent_requirement":
        out.append({"requirement_id": rid, "issue": "top_level_basis_not_external"})
    return out


def attribution_violations(requirement):
    """Findings for missing attribution. A rationale nobody signed cannot be
    questioned later, which is what the file exists to allow."""
    rid = requirement.get("requirement_id")
    out = []
    if not requirement.get("author"):
        out.append({"requirement_id": rid, "issue": "no_author"})
    return out


def rjf_review(requirements):
    """Full Annex O RJF review.

    requirements: [{"requirement_id", "text", "rationale", "basis",
                    "parent_id" | None, "is_top_level": bool, "author"}]

    Returns {"reviewed", "justified", "findings"}. Raises ValueError for a
    missing or duplicate requirement id, or an unrecognized basis.
    """
    seen = set()
    findings = []
    for req in requirements:
        rid = req.get("requirement_id")
        if not rid:
            raise ValueError("requirement with no requirement_id")
        if rid in seen:
            raise ValueError("duplicate requirement_id: %s" % rid)
        seen.add(rid)
        findings += rationale_violations(req)
        findings += basis_violations(req)
        findings += attribution_violations(req)
    flagged = {f["requirement_id"] for f in findings}
    return {"reviewed": sorted(seen),
            "justified": sorted(seen - flagged),
            "findings": findings}


def is_rjf_complete(review):
    """True when every reviewed requirement is justified -- no findings."""
    return not review["findings"]
