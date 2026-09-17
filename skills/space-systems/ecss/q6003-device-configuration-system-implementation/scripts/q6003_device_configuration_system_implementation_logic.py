"""Device configuration system able to regenerate any released baseline.

Anchor: ECSS-Q-ST-60-03 clause 8.2.1 (operate a configuration system under
which any released device baseline can be reproduced). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the released baselines: each needs an identifier, the device it
   belongs to, how many units were built to it, and the artefacts and tools it
   was produced from.
2. Decide per artefact whether it can still be retrieved as it was. Retention
   is not enough on its own: an artefact kept under its old name but rewritten
   in place is present and no longer the artefact the baseline used, and one
   with no recorded integrity value cannot be shown to be either.
3. Decide per tool whether the chain is reproducible. A tool reference that
   floats to whatever version is current today does not pin anything, and a
   withdrawn tool cannot be run at all however well the version is recorded.
4. Require at least one design source artefact per baseline. Netlists, test
   programmes and process records describe a build; none of them regenerates
   one.
5. Report the first failing check per baseline, so the finding names the
   defect the configuration system has to fix first.
6. Weight regeneration coverage by units built rather than by baseline count,
   because an unreproducible baseline behind a hundred flight units is not the
   same exposure as one behind a single engineering model.
"""

import math

__all__ = [
    "ARTEFACT_FIELDS",
    "BASELINE_FIELDS",
    "COVERAGE_TOLERANCE",
    "REGENERATING_ARTEFACT_KINDS",
    "RETENTION_STATES",
    "TOOL_AVAILABILITY",
    "UNPINNED_VERSION_TOKENS",
    "validate_baseline_id",
    "artefact_retrievability",
    "tool_reproducibility",
    "baseline_completeness",
    "evaluate_baseline",
    "regeneration_coverage",
    "assess_device_configuration_system",
]

# Coverage is a ratio of summed unit counts. An exactly-met requirement can
# land a few ULPs low; absorb the representation error here rather than
# lowering the level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Fields one released baseline record cannot be judged without.
BASELINE_FIELDS = (
    "baseline_id",
    "device_id",
    "units_built",
    "artefact_refs",
    "tool_refs",
)

# Fields one stored configuration artefact cannot be judged without.
ARTEFACT_FIELDS = ("artefact_id", "kind", "retention_state", "integrity_value")

# Retention state -> whether the stored copy can still be fetched as it was.
# "superseded-in-place" is the trap: the name resolves, the content does not
# match what the baseline was built from.
RETENTION_STATES = {
    "retained": True,
    "archived-offline": True,
    "archived-nearline": True,
    "superseded-in-place": False,
    "purged": False,
    "unknown": False,
}

# Tool availability -> whether the tool can still be executed today.
TOOL_AVAILABILITY = {
    "available": True,
    "archived-executable": True,
    "withdrawn": False,
    "unknown": False,
}

# Version strings that name no fixed version. A reference that resolves to
# whatever is current is not a pinned tool chain.
UNPINNED_VERSION_TOKENS = ("latest", "current", "head", "rolling", "trunk")

# Artefact kinds a device can actually be regenerated from. The others record
# a build; they do not reproduce one.
REGENERATING_ARTEFACT_KINDS = ("design-source", "mask-set")

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "artefact-reference-unresolved": 1,
    "tool-reference-unresolved": 2,
    "artefact-overwritten-in-place": 3,
    "artefact-not-retained": 4,
    "artefact-integrity-unrecorded": 5,
    "tool-withdrawn": 6,
    "tool-version-unpinned": 7,
    "regenerating-artefact-absent": 8,
    "regenerable": 10,
}

_REGENERABLE = "regenerable"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def validate_baseline_id(value):
    """Return the validated identifier of one released device baseline."""
    return _require_text(value, "baseline_id")


def artefact_retrievability(artefact):
    """Return (retrievable, reason) for one stored configuration artefact."""
    if not isinstance(artefact, dict):
        raise ValueError(
            "each artefact must be a mapping, got %r" % (type(artefact).__name__,)
        )
    for field in ("artefact_id", "kind", "retention_state"):
        _require_text(artefact.get(field), field)
    state = artefact["retention_state"].strip().lower()
    if state not in RETENTION_STATES:
        raise ValueError(
            "unknown retention_state %r; known: %s"
            % (artefact["retention_state"], ", ".join(sorted(RETENTION_STATES)))
        )
    if state == "superseded-in-place":
        return (False, "artefact-overwritten-in-place")
    if not RETENTION_STATES[state]:
        return (False, "artefact-not-retained")
    integrity = artefact.get("integrity_value")
    if not isinstance(integrity, str) or not integrity.strip():
        return (False, "artefact-integrity-unrecorded")
    return (True, None)


def tool_reproducibility(tool):
    """Return (reproducible, reason) for one recorded production tool."""
    if not isinstance(tool, dict):
        raise ValueError(
            "each tool must be a mapping, got %r" % (type(tool).__name__,)
        )
    _require_text(tool.get("tool_id"), "tool_id")
    availability = _require_text(tool.get("availability"), "availability").lower()
    if availability not in TOOL_AVAILABILITY:
        raise ValueError(
            "unknown availability %r; known: %s"
            % (tool["availability"], ", ".join(sorted(TOOL_AVAILABILITY)))
        )
    if not TOOL_AVAILABILITY[availability]:
        return (False, "tool-withdrawn")
    version = tool.get("version")
    if not isinstance(version, str) or not version.strip():
        return (False, "tool-version-unpinned")
    if version.strip().lower() in UNPINNED_VERSION_TOKENS:
        return (False, "tool-version-unpinned")
    return (True, None)


def baseline_completeness(baseline):
    """Return (missing_fields, completeness_fraction) for one baseline record."""
    if not isinstance(baseline, dict):
        raise ValueError(
            "each baseline must be a mapping, got %r" % (type(baseline).__name__,)
        )
    missing = []
    for field in BASELINE_FIELDS:
        if field not in baseline:
            missing.append(field)
            continue
        value = baseline[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
        elif isinstance(value, (list, tuple)) and not value:
            missing.append(field)
    total = len(BASELINE_FIELDS)
    return (tuple(missing), (total - len(missing)) / total)


def evaluate_baseline(baseline, artefact_index, tool_index):
    """Return the disposition record of one released device baseline."""
    if not isinstance(artefact_index, dict):
        raise ValueError("artefact_index must be a mapping of artefact_id -> artefact")
    if not isinstance(tool_index, dict):
        raise ValueError("tool_index must be a mapping of tool_id -> tool")
    missing, completeness = baseline_completeness(baseline)
    raw_label = baseline.get("baseline_id") if isinstance(baseline, dict) else None
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unidentified>"
    )
    record = {
        "baseline_id": label,
        "device_id": None,
        "missing_fields": missing,
        "completeness": completeness,
        "units_built": 0,
        "blocking_reference": None,
        "disposition": "record-incomplete",
        "regenerable": False,
    }
    if missing:
        return record

    record["device_id"] = _require_text(baseline["device_id"], "device_id")
    record["units_built"] = _require_positive_int(
        baseline["units_built"], "units_built"
    )

    artefact_refs = baseline["artefact_refs"]
    if not isinstance(artefact_refs, (list, tuple)):
        raise ValueError("artefact_refs must be a sequence of artefact identifiers")
    tool_refs = baseline["tool_refs"]
    if not isinstance(tool_refs, (list, tuple)):
        raise ValueError("tool_refs must be a sequence of tool identifiers")

    resolved = []
    for ref in artefact_refs:
        artefact_id = _require_text(ref, "artefact reference")
        if artefact_id not in artefact_index:
            record["disposition"] = "artefact-reference-unresolved"
            record["blocking_reference"] = artefact_id
            return record
        resolved.append(artefact_index[artefact_id])

    resolved_tools = []
    for ref in tool_refs:
        tool_id = _require_text(ref, "tool reference")
        if tool_id not in tool_index:
            record["disposition"] = "tool-reference-unresolved"
            record["blocking_reference"] = tool_id
            return record
        resolved_tools.append(tool_index[tool_id])

    for artefact in resolved:
        retrievable, reason = artefact_retrievability(artefact)
        if not retrievable:
            record["disposition"] = reason
            record["blocking_reference"] = artefact["artefact_id"]
            return record

    for tool in resolved_tools:
        reproducible, reason = tool_reproducibility(tool)
        if not reproducible:
            record["disposition"] = reason
            record["blocking_reference"] = tool["tool_id"]
            return record

    kinds = {artefact["kind"].strip().lower() for artefact in resolved}
    if not kinds.intersection(REGENERATING_ARTEFACT_KINDS):
        record["disposition"] = "regenerating-artefact-absent"
        return record

    record["disposition"] = _REGENERABLE
    record["regenerable"] = True
    return record


def regeneration_coverage(records):
    """Return the built-unit share sitting behind a regenerable baseline."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of baseline records")
    total = 0
    covered = 0
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        units = record.get("units_built", 0)
        if isinstance(units, bool) or not isinstance(units, int) or units < 0:
            raise ValueError("record units_built must be a non-negative integer")
        total += units
        if record["disposition"] == _REGENERABLE:
            covered += units
    if total <= 0:
        raise ValueError("no graded baseline carries a usable built-unit count")
    return covered / total


def assess_device_configuration_system(spec):
    """Run the full clause 8.2.1 configuration system assessment.

    spec keys: baselines (sequence of released baseline mappings), artefacts
    (sequence of stored artefact mappings), tools (sequence of tool mappings),
    optional required_coverage (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("baselines", "artefacts", "tools"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    baselines = spec["baselines"]
    if not isinstance(baselines, (list, tuple)) or not baselines:
        raise ValueError("spec['baselines'] must be a non-empty sequence")

    artefacts = spec["artefacts"]
    if not isinstance(artefacts, (list, tuple)):
        raise ValueError("spec['artefacts'] must be a sequence")
    tools = spec["tools"]
    if not isinstance(tools, (list, tuple)):
        raise ValueError("spec['tools'] must be a sequence")

    required = spec.get("required_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],)
        )

    artefact_index = {}
    for artefact in artefacts:
        if not isinstance(artefact, dict):
            raise ValueError("each artefact must be a mapping")
        artefact_id = _require_text(artefact.get("artefact_id"), "artefact_id")
        if artefact_id in artefact_index:
            raise ValueError("artefact %s is stored twice" % artefact_id)
        artefact_index[artefact_id] = artefact

    tool_index = {}
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("each tool must be a mapping")
        tool_id = _require_text(tool.get("tool_id"), "tool_id")
        if tool_id in tool_index:
            raise ValueError("tool %s is recorded twice" % tool_id)
        tool_index[tool_id] = tool

    records = []
    seen_baselines = set()
    for baseline in baselines:
        record = evaluate_baseline(baseline, artefact_index, tool_index)
        if record["baseline_id"] != "<unidentified>":
            if record["baseline_id"] in seen_baselines:
                raise ValueError(
                    "baseline %s is released twice" % record["baseline_id"]
                )
            seen_baselines.add(record["baseline_id"])
        records.append(record)

    graded = [record for record in records if record["units_built"] > 0]
    coverage = regeneration_coverage(records) if graded else 0.0

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition == _REGENERABLE:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 9),
                "reference": record["baseline_id"],
                "blocking_reference": record["blocking_reference"],
                "disposition": disposition,
                "detail": _finding_detail(record),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    conformant = meets and not findings
    return {
        "records": records,
        "regeneration_coverage": coverage,
        "required_coverage": required,
        "findings": findings,
        "conformant": conformant,
        "verdict": "conformant" if conformant else "non-conformant",
    }


def _finding_detail(record):
    """Return the human-readable reason one baseline cannot be regenerated."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "baseline record lacks %s; it cannot be judged at all" % ", ".join(
            record["missing_fields"]
        )
    if disposition == "artefact-reference-unresolved":
        return "the baseline cites an artefact the configuration system does not hold"
    if disposition == "tool-reference-unresolved":
        return "the baseline cites a tool the configuration system does not record"
    if disposition == "artefact-overwritten-in-place":
        return (
            "an artefact was rewritten under its old name, so the stored copy is "
            "no longer what the baseline was built from"
        )
    if disposition == "artefact-not-retained":
        return "an artefact the baseline needs is no longer held"
    if disposition == "artefact-integrity-unrecorded":
        return (
            "an artefact carries no integrity value, so the stored copy cannot be "
            "shown to be the one the baseline used"
        )
    if disposition == "tool-withdrawn":
        return "a tool the baseline was produced with can no longer be executed"
    if disposition == "tool-version-unpinned":
        return "a tool reference floats to whatever version is current today"
    return (
        "the baseline holds no artefact a device can be regenerated from, only "
        "records describing one that was"
    )
