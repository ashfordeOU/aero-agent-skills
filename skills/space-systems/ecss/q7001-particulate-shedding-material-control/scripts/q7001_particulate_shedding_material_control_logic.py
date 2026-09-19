"""Control of particulate-shedding materials near a sensitive surface.

Anchor: ECSS-Q-ST-70-01C cleanliness and contamination control, the control it
imposes on materials that shed particulate -- paints, textiles, hook-and-loop
fastener, foams, tape edges -- when they are installed where the particulate
can reach a surface with a particulate cleanliness budget. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the shedding family of each installed source and the control that
   family carries by construction, refusing a family outside the recognised
   set rather than defaulting to the mildest one.
2. Normalise each source: exposed area, orientation relative to the surface,
   view factor, and whether the mandatory control for its family has been
   applied.
3. Capture factor: fallout reaches an upward-facing surface, largely misses a
   vertical one and barely touches a downward-facing one, scaled by the view
   factor between source and surface.
4. Contribution: the family shedding index, the applied-control credit, the
   source-to-surface area ratio, the capture factor and the exposure hours
   give the percent area coverage the source adds to the surface.
5. Sum the contributions, compare the total with the cleanliness budget the
   surface level allows, and report the control actions still owed.
"""

import math

__all__ = [
    "SHEDDING_FAMILIES",
    "ORIENTATION_CAPTURE",
    "CLEANLINESS_LEVELS",
    "CONTROL_CREDIT",
    "PAC_TOLERANCE_PCT",
    "normalise_identifier",
    "shedding_family",
    "mandatory_control",
    "capture_factor",
    "validate_source",
    "source_contribution_pct",
    "cleanliness_budget_pct",
    "control_findings",
    "aggregate_contributions",
    "assess_particulate_control",
]

# Shedding families, the percent area coverage each adds per 1000 hours at a
# unit source-to-surface area ratio and full capture, and the control the
# family carries by construction.
SHEDDING_FAMILIES = {
    "hook-and-loop-fastener": {"index_pac_per_1000h": 0.90,
                               "control": "enclose-or-move-out-of-line-of-sight"},
    "unsealed-paint": {"index_pac_per_1000h": 0.45,
                       "control": "seal-and-verify-adhesion"},
    "woven-textile": {"index_pac_per_1000h": 0.40,
                      "control": "bind-and-seal-cut-edges"},
    "multilayer-insulation-edge": {"index_pac_per_1000h": 0.30,
                                   "control": "bind-and-seal-cut-edges"},
    "open-cell-foam": {"index_pac_per_1000h": 0.35,
                       "control": "encapsulate-in-a-bagged-liner"},
    "tape-edge": {"index_pac_per_1000h": 0.12,
                  "control": "overtape-or-trim-the-exposed-edge"},
    "sealed-paint": {"index_pac_per_1000h": 0.05, "control": None},
    "conversion-coated-metal": {"index_pac_per_1000h": 0.01, "control": None},
    "polished-metal": {"index_pac_per_1000h": 0.002, "control": None},
}

# Fallout capture by the orientation of the receiving surface.
ORIENTATION_CAPTURE = {
    "upward-facing": 1.0,
    "vertical": 0.35,
    "downward-facing": 0.05,
}

# Particulate cleanliness levels and the percent area coverage each admits.
CLEANLINESS_LEVELS = {
    "level-100": 0.0010,
    "level-300": 0.0100,
    "level-500": 0.0700,
    "level-750": 0.4000,
}

# A correctly applied mandatory control leaves this fraction of the family
# shedding index in place; it reduces the source, it does not remove it.
CONTROL_CREDIT = 0.10

# Budget comparisons are sums of computed contributions; a source stack
# landing exactly on its budget is a pass, not a representation accident.
PAC_TOLERANCE_PCT = 1e-12


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _positive_real(value, label, allow_zero=False):
    """Return value as a finite float, raising when it is not usable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, number))
    elif number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def shedding_family(family):
    """Return the shedding index and mandatory control of a family."""
    key = normalise_identifier(family, "family")
    if key not in SHEDDING_FAMILIES:
        raise ValueError(
            "family must be one of %s, got %r"
            % ("/".join(sorted(SHEDDING_FAMILIES)), family)
        )
    entry = SHEDDING_FAMILIES[key]
    return {
        "family": key,
        "index_pac_per_1000h": entry["index_pac_per_1000h"],
        "control": entry["control"],
    }


def mandatory_control(family):
    """Return the control a family carries by construction, or None."""
    return shedding_family(family)["control"]


def capture_factor(orientation, view_factor):
    """Return the fraction of shed particulate the surface actually collects."""
    key = normalise_identifier(orientation, "orientation")
    if key not in ORIENTATION_CAPTURE:
        raise ValueError(
            "orientation must be one of %s, got %r"
            % ("/".join(sorted(ORIENTATION_CAPTURE)), orientation)
        )
    factor = _positive_real(view_factor, "view_factor", allow_zero=True)
    if factor > 1.0:
        raise ValueError("view_factor must not exceed unity, got %g" % factor)
    return ORIENTATION_CAPTURE[key] * factor


def validate_source(source, index=0):
    """Return one normalised particulate source record."""
    if not isinstance(source, dict):
        raise ValueError("source[%d] must be a mapping" % index)
    for key in ("name", "family", "area_cm2", "orientation", "view_factor"):
        if key not in source:
            raise ValueError("source[%d] is missing '%s'" % (index, key))
    entry = shedding_family(source["family"])
    return {
        "name": normalise_identifier(source["name"], "source[%d].name" % index),
        "family": entry["family"],
        "index_pac_per_1000h": entry["index_pac_per_1000h"],
        "mandatory_control": entry["control"],
        "area_cm2": _positive_real(source["area_cm2"], "source[%d].area_cm2" % index),
        "orientation": normalise_identifier(
            source["orientation"], "source[%d].orientation" % index
        ),
        "view_factor": _positive_real(
            source["view_factor"], "source[%d].view_factor" % index, allow_zero=True
        ),
        "control_applied": bool(source.get("control_applied", False)),
    }


def source_contribution_pct(source, surface_area_cm2, exposure_hours):
    """Return the percent area coverage one source adds to the surface."""
    record = source if "index_pac_per_1000h" in source else validate_source(source)
    area = _positive_real(surface_area_cm2, "surface_area_cm2")
    hours = _positive_real(exposure_hours, "exposure_hours", allow_zero=True)
    capture = capture_factor(record["orientation"], record["view_factor"])
    credit = 1.0
    if record["mandatory_control"] is not None and record["control_applied"]:
        credit = CONTROL_CREDIT
    return (
        record["index_pac_per_1000h"]
        * credit
        * (record["area_cm2"] / area)
        * capture
        * (hours / 1000.0)
    )


def cleanliness_budget_pct(level):
    """Return the percent area coverage a particulate cleanliness level admits."""
    key = normalise_identifier(level, "level")
    if key not in CLEANLINESS_LEVELS:
        raise ValueError(
            "level must be one of %s, got %r"
            % ("/".join(sorted(CLEANLINESS_LEVELS)), level)
        )
    return CLEANLINESS_LEVELS[key]


def control_findings(records):
    """Return the controls still owed by the installed sources."""
    findings = []
    for record in records:
        control = record["mandatory_control"]
        if control is None:
            continue
        if record["control_applied"]:
            continue
        if record["view_factor"] == 0.0:
            continue
        findings.append(
            "%s is a %s source in line of sight of the surface with no %s applied"
            % (record["name"], record["family"], control)
        )
    return findings


def aggregate_contributions(records, surface_area_cm2, exposure_hours):
    """Return the per-source and total percent area coverage."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of sources")
    contributions = []
    total = 0.0
    for record in records:
        value = source_contribution_pct(record, surface_area_cm2, exposure_hours)
        contributions.append({
            "name": record["name"],
            "family": record["family"],
            "contribution_pac_pct": value,
        })
        total += value
    contributions.sort(key=lambda item: (-item["contribution_pac_pct"], item["name"]))
    return {"contributions": contributions, "total_pac_pct": total}


def assess_particulate_control(spec):
    """Grade a particulate-shedding installation against a surface budget.

    spec keys: sources, surface_area_cm2, exposure_hours, cleanliness_level.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sources", "surface_area_cm2", "exposure_hours", "cleanliness_level"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    raw = spec["sources"]
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("spec['sources'] must be a non-empty sequence")
    records = []
    seen = set()
    for index, item in enumerate(raw):
        record = validate_source(item, index)
        if record["name"] in seen:
            raise ValueError("source %r is listed twice" % record["name"])
        seen.add(record["name"])
        records.append(record)
    budget = cleanliness_budget_pct(spec["cleanliness_level"])
    rolled = aggregate_contributions(
        records, spec["surface_area_cm2"], spec["exposure_hours"]
    )
    total = rolled["total_pac_pct"]
    over_budget = total > budget and not math.isclose(
        total, budget, rel_tol=0.0, abs_tol=PAC_TOLERANCE_PCT
    )
    findings = control_findings(records)
    if over_budget:
        findings.append(
            "particulate budget exceeded: %.5f percent area coverage against the "
            "%.5f percent the level admits" % (total, budget)
        )
    driver = rolled["contributions"][0] if rolled["contributions"] else None
    return {
        "cleanliness_level": normalise_identifier(
            spec["cleanliness_level"], "cleanliness_level"
        ),
        "budget_pac_pct": budget,
        "total_pac_pct": total,
        "margin_pac_pct": budget - total,
        "within_budget": not over_budget,
        "contributions": rolled["contributions"],
        "dominant_source": None if driver is None else driver["name"],
        "findings": findings,
        "verdict": "installation-controlled" if not findings else "controls-owed",
    }
