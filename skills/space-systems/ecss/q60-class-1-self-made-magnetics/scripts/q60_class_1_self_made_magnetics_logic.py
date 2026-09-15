"""Design and screening of in-house wound magnetic parts for class 1 equipment.

Anchor: ECSS-Q-ST-60C clause 4.6.8 (designing and screening self-made wound
magnetic parts for class 1 equipment to recognised practice). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the part is admissible at all: an untraceable identity, an
   unstated wire or core specification, an unqualified winding procedure or an
   uncertified operator stops the part before any design check is run.
2. Run the four recognised-practice design checks: winding current density,
   core flux utilisation, interwinding dielectric withstanding voltage and hot
   spot margin against the insulation rating.
3. Record the design findings those checks raise.
4. Derive the screening sequence the construction, impregnation state, working
   voltage, core gap and flight lot size call for.
5. Compare the screening already closed against the owed sequence and return
   the outstanding steps and the coverage fraction.
6. Return one disposition: practice-satisfied, screening-outstanding,
   design-nonconforming or magnetics-not-admissible.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "SCREENING_SEQUENCE",
    "BASELINE_SCREENING",
    "CURRENT_DENSITY_LIMIT_A_PER_MM2",
    "FLUX_UTILISATION_LIMIT",
    "DIELECTRIC_TEST_FACTOR",
    "DIELECTRIC_TEST_BASE_V",
    "DIELECTRIC_TRIGGER_VOLTAGE_V",
    "HOT_SPOT_DERATING_K",
    "magnetics_admissibility",
    "winding_current_density",
    "current_density_acceptable",
    "flux_utilisation",
    "flux_utilisation_acceptable",
    "required_dielectric_test_voltage",
    "dielectric_test_adequate",
    "hot_spot_margin_k",
    "hot_spot_margin_acceptable",
    "design_findings",
    "ordered_screening",
    "required_screening",
    "outstanding_screening",
    "screening_coverage",
    "magnetics_disposition",
    "assess_class_1_self_made_magnetics",
]

# Current densities, flux ratios and temperature margins are float quotients
# and differences; a part sitting exactly on a bound can land a few ULP on the
# wrong side. Absorb the representation error here, never by moving the bound.
BOUND_TOLERANCE = 1e-9

# Every screening step, in the order it is performed. Non-destructive work
# comes first and the sampled destructive step comes last, so a part is never
# consumed before the cheap evidence is in.
SCREENING_SEQUENCE = (
    "wire-and-core-material-review",
    "winding-procedure-qualification",
    "in-process-winding-inspection",
    "vacuum-impregnation-verification",
    "external-visual-inspection",
    "winding-resistance-measurement",
    "insulation-resistance-measurement",
    "interwinding-dielectric-withstanding-test",
    "gap-stability-verification",
    "thermal-vacuum-conditioning",
    "final-electrical-measurement",
    "sample-destructive-physical-analysis",
)

_STEP_ORDER = {name: index for index, name in enumerate(SCREENING_SEQUENCE)}

# Steps a self-made magnetic part owes whatever its construction.
BASELINE_SCREENING = (
    "wire-and-core-material-review",
    "winding-procedure-qualification",
    "in-process-winding-inspection",
    "external-visual-inspection",
    "winding-resistance-measurement",
    "insulation-resistance-measurement",
    "thermal-vacuum-conditioning",
    "final-electrical-measurement",
)

# Recognised-practice ceiling on the current a winding conductor carries per
# square millimetre of conductor cross section.
CURRENT_DENSITY_LIMIT_A_PER_MM2 = 5.0

# Fraction of the core saturation flux density the peak working flux may reach.
FLUX_UTILISATION_LIMIT = 0.7

# Interwinding dielectric withstanding voltage: twice the working voltage plus
# a fixed base, the recognised-practice construction for wound parts.
DIELECTRIC_TEST_FACTOR = 2.0
DIELECTRIC_TEST_BASE_V = 1000.0

# Working voltage at or above which an interwinding dielectric withstanding
# test is owed as a screening step in its own right.
DIELECTRIC_TRIGGER_VOLTAGE_V = 50.0

# Kelvin the winding hot spot must stay below the insulation system rating.
HOT_SPOT_DERATING_K = 25.0


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_positive(value, label):
    """Return a validated strictly positive float or raise."""
    number = _require_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_flag(value, label):
    """Return a validated boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def magnetics_admissibility(part):
    """Return the reasons a self-made magnetic part cannot be assessed.

    An empty list means the design checks may be run. The reasons are ordered
    from identity outwards, because a part nobody can name is not a current
    density problem.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    reasons = []
    if not _is_text(part.get("part_id")):
        reasons.append("part-identity-not-traceable")
    if not _is_text(part.get("wire_specification")):
        reasons.append("wire-specification-not-stated")
    if not _is_text(part.get("core_specification")):
        reasons.append("core-specification-not-stated")
    if not _require_flag(part.get("winding_procedure_qualified", False),
                         "winding_procedure_qualified"):
        reasons.append("winding-procedure-not-qualified")
    if not _require_flag(part.get("operator_certified", False),
                         "operator_certified"):
        reasons.append("winding-operator-not-certified")
    return reasons


def winding_current_density(winding_current_a, conductor_area_mm2):
    """Return the winding current density in ampere per square millimetre."""
    current = _require_number(winding_current_a, "winding_current_a")
    area = _require_positive(conductor_area_mm2, "conductor_area_mm2")
    return current / area


def current_density_acceptable(density):
    """Return whether a current density sits at or under the practice limit."""
    value = _require_number(density, "density")
    return value <= CURRENT_DENSITY_LIMIT_A_PER_MM2 + BOUND_TOLERANCE


def flux_utilisation(peak_flux_density_t, saturation_flux_density_t):
    """Return the fraction of core saturation the peak working flux reaches."""
    peak = _require_number(peak_flux_density_t, "peak_flux_density_t")
    saturation = _require_positive(saturation_flux_density_t,
                                   "saturation_flux_density_t")
    return peak / saturation


def flux_utilisation_acceptable(utilisation):
    """Return whether a flux utilisation sits at or under the practice limit."""
    value = _require_number(utilisation, "utilisation")
    return value <= FLUX_UTILISATION_LIMIT + BOUND_TOLERANCE


def required_dielectric_test_voltage(working_voltage_v):
    """Return the interwinding test voltage recognised practice calls for."""
    working = _require_number(working_voltage_v, "working_voltage_v")
    return DIELECTRIC_TEST_FACTOR * working + DIELECTRIC_TEST_BASE_V


def dielectric_test_adequate(applied_test_voltage_v, working_voltage_v):
    """Return whether an applied test voltage meets the required one."""
    applied = _require_number(applied_test_voltage_v, "applied_test_voltage_v")
    required = required_dielectric_test_voltage(working_voltage_v)
    return applied >= required - BOUND_TOLERANCE


def hot_spot_margin_k(insulation_rating_c, hot_spot_temperature_c):
    """Return the kelvin between the winding hot spot and the rating."""
    rating = _require_number(insulation_rating_c, "insulation_rating_c",
                             allow_negative=True)
    hot_spot = _require_number(hot_spot_temperature_c, "hot_spot_temperature_c",
                               allow_negative=True)
    return rating - hot_spot


def hot_spot_margin_acceptable(margin_k):
    """Return whether a hot spot margin meets the class 1 derating."""
    margin = _require_number(margin_k, "margin_k", allow_negative=True)
    return margin >= HOT_SPOT_DERATING_K - BOUND_TOLERANCE


def design_findings(part):
    """Return the recognised-practice findings the design raises.

    part keys read here: winding_current_a, conductor_area_mm2,
    peak_flux_density_t, saturation_flux_density_t, applied_test_voltage_v,
    working_voltage_v, insulation_rating_c and hot_spot_temperature_c.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    findings = []
    density = winding_current_density(part.get("winding_current_a", 0.0),
                                      part.get("conductor_area_mm2"))
    if not current_density_acceptable(density):
        findings.append("winding-current-density-above-practice-limit")
    utilisation = flux_utilisation(part.get("peak_flux_density_t", 0.0),
                                   part.get("saturation_flux_density_t"))
    if not flux_utilisation_acceptable(utilisation):
        findings.append("core-flux-utilisation-above-practice-limit")
    if not dielectric_test_adequate(part.get("applied_test_voltage_v", 0.0),
                                    part.get("working_voltage_v", 0.0)):
        findings.append("interwinding-test-voltage-below-required")
    margin = hot_spot_margin_k(part.get("insulation_rating_c"),
                               part.get("hot_spot_temperature_c"))
    if not hot_spot_margin_acceptable(margin):
        findings.append("hot-spot-margin-below-class-1-derating")
    return findings


def ordered_screening(steps):
    """Return the screening steps in performance order, rejecting unknowns."""
    if not isinstance(steps, (list, tuple, set, frozenset)):
        raise ValueError("steps must be a sequence or set")
    names = []
    for item in steps:
        name = _require_text(item, "screening step").casefold()
        if name not in _STEP_ORDER:
            raise ValueError(
                "unknown screening step %r; expected one of %r"
                % (item, list(SCREENING_SEQUENCE))
            )
        if name in names:
            raise ValueError("screening step %r listed twice" % name)
        names.append(name)
    return sorted(names, key=lambda name: _STEP_ORDER[name])


def required_screening(part):
    """Return the screening sequence a self-made magnetic part owes.

    part keys read here: vacuum_impregnated, working_voltage_v, gapped_core
    and flight_lot_size.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    owed = set(BASELINE_SCREENING)
    if not _require_flag(part.get("vacuum_impregnated", False),
                         "vacuum_impregnated"):
        owed.add("vacuum-impregnation-verification")
    working = _require_number(part.get("working_voltage_v", 0.0),
                              "working_voltage_v")
    if working >= DIELECTRIC_TRIGGER_VOLTAGE_V - BOUND_TOLERANCE:
        owed.add("interwinding-dielectric-withstanding-test")
    if _require_flag(part.get("gapped_core", False), "gapped_core"):
        owed.add("gap-stability-verification")
    lot_size = part.get("flight_lot_size", 1)
    if not isinstance(lot_size, int) or isinstance(lot_size, bool) or lot_size <= 0:
        raise ValueError("flight_lot_size must be a positive integer, got %r"
                         % (lot_size,))
    if lot_size > 1:
        owed.add("sample-destructive-physical-analysis")
    return ordered_screening(owed)


def outstanding_screening(owed, closed):
    """Return the owed screening steps not yet closed, in performance order."""
    owed_names = ordered_screening(owed)
    if not isinstance(closed, (list, tuple, set, frozenset)):
        raise ValueError("closed must be a sequence or set")
    done = set()
    for item in closed:
        name = _require_text(item, "closed step").casefold()
        if name not in _STEP_ORDER:
            raise ValueError(
                "unknown screening step %r; expected one of %r"
                % (item, list(SCREENING_SEQUENCE))
            )
        done.add(name)
    return [name for name in owed_names if name not in done]


def screening_coverage(owed, closed):
    """Return the fraction of the owed screening sequence already closed."""
    owed_names = ordered_screening(owed)
    if not owed_names:
        raise ValueError("owed must name at least one screening step")
    remaining = outstanding_screening(owed_names, closed)
    return (len(owed_names) - len(remaining)) / float(len(owed_names))


def magnetics_disposition(admissibility_reasons, findings, remaining):
    """Return the disposition implied by the assessment state."""
    for label, value in (("admissibility_reasons", admissibility_reasons),
                         ("findings", findings), ("remaining", remaining)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    if admissibility_reasons:
        return "magnetics-not-admissible"
    if findings:
        return "design-nonconforming"
    if remaining:
        return "screening-outstanding"
    return "practice-satisfied"


def assess_class_1_self_made_magnetics(part):
    """Assess one clause 4.6.8 in-house wound magnetic part.

    part keys: part_id, wire_specification, core_specification,
    winding_procedure_qualified, operator_certified, conductor_area_mm2,
    saturation_flux_density_t, insulation_rating_c, hot_spot_temperature_c,
    and the optional winding_current_a, peak_flux_density_t,
    working_voltage_v, applied_test_voltage_v, vacuum_impregnated,
    gapped_core, flight_lot_size and screening_closed.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    reasons = magnetics_admissibility(part)
    if reasons:
        return {
            "admissibility_reasons": reasons,
            "admissible": False,
            "current_density_a_per_mm2": None,
            "flux_utilisation": None,
            "required_test_voltage_v": None,
            "hot_spot_margin_k": None,
            "findings": [],
            "screening_sequence": [],
            "outstanding_screening": [],
            "screening_coverage": 0.0,
            "disposition": "magnetics-not-admissible",
            "cleared_for_class_1_use": False,
        }
    density = winding_current_density(part.get("winding_current_a", 0.0),
                                      part.get("conductor_area_mm2"))
    utilisation = flux_utilisation(part.get("peak_flux_density_t", 0.0),
                                   part.get("saturation_flux_density_t"))
    required_voltage = required_dielectric_test_voltage(
        part.get("working_voltage_v", 0.0))
    margin = hot_spot_margin_k(part.get("insulation_rating_c"),
                               part.get("hot_spot_temperature_c"))
    findings = design_findings(part)
    owed = required_screening(part)
    closed = part.get("screening_closed", [])
    remaining = outstanding_screening(owed, closed)
    coverage = screening_coverage(owed, closed)
    disposition = magnetics_disposition(reasons, findings, remaining)
    return {
        "admissibility_reasons": reasons,
        "admissible": True,
        "current_density_a_per_mm2": density,
        "flux_utilisation": utilisation,
        "required_test_voltage_v": required_voltage,
        "hot_spot_margin_k": margin,
        "findings": findings,
        "screening_sequence": owed,
        "outstanding_screening": remaining,
        "screening_coverage": coverage,
        "disposition": disposition,
        "cleared_for_class_1_use": disposition == "practice-satisfied",
    }
