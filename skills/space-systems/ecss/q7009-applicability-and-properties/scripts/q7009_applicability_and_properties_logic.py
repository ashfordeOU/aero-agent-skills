"""Applicability envelope and obtainable properties for thermo-optical measurement.

Anchor: ECSS-Q-ST-70-09C framework clauses -- the scope of the thermo-optical
property measurements (solar absorptance and infrared emittance) and the
surface types those measurements cover. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the specimen record: surface category, transmittance, specimen and
   measurement-port dimensions, pattern pitch where the surface is textured.
2. Screen opacity against the transmittance floor. An opaque surface closes the
   energy balance with reflectance alone; a transmitting one does not.
3. Check the specimen overfills the measurement port by the required margin and,
   for a patterned surface, that enough pattern periods sit inside the port for
   the reading to represent the surface rather than one cell of it.
4. Decide which properties the surface can yield (solar absorptance, infrared
   emittance, or neither) and under which method constraints.
5. Report blocking findings separately from method constraints, and roll a
   specimen set up into a campaign scope statement.
"""

import math

__all__ = [
    "SURFACE_CATEGORIES",
    "SOLAR_ABSORPTANCE",
    "INFRARED_EMITTANCE",
    "TRANSMITTANCE_FLOOR",
    "PORT_OVERFILL_MARGIN",
    "MIN_PATTERN_PERIODS",
    "BALANCE_TOLERANCE",
    "validate_surface_category",
    "opacity_state",
    "port_overfill_ratio",
    "overfills_port",
    "pattern_periods_across_port",
    "absorptance_from_reflectance_transmittance",
    "measurable_properties",
    "assess_specimen",
    "assess_campaign",
]

SOLAR_ABSORPTANCE = "solar-absorptance"
INFRARED_EMITTANCE = "infrared-emittance"

# Surface families the measurement methods cover. Each one changes what the
# instrument actually sees, so the family is part of the scope statement.
SURFACE_CATEGORIES = (
    "diffuse-opaque-coating",
    "specular-metallized",
    "semi-transparent-film",
    "patterned-or-textured",
    "in-service-contaminated",
)

# A surface transmitting less than this is treated as opaque: the transmitted
# term is then below what the instrument can separate from stray light.
TRANSMITTANCE_FLOOR = 1.0e-3

# The specimen has to be larger than the port it is read through, or the
# reading carries the port surround as well as the specimen.
PORT_OVERFILL_MARGIN = 0.10

# A textured surface read over fewer periods than this reports one cell of the
# pattern, not the surface.
MIN_PATTERN_PERIODS = 5.0

# Fractions that should land exactly on a bound land a few ULPs off it.
BALANCE_TOLERANCE = 1.0e-9


def _require_real(value, label):
    """Return value as a float, refusing booleans, non-numerics and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_positive(value, label):
    """Return a strictly positive float."""
    number = _require_real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_fraction(value, label):
    """Return a float constrained to the closed unit interval."""
    number = _require_real(value, label)
    if number < -BALANCE_TOLERANCE or number > 1.0 + BALANCE_TOLERANCE:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, number))
    return min(max(number, 0.0), 1.0)


def validate_surface_category(category):
    """Return the surface category, refusing one outside the covered families."""
    if not isinstance(category, str) or not category:
        raise ValueError("surface category must be a non-empty string")
    if category not in SURFACE_CATEGORIES:
        raise ValueError(
            "surface category %r is outside the covered families %s"
            % (category, ", ".join(SURFACE_CATEGORIES))
        )
    return category


def opacity_state(transmittance, floor=TRANSMITTANCE_FLOOR):
    """Return 'opaque' or 'transmitting' for a measured total transmittance."""
    tau = _require_fraction(transmittance, "transmittance")
    limit = _require_positive(floor, "transmittance floor")
    if limit > 1.0:
        raise ValueError("transmittance floor must not exceed unity, got %g" % limit)
    if tau <= limit + BALANCE_TOLERANCE:
        return "opaque"
    return "transmitting"


def port_overfill_ratio(specimen_size_mm, port_size_mm):
    """Return the ratio of the specimen extent to the measurement-port extent."""
    specimen = _require_positive(specimen_size_mm, "specimen_size_mm")
    port = _require_positive(port_size_mm, "port_size_mm")
    return specimen / port


def overfills_port(specimen_size_mm, port_size_mm, margin=PORT_OVERFILL_MARGIN):
    """Return True when the specimen overfills the port by at least the margin."""
    required = 1.0 + _require_real(margin, "margin")
    if required <= 0.0:
        raise ValueError("margin must leave a positive required ratio, got %g" % required)
    ratio = port_overfill_ratio(specimen_size_mm, port_size_mm)
    return ratio > required or math.isclose(
        ratio, required, rel_tol=0.0, abs_tol=BALANCE_TOLERANCE
    )


def pattern_periods_across_port(pattern_pitch_mm, port_size_mm):
    """Return how many pattern periods the measurement port spans."""
    pitch = _require_positive(pattern_pitch_mm, "pattern_pitch_mm")
    port = _require_positive(port_size_mm, "port_size_mm")
    return port / pitch


def absorptance_from_reflectance_transmittance(reflectance, transmittance=0.0):
    """Return the absorptance closing the energy balance of a measured surface."""
    rho = _require_fraction(reflectance, "reflectance")
    tau = _require_fraction(transmittance, "transmittance")
    total = rho + tau
    if total > 1.0 + BALANCE_TOLERANCE:
        raise ValueError(
            "reflectance %g plus transmittance %g exceeds unity; the energy "
            "balance cannot close" % (rho, tau)
        )
    return max(0.0, 1.0 - total)


def measurable_properties(category, transmittance, substrate_backed=False):
    """Return the properties a surface of this family can yield, as a tuple."""
    validate_surface_category(category)
    state = opacity_state(transmittance)
    if not isinstance(substrate_backed, bool):
        raise ValueError("substrate_backed must be a boolean")
    if state == "transmitting" and not substrate_backed:
        # A free film transmits into the instrument background: neither the
        # absorptance nor the emittance of the film alone is separable.
        return ()
    return (SOLAR_ABSORPTANCE, INFRARED_EMITTANCE)


def assess_specimen(specimen, margin=PORT_OVERFILL_MARGIN,
                    min_periods=MIN_PATTERN_PERIODS):
    """Assess one specimen against the applicability envelope.

    specimen keys: id, category, transmittance, specimen_size_mm, port_size_mm,
    optional pattern_pitch_mm, optional substrate_backed, optional
    reflectance_only (a campaign that will measure reflectance and nothing else).
    """
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping")
    for key in ("id", "category", "transmittance", "specimen_size_mm", "port_size_mm"):
        if key not in specimen:
            raise ValueError("specimen missing required key '%s'" % key)
    identifier = specimen["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("specimen id must be a non-empty string")
    category = validate_surface_category(specimen["category"])
    tau = _require_fraction(specimen["transmittance"], "transmittance")
    state = opacity_state(tau)
    substrate_backed = specimen.get("substrate_backed", False)
    if not isinstance(substrate_backed, bool):
        raise ValueError("substrate_backed must be a boolean")
    reflectance_only = specimen.get("reflectance_only", False)
    if not isinstance(reflectance_only, bool):
        raise ValueError("reflectance_only must be a boolean")

    ratio = port_overfill_ratio(specimen["specimen_size_mm"], specimen["port_size_mm"])
    fills = overfills_port(specimen["specimen_size_mm"], specimen["port_size_mm"], margin)

    findings = []
    constraints = []

    if not fills:
        findings.append(
            "specimen %s spans %.3f of the port extent; the port surround is "
            "inside the field of view" % (identifier, ratio)
        )

    periods = None
    if category == "patterned-or-textured":
        if "pattern_pitch_mm" not in specimen:
            raise ValueError("a patterned surface needs 'pattern_pitch_mm'")
        periods = pattern_periods_across_port(
            specimen["pattern_pitch_mm"], specimen["port_size_mm"]
        )
        threshold = _require_positive(min_periods, "min_periods")
        if periods < threshold and not math.isclose(
            periods, threshold, rel_tol=0.0, abs_tol=BALANCE_TOLERANCE
        ):
            findings.append(
                "specimen %s spans %.2f pattern periods across the port; the "
                "reading describes one cell, not the surface" % (identifier, periods)
            )
        else:
            constraints.append(
                "average over at least one whole number of pattern periods and "
                "record the port position relative to the pattern"
            )

    if state == "transmitting":
        if reflectance_only:
            findings.append(
                "specimen %s transmits %.4f; a reflectance-only absorptance "
                "omits the transmitted term" % (identifier, tau)
            )
        else:
            constraints.append(
                "measure transmittance alongside reflectance and close the "
                "balance as one minus their sum"
            )
        if not substrate_backed:
            findings.append(
                "specimen %s is a free transmitting film; neither property is "
                "separable from the instrument background" % identifier
            )
        else:
            constraints.append(
                "report the film on its declared substrate; the pair is the "
                "measured article, not the film alone"
            )

    if category == "semi-transparent-film" and state == "opaque":
        findings.append(
            "specimen %s is declared semi-transparent but measures opaque at "
            "%.5f transmittance; the declaration and the specimen disagree"
            % (identifier, tau)
        )

    if category == "specular-metallized":
        constraints.append(
            "keep the specular component inside the collected signal; a trap "
            "left open removes most of the reflected energy"
        )
    if category == "in-service-contaminated":
        constraints.append(
            "report as-received; cleaning the specimen measures the cleaning, "
            "not the surface that flew"
        )

    properties = measurable_properties(category, tau, substrate_backed)
    in_scope = not findings and bool(properties)
    return {
        "id": identifier,
        "category": category,
        "opacity": state,
        "transmittance": tau,
        "port_overfill_ratio": ratio,
        "pattern_periods": periods,
        "measurable_properties": list(properties),
        "constraints": constraints,
        "findings": findings,
        "in_scope": in_scope,
    }


def assess_campaign(specimens, margin=PORT_OVERFILL_MARGIN,
                    min_periods=MIN_PATTERN_PERIODS):
    """Assess a specimen set and return the campaign scope statement."""
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("specimens must be a non-empty sequence")
    records = [assess_specimen(item, margin, min_periods) for item in specimens]
    seen = set()
    duplicates = []
    for record in records:
        if record["id"] in seen:
            duplicates.append(record["id"])
        seen.add(record["id"])
    findings = []
    for identifier in sorted(set(duplicates)):
        findings.append("specimen id %s appears more than once" % identifier)
    in_scope = [r for r in records if r["in_scope"]]
    absorptance_count = sum(
        1 for r in in_scope if SOLAR_ABSORPTANCE in r["measurable_properties"]
    )
    emittance_count = sum(
        1 for r in in_scope if INFRARED_EMITTANCE in r["measurable_properties"]
    )
    return {
        "records": records,
        "specimen_count": len(records),
        "in_scope_count": len(in_scope),
        "solar_absorptance_count": absorptance_count,
        "infrared_emittance_count": emittance_count,
        "findings": findings,
        "campaign_in_scope": len(in_scope) == len(records) and not findings,
    }
