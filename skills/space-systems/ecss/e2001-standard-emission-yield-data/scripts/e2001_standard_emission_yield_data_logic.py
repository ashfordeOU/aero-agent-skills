#!/usr/bin/env python3
"""ECSS-E-ST-20-01C clause 9.6 -- tabulated emission-yield data fallback.

Deterministic, offline, stdlib-only implementation of the clause 9.6
fallback rule: when no representative measured secondary-electron-emission
yield record exists for a surface, the multipaction assessment uses the
tabulated experimental yield parameters held for the common spacecraft
metals, and declares that it did so.

The module resolves supplier material and surface-condition names onto
canonical table keys, assesses a measured record for representativeness,
selects the yield source (measured, tabulated fallback, or a refusal when
neither exists), evaluates the universal yield-curve shape, locates the
first and second crossover energies by bisection, and reports the
disposition at an impact energy.

Paraphrase only -- no ECSS text is reproduced. The tabulated parameters
below are house reference values for the common metals. Clause anchor:
ECSS-E-ST-20-01C 9.6.
"""

import math

AS_RECEIVED = "as-received"
SPUTTER_CLEANED = "sputter-cleaned"

# (material, surface-condition) -> peak yield and the impact energy at the
# peak, in electronvolts. House reference values for the common metals.
STANDARD_YIELD_TABLE = {
    ("aluminium", AS_RECEIVED): {"delta_max": 2.40, "e_max_ev": 300.0},
    ("aluminium", SPUTTER_CLEANED): {"delta_max": 0.95, "e_max_ev": 300.0},
    ("gold", AS_RECEIVED): {"delta_max": 1.75, "e_max_ev": 800.0},
    ("gold", SPUTTER_CLEANED): {"delta_max": 1.45, "e_max_ev": 800.0},
    ("silver", AS_RECEIVED): {"delta_max": 1.90, "e_max_ev": 800.0},
    ("silver", SPUTTER_CLEANED): {"delta_max": 1.50, "e_max_ev": 800.0},
    ("copper", AS_RECEIVED): {"delta_max": 1.90, "e_max_ev": 600.0},
    ("copper", SPUTTER_CLEANED): {"delta_max": 1.30, "e_max_ev": 600.0},
    ("nickel", AS_RECEIVED): {"delta_max": 1.60, "e_max_ev": 550.0},
    ("nickel", SPUTTER_CLEANED): {"delta_max": 1.30, "e_max_ev": 550.0},
    ("titanium", AS_RECEIVED): {"delta_max": 1.20, "e_max_ev": 280.0},
    ("titanium", SPUTTER_CLEANED): {"delta_max": 0.90, "e_max_ev": 280.0},
    ("magnesium", AS_RECEIVED): {"delta_max": 1.60, "e_max_ev": 300.0},
    ("magnesium", SPUTTER_CLEANED): {"delta_max": 0.95, "e_max_ev": 300.0},
    ("stainless-steel", AS_RECEIVED): {"delta_max": 2.10, "e_max_ev": 350.0},
    ("stainless-steel", SPUTTER_CLEANED): {"delta_max": 1.40, "e_max_ev": 350.0},
}

MATERIAL_ALIASES = {
    "aluminum": "aluminium",
    "al": "aluminium",
    "au": "gold",
    "ag": "silver",
    "cu": "copper",
    "ni": "nickel",
    "ti": "titanium",
    "mg": "magnesium",
    "cres": "stainless-steel",
    "stainless": "stainless-steel",
    "stainless-steel-304": "stainless-steel",
}

SURFACE_ALIASES = {
    "oxidized": AS_RECEIVED,
    "oxidised": AS_RECEIVED,
    "untreated": AS_RECEIVED,
    "cleaned": SPUTTER_CLEANED,
    "ion-cleaned": SPUTTER_CLEANED,
    "argon-sputtered": SPUTTER_CLEANED,
}

MEASURED = "measured"
TABULATED_FALLBACK = "tabulated-fallback"

# A record drawn from a single specimen is not representative of a batch.
MIN_SPECIMEN_COUNT = 2

# Universal yield-curve shape constants (normalized so the curve peaks at
# the tabulated peak yield at the tabulated peak energy).
CURVE_SCALE = 1.114
CURVE_LOW_EXPONENT = -0.35
CURVE_DECAY = 2.28
CURVE_HIGH_EXPONENT = 1.35

# Absorbs representation residue in unity comparisons and energy-span
# coverage. Not an engineering allowance.
UNITY_TOLERANCE = 1e-9
SPAN_REL_TOL = 1e-9

BISECTION_MAX_ITERATIONS = 200
BISECTION_REL_TOL = 1e-12
MIN_BRACKET_EV = 1e-3
MAX_BRACKET_FACTOR = 1.0e5


def normalize_token(raw, label):
    """Fold a supplier name onto a canonical lowercase hyphenated token."""
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (label, raw))
    token = raw.strip().lower().replace("_", "-")
    token = "-".join(part for part in token.split() if part)
    while "--" in token:
        token = token.replace("--", "-")
    token = token.strip("-")
    if not token:
        raise ValueError("%s is empty after normalization" % label)
    return token


def resolve_material(raw):
    """Resolve a supplier material name onto a canonical table material."""
    token = normalize_token(raw, "material")
    return MATERIAL_ALIASES.get(token, token)


def resolve_surface_condition(raw):
    """Resolve a surface-condition name onto a canonical table condition."""
    token = normalize_token(raw, "surface condition")
    token = SURFACE_ALIASES.get(token, token)
    if token not in (AS_RECEIVED, SPUTTER_CLEANED):
        raise ValueError("unrecognized surface condition %r" % (token,))
    return token


def tabulated_materials():
    """Sorted list of materials carried in the tabulated set."""
    return sorted({material for material, _ in STANDARD_YIELD_TABLE})


def lookup_tabulated_yield(material, surface_condition):
    """Fetch the tabulated parameters; refuse when there is no entry."""
    key = (resolve_material(material), resolve_surface_condition(surface_condition))
    entry = STANDARD_YIELD_TABLE.get(key)
    if entry is None:
        raise ValueError(
            "no tabulated yield entry for %s in %s condition; a measurement is required"
            % key
        )
    return dict(entry)


def secondary_yield(energy_ev, delta_max, e_max_ev):
    """Universal secondary-electron-emission yield at an impact energy."""
    for label, value in (
        ("energy_ev", energy_ev),
        ("delta_max", delta_max),
        ("e_max_ev", e_max_ev),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be numeric, got %r" % (label, value))
        if value <= 0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    ratio = float(energy_ev) / float(e_max_ev)
    low = ratio ** CURVE_LOW_EXPONENT
    high = 1.0 - math.exp(-CURVE_DECAY * ratio ** CURVE_HIGH_EXPONENT)
    return CURVE_SCALE * float(delta_max) * low * high


def peak_yield(delta_max, e_max_ev):
    """Yield evaluated at the tabulated peak energy."""
    return secondary_yield(e_max_ev, delta_max, e_max_ev)


def has_crossover(delta_max, e_max_ev):
    """True when the curve actually rises above unity somewhere."""
    return peak_yield(delta_max, e_max_ev) > 1.0 + UNITY_TOLERANCE


def _bisect_unity(low_ev, high_ev, delta_max, e_max_ev):
    """Bisect for yield == 1 on a bracket where the sign of (yield-1) flips."""
    f_low = secondary_yield(low_ev, delta_max, e_max_ev) - 1.0
    f_high = secondary_yield(high_ev, delta_max, e_max_ev) - 1.0
    if f_low * f_high > 0.0:
        raise ValueError("unity crossing is not bracketed by the given energies")
    for _ in range(BISECTION_MAX_ITERATIONS):
        mid = 0.5 * (low_ev + high_ev)
        f_mid = secondary_yield(mid, delta_max, e_max_ev) - 1.0
        if f_mid == 0.0 or (high_ev - low_ev) <= BISECTION_REL_TOL * mid:
            return mid
        if f_low * f_mid < 0.0:
            high_ev = mid
            f_high = f_mid
        else:
            low_ev = mid
            f_low = f_mid
    return 0.5 * (low_ev + high_ev)


def first_crossover_energy(delta_max, e_max_ev):
    """Impact energy below the peak at which the yield first reaches unity."""
    if not has_crossover(delta_max, e_max_ev):
        raise ValueError(
            "peak yield does not exceed unity; no crossover energy exists"
        )
    return _bisect_unity(MIN_BRACKET_EV, float(e_max_ev), delta_max, e_max_ev)


def second_crossover_energy(delta_max, e_max_ev):
    """Impact energy above the peak at which the yield falls back to unity."""
    if not has_crossover(delta_max, e_max_ev):
        raise ValueError(
            "peak yield does not exceed unity; no crossover energy exists"
        )
    upper = float(e_max_ev) * MAX_BRACKET_FACTOR
    return _bisect_unity(float(e_max_ev), upper, delta_max, e_max_ev)


def charging_disposition(energy_ev, delta_max, e_max_ev):
    """Net emission disposition of a surface at one impact energy."""
    value = secondary_yield(energy_ev, delta_max, e_max_ev)
    if math.isclose(value, 1.0, rel_tol=0.0, abs_tol=UNITY_TOLERANCE):
        return "unity-yield-balance"
    if value > 1.0:
        return "net-secondary-emission-positive-drift"
    return "net-electron-absorption-negative-drift"


def _covers_span(record_min, record_max, required_min, required_max):
    """True when a record's energy span covers the required span."""
    low_ok = record_min <= required_min or math.isclose(
        record_min, required_min, rel_tol=SPAN_REL_TOL, abs_tol=0.0
    )
    high_ok = record_max >= required_max or math.isclose(
        record_max, required_max, rel_tol=SPAN_REL_TOL, abs_tol=0.0
    )
    return low_ok and high_ok


def validate_measured_record(record):
    """Structurally validate a measured yield record; return it normalized."""
    if not isinstance(record, dict):
        raise ValueError("measured record must be a mapping, got %r" % (record,))
    material = resolve_material(record.get("material"))
    condition = resolve_surface_condition(record.get("surface_condition"))
    lo = record.get("energy_min_ev")
    hi = record.get("energy_max_ev")
    for label, value in (("energy_min_ev", lo), ("energy_max_ev", hi)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be numeric, got %r" % (label, value))
        if value <= 0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    if lo >= hi:
        raise ValueError("energy_min_ev must be below energy_max_ev")
    count = record.get("specimen_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("specimen_count must be a positive integer, got %r" % (count,))
    delta_max = record.get("delta_max")
    e_max = record.get("e_max_ev")
    for label, value in (("delta_max", delta_max), ("e_max_ev", e_max)):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ValueError("%s must be a positive number, got %r" % (label, value))
    return {
        "material": material,
        "surface_condition": condition,
        "energy_min_ev": float(lo),
        "energy_max_ev": float(hi),
        "specimen_count": count,
        "delta_max": float(delta_max),
        "e_max_ev": float(e_max),
    }


def assess_representativeness(record, material, surface_condition, required_span):
    """Return (is_representative, reasons) for a measured record."""
    normalized = validate_measured_record(record)
    wanted_material = resolve_material(material)
    wanted_condition = resolve_surface_condition(surface_condition)
    if not isinstance(required_span, (list, tuple)) or len(required_span) != 2:
        raise ValueError("required_span must be a two-element sequence")
    req_lo, req_hi = required_span
    for label, value in (("required_span low", req_lo), ("required_span high", req_hi)):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ValueError("%s must be a positive number, got %r" % (label, value))
    if req_lo >= req_hi:
        raise ValueError("required_span low must be below required_span high")
    reasons = []
    if normalized["material"] != wanted_material:
        reasons.append(
            "record material %s does not match the flight material %s"
            % (normalized["material"], wanted_material)
        )
    if normalized["surface_condition"] != wanted_condition:
        reasons.append(
            "record surface condition %s does not match the flight condition %s"
            % (normalized["surface_condition"], wanted_condition)
        )
    if not _covers_span(
        normalized["energy_min_ev"], normalized["energy_max_ev"], req_lo, req_hi
    ):
        reasons.append(
            "record energy span %.3f-%.3f eV does not cover the required %.3f-%.3f eV"
            % (
                normalized["energy_min_ev"],
                normalized["energy_max_ev"],
                float(req_lo),
                float(req_hi),
            )
        )
    if normalized["specimen_count"] < MIN_SPECIMEN_COUNT:
        reasons.append(
            "record draws on %d specimen; at least %d are needed"
            % (normalized["specimen_count"], MIN_SPECIMEN_COUNT)
        )
    return (not reasons, reasons)


def select_yield_source(record, material, surface_condition, required_span):
    """Choose the measured record or the tabulated fallback, or refuse."""
    reasons = []
    if record is not None:
        representative, reasons = assess_representativeness(
            record, material, surface_condition, required_span
        )
        if representative:
            normalized = validate_measured_record(record)
            return {
                "provenance": MEASURED,
                "delta_max": normalized["delta_max"],
                "e_max_ev": normalized["e_max_ev"],
                "fallback_reasons": [],
                "declaration": "measured data representative of the flight surface",
            }
    else:
        reasons = ["no measured record was supplied for this surface"]
    entry = lookup_tabulated_yield(material, surface_condition)
    return {
        "provenance": TABULATED_FALLBACK,
        "delta_max": entry["delta_max"],
        "e_max_ev": entry["e_max_ev"],
        "fallback_reasons": reasons,
        "declaration": (
            "tabulated experimental data substituted for representative "
            "measurement under clause 9.6"
        ),
    }


def evaluate_surface(record, material, surface_condition, required_span, energies_ev):
    """Select a source and report the curve, crossovers and dispositions."""
    if not isinstance(energies_ev, (list, tuple)) or not energies_ev:
        raise ValueError("energies_ev must be a non-empty sequence")
    source = select_yield_source(record, material, surface_condition, required_span)
    delta_max = source["delta_max"]
    e_max = source["e_max_ev"]
    points = []
    for energy in energies_ev:
        points.append(
            {
                "energy_ev": float(energy),
                "yield": secondary_yield(energy, delta_max, e_max),
                "disposition": charging_disposition(energy, delta_max, e_max),
            }
        )
    crossovers = None
    if has_crossover(delta_max, e_max):
        crossovers = {
            "first_ev": first_crossover_energy(delta_max, e_max),
            "second_ev": second_crossover_energy(delta_max, e_max),
        }
    return {
        "provenance": source["provenance"],
        "declaration": source["declaration"],
        "fallback_reasons": source["fallback_reasons"],
        "delta_max": delta_max,
        "e_max_ev": e_max,
        "crossovers": crossovers,
        "points": points,
    }
