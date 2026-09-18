"""Purpose and application of the hybrid technology identification form.

Anchor: ECSS-Q-ST-60-05C clause 6.2 (the technology identification form and
the part it plays when a hybrid supplier is assessed). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the construction technologies the supplier declares for the hybrid.
   Each technology pulls in the assessment areas the assessor has to form an
   opinion on; a hybrid that declares no technology has nothing to assess and
   is refused as an input error.
2. Derive the form sections those areas make owed. The form exists so that
   the declared technology and the evidence needed to assess it arrive
   together, before anyone visits the supplier.
3. Compare the sections actually submitted with the sections owed and report
   the assessment areas left uncovered.
4. Decide, per assessment activity, whether it may run. An activity is
   enabled only when every area it depends on that is relevant to this hybrid
   is covered; an activity whose areas are all irrelevant here is not
   applicable rather than enabled.
5. Derive the sealing category from the declared packaging, because a hybrid
   that is sealed both hermetically and with a polymer has contradictory
   construction data and must be resolved before assessment.
6. Return a readiness verdict: with no form, or with a relevant area
   uncovered, the supplier assessment cannot start.
"""

__all__ = [
    "CONSTRUCTION_TECHNOLOGIES",
    "TECHNOLOGY_FAMILIES",
    "HERMETIC_PACKAGES",
    "NON_HERMETIC_PACKAGES",
    "ASSESSMENT_AREAS",
    "FORM_SECTIONS",
    "ACTIVITY_DEPENDENCIES",
    "READINESS_STATES",
    "normalize_token",
    "normalize_technologies",
    "normalize_sections",
    "group_technologies_by_family",
    "relevant_assessment_areas",
    "covered_assessment_areas",
    "required_form_sections",
    "absent_form_sections",
    "uncovered_assessment_areas",
    "sealing_category",
    "coverage_percent",
    "activity_status",
    "assess_form_application",
]

# Construction technologies a hybrid supplier can declare, each mapped onto
# the assessment areas it obliges the assessor to cover.
CONSTRUCTION_TECHNOLOGIES = {
    "thick-film-substrate": (
        "substrate-and-conductor-assessment",
        "resistor-trim-assessment",
    ),
    "thin-film-substrate": (
        "substrate-and-conductor-assessment",
        "thin-film-deposition-assessment",
    ),
    "co-fired-ceramic-substrate": ("substrate-and-conductor-assessment",),
    "eutectic-die-attach": ("die-attach-assessment",),
    "solder-die-attach": ("die-attach-assessment",),
    "adhesive-die-attach": (
        "die-attach-assessment",
        "outgassing-and-materials-assessment",
    ),
    "gold-wire-bonding": ("interconnection-assessment",),
    "aluminium-wire-bonding": ("interconnection-assessment",),
    "flip-chip-attach": (
        "interconnection-assessment",
        "underfill-and-materials-assessment",
    ),
    "internal-active-die": ("die-procurement-assessment",),
    "internal-passive-attachment": ("component-mounting-assessment",),
    "seam-welded-package": (
        "package-sealing-assessment",
        "hermeticity-assessment",
    ),
    "solder-sealed-package": (
        "package-sealing-assessment",
        "hermeticity-assessment",
    ),
    "polymer-sealed-package": (
        "package-sealing-assessment",
        "moisture-control-assessment",
    ),
}

# The same technologies grouped by the construction step they belong to. The
# grouping is what lets a reviewer see at a glance that a declaration has, for
# example, a substrate and an interconnection but no packaging step at all.
TECHNOLOGY_FAMILIES = {
    "substrate": (
        "co-fired-ceramic-substrate",
        "thick-film-substrate",
        "thin-film-substrate",
    ),
    "die-attachment": (
        "adhesive-die-attach",
        "eutectic-die-attach",
        "solder-die-attach",
    ),
    "interconnection": (
        "aluminium-wire-bonding",
        "flip-chip-attach",
        "gold-wire-bonding",
    ),
    "internal-parts": (
        "internal-active-die",
        "internal-passive-attachment",
    ),
    "packaging": (
        "polymer-sealed-package",
        "seam-welded-package",
        "solder-sealed-package",
    ),
}

HERMETIC_PACKAGES = ("seam-welded-package", "solder-sealed-package")

NON_HERMETIC_PACKAGES = ("polymer-sealed-package",)

# Derived so the area vocabulary can never drift away from the technology map.
ASSESSMENT_AREAS = tuple(
    sorted({area for areas in CONSTRUCTION_TECHNOLOGIES.values() for area in areas})
)

# Sections of the identification form, each carrying the areas it evidences.
FORM_SECTIONS = {
    "substrate-and-conductor-data": (
        "substrate-and-conductor-assessment",
        "resistor-trim-assessment",
        "thin-film-deposition-assessment",
    ),
    "die-attach-data": ("die-attach-assessment",),
    "interconnection-data": ("interconnection-assessment",),
    "internal-component-data": (
        "die-procurement-assessment",
        "component-mounting-assessment",
    ),
    "package-and-sealing-data": (
        "package-sealing-assessment",
        "hermeticity-assessment",
    ),
    "materials-and-contamination-data": (
        "outgassing-and-materials-assessment",
        "underfill-and-materials-assessment",
        "moisture-control-assessment",
    ),
}

# Supplier-assessment activities and the areas each one needs evidence for.
ACTIVITY_DEPENDENCIES = {
    "supplier-technology-review": ASSESSMENT_AREAS,
    "manufacturing-line-audit": (
        "substrate-and-conductor-assessment",
        "resistor-trim-assessment",
        "thin-film-deposition-assessment",
        "die-attach-assessment",
        "interconnection-assessment",
        "package-sealing-assessment",
    ),
    "materials-and-contamination-review": (
        "outgassing-and-materials-assessment",
        "underfill-and-materials-assessment",
        "moisture-control-assessment",
    ),
    "sealing-and-hermeticity-review": (
        "package-sealing-assessment",
        "hermeticity-assessment",
        "moisture-control-assessment",
    ),
    "internal-part-procurement-review": (
        "die-procurement-assessment",
        "component-mounting-assessment",
    ),
}

READINESS_STATES = (
    "assessment-may-start",
    "assessment-blocked",
    "form-not-submitted",
)


def normalize_token(value, label):
    """Return a trimmed, lower-cased token, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def _normalize_sequence(items, label, vocabulary):
    if items is None:
        items = []
    if isinstance(items, (str, bytes)):
        raise ValueError("%s must be a sequence, not a single string" % label)
    if not isinstance(items, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence" % label)
    seen = []
    for item in items:
        key = normalize_token(item, label)
        if key not in vocabulary:
            raise ValueError("unknown %s '%s'" % (label, key))
        if key not in seen:
            seen.append(key)
    return sorted(seen)


def normalize_technologies(technologies):
    """Return the sorted, de-duplicated declared technology set, or raise."""
    declared = _normalize_sequence(
        technologies, "construction technology", CONSTRUCTION_TECHNOLOGIES
    )
    if not declared:
        raise ValueError("a hybrid declares at least one construction technology")
    return declared


def normalize_sections(sections):
    """Return the sorted, de-duplicated submitted form sections, or raise."""
    return _normalize_sequence(sections, "form section", FORM_SECTIONS)


def group_technologies_by_family(technologies):
    """Return the declared technologies grouped by construction step."""
    declared = normalize_technologies(technologies)
    grouped = {}
    for family in sorted(TECHNOLOGY_FAMILIES):
        members = [item for item in declared if item in TECHNOLOGY_FAMILIES[family]]
        grouped[family] = sorted(members)
    return grouped


def relevant_assessment_areas(technologies):
    """Return the assessment areas the declared technologies make relevant."""
    declared = normalize_technologies(technologies)
    areas = set()
    for item in declared:
        areas.update(CONSTRUCTION_TECHNOLOGIES[item])
    return tuple(sorted(areas))


def covered_assessment_areas(sections):
    """Return the assessment areas the submitted form sections evidence."""
    submitted = normalize_sections(sections)
    areas = set()
    for item in submitted:
        areas.update(FORM_SECTIONS[item])
    return tuple(sorted(areas))


def required_form_sections(technologies):
    """Return the form sections owed by the declared technology set."""
    relevant = set(relevant_assessment_areas(technologies))
    owed = [
        section
        for section, areas in FORM_SECTIONS.items()
        if relevant.intersection(areas)
    ]
    return tuple(sorted(owed))


def absent_form_sections(technologies, sections):
    """Return the owed form sections the submission does not carry."""
    submitted = set(normalize_sections(sections))
    return [item for item in required_form_sections(technologies) if item not in submitted]


def uncovered_assessment_areas(technologies, sections):
    """Return the relevant assessment areas no submitted section evidences."""
    covered = set(covered_assessment_areas(sections))
    return [item for item in relevant_assessment_areas(technologies) if item not in covered]


def sealing_category(technologies):
    """Return the sealing category implied by the declared packaging."""
    declared = normalize_technologies(technologies)
    hermetic = [item for item in declared if item in HERMETIC_PACKAGES]
    non_hermetic = [item for item in declared if item in NON_HERMETIC_PACKAGES]
    if hermetic and non_hermetic:
        raise ValueError(
            "the declaration carries both a hermetic and a non-hermetic package"
        )
    if hermetic:
        return "hermetic"
    if non_hermetic:
        return "non-hermetic"
    return "sealing-not-declared"


def coverage_percent(technologies, sections):
    """Return the percentage of relevant assessment areas that are covered."""
    relevant = relevant_assessment_areas(technologies)
    covered = set(covered_assessment_areas(sections))
    hits = sum(1 for item in relevant if item in covered)
    return hits * 100.0 / len(relevant)


def activity_status(technologies, sections):
    """Return the enablement state of every supplier-assessment activity."""
    relevant = set(relevant_assessment_areas(technologies))
    covered = set(covered_assessment_areas(sections))
    status = {}
    for activity in sorted(ACTIVITY_DEPENDENCIES):
        needed = relevant.intersection(ACTIVITY_DEPENDENCIES[activity])
        if not needed:
            status[activity] = "not-applicable"
        elif needed.issubset(covered):
            status[activity] = "enabled"
        else:
            status[activity] = "blocked"
    return status


def assess_form_application(spec):
    """Run the full clause 6.2 application assessment for one hybrid.

    spec keys: declared_technologies, form_submitted (boolean) and
    form_sections (the sections the submitted form carries).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declared_technologies", "form_submitted", "form_sections"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if not isinstance(spec["form_submitted"], bool):
        raise ValueError("form_submitted must be a boolean")

    declared = normalize_technologies(spec["declared_technologies"])
    submitted = normalize_sections(spec["form_sections"])
    if not spec["form_submitted"] and submitted:
        raise ValueError("form sections were listed for a form that was not submitted")

    grouped = group_technologies_by_family(declared)
    relevant = list(relevant_assessment_areas(declared))
    owed = list(required_form_sections(declared))
    absent = absent_form_sections(declared, submitted)
    uncovered = uncovered_assessment_areas(declared, submitted)
    sealing = sealing_category(declared)
    activities = activity_status(declared, submitted)

    findings = []
    if not spec["form_submitted"]:
        findings.append(
            "no technology identification form was submitted, so the supplier "
            "assessment has nothing to be planned against"
        )
        readiness = "form-not-submitted"
    elif uncovered:
        readiness = "assessment-blocked"
    else:
        readiness = "assessment-may-start"
    for item in absent:
        findings.append("the submitted form is missing the '%s' section" % item)
    for item in uncovered:
        findings.append("no submitted section evidences '%s'" % item)
    if sealing == "sealing-not-declared":
        findings.append(
            "the declaration names no packaging technology, so the sealing "
            "category cannot be derived"
        )
    for family in sorted(grouped):
        if not grouped[family]:
            findings.append("the declaration names no '%s' technology" % family)

    return {
        "declared_technologies": declared,
        "technology_families": grouped,
        "sealing_category": sealing,
        "relevant_assessment_areas": relevant,
        "required_form_sections": owed,
        "submitted_form_sections": submitted,
        "absent_form_sections": absent,
        "uncovered_assessment_areas": uncovered,
        "coverage_percent": coverage_percent(declared, submitted),
        "activity_status": activities,
        "readiness": readiness,
        "findings": findings,
        "ready_for_assessment": readiness == "assessment-may-start",
    }
