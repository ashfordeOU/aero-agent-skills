"""Thermo optical property measurement on a designated subgroup of assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.6.2. The procedure below is a paraphrase
of the clause intent and reproduces none of its text: solar absorptance and
hemispherical emittance are measured on the subgroup of cell assemblies the
test plan designated for it, so the thermal balance of the array rests on
numbers that came off named samples rather than off a datasheet.

Procedure implemented here
--------------------------
1. Reconcile the samples actually measured against the subgroup the plan
   designated. A designated sample that was never measured is a shortfall; a
   measured sample nobody designated is extra work that does not close the
   subgroup.
2. Reduce each spectral scan into the two properties. Both are weighted means
   over the reflectance the instrument returned: absorptance is one minus the
   solar-weighted reflectance, emittance is one minus the thermally weighted
   reflectance. The weights carry the spectrum, so an unweighted average of
   the same bands is a different and wrong number.
3. Derive the absorptance to emittance ratio, which is the quantity the
   thermal design actually consumes.
4. Repeat scans of one sample are the only evidence of instrument
   repeatability, so require the declared number of them and hold their spread
   inside the declared repeatability limit.
5. Refuse any band whose wavelength lies outside the spectral range of the
   instrument that reported it. A reflectance returned beyond the range of the
   instrument is an extrapolation of its own calibration.
"""

import math

__all__ = [
    "PROPERTY_TOLERANCE",
    "DEFAULT_REQUIRED_SCANS",
    "DEFAULT_ABSORPTANCE_REPEATABILITY",
    "DEFAULT_EMITTANCE_REPEATABILITY",
    "weighted_reflectance",
    "solar_absorptance",
    "hemispherical_emittance",
    "absorptance_emittance_ratio",
    "mean_value",
    "reading_spread",
    "uncovered_wavelengths_um",
    "resolve_subgroup",
    "evaluate_sample",
    "assess_thermo_optical_measurement",
]

# Weighted means and spreads are sums of products of floats, so a scan set built
# exactly to the repeatability limit can land a few units in the last place
# outside it. Absorb that representation error here, not by relaxing the limit.
PROPERTY_TOLERANCE = 1e-9

# A single scan proves nothing about the instrument; repeatability needs at
# least a pair on the same sample.
DEFAULT_REQUIRED_SCANS = 2

# Default spread ceilings across repeat scans of one sample.
DEFAULT_ABSORPTANCE_REPEATABILITY = 0.01
DEFAULT_EMITTANCE_REPEATABILITY = 0.01


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative:
        if allow_zero and number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
        if not allow_zero and number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _fraction(label, value):
    """Return value as a validated reflectance in the closed zero to one range."""
    number = _real(label, value, allow_zero=True)
    if number > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (label, value))
    return number


def _count(label, value, allow_zero=True):
    """Return value as a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    if not allow_zero and value == 0:
        raise ValueError("%s must be greater than zero" % label)
    return value


def _mapping(label, value, required_keys=()):
    """Return value as a mapping carrying every required key."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in required_keys:
        if key not in value:
            raise ValueError("%s is missing required key '%s'" % (label, key))
    return value


def _identifier(label, value):
    """Return value as a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _range(label, value):
    """Return value as a validated (low, high) wavelength range in micrometres."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _real("%s[0]" % label, value[0])
    high = _real("%s[1]" % label, value[1])
    if low >= high:
        raise ValueError("%s is inverted: %g is not below %g" % (label, low, high))
    return (low, high)


def weighted_reflectance(bands):
    """Return the spectrum-weighted mean reflectance of a set of bands."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty sequence of band records")
    weighted = 0.0
    total_weight = 0.0
    for index, band in enumerate(bands):
        data = _mapping("bands[%d]" % index, band, ("wavelength_um", "weight",
                                                    "reflectance"))
        _real("bands[%d]['wavelength_um']" % index, data["wavelength_um"])
        weight = _real("bands[%d]['weight']" % index, data["weight"])
        reflectance = _fraction(
            "bands[%d]['reflectance']" % index, data["reflectance"]
        )
        weighted += weight * reflectance
        total_weight += weight
    return weighted / total_weight


def solar_absorptance(bands):
    """Return the solar absorptance implied by a solar-band reflectance scan."""
    return 1.0 - weighted_reflectance(bands)


def hemispherical_emittance(bands):
    """Return the hemispherical emittance implied by a thermal-band scan."""
    return 1.0 - weighted_reflectance(bands)


def absorptance_emittance_ratio(absorptance, emittance):
    """Return the absorptance to emittance ratio the thermal design consumes."""
    alpha = _real("absorptance", absorptance, allow_zero=True)
    epsilon = _real("emittance", emittance)
    return alpha / epsilon


def mean_value(values):
    """Return the arithmetic mean of a non-empty sequence of readings."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    return math.fsum(values) / len(values)


def reading_spread(values):
    """Return the full spread between the largest and smallest reading."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    return max(values) - min(values)


def uncovered_wavelengths_um(bands, instrument_range_um):
    """Return the band wavelengths the instrument spectral range never covered."""
    low, high = _range("instrument_range_um", instrument_range_um)
    uncovered = []
    for index, band in enumerate(bands):
        data = _mapping("bands[%d]" % index, band, ("wavelength_um",))
        wavelength = _real("bands[%d]['wavelength_um']" % index, data["wavelength_um"])
        below = wavelength < low and not math.isclose(
            wavelength, low, rel_tol=0.0, abs_tol=PROPERTY_TOLERANCE
        )
        above = wavelength > high and not math.isclose(
            wavelength, high, rel_tol=0.0, abs_tol=PROPERTY_TOLERANCE
        )
        if below or above:
            uncovered.append(wavelength)
    return uncovered


def resolve_subgroup(designated_ids, measured_ids):
    """Return the coverage of the designated subgroup by the samples measured."""
    for label, sequence in (("designated_ids", designated_ids),
                            ("measured_ids", measured_ids)):
        if not isinstance(sequence, (list, tuple)):
            raise ValueError("%s must be a sequence of identifiers" % label)
    designated = []
    for entry in designated_ids:
        name = _identifier("designated_ids entry", entry)
        if name in designated:
            raise ValueError("designated sample '%s' is listed twice" % name)
        designated.append(name)
    if not designated:
        raise ValueError("designated_ids must name at least one sample")
    measured = []
    for entry in measured_ids:
        name = _identifier("measured_ids entry", entry)
        if name in measured:
            raise ValueError("measured sample '%s' is listed twice" % name)
        measured.append(name)
    designated_set = set(designated)
    measured_set = set(measured)
    return {
        "designated": designated,
        "measured": measured,
        "covered": sorted(designated_set & measured_set),
        "missing": sorted(designated_set - measured_set),
        "extra": sorted(measured_set - designated_set),
    }


def evaluate_sample(sample, instruments, limits=None):
    """Reduce the repeat scans of one sample into its thermo optical record."""
    data = _mapping("sample", sample, ("id", "scans"))
    sample_id = _identifier("sample['id']", data["id"])
    instrument_data = _mapping(
        "instruments", instruments, ("reflectometer_range_um", "emissometer_range_um")
    )
    solar_range = _range(
        "instruments['reflectometer_range_um']",
        instrument_data["reflectometer_range_um"],
    )
    thermal_range = _range(
        "instruments['emissometer_range_um']", instrument_data["emissometer_range_um"]
    )
    options = _mapping("limits", limits or {})
    required_scans = _count(
        "limits['required_scans']",
        options.get("required_scans", DEFAULT_REQUIRED_SCANS),
        allow_zero=False,
    )
    absorptance_limit = _real(
        "limits['absorptance_repeatability']",
        options.get("absorptance_repeatability", DEFAULT_ABSORPTANCE_REPEATABILITY),
    )
    emittance_limit = _real(
        "limits['emittance_repeatability']",
        options.get("emittance_repeatability", DEFAULT_EMITTANCE_REPEATABILITY),
    )
    scans = data["scans"]
    if not isinstance(scans, (list, tuple)) or not scans:
        raise ValueError("sample['scans'] must be a non-empty sequence of scans")
    absorptances = []
    emittances = []
    findings = []
    uncovered = []
    for index, scan in enumerate(scans):
        scan_data = _mapping(
            "sample['scans'][%d]" % index, scan, ("solar_bands", "thermal_bands")
        )
        solar_bands = scan_data["solar_bands"]
        thermal_bands = scan_data["thermal_bands"]
        if not isinstance(solar_bands, (list, tuple)) or not solar_bands:
            raise ValueError("scan %d carries no solar bands" % index)
        if not isinstance(thermal_bands, (list, tuple)) or not thermal_bands:
            raise ValueError("scan %d carries no thermal bands" % index)
        uncovered.extend(uncovered_wavelengths_um(solar_bands, solar_range))
        uncovered.extend(uncovered_wavelengths_um(thermal_bands, thermal_range))
        absorptances.append(solar_absorptance(solar_bands))
        emittances.append(hemispherical_emittance(thermal_bands))
    absorptance = mean_value(absorptances)
    emittance = mean_value(emittances)
    absorptance_spread = reading_spread(absorptances)
    emittance_spread = reading_spread(emittances)
    ratio = absorptance_emittance_ratio(absorptance, emittance)
    if len(scans) < required_scans:
        findings.append(
            "sample %s carries %d scan(s), fewer than the %d the repeatability "
            "check needs" % (sample_id, len(scans), required_scans)
        )
    if absorptance_spread > absorptance_limit and not math.isclose(
        absorptance_spread, absorptance_limit, rel_tol=0.0, abs_tol=PROPERTY_TOLERANCE
    ):
        findings.append(
            "sample %s absorptance scatters %.6g across repeat scans, above the "
            "%g repeatability limit"
            % (sample_id, absorptance_spread, absorptance_limit)
        )
    if emittance_spread > emittance_limit and not math.isclose(
        emittance_spread, emittance_limit, rel_tol=0.0, abs_tol=PROPERTY_TOLERANCE
    ):
        findings.append(
            "sample %s emittance scatters %.6g across repeat scans, above the "
            "%g repeatability limit" % (sample_id, emittance_spread, emittance_limit)
        )
    for wavelength in uncovered:
        findings.append(
            "sample %s reports a band at %g um that the instrument spectral range "
            "never covered" % (sample_id, wavelength)
        )
    return {
        "id": sample_id,
        "scan_count": len(scans),
        "solar_absorptance": absorptance,
        "hemispherical_emittance": emittance,
        "absorptance_emittance_ratio": ratio,
        "absorptance_spread": absorptance_spread,
        "emittance_spread": emittance_spread,
        "bands_out_of_instrument_range": uncovered,
        "repeatable": not any(
            "scatters" in item or "scan(s)" in item for item in findings
        ),
        "conforms": not findings,
        "findings": findings,
    }


def assess_thermo_optical_measurement(spec):
    """Run the full clause 6.4.3.6.2 thermo optical measurement assessment.

    spec keys: designated_ids (the subgroup the plan named), samples (non-empty
    sequence of measured samples, each with repeat scans), instruments
    (reflectometer_range_um and emissometer_range_um), optional limits
    (required_scans, absorptance_repeatability, emittance_repeatability).
    """
    data = _mapping("spec", spec, ("designated_ids", "samples", "instruments"))
    samples = data["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("spec['samples'] must be a non-empty sequence of samples")
    limits = data.get("limits")
    records = []
    findings = []
    for sample in samples:
        record = evaluate_sample(sample, data["instruments"], limits)
        records.append(record)
        findings.extend(record["findings"])
    coverage = resolve_subgroup(
        data["designated_ids"], [record["id"] for record in records]
    )
    for sample_id in coverage["missing"]:
        findings.append(
            "designated sample %s carries no thermo optical measurement" % sample_id
        )
    for sample_id in coverage["extra"]:
        findings.append(
            "sample %s was measured but sits outside the designated subgroup"
            % sample_id
        )
    absorptances = [record["solar_absorptance"] for record in records]
    emittances = [record["hemispherical_emittance"] for record in records]
    return {
        "coverage": coverage,
        "sample_records": records,
        "samples_measured": len(records),
        "subgroup_size": len(coverage["designated"]),
        "mean_solar_absorptance": mean_value(absorptances),
        "mean_hemispherical_emittance": mean_value(emittances),
        "findings": findings,
        "valid": not findings,
    }
