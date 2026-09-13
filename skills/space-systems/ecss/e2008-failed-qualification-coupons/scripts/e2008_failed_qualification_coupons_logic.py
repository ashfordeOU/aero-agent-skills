"""Treatment of a qualification coupon that showed one or more failure modes.

Anchor: ECSS-E-ST-20-08C clause 5.6.2 (what happens to a qualification coupon
once it exhibits any of the failure modes the standard lists). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the failure record of the coupon: at least one recognized failure
   mode, each carrying the cause category the investigation attributed to it.
2. Withdraw the coupon as qualification evidence. This happens on the strength
   of the failure alone and does not wait on the investigation, because a
   coupon that failed cannot also stand as proof that the design passes.
3. Hold the disposition open while any mode is still without an attributed
   cause. An unattributed failure has no retest scope, and guessing one is how
   a systematic cause is repaired as if it were a one-off.
4. Map every attributed cause onto the retest scope it forces - the test
   installation, the single coupon, the subgroup, or the whole qualification -
   and let the widest scope among the modes govern.
5. Keep the retest inadmissible until the corrective action for the governing
   cause is both implemented and independently verified.
"""

__all__ = [
    "CAUSE_CATEGORIES",
    "CAUSE_TO_SCOPE",
    "FAILURE_MODES",
    "RETEST_SCOPES",
    "UNDETERMINED_CAUSE",
    "assess_failed_coupon",
    "governing_failure",
    "normalize_cause",
    "normalize_mode",
    "qualification_status_for_scope",
    "retest_scope_for_cause",
    "scope_rank",
    "validate_corrective_action",
    "validate_failure_record",
    "widest_scope",
]

# The failure modes a qualification coupon can present. Any one of them puts
# the coupon into this clause.
FAILURE_MODES = (
    "open-circuit",
    "short-circuit",
    "interconnect-fracture",
    "cell-cracking",
    "coverglass-loss",
    "adhesive-debonding",
    "excessive-power-loss",
    "insulation-breakdown",
)

# What the investigation attributed the failure to. The cause is what decides
# how far the retest reaches, so an unattributed cause decides nothing.
UNDETERMINED_CAUSE = "undetermined"
CAUSE_CATEGORIES = (
    UNDETERMINED_CAUSE,
    "test-installation-artefact",
    "isolated-build-escape",
    "systematic-process-cause",
    "design-inherent-cause",
)

# Retest scopes, ordered from narrowest to widest. The order is the ranking.
RETEST_SCOPES = (
    "none",
    "repeat-affected-coupon",
    "repeat-affected-subgroup",
    "requalify-full-programme",
)

CAUSE_TO_SCOPE = {
    "test-installation-artefact": "repeat-affected-coupon",
    "isolated-build-escape": "repeat-affected-subgroup",
    "systematic-process-cause": "requalify-full-programme",
    "design-inherent-cause": "requalify-full-programme",
}

# What the governing scope says about the standing of work already done.
_SCOPE_TO_STATUS = {
    "none": "qualification-status-undecided",
    "repeat-affected-coupon": "coupon-result-void",
    "repeat-affected-subgroup": "subgroup-result-void",
    "requalify-full-programme": "qualification-invalidated",
}


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _flag(value, label):
    """Return a strict boolean, refusing a truthy stand-in."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def normalize_mode(mode):
    """Return a recognized failure mode, refusing anything else."""
    if not isinstance(mode, str):
        raise ValueError("failure mode must be a string, got %r" % (mode,))
    cleaned = mode.strip().lower()
    if cleaned not in FAILURE_MODES:
        raise ValueError(
            "unrecognized failure mode %r; recognized: %s"
            % (mode, ", ".join(FAILURE_MODES))
        )
    return cleaned


def normalize_cause(cause):
    """Return a recognized cause category, refusing anything else."""
    if not isinstance(cause, str):
        raise ValueError("cause must be a string, got %r" % (cause,))
    cleaned = cause.strip().lower()
    if cleaned not in CAUSE_CATEGORIES:
        raise ValueError(
            "unrecognized cause %r; recognized: %s"
            % (cause, ", ".join(CAUSE_CATEGORIES))
        )
    return cleaned


def scope_rank(scope):
    """Return the reach of a retest scope, larger meaning wider."""
    if not isinstance(scope, str) or scope.strip().lower() not in RETEST_SCOPES:
        raise ValueError(
            "unrecognized retest scope %r; recognized: %s"
            % (scope, ", ".join(RETEST_SCOPES))
        )
    return RETEST_SCOPES.index(scope.strip().lower())


def retest_scope_for_cause(cause):
    """Return the retest scope an attributed cause forces."""
    cleaned = normalize_cause(cause)
    if cleaned == UNDETERMINED_CAUSE:
        raise ValueError(
            "an undetermined cause forces no retest scope; the investigation has "
            "to attribute the failure first"
        )
    return CAUSE_TO_SCOPE[cleaned]


def widest_scope(scopes):
    """Return the widest of several retest scopes."""
    if not isinstance(scopes, (list, tuple)) or not scopes:
        raise ValueError("scopes must be a non-empty sequence")
    widest = RETEST_SCOPES[0]
    for scope in scopes:
        if scope_rank(scope) > scope_rank(widest):
            widest = scope.strip().lower()
    return widest


def qualification_status_for_scope(scope):
    """Return what a governing retest scope says about work already done."""
    return _SCOPE_TO_STATUS[RETEST_SCOPES[scope_rank(scope)]]


def validate_failure_record(record, label="failure"):
    """Return one observed failure mode with its attributed cause."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    if "mode" not in record:
        raise ValueError("%s missing required key 'mode'" % label)
    if "cause" not in record:
        raise ValueError(
            "%s missing required key 'cause'; an unrecorded cause is recorded as "
            "'%s', never left out" % (label, UNDETERMINED_CAUSE)
        )
    out = {
        "mode": normalize_mode(record["mode"]),
        "cause": normalize_cause(record["cause"]),
    }
    if "evidence" in record:
        out["evidence"] = _identifier(record["evidence"], "%s evidence" % label)
    return out


def validate_failure_records(records):
    """Return the validated failure records of one coupon."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError(
            "failures must be a non-empty sequence; this clause governs a coupon "
            "that showed at least one failure mode"
        )
    seen = set()
    out = []
    for index, record in enumerate(records):
        validated = validate_failure_record(record, "failures[%d]" % index)
        if validated["mode"] in seen:
            raise ValueError("duplicate failure mode %r" % validated["mode"])
        seen.add(validated["mode"])
        out.append(validated)
    return out


def governing_failure(records):
    """Return the validated failure whose cause forces the widest retest."""
    validated = validate_failure_records(records)
    attributed = [r for r in validated if r["cause"] != UNDETERMINED_CAUSE]
    if not attributed:
        raise ValueError("no failure carries an attributed cause yet")
    governing = attributed[0]
    for record in attributed[1:]:
        if scope_rank(retest_scope_for_cause(record["cause"])) > scope_rank(
            retest_scope_for_cause(governing["cause"])
        ):
            governing = record
    return governing


def validate_corrective_action(action):
    """Return the corrective-action state, both flags explicit."""
    if action is None:
        return {"implemented": False, "verified": False}
    if not isinstance(action, dict):
        raise ValueError("corrective_action must be a mapping or None")
    for key in ("implemented", "verified"):
        if key not in action:
            raise ValueError(
                "corrective_action missing required key '%s'; an unrecorded state "
                "is not a done state" % key
            )
    implemented = _flag(action["implemented"], "corrective_action implemented")
    verified = _flag(action["verified"], "corrective_action verified")
    if verified and not implemented:
        raise ValueError(
            "corrective_action cannot be verified while it is not implemented"
        )
    return {"implemented": implemented, "verified": verified}


def assess_failed_coupon(spec):
    """Run the full clause 5.6.2 treatment of a failed qualification coupon.

    spec keys: coupon_id, failures; optional corrective_action.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("coupon_id", "failures"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    coupon_id = _identifier(spec["coupon_id"], "coupon_id")
    failures = validate_failure_records(spec["failures"])
    action = validate_corrective_action(spec.get("corrective_action"))

    findings = []
    unattributed = tuple(r["mode"] for r in failures if r["cause"] == UNDETERMINED_CAUSE)
    for mode in unattributed:
        findings.append(
            "failure mode '%s' on coupon %s has no attributed cause, so no retest "
            "scope follows from it" % (mode, coupon_id)
        )

    if unattributed:
        scope = "none"
        governing = None
        disposition = "investigation-open"
    else:
        governing = governing_failure(failures)
        scope = widest_scope([retest_scope_for_cause(r["cause"]) for r in failures])
        if not action["implemented"]:
            findings.append(
                "corrective action for '%s' is not implemented, so the %s retest is "
                "not admissible" % (governing["cause"], scope)
            )
            disposition = "retest-blocked"
        elif not action["verified"]:
            findings.append(
                "corrective action for '%s' is implemented but unverified, so the %s "
                "retest is not admissible" % (governing["cause"], scope)
            )
            disposition = "retest-blocked"
        else:
            disposition = "retest-authorized"

    return {
        "coupon_id": coupon_id,
        "failures": failures,
        "failure_mode_count": len(failures),
        "unattributed_modes": unattributed,
        "governing_cause": governing["cause"] if governing else UNDETERMINED_CAUSE,
        "governing_mode": governing["mode"] if governing else None,
        "retest_scope": scope,
        "qualification_status": qualification_status_for_scope(scope),
        "qualification_evidence_withdrawn": True,
        "corrective_action": action,
        "disposition": disposition,
        "retest_authorized": disposition == "retest-authorized",
        "findings": findings,
    }
