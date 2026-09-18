"""Apparatus configuration for a thermal-vacuum outgassing screening chamber.

Anchor: ECSS-Q-ST-70-02C, apparatus clause -- the vacuum chamber, the heated
specimen bar and the cooled collector plates have to be set up the way the
method assumes before a run means anything. Paraphrased into an implementable
procedure; no standard text is reproduced.

What this module decides
------------------------
Whether the chamber as built matches the method, and what has to be corrected
before specimens are loaded.

1. Pairing. Every specimen compartment effuses onto its own collector plate. A
   collector serving two compartments mixes two materials on one deposit, and
   a compartment with no collector produces no condensable reading at all.
2. Geometry. The aperture between a compartment and its collector fixes the
   fraction of the effused flux the plate can intercept. That fraction follows
   from the aperture radius and the compartment-to-collector gap, and is the
   quantity that has to sit inside the method band -- not the two dimensions
   on their own.
3. Heating. The compartments sit in a common heated bar, so the spread of
   compartment temperatures inside one zone is the property that matters, and
   it is reported per zone rather than as a single chamber number.
4. Collector control. The collector plates are held at their own controlled
   temperature, independent of the bar, and a plate outside its band changes
   what condenses on it.
5. Pressure capability. The chamber has to reach a base pressure comfortably
   below the pressure the run is held at, or the run limit is the pump rather
   than a controlled condition.
"""

import math

__all__ = [
    "DEFAULT_CAPTURE_FRACTION_BAND",
    "DEFAULT_ZONE_SPREAD_C",
    "DEFAULT_COLLECTOR_BAND_C",
    "DEFAULT_BASE_PRESSURE_MARGIN",
    "as_positive_float",
    "capture_fraction",
    "validate_compartment",
    "aperture_findings",
    "collector_assignment_findings",
    "zone_spread_c",
    "zone_uniformity_findings",
    "collector_temperature_findings",
    "base_pressure_findings",
    "assess_chamber_configuration",
]

# Fraction of the flux leaving a compartment that its collector can intercept.
DEFAULT_CAPTURE_FRACTION_BAND = (0.05, 0.50)

# Largest accepted spread of compartment temperatures inside one heated zone.
DEFAULT_ZONE_SPREAD_C = 1.0

# Controlled collector plate band.
DEFAULT_COLLECTOR_BAND_C = (24.0, 26.0)

# The chamber base pressure has to be at least this many times below the
# pressure the run is held at.
DEFAULT_BASE_PRESSURE_MARGIN = 10.0

# Band comparisons are inclusive; absorb representation error at the edge
# rather than widening the band itself.
BAND_TOLERANCE = 1e-9


def as_positive_float(value, label):
    """Return value as a strictly positive finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _validate_band(band, label):
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _as_finite_float(band[0], "%s low" % label)
    high = _as_finite_float(band[1], "%s high" % label)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def _in_band(value, band):
    low, high = band
    return (value >= low - BAND_TOLERANCE) and (value <= high + BAND_TOLERANCE)


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-blank string, got %r" % (label, value))
    return value.strip()


def capture_fraction(aperture_diameter_mm, gap_mm):
    """Return the on-axis fraction of effused flux an aperture can intercept.

    A small diffusely emitting source at distance L on the axis of a circular
    aperture of radius r delivers r^2 / (r^2 + L^2) of its total flux through
    that aperture. Both dimensions therefore move the same single number, and
    that number is what the method band is written against.
    """
    diameter = as_positive_float(aperture_diameter_mm, "aperture_diameter_mm")
    gap = as_positive_float(gap_mm, "gap_mm")
    radius = diameter / 2.0
    return (radius * radius) / (radius * radius + gap * gap)


def validate_compartment(record):
    """Return a normalised compartment record, or raise on a malformed one."""
    if not isinstance(record, dict):
        raise ValueError("compartment must be a mapping")
    for key in ("id", "collector_id", "zone", "aperture_diameter_mm", "gap_mm",
                "temperature_c"):
        if key not in record:
            raise ValueError("compartment is missing '%s'" % key)
    return {
        "id": _identifier(record["id"], "compartment id"),
        "collector_id": _identifier(record["collector_id"], "collector_id"),
        "zone": _identifier(record["zone"], "zone"),
        "aperture_diameter_mm": as_positive_float(
            record["aperture_diameter_mm"], "aperture_diameter_mm"
        ),
        "gap_mm": as_positive_float(record["gap_mm"], "gap_mm"),
        "temperature_c": _as_finite_float(record["temperature_c"], "temperature_c"),
        "capture_fraction": capture_fraction(
            record["aperture_diameter_mm"], record["gap_mm"]
        ),
    }


def aperture_findings(compartments, band=DEFAULT_CAPTURE_FRACTION_BAND):
    """Return a finding per compartment whose capture fraction left the band."""
    limits = _validate_band(band, "capture fraction band")
    findings = []
    for record in compartments:
        value = record["capture_fraction"]
        if not _in_band(value, limits):
            findings.append(
                "compartment '%s' intercepts %.4f of the effused flux, outside the "
                "%.4f-%.4f band" % (record["id"], value, limits[0], limits[1])
            )
    return findings


def collector_assignment_findings(compartments):
    """Return findings for collectors serving more than one compartment."""
    owners = {}
    order = []
    for record in compartments:
        collector = record["collector_id"]
        if collector not in owners:
            owners[collector] = []
            order.append(collector)
        owners[collector].append(record["id"])
    findings = []
    for collector in order:
        served = owners[collector]
        if len(served) > 1:
            findings.append(
                "collector '%s' serves %d compartments (%s); one deposit cannot "
                "report several materials" % (collector, len(served), ", ".join(served))
            )
    return findings


def zone_spread_c(temperatures):
    """Return the spread in kelvin of the compartment temperatures of one zone."""
    if not isinstance(temperatures, (list, tuple)) or not temperatures:
        raise ValueError("temperatures must be a non-empty sequence")
    values = [_as_finite_float(t, "zone temperature") for t in temperatures]
    return max(values) - min(values)


def zone_uniformity_findings(compartments, allowed_spread_c=DEFAULT_ZONE_SPREAD_C):
    """Return a finding per heated zone whose compartments do not agree."""
    allowed = as_positive_float(allowed_spread_c, "allowed_spread_c")
    zones = {}
    order = []
    for record in compartments:
        zone = record["zone"]
        if zone not in zones:
            zones[zone] = []
            order.append(zone)
        zones[zone].append(record["temperature_c"])
    findings = []
    for zone in order:
        spread = zone_spread_c(zones[zone])
        if spread > allowed + BAND_TOLERANCE:
            findings.append(
                "heated zone '%s' spans %.2f K across its compartments, beyond the "
                "%.2f K allowance" % (zone, spread, allowed)
            )
    return findings


def collector_temperature_findings(collectors, band=DEFAULT_COLLECTOR_BAND_C):
    """Return a finding per collector plate held outside its controlled band."""
    if not isinstance(collectors, dict) or not collectors:
        raise ValueError("collectors must be a non-empty mapping of id to temperature")
    limits = _validate_band(band, "collector band")
    findings = []
    for collector in sorted(collectors):
        value = _as_finite_float(collectors[collector], "collector temperature")
        if not _in_band(value, limits):
            findings.append(
                "collector '%s' is held at %.2f C, outside the %.2f-%.2f C band"
                % (collector, value, limits[0], limits[1])
            )
    return findings


def base_pressure_findings(base_pressure_pa, run_pressure_pa,
                           margin=DEFAULT_BASE_PRESSURE_MARGIN):
    """Return a finding when the chamber cannot pump below the run pressure."""
    base = as_positive_float(base_pressure_pa, "base_pressure_pa")
    run = as_positive_float(run_pressure_pa, "run_pressure_pa")
    factor = as_positive_float(margin, "margin")
    achieved = run / base
    if achieved < factor - BAND_TOLERANCE:
        return [
            "chamber base pressure is only %.2f times below the run pressure; "
            "%.2f times are required" % (achieved, factor)
        ]
    return []


def assess_chamber_configuration(spec):
    """Run the full apparatus configuration assessment for one chamber.

    spec keys: compartments (sequence), collectors (mapping id to temperature),
    base_pressure_pa, run_pressure_pa, optional capture_band, zone_spread_c,
    collector_band, base_pressure_margin.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("compartments", "collectors", "base_pressure_pa", "run_pressure_pa"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    raw = spec["compartments"]
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("spec['compartments'] must be a non-empty sequence")
    records = [validate_compartment(item) for item in raw]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("compartment id '%s' is used more than once" % record["id"])
        seen.add(record["id"])
    collectors = spec["collectors"]
    if not isinstance(collectors, dict) or not collectors:
        raise ValueError("spec['collectors'] must be a non-empty mapping")
    findings = []
    for record in records:
        if record["collector_id"] not in collectors:
            findings.append(
                "compartment '%s' names collector '%s', which the chamber does not have"
                % (record["id"], record["collector_id"])
            )
    findings.extend(collector_assignment_findings(records))
    findings.extend(
        aperture_findings(records, spec.get("capture_band", DEFAULT_CAPTURE_FRACTION_BAND))
    )
    findings.extend(
        zone_uniformity_findings(records, spec.get("zone_spread_c", DEFAULT_ZONE_SPREAD_C))
    )
    findings.extend(
        collector_temperature_findings(
            collectors, spec.get("collector_band", DEFAULT_COLLECTOR_BAND_C)
        )
    )
    findings.extend(
        base_pressure_findings(
            spec["base_pressure_pa"],
            spec["run_pressure_pa"],
            spec.get("base_pressure_margin", DEFAULT_BASE_PRESSURE_MARGIN),
        )
    )
    unused = sorted(set(collectors) - {record["collector_id"] for record in records})
    for collector in unused:
        findings.append("collector '%s' is not paired with any compartment" % collector)
    return {
        "compartments": records,
        "capture_fractions": {r["id"]: r["capture_fraction"] for r in records},
        "zones": sorted({r["zone"] for r in records}),
        "findings": findings,
        "configured": not findings,
    }
