#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2.1.3 + Annex B.4/B.5 -- worst-case trapped
electron spectrum for internal (deep-dielectric) charging (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
internal charging is driven by penetrating trapped electrons depositing
charge inside dielectrics and floating conductors. Clause 9.2.1.3
requires the worst-case electron spectrum for MEO/GEO/GTO/HEO orbit
segments, built from two models: FLUMIC (Annex B.4, a percentile-
parameterized worst-case fluence spectrum) and the NASA worst-case GEO
spectrum (Annex B.5, a fixed reference envelope). Because neither model
dominates at every energy, the RES-required spectrum is the per-energy
envelope (the higher of the two).

This module scopes only the workflow around the two models: orbit-
regime applicability, input validation, per-energy envelope
construction, energy-order-violation checking, and screening the
envelope against a stated flux threshold at a mission-critical energy.
The FLUMIC and NASA worst-case GEO models' own numeric coefficients are
out of scope here and are supplied by the caller as pluggable
model_fn(energy_mev, percentile) -> flux_cm2_day callables. The
material-level (charge-accumulation / breakdown-field) response is out
of scope (electrical/EEE-parts engineering discipline, not this
clause).
"""

APPLICABLE_ORBIT_REGIMES = frozenset({"MEO", "GEO", "GTO", "HEO"})

KNOWN_ORBIT_REGIMES = frozenset(
    {"LEO", "MEO", "GEO", "GTO", "HEO", "L2", "deep-tail", "interplanetary"}
)

HIGH_PERCENTILE_CAVEAT_THRESHOLD = 99.0


def validate_energy_mev(energy_mev):
    """Raise ValueError unless energy_mev > 0."""
    if energy_mev <= 0:
        raise ValueError("energy_mev must be > 0: %r" % (energy_mev,))


def validate_percentile(percentile):
    """Raise ValueError unless 0 < percentile < 100. A percentile of 0
    or 100 is degenerate for a worst-case statistical spectrum (no
    protection, or an undefined/infinite worst case)."""
    if not (0 < percentile < 100):
        raise ValueError("percentile must be in (0, 100): %r" % (percentile,))


def percentile_caveat(percentile):
    """Return a caveat string if percentile is at or above
    HIGH_PERCENTILE_CAVEAT_THRESHOLD (extrapolates well beyond FLUMIC's
    underlying historical database), else None."""
    validate_percentile(percentile)
    if percentile >= HIGH_PERCENTILE_CAVEAT_THRESHOLD:
        return (
            "percentile %.2f extrapolates beyond FLUMIC's limited historical "
            "database; treat the enveloped spectrum as carrying materially "
            "larger statistical uncertainty than a mid-range percentile."
            % percentile
        )
    return None


def check_orbit_applicability(orbit_regime):
    """Return True if orbit_regime is one of APPLICABLE_ORBIT_REGIMES
    (MEO, GEO, GTO, HEO), False if it is a known regime outside that
    set. Raise ValueError if orbit_regime is not in
    KNOWN_ORBIT_REGIMES at all."""
    if orbit_regime not in KNOWN_ORBIT_REGIMES:
        raise ValueError("unknown orbit_regime: %r" % (orbit_regime,))
    return orbit_regime in APPLICABLE_ORBIT_REGIMES


def compute_model_flux(energy_mev, percentile, model_fn, model_name):
    """Compute one model's flux at one energy. Validates inputs, calls
    model_fn(energy_mev, percentile), and checks the returned flux is a
    finite, non-negative number. Returns a new dict; raises ValueError
    on invalid input or an invalid model_fn result."""
    validate_energy_mev(energy_mev)
    validate_percentile(percentile)

    flux_cm2_day = model_fn(energy_mev, percentile)
    if not isinstance(flux_cm2_day, (int, float)) or flux_cm2_day != flux_cm2_day:
        raise ValueError("model_fn must return a finite number: %r" % (flux_cm2_day,))
    if flux_cm2_day < 0:
        raise ValueError("model_fn returned a negative flux: %r" % (flux_cm2_day,))

    return {
        "model_name": model_name,
        "energy_mev": energy_mev,
        "percentile": percentile,
        "flux_cm2_day": flux_cm2_day,
    }


def compute_model_spectrum(energies_mev, percentile, model_fn, model_name):
    """Compute one model's spectrum across energies_mev (a non-empty
    iterable) at one percentile. Returns a new dict with entries sorted
    ascending by energy and an energy_order_violations list: pairs of
    (lower, higher) energy entries where the higher-energy flux exceeds
    the lower-energy flux (should be empty for a physically consistent
    spectrum, since a harder population cannot outnumber a softer
    one). Raises ValueError if energies_mev is empty."""
    energies = sorted(set(energies_mev))
    if not energies:
        raise ValueError("energies_mev must be non-empty")

    entries = [
        compute_model_flux(e, percentile, model_fn, model_name) for e in energies
    ]

    violations = [
        (lower, higher)
        for lower, higher in zip(entries, entries[1:])
        if higher["flux_cm2_day"] > lower["flux_cm2_day"]
    ]

    return {
        "model_name": model_name,
        "percentile": percentile,
        "entries": entries,
        "energy_order_violations": violations,
    }


def compute_worst_case_envelope(energies_mev, percentile, flumic_fn, nasa_geo_fn):
    """Compute the per-energy worst-case envelope across FLUMIC and the
    NASA worst-case GEO spectrum: at each energy, take the higher of
    the two model fluxes and record which model dominated. Returns a
    new dict with entries sorted ascending by energy and an
    energy_order_violations list on the envelope itself (mirrors
    compute_model_spectrum's invariant). Raises ValueError if
    energies_mev is empty or either model produces an invalid flux."""
    flumic_spectrum = compute_model_spectrum(energies_mev, percentile, flumic_fn, "FLUMIC")
    nasa_spectrum = compute_model_spectrum(
        energies_mev, percentile, nasa_geo_fn, "NASA-worst-case-GEO"
    )

    envelope_entries = []
    for flumic_entry, nasa_entry in zip(flumic_spectrum["entries"], nasa_spectrum["entries"]):
        flumic_flux = flumic_entry["flux_cm2_day"]
        nasa_flux = nasa_entry["flux_cm2_day"]
        if flumic_flux >= nasa_flux:
            dominant_model, envelope_flux = "FLUMIC", flumic_flux
        else:
            dominant_model, envelope_flux = "NASA-worst-case-GEO", nasa_flux
        envelope_entries.append(
            {
                "energy_mev": flumic_entry["energy_mev"],
                "flumic_flux_cm2_day": flumic_flux,
                "nasa_geo_flux_cm2_day": nasa_flux,
                "envelope_flux_cm2_day": envelope_flux,
                "dominant_model": dominant_model,
            }
        )

    violations = [
        (lower, higher)
        for lower, higher in zip(envelope_entries, envelope_entries[1:])
        if higher["envelope_flux_cm2_day"] > lower["envelope_flux_cm2_day"]
    ]

    return {
        "percentile": percentile,
        "entries": envelope_entries,
        "energy_order_violations": violations,
    }


def screen_internal_charging_risk(envelope, energy_threshold_mev, flux_threshold_cm2_day):
    """Screen a worst-case envelope (as returned by
    compute_worst_case_envelope) against flux_threshold_cm2_day at
    energy_threshold_mev. Returns a new dict with the enveloped flux,
    the dominant model at that energy, and a risk_flagged bool (True
    when the enveloped flux meets or exceeds the threshold). Raises
    ValueError if flux_threshold_cm2_day is negative or if
    energy_threshold_mev is not one of the envelope's modeled
    energies."""
    if flux_threshold_cm2_day < 0:
        raise ValueError(
            "flux_threshold_cm2_day must be >= 0: %r" % (flux_threshold_cm2_day,)
        )

    matches = [e for e in envelope["entries"] if e["energy_mev"] == energy_threshold_mev]
    if not matches:
        raise ValueError(
            "energy_threshold_mev must be one of the modeled energies: %r"
            % (energy_threshold_mev,)
        )
    entry = matches[0]

    return {
        "energy_threshold_mev": energy_threshold_mev,
        "flux_threshold_cm2_day": flux_threshold_cm2_day,
        "envelope_flux_cm2_day": entry["envelope_flux_cm2_day"],
        "dominant_model": entry["dominant_model"],
        "risk_flagged": entry["envelope_flux_cm2_day"] >= flux_threshold_cm2_day,
    }


def internal_charging_specification(
    orbit_regime,
    energies_mev,
    percentile,
    flumic_fn,
    nasa_geo_fn,
    energy_threshold_mev,
    flux_threshold_cm2_day,
):
    """Assemble the clause 9.2.1.3 internal-charging entry for the
    mission's radiation environment specification. If orbit_regime is
    not applicable (outside MEO/GEO/GTO/HEO), returns a new dict with
    applicable False and no further computation. Otherwise builds the
    worst-case envelope, screens it for risk, and returns a new dict
    with the envelope, the screening result, a verified bool (True only
    when the envelope has no energy_order_violations), and the
    percentile caveat (None if not applicable). Raises ValueError for
    an unknown orbit_regime or any invalid input surfaced by the
    underlying model/screening calls."""
    applicable = check_orbit_applicability(orbit_regime)
    if not applicable:
        return {
            "orbit_regime": orbit_regime,
            "applicable": False,
            "note": (
                "clause 9.2.1.3 internal-charging worst-case electron spectrum "
                "does not apply to orbit regime %r (applicable regimes: %s)"
                % (orbit_regime, sorted(APPLICABLE_ORBIT_REGIMES))
            ),
        }

    envelope = compute_worst_case_envelope(energies_mev, percentile, flumic_fn, nasa_geo_fn)
    screening = screen_internal_charging_risk(
        envelope, energy_threshold_mev, flux_threshold_cm2_day
    )
    verified = not envelope["energy_order_violations"]

    return {
        "orbit_regime": orbit_regime,
        "applicable": True,
        "percentile": percentile,
        "envelope": envelope,
        "screening": screening,
        "verified": verified,
        "caveat": percentile_caveat(percentile),
    }
