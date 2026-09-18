"""Coating defect grouping and disposition for an applied paint system.

Anchor: ECSS-Q-ST-70-31C, Quality. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Group each recorded imperfection under one of the coating defect families
   the process controls: runs, sags, pinholes, orange peel, inclusions and
   contamination.
2. Scale the family's size and density allowances by the surface the defect
   sits on. A plain structural face, a thermo-optical control surface, a
   bonding or electrical contact face and an optical face do not tolerate the
   same imperfection.
3. Grade each defect twice: against the individual size limit, and against
   the density limit formed from its count over the inspected area.
4. Map a breach to the disposition that family earns -- a local rework, a
   strip and recoat, or a referral -- and escalate anything out of limits on
   an optical face to a referral.
5. Roll the per-defect dispositions up to the worst one on the lot and report
   it with every finding named.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "DEFECT_FAMILIES",
    "SURFACE_ALLOWANCE_FACTORS",
    "DISPOSITION_ORDER",
    "validate_positive",
    "defect_family_limits",
    "surface_allowance_factor",
    "defect_density_per_m2",
    "validate_defect",
    "grade_defect",
    "worst_disposition",
    "assess_defects",
]

# Counts over areas land exactly on a density limit. Absorb the
# representation error here, never by loosening the limit.
LIMIT_TOLERANCE = 1e-9

# Per-family allowances on a plain structural surface, plus the disposition a
# breach of that family earns.
DEFECT_FAMILIES = {
    "run": {"max_dimension_mm": 0.0, "max_density_per_m2": 0.0,
            "disposition": "local-rework"},
    "sag": {"max_dimension_mm": 0.0, "max_density_per_m2": 0.0,
            "disposition": "local-rework"},
    "orange-peel": {"max_dimension_mm": 0.0, "max_density_per_m2": 0.0,
                    "disposition": "local-rework"},
    "pinhole": {"max_dimension_mm": 0.5, "max_density_per_m2": 4.0,
                "disposition": "strip-and-recoat"},
    "inclusion": {"max_dimension_mm": 0.8, "max_density_per_m2": 2.0,
                  "disposition": "local-rework"},
    "contamination": {"max_dimension_mm": 0.0, "max_density_per_m2": 0.0,
                      "disposition": "strip-and-recoat"},
}

# How much of the structural-surface allowance each surface category keeps.
SURFACE_ALLOWANCE_FACTORS = {
    "general": 1.0,
    "thermal-control": 0.5,
    "bonding": 0.25,
    "optical": 0.0,
}

# Increasing severity; the lot carries the worst one present.
DISPOSITION_ORDER = ["accept", "local-rework", "strip-and-recoat", "refer-to-review-board"]


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


def defect_family_limits(family):
    """Return the structural-surface allowances for a defect family."""
    if not isinstance(family, str):
        raise ValueError("family must be a string, got %r" % (family,))
    key = family.strip().lower()
    if key not in DEFECT_FAMILIES:
        raise ValueError(
            "unknown defect family '%s'; known families: %s"
            % (family, ", ".join(sorted(DEFECT_FAMILIES)))
        )
    return dict(DEFECT_FAMILIES[key])


def surface_allowance_factor(category):
    """Return the fraction of the structural allowance a surface keeps."""
    if not isinstance(category, str):
        raise ValueError("surface category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in SURFACE_ALLOWANCE_FACTORS:
        raise ValueError(
            "unknown surface category '%s'; known categories: %s"
            % (category, ", ".join(sorted(SURFACE_ALLOWANCE_FACTORS)))
        )
    return SURFACE_ALLOWANCE_FACTORS[key]


def defect_density_per_m2(count, area_m2):
    """Return the areal density of a defect count over the inspected area."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 0:
        raise ValueError("count must be non-negative, got %d" % count)
    area = validate_positive(area_m2, "area_m2")
    return count / area


def validate_defect(defect, index=0):
    """Return a validated defect record as a plain mapping."""
    if not isinstance(defect, dict):
        raise ValueError("defects[%d] must be a mapping" % index)
    for key in ("family", "count", "max_dimension_mm", "surface_category"):
        if key not in defect:
            raise ValueError("defects[%d] missing required key '%s'" % (index, key))
    family = defect["family"]
    defect_family_limits(family)
    count = defect["count"]
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("defects[%d].count must be an integer, got %r" % (index, count))
    if count < 1:
        raise ValueError(
            "defects[%d].count must be at least one; an absent defect is not a record"
            % index
        )
    dimension = _real(defect["max_dimension_mm"], "defects[%d].max_dimension_mm" % index)
    if dimension < 0.0:
        raise ValueError(
            "defects[%d].max_dimension_mm must be non-negative, got %g" % (index, dimension)
        )
    surface_allowance_factor(defect["surface_category"])
    return {
        "family": str(family).strip().lower(),
        "count": count,
        "max_dimension_mm": dimension,
        "surface_category": str(defect["surface_category"]).strip().lower(),
        "location": str(defect.get("location", "unrecorded")),
    }


def grade_defect(defect, area_m2, index=0):
    """Grade one defect record against its scaled family allowances."""
    record = validate_defect(defect, index)
    limits = defect_family_limits(record["family"])
    factor = surface_allowance_factor(record["surface_category"])
    size_limit = limits["max_dimension_mm"] * factor
    density_limit = limits["max_density_per_m2"] * factor
    density = defect_density_per_m2(record["count"], area_m2)

    size_exceeded = record["max_dimension_mm"] > size_limit + LIMIT_TOLERANCE
    density_exceeded = density > density_limit + LIMIT_TOLERANCE
    findings = []
    disposition = "accept"
    if size_exceeded or density_exceeded:
        disposition = limits["disposition"]
        if record["surface_category"] == "optical":
            disposition = "refer-to-review-board"
        if size_exceeded:
            findings.append(
                "%s on %s: %.2f mm exceeds the %.2f mm allowed there"
                % (record["family"], record["surface_category"],
                   record["max_dimension_mm"], size_limit)
            )
        if density_exceeded:
            findings.append(
                "%s on %s: %.3f per m2 exceeds the %.3f per m2 allowed there"
                % (record["family"], record["surface_category"], density, density_limit)
            )
    out = dict(record)
    out.update(
        {
            "density_per_m2": density,
            "size_limit_mm": size_limit,
            "density_limit_per_m2": density_limit,
            "size_exceeded": size_exceeded,
            "density_exceeded": density_exceeded,
            "disposition": disposition,
            "findings": findings,
        }
    )
    return out


def worst_disposition(dispositions):
    """Return the most severe disposition present in the sequence."""
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    worst = "accept"
    for item in dispositions:
        if item not in DISPOSITION_ORDER:
            raise ValueError("unknown disposition '%r'" % (item,))
        if DISPOSITION_ORDER.index(item) > DISPOSITION_ORDER.index(worst):
            worst = item
    return worst


def assess_defects(spec):
    """Run the full defect grouping and disposition assessment.

    spec keys: inspected_area_m2, defects (each with family, count,
    max_dimension_mm, surface_category, optional location).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("inspected_area_m2", "defects"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    area = validate_positive(spec["inspected_area_m2"], "inspected_area_m2")
    defects = spec["defects"]
    if not isinstance(defects, (list, tuple)):
        raise ValueError("spec['defects'] must be a sequence")
    records = [grade_defect(defect, area, i) for i, defect in enumerate(defects)]
    findings = [text for record in records for text in record["findings"]]
    by_family = {}
    for record in records:
        by_family.setdefault(record["family"], 0)
        by_family[record["family"]] += record["count"]
    total = sum(record["count"] for record in records)
    disposition = worst_disposition([record["disposition"] for record in records])
    return {
        "inspected_area_m2": area,
        "defects": records,
        "counts_by_family": by_family,
        "total_defect_count": total,
        "total_density_per_m2": total / area,
        "disposition": disposition,
        "findings": findings,
        "acceptable": disposition == "accept",
    }
