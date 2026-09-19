"""Vacuum-probe and solvent-rinse sampling of hardware surfaces.

Anchor: ECSS-Q-ST-70-50C, the surface sampling clause. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide which sampling method a surface can actually carry, from its
   accessibility, its solvent compatibility, whether rinsate can be
   collected, and whether the surface tolerates a probe.
2. Turn the raw sampling record into a mass or a count that belongs to a
   known area:
   * a solvent rinse evaporates one aliquot of the rinsate, so the weighed
     residue is scaled back to the whole collected volume;
   * a vacuum probe sweeps a stroke pattern, so the swept area is the
     pattern area less the deliberate overlap between strokes.
3. Subtract the witness blank, and hold a net the balance cannot resolve to
   a bounded sub-floor statement instead of a small positive number.
4. Divide out the collection recovery of the method, so the reported figure
   is surface loading and not collected loading.
5. Express the result per unit area, alongside the detection limit the same
   area and recovery imply, and grade it against the reporting limit the
   programme set.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "DEFAULT_BALANCE_FLOOR_MG",
    "SAMPLING_METHODS",
    "require_real",
    "validate_area_m2",
    "probe_swept_area_m2",
    "aliquot_scale_factor",
    "blank_corrected_residue_mg",
    "recovery_corrected_mg",
    "area_density_mg_per_m2",
    "particle_density_per_m2",
    "detection_limit_mg_per_m2",
    "select_sampling_method",
    "evaluate_rinse_sample",
    "evaluate_probe_sample",
    "assess_surface_sampling",
]

# An area density compared with a reporting limit is a ratio of two
# floating-point quotients; an exact equality can land a few ULPs either
# side. Absorb the representation error here, never by moving the limit.
LIMIT_TOLERANCE = 1e-9

# Microbalance readability below which a net residue is scatter, not a mass.
DEFAULT_BALANCE_FLOOR_MG = 0.01

SAMPLING_METHODS = ("solvent-rinse", "vacuum-probe")

_TARGETS = ("nvr", "particulate")

# Which method each target prefers when a surface can carry both: rinsate
# recovers a film over the whole wetted area, a probe lifts discrete
# particles the solvent would only redistribute.
_PREFERENCE = {
    "nvr": ("solvent-rinse", "vacuum-probe"),
    "particulate": ("vacuum-probe", "solvent-rinse"),
}


def require_real(value, label, positive=False, non_negative=False):
    """Return value as a float, rejecting booleans, strings and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and result <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, result))
    if non_negative and result < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, result))
    return result


def validate_area_m2(area_m2):
    """Return the validated sampled area in square metres."""
    return require_real(area_m2, "area_m2", positive=True)


def probe_swept_area_m2(strokes, probe_width_mm, stroke_length_mm, overlap_fraction=0.0):
    """Return the area a vacuum-probe stroke pattern actually swept.

    Adjacent strokes are deliberately overlapped so no lane is missed; the
    overlapped band is swept twice and must not be counted twice.
    """
    if isinstance(strokes, bool) or not isinstance(strokes, int):
        raise ValueError("strokes must be an integer, got %r" % (strokes,))
    if strokes < 1:
        raise ValueError("strokes must be at least 1, got %d" % strokes)
    width = require_real(probe_width_mm, "probe_width_mm", positive=True)
    length = require_real(stroke_length_mm, "stroke_length_mm", positive=True)
    overlap = require_real(overlap_fraction, "overlap_fraction", non_negative=True)
    if overlap >= 1.0:
        raise ValueError("overlap_fraction must be below 1, got %g" % overlap)
    # First stroke contributes its full width; each later stroke contributes
    # only the fresh fraction of its width.
    fresh_widths = 1.0 + (strokes - 1) * (1.0 - overlap)
    area_mm2 = fresh_widths * width * length
    return area_mm2 / 1.0e6


def aliquot_scale_factor(aliquot_ml, rinse_volume_ml):
    """Return the factor scaling an evaporated aliquot to the whole rinsate."""
    aliquot = require_real(aliquot_ml, "aliquot_ml", positive=True)
    total = require_real(rinse_volume_ml, "rinse_volume_ml", positive=True)
    if aliquot > total:
        raise ValueError(
            "aliquot_ml %g exceeds the collected rinse_volume_ml %g" % (aliquot, total)
        )
    return total / aliquot


def blank_corrected_residue_mg(sample_mg, blank_mg, balance_floor_mg=DEFAULT_BALANCE_FLOOR_MG):
    """Subtract the witness blank and categorize what is left.

    Returns a mapping with the net mass, a status of quantified, sub-floor or
    blank-dominated, and the floor the status was judged against.
    """
    sample = require_real(sample_mg, "sample_mg", non_negative=True)
    blank = require_real(blank_mg, "blank_mg", non_negative=True)
    floor = require_real(balance_floor_mg, "balance_floor_mg", positive=True)
    net = sample - blank
    if net < -floor:
        status = "blank-dominated"
    elif net <= floor:
        status = "sub-floor"
    else:
        status = "quantified"
    return {
        "net_mg": net,
        "status": status,
        "balance_floor_mg": floor,
    }


def recovery_corrected_mg(mass_mg, recovery_fraction):
    """Divide out the collection recovery of the sampling method."""
    mass = require_real(mass_mg, "mass_mg", non_negative=True)
    recovery = require_real(recovery_fraction, "recovery_fraction", positive=True)
    if recovery > 1.0:
        raise ValueError("recovery_fraction must not exceed 1, got %g" % recovery)
    return mass / recovery


def area_density_mg_per_m2(mass_mg, area_m2):
    """Return a residue mass as a loading per unit sampled area."""
    mass = require_real(mass_mg, "mass_mg", non_negative=True)
    return mass / validate_area_m2(area_m2)


def particle_density_per_m2(count, area_m2):
    """Return a particle count as a count per unit sampled area."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 0:
        raise ValueError("count must be non-negative, got %d" % count)
    return count / validate_area_m2(area_m2)


def detection_limit_mg_per_m2(balance_floor_mg, area_m2, recovery_fraction=1.0,
                              dilution_factor=1.0):
    """Return the lowest loading the method can report for this sample."""
    floor = require_real(balance_floor_mg, "balance_floor_mg", positive=True)
    recovery = require_real(recovery_fraction, "recovery_fraction", positive=True)
    if recovery > 1.0:
        raise ValueError("recovery_fraction must not exceed 1, got %g" % recovery)
    dilution = require_real(dilution_factor, "dilution_factor", positive=True)
    if dilution < 1.0:
        raise ValueError("dilution_factor must be at least 1, got %g" % dilution)
    area = validate_area_m2(area_m2)
    return (floor * dilution) / (recovery * area)


def select_sampling_method(surface):
    """Choose the sampling method a surface can carry for the stated target."""
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    target = surface.get("target", "nvr")
    if target not in _TARGETS:
        raise ValueError("target must be one of %s, got %r" % (_TARGETS, target))
    for key in ("accessible", "solvent_compatible", "rinsate_collectable",
                "probe_tolerant"):
        if key in surface and not isinstance(surface[key], bool):
            raise ValueError("surface['%s'] must be a boolean" % key)
    accessible = surface.get("accessible", True)
    eligible = []
    if accessible and surface.get("solvent_compatible", False) \
            and surface.get("rinsate_collectable", False):
        eligible.append("solvent-rinse")
    if accessible and surface.get("probe_tolerant", False):
        eligible.append("vacuum-probe")
    if not eligible:
        raise ValueError(
            "no sampling method is applicable to this surface; a witness plate or a "
            "design change is required rather than an unsupported sample"
        )
    chosen = None
    for candidate in _PREFERENCE[target]:
        if candidate in eligible:
            chosen = candidate
            break
    return {"target": target, "eligible": eligible, "chosen": chosen}


def evaluate_rinse_sample(sample):
    """Evaluate one solvent-rinse record into a blank- and recovery-corrected loading."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    for key in ("area_m2", "rinse_volume_ml", "aliquot_ml", "residue_mg", "blank_mg"):
        if key not in sample:
            raise ValueError("rinse sample missing required key '%s'" % key)
    area = validate_area_m2(sample["area_m2"])
    dilution = aliquot_scale_factor(sample["aliquot_ml"], sample["rinse_volume_ml"])
    floor = require_real(
        sample.get("balance_floor_mg", DEFAULT_BALANCE_FLOOR_MG),
        "balance_floor_mg",
        positive=True,
    )
    corrected = blank_corrected_residue_mg(sample["residue_mg"], sample["blank_mg"], floor)
    recovery = require_real(sample.get("recovery_fraction", 1.0),
                            "recovery_fraction", positive=True)
    if recovery > 1.0:
        raise ValueError("recovery_fraction must not exceed 1, got %g" % recovery)
    record = {
        "id": sample.get("id", "rinse"),
        "method": "solvent-rinse",
        "area_m2": area,
        "dilution_factor": dilution,
        "status": corrected["status"],
        "net_mg": corrected["net_mg"],
        "detection_limit_mg_per_m2": detection_limit_mg_per_m2(
            floor, area, recovery, dilution
        ),
    }
    if corrected["status"] == "quantified":
        whole = corrected["net_mg"] * dilution
        record["loading_mg_per_m2"] = area_density_mg_per_m2(
            recovery_corrected_mg(whole, recovery), area
        )
    else:
        record["loading_mg_per_m2"] = None
    return record


def evaluate_probe_sample(sample):
    """Evaluate one vacuum-probe record into a particle density per unit area."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    for key in ("strokes", "probe_width_mm", "stroke_length_mm", "count"):
        if key not in sample:
            raise ValueError("probe sample missing required key '%s'" % key)
    area = probe_swept_area_m2(
        sample["strokes"],
        sample["probe_width_mm"],
        sample["stroke_length_mm"],
        sample.get("overlap_fraction", 0.0),
    )
    recovery = require_real(sample.get("recovery_fraction", 1.0),
                            "recovery_fraction", positive=True)
    if recovery > 1.0:
        raise ValueError("recovery_fraction must not exceed 1, got %g" % recovery)
    density = particle_density_per_m2(sample["count"], area) / recovery
    return {
        "id": sample.get("id", "probe"),
        "method": "vacuum-probe",
        "area_m2": area,
        "count": sample["count"],
        "status": "quantified",
        "particles_per_m2": density,
    }


def assess_surface_sampling(spec):
    """Run the full surface-sampling assessment for a set of samples.

    spec keys: samples (list of rinse and probe records, each carrying a
    'method'), optional reporting_limit_mg_per_m2.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    samples = spec.get("samples")
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("spec['samples'] must be a non-empty sequence")
    limit = spec.get("reporting_limit_mg_per_m2")
    if limit is not None:
        limit = require_real(limit, "reporting_limit_mg_per_m2", positive=True)
    records = []
    findings = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict) or "method" not in sample:
            raise ValueError("samples[%d] must be a mapping carrying 'method'" % index)
        method = sample["method"]
        if method == "solvent-rinse":
            record = evaluate_rinse_sample(sample)
        elif method == "vacuum-probe":
            record = evaluate_probe_sample(sample)
        else:
            raise ValueError(
                "samples[%d] method must be one of %s, got %r"
                % (index, SAMPLING_METHODS, method)
            )
        records.append(record)
        if record["status"] == "blank-dominated":
            findings.append(
                "sample %s: witness blank exceeds the sample past the balance floor; "
                "the rinsate or the glassware was contaminated" % record["id"]
            )
        if limit is not None and record["method"] == "solvent-rinse":
            floor = record["detection_limit_mg_per_m2"]
            if floor > limit and not math.isclose(
                floor, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
            ):
                findings.append(
                    "sample %s: detection limit %.4g mg/m2 is above the reporting "
                    "limit %.4g mg/m2; enlarge the sampled area or reduce the dilution"
                    % (record["id"], floor, limit)
                )
            loading = record["loading_mg_per_m2"]
            if loading is not None and loading > limit and not math.isclose(
                loading, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
            ):
                findings.append(
                    "sample %s: loading %.4g mg/m2 exceeds the reporting limit %.4g mg/m2"
                    % (record["id"], loading, limit)
                )
    quantified = [r for r in records if r["status"] == "quantified"]
    return {
        "records": records,
        "quantified_count": len(quantified),
        "reporting_limit_mg_per_m2": limit,
        "findings": findings,
        "acceptable": not findings,
    }
