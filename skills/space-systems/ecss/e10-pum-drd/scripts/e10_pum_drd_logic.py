"""ECSS-E-ST-10C Annex P product user manual DRD (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex P
Document Requirements Definition governs the Product User Manual delivered
with a product. The manual is written against one configuration of one
product and must say which; it carries a fixed set of sections (description,
operating procedures, maintenance, safety, limitations, handling); every
operating step that touches a hazard carries its warning BEFORE the step, not
after it; and every maintenance task states both its interval and what it
needs. A manual whose declared configuration does not match the delivered
product is not a documentation defect -- it describes a different article.
"""

REQUIRED_SECTIONS = ("product_description", "operating_procedures",
                     "maintenance", "safety", "limitations", "handling")
HAZARD_CLASSES = ("pressure", "pyrotechnic", "electrical", "cryogenic",
                  "radiation", "chemical", "mechanical")


def validate_hazard_class(hazard):
    """Return hazard if it is a recognized hazard class, else raise."""
    if hazard not in HAZARD_CLASSES:
        raise ValueError("unknown hazard class: %r" % (hazard,))
    return hazard


def missing_sections(manual):
    """Required Annex P sections absent or empty, in the declared order. An
    empty section and an absent one are the same defect: nothing to read."""
    sections = manual.get("sections", {})
    return [s for s in REQUIRED_SECTIONS
            if not (sections.get(s) or "").strip()]


def configuration_violations(manual, delivered_configuration):
    """Findings when the manual does not identify the article it describes, or
    identifies a different one from what was delivered."""
    declared = manual.get("configuration")
    if not declared:
        return [{"issue": "no_declared_configuration"}]
    if declared != delivered_configuration:
        return [{"issue": "configuration_mismatch", "declared": declared,
                 "delivered": delivered_configuration}]
    return []


def step_numbering_violations(steps):
    """Findings for a procedure's step numbering: a duplicate number, or a
    sequence that does not run 1..n. Operators follow steps by number, so a
    gap or a repeat is an execution hazard, not a typographic one."""
    numbers = [s.get("number") for s in steps]
    out = []
    if len(set(numbers)) != len(numbers):
        out.append({"issue": "duplicate_step_number"})
    if numbers and sorted(numbers) != list(range(1, len(numbers) + 1)):
        out.append({"issue": "step_numbering_not_contiguous"})
    return out


def hazard_warning_violations(procedure):
    """Findings for hazardous steps lacking their warning, or carrying it in
    the wrong place.

    procedure: {"procedure_id": str, "steps": [{"number": int, "hazard": str |
    None, "warning_before": bool}]}. A warning that follows the step it
    protects has already failed -- the operator reads it after acting.
    """
    pid = procedure.get("procedure_id")
    out = []
    for step in procedure.get("steps", []):
        hazard = step.get("hazard")
        if not hazard:
            continue
        validate_hazard_class(hazard)
        if not step.get("warning_before"):
            out.append({"procedure_id": pid, "number": step.get("number"),
                        "hazard": hazard, "issue": "hazard_warning_not_before_step"})
    return out


def maintenance_violations(tasks):
    """Findings for maintenance tasks missing their interval or their required
    resources. A task with no interval is never scheduled; a task with no
    stated tooling or consumables cannot be prepared for."""
    out = []
    for t in tasks:
        tid = t.get("task_id")
        if not tid:
            raise ValueError("maintenance task with no task_id")
        if not t.get("interval"):
            out.append({"task_id": tid, "issue": "no_maintenance_interval"})
        if not t.get("resources"):
            out.append({"task_id": tid, "issue": "no_required_resources"})
    return out


def pum_review(manual, delivered_configuration):
    """Full Annex P product user manual review.

    manual: {"configuration": str, "sections": {name: text},
             "procedures": [procedure], "maintenance_tasks": [task]}

    Returns {"configuration", "findings"}. Raises ValueError for an unknown
    hazard class or a maintenance task with no identifier.
    """
    findings = []
    for s in missing_sections(manual):
        findings.append({"section": s, "issue": "missing_section"})
    findings += configuration_violations(manual, delivered_configuration)
    for proc in manual.get("procedures", []):
        findings += [dict(f, procedure_id=proc.get("procedure_id"))
                     for f in step_numbering_violations(proc.get("steps", []))]
        findings += hazard_warning_violations(proc)
    findings += maintenance_violations(manual.get("maintenance_tasks", []))
    return {"configuration": manual.get("configuration"), "findings": findings}


def is_pum_deliverable(review):
    """True when the manual may ship with the product -- no findings."""
    return not review["findings"]
