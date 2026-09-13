#!/usr/bin/env python3
"""Corona design and verification for radio-frequency chain hardware.

Anchor: ECSS-E-ST-20C clause 7.3.3.2 (paraphrased into an implementable
procedure; no standard text is reproduced).

Clause 7.3.3.1 asks for freedom from discharge. Clause 7.3.3.2 says how that
freedom is designed in and how it is shown, and it ties the size of the
required headroom to the strength of the evidence offered:

* The design side converts the onset voltage a geometry can stand into an
  onset power, raises the applied peak voltage for the mismatch the item
  really presents, and states the headroom between the two in decibels.
* The verification side categorizes the route -- a measurement on
  flight-standard hardware, a measurement on a representative model, a
  numerical prediction, or an argument from heritage -- and applies the
  allowance that route earns. A weaker route earns a larger allowance.
* An allowance relaxed below the route's default is only usable when the
  agreement that relaxed it is on record, and a measurement route only
  produces evidence when a seed-electron source and a discharge detection
  method were present and the sweep actually crossed the critical pressure
  band.

Stdlib only, offline, deterministic.
"""

import math

# Verification routes, the default headroom each earns, and what a route has
# to have in place before its result counts as evidence.
VERIFICATION_ROUTES = {
    "flight-standard-test": {
        "default_allowance_db": 3.0,
        "evidence_strength": 3,
        "needs_detection": True,
        "needs_seeding": True,
    },
    "representative-model-test": {
        "default_allowance_db": 4.5,
        "evidence_strength": 2,
        "needs_detection": True,
        "needs_seeding": True,
    },
    "numerical-analysis": {
        "default_allowance_db": 6.0,
        "evidence_strength": 1,
        "needs_detection": False,
        "needs_seeding": False,
    },
    "heritage-similarity": {
        "default_allowance_db": 8.0,
        "evidence_strength": 0,
        "needs_detection": False,
        "needs_seeding": False,
    },
}

ROUTE_ALIASES = {
    "flight-model-test": "flight-standard-test",
    "qualification-model-test": "representative-model-test",
    "engineering-model-test": "representative-model-test",
    "simulation": "numerical-analysis",
    "heritage": "heritage-similarity",
}

DETECTION_METHODS = (
    "forward-reverse-power-nulling",
    "third-harmonic-detection",
    "optical-emission-detection",
    "electron-current-probe",
)

SEEDING_SOURCES = (
    "radioactive-source",
    "ultraviolet-illumination",
    "electron-gun",
)

# Representation tolerance only. It absorbs floating-point round-off on an
# exactly-compliant comparison; it never relaxes an engineering limit.
COMPARISON_TOLERANCE = 1e-9


def _meets(value, limit):
    """True when value is at or above limit, ULP noise absorbed."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=1e-12, abs_tol=COMPARISON_TOLERANCE)


def categorize_verification_route(route):
    """Resolve a declared verification route to its canonical category."""
    if not isinstance(route, str) or not route.strip():
        raise ValueError("route must be a non-empty string")
    key = route.strip().lower()
    key = ROUTE_ALIASES.get(key, key)
    if key not in VERIFICATION_ROUTES:
        raise ValueError("unrecognized verification route %r" % (route,))
    return key


def route_profile(route):
    """Return a copy of the profile attached to a verification route."""
    return dict(VERIFICATION_ROUTES[categorize_verification_route(route)])


def default_margin_allowance_db(route):
    """Headroom the route earns when nothing else is agreed."""
    return route_profile(route)["default_allowance_db"]


def resolve_margin_allowance_db(route, agreed_allowance_db=None, agreement_reference=None):
    """Settle the allowance in force for one item.

    An agreed allowance at or above the route default stands on its own. An
    agreed allowance below the default is a relaxation and needs the
    agreement that granted it on record.
    """
    category = categorize_verification_route(route)
    default_db = VERIFICATION_ROUTES[category]["default_allowance_db"]
    findings = []
    if agreed_allowance_db is None:
        return {
            "route": category,
            "allowance_db": default_db,
            "default_db": default_db,
            "relaxed": False,
            "findings": findings,
        }
    if agreed_allowance_db < 0.0:
        raise ValueError("agreed_allowance_db must be >= 0")
    relaxed = agreed_allowance_db < default_db and not math.isclose(
        agreed_allowance_db, default_db, rel_tol=1e-12, abs_tol=COMPARISON_TOLERANCE
    )
    if relaxed and not agreement_reference:
        findings.append(
            "allowance relaxed from %.2f dB to %.2f dB with no agreement on record"
            % (default_db, agreed_allowance_db)
        )
    return {
        "route": category,
        "allowance_db": agreed_allowance_db,
        "default_db": default_db,
        "relaxed": relaxed,
        "findings": findings,
    }


def reflection_coefficient(vswr):
    """Voltage reflection coefficient magnitude of a declared mismatch."""
    if vswr < 1.0:
        raise ValueError("vswr must be >= 1.0")
    return (vswr - 1.0) / (vswr + 1.0)


def applied_peak_voltage_v(power_w, impedance_ohm, vswr=1.0):
    """Peak voltage the standing wave presents across the critical gap."""
    if power_w <= 0.0:
        raise ValueError("power_w must be > 0")
    if impedance_ohm <= 0.0:
        raise ValueError("impedance_ohm must be > 0")
    matched_peak = math.sqrt(2.0 * power_w * impedance_ohm)
    return matched_peak * (1.0 + reflection_coefficient(vswr))


def corona_onset_power_w(onset_voltage_v, impedance_ohm):
    """Power that corresponds to a measured or predicted onset voltage."""
    if onset_voltage_v <= 0.0:
        raise ValueError("onset_voltage_v must be > 0")
    if impedance_ohm <= 0.0:
        raise ValueError("impedance_ohm must be > 0")
    return onset_voltage_v ** 2 / (2.0 * impedance_ohm)


def corona_margin_db(onset_voltage_v, applied_voltage_v):
    """Headroom in decibels between onset and applied peak voltage."""
    if onset_voltage_v <= 0.0:
        raise ValueError("onset_voltage_v must be > 0")
    if applied_voltage_v <= 0.0:
        raise ValueError("applied_voltage_v must be > 0")
    return 20.0 * math.log10(onset_voltage_v / applied_voltage_v)


def required_onset_voltage_v(power_w, impedance_ohm, vswr, allowance_db):
    """Onset voltage the geometry has to reach to satisfy the allowance."""
    if allowance_db < 0.0:
        raise ValueError("allowance_db must be >= 0")
    applied = applied_peak_voltage_v(power_w, impedance_ohm, vswr)
    return applied * 10.0 ** (allowance_db / 20.0)


def critical_band_covered(verification_band_pa, critical_band_pa):
    """Check that the verification sweep crossed the whole critical band."""
    for name, band in (
        ("verification_band_pa", verification_band_pa),
        ("critical_band_pa", critical_band_pa),
    ):
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("%s must be a (low, high) pair" % name)
        if band[0] <= 0.0:
            raise ValueError("%s low edge must be > 0" % name)
        if band[1] < band[0]:
            raise ValueError("%s high edge must be >= low edge" % name)
    swept_low, swept_high = verification_band_pa
    critical_low, critical_high = critical_band_pa
    uncovered = []
    if swept_low > critical_low:
        uncovered.append((critical_low, min(swept_low, critical_high)))
    if swept_high < critical_high:
        uncovered.append((max(swept_high, critical_low), critical_high))
    return {"covered": not uncovered, "uncovered": uncovered}


def evaluate_corona_item(item, required_keys=("id", "applied_power_w", "impedance_ohm", "onset_voltage_v", "route")):
    """Design-and-verification check for one radio-frequency chain item."""
    for key in required_keys:
        if key not in item:
            raise ValueError("item missing required key %r" % (key,))
    allowance = resolve_margin_allowance_db(
        item["route"],
        item.get("agreed_allowance_db"),
        item.get("agreement_reference"),
    )
    profile = VERIFICATION_ROUTES[allowance["route"]]
    findings = list(allowance["findings"])

    applied_voltage = applied_peak_voltage_v(
        item["applied_power_w"], item["impedance_ohm"], item.get("vswr", 1.0)
    )
    onset_voltage = item["onset_voltage_v"]
    margin = corona_margin_db(onset_voltage, applied_voltage)
    compliant_margin = _meets(margin, allowance["allowance_db"])
    if not compliant_margin:
        findings.append(
            "%s: corona margin %.2f dB below the %.2f dB allowance of route %s"
            % (item["id"], margin, allowance["allowance_db"], allowance["route"])
        )

    if profile["needs_detection"]:
        method = item.get("detection_method")
        if not method:
            findings.append("%s: measurement route with no detection method on record" % item["id"])
        elif method not in DETECTION_METHODS:
            findings.append("%s: unrecognized detection method %r" % (item["id"], method))
    if profile["needs_seeding"]:
        seeding = item.get("seeding_source")
        if not seeding:
            findings.append(
                "%s: measurement route with no seed-electron source; a null result is not evidence"
                % item["id"]
            )
        elif seeding not in SEEDING_SOURCES:
            findings.append("%s: unrecognized seed-electron source %r" % (item["id"], seeding))

    coverage = None
    if profile["needs_detection"]:
        if "verification_band_pa" not in item or "critical_band_pa" not in item:
            findings.append("%s: measurement route with no pressure sweep on record" % item["id"])
        else:
            coverage = critical_band_covered(
                item["verification_band_pa"], item["critical_band_pa"]
            )
            if not coverage["covered"]:
                findings.append(
                    "%s: pressure sweep leaves %d critical sub-band(s) unexercised"
                    % (item["id"], len(coverage["uncovered"]))
                )

    return {
        "id": item["id"],
        "route": allowance["route"],
        "evidence_strength": profile["evidence_strength"],
        "allowance_db": allowance["allowance_db"],
        "applied_voltage_v": applied_voltage,
        "onset_voltage_v": onset_voltage,
        "onset_power_w": corona_onset_power_w(onset_voltage, item["impedance_ohm"]),
        "required_onset_voltage_v": required_onset_voltage_v(
            item["applied_power_w"],
            item["impedance_ohm"],
            item.get("vswr", 1.0),
            allowance["allowance_db"],
        ),
        "margin_db": margin,
        "coverage": coverage,
        "findings": findings,
        "compliant": not findings,
    }


def assess_corona_design(items):
    """Roll one chain's items up into a clause 7.3.3.2 verdict."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    seen = set()
    evaluations = []
    for item in items:
        evaluation = evaluate_corona_item(item)
        if evaluation["id"] in seen:
            raise ValueError("item %r appears more than once" % (evaluation["id"],))
        seen.add(evaluation["id"])
        evaluations.append(evaluation)
    findings = []
    for evaluation in evaluations:
        findings.extend(evaluation["findings"])
    margins = [evaluation["margin_db"] for evaluation in evaluations]
    weakest = min(evaluations, key=lambda evaluation: evaluation["margin_db"])
    return {
        "items": evaluations,
        "worst_margin_db": min(margins),
        "driving_item": weakest["id"],
        "weakest_evidence_strength": min(
            evaluation["evidence_strength"] for evaluation in evaluations
        ),
        "findings": findings,
        "compliant": not findings,
    }
