"""Purpose of the vacuum thermal-cycling run of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.11.1 (showing that the components, the
assemblies and the interfaces of a photovoltaic assembly survive cycling in a
vacuum environment). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the campaign policy: the chamber pressure that still counts as a
   vacuum environment, the temperature margin the run owes the predicted
   extremes, and the coverage factor applied to the predicted cycle count.
2. Group every declared component, assembly and interface into the survival
   objective it makes the run demonstrate, and mark the items whose failure
   mode only exists once the air is gone -- those are what make the run a
   vacuum run rather than an ambient one.
3. Measure whether the cycled article actually carries each declared item. An
   objective nobody can observe on the article is an objective the run does
   not demonstrate, whatever the chamber does.
4. Check the planned run bounds the environment it stands in for: pressure at
   or below the vacuum limit, hot and cold extremes beyond the predicted ones
   by the margin, and at least the covered cycle count.
5. Close on one verdict -- the vacuum environment is not required, it is
   required but nothing is planned, the planned run falls short, or the
   planned run bounds the flight environment -- carrying the objectives the
   run serves and every shortfall found.
"""

import math

__all__ = [
    "ITEM_CATEGORIES",
    "ITEM_OBJECTIVES",
    "LIMIT_TOLERANCE",
    "VACUUM_PRESSURE_LIMIT_PA",
    "VACUUM_SENSITIVE_ITEMS",
    "assess_article_coverage",
    "assess_vacuum_cycling_purpose",
    "at_or_above",
    "at_or_below",
    "evaluate_environment_bounds",
    "group_demonstration_objectives",
    "pressure_margin_decades",
    "validate_campaign_policy",
]

# Bounds are compared against quantities built from differences and products of
# declared values, so a run that lands exactly on a bound can sit a few ULPs on
# the wrong side. Absorb that representation error here rather than moving any
# engineering bound.
LIMIT_TOLERANCE = 1e-9

# Above this chamber pressure the residual gas still carries heat and still
# suppresses the vacuum-only failure modes, so the run is an ambient-cycling
# run wearing a chamber. A campaign may declare a stricter limit of its own.
VACUUM_PRESSURE_LIMIT_PA = 1.3e-3

# Every item the clause speaks about belongs to one of three families, and the
# purpose statement owes an objective to each family it declares.
ITEM_CATEGORIES = {
    "solar-cell-assembly": "component",
    "coverglass-adhesive": "component",
    "interconnector": "component",
    "bypass-diode": "component",
    "bus-bar-joint": "assembly",
    "substrate-bondline": "assembly",
    "harness-insulation": "assembly",
    "connector-interface": "interface",
    "hinge-interface": "interface",
    "grounding-interface": "interface",
    "thermal-blanket-interface": "interface",
}

# What the run is bought to demonstrate about each item.
ITEM_OBJECTIVES = {
    "solar-cell-assembly":
        "the cell stack endures the expansion mismatch of every cycle without "
        "cracking or losing output",
    "coverglass-adhesive":
        "the coverglass bondline keeps its adhesion while it outgasses and while "
        "the stack expands and contracts",
    "interconnector":
        "the interconnect survives the flexing each cycle imposes without "
        "fatigue cracking",
    "bypass-diode":
        "the protection diode and its joints still conduct and still block after "
        "the cycles",
    "bus-bar-joint":
        "the joined conductors keep a stable joint resistance across the cycles",
    "substrate-bondline":
        "the bond to the substrate carries the cycled shear without disbonding",
    "harness-insulation":
        "the wiring insulation stays intact and keeps its dielectric strength "
        "after outgassing and cycling",
    "connector-interface":
        "the mated contacts keep their contact resistance and separate again "
        "without cold welding",
    "hinge-interface":
        "the moving metallic interface still moves after cycling in vacuum "
        "without cold welding",
    "grounding-interface":
        "the bonding path across the interface keeps its resistance across the "
        "cycles",
    "thermal-blanket-interface":
        "the blanket attachment absorbs the differential motion of every cycle "
        "and stays attached",
}

# Items whose failure mode only exists once the air is gone. One of these on
# the article is what makes an ambient-air cycling run an inadequate substitute.
VACUUM_SENSITIVE_ITEMS = frozenset({
    "coverglass-adhesive",
    "harness-insulation",
    "connector-interface",
    "hinge-interface",
    "thermal-blanket-interface",
})

VERDICT_NOT_REQUIRED = "vacuum-environment-not-required"
VERDICT_NOT_PLANNED = "justified-but-nothing-planned"
VERDICT_UNDER_BOUNDS = "planned-run-under-bounds"
VERDICT_BOUNDING = "planned-run-bounds-the-flight-environment"


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def at_or_below(value, limit):
    """Return True when value respects an upper bound, equality included."""
    v = _real(value, "value")
    lim = _real(limit, "limit")
    if v < lim:
        return True
    return math.isclose(v, lim, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def at_or_above(value, floor):
    """Return True when value respects a lower bound, equality included."""
    v = _real(value, "value")
    low = _real(floor, "floor")
    if v > low:
        return True
    return math.isclose(v, low, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def pressure_margin_decades(chamber_pressure_pa, limit_pa=VACUUM_PRESSURE_LIMIT_PA):
    """Return how many decades the chamber sits below the vacuum limit.

    A negative result means the chamber is above the limit, i.e. the run is
    not being performed in the environment the clause asks for.
    """
    pressure = _positive(chamber_pressure_pa, "chamber_pressure_pa")
    limit = _positive(limit_pa, "limit_pa")
    return math.log10(limit / pressure)


def validate_campaign_policy(policy):
    """Return the normalised campaign policy, refusing a self-defeating one."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    limit = _positive(
        policy.get("vacuum_pressure_limit_pa", VACUUM_PRESSURE_LIMIT_PA),
        "vacuum_pressure_limit_pa",
    )
    margin = _non_negative(
        policy.get("temperature_margin_c", 0.0), "temperature_margin_c"
    )
    coverage = _positive(
        policy.get("cycle_coverage_factor", 1.0), "cycle_coverage_factor"
    )
    if coverage < 1.0:
        raise ValueError(
            "cycle_coverage_factor %g would let the run fall short of the "
            "predicted cycles by construction" % coverage
        )
    return {
        "vacuum_pressure_limit_pa": limit,
        "temperature_margin_c": margin,
        "cycle_coverage_factor": coverage,
    }


def group_demonstration_objectives(items):
    """Return one objective record per declared component, assembly or interface."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of item records")
    seen = set()
    records = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        for key in ("item_id", "item_class"):
            if key not in item:
                raise ValueError("items[%d] missing required key '%s'" % (index, key))
        item_id = item["item_id"]
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("items[%d] item_id must be a non-empty string" % index)
        item_id = item_id.strip()
        if item_id in seen:
            raise ValueError("duplicate item_id %r in items" % item_id)
        seen.add(item_id)
        item_class = item["item_class"]
        if item_class not in ITEM_CATEGORIES:
            raise ValueError(
                "items[%d] item_class %r is not a recognised photovoltaic-assembly "
                "item; declare it or correct it rather than dropping it"
                % (index, item_class)
            )
        on_article = item.get("on_cycled_article", True)
        if not isinstance(on_article, bool):
            raise ValueError("items[%d] on_cycled_article must be a boolean" % index)
        records.append({
            "item_id": item_id,
            "item_class": item_class,
            "category": ITEM_CATEGORIES[item_class],
            "objective": ITEM_OBJECTIVES[item_class],
            "vacuum_specific": item_class in VACUUM_SENSITIVE_ITEMS,
            "on_cycled_article": on_article,
        })
    categories = sorted({record["category"] for record in records})
    vacuum_items = [r["item_id"] for r in records if r["vacuum_specific"]]
    return {
        "objectives": records,
        "categories": categories,
        "vacuum_specific_items": vacuum_items,
        "vacuum_environment_required": bool(vacuum_items),
    }


def assess_article_coverage(objective_records):
    """Return how much of the declared inventory the cycled article carries."""
    if not isinstance(objective_records, (list, tuple)) or not objective_records:
        raise ValueError("objective_records must be a non-empty sequence")
    declared = len(objective_records)
    missing = [r["item_id"] for r in objective_records if not r["on_cycled_article"]]
    carried = declared - len(missing)
    missing_categories = sorted({
        r["category"] for r in objective_records if not r["on_cycled_article"]
    })
    return {
        "declared_items": declared,
        "carried_items": carried,
        "coverage_fraction": carried / float(declared),
        "missing_items": missing,
        "missing_categories": missing_categories,
        "complete": not missing,
    }


def evaluate_environment_bounds(planned_run, predicted_environment, policy):
    """Return every count on which the planned run fails to bound the flight case."""
    normalised = validate_campaign_policy(policy)
    if not isinstance(planned_run, dict):
        raise ValueError("planned_run must be a mapping")
    if not isinstance(predicted_environment, dict):
        raise ValueError("predicted_environment must be a mapping")
    for key in ("chamber_pressure_pa", "hot_extreme_c", "cold_extreme_c", "cycle_count"):
        if key not in planned_run:
            raise ValueError("planned_run missing required key '%s'" % key)
    for key in ("hot_extreme_c", "cold_extreme_c", "cycle_count"):
        if key not in predicted_environment:
            raise ValueError("predicted_environment missing required key '%s'" % key)

    pressure = _positive(planned_run["chamber_pressure_pa"], "chamber_pressure_pa")
    planned_hot = _real(planned_run["hot_extreme_c"], "planned hot_extreme_c")
    planned_cold = _real(planned_run["cold_extreme_c"], "planned cold_extreme_c")
    planned_cycles = _non_negative(planned_run["cycle_count"], "planned cycle_count")
    predicted_hot = _real(predicted_environment["hot_extreme_c"], "predicted hot_extreme_c")
    predicted_cold = _real(predicted_environment["cold_extreme_c"], "predicted cold_extreme_c")
    predicted_cycles = _positive(
        predicted_environment["cycle_count"], "predicted cycle_count"
    )
    if planned_cold >= planned_hot:
        raise ValueError(
            "planned cold extreme %g C is not below the hot extreme %g C"
            % (planned_cold, planned_hot)
        )
    if predicted_cold >= predicted_hot:
        raise ValueError(
            "predicted cold extreme %g C is not below the hot extreme %g C"
            % (predicted_cold, predicted_hot)
        )

    margin = normalised["temperature_margin_c"]
    owed_hot = predicted_hot + margin
    owed_cold = predicted_cold - margin
    owed_cycles = predicted_cycles * normalised["cycle_coverage_factor"]
    decades = pressure_margin_decades(pressure, normalised["vacuum_pressure_limit_pa"])

    shortfalls = []
    pressure_ok = at_or_below(pressure, normalised["vacuum_pressure_limit_pa"])
    if not pressure_ok:
        shortfalls.append(
            "chamber pressure %g Pa is above the %g Pa that still counts as a vacuum "
            "environment" % (pressure, normalised["vacuum_pressure_limit_pa"])
        )
    hot_ok = at_or_above(planned_hot, owed_hot)
    if not hot_ok:
        shortfalls.append(
            "planned hot extreme %g C does not reach the owed %g C" % (planned_hot, owed_hot)
        )
    cold_ok = at_or_below(planned_cold, owed_cold)
    if not cold_ok:
        shortfalls.append(
            "planned cold extreme %g C does not reach the owed %g C" % (planned_cold, owed_cold)
        )
    cycles_ok = at_or_above(planned_cycles, owed_cycles)
    if not cycles_ok:
        shortfalls.append(
            "planned %g cycles fall short of the owed %g cycles" % (planned_cycles, owed_cycles)
        )
    return {
        "chamber_pressure_pa": pressure,
        "pressure_margin_decades": decades,
        "owed_hot_extreme_c": owed_hot,
        "owed_cold_extreme_c": owed_cold,
        "owed_cycle_count": owed_cycles,
        "pressure_within_limit": pressure_ok,
        "hot_extreme_bounds": hot_ok,
        "cold_extreme_bounds": cold_ok,
        "cycle_count_bounds": cycles_ok,
        "shortfalls": shortfalls,
        "bounds_environment": not shortfalls,
    }


def assess_vacuum_cycling_purpose(spec):
    """Run the full clause 5.5.3.11.1 purpose assessment.

    spec keys: items, optional policy, optional planned_run and
    predicted_environment. A spec with no planned_run is a purpose that has
    been stated but not yet served.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "items" not in spec:
        raise ValueError("spec missing required key 'items'")
    grouped = group_demonstration_objectives(spec["items"])
    coverage = assess_article_coverage(grouped["objectives"])
    policy = validate_campaign_policy(spec.get("policy", {}))

    findings = []
    if coverage["missing_items"]:
        findings.append(
            "the cycled article does not carry %d declared item(s): %s"
            % (len(coverage["missing_items"]), ", ".join(coverage["missing_items"]))
        )

    if not grouped["vacuum_environment_required"]:
        return {
            "objectives": grouped["objectives"],
            "categories": grouped["categories"],
            "vacuum_specific_items": [],
            "coverage": coverage,
            "bounds": None,
            "findings": findings,
            "verdict": VERDICT_NOT_REQUIRED,
            "purpose_served": False,
        }

    planned = spec.get("planned_run")
    if planned is None:
        return {
            "objectives": grouped["objectives"],
            "categories": grouped["categories"],
            "vacuum_specific_items": grouped["vacuum_specific_items"],
            "coverage": coverage,
            "bounds": None,
            "findings": findings,
            "verdict": VERDICT_NOT_PLANNED,
            "purpose_served": False,
        }
    if "predicted_environment" not in spec:
        raise ValueError(
            "spec carries a planned_run but no predicted_environment to bound"
        )
    bounds = evaluate_environment_bounds(
        planned, spec["predicted_environment"], policy
    )
    findings.extend(bounds["shortfalls"])
    served = bounds["bounds_environment"] and coverage["complete"]
    return {
        "objectives": grouped["objectives"],
        "categories": grouped["categories"],
        "vacuum_specific_items": grouped["vacuum_specific_items"],
        "coverage": coverage,
        "bounds": bounds,
        "findings": findings,
        "verdict": VERDICT_BOUNDING if served else VERDICT_UNDER_BOUNDS,
        "purpose_served": served,
    }
