"""
ECSS-E-ST-10-24C §5.10 — Test Interface Control Document (TICD) logic.
Deterministic, offline, stdlib only.
"""

VALID_SIGNAL_TYPES = frozenset({
    "electrical", "mechanical", "thermal", "rf",
    "optical", "data", "power", "ground",
})

VALID_DIRECTIONS = frozenset({"source", "sink", "bidirectional"})


def validate_signal_record(record):
    """
    Validate one signal record for required fields and controlled values.
    Returns (True, "ok") or (False, reason_string).
    """
    required = {"signal_name", "signal_type", "direction", "connector", "pin"}
    missing = required - set(record.keys())
    if missing:
        return False, "missing fields: {}".format(", ".join(sorted(missing)))

    name = str(record["signal_name"]).strip()
    if not name:
        return False, "signal_name must not be blank"

    sig_type = record["signal_type"]
    if sig_type not in VALID_SIGNAL_TYPES:
        return False, "unrecognized signal_type: {}".format(sig_type)

    direction = record["direction"]
    if direction not in VALID_DIRECTIONS:
        return False, "unrecognized direction: {}".format(direction)

    connector = str(record["connector"]).strip()
    if not connector:
        return False, "connector must not be blank"

    pin = str(record["pin"]).strip()
    if not pin:
        return False, "pin must not be blank"

    return True, "ok"


def check_pin_conflicts(signals):
    """
    Return list of (connector, pin) pairs assigned to more than one signal.
    Each conflicting pair appears once in the result.
    """
    seen = {}
    conflicts = []
    for sig in signals:
        key = (str(sig["connector"]).strip(), str(sig["pin"]).strip())
        if key in seen:
            if key not in conflicts:
                conflicts.append(key)
        else:
            seen[key] = sig["signal_name"]
    return conflicts


def check_signal_name_duplicates(signals):
    """
    Return list of signal names that appear more than once in the signal set.
    Each duplicate name appears once in the result.
    """
    seen = set()
    duplicates = []
    for sig in signals:
        name = sig["signal_name"]
        if name in seen:
            if name not in duplicates:
                duplicates.append(name)
        else:
            seen.add(name)
    return duplicates


def check_ground_reference(signals):
    """Return True if at least one signal of type 'ground' is present."""
    return any(s["signal_type"] == "ground" for s in signals)


def check_category_coverage(signals, required_categories):
    """
    Return the subset of required_categories that has no representative
    signal in the signal set.
    """
    present = {s["signal_type"] for s in signals}
    return [c for c in required_categories if c not in present]


def check_direction_conflicts(signals):
    """
    Return signal names that appear as both 'source' and 'sink'
    in the same TICD — a contradictory interface definition.
    """
    directions_by_name = {}
    for sig in signals:
        name = sig["signal_name"]
        directions_by_name.setdefault(name, set()).add(sig["direction"])
    return [
        name
        for name, dirs in directions_by_name.items()
        if "source" in dirs and "sink" in dirs
    ]


def assess_ticd(ticd_record):
    """
    Full TICD assessment for one test configuration.

    Expected ticd_record structure::

        {
            "ticd_id":            str,        # mandatory traceability anchor
            "test_item":          str,        # UUT name/config identifier
            "signals": [                      # list of signal descriptors
                {
                    "signal_name":  str,
                    "signal_type":  str,      # from VALID_SIGNAL_TYPES
                    "direction":    str,      # from VALID_DIRECTIONS
                    "connector":    str,
                    "pin":          str,
                },
                ...
            ],
            "required_categories": [str, ...] # signal types the test requires
        }

    Returns::

        {
            "valid":    bool,
            "findings": [str]   # empty list means TICD is ready to baseline
        }
    """
    findings = []

    if not str(ticd_record.get("ticd_id", "")).strip():
        findings.append("ticd_id must not be blank")

    if not str(ticd_record.get("test_item", "")).strip():
        findings.append("test_item must not be blank")

    signals = ticd_record.get("signals", [])
    if not signals:
        findings.append("no signals defined — TICD has no interface content")
        return {"valid": False, "findings": findings}

    # Per-record validation
    valid_signals = []
    for i, sig in enumerate(signals):
        ok, msg = validate_signal_record(sig)
        if not ok:
            findings.append("signal[{}]: {}".format(i, msg))
        else:
            valid_signals.append(sig)

    # Pin conflict check (on all records that have connector+pin)
    pin_conflicts = check_pin_conflicts(
        [s for s in signals if "connector" in s and "pin" in s]
    )
    for conn, pin in pin_conflicts:
        findings.append(
            "pin conflict: connector={} pin={} assigned to multiple signals".format(conn, pin)
        )

    # Duplicate signal names
    for name in check_signal_name_duplicates(signals):
        findings.append("duplicate signal name: {}".format(name))

    # Ground reference
    if not check_ground_reference(valid_signals):
        findings.append(
            "no ground reference signal — at least one signal of type 'ground' is required"
        )

    # Required category coverage
    required = ticd_record.get("required_categories", [])
    for cat in check_category_coverage(valid_signals, required):
        findings.append("required interface category not covered: {}".format(cat))

    # Direction conflicts
    for name in check_direction_conflicts(valid_signals):
        findings.append(
            "direction conflict: signal '{}' is defined as both source and sink".format(name)
        )

    return {"valid": len(findings) == 0, "findings": findings}
