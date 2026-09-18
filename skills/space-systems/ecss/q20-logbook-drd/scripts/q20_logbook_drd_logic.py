"""Unit logbook document requirements description.

Anchor: ECSS-Q-ST-20C Annex C (normative), the document requirements
description for the logbook that travels with a unit: the running record of
what was done to it, what was inspected on it, what was modified in it, and
what environment it saw. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every entry against the field set its type owes.
2. Check the sequence: entries numbered from one, no gap, no repeat.
3. Check the chronology: entry dates never run backwards down the sequence.
4. Trace the configuration through the modification entries, so each one
   starts from the state the previous one left.
5. Find the environmental entries that ran outside their stated limit and
   were not tied to a nonconformance.
6. Accumulate the exposure the logbook records, per parameter and in total.
7. Return the whole-logbook findings and its verdict.
"""

from datetime import date

__all__ = [
    "ENTRY_TYPES",
    "ENTRY_FIELDS",
    "COMMON_FIELDS",
    "INSPECTION_RESULTS",
    "normalise_identifier",
    "parse_day",
    "validate_entry",
    "normalise_logbook",
    "sequence_findings",
    "chronology_findings",
    "configuration_trace_findings",
    "inspection_result_findings",
    "environmental_excursions",
    "cumulative_exposure",
    "assess_logbook",
]

# The four kinds of line the logbook carries.
ENTRY_TYPES = ("history", "inspection", "modification", "environmental")

# Fields every entry carries whatever its type.
COMMON_FIELDS = ("sequence", "entry_date", "entry_type", "signed_by")

# What each type adds on top of the common fields.
ENTRY_FIELDS = {
    "history": ("activity", "location", "reference"),
    "inspection": ("inspection_type", "result", "reference"),
    "modification": ("modification_reference", "configuration_before", "configuration_after"),
    "environmental": ("parameter", "value", "unit", "duration_hours"),
}

# Inspection results the logbook recognises.
INSPECTION_RESULTS = ("pass", "fail", "conditional")


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO date; raise on anything that is not one."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def validate_entry(entry, index):
    """Return one normalised logbook entry; raise on a malformed one."""
    if not isinstance(entry, dict):
        raise ValueError("entry[%d] must be a mapping" % index)
    entry_type = normalise_identifier(entry.get("entry_type"), "entry[%d].entry_type" % index)
    if entry_type not in ENTRY_TYPES:
        raise ValueError(
            "entry[%d].entry_type must be one of %s, got %r"
            % (index, "/".join(ENTRY_TYPES), entry_type)
        )
    sequence = entry.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError(
            "entry[%d].sequence must be an integer of at least 1, got %r" % (index, sequence)
        )
    result = {
        "sequence": sequence,
        "entry_type": entry_type,
        "entry_date": parse_day(entry.get("entry_date"), "entry[%d].entry_date" % index),
        "signed_by": normalise_identifier(entry.get("signed_by"), "entry[%d].signed_by" % index),
        "nonconformance": None,
    }
    raw_nc = entry.get("nonconformance")
    if raw_nc is not None:
        result["nonconformance"] = normalise_identifier(
            raw_nc, "entry[%d].nonconformance" % index
        )
    for field in ENTRY_FIELDS[entry_type]:
        value = entry.get(field)
        if field in ("value", "duration_hours", "limit"):
            continue
        result[field] = normalise_identifier(value, "entry[%d].%s" % (index, field))
    if entry_type == "inspection" and result["result"] not in INSPECTION_RESULTS:
        raise ValueError(
            "entry[%d].result must be one of %s, got %r"
            % (index, "/".join(INSPECTION_RESULTS), result["result"])
        )
    if entry_type == "environmental":
        for field in ("value", "duration_hours"):
            value = entry.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    "entry[%d].%s must be a number, got %r" % (index, field, value)
                )
            result[field] = float(value)
        if result["duration_hours"] < 0.0:
            raise ValueError("entry[%d].duration_hours must not be negative" % index)
        limit = entry.get("limit")
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, (int, float)):
                raise ValueError("entry[%d].limit must be a number, got %r" % (index, limit))
            limit = float(limit)
        result["limit"] = limit
    return result


def normalise_logbook(entries):
    """Return the validated logbook in submitted order."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence")
    return [validate_entry(entry, index) for index, entry in enumerate(entries)]


def sequence_findings(book):
    """Return findings where the entry numbering is broken."""
    numbers = [entry["sequence"] for entry in book]
    findings = []
    seen = set()
    for number in numbers:
        if number in seen:
            findings.append("entry number %d appears more than once" % number)
        seen.add(number)
    expected = list(range(1, len(numbers) + 1))
    absent = [number for number in expected if number not in seen]
    if absent:
        findings.append(
            "the logbook has no entry numbered %s"
            % ", ".join(str(number) for number in absent)
        )
    return findings


def chronology_findings(book):
    """Return findings where an entry is dated before the one before it."""
    findings = []
    ordered = sorted(book, key=lambda entry: entry["sequence"])
    for previous, current in zip(ordered, ordered[1:]):
        if current["entry_date"] < previous["entry_date"]:
            findings.append(
                "entry %d is dated %s, before entry %d dated %s"
                % (
                    current["sequence"],
                    current["entry_date"].isoformat(),
                    previous["sequence"],
                    previous["entry_date"].isoformat(),
                )
            )
    return findings


def configuration_trace_findings(book, initial_configuration):
    """Return findings where the modification chain does not join up."""
    state = normalise_identifier(initial_configuration, "initial_configuration")
    findings = []
    for entry in sorted(book, key=lambda item: item["sequence"]):
        if entry["entry_type"] != "modification":
            continue
        if entry["configuration_before"] != state:
            findings.append(
                "entry %d modifies from %s while the unit stands at %s"
                % (entry["sequence"], entry["configuration_before"], state)
            )
        if entry["configuration_after"] == entry["configuration_before"]:
            findings.append(
                "entry %d records a modification that leaves the configuration unchanged"
                % entry["sequence"]
            )
        state = entry["configuration_after"]
    return findings, state


def environmental_excursions(book):
    """Return the environmental entries that ran past their stated limit."""
    excursions = []
    for entry in sorted(book, key=lambda item: item["sequence"]):
        if entry["entry_type"] != "environmental":
            continue
        limit = entry.get("limit")
        if limit is None:
            continue
        if entry["value"] > limit:
            excursions.append(
                {
                    "sequence": entry["sequence"],
                    "parameter": entry["parameter"],
                    "value": entry["value"],
                    "limit": limit,
                    "margin": entry["value"] - limit,
                    "nonconformance": entry["nonconformance"],
                }
            )
    return excursions


def inspection_result_findings(book):
    """Return findings where a failed inspection is not tied to a finding."""
    findings = []
    for entry in sorted(book, key=lambda item: item["sequence"]):
        if entry["entry_type"] != "inspection":
            continue
        if entry["result"] == "pass":
            continue
        if entry["nonconformance"] is None:
            findings.append(
                "entry %d records a %s inspection with no nonconformance reference"
                % (entry["sequence"], entry["result"])
            )
    return findings


def cumulative_exposure(book):
    """Return the recorded exposure hours per parameter and in total."""
    per_parameter = {}
    total = 0.0
    for entry in book:
        if entry["entry_type"] != "environmental":
            continue
        hours = entry["duration_hours"]
        per_parameter[entry["parameter"]] = per_parameter.get(entry["parameter"], 0.0) + hours
        total += hours
    return {"per_parameter": per_parameter, "total_hours": total}


def assess_logbook(entries, initial_configuration):
    """Grade a whole unit logbook against the Annex C DRD."""
    book = normalise_logbook(entries)
    findings = []
    findings.extend(sequence_findings(book))
    findings.extend(chronology_findings(book))
    trace, final_configuration = configuration_trace_findings(book, initial_configuration)
    findings.extend(trace)
    excursions = environmental_excursions(book)
    for excursion in excursions:
        if excursion["nonconformance"] is None:
            findings.append(
                "entry %d records %s past its limit with no nonconformance reference"
                % (excursion["sequence"], excursion["parameter"])
            )
    findings.extend(inspection_result_findings(book))
    exposure = cumulative_exposure(book)
    counts = {kind: 0 for kind in ENTRY_TYPES}
    for entry in book:
        counts[entry["entry_type"]] += 1
    return {
        "entry_count": len(book),
        "entry_counts": counts,
        "final_configuration": final_configuration,
        "excursions": excursions,
        "exposure": exposure,
        "findings": findings,
        "verdict": "logbook-conformant" if not findings else "logbook-nonconformant",
    }
