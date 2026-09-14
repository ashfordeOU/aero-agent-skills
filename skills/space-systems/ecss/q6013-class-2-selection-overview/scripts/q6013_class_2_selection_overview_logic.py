"""Selection duties owed by a Class 2 commercial EEE component choice.

Anchor: ECSS-Q-ST-60-13C clause 5.2.1 (the framing of what a commercial
component selection owes at the intermediate assurance class, before any
single rule is applied to any single part). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared programme context and the per-part context. A
   condition that was never declared is unknown, not false, and the scoping
   refuses it rather than quietly dropping the duty it governs.
2. Decide which catalogued duties are in scope. At the intermediate class part
   of the duty set is conditional: it is owed only where the condition that
   makes it meaningful actually holds, which is what separates this framing
   from the highest class, where the whole set is owed unconditionally.
3. Instantiate the in-scope duties. A per-part duty produces one instance per
   candidate part; a per-programme duty produces exactly one instance for the
   whole programme and is never re-owed by each part.
4. Match the declared evidence to the instances and give each one a
   disposition: covered, waived under a named authority, mis-owned, open,
   rejected or absent.
5. Return the duty-coverage share against the declared minimum, the
   outstanding duties, and one selection-readiness verdict.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "DUTY_CATALOGUE",
    "CONDITION_SOURCE",
    "OWNER_ROLES",
    "EVIDENCE_STATUSES",
    "DISPOSITIONS",
    "DEFAULT_MINIMUM_COVERAGE",
    "validate_programme_context",
    "validate_part",
    "duty_instances",
    "validate_evidence",
    "disposition_of",
    "coverage_share",
    "assess_class2_selection_duties",
]

# The coverage share is a ratio of small integers; an exactly-met minimum can
# land a ULP low. Absorb that here, never by lowering the minimum.
COVERAGE_TOLERANCE = 1e-9

# Duty -> where it is owed, who owes it, what makes it owed, and whether it can
# be waived. A duty with condition None is owed unconditionally.
DUTY_CATALOGUE = {
    "usage-justification": {
        "scope": "per-part",
        "owner": "design-authority",
        "condition": None,
        "waivable": False,
    },
    "procurement-route-record": {
        "scope": "per-part",
        "owner": "procurement",
        "condition": None,
        "waivable": False,
    },
    "derating-declaration": {
        "scope": "per-part",
        "owner": "design-authority",
        "condition": None,
        "waivable": True,
    },
    "radiation-suitability": {
        "scope": "per-part",
        "owner": "product-assurance",
        "condition": "radiation-environment-declared",
        "waivable": False,
    },
    "lifetime-assessment": {
        "scope": "per-part",
        "owner": "product-assurance",
        "condition": "mission-beyond-short-duration",
        "waivable": False,
    },
    "evaluation-plan": {
        "scope": "per-part",
        "owner": "product-assurance",
        "condition": "no-qualification-heritage",
        "waivable": True,
    },
    "obsolescence-continuity": {
        "scope": "per-programme",
        "owner": "programme-management",
        "condition": "multi-batch-production",
        "waivable": True,
    },
    "customer-agreement": {
        "scope": "per-programme",
        "owner": "programme-management",
        "condition": None,
        "waivable": False,
    },
}

# Condition -> whether it is a fact about the programme or about the part.
CONDITION_SOURCE = {
    "radiation-environment-declared": "programme",
    "mission-beyond-short-duration": "programme",
    "multi-batch-production": "programme",
    "no-qualification-heritage": "part",
}

OWNER_ROLES = tuple(
    sorted({entry["owner"] for entry in DUTY_CATALOGUE.values()})
)

EVIDENCE_STATUSES = ("recorded", "open", "rejected", "waived")

DISPOSITIONS = (
    "covered",
    "waived",
    "mis-owned",
    "waiver-invalid",
    "open",
    "rejected",
    "absent",
)

_SETTLED = ("covered", "waived")

DEFAULT_MINIMUM_COVERAGE = 0.8

PROGRAMME_SUBJECT = "programme"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a real boolean, or raise. An absent condition is unknown, not false."""
    if not isinstance(value, bool):
        raise ValueError("%s must be declared true or false, got %r" % (label, value))
    return value


def _conditions_for(source):
    """Return the condition names sourced from the programme or from the part."""
    return tuple(
        sorted(name for name, origin in CONDITION_SOURCE.items() if origin == source)
    )


def validate_programme_context(context):
    """Return the validated programme-sourced condition declarations."""
    if not isinstance(context, dict):
        raise ValueError("programme context must be a mapping")
    expected = _conditions_for("programme")
    cleaned = {}
    for name in expected:
        if name not in context:
            raise ValueError(
                "programme condition %s was never declared; unknown is not false" % name
            )
        cleaned[name] = _require_bool(context[name], "programme condition %s" % name)
    for name in context:
        if name not in expected:
            raise ValueError("%s is not a programme-sourced condition" % name)
    return cleaned


def validate_part(part):
    """Return a validated candidate part with its part-sourced conditions."""
    if not isinstance(part, dict):
        raise ValueError("each candidate part must be a mapping")
    reference = _require_text(part.get("reference"), "part reference")
    if reference == PROGRAMME_SUBJECT:
        raise ValueError("a part may not be referenced as the programme itself")
    conditions = part.get("conditions")
    if not isinstance(conditions, dict):
        raise ValueError("part %s must carry a 'conditions' mapping" % reference)
    expected = _conditions_for("part")
    cleaned = {}
    for name in expected:
        if name not in conditions:
            raise ValueError(
                "part %s never declared the condition %s; unknown is not false"
                % (reference, name)
            )
        cleaned[name] = _require_bool(conditions[name], "part condition %s" % name)
    for name in conditions:
        if name not in expected:
            raise ValueError("%s is not a part-sourced condition" % name)
    return {"reference": reference, "conditions": cleaned}


def duty_instances(parts, context):
    """Return the in-scope duty instances for the declared parts and programme."""
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty sequence of candidate parts")
    programme = validate_programme_context(context)
    checked = []
    seen = set()
    for part in parts:
        entry = validate_part(part)
        if entry["reference"] in seen:
            raise ValueError("part %s appears more than once" % entry["reference"])
        seen.add(entry["reference"])
        checked.append(entry)

    instances = []
    for duty in sorted(DUTY_CATALOGUE):
        spec = DUTY_CATALOGUE[duty]
        condition = spec["condition"]
        if spec["scope"] == "per-programme":
            if condition is not None and not programme[condition]:
                continue
            instances.append(
                {
                    "duty": duty,
                    "scope": "per-programme",
                    "owner": spec["owner"],
                    "subject": PROGRAMME_SUBJECT,
                    "waivable": spec["waivable"],
                }
            )
            continue
        for part in checked:
            if condition is not None:
                if CONDITION_SOURCE[condition] == "programme":
                    holds = programme[condition]
                else:
                    holds = part["conditions"][condition]
                if not holds:
                    continue
            instances.append(
                {
                    "duty": duty,
                    "scope": "per-part",
                    "owner": spec["owner"],
                    "subject": part["reference"],
                    "waivable": spec["waivable"],
                }
            )
    return tuple(instances)


def validate_evidence(record):
    """Return a validated evidence record for one duty instance."""
    if not isinstance(record, dict):
        raise ValueError("each evidence record must be a mapping")
    duty = _require_text(record.get("duty"), "evidence duty")
    if duty not in DUTY_CATALOGUE:
        raise ValueError("%s is not a catalogued selection duty" % duty)
    subject = _require_text(record.get("subject"), "evidence subject")
    if DUTY_CATALOGUE[duty]["scope"] == "per-programme" and subject != PROGRAMME_SUBJECT:
        raise ValueError(
            "%s is owed once for the programme; it cannot be recorded against part %s"
            % (duty, subject)
        )
    if DUTY_CATALOGUE[duty]["scope"] == "per-part" and subject == PROGRAMME_SUBJECT:
        raise ValueError("%s is owed per part; it cannot be recorded once for the programme" % duty)
    owner = _require_text(record.get("owner"), "evidence owner")
    if owner not in OWNER_ROLES:
        raise ValueError("%s is not a declared owner role" % owner)
    status = _require_text(record.get("status"), "evidence status")
    if status not in EVIDENCE_STATUSES:
        raise ValueError("%s is not a declared evidence status" % status)
    reference = record.get("reference")
    if status == "recorded":
        reference = _require_text(reference, "evidence reference for %s" % duty)
    elif reference is not None:
        reference = _require_text(reference, "evidence reference for %s" % duty)
    authority = record.get("waiver_authority")
    if status == "waived":
        authority = _require_text(authority, "waiver authority for %s" % duty)
    elif authority is not None:
        authority = _require_text(authority, "waiver authority for %s" % duty)
    return {
        "duty": duty,
        "subject": subject,
        "owner": owner,
        "status": status,
        "reference": reference,
        "waiver_authority": authority,
    }


def disposition_of(instance, records):
    """Return the disposition of one duty instance against the evidence records."""
    if not isinstance(instance, dict) or "duty" not in instance:
        raise ValueError("instance must be a duty instance mapping")
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of evidence records")
    matches = [
        record
        for record in records
        if record["duty"] == instance["duty"] and record["subject"] == instance["subject"]
    ]
    if len(matches) > 1:
        raise ValueError(
            "duty %s for %s carries more than one evidence record"
            % (instance["duty"], instance["subject"])
        )
    if not matches:
        return "absent"
    record = matches[0]
    if record["owner"] != instance["owner"]:
        return "mis-owned"
    if record["status"] == "recorded":
        return "covered"
    if record["status"] == "waived":
        return "waived" if instance["waivable"] else "waiver-invalid"
    return record["status"]


def coverage_share(dispositions):
    """Return the share of duty instances that are settled."""
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    settled = 0
    for entry in dispositions:
        name = _require_text(entry, "disposition")
        if name not in DISPOSITIONS:
            raise ValueError("%s is not a declared disposition" % name)
        if name in _SETTLED:
            settled += 1
    return settled / len(dispositions)


def assess_class2_selection_duties(spec):
    """Run the full clause 5.2.1 intermediate-class selection duty framing.

    spec keys: parts (sequence), context (programme conditions), evidence
    (sequence of records), optional minimum_coverage (default 0.8).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parts", "context"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    minimum = spec.get("minimum_coverage", DEFAULT_MINIMUM_COVERAGE)
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        raise ValueError("minimum_coverage must be a real number")
    minimum = float(minimum)
    if not math.isfinite(minimum) or minimum < 0.0 or minimum > 1.0:
        raise ValueError("minimum_coverage must lie in [0, 1]")

    instances = duty_instances(spec["parts"], spec["context"])
    raw = spec.get("evidence", ())
    if not isinstance(raw, (list, tuple)):
        raise ValueError("evidence must be a sequence of records")
    records = [validate_evidence(record) for record in raw]

    graded = []
    for instance in instances:
        entry = dict(instance)
        entry["disposition"] = disposition_of(instance, records)
        graded.append(entry)

    keys = {(instance["duty"], instance["subject"]) for instance in instances}
    unmatched = tuple(
        sorted(
            "%s/%s" % (record["duty"], record["subject"])
            for record in records
            if (record["duty"], record["subject"]) not in keys
        )
    )

    share = coverage_share([entry["disposition"] for entry in graded])
    outstanding = [entry for entry in graded if entry["disposition"] not in _SETTLED]
    blocking = [entry for entry in outstanding if not entry["waivable"]]

    findings = []
    for entry in outstanding:
        findings.append(
            {
                "severity": 0 if not entry["waivable"] else 1,
                "duty": entry["duty"],
                "subject": entry["subject"],
                "detail": "%s for %s is %s; owed to %s"
                % (entry["duty"], entry["subject"], entry["disposition"], entry["owner"]),
            }
        )
    for key in unmatched:
        findings.append(
            {
                "severity": 2,
                "duty": key.split("/")[0],
                "subject": key.split("/")[1],
                "detail": "evidence recorded for %s, which is not in scope" % key,
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["duty"], entry["subject"]))

    meets = share > minimum or math.isclose(
        share, minimum, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if blocking or not meets:
        verdict = "not-selection-ready"
    elif outstanding:
        verdict = "selection-ready-with-actions"
    else:
        verdict = "selection-ready"
    return {
        "instances": graded,
        "instance_count": len(graded),
        "coverage_share": share,
        "minimum_coverage": minimum,
        "outstanding": tuple(
            sorted((entry["duty"], entry["subject"]) for entry in outstanding)
        ),
        "unmatched_evidence": unmatched,
        "findings": findings,
        "verdict": verdict,
    }
