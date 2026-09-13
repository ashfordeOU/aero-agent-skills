#!/usr/bin/env python3
"""Secondary-emission property selection for the second multipactor-analysis
level (ECSS-E-ST-20-01C clause 5.3.2.3.2).

Offline, deterministic, stdlib only.  Screens candidate secondary-electron-
yield datasets against the electrode material, the flight surface condition,
the representative temperature and the impact-energy range of the tracked
electrons, then picks the most conservative qualifying dataset and checks the
declared cross-over energies against the yield-curve model.

Paraphrased procedure only; the standard clause is the anchor, not the text.
"""

from __future__ import annotations

import math

__all__ = [
    "CONDITION_RANK",
    "MATERIALS",
    "DEFAULT_TEMPERATURE_WINDOW_C",
    "DEFAULT_CROSSOVER_TOLERANCE",
    "normalize_material",
    "normalize_surface_condition",
    "validate_yield_dataset",
    "secondary_yield_at",
    "unity_crossover_energies",
    "check_crossover_consistency",
    "condition_is_representative",
    "covers_energy_range",
    "temperature_is_representative",
    "screen_yield_datasets",
    "conservatism_key",
    "select_yield_dataset",
    "assess_material_criteria",
]

# Surface condition ordered by how much conditioning the surface has had.
# A cleaner surface emits fewer secondaries, so a dataset measured on a
# surface cleaner than the flight surface is optimistic and is not usable.
CONDITION_RANK = {
    "as-received": 0,
    "air-exposed": 1,
    "solvent-cleaned": 2,
    "vacuum-baked": 3,
    "electron-conditioned": 4,
    "atomically-clean": 5,
}

MATERIALS = (
    "silver",
    "gold",
    "aluminium",
    "alodine-coated-aluminium",
    "silver-plated-aluminium",
    "gold-plated-copper",
    "copper",
    "stainless-steel",
    "titanium",
)

_MATERIAL_ALIASES = {
    "aluminum": "aluminium",
    "ag": "silver",
    "au": "gold",
    "cu": "copper",
    "ti": "titanium",
    "alodine-aluminium": "alodine-coated-aluminium",
    "alodine-aluminum": "alodine-coated-aluminium",
}

_CONDITION_ALIASES = {
    "unconditioned": "as-received",
    "air-contaminated": "air-exposed",
    "baked": "vacuum-baked",
    "conditioned": "electron-conditioned",
    "sputter-cleaned": "atomically-clean",
}

DEFAULT_TEMPERATURE_WINDOW_C = 40.0
DEFAULT_CROSSOVER_TOLERANCE = 0.10  # relative agreement with the curve model
COMPARISON_TOLERANCE = 1e-9

_DATASET_KEYS = (
    "dataset_id",
    "material",
    "surface_condition",
    "sigma_max",
    "e_max_ev",
    "e1_ev",
    "e2_ev",
    "temperature_c",
    "energy_range_ev",
)

_TARGET_KEYS = (
    "material",
    "surface_condition",
    "temperature_c",
    "impact_energy_range_ev",
)


def _at_least(value, limit):
    """Inclusive >= that absorbs float representation error."""
    return value > limit or math.isclose(
        value, limit, rel_tol=COMPARISON_TOLERANCE, abs_tol=COMPARISON_TOLERANCE
    )


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _real(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _normalize_token(raw, label):
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (label, raw))
    key = raw.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in key:
        key = key.replace("--", "-")
    if not key:
        raise ValueError("%s must not be blank" % label)
    return key


def normalize_material(raw):
    """Fold a free-form electrode-material label onto a known material."""
    key = _normalize_token(raw, "material")
    key = _MATERIAL_ALIASES.get(key, key)
    if key not in MATERIALS:
        raise ValueError("unknown electrode material %r" % (raw,))
    return key


def normalize_surface_condition(raw):
    """Fold a free-form surface-condition label onto a ranked condition."""
    key = _normalize_token(raw, "surface_condition")
    key = _CONDITION_ALIASES.get(key, key)
    if key not in CONDITION_RANK:
        raise ValueError("unknown surface condition %r" % (raw,))
    return key


def validate_yield_dataset(dataset):
    """Structurally and physically validate one yield dataset record."""
    if not isinstance(dataset, dict):
        raise ValueError("yield dataset must be a mapping, got %r" % (dataset,))
    for key in _DATASET_KEYS:
        if key not in dataset:
            raise ValueError("yield dataset missing required key %r" % (key,))
    if not isinstance(dataset["dataset_id"], str) or not dataset["dataset_id"].strip():
        raise ValueError("dataset_id must be a non-blank string")
    material = normalize_material(dataset["material"])
    condition = normalize_surface_condition(dataset["surface_condition"])
    sigma_max = _positive(dataset["sigma_max"], "sigma_max")
    if sigma_max <= 1.0:
        raise ValueError(
            "sigma_max %r does not exceed unity, so no cross-over energy exists"
            % (dataset["sigma_max"],)
        )
    e1 = _positive(dataset["e1_ev"], "e1_ev")
    e_max = _positive(dataset["e_max_ev"], "e_max_ev")
    e2 = _positive(dataset["e2_ev"], "e2_ev")
    if not e1 < e_max:
        raise ValueError("e1_ev %r must sit below e_max_ev %r" % (e1, e_max))
    if not e_max < e2:
        raise ValueError("e_max_ev %r must sit below e2_ev %r" % (e_max, e2))
    rng = dataset["energy_range_ev"]
    if not isinstance(rng, (list, tuple)) or len(rng) != 2:
        raise ValueError("energy_range_ev must be a two-element sequence")
    low = _real(rng[0], "energy_range_ev[0]")
    high = _real(rng[1], "energy_range_ev[1]")
    if low < 0.0:
        raise ValueError("energy_range_ev lower bound must not be negative")
    if not low < high:
        raise ValueError("energy_range_ev must be increasing, got %r" % (rng,))
    threshold = _real(dataset.get("threshold_energy_ev", 0.0), "threshold_energy_ev")
    if threshold < 0.0 or threshold >= e_max:
        raise ValueError("threshold_energy_ev must sit in [0, e_max_ev)")
    return {
        "dataset_id": dataset["dataset_id"].strip(),
        "material": material,
        "surface_condition": condition,
        "sigma_max": sigma_max,
        "e_max_ev": e_max,
        "e1_ev": e1,
        "e2_ev": e2,
        "temperature_c": _real(dataset["temperature_c"], "temperature_c"),
        "energy_range_ev": (low, high),
        "threshold_energy_ev": threshold,
    }


def _yield_from_record(record, energy):
    """Vaughan-form yield evaluation on an already validated record."""
    e0 = record["threshold_energy_ev"]
    if energy <= e0:
        return 0.0
    v = (energy - e0) / (record["e_max_ev"] - e0)
    if v > 3.6:
        return record["sigma_max"] * 1.125 / (v ** 0.35)
    k = 0.56 if v <= 1.0 else 0.25
    return record["sigma_max"] * ((v * math.exp(1.0 - v)) ** k)


def secondary_yield_at(dataset, impact_energy_ev):
    """Secondary-electron-yield at an impact energy, from the curve model."""
    record = validate_yield_dataset(dataset)
    energy = _real(impact_energy_ev, "impact_energy_ev")
    if energy < 0.0:
        raise ValueError("impact_energy_ev must not be negative, got %r" % (energy,))
    return _yield_from_record(record, energy)


def _bisect_unity(record, low, high, rising, iterations=200):
    """Bisect a monotone branch of the yield curve for the unity crossing."""
    lo, hi = float(low), float(high)
    for _ in range(iterations):
        if hi - lo < 1e-10:
            break
        mid = 0.5 * (lo + hi)
        below = _yield_from_record(record, mid) < 1.0
        if (rising and below) or (not rising and not below):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def unity_crossover_energies(dataset):
    """Model first and second cross-over energies of the yield curve."""
    record = validate_yield_dataset(dataset)
    e0 = record["threshold_energy_ev"]
    e_max = record["e_max_ev"]
    first = _bisect_unity(record, e0 + 1e-9, e_max, rising=True)
    upper = e_max * 2.0
    for _ in range(80):
        if _yield_from_record(record, upper) < 1.0:
            break
        upper *= 2.0
    else:
        raise ValueError("yield curve never returns below unity below the search cap")
    second = _bisect_unity(record, e_max, upper, rising=False)
    return (first, second)


def check_crossover_consistency(dataset, tolerance=DEFAULT_CROSSOVER_TOLERANCE):
    """Compare declared cross-over energies against the curve model."""
    record = validate_yield_dataset(dataset)
    tol = _positive(tolerance, "tolerance")
    model_e1, model_e2 = unity_crossover_energies(dataset)
    dev1 = abs(record["e1_ev"] - model_e1) / model_e1
    dev2 = abs(record["e2_ev"] - model_e2) / model_e2
    consistent = _at_least(tol, dev1) and _at_least(tol, dev2)
    return {
        "dataset_id": record["dataset_id"],
        "model_e1_ev": model_e1,
        "model_e2_ev": model_e2,
        "relative_deviation_e1": dev1,
        "relative_deviation_e2": dev2,
        "consistent": consistent,
    }


def condition_is_representative(dataset_condition, flight_condition):
    """True when the dataset surface is no cleaner than the flight surface."""
    ds_rank = CONDITION_RANK[normalize_surface_condition(dataset_condition)]
    fl_rank = CONDITION_RANK[normalize_surface_condition(flight_condition)]
    return ds_rank <= fl_rank


def covers_energy_range(dataset, impact_low_ev, impact_high_ev):
    """True when the measured energy span covers the tracked impact energies."""
    record = validate_yield_dataset(dataset)
    low = _real(impact_low_ev, "impact_low_ev")
    high = _real(impact_high_ev, "impact_high_ev")
    if low < 0.0:
        raise ValueError("impact_low_ev must not be negative")
    if not low < high:
        raise ValueError("impact energy range must be increasing")
    ds_low, ds_high = record["energy_range_ev"]
    return _at_least(low, ds_low) and _at_least(ds_high, high)


def temperature_is_representative(
    dataset, flight_temperature_c, window_c=DEFAULT_TEMPERATURE_WINDOW_C
):
    """True when the dataset temperature sits inside the flight window."""
    record = validate_yield_dataset(dataset)
    flight = _real(flight_temperature_c, "flight_temperature_c")
    window = _positive(window_c, "window_c")
    return _at_least(window, abs(record["temperature_c"] - flight))


def _validate_target(target):
    if not isinstance(target, dict):
        raise ValueError("target surface must be a mapping, got %r" % (target,))
    for key in _TARGET_KEYS:
        if key not in target:
            raise ValueError("target surface missing required key %r" % (key,))
    rng = target["impact_energy_range_ev"]
    if not isinstance(rng, (list, tuple)) or len(rng) != 2:
        raise ValueError("impact_energy_range_ev must be a two-element sequence")
    return {
        "material": normalize_material(target["material"]),
        "surface_condition": normalize_surface_condition(target["surface_condition"]),
        "temperature_c": _real(target["temperature_c"], "temperature_c"),
        "impact_energy_range_ev": (
            _real(rng[0], "impact_energy_range_ev[0]"),
            _real(rng[1], "impact_energy_range_ev[1]"),
        ),
        "temperature_window_c": _positive(
            target.get("temperature_window_c", DEFAULT_TEMPERATURE_WINDOW_C),
            "temperature_window_c",
        ),
    }


def screen_yield_datasets(candidates, target):
    """Split candidate datasets into accepted and rejected, with reasons."""
    if not isinstance(candidates, (list, tuple)):
        raise ValueError("candidates must be a list of yield datasets")
    if len(candidates) == 0:
        raise ValueError("candidates must contain at least one yield dataset")
    goal = _validate_target(target)
    low, high = goal["impact_energy_range_ev"]
    accepted, rejected = [], []
    seen = set()
    for candidate in candidates:
        record = validate_yield_dataset(candidate)
        if record["dataset_id"] in seen:
            raise ValueError("duplicate dataset_id %r" % (record["dataset_id"],))
        seen.add(record["dataset_id"])
        reasons = []
        if record["material"] != goal["material"]:
            reasons.append("electrode-material-mismatch")
        if not condition_is_representative(
            record["surface_condition"], goal["surface_condition"]
        ):
            reasons.append("surface-condition-cleaner-than-flight")
        if not covers_energy_range(candidate, low, high):
            reasons.append("impact-energy-range-not-covered")
        if not temperature_is_representative(
            candidate, goal["temperature_c"], goal["temperature_window_c"]
        ):
            reasons.append("temperature-outside-window")
        if reasons:
            rejected.append({"dataset_id": record["dataset_id"], "reasons": reasons})
        else:
            accepted.append(record)
    return {"accepted": accepted, "rejected": rejected}


def conservatism_key(record):
    """Sort key: lowest first-crossover-energy, then highest peak yield."""
    return (record["e1_ev"], -record["sigma_max"], record["dataset_id"])


def select_yield_dataset(candidates, target):
    """Pick the most conservative qualifying dataset for the target surface."""
    screened = screen_yield_datasets(candidates, target)
    accepted = sorted(screened["accepted"], key=conservatism_key)
    findings = []
    selected = accepted[0] if accepted else None
    if selected is None:
        findings.append("no-representative-yield-dataset")
    return {
        "selected": selected,
        "ranked": [r["dataset_id"] for r in accepted],
        "rejected": screened["rejected"],
        "fallback_required": selected is None,
        "findings": findings,
    }


def assess_material_criteria(
    candidates, target, crossover_tolerance=DEFAULT_CROSSOVER_TOLERANCE
):
    """Full clause-5.3.2.3.2 verdict for one susceptible surface."""
    result = select_yield_dataset(candidates, target)
    findings = list(result["findings"])
    consistency = None
    if result["selected"] is not None:
        source = None
        for candidate in candidates:
            if str(candidate.get("dataset_id", "")).strip() == result["selected"]["dataset_id"]:
                source = candidate
                break
        consistency = check_crossover_consistency(source, tolerance=crossover_tolerance)
        if not consistency["consistent"]:
            findings.append("declared-crossover-energies-inconsistent-with-curve")
    return {
        "selected_dataset_id": (
            result["selected"]["dataset_id"] if result["selected"] else None
        ),
        "ranked": result["ranked"],
        "rejected": result["rejected"],
        "crossover_consistency": consistency,
        "fallback_required": result["fallback_required"],
        "findings": findings,
        "compliant": not findings,
    }
