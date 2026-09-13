#!/usr/bin/env python3
"""Secondary emission data selection for a multipactor-critical part material.

Anchor: ECSS-E-ST-20-01C clause 5.3.3.3. The procedure below is a paraphrased,
implementable restatement -- no verbatim standard text. Offline, deterministic,
Python standard library only.

A multipactor analysis is only as good as the secondary-electron-yield curve
behind it. This module categorizes candidate datasets by provenance, tests each
one for representativeness against the part it is meant to describe, selects
the dataset the analysis must use, and falls back to the conservative standard
tabulated curve when nothing on offer represents the emitting surface.
"""

import math

__all__ = [
    "categorize_data_source",
    "validate_yield_dataset",
    "interpolate_yield",
    "yield_above_unity_window",
    "representativeness_findings",
    "is_representative",
    "conservatism_key",
    "more_conservative",
    "select_yield_dataset",
    "assess_part_data",
    "assess_part_set",
]

# Provenance tiers: lower is stronger evidence about the actual emitting
# surface. The tier orders selection; it never overrides representativeness.
SOURCE_TIERS = {
    "flight-lot-sample-measurement": 1,
    "representative-coupon-measurement": 2,
    "standard-tabulated-dataset": 3,
    "supplier-datasheet": 4,
    "open-literature": 5,
}

SOURCE_FAMILIES = {
    "flight-lot-sample-measurement": "measured",
    "representative-coupon-measurement": "measured",
    "standard-tabulated-dataset": "standard",
    "supplier-datasheet": "declared",
    "open-literature": "declared",
}

# Absorbs the representation error of an energy bound built as a sum or a
# product of decimal values; it never widens the coverage requirement itself.
ENERGY_REL_TOL = 1e-9


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def categorize_data_source(source):
    """Return the provenance family and tier of a data source.

    An unrecognised source is rejected: an uncategorized provenance cannot be
    ranked against the others and must not enter the selection silently.
    """
    key = _token(source, "source")
    if key not in SOURCE_TIERS:
        raise ValueError("unrecognized secondary-emission data source: %r" % (source,))
    return {"source": key, "family": SOURCE_FAMILIES[key], "tier": SOURCE_TIERS[key]}


def validate_yield_dataset(dataset):
    """Normalize one secondary-electron-yield dataset, raising on a bad curve.

    The dataset carries the emitting surface it describes (base-material,
    surface-treatment, surface-condition), its provenance, the peak yield, the
    two crossover energies where the yield passes unity, and the tabulated
    curve the analysis interpolates.
    """
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be a mapping, got %r" % type(dataset))
    provenance = categorize_data_source(dataset.get("source"))
    base_material = _token(dataset.get("base_material"), "base_material")
    surface_treatment = _token(dataset.get("surface_treatment"), "surface_treatment")
    surface_condition = _token(dataset.get("surface_condition"), "surface_condition")
    delta_max = _finite_number(dataset.get("delta_max"), "delta_max")
    if delta_max <= 0.0:
        raise ValueError("delta_max must be strictly positive, got %r" % (delta_max,))
    first_crossover = _finite_number(
        dataset.get("first_crossover_ev"), "first_crossover_ev"
    )
    second_crossover = _finite_number(
        dataset.get("second_crossover_ev"), "second_crossover_ev"
    )
    if first_crossover <= 0.0:
        raise ValueError("first_crossover_ev must be strictly positive")
    if second_crossover <= first_crossover:
        raise ValueError("second_crossover_ev must exceed first_crossover_ev")
    if delta_max <= 1.0:
        raise ValueError(
            "a curve with crossover energies must peak above unity yield, got %r"
            % (delta_max,)
        )
    curve = dataset.get("curve")
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("curve needs at least two (energy_ev, yield) points")
    points = []
    previous_energy = None
    for index, point in enumerate(curve):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("curve[%d] must be an (energy_ev, yield) pair" % index)
        energy = _finite_number(point[0], "curve[%d] energy_ev" % index)
        value = _finite_number(point[1], "curve[%d] yield" % index)
        if energy <= 0.0:
            raise ValueError("curve[%d] energy must be strictly positive" % index)
        if value < 0.0:
            raise ValueError("curve[%d] yield cannot be negative" % index)
        if previous_energy is not None and energy <= previous_energy:
            raise ValueError("curve energies must strictly increase (at index %d)" % index)
        previous_energy = energy
        points.append((energy, value))
    return {
        "source": provenance["source"],
        "family": provenance["family"],
        "tier": provenance["tier"],
        "base_material": base_material,
        "surface_treatment": surface_treatment,
        "surface_condition": surface_condition,
        "delta_max": delta_max,
        "first_crossover_ev": first_crossover,
        "second_crossover_ev": second_crossover,
        "curve": points,
        "energy_min_ev": points[0][0],
        "energy_max_ev": points[-1][0],
    }


def interpolate_yield(dataset, energy_ev):
    """Linearly interpolate the yield at a primary-electron energy.

    Extrapolation outside the tabulated span is refused: the curve shape past
    its last measured point is not knowledge the dataset carries. The endpoint
    comparison uses math.isclose so an energy built as a sum of decimals still
    counts as inside its own bound.
    """
    entry = dataset if "curve" in dataset and "energy_min_ev" in dataset else validate_yield_dataset(dataset)
    energy = _finite_number(energy_ev, "energy_ev")
    low = entry["energy_min_ev"]
    high = entry["energy_max_ev"]
    if energy < low and not math.isclose(energy, low, rel_tol=ENERGY_REL_TOL):
        raise ValueError(
            "energy %.6g eV is below the tabulated span (%.6g eV)" % (energy, low)
        )
    if energy > high and not math.isclose(energy, high, rel_tol=ENERGY_REL_TOL):
        raise ValueError(
            "energy %.6g eV is above the tabulated span (%.6g eV)" % (energy, high)
        )
    if energy <= low:
        return entry["curve"][0][1]
    if energy >= high:
        return entry["curve"][-1][1]
    points = entry["curve"]
    for index in range(1, len(points)):
        left_energy, left_yield = points[index - 1]
        right_energy, right_yield = points[index]
        if energy <= right_energy:
            span = right_energy - left_energy
            fraction = (energy - left_energy) / span
            return left_yield + fraction * (right_yield - left_yield)
    return points[-1][1]


def yield_above_unity_window(dataset):
    """Return the primary-energy window where the surface multiplies."""
    entry = validate_yield_dataset(dataset)
    return (entry["first_crossover_ev"], entry["second_crossover_ev"])


def representativeness_findings(part, dataset):
    """List every way a dataset fails to represent the part's emitting surface.

    An empty list means the dataset may be used as measured data for the part.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % type(part))
    entry = validate_yield_dataset(dataset)
    findings = []
    if _token(part.get("base_material"), "part base_material") != entry["base_material"]:
        findings.append("base-material-mismatch")
    treatment = _token(part.get("surface_treatment"), "part surface_treatment")
    if treatment != entry["surface_treatment"]:
        findings.append("surface-treatment-mismatch")
    condition = _token(part.get("surface_condition"), "part surface_condition")
    if condition != entry["surface_condition"]:
        findings.append("surface-condition-mismatch")
    required_low = _finite_number(part.get("energy_min_ev"), "part energy_min_ev")
    required_high = _finite_number(part.get("energy_max_ev"), "part energy_max_ev")
    if required_high <= required_low:
        raise ValueError("part energy_max_ev must exceed energy_min_ev")
    below = entry["energy_min_ev"] > required_low and not math.isclose(
        entry["energy_min_ev"], required_low, rel_tol=ENERGY_REL_TOL
    )
    above = entry["energy_max_ev"] < required_high and not math.isclose(
        entry["energy_max_ev"], required_high, rel_tol=ENERGY_REL_TOL
    )
    if below or above:
        findings.append("energy-coverage-short")
    return sorted(findings)


def is_representative(part, dataset):
    """True when the dataset describes this part's emitting surface."""
    return not representativeness_findings(part, dataset)


def conservatism_key(dataset):
    """Sort key placing the more conservative curve first.

    A curve is more conservative when it multiplies harder (higher peak yield)
    and starts multiplying earlier (lower first-crossover-energy).
    """
    entry = validate_yield_dataset(dataset)
    return (-entry["delta_max"], entry["first_crossover_ev"])


def more_conservative(left, right):
    """Return whichever of two datasets drives the harsher multipactor case."""
    return left if conservatism_key(left) <= conservatism_key(right) else right


def select_yield_dataset(part, candidates, fallback=None):
    """Pick the dataset the multipactor analysis must use for this part.

    Representative candidates win, best provenance tier first, the more
    conservative curve breaking a tie. With no representative candidate the
    standard tabulated fallback is applied; with no fallback either, the part
    has no usable secondary-emission data and the call fails.
    """
    if not isinstance(candidates, (list, tuple)):
        raise ValueError("candidates must be a list")
    representative = []
    for candidate in candidates:
        if is_representative(part, candidate):
            representative.append(validate_yield_dataset(candidate))
    if representative:
        representative.sort(key=lambda item: (item["tier"], conservatism_key(item)))
        chosen = representative[0]
        basis = "representative-" + chosen["family"]
        return {"dataset": chosen, "basis": basis, "findings": []}
    if fallback is None:
        raise ValueError(
            "no representative secondary-emission dataset and no standard fallback"
        )
    entry = validate_yield_dataset(fallback)
    if entry["family"] != "standard":
        raise ValueError(
            "fallback must be a standard tabulated dataset, got %r" % (entry["source"],)
        )
    findings = ["standard-fallback-applied"]
    findings.extend(
        "fallback-" + item for item in representativeness_findings(part, fallback)
    )
    return {"dataset": entry, "basis": "standard-fallback", "findings": sorted(findings)}


def assess_part_data(part, candidates, fallback=None):
    """Select the dataset for one part and grade the selection."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % type(part))
    name = part.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("part requires a non-empty name")
    selection = select_yield_dataset(part, candidates, fallback=fallback)
    entry = selection["dataset"]
    findings = list(selection["findings"])
    if entry["family"] == "declared":
        findings.append("provenance-not-measured-or-standard")
    window = (entry["first_crossover_ev"], entry["second_crossover_ev"])
    peak_yield = max(value for _, value in entry["curve"])
    if peak_yield > entry["delta_max"] and not math.isclose(
        peak_yield, entry["delta_max"], rel_tol=ENERGY_REL_TOL
    ):
        findings.append("curve-peak-exceeds-declared-delta-max")
    return {
        "name": name.strip(),
        "dataset": entry,
        "basis": selection["basis"],
        "multiplying_window_ev": window,
        "findings": sorted(findings),
        "data_accepted": not findings,
    }


def assess_part_set(parts, fallback=None):
    """Grade a set of parts; every entry carries its own candidate list."""
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("at least one part is required")
    results = []
    for item in parts:
        if not isinstance(item, dict):
            raise ValueError("each part entry must be a mapping")
        results.append(
            assess_part_data(
                item, item.get("candidates", []), fallback=item.get("fallback", fallback)
            )
        )
    names = [entry["name"] for entry in results]
    if len(set(names)) != len(names):
        raise ValueError("part names must be unique within a set")
    open_findings = sorted(
        "%s:%s" % (entry["name"], finding)
        for entry in results
        for finding in entry["findings"]
    )
    return {
        "parts": results,
        "fallback_parts": [
            entry["name"] for entry in results if entry["basis"] == "standard-fallback"
        ],
        "open_findings": open_findings,
        "set_accepted": not open_findings,
    }
