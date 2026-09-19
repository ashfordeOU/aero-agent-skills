#!/usr/bin/env python3
"""Customer-led phase review conduct (ECSS-E-ST-20-40C clause 5.1.4).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A phase review closes one development phase, and it is led by the customer
rather than by the supplier that produced the outputs. Three things decide
the verdict, and they are independent of each other:

* the review has to be the one that closes the phase being reviewed. The
  entry criteria and the mandatory output list follow the phase, so a
  review identifier borrowed from a neighbouring phase reviews the wrong
  list;
* each mandatory output carries two separate properties -- whether it was
  delivered and whether it is mature enough to be read. A draft handed
  over on the due date is delivered and not reviewable, so readiness is
  counted on both;
* each observation carries a severity and a disposition. Severity says how
  much the finding matters, disposition says what the board did with it,
  and an open major observation blocks the phase however the rest of the
  review reads.

Readiness is a fraction of the mandatory output set. A fraction landing
exactly on its threshold has met it, so the comparison absorbs the
representation error of a division instead of failing on it.
"""

import math

# Reviews, in the order the phases they close run.
PHASE_REVIEWS = (
    "prr",
    "pdr",
    "cdr",
    "qr",
    "ar",
    "orr",
)

# Development phases, in order.
DEVELOPMENT_PHASES = (
    "requirements",
    "definition",
    "detailed-design",
    "qualification",
    "acceptance",
    "operations-readiness",
)

# The review that closes each phase.
REVIEW_FOR_PHASE = {
    "requirements": "prr",
    "definition": "pdr",
    "detailed-design": "cdr",
    "qualification": "qr",
    "acceptance": "ar",
    "operations-readiness": "orr",
}

_REVIEW_ALIASES = {
    "prr": "prr",
    "preliminary requirements review": "prr",
    "pdr": "pdr",
    "preliminary design review": "pdr",
    "cdr": "cdr",
    "critical design review": "cdr",
    "qr": "qr",
    "qualification review": "qr",
    "ar": "ar",
    "acceptance review": "ar",
    "orr": "orr",
    "operational readiness review": "orr",
    "operations readiness review": "orr",
}

_PHASE_ALIASES = {
    "requirements": "requirements",
    "requirement definition": "requirements",
    "definition": "definition",
    "preliminary design": "definition",
    "detailed-design": "detailed-design",
    "detailed design": "detailed-design",
    "design": "detailed-design",
    "qualification": "qualification",
    "acceptance": "acceptance",
    "operations-readiness": "operations-readiness",
    "operations readiness": "operations-readiness",
    "operational readiness": "operations-readiness",
}

# Observation severities, most serious first.
SEVERITIES = ("major", "minor", "comment")
_SEVERITY_ALIASES = {
    "major": "major",
    "critical": "major",
    "category-1": "major",
    "minor": "minor",
    "category-2": "minor",
    "comment": "comment",
    "remark": "comment",
    "editorial": "comment",
}

# What the board did with an observation.
DISPOSITIONS = ("closed", "action-raised", "open", "rejected")
_DISPOSITION_ALIASES = {
    "closed": "closed",
    "accepted-closed": "closed",
    "action-raised": "action-raised",
    "action": "action-raised",
    "accepted with action": "action-raised",
    "open": "open",
    "outstanding": "open",
    "rejected": "rejected",
    "not accepted": "rejected",
}

# Sides a board chair can sit on.
BOARD_SIDES = ("customer", "supplier", "third-party")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_REVIEW_REQUIRED_KEYS = ("review", "phase", "board", "outputs")
_REVIEW_OPTIONAL_KEYS = ("observations", "readiness_threshold")
_BOARD_KEYS = ("chair", "chair_side", "participants")
_OUTPUT_KEYS = ("id", "title", "mandatory", "delivered", "mature")
_OBSERVATION_KEYS = ("id", "severity", "disposition", "rationale", "subject")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_readiness_threshold(achieved, threshold):
    """True when readiness reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_review(value):
    """Fold a review spelling onto one of the recognised review names."""
    key = _key(_text("review", value))
    if key in _REVIEW_ALIASES:
        return _REVIEW_ALIASES[key]
    raise ValueError(
        "unknown phase review %r; use one of %s" % (value, ", ".join(PHASE_REVIEWS))
    )


def normalize_phase(value):
    """Fold a phase spelling onto one of the recognised development phases."""
    key = _key(_text("phase", value))
    key = key.replace(" ", "-") if key.replace(" ", "-") in _PHASE_ALIASES else key
    if key in _PHASE_ALIASES:
        return _PHASE_ALIASES[key]
    raise ValueError(
        "unknown development phase %r; use one of %s"
        % (value, ", ".join(DEVELOPMENT_PHASES))
    )


def normalize_severity(value):
    """Fold an observation severity onto major, minor or comment."""
    key = _key(_text("severity", value)).replace(" ", "-")
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    raise ValueError(
        "unknown observation severity %r; use one of %s"
        % (value, ", ".join(SEVERITIES))
    )


def normalize_disposition(value):
    """Fold a board disposition onto one of the recognised dispositions."""
    key = _key(_text("disposition", value))
    if key in _DISPOSITION_ALIASES:
        return _DISPOSITION_ALIASES[key]
    hyphen = key.replace(" ", "-")
    if hyphen in _DISPOSITION_ALIASES:
        return _DISPOSITION_ALIASES[hyphen]
    raise ValueError(
        "unknown disposition %r; use one of %s" % (value, ", ".join(DISPOSITIONS))
    )


def review_closing_phase(phase):
    """The review that closes this development phase."""
    return REVIEW_FOR_PHASE[normalize_phase(phase)]


def validate_board(board):
    """Check the review board and return the chair and the chair side."""
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping of chair, chair_side, participants")
    unknown = sorted(set(board) - set(_BOARD_KEYS))
    if unknown:
        raise ValueError("board has unknown keys: %s" % ", ".join(unknown))
    chair = _text("board.chair", board.get("chair", ""))
    side = _key(_text("board.chair_side", board.get("chair_side", ""))).replace(
        " ", "-"
    )
    if side not in BOARD_SIDES:
        raise ValueError(
            "board.chair_side must be one of %s, got %r"
            % (", ".join(BOARD_SIDES), board.get("chair_side"))
        )
    participants = board.get("participants", [])
    if not isinstance(participants, (list, tuple)):
        raise ValueError("board.participants must be a list")
    names = []
    for index, participant in enumerate(participants):
        names.append(_text("board.participants[%d]" % index, participant))
    return {"chair": chair, "chair_side": side, "participants": names}


def validate_outputs(entries):
    """Check the phase output list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("outputs must be a list of phase output items")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("outputs[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_OUTPUT_KEYS))
        if unknown:
            raise ValueError(
                "outputs[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in entry:
            raise ValueError("outputs[%d] missing key: id" % index)
        item_id = _text("outputs[%d].id" % index, entry["id"])
        if item_id in seen:
            raise ValueError("duplicate output item id %r" % item_id)
        seen.add(item_id)
        resolved.append(
            {
                "id": item_id,
                "title": _text(
                    "outputs[%d].title" % index,
                    entry.get("title", ""),
                    allow_empty=True,
                ),
                "mandatory": _flag(
                    "outputs[%d].mandatory" % index, entry.get("mandatory", True)
                ),
                "delivered": _flag(
                    "outputs[%d].delivered" % index, entry.get("delivered", False)
                ),
                "mature": _flag(
                    "outputs[%d].mature" % index, entry.get("mature", False)
                ),
            }
        )
    return resolved


def validate_observations(entries):
    """Check the observation list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("observations must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("observations[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_OBSERVATION_KEYS))
        if unknown:
            raise ValueError(
                "observations[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "severity", "disposition"):
            if key not in entry:
                raise ValueError("observations[%d] missing key: %s" % (index, key))
        obs_id = _text("observations[%d].id" % index, entry["id"])
        if obs_id in seen:
            raise ValueError("duplicate observation id %r" % obs_id)
        seen.add(obs_id)
        resolved.append(
            {
                "id": obs_id,
                "severity": normalize_severity(entry["severity"]),
                "disposition": normalize_disposition(entry["disposition"]),
                "rationale": _text(
                    "observations[%d].rationale" % index,
                    entry.get("rationale", ""),
                    allow_empty=True,
                ),
                "subject": _text(
                    "observations[%d].subject" % index,
                    entry.get("subject", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def mandatory_outputs(outputs):
    """The output items the phase cannot close without."""
    return [item for item in outputs if item["mandatory"]]


def output_readiness(outputs):
    """Fraction of mandatory outputs both delivered and mature."""
    mandatory = mandatory_outputs(outputs)
    if not mandatory:
        raise ValueError("output_readiness needs at least one mandatory output")
    ready = sum(1 for item in mandatory if item["delivered"] and item["mature"])
    return ready / len(mandatory)


def outstanding_outputs(outputs):
    """Mandatory output ids that are undelivered or not yet mature."""
    return sorted(
        item["id"]
        for item in mandatory_outputs(outputs)
        if not (item["delivered"] and item["mature"])
    )


def open_observations(observations, severity=None):
    """Observation ids still open, optionally restricted to one severity."""
    wanted = None if severity is None else normalize_severity(severity)
    return sorted(
        obs["id"]
        for obs in observations
        if obs["disposition"] in ("open", "action-raised")
        and (wanted is None or obs["severity"] == wanted)
    )


def observation_closure(observations):
    """Fraction of observations the board actually closed or rejected."""
    if not observations:
        raise ValueError("observation_closure needs at least one observation")
    settled = sum(
        1 for obs in observations if obs["disposition"] in ("closed", "rejected")
    )
    return settled / len(observations)


def conduct_phase_review(review):
    """Full clause 5.1.4 assessment of one customer-led phase review.

    Returns the resolved review, the readiness figures, the findings and
    the closure verdict.
    """
    if not isinstance(review, dict):
        raise ValueError(
            "review must be a mapping of review, phase, board and outputs"
        )
    known = set(_REVIEW_REQUIRED_KEYS) | set(_REVIEW_OPTIONAL_KEYS)
    unknown = sorted(set(review) - known)
    if unknown:
        raise ValueError("unknown review keys: %s" % ", ".join(unknown))
    missing = [key for key in _REVIEW_REQUIRED_KEYS if key not in review]
    if missing:
        raise ValueError("review missing required keys: %s" % ", ".join(missing))

    name = normalize_review(review["review"])
    phase = normalize_phase(review["phase"])
    board = validate_board(review["board"])
    outputs = validate_outputs(review["outputs"])
    if not outputs:
        raise ValueError("review must carry at least one phase output")
    if not mandatory_outputs(outputs):
        raise ValueError("review must carry at least one mandatory phase output")
    observations = validate_observations(review.get("observations", []) or [])
    threshold = _fraction(
        "readiness_threshold", review.get("readiness_threshold", 1.0)
    )

    findings = []
    expected = review_closing_phase(phase)
    if name != expected:
        findings.append(
            {
                "code": "review-does-not-close-phase",
                "detail": "the %s phase is closed by the %s, not by the %s"
                % (phase, expected, name),
            }
        )
    if board["chair_side"] != "customer":
        findings.append(
            {
                "code": "review-not-customer-chaired",
                "detail": "the board is chaired from the %s side, so the review is "
                "not customer-led" % board["chair_side"],
            }
        )

    for item in mandatory_outputs(outputs):
        if not item["delivered"]:
            findings.append(
                {
                    "code": "mandatory-output-undelivered",
                    "output": item["id"],
                    "detail": "mandatory output %s was not delivered for the review"
                    % item["id"],
                }
            )
        elif not item["mature"]:
            findings.append(
                {
                    "code": "mandatory-output-immature",
                    "output": item["id"],
                    "detail": "mandatory output %s was delivered but is not mature "
                    "enough to be reviewed" % item["id"],
                }
            )

    for obs in observations:
        if obs["disposition"] == "rejected" and not obs["rationale"]:
            findings.append(
                {
                    "code": "disposition-without-rationale",
                    "observation": obs["id"],
                    "detail": "observation %s was rejected with no rationale "
                    "recorded" % obs["id"],
                }
            )
        if obs["disposition"] in ("open", "action-raised") and obs["severity"] == (
            "major"
        ):
            findings.append(
                {
                    "code": "major-observation-open",
                    "observation": obs["id"],
                    "detail": "major observation %s is still %s"
                    % (obs["id"], obs["disposition"]),
                }
            )

    readiness = output_readiness(outputs)
    if not meets_readiness_threshold(readiness, threshold):
        findings.append(
            {
                "code": "readiness-below-threshold",
                "achieved": readiness,
                "threshold": threshold,
                "detail": "mandatory output readiness reaches %.1f %% against a "
                "%.1f %% threshold" % (100.0 * readiness, 100.0 * threshold),
            }
        )

    blocking = {
        "mandatory-output-undelivered",
        "mandatory-output-immature",
        "major-observation-open",
        "review-does-not-close-phase",
        "review-not-customer-chaired",
        "readiness-below-threshold",
    }
    codes = {finding["code"] for finding in findings}
    if codes & blocking:
        verdict = "review-repeated"
    elif findings or open_observations(observations):
        verdict = "closed-with-actions"
    else:
        verdict = "closed"

    return {
        "review": name,
        "phase": phase,
        "chair_side": board["chair_side"],
        "mandatory_count": len(mandatory_outputs(outputs)),
        "readiness": readiness,
        "readiness_threshold": threshold,
        "outstanding_outputs": outstanding_outputs(outputs),
        "open_observations": open_observations(observations),
        "open_major_observations": open_observations(observations, "major"),
        "findings": findings,
        "verdict": verdict,
        "acceptable": verdict == "closed",
    }
