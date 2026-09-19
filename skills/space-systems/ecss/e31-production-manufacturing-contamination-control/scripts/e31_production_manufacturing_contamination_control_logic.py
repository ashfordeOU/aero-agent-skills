"""Production, manufacturing and contamination control for thermal hardware.

Anchor: ECSS-E-ST-31C clause 4.6 (procurement, manufacturing, cleanliness and
contamination control of thermal surfaces, integration, marking, the declared
heat-treatment operation (PHT), storage and repair). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn a contamination allocation into thermo-optical numbers. Deposited
   molecular film and particulate obscuration both raise the solar
   absorptance of a radiator, MLI outer layer or optical surface, and the
   molecular film also depresses the infrared emittance.
2. Turn those numbers into the quantity a thermal engineer acts on: the
   radiator area needed to reject the same heat at end of life, and the area
   growth over the beginning-of-life design.
3. Roll the per-stage contamination allocations (manufacture, integration,
   storage, transport, launch, on-orbit) up against the end-of-life budget,
   so an overspend is attributed to the stage that caused it.
4. Grade the production control set declared for each stage against the
   controls that stage owes, and raise the specific traps: marking placed
   inside an optically active area, a heat-treatment operation with no
   recorded profile, storage beyond shelf life, and a repair closed without
   re-verification.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN",
    "OPTICAL_TOLERANCE",
    "AREA_TOLERANCE_M2",
    "SURFACE_TYPES",
    "REQUIRED_CONTROLS",
    "validate_fraction",
    "validate_positive",
    "validate_surface_type",
    "contaminated_absorptance",
    "contaminated_emittance",
    "net_rejection_w_m2",
    "radiator_area_m2",
    "area_growth_ratio",
    "allocation_rollup",
    "stage_control_findings",
    "marking_findings",
    "storage_findings",
    "repair_findings",
    "evaluate_surface",
    "assess_production_controls",
]

STEFAN_BOLTZMANN = 5.670374419e-8

# Optical properties and areas are sums and quotients of floats. A value that
# should sit exactly on its limit can land a few ULPs either side, so absorb
# the representation error here instead of loosening the engineering limit.
OPTICAL_TOLERANCE = 1e-12
AREA_TOLERANCE_M2 = 1e-9

SURFACE_TYPES = ("radiator", "mli", "optical")

# The controls each production stage owes before the hardware may move on.
REQUIRED_CONTROLS = {
    "procurement": ("approved-supplier", "lot-traceability"),
    "manufacturing": ("process-specification", "operator-qualification"),
    "cleanliness": ("cleanroom-class", "handling-procedure"),
    "integration": ("protective-cover", "witness-sample"),
    "marking": ("item-identification", "marking-location-record"),
    "heat-treatment": ("recorded-profile", "post-treatment-inspection"),
    "storage": ("controlled-environment", "shelf-life-record"),
    "repair": ("approved-repair-procedure", "post-repair-reverification"),
}


def validate_fraction(value, label, allow_one=True):
    """Return a validated dimensionless fraction in [0, 1]."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    upper = 1.0 if allow_one else 1.0 - OPTICAL_TOLERANCE
    if number > upper + OPTICAL_TOLERANCE:
        raise ValueError("%s must not exceed unity, got %r" % (label, value))
    return number


def validate_positive(value, label, allow_zero=False):
    """Return a validated positive (optionally non-negative) real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_surface_type(surface_type):
    """Return a validated thermal surface type name."""
    if not isinstance(surface_type, str):
        raise ValueError("surface type must be a string")
    name = surface_type.strip().lower()
    if name not in SURFACE_TYPES:
        raise ValueError("unknown surface type %r; expected one of %s"
                         % (surface_type, SURFACE_TYPES))
    return name


def contaminated_absorptance(alpha_bol, molecular_mg_per_m2, obscuration_fraction,
                             k_molecular, k_particulate):
    """Return the solar absorptance after molecular and particulate deposition."""
    alpha = validate_fraction(alpha_bol, "alpha_bol")
    molecular = validate_positive(molecular_mg_per_m2, "molecular_mg_per_m2", allow_zero=True)
    obscuration = validate_fraction(obscuration_fraction, "obscuration_fraction")
    k_mol = validate_positive(k_molecular, "k_molecular", allow_zero=True)
    k_part = validate_positive(k_particulate, "k_particulate", allow_zero=True)
    result = alpha + k_mol * molecular + k_part * obscuration
    if result > 1.0:
        return 1.0
    return result


def contaminated_emittance(emittance_bol, molecular_mg_per_m2, k_molecular_emittance):
    """Return the infrared emittance after molecular deposition depresses it."""
    emittance = validate_fraction(emittance_bol, "emittance_bol")
    if emittance <= 0.0:
        raise ValueError("emittance_bol must be positive; a zero-emittance radiator rejects nothing")
    molecular = validate_positive(molecular_mg_per_m2, "molecular_mg_per_m2", allow_zero=True)
    coefficient = validate_positive(k_molecular_emittance, "k_molecular_emittance",
                                    allow_zero=True)
    result = emittance - coefficient * molecular
    if result <= 0.0:
        raise ValueError(
            "molecular deposition of %g mg/m2 drives emittance to %g; the surface no longer "
            "radiates and the allocation must be reworked" % (molecular, result)
        )
    return result


def net_rejection_w_m2(emittance, absorptance, radiator_temperature_k, sink_temperature_k,
                       solar_flux_w_m2, view_factor):
    """Return the net heat a unit radiator area rejects under a solar load."""
    eps = validate_fraction(emittance, "emittance")
    alpha = validate_fraction(absorptance, "absorptance")
    t_rad = validate_positive(radiator_temperature_k, "radiator_temperature_k")
    t_sink = validate_positive(sink_temperature_k, "sink_temperature_k", allow_zero=True)
    flux = validate_positive(solar_flux_w_m2, "solar_flux_w_m2", allow_zero=True)
    factor = validate_fraction(view_factor, "view_factor")
    if t_sink >= t_rad:
        raise ValueError(
            "sink temperature %g K is not below the radiator temperature %g K; there is no "
            "rejection to compute" % (t_sink, t_rad)
        )
    radiated = eps * STEFAN_BOLTZMANN * (
        t_rad * t_rad * t_rad * t_rad - t_sink * t_sink * t_sink * t_sink
    )
    absorbed = alpha * flux * factor
    return radiated - absorbed


def radiator_area_m2(heat_w, emittance, absorptance, radiator_temperature_k,
                     sink_temperature_k, solar_flux_w_m2, view_factor):
    """Return the radiator area needed to reject a heat load at the stated properties."""
    heat = validate_positive(heat_w, "heat_w")
    per_area = net_rejection_w_m2(
        emittance, absorptance, radiator_temperature_k, sink_temperature_k,
        solar_flux_w_m2, view_factor,
    )
    if per_area <= 0.0:
        raise ValueError(
            "net rejection is %g W/m2; the absorbed solar load equals or exceeds what the "
            "surface radiates, so no finite area rejects the heat" % per_area
        )
    return heat / per_area


def area_growth_ratio(area_eol_m2, area_bol_m2):
    """Return the end-of-life radiator area as a ratio of the beginning-of-life area."""
    eol = validate_positive(area_eol_m2, "area_eol_m2")
    bol = validate_positive(area_bol_m2, "area_bol_m2")
    return eol / bol


def allocation_rollup(stage_allocations, end_of_life_budget):
    """Sum the per-stage contamination allocations and grade them against the budget."""
    if not isinstance(stage_allocations, dict) or not stage_allocations:
        raise ValueError("stage_allocations must be a non-empty mapping of stage to amount")
    budget = validate_positive(end_of_life_budget, "end_of_life_budget")
    contributions = {}
    total = 0.0
    for stage, amount in stage_allocations.items():
        if not isinstance(stage, str) or not stage.strip():
            raise ValueError("every allocation stage needs a non-empty name")
        key = stage.strip().lower()
        if key in contributions:
            raise ValueError("duplicate allocation stage %r" % stage)
        value = validate_positive(amount, "allocation for %r" % stage, allow_zero=True)
        contributions[key] = value
        total += value
    within = total < budget or math.isclose(total, budget, rel_tol=0.0, abs_tol=OPTICAL_TOLERANCE)
    dominant = max(contributions.items(), key=lambda item: (item[1], item[0]))[0]
    return {
        "contributions": contributions,
        "total": total,
        "budget": budget,
        "within_budget": within,
        "dominant_stage": dominant,
        "unallocated": budget - total,
    }


def stage_control_findings(stage, declared_controls):
    """Return the controls a production stage owes and did not declare."""
    if not isinstance(stage, str) or stage.strip().lower() not in REQUIRED_CONTROLS:
        raise ValueError("unknown production stage %r; expected one of %s"
                         % (stage, tuple(sorted(REQUIRED_CONTROLS))))
    key = stage.strip().lower()
    if not isinstance(declared_controls, (list, tuple, set, frozenset)):
        raise ValueError("declared controls must be a collection of control names")
    declared = set()
    for control in declared_controls:
        if not isinstance(control, str) or not control.strip():
            raise ValueError("control names must be non-empty strings")
        declared.add(control.strip().lower())
    return ["%s: %s not declared" % (key, control)
            for control in REQUIRED_CONTROLS[key] if control not in declared]


def marking_findings(surface_type, marking_inside_active_area, marking_outgassing_qualified):
    """Return the findings raised by how an item is marked on a thermal surface."""
    name = validate_surface_type(surface_type)
    findings = []
    if bool(marking_inside_active_area):
        findings.append(
            "marking sits inside the optically active area of the %s surface" % name
        )
    if not bool(marking_outgassing_qualified):
        findings.append(
            "marking medium on the %s surface has no outgassing qualification" % name
        )
    return findings


def storage_findings(days_in_storage, shelf_life_days, purge_maintained):
    """Return the findings raised by the storage record of a thermal item."""
    stored = validate_positive(days_in_storage, "days_in_storage", allow_zero=True)
    shelf = validate_positive(shelf_life_days, "shelf_life_days")
    findings = []
    overrun = stored - shelf
    if overrun > 0.0 and not math.isclose(overrun, 0.0, rel_tol=0.0, abs_tol=AREA_TOLERANCE_M2):
        findings.append("item stored %.1f days beyond its shelf life" % overrun)
    if not bool(purge_maintained):
        findings.append("controlled storage environment was not maintained")
    return findings


def repair_findings(repaired, procedure_approved, reverified):
    """Return the findings raised by a repair carried out on a thermal item."""
    if not bool(repaired):
        return []
    findings = []
    if not bool(procedure_approved):
        findings.append("repair carried out without an approved repair procedure")
    if not bool(reverified):
        findings.append("repair closed without thermo-optical re-verification")
    return findings


def evaluate_surface(item):
    """Evaluate one thermal surface through the clause 4.6 production controls."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    required_keys = (
        "id", "surface_type", "alpha_bol", "emittance_bol", "molecular_mg_per_m2",
        "obscuration_fraction", "k_molecular", "k_particulate", "k_molecular_emittance",
        "heat_w", "radiator_temperature_k", "sink_temperature_k", "solar_flux_w_m2",
        "view_factor", "stage_allocations", "end_of_life_budget", "stage_controls",
        "marking", "storage", "repair", "area_growth_limit",
    )
    for key in required_keys:
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    identifier = item["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("item id must be a non-empty string")
    identifier = identifier.strip()
    surface_type = validate_surface_type(item["surface_type"])

    alpha_eol = contaminated_absorptance(
        item["alpha_bol"], item["molecular_mg_per_m2"], item["obscuration_fraction"],
        item["k_molecular"], item["k_particulate"],
    )
    emittance_eol = contaminated_emittance(
        item["emittance_bol"], item["molecular_mg_per_m2"], item["k_molecular_emittance"]
    )
    area_bol = radiator_area_m2(
        item["heat_w"], item["emittance_bol"], item["alpha_bol"],
        item["radiator_temperature_k"], item["sink_temperature_k"],
        item["solar_flux_w_m2"], item["view_factor"],
    )
    area_eol = radiator_area_m2(
        item["heat_w"], emittance_eol, alpha_eol,
        item["radiator_temperature_k"], item["sink_temperature_k"],
        item["solar_flux_w_m2"], item["view_factor"],
    )
    growth = area_growth_ratio(area_eol, area_bol)
    limit = validate_positive(item["area_growth_limit"], "area_growth_limit")
    if limit < 1.0:
        raise ValueError("area_growth_limit must be at least 1.0, got %r" % (item["area_growth_limit"],))
    growth_ok = growth < limit or math.isclose(growth, limit, rel_tol=1e-12, abs_tol=0.0)

    allocations = allocation_rollup(item["stage_allocations"], item["end_of_life_budget"])

    findings = []
    controls = item["stage_controls"]
    if not isinstance(controls, dict) or not controls:
        raise ValueError("stage_controls must be a non-empty mapping of stage to controls")
    for stage in sorted(REQUIRED_CONTROLS):
        if stage not in controls:
            findings.append("%s: no production controls declared for this stage" % stage)
        else:
            findings.extend(stage_control_findings(stage, controls[stage]))

    marking = item["marking"]
    if not isinstance(marking, dict):
        raise ValueError("marking must be a mapping")
    findings.extend(marking_findings(
        surface_type,
        marking.get("inside_active_area", False),
        marking.get("outgassing_qualified", False),
    ))

    storage = item["storage"]
    if not isinstance(storage, dict):
        raise ValueError("storage must be a mapping")
    for key in ("days_in_storage", "shelf_life_days"):
        if key not in storage:
            raise ValueError("storage must carry '%s'" % key)
    findings.extend(storage_findings(
        storage["days_in_storage"], storage["shelf_life_days"],
        storage.get("purge_maintained", False),
    ))

    repair = item["repair"]
    if not isinstance(repair, dict):
        raise ValueError("repair must be a mapping")
    findings.extend(repair_findings(
        repair.get("repaired", False),
        repair.get("procedure_approved", False),
        repair.get("reverified", False),
    ))

    if not allocations["within_budget"]:
        findings.append(
            "contamination allocations total %.4f against a budget of %.4f, %s dominating"
            % (allocations["total"], allocations["budget"], allocations["dominant_stage"])
        )
    if not growth_ok:
        findings.append(
            "end-of-life radiator area grows by a factor %.4f against a limit of %.4f"
            % (growth, limit)
        )

    findings = ["%s: %s" % (identifier, text) for text in findings]
    return {
        "id": identifier,
        "surface_type": surface_type,
        "alpha_eol": alpha_eol,
        "emittance_eol": emittance_eol,
        "area_bol_m2": area_bol,
        "area_eol_m2": area_eol,
        "area_growth_ratio": growth,
        "area_growth_acceptable": growth_ok,
        "allocations": allocations,
        "controlled": not findings,
        "findings": findings,
    }


def assess_production_controls(spec):
    """Run the full clause 4.6 production and contamination control assessment.

    spec keys: items (sequence of thermal surface mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "items" not in spec:
        raise ValueError("spec missing required key 'items'")
    items = spec["items"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    records = []
    seen = set()
    for item in items:
        record = evaluate_surface(item)
        if record["id"] in seen:
            raise ValueError("duplicate thermal surface id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    controlled = [record["id"] for record in records if record["controlled"]]
    driving = max(records, key=lambda r: (r["area_growth_ratio"], r["id"]))["id"]
    return {
        "items": records,
        "controlled_items": controlled,
        "controlled_fraction": len(controlled) / float(len(records)),
        "driving_item": driving,
        "controlled": not findings,
        "findings": findings,
    }
