"""
ECSS-E-ST-10-24C §5.4 — Interface Definition Logic

Deterministic, offline checks for IDD / single-end ICD completeness:
geometry, signals, protocols, and budget at each interface end.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECOGNIZED_INTERFACE_TYPES = frozenset({
    "mechanical", "electrical", "data", "fluid", "thermal", "optical"
})

GEOMETRY_REQUIRED = frozenset({"mounting_point", "envelope_mm", "mass_kg"})
SIGNAL_REQUIRED = frozenset({"signal_type", "voltage_v", "impedance_ohm"})
PROTOCOL_REQUIRED = frozenset({"protocol_name", "data_rate_bps", "message_format"})
BUDGET_REQUIRED = frozenset({"allocated", "capacity"})

# Attribute groups required per interface type
_TYPE_GROUPS = {
    "mechanical": frozenset({"geometry"}),
    "electrical": frozenset({"geometry", "signals"}),
    "data":       frozenset({"geometry", "protocols", "budget"}),
    "fluid":      frozenset({"geometry", "budget"}),
    "thermal":    frozenset({"geometry", "budget"}),
    "optical":    frozenset({"geometry", "signals"}),
}

# Voltage tolerance (V) for signal compatibility check
_VOLTAGE_TOLERANCE_V = 0.5


# ---------------------------------------------------------------------------
# Attribute-group validators
# ---------------------------------------------------------------------------

def validate_geometry(geometry: dict) -> list:
    """Return list of missing-field finding strings for a geometry block."""
    return [
        f"geometry.{f}" for f in sorted(GEOMETRY_REQUIRED)
        if f not in geometry
    ]


def validate_signals(signals: dict) -> list:
    """Return list of missing-field finding strings for a signals block."""
    return [
        f"signals.{f}" for f in sorted(SIGNAL_REQUIRED)
        if f not in signals
    ]


def validate_protocols(protocols: dict) -> list:
    """Return list of missing-field finding strings for a protocols block."""
    return [
        f"protocols.{f}" for f in sorted(PROTOCOL_REQUIRED)
        if f not in protocols
    ]


def check_budget(budget: dict) -> dict:
    """
    Evaluate a budget block for a single interface end.

    Returns:
        dict with keys:
          compliant  (bool)
          margin_pct (float | None)
          findings   (list[str])
    """
    findings = []
    for field in sorted(BUDGET_REQUIRED):
        if field not in budget:
            findings.append(f"budget.{field} missing")

    if findings:
        return {"compliant": False, "margin_pct": None, "findings": findings}

    allocated = budget["allocated"]
    capacity = budget["capacity"]

    if not isinstance(allocated, (int, float)):
        findings.append("budget.allocated must be numeric")
    if not isinstance(capacity, (int, float)):
        findings.append("budget.capacity must be numeric")
    if findings:
        return {"compliant": False, "margin_pct": None, "findings": findings}

    if capacity <= 0:
        return {
            "compliant": False,
            "margin_pct": None,
            "findings": ["budget.capacity must be positive (> 0)"],
        }

    if allocated < 0:
        return {
            "compliant": False,
            "margin_pct": None,
            "findings": ["budget.allocated must be non-negative (>= 0)"],
        }

    margin_pct = round((capacity - allocated) / capacity * 100.0, 4)
    compliant = allocated <= capacity

    if not compliant:
        findings.append(
            f"budget exceeded: allocated={allocated} > capacity={capacity}"
        )

    return {"compliant": compliant, "margin_pct": margin_pct, "findings": findings}


# ---------------------------------------------------------------------------
# Interface-end validator
# ---------------------------------------------------------------------------

def validate_interface_end(end: dict) -> list:
    """
    Validate one interface end against ECSS-E-ST-10-24C §5.4 requirements.

    Returns list of finding strings (empty list means the end is valid).
    """
    findings = []

    end_id = end.get("end_id", "")
    if not str(end_id).strip():
        findings.append("end_id missing or blank")

    itype = end.get("interface_type")
    if itype is None:
        findings.append("interface_type missing")
        return findings

    if itype not in RECOGNIZED_INTERFACE_TYPES:
        findings.append(
            f"interface_type '{itype}' not recognized; "
            f"expected one of {sorted(RECOGNIZED_INTERFACE_TYPES)}"
        )
        return findings

    required = _TYPE_GROUPS[itype]

    if "geometry" in required:
        geo = end.get("geometry")
        if geo is None:
            findings.append("geometry block missing")
        elif not isinstance(geo, dict):
            findings.append("geometry must be a dict")
        else:
            findings.extend(validate_geometry(geo))

    if "signals" in required:
        sig = end.get("signals")
        if sig is None:
            findings.append("signals block missing")
        elif not isinstance(sig, dict):
            findings.append("signals must be a dict")
        else:
            findings.extend(validate_signals(sig))

    if "protocols" in required:
        proto = end.get("protocols")
        if proto is None:
            findings.append("protocols block missing")
        elif not isinstance(proto, dict):
            findings.append("protocols must be a dict")
        else:
            findings.extend(validate_protocols(proto))

    if "budget" in required:
        bud = end.get("budget")
        if bud is None:
            findings.append("budget block missing")
        elif not isinstance(bud, dict):
            findings.append("budget must be a dict")
        else:
            findings.extend(check_budget(bud)["findings"])

    return findings


# ---------------------------------------------------------------------------
# Cross-end compatibility check
# ---------------------------------------------------------------------------

def check_signal_compatibility(end_a: dict, end_b: dict) -> list:
    """
    Check signal compatibility between two electrical or optical ends.

    Returns list of incompatibility finding strings.
    """
    findings = []
    sig_a = end_a.get("signals") or {}
    sig_b = end_b.get("signals") or {}

    type_a = sig_a.get("signal_type")
    type_b = sig_b.get("signal_type")
    if type_a and type_b and type_a != type_b:
        findings.append(
            f"signal_type mismatch: end '{end_a.get('end_id')}' has '{type_a}', "
            f"end '{end_b.get('end_id')}' has '{type_b}'"
        )

    v_a = sig_a.get("voltage_v")
    v_b = sig_b.get("voltage_v")
    if isinstance(v_a, (int, float)) and isinstance(v_b, (int, float)):
        delta = abs(v_a - v_b)
        if delta > _VOLTAGE_TOLERANCE_V:
            findings.append(
                f"voltage mismatch: end '{end_a.get('end_id')}' = {v_a} V, "
                f"end '{end_b.get('end_id')}' = {v_b} V "
                f"(delta {round(delta, 4)} V > tolerance {_VOLTAGE_TOLERANCE_V} V)"
            )

    return findings


# ---------------------------------------------------------------------------
# Top-level IDD checker
# ---------------------------------------------------------------------------

def define_interface(idd: dict) -> dict:
    """
    Run the full ECSS-E-ST-10-24C §5.4 interface-definition check on one IDD.

    Args:
        idd: dict with keys:
          idd_id          (str)
          interface_ends  (list of end dicts)

    Returns:
        dict with keys:
          complete               (bool)
          end_findings           (dict: end_id -> list[str])
          compatibility_findings (list[str])
          summary                (str)
    """
    idd_id = str(idd.get("idd_id", "")).strip()
    if not idd_id:
        return {
            "complete": False,
            "end_findings": {},
            "compatibility_findings": [],
            "summary": "idd_id missing or blank",
        }

    ends = idd.get("interface_ends")
    if not isinstance(ends, list) or len(ends) == 0:
        return {
            "complete": False,
            "end_findings": {},
            "compatibility_findings": [],
            "summary": f"IDD '{idd_id}': interface_ends must be a non-empty list",
        }

    end_findings: dict = {}
    for end in ends:
        eid = str(end.get("end_id", "<unknown>")).strip() or "<unknown>"
        end_findings[eid] = validate_interface_end(end)

    # Signal compatibility for electrical/optical pairs
    compatibility_findings: list = []
    signal_ends = [
        e for e in ends
        if e.get("interface_type") in {"electrical", "optical"}
    ]
    if len(signal_ends) == 2:
        compatibility_findings.extend(
            check_signal_compatibility(signal_ends[0], signal_ends[1])
        )

    all_ends_ok = all(len(f) == 0 for f in end_findings.values())
    complete = all_ends_ok and len(compatibility_findings) == 0

    if complete:
        summary = (
            f"IDD '{idd_id}': interface definition complete — "
            f"{len(ends)} end(s) validated."
        )
    else:
        total = (
            sum(len(f) for f in end_findings.values())
            + len(compatibility_findings)
        )
        summary = (
            f"IDD '{idd_id}': {total} finding(s) — "
            f"interface definition incomplete."
        )

    return {
        "complete": complete,
        "end_findings": end_findings,
        "compatibility_findings": compatibility_findings,
        "summary": summary,
    }
