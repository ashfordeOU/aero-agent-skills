#!/usr/bin/env python3
"""Reduction of a coverglass transmission scan taken into an adhesive.

Anchor: ECSS-E-ST-20-08C clause 8.7.9. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause asks a different question from the into-air scan. A coverglass
sitting alone in a spectrophotometer has an air interface on its far face
and the scan carries the Fresnel reflection at that interface. A coverglass
bonded to a solar cell does not: the adhesive behind it has a refractive
index close to the glass, so most of that reflection disappears. To measure
the transmission the assembly will actually have, a backing piece -- fused
silica, or an uncoated coverglass of the same material -- is bonded behind
the sample with the flight adhesive, and the scan is taken through the whole
stack.

Three consequences drive this reduction.

The backing piece is part of the measurement, not part of the sample. The
stack scan carries the backing's own bulk absorption and its own rear air
interface, neither of which belongs to the coverglass. A reference scan of
the backing piece bonded in the same configuration without the sample
divides those out. Quoting the raw stack figure understates the coverglass
by whatever the backing costs.

The backing piece has to be qualified before its scan is used. A coated
backing piece puts a second coating in the beam; a backing of a material
whose index is far from the adhesive reintroduces an interface the whole
method exists to remove; a bond with a void in it is an air gap wearing the
adhesive's name.

The result is checkable against the into-air figure for the same part. The
gain from removing the rear air interface is a Fresnel ratio computed from
the glass, adhesive and air indices, and it is small -- a few percent. A
corrected figure that beats the into-air figure by much more than that is
not a better coverglass, it is a reduction with the wrong reference scan in
it.

The band, the sampling interval, the index set and the gain tolerance below
are declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Backing piece materials the clause admits behind the sample, with the
# refractive index each is carried at in the declared reduction model.
BACKING_MATERIALS = {
    "fused-silica-backing-piece": 1.4585,
    "uncoated-coverglass-backing-piece": 1.4700,
    "cerium-doped-uncoated-coverglass-backing-piece": 1.4740,
}

RECOGNISED_BACKINGS = tuple(sorted(BACKING_MATERIALS))

BACKING_NOT_QUALIFIED = "backing-piece-not-qualified"
BOND_NOT_VOID_FREE = "backing-bond-not-void-free"
BASELINE_NOT_REFERENCED = "baseline-calibration-not-referenced"
BAND_NOT_COVERED = "specified-band-not-covered"
SAMPLING_TOO_COARSE = "sampling-interval-too-coarse"
GAIN_NOT_PHYSICAL = "interface-gain-not-physical"
AVERAGE_BELOW_REQUIREMENT = "band-average-below-requirement"
AVERAGE_MEETS_REQUIREMENT = "band-average-meets-requirement"

DEFAULT_STACK_POLICY = {
    "band_start_nm": 350.0,
    "band_end_nm": 1800.0,
    "max_sample_interval_nm": 10.0,
    "refractive_index_air": 1.0,
    "refractive_index_coverglass": 1.4700,
    "refractive_index_adhesive": 1.4100,
    "max_bond_void_fraction": 0.01,
    "gain_tolerance": 0.02,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_stack_policy(policy):
    """Check a bonded-stack policy names a real band and a usable index set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    start = _require_positive("band_start_nm", policy.get("band_start_nm"))
    end = _require_positive("band_end_nm", policy.get("band_end_nm"))
    if not end > start:
        raise ValueError(
            "band_end_nm %g must be above band_start_nm %g; a band of zero "
            "width has no average" % (end, start)
        )
    interval = _require_positive(
        "max_sample_interval_nm", policy.get("max_sample_interval_nm")
    )
    if interval > (end - start):
        raise ValueError(
            "max_sample_interval_nm %g is wider than the %g nm band, so no "
            "scan could ever be too coarse" % (interval, end - start)
        )
    air = _require_positive("refractive_index_air", policy.get("refractive_index_air"))
    glass = _require_positive(
        "refractive_index_coverglass", policy.get("refractive_index_coverglass")
    )
    adhesive = _require_positive(
        "refractive_index_adhesive", policy.get("refractive_index_adhesive")
    )
    for name, index in (
        ("refractive_index_air", air),
        ("refractive_index_coverglass", glass),
        ("refractive_index_adhesive", adhesive),
    ):
        if index < 1.0:
            raise ValueError(
                "%s %g is below one; no transparent medium refracts less than "
                "vacuum" % (name, index)
            )
    if not glass > air:
        raise ValueError(
            "refractive_index_coverglass %g must exceed the ambient index %g, "
            "or there is no rear interface to remove" % (glass, air)
        )
    void = _require_non_negative(
        "max_bond_void_fraction", policy.get("max_bond_void_fraction")
    )
    if void >= 1.0:
        raise ValueError(
            "max_bond_void_fraction %g admits a bond that is mostly void" % void
        )
    _require_positive("gain_tolerance", policy.get("gain_tolerance"))
    return policy


def normal_incidence_reflectance(index_one, index_two):
    """Fresnel reflectance of one interface between two media at normal incidence."""
    first = _require_positive("index_one", index_one)
    second = _require_positive("index_two", index_two)
    return ((first - second) / (first + second)) ** 2


def expected_interface_gain(
    index_coverglass, index_adhesive, index_air=1.0
):
    """Transmission gain from replacing a rear air interface with an adhesive one."""
    glass = _require_positive("index_coverglass", index_coverglass)
    adhesive = _require_positive("index_adhesive", index_adhesive)
    air = _require_positive("index_air", index_air)
    if not glass > air:
        raise ValueError(
            "index_coverglass %g must exceed index_air %g" % (glass, air)
        )
    into_air = 1.0 - normal_incidence_reflectance(glass, air)
    into_adhesive = 1.0 - normal_incidence_reflectance(glass, adhesive)
    if into_air <= 0.0:
        raise ValueError("the rear air interface reflects everything; no gain exists")
    return into_adhesive / into_air


def validate_backing_piece(backing):
    """Check the piece bonded behind the sample belongs in the beam at all."""
    if not isinstance(backing, dict):
        raise ValueError("backing must be a mapping, got %r" % (backing,))
    material = backing.get("material")
    if material not in BACKING_MATERIALS:
        raise ValueError(
            "unknown backing material %r; recognised backings are %s"
            % (material, ", ".join(RECOGNISED_BACKINGS))
        )
    coated = backing.get("coated")
    if not isinstance(coated, bool):
        raise ValueError(
            "backing 'coated' must be True or False, got %r; an unstated "
            "coating is not an absent one" % (coated,)
        )
    _require_positive("backing thickness_mm", backing.get("thickness_mm"))
    _require_non_negative(
        "backing bond_void_fraction", backing.get("bond_void_fraction")
    )
    if backing["bond_void_fraction"] > 1.0:
        raise ValueError(
            "bond_void_fraction %g is above one" % backing["bond_void_fraction"]
        )
    return backing


def backing_is_qualified(backing, index_adhesive, max_index_mismatch=0.10):
    """True when the backing piece may carry the measurement."""
    validate_backing_piece(backing)
    adhesive = _require_positive("index_adhesive", index_adhesive)
    mismatch_limit = _require_positive("max_index_mismatch", max_index_mismatch)
    if backing["coated"]:
        return False
    mismatch = abs(BACKING_MATERIALS[backing["material"]] - adhesive)
    return _at_most(mismatch, mismatch_limit)


def _point(entry, index):
    if isinstance(entry, dict):
        wavelength = entry.get("wavelength_nm")
        transmittance = entry.get("transmittance")
    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
        wavelength, transmittance = entry
    else:
        raise ValueError(
            "scan point %d must be a (wavelength_nm, transmittance) pair or a "
            "mapping, got %r" % (index, entry)
        )
    wavelength = _require_positive("wavelength_nm at point %d" % index, wavelength)
    transmittance = _require_number("transmittance at point %d" % index, transmittance)
    if transmittance < 0.0 or transmittance > 1.0:
        raise ValueError(
            "transmittance %g at point %d is outside zero to one; a "
            "transmittance is a fraction of the incident beam"
            % (transmittance, index)
        )
    return wavelength, transmittance


def validate_scan(points):
    """Check a spectrophotometer scan is orderly and physically readable."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("scan must be a sequence of points")
    if len(points) < 2:
        raise ValueError(
            "a scan of %d point(s) spans no wavelength interval and cannot be "
            "integrated" % len(points)
        )
    reduced = []
    previous = None
    for index, entry in enumerate(points, start=1):
        wavelength, transmittance = _point(entry, index)
        if previous is not None and not wavelength > previous:
            raise ValueError(
                "scan wavelengths must strictly ascend; point %d at %g nm does "
                "not follow %g nm" % (index, wavelength, previous)
            )
        previous = wavelength
        reduced.append((wavelength, transmittance))
    return tuple(reduced)


def scan_span_nm(points):
    """The first and last wavelength the scan actually reaches."""
    reduced = validate_scan(points)
    return reduced[0][0], reduced[-1][0]


def covers_band(points, band_start_nm, band_end_nm):
    """True when the scan reaches both edges of the specified band."""
    start = _require_positive("band_start_nm", band_start_nm)
    end = _require_positive("band_end_nm", band_end_nm)
    if not end > start:
        raise ValueError("band_end_nm must be above band_start_nm")
    first, last = scan_span_nm(points)
    return _at_most(first, start) and _at_least(last, end)


def max_sample_interval_nm(points):
    """The widest gap between adjacent samples in the scan."""
    reduced = validate_scan(points)
    return max(reduced[i + 1][0] - reduced[i][0] for i in range(len(reduced) - 1))


def interpolate_transmittance(points, wavelength_nm):
    """Transmittance at one wavelength, linear between the bracketing samples."""
    reduced = validate_scan(points)
    target = _require_positive("wavelength_nm", wavelength_nm)
    first, last = reduced[0][0], reduced[-1][0]
    if target < first or target > last:
        raise ValueError(
            "%g nm lies outside the %g to %g nm scan; the scan is evidence "
            "only where it was taken" % (target, first, last)
        )
    for index in range(len(reduced) - 1):
        low_w, low_t = reduced[index]
        high_w, high_t = reduced[index + 1]
        if low_w <= target <= high_w:
            width = high_w - low_w
            if width == 0.0:
                return low_t
            return low_t + (high_t - low_t) * (target - low_w) / width
    return reduced[-1][1]


def _band_nodes(points, band_start_nm, band_end_nm, extra=()):
    reduced = validate_scan(points)
    nodes = {band_start_nm, band_end_nm}
    for wavelength, _transmittance in reduced:
        if band_start_nm < wavelength < band_end_nm:
            nodes.add(wavelength)
    for wavelength in extra:
        if band_start_nm < wavelength < band_end_nm:
            nodes.add(wavelength)
    return sorted(nodes)


def band_average_transmittance(points, band_start_nm, band_end_nm):
    """Trapezoidal band average, with the band edges interpolated onto the scan."""
    start = _require_positive("band_start_nm", band_start_nm)
    end = _require_positive("band_end_nm", band_end_nm)
    if not end > start:
        raise ValueError("band_end_nm must be above band_start_nm")
    if not covers_band(points, start, end):
        first, last = scan_span_nm(points)
        raise ValueError(
            "the scan spans %g to %g nm and cannot produce a %g to %g nm band "
            "average; the missing wavelengths would be extrapolation"
            % (first, last, start, end)
        )
    nodes = _band_nodes(points, start, end)
    integral = 0.0
    for index in range(len(nodes) - 1):
        low, high = nodes[index], nodes[index + 1]
        low_t = interpolate_transmittance(points, low)
        high_t = interpolate_transmittance(points, high)
        integral += 0.5 * (low_t + high_t) * (high - low)
    return integral / (end - start)


def backing_corrected_scan(stack_points, backing_points):
    """Divide the backing piece's own loss out of the bonded-stack scan."""
    stack = validate_scan(stack_points)
    backing = validate_scan(backing_points)
    backing_first, backing_last = backing[0][0], backing[-1][0]
    corrected = []
    for wavelength, transmittance in stack:
        if wavelength < backing_first or wavelength > backing_last:
            raise ValueError(
                "the backing reference spans %g to %g nm and does not reach %g "
                "nm; the backing's loss there is unknown, not zero"
                % (backing_first, backing_last, wavelength)
            )
        reference = interpolate_transmittance(backing, wavelength)
        if reference <= 0.0:
            raise ValueError(
                "the backing reference reads zero at %g nm; nothing can be "
                "divided out of an opaque reference" % wavelength
            )
        ratio = transmittance / reference
        if ratio > 1.0:
            if math.isclose(ratio, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
                ratio = 1.0
            else:
                raise ValueError(
                    "the stack transmits %g at %g nm against a backing "
                    "reference of %g; a corrected transmittance above one means "
                    "the two scans are not the same configuration"
                    % (transmittance, wavelength, reference)
                )
        corrected.append((wavelength, ratio))
    return tuple(corrected)


def observed_interface_gain(into_adhesive_average, into_air_average):
    """Ratio of the into-adhesive band figure to the into-air one."""
    adhesive = _require_number("into_adhesive_average", into_adhesive_average)
    air = _require_positive("into_air_average", into_air_average)
    if adhesive < 0.0 or adhesive > 1.0:
        raise ValueError(
            "into_adhesive_average %g is outside zero to one" % adhesive
        )
    if air > 1.0:
        raise ValueError("into_air_average %g is outside zero to one" % air)
    return adhesive / air


def gain_is_physical(observed, expected, tolerance):
    """True when the measured gain sits within tolerance of the Fresnel gain."""
    seen = _require_positive("observed", observed)
    predicted = _require_positive("expected", expected)
    band = _require_positive("tolerance", tolerance)
    return _at_most(abs(seen - predicted), band)


def meets_requirement(average, required_minimum):
    """True when the band average reaches the requirement; a tie is admissible."""
    value = _require_number("average", average)
    minimum = _require_number("required_minimum", required_minimum)
    if not 0.0 <= value <= 1.0:
        raise ValueError("average %g is outside zero to one" % value)
    if not 0.0 < minimum <= 1.0:
        raise ValueError(
            "required_minimum %g must sit above zero and at or below one" % minimum
        )
    return _at_least(value, minimum)


def assess_transmission_into_adhesive(case, policy=DEFAULT_STACK_POLICY):
    """Full clause 8.7.9 reduction and verdict for one bonded-stack scan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_stack_policy(policy)

    start = float(policy["band_start_nm"])
    end = float(policy["band_end_nm"])
    findings = []
    advisories = []
    result = {
        "band_start_nm": start,
        "band_end_nm": end,
        "backing_material": None,
        "baseline_reference": None,
        "scan_first_nm": None,
        "scan_last_nm": None,
        "sample_count": None,
        "max_sample_interval_nm": None,
        "stack_band_average": None,
        "band_average_transmittance": None,
        "expected_interface_gain": None,
        "observed_interface_gain": None,
        "required_minimum": None,
        "margin": None,
        "findings": findings,
        "advisories": advisories,
    }

    backing = case.get("backing")
    validate_backing_piece(backing)
    result["backing_material"] = backing["material"]
    adhesive_index = float(policy["refractive_index_adhesive"])
    if not backing_is_qualified(backing, adhesive_index):
        findings.append(
            "the backing piece is coated or its index is too far from the "
            "adhesive; it puts back an interface this method exists to remove"
        )
        result["verdict"] = BACKING_NOT_QUALIFIED
        return result

    void_limit = float(policy["max_bond_void_fraction"])
    void = float(backing["bond_void_fraction"])
    if not _at_most(void, void_limit):
        findings.append(
            "the bond behind the sample carries a void fraction of %g against "
            "a limit of %g; a void is an air gap wearing the adhesive's name"
            % (void, void_limit)
        )
        result["verdict"] = BOND_NOT_VOID_FREE
        return result

    points = validate_scan(case.get("stack_scan"))
    result["sample_count"] = len(points)
    result["scan_first_nm"] = points[0][0]
    result["scan_last_nm"] = points[-1][0]
    result["max_sample_interval_nm"] = max_sample_interval_nm(points)

    reference = _require_label("baseline_reference", case.get("baseline_reference") or "")
    result["baseline_reference"] = reference or None
    if not reference:
        findings.append(
            "the stack scan carries no baseline calibration reference; an "
            "uncalibrated trace is not a transmission measurement"
        )
        result["verdict"] = BASELINE_NOT_REFERENCED
        return result

    if not covers_band(points, start, end):
        findings.append(
            "the stack scan spans %g to %g nm and the specified band is %g to "
            "%g nm; a band average taken from it would be extrapolation"
            % (points[0][0], points[-1][0], start, end)
        )
        result["verdict"] = BAND_NOT_COVERED
        return result

    interval_limit = float(policy["max_sample_interval_nm"])
    if not _at_most(result["max_sample_interval_nm"], interval_limit):
        findings.append(
            "the widest sample gap is %g nm against a specified %g nm "
            "interval; a coating feature can fall between two points"
            % (result["max_sample_interval_nm"], interval_limit)
        )
        result["verdict"] = SAMPLING_TOO_COARSE
        return result

    result["stack_band_average"] = band_average_transmittance(points, start, end)

    backing_scan = case.get("backing_reference_scan")
    if backing_scan is None:
        advisories.append(
            "no backing reference scan is supplied, so the backing's own bulk "
            "absorption and rear air interface stay inside the reported figure"
        )
        corrected = points
    else:
        corrected = backing_corrected_scan(points, backing_scan)
    average = band_average_transmittance(corrected, start, end)
    result["band_average_transmittance"] = average

    predicted = expected_interface_gain(
        float(policy["refractive_index_coverglass"]),
        adhesive_index,
        float(policy["refractive_index_air"]),
    )
    result["expected_interface_gain"] = predicted
    into_air = case.get("into_air_band_average")
    if into_air is None:
        advisories.append(
            "no into-air band average is supplied for the same part, so the "
            "interface gain cannot be checked against the Fresnel prediction"
        )
    else:
        observed = observed_interface_gain(average, into_air)
        result["observed_interface_gain"] = observed
        if not gain_is_physical(observed, predicted, float(policy["gain_tolerance"])):
            findings.append(
                "the corrected figure beats the into-air figure by a factor of "
                "%.4f against a Fresnel prediction of %.4f; the reduction, not "
                "the coverglass, is what changed" % (observed, predicted)
            )
            result["verdict"] = GAIN_NOT_PHYSICAL
            return result

    required = case.get("required_minimum_transmittance")
    if required is None:
        advisories.append(
            "no minimum transmission is declared for this coverglass, so the "
            "band average is reported without a verdict against a requirement"
        )
        result["verdict"] = AVERAGE_MEETS_REQUIREMENT
        return result

    minimum = _require_number("required_minimum_transmittance", required)
    result["required_minimum"] = minimum
    result["margin"] = average - minimum
    if meets_requirement(average, minimum):
        result["verdict"] = AVERAGE_MEETS_REQUIREMENT
        return result

    findings.append(
        "the %g to %g nm into-adhesive band average is %.4f against a required "
        "minimum of %.4f, short by %.4f"
        % (start, end, average, minimum, minimum - average)
    )
    result["verdict"] = AVERAGE_BELOW_REQUIREMENT
    return result
