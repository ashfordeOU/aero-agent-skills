"""Repair planning for printed-circuit-board assemblies.

Anchor: ECSS-Q-ST-70-28C, programme clause -- once a repair is authorized, the
method, the consumables and the risk are settled on paper before the operator
starts, so that the bench is executing a plan rather than improvising one.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Select a repair method from the catalogue for the damage category, refusing
   a method whose damage-extent limit the damage exceeds.
2. Check each consumable: still inside shelf life at the planned date, and a
   process temperature the board construction can take.
3. Count the rework cycles the location has already taken against the budget a
   land or a hole survives.
4. Score the risk from criticality, accessibility and thermal exposure, place
   it in a band, and call for a trial coupon where the band demands one.
5. Return the plan with every finding that would send it back.
"""

import datetime
import math

__all__ = [
    "METHOD_CATALOGUE",
    "BOARD_MAX_PROCESS_TEMPERATURE_C",
    "MAX_REWORK_CYCLES",
    "CRITICALITY_FACTOR",
    "ACCESSIBILITY_FACTOR",
    "THERMAL_EXPOSURE_FACTOR",
    "RISK_BAND_BOUNDS",
    "COUPON_REQUIRED_BANDS",
    "TEMPERATURE_TOLERANCE_C",
    "RISK_TOLERANCE",
    "parse_date",
    "methods_for",
    "select_method",
    "material_findings",
    "rework_cycle_findings",
    "risk_score",
    "risk_band",
    "plan_repair",
]

# Repair methods by damage category. Each entry carries the largest damage
# extent, as a fraction of the feature, that the method still covers.
METHOD_CATALOGUE = {
    "conductor-repair": (
        ("conductor-lap-solder-splice", 0.15),
        ("conductor-jumper-wire", 0.60),
    ),
    "land-repair": (
        ("land-rebond-in-place", 0.25),
        ("replacement-land-epoxy-bond", 0.90),
    ),
    "plated-hole-repair": (
        ("barrel-eyelet", 0.70),
    ),
    "base-material-repair": (
        ("laminate-epoxy-fill", 0.30),
    ),
    "coating-repair": (
        ("coating-local-touch-up", 0.50),
    ),
    "component-replacement": (
        ("hand-solder-replacement", 1.00),
    ),
}

# The highest process temperature each board construction tolerates, in degC.
BOARD_MAX_PROCESS_TEMPERATURE_C = {
    "single-sided": 260.0,
    "double-sided": 260.0,
    "multilayer": 245.0,
    "flexible": 230.0,
    "rigid-flex": 230.0,
}

# Thermal excursions one location survives before the land or barrel is spent.
MAX_REWORK_CYCLES = 3

# Risk drivers. The product of the three is the score.
CRITICALITY_FACTOR = {1: 3.0, 2: 2.0, 3: 1.4, 4: 1.0}
ACCESSIBILITY_FACTOR = {"open": 1.0, "restricted": 1.5, "under-component": 2.2}
THERMAL_EXPOSURE_FACTOR = {"none": 1.0, "single-reflow": 1.3, "repeated-reflow": 1.8}

# Upper bound of each band, walked in order.
RISK_BAND_BOUNDS = (("low", 2.0), ("medium", 5.0), ("high", float("inf")))

# Bands that oblige a trial repair on a coupon before the flight board.
COUPON_REQUIRED_BANDS = ("high",)

# Temperatures and scores are computed quantities; a value on a bound is inside.
TEMPERATURE_TOLERANCE_C = 1e-9
RISK_TOLERANCE = 1e-9


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _fraction(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, number))
    return number


def parse_date(value, label="date"):
    """Return a date from an ISO string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s '%s' is not an ISO date" % (label, value))
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def methods_for(damage_category):
    """Return the catalogue entries available for a damage category."""
    token = _token(damage_category, "damage_category")
    if token not in METHOD_CATALOGUE:
        raise ValueError(
            "no method catalogue for damage category '%s'; triage it first" % token
        )
    return METHOD_CATALOGUE[token]


def select_method(damage_category, damage_extent_fraction, preferred=None):
    """Select the least invasive method whose extent limit covers the damage."""
    entries = methods_for(damage_category)
    extent = _fraction(damage_extent_fraction, "damage_extent_fraction")
    covering = [name for name, limit in entries if extent <= limit + RISK_TOLERANCE]
    if preferred is not None:
        wanted = _token(preferred, "preferred")
        known = dict(entries)
        if wanted not in known:
            raise ValueError(
                "method '%s' is not in the catalogue for '%s'" % (wanted, damage_category)
            )
        if wanted not in covering:
            return {
                "method": None,
                "candidates": covering,
                "finding": "requested method '%s' covers damage up to %g of the feature, "
                "but %g is damaged" % (wanted, known[wanted], extent),
            }
        return {"method": wanted, "candidates": covering, "finding": None}
    if not covering:
        return {
            "method": None,
            "candidates": [],
            "finding": "no catalogued method for '%s' covers damage of %g of the feature"
            % (_token(damage_category, "damage_category"), extent),
        }
    return {"method": covering[0], "candidates": covering, "finding": None}


def material_findings(materials, planned_date, board_type):
    """Grade the consumables for shelf life and process temperature."""
    if not isinstance(materials, (list, tuple)):
        raise ValueError("materials must be a list of mappings")
    planned = parse_date(planned_date, "planned_date")
    board = _token(board_type, "board_type")
    if board not in BOARD_MAX_PROCESS_TEMPERATURE_C:
        raise ValueError("unknown board_type '%s'" % board)
    ceiling = BOARD_MAX_PROCESS_TEMPERATURE_C[board]

    findings = []
    for index, material in enumerate(materials):
        if not isinstance(material, dict):
            raise ValueError("materials[%d] must be a mapping" % index)
        for key in ("name", "expiry_date", "process_temperature_c"):
            if key not in material:
                raise ValueError("materials[%d] missing required key '%s'" % (index, key))
        name = _token(material["name"], "materials[%d].name" % index)
        expiry = parse_date(material["expiry_date"], "materials[%d].expiry_date" % index)
        if expiry < planned:
            findings.append(
                "material '%s' expires on %s, before the planned repair date %s"
                % (name, expiry.isoformat(), planned.isoformat())
            )
        temperature = material["process_temperature_c"]
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
            raise ValueError("materials[%d].process_temperature_c must be a number" % index)
        temperature = float(temperature)
        if not math.isfinite(temperature):
            raise ValueError("materials[%d].process_temperature_c must be finite" % index)
        if temperature > ceiling + TEMPERATURE_TOLERANCE_C:
            findings.append(
                "material '%s' is processed at %g degC, above the %g degC a %s board "
                "takes" % (name, temperature, ceiling, board)
            )
    return findings


def rework_cycle_findings(prior_cycles, planned_cycles=1):
    """Grade the thermal excursions this location will have taken."""
    for label, value in (("prior_cycles", prior_cycles), ("planned_cycles", planned_cycles)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer count, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must be non-negative, got %d" % (label, value))
    if planned_cycles < 1:
        raise ValueError("planned_cycles must be at least 1")
    total = prior_cycles + planned_cycles
    if total > MAX_REWORK_CYCLES:
        return [
            "this location would reach %d thermal excursions, past the %d it survives"
            % (total, MAX_REWORK_CYCLES)
        ]
    return []


def risk_score(criticality, accessibility, thermal_exposure):
    """Return the product of the three risk drivers."""
    if not isinstance(criticality, int) or isinstance(criticality, bool):
        raise ValueError("criticality must be an integer level, got %r" % (criticality,))
    if criticality not in CRITICALITY_FACTOR:
        raise ValueError(
            "criticality must be one of %s, got %d" % (sorted(CRITICALITY_FACTOR), criticality)
        )
    access = _token(accessibility, "accessibility")
    if access not in ACCESSIBILITY_FACTOR:
        raise ValueError("unknown accessibility '%s'" % access)
    thermal = _token(thermal_exposure, "thermal_exposure")
    if thermal not in THERMAL_EXPOSURE_FACTOR:
        raise ValueError("unknown thermal_exposure '%s'" % thermal)
    return (
        CRITICALITY_FACTOR[criticality]
        * ACCESSIBILITY_FACTOR[access]
        * THERMAL_EXPOSURE_FACTOR[thermal]
    )


def risk_band(score):
    """Place a risk score in its band."""
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("score must be a real number, got %r" % (score,))
    value = float(score)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("score must be positive and finite, got %r" % (score,))
    for name, upper in RISK_BAND_BOUNDS:
        if value <= upper + RISK_TOLERANCE:
            return name
    return RISK_BAND_BOUNDS[-1][0]


def plan_repair(request):
    """Build the repair plan for one authorized repair and return its findings.

    request keys: damage_category, damage_extent_fraction, board_type,
    planned_date, criticality, accessibility, thermal_exposure, optional
    preferred_method, materials, prior_rework_cycles and planned_rework_cycles.
    """
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    required = (
        "damage_category",
        "damage_extent_fraction",
        "board_type",
        "planned_date",
        "criticality",
        "accessibility",
        "thermal_exposure",
    )
    for key in required:
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)

    findings = []
    selection = select_method(
        request["damage_category"],
        request["damage_extent_fraction"],
        request.get("preferred_method"),
    )
    if selection["finding"]:
        findings.append(selection["finding"])

    findings.extend(
        material_findings(
            request.get("materials", ()), request["planned_date"], request["board_type"]
        )
    )
    findings.extend(
        rework_cycle_findings(
            request.get("prior_rework_cycles", 0), request.get("planned_rework_cycles", 1)
        )
    )

    score = risk_score(
        request["criticality"], request["accessibility"], request["thermal_exposure"]
    )
    band = risk_band(score)
    coupon = band in COUPON_REQUIRED_BANDS
    if coupon:
        findings.append(
            "risk band '%s' (score %.3f) calls for a trial repair on a coupon before "
            "the flight board" % (band, score)
        )

    return {
        "damage_category": _token(request["damage_category"], "damage_category"),
        "method": selection["method"],
        "candidate_methods": selection["candidates"],
        "board_type": _token(request["board_type"], "board_type"),
        "planned_date": parse_date(request["planned_date"], "planned_date").isoformat(),
        "risk_score": score,
        "risk_band": band,
        "trial_coupon_required": coupon,
        "findings": findings,
        "ready": not findings,
    }
