"""Applying flammability screening results to crewed-compartment control.

Anchor: ECSS-Q-ST-70-21C, the interface clause that hands the result of
an upward flame propagation run to the material control of a habitable
compartment under ECSS-Q-ST-70C (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A flammability entry is evidence only inside the atmosphere it was
   obtained in. The compartment's oxygen partial pressure is what the
   tested partial pressure must bound; a milder test is not evidence for
   a harsher cabin, so the usage goes to assessment rather than through.
2. The entry is evidence only for the configuration tested. An installed
   thickness outside the tested band is a different configuration and
   the entry does not speak for it.
3. A propagating material is not automatically excluded from a crewed
   compartment; it is excluded from open installation. Sealed
   non-combustible containment, or a quantity small enough that there is
   nothing to propagate through, are the two ways it can still be used,
   and both have to be recorded as the reason.
4. A material that self-extinguishes but drips burning material is safe
   above nothing and unsafe above something ignitable. The usage
   geometry, not the rating alone, decides.
5. A compartment is more than its worst item. Exposed area of every item
   that is only acceptable with containment or still under assessment is
   summed against a compartment budget, because ten small exceptions
   make one large one.

Stdlib only, offline, deterministic.
"""

TOLERANCE = 1.0e-9

# Installed thickness may differ from the tested band by this much
# before the entry stops describing the installed configuration.
THICKNESS_TOLERANCE_MM = 0.05

# An exposed item below both of these is too little material to sustain
# propagation on its own.
EXEMPT_AREA_CM2 = 10.0
EXEMPT_MASS_G = 5.0

# Total exposed area of contained or unresolved items a single
# compartment may carry before the accumulation is itself a finding.
COMPARTMENT_EXCEPTION_BUDGET_CM2 = 100.0

NOT_PROPAGATING = "not-propagating"
NOT_PROPAGATING_RESTRICTED = "not-propagating-with-drip-restriction"
PROPAGATING = "propagating"
RATINGS = (NOT_PROPAGATING, NOT_PROPAGATING_RESTRICTED, PROPAGATING)

CONTAINMENT_NONE = "none"
CONTAINMENT_SEALED = "sealed-non-combustible-enclosure"
CONTAINMENT_HOUSING = "vented-metal-housing"
CONTAINMENTS = (CONTAINMENT_NONE, CONTAINMENT_SEALED, CONTAINMENT_HOUSING)

ACCEPTED = "accepted"
ACCEPTED_WITH_CONTAINMENT = "accepted-with-containment"
NEEDS_ASSESSMENT = "needs-assessment"
REJECTED = "rejected"

# Worst-first ordering used to roll a compartment up.
SEVERITY = {
    ACCEPTED: 0,
    ACCEPTED_WITH_CONTAINMENT: 1,
    NEEDS_ASSESSMENT: 2,
    REJECTED: 3,
}


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def oxygen_partial_pressure(oxygen_volume_pct, total_pressure_kpa):
    """Oxygen partial pressure of an atmosphere, in kPa."""
    fraction = _numeric("oxygen_volume_pct", oxygen_volume_pct, 0.0, 100.0)
    total = _numeric("total_pressure_kpa", total_pressure_kpa, 0.0)
    if total <= 0.0:
        raise ValueError("total_pressure_kpa must be greater than zero")
    return fraction * total / 100.0


def validate_entry(entry):
    """Validate a flammability data-set entry offered as evidence."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    rating = _text("rating", entry.get("rating"))
    if rating not in RATINGS:
        raise ValueError("rating %r is not a recorded flammability rating" % rating)
    return {
        "material_designation": _text(
            "material_designation", entry.get("material_designation")
        ),
        "rating": rating,
        "tested_oxygen_partial_pressure_kpa": _numeric(
            "tested_oxygen_partial_pressure_kpa",
            entry.get("tested_oxygen_partial_pressure_kpa"),
            0.0,
        ),
        "tested_thickness_mm": _numeric(
            "tested_thickness_mm", entry.get("tested_thickness_mm"), 0.0
        ),
    }


def validate_usage(usage):
    """Validate one proposed installation in a crewed compartment."""
    if not isinstance(usage, dict):
        raise ValueError("usage must be a mapping")
    containment = _text("containment", usage.get("containment", CONTAINMENT_NONE))
    if containment not in CONTAINMENTS:
        raise ValueError("containment %r is not a recognised form" % containment)
    thickness = _numeric(
        "installed_thickness_mm", usage.get("installed_thickness_mm"), 0.0
    )
    if thickness <= 0.0:
        raise ValueError("installed_thickness_mm must be greater than zero")
    return {
        "location_id": _text("location_id", usage.get("location_id")),
        "compartment_oxygen_volume_pct": _numeric(
            "compartment_oxygen_volume_pct",
            usage.get("compartment_oxygen_volume_pct"),
            0.0,
            100.0,
        ),
        "compartment_total_pressure_kpa": _numeric(
            "compartment_total_pressure_kpa",
            usage.get("compartment_total_pressure_kpa"),
            0.0,
        ),
        "installed_thickness_mm": thickness,
        "exposed_area_cm2": _numeric(
            "exposed_area_cm2", usage.get("exposed_area_cm2"), 0.0
        ),
        "mass_g": _numeric("mass_g", usage.get("mass_g"), 0.0),
        "ignitable_item_below": _flag(
            "ignitable_item_below", usage.get("ignitable_item_below", False)
        ),
        "containment": containment,
    }


def atmosphere_covered(entry, usage):
    """Does the tested atmosphere bound the compartment atmosphere?"""
    tested = entry["tested_oxygen_partial_pressure_kpa"]
    cabin = oxygen_partial_pressure(
        usage["compartment_oxygen_volume_pct"],
        usage["compartment_total_pressure_kpa"],
    )
    return {
        "covered": tested + TOLERANCE >= cabin,
        "tested_kpa": tested,
        "compartment_kpa": cabin,
    }


def configuration_covered(entry, usage):
    """Is the installed thickness inside the band the entry was tested at?"""
    delta = abs(entry["tested_thickness_mm"] - usage["installed_thickness_mm"])
    return delta <= THICKNESS_TOLERANCE_MM + TOLERANCE


def small_quantity_exempt(usage):
    """Too little exposed material to sustain propagation on its own."""
    return (
        usage["exposed_area_cm2"] <= EXEMPT_AREA_CM2 + TOLERANCE
        and usage["mass_g"] <= EXEMPT_MASS_G + TOLERANCE
    )


def isolates_from_the_cabin(usage):
    """Does the containment keep a burning item away from cabin air?"""
    return usage["containment"] == CONTAINMENT_SEALED


def assess_usage(entry, usage):
    """Decide whether one material may be installed where it is proposed."""
    checked_entry = validate_entry(entry)
    checked_usage = validate_usage(usage)
    reasons = []

    atmosphere = atmosphere_covered(checked_entry, checked_usage)
    if not atmosphere["covered"]:
        reasons.append("test-atmosphere-milder-than-the-compartment")
    if not configuration_covered(checked_entry, checked_usage):
        reasons.append("installed-thickness-outside-the-tested-band")

    if reasons:
        disposition = NEEDS_ASSESSMENT
    elif checked_entry["rating"] == PROPAGATING:
        if isolates_from_the_cabin(checked_usage):
            disposition = ACCEPTED_WITH_CONTAINMENT
            reasons.append("propagating-material-sealed-from-cabin-air")
        elif small_quantity_exempt(checked_usage):
            disposition = NEEDS_ASSESSMENT
            reasons.append("propagating-material-below-the-quantity-limit")
        else:
            disposition = REJECTED
            reasons.append("propagating-material-openly-installed")
    elif checked_entry["rating"] == NOT_PROPAGATING_RESTRICTED:
        if not checked_usage["ignitable_item_below"]:
            disposition = ACCEPTED
        elif checked_usage["containment"] != CONTAINMENT_NONE:
            disposition = ACCEPTED_WITH_CONTAINMENT
            reasons.append("drip-restriction-met-by-containment")
        else:
            disposition = REJECTED
            reasons.append("dripping-material-above-an-ignitable-item")
    else:
        disposition = ACCEPTED

    return {
        "location_id": checked_usage["location_id"],
        "material_designation": checked_entry["material_designation"],
        "rating": checked_entry["rating"],
        "disposition": disposition,
        "reasons": reasons,
        "tested_kpa": atmosphere["tested_kpa"],
        "compartment_kpa": atmosphere["compartment_kpa"],
        "exposed_area_cm2": checked_usage["exposed_area_cm2"],
    }


def worst_disposition(dispositions):
    """The governing disposition of a set of installations."""
    if not isinstance(dispositions, list) or not dispositions:
        raise ValueError("dispositions must be a non-empty list")
    for value in dispositions:
        if value not in SEVERITY:
            raise ValueError("%r is not a disposition" % (value,))
    return max(dispositions, key=lambda d: SEVERITY[d])


def assess_compartment(items):
    """Roll a set of proposed installations up to a compartment verdict."""
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    results = []
    findings = []
    exception_area = 0.0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be a mapping with entry and usage")
        result = assess_usage(item.get("entry"), item.get("usage"))
        results.append(result)
        if result["disposition"] in (ACCEPTED_WITH_CONTAINMENT, NEEDS_ASSESSMENT):
            exception_area += result["exposed_area_cm2"]
        if result["disposition"] == REJECTED:
            findings.append(
                "rejected-installation-at-%s" % result["location_id"]
            )
    if exception_area > COMPARTMENT_EXCEPTION_BUDGET_CM2 + TOLERANCE:
        findings.append("exception-area-over-the-compartment-budget")
    return {
        "results": results,
        "governing_disposition": worst_disposition(
            [r["disposition"] for r in results]
        ),
        "exception_area_cm2": exception_area,
        "findings": findings,
        "clean": not findings,
    }
