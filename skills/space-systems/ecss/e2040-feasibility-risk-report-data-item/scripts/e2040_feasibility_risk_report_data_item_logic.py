"""Required contents of the device feasibility and risk report.

Anchor: ECSS-E-ST-20-40C Annex F (feasibility and risk report data item --
the record produced during the definition phase covering the open feasibility
questions, the risks behind them and the residual position after mitigation).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the supplied section list against the required contents.
2. Validate the declared risk bands: worsening order, strictly increasing
   upper magnitudes, last band open-ended.
3. Score every risk: severity-by-likelihood magnitude before and after
   mitigation, both banded, with the reduction the mitigation buys.
4. Validate every feasibility question and the risks it links to.
5. Close a question only when its evidence exists and no linked residual sits
   above the accepted band.
6. Compute the criticality-weighted feasibility confidence and report it
   against the required level together with the findings.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "SCALE_MIN",
    "SCALE_MAX",
    "CONFIDENCE_TOLERANCE",
    "DEFAULT_BANDS",
    "missing_sections",
    "validate_scale_index",
    "validate_bands",
    "risk_magnitude",
    "band_of",
    "validate_risk",
    "grade_risk",
    "grade_risks",
    "validate_question",
    "validate_questions",
    "close_question",
    "weighted_feasibility_confidence",
    "residual_band_counts",
    "assess_feasibility_risk_report",
]

REQUIRED_SECTIONS = (
    "scope",
    "feasibility-questions",
    "risk-assessment-method",
    "risk-register",
    "mitigation-actions",
    "residual-risk-statement",
)

SCALE_MIN = 1
SCALE_MAX = 5

# Confidence is a ratio of sums; an exact equality can land a few ULPs on the
# wrong side of the required level.
CONFIDENCE_TOLERANCE = 1e-12

# Bands in worsening order; the last upper bound is None (open-ended).
DEFAULT_BANDS = (
    ("low", 4),
    ("medium", 9),
    ("high", 14),
    ("unacceptable", None),
)


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def missing_sections(sections):
    """Return the required sections absent from the supplied section list."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list or tuple of section names")
    present = set()
    for i, name in enumerate(sections):
        present.add(_identifier(name, "sections[%d]" % i).lower())
    return [name for name in REQUIRED_SECTIONS if name not in present]


def validate_scale_index(value, label):
    """Return a whole ordinal index inside the recognized scale."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole index, got %r" % (label, value))
    if value < SCALE_MIN or value > SCALE_MAX:
        raise ValueError(
            "%s must lie in [%d, %d], got %d" % (label, SCALE_MIN, SCALE_MAX, value)
        )
    return value


def validate_bands(bands):
    """Return the validated risk bands in worsening order."""
    if not isinstance(bands, (list, tuple)) or len(bands) < 2:
        raise ValueError("bands must be a sequence of at least two (name, upper) pairs")
    validated = []
    previous = None
    for i, entry in enumerate(bands):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("bands[%d] must be a (name, upper_magnitude) pair" % i)
        name = _identifier(entry[0], "bands[%d] name" % i)
        upper = entry[1]
        if i == len(bands) - 1:
            if upper is not None:
                raise ValueError("the worst band must be open-ended with an upper bound of None")
        else:
            if not isinstance(upper, int) or isinstance(upper, bool):
                raise ValueError("bands[%d] upper magnitude must be a whole number" % i)
            if upper < SCALE_MIN:
                raise ValueError("bands[%d] upper magnitude must be at least %d" % (i, SCALE_MIN))
            if previous is not None and upper <= previous:
                raise ValueError(
                    "band upper magnitudes must strictly increase (bands[%d] = %d)" % (i, upper)
                )
            previous = upper
        validated.append((name, upper))
    names = [name for name, _ in validated]
    if len(set(names)) != len(names):
        raise ValueError("band names must be distinct")
    return validated


def risk_magnitude(severity, likelihood):
    """Return the ordinal severity-by-likelihood magnitude of a risk."""
    s = validate_scale_index(severity, "severity")
    p = validate_scale_index(likelihood, "likelihood")
    return s * p


def band_of(magnitude, bands=DEFAULT_BANDS):
    """Return the band name a magnitude falls into."""
    validated = validate_bands(bands)
    if not isinstance(magnitude, int) or isinstance(magnitude, bool):
        raise ValueError("magnitude must be a whole number, got %r" % (magnitude,))
    if magnitude < SCALE_MIN:
        raise ValueError("magnitude must be at least %d, got %d" % (SCALE_MIN, magnitude))
    for name, upper in validated:
        if upper is None or magnitude <= upper:
            return name
    return validated[-1][0]


def validate_risk(risk):
    """Return a normalized risk record with residual indices defaulted."""
    if not isinstance(risk, dict):
        raise ValueError("risk must be a mapping")
    for key in ("id", "severity", "likelihood"):
        if key not in risk:
            raise ValueError("risk missing required key '%s'" % key)
    identifier = _identifier(risk["id"], "risk id")
    severity = validate_scale_index(risk["severity"], "severity of %s" % identifier)
    likelihood = validate_scale_index(risk["likelihood"], "likelihood of %s" % identifier)
    residual_severity = risk.get("residual_severity", severity)
    residual_likelihood = risk.get("residual_likelihood", likelihood)
    residual_severity = validate_scale_index(
        residual_severity, "residual_severity of %s" % identifier
    )
    residual_likelihood = validate_scale_index(
        residual_likelihood, "residual_likelihood of %s" % identifier
    )
    mitigation = risk.get("mitigation")
    if mitigation is not None:
        mitigation = _identifier(mitigation, "mitigation of %s" % identifier)
    return {
        "id": identifier,
        "severity": severity,
        "likelihood": likelihood,
        "residual_severity": residual_severity,
        "residual_likelihood": residual_likelihood,
        "mitigation": mitigation,
    }


def grade_risk(risk, bands=DEFAULT_BANDS):
    """Return the graded risk with both magnitudes, both bands and the reduction."""
    record = validate_risk(risk)
    initial = risk_magnitude(record["severity"], record["likelihood"])
    residual = risk_magnitude(record["residual_severity"], record["residual_likelihood"])
    record["initial_magnitude"] = initial
    record["residual_magnitude"] = residual
    record["initial_band"] = band_of(initial, bands)
    record["residual_band"] = band_of(residual, bands)
    record["reduction"] = initial - residual
    record["inconsistent"] = residual > initial
    record["mitigation_credited"] = record["mitigation"] is not None and residual < initial
    record["empty_mitigation"] = record["mitigation"] is not None and residual >= initial
    return record


def grade_risks(risks, bands=DEFAULT_BANDS):
    """Return the graded risk register, rejecting duplicate identifiers."""
    if not isinstance(risks, (list, tuple)):
        raise ValueError("risks must be a sequence")
    graded = []
    seen = set()
    for risk in risks:
        record = grade_risk(risk, bands)
        if record["id"] in seen:
            raise ValueError("duplicate risk identifier %r" % record["id"])
        seen.add(record["id"])
        graded.append(record)
    return graded


def validate_question(question, known_risk_ids):
    """Return a normalized feasibility question."""
    if not isinstance(question, dict):
        raise ValueError("feasibility question must be a mapping")
    for key in ("id", "criticality_weight", "evidence"):
        if key not in question:
            raise ValueError("feasibility question missing required key '%s'" % key)
    identifier = _identifier(question["id"], "question id")
    weight = _real(question["criticality_weight"], "criticality_weight of %s" % identifier)
    if weight <= 0.0:
        raise ValueError("criticality_weight of %s must be positive, got %g" % (identifier, weight))
    evidence = question["evidence"]
    if evidence is not None:
        evidence = _identifier(evidence, "evidence of %s" % identifier)
    links = question.get("risk_ids", [])
    if not isinstance(links, (list, tuple)):
        raise ValueError("risk_ids of %s must be a sequence" % identifier)
    resolved = []
    for i, ref in enumerate(links):
        ref_id = _identifier(ref, "%s risk_ids[%d]" % (identifier, i))
        if ref_id not in known_risk_ids:
            raise ValueError(
                "question %s links risk %r, which the register does not carry"
                % (identifier, ref_id)
            )
        if ref_id not in resolved:
            resolved.append(ref_id)
    return {
        "id": identifier,
        "criticality_weight": weight,
        "evidence": evidence,
        "risk_ids": resolved,
    }


def validate_questions(questions, known_risk_ids):
    """Return the normalized question set, rejecting duplicate identifiers."""
    if not isinstance(questions, (list, tuple)) or not questions:
        raise ValueError("questions must be a non-empty sequence")
    records = []
    seen = set()
    for question in questions:
        record = validate_question(question, known_risk_ids)
        if record["id"] in seen:
            raise ValueError("duplicate question identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def close_question(question, graded_by_id, accepted_bands):
    """Return the question with its closure decision and the reason it stays open."""
    if not isinstance(accepted_bands, (list, tuple)) or not accepted_bands:
        raise ValueError("accepted_bands must be a non-empty sequence of band names")
    accepted = set(_identifier(b, "accepted band") for b in accepted_bands)
    record = dict(question)
    blocking = [
        ref for ref in record["risk_ids"] if graded_by_id[ref]["residual_band"] not in accepted
    ]
    reasons = []
    if not record["evidence"]:
        reasons.append("no evidence reference")
    if blocking:
        reasons.append("residual above the accepted band on " + ", ".join(blocking))
    record["blocking_risk_ids"] = blocking
    record["closed"] = not reasons
    record["open_reasons"] = reasons
    return record


def weighted_feasibility_confidence(closed_questions):
    """Return the closed criticality weight over the total criticality weight."""
    if not isinstance(closed_questions, (list, tuple)) or not closed_questions:
        raise ValueError("closed_questions must be a non-empty sequence")
    total = 0.0
    closed = 0.0
    for record in closed_questions:
        total += record["criticality_weight"]
        if record["closed"]:
            closed += record["criticality_weight"]
    if total <= 0.0:
        raise ValueError("total criticality weight must be positive")
    return closed / total


def residual_band_counts(graded_risks, bands=DEFAULT_BANDS):
    """Return the number of risks sitting in each residual band."""
    validated = validate_bands(bands)
    counts = dict((name, 0) for name, _ in validated)
    for record in graded_risks:
        counts[record["residual_band"]] += 1
    return counts


def assess_feasibility_risk_report(report):
    """Run the full Annex F feasibility and risk report content assessment.

    report keys: sections, risks, questions, accepted_bands,
    required_confidence, optional bands.
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    for key in ("sections", "risks", "questions", "accepted_bands", "required_confidence"):
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    required = _real(report["required_confidence"], "required_confidence")
    if required < 0.0 or required > 1.0:
        raise ValueError("required_confidence must lie in [0, 1], got %g" % required)
    bands = validate_bands(report.get("bands", DEFAULT_BANDS))

    absent = missing_sections(report["sections"])
    graded = grade_risks(report["risks"], bands)
    by_id = dict((record["id"], record) for record in graded)
    questions = validate_questions(report["questions"], set(by_id))
    closed = [close_question(q, by_id, report["accepted_bands"]) for q in questions]
    confidence = weighted_feasibility_confidence(closed)
    counts = residual_band_counts(graded, bands)

    findings = []
    for name in absent:
        findings.append("required section %r is absent from the report" % name)
    for record in graded:
        if record["inconsistent"]:
            findings.append(
                "risk %s has a residual magnitude %d above its initial %d"
                % (record["id"], record["residual_magnitude"], record["initial_magnitude"])
            )
        elif record["empty_mitigation"]:
            findings.append(
                "risk %s declares a mitigation that moves neither index" % record["id"]
            )
    for record in closed:
        if not record["closed"]:
            findings.append(
                "feasibility question %s stays open: %s"
                % (record["id"], "; ".join(record["open_reasons"]))
            )
    confidence_met = confidence > required or math.isclose(
        confidence, required, rel_tol=0.0, abs_tol=CONFIDENCE_TOLERANCE
    )
    if not confidence_met:
        findings.append(
            "criticality-weighted feasibility confidence %.4f is below the required %.4f"
            % (confidence, required)
        )
    return {
        "missing_sections": absent,
        "risks": graded,
        "questions": closed,
        "residual_band_counts": counts,
        "feasibility_confidence": confidence,
        "required_confidence": required,
        "confidence_met": confidence_met,
        "open_questions": [r["id"] for r in closed if not r["closed"]],
        "compliant": not findings,
        "findings": findings,
    }
