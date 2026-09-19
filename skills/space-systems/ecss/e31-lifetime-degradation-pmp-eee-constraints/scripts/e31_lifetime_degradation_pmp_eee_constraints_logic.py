"""End-of-life degradation, PMP and EEE constraints on a thermal control design.

Anchor: ECSS-E-ST-31C clauses 4.4.3 to 4.4.5 (design provisions for lifetime
degradation of thermo-optical properties, materials-and-processes restrictions
and electrical-parts restrictions). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each thermal-optical surface at beginning of life.
2. Age the solar absorptance towards a saturating asymptote with the
   accumulated equivalent sun hours, and move the infrared emittance with the
   atomic-oxygen fluence.
3. Re-form the absorptance-to-emittance ratio at end of life and convert the
   absorptance growth into the extra absorbed power on the radiator area.
4. Screen every vacuum-exposed material against the outgassing mass-loss and
   condensable limits, grouping exempt materials separately and requiring a
   recorded reason for the exemption.
5. Grade every electronic part's end-of-life hot prediction against its rated
   limit reduced by the required derating margin.
"""

import math

__all__ = [
    "DEFAULT_MASS_LOSS_LIMIT_PERCENT",
    "DEFAULT_CONDENSABLE_LIMIT_PERCENT",
    "DERATING_TOLERANCE_K",
    "SOLAR_CONSTANT_W_M2",
    "validate_unit_property",
    "aged_absorptance",
    "aged_emittance",
    "absorptance_emittance_ratio",
    "absorbed_power_growth_w",
    "age_surface",
    "screen_material",
    "usable_part_limit_k",
    "grade_part",
    "assess_lifetime_constraints",
]

# Outgassing screening limits, expressed as percentages of the specimen mass.
# Both are defaults: a programme may impose a tighter figure, never a looser
# one, and the caller passes it in rather than editing these.
DEFAULT_MASS_LOSS_LIMIT_PERCENT = 1.0
DEFAULT_CONDENSABLE_LIMIT_PERCENT = 0.10

# A derating comparison is a subtraction of two temperatures that a prediction
# can land exactly on. Absorb the representation error here instead of shaving
# the engineering margin.
DERATING_TOLERANCE_K = 1e-9

# Solar irradiance at one astronomical unit, W/m^2, used only as the default
# incident flux when the caller declares none.
SOLAR_CONSTANT_W_M2 = 1361.0


def _require_real(value, label):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _require_real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _require_non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _require_real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def validate_unit_property(value, label):
    """Return a thermo-optical property validated into the open unit interval."""
    out = _require_real(value, label)
    if out <= 0.0 or out > 1.0:
        raise ValueError(
            "%s must lie in (0, 1], got %g" % (label, out)
        )
    return out


def aged_absorptance(alpha_bol, delta_alpha_saturated, exposure_esh, dose_constant_esh):
    """Return the solar absorptance after an accumulated ultraviolet dose.

    The increment approaches ``delta_alpha_saturated`` exponentially with the
    accumulated equivalent sun hours, which reproduces coating ageing far
    better than a linear rate fitted to an early data point.
    """
    alpha = validate_unit_property(alpha_bol, "alpha_bol")
    delta = _require_non_negative(delta_alpha_saturated, "delta_alpha_saturated")
    esh = _require_non_negative(exposure_esh, "exposure_esh")
    tau = _require_positive(dose_constant_esh, "dose_constant_esh")
    if alpha + delta > 1.0:
        raise ValueError(
            "saturated absorptance %g exceeds unity; the ageing model is not "
            "physical for this surface" % (alpha + delta)
        )
    return alpha + delta * (1.0 - math.exp(-esh / tau))


def aged_emittance(epsilon_bol, delta_epsilon_per_fluence, atomic_oxygen_fluence):
    """Return the infrared emittance after an atomic-oxygen fluence.

    The movement is linear in fluence and may be negative on a surface that
    the erosion smooths; the result still has to stay physical.
    """
    eps = validate_unit_property(epsilon_bol, "epsilon_bol")
    slope = _require_real(delta_epsilon_per_fluence, "delta_epsilon_per_fluence")
    fluence = _require_non_negative(atomic_oxygen_fluence, "atomic_oxygen_fluence")
    out = eps + slope * fluence
    if out <= 0.0 or out > 1.0:
        raise ValueError(
            "aged emittance %g leaves the physical unit interval" % out
        )
    return out


def absorptance_emittance_ratio(alpha, epsilon):
    """Return the absorptance-to-emittance ratio that sizes the radiator."""
    a = validate_unit_property(alpha, "alpha")
    e = validate_unit_property(epsilon, "epsilon")
    return a / e


def absorbed_power_growth_w(area_m2, incident_flux_w_m2, alpha_bol, alpha_eol):
    """Return the extra absorbed power the surface picks up through life."""
    area = _require_positive(area_m2, "area_m2")
    flux = _require_non_negative(incident_flux_w_m2, "incident_flux_w_m2")
    a_bol = validate_unit_property(alpha_bol, "alpha_bol")
    a_eol = validate_unit_property(alpha_eol, "alpha_eol")
    if a_eol < a_bol:
        raise ValueError(
            "end-of-life absorptance %g is below the beginning-of-life value "
            "%g; an improving coating is an input error" % (a_eol, a_bol)
        )
    return area * flux * (a_eol - a_bol)


def age_surface(surface):
    """Age one thermal-optical surface and return its lifetime record.

    surface keys: name, alpha_bol, epsilon_bol, delta_alpha_saturated,
    dose_constant_esh, exposure_esh, optional delta_epsilon_per_fluence,
    atomic_oxygen_fluence, area_m2, incident_flux_w_m2.
    """
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    for key in ("name", "alpha_bol", "epsilon_bol", "delta_alpha_saturated",
                "dose_constant_esh", "exposure_esh"):
        if key not in surface:
            raise ValueError("surface missing required key '%s'" % key)
    name = surface["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("surface name must be a non-empty string")
    alpha_bol = validate_unit_property(surface["alpha_bol"], "alpha_bol")
    epsilon_bol = validate_unit_property(surface["epsilon_bol"], "epsilon_bol")
    alpha_eol = aged_absorptance(
        alpha_bol,
        surface["delta_alpha_saturated"],
        surface["exposure_esh"],
        surface["dose_constant_esh"],
    )
    epsilon_eol = aged_emittance(
        epsilon_bol,
        surface.get("delta_epsilon_per_fluence", 0.0),
        surface.get("atomic_oxygen_fluence", 0.0),
    )
    ratio_bol = absorptance_emittance_ratio(alpha_bol, epsilon_bol)
    ratio_eol = absorptance_emittance_ratio(alpha_eol, epsilon_eol)
    area = surface.get("area_m2")
    if area is None:
        growth_w = None
    else:
        growth_w = absorbed_power_growth_w(
            area,
            surface.get("incident_flux_w_m2", SOLAR_CONSTANT_W_M2),
            alpha_bol,
            alpha_eol,
        )
    return {
        "name": name,
        "alpha_bol": alpha_bol,
        "alpha_eol": alpha_eol,
        "epsilon_bol": epsilon_bol,
        "epsilon_eol": epsilon_eol,
        "ratio_bol": ratio_bol,
        "ratio_eol": ratio_eol,
        "ratio_growth": ratio_eol - ratio_bol,
        "absorbed_power_growth_w": growth_w,
    }


def screen_material(material,
                    mass_loss_limit_percent=DEFAULT_MASS_LOSS_LIMIT_PERCENT,
                    condensable_limit_percent=DEFAULT_CONDENSABLE_LIMIT_PERCENT):
    """Group one material against the outgassing restrictions.

    material keys: name, vacuum_exposed (bool); mass_loss_percent and
    condensable_percent when exposed; exemption_reason when not.
    """
    if not isinstance(material, dict):
        raise ValueError("material must be a mapping")
    for key in ("name", "vacuum_exposed"):
        if key not in material:
            raise ValueError("material missing required key '%s'" % key)
    name = material["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("material name must be a non-empty string")
    exposed = material["vacuum_exposed"]
    if not isinstance(exposed, bool):
        raise ValueError("vacuum_exposed must be a boolean")
    mass_limit = _require_positive(mass_loss_limit_percent, "mass_loss_limit_percent")
    cvcm_limit = _require_positive(condensable_limit_percent, "condensable_limit_percent")
    if not exposed:
        reason = material.get("exemption_reason")
        justified = isinstance(reason, str) and bool(reason.strip())
        return {
            "name": name,
            "category": "exempt",
            "acceptable": justified,
            "finding": None if justified
            else "material %s is claimed outside vacuum exposure with no "
                 "recorded reason" % name,
        }
    for key in ("mass_loss_percent", "condensable_percent"):
        if key not in material:
            raise ValueError(
                "vacuum-exposed material %s missing '%s'" % (name, key)
            )
    mass_loss = _require_non_negative(material["mass_loss_percent"], "mass_loss_percent")
    condensable = _require_non_negative(
        material["condensable_percent"], "condensable_percent"
    )
    breaches = []
    if mass_loss > mass_limit:
        breaches.append("mass loss %.3f%% over the %.3f%% limit" % (mass_loss, mass_limit))
    if condensable > cvcm_limit:
        breaches.append(
            "condensable fraction %.3f%% over the %.3f%% limit" % (condensable, cvcm_limit)
        )
    if breaches:
        return {
            "name": name,
            "category": "screened-out",
            "acceptable": False,
            "finding": "material %s: %s" % (name, "; ".join(breaches)),
        }
    return {
        "name": name,
        "category": "compliant",
        "acceptable": True,
        "finding": None,
    }


def usable_part_limit_k(rated_limit_k, derating_margin_k):
    """Return the temperature an electronic part is allowed to reach."""
    rated = _require_real(rated_limit_k, "rated_limit_k")
    if rated <= 0.0:
        raise ValueError("rated_limit_k must be an absolute temperature above zero")
    margin = _require_non_negative(derating_margin_k, "derating_margin_k")
    usable = rated - margin
    if usable <= 0.0:
        raise ValueError(
            "derating margin %g K consumes the whole rated limit %g K" % (margin, rated)
        )
    return usable


def grade_part(part, default_derating_margin_k=0.0):
    """Grade one electronic part's end-of-life hot prediction.

    part keys: name, rated_limit_k, predicted_hot_eol_k, optional
    derating_margin_k.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("name", "rated_limit_k", "predicted_hot_eol_k"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    name = part["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("part name must be a non-empty string")
    margin = part.get("derating_margin_k", default_derating_margin_k)
    usable = usable_part_limit_k(part["rated_limit_k"], margin)
    predicted = _require_real(part["predicted_hot_eol_k"], "predicted_hot_eol_k")
    if predicted <= 0.0:
        raise ValueError("predicted_hot_eol_k must be an absolute temperature above zero")
    exceedance = predicted - usable
    acceptable = exceedance <= DERATING_TOLERANCE_K
    return {
        "name": name,
        "usable_limit_k": usable,
        "predicted_hot_eol_k": predicted,
        "exceedance_k": exceedance,
        "acceptable": acceptable,
        "finding": None if acceptable
        else "part %s reaches %.3f K against a usable limit of %.3f K"
             % (name, predicted, usable),
    }


def assess_lifetime_constraints(spec):
    """Run the full clauses 4.4.3 to 4.4.5 end-of-life assessment.

    spec keys: surfaces (sequence), materials (sequence), parts (sequence),
    optional mass_loss_limit_percent, condensable_limit_percent,
    default_derating_margin_k, max_ratio_growth.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("surfaces", "materials", "parts"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
        if not isinstance(spec[key], (list, tuple)):
            raise ValueError("spec['%s'] must be a sequence" % key)
    if not spec["surfaces"]:
        raise ValueError("spec['surfaces'] must name at least one surface")
    max_growth = spec.get("max_ratio_growth")
    if max_growth is not None:
        max_growth = _require_non_negative(max_growth, "max_ratio_growth")
    surfaces = [age_surface(s) for s in spec["surfaces"]]
    materials = [
        screen_material(
            m,
            spec.get("mass_loss_limit_percent", DEFAULT_MASS_LOSS_LIMIT_PERCENT),
            spec.get("condensable_limit_percent", DEFAULT_CONDENSABLE_LIMIT_PERCENT),
        )
        for m in spec["materials"]
    ]
    parts = [
        grade_part(p, spec.get("default_derating_margin_k", 0.0))
        for p in spec["parts"]
    ]
    findings = []
    if max_growth is not None:
        for record in surfaces:
            if record["ratio_growth"] > max_growth + DERATING_TOLERANCE_K:
                findings.append(
                    "surface %s grows its absorptance-to-emittance ratio by "
                    "%.4f against an allowance of %.4f"
                    % (record["name"], record["ratio_growth"], max_growth)
                )
    findings.extend(r["finding"] for r in materials if r["finding"])
    findings.extend(r["finding"] for r in parts if r["finding"])
    total_growth_w = sum(
        r["absorbed_power_growth_w"] for r in surfaces
        if r["absorbed_power_growth_w"] is not None
    )
    return {
        "surfaces": surfaces,
        "materials": materials,
        "parts": parts,
        "absorbed_power_growth_w": total_growth_w,
        "findings": findings,
        "compliant": not findings,
    }
