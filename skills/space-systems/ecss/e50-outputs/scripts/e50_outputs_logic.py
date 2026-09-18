"""Output-set audit for the communication system engineering process.

Anchor: ECSS-E-ST-50C clause 5.2.1.3 -- the outputs the communication system
engineering step produces. Paraphrased into an implementable procedure; no
standard text is reproduced.

The single normative item fixes what the step hands on. A step is finished when
its outputs exist, not when its activities stop, and "exists" is stricter than
it sounds. This module grades a declared output set on the three ways a claimed
output turns out not to be one:

  1. absent      -- a required output nobody declared;
  2. unidentified -- declared, but with no identifier, so it cannot be called
                     for by name at the next step or in a review;
  3. untraced    -- declared, but produced by no activity of the step, which
                     means it arrived from somewhere the step does not control.

Duplicated output names are graded separately, because two entries under one
name leave nobody able to say which copy is the deliverable.
"""

__all__ = [
    "COMPLETE",
    "INCOMPLETE",
    "normalize_output",
    "validate_output_set",
    "assess_completeness",
    "find_unidentified_outputs",
    "find_untraced_outputs",
    "find_duplicate_output_names",
    "audit_outputs",
]

COMPLETE = "complete"
INCOMPLETE = "incomplete"


def _clean_name(value, field):
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % field)
    token = value.strip()
    if not token:
        raise ValueError("%s must not be empty" % field)
    return token


def _clean_name_list(values, field):
    if isinstance(values, str):
        raise ValueError("%s must be a list of names, not a single string" % field)
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple" % field)
    return [_clean_name(value, "%s[%d]" % (field, i)) for i, value in enumerate(values)]


def normalize_output(record):
    """Return one declared output as a validated dict.

    The name is required. The identifier and the producing activity may be
    declared as absent -- they are graded, not rejected, because an output with
    neither is exactly the case the audit exists to surface.
    """
    if not isinstance(record, dict):
        raise ValueError("output must be a mapping with at least a name")
    if "name" not in record:
        raise ValueError("output is missing name")
    identifier = record.get("identifier")
    if identifier is not None:
        if not isinstance(identifier, str):
            raise ValueError("identifier must be a string or absent")
        identifier = identifier.strip() or None
    produced_by = record.get("produced_by")
    if produced_by is not None:
        if not isinstance(produced_by, str):
            raise ValueError("produced_by must be a string or absent")
        produced_by = produced_by.strip() or None
    return {
        "name": _clean_name(record["name"], "output name"),
        "identifier": identifier,
        "produced_by": produced_by,
    }


def validate_output_set(outputs):
    """Return the declared outputs validated. Duplicates are kept for grading."""
    if isinstance(outputs, dict) or not isinstance(outputs, (list, tuple)):
        raise ValueError("outputs must be a list or tuple of output mappings")
    if not outputs:
        raise ValueError("outputs must not be empty")
    return [normalize_output(record) for record in outputs]


def assess_completeness(required, outputs):
    """Compare the required output set against what the step declares."""
    wanted = _clean_name_list(required, "required")
    if not wanted:
        raise ValueError("required must not be empty")
    declared = [output["name"] for output in validate_output_set(outputs)]
    declared_set = set(declared)
    present = [name for name in wanted if name in declared_set]
    missing = [name for name in wanted if name not in declared_set]
    wanted_set = set(wanted)
    undeclared = sorted(set(name for name in declared if name not in wanted_set))
    return {
        "required": wanted,
        "present": present,
        "missing": missing,
        "undeclared": undeclared,
        "completion_fraction": float(len(present)) / float(len(wanted)),
    }


def find_unidentified_outputs(outputs):
    """Name the declared outputs that carry no identifier."""
    findings = []
    for output in validate_output_set(outputs):
        if output["identifier"] is None:
            findings.append(
                "output %r carries no identifier and cannot be called for by "
                "name at the next step" % output["name"]
            )
    return findings


def find_untraced_outputs(outputs, activities):
    """Name outputs no activity of the step produces."""
    known = set(_clean_name_list(activities, "activities"))
    findings = []
    for output in validate_output_set(outputs):
        producer = output["produced_by"]
        if producer is None:
            findings.append(
                "output %r names no producing activity; it is asserted rather "
                "than produced by the step" % output["name"]
            )
        elif producer not in known:
            findings.append(
                "output %r names producing activity %r, which is not an activity "
                "of this step" % (output["name"], producer)
            )
    return findings


def find_duplicate_output_names(outputs):
    """Name any output declared more than once."""
    seen = {}
    for output in validate_output_set(outputs):
        seen[output["name"]] = seen.get(output["name"], 0) + 1
    findings = []
    for name in sorted(seen):
        if seen[name] > 1:
            findings.append(
                "output %r is declared %d times; which copy is the deliverable "
                "is undetermined" % (name, seen[name])
            )
    return findings


def audit_outputs(required, outputs, activities):
    """Grade a declared output set against the clause in one pass."""
    completeness = assess_completeness(required, outputs)
    unidentified = find_unidentified_outputs(outputs)
    untraced = find_untraced_outputs(outputs, activities)
    duplicates = find_duplicate_output_names(outputs)
    findings = []
    if completeness["missing"]:
        findings.append(
            "%d required output(s) not declared: %s"
            % (len(completeness["missing"]), ", ".join(completeness["missing"]))
        )
    findings.extend(unidentified)
    findings.extend(untraced)
    findings.extend(duplicates)
    return {
        "completion_fraction": completeness["completion_fraction"],
        "missing": completeness["missing"],
        "undeclared": completeness["undeclared"],
        "unidentified": unidentified,
        "untraced": untraced,
        "duplicates": duplicates,
        "findings": findings,
        "verdict": COMPLETE if not findings else INCOMPLETE,
    }
