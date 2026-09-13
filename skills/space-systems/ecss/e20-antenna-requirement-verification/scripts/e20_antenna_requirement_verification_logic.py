#!/usr/bin/env python3
"""Antenna requirement verification logic (ECSS-E-ST-20C clause 7.2.4).

Deterministic, offline, stdlib only. The standard is cited as the anchor
only; the procedure below is a paraphrase, not standard text.

Scope: assign and audit the verification method, the review-gate closure
and the verification record of each antenna engineering requirement, then
measure verification-coverage against the agreed threshold.
"""

import math
import re

# --- domain constants ------------------------------------------------------

VERIFICATION_METHODS = (
    "analysis",
    "review-of-design",
    "test",
    "inspection",
    "similarity",
)

_METHOD_ALIASES = {
    "a": "analysis",
    "analysis": "analysis",
    "r": "review-of-design",
    "rod": "review-of-design",
    "review of design": "review-of-design",
    "review-of-design": "review-of-design",
    "t": "test",
    "test": "test",
    "i": "inspection",
    "inspection": "inspection",
    "s": "similarity",
    "similarity": "similarity",
}

# Ordered project review gates used as closure milestones.
REVIEW_GATES = ("PDR", "CDR", "QR", "AR")

# Earliest gate at which each method can physically produce its evidence.
EARLIEST_EVIDENCE_GATE = {
    "review-of-design": "PDR",
    "analysis": "CDR",
    "similarity": "CDR",
    "test": "QR",
    "inspection": "QR",
}

# Antenna requirement categories: admissible methods + latest allowed gate.
REQUIREMENT_CATEGORIES = {
    "radiation-pattern": {"methods": ("test", "analysis"), "latest_gate": "QR"},
    "gain-and-polarization": {"methods": ("test", "analysis"), "latest_gate": "QR"},
    "guided-wave-interface": {"methods": ("test", "inspection"), "latest_gate": "QR"},
    "radiative-interface": {"methods": ("test", "analysis"), "latest_gate": "QR"},
    "deployment-kinematics": {"methods": ("test", "analysis"), "latest_gate": "QR"},
    "support-structure-scattering": {
        "methods": ("analysis", "test"),
        "latest_gate": "QR",
    },
    "mechanical-and-thermal-interface": {
        "methods": ("inspection", "review-of-design"),
        "latest_gate": "QR",
    },
    "materials-and-finish": {
        "methods": ("inspection", "review-of-design", "similarity"),
        "latest_gate": "QR",
    },
    "failure-rate-allocation": {
        "methods": ("analysis", "similarity"),
        "latest_gate": "CDR",
    },
}

REQUIREMENT_STATUSES = ("open", "closed", "waived")

# e.g. AVR-0142, ANT-17, TRP-004512
RECORD_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}-[0-9]{2,6}$")

# Absorbs floating-point representation error on an exactly-met threshold.
COVERAGE_TOLERANCE = 1e-9


# --- normalization ---------------------------------------------------------


def normalize_method(method):
    """Return the canonical verification method token.

    Raises ValueError for a non-string or an unrecognized method.
    """
    if not isinstance(method, str):
        raise ValueError("verification method must be a string, got %r" % (method,))
    key = method.strip().lower()
    if not key:
        raise ValueError("verification method must not be empty")
    canonical = _METHOD_ALIASES.get(key)
    if canonical is None:
        raise ValueError(
            "unknown verification method %r; expected one of %s"
            % (method, ", ".join(VERIFICATION_METHODS))
        )
    return canonical


def normalize_gate(gate):
    """Return the canonical review-gate token (PDR/CDR/QR/AR)."""
    if not isinstance(gate, str):
        raise ValueError("review gate must be a string, got %r" % (gate,))
    key = gate.strip().upper()
    if key not in REVIEW_GATES:
        raise ValueError(
            "unknown review gate %r; expected one of %s"
            % (gate, ", ".join(REVIEW_GATES))
        )
    return key


def gate_index(gate):
    """Return the ordinal position of a review gate (PDR=0 ... AR=3)."""
    return REVIEW_GATES.index(normalize_gate(gate))


def normalize_category(category):
    """Return the canonical antenna requirement category token."""
    if not isinstance(category, str):
        raise ValueError("antenna category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in REQUIREMENT_CATEGORIES:
        raise ValueError(
            "unknown antenna requirement category %r; expected one of %s"
            % (category, ", ".join(sorted(REQUIREMENT_CATEGORIES)))
        )
    return key


def normalize_status(status):
    """Return the canonical requirement status token."""
    if not isinstance(status, str):
        raise ValueError("requirement status must be a string, got %r" % (status,))
    key = status.strip().lower()
    if key not in REQUIREMENT_STATUSES:
        raise ValueError(
            "unknown requirement status %r; expected one of %s"
            % (status, ", ".join(REQUIREMENT_STATUSES))
        )
    return key


# --- per-rule checks -------------------------------------------------------


def admissible_methods(category):
    """Return the frozenset of methods that can evidence this category."""
    return frozenset(REQUIREMENT_CATEGORIES[normalize_category(category)]["methods"])


def latest_allowed_gate(category):
    """Return the latest review gate this antenna category may close at."""
    return REQUIREMENT_CATEGORIES[normalize_category(category)]["latest_gate"]


def earliest_feasible_gate(method):
    """Return the earliest review gate at which a method can close."""
    return EARLIEST_EVIDENCE_GATE[normalize_method(method)]


def is_well_formed_record(record_id):
    """True when the verification record identifier matches the house form."""
    return isinstance(record_id, str) and RECORD_ID_RE.match(record_id.strip()) is not None


def evaluate_requirement(requirement, at_gate=None):
    """Evaluate one antenna requirement and return its verdict dict.

    Raises ValueError when the requirement itself cannot be interpreted
    (missing identifier, unknown category/method/gate/status).
    """
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    req_id = requirement.get("id")
    if not isinstance(req_id, str) or not req_id.strip():
        raise ValueError("requirement is missing a non-empty 'id'")
    req_id = req_id.strip()

    category = normalize_category(requirement.get("category"))
    method = normalize_method(requirement.get("method"))
    planned_gate = normalize_gate(requirement.get("planned_gate"))
    status = normalize_status(requirement.get("status"))

    findings = []

    if method not in admissible_methods(category):
        findings.append(
            "method-not-admissible: %s cannot evidence a %s requirement"
            % (method, category)
        )

    earliest = earliest_feasible_gate(method)
    if gate_index(planned_gate) < gate_index(earliest):
        findings.append(
            "gate-earlier-than-method-can-close: %s closes no earlier than %s"
            % (method, earliest)
        )

    latest = latest_allowed_gate(category)
    if gate_index(planned_gate) > gate_index(latest):
        findings.append(
            "gate-later-than-category-allows: %s must close by %s" % (category, latest)
        )

    record_id = requirement.get("record")
    if status == "closed":
        if record_id is None or (isinstance(record_id, str) and not record_id.strip()):
            findings.append("missing-verification-record: closure claimed with no record")
        elif not is_well_formed_record(record_id):
            findings.append("malformed-verification-record: %r" % (record_id,))
    elif status == "waived":
        waiver = requirement.get("waiver_reference")
        rationale = requirement.get("rationale")
        if not isinstance(waiver, str) or not waiver.strip():
            findings.append("waiver-without-reference: deviation is untraced")
        if not isinstance(rationale, str) or not rationale.strip():
            findings.append("waiver-without-rationale: deviation is unjustified")
    elif at_gate is not None:
        reached = normalize_gate(at_gate)
        if gate_index(planned_gate) <= gate_index(reached):
            findings.append(
                "open-past-planned-gate: planned %s, assessment at %s"
                % (planned_gate, reached)
            )

    return {
        "id": req_id,
        "category": category,
        "method": method,
        "planned_gate": planned_gate,
        "status": status,
        "findings": findings,
        "compliant": not findings,
    }


# --- aggregation -----------------------------------------------------------


def verification_coverage(results):
    """Fraction of requirements that are closed or formally waived."""
    if not results:
        raise ValueError("verification coverage needs at least one requirement result")
    settled = sum(1 for r in results if r["status"] in ("closed", "waived"))
    return settled / len(results)


def meets_coverage_threshold(coverage, threshold):
    """Compare coverage with the agreed threshold, absorbing float error.

    The engineering limit is never widened: only representation error at
    an exactly-met threshold is absorbed.
    """
    if not isinstance(coverage, (int, float)) or isinstance(coverage, bool):
        raise ValueError("coverage must be a real number, got %r" % (coverage,))
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("threshold must be a real number, got %r" % (threshold,))
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must lie in [0, 1], got %r" % (threshold,))
    if coverage >= threshold:
        return True
    return math.isclose(coverage, threshold, rel_tol=COVERAGE_TOLERANCE, abs_tol=1e-12)


def summarize_findings(results):
    """Count findings by their leading code across all requirement results."""
    counts = {}
    for result in results:
        for finding in result["findings"]:
            code = finding.split(":", 1)[0]
            counts[code] = counts.get(code, 0) + 1
    return counts


def assess_antenna_requirement_verification(
    requirements, coverage_threshold=1.0, at_gate=None
):
    """Assess a whole antenna requirement set against clause 7.2.4.

    Returns a report dict with per-requirement results, the finding
    counts, the verification-coverage fraction and the overall verdict.
    """
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("requirements must be a list, got %r" % (requirements,))
    if not requirements:
        raise ValueError("requirement list must not be empty")

    seen = set()
    results = []
    for requirement in requirements:
        result = evaluate_requirement(requirement, at_gate=at_gate)
        if result["id"] in seen:
            raise ValueError("duplicate requirement identifier %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)

    coverage = verification_coverage(results)
    coverage_met = meets_coverage_threshold(coverage, coverage_threshold)
    counts = summarize_findings(results)
    return {
        "results": results,
        "finding_counts": counts,
        "finding_total": sum(counts.values()),
        "coverage": coverage,
        "coverage_threshold": float(coverage_threshold),
        "coverage_met": coverage_met,
        "open_ids": [r["id"] for r in results if r["status"] == "open"],
        "compliant": coverage_met and all(r["compliant"] for r in results),
    }
