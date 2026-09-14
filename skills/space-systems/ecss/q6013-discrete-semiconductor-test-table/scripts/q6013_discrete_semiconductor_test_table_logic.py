"""Discrete semiconductor test-matrix evaluation for a commercial EEE lot.

Anchor: ECSS-Q-ST-60-13C Table 8-3 (the test matrix applied to discrete
semiconductors -- diodes, transistors and optocouplers -- with the methods
run on each family and the acceptance limits their measured parameters are
taken against). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the device family. The required test groups and the parameters
   that carry the acceptance decision differ by family, so a matrix is
   judged against the family it was written for and an unknown family is
   refused rather than defaulted.
2. Check the declared matrix covers every required group for that family and
   that no group is declared twice.
3. Evaluate each measured parameter as a drift between the initial and the
   post-stress reading, in the direction that parameter degrades in: a
   forward voltage may move either way, a leakage current only upward
   matters, and an optocoupler current transfer ratio only downward.
4. Take each row's failures against its accept number and count the devices
   whose drift left its limit, holding the lot when either path rejects.
5. Report the disposition with every rejecting group named, not the first,
   and a marginal-row advisory where a row used its accept number in full.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "DEVICE_FAMILIES",
    "FAMILY_TEST_GROUPS",
    "FAMILY_PARAMETERS",
    "DRIFT_DIRECTIONS",
    "normalize_family",
    "required_test_groups",
    "relative_drift_percent",
    "drift_within_limit",
    "evaluate_parameter",
    "evaluate_device",
    "matrix_coverage",
    "row_verdict",
    "assess_discrete_semiconductor_test_table",
]

# Drift is a ratio of two measured readings scaled by 100; an exact equality
# with a limit can land a few ULPs on the wrong side. Absorb the
# representation error here, never by relaxing the limit.
LIMIT_TOLERANCE = 1e-9

DEVICE_FAMILIES = ("diode", "transistor", "optocoupler")

# The test groups each family's matrix has to cover. The three share the
# environmental and construction groups; the electrical group differs,
# and the optocoupler adds the isolation group no two-terminal part has.
_COMMON_GROUPS = (
    "visual-inspection",
    "electrical-measurement",
    "burn-in",
    "thermal-shock",
    "life-test",
    "solderability",
    "destructive-physical-analysis",
)

FAMILY_TEST_GROUPS = {
    "diode": _COMMON_GROUPS + ("reverse-bias-stress",),
    "transistor": _COMMON_GROUPS + ("safe-operating-area-check",),
    "optocoupler": _COMMON_GROUPS + ("isolation-voltage", "current-transfer-ratio"),
}

# How each family's acceptance parameters degrade. 'both' bounds the
# magnitude of the change, 'increase' only penalises an upward move, and
# 'decrease' only penalises a downward one.
DRIFT_DIRECTIONS = ("both", "increase", "decrease")

FAMILY_PARAMETERS = {
    "diode": {
        "forward-voltage": "both",
        "reverse-leakage": "increase",
    },
    "transistor": {
        "forward-current-gain": "both",
        "collector-cutoff-current": "increase",
        "collector-emitter-saturation-voltage": "increase",
    },
    "optocoupler": {
        "current-transfer-ratio": "decrease",
        "input-forward-voltage": "both",
        "output-leakage-current": "increase",
    },
}


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def normalize_family(family):
    """Return the canonical device family name for a declared matrix."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("device family must be a non-empty name, got %r" % (family,))
    name = family.strip().lower()
    if name not in DEVICE_FAMILIES:
        raise ValueError(
            "device family must be one of %r, got %r" % (DEVICE_FAMILIES, family)
        )
    return name


def required_test_groups(family):
    """Return the test groups the matrix of one device family has to cover."""
    return FAMILY_TEST_GROUPS[normalize_family(family)]


def relative_drift_percent(initial, final):
    """Return the signed drift of a parameter, in percent of its initial reading."""
    start = _real("initial reading", initial)
    end = _real("final reading", final)
    if start == 0.0:
        raise ValueError("relative drift is undefined against a zero initial reading")
    return (end - start) / abs(start) * 100.0


def drift_within_limit(initial, final, limit_percent, direction):
    """Return True when a parameter's drift stays inside its declared limit."""
    if direction not in DRIFT_DIRECTIONS:
        raise ValueError(
            "drift direction must be one of %r, got %r" % (DRIFT_DIRECTIONS, direction)
        )
    limit = _real("limit_percent", limit_percent)
    if limit < 0.0:
        raise ValueError("a drift limit must be non-negative, got %g" % limit)
    drift = relative_drift_percent(initial, final)
    if direction == "both":
        return abs(drift) <= limit + LIMIT_TOLERANCE
    if direction == "increase":
        return drift <= limit + LIMIT_TOLERANCE
    return -drift <= limit + LIMIT_TOLERANCE


def evaluate_parameter(family, parameter, initial, final, limit_percent):
    """Return the drift record of one acceptance parameter of one family."""
    name = normalize_family(family)
    if not isinstance(parameter, str) or not parameter.strip():
        raise ValueError("parameter must be a non-empty name, got %r" % (parameter,))
    key = parameter.strip().lower()
    directions = FAMILY_PARAMETERS[name]
    if key not in directions:
        raise ValueError(
            "parameter %r is not an acceptance parameter of the %s family" % (parameter, name)
        )
    direction = directions[key]
    drift = relative_drift_percent(initial, final)
    return {
        "family": name,
        "parameter": key,
        "initial": _real("initial reading", initial),
        "final": _real("final reading", final),
        "drift_percent": drift,
        "limit_percent": _real("limit_percent", limit_percent),
        "direction": direction,
        "within_limit": drift_within_limit(initial, final, limit_percent, direction),
    }


def evaluate_device(family, readings, limits):
    """Return the per-device record of every declared parameter drift.

    readings maps a parameter name to an (initial, final) pair; limits maps
    the same names to their drift limits in percent.
    """
    name = normalize_family(family)
    if not isinstance(readings, dict) or not readings:
        raise ValueError("readings must be a non-empty mapping of parameter to (initial, final)")
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping of parameter to a percent limit")
    records = []
    for parameter, pair in readings.items():
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("readings[%r] must be an (initial, final) pair" % (parameter,))
        key = parameter.strip().lower() if isinstance(parameter, str) else parameter
        if key not in limits:
            raise ValueError("no drift limit declared for parameter %r" % (parameter,))
        records.append(evaluate_parameter(name, parameter, pair[0], pair[1], limits[key]))
    drifted = [r["parameter"] for r in records if not r["within_limit"]]
    return {
        "family": name,
        "parameters": records,
        "drifted_parameters": drifted,
        "rejected": bool(drifted),
    }


def matrix_coverage(family, entries):
    """Return the coverage record of a declared matrix against one family."""
    required = required_test_groups(family)
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of matrix rows")
    seen = []
    duplicates = []
    unknown = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        group = entry.get("group")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("entries[%d] needs a non-empty 'group'" % index)
        group = group.strip()
        if group in seen and group not in duplicates:
            duplicates.append(group)
        if group not in seen:
            seen.append(group)
        if group not in required and group not in unknown:
            unknown.append(group)
    missing = [g for g in required if g not in seen]
    return {
        "family": normalize_family(family),
        "declared": seen,
        "missing": missing,
        "duplicated": duplicates,
        "unrecognized": unknown,
        "complete": not missing and not duplicates,
    }


def row_verdict(entry):
    """Return the verdict record for one row of a discrete semiconductor matrix.

    entry keys: group, method, sample_size, failures, accept_number.
    """
    if not isinstance(entry, dict):
        raise ValueError("a matrix row must be a mapping, got %r" % (entry,))
    for key in ("group", "method", "sample_size", "failures", "accept_number"):
        if key not in entry:
            raise ValueError("matrix row missing required key '%s'" % key)
    group = entry["group"]
    if not isinstance(group, str) or not group.strip():
        raise ValueError("matrix row needs a non-empty 'group'")
    method = entry["method"]
    if not isinstance(method, str) or not method.strip():
        raise ValueError("matrix row needs a non-empty 'method' reference")
    sample = _count("sample_size", entry["sample_size"])
    if sample < 1:
        raise ValueError("a matrix row sample must be at least one device")
    failures = _count("failures", entry["failures"])
    accept = _count("accept_number", entry["accept_number"])
    if failures > sample:
        raise ValueError(
            "row '%s' reports %d failures in a sample of %d"
            % (group.strip(), failures, sample)
        )
    if accept > sample:
        raise ValueError(
            "row '%s' has an accept number of %d for a sample of %d"
            % (group.strip(), accept, sample)
        )
    accepted = failures <= accept
    findings = []
    if not accepted:
        findings.append(
            "row '%s' took %d failures against an accept number of %d"
            % (group.strip(), failures, accept)
        )
    return {
        "group": group.strip(),
        "method": method.strip(),
        "sample_size": sample,
        "failures": failures,
        "accept_number": accept,
        "accepted": accepted,
        "marginal": accepted and accept > 0 and failures == accept,
        "findings": findings,
    }


def assess_discrete_semiconductor_test_table(spec):
    """Run the full Table 8-3 discrete semiconductor matrix assessment.

    spec keys: family, entries; optional devices (each a mapping of
    parameter to an (initial, final) pair) and drift_limits.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("family", "entries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    family = normalize_family(spec["family"])
    coverage = matrix_coverage(family, spec["entries"])
    rows = [row_verdict(entry) for entry in spec["entries"]]
    devices = spec.get("devices") or []
    if not isinstance(devices, (list, tuple)):
        raise ValueError("devices must be a sequence of per-device reading mappings")
    limits = spec.get("drift_limits") or {}
    device_records = []
    for index, readings in enumerate(devices):
        if not isinstance(readings, dict):
            raise ValueError("devices[%d] must be a mapping of parameter readings" % index)
        device_records.append(evaluate_device(family, readings, limits))
    drift_rejects = sum(1 for record in device_records if record["rejected"])
    findings = []
    for group in coverage["missing"]:
        findings.append("required test group '%s' is absent from the %s matrix" % (group, family))
    for group in coverage["duplicated"]:
        findings.append("test group '%s' is declared more than once" % group)
    for row in rows:
        findings.extend(row["findings"])
    if drift_rejects:
        findings.append(
            "%d of %d devices drifted past an acceptance limit"
            % (drift_rejects, len(device_records))
        )
    advisories = [
        "row '%s' used its accept number in full" % row["group"]
        for row in rows
        if row["marginal"]
    ]
    accepted = not findings
    return {
        "family": family,
        "coverage": coverage,
        "rows": rows,
        "devices": device_records,
        "drift_reject_count": drift_rejects,
        "rejecting_groups": [row["group"] for row in rows if not row["accepted"]],
        "accepted": accepted,
        "disposition": "accept" if accepted else "hold",
        "findings": findings,
        "advisories": advisories,
    }
