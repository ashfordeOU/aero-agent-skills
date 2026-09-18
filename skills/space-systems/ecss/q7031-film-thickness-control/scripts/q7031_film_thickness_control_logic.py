"""Wet and dry film thickness control for each coat of a paint system.

Anchor: ECSS-Q-ST-70-31C, Application. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Reduce the declared volume solids of the paint by any thinner added at the
   gun, because the thinner leaves with the solvent and the operator's wet
   comb reading no longer converts at the tin value.
2. Convert between wet film thickness and dry film thickness in both
   directions, so the wet comb target that lands a coat inside its dry band
   can be issued before spraying rather than measured afterwards.
3. Grade a population of dry film readings for one coat against its band: the
   mean has to sit inside the band, and no single reading may fall under an
   absolute floor expressed as a fraction of the band minimum.
4. Sum the per-coat means into a system dry film thickness and grade that
   against the system band, because a stack of individually acceptable coats
   can still overshoot the system maximum.
5. Report the theoretical spreading rate at the target dry thickness, derated
   by transfer efficiency, so the material drawn matches the coats planned.
"""

import math

__all__ = [
    "BAND_TOLERANCE",
    "DEFAULT_MIN_SINGLE_FRACTION",
    "validate_positive",
    "validate_fraction",
    "effective_volume_solids_pct",
    "wet_to_dry_um",
    "dry_to_wet_um",
    "spreading_rate_m2_per_l",
    "coat_verdict",
    "assess_coat_readings",
    "system_dry_thickness_um",
    "assess_film_thickness",
]

# A gauge can report a value that is exactly a band limit. Absorb the
# representation error here, never by moving the limit.
BAND_TOLERANCE = 1e-9

# No single reading may fall below this fraction of the coat band minimum,
# even when the mean of the population is inside the band.
DEFAULT_MIN_SINGLE_FRACTION = 0.8


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_positive(value, label):
    """Return a validated strictly positive float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_fraction(value, label, upper=1.0):
    """Return a validated fraction in (0, upper]."""
    out = _real(value, label)
    if out <= 0.0 or out > upper:
        raise ValueError("%s must lie in (0, %g], got %g" % (label, upper, out))
    return out


def effective_volume_solids_pct(volume_solids_pct, thinner_volume_ratio=0.0):
    """Return volume solids after thinning, in percent."""
    solids = _real(volume_solids_pct, "volume_solids_pct")
    if solids <= 0.0 or solids > 100.0:
        raise ValueError("volume_solids_pct must lie in (0, 100], got %g" % solids)
    ratio = _real(thinner_volume_ratio, "thinner_volume_ratio")
    if ratio < 0.0:
        raise ValueError("thinner_volume_ratio must be non-negative, got %g" % ratio)
    return solids / (1.0 + ratio)


def wet_to_dry_um(wft_um, volume_solids_pct, thinner_volume_ratio=0.0):
    """Return the dry film thickness a wet film of wft_um will leave."""
    wet = validate_positive(wft_um, "wft_um")
    solids = effective_volume_solids_pct(volume_solids_pct, thinner_volume_ratio)
    return wet * solids / 100.0


def dry_to_wet_um(dft_um, volume_solids_pct, thinner_volume_ratio=0.0):
    """Return the wet comb target that lands the requested dry thickness."""
    dry = validate_positive(dft_um, "dft_um")
    solids = effective_volume_solids_pct(volume_solids_pct, thinner_volume_ratio)
    return dry * 100.0 / solids


def spreading_rate_m2_per_l(dft_um, volume_solids_pct, thinner_volume_ratio=0.0,
                            transfer_efficiency=1.0):
    """Return the achievable spreading rate in square metres per litre."""
    dry = validate_positive(dft_um, "dft_um")
    solids = effective_volume_solids_pct(volume_solids_pct, thinner_volume_ratio)
    efficiency = validate_fraction(transfer_efficiency, "transfer_efficiency")
    return (10.0 * solids / dry) * efficiency


def coat_verdict(dft_um, min_um, max_um, tolerance=BAND_TOLERANCE):
    """Return 'below', 'within' or 'above' for one dry film thickness value."""
    value = _real(dft_um, "dft_um")
    low = validate_positive(min_um, "min_um")
    high = validate_positive(max_um, "max_um")
    if low > high:
        raise ValueError("min_um %g exceeds max_um %g" % (low, high))
    tol = _real(tolerance, "tolerance")
    if tol < 0.0:
        raise ValueError("tolerance must be non-negative, got %g" % tol)
    if value < low - tol:
        return "below"
    if value > high + tol:
        return "above"
    return "within"


def assess_coat_readings(readings, min_um, max_um,
                         min_single_fraction=DEFAULT_MIN_SINGLE_FRACTION):
    """Grade a population of dry film readings for one coat."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of gauge values")
    low = validate_positive(min_um, "min_um")
    high = validate_positive(max_um, "max_um")
    if low > high:
        raise ValueError("min_um %g exceeds max_um %g" % (low, high))
    fraction = validate_fraction(min_single_fraction, "min_single_fraction")
    values = []
    for i, raw in enumerate(readings):
        value = _real(raw, "readings[%d]" % i)
        if value < 0.0:
            raise ValueError("readings[%d] must be non-negative, got %g" % (i, value))
        values.append(value)
    floor = low * fraction
    mean = sum(values) / len(values)
    below_floor = [v for v in values if v < floor - BAND_TOLERANCE]
    above_max = [v for v in values if v > high + BAND_TOLERANCE]
    findings = []
    mean_verdict = coat_verdict(mean, low, high)
    if mean_verdict != "within":
        findings.append(
            "mean dry film thickness %.2f um is %s the band [%g, %g]"
            % (mean, mean_verdict, low, high)
        )
    if below_floor:
        findings.append(
            "%d reading(s) fall under the absolute floor %.2f um"
            % (len(below_floor), floor)
        )
    if above_max:
        findings.append(
            "%d reading(s) exceed the coat maximum %g um" % (len(above_max), high)
        )
    return {
        "readings": values,
        "count": len(values),
        "mean_um": mean,
        "minimum_um": min(values),
        "maximum_um": max(values),
        "absolute_floor_um": floor,
        "mean_verdict": mean_verdict,
        "readings_below_floor": len(below_floor),
        "readings_above_maximum": len(above_max),
        "findings": findings,
        "acceptable": not findings,
    }


def system_dry_thickness_um(coat_means):
    """Return the summed system dry film thickness of the coat stack."""
    if not isinstance(coat_means, (list, tuple)) or not coat_means:
        raise ValueError("coat_means must be a non-empty sequence")
    total = 0.0
    for i, raw in enumerate(coat_means):
        total += validate_positive(raw, "coat_means[%d]" % i)
    return total


def assess_film_thickness(spec):
    """Run the full per-coat and system film thickness assessment.

    spec keys: coats (each with name, volume_solids_pct, min_dft_um, max_dft_um,
    readings, optional thinner_volume_ratio), optional system_dft_band,
    optional min_single_fraction and transfer_efficiency.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    coats = spec.get("coats")
    if not isinstance(coats, (list, tuple)) or not coats:
        raise ValueError("spec['coats'] must be a non-empty sequence of coat records")
    fraction = spec.get("min_single_fraction", DEFAULT_MIN_SINGLE_FRACTION)
    efficiency = spec.get("transfer_efficiency", 1.0)
    records = []
    findings = []
    for i, coat in enumerate(coats):
        if not isinstance(coat, dict):
            raise ValueError("coats[%d] must be a mapping" % i)
        for key in ("name", "volume_solids_pct", "min_dft_um", "max_dft_um", "readings"):
            if key not in coat:
                raise ValueError("coats[%d] missing required key '%s'" % (i, key))
        thinner = coat.get("thinner_volume_ratio", 0.0)
        graded = assess_coat_readings(
            coat["readings"], coat["min_dft_um"], coat["max_dft_um"], fraction
        )
        target_dft = 0.5 * (
            validate_positive(coat["min_dft_um"], "min_dft_um")
            + validate_positive(coat["max_dft_um"], "max_dft_um")
        )
        record = {
            "name": str(coat["name"]),
            "target_dft_um": target_dft,
            "wet_comb_target_um": dry_to_wet_um(
                target_dft, coat["volume_solids_pct"], thinner
            ),
            "effective_volume_solids_pct": effective_volume_solids_pct(
                coat["volume_solids_pct"], thinner
            ),
            "spreading_rate_m2_per_l": spreading_rate_m2_per_l(
                target_dft, coat["volume_solids_pct"], thinner, efficiency
            ),
        }
        record.update(graded)
        records.append(record)
        for text in graded["findings"]:
            findings.append("%s: %s" % (record["name"], text))

    total = system_dry_thickness_um([r["mean_um"] for r in records])
    system_verdict = None
    band = spec.get("system_dft_band")
    if band is not None:
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("spec['system_dft_band'] must be a (min, max) pair")
        system_verdict = coat_verdict(total, band[0], band[1])
        if system_verdict != "within":
            findings.append(
                "system dry film thickness %.2f um is %s the system band [%g, %g]"
                % (total, system_verdict, float(band[0]), float(band[1]))
            )
    return {
        "coats": records,
        "system_dft_um": total,
        "system_verdict": system_verdict,
        "findings": findings,
        "acceptable": not findings,
    }
