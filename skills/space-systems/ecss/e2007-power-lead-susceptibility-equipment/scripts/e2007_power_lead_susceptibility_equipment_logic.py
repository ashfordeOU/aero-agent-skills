#!/usr/bin/env python3
"""Power-lead susceptibility injection equipment (ECSS-E-ST-20-07C, 5.4.7.2).

Offline, deterministic, standard-library only. The module sizes and checks
the items that put a conducted disturbance onto the supply leads of a unit:

* the signal generator and the span of frequencies it can be tuned over,
* the power amplifier and the drive power it has to deliver once the
  cable loss of the injection path and the test headroom are added,
* the low-inductance series resistor, its residual reactance at the top
  frequency of the band and its derated dissipation at the lead current,
* the chain as a whole: one item per role, no duplicates, no gap in the
  band the injection has to cover.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "INJECTION_BAND_LOWER_HZ",
    "INJECTION_BAND_UPPER_HZ",
    "AMPLIFIER_HEADROOM_DB",
    "RESISTOR_REACTANCE_RATIO_LIMIT",
    "RESISTOR_DERATING_FRACTION",
    "ITEM_ROLES",
    "drive_power_w",
    "amplifier_margin_db",
    "check_amplifier",
    "resistor_reactance_ohm",
    "check_injection_resistor",
    "check_generator_span",
    "normalize_item",
    "assess_injection_equipment",
]

# Absorbs binary-representation error when a ratio or a decibel conversion
# lands a few units in the last place outside an exactly-met bound. It never
# widens the bound itself.
REL_TOL = 1e-9

# Span the injection onto a supply lead is normally required to cover.
INJECTION_BAND_LOWER_HZ = 30.0
INJECTION_BAND_UPPER_HZ = 5.0e7

# Drive power is sized above the delivered power by this many decibels so
# that the amplifier is never run at its compression point.
AMPLIFIER_HEADROOM_DB = 3.0

# The series resistor is only usable while its residual reactance stays this
# small a fraction of its resistance at the top frequency of the band.
RESISTOR_REACTANCE_RATIO_LIMIT = 0.10

# Dissipation in the series resistor is held to this fraction of its rating.
RESISTOR_DERATING_FRACTION = 0.5

ITEM_ROLES = ("generator", "amplifier", "injection-resistor")

_ITEM_KEYS = {
    "generator": ("id", "role", "lower_hz", "upper_hz"),
    "amplifier": ("id", "role", "lower_hz", "upper_hz", "rated_power_w"),
    "injection-resistor": (
        "id",
        "role",
        "resistance_ohm",
        "inductance_h",
        "rating_w",
    ),
}

_REQUIREMENT_KEYS = (
    "required_lower_hz",
    "required_upper_hz",
    "injection_voltage_v",
    "load_ohm",
    "cable_loss_db",
    "headroom_db",
    "lead_current_a",
)


def _finding(code, subject, detail):
    """Build one equipment finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _as_nonnegative_float(value, label):
    number = _as_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _as_identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _within(value, allowed):
    """Bound comparison that absorbs binary-representation error."""
    return value <= allowed or math.isclose(
        value, allowed, rel_tol=REL_TOL, abs_tol=0.0
    )


def _at_least(value, required):
    """Lower-bound comparison that absorbs binary-representation error."""
    return value >= required or math.isclose(
        value, required, rel_tol=REL_TOL, abs_tol=0.0
    )


def drive_power_w(
    injection_voltage_v,
    load_ohm,
    cable_loss_db=0.0,
    headroom_db=AMPLIFIER_HEADROOM_DB,
):
    """Power the amplifier has to produce for a wanted injected voltage.

    The wanted voltage across the lead impedance fixes the power delivered
    there; the loss of the injection path and the headroom are added on top
    as decibels.
    """
    voltage = _as_positive_float(injection_voltage_v, "injection_voltage_v")
    load = _as_positive_float(load_ohm, "load_ohm")
    loss = _as_nonnegative_float(cable_loss_db, "cable_loss_db")
    headroom = _as_nonnegative_float(headroom_db, "headroom_db")
    delivered = voltage * voltage / load
    return delivered * 10.0 ** ((loss + headroom) / 10.0)


def amplifier_margin_db(rated_power_w, required_power_w):
    """Decibel margin of a rated output over the power the chain needs."""
    rated = _as_positive_float(rated_power_w, "rated_power_w")
    required = _as_positive_float(required_power_w, "required_power_w")
    return 10.0 * math.log10(rated / required)


def check_amplifier(rated_power_w, required_power_w):
    """Check one amplifier against the drive power the chain needs."""
    rated = _as_positive_float(rated_power_w, "rated_power_w")
    required = _as_positive_float(required_power_w, "required_power_w")
    return {
        "quantity": "drive-power",
        "rated_w": rated,
        "required_w": required,
        "margin_db": amplifier_margin_db(rated, required),
        "sufficient": _at_least(rated, required),
    }


def resistor_reactance_ohm(inductance_h, frequency_hz):
    """Reactance a residual series inductance shows at a frequency."""
    inductance = _as_nonnegative_float(inductance_h, "inductance_h")
    frequency = _as_positive_float(frequency_hz, "frequency_hz")
    return 2.0 * math.pi * frequency * inductance


def check_injection_resistor(
    resistance_ohm,
    inductance_h,
    rating_w,
    lead_current_a,
    top_frequency_hz,
    ratio_limit=RESISTOR_REACTANCE_RATIO_LIMIT,
    derating=RESISTOR_DERATING_FRACTION,
):
    """Check the series resistor for low inductance and for dissipation.

    The resistor only behaves as a resistor while its residual reactance
    stays a small fraction of its resistance at the top of the band, and it
    only survives the run while the lead current keeps it inside its
    derated rating.
    """
    resistance = _as_positive_float(resistance_ohm, "resistance_ohm")
    inductance = _as_nonnegative_float(inductance_h, "inductance_h")
    rating = _as_positive_float(rating_w, "rating_w")
    current = _as_nonnegative_float(lead_current_a, "lead_current_a")
    top = _as_positive_float(top_frequency_hz, "top_frequency_hz")
    limit = _as_positive_float(ratio_limit, "ratio_limit")
    fraction = _as_positive_float(derating, "derating")
    if fraction > 1.0:
        raise ValueError("derating must not exceed one, got %r" % (derating,))
    reactance = resistor_reactance_ohm(inductance, top)
    ratio = reactance / resistance
    dissipated = current * current * resistance
    allowed = rating * fraction
    return {
        "resistance_ohm": resistance,
        "inductance_h": inductance,
        "top_frequency_hz": top,
        "reactance_ohm": reactance,
        "reactance_ratio": ratio,
        "ratio_limit": limit,
        "low_inductance": _within(ratio, limit),
        "dissipated_w": dissipated,
        "allowed_w": allowed,
        "power_within": _within(dissipated, allowed),
    }


def check_generator_span(
    lower_hz,
    upper_hz,
    required_lower_hz=INJECTION_BAND_LOWER_HZ,
    required_upper_hz=INJECTION_BAND_UPPER_HZ,
):
    """Check a tuning span against the band the injection has to cover."""
    lower = _as_positive_float(lower_hz, "lower_hz")
    upper = _as_positive_float(upper_hz, "upper_hz")
    required_lower = _as_positive_float(required_lower_hz, "required_lower_hz")
    required_upper = _as_positive_float(required_upper_hz, "required_upper_hz")
    if upper <= lower:
        raise ValueError(
            "a tuning span must rise: upper %r does not exceed lower %r"
            % (upper_hz, lower_hz)
        )
    if required_upper <= required_lower:
        raise ValueError(
            "a required band must rise: upper %r does not exceed lower %r"
            % (required_upper_hz, required_lower_hz)
        )
    reaches_bottom = _within(lower, required_lower)
    reaches_top = _at_least(upper, required_upper)
    uncovered = []
    if not reaches_bottom:
        uncovered.append((required_lower, min(lower, required_upper)))
    if not reaches_top:
        uncovered.append((max(upper, required_lower), required_upper))
    return {
        "lower_hz": lower,
        "upper_hz": upper,
        "required_lower_hz": required_lower,
        "required_upper_hz": required_upper,
        "reaches_bottom": reaches_bottom,
        "reaches_top": reaches_top,
        "uncovered_hz": tuple(uncovered),
        "covers": reaches_bottom and reaches_top,
    }


def normalize_item(item):
    """Validate one inventory item and return it with numbers coerced."""
    if not isinstance(item, dict):
        raise ValueError("an inventory item must be a mapping, got %r" % (item,))
    role = item.get("role")
    if role not in _ITEM_KEYS:
        raise ValueError(
            "unknown item role %r, expected one of %s" % (role, list(ITEM_ROLES))
        )
    expected = _ITEM_KEYS[role]
    unknown = sorted(set(item) - set(expected))
    if unknown:
        raise ValueError("unknown key(s) %s on a %s item" % (unknown, role))
    missing = sorted(set(expected) - set(item))
    if missing:
        raise ValueError("missing key(s) %s on a %s item" % (missing, role))
    normalized = {"id": _as_identifier(item["id"], "id"), "role": role}
    for key in expected:
        if key in ("id", "role"):
            continue
        if key == "inductance_h":
            normalized[key] = _as_nonnegative_float(item[key], key)
        else:
            normalized[key] = _as_positive_float(item[key], key)
    if role in ("generator", "amplifier") and normalized["upper_hz"] <= normalized["lower_hz"]:
        raise ValueError(
            "item %s declares a span that does not rise" % normalized["id"]
        )
    return normalized


def _normalize_requirement(requirement):
    if not isinstance(requirement, dict):
        raise ValueError("the requirement must be a mapping, got %r" % (requirement,))
    unknown = sorted(set(requirement) - set(_REQUIREMENT_KEYS))
    if unknown:
        raise ValueError("unknown requirement key(s) %s" % (unknown,))
    values = {
        "required_lower_hz": INJECTION_BAND_LOWER_HZ,
        "required_upper_hz": INJECTION_BAND_UPPER_HZ,
        "cable_loss_db": 0.0,
        "headroom_db": AMPLIFIER_HEADROOM_DB,
        "lead_current_a": 0.0,
    }
    for key in ("injection_voltage_v", "load_ohm"):
        if key not in requirement:
            raise ValueError("the requirement must declare %s" % key)
    values.update(requirement)
    for key in ("required_lower_hz", "required_upper_hz", "injection_voltage_v", "load_ohm"):
        values[key] = _as_positive_float(values[key], key)
    for key in ("cable_loss_db", "headroom_db", "lead_current_a"):
        values[key] = _as_nonnegative_float(values[key], key)
    if values["required_upper_hz"] <= values["required_lower_hz"]:
        raise ValueError("the required band does not rise")
    return values


def assess_injection_equipment(items, requirement):
    """Assess a bench inventory against one injection requirement.

    Returns the drive power the chain needs, the per-role checks, every
    finding raised against the inventory and whether the chain is ready.
    """
    if isinstance(items, (str, bytes)) or not hasattr(items, "__iter__"):
        raise ValueError("items must be an iterable of inventory items")
    normalized = [normalize_item(item) for item in items]
    if not normalized:
        raise ValueError("an inventory must contain at least one item")
    seen_ids = set()
    by_role = {}
    for item in normalized:
        if item["id"] in seen_ids:
            raise ValueError("inventory item %r appears twice" % item["id"])
        seen_ids.add(item["id"])
        if item["role"] in by_role:
            raise ValueError("role %r is declared twice" % item["role"])
        by_role[item["role"]] = item
    needs = _normalize_requirement(requirement)
    required_power = drive_power_w(
        needs["injection_voltage_v"],
        needs["load_ohm"],
        needs["cable_loss_db"],
        needs["headroom_db"],
    )
    findings = []
    checks = {}
    for role in ITEM_ROLES:
        if role not in by_role:
            findings.append(
                _finding("role-missing", role, "no %s is listed in the inventory" % role)
            )
    generator = by_role.get("generator")
    if generator is not None:
        span = check_generator_span(
            generator["lower_hz"],
            generator["upper_hz"],
            needs["required_lower_hz"],
            needs["required_upper_hz"],
        )
        checks["generator"] = span
        if not span["covers"]:
            findings.append(
                _finding(
                    "generator-span-short",
                    generator["id"],
                    "tunes %.6g to %.6g Hz against a required %.6g to %.6g Hz"
                    % (
                        span["lower_hz"],
                        span["upper_hz"],
                        span["required_lower_hz"],
                        span["required_upper_hz"],
                    ),
                )
            )
    amplifier = by_role.get("amplifier")
    if amplifier is not None:
        span = check_generator_span(
            amplifier["lower_hz"],
            amplifier["upper_hz"],
            needs["required_lower_hz"],
            needs["required_upper_hz"],
        )
        power = check_amplifier(amplifier["rated_power_w"], required_power)
        checks["amplifier"] = power
        checks["amplifier_span"] = span
        if not span["covers"]:
            findings.append(
                _finding(
                    "amplifier-span-short",
                    amplifier["id"],
                    "passes %.6g to %.6g Hz against a required %.6g to %.6g Hz"
                    % (
                        span["lower_hz"],
                        span["upper_hz"],
                        span["required_lower_hz"],
                        span["required_upper_hz"],
                    ),
                )
            )
        if not power["sufficient"]:
            findings.append(
                _finding(
                    "amplifier-underpowered",
                    amplifier["id"],
                    "rated %.4f W against the %.4f W the chain needs"
                    % (power["rated_w"], power["required_w"]),
                )
            )
    resistor = by_role.get("injection-resistor")
    if resistor is not None:
        series = check_injection_resistor(
            resistor["resistance_ohm"],
            resistor["inductance_h"],
            resistor["rating_w"],
            needs["lead_current_a"],
            needs["required_upper_hz"],
        )
        checks["injection-resistor"] = series
        if not series["low_inductance"]:
            findings.append(
                _finding(
                    "resistor-not-low-inductance",
                    resistor["id"],
                    "shows %.4f ohm of reactance at %.6g Hz, a ratio of %.4f "
                    "against a %.4f limit"
                    % (
                        series["reactance_ohm"],
                        series["top_frequency_hz"],
                        series["reactance_ratio"],
                        series["ratio_limit"],
                    ),
                )
            )
        if not series["power_within"]:
            findings.append(
                _finding(
                    "resistor-over-dissipation",
                    resistor["id"],
                    "dissipates %.4f W against a derated %.4f W"
                    % (series["dissipated_w"], series["allowed_w"]),
                )
            )
    ready = not findings
    return {
        "verdict": "chain-ready" if ready else "chain-not-ready",
        "ready": ready,
        "required_power_w": required_power,
        "roles_present": tuple(role for role in ITEM_ROLES if role in by_role),
        "item_count": len(normalized),
        "checks": checks,
        "findings": findings,
        "items": normalized,
    }
