"""High-voltage application requirements for an electrical harness.

Anchor: ECSS-Q-ST-20-30C section 6.20, which binds the high-voltage
section (section 20) of the IPC/WHMA-A-620 acceptance basis
(paraphrased into an implementable procedure; no standard text is
reproduced). The numeric constants below are the representative
defaults a project tailors; the procedure is what this module fixes.

Procedure implemented here:

1. Decide whether the high-voltage provisions apply at all. Below the
   high-voltage threshold a harness feature is graded by the ordinary
   acceptance criteria and no clearance, creepage or proof test is
   owed under this section.
2. Read the pressure the feature actually operates at and pick the
   insulation regime from it. Well above the Paschen minimum the
   medium is air, and its dielectric strength falls with pressure.
   Well below it the residual gas breaks down at a far higher voltage
   and the limiting mechanism is surface flashover. Between the two
   lies the band where the breakdown voltage of air is at its lowest,
   and an unencapsulated feature cannot be held off there at any
   practical spacing.
3. Size the clearance through the medium from the working voltage, the
   gradient of the regime and a safety factor, with a floor no feature
   goes below.
4. Size the creepage along the insulating surface from the working
   voltage, the material group and the contamination category, with
   its own floor, and never below the clearance -- a path along a
   surface is not allowed to be shorter than the path through the gap
   it parallels.
5. Grade the as-built distances against those two figures.
6. Derive the proof voltage of the high-voltage test from the working
   voltage and grade the applied voltage, the dwell and the leakage
   current against it.

Stdlib only, offline, deterministic.
"""

REGIME_AMBIENT_AIR = "ambient-air"
REGIME_PASCHEN_MINIMUM_BAND = "paschen-minimum-band"
REGIME_VACUUM = "vacuum"

# Pressure band where the breakdown voltage of air passes through its
# minimum. Air is not a usable insulator here.
PASCHEN_BAND_LOW_MBAR = 1.0e-2
PASCHEN_BAND_HIGH_MBAR = 1.0e2

SEA_LEVEL_PRESSURE_MBAR = 1013.25

# Breakdown gradient of air at sea level, and of a clean insulating
# surface in vacuum.
AIR_BREAKDOWN_V_PER_MM = 3000.0
VACUUM_SURFACE_FLASHOVER_V_PER_MM = 10000.0

CLEARANCE_SAFETY_FACTOR = 2.0
MIN_CLEARANCE_MM = 0.5
MIN_CREEPAGE_MM = 0.8

# Comparative tracking performance of the insulating material.
MATERIAL_GROUP_I = "group-i"
MATERIAL_GROUP_II = "group-ii"
MATERIAL_GROUP_III = "group-iii"
VALID_MATERIAL_GROUPS = (MATERIAL_GROUP_I, MATERIAL_GROUP_II, MATERIAL_GROUP_III)

CONTAMINATION_CONTROLLED = "controlled-clean"
CONTAMINATION_LIGHT = "light"
CONTAMINATION_HEAVY = "heavy"
VALID_CONTAMINATION = (
    CONTAMINATION_CONTROLLED,
    CONTAMINATION_LIGHT,
    CONTAMINATION_HEAVY,
)

# Creepage per volt, in mm/V, by material group and contamination.
CREEPAGE_MM_PER_VOLT = {
    MATERIAL_GROUP_I: {
        CONTAMINATION_CONTROLLED: 0.0020,
        CONTAMINATION_LIGHT: 0.0032,
        CONTAMINATION_HEAVY: 0.0050,
    },
    MATERIAL_GROUP_II: {
        CONTAMINATION_CONTROLLED: 0.0025,
        CONTAMINATION_LIGHT: 0.0040,
        CONTAMINATION_HEAVY: 0.0063,
    },
    MATERIAL_GROUP_III: {
        CONTAMINATION_CONTROLLED: 0.0031,
        CONTAMINATION_LIGHT: 0.0050,
        CONTAMINATION_HEAVY: 0.0080,
    },
}

HIGH_VOLTAGE_THRESHOLD_V = 100.0

PROOF_VOLTAGE_FACTOR = 1.5
PROOF_VOLTAGE_OFFSET_V = 1000.0
MIN_PROOF_DWELL_S = 60.0
MAX_PROOF_LEAKAGE_UA = 50.0

# Distances, voltages and currents are products of measured floats, so a
# value sitting exactly on its limit can land a few units in the last
# place beyond it. These tolerances are far below any measurement
# resolution and absorb that representation error without relaxing the
# limits themselves.
DISTANCE_TOLERANCE_MM = 1.0e-9
VOLTAGE_TOLERANCE_V = 1.0e-9
TIME_TOLERANCE_S = 1.0e-9
CURRENT_TOLERANCE_UA = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_feature(feature):
    """Validate one harness high-voltage feature and normalize it."""
    if not isinstance(feature, dict):
        raise ValueError("feature must be a mapping")
    feature_id = feature.get("id")
    if not isinstance(feature_id, str) or not feature_id.strip():
        raise ValueError("feature needs a non-empty string id")
    working = _numeric(
        "feature %s working_voltage_v" % feature_id, feature.get("working_voltage_v")
    )
    if working <= 0:
        raise ValueError("feature %s working_voltage_v must be positive" % feature_id)
    pressure = _numeric(
        "feature %s pressure_mbar" % feature_id, feature.get("pressure_mbar")
    )
    if pressure <= 0:
        raise ValueError("feature %s pressure_mbar must be positive" % feature_id)
    group = feature.get("material_group", MATERIAL_GROUP_II)
    if group not in VALID_MATERIAL_GROUPS:
        raise ValueError(
            "feature %s has unknown material_group %r (expected one of %s)"
            % (feature_id, group, ", ".join(VALID_MATERIAL_GROUPS))
        )
    contamination = feature.get("contamination_category", CONTAMINATION_LIGHT)
    if contamination not in VALID_CONTAMINATION:
        raise ValueError(
            "feature %s has unknown contamination_category %r (expected one of %s)"
            % (feature_id, contamination, ", ".join(VALID_CONTAMINATION))
        )
    proof = feature.get("proof_test")
    if proof is not None and not isinstance(proof, dict):
        raise ValueError("feature %s proof_test must be a mapping" % feature_id)
    return {
        "id": feature_id,
        "working_voltage_v": working,
        "pressure_mbar": pressure,
        "material_group": group,
        "contamination_category": contamination,
        "encapsulated": _boolean(
            "feature %s encapsulated" % feature_id, feature.get("encapsulated", False)
        ),
        "measured_clearance_mm": _numeric(
            "feature %s measured_clearance_mm" % feature_id,
            feature.get("measured_clearance_mm", 0.0),
            0.0,
        ),
        "measured_creepage_mm": _numeric(
            "feature %s measured_creepage_mm" % feature_id,
            feature.get("measured_creepage_mm", 0.0),
            0.0,
        ),
        "proof_test": dict(proof) if isinstance(proof, dict) else None,
    }


def high_voltage_applies(working_voltage_v):
    """Whether the high-voltage provisions are owed at this voltage."""
    return _numeric("working_voltage_v", working_voltage_v, 0.0) > HIGH_VOLTAGE_THRESHOLD_V


def pressure_regime(pressure_mbar):
    """Insulation regime the operating pressure puts the feature in."""
    pressure = _numeric("pressure_mbar", pressure_mbar)
    if pressure <= 0:
        raise ValueError("pressure_mbar must be positive")
    if pressure > PASCHEN_BAND_HIGH_MBAR:
        return REGIME_AMBIENT_AIR
    if pressure < PASCHEN_BAND_LOW_MBAR:
        return REGIME_VACUUM
    return REGIME_PASCHEN_MINIMUM_BAND


def breakdown_gradient_v_per_mm(pressure_mbar):
    """Breakdown gradient of the medium at this pressure, in V/mm."""
    regime = pressure_regime(pressure_mbar)
    if regime == REGIME_AMBIENT_AIR:
        return AIR_BREAKDOWN_V_PER_MM * (
            _numeric("pressure_mbar", pressure_mbar) / SEA_LEVEL_PRESSURE_MBAR
        )
    if regime == REGIME_VACUUM:
        return VACUUM_SURFACE_FLASHOVER_V_PER_MM
    raise ValueError(
        "no breakdown gradient inside the Paschen minimum band at %r mbar; "
        "the feature has to be encapsulated or pressurized" % (pressure_mbar,)
    )


def required_clearance_mm(working_voltage_v, pressure_mbar):
    """Clearance owed through the medium, in mm."""
    working = _numeric("working_voltage_v", working_voltage_v)
    if working <= 0:
        raise ValueError("working_voltage_v must be positive")
    gradient = breakdown_gradient_v_per_mm(pressure_mbar)
    sized = working * CLEARANCE_SAFETY_FACTOR / gradient
    return sized if sized > MIN_CLEARANCE_MM else MIN_CLEARANCE_MM


def required_creepage_mm(
    working_voltage_v, material_group, contamination_category, clearance_mm=None
):
    """Creepage owed along the insulating surface, in mm."""
    working = _numeric("working_voltage_v", working_voltage_v)
    if working <= 0:
        raise ValueError("working_voltage_v must be positive")
    if material_group not in CREEPAGE_MM_PER_VOLT:
        raise ValueError("unknown material_group %r" % (material_group,))
    table = CREEPAGE_MM_PER_VOLT[material_group]
    if contamination_category not in table:
        raise ValueError(
            "unknown contamination_category %r" % (contamination_category,)
        )
    sized = working * table[contamination_category]
    if sized < MIN_CREEPAGE_MM:
        sized = MIN_CREEPAGE_MM
    if clearance_mm is not None:
        floor = _numeric("clearance_mm", clearance_mm, 0.0)
        if sized < floor:
            sized = floor
    return sized


def proof_voltage_v(working_voltage_v):
    """Proof voltage of the high-voltage test, in volts."""
    working = _numeric("working_voltage_v", working_voltage_v)
    if working <= 0:
        raise ValueError("working_voltage_v must be positive")
    return PROOF_VOLTAGE_FACTOR * working + PROOF_VOLTAGE_OFFSET_V


def medium_findings(feature):
    """Findings about the insulating medium of one feature."""
    norm = validate_feature(feature)
    regime = pressure_regime(norm["pressure_mbar"])
    if regime == REGIME_PASCHEN_MINIMUM_BAND and not norm["encapsulated"]:
        return ["unencapsulated-feature-inside-the-paschen-minimum-band"]
    return []


def distance_findings(feature):
    """Findings about the as-built clearance and creepage of one feature."""
    norm = validate_feature(feature)
    regime = pressure_regime(norm["pressure_mbar"])
    if regime == REGIME_PASCHEN_MINIMUM_BAND:
        return []
    findings = []
    clearance = required_clearance_mm(norm["working_voltage_v"], norm["pressure_mbar"])
    creepage = required_creepage_mm(
        norm["working_voltage_v"],
        norm["material_group"],
        norm["contamination_category"],
        clearance_mm=clearance,
    )
    if norm["measured_clearance_mm"] + DISTANCE_TOLERANCE_MM < clearance:
        findings.append("as-built-clearance-below-the-sized-value")
    if norm["measured_creepage_mm"] + DISTANCE_TOLERANCE_MM < creepage:
        findings.append("as-built-creepage-below-the-sized-value")
    return findings


def proof_test_findings(feature):
    """Findings about the high-voltage proof test of one feature."""
    norm = validate_feature(feature)
    record = norm["proof_test"]
    if record is None:
        return ["no-high-voltage-proof-test-on-record"]
    findings = []
    applied = _numeric("applied_v", record.get("applied_v"), 0.0)
    dwell = _numeric("dwell_s", record.get("dwell_s", 0.0), 0.0)
    leakage = _numeric("leakage_ua", record.get("leakage_ua", 0.0), 0.0)
    required = proof_voltage_v(norm["working_voltage_v"])
    if applied + VOLTAGE_TOLERANCE_V < required:
        findings.append("proof-voltage-below-the-derived-level")
    if dwell + TIME_TOLERANCE_S < MIN_PROOF_DWELL_S:
        findings.append("proof-dwell-shorter-than-required")
    if leakage > MAX_PROOF_LEAKAGE_UA + CURRENT_TOLERANCE_UA:
        findings.append("proof-leakage-current-above-the-limit")
    return findings


def assess_hv_feature(feature):
    """Assess one harness feature against section 6.20."""
    norm = validate_feature(feature)
    if not high_voltage_applies(norm["working_voltage_v"]):
        return {
            "id": norm["id"],
            "applicable": False,
            "regime": pressure_regime(norm["pressure_mbar"]),
            "required_clearance_mm": None,
            "required_creepage_mm": None,
            "proof_voltage_v": None,
            "findings": [],
            "compliant": True,
        }
    regime = pressure_regime(norm["pressure_mbar"])
    clearance = None
    creepage = None
    if regime != REGIME_PASCHEN_MINIMUM_BAND:
        clearance = required_clearance_mm(norm["working_voltage_v"], norm["pressure_mbar"])
        creepage = required_creepage_mm(
            norm["working_voltage_v"],
            norm["material_group"],
            norm["contamination_category"],
            clearance_mm=clearance,
        )
    findings = list(medium_findings(norm))
    findings.extend(distance_findings(norm))
    findings.extend(proof_test_findings(norm))
    return {
        "id": norm["id"],
        "applicable": True,
        "regime": regime,
        "required_clearance_mm": clearance,
        "required_creepage_mm": creepage,
        "proof_voltage_v": proof_voltage_v(norm["working_voltage_v"]),
        "findings": findings,
        "compliant": not findings,
    }


def assess_hv_application(features):
    """Run the section 6.20 assessment over a set of harness features."""
    if not isinstance(features, list) or not features:
        raise ValueError("features must be a non-empty list")
    results = []
    seen = set()
    for feature in features:
        result = assess_hv_feature(feature)
        if result["id"] in seen:
            raise ValueError("duplicate feature id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "features": results,
        "high_voltage_ids": [r["id"] for r in results if r["applicable"]],
        "encapsulation_required_ids": [
            r["id"]
            for r in results
            if r["applicable"] and r["regime"] == REGIME_PASCHEN_MINIMUM_BAND
        ],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
