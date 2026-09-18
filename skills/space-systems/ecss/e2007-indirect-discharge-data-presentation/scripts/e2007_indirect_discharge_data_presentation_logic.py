"""Presentation of indirect-discharge results: compliance table plus observed levels.

Anchor: ECSS-E-ST-20-07C clause 5.4.12.5 (indirect-discharge results are
presented as tables of compliance carrying the induced current levels observed
during the discharges). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the presentation record: every table row names the discharge event,
   the application point, the polarity, how many discharges it stands for, the
   monitored circuit, the induced current observed on it, the susceptibility
   limit that current is graded against, and the compliance verdict entered.
2. Grade each row on its own numbers: the reported margin between the limit and
   the observed induced current, and whether the entered verdict agrees with
   that margin.
3. Grade the table as a whole for coverage: every declared application point
   present, every declared monitored circuit present, both polarities applied at
   each point, and the required number of discharges reached.
4. Separate hard findings (a level cell left empty, a verdict contradicting its
   own numbers, a coverage gap) from limitations (a narrow margin, a level so
   far below the limit that the monitor itself is in question).
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_DB",
    "NARROW_MARGIN_DB",
    "IMPLAUSIBLY_QUIET_DB",
    "REQUIRED_ROW_KEYS",
    "normalize_verdict",
    "normalize_polarity",
    "validate_row",
    "induced_current_margin_db",
    "grade_row",
    "grade_rows",
    "coverage_gaps",
    "peak_levels_by_circuit",
    "assess_presentation",
]

# A margin is a difference of logarithms: a physically exact equality between
# the observed level and the limit can land a few ULPs on either side. Absorb
# the representation error here rather than by moving the engineering limit.
MARGIN_TOLERANCE_DB = 1e-9

# A row that clears its limit by less than this is reportable as a limitation:
# it passes, but it has no room for unit-to-unit spread.
NARROW_MARGIN_DB = 6.0

# A monitored circuit that reports a level this far under its limit is more
# often an unconnected or wrongly ranged monitor than a quiet circuit.
IMPLAUSIBLY_QUIET_DB = 60.0

REQUIRED_ROW_KEYS = (
    "event_id",
    "application_point",
    "polarity",
    "discharge_count",
    "monitored_circuit",
    "susceptibility_limit_a",
    "verdict",
)

_COMPLIANT_TOKENS = ("compliant", "pass", "passed", "conform", "conforming")
_NON_COMPLIANT_TOKENS = ("non-compliant", "noncompliant", "fail", "failed", "not-compliant")

_POSITIVE_TOKENS = ("positive", "pos", "+", "plus")
_NEGATIVE_TOKENS = ("negative", "neg", "-", "minus")


def _require_text(label, value):
    """Return a stripped non-empty string for a table cell that must name something."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive(label, value):
    """Return a positive finite float for a measured or limiting quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def normalize_verdict(token):
    """Return 'compliant' or 'non-compliant' for a verdict cell."""
    text = _require_text("verdict", token).lower().replace("_", "-").replace(" ", "-")
    if text in _COMPLIANT_TOKENS:
        return "compliant"
    if text in _NON_COMPLIANT_TOKENS:
        return "non-compliant"
    raise ValueError("unrecognized verdict token %r" % (token,))


def normalize_polarity(token):
    """Return 'positive' or 'negative' for a discharge-polarity cell."""
    text = _require_text("polarity", token).lower().replace("_", "-").replace(" ", "-")
    if text in _POSITIVE_TOKENS:
        return "positive"
    if text in _NEGATIVE_TOKENS:
        return "negative"
    raise ValueError("unrecognized polarity token %r" % (token,))


def validate_row(row):
    """Return a normalized copy of one compliance-table row.

    An absent or None induced current is preserved as None: an unreported level
    is the defect this clause exists to catch, so it is carried through to the
    grading rather than rejected as malformed input.
    """
    if not isinstance(row, dict):
        raise ValueError("each table row must be a mapping, got %r" % (row,))
    for key in REQUIRED_ROW_KEYS:
        if key not in row:
            raise ValueError("table row missing required cell '%s'" % key)
    count = row["discharge_count"]
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("discharge_count must be an integer, got %r" % (count,))
    if count < 1:
        raise ValueError("discharge_count must be at least 1, got %r" % (count,))
    observed = row.get("induced_current_a")
    if observed is not None:
        observed = _require_positive("induced_current_a", observed)
    return {
        "event_id": _require_text("event_id", row["event_id"]),
        "application_point": _require_text("application_point", row["application_point"]),
        "polarity": normalize_polarity(row["polarity"]),
        "discharge_count": count,
        "monitored_circuit": _require_text("monitored_circuit", row["monitored_circuit"]),
        "induced_current_a": observed,
        "susceptibility_limit_a": _require_positive(
            "susceptibility_limit_a", row["susceptibility_limit_a"]
        ),
        "verdict": normalize_verdict(row["verdict"]),
    }


def induced_current_margin_db(limit_a, observed_a):
    """Return the margin in dB by which an observed induced current clears its limit."""
    limit = _require_positive("susceptibility_limit_a", limit_a)
    observed = _require_positive("induced_current_a", observed_a)
    return 20.0 * math.log10(limit / observed)


def grade_row(row):
    """Return the graded record for one validated compliance-table row."""
    record = validate_row(row)
    findings = []
    limitations = []
    observed = record["induced_current_a"]
    if observed is None:
        record["margin_db"] = None
        record["margin_compliant"] = None
        findings.append(
            "event %s reports a verdict with no induced current level; the table "
            "carries compliance without the level it was decided on" % record["event_id"]
        )
        record["findings"] = findings
        record["limitations"] = limitations
        return record
    margin = induced_current_margin_db(record["susceptibility_limit_a"], observed)
    at_limit = math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB)
    margin_compliant = at_limit or margin > 0.0
    record["margin_db"] = margin
    record["margin_compliant"] = margin_compliant
    if margin_compliant != (record["verdict"] == "compliant"):
        findings.append(
            "event %s is entered as %s but its induced current of %.4g A against a "
            "%.4g A limit gives %.3f dB" % (
                record["event_id"],
                record["verdict"],
                observed,
                record["susceptibility_limit_a"],
                margin,
            )
        )
    elif margin_compliant and margin < NARROW_MARGIN_DB and not at_limit:
        limitations.append(
            "event %s clears its limit by %.3f dB only" % (record["event_id"], margin)
        )
    if margin > IMPLAUSIBLY_QUIET_DB:
        limitations.append(
            "event %s reports %.3f dB below its limit; confirm the monitor on %s was "
            "connected and in range" % (record["event_id"], margin, record["monitored_circuit"])
        )
    record["findings"] = findings
    record["limitations"] = limitations
    return record


def grade_rows(rows):
    """Return the graded records for a whole compliance table."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("rows must be a non-empty sequence of table rows")
    graded = [grade_row(row) for row in rows]
    seen = set()
    for record in graded:
        key = record["event_id"]
        if key in seen:
            raise ValueError("duplicate event_id %r in the compliance table" % key)
        seen.add(key)
    return graded


def coverage_gaps(graded, declared_points, declared_circuits,
                  required_polarities=("positive", "negative"),
                  required_discharges_per_point=1):
    """Return the coverage findings of a graded compliance table."""
    if not isinstance(declared_points, (list, tuple)) or not declared_points:
        raise ValueError("declared_points must be a non-empty sequence")
    if not isinstance(declared_circuits, (list, tuple)) or not declared_circuits:
        raise ValueError("declared_circuits must be a non-empty sequence")
    if not isinstance(required_discharges_per_point, int) or isinstance(
        required_discharges_per_point, bool
    ):
        raise ValueError("required_discharges_per_point must be an integer")
    if required_discharges_per_point < 1:
        raise ValueError("required_discharges_per_point must be at least 1")
    wanted_polarities = [normalize_polarity(token) for token in required_polarities]
    if not wanted_polarities:
        raise ValueError("required_polarities must name at least one polarity")
    gaps = []
    tabled_points = set(record["application_point"] for record in graded)
    tabled_circuits = set(record["monitored_circuit"] for record in graded)
    for point in declared_points:
        name = _require_text("declared application point", point)
        if name not in tabled_points:
            gaps.append("declared application point %s appears in no table row" % name)
            continue
        for polarity in wanted_polarities:
            applied = sum(
                record["discharge_count"]
                for record in graded
                if record["application_point"] == name and record["polarity"] == polarity
            )
            if applied == 0:
                gaps.append(
                    "application point %s has no %s-polarity discharge row" % (name, polarity)
                )
            elif applied < required_discharges_per_point:
                gaps.append(
                    "application point %s carries %d %s-polarity discharges against %d required"
                    % (name, applied, polarity, required_discharges_per_point)
                )
    for circuit in declared_circuits:
        name = _require_text("declared monitored circuit", circuit)
        if name not in tabled_circuits:
            gaps.append("declared monitored circuit %s appears in no table row" % name)
    return gaps


def peak_levels_by_circuit(graded):
    """Return the highest reported induced current per monitored circuit, in amperes."""
    peaks = {}
    for record in graded:
        observed = record["induced_current_a"]
        if observed is None:
            continue
        circuit = record["monitored_circuit"]
        if circuit not in peaks or observed > peaks[circuit]:
            peaks[circuit] = observed
    return peaks


def assess_presentation(record):
    """Run the full clause 5.4.12.5 presentation assessment.

    record keys: rows, declared_application_points, declared_monitored_circuits,
    optional required_polarities and required_discharges_per_point.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("rows", "declared_application_points", "declared_monitored_circuits"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    graded = grade_rows(record["rows"])
    findings = []
    limitations = []
    for row in graded:
        findings.extend(row["findings"])
        limitations.extend(row["limitations"])
    findings.extend(
        coverage_gaps(
            graded,
            record["declared_application_points"],
            record["declared_monitored_circuits"],
            record.get("required_polarities", ("positive", "negative")),
            record.get("required_discharges_per_point", 1),
        )
    )
    levels_reported = sum(1 for row in graded if row["induced_current_a"] is not None)
    return {
        "rows": graded,
        "row_count": len(graded),
        "levels_reported": levels_reported,
        "peak_levels_by_circuit": peak_levels_by_circuit(graded),
        "findings": findings,
        "limitations": limitations,
        "presentable": not findings,
    }
