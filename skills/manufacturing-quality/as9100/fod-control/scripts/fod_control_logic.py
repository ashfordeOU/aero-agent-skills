"""FOD prevention program logic: zone classification, risk score, sweep
cadence, tool reconciliation, and audit verdicts for aerospace production.

Pure Python stdlib, deterministic, offline. The zone cuts, sweep cadence,
and control sets are documented example policy values: a site redefines
them through the module constants without touching the scoring functions.
"""

# Risk score thresholds, highest protection first: score >= 14 -> zone A,
# score >= 10 -> zone B, below 10 -> zone C.
ZONE_CUTS = [(14, "A"), (10, "B")]

# Required FOD sweep cadence in hours per zone (example policy input).
SWEEP_INTERVAL_H = {"A": 8, "B": 40, "C": 160}

# Required FOD control sets per zone (example policy input).
CONTROL_SET = {
    "A": ["tool-control", "count-reconcile", "sweep-log",
          "tethering", "fod-mats", "training"],
    "B": ["tool-control", "count-reconcile", "sweep-log", "fod-mats"],
    "C": ["tool-control", "sweep-log"],
}

CONTROL_VOCABULARY = sorted({c for cs in CONTROL_SET.values() for c in cs})


def _check_int(value, lo, hi, name):
    """Reject a non-integer or an integer outside the stated band."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < lo or value > hi:
        raise ValueError(
            "%s must be in %d..%d, got %d" % (name, lo, hi, value)
        )


def risk_score(part_criticality, debris_exposure, open_cavity_exposure):
    """Weighted FOD risk score: 3*criticality + 2*debris + 2*open_cavity.

    part_criticality is 1-3 (3 flight-control or propulsion critical,
    2 structural, 1 non-flight), debris_exposure 1-3 (3 machining or
    cutting, 2 assembly with fasteners and rework, 1 inspection or bench
    work), open_cavity_exposure 0-2 (2 open fuel tank or engine inlet
    cavity, 1 open assembly, 0 enclosed). ValueError on any input
    outside its stated band.
    """
    _check_int(part_criticality, 1, 3, "part_criticality")
    _check_int(debris_exposure, 1, 3, "debris_exposure")
    _check_int(open_cavity_exposure, 0, 2, "open_cavity_exposure")
    return (3 * part_criticality + 2 * debris_exposure
            + 2 * open_cavity_exposure)


def zone_class(score):
    """Map a FOD risk score to zone A (>= 14), zone B (>= 10), or C."""
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError("score must be an integer, got %r" % (score,))
    if score < 0:
        raise ValueError("score must be non-negative, got %d" % score)
    for cut, zone in sorted(ZONE_CUTS, reverse=True):
        if score >= cut:
            return zone
    return "C"


def sweep_interval_h(zone):
    """Required FOD sweep interval in hours for the zone."""
    if zone not in SWEEP_INTERVAL_H:
        raise ValueError(
            "unknown zone %r; expected one of %s"
            % (zone, ", ".join(sorted(SWEEP_INTERVAL_H)))
        )
    return SWEEP_INTERVAL_H[zone]


def required_controls(zone):
    """The required FOD control set for the zone, as a fresh list."""
    if zone not in CONTROL_SET:
        raise ValueError(
            "unknown zone %r; expected one of %s"
            % (zone, ", ".join(sorted(CONTROL_SET)))
        )
    return list(CONTROL_SET[zone])


def _check_counts(tool_counts, label):
    """Reject a negative or non-integer quantity in a tool count dict."""
    for name, qty in tool_counts.items():
        if isinstance(qty, bool) or not isinstance(qty, int):
            raise ValueError(
                "%s qty for %r must be an integer, got %r"
                % (label, name, qty)
            )
        if qty < 0:
            raise ValueError(
                "%s qty for %r must be non-negative, got %d"
                % (label, name, qty)
            )


def reconcile_tools(issued, returned):
    """Compare returned tool counts against issued; report shortfalls.

    missing maps every issued tool with a shortfall to that shortfall;
    reconciled is True only when no issued tool is short. Extra returned
    tools that were never issued, and over-returns of an issued tool,
    are ignored. ValueError on a negative quantity in either dict.
    """
    _check_counts(issued, "issued")
    _check_counts(returned, "returned")
    missing = {}
    for name, qty in issued.items():
        back = returned.get(name, 0)
        if back < qty:
            missing[name] = qty - back
    return {"missing": missing, "reconciled": not missing}


def program_audit(part_criticality, debris_exposure, open_cavity_exposure,
                  issued_tools, returned_tools, controls_present):
    """Score the FOD program and produce the audit verdict with findings.

    Returns the zone class, the risk score, the sweep interval, the
    required and present control lists, the missing controls, the tool
    reconciliation result, the control completeness (present over
    required), and the verdict: fod-pass needs completeness 1.0 and a
    reconciled tool count, otherwise fod-fail. Findings list the missing
    controls plus "missing-tool" when the tool count is not reconciled.
    ValueError on a negative tool quantity or an unknown control name.
    """
    for control in controls_present:
        if control not in CONTROL_VOCABULARY:
            raise ValueError(
                "unknown control %r; expected one of %s"
                % (control, ", ".join(CONTROL_VOCABULARY))
            )
    score = risk_score(part_criticality, debris_exposure,
                       open_cavity_exposure)
    zone = zone_class(score)
    required = required_controls(zone)
    present = [c for c in required if c in controls_present]
    missing_controls = [c for c in required if c not in controls_present]
    reconciliation = reconcile_tools(issued_tools, returned_tools)
    completeness = len(present) / float(len(required))
    reconciled = reconciliation["reconciled"]
    verdict = "fod-pass" if completeness == 1.0 and reconciled else "fod-fail"
    findings = list(missing_controls)
    if not reconciled:
        findings.append("missing-tool")
    return {
        "zone": zone,
        "score": score,
        "sweep_interval_h": sweep_interval_h(zone),
        "required": required,
        "present": present,
        "missing_controls": missing_controls,
        "reconciliation": reconciliation,
        "completeness": completeness,
        "verdict": verdict,
        "findings": findings,
    }
