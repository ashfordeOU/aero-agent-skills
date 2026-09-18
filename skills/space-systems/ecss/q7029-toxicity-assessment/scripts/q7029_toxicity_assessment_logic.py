"""Offgassing toxicity assessment against spacecraft maximum allowable limits.

Anchor: ECSS-Q-ST-70-29 assessment step -- grading the offgassing load of a
material or assembled article against the spacecraft maximum allowable
concentrations (SMACs) for the crew compartment. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the cabin model: vessel and cabin volumes, tested and flown mass,
   and the exposure duration the SMAC set is stated for.
2. Scale each measured vessel concentration to the predicted cabin
   concentration through the mass ratio and the volume ratio.
3. Apply and record any credited trace-contaminant removal fraction.
4. Look up the SMAC at the stated exposure duration; a missing entry is a gap
   record and a finding, never a zero contribution.
5. Form each concentration-to-SMAC ratio, add the ratios inside each
   toxicological group, and take the governing T-value as the largest group
   total.
6. Compare the governing total with the unit boundary under a named tolerance.
"""

import math

__all__ = [
    "T_VALUE_TOLERANCE",
    "T_VALUE_LIMIT",
    "validate_cabin_model",
    "scale_to_cabin",
    "apply_removal_credit",
    "lookup_smac",
    "t_ratio",
    "group_totals",
    "governing_group",
    "assess_toxicity",
]

# The governing total is a sum of quotients; a case that is physically exactly
# at the unit boundary can land a few ULP either side of it. Absorb the
# representation error here rather than by moving the boundary.
T_VALUE_TOLERANCE = 1e-9
T_VALUE_LIMIT = 1.0

_UNGROUPED = "ungrouped"


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def validate_cabin_model(model):
    """Return the validated cabin model used to scale vessel concentrations."""
    if not isinstance(model, dict):
        raise ValueError("cabin model must be a mapping")
    for key in ("vessel_volume_m3", "cabin_volume_m3", "tested_mass_g",
                "flown_mass_g", "exposure_duration_h"):
        if key not in model:
            raise ValueError("cabin model missing required key '%s'" % key)
    validated = {
        "vessel_volume_m3": _positive("vessel_volume_m3", model["vessel_volume_m3"]),
        "cabin_volume_m3": _positive("cabin_volume_m3", model["cabin_volume_m3"]),
        "tested_mass_g": _positive("tested_mass_g", model["tested_mass_g"]),
        "flown_mass_g": _positive("flown_mass_g", model["flown_mass_g"]),
        "exposure_duration_h": _positive(
            "exposure_duration_h", model["exposure_duration_h"]
        ),
    }
    return validated


def scale_to_cabin(vessel_concentration_mg_m3, model):
    """Scale a vessel concentration to the predicted cabin concentration."""
    conc = _non_negative("vessel_concentration_mg_m3", vessel_concentration_mg_m3)
    m = validate_cabin_model(model)
    mass_ratio = m["flown_mass_g"] / m["tested_mass_g"]
    volume_ratio = m["vessel_volume_m3"] / m["cabin_volume_m3"]
    return conc * mass_ratio * volume_ratio


def apply_removal_credit(concentration_mg_m3, removal_fraction):
    """Return the concentration left after a credited removal fraction."""
    conc = _non_negative("concentration_mg_m3", concentration_mg_m3)
    removal = _real("removal_fraction", removal_fraction)
    if removal < 0.0 or removal >= 1.0:
        raise ValueError(
            "removal_fraction must lie in [0, 1), got %r" % (removal_fraction,)
        )
    return conc * (1.0 - removal)


def lookup_smac(smac_table, compound, exposure_duration_h):
    """Return the SMAC in mg/m3 for a compound at an exposure duration, or None."""
    if not isinstance(smac_table, dict) or not smac_table:
        raise ValueError("smac_table must be a non-empty mapping")
    duration = _positive("exposure_duration_h", exposure_duration_h)
    entry = smac_table.get(compound)
    if entry is None:
        return None
    if not isinstance(entry, dict) or not entry:
        raise ValueError("smac_table entry for %s must be a non-empty mapping" % compound)
    best = None
    for key, value in entry.items():
        hours = _positive("smac duration for %s" % compound, key)
        limit = _positive("smac limit for %s at %gh" % (compound, hours), value)
        if math.isclose(hours, duration, rel_tol=1e-12, abs_tol=0.0):
            return limit
        if hours > duration and (best is None or hours < best[0]):
            best = (hours, limit)
    if best is None:
        return None
    return best[1]


def t_ratio(concentration_mg_m3, smac_mg_m3):
    """Return the concentration-to-SMAC ratio of one product."""
    conc = _non_negative("concentration_mg_m3", concentration_mg_m3)
    smac = _positive("smac_mg_m3", smac_mg_m3)
    return conc / smac


def group_totals(records):
    """Return the additive ratio total of each toxicological group."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    totals = {}
    for record in records:
        if not isinstance(record, dict) or "t_ratio" not in record:
            raise ValueError("each record must be a mapping carrying 't_ratio'")
        if record["t_ratio"] is None:
            continue
        group = record.get("group") or _UNGROUPED
        totals[group] = totals.get(group, 0.0) + float(record["t_ratio"])
    return totals


def governing_group(totals):
    """Return (group, total) for the group with the largest additive total."""
    if not isinstance(totals, dict) or not totals:
        raise ValueError("totals must be a non-empty mapping of group -> total")
    best_group = None
    best_total = None
    for group in sorted(totals):
        total = float(totals[group])
        if best_total is None or total > best_total + T_VALUE_TOLERANCE:
            best_group, best_total = group, total
    return (best_group, best_total)


def assess_toxicity(spec):
    """Run the full SMAC assessment over a set of measured offgassing products.

    spec keys: products (sequence of mappings with compound,
    vessel_concentration_mg_m3, optional group and removal_fraction),
    cabin_model (mapping), smac_table (mapping), optional t_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("products", "cabin_model", "smac_table"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    products = spec["products"]
    if not isinstance(products, (list, tuple)) or not products:
        raise ValueError("spec['products'] must be a non-empty sequence")
    model = validate_cabin_model(spec["cabin_model"])
    limit = _positive("t_limit", spec.get("t_limit", T_VALUE_LIMIT))
    records = []
    gaps = []
    credits = []
    seen = set()
    for product in products:
        if not isinstance(product, dict):
            raise ValueError("each product must be a mapping")
        for key in ("compound", "vessel_concentration_mg_m3"):
            if key not in product:
                raise ValueError("product missing required key '%s'" % key)
        compound = product["compound"]
        if not isinstance(compound, str) or not compound.strip():
            raise ValueError("compound must be a non-empty string")
        compound = compound.strip()
        if compound in seen:
            raise ValueError("duplicate compound %r in the product list" % compound)
        seen.add(compound)
        cabin = scale_to_cabin(product["vessel_concentration_mg_m3"], model)
        removal = product.get("removal_fraction", 0.0)
        after = apply_removal_credit(cabin, removal)
        if float(removal) > 0.0:
            credits.append(compound)
        smac = lookup_smac(spec["smac_table"], compound, model["exposure_duration_h"])
        record = {
            "compound": compound,
            "group": product.get("group") or _UNGROUPED,
            "cabin_concentration_mg_m3": after,
            "removal_fraction": float(removal),
            "smac_mg_m3": smac,
            "t_ratio": None,
        }
        if smac is None:
            gaps.append(compound)
            record["note"] = "no SMAC available at the stated exposure duration"
        else:
            record["t_ratio"] = t_ratio(after, smac)
        records.append(record)
    totals = group_totals(records)
    findings = []
    if not totals:
        governing, governing_total = (None, 0.0)
        findings.append("no product carried a usable SMAC; assessment is empty")
    else:
        governing, governing_total = governing_group(totals)
    if gaps:
        findings.append(
            "no published SMAC for: %s; these are gaps, not zero contributions"
            % ", ".join(sorted(gaps))
        )
    if credits:
        findings.append(
            "verdict relies on a credited removal fraction for: %s"
            % ", ".join(sorted(credits))
        )
    within = governing_total <= limit + T_VALUE_TOLERANCE
    if not within:
        findings.append(
            "governing group %r totals %.4f against the limit %.4f"
            % (governing, governing_total, limit)
        )
    drivers = sorted(
        (r for r in records if r["t_ratio"] is not None and r["group"] == governing),
        key=lambda r: (-r["t_ratio"], r["compound"]),
    )
    return {
        "records": records,
        "group_totals": totals,
        "governing_group": governing,
        "governing_t_value": governing_total,
        "t_limit": limit,
        "driving_compounds": [r["compound"] for r in drivers],
        "smac_gaps": sorted(gaps),
        "removal_credits": sorted(credits),
        "acceptable": within and not gaps,
        "findings": findings,
    }
