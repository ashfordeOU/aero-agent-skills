#!/usr/bin/env python3
"""Single-carrier design-analysis-level selection -- ECSS-E-ST-20-01C 4.6.2.1.

Deterministic, offline, standard-library-only implementation of the route
decision of the clause:

* categorize the gap geometry and decide whether it reduces to a
  chart-representable equivalent parallel-plate configuration;
* form the frequency-gap-product and check it against the charted band of the
  electrode material;
* check the separation against the operating wavelength so the quasi-static
  basis of the susceptibility curves holds;
* admit the simplified level-one route only when every applicability gate
  holds, otherwise route the case to the detailed level-two
  numerical-modelling path;
* check the level-two prerequisites (validated solver, traceable
  secondary-electron-yield data, electron-seeding model, convergence
  evidence) and report every missing one.

Tables below are project defaults that a programme replaces with its declared
chart coverage; nothing in the module hard-codes an admissibility.

The clause is cited as the anchor only; no standard text is reproduced.
"""

import math

#: Speed of light in vacuum, metre per second.
SPEED_OF_LIGHT_M_S = 299792458.0

LEVEL_ONE = "level-one"
LEVEL_TWO = "level-two"
ANALYSIS_LEVELS = (LEVEL_ONE, LEVEL_TWO)

#: Gap geometry families and whether each reduces to a chart-representable
#: equivalent parallel-plate configuration.
GEOMETRY_FAMILIES = {
    "parallel-plate": {"chart_representable": True, "reduction": "direct"},
    "coaxial-line": {"chart_representable": True, "reduction": "inner-to-outer-gap"},
    "waveguide-iris": {
        "chart_representable": True,
        "reduction": "equivalent-parallel-plate",
    },
    "stepped-waveguide-junction": {
        "chart_representable": True,
        "reduction": "equivalent-parallel-plate",
    },
    "microstrip-gap": {"chart_representable": False, "reduction": "none"},
    "dielectric-loaded-gap": {"chart_representable": False, "reduction": "none"},
    "arbitrary-three-dimensional": {"chart_representable": False, "reduction": "none"},
}

#: Charted frequency-gap-product coverage per electrode surface, in
#: gigahertz-millimetre.
CHART_BANDS_GHZ_MM = {
    "silver": (0.1, 100.0),
    "copper": (0.1, 100.0),
    "aluminium": (0.1, 100.0),
    "gold": (0.2, 50.0),
    "silver-plated-aluminium": (0.1, 60.0),
    "alodine-treated-aluminium": (0.3, 30.0),
    "titanium": (0.5, 20.0),
}

#: Level-one holds only while the separation stays electrically small: the
#: declared limit is a quarter of the operating wavelength, beyond which the
#: field seen during the electron transit is no longer treated as uniform.
QUASI_STATIC_GAP_TO_WAVELENGTH_LIMIT = 0.25

#: Largest admissible ratio of maximum to minimum separation for an
#: equivalent parallel-plate reduction.
GAP_UNIFORMITY_LIMIT = 1.10

#: Evidence a level-two case carries before the modelling starts.
LEVEL_TWO_PREREQUISITES = (
    "validated-electromagnetic-field-solver",
    "traceable-secondary-electron-yield-data",
    "electron-seeding-model",
    "convergence-evidence",
)

#: Relative tolerance for band and ratio comparisons. Both sides are derived
#: quantities, so an exactly-met limit can land a few units in the last place
#: outside; the tolerance absorbs that without moving the limit itself.
COMPARISON_TOLERANCE_REL = 1e-12


def _require_positive(name, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return value


def _at_or_below(value, limit):
    """value <= limit, absorbing representation error at the limit."""
    if math.isclose(value, limit, rel_tol=COMPARISON_TOLERANCE_REL):
        return True
    return value < limit


def _at_or_above(value, limit):
    """value >= limit, absorbing representation error at the limit."""
    if math.isclose(value, limit, rel_tol=COMPARISON_TOLERANCE_REL):
        return True
    return value > limit


def normalize_geometry_family(family):
    """Resolve a geometry family name and return its reduction record."""
    if not isinstance(family, str):
        raise ValueError("geometry family must be a string, got %r" % (family,))
    key = family.strip().lower()
    if key not in GEOMETRY_FAMILIES:
        raise ValueError(
            "unrecognized geometry family %r; expected one of %s"
            % (family, ", ".join(sorted(GEOMETRY_FAMILIES)))
        )
    record = dict(GEOMETRY_FAMILIES[key])
    record["family"] = key
    return record


def frequency_gap_product_ghz_mm(frequency_hz, gap_m):
    """Similarity parameter of the gap, in gigahertz-millimetre."""
    frequency_hz = _require_positive("frequency_hz", frequency_hz)
    gap_m = _require_positive("gap_m", gap_m)
    return (frequency_hz / 1.0e9) * (gap_m * 1000.0)


def chart_band_for_material(material, chart_bands=None):
    """Charted frequency-gap-product band of an electrode surface."""
    if not isinstance(material, str):
        raise ValueError("material must be a string, got %r" % (material,))
    table = CHART_BANDS_GHZ_MM if chart_bands is None else chart_bands
    key = material.strip().lower()
    if key not in table:
        raise ValueError(
            "no charted band on record for surface %r; an uncharted surface "
            "is a level-two case, not a nearest-neighbour substitution"
            % (material,)
        )
    low, high = table[key]
    low = _require_positive("band lower edge", low)
    high = _require_positive("band upper edge", high)
    if high <= low:
        raise ValueError(
            "charted band for %r is inverted or empty: (%r, %r)" % (material, low, high)
        )
    return (low, high)


def is_within_chart_band(product_ghz_mm, band):
    """True when the frequency-gap-product sits inside the charted band."""
    product_ghz_mm = _require_positive("product_ghz_mm", product_ghz_mm)
    low, high = band
    return _at_or_above(product_ghz_mm, low) and _at_or_below(product_ghz_mm, high)


def gap_to_wavelength_ratio(frequency_hz, gap_m):
    """Electrode separation expressed as a fraction of the wavelength."""
    frequency_hz = _require_positive("frequency_hz", frequency_hz)
    gap_m = _require_positive("gap_m", gap_m)
    wavelength_m = SPEED_OF_LIGHT_M_S / frequency_hz
    return gap_m / wavelength_m


def is_quasi_static(frequency_hz, gap_m, limit=QUASI_STATIC_GAP_TO_WAVELENGTH_LIMIT):
    """True when the gap is electrically small enough for the chart basis."""
    limit = _require_positive("limit", limit)
    return _at_or_below(gap_to_wavelength_ratio(frequency_hz, gap_m), limit)


def gap_uniformity_ratio(case):
    """Ratio of maximum to minimum separation; 1.0 when a single gap is given."""
    if "gap_max_m" not in case and "gap_min_m" not in case:
        return 1.0
    gap_max = _require_positive("gap_max_m", case.get("gap_max_m"))
    gap_min = _require_positive("gap_min_m", case.get("gap_min_m"))
    if gap_max < gap_min:
        raise ValueError(
            "gap_max_m (%r) is below gap_min_m (%r)" % (gap_max, gap_min)
        )
    return gap_max / gap_min


def level_one_eligibility(case, chart_bands=None):
    """Apply every level-one applicability gate to one gap case.

    Returns a record carrying the frequency-gap-product, the charted band when
    resolvable, the gap-to-wavelength ratio, the separation uniformity and the
    list of blockers. An empty blocker list means the chart route is
    admissible. Raises ValueError for a multi-carrier case or invalid input.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    carrier_count = case.get("carrier_count", 1)
    if not isinstance(carrier_count, int) or isinstance(carrier_count, bool):
        raise ValueError("carrier_count must be an integer, got %r" % (carrier_count,))
    if carrier_count < 1:
        raise ValueError("carrier_count must be at least 1, got %r" % (carrier_count,))
    if carrier_count > 1:
        raise ValueError(
            "clause 4.6.2.1 covers single-carrier operation; %d carriers "
            "declared, route the case to the multi-carrier clause"
            % carrier_count
        )

    geometry = normalize_geometry_family(case.get("geometry_family"))
    frequency_hz = _require_positive("frequency_hz", case.get("frequency_hz"))
    gap_m = _require_positive("gap_m", case.get("gap_m"))

    blockers = []
    if not geometry["chart_representable"]:
        blockers.append(
            "geometry family %r does not reduce to a chart-representable "
            "equivalent parallel-plate gap" % geometry["family"]
        )

    uniformity = gap_uniformity_ratio(case)
    if not _at_or_below(uniformity, GAP_UNIFORMITY_LIMIT):
        blockers.append(
            "separation uniformity ratio %.3f exceeds the equivalent "
            "parallel-plate limit %.3f" % (uniformity, GAP_UNIFORMITY_LIMIT)
        )

    product = frequency_gap_product_ghz_mm(frequency_hz, gap_m)
    band = None
    try:
        band = chart_band_for_material(case.get("electrode_material"), chart_bands)
    except ValueError as exc:
        blockers.append(str(exc))
    if band is not None and not is_within_chart_band(product, band):
        blockers.append(
            "frequency-gap-product %.4f gigahertz-millimetre falls outside "
            "the charted band %.4f to %.4f" % (product, band[0], band[1])
        )

    ratio = gap_to_wavelength_ratio(frequency_hz, gap_m)
    if not is_quasi_static(frequency_hz, gap_m):
        blockers.append(
            "separation is %.4f of a wavelength, above the quasi-static "
            "limit %.4f" % (ratio, QUASI_STATIC_GAP_TO_WAVELENGTH_LIMIT)
        )

    if case.get("dielectric_in_gap", False):
        blockers.append(
            "a dielectric filling the gap sits outside the chart basis"
        )
    if case.get("static_magnetic_field", False):
        blockers.append(
            "a static magnetic field across the gap sits outside the chart basis"
        )

    return {
        "frequency_gap_product_ghz_mm": product,
        "chart_band_ghz_mm": band,
        "gap_to_wavelength_ratio": ratio,
        "gap_uniformity_ratio": uniformity,
        "geometry_family": geometry["family"],
        "geometry_reduction": geometry["reduction"],
        "blockers": blockers,
        "eligible": not blockers,
    }


def missing_level_two_prerequisites(case):
    """Prerequisites a level-two case has not yet put on record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    declared = case.get("level_two_evidence", [])
    if not isinstance(declared, (list, tuple, set)):
        raise ValueError(
            "level_two_evidence must be a list of prerequisite names, got %r"
            % (declared,)
        )
    unknown = [item for item in declared if item not in LEVEL_TWO_PREREQUISITES]
    if unknown:
        raise ValueError(
            "unrecognized level-two evidence item(s): %s" % ", ".join(sorted(unknown))
        )
    return [item for item in LEVEL_TWO_PREREQUISITES if item not in declared]


def select_design_analysis_level(case, chart_bands=None):
    """Choose the route for one gap case and explain the choice."""
    requested = case.get("requested_level")
    if requested is not None and requested not in ANALYSIS_LEVELS:
        raise ValueError(
            "requested_level must be one of %s, got %r"
            % (", ".join(ANALYSIS_LEVELS), requested)
        )
    eligibility = level_one_eligibility(case, chart_bands)
    rationale = []
    request_rejected = False

    if requested == LEVEL_TWO:
        selected = LEVEL_TWO
        rationale.append("detailed route requested; level two is always admissible")
    elif eligibility["eligible"]:
        selected = LEVEL_ONE
        rationale.append(
            "every level-one applicability gate holds; the chart route is "
            "admissible"
        )
    else:
        selected = LEVEL_TWO
        if requested == LEVEL_ONE:
            request_rejected = True
            rationale.append(
                "level one was requested but the case fails an applicability "
                "gate; re-routed to level two"
            )
        else:
            rationale.append(
                "at least one level-one applicability gate fails; the case "
                "carries to level two"
            )
        rationale.extend(eligibility["blockers"])

    return {
        "selected_level": selected,
        "requested_level": requested,
        "requested_level_rejected": request_rejected,
        "level_one_eligible": eligibility["eligible"],
        "rationale": rationale,
        "eligibility": eligibility,
    }


def assess_analysis_level_selection(case, chart_bands=None):
    """Full route record for one gap, including level-two readiness."""
    selection = select_design_analysis_level(case, chart_bands)
    missing = []
    if selection["selected_level"] == LEVEL_TWO:
        missing = missing_level_two_prerequisites(case)
    findings = list(selection["rationale"]) if selection["requested_level_rejected"] else []
    for item in missing:
        findings.append("level-two prerequisite not on record: %s" % item)
    return {
        "identifier": case.get("identifier", "unnamed-gap"),
        "selected_level": selection["selected_level"],
        "level_one_eligible": selection["level_one_eligible"],
        "requested_level_rejected": selection["requested_level_rejected"],
        "blockers": selection["eligibility"]["blockers"],
        "missing_prerequisites": missing,
        "frequency_gap_product_ghz_mm": selection["eligibility"][
            "frequency_gap_product_ghz_mm"
        ],
        "gap_to_wavelength_ratio": selection["eligibility"]["gap_to_wavelength_ratio"],
        "ready_to_analyse": not missing,
        "findings": findings,
    }


def summarize_level_selection(cases, chart_bands=None):
    """Roll a unit's gaps up into one route-decision record."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty list of mappings")
    records = [assess_analysis_level_selection(c, chart_bands) for c in cases]
    level_one = [r["identifier"] for r in records if r["selected_level"] == LEVEL_ONE]
    level_two = [r["identifier"] for r in records if r["selected_level"] == LEVEL_TWO]
    blocked = [r["identifier"] for r in records if not r["ready_to_analyse"]]
    return {
        "gap_count": len(records),
        "level_one_gaps": level_one,
        "level_two_gaps": level_two,
        "gaps_not_ready": blocked,
        "unit_ready": not blocked,
        "records": records,
    }
