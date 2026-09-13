#!/usr/bin/env python3
"""ESD-related EMI control assessment - ECSS-E-ST-20-07C clause 4.2.4.2.

Deterministic, offline, standard-library-only helpers that turn the
electrostatic-discharge interference-control provisions of clause 4.2.4.2
into a checkable procedure:

  1. categorize a discharge event into its family,
  2. size the arc-discharge pulse it delivers,
  3. couple that pulse onto a victim harness through the shield surface
     transfer-impedance,
  4. compare the coupled transient against the victim susceptibility
     threshold with a declared emi-margin, and
  5. confirm the family-specific interference-control provisions are on
     record.

No verbatim standard text is reproduced; the clause is cited as an anchor
only.
"""

import math

__all__ = [
    "EVENT_FAMILIES",
    "REQUIRED_PROVISIONS",
    "DEFAULT_REQUIRED_MARGIN_DB",
    "categorize_event",
    "arc_pulse",
    "coupled_transient_voltage",
    "emi_margin_db",
    "check_transient_compatibility",
    "missing_provisions",
    "assess_event",
    "assess_esd_emi_control",
    "worst_case_record",
]

# Event kind -> interference event family (clause 4.2.4.2 scope).
EVENT_FAMILIES = {
    "surface-arc": "surface-charging-arc",
    "dielectric-surface-arc": "surface-charging-arc",
    "differential-charging-arc": "surface-charging-arc",
    "blow-off-discharge": "surface-charging-arc",
    "internal-arc": "internal-charging-arc",
    "deep-dielectric-arc": "internal-charging-arc",
    "buried-charge-arc": "internal-charging-arc",
    "triboelectric-separation": "triboelectric-separation-event",
    "deployment-separation": "triboelectric-separation-event",
    "release-mechanism-separation": "triboelectric-separation-event",
    "human-body-model": "ground-handling-event",
    "machine-model": "ground-handling-event",
    "charged-device-model": "ground-handling-event",
}

# Family -> interference-control provisions that must be on record.
REQUIRED_PROVISIONS = {
    "surface-charging-arc": (
        "surface-conductivity-control",
        "chassis-bonding",
        "shield-termination",
    ),
    "internal-charging-arc": (
        "dielectric-shielding-control",
        "chassis-bonding",
        "transient-filtering",
    ),
    "triboelectric-separation-event": (
        "static-dissipative-material",
        "chassis-bonding",
    ),
    "ground-handling-event": (
        "controlled-handling-area",
        "operator-bonding",
        "transient-filtering",
    ),
}

DEFAULT_REQUIRED_MARGIN_DB = 6.0

# The comparison tolerance absorbs floating-point representation error at an
# exactly on-limit result. It never widens the engineering requirement.
MARGIN_REL_TOL = 1e-9
MARGIN_ABS_TOL = 1e-9

# Decay fraction used to define the usable pulse duration of an RC arc.
_DECAY_FRACTION = 0.1

_EVENT_KEYS = (
    "id",
    "kind",
    "capacitance_f",
    "breakdown_voltage_v",
    "arc_resistance_ohm",
    "provisions",
    "victim",
)
_VICTIM_KEYS = (
    "id",
    "transfer_impedance_ohm_per_m",
    "exposed_length_m",
    "shield_effectiveness_db",
    "susceptibility_threshold_v",
)


def _as_finite_float(value, label):
    """Coerce value to a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_finite_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _as_finite_float(value, label)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return out


def _require_keys(mapping, keys, context):
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping, got %r" % (context, type(mapping).__name__))
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ValueError("%s missing required key(s): %s" % (context, ", ".join(missing)))


def categorize_event(event_kind):
    """Return the interference event family for an ESD event kind."""
    if not isinstance(event_kind, str):
        raise ValueError("event kind must be a string, got %r" % (event_kind,))
    key = event_kind.strip().lower()
    if not key:
        raise ValueError("event kind must not be empty")
    if key not in EVENT_FAMILIES:
        raise ValueError(
            "uncategorized ESD event kind %r; known kinds: %s"
            % (event_kind, ", ".join(sorted(EVENT_FAMILIES)))
        )
    return EVENT_FAMILIES[key]


def arc_pulse(capacitance_f, breakdown_voltage_v, arc_resistance_ohm):
    """Size a capacitive arc discharge into its EMI-relevant pulse figures."""
    cap = _positive(capacitance_f, "capacitance_f")
    volt = _positive(breakdown_voltage_v, "breakdown_voltage_v")
    res = _positive(arc_resistance_ohm, "arc_resistance_ohm")
    tau = res * cap
    peak_current = volt / res
    duration = tau * math.log(1.0 / _DECAY_FRACTION)
    return {
        "peak_current_a": peak_current,
        "transferred_charge_c": cap * volt,
        "stored_energy_j": 0.5 * cap * volt * volt,
        "time_constant_s": tau,
        "pulse_duration_s": duration,
        "corner_frequency_hz": 1.0 / (2.0 * math.pi * tau),
    }


def coupled_transient_voltage(
    peak_current_a,
    transfer_impedance_ohm_per_m,
    exposed_length_m,
    shield_effectiveness_db=0.0,
):
    """Couple an arc pulse onto a victim harness through its shield."""
    current = _positive(peak_current_a, "peak_current_a")
    z_t = _positive(transfer_impedance_ohm_per_m, "transfer_impedance_ohm_per_m")
    length = _positive(exposed_length_m, "exposed_length_m")
    s_e = _non_negative(shield_effectiveness_db, "shield_effectiveness_db")
    open_circuit_v = current * z_t * length
    return open_circuit_v / (10.0 ** (s_e / 20.0))


def emi_margin_db(susceptibility_threshold_v, coupled_voltage_v):
    """Decibel ratio of the victim threshold to the coupled transient."""
    threshold = _positive(susceptibility_threshold_v, "susceptibility_threshold_v")
    coupled = _positive(coupled_voltage_v, "coupled_voltage_v")
    return 20.0 * math.log10(threshold / coupled)


def check_transient_compatibility(
    susceptibility_threshold_v,
    coupled_voltage_v,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Compare the achieved emi-margin against the declared requirement."""
    required = _as_finite_float(required_margin_db, "required_margin_db")
    if required < 0.0:
        raise ValueError("required_margin_db must be >= 0, got %r" % (required_margin_db,))
    achieved = emi_margin_db(susceptibility_threshold_v, coupled_voltage_v)
    compliant = achieved >= required or math.isclose(
        achieved, required, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
    )
    shortfall = 0.0 if compliant else required - achieved
    return {
        "achieved_margin_db": achieved,
        "required_margin_db": required,
        "compliant": compliant,
        "shortfall_db": shortfall,
    }


def missing_provisions(family, provisions_on_record):
    """List the family-specific provisions that are not on record."""
    if family not in REQUIRED_PROVISIONS:
        raise ValueError(
            "unknown event family %r; known families: %s"
            % (family, ", ".join(sorted(REQUIRED_PROVISIONS)))
        )
    if isinstance(provisions_on_record, str) or not hasattr(provisions_on_record, "__iter__"):
        raise ValueError(
            "provisions_on_record must be an iterable of strings, got %r"
            % (provisions_on_record,)
        )
    recorded = set()
    for item in provisions_on_record:
        if not isinstance(item, str):
            raise ValueError("provision entry must be a string, got %r" % (item,))
        recorded.add(item.strip().lower())
    return tuple(p for p in REQUIRED_PROVISIONS[family] if p not in recorded)


def assess_event(event, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Assess one ESD exposure end to end and return its record."""
    _require_keys(event, _EVENT_KEYS, "event")
    victim = event["victim"]
    _require_keys(victim, _VICTIM_KEYS, "event %r victim" % (event["id"],))
    family = categorize_event(event["kind"])
    pulse = arc_pulse(
        event["capacitance_f"],
        event["breakdown_voltage_v"],
        event["arc_resistance_ohm"],
    )
    coupled_v = coupled_transient_voltage(
        pulse["peak_current_a"],
        victim["transfer_impedance_ohm_per_m"],
        victim["exposed_length_m"],
        victim["shield_effectiveness_db"],
    )
    compat = check_transient_compatibility(
        victim["susceptibility_threshold_v"], coupled_v, required_margin_db
    )
    gaps = missing_provisions(family, event["provisions"])
    findings = []
    if not compat["compliant"]:
        findings.append(
            "event %s couples %.4g V into victim %s, %.3f dB short of the "
            "required emi-margin" % (event["id"], coupled_v, victim["id"], compat["shortfall_db"])
        )
    for gap in gaps:
        findings.append(
            "event %s (%s) has no %s provision on record" % (event["id"], family, gap)
        )
    return {
        "event_id": event["id"],
        "family": family,
        "victim_id": victim["id"],
        "pulse": pulse,
        "coupled_voltage_v": coupled_v,
        "margin": compat,
        "missing_provisions": gaps,
        "findings": tuple(findings),
        "compliant": compat["compliant"] and not gaps,
    }


def worst_case_record(records):
    """Return the record with the lowest achieved emi-margin."""
    if not records:
        raise ValueError("records must be a non-empty sequence")
    return min(records, key=lambda r: r["margin"]["achieved_margin_db"])


def assess_esd_emi_control(events, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Assess every ESD exposure and aggregate the clause 4.2.4.2 verdict."""
    if isinstance(events, dict) or not hasattr(events, "__iter__"):
        raise ValueError("events must be an iterable of event mappings")
    items = list(events)
    if not items:
        raise ValueError("events must not be empty; an assessment needs at least one exposure")
    seen = set()
    records = []
    for event in items:
        _require_keys(event, _EVENT_KEYS, "event")
        event_id = event["id"]
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event id must be a non-empty string, got %r" % (event_id,))
        if event_id in seen:
            raise ValueError("duplicate event id %r" % (event_id,))
        seen.add(event_id)
        records.append(assess_event(event, required_margin_db))
    findings = []
    for record in records:
        findings.extend(record["findings"])
    driver = worst_case_record(records)
    return {
        "records": tuple(records),
        "findings": tuple(findings),
        "compliant": not findings,
        "event_count": len(records),
        "driving_event_id": driver["event_id"],
        "worst_margin_db": driver["margin"]["achieved_margin_db"],
    }
