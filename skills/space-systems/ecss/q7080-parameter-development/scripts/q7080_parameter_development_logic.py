"""Process-parameter development for one material in powder-bed additive manufacturing.

Anchor: ECSS-Q-ST-70-80 process clauses covering the development of build
parameters per material, with density as the optimisation objective.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the campaign material and the reference (fully dense) density that
   every coupon result is normalised against.
2. For each trial, validate the four primary parameters (beam power, scan
   speed, hatch spacing, layer thickness) and form the volumetric energy
   density E = P / (v * h * t) and the linear energy density P / v.
3. Convert the measured coupon density into a relative density and a porosity
   fraction, and group the trial as lack-of-fusion, stable or keyhole against
   the declared energy band for the material.
4. Keep the highest relative density trial that sits inside the stable band and
   meets the declared target, breaking ties towards the lower energy density so
   the released set is the least aggressive one that works.
5. Raise campaign findings: too few trials to be a development matrix, an
   explored energy span that never brackets the optimum, and a selected
   optimum that sits on an edge of the explored span.
"""

import math

__all__ = [
    "DENSITY_TOLERANCE_PCT",
    "MIN_TRIALS",
    "MIN_DISTINCT_ENERGY_POINTS",
    "validate_parameters",
    "volumetric_energy_density",
    "linear_energy_density",
    "validate_energy_band",
    "categorize_regime",
    "relative_density_pct",
    "porosity_pct",
    "evaluate_trial",
    "evaluate_campaign",
    "select_parameter_set",
    "bracketing_findings",
    "develop_parameters",
]

# Relative density is a ratio of two measured masses carried through a
# division; an exactly-on-target coupon can land a few units in the last place
# on the wrong side. Absorb that here instead of moving the target.
DENSITY_TOLERANCE_PCT = 1e-9

# Energy-band edges are compared against a quotient of four parameters, so the
# same representation argument applies to the regime boundaries.
ENERGY_TOLERANCE = 1e-9

# A development matrix is a matrix. Below this many trials, or this many
# distinct energy points, the campaign has not explored anything.
MIN_TRIALS = 4
MIN_DISTINCT_ENERGY_POINTS = 3

PARAMETER_KEYS = (
    "beam_power_w",
    "scan_speed_mm_s",
    "hatch_spacing_mm",
    "layer_thickness_mm",
)


def _positive(label, value):
    """Return value as a positive finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_parameters(parameters):
    """Return the validated four primary build parameters as floats."""
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping")
    validated = {}
    for key in PARAMETER_KEYS:
        if key not in parameters:
            raise ValueError("parameters missing required key '%s'" % key)
        validated[key] = _positive(key, parameters[key])
    return validated


def volumetric_energy_density(parameters):
    """Return the volumetric energy density in J/mm^3 for a parameter set."""
    values = validate_parameters(parameters)
    return values["beam_power_w"] / (
        values["scan_speed_mm_s"]
        * values["hatch_spacing_mm"]
        * values["layer_thickness_mm"]
    )


def linear_energy_density(parameters):
    """Return the linear energy density in J/mm for a parameter set."""
    values = validate_parameters(parameters)
    return values["beam_power_w"] / values["scan_speed_mm_s"]


def validate_energy_band(band):
    """Return the validated (low, high) stable energy band in J/mm^3."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("energy band must be a (low, high) pair in J/mm^3")
    low = _positive("energy band low", band[0])
    high = _positive("energy band high", band[1])
    if low >= high:
        raise ValueError("energy band low %g must be below high %g" % (low, high))
    return (low, high)


def categorize_regime(energy_density, band):
    """Group an energy density as lack-of-fusion, stable or keyhole."""
    low, high = validate_energy_band(band)
    value = _positive("energy_density", energy_density)
    if math.isclose(value, low, rel_tol=ENERGY_TOLERANCE, abs_tol=0.0):
        return "stable"
    if math.isclose(value, high, rel_tol=ENERGY_TOLERANCE, abs_tol=0.0):
        return "stable"
    if value < low:
        return "lack-of-fusion"
    if value > high:
        return "keyhole"
    return "stable"


def relative_density_pct(measured_density, reference_density):
    """Return the coupon density as a percentage of the fully dense reference."""
    measured = _positive("measured_density", measured_density)
    reference = _positive("reference_density", reference_density)
    ratio = 100.0 * measured / reference
    if ratio > 101.0:
        raise ValueError(
            "measured density %g exceeds the reference %g by more than a "
            "measurement tolerance; the reference or the units are wrong"
            % (measured, reference)
        )
    return ratio


def porosity_pct(relative_density):
    """Return the porosity percentage implied by a relative density."""
    if not isinstance(relative_density, (int, float)) or isinstance(relative_density, bool):
        raise ValueError("relative_density must be a real number")
    value = float(relative_density)
    if not math.isfinite(value) or value <= 0.0 or value > 101.0:
        raise ValueError("relative_density must be a plausible percentage, got %r" % (relative_density,))
    return max(0.0, 100.0 - value)


def evaluate_trial(trial, reference_density, band):
    """Evaluate one development trial and return its record."""
    if not isinstance(trial, dict):
        raise ValueError("trial must be a mapping")
    for key in ("id", "parameters", "measured_density"):
        if key not in trial:
            raise ValueError("trial missing required key '%s'" % key)
    identifier = trial["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("trial id must be a non-empty string")
    parameters = validate_parameters(trial["parameters"])
    energy = volumetric_energy_density(parameters)
    density = relative_density_pct(trial["measured_density"], reference_density)
    return {
        "id": identifier,
        "parameters": parameters,
        "volumetric_energy_density": energy,
        "linear_energy_density": linear_energy_density(parameters),
        "relative_density_pct": density,
        "porosity_pct": porosity_pct(density),
        "regime": categorize_regime(energy, band),
    }


def evaluate_campaign(trials, reference_density, band, material=None):
    """Evaluate every trial of a campaign, refusing a foreign material."""
    if not isinstance(trials, (list, tuple)) or not trials:
        raise ValueError("trials must be a non-empty sequence")
    records = []
    seen = set()
    for trial in trials:
        if isinstance(trial, dict) and material is not None and "material" in trial:
            if trial["material"] != material:
                raise ValueError(
                    "trial %r declares material %r, the campaign is for %r; "
                    "parameters are developed per material"
                    % (trial.get("id"), trial["material"], material)
                )
        record = evaluate_trial(trial, reference_density, band)
        if record["id"] in seen:
            raise ValueError("duplicate trial id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def select_parameter_set(records, target_relative_density_pct):
    """Return the stable-regime record that best meets the density target."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    target = _positive("target_relative_density_pct", target_relative_density_pct)
    if target > 100.0:
        raise ValueError("target_relative_density_pct cannot exceed 100")
    eligible = []
    for record in records:
        if record["regime"] != "stable":
            continue
        density = record["relative_density_pct"]
        if density > target or math.isclose(
            density, target, rel_tol=0.0, abs_tol=DENSITY_TOLERANCE_PCT
        ):
            eligible.append(record)
    if not eligible:
        return None
    best = eligible[0]
    for record in eligible[1:]:
        if math.isclose(
            record["relative_density_pct"],
            best["relative_density_pct"],
            rel_tol=1e-12,
            abs_tol=0.0,
        ):
            if record["volumetric_energy_density"] < best["volumetric_energy_density"]:
                best = record
        elif record["relative_density_pct"] > best["relative_density_pct"]:
            best = record
    return best


def bracketing_findings(records, selected):
    """Return findings about the coverage of the explored energy span."""
    findings = []
    if len(records) < MIN_TRIALS:
        findings.append(
            "campaign ran %d trials; a development matrix needs at least %d"
            % (len(records), MIN_TRIALS)
        )
    energies = sorted(record["volumetric_energy_density"] for record in records)
    distinct = []
    for value in energies:
        if not distinct or not math.isclose(value, distinct[-1], rel_tol=1e-12, abs_tol=0.0):
            distinct.append(value)
    if len(distinct) < MIN_DISTINCT_ENERGY_POINTS:
        findings.append(
            "campaign explored %d distinct energy densities; at least %d are "
            "needed to bracket an optimum" % (len(distinct), MIN_DISTINCT_ENERGY_POINTS)
        )
    if selected is not None and len(distinct) > 1:
        energy = selected["volumetric_energy_density"]
        if math.isclose(energy, distinct[0], rel_tol=1e-12, abs_tol=0.0) or math.isclose(
            energy, distinct[-1], rel_tol=1e-12, abs_tol=0.0
        ):
            findings.append(
                "selected trial %s sits on an edge of the explored energy span "
                "[%.3f, %.3f] J/mm^3; the optimum is not bracketed"
                % (selected["id"], distinct[0], distinct[-1])
            )
    return findings


def develop_parameters(spec):
    """Run the full per-material parameter-development assessment.

    spec keys: material, reference_density, energy_band, trials,
    target_relative_density_pct.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("material", "reference_density", "energy_band", "trials",
                "target_relative_density_pct"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    material = spec["material"]
    if not isinstance(material, str) or not material.strip():
        raise ValueError("material must be a non-empty string")
    band = validate_energy_band(spec["energy_band"])
    records = evaluate_campaign(
        spec["trials"], spec["reference_density"], band, material=material
    )
    selected = select_parameter_set(records, spec["target_relative_density_pct"])
    findings = bracketing_findings(records, selected)
    if selected is None:
        findings.insert(
            0,
            "no stable-regime trial reached the %g%% relative-density target"
            % float(spec["target_relative_density_pct"]),
        )
    return {
        "material": material,
        "energy_band": band,
        "records": records,
        "selected": selected,
        "achieved_relative_density_pct": (
            None if selected is None else selected["relative_density_pct"]
        ),
        "findings": findings,
        "released": selected is not None and not findings,
    }
