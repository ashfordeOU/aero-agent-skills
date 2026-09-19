"""Post-cleaning cleanliness verification for contamination-controlled hardware.

Anchor: ECSS-Q-ST-70-01 operations clause (verifying that the cleanliness level
was actually reached after a cleaning operation). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the measurement set taken after cleaning: particle counts per size
   band over a sampled area, and a non-volatile-residue sample with its blank.
2. Convert the counts to a particle obscuration figure per unit area and place
   the surface on the particulate ladder by the largest band that was found
   populated and by the obscuration reached.
3. Subtract the witness blank from the residue sample, refuse a negative net
   result, and treat a net result under the balance resolution as a bound
   rather than a value.
4. Test the sampling itself: the sampled area has to be a real fraction of the
   surface and the sites have to be more than one, or the result describes a
   patch and not the item.
5. Return the achieved particulate and residue levels, the verdict -- accept,
   re-clean or re-sample -- and the finding that drove it.
"""

import math

__all__ = [
    "PARTICULATE_LEVELS",
    "SIZE_BANDS",
    "MOLECULAR_LEVELS_MG_PER_M2",
    "MIN_SAMPLE_SITES",
    "MIN_SAMPLED_FRACTION",
    "LEVEL_TOLERANCE",
    "validate_counts",
    "band_upper_micron",
    "obscuration_ppm",
    "largest_populated_band",
    "particulate_level_reached",
    "net_residue_mg",
    "residue_is_bounded",
    "residue_mg_per_m2",
    "residue_level_reached",
    "sampling_adequacy",
    "level_meets",
    "verify_after_cleaning",
]

# Particulate ladder, cleanest first; value is the largest particle size in
# micrometres the level tolerates on a witnessed area.
PARTICULATE_LEVELS = (
    ("PCL-50", 50.0),
    ("PCL-100", 100.0),
    ("PCL-200", 200.0),
    ("PCL-300", 300.0),
    ("PCL-500", 500.0),
    ("PCL-750", 750.0),
    ("PCL-1000", 1000.0),
)

# Count size bands, each keyed by its upper bound in micrometres. A count in a
# band is treated as sitting at the band's upper bound for obscuration.
SIZE_BANDS = (
    ("5-15", 15.0),
    ("15-25", 25.0),
    ("25-50", 50.0),
    ("50-100", 100.0),
    ("100-250", 250.0),
    ("250-500", 500.0),
    ("500-1000", 1000.0),
)

# Residue ladder, cleanest first; value is the residue loading in milligrams
# per square metre the level tolerates.
MOLECULAR_LEVELS_MG_PER_M2 = (
    ("NVR-A/10", 0.1),
    ("NVR-A/5", 0.2),
    ("NVR-A/2", 0.5),
    ("NVR-A", 1.0),
    ("NVR-B", 2.0),
    ("NVR-C", 3.0),
)

MIN_SAMPLE_SITES = 2
MIN_SAMPLED_FRACTION = 0.01

# Ladder placement compares a computed loading with a tabulated bound; a
# sample landing exactly on a bound must not fall off it through float error.
LEVEL_TOLERANCE = 1e-9

_BAND_NAMES = tuple(name for name, _upper in SIZE_BANDS)


def band_upper_micron(band_name):
    """Return the upper size bound in micrometres of a known count band."""
    if not isinstance(band_name, str):
        raise ValueError("band name must be a string, got %r" % (band_name,))
    for name, upper in SIZE_BANDS:
        if name == band_name:
            return upper
    raise ValueError(
        "unknown size band %r; known: %s" % (band_name, ", ".join(_BAND_NAMES))
    )


def validate_counts(counts):
    """Return the validated per-band particle counts as a plain mapping."""
    if not isinstance(counts, dict) or not counts:
        raise ValueError("counts must be a non-empty mapping of band to count")
    validated = {}
    for band_name, count in counts.items():
        band_upper_micron(band_name)
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count for band %r must be an integer" % (band_name,))
        if count < 0:
            raise ValueError("count for band %r must not be negative" % (band_name,))
        validated[band_name] = count
    return validated


def obscuration_ppm(counts, sampled_area_m2):
    """Return the projected-area obscuration in parts per million."""
    validated = validate_counts(counts)
    if isinstance(sampled_area_m2, bool) or not isinstance(sampled_area_m2, (int, float)):
        raise ValueError("sampled_area_m2 must be a real number")
    area = float(sampled_area_m2)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("sampled_area_m2 must be positive and finite, got %r" % (sampled_area_m2,))
    projected_m2 = 0.0
    for band_name, count in validated.items():
        diameter_m = band_upper_micron(band_name) * 1e-6
        radius_m = 0.5 * diameter_m
        projected_m2 += float(count) * math.pi * radius_m * radius_m
    return 1.0e6 * projected_m2 / area


def largest_populated_band(counts):
    """Return the name of the largest size band carrying a non-zero count."""
    validated = validate_counts(counts)
    largest = None
    largest_upper = 0.0
    for band_name, count in validated.items():
        if count <= 0:
            continue
        upper = band_upper_micron(band_name)
        if upper > largest_upper:
            largest_upper = upper
            largest = band_name
    return largest


def particulate_level_reached(counts):
    """Return the cleanest particulate level the counted surface satisfies."""
    band_name = largest_populated_band(counts)
    if band_name is None:
        return PARTICULATE_LEVELS[0][0]
    upper = band_upper_micron(band_name)
    for level_name, bound in PARTICULATE_LEVELS:
        if upper < bound or math.isclose(
            upper, bound, rel_tol=0.0, abs_tol=LEVEL_TOLERANCE
        ):
            return level_name
    return None


def net_residue_mg(sample_mg, blank_mg):
    """Return the blank-subtracted residue mass in milligrams."""
    for label, value in (("sample_mg", sample_mg), ("blank_mg", blank_mg)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("%s must be non-negative and finite, got %r" % (label, value))
    net = float(sample_mg) - float(blank_mg)
    if net < 0.0:
        raise ValueError(
            "blank %g mg exceeds the sample %g mg; the run is invalid, not clean"
            % (float(blank_mg), float(sample_mg))
        )
    return net


def residue_is_bounded(net_mg, balance_resolution_mg):
    """Return True when the net residue sits at or under the balance floor."""
    if isinstance(net_mg, bool) or not isinstance(net_mg, (int, float)):
        raise ValueError("net_mg must be a real number")
    if isinstance(balance_resolution_mg, bool) or not isinstance(
        balance_resolution_mg, (int, float)
    ):
        raise ValueError("balance_resolution_mg must be a real number")
    net = float(net_mg)
    floor = float(balance_resolution_mg)
    if not math.isfinite(net) or net < 0.0:
        raise ValueError("net_mg must be non-negative and finite")
    if not math.isfinite(floor) or floor <= 0.0:
        raise ValueError("balance_resolution_mg must be positive and finite")
    return net < floor or math.isclose(net, floor, rel_tol=0.0, abs_tol=LEVEL_TOLERANCE)


def residue_mg_per_m2(net_mg, sampled_area_m2):
    """Return the residue loading in milligrams per square metre."""
    if isinstance(net_mg, bool) or not isinstance(net_mg, (int, float)):
        raise ValueError("net_mg must be a real number")
    net = float(net_mg)
    if not math.isfinite(net) or net < 0.0:
        raise ValueError("net_mg must be non-negative and finite")
    if isinstance(sampled_area_m2, bool) or not isinstance(sampled_area_m2, (int, float)):
        raise ValueError("sampled_area_m2 must be a real number")
    area = float(sampled_area_m2)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("sampled_area_m2 must be positive and finite")
    return net / area


def residue_level_reached(loading_mg_per_m2):
    """Return the cleanest residue level the measured loading satisfies."""
    if isinstance(loading_mg_per_m2, bool) or not isinstance(
        loading_mg_per_m2, (int, float)
    ):
        raise ValueError("loading must be a real number")
    loading = float(loading_mg_per_m2)
    if not math.isfinite(loading) or loading < 0.0:
        raise ValueError("loading must be non-negative and finite")
    for level_name, bound in MOLECULAR_LEVELS_MG_PER_M2:
        if loading < bound or math.isclose(
            loading, bound, rel_tol=0.0, abs_tol=LEVEL_TOLERANCE
        ):
            return level_name
    return None


def sampling_adequacy(sampled_area_m2, surface_area_m2, site_count):
    """Return the findings that make a sample unrepresentative of the surface."""
    for label, value in (
        ("sampled_area_m2", sampled_area_m2),
        ("surface_area_m2", surface_area_m2),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    if isinstance(site_count, bool) or not isinstance(site_count, int):
        raise ValueError("site_count must be an integer")
    if site_count < 1:
        raise ValueError("site_count must be at least 1, got %d" % site_count)
    sampled = float(sampled_area_m2)
    surface = float(surface_area_m2)
    if sampled > surface and not math.isclose(
        sampled, surface, rel_tol=1e-12, abs_tol=0.0
    ):
        raise ValueError(
            "sampled area %g m2 exceeds the surface area %g m2" % (sampled, surface)
        )
    findings = []
    fraction = sampled / surface
    if fraction < MIN_SAMPLED_FRACTION and not math.isclose(
        fraction, MIN_SAMPLED_FRACTION, rel_tol=0.0, abs_tol=LEVEL_TOLERANCE
    ):
        findings.append(
            "sampled fraction %.4f is under the %.2f minimum; the result "
            "describes the patch, not the surface" % (fraction, MIN_SAMPLED_FRACTION)
        )
    if site_count < MIN_SAMPLE_SITES:
        findings.append(
            "only %d sample site; at least %d are needed to see a non-uniform "
            "surface" % (site_count, MIN_SAMPLE_SITES)
        )
    return findings


def level_meets(reached, required, ladder):
    """Return True when the reached level is at least as clean as required."""
    names = [name for name, _bound in ladder]
    if reached is None:
        return False
    if reached not in names:
        raise ValueError("unknown level %r on this ladder" % (reached,))
    if required not in names:
        raise ValueError("unknown required level %r on this ladder" % (required,))
    return names.index(reached) <= names.index(required)


def verify_after_cleaning(measurement):
    """Run the full post-cleaning verification and return the verdict.

    measurement keys: counts (band -> integer count), sampled_area_m2,
    surface_area_m2, site_count, sample_mg, blank_mg, balance_resolution_mg,
    required_particulate_level, required_residue_level.
    """
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping")
    required_keys = (
        "counts",
        "sampled_area_m2",
        "surface_area_m2",
        "site_count",
        "sample_mg",
        "blank_mg",
        "balance_resolution_mg",
        "required_particulate_level",
        "required_residue_level",
    )
    for key in required_keys:
        if key not in measurement:
            raise ValueError("measurement missing required key '%s'" % key)

    sampled_area = measurement["sampled_area_m2"]
    counts = validate_counts(measurement["counts"])
    obscuration = obscuration_ppm(counts, sampled_area)
    particulate = particulate_level_reached(counts)
    net_mg = net_residue_mg(measurement["sample_mg"], measurement["blank_mg"])
    bounded = residue_is_bounded(net_mg, measurement["balance_resolution_mg"])
    loading = residue_mg_per_m2(net_mg, sampled_area)
    residue = residue_level_reached(loading)
    sampling_findings = sampling_adequacy(
        sampled_area, measurement["surface_area_m2"], measurement["site_count"]
    )

    findings = list(sampling_findings)
    particulate_ok = level_meets(
        particulate, measurement["required_particulate_level"], PARTICULATE_LEVELS
    )
    if not particulate_ok:
        findings.append(
            "particulate result %s does not meet the required %s"
            % (particulate or "off-ladder", measurement["required_particulate_level"])
        )
    residue_ok = level_meets(
        residue, measurement["required_residue_level"], MOLECULAR_LEVELS_MG_PER_M2
    )
    if not residue_ok:
        findings.append(
            "residue loading %.4f mg/m2 reaches %s, short of the required %s"
            % (loading, residue or "off-ladder", measurement["required_residue_level"])
        )
    if bounded:
        findings.append(
            "net residue %.4f mg is at or under the balance resolution; the "
            "loading is a bound, not a value" % net_mg
        )

    if sampling_findings:
        verdict = "re-sample"
    elif particulate_ok and residue_ok:
        verdict = "accept"
    else:
        verdict = "re-clean"

    return {
        "obscuration_ppm": obscuration,
        "particulate_level_reached": particulate,
        "net_residue_mg": net_mg,
        "residue_loading_mg_per_m2": loading,
        "residue_level_reached": residue,
        "residue_is_bound": bounded,
        "particulate_meets_requirement": particulate_ok,
        "residue_meets_requirement": residue_ok,
        "verdict": verdict,
        "findings": findings,
    }
