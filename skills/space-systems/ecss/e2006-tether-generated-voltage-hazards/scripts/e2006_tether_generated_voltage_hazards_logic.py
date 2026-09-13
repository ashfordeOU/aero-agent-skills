#!/usr/bin/env python3
"""Tether-generated potential hazards (ECSS-E-ST-20-06C clause 10.2.1).

Deterministic, offline, stdlib-only implementation of the hazard procedure
for the potentials a conducting tether develops while it is carried through
a planetary magnetic field. The standard text is not reproduced; the clause
is cited as an anchor only and its intent is re-expressed as a checkable
procedure:

  * derive the motional electric field from orbital velocity and field
    strength,
  * project it along the deployed line to get the end-to-end electromotive
    force,
  * split that force about the point where the line floats with the plasma,
  * compare each exposed end, each insulation span and the ground-handling
    touch point against its own limit, and
  * report every limit exceeded, with the driving quantity alongside it.
"""

import math

# Touch-potential limit for a tether end that can be reached during ground
# handling or by crew on an inhabited vehicle, in volts.
GROUND_HANDLING_TOUCH_LIMIT_V = 60.0

# Arc-onset magnitude for each kind of exposed metal sitting in the ambient
# plasma, in volts. Negative-going potentials drive the arc, so the entries
# are magnitudes and the check is applied to the absolute potential.
ARC_ONSET_BY_SURFACE = {
    "bare-metal-in-plasma": 100.0,
    "solar-array-interconnect": 150.0,
    "anodized-structure": 200.0,
    "plasma-contactor-electrode": 400.0,
}

# Severity bands for an end potential measured against its arc onset.
SEVERITY_COMPLIANT = "compliant"
SEVERITY_MARGINAL = "marginal"
SEVERITY_EXCEEDED = "exceeded"

# A potential inside this fraction of its onset is not yet an exceedance but
# no longer carries usable margin.
MARGINAL_FRACTION = 0.8

# Minimum withstand-to-stress ratio an insulation span must show.
MIN_INSULATION_MARGIN = 2.0

# Slack used only to absorb float representation error at an exact boundary.
# It never widens an engineering limit.
BOUNDARY_REL_TOL = 1e-9
BOUNDARY_ABS_TOL = 1e-9

END_ROLES = ("anode-end", "cathode-end")


def _require_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_positive(value, name):
    out = _require_number(value, name)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _require_angle(value, name):
    out = _require_number(value, name)
    if not 0.0 <= out <= 180.0:
        raise ValueError("%s must lie in [0, 180] degrees, got %r" % (name, value))
    return out


def _within(value, limit):
    """True when value <= limit, absorbing float representation error."""
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL
    )


def motional_electric_field(velocity_mps, field_tesla, velocity_field_angle_deg):
    """Magnitude of the induced field seen by the moving line, in V/m.

    The induced field is the cross product of velocity and magnetic flux
    density, so only the component of the field across the velocity counts.
    """
    velocity = _require_positive(velocity_mps, "velocity_mps")
    flux = _require_positive(field_tesla, "field_tesla")
    angle = _require_angle(velocity_field_angle_deg, "velocity_field_angle_deg")
    return velocity * flux * math.sin(math.radians(angle))


def tether_emf(field_v_per_m, deployed_length_m, tether_alignment_deg):
    """Signed end-to-end electromotive force along the deployed line, in V.

    Only the component of the induced field along the line integrates into a
    potential difference; a line lying across the induced field develops
    nothing, and past ninety degrees the polarity reverses.
    """
    field = _require_number(field_v_per_m, "field_v_per_m")
    if field < 0.0:
        raise ValueError("field_v_per_m must be >= 0, got %r" % (field_v_per_m,))
    length = _require_positive(deployed_length_m, "deployed_length_m")
    alignment = _require_angle(tether_alignment_deg, "tether_alignment_deg")
    return field * length * math.cos(math.radians(alignment))


def end_potentials(emf_v, floating_fraction):
    """Potentials of the two ends relative to the ambient plasma, in volts.

    The line floats so that the collected electron current balances the
    collected ion current; floating_fraction is the share of the total force
    that falls on the negative side of that balance point.
    """
    emf = _require_number(emf_v, "emf_v")
    fraction = _require_number(floating_fraction, "floating_fraction")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("floating_fraction must lie in [0, 1], got %r" % (floating_fraction,))
    positive_end = emf * (1.0 - fraction)
    negative_end = -emf * fraction
    return {"anode-end": positive_end, "cathode-end": negative_end}


def arc_onset_v(surface_kind):
    """Arc-onset magnitude for one kind of exposed surface, in volts."""
    if surface_kind not in ARC_ONSET_BY_SURFACE:
        raise ValueError(
            "unknown surface_kind %r; expected one of %s"
            % (surface_kind, tuple(sorted(ARC_ONSET_BY_SURFACE)))
        )
    return ARC_ONSET_BY_SURFACE[surface_kind]


def categorize_end_severity(potential_v, onset_v):
    """Band one end potential against its arc-onset magnitude."""
    magnitude = abs(_require_number(potential_v, "potential_v"))
    onset = _require_positive(onset_v, "onset_v")
    if not _within(magnitude, onset):
        return SEVERITY_EXCEEDED
    if _within(magnitude, MARGINAL_FRACTION * onset):
        return SEVERITY_COMPLIANT
    return SEVERITY_MARGINAL


def insulation_margin(stress_v, withstand_v):
    """Ratio of insulation withstand rating to the applied stress."""
    stress = abs(_require_number(stress_v, "stress_v"))
    withstand = _require_positive(withstand_v, "withstand_v")
    if stress == 0.0:
        return float("inf")
    return withstand / stress


def ground_handling_exceedance(potential_v, limit_v=GROUND_HANDLING_TOUCH_LIMIT_V):
    """True when a reachable end sits above the touch-potential limit."""
    magnitude = abs(_require_number(potential_v, "potential_v"))
    limit = _require_positive(limit_v, "limit_v")
    return not _within(magnitude, limit)


def assess_end(end_spec, potential_v):
    """Check one tether end: arc onset, touch limit and severity band."""
    if not isinstance(end_spec, dict):
        raise ValueError("end_spec must be a mapping, got %r" % (type(end_spec),))
    role = end_spec.get("role")
    if role not in END_ROLES:
        raise ValueError("role must be one of %s, got %r" % (END_ROLES, role))
    surface = end_spec.get("surface_kind")
    onset = arc_onset_v(surface)
    reachable = end_spec.get("reachable_during_handling", False)
    if not isinstance(reachable, bool):
        raise ValueError(
            "reachable_during_handling must be a boolean, got %r" % (reachable,)
        )
    severity = categorize_end_severity(potential_v, onset)
    findings = []
    if severity == SEVERITY_EXCEEDED:
        findings.append(
            "%s: %.1f V exceeds the %.1f V arc onset of %s"
            % (role, potential_v, onset, surface)
        )
    elif severity == SEVERITY_MARGINAL:
        findings.append(
            "%s: %.1f V sits above %.0f%% of the %.1f V arc onset of %s"
            % (role, potential_v, MARGINAL_FRACTION * 100.0, onset, surface)
        )
    touch_exceeded = reachable and ground_handling_exceedance(potential_v)
    if touch_exceeded:
        findings.append(
            "%s: reachable end at %.1f V exceeds the %.1f V touch limit"
            % (role, potential_v, GROUND_HANDLING_TOUCH_LIMIT_V)
        )
    return {
        "role": role,
        "surface_kind": surface,
        "potential_v": potential_v,
        "arc_onset_v": onset,
        "severity": severity,
        "touch_exceeded": touch_exceeded,
        "findings": findings,
        "compliant": severity != SEVERITY_EXCEEDED and not touch_exceeded,
    }


def assess_insulation_spans(spans, emf_v):
    """Check each insulated span against the stress its share of the force puts on it."""
    if not isinstance(spans, (list, tuple)):
        raise ValueError("spans must be a list, got %r" % (type(spans),))
    records = []
    for span in spans:
        if not isinstance(span, dict):
            raise ValueError("span must be a mapping, got %r" % (type(span),))
        span_id = span.get("id")
        if not isinstance(span_id, str) or not span_id.strip():
            raise ValueError("span id must be a non-empty string, got %r" % (span_id,))
        share = _require_number(span.get("length_share"), "length_share")
        if not 0.0 < share <= 1.0:
            raise ValueError("length_share must lie in (0, 1], got %r" % (share,))
        withstand = _require_positive(span.get("withstand_v"), "withstand_v")
        stress = abs(_require_number(emf_v, "emf_v")) * share
        margin = insulation_margin(stress, withstand)
        ok = margin >= MIN_INSULATION_MARGIN or math.isclose(
            margin, MIN_INSULATION_MARGIN, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL
        )
        findings = []
        if not ok:
            findings.append(
                "%s: insulation margin %.3f is below the required %.1f"
                % (span_id, margin, MIN_INSULATION_MARGIN)
            )
        records.append(
            {
                "id": span_id,
                "stress_v": stress,
                "withstand_v": withstand,
                "margin": margin,
                "compliant": ok,
                "findings": findings,
            }
        )
    return records


def assess_voltage_hazards(config):
    """Run the clause 10.2.1 procedure over one tether configuration."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping, got %r" % (type(config),))
    for key in ("velocity_mps", "field_tesla", "deployed_length_m", "ends"):
        if key not in config:
            raise ValueError("config is missing required field %r" % (key,))
    field = motional_electric_field(
        config["velocity_mps"],
        config["field_tesla"],
        config.get("velocity_field_angle_deg", 90.0),
    )
    emf = tether_emf(
        field, config["deployed_length_m"], config.get("tether_alignment_deg", 0.0)
    )
    potentials = end_potentials(emf, config.get("floating_fraction", 0.5))
    ends = config["ends"]
    if not isinstance(ends, (list, tuple)) or len(ends) != 2:
        raise ValueError("ends must be a list of exactly two end specs")
    end_records = []
    seen_roles = set()
    for end_spec in ends:
        role = end_spec.get("role") if isinstance(end_spec, dict) else None
        if role in seen_roles:
            raise ValueError("duplicate end role %r" % (role,))
        record = assess_end(end_spec, potentials.get(role, 0.0))
        seen_roles.add(record["role"])
        end_records.append(record)
    if seen_roles != set(END_ROLES):
        raise ValueError("ends must cover both %s" % (END_ROLES,))
    span_records = assess_insulation_spans(config.get("insulation_spans", []), emf)
    findings = []
    for record in end_records + span_records:
        findings.extend(record["findings"])
    graded = end_records + span_records
    return {
        "induced_field_v_per_m": field,
        "emf_v": emf,
        "end_potentials_v": potentials,
        "ends": end_records,
        "insulation_spans": span_records,
        "findings": findings,
        "marginal_ends": [r["role"] for r in end_records if r["severity"] == SEVERITY_MARGINAL],
        "compliant": all(r["compliant"] for r in graded),
    }
