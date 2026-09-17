"""Device reuse file DRD evaluation: heritage evidence for a reused device.

Anchor: ECSS-Q-ST-60-03C Annex C (the document requirements definition
that fixes the content of the reuse file, the record that holds the
heritage evidence offered in support of reusing a device in a new
application). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Read the drafted reuse file as section key -> body and refuse a
   section that is present but blank.
2. Check each heritage item is identified well enough to be traced: the
   element it names, the application it flew or ran in, the
   qualification state that application left it in, and a reference into
   an evidence register that actually resolves.
3. Compare the environment the new application imposes against the
   envelope the heritage established, one parameter at a time and in the
   direction each parameter is bounded. A duty outside the envelope does
   not void the reuse; it converts the reuse into a delta-qualification
   with a named parameter behind it.
4. Check every declared change between the heritage build and the new
   one carries an impact assessment and a verification action. An
   unassessed change is the mechanism by which heritage silently stops
   applying.
5. Aggregate into one disposition: the reuse is substantiated, needs a
   delta qualification, or is not substantiated at all.
"""

import math

__all__ = [
    "REQUIRED_FILE_SECTIONS",
    "REQUIRED_HERITAGE_FIELDS",
    "QUALIFICATION_STATES",
    "ENVELOPE_DIRECTIONS",
    "ENVELOPE_TOLERANCE",
    "missing_file_sections",
    "heritage_item_deficiencies",
    "unresolved_evidence_references",
    "envelope_exceedances",
    "unassessed_changes",
    "assess_device_reuse_file_drd",
]

# The content blocks Annex C expects the reuse file to carry.
REQUIRED_FILE_SECTIONS = (
    "introduction",
    "reused-element-identification",
    "previous-application-record",
    "heritage-environment-envelope",
    "change-record",
    "verification-evidence",
    "open-risks-and-limitations",
    "reuse-justification",
)

# What each heritage item must state before it can be traced at all.
REQUIRED_HERITAGE_FIELDS = (
    "element_id",
    "previous_application",
    "qualification_state",
    "evidence_reference",
)

# The states a previous application can have left the element in.
QUALIFICATION_STATES = (
    "fully-qualified",
    "qualified-with-limitations",
    "flight-proven-not-qualified",
    "development-only",
)

# How an envelope parameter is bounded: an upper bound the new duty must
# stay under, a lower bound it must stay above, or a bound on the
# magnitude of an excursion that may go either way.
ENVELOPE_DIRECTIONS = ("max", "min", "abs")

# A new duty that lands exactly on a heritage bound is inside it. The
# bound and the duty are floats from two different computations, so the
# equality is absorbed here rather than by moving the bound.
ENVELOPE_TOLERANCE = 1e-9

# Qualification states that cannot carry a reuse on their own, whatever
# the envelope says.
WEAK_STATES = ("flight-proven-not-qualified", "development-only")


def _nonempty_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence(label, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, value))
    return list(value)


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def missing_file_sections(reuse_file):
    """Return the required reuse-file sections that are absent or blank."""
    if not isinstance(reuse_file, dict):
        raise ValueError(
            "reuse_file must be a mapping of section key to body, got %r" % (reuse_file,)
        )
    missing = []
    for key in REQUIRED_FILE_SECTIONS:
        body = reuse_file.get(key)
        if not isinstance(body, str) or not body.strip():
            missing.append(key)
    return missing


def heritage_item_deficiencies(items):
    """Return the per-item deficiency records for the heritage item list.

    items is a non-empty sequence of mappings carrying the fields in
    REQUIRED_HERITAGE_FIELDS. Returns a list of mappings, one per
    deficient item, each with the element identifier (or the item index
    when even that is absent) and the deficiency tags found. Raises
    ValueError when items is not a non-empty sequence, or when an entry
    is not a mapping, because a malformed list cannot be scored.
    """
    entries = _sequence("items", items)
    if not entries:
        raise ValueError("items must carry at least one heritage item")
    deficient = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("items[%d] must be a mapping, got %r" % (index, entry))
        tags = []
        for field in REQUIRED_HERITAGE_FIELDS:
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                tags.append("missing-%s" % field.replace("_", "-"))
        state = entry.get("qualification_state")
        if isinstance(state, str) and state.strip():
            normalised = state.strip().lower()
            if normalised not in QUALIFICATION_STATES:
                raise ValueError(
                    "items[%d] qualification_state %r is not one of %s"
                    % (index, state, ", ".join(QUALIFICATION_STATES))
                )
            if normalised in WEAK_STATES:
                tags.append("weak-qualification-state")
        if tags:
            element = entry.get("element_id")
            label = element.strip() if isinstance(element, str) and element.strip() else "items[%d]" % index
            deficient.append({"element_id": label, "deficiencies": tags})
    return deficient


def unresolved_evidence_references(items, evidence_register):
    """Return heritage evidence references absent from the evidence register.

    evidence_register is the set of reference identifiers the project can
    actually produce a document for. Returns the unresolved references in
    the order the items declare them, with duplicates collapsed. Raises
    ValueError when the register is not a sequence or set.
    """
    if isinstance(evidence_register, (str, bytes)) or not isinstance(
        evidence_register, (list, tuple, set, frozenset)
    ):
        raise ValueError(
            "evidence_register must be a sequence or set of references, got %r"
            % (evidence_register,)
        )
    known = {ref.strip() for ref in evidence_register if isinstance(ref, str)}
    unresolved = []
    for index, entry in enumerate(_sequence("items", items)):
        if not isinstance(entry, dict):
            raise ValueError("items[%d] must be a mapping, got %r" % (index, entry))
        ref = entry.get("evidence_reference")
        if not isinstance(ref, str) or not ref.strip():
            continue
        ref = ref.strip()
        if ref not in known and ref not in unresolved:
            unresolved.append(ref)
    return unresolved


def envelope_exceedances(heritage_envelope, new_duty):
    """Return the parameters where the new duty leaves the heritage envelope.

    heritage_envelope maps a parameter name to a mapping with 'bound' and
    'direction' (one of ENVELOPE_DIRECTIONS). new_duty maps the same
    parameter names to the value the new application imposes. Returns a
    list of mappings naming the parameter, its bound, the duty and the
    margin by which the bound was left, plus a separate list of the
    parameters the new duty never declared. Raises ValueError on a
    malformed envelope entry, an unknown direction, a negative magnitude
    bound, or a duty parameter the envelope never covered.
    """
    if not isinstance(heritage_envelope, dict) or not heritage_envelope:
        raise ValueError("heritage_envelope must be a non-empty mapping")
    if not isinstance(new_duty, dict):
        raise ValueError("new_duty must be a mapping of parameter to value")
    for parameter in new_duty:
        if parameter not in heritage_envelope:
            raise ValueError(
                "new_duty declares %r, which the heritage envelope never bounds" % parameter
            )
    exceeded = []
    undeclared = []
    for parameter in sorted(heritage_envelope):
        spec = heritage_envelope[parameter]
        if not isinstance(spec, dict):
            raise ValueError("envelope entry %r must be a mapping, got %r" % (parameter, spec))
        for key in ("bound", "direction"):
            if key not in spec:
                raise ValueError("envelope entry %r is missing '%s'" % (parameter, key))
        direction = spec["direction"]
        if direction not in ENVELOPE_DIRECTIONS:
            raise ValueError(
                "envelope entry %r has direction %r; expected one of %s"
                % (parameter, direction, ", ".join(ENVELOPE_DIRECTIONS))
            )
        bound = _real("envelope entry %r bound" % parameter, spec["bound"])
        if direction == "abs" and bound < 0.0:
            raise ValueError("a magnitude bound must be non-negative, got %g" % bound)
        if parameter not in new_duty:
            undeclared.append(parameter)
            continue
        duty = _real("new_duty[%r]" % parameter, new_duty[parameter])
        if direction == "max":
            margin = bound - duty
        elif direction == "min":
            margin = duty - bound
        else:
            margin = bound - abs(duty)
        if margin < -ENVELOPE_TOLERANCE:
            exceeded.append(
                {
                    "parameter": parameter,
                    "direction": direction,
                    "bound": bound,
                    "duty": duty,
                    "exceeded_by": -margin,
                }
            )
    return {"exceeded": exceeded, "undeclared": undeclared}


def unassessed_changes(changes):
    """Return changes between the heritage build and the new one lacking rigour.

    changes is a sequence of mappings with 'change_id', an
    'impact_assessment' body and a 'verification_action'. Returns a list
    of mappings naming the change and its deficiency tags. Raises
    ValueError when an entry is not a mapping or has no identifier: an
    anonymous change cannot be tracked to closure.
    """
    deficient = []
    for index, entry in enumerate(_sequence("changes", changes)):
        if not isinstance(entry, dict):
            raise ValueError("changes[%d] must be a mapping, got %r" % (index, entry))
        change_id = _nonempty_text("changes[%d]['change_id']" % index, entry.get("change_id"))
        tags = []
        for field in ("impact_assessment", "verification_action"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                tags.append("missing-%s" % field.replace("_", "-"))
        if tags:
            deficient.append({"change_id": change_id, "deficiencies": tags})
    return deficient


def assess_device_reuse_file_drd(spec):
    """Return the aggregate Annex C verdict for a drafted reuse file.

    spec keys: reuse_file, heritage_items, evidence_register,
    heritage_envelope, new_duty and changes. Returns the individual
    records, a flat 'findings' list and a 'disposition' of
    'reuse-substantiated', 'delta-qualification-required' or
    'reuse-not-substantiated'.

    An envelope exceedance alone converts the reuse into a delta
    qualification, because the heritage is real but does not reach the
    new duty. Any documentary defect -- a missing section, an untraceable
    heritage item, an evidence reference that resolves nowhere, an
    undeclared duty parameter or an unassessed change -- leaves the reuse
    unsubstantiated, because there is nothing to write a delta against.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    required = (
        "reuse_file",
        "heritage_items",
        "evidence_register",
        "heritage_envelope",
        "new_duty",
        "changes",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    missing_sections = missing_file_sections(spec["reuse_file"])
    item_defects = heritage_item_deficiencies(spec["heritage_items"])
    unresolved = unresolved_evidence_references(
        spec["heritage_items"], spec["evidence_register"]
    )
    envelope = envelope_exceedances(spec["heritage_envelope"], spec["new_duty"])
    change_defects = unassessed_changes(spec["changes"])
    documentary = []
    for key in missing_sections:
        documentary.append("required reuse-file section '%s' is absent or blank" % key)
    for record in item_defects:
        documentary.append(
            "heritage item '%s' is deficient: %s"
            % (record["element_id"], ", ".join(record["deficiencies"]))
        )
    for ref in unresolved:
        documentary.append("evidence reference '%s' resolves to nothing in the register" % ref)
    for parameter in envelope["undeclared"]:
        documentary.append(
            "new duty never declares envelope parameter '%s', so heritage cannot be compared"
            % parameter
        )
    for record in change_defects:
        documentary.append(
            "change '%s' is deficient: %s"
            % (record["change_id"], ", ".join(record["deficiencies"]))
        )
    envelope_findings = [
        "new duty on '%s' leaves the heritage envelope by %g"
        % (record["parameter"], record["exceeded_by"])
        for record in envelope["exceeded"]
    ]
    if documentary:
        disposition = "reuse-not-substantiated"
    elif envelope_findings:
        disposition = "delta-qualification-required"
    else:
        disposition = "reuse-substantiated"
    return {
        "missing_sections": missing_sections,
        "heritage_item_defects": item_defects,
        "unresolved_evidence": unresolved,
        "envelope": envelope,
        "change_defects": change_defects,
        "documentary_findings": documentary,
        "envelope_findings": envelope_findings,
        "findings": documentary + envelope_findings,
        "disposition": disposition,
    }
