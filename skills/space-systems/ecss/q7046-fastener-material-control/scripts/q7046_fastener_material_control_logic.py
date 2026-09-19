"""Material control for threaded fasteners: alloy, stress corrosion, couple.

Anchor: ECSS-Q-ST-70-46, materials clause, read together with the
companion stress-corrosion standard ECSS-Q-ST-70-36 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. A fastener alloy is admitted by name, never by description. Each
   admitted alloy carries a stress-corrosion resistance category, a
   position in the galvanic series, a minimum tensile strength and the
   service temperature band it was characterized over.
2. The stress-corrosion category is what limits sustained tensile
   stress. A high-resistance alloy runs to the general design fraction
   of yield; a moderate-resistance alloy is held to half yield and
   carries that restriction as a written control; a low-resistance
   alloy takes no sustained tensile load at all, because the failure
   arrives with no warning and no load excursion to blame.
3. A fastener and the structure it clamps form a galvanic couple. The
   couple is judged by the potential difference between the two
   alloys, against a limit that tightens as the environment gets
   wetter and saltier, not by naming either alloy on its own.
4. A high-strength alloy is hydrogen-embrittlement susceptible. Above
   the susceptibility threshold the material may still be used, but
   the finish route is constrained and the constraint is issued as a
   control rather than left to the plating shop.
5. Service temperature is a covering check: the alloy band has to
   contain the mission band at both ends, so a cold end that is not
   characterized is a finding even when the hot end is comfortable.
6. Traceability is part of material control. A declaration with no
   heat number cannot be tied to a certificate, so it is rejected
   rather than accepted pending paperwork.

Stdlib only, offline, deterministic.
"""

ACCEPTED = "accepted"
ACCEPTED_WITH_CONTROLS = "accepted-with-controls"
REJECTED = "rejected"

_RANK = {ACCEPTED: 0, ACCEPTED_WITH_CONTROLS: 1, REJECTED: 2}

HIGH_RESISTANCE = "high-resistance"
MODERATE_RESISTANCE = "moderate-resistance"
LOW_RESISTANCE = "low-resistance"

# Admitted fastener alloys. galvanic_potential_v is a position in the
# galvanic series in volts, more negative being more anodic; the
# service band is the range the alloy is characterized over.
ALLOY_DATA = {
    "a286-precipitation-hardened": {
        "scc": HIGH_RESISTANCE,
        "galvanic_potential_v": -0.20,
        "min_uts_mpa": 900.0,
        "min_service_c": -250.0,
        "max_service_c": 650.0,
    },
    "inconel-718": {
        "scc": HIGH_RESISTANCE,
        "galvanic_potential_v": -0.10,
        "min_uts_mpa": 1240.0,
        "min_service_c": -250.0,
        "max_service_c": 650.0,
    },
    "titanium-6al-4v": {
        "scc": HIGH_RESISTANCE,
        "galvanic_potential_v": -0.15,
        "min_uts_mpa": 900.0,
        "min_service_c": -200.0,
        "max_service_c": 315.0,
    },
    "stainless-316-austenitic": {
        "scc": HIGH_RESISTANCE,
        "galvanic_potential_v": -0.20,
        "min_uts_mpa": 500.0,
        "min_service_c": -250.0,
        "max_service_c": 425.0,
    },
    "stainless-17-4ph-h1150": {
        "scc": MODERATE_RESISTANCE,
        "galvanic_potential_v": -0.25,
        "min_uts_mpa": 930.0,
        "min_service_c": -100.0,
        "max_service_c": 300.0,
    },
    "stainless-410-martensitic": {
        "scc": LOW_RESISTANCE,
        "galvanic_potential_v": -0.35,
        "min_uts_mpa": 700.0,
        "min_service_c": -50.0,
        "max_service_c": 400.0,
    },
    "low-alloy-steel-4340": {
        "scc": LOW_RESISTANCE,
        "galvanic_potential_v": -0.65,
        "min_uts_mpa": 1240.0,
        "min_service_c": -55.0,
        "max_service_c": 200.0,
    },
    "aluminium-7075-t73": {
        "scc": HIGH_RESISTANCE,
        "galvanic_potential_v": -0.90,
        "min_uts_mpa": 460.0,
        "min_service_c": -200.0,
        "max_service_c": 120.0,
    },
    "aluminium-7075-t6": {
        "scc": LOW_RESISTANCE,
        "galvanic_potential_v": -0.90,
        "min_uts_mpa": 525.0,
        "min_service_c": -200.0,
        "max_service_c": 120.0,
    },
    "aluminium-2024-t4": {
        "scc": LOW_RESISTANCE,
        "galvanic_potential_v": -0.85,
        "min_uts_mpa": 425.0,
        "min_service_c": -200.0,
        "max_service_c": 120.0,
    },
}

VALID_ALLOYS = tuple(sorted(ALLOY_DATA))

# Structure alloys a fastener is couple-checked against.
STRUCTURE_POTENTIAL_V = {
    "aluminium-7075-t73": -0.90,
    "aluminium-6061-t6": -0.85,
    "magnesium-az31": -1.60,
    "titanium-6al-4v": -0.15,
    "stainless-316-austenitic": -0.20,
    "carbon-fibre-laminate": 0.25,
    "low-alloy-steel-4340": -0.65,
}

VALID_STRUCTURES = tuple(sorted(STRUCTURE_POTENTIAL_V))

# Admissible couple potential difference, tightening with wetness.
ENVIRONMENT_COUPLE_LIMIT_V = {
    "controlled-cleanroom": 0.50,
    "general-indoor": 0.25,
    "coastal-launch-site": 0.15,
}

VALID_ENVIRONMENTS = tuple(sorted(ENVIRONMENT_COUPLE_LIMIT_V))

# Fraction of yield a sustained tensile stress may reach, by category.
SUSTAINED_STRESS_FRACTION = {
    HIGH_RESISTANCE: 0.75,
    MODERATE_RESISTANCE: 0.50,
    LOW_RESISTANCE: 0.0,
}

# Above this declared tensile strength the alloy is treated as
# hydrogen-embrittlement susceptible and the finish route is controlled.
EMBRITTLEMENT_THRESHOLD_MPA = 1000.0

# Stresses and potentials are quotients and differences of measured
# floats, so a case sitting exactly on a limit can land a few units in
# the last place outside it. These absorb that representation error
# without widening any limit to an engineering degree.
STRESS_TOLERANCE_MPA = 1.0e-9
POTENTIAL_TOLERANCE_V = 1.0e-9
TEMPERATURE_TOLERANCE_C = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def alloy_record(alloy):
    """Return the admitted data for one fastener alloy."""
    if not isinstance(alloy, str) or alloy not in ALLOY_DATA:
        raise ValueError(
            "unknown fastener alloy %r (expected one of %s)"
            % (alloy, ", ".join(VALID_ALLOYS))
        )
    return dict(ALLOY_DATA[alloy])


def scc_category(alloy):
    """Stress-corrosion resistance category of an admitted alloy."""
    return alloy_record(alloy)["scc"]


def sustained_stress_limit_mpa(alloy, yield_mpa):
    """Highest sustained tensile stress the category permits, in MPa."""
    fraction = SUSTAINED_STRESS_FRACTION[scc_category(alloy)]
    return fraction * _numeric("yield_mpa", yield_mpa, 0.0)


def assess_sustained_stress(alloy, applied_stress_mpa, yield_mpa):
    """Judge a sustained tensile stress against the category limit."""
    applied = _numeric("applied_stress_mpa", applied_stress_mpa, 0.0)
    limit = sustained_stress_limit_mpa(alloy, yield_mpa)
    category = scc_category(alloy)
    compliant = applied <= limit + STRESS_TOLERANCE_MPA
    return {
        "alloy": alloy,
        "category": category,
        "applied_stress_mpa": applied,
        "limit_mpa": limit,
        "margin_mpa": limit - applied,
        "compliant": compliant,
    }


def galvanic_couple(alloy, structure_alloy, environment):
    """Judge the fastener-to-structure couple against the environment."""
    fastener_v = alloy_record(alloy)["galvanic_potential_v"]
    if not isinstance(structure_alloy, str) or structure_alloy not in STRUCTURE_POTENTIAL_V:
        raise ValueError(
            "unknown structure alloy %r (expected one of %s)"
            % (structure_alloy, ", ".join(VALID_STRUCTURES))
        )
    if not isinstance(environment, str) or environment not in ENVIRONMENT_COUPLE_LIMIT_V:
        raise ValueError(
            "unknown environment %r (expected one of %s)"
            % (environment, ", ".join(VALID_ENVIRONMENTS))
        )
    structure_v = STRUCTURE_POTENTIAL_V[structure_alloy]
    difference = abs(fastener_v - structure_v)
    limit = ENVIRONMENT_COUPLE_LIMIT_V[environment]
    anodic = structure_alloy if structure_v < fastener_v else alloy
    return {
        "difference_v": difference,
        "limit_v": limit,
        "anodic_member": anodic,
        "admissible": difference <= limit + POTENTIAL_TOLERANCE_V,
    }


def embrittlement_susceptible(alloy, declared_uts_mpa=None):
    """Whether the alloy sits above the embrittlement threshold."""
    strength = alloy_record(alloy)["min_uts_mpa"]
    if declared_uts_mpa is not None:
        strength = _numeric("declared_uts_mpa", declared_uts_mpa, 0.0)
    return strength >= EMBRITTLEMENT_THRESHOLD_MPA - STRESS_TOLERANCE_MPA


def temperature_coverage(alloy, mission_min_c, mission_max_c):
    """Whether the alloy band covers the mission band at both ends."""
    data = alloy_record(alloy)
    low = _numeric("mission_min_c", mission_min_c)
    high = _numeric("mission_max_c", mission_max_c)
    if high < low:
        raise ValueError("mission_max_c must not sit below mission_min_c")
    cold_ok = low >= data["min_service_c"] - TEMPERATURE_TOLERANCE_C
    hot_ok = high <= data["max_service_c"] + TEMPERATURE_TOLERANCE_C
    return {
        "cold_end_covered": cold_ok,
        "hot_end_covered": hot_ok,
        "covered": cold_ok and hot_ok,
        "alloy_min_service_c": data["min_service_c"],
        "alloy_max_service_c": data["max_service_c"],
    }


def validate_declaration(record):
    """Validate one material declaration and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("material declaration must be a mapping")
    alloy = record.get("alloy")
    data = alloy_record(alloy)
    heat_number = record.get("heat_number")
    if not isinstance(heat_number, str) or not heat_number.strip():
        raise ValueError("declaration for %s needs a non-empty heat_number" % alloy)
    part = record.get("part_number")
    if not isinstance(part, str) or not part.strip():
        raise ValueError("declaration for %s needs a non-empty part_number" % alloy)
    yield_mpa = _numeric("yield_mpa", record.get("yield_mpa"), 0.0)
    if yield_mpa <= 0.0:
        raise ValueError("yield_mpa must be positive")
    uts_mpa = _numeric("uts_mpa", record.get("uts_mpa", data["min_uts_mpa"]), 0.0)
    if uts_mpa < yield_mpa:
        raise ValueError("uts_mpa must not sit below yield_mpa")
    structure_alloy = record.get("structure_alloy")
    if structure_alloy not in STRUCTURE_POTENTIAL_V:
        raise ValueError("unknown structure alloy %r" % (structure_alloy,))
    environment = record.get("environment")
    if environment not in ENVIRONMENT_COUPLE_LIMIT_V:
        raise ValueError("unknown environment %r" % (environment,))
    return {
        "alloy": alloy,
        "part_number": part.strip(),
        "heat_number": heat_number.strip(),
        "yield_mpa": yield_mpa,
        "uts_mpa": uts_mpa,
        "sustained_stress_mpa": _numeric(
            "sustained_stress_mpa", record.get("sustained_stress_mpa", 0.0), 0.0
        ),
        "structure_alloy": structure_alloy,
        "environment": environment,
        "mission_min_c": _numeric("mission_min_c", record.get("mission_min_c", 20.0)),
        "mission_max_c": _numeric("mission_max_c", record.get("mission_max_c", 20.0)),
        "electrolytic_finish": bool(record.get("electrolytic_finish", False)),
        "relief_bake_declared": bool(record.get("relief_bake_declared", False)),
    }


def assess_declaration(record):
    """Assess one material declaration end to end."""
    norm = validate_declaration(record)
    findings = []
    controls = []
    disposition = ACCEPTED

    def escalate(level):
        if _RANK[level] > _RANK[disposition]:
            return level
        return disposition

    stress = assess_sustained_stress(
        norm["alloy"], norm["sustained_stress_mpa"], norm["yield_mpa"]
    )
    category = stress["category"]
    if category == LOW_RESISTANCE and norm["sustained_stress_mpa"] > STRESS_TOLERANCE_MPA:
        findings.append("low-resistance-alloy-under-sustained-tension")
        disposition = escalate(REJECTED)
    elif not stress["compliant"]:
        findings.append("sustained-stress-above-the-category-limit")
        disposition = escalate(REJECTED)
    elif category == MODERATE_RESISTANCE:
        controls.append("hold-sustained-stress-below-half-yield")
        disposition = escalate(ACCEPTED_WITH_CONTROLS)

    couple = galvanic_couple(
        norm["alloy"], norm["structure_alloy"], norm["environment"]
    )
    if not couple["admissible"]:
        findings.append("galvanic-couple-above-the-environment-limit")
        disposition = escalate(REJECTED)

    susceptible = embrittlement_susceptible(norm["alloy"], norm["uts_mpa"])
    if susceptible:
        if norm["electrolytic_finish"] and not norm["relief_bake_declared"]:
            findings.append("electrolytic-finish-without-a-relief-bake")
            disposition = escalate(REJECTED)
        else:
            controls.append("constrain-the-finish-route-for-embrittlement")
            disposition = escalate(ACCEPTED_WITH_CONTROLS)

    coverage = temperature_coverage(
        norm["alloy"], norm["mission_min_c"], norm["mission_max_c"]
    )
    if not coverage["cold_end_covered"]:
        findings.append("mission-cold-end-outside-the-alloy-band")
        disposition = escalate(REJECTED)
    if not coverage["hot_end_covered"]:
        findings.append("mission-hot-end-outside-the-alloy-band")
        disposition = escalate(REJECTED)

    return {
        "part_number": norm["part_number"],
        "alloy": norm["alloy"],
        "heat_number": norm["heat_number"],
        "category": category,
        "sustained_stress": stress,
        "galvanic_couple": couple,
        "embrittlement_susceptible": susceptible,
        "temperature_coverage": coverage,
        "controls": controls,
        "findings": findings,
        "disposition": disposition,
    }


def assess_material_schedule(records):
    """Assess every declaration on a build and roll them up."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_declaration(record)
        key = (result["part_number"], result["heat_number"])
        if key in seen:
            raise ValueError("duplicate part and heat %r" % (key,))
        seen.add(key)
        results.append(result)
    build = ACCEPTED
    for result in results:
        if _RANK[result["disposition"]] > _RANK[build]:
            build = result["disposition"]
    return {
        "declarations": results,
        "build_disposition": build,
        "rejected_parts": [
            r["part_number"] for r in results if r["disposition"] == REJECTED
        ],
        "controlled_parts": [
            r["part_number"]
            for r in results
            if r["disposition"] == ACCEPTED_WITH_CONTROLS
        ],
    }
