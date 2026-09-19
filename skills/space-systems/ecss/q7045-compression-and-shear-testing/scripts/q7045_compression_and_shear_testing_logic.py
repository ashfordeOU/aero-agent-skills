"""Compression and shear test methods for metallic materials, where applicable.

Anchor: ECSS-Q-ST-70-45, methods clause -- besides tension, the mechanical
test set covers compression of short specimens and shear of pins and plate
coupons, each applicable only to the properties it can actually deliver.
Paraphrased into an implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Which method a required property can be obtained from, and whether the
specimen that was tested could return that property at all.

1. Applicability first. A property is asked of the method that measures it.
   Shear modulus does not come out of a pin shear rig and compressive yield
   does not come out of a lap coupon; naming the method that cannot deliver
   the property is the failure this module exists to stop.
2. A compression specimen is a short column. Its slenderness decides whether
   the recorded peak is material strength or the Euler load of a strut, and
   the two are indistinguishable in the load trace.
3. Shear strength depends on how many planes carried the load. A double-shear
   pin presents two areas, and dividing by one of them halves the answer.
4. A finding is reported, not silently corrected. A buckling-limited run is
   still a run; what it is not is a compressive strength.
"""

import math

__all__ = [
    "MODES",
    "SLENDERNESS_BAND",
    "BUCKLING_ALERT_RATIO",
    "PROPERTY_METHODS",
    "method_for_property",
    "radius_of_gyration_mm",
    "slenderness_ratio",
    "euler_buckling_stress_mpa",
    "shear_plane_area_mm2",
    "shear_strength_mpa",
    "compressive_strength_mpa",
    "assess_compression_and_shear_test",
]

# The loading arrangements this module covers.
MODES = ("compression", "single-shear", "double-shear")

# Length-to-diameter band a short compression specimen has to sit inside.
SLENDERNESS_BAND = (1.5, 3.0)

# Above this fraction of the Euler stress the column, not the material, set
# the peak load.
BUCKLING_ALERT_RATIO = 0.5

# Which arrangement can actually deliver each property. A property mapped to
# None is outside the compression and shear method set entirely.
PROPERTY_METHODS = {
    "compressive-yield-strength": "compression",
    "compressive-ultimate-strength": "compression",
    "compressive-modulus": "compression",
    "ultimate-shear-strength-pin": "double-shear",
    "ultimate-shear-strength-coupon": "single-shear",
    "shear-modulus": None,
    "fracture-toughness": None,
}

# Comparisons at a band edge are inclusive; absorb representation error there
# rather than widening the band itself.
REL_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _within(value, low, high):
    slack = REL_TOLERANCE * max(abs(low), abs(high), 1.0)
    return low - slack <= value <= high + slack


def method_for_property(name):
    """Return the arrangement that can deliver a property, or None when none can."""
    if not isinstance(name, str):
        raise ValueError("property name must be a string, got %r" % (name,))
    if name not in PROPERTY_METHODS:
        raise ValueError("'%s' is not a property this method set covers" % name)
    return PROPERTY_METHODS[name]


def radius_of_gyration_mm(diameter_mm):
    """Return the radius of gyration of a solid circular section."""
    return _as_positive_float(diameter_mm, "diameter_mm") / 4.0


def slenderness_ratio(length_mm, diameter_mm):
    """Return the effective slenderness of a solid circular compression specimen."""
    length = _as_positive_float(length_mm, "length_mm")
    return length / radius_of_gyration_mm(diameter_mm)


def euler_buckling_stress_mpa(modulus_mpa, slenderness, end_fixity=1.0):
    """Return the elastic buckling stress of a strut at a given slenderness."""
    modulus = _as_positive_float(modulus_mpa, "modulus_mpa")
    ratio = _as_positive_float(slenderness, "slenderness")
    fixity = _as_positive_float(end_fixity, "end_fixity")
    return fixity * math.pi * math.pi * modulus / (ratio * ratio)


def shear_plane_area_mm2(diameter_mm, mode):
    """Return the total area carrying the load for a given shear arrangement."""
    diameter = _as_positive_float(diameter_mm, "diameter_mm")
    if mode not in MODES:
        raise ValueError("'%s' is not a covered arrangement" % (mode,))
    if mode == "compression":
        raise ValueError("compression is not a shear arrangement")
    single = math.pi * diameter * diameter / 4.0
    return single * (2.0 if mode == "double-shear" else 1.0)


def shear_strength_mpa(load_n, diameter_mm, mode):
    """Return shear strength, dividing by every plane that carried the load."""
    load = _as_positive_float(load_n, "load_n")
    return load / shear_plane_area_mm2(diameter_mm, mode)


def compressive_strength_mpa(load_n, diameter_mm):
    """Return the engineering compressive stress at the recorded peak load."""
    load = _as_positive_float(load_n, "load_n")
    diameter = _as_positive_float(diameter_mm, "diameter_mm")
    return load / (math.pi * diameter * diameter / 4.0)


def _assess_compression(spec):
    diameter = _as_positive_float(spec["diameter_mm"], "diameter_mm")
    length = _as_positive_float(spec["length_mm"], "length_mm")
    modulus = _as_positive_float(spec["modulus_mpa"], "modulus_mpa")
    fixity = _as_positive_float(spec.get("end_fixity", 1.0), "end_fixity")
    strength = compressive_strength_mpa(spec["peak_load_n"], diameter)
    ratio = slenderness_ratio(length, diameter)
    euler = euler_buckling_stress_mpa(modulus, ratio, fixity)
    utilisation = strength / euler
    findings = []
    low, high = SLENDERNESS_BAND
    shape = length / diameter
    if not _within(shape, low, high):
        findings.append(
            "length-to-diameter ratio %.4f is outside the short-specimen band "
            "%.2f to %.2f" % (shape, low, high)
        )
    if utilisation >= BUCKLING_ALERT_RATIO - REL_TOLERANCE:
        findings.append(
            "peak stress %.3f MPa reaches %.1f%% of the Euler stress %.3f MPa; "
            "the column, not the material, set the peak load"
            % (strength, utilisation * 100.0, euler)
        )
    return {
        "strength_mpa": strength,
        "length_to_diameter": shape,
        "slenderness_ratio": ratio,
        "euler_stress_mpa": euler,
        "buckling_utilisation": utilisation,
        "findings": findings,
    }


def _assess_shear(spec, mode):
    diameter = _as_positive_float(spec["diameter_mm"], "diameter_mm")
    area = shear_plane_area_mm2(diameter, mode)
    strength = shear_strength_mpa(spec["peak_load_n"], diameter, mode)
    findings = []
    planes = 2 if mode == "double-shear" else 1
    if spec.get("declared_planes") is not None:
        declared = spec["declared_planes"]
        if not isinstance(declared, int) or isinstance(declared, bool):
            raise ValueError("declared_planes must be an integer")
        if declared != planes:
            findings.append(
                "arrangement '%s' carries %d plane(s) but %d was declared"
                % (mode, planes, declared)
            )
    return {
        "strength_mpa": strength,
        "shear_area_mm2": area,
        "planes": planes,
        "findings": findings,
    }


def assess_compression_and_shear_test(spec):
    """Decide whether a compression or shear run delivers the required property.

    spec keys: property (the property being sought), mode (one of MODES),
    diameter_mm, peak_load_n; compression additionally needs length_mm and
    modulus_mpa, and accepts end_fixity. Shear accepts declared_planes.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("property", "mode", "diameter_mm", "peak_load_n"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    mode = spec["mode"]
    if mode not in MODES:
        raise ValueError("'%s' is not a covered arrangement" % (mode,))
    wanted = method_for_property(spec["property"])

    findings = []
    if wanted is None:
        findings.append(
            "property '%s' cannot be obtained from a compression or shear run; "
            "no arrangement in this method set measures it" % spec["property"]
        )
    elif wanted != mode:
        findings.append(
            "property '%s' is measured by the '%s' arrangement, but the run "
            "used '%s'" % (spec["property"], wanted, mode)
        )

    if mode == "compression":
        for key in ("length_mm", "modulus_mpa"):
            if key not in spec:
                raise ValueError("a compression run needs '%s'" % key)
        detail = _assess_compression(spec)
    else:
        detail = _assess_shear(spec, mode)
    findings.extend(detail["findings"])

    result = {
        "property": spec["property"],
        "mode": mode,
        "applicable_mode": wanted,
        "strength_mpa": detail["strength_mpa"],
        "findings": findings,
        "property_delivered": not findings,
    }
    for key, value in detail.items():
        if key not in ("findings", "strength_mpa"):
            result[key] = value
    return result
