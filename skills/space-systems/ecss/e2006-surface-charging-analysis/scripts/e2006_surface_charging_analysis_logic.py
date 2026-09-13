#!/usr/bin/env python3
"""Spacecraft-wide surface-potential analysis of external materials.

Anchor: ECSS-E-ST-20-06C clause 6.4 (paraphrased into an implementable
procedure; no verbatim standard text).

The clause asks for two linked products: an inventory of every external
material exposed to the ambient plasma, and an analysis of the potentials
that inventory produces across the vehicle.  This module implements that
pair offline and deterministically with the standard library only:

1. normalise and validate each inventory item;
2. categorize each item as charge-dissipating or charge-storing from its
   surface resistivity and its grounding path;
3. check the inventoried area against the declared external area so no
   exposed item escapes the assessment;
4. evaluate the secondary-emission and backscatter yield at the
   worst-case plasma temperature;
5. solve each item's equilibrium potential for its illumination state;
6. derive the vehicle frame potential from the grounded dissipative
   items and compare every differential offset against its limit.
"""

import math

# --- registry of external material kinds -------------------------------
# delta_max      : peak secondary-electron yield (dimensionless)
# e_max_ev       : impact energy of that peak, electronvolt
# backscatter    : backscattered-electron fraction (dimensionless)
# photo_a_m2     : photoelectron current density at 1 AU, ampere/metre^2
MATERIAL_KINDS = {
    "kapton-thermal-blanket": {
        "delta_max": 2.10, "e_max_ev": 150.0,
        "backscatter": 0.25, "photo_a_m2": 2.0e-5,
    },
    "optical-solar-reflector": {
        "delta_max": 2.40, "e_max_ev": 400.0,
        "backscatter": 0.30, "photo_a_m2": 2.0e-5,
    },
    "solar-cell-coverglass": {
        "delta_max": 2.40, "e_max_ev": 300.0,
        "backscatter": 0.28, "photo_a_m2": 2.0e-5,
    },
    "conductive-black-paint": {
        "delta_max": 1.50, "e_max_ev": 300.0,
        "backscatter": 0.20, "photo_a_m2": 2.0e-5,
    },
    "indium-tin-oxide-coating": {
        "delta_max": 1.40, "e_max_ev": 300.0,
        "backscatter": 0.22, "photo_a_m2": 2.0e-5,
    },
    "bare-aluminium": {
        "delta_max": 0.97, "e_max_ev": 300.0,
        "backscatter": 0.19, "photo_a_m2": 2.9e-5,
    },
}

ILLUMINATION_STATES = ("sunlit", "eclipsed")

# A surface drains to structure when it is bonded AND its sheet
# resistivity sits at or below this value; above it the item stores
# charge for longer than a substorm and is treated as a dielectric.
DISSIPATIVE_RESISTIVITY_LIMIT_OHM_SQ = 1.0e9

DEFAULT_DIFFERENTIAL_LIMIT_V = 500.0
SUNLIT_PINNED_POTENTIAL_V = 3.0
CHARGING_COEFFICIENT = 1.0

# Relative tolerance that absorbs floating-point representation error in
# limit and area comparisons.  It never widens an engineering limit: a
# value one part in 1e-9 above a limit is the same physical value.
LIMIT_REL_TOL = 1e-9

POTENTIAL_BANDS = (
    ("benign", 100.0),
    ("moderate", 1000.0),
    ("severe", None),
)


def _number(value, label, minimum=None, strict=True):
    """Return value as float, or raise ValueError with a named reason."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if strict and out <= minimum:
            raise ValueError("%s must be > %g, got %g" % (label, minimum, out))
        if not strict and out < minimum:
            raise ValueError("%s must be >= %g, got %g" % (label, minimum, out))
    return out


def _at_or_below(value, limit):
    """True when value <= limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def normalize_material_item(item):
    """Validate one external-material inventory row and fill defaults."""
    if not isinstance(item, dict):
        raise ValueError("inventory item must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("inventory item needs a non-empty string id")
    material = item.get("material")
    if material not in MATERIAL_KINDS:
        raise ValueError(
            "item %s: unknown external material %r (known: %s)"
            % (item_id, material, ", ".join(sorted(MATERIAL_KINDS)))
        )
    illumination = item.get("illumination")
    if illumination not in ILLUMINATION_STATES:
        raise ValueError(
            "item %s: illumination must be one of %s, got %r"
            % (item_id, ", ".join(ILLUMINATION_STATES), illumination)
        )
    grounded = item.get("grounded")
    if not isinstance(grounded, bool):
        raise ValueError("item %s: grounded must be a boolean" % item_id)
    area = _number(item.get("area_m2"), "item %s: area_m2" % item_id, 0.0)
    resistivity = _number(
        item.get("surface_resistivity_ohm_sq"),
        "item %s: surface_resistivity_ohm_sq" % item_id,
        0.0,
    )
    limit = item.get("differential_limit_v", DEFAULT_DIFFERENTIAL_LIMIT_V)
    limit = _number(limit, "item %s: differential_limit_v" % item_id, 0.0)
    row = dict(MATERIAL_KINDS[material])
    row.update(
        {
            "id": item_id,
            "material": material,
            "illumination": illumination,
            "grounded": grounded,
            "area_m2": area,
            "surface_resistivity_ohm_sq": resistivity,
            "differential_limit_v": limit,
        }
    )
    return row


def build_external_material_inventory(items):
    """Normalise every row; reject an empty inventory or a duplicate id."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("external-material inventory must be a non-empty list")
    inventory = []
    seen = set()
    for item in items:
        row = normalize_material_item(item)
        if row["id"] in seen:
            raise ValueError("duplicate inventory id %r" % row["id"])
        seen.add(row["id"])
        inventory.append(row)
    return inventory


def categorize_conduction_path(row):
    """Return charge-dissipating or charge-storing for one inventory row."""
    if "grounded" not in row or "surface_resistivity_ohm_sq" not in row:
        raise ValueError("row is not a normalised inventory item")
    if not row["grounded"]:
        return "charge-storing"
    if _at_or_below(
        row["surface_resistivity_ohm_sq"], DISSIPATIVE_RESISTIVITY_LIMIT_OHM_SQ
    ):
        return "charge-dissipating"
    return "charge-storing"


def inventory_area_coverage(inventory, declared_external_area_m2):
    """Compare the inventoried area with the declared external area."""
    declared = _number(
        declared_external_area_m2, "declared_external_area_m2", 0.0
    )
    inventoried = math.fsum(row["area_m2"] for row in inventory)
    complete = inventoried >= declared or math.isclose(
        inventoried, declared, rel_tol=LIMIT_REL_TOL
    )
    overrun = inventoried > declared and not math.isclose(
        inventoried, declared, rel_tol=LIMIT_REL_TOL
    )
    return {
        "inventoried_area_m2": inventoried,
        "declared_area_m2": declared,
        "covered_fraction": inventoried / declared,
        "complete": complete,
        "overrun": overrun,
    }


def emission_yield(row, electron_temperature_ev):
    """Total emitted-electron fraction (secondary + backscattered).

    Secondary yield uses the standard peaked fit: it rises with impact
    energy, reaches delta_max at e_max_ev, then falls as deeper
    penetration traps the secondaries.
    """
    energy = _number(electron_temperature_ev, "electron_temperature_ev", 0.0)
    e_max = _number(row.get("e_max_ev"), "e_max_ev", 0.0)
    delta_max = _number(row.get("delta_max"), "delta_max", 0.0, strict=False)
    backscatter = _number(
        row.get("backscatter"), "backscatter", 0.0, strict=False
    )
    x = energy / e_max
    secondary = delta_max * 1.114 * (x ** -0.35) * (1.0 - math.exp(-2.28 * (x ** 1.35)))
    return secondary + backscatter


def normalize_environment(environment):
    """Validate the worst-case plasma environment used by the analysis."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping, got %r" % (environment,))
    temperature = _number(
        environment.get("electron_temperature_ev"),
        "environment electron_temperature_ev",
        0.0,
    )
    ambient = _number(
        environment.get("ambient_electron_current_density_a_m2"),
        "environment ambient_electron_current_density_a_m2",
        0.0,
    )
    scale = environment.get("photoemission_scale", 1.0)
    scale = _number(scale, "environment photoemission_scale", 0.0, strict=False)
    return {
        "electron_temperature_ev": temperature,
        "ambient_electron_current_density_a_m2": ambient,
        "photoemission_scale": scale,
    }


def equilibrium_surface_potential(row, environment):
    """Equilibrium potential of one exposed item, in volts.

    The net collected-electron fraction is 1 - (secondary + backscatter).
    An item whose emission already exceeds unity cannot charge negative;
    in sunlight the photoelectron term pins it a few volts positive.
    """
    env = normalize_environment(environment)
    temperature = env["electron_temperature_ev"]
    ambient = env["ambient_electron_current_density_a_m2"]
    net_fraction = 1.0 - emission_yield(row, temperature)
    if net_fraction <= 0.0 or math.isclose(net_fraction, 0.0, abs_tol=1e-15):
        return SUNLIT_PINNED_POTENTIAL_V if row["illumination"] == "sunlit" else 0.0
    driver = ambient * net_fraction
    if row["illumination"] == "sunlit":
        photo = row["photo_a_m2"] * env["photoemission_scale"]
        driver -= photo
        if driver <= 0.0 or math.isclose(driver, 0.0, abs_tol=1e-18):
            return SUNLIT_PINNED_POTENTIAL_V
    return -CHARGING_COEFFICIENT * temperature * (driver / ambient)


def categorize_potential_band(potential_v):
    """Band the magnitude of a potential as benign, moderate or severe."""
    magnitude = abs(_number(potential_v, "potential_v"))
    for name, ceiling in POTENTIAL_BANDS:
        if ceiling is None or _at_or_below(magnitude, ceiling):
            return name
    return "severe"


def frame_potential(inventory, environment):
    """Area-weighted potential of the grounded dissipative surfaces."""
    env = normalize_environment(environment)
    weighted = []
    area = 0.0
    for row in inventory:
        if categorize_conduction_path(row) != "charge-dissipating":
            continue
        area += row["area_m2"]
        weighted.append(row["area_m2"] * equilibrium_surface_potential(row, env))
    if area <= 0.0:
        raise ValueError(
            "no grounded charge-dissipating surface in the inventory: the "
            "vehicle frame potential is undefined"
        )
    return math.fsum(weighted) / area


def surface_potential_rows(inventory, environment):
    """Per-item potential, band, conduction path and differential offset.

    A bonded charge-dissipating item shares the conductor, so it sits at
    the frame potential and carries no offset of its own.  A
    charge-storing item floats to its isolated equilibrium potential and
    the difference against the frame is its differential-charging offset.
    """
    env = normalize_environment(environment)
    reference = frame_potential(inventory, env)
    rows = []
    for row in inventory:
        path = categorize_conduction_path(row)
        isolated = equilibrium_surface_potential(row, env)
        if path == "charge-dissipating":
            potential = reference
            offset = 0.0
        else:
            potential = isolated
            offset = isolated - reference
        rows.append(
            {
                "id": row["id"],
                "material": row["material"],
                "illumination": row["illumination"],
                "conduction_path": path,
                "area_m2": row["area_m2"],
                "isolated_potential_v": isolated,
                "surface_potential_v": potential,
                "frame_potential_v": reference,
                "differential_offset_v": offset,
                "potential_band": categorize_potential_band(potential),
                "differential_limit_v": row["differential_limit_v"],
            }
        )
    return rows


def assess_surface_potentials(rows, limits=None):
    """Findings against the differential and optional absolute limits."""
    limits = dict(limits or {})
    absolute_limit = limits.get("absolute_limit_v")
    if absolute_limit is not None:
        absolute_limit = _number(absolute_limit, "absolute_limit_v", 0.0)
    findings = []
    for row in rows:
        magnitude = abs(row["differential_offset_v"])
        if not _at_or_below(magnitude, row["differential_limit_v"]):
            findings.append(
                {
                    "kind": "differential-offset-exceedance",
                    "id": row["id"],
                    "value_v": magnitude,
                    "limit_v": row["differential_limit_v"],
                }
            )
        if absolute_limit is not None and not _at_or_below(
            abs(row["surface_potential_v"]), absolute_limit
        ):
            findings.append(
                {
                    "kind": "absolute-potential-exceedance",
                    "id": row["id"],
                    "value_v": abs(row["surface_potential_v"]),
                    "limit_v": absolute_limit,
                }
            )
    return findings


def analyze_surface_charging(items, declared_external_area_m2, environment,
                             limits=None):
    """Full clause 6.4 product: inventory, coverage, potentials, findings."""
    inventory = build_external_material_inventory(items)
    coverage = inventory_area_coverage(inventory, declared_external_area_m2)
    rows = surface_potential_rows(inventory, environment)
    findings = assess_surface_potentials(rows, limits)
    if not coverage["complete"]:
        findings.insert(
            0,
            {
                "kind": "inventory-coverage-gap",
                "id": "*inventory*",
                "value_v": coverage["covered_fraction"],
                "limit_v": 1.0,
            },
        )
    if coverage["overrun"]:
        findings.append(
            {
                "kind": "inventory-area-overrun",
                "id": "*inventory*",
                "value_v": coverage["inventoried_area_m2"],
                "limit_v": coverage["declared_area_m2"],
            }
        )
    return {
        "item_count": len(inventory),
        "coverage": coverage,
        "frame_potential_v": rows[0]["frame_potential_v"],
        "surfaces": rows,
        "findings": findings,
        "compliant": not findings,
    }


def summarize_findings(report):
    """Count findings by kind for the analysis summary table."""
    if not isinstance(report, dict) or "findings" not in report:
        raise ValueError("report must be the mapping returned by analyze_surface_charging")
    counts = {}
    for finding in report["findings"]:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1
    return counts
