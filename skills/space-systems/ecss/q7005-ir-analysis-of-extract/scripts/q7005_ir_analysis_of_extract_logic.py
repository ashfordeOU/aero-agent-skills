"""Indirect solvent-extract infrared analysis of organic surface contamination.

Anchor: ECSS-Q-ST-70-05C, indirect method. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the sampling record: sampled area, extract volume, cast aliquot
   volume and the extraction recovery fraction.
2. Form the net band absorbance from the gross reading, its local baseline and
   the solvent blank carried through the same evaporation.
3. Convert the net absorbance into the mass of deposit cast on the infrared
   window through the method response in absorbance per microgram.
4. Restore the dilution factor (extract volume / cast aliquot volume) and the
   extraction recovery fraction to recover the mass that was on the surface.
5. Divide by the sampled area to obtain the areal mass in ug/cm2.
6. Score the observed band positions against a library of reference spectra and
   report an ambiguous identification when the two best scores are closer than
   the separation margin.
"""

__all__ = [
    "ABSORBANCE_NOISE",
    "AMBIGUITY_MARGIN",
    "BLANK_SHARE_LIMIT",
    "DEFAULT_BAND_TOLERANCE_CM1",
    "QUANTIFICATION_FLOOR_ABS",
    "areal_mass_ug_per_cm2",
    "assess_extract_analysis",
    "blank_share",
    "cast_film_mass_ug",
    "dilution_factor",
    "extract_mass_ug",
    "match_reference_spectra",
    "net_absorbance",
    "score_reference",
    "surface_mass_ug",
    "validate_extraction_record",
]

# Absorbance readings carry instrument noise; a net a hair below zero is a
# representation and noise question, a net well below zero is a bad baseline.
ABSORBANCE_NOISE = 1.0e-4

# Below this net absorbance the band is present but not quantifiable; the
# result is reported as bounded, never as a small positive mass.
QUANTIFICATION_FLOOR_ABS = 5.0e-3

# A blank contributing more than this share of the gross-minus-baseline
# reading means the band is reporting the solvent, not the hardware.
BLANK_SHARE_LIMIT = 0.10

# Two reference spectra whose coverage scores sit inside this margin have not
# been discriminated by the spectrum.
AMBIGUITY_MARGIN = 0.10

# Band positions match within the instrument resolution, in wavenumbers.
DEFAULT_BAND_TOLERANCE_CM1 = 8.0


def _positive(label, value, allow_zero=False):
    """Return value as a finite float, raising on a non-numeric or non-positive."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _real(label, value):
    """Return value as a finite float of any sign."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_extraction_record(record):
    """Return the normalised sampling record for an indirect extract analysis.

    Keys: sampled_area_cm2, extract_volume_ml, cast_aliquot_ml,
    recovery_fraction (0 < r <= 1).
    """
    if not isinstance(record, dict):
        raise ValueError("extraction record must be a mapping")
    for key in ("sampled_area_cm2", "extract_volume_ml", "cast_aliquot_ml",
                "recovery_fraction"):
        if key not in record:
            raise ValueError("extraction record missing required key '%s'" % key)
    area = _positive("sampled_area_cm2", record["sampled_area_cm2"])
    volume = _positive("extract_volume_ml", record["extract_volume_ml"])
    aliquot = _positive("cast_aliquot_ml", record["cast_aliquot_ml"])
    recovery = _positive("recovery_fraction", record["recovery_fraction"])
    if aliquot > volume:
        raise ValueError(
            "cast_aliquot_ml %g exceeds extract_volume_ml %g" % (aliquot, volume)
        )
    if recovery > 1.0:
        raise ValueError("recovery_fraction must not exceed unity, got %g" % recovery)
    return {
        "sampled_area_cm2": area,
        "extract_volume_ml": volume,
        "cast_aliquot_ml": aliquot,
        "recovery_fraction": recovery,
    }


def net_absorbance(gross_absorbance, baseline_absorbance, blank_absorbance=0.0):
    """Return the blank-corrected net band absorbance."""
    gross = _real("gross_absorbance", gross_absorbance)
    baseline = _real("baseline_absorbance", baseline_absorbance)
    blank = _positive("blank_absorbance", blank_absorbance, allow_zero=True)
    above_baseline = gross - baseline
    if above_baseline < -ABSORBANCE_NOISE:
        raise ValueError(
            "gross absorbance %g sits below its baseline %g; the baseline is wrong"
            % (gross, baseline)
        )
    net = above_baseline - blank
    if net < -ABSORBANCE_NOISE:
        raise ValueError(
            "blank absorbance %g exceeds the band above its baseline %g"
            % (blank, above_baseline)
        )
    return net if net > 0.0 else 0.0


def blank_share(gross_absorbance, baseline_absorbance, blank_absorbance):
    """Return the share of the band above baseline contributed by the blank."""
    gross = _real("gross_absorbance", gross_absorbance)
    baseline = _real("baseline_absorbance", baseline_absorbance)
    blank = _positive("blank_absorbance", blank_absorbance, allow_zero=True)
    above_baseline = gross - baseline
    if above_baseline <= 0.0:
        raise ValueError("band above baseline must be positive to form a blank share")
    return blank / above_baseline


def cast_film_mass_ug(net_abs, response_abs_per_ug):
    """Return the mass of deposit on the window from the net band absorbance."""
    net = _positive("net_abs", net_abs, allow_zero=True)
    response = _positive("response_abs_per_ug", response_abs_per_ug)
    return net / response


def dilution_factor(extract_volume_ml, cast_aliquot_ml):
    """Return the factor restoring a cast aliquot to the whole extract."""
    volume = _positive("extract_volume_ml", extract_volume_ml)
    aliquot = _positive("cast_aliquot_ml", cast_aliquot_ml)
    if aliquot > volume:
        raise ValueError(
            "cast_aliquot_ml %g exceeds extract_volume_ml %g" % (aliquot, volume)
        )
    return volume / aliquot


def extract_mass_ug(cast_mass_ug, extract_volume_ml, cast_aliquot_ml):
    """Return the contaminant mass held in the whole extract."""
    mass = _positive("cast_mass_ug", cast_mass_ug, allow_zero=True)
    return mass * dilution_factor(extract_volume_ml, cast_aliquot_ml)


def surface_mass_ug(extract_mass, recovery_fraction):
    """Return the mass that was on the surface, correcting for recovery."""
    mass = _positive("extract_mass", extract_mass, allow_zero=True)
    recovery = _positive("recovery_fraction", recovery_fraction)
    if recovery > 1.0:
        raise ValueError("recovery_fraction must not exceed unity, got %g" % recovery)
    return mass / recovery


def areal_mass_ug_per_cm2(surface_mass, sampled_area_cm2):
    """Return the areal contamination level in ug/cm2."""
    mass = _positive("surface_mass", surface_mass, allow_zero=True)
    area = _positive("sampled_area_cm2", sampled_area_cm2)
    return mass / area


def _validate_bands(bands, label):
    """Return a sorted list of finite positive wavenumbers."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("%s must be a non-empty sequence of wavenumbers" % label)
    out = []
    for i, value in enumerate(bands):
        out.append(_positive("%s[%d]" % (label, i), value))
    return sorted(out)


def score_reference(observed_bands, reference_bands,
                    tolerance_cm1=DEFAULT_BAND_TOLERANCE_CM1):
    """Return the coverage record of one reference spectrum.

    Coverage is the share of the reference's characteristic bands that an
    observed band falls within tolerance of. Unmatched observed bands are
    returned so a reviewer can see what the candidate does not explain.
    """
    observed = _validate_bands(observed_bands, "observed_bands")
    reference = _validate_bands(reference_bands, "reference_bands")
    tolerance = _positive("tolerance_cm1", tolerance_cm1)
    matched = []
    missing = []
    explained = set()
    for ref in reference:
        hit = None
        for idx, obs in enumerate(observed):
            if abs(obs - ref) <= tolerance:
                if hit is None or abs(obs - ref) < abs(observed[hit] - ref):
                    hit = idx
        if hit is None:
            missing.append(ref)
        else:
            matched.append(ref)
            explained.add(hit)
    unexplained = [obs for idx, obs in enumerate(observed) if idx not in explained]
    return {
        "coverage": len(matched) / float(len(reference)),
        "matched_bands": matched,
        "missing_bands": missing,
        "unexplained_observed": unexplained,
        "single_band_support": len(matched) <= 1,
    }


def match_reference_spectra(observed_bands, library,
                            tolerance_cm1=DEFAULT_BAND_TOLERANCE_CM1,
                            ambiguity_margin=AMBIGUITY_MARGIN):
    """Rank a library of reference spectra against the observed band set."""
    if not isinstance(library, dict) or not library:
        raise ValueError("library must be a non-empty mapping of name to band list")
    margin = _positive("ambiguity_margin", ambiguity_margin)
    scored = []
    for name in sorted(library):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("reference name must be a non-empty string")
        record = score_reference(observed_bands, library[name], tolerance_cm1)
        record["name"] = name
        scored.append(record)
    scored.sort(key=lambda r: (-r["coverage"], r["name"]))
    best = scored[0]
    ambiguous = False
    contenders = [best["name"]]
    if len(scored) > 1:
        gap = best["coverage"] - scored[1]["coverage"]
        if gap < margin or abs(gap - margin) <= 1e-12:
            ambiguous = True
            for record in scored[1:]:
                near = best["coverage"] - record["coverage"]
                if near < margin or abs(near - margin) <= 1e-12:
                    contenders.append(record["name"])
    return {
        "ranking": scored,
        "best": best["name"],
        "best_coverage": best["coverage"],
        "ambiguous": ambiguous,
        "contenders": sorted(contenders),
        "identification": None if ambiguous else best["name"],
    }


def assess_extract_analysis(spec):
    """Run the full indirect-extract assessment.

    spec keys: sampling (extraction record), gross_absorbance,
    baseline_absorbance, blank_absorbance, response_abs_per_ug, and optionally
    observed_bands plus reference_library, band_tolerance_cm1.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sampling", "gross_absorbance", "baseline_absorbance",
                "response_abs_per_ug"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    sampling = validate_extraction_record(spec["sampling"])
    blank = spec.get("blank_absorbance", 0.0)
    net = net_absorbance(spec["gross_absorbance"], spec["baseline_absorbance"], blank)
    share = blank_share(spec["gross_absorbance"], spec["baseline_absorbance"], blank)
    findings = []
    quantifiable = net > QUANTIFICATION_FLOOR_ABS and not (
        abs(net - QUANTIFICATION_FLOOR_ABS) <= 1e-12
    )
    cast_mass = cast_film_mass_ug(net, spec["response_abs_per_ug"])
    whole = extract_mass_ug(
        cast_mass, sampling["extract_volume_ml"], sampling["cast_aliquot_ml"]
    )
    on_surface = surface_mass_ug(whole, sampling["recovery_fraction"])
    areal = areal_mass_ug_per_cm2(on_surface, sampling["sampled_area_cm2"])
    if not quantifiable:
        findings.append(
            "net band absorbance %.5f is at or below the quantification floor "
            "%.5f; report the areal mass as an upper bound"
            % (net, QUANTIFICATION_FLOOR_ABS)
        )
    if share > BLANK_SHARE_LIMIT and abs(share - BLANK_SHARE_LIMIT) > 1e-12:
        findings.append(
            "solvent blank supplies %.1f%% of the band above baseline, past the "
            "%.1f%% limit; quantify on a band the blank does not occupy"
            % (100.0 * share, 100.0 * BLANK_SHARE_LIMIT)
        )
    identification = None
    if "observed_bands" in spec and "reference_library" in spec:
        identification = match_reference_spectra(
            spec["observed_bands"],
            spec["reference_library"],
            spec.get("band_tolerance_cm1", DEFAULT_BAND_TOLERANCE_CM1),
        )
        if identification["ambiguous"]:
            findings.append(
                "reference spectra %s are covered inside the separation margin; "
                "the identification is ambiguous"
                % ", ".join(identification["contenders"])
            )
        top = identification["ranking"][0]
        if top["single_band_support"]:
            findings.append(
                "the leading candidate is supported by one band only; a "
                "characteristic band set is needed to identify it"
            )
    return {
        "net_absorbance": net,
        "blank_share": share,
        "cast_film_mass_ug": cast_mass,
        "extract_mass_ug": whole,
        "surface_mass_ug": on_surface,
        "areal_mass_ug_per_cm2": areal,
        "quantifiable": quantifiable,
        "bounded_upper_limit": not quantifiable,
        "identification": identification,
        "findings": findings,
        "acceptable": not findings,
    }
