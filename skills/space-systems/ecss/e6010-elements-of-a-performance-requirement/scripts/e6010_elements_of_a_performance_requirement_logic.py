"""Completeness of a control performance requirement statement.

Anchor: ECSS-E-ST-60-10C clause 4.1.2 -- the elements of a performance
requirement. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that a performance requirement is stated with all
of its elements present. A number and a unit are not a requirement: the same
"pointing error below 0.1 degrees" is four different obligations depending on
whether it is a mean, a root-mean-square, a peak or a 99.7 percent value, over
what averaging window, in which frame, and under which operating condition.
The verification campaign that follows is built from those elements, so an
element left out is an argument deferred to the review that can least afford
it.

The elements this module insists on:

  parameter       -- the physical quantity being bounded;
  index           -- the statistical interpretation of the value;
  value + unit    -- the bound itself, with the unit it is expressed in;
  window_s        -- the interval the index is evaluated over;
  reference_frame -- the frame the parameter is expressed in;
  condition       -- the mission phase or operating case it applies under;
  confidence      -- the probability level, where the index is a statistical
                     one and only then.

The last of those is the coherence rule and the part a checklist misses: an
ensemble or percentile index without a probability level is incomplete, and an
absolute or peak index carrying one is incoherent, because a bound that is
never to be exceeded does not have a confidence attached to it.
"""

import math

__all__ = [
    "COMPLETE",
    "INCOMPLETE",
    "INCOHERENT",
    "REQUIRED_ELEMENTS",
    "STATISTICAL_INDICES",
    "DETERMINISTIC_INDICES",
    "KNOWN_INDICES",
    "validate_index",
    "validate_text_element",
    "validate_value",
    "validate_window",
    "validate_confidence",
    "missing_elements",
    "coherence_findings",
    "completeness_score",
    "normalize_requirement",
    "restate_requirement",
    "assess_requirement",
    "group_by_verdict",
]

COMPLETE = "complete"
INCOMPLETE = "incomplete"
INCOHERENT = "incoherent"

REQUIRED_ELEMENTS = (
    "parameter",
    "index",
    "value",
    "unit",
    "window_s",
    "reference_frame",
    "condition",
)

# Indices whose meaning depends on a stated probability level.
STATISTICAL_INDICES = ("mean", "rms", "standard-deviation", "percentile", "ensemble")

# Indices that bound every sample and therefore carry no probability level.
DETERMINISTIC_INDICES = ("absolute", "peak")

KNOWN_INDICES = tuple(sorted(STATISTICAL_INDICES + DETERMINISTIC_INDICES))

# Indices that are meaningless without an averaging interval longer than an
# instant; a peak or absolute bound can legitimately apply at every instant.
_AVERAGING_INDICES = ("mean", "rms", "standard-deviation")


def _is_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float))


def validate_index(value, name="index"):
    """Return a known statistical interpretation for the bound."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % name)
    index = value.strip().lower()
    if index not in KNOWN_INDICES:
        raise ValueError(
            "%s %r is not one of %s" % (name, value, ", ".join(KNOWN_INDICES))
        )
    return index


def validate_text_element(value, name):
    """Return a non-empty descriptive element."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % name)
    return value.strip()


def validate_value(value, name="value"):
    """Return a finite, non-negative bound.

    A performance bound is on the magnitude of an error, so a negative bound is
    a sign error in the requirement rather than a tighter requirement.
    """
    if not _is_number(value):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_window(value, name="window_s"):
    """Return a strictly positive evaluation interval in seconds."""
    if not _is_number(value):
        raise ValueError("%s must be a number" % name)
    window = float(value)
    if math.isnan(window) or math.isinf(window):
        raise ValueError("%s must be finite" % name)
    if window <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return window


def validate_confidence(value, name="confidence"):
    """Return a probability level strictly inside zero and one.

    Zero and one are both rejected: a level of zero bounds nothing and a level
    of one is an absolute bound wearing a statistical label, which is exactly
    the confusion the element list exists to prevent.
    """
    if not _is_number(value):
        raise ValueError("%s must be a number" % name)
    level = float(value)
    if math.isnan(level) or math.isinf(level):
        raise ValueError("%s must be finite" % name)
    if level <= 0.0 or level >= 1.0:
        raise ValueError(
            "%s must lie strictly between 0 and 1, got %r" % (name, value)
        )
    return level


def _present(record, key):
    if key not in record:
        return False
    value = record[key]
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def missing_elements(record):
    """Return the required elements this requirement does not state."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = [key for key in REQUIRED_ELEMENTS if not _present(record, key)]
    index = record.get("index")
    if isinstance(index, str) and index.strip().lower() in STATISTICAL_INDICES:
        if not _present(record, "confidence"):
            missing.append("confidence")
    return missing


def coherence_findings(record):
    """Return what is stated but does not hold together."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    findings = []
    index = record.get("index")
    normalized = None
    if isinstance(index, str) and index.strip():
        try:
            normalized = validate_index(index)
        except ValueError as exc:
            findings.append(str(exc))
    if normalized in DETERMINISTIC_INDICES and _present(record, "confidence"):
        findings.append(
            "index %r bounds every sample, so a confidence level of %r does not "
            "apply to it" % (normalized, record["confidence"])
        )
    if _present(record, "confidence"):
        try:
            validate_confidence(record["confidence"])
        except ValueError as exc:
            findings.append(str(exc))
    if _present(record, "value"):
        try:
            validate_value(record["value"])
        except ValueError as exc:
            findings.append(str(exc))
    if _present(record, "window_s"):
        try:
            window = validate_window(record["window_s"])
        except ValueError as exc:
            findings.append(str(exc))
        else:
            if normalized in _AVERAGING_INDICES and window <= 0.0:
                findings.append(
                    "index %r is an average and needs an interval to average "
                    "over" % normalized
                )
    return findings


def completeness_score(record):
    """Return the fraction of the required elements that are stated."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = missing_elements(record)
    index = record.get("index")
    total = len(REQUIRED_ELEMENTS)
    if isinstance(index, str) and index.strip().lower() in STATISTICAL_INDICES:
        total += 1
    return (total - len(missing)) / float(total)


def normalize_requirement(record):
    """Return a canonical form of a complete, coherent requirement.

    Raises on anything incomplete or incoherent, so a caller that gets a record
    back has one it can build a verification case from.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = missing_elements(record)
    if missing:
        raise ValueError("requirement is missing: %s" % ", ".join(missing))
    findings = coherence_findings(record)
    if findings:
        raise ValueError("requirement does not hold together: %s" % "; ".join(findings))
    normalized = {
        "parameter": validate_text_element(record["parameter"], "parameter"),
        "index": validate_index(record["index"]),
        "value": validate_value(record["value"]),
        "unit": validate_text_element(record["unit"], "unit"),
        "window_s": validate_window(record["window_s"]),
        "reference_frame": validate_text_element(
            record["reference_frame"], "reference_frame"
        ),
        "condition": validate_text_element(record["condition"], "condition"),
    }
    if normalized["index"] in STATISTICAL_INDICES:
        normalized["confidence"] = validate_confidence(record["confidence"])
    else:
        normalized["confidence"] = None
    return normalized


def restate_requirement(record):
    """Return a one-line restatement carrying every element."""
    normalized = normalize_requirement(record)
    line = "%s (%s) shall stay at or below %.6g %s over %.6g s in %s during %s" % (
        normalized["parameter"],
        normalized["index"],
        normalized["value"],
        normalized["unit"],
        normalized["window_s"],
        normalized["reference_frame"],
        normalized["condition"],
    )
    if normalized["confidence"] is not None:
        line += " at a confidence of %.6g" % normalized["confidence"]
    return line


def assess_requirement(record):
    """Grade one performance requirement statement against clause 4.1.2."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = missing_elements(record)
    findings = list(coherence_findings(record))
    score = completeness_score(record)
    if missing:
        findings.insert(
            0,
            "requirement does not state %s, so the verification case for it "
            "cannot be written" % ", ".join(missing),
        )
        verdict = INCOMPLETE
    elif findings:
        verdict = INCOHERENT
    else:
        verdict = COMPLETE
    restatement = None
    if verdict == COMPLETE:
        restatement = restate_requirement(record)
    return {
        "identifier": record.get("identifier"),
        "missing": missing,
        "completeness_score": score,
        "verdict": verdict,
        "findings": findings,
        "restatement": restatement,
    }


def group_by_verdict(records):
    """Return the identifiers of a set of requirements grouped by verdict."""
    if isinstance(records, (str, bytes, dict)) or not isinstance(
        records, (list, tuple)
    ):
        raise ValueError("records must be a list or tuple of mappings")
    grouped = {COMPLETE: [], INCOMPLETE: [], INCOHERENT: []}
    for index, record in enumerate(records):
        result = assess_requirement(record)
        identifier = result["identifier"]
        if identifier is None:
            identifier = "record[%d]" % index
        grouped[result["verdict"]].append(identifier)
    return grouped
