#!/usr/bin/env python3
"""Electrostatic disturbance produced by deliberately biased surfaces.

Anchor: ECSS-E-ST-20-06C clause 6.5 (paraphrased into an implementable
procedure; no verbatim standard text).

A deliberately biased surface is an exposed conductor held at a
commanded offset from structure: a high-voltage solar-array string end,
an electric-propulsion grid or neutraliser, a plasma-contactor, a biased
plasma probe, a tether anode, a driven antenna element.  Each one
exchanges current with the ambient plasma at its own potential, so the
whole vehicle floats wherever the summed exchange cancels.  The result
is a shifted frame potential and a sheath whose reach can swallow a
nearby sensitive item.

This module is offline, deterministic and standard-library only:

1. normalise and validate each biased element;
2. evaluate its plasma current at a trial frame potential;
3. solve the vehicle floating condition by bisection;
4. size the sheath around each biased element;
5. report snapover, arc-inception, sputtering and sheath findings.
"""

import math

EPSILON_0 = 8.8541878128e-12      # farad/metre
ELEMENTARY_CHARGE = 1.602176634e-19  # coulomb

# Per-function onset thresholds, in volt relative to the ambient plasma.
# positive_limit_v : onset of electron snapover on the exposed conductor
# negative_limit_v : onset of arcing on the surrounding dielectric
BIASED_FUNCTIONS = {
    "solar-array-string-end": {"positive_limit_v": 100.0, "negative_limit_v": -150.0},
    "electric-propulsion-grid": {"positive_limit_v": 60.0, "negative_limit_v": -200.0},
    "plasma-contactor": {"positive_limit_v": 40.0, "negative_limit_v": -80.0},
    "biased-plasma-probe": {"positive_limit_v": 30.0, "negative_limit_v": -60.0},
    "electrodynamic-tether-anode": {"positive_limit_v": 200.0, "negative_limit_v": -300.0},
    "high-voltage-antenna-element": {"positive_limit_v": 120.0, "negative_limit_v": -180.0},
}

DEFAULT_FRAME_SPUTTERING_LIMIT_V = -100.0
BISECTION_TOLERANCE_V = 1.0e-6
BISECTION_MAX_STEPS = 200
BRACKET_GROWTH_STEPS = 12
LIMIT_REL_TOL = 1e-9


def _number(value, label, minimum=None, strict=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if strict and out <= minimum:
            raise ValueError("%s must be > %g, got %g" % (label, minimum, out))
        if not strict and out < minimum:
            raise ValueError("%s must be >= %g, got %g" % (label, minimum, out))
    return out


def _at_or_below(value, limit):
    """True when value <= limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def _at_or_above(value, limit):
    """True when value >= limit, absorbing representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def normalize_biased_element(element):
    """Validate one deliberately biased element and fill its thresholds."""
    if not isinstance(element, dict):
        raise ValueError("biased element must be a mapping, got %r" % (element,))
    element_id = element.get("id")
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("biased element needs a non-empty string id")
    function = element.get("function")
    if function not in BIASED_FUNCTIONS:
        raise ValueError(
            "element %s: unknown biased function %r (known: %s)"
            % (element_id, function, ", ".join(sorted(BIASED_FUNCTIONS)))
        )
    bias = _number(element.get("bias_v"), "element %s: bias_v" % element_id)
    if bias == 0.0:
        raise ValueError(
            "element %s: bias_v is zero, which is not a deliberately biased "
            "surface; drop it or fold its area into the structure" % element_id
        )
    insulated = element.get("insulated", False)
    if not isinstance(insulated, bool):
        raise ValueError("element %s: insulated must be a boolean" % element_id)
    area = _number(
        element.get("exposed_area_m2"),
        "element %s: exposed_area_m2" % element_id,
        0.0,
        strict=False,
    )
    clearance = element.get("clearance_m")
    if clearance is not None:
        clearance = _number(
            clearance, "element %s: clearance_m" % element_id, 0.0
        )
    defaults = BIASED_FUNCTIONS[function]
    positive_limit = _number(
        element.get("positive_limit_v", defaults["positive_limit_v"]),
        "element %s: positive_limit_v" % element_id,
        0.0,
    )
    negative_limit = _number(
        element.get("negative_limit_v", defaults["negative_limit_v"]),
        "element %s: negative_limit_v" % element_id,
    )
    if negative_limit >= 0.0:
        raise ValueError(
            "element %s: negative_limit_v must be negative, got %g"
            % (element_id, negative_limit)
        )
    return {
        "id": element_id,
        "function": function,
        "bias_v": bias,
        "insulated": insulated,
        "exposed_area_m2": 0.0 if insulated else area,
        "declared_area_m2": area,
        "clearance_m": clearance,
        "positive_limit_v": positive_limit,
        "negative_limit_v": negative_limit,
    }


def build_bias_set(elements):
    """Normalise every biased element; reject an empty set or a repeat id."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("biased-element set must be a non-empty list")
    out = []
    seen = set()
    for element in elements:
        row = normalize_biased_element(element)
        if row["id"] in seen:
            raise ValueError("duplicate biased-element id %r" % row["id"])
        seen.add(row["id"])
        out.append(row)
    return out


def normalize_environment(environment):
    """Validate the ambient plasma the biased surfaces couple into."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping, got %r" % (environment,))
    return {
        "electron_temperature_ev": _number(
            environment.get("electron_temperature_ev"),
            "environment electron_temperature_ev",
            0.0,
        ),
        "ion_temperature_ev": _number(
            environment.get("ion_temperature_ev"),
            "environment ion_temperature_ev",
            0.0,
        ),
        "electron_density_m3": _number(
            environment.get("electron_density_m3"),
            "environment electron_density_m3",
            0.0,
        ),
        "electron_current_density_a_m2": _number(
            environment.get("electron_current_density_a_m2"),
            "environment electron_current_density_a_m2",
            0.0,
            strict=False,
        ),
        "ion_current_density_a_m2": _number(
            environment.get("ion_current_density_a_m2"),
            "environment ion_current_density_a_m2",
            0.0,
            strict=False,
        ),
    }


def debye_length_m(environment):
    """Ambient Debye length, the scale of every sheath in this model."""
    env = normalize_environment(environment)
    return math.sqrt(
        EPSILON_0
        * env["electron_temperature_ev"]
        / (env["electron_density_m3"] * ELEMENTARY_CHARGE)
    )


def collected_current_a(area_m2, potential_v, environment):
    """Net plasma current onto one exposed area, ampere.

    Positive means net electron collection.  A surface positive with
    respect to the plasma collects electrons with a linearly growing
    sheath and repels ions exponentially; a negative surface does the
    mirror image.  The two branches agree at zero potential.
    """
    env = normalize_environment(environment)
    area = _number(area_m2, "area_m2", 0.0, strict=False)
    potential = _number(potential_v, "potential_v")
    te = env["electron_temperature_ev"]
    ti = env["ion_temperature_ev"]
    je = env["electron_current_density_a_m2"]
    ji = env["ion_current_density_a_m2"]
    if area == 0.0:
        return 0.0
    if potential >= 0.0:
        electron = je * (1.0 + potential / te)
        ion = ji * math.exp(-min(potential / ti, 700.0))
    else:
        electron = je * math.exp(-min(-potential / te, 700.0))
        ion = ji * (1.0 + (-potential) / ti)
    return area * (electron - ion)


def net_vehicle_current_a(bias_set, structure_area_m2, frame_potential_v,
                          environment):
    """Summed plasma current onto the whole vehicle at a trial frame."""
    env = normalize_environment(environment)
    frame = _number(frame_potential_v, "frame_potential_v")
    structure_area = _number(
        structure_area_m2, "structure_area_m2", 0.0, strict=False
    )
    total = collected_current_a(structure_area, frame, env)
    for element in bias_set:
        total += collected_current_a(
            element["exposed_area_m2"], frame + element["bias_v"], env
        )
    return total


def solve_frame_potential(bias_set, structure_area_m2, environment):
    """Frame potential at which the vehicle collects no net current."""
    env = normalize_environment(environment)
    exposed = math.fsum(e["exposed_area_m2"] for e in bias_set)
    structure_area = _number(
        structure_area_m2, "structure_area_m2", 0.0, strict=False
    )
    if exposed + structure_area <= 0.0:
        raise ValueError(
            "no exposed conductive area on the vehicle: the floating "
            "condition has no solution"
        )
    span = max(abs(e["bias_v"]) for e in bias_set)
    span = max(span, env["electron_temperature_ev"], 1.0)
    low, high = -10.0 * span, 10.0 * span
    f_low = net_vehicle_current_a(bias_set, structure_area, low, env)
    f_high = net_vehicle_current_a(bias_set, structure_area, high, env)
    steps = 0
    while f_low * f_high > 0.0 and steps < BRACKET_GROWTH_STEPS:
        low *= 4.0
        high *= 4.0
        f_low = net_vehicle_current_a(bias_set, structure_area, low, env)
        f_high = net_vehicle_current_a(bias_set, structure_area, high, env)
        steps += 1
    if f_low * f_high > 0.0:
        raise ValueError(
            "no floating potential inside the bracket: the current balance "
            "never changes sign, check the plasma current densities"
        )
    for _ in range(BISECTION_MAX_STEPS):
        mid = 0.5 * (low + high)
        value = net_vehicle_current_a(bias_set, structure_area, mid, env)
        if abs(high - low) < BISECTION_TOLERANCE_V:
            return mid
        if value * f_low <= 0.0:
            high = mid
        else:
            low, f_low = mid, value
    return 0.5 * (low + high)


def sheath_extent_m(potential_v, environment):
    """Child-law sheath reach around a surface at this potential."""
    env = normalize_environment(environment)
    potential = _number(potential_v, "potential_v")
    magnitude = abs(potential)
    if magnitude == 0.0:
        return 0.0
    ratio = 2.0 * magnitude / env["electron_temperature_ev"]
    return (math.sqrt(2.0) / 3.0) * debye_length_m(env) * (ratio ** 0.75)


def element_rows(bias_set, frame_potential_v, environment):
    """Per-element potential, current, sheath reach and clearance margin."""
    env = normalize_environment(environment)
    frame = _number(frame_potential_v, "frame_potential_v")
    rows = []
    for element in bias_set:
        potential = frame + element["bias_v"]
        sheath = sheath_extent_m(potential, env)
        clearance = element["clearance_m"]
        rows.append(
            {
                "id": element["id"],
                "function": element["function"],
                "bias_v": element["bias_v"],
                "potential_v": potential,
                "exposed_area_m2": element["exposed_area_m2"],
                "current_a": collected_current_a(
                    element["exposed_area_m2"], potential, env
                ),
                "sheath_extent_m": sheath,
                "clearance_m": clearance,
                "clearance_margin_m": None if clearance is None else clearance - sheath,
                "positive_limit_v": element["positive_limit_v"],
                "negative_limit_v": element["negative_limit_v"],
            }
        )
    return rows


def assess_bias_disturbance(rows, frame_potential_v, limits=None):
    """Findings against snapover, arc-inception, sputtering and sheath."""
    limits = dict(limits or {})
    frame = _number(frame_potential_v, "frame_potential_v")
    frame_limit = _number(
        limits.get("frame_sputtering_limit_v", DEFAULT_FRAME_SPUTTERING_LIMIT_V),
        "frame_sputtering_limit_v",
    )
    if frame_limit >= 0.0:
        raise ValueError(
            "frame_sputtering_limit_v must be negative, got %g" % frame_limit
        )
    findings = []
    if not _at_or_above(frame, frame_limit):
        findings.append(
            {
                "kind": "frame-potential-sputtering-exceedance",
                "id": "*frame*",
                "value_v": frame,
                "limit_v": frame_limit,
            }
        )
    for row in rows:
        if row["exposed_area_m2"] == 0.0:
            continue
        if not _at_or_below(row["potential_v"], row["positive_limit_v"]):
            findings.append(
                {
                    "kind": "snapover-onset-exceedance",
                    "id": row["id"],
                    "value_v": row["potential_v"],
                    "limit_v": row["positive_limit_v"],
                }
            )
        if not _at_or_above(row["potential_v"], row["negative_limit_v"]):
            findings.append(
                {
                    "kind": "arc-inception-exceedance",
                    "id": row["id"],
                    "value_v": row["potential_v"],
                    "limit_v": row["negative_limit_v"],
                }
            )
        if row["clearance_m"] is not None and not _at_or_below(
            row["sheath_extent_m"], row["clearance_m"]
        ):
            findings.append(
                {
                    "kind": "sheath-reaches-sensitive-item",
                    "id": row["id"],
                    "value_v": row["sheath_extent_m"],
                    "limit_v": row["clearance_m"],
                }
            )
    return findings


def analyze_biased_surface_potentials(elements, structure_area_m2, environment,
                                      limits=None):
    """Full clause 6.5 product: frame shift, element rows and findings."""
    bias_set = build_bias_set(elements)
    env = normalize_environment(environment)
    structure_area = _number(
        structure_area_m2, "structure_area_m2", 0.0, strict=False
    )
    frame = solve_frame_potential(bias_set, structure_area, env)
    rows = element_rows(bias_set, frame, env)
    if structure_area > 0.0:
        unbiased_frame = solve_frame_potential(
            [dict(e, exposed_area_m2=0.0) for e in bias_set],
            structure_area,
            env,
        )
        frame_shift = frame - unbiased_frame
    else:
        unbiased_frame = None
        frame_shift = None
    findings = assess_bias_disturbance(rows, frame, limits)
    return {
        "element_count": len(bias_set),
        "frame_potential_v": frame,
        "unbiased_frame_potential_v": unbiased_frame,
        "frame_shift_v": frame_shift,
        "debye_length_m": debye_length_m(env),
        "elements": rows,
        "findings": findings,
        "compliant": not findings,
    }


def summarize_findings(report):
    """Count findings by kind for the disturbance summary table."""
    if not isinstance(report, dict) or "findings" not in report:
        raise ValueError(
            "report must be the mapping returned by "
            "analyze_biased_surface_potentials"
        )
    counts = {}
    for finding in report["findings"]:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1
    return counts
