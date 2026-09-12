#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §9.5 SEE hardness assurance procedure (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
space environment engineering standard's SEE hardness assurance clause
requires that every electronic device susceptible to single-event effects
have its on-orbit SEE rate predicted from the device Weibull cross-section
model and the mission particle spectrum, then compared against the system
error-rate requirement. Devices are categorized into a hardness assurance
tier (HA1/HA2/HA3) that sets lot-acceptance and screening obligations.
Destructive effects (SEL, SEB, SEGR) always attract the most stringent
tier regardless of the numerical rate. The cross-section model follows
the standard Weibull parameterisation: σ(x) = σ_sat × (1 − exp(−((x−x₀)/W)^s))
for x > x₀. This module implements: SEE-type categorization, Weibull
cross-section evaluation, ion-induced SEE rate estimation, proton/neutron-
induced SEE rate estimation, hardness assurance category assignment, and
the full per-device hardness assurance review.
"""

import math

# ── SEE-type vocabulary ────────────────────────────────────────────────────

DESTRUCTIVE_SEE_TYPES = frozenset({"sel", "seb", "segr"})
NON_DESTRUCTIVE_SEE_TYPES = frozenset({"seu", "sefi", "setr", "sehe"})

# Immunity thresholds (§9.5 paraphrase):
# Ion LET threshold at or above this value → no ion SEE hardness assurance needed.
# Proton energy threshold at or above this value → no proton/neutron SEE assurance needed.
ION_IMMUNITY_LET_THRESHOLD_MEV_CM2_MG = 37.0
PROTON_IMMUNITY_ENERGY_THRESHOLD_MEV = 200.0

# Hardness assurance category labels (ECSS-E-ST-10-12C §9.5 paraphrase):
# HA1 – destructive SEE susceptibility: lot screening + acceptance test every lot
# HA2 – non-destructive SEE with rate exceeding requirement: representative sample test
# HA3 – non-destructive SEE compliant by analysis: document analysis, review on environment update
HARDNESS_ASSURANCE_CATEGORIES = frozenset({"HA1", "HA2", "HA3"})


# ── Effect-type categorization ─────────────────────────────────────────────

def categorize_see_effect(effect_type):
    """Return "destructive" or "non_destructive" for a known SEE effect type.
    Raises ValueError for unrecognized types."""
    if effect_type in DESTRUCTIVE_SEE_TYPES:
        return "destructive"
    if effect_type in NON_DESTRUCTIVE_SEE_TYPES:
        return "non_destructive"
    raise ValueError(
        "unrecognized SEE effect type %r; expected one of %r"
        % (effect_type, sorted(DESTRUCTIVE_SEE_TYPES | NON_DESTRUCTIVE_SEE_TYPES))
    )


# ── Weibull cross-section model ────────────────────────────────────────────

def weibull_cross_section(particle_param, threshold, sigma_sat, width, shape):
    """Evaluate the Weibull device cross-section (cm²) at a given particle
    parameter value (LET in MeV·cm²/mg, or proton energy in MeV).

    Returns 0.0 when particle_param <= threshold (below onset).
    Raises ValueError for non-positive sigma_sat, width, or shape."""
    if sigma_sat <= 0:
        raise ValueError("sigma_sat must be > 0, got %r" % sigma_sat)
    if width <= 0:
        raise ValueError("width must be > 0, got %r" % width)
    if shape <= 0:
        raise ValueError("shape must be > 0, got %r" % shape)
    if particle_param <= threshold:
        return 0.0
    return sigma_sat * (1.0 - math.exp(-((particle_param - threshold) / width) ** shape))


# ── Device immunity helpers ────────────────────────────────────────────────

def is_ion_immune(let_threshold_mev_cm2_mg):
    """True when the device LET threshold meets or exceeds the ion immunity
    level, indicating no ion-induced SEE hardness assurance is required."""
    return let_threshold_mev_cm2_mg >= ION_IMMUNITY_LET_THRESHOLD_MEV_CM2_MG


def is_proton_immune(energy_threshold_mev):
    """True when the device proton energy threshold meets or exceeds the
    proton immunity level, indicating no proton/neutron SEE assurance is
    required."""
    return energy_threshold_mev >= PROTON_IMMUNITY_ENERGY_THRESHOLD_MEV


# ── Ion-induced SEE rate ───────────────────────────────────────────────────

def ion_see_rate(
    let_threshold_mev_cm2_mg,
    sigma_sat_cm2,
    weibull_width,
    weibull_shape,
    let_spectrum,
):
    """Estimate the ion-induced SEE rate (events/device/day) by integrating
    the Weibull cross-section against a discrete heavy-ion LET spectrum.

    let_spectrum: list of dicts, each {"let_mev_cm2_mg": float,
    "flux_per_cm2_per_day": float}. Rate = Σ σ_Weibull(LET_i) × flux_i.

    Returns 0.0 immediately when let_threshold_mev_cm2_mg >= the ion
    immunity threshold (device is ion-immune). Raises ValueError for a
    negative LET threshold or for any spectrum bin with negative flux."""
    if let_threshold_mev_cm2_mg < 0:
        raise ValueError("let_threshold_mev_cm2_mg must be >= 0")
    if is_ion_immune(let_threshold_mev_cm2_mg):
        return 0.0
    rate = 0.0
    for bin_ in let_spectrum:
        flux = bin_["flux_per_cm2_per_day"]
        if flux < 0:
            raise ValueError("flux_per_cm2_per_day must be >= 0, got %r" % flux)
        sigma = weibull_cross_section(
            bin_["let_mev_cm2_mg"],
            let_threshold_mev_cm2_mg,
            sigma_sat_cm2,
            weibull_width,
            weibull_shape,
        )
        rate += sigma * flux
    return rate


# ── Proton/neutron-induced SEE rate ───────────────────────────────────────

def proton_neutron_see_rate(
    energy_threshold_mev,
    sigma_sat_cm2,
    weibull_width,
    weibull_shape,
    energy_spectrum,
):
    """Estimate the proton/neutron-induced SEE rate (events/device/day) by
    integrating the Weibull cross-section against a discrete energy spectrum.

    energy_spectrum: list of dicts, each {"energy_mev": float,
    "flux_per_cm2_per_day": float}. Rate = Σ σ_Weibull(E_i) × flux_i.

    Returns 0.0 immediately when energy_threshold_mev >= the proton immunity
    threshold (device is proton-immune). Raises ValueError for a negative
    energy threshold or for any spectrum bin with negative flux."""
    if energy_threshold_mev < 0:
        raise ValueError("energy_threshold_mev must be >= 0")
    if is_proton_immune(energy_threshold_mev):
        return 0.0
    rate = 0.0
    for bin_ in energy_spectrum:
        flux = bin_["flux_per_cm2_per_day"]
        if flux < 0:
            raise ValueError("flux_per_cm2_per_day must be >= 0, got %r" % flux)
        sigma = weibull_cross_section(
            bin_["energy_mev"],
            energy_threshold_mev,
            sigma_sat_cm2,
            weibull_width,
            weibull_shape,
        )
        rate += sigma * flux
    return rate


# ── Rate comparison ────────────────────────────────────────────────────────

def rate_exceeds_requirement(predicted_rate, requirement_rate):
    """True when predicted_rate > requirement_rate. Raises ValueError for
    negative predicted or requirement rate."""
    if predicted_rate < 0:
        raise ValueError("predicted_rate must be >= 0")
    if requirement_rate < 0:
        raise ValueError("requirement_rate must be >= 0")
    return predicted_rate > requirement_rate


# ── Hardness assurance category ────────────────────────────────────────────

def assign_hardness_assurance_category(effect_type, predicted_rate, requirement_rate):
    """Assign the hardness assurance category for a device-effect pair.

    HA1: effect is destructive (SEL, SEB, SEGR) — lot screening + test every lot.
    HA2: non-destructive effect with predicted_rate > requirement_rate.
    HA3: non-destructive effect with predicted_rate <= requirement_rate.

    Raises ValueError for an unrecognized effect_type or negative rates."""
    category = categorize_see_effect(effect_type)
    if category == "destructive":
        return "HA1"
    if rate_exceeds_requirement(predicted_rate, requirement_rate):
        return "HA2"
    return "HA3"


# ── Full device hardness assurance review ─────────────────────────────────

def see_hardness_review(device):
    """Run the §9.5 SEE hardness assurance procedure for one device.

    device dict schema:
      device_id: str
      effects: list of dicts, each:
        effect_type: str               (e.g. "seu", "sel")
        let_threshold: float           MeV·cm²/mg
        sigma_sat_ion: float           cm²
        weibull_width_ion: float
        weibull_shape_ion: float
        energy_threshold: float        MeV
        sigma_sat_proton: float        cm²
        weibull_width_proton: float
        weibull_shape_proton: float
        requirement_rate: float        events/device/day
      let_spectrum: list of {"let_mev_cm2_mg": float, "flux_per_cm2_per_day": float}
      energy_spectrum: list of {"energy_mev": float, "flux_per_cm2_per_day": float}

    Returns:
      device_id: str
      effect_assessments: list of per-effect dicts with computed rates,
        immunity flags, hardness assurance category, and rate_violation flag
      findings: list of violation dicts (empty when all effects are within
        their rate requirements)
    """
    device_id = device["device_id"]
    let_spectrum = device.get("let_spectrum", [])
    energy_spectrum = device.get("energy_spectrum", [])
    assessments = []
    findings = []

    for effect in device.get("effects", []):
        etype = effect["effect_type"]
        let_thresh = effect["let_threshold"]
        e_thresh = effect["energy_threshold"]
        req_rate = effect["requirement_rate"]

        ion_immune = is_ion_immune(let_thresh)
        proton_immune = is_proton_immune(e_thresh)

        ion_rate = 0.0
        if not ion_immune:
            ion_rate = ion_see_rate(
                let_thresh,
                effect["sigma_sat_ion"],
                effect["weibull_width_ion"],
                effect["weibull_shape_ion"],
                let_spectrum,
            )

        p_rate = 0.0
        if not proton_immune:
            p_rate = proton_neutron_see_rate(
                e_thresh,
                effect["sigma_sat_proton"],
                effect["weibull_width_proton"],
                effect["weibull_shape_proton"],
                energy_spectrum,
            )

        total_rate = ion_rate + p_rate
        ha_cat = assign_hardness_assurance_category(etype, total_rate, req_rate)
        violation = rate_exceeds_requirement(total_rate, req_rate)

        assessments.append({
            "effect_type": etype,
            "ion_immune": ion_immune,
            "proton_immune": proton_immune,
            "ion_rate": ion_rate,
            "proton_rate": p_rate,
            "total_rate": total_rate,
            "requirement_rate": req_rate,
            "hardness_assurance_category": ha_cat,
            "rate_violation": violation,
        })

        if violation:
            findings.append({
                "issue": "see_rate_requirement_exceeded",
                "device": device_id,
                "effect_type": etype,
                "total_rate": total_rate,
                "requirement_rate": req_rate,
                "hardness_assurance_category": ha_cat,
            })

    return {
        "device_id": device_id,
        "effect_assessments": assessments,
        "findings": findings,
    }


def is_see_hardness_compliant(review):
    """True when a see_hardness_review result contains no findings."""
    return len(review.get("findings", [])) == 0
