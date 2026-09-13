#!/usr/bin/env python3
"""Material-characterization waiver by assembly evidence.

Anchor: ECSS-E-ST-20-06C clause 6.6.2 (paraphrased into an implementable
procedure; no standard text is reproduced).

Decision implemented here: an individual material would normally be
characterized on coupons for its charging-relevant electrical parameters.
That coupon campaign may be dropped only where an assembly-level
qualification campaign already exercises the same material, in the same
as-flown configuration, under an environment that bounds the flight
exposure, with instrumentation that actually observes every parameter the
coupon campaign would have delivered.

Deterministic, offline, stdlib only.
"""

import math

# Relative tolerance used to absorb floating-point representation error when
# an envelope axis is compared against a flight value. It is NOT an
# engineering allowance: an exact match is compliant, and this only prevents
# a few ULPs of stored-value error from reading as a shortfall.
REPR_TOL = 1e-9

# Charging-relevant material parameters and the instrumentation channel an
# assembly-level campaign must carry to deliver each one.
PARAMETER_INSTRUMENTATION = {
    "bulk-resistivity": "through-thickness-current-monitor",
    "surface-resistivity": "surface-current-monitor",
    "radiation-induced-conductivity": "through-thickness-current-monitor",
    "relative-permittivity": "capacitance-bridge",
    "dielectric-strength": "breakdown-voltage-monitor",
    "secondary-electron-yield": "electron-beam-current-monitor",
    "photoemission-yield": "calibrated-uv-source",
}

# Campaign levels and whether they may carry a characterization waiver.
CAMPAIGN_LEVELS = {
    "qualification": True,
    "protoflight": True,
    "acceptance": False,
    "development": False,
    "engineering-model": False,
}

# Environment axes that must reach or exceed the flight value.
ENVELOPE_AXES = (
    "electron-energy-kev",
    "particle-flux-a-per-m2",
    "exposure-duration-h",
    "applied-bias-v",
)


def _as_float(value, label):
    """Coerce to float or raise ValueError naming the offending field."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _covers(envelope_value, flight_value):
    """True when envelope_value >= flight_value, exact match included."""
    if envelope_value >= flight_value:
        return True
    return math.isclose(envelope_value, flight_value, rel_tol=REPR_TOL, abs_tol=0.0)


def normalize_parameter(token):
    """Canonicalize a charging-relevant parameter token.

    Raises ValueError for an unrecognized parameter.
    """
    if not isinstance(token, str) or not token.strip():
        raise ValueError("parameter token must be a non-empty string, got %r" % (token,))
    key = token.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in PARAMETER_INSTRUMENTATION:
        raise ValueError(
            "unrecognized charging parameter %r (known: %s)"
            % (token, ", ".join(sorted(PARAMETER_INSTRUMENTATION)))
        )
    return key


def normalize_environment(env, label):
    """Validate an environment record and return it with float values.

    Requires every axis in ENVELOPE_AXES plus a temperature band
    (temperature-min-c, temperature-max-c). Raises ValueError on a missing
    axis, a negative magnitude, or an inverted temperature band.
    """
    if not isinstance(env, dict):
        raise ValueError("%s environment must be a mapping, got %r" % (label, type(env).__name__))
    out = {}
    for axis in ENVELOPE_AXES:
        if axis not in env:
            raise ValueError("%s environment missing axis %r" % (label, axis))
        value = _as_float(env[axis], "%s.%s" % (label, axis))
        if value < 0.0:
            raise ValueError("%s.%s must be non-negative, got %r" % (label, axis, value))
        out[axis] = value
    for axis in ("temperature-min-c", "temperature-max-c"):
        if axis not in env:
            raise ValueError("%s environment missing axis %r" % (label, axis))
        out[axis] = _as_float(env[axis], "%s.%s" % (label, axis))
    if out["temperature-min-c"] > out["temperature-max-c"]:
        raise ValueError(
            "%s temperature band inverted: min %.3f > max %.3f"
            % (label, out["temperature-min-c"], out["temperature-max-c"])
        )
    return out


def normalize_campaign(campaign):
    """Validate an assembly-level campaign record.

    Keys: id, level, environment (mapping), instrumentation (list).
    Raises ValueError on an unknown level or empty instrumentation.
    """
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (type(campaign).__name__,))
    ident = campaign.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("campaign id must be a non-empty string, got %r" % (ident,))
    level = campaign.get("level")
    if not isinstance(level, str) or level.strip().lower() not in CAMPAIGN_LEVELS:
        raise ValueError(
            "unknown campaign level %r (known: %s)"
            % (level, ", ".join(sorted(CAMPAIGN_LEVELS)))
        )
    level = level.strip().lower()
    instrumentation = campaign.get("instrumentation")
    if not isinstance(instrumentation, (list, tuple)) or not instrumentation:
        raise ValueError("campaign %s carries no instrumentation channels" % ident)
    channels = set()
    for chan in instrumentation:
        if not isinstance(chan, str) or not chan.strip():
            raise ValueError("instrumentation channel must be a non-empty string, got %r" % (chan,))
        channels.add(chan.strip().lower())
    return {
        "id": ident.strip(),
        "level": level,
        "waiver-capable-level": CAMPAIGN_LEVELS[level],
        "environment": normalize_environment(campaign.get("environment"), "campaign %s" % ident),
        "instrumentation": channels,
    }


def normalize_material(material):
    """Validate one material record.

    Keys: id, parameters (list), thickness-mm, assembly-thickness-mm,
    thickness-tolerance-frac, surface-treatment, assembly-surface-treatment,
    flight-environment (mapping), exposed-outside-assembly (bool).
    """
    if not isinstance(material, dict):
        raise ValueError("material must be a mapping, got %r" % (type(material).__name__,))
    ident = material.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("material id must be a non-empty string, got %r" % (ident,))
    raw_params = material.get("parameters")
    if not isinstance(raw_params, (list, tuple)) or not raw_params:
        raise ValueError("material %s declares no charging parameters" % ident)
    params = []
    for token in raw_params:
        key = normalize_parameter(token)
        if key not in params:
            params.append(key)
    flight_thk = _as_float(material.get("thickness-mm"), "material %s thickness-mm" % ident)
    assy_thk = _as_float(
        material.get("assembly-thickness-mm"), "material %s assembly-thickness-mm" % ident
    )
    if flight_thk <= 0.0 or assy_thk <= 0.0:
        raise ValueError("material %s thicknesses must be positive" % ident)
    tol = _as_float(
        material.get("thickness-tolerance-frac", 0.05),
        "material %s thickness-tolerance-frac" % ident,
    )
    if not 0.0 <= tol < 1.0:
        raise ValueError("material %s thickness-tolerance-frac must be in [0, 1)" % ident)
    treat = material.get("surface-treatment")
    assy_treat = material.get("assembly-surface-treatment")
    for label, value in (("surface-treatment", treat), ("assembly-surface-treatment", assy_treat)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("material %s %s must be a non-empty string" % (ident, label))
    outside = material.get("exposed-outside-assembly", False)
    if not isinstance(outside, bool):
        raise ValueError("material %s exposed-outside-assembly must be a boolean" % ident)
    return {
        "id": ident.strip(),
        "parameters": sorted(params),
        "thickness-mm": flight_thk,
        "assembly-thickness-mm": assy_thk,
        "thickness-tolerance-frac": tol,
        "surface-treatment": treat.strip().lower(),
        "assembly-surface-treatment": assy_treat.strip().lower(),
        "exposed-outside-assembly": outside,
        "flight-environment": normalize_environment(
            material.get("flight-environment"), "material %s flight" % ident
        ),
    }


def configuration_findings(material):
    """Return the list of configuration mismatches for one normalized material."""
    findings = []
    flight_thk = material["thickness-mm"]
    assy_thk = material["assembly-thickness-mm"]
    tol = material["thickness-tolerance-frac"]
    deviation = abs(assy_thk - flight_thk) / flight_thk
    allowed = tol
    if deviation > allowed and not math.isclose(deviation, allowed, rel_tol=REPR_TOL, abs_tol=0.0):
        findings.append(
            "thickness deviation %.4f exceeds build tolerance %.4f" % (deviation, allowed)
        )
    if material["surface-treatment"] != material["assembly-surface-treatment"]:
        findings.append(
            "surface-treatment mismatch: flight %r vs assembly %r"
            % (material["surface-treatment"], material["assembly-surface-treatment"])
        )
    return findings


def envelope_margins(campaign_env, flight_env):
    """Per-axis margin of an assembly envelope over a flight exposure.

    Positive or zero = covered. Temperature is reported as the cold-side and
    hot-side extension of the campaign band beyond the flight band.
    """
    margins = {}
    for axis in ENVELOPE_AXES:
        margins[axis] = campaign_env[axis] - flight_env[axis]
    margins["temperature-cold-margin-c"] = (
        flight_env["temperature-min-c"] - campaign_env["temperature-min-c"]
    )
    margins["temperature-hot-margin-c"] = (
        campaign_env["temperature-max-c"] - flight_env["temperature-max-c"]
    )
    return margins


def envelope_findings(campaign_env, flight_env):
    """Return the list of axes where the campaign fails to bound the flight case."""
    findings = []
    for axis in ENVELOPE_AXES:
        if not _covers(campaign_env[axis], flight_env[axis]):
            findings.append(
                "%s shortfall: campaign %.6g < flight %.6g"
                % (axis, campaign_env[axis], flight_env[axis])
            )
    if not _covers(flight_env["temperature-min-c"], campaign_env["temperature-min-c"]):
        findings.append(
            "cold-end shortfall: campaign %.6g C does not reach flight %.6g C"
            % (campaign_env["temperature-min-c"], flight_env["temperature-min-c"])
        )
    if not _covers(campaign_env["temperature-max-c"], flight_env["temperature-max-c"]):
        findings.append(
            "hot-end shortfall: campaign %.6g C does not reach flight %.6g C"
            % (campaign_env["temperature-max-c"], flight_env["temperature-max-c"])
        )
    return findings


def parameter_coverage(parameters, instrumentation):
    """Split required parameters into observed and unobserved by channel."""
    observed = []
    unobserved = []
    for key in parameters:
        channel = PARAMETER_INSTRUMENTATION[normalize_parameter(key)]
        if channel in instrumentation:
            observed.append(key)
        else:
            unobserved.append(key)
    return sorted(observed), sorted(unobserved)


def evaluate_material_waiver(material, campaign):
    """Decide the coupon-characterization waiver for one material.

    Returns a mapping with the waiver decision, the blocking findings and the
    residual parameters still owed to the programme.
    """
    mat = normalize_material(material)
    camp = campaign if isinstance(campaign, dict) and "waiver-capable-level" in campaign else normalize_campaign(campaign)
    findings = []
    if not camp["waiver-capable-level"]:
        findings.append("campaign level %r cannot carry a waiver" % camp["level"])
    findings.extend(configuration_findings(mat))
    findings.extend(envelope_findings(camp["environment"], mat["flight-environment"]))
    if mat["exposed-outside-assembly"]:
        findings.append("material also exposed outside the tested assembly boundary")
    observed, unobserved = parameter_coverage(mat["parameters"], camp["instrumentation"])
    for key in unobserved:
        findings.append(
            "parameter %s has no instrumentation channel (%s) in the campaign"
            % (key, PARAMETER_INSTRUMENTATION[key])
        )
    granted = not findings
    residual = [] if granted else list(mat["parameters"])
    return {
        "material": mat["id"],
        "campaign": camp["id"],
        "waiver": "granted" if granted else "refused",
        "findings": findings,
        "observed-parameters": observed,
        "residual-parameters": sorted(residual),
        "margins": envelope_margins(camp["environment"], mat["flight-environment"]),
    }


def assess_characterization_programme(campaign, materials):
    """Aggregate the waiver decision across every material in one campaign.

    Returns the per-material results, the residual coupon matrix, and a
    complete flag that is True only when the residual matrix is empty.
    """
    camp = normalize_campaign(campaign)
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("materials must be a non-empty list")
    seen = set()
    results = []
    residual = {}
    for entry in materials:
        result = evaluate_material_waiver(entry, camp)
        if result["material"] in seen:
            raise ValueError("duplicate material id %r" % result["material"])
        seen.add(result["material"])
        results.append(result)
        if result["residual-parameters"]:
            residual[result["material"]] = result["residual-parameters"]
    return {
        "campaign": camp["id"],
        "level": camp["level"],
        "results": results,
        "residual-matrix": residual,
        "waived": sorted(r["material"] for r in results if r["waiver"] == "granted"),
        "complete": not residual,
    }
