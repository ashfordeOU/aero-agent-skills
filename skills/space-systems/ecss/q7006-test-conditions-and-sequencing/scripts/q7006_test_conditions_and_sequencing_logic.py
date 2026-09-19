"""Test conditions and exposure sequencing for a radiation degradation test.

Anchor: ECSS-Q-ST-70-06C, procedure clause -- the chamber pressure and
specimen temperature the exposure is held at, the flux rate it is driven at,
and the order and interruption structure of the exposure itself. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade the chamber pressure and the achieved specimen temperature against
   the limits and the band the specification fixed.
2. Normalise the requested exposure steps into fractions of the total
   exposure, refusing a set that does not account for the whole exposure.
3. Build the sequence: per-step exposure, duration at the chosen flux, and
   the cumulative exposure and elapsed beam time at every measurement point.
4. Grade the flux rate against the mission flux and the acceleration limit.
5. Grade the agent block order against the agents the campaign needs, so a
   sequential campaign has a stated and complete order.
6. Grade the measurement interruptions: a property that recovers on contact
   with air has to be read in place, or inside a bounded air-exposure time.
"""

import math

__all__ = [
    "AGENTS",
    "MAX_CHAMBER_PRESSURE_PA",
    "DEFAULT_TEMPERATURE_TOLERANCE_C",
    "MAX_ACCELERATION_FACTOR",
    "MAX_AIR_EXPOSURE_MINUTES",
    "FRACTION_TOLERANCE",
    "pressure_findings",
    "temperature_findings",
    "normalise_step_fractions",
    "step_duration_hours",
    "build_sequence",
    "flux_rate_findings",
    "agent_order_findings",
    "interruption_findings",
    "assess_test_conditions",
]

AGENTS = ("particles", "ultraviolet")

# Above this chamber pressure the residual atmosphere joins the degradation
# chemistry and the run stops representing the space environment.
MAX_CHAMBER_PRESSURE_PA = 1.0e-3

# Specimen temperature is held to this band about the specified value unless
# the specification names a tighter one.
DEFAULT_TEMPERATURE_TOLERANCE_C = 5.0

# Beyond this ratio of test flux to mission flux the dose rate changes the
# mechanism rather than merely shortening the test.
MAX_ACCELERATION_FACTOR = 1000.0

# A property that recovers in air has to be read inside this window when it
# cannot be read in place.
MAX_AIR_EXPOSURE_MINUTES = 30.0

# Step fractions are compared against unity to this absolute tolerance.
FRACTION_TOLERANCE = 1e-9


def _real(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _signed(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def pressure_findings(achieved_pa, limit_pa=MAX_CHAMBER_PRESSURE_PA):
    """Return the findings raised by the chamber pressure held during exposure."""
    achieved = _real(achieved_pa, "achieved_pa")
    limit = _real(limit_pa, "limit_pa")
    if achieved > limit and not math.isclose(achieved, limit, rel_tol=1e-9, abs_tol=0.0):
        return [
            "chamber held %.3g Pa during exposure, above the %.3g Pa limit" % (achieved, limit)
        ]
    return []


def temperature_findings(achieved_c, specified_c, tolerance_c=DEFAULT_TEMPERATURE_TOLERANCE_C):
    """Return the findings raised by the specimen temperature held during exposure."""
    achieved = _signed(achieved_c, "achieved_c")
    specified = _signed(specified_c, "specified_c")
    band = _real(tolerance_c, "tolerance_c", allow_zero=True)
    deviation = abs(achieved - specified)
    if deviation > band and not math.isclose(deviation, band, rel_tol=0.0, abs_tol=1e-9):
        return [
            "specimen held at %.2f C against a specified %.2f C +/- %.2f C"
            % (achieved, specified, band)
        ]
    return []


def normalise_step_fractions(fractions):
    """Return the exposure step fractions, checking they account for the whole run."""
    if not isinstance(fractions, (list, tuple)) or not fractions:
        raise ValueError("fractions must be a non-empty sequence")
    cleaned = []
    for index, value in enumerate(fractions):
        cleaned.append(_real(value, "step fraction %d" % index))
    total = math.fsum(cleaned)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("step fractions sum to %.12g, not to 1" % total)
    return cleaned


def step_duration_hours(step_exposure, flux):
    """Return the beam hours one exposure step takes at the chosen flux."""
    exposure = _real(step_exposure, "step_exposure", allow_zero=True)
    rate = _real(flux, "flux")
    return exposure / rate / 3600.0


def build_sequence(total_exposure, fractions, flux):
    """Return the ordered exposure steps with cumulative exposure and hours."""
    total = _real(total_exposure, "total_exposure")
    cleaned = normalise_step_fractions(fractions)
    rate = _real(flux, "flux")
    steps = []
    cumulative = 0.0
    elapsed = 0.0
    for index, fraction in enumerate(cleaned):
        exposure = total * fraction
        hours = step_duration_hours(exposure, rate)
        cumulative += exposure
        elapsed += hours
        steps.append(
            {
                "index": index + 1,
                "fraction": fraction,
                "step_exposure": exposure,
                "cumulative_exposure": cumulative,
                "step_hours": hours,
                "cumulative_hours": elapsed,
            }
        )
    return steps


def flux_rate_findings(flux, mission_flux, limit=MAX_ACCELERATION_FACTOR):
    """Return the findings raised by the flux rate the exposure is driven at."""
    rate = _real(flux, "flux")
    mission = _real(mission_flux, "mission_flux")
    ceiling = _real(limit, "limit")
    factor = rate / mission
    findings = []
    if factor > ceiling and not math.isclose(factor, ceiling, rel_tol=1e-9, abs_tol=0.0):
        findings.append(
            "exposure runs at an acceleration factor of %.4g, above the limit of %.4g"
            % (factor, ceiling)
        )
    if factor < 1.0 and not math.isclose(factor, 1.0, rel_tol=1e-9, abs_tol=0.0):
        findings.append(
            "exposure runs slower than the mission at a factor of %.4g" % factor
        )
    return findings


def agent_order_findings(order, agents_required):
    """Return the findings raised by the declared order of the exposure blocks."""
    if not isinstance(order, (list, tuple)) or not order:
        raise ValueError("order must be a non-empty sequence of exposure blocks")
    if not isinstance(agents_required, (list, tuple)) or not agents_required:
        raise ValueError("agents_required must be a non-empty sequence")
    needed = set()
    for agent in agents_required:
        if agent not in AGENTS:
            raise ValueError("unknown required agent %r" % agent)
        needed.add(agent)
    covered = []
    for block in order:
        if block == "combined":
            covered.extend(AGENTS)
        elif block in AGENTS:
            covered.append(block)
        else:
            raise ValueError("unknown exposure block %r" % block)
    findings = []
    for agent in sorted(needed):
        if covered.count(agent) == 0:
            findings.append("the declared order never exposes the specimens to %s" % agent)
        elif covered.count(agent) > 1:
            findings.append("the declared order exposes the specimens to %s twice" % agent)
    for agent in sorted(set(covered) - needed):
        findings.append("the declared order adds %s, which the campaign does not need" % agent)
    if "combined" not in order and len(needed) > 1 and len(order) < 2:
        findings.append("a multi-agent campaign needs either a combined block or one per agent")
    return findings


def interruption_findings(step_count, air_sensitive, read_in_situ, air_exposure_minutes):
    """Return the findings raised by how the exposure is interrupted to measure."""
    if isinstance(step_count, bool) or not isinstance(step_count, int) or step_count < 1:
        raise ValueError("step_count must be a positive integer")
    if not isinstance(air_sensitive, bool) or not isinstance(read_in_situ, bool):
        raise ValueError("air_sensitive and read_in_situ must be booleans")
    minutes = _real(air_exposure_minutes, "air_exposure_minutes", allow_zero=True)
    findings = []
    if step_count < 2:
        findings.append(
            "a single exposure step gives one end point and no degradation trend"
        )
    if air_sensitive and not read_in_situ:
        if minutes > MAX_AIR_EXPOSURE_MINUTES and not math.isclose(
            minutes, MAX_AIR_EXPOSURE_MINUTES, rel_tol=1e-9, abs_tol=0.0
        ):
            findings.append(
                "air-sensitive property is read after %.1f minutes in air, past the "
                "%.1f minute window" % (minutes, MAX_AIR_EXPOSURE_MINUTES)
            )
    return findings


def assess_test_conditions(spec):
    """Build and grade the exposure sequence and the conditions it runs under.

    spec keys: total_exposure, step_fractions, flux, mission_flux,
    achieved_pressure_pa, achieved_temperature_c, specified_temperature_c,
    agents, order, optional temperature_tolerance_c, pressure_limit_pa,
    air_sensitive, read_in_situ, air_exposure_minutes.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "total_exposure",
        "step_fractions",
        "flux",
        "mission_flux",
        "achieved_pressure_pa",
        "achieved_temperature_c",
        "specified_temperature_c",
        "agents",
        "order",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    steps = build_sequence(spec["total_exposure"], spec["step_fractions"], spec["flux"])
    findings = []
    findings.extend(
        pressure_findings(
            spec["achieved_pressure_pa"],
            spec.get("pressure_limit_pa", MAX_CHAMBER_PRESSURE_PA),
        )
    )
    findings.extend(
        temperature_findings(
            spec["achieved_temperature_c"],
            spec["specified_temperature_c"],
            spec.get("temperature_tolerance_c", DEFAULT_TEMPERATURE_TOLERANCE_C),
        )
    )
    findings.extend(flux_rate_findings(spec["flux"], spec["mission_flux"]))
    findings.extend(agent_order_findings(spec["order"], spec["agents"]))
    findings.extend(
        interruption_findings(
            len(steps),
            bool(spec.get("air_sensitive", False)),
            bool(spec.get("read_in_situ", False)),
            spec.get("air_exposure_minutes", 0.0),
        )
    )
    return {
        "steps": steps,
        "measurement_points": len(steps),
        "total_exposure": float(spec["total_exposure"]),
        "total_beam_hours": steps[-1]["cumulative_hours"],
        "acceleration_factor": float(spec["flux"]) / float(spec["mission_flux"]),
        "order": tuple(spec["order"]),
        "findings": findings,
        "procedure_ready": not findings,
    }
