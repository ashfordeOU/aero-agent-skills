"""Quality assurance plan document requirements description.

Anchor: ECSS-Q-ST-20C Annex A (normative), the document requirements
description for the quality assurance plan: what the plan owes as content --
its scope, the organisation that carries it, the quality task provisions it
commits to, and the documentation it governs. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the DRD-ordered outline for the contract level the plan is written
   at, numbering the sections and their subjects deterministically.
2. Normalise a submitted plan and refuse a malformed or duplicated section.
3. Decide, per DRD section, whether the subjects the DRD names are covered,
   validly declared not applicable, or absent.
4. Refuse a not-applicable declaration on scope or organisation, and demand a
   justification and a customer approver where it is admissible.
5. Reconcile the quality task provisions against the task set the contract
   level owes.
6. Resolve every document the plan cites against its own reference list.
7. Return the conformance fraction and the plan verdict.
"""

__all__ = [
    "CONTRACT_LEVELS",
    "DRD_SECTIONS",
    "SECTION_SUBJECTS",
    "BASE_TASKS",
    "LEVEL_TASKS",
    "UNTAILORABLE_SECTIONS",
    "normalise_identifier",
    "required_tasks",
    "plan_outline",
    "validate_plan",
    "section_findings",
    "task_findings",
    "reference_findings",
    "conformance_fraction",
    "assess_qa_plan",
]

# The level the plan is written at. The task provisions differ by level.
CONTRACT_LEVELS = ("prime", "subcontractor", "supplier")

# The DRD content, in the order the plan presents it.
DRD_SECTIONS = (
    "introduction-and-scope",
    "applicable-and-reference-documents",
    "organization-and-responsibilities",
    "quality-task-provisions",
    "documentation-and-records",
    "plan-maintenance",
)

# What each section has to actually say to count as written.
SECTION_SUBJECTS = {
    "introduction-and-scope": (
        "product-covered",
        "contract-phases-covered",
        "tailoring-statement",
    ),
    "applicable-and-reference-documents": (
        "applicable-document-list",
        "reference-document-list",
    ),
    "organization-and-responsibilities": (
        "quality-function-independence",
        "reporting-line",
        "resource-and-authority",
    ),
    "quality-task-provisions": (
        "task-list",
        "task-responsibility-matrix",
        "task-schedule-link",
    ),
    "documentation-and-records": (
        "record-list",
        "retention-period",
        "record-access-rules",
    ),
    "plan-maintenance": (
        "revision-rules",
        "approval-authority",
    ),
}

# Task provisions every plan commits to, whatever the level.
BASE_TASKS = (
    "procurement-control",
    "inspection-and-test-control",
    "nonconformance-control",
    "metrology-and-calibration-control",
    "handling-storage-and-transport-control",
    "records-and-traceability-control",
)

# What each contract level adds on top of the base set.
LEVEL_TASKS = {
    "prime": (
        "supplier-surveillance",
        "customer-interface-and-reporting",
        "internal-audit-programme",
    ),
    "subcontractor": (
        "supplier-surveillance",
        "requirement-flow-down-verification",
    ),
    "supplier": (
        "requirement-flow-down-verification",
    ),
}

# Sections that cannot be tailored out: without them the plan says nothing
# about what it covers or who is accountable for it.
UNTAILORABLE_SECTIONS = (
    "introduction-and-scope",
    "organization-and-responsibilities",
)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def required_tasks(contract_level):
    """Return the ordered task provisions a contract level owes."""
    key = normalise_identifier(contract_level, "contract_level")
    if key not in CONTRACT_LEVELS:
        raise ValueError(
            "contract_level must be one of %s, got %r"
            % ("/".join(CONTRACT_LEVELS), contract_level)
        )
    return tuple(BASE_TASKS) + tuple(LEVEL_TASKS[key])


def plan_outline(contract_level):
    """Return the DRD-ordered outline, numbered, for a contract level."""
    tasks = required_tasks(contract_level)
    outline = []
    for index, section in enumerate(DRD_SECTIONS, start=1):
        subjects = []
        for sub_index, subject in enumerate(SECTION_SUBJECTS[section], start=1):
            subjects.append({"number": "%d.%d" % (index, sub_index), "subject": subject})
        entry = {"number": str(index), "section": section, "subjects": tuple(subjects)}
        if section == "quality-task-provisions":
            entry["tasks"] = tasks
        outline.append(entry)
    return tuple(outline)


def validate_plan(plan):
    """Return the normalised plan; raise on a malformed submission."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    raw_sections = plan.get("sections")
    if not isinstance(raw_sections, (list, tuple)) or not raw_sections:
        raise ValueError("plan['sections'] must be a non-empty sequence")
    sections = {}
    for index, item in enumerate(raw_sections):
        if not isinstance(item, dict):
            raise ValueError("sections[%d] must be a mapping" % index)
        name = normalise_identifier(item.get("section"), "sections[%d].section" % index)
        if name in sections:
            raise ValueError("section %r is submitted twice" % name)
        not_applicable = bool(item.get("not_applicable", False))
        entry = {
            "section": name,
            "not_applicable": not_applicable,
            "subjects": (),
            "justification": None,
            "approved_by": None,
        }
        if not_applicable:
            justification = item.get("justification")
            if justification is not None:
                if not isinstance(justification, str) or not justification.strip():
                    raise ValueError(
                        "sections[%d].justification must be a non-empty string" % index
                    )
                entry["justification"] = justification.strip()
            approver = item.get("approved_by")
            entry["approved_by"] = (
                None
                if approver is None
                else normalise_identifier(approver, "sections[%d].approved_by" % index)
            )
        else:
            raw_subjects = item.get("subjects", ())
            if not isinstance(raw_subjects, (list, tuple)):
                raise ValueError("sections[%d].subjects must be a sequence" % index)
            entry["subjects"] = tuple(
                normalise_identifier(value, "sections[%d].subjects entry" % index)
                for value in raw_subjects
            )
        sections[name] = entry
    raw_tasks = plan.get("tasks", ())
    if not isinstance(raw_tasks, (list, tuple)):
        raise ValueError("plan['tasks'] must be a sequence")
    tasks = tuple(
        normalise_identifier(value, "plan['tasks'] entry") for value in raw_tasks
    )
    raw_refs = plan.get("reference_documents", ())
    if not isinstance(raw_refs, (list, tuple)):
        raise ValueError("plan['reference_documents'] must be a sequence")
    references = tuple(
        normalise_identifier(value, "plan['reference_documents'] entry")
        for value in raw_refs
    )
    raw_cited = plan.get("cited_documents", ())
    if not isinstance(raw_cited, (list, tuple)):
        raise ValueError("plan['cited_documents'] must be a sequence")
    cited = tuple(
        normalise_identifier(value, "plan['cited_documents'] entry") for value in raw_cited
    )
    return {
        "sections": sections,
        "tasks": tasks,
        "reference_documents": references,
        "cited_documents": cited,
    }


def section_findings(normalised):
    """Return the per-section result of a normalised plan."""
    if not isinstance(normalised, dict) or "sections" not in normalised:
        raise ValueError("normalised must be the mapping returned by validate_plan")
    sections = normalised["sections"]
    missing = []
    incomplete = []
    accepted_not_applicable = []
    refused = []
    satisfied = 0
    for name in DRD_SECTIONS:
        entry = sections.get(name)
        if entry is None:
            missing.append(name)
            continue
        if entry["not_applicable"]:
            if name in UNTAILORABLE_SECTIONS:
                refused.append(
                    "%s cannot be declared not applicable; the plan would not state "
                    "what it covers or who is accountable" % name
                )
                continue
            if entry["justification"] is None:
                refused.append("%s is tailored out with no justification" % name)
                continue
            if entry["approved_by"] is None:
                refused.append("%s is tailored out with no customer approver" % name)
                continue
            accepted_not_applicable.append(name)
            satisfied += 1
            continue
        owed = SECTION_SUBJECTS[name]
        absent = [subject for subject in owed if subject not in entry["subjects"]]
        if absent:
            incomplete.append(
                "%s does not address %s" % (name, ", ".join(absent))
            )
            continue
        satisfied += 1
    extras = sorted(name for name in sections if name not in DRD_SECTIONS)
    findings = []
    if missing:
        findings.append("DRD sections the plan omits: %s" % ", ".join(missing))
    findings.extend(incomplete)
    findings.extend(refused)
    return {
        "required_count": len(DRD_SECTIONS),
        "satisfied_count": satisfied,
        "missing": missing,
        "incomplete": incomplete,
        "accepted_not_applicable": accepted_not_applicable,
        "refused_tailoring": refused,
        "extras": extras,
        "findings": findings,
    }


def task_findings(contract_level, normalised):
    """Return findings where the task provisions do not match the level."""
    owed = required_tasks(contract_level)
    declared = set(normalised["tasks"])
    absent = [task for task in owed if task not in declared]
    extras = sorted(task for task in declared if task not in owed)
    findings = []
    if absent:
        findings.append(
            "task provisions a %s plan owes and does not commit to: %s"
            % (normalise_identifier(contract_level, "contract_level"), ", ".join(absent))
        )
    return {"missing_tasks": absent, "extra_tasks": extras, "findings": findings}


def reference_findings(normalised):
    """Return findings where a cited document is not in the reference list."""
    listed = set(normalised["reference_documents"])
    dangling = [doc for doc in normalised["cited_documents"] if doc not in listed]
    seen = []
    for doc in dangling:
        if doc not in seen:
            seen.append(doc)
    if not seen:
        return []
    return ["documents cited by the plan but absent from its reference list: %s" % ", ".join(seen)]


def conformance_fraction(result):
    """Return the satisfied fraction of the DRD section list."""
    if not isinstance(result, dict):
        raise ValueError("result must be the mapping returned by section_findings")
    for key in ("required_count", "satisfied_count"):
        if key not in result:
            raise ValueError("result is missing '%s'" % key)
    if result["required_count"] <= 0:
        raise ValueError("required_count must be positive")
    return result["satisfied_count"] / float(result["required_count"])


def assess_qa_plan(contract_level, plan):
    """Grade a whole quality assurance plan against the Annex A DRD."""
    level = normalise_identifier(contract_level, "contract_level")
    normalised = validate_plan(plan)
    result = section_findings(normalised)
    tasks = task_findings(level, normalised)
    findings = list(result["findings"])
    findings.extend(tasks["findings"])
    findings.extend(reference_findings(normalised))
    return {
        "contract_level": level,
        "required_count": result["required_count"],
        "satisfied_count": result["satisfied_count"],
        "conformance_fraction": conformance_fraction(result),
        "missing_sections": result["missing"],
        "incomplete_sections": result["incomplete"],
        "accepted_not_applicable": result["accepted_not_applicable"],
        "refused_tailoring": result["refused_tailoring"],
        "missing_tasks": tasks["missing_tasks"],
        "extra_tasks": tasks["extra_tasks"],
        "extras": result["extras"],
        "findings": findings,
        "verdict": "plan-conformant" if not findings else "plan-nonconformant",
    }
