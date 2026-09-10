#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.5 NASA worst-case geosynchronous (GEO)
electron environment spectrum logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
NASA worst-case GEO electron environment is a conservative design
spectrum bounding the electron population encountered at GEO, built
from two contiguous exponential-fit energy bands -- a lower-energy
population associated with spacecraft surface charging and a
higher-energy, more penetrating population associated with
deep-dielectric (internal) charging. The spectrum is a worst-case, not
a time-averaged, environment: it is applied as a sustained flux over a
stated worst-case exposure duration to derive a worst-case fluence,
with no duty-cycle reduction. This module implements the band
selection, differential/integral flux, worst-case fluence, and
fluence-vs-limit compliance logic; it does not implement the
trapped-electron internal-charging screening that combines this
spectrum with the sibling FLUMIC-based Annex B.4 model (see the
sibling e1004-internal-charging leaf) or the radiation environment
specification roll-up (see the sibling e1004-rad-env-spec leaf).
"""

import math

# Illustrative two-band exponential parameterization of the model's
# spectral form (band name, valid energy sub-range in MeV, flux
# coefficient j0 in electrons/(cm^2 s sr MeV), and characteristic
# (e-folding) energy e0 in MeV). Not verbatim ECSS/NASA table values.
BANDS = (
    {"name": "surface", "min_mev": 0.02, "max_mev": 0.15, "j0": 4.0e9, "e0_mev": 0.03},
    {"name": "internal", "min_mev": 0.15, "max_mev": 5.0, "j0": 3.0e6, "e0_mev": 0.35},
)

MODEL_MIN_MEV = BANDS[0]["min_mev"]
MODEL_MAX_MEV = BANDS[-1]["max_mev"]

WORST_CASE_REFERENCE_DURATION_DAYS = 1.0
SECONDS_PER_DAY = 86400.0


def band_for_energy(energy_mev):
    """The BANDS entry whose energy sub-range contains energy_mev.
    Raises ValueError when energy_mev is outside [MODEL_MIN_MEV,
    MODEL_MAX_MEV]."""
    if energy_mev < MODEL_MIN_MEV or energy_mev > MODEL_MAX_MEV:
        raise ValueError(
            "energy %r MeV is outside the model's valid range [%r, %r] MeV"
            % (energy_mev, MODEL_MIN_MEV, MODEL_MAX_MEV)
        )
    last_index = len(BANDS) - 1
    for index, band in enumerate(BANDS):
        is_last = index == last_index
        if band["min_mev"] <= energy_mev < band["max_mev"]:
            return band
        if is_last and energy_mev == band["max_mev"]:
            return band
    raise ValueError("energy %r MeV did not match a model band" % (energy_mev,))


def differential_flux(energy_mev):
    """Differential electron flux (electrons/(cm^2 s sr MeV)) at
    energy_mev from its band's exponential fit. Raises ValueError when
    energy_mev is outside the model's valid range."""
    band = band_for_energy(energy_mev)
    return band["j0"] * math.exp(-energy_mev / band["e0_mev"])


def _band_integral(band, lo_mev, hi_mev):
    """Analytic integral of the band's exponential differential flux
    from lo_mev to hi_mev: integral of j0 * exp(-E/e0) dE = j0 * e0 *
    (exp(-lo/e0) - exp(-hi/e0))."""
    j0 = band["j0"]
    e0 = band["e0_mev"]
    return j0 * e0 * (math.exp(-lo_mev / e0) - math.exp(-hi_mev / e0))


def integral_flux_above(energy_mev):
    """Integral electron flux (electrons/(cm^2 s sr)) above
    energy_mev, summing the partial integral of energy_mev's own band
    (from energy_mev up to that band's upper edge) with the full
    integral of every band above it. Raises ValueError when energy_mev
    is outside the model's valid range."""
    band_for_energy(energy_mev)  # validates range
    total = 0.0
    for band in BANDS:
        if band["max_mev"] <= energy_mev:
            continue
        lo_mev = band["min_mev"] if band["min_mev"] >= energy_mev else energy_mev
        total += _band_integral(band, lo_mev, band["max_mev"])
    return total


def worst_case_fluence(energy_mev, duration_days):
    """Worst-case electron fluence (electrons/cm^2) above energy_mev
    over duration_days, applying integral_flux_above() as a sustained
    flux for the full duration (no duty-cycle reduction). Raises
    ValueError when duration_days is not positive or energy_mev is
    outside the model's valid range."""
    if duration_days <= 0:
        raise ValueError("duration_days must be positive")
    return integral_flux_above(energy_mev) * duration_days * SECONDS_PER_DAY


def assess_case(case):
    """Worst-case fluence compliance assessment for one case dict.
    Required keys: id, energy_threshold_mev, duration_days,
    qualified_fluence_limit. Returns a new dict; does not mutate the
    input. Raises ValueError when 'id' is missing or the case's
    parameters are invalid."""
    if "id" not in case:
        raise ValueError("GEO worst-case case is missing an id")
    energy_threshold_mev = case["energy_threshold_mev"]
    duration_days = case["duration_days"]
    qualified_fluence_limit = case["qualified_fluence_limit"]
    fluence = worst_case_fluence(energy_threshold_mev, duration_days)
    compliant = fluence <= qualified_fluence_limit
    margin = qualified_fluence_limit / fluence if fluence > 0 else float("inf")
    return {
        "id": case["id"],
        "energy_threshold_mev": energy_threshold_mev,
        "duration_days": duration_days,
        "worst_case_fluence": fluence,
        "qualified_fluence_limit": qualified_fluence_limit,
        "margin": margin,
        "compliant": compliant,
    }


def build_geo_wc_assessment(cases):
    """Assessment record: one assess_case() result per case, in input
    order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate GEO worst-case case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot support the internal-charging screening
    as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0
