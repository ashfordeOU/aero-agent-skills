#!/usr/bin/env python3
"""System-level verification of the required lightning protection.

Anchor: ECSS-E-ST-20-07C clause 5.3.4 (confirmation, at system level,
that the required protection against lightning effects is achieved).
The clause is paraphrased into an implementable procedure; no standard
text is reproduced.

Model used throughout:
  attachment zoning -> each exposed surface sits in a lightning
                       attachment zone, and the zone fixes which current
                       waveform components the surface must survive
  direct effects    -> closure of a zoned surface by an admissible
                       verification method, inspection alone never being
                       one of them inside an attachment zone
  indirect effects  -> the transient control level induced on a circuit
                       against the equipment transient design level, the
                       difference taken as a decibel margin
  system verdict    -> the case closes only when every surface is closed
                       and every circuit holds its required margin

Stdlib only, deterministic, offline.
"""

import math

# --- attachment zones -------------------------------------------------------

ZONE_1A = "zone-1a"
ZONE_1B = "zone-1b"
ZONE_1C = "zone-1c"
ZONE_2A = "zone-2a"
ZONE_2B = "zone-2b"
ZONE_3 = "zone-3"

ATTACHMENT_ZONES = (ZONE_1A, ZONE_1B, ZONE_1C, ZONE_2A, ZONE_2B, ZONE_3)

ZONE_ALIASES = {
    "zone-1a": ZONE_1A,
    "1a": ZONE_1A,
    "initial-attachment-low-dwell": ZONE_1A,
    "zone-1b": ZONE_1B,
    "1b": ZONE_1B,
    "initial-attachment-with-dwell": ZONE_1B,
    "zone-1c": ZONE_1C,
    "1c": ZONE_1C,
    "initial-attachment-reduced-current": ZONE_1C,
    "zone-2a": ZONE_2A,
    "2a": ZONE_2A,
    "swept-stroke-low-dwell": ZONE_2A,
    "zone-2b": ZONE_2B,
    "2b": ZONE_2B,
    "swept-stroke-with-dwell": ZONE_2B,
    "zone-3": ZONE_3,
    "3": ZONE_3,
    "conduction-only": ZONE_3,
}

# Waveform components each zone owes, paraphrased: A first return stroke,
# B intermediate current, C continuing current, C-reduced a shortened
# continuing current, D restrike, A-reduced a reduced first stroke.
ZONE_COMPONENTS = {
    ZONE_1A: ("a", "b", "c-reduced", "d"),
    ZONE_1B: ("a", "b", "c", "d"),
    ZONE_1C: ("a-reduced", "b", "c-reduced", "d"),
    ZONE_2A: ("b", "c-reduced", "d"),
    ZONE_2B: ("b", "c", "d"),
    ZONE_3: ("a", "c"),
}

# --- verification methods ---------------------------------------------------

VERIFICATION_METHODS = ("test", "analysis", "similarity", "inspection", "review-of-design")

METHOD_ALIASES = {
    "test": "test",
    "testing": "test",
    "analysis": "analysis",
    "analytical": "analysis",
    "similarity": "similarity",
    "heritage": "similarity",
    "inspection": "inspection",
    "visual-inspection": "inspection",
    "review-of-design": "review-of-design",
    "rod": "review-of-design",
}

EFFECT_DIRECT = "direct-effects"
EFFECT_INDIRECT = "indirect-effects"
EFFECT_KINDS = (EFFECT_DIRECT, EFFECT_INDIRECT)

EFFECT_ALIASES = {
    "direct-effects": EFFECT_DIRECT,
    "direct": EFFECT_DIRECT,
    "attachment-effects": EFFECT_DIRECT,
    "indirect-effects": EFFECT_INDIRECT,
    "indirect": EFFECT_INDIRECT,
    "coupled-transients": EFFECT_INDIRECT,
}

# Inside an attachment zone a direct-effects requirement is closed only by
# arc-current evidence; outside one, conduction can be argued analytically.
ADMISSIBLE_IN_ATTACHMENT_ZONE = ("test", "similarity")
ADMISSIBLE_OUTSIDE_ATTACHMENT_ZONE = ("test", "similarity", "analysis")
ADMISSIBLE_FOR_INDIRECT = ("test", "analysis", "similarity")

DEFAULT_REQUIRED_MARGIN_DB = 6.0
MARGIN_TOLERANCE_DB = 1e-9


def _finite_number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric" % label)
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    return value


# --- zoning -----------------------------------------------------------------


def attachment_zone(raw_zone):
    """Resolve a declared lightning attachment zone to its canonical name."""
    key = str(raw_zone).strip().lower()
    if not key:
        raise ValueError("attachment zone must not be blank")
    if key not in ZONE_ALIASES:
        raise ValueError("unrecognised attachment zone: %r" % (raw_zone,))
    return ZONE_ALIASES[key]


def is_attachment_zone(raw_zone):
    """True for a zone where an arc can attach or be swept across."""
    return attachment_zone(raw_zone) != ZONE_3


def zone_current_components(raw_zone):
    """Waveform components a surface in this zone must survive."""
    return ZONE_COMPONENTS[attachment_zone(raw_zone)]


def zone_requires_dwell_component(raw_zone):
    """True when the zone carries a full continuing current, not a shortened one."""
    return "c" in zone_current_components(raw_zone)


# --- methods ----------------------------------------------------------------


def verification_method(raw_method):
    """Resolve a declared verification method to its canonical name."""
    key = str(raw_method).strip().lower()
    if not key:
        raise ValueError("verification method must not be blank")
    if key not in METHOD_ALIASES:
        raise ValueError("unrecognised verification method: %r" % (raw_method,))
    return METHOD_ALIASES[key]


def effect_kind(raw_effect):
    """Resolve a declared lightning effect kind."""
    key = str(raw_effect).strip().lower()
    if not key:
        raise ValueError("effect kind must not be blank")
    if key not in EFFECT_ALIASES:
        raise ValueError("unrecognised effect kind: %r" % (raw_effect,))
    return EFFECT_ALIASES[key]


def admissible_methods(raw_effect, raw_zone):
    """Methods that may close a requirement of this kind in this zone."""
    kind = effect_kind(raw_effect)
    if kind == EFFECT_INDIRECT:
        return ADMISSIBLE_FOR_INDIRECT
    if is_attachment_zone(raw_zone):
        return ADMISSIBLE_IN_ATTACHMENT_ZONE
    return ADMISSIBLE_OUTSIDE_ATTACHMENT_ZONE


def methods_close_requirement(raw_effect, raw_zone, raw_methods):
    """True when at least one declared method is admissible here."""
    if not isinstance(raw_methods, (list, tuple, set, frozenset)):
        raise ValueError("declared methods must be a list, tuple or set")
    if not raw_methods:
        raise ValueError("at least one verification method must be declared")
    allowed = set(admissible_methods(raw_effect, raw_zone))
    declared = set(verification_method(m) for m in raw_methods)
    return bool(declared & allowed)


# --- indirect effects -------------------------------------------------------


def transient_control_level_v(measured_transient_v, measurement_uncertainty_db):
    """Raise a measured transient by its measurement uncertainty."""
    measured = _finite_number(measured_transient_v, "measured transient")
    if measured <= 0.0:
        raise ValueError("measured transient must be positive")
    uncertainty = _finite_number(
        measurement_uncertainty_db, "measurement uncertainty"
    )
    if uncertainty < 0.0:
        raise ValueError("measurement uncertainty must not be negative")
    return measured * (10.0 ** (uncertainty / 20.0))


def lightning_margin_db(design_level_v, control_level_v):
    """Decibel margin of the equipment design level over the control level."""
    design = _finite_number(design_level_v, "equipment design level")
    if design <= 0.0:
        raise ValueError("equipment design level must be positive")
    control = _finite_number(control_level_v, "transient control level")
    if control <= 0.0:
        raise ValueError("transient control level must be positive")
    return 20.0 * math.log10(design / control)


def meets_required_margin_db(
    achieved_db, required_db=DEFAULT_REQUIRED_MARGIN_DB, tolerance=MARGIN_TOLERANCE_DB
):
    """True when an achieved margin reaches the required one.

    The achieved margin runs through a base-ten logarithm, which is not
    correctly rounded and does not round identically on every platform,
    so an exactly compliant circuit can land a unit in the last place
    below the requirement. The representation error is absorbed here;
    the required margin itself is never lowered.
    """
    achieved = _finite_number(achieved_db, "achieved margin")
    required = _finite_number(required_db, "required margin")
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative")
    return achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=tolerance
    )


def circuit_margin_report(circuit, required_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Margin verdict for one victim circuit."""
    if not isinstance(circuit, dict):
        raise ValueError("circuit record must be a mapping")
    circuit_id = str(circuit.get("id", "")).strip()
    if not circuit_id:
        raise ValueError("circuit record must carry a non-blank id")
    control = transient_control_level_v(
        circuit.get("measured_transient_v"),
        circuit.get("measurement_uncertainty_db", 0.0),
    )
    design = _finite_number(
        circuit.get("equipment_design_level_v"), "equipment design level"
    )
    margin = lightning_margin_db(design, control)
    return {
        "id": circuit_id,
        "control_level_v": control,
        "design_level_v": design,
        "margin_db": margin,
        "meets_margin": meets_required_margin_db(margin, required_db),
    }


# --- surfaces ---------------------------------------------------------------


def surface_closure_report(surface):
    """Closure verdict for one zoned external surface."""
    if not isinstance(surface, dict):
        raise ValueError("surface record must be a mapping")
    surface_id = str(surface.get("id", "")).strip()
    if not surface_id:
        raise ValueError("surface record must carry a non-blank id")
    zone = attachment_zone(surface.get("zone"))
    kind = effect_kind(surface.get("effect", EFFECT_DIRECT))
    raw_methods = surface.get("methods")
    if not isinstance(raw_methods, (list, tuple, set, frozenset)) or not raw_methods:
        raise ValueError("surface %s declares no verification method" % surface_id)
    methods = tuple(verification_method(m) for m in raw_methods)
    closed = methods_close_requirement(kind, zone, methods)
    return {
        "id": surface_id,
        "zone": zone,
        "effect": kind,
        "components": zone_current_components(zone),
        "methods": methods,
        "admissible_methods": admissible_methods(kind, zone),
        "closed": closed,
    }


# --- top-level verification -------------------------------------------------


def verify_lightning_protection(config):
    """Run the clause 5.3.4 system-level lightning protection verification."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    surfaces = config.get("surfaces")
    if not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError("at least one zoned surface record is required")
    circuits = config.get("circuits")
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("at least one victim circuit record is required")
    required_db = _finite_number(
        config.get("required_margin_db", DEFAULT_REQUIRED_MARGIN_DB),
        "required margin",
    )

    surface_reports = [surface_closure_report(s) for s in surfaces]
    circuit_reports = [circuit_margin_report(c, required_db) for c in circuits]

    covered_zones = set(r["zone"] for r in surface_reports)
    declared_zones = config.get("declared_zones")
    if declared_zones is None:
        missing = ()
    else:
        if not isinstance(declared_zones, (list, tuple, set, frozenset)):
            raise ValueError("declared zones must be a list, tuple or set")
        wanted = set(attachment_zone(z) for z in declared_zones)
        missing = tuple(z for z in ATTACHMENT_ZONES if z in wanted - covered_zones)

    findings = []
    for zone in missing:
        findings.append("zone-not-verified:%s" % zone)
    for report in surface_reports:
        if not report["closed"]:
            findings.append("inadmissible-method:%s" % report["id"])
    worst = None
    for report in circuit_reports:
        if not report["meets_margin"]:
            findings.append("lightning-margin-shortfall:%s" % report["id"])
        if worst is None or report["margin_db"] < worst["margin_db"]:
            worst = report

    return {
        "required_margin_db": required_db,
        "surfaces": tuple(surface_reports),
        "circuits": tuple(circuit_reports),
        "covered_zones": tuple(z for z in ATTACHMENT_ZONES if z in covered_zones),
        "unverified_zones": missing,
        "worst_circuit": worst["id"],
        "worst_margin_db": worst["margin_db"],
        "findings": tuple(findings),
        "acceptable": not findings,
    }
