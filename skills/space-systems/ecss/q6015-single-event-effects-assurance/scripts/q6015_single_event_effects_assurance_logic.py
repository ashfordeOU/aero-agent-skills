"""Single event effects assurance for an equipment's parts.

Anchor: ECSS-Q-ST-60-15C clause 5.3 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Separate the events by what they cost. An upset, a transient or a
   functional interrupt is recoverable, so it is budgeted as a rate.
   A latchup, a burnout or a gate rupture destroys the part, so it is
   not budgeted at all -- it has to be excluded, or mitigated by
   hardware that stops the destruction.
2. Compare the part's linear-energy-transfer threshold with the
   environment. The mission supplies an integral linear-energy-transfer
   spectrum: the flux of particles able to deposit at least a given
   linear energy transfer. A threshold above the spectrum's cut-off
   means no particle in this environment can trigger the event.
3. For a recoverable event, read the integral flux at the threshold,
   multiply by the saturated cross-section and the number of devices,
   divide by whatever mitigation removes, and compare the resulting
   event rate with the budget the system can carry.
4. For a destructive event that is not excluded by threshold, insist
   on mitigation that addresses that event. A latchup needs a current
   limiter that trips below the destructive current and acts inside
   the time the part survives; a burnout or gate rupture needs the
   applied voltage held at or under the voltage the part was shown
   safe at.
5. Aggregate: every event carries its own findings, and the equipment
   is clear only when none of them does.

Stdlib only, offline, deterministic.
"""

import math

SECONDS_PER_DAY = 86400.0

# Event types and whether the event destroys the part.
EVENT_TYPES = {
    "single-event-upset": False,
    "single-event-transient": False,
    "single-event-functional-interrupt": False,
    "single-event-latchup": True,
    "single-event-burnout": True,
    "single-event-gate-rupture": True,
}

MITIGATION_KINDS = (
    "error-detection-and-correction",
    "triple-modular-redundancy",
    "watchdog-reset",
    "latchup-current-limiter",
    "voltage-derating",
    "none",
)

# Which mitigation kinds address which event type.
MITIGATION_FOR_EVENT = {
    "single-event-upset": (
        "error-detection-and-correction",
        "triple-modular-redundancy",
    ),
    "single-event-transient": (
        "triple-modular-redundancy",
        "error-detection-and-correction",
    ),
    "single-event-functional-interrupt": (
        "watchdog-reset",
        "triple-modular-redundancy",
    ),
    "single-event-latchup": ("latchup-current-limiter",),
    "single-event-burnout": ("voltage-derating",),
    "single-event-gate-rupture": ("voltage-derating",),
}

# Multiplier applied to the environment cut-off before a destructive
# event may be declared excluded on threshold alone.
DESTRUCTIVE_LET_MARGIN = 1.0

# An integral spectrum tabulated to its cut-off has fallen a long way
# from its first point. A tabulation that has not is not a spectrum
# carried to its cut-off, and taking the flux above its last point as
# zero would throw away real particles.
MIN_SPECTRUM_FLUX_RATIO = 1000.0

# Rates, currents and voltages are quotients and products of measured
# floats, so a case sitting exactly on a bound can land a few units in
# the last place either side of it.
RELATIVE_TOLERANCE = 1.0e-9

FINDING_RATE_ABOVE_BUDGET = "event-rate-above-budget"
FINDING_NO_MITIGATION = "destructive-event-without-mitigation"
FINDING_WRONG_MITIGATION = "mitigation-kind-does-not-address-event"
FINDING_TRIP_TOO_HIGH = "latchup-trip-current-not-below-destructive-current"
FINDING_TRIP_TOO_SLOW = "latchup-detection-slower-than-survivable-duration"
FINDING_VOLTAGE_TOO_HIGH = "applied-voltage-above-demonstrated-safe-voltage"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def event_is_destructive(event_type):
    """True when an event type destroys the part it happens in."""
    if event_type not in EVENT_TYPES:
        raise ValueError(
            "event_type %r unknown (expected one of %s)"
            % (event_type, ", ".join(sorted(EVENT_TYPES)))
        )
    return EVENT_TYPES[event_type]


def group_events_by_consequence(event_types):
    """Group event types into destructive and recoverable lists."""
    if not isinstance(event_types, (list, tuple)) or not event_types:
        raise ValueError("event_types must be a non-empty sequence")
    destructive = []
    recoverable = []
    for event_type in event_types:
        if event_is_destructive(event_type):
            destructive.append(event_type)
        else:
            recoverable.append(event_type)
    return {"destructive": destructive, "recoverable": recoverable}


def validate_let_spectrum(spectrum):
    """Validate an integral linear-energy-transfer spectrum."""
    if not isinstance(spectrum, (list, tuple)) or len(spectrum) < 2:
        raise ValueError("let spectrum needs at least two points")
    points = []
    previous_let = None
    previous_flux = None
    for index, point in enumerate(spectrum):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("spectrum point %d must be a (let, flux) pair" % index)
        let = _numeric("spectrum point %d let_mev_cm2_mg" % index, point[0])
        flux = _numeric("spectrum point %d integral_flux" % index, point[1])
        if let <= 0.0:
            raise ValueError("spectrum point %d let must be positive" % index)
        if flux <= 0.0:
            raise ValueError("spectrum point %d integral_flux must be positive" % index)
        if previous_let is not None and let <= previous_let:
            raise ValueError("spectrum let values must be strictly ascending")
        if previous_flux is not None and flux >= previous_flux:
            raise ValueError("spectrum integral_flux must fall as let rises")
        previous_let = let
        previous_flux = flux
        points.append((let, flux))
    if points[0][1] < points[-1][1] * MIN_SPECTRUM_FLUX_RATIO:
        raise ValueError(
            "spectrum flux falls by less than a factor of %r across its span, "
            "so it is not tabulated to a cut-off" % (MIN_SPECTRUM_FLUX_RATIO,)
        )
    return tuple(points)


def environment_let_cutoff(spectrum):
    """Highest linear energy transfer the environment is tabulated to."""
    return validate_let_spectrum(spectrum)[-1][0]


def integral_flux_above_let(spectrum, let_mev_cm2_mg):
    """Integral flux of particles above one linear-energy-transfer value."""
    points = validate_let_spectrum(spectrum)
    let = _numeric("let_mev_cm2_mg", let_mev_cm2_mg)
    if let <= 0.0:
        raise ValueError("let_mev_cm2_mg must be positive")
    low = points[0][0]
    high = points[-1][0]
    if let < low:
        raise ValueError(
            "let %r is below the tabulated span starting at %r; obtain "
            "spectrum data covering it rather than extrapolating" % (let, low)
        )
    if let > high:
        return 0.0
    for (l0, f0), (l1, f1) in zip(points, points[1:]):
        if l0 <= let <= l1:
            fraction = (math.log(let) - math.log(l0)) / (math.log(l1) - math.log(l0))
            return math.exp(math.log(f0) + fraction * (math.log(f1) - math.log(f0)))
    return points[-1][1]


def excluded_by_let_threshold(spectrum, let_threshold, margin=DESTRUCTIVE_LET_MARGIN):
    """True when no particle in the environment reaches the threshold."""
    threshold = _numeric("let_threshold", let_threshold)
    if threshold <= 0.0:
        raise ValueError("let_threshold must be positive")
    margin = _numeric("margin", margin)
    if margin <= 0.0:
        raise ValueError("margin must be positive")
    cutoff = environment_let_cutoff(spectrum)
    return threshold >= cutoff * margin * (1.0 - RELATIVE_TOLERANCE)


def event_rate_per_day(
    spectrum,
    let_threshold,
    saturation_cross_section_cm2,
    device_count,
    reduction_factor=1.0,
):
    """Recoverable event rate per day for one device population."""
    cross_section = _numeric(
        "saturation_cross_section_cm2", saturation_cross_section_cm2
    )
    if cross_section <= 0.0:
        raise ValueError("saturation_cross_section_cm2 must be positive")
    if not isinstance(device_count, int) or isinstance(device_count, bool):
        raise ValueError("device_count must be an integer")
    if device_count < 1:
        raise ValueError("device_count must be at least 1")
    reduction = _numeric("reduction_factor", reduction_factor)
    if reduction < 1.0:
        raise ValueError("reduction_factor must be at least 1.0")
    flux = integral_flux_above_let(spectrum, let_threshold)
    return flux * cross_section * device_count * SECONDS_PER_DAY / reduction


def validate_mitigation(mitigation, event_type):
    """Validate a mitigation record and return a normalized copy."""
    event_is_destructive(event_type)
    if mitigation is None:
        return {"kind": "none", "reduction_factor": 1.0}
    if not isinstance(mitigation, dict):
        raise ValueError("mitigation must be a mapping or None")
    kind = mitigation.get("kind", "none")
    if kind not in MITIGATION_KINDS:
        raise ValueError(
            "mitigation kind %r unknown (expected one of %s)"
            % (kind, ", ".join(MITIGATION_KINDS))
        )
    normalized = dict(mitigation)
    normalized["kind"] = kind
    reduction = mitigation.get("reduction_factor", 1.0)
    reduction = _numeric("mitigation reduction_factor", reduction)
    if reduction < 1.0:
        raise ValueError("mitigation reduction_factor must be at least 1.0")
    normalized["reduction_factor"] = reduction
    return normalized


def latchup_mitigation_findings(mitigation):
    """Findings about a latchup current limiter."""
    trip = _numeric("mitigation trip_current_a", mitigation.get("trip_current_a"))
    destructive = _numeric(
        "mitigation destructive_current_a", mitigation.get("destructive_current_a")
    )
    detection = _numeric(
        "mitigation detection_time_s", mitigation.get("detection_time_s")
    )
    survivable = _numeric(
        "mitigation survivable_duration_s", mitigation.get("survivable_duration_s")
    )
    for label, value in (
        ("trip_current_a", trip),
        ("destructive_current_a", destructive),
        ("detection_time_s", detection),
        ("survivable_duration_s", survivable),
    ):
        if value <= 0.0:
            raise ValueError("mitigation %s must be positive" % label)
    findings = []
    if trip >= destructive * (1.0 - RELATIVE_TOLERANCE):
        findings.append(FINDING_TRIP_TOO_HIGH)
    if detection >= survivable * (1.0 - RELATIVE_TOLERANCE):
        findings.append(FINDING_TRIP_TOO_SLOW)
    return findings


def voltage_derating_findings(mitigation):
    """Findings about a burnout or gate-rupture voltage derating."""
    applied = _numeric(
        "mitigation applied_voltage_v", mitigation.get("applied_voltage_v")
    )
    safe = _numeric(
        "mitigation demonstrated_safe_voltage_v",
        mitigation.get("demonstrated_safe_voltage_v"),
    )
    if applied <= 0.0 or safe <= 0.0:
        raise ValueError("mitigation voltages must be positive")
    findings = []
    if applied > safe * (1.0 + RELATIVE_TOLERANCE):
        findings.append(FINDING_VOLTAGE_TOO_HIGH)
    return findings


def validate_event(event):
    """Validate one part-event record and return a normalized copy."""
    if not isinstance(event, dict):
        raise ValueError("event must be a mapping")
    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event needs a non-empty string id")
    event_type = event.get("event_type")
    destructive = event_is_destructive(event_type)
    threshold = _numeric(
        "event %s let_threshold_mev_cm2_mg" % event_id,
        event.get("let_threshold_mev_cm2_mg"),
    )
    if threshold <= 0.0:
        raise ValueError("event %s let_threshold must be positive" % event_id)
    mitigation = validate_mitigation(event.get("mitigation"), event_type)
    normalized = {
        "id": event_id,
        "event_type": event_type,
        "destructive": destructive,
        "let_threshold_mev_cm2_mg": threshold,
        "mitigation": mitigation,
    }
    if not destructive:
        cross_section = _numeric(
            "event %s saturation_cross_section_cm2" % event_id,
            event.get("saturation_cross_section_cm2"),
        )
        if cross_section <= 0.0:
            raise ValueError(
                "event %s saturation_cross_section_cm2 must be positive" % event_id
            )
        device_count = event.get("device_count", 1)
        if not isinstance(device_count, int) or isinstance(device_count, bool):
            raise ValueError("event %s device_count must be an integer" % event_id)
        if device_count < 1:
            raise ValueError("event %s device_count must be at least 1" % event_id)
        normalized["saturation_cross_section_cm2"] = cross_section
        normalized["device_count"] = device_count
    return normalized


def assess_event(event, spectrum, budget_per_day=None):
    """Assess one part-event against the clause 5.3 requirement."""
    norm = validate_event(event)
    excluded = excluded_by_let_threshold(
        spectrum, norm["let_threshold_mev_cm2_mg"]
    )
    kind = norm["mitigation"]["kind"]
    findings = []
    rate = None
    if norm["destructive"]:
        if not excluded:
            if kind == "none":
                findings.append(FINDING_NO_MITIGATION)
            elif kind not in MITIGATION_FOR_EVENT[norm["event_type"]]:
                findings.append(FINDING_WRONG_MITIGATION)
            elif kind == "latchup-current-limiter":
                findings.extend(latchup_mitigation_findings(norm["mitigation"]))
            else:
                findings.extend(voltage_derating_findings(norm["mitigation"]))
    else:
        if kind != "none" and kind not in MITIGATION_FOR_EVENT[norm["event_type"]]:
            findings.append(FINDING_WRONG_MITIGATION)
        rate = event_rate_per_day(
            spectrum,
            norm["let_threshold_mev_cm2_mg"],
            norm["saturation_cross_section_cm2"],
            norm["device_count"],
            norm["mitigation"]["reduction_factor"],
        )
        if budget_per_day is not None:
            budget = _numeric("budget_per_day", budget_per_day, 0.0)
            if rate > budget * (1.0 + RELATIVE_TOLERANCE):
                findings.append(FINDING_RATE_ABOVE_BUDGET)
    return {
        "id": norm["id"],
        "event_type": norm["event_type"],
        "destructive": norm["destructive"],
        "let_threshold_mev_cm2_mg": norm["let_threshold_mev_cm2_mg"],
        "excluded_by_threshold": excluded,
        "mitigation_kind": kind,
        "rate_per_day": rate,
        "findings": findings,
        "compliant": not findings,
    }


def assess_single_event_effects(events, spectrum, budget_per_day=None):
    """Run the clause 5.3 assessment over a list of part-events."""
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    validate_let_spectrum(spectrum)
    results = []
    seen = set()
    for event in events:
        result = assess_event(event, spectrum, budget_per_day)
        key = (result["id"], result["event_type"])
        if key in seen:
            raise ValueError("duplicate event %r for part %r" % (key[1], key[0]))
        seen.add(key)
        results.append(result)
    rates = [r["rate_per_day"] for r in results if r["rate_per_day"] is not None]
    non_compliant = sorted({r["id"] for r in results if not r["compliant"]})
    return {
        "events": results,
        "total_rate_per_day": sum(rates) if rates else 0.0,
        "destructive_ids": sorted(
            {r["id"] for r in results if r["destructive"]}
        ),
        "excluded_ids": sorted(
            {r["id"] for r in results if r["excluded_by_threshold"]}
        ),
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
