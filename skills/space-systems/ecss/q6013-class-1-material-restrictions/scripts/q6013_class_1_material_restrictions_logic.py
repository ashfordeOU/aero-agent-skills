#!/usr/bin/env python3
"""Restricted materials and constructions in a Class 1 commercial part.

Anchor: ECSS-Q-ST-60-13C clause 4.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A commercial part can satisfy every baseline selection rule and still be
unusable, because the rules grade the supply chain and this clause
grades what the part is made of. The screen runs on three axes, and the
axes answer differently.

Finishes and platings split three ways, not two. Some are simply
accepted. Some are barred outright, with no mitigation available at all
-- cadmium and zinc are barred because the failure mechanism is the
metal itself, and no process applied afterwards changes that. And one,
a pure-tin finish, is restricted rather than barred: it is admissible
when a declared mitigation is present and demonstrated, which for tin
means enough lead alloyed into the finish to suppress whisker growth,
measured as a mass fraction against a declared threshold. Reporting
"restricted" and "prohibited" as one state is the mistake that costs a
programme a part it could have kept, or lets through one it could not.

Encapsulation is a conditional axis. A hermetic metal or ceramic package
is accepted. A plastic-encapsulated part is not barred, but it carries
conditions that are themselves data: a moisture sensitivity level at or
below the declared limit, a bake-and-dry-pack record, and a total
ionising dose environment within the declared limit for an unscreened
plastic package. A missing condition is not a failed condition -- the
two are dispositioned by different people, so absence is kept separate.

Outgassing is arithmetic. The total mass loss and the collected volatile
condensable material are each compared with a declared limit, and a
material sitting exactly on a limit is inside it. Those limits are round
decimal numbers that a measured value lands on exactly often enough that
the comparison absorbs representation error rather than asserting a
strict inequality.

The material table, the mitigation threshold and the outgassing limits
below are declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MATERIAL_ACCEPTED = "material-accepted"
MATERIAL_MITIGATION_REQUIRED = "material-mitigation-required"
MATERIAL_PROHIBITED = "material-prohibited"

MATERIAL_RANK = {
    MATERIAL_PROHIBITED: 0,
    MATERIAL_MITIGATION_REQUIRED: 1,
    MATERIAL_ACCEPTED: 2,
}

CONSTRUCTION_ACCEPTED = "construction-accepted"
CONSTRUCTION_MITIGATION_REQUIRED = "construction-mitigation-required"
CONSTRUCTION_PROHIBITED = "construction-prohibited"

CONSTRUCTION_BY_RANK = {
    MATERIAL_PROHIBITED: CONSTRUCTION_PROHIBITED,
    MATERIAL_MITIGATION_REQUIRED: CONSTRUCTION_MITIGATION_REQUIRED,
    MATERIAL_ACCEPTED: CONSTRUCTION_ACCEPTED,
}

# Disposition of each declared finish or plating. "barred" materials carry
# no mitigation at all; "mitigable" ones name the mitigation that clears
# them; the rest are accepted as declared.
ACCEPTED_FINISHES = ("tin-lead", "gold", "nickel", "palladium-nickel")
BARRED_FINISHES = ("cadmium", "zinc")
MITIGABLE_FINISHES = ("pure-tin", "pure-silver")
FINISH_MATERIALS = ACCEPTED_FINISHES + BARRED_FINISHES + MITIGABLE_FINISHES

FINISH_MITIGATIONS = {
    "pure-tin": "lead-alloyed-finish",
    "pure-silver": "nickel-barrier-underplate",
}

BARRED_REASONS = {
    "cadmium": "cadmium sublimes in vacuum and grows whiskers; the mechanism "
    "is the metal itself, so no later process clears it",
    "zinc": "zinc grows whiskers and has no qualified mitigation for a "
    "Class 1 part",
}

ENCAPSULATIONS = (
    "hermetic-metal",
    "hermetic-ceramic",
    "plastic-encapsulated",
    "unknown-encapsulation",
)
HERMETIC_ENCAPSULATIONS = ("hermetic-metal", "hermetic-ceramic")

DEFAULT_MATERIAL_POLICY = {
    "min_lead_mass_fraction_percent": 3.0,
    "max_total_mass_loss_percent": 1.0,
    "max_collected_volatile_percent": 0.10,
    "max_moisture_sensitivity_level": 3,
    "max_plastic_package_dose_krad": 30.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_number(name, value, minimum=0.0):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must not sit below %r, got %r" % (name, minimum, value))
    return float(value)


def _require_level(name, value, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An outgassing limit is a round decimal and a measured mass loss
    lands on it exactly often enough that a strict comparison decides
    the case on the last bit. A value sitting on a limit is inside it.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_MATERIAL_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    fraction = _require_number(
        "min_lead_mass_fraction_percent",
        settings.get("min_lead_mass_fraction_percent"),
    )
    if fraction > 100.0:
        raise ValueError(
            "min_lead_mass_fraction_percent must not exceed 100, got %r" % (fraction,)
        )
    settings["min_lead_mass_fraction_percent"] = fraction
    settings["max_total_mass_loss_percent"] = _require_number(
        "max_total_mass_loss_percent", settings.get("max_total_mass_loss_percent")
    )
    settings["max_collected_volatile_percent"] = _require_number(
        "max_collected_volatile_percent",
        settings.get("max_collected_volatile_percent"),
    )
    settings["max_moisture_sensitivity_level"] = _require_level(
        "max_moisture_sensitivity_level",
        settings.get("max_moisture_sensitivity_level"),
    )
    settings["max_plastic_package_dose_krad"] = _require_number(
        "max_plastic_package_dose_krad",
        settings.get("max_plastic_package_dose_krad"),
    )
    return settings


def restricted_materials():
    """List the finishes barred outright and those carrying a mitigation."""
    return {
        "barred": tuple(BARRED_FINISHES),
        "mitigable": {name: FINISH_MITIGATIONS[name] for name in MITIGABLE_FINISHES},
    }


def assess_finish(finish, policy=None):
    """Grade one declared finish or plating against the material table."""
    settings = resolve_policy(policy)
    _require_mapping("finish", finish)
    material = _require_choice("material", finish.get("material"), FINISH_MATERIALS)
    surface = _require_label("surface", finish.get("surface", "part-termination"))

    findings = []
    mitigation = FINISH_MITIGATIONS.get(material)

    if material in BARRED_FINISHES:
        findings.append(
            "%s on %s: %s" % (material, surface, BARRED_REASONS[material])
        )
        return {
            "surface": surface,
            "material": material,
            "mitigation": None,
            "mitigation_applied": False,
            "lead_mass_fraction_percent": None,
            "verdict": MATERIAL_PROHIBITED,
            "findings": findings,
        }

    if material not in MITIGABLE_FINISHES:
        return {
            "surface": surface,
            "material": material,
            "mitigation": None,
            "mitigation_applied": False,
            "lead_mass_fraction_percent": None,
            "verdict": MATERIAL_ACCEPTED,
            "findings": findings,
        }

    if material == "pure-tin":
        declared = finish.get("lead_mass_fraction_percent")
        if declared is None:
            findings.append(
                "pure tin on %s: no lead mass fraction declared, so the "
                "whisker mitigation is unevidenced rather than absent" % surface
            )
            return {
                "surface": surface,
                "material": material,
                "mitigation": mitigation,
                "mitigation_applied": False,
                "lead_mass_fraction_percent": None,
                "verdict": MATERIAL_MITIGATION_REQUIRED,
                "findings": findings,
            }
        fraction = _require_number("lead_mass_fraction_percent", declared)
        if fraction > 100.0:
            raise ValueError(
                "lead_mass_fraction_percent must not exceed 100, got %r" % (fraction,)
            )
        threshold = settings["min_lead_mass_fraction_percent"]
        applied = _at_least(fraction, threshold)
        if not applied:
            findings.append(
                "pure tin on %s: lead mass fraction %.4g%% against a declared "
                "%.4g%% whisker-mitigation threshold" % (surface, fraction, threshold)
            )
        return {
            "surface": surface,
            "material": material,
            "mitigation": mitigation,
            "mitigation_applied": applied,
            "lead_mass_fraction_percent": fraction,
            "verdict": MATERIAL_ACCEPTED if applied else MATERIAL_MITIGATION_REQUIRED,
            "findings": findings,
        }

    applied = _require_flag(
        "barrier_underplate", finish.get("barrier_underplate", False)
    )
    if not applied:
        findings.append(
            "pure silver on %s: no barrier underplate declared against silver "
            "migration and tarnish" % surface
        )
    return {
        "surface": surface,
        "material": material,
        "mitigation": mitigation,
        "mitigation_applied": applied,
        "lead_mass_fraction_percent": None,
        "verdict": MATERIAL_ACCEPTED if applied else MATERIAL_MITIGATION_REQUIRED,
        "findings": findings,
    }


def assess_encapsulation(encapsulation, policy=None):
    """Grade the package construction and the conditions it carries."""
    settings = resolve_policy(policy)
    _require_mapping("encapsulation", encapsulation)
    kind = _require_choice("kind", encapsulation.get("kind"), ENCAPSULATIONS)

    findings = []
    if kind == "unknown-encapsulation":
        findings.append(
            "the package construction is not declared, so no condition on it "
            "can be shown met"
        )
        return {
            "kind": kind,
            "conditions_met": [],
            "conditions_open": [],
            "conditions_absent": ["package-construction-declaration"],
            "verdict": MATERIAL_PROHIBITED,
            "findings": findings,
        }

    if kind in HERMETIC_ENCAPSULATIONS:
        return {
            "kind": kind,
            "conditions_met": [],
            "conditions_open": [],
            "conditions_absent": [],
            "verdict": MATERIAL_ACCEPTED,
            "findings": findings,
        }

    met = []
    open_conditions = []
    absent = []

    level = encapsulation.get("moisture_sensitivity_level")
    if level is None:
        absent.append("moisture-sensitivity-level")
        findings.append(
            "plastic encapsulation: no moisture sensitivity level declared; "
            "absence is not a failure, it is nobody having answered"
        )
    else:
        value = _require_level("moisture_sensitivity_level", level)
        if value <= settings["max_moisture_sensitivity_level"]:
            met.append("moisture-sensitivity-level")
        else:
            open_conditions.append("moisture-sensitivity-level")
            findings.append(
                "plastic encapsulation: moisture sensitivity level %d against a "
                "declared limit of %d"
                % (value, settings["max_moisture_sensitivity_level"])
            )

    record = encapsulation.get("bake_and_dry_pack_record")
    if record is None:
        absent.append("bake-and-dry-pack-record")
        findings.append(
            "plastic encapsulation: no bake-and-dry-pack record declared"
        )
    elif _require_flag("bake_and_dry_pack_record", record):
        met.append("bake-and-dry-pack-record")
    else:
        open_conditions.append("bake-and-dry-pack-record")
        findings.append(
            "plastic encapsulation: the bake-and-dry-pack record is recorded "
            "as not held"
        )

    dose = encapsulation.get("total_ionising_dose_krad")
    if dose is None:
        absent.append("plastic-package-dose-environment")
        findings.append(
            "plastic encapsulation: no total ionising dose environment declared"
        )
    else:
        value = _require_number("total_ionising_dose_krad", dose)
        if _at_most(value, settings["max_plastic_package_dose_krad"]):
            met.append("plastic-package-dose-environment")
        else:
            open_conditions.append("plastic-package-dose-environment")
            findings.append(
                "plastic encapsulation: %.4g krad against a declared %.4g krad "
                "limit for an unscreened plastic package"
                % (value, settings["max_plastic_package_dose_krad"])
            )

    if open_conditions or absent:
        verdict = MATERIAL_MITIGATION_REQUIRED
    else:
        verdict = MATERIAL_ACCEPTED
    return {
        "kind": kind,
        "conditions_met": met,
        "conditions_open": open_conditions,
        "conditions_absent": absent,
        "verdict": verdict,
        "findings": findings,
    }


def assess_outgassing(outgassing, policy=None):
    """Compare declared mass loss and condensable material with the limits."""
    settings = resolve_policy(policy)
    _require_mapping("outgassing", outgassing)

    tml = outgassing.get("total_mass_loss_percent")
    cvcm = outgassing.get("collected_volatile_percent")
    if tml is None or cvcm is None:
        return {
            "total_mass_loss_percent": None,
            "collected_volatile_percent": None,
            "mass_loss_margin_percent": None,
            "volatile_margin_percent": None,
            "verdict": MATERIAL_MITIGATION_REQUIRED,
            "findings": [
                "no vacuum outgassing data declared, so neither limit can be "
                "shown met"
            ],
        }

    tml_value = _require_number("total_mass_loss_percent", tml)
    cvcm_value = _require_number("collected_volatile_percent", cvcm)
    tml_limit = settings["max_total_mass_loss_percent"]
    cvcm_limit = settings["max_collected_volatile_percent"]

    findings = []
    tml_ok = _at_most(tml_value, tml_limit)
    cvcm_ok = _at_most(cvcm_value, cvcm_limit)
    if not tml_ok:
        findings.append(
            "total mass loss %.4g%% against a declared %.4g%% limit"
            % (tml_value, tml_limit)
        )
    if not cvcm_ok:
        findings.append(
            "collected volatile condensable material %.4g%% against a declared "
            "%.4g%% limit" % (cvcm_value, cvcm_limit)
        )
    return {
        "total_mass_loss_percent": tml_value,
        "collected_volatile_percent": cvcm_value,
        "mass_loss_margin_percent": tml_limit - tml_value,
        "volatile_margin_percent": cvcm_limit - cvcm_value,
        "verdict": MATERIAL_ACCEPTED
        if tml_ok and cvcm_ok
        else MATERIAL_PROHIBITED,
        "findings": findings,
    }


def assess_part_construction(part):
    """Full clause 4.2.2.2 screen over one part's declared construction."""
    _require_mapping("part", part)
    part_id = _require_label("part_id", part.get("part_id"))
    settings = resolve_policy(part.get("policy"))

    finishes = part.get("finishes")
    if not isinstance(finishes, (list, tuple)) or not finishes:
        raise ValueError("part must carry a non-empty finishes sequence")

    seen = set()
    finish_results = []
    for finish in finishes:
        result = assess_finish(finish, settings)
        if result["surface"] in seen:
            raise ValueError(
                "surface %r is declared twice on one part" % result["surface"]
            )
        seen.add(result["surface"])
        finish_results.append(result)

    encapsulation = assess_encapsulation(part.get("encapsulation") or {}, settings)
    outgassing = assess_outgassing(part.get("outgassing") or {}, settings)

    findings = []
    for result in finish_results:
        findings.extend("%s: %s" % (part_id, f) for f in result["findings"])
    findings.extend("%s: %s" % (part_id, f) for f in encapsulation["findings"])
    findings.extend("%s: %s" % (part_id, f) for f in outgassing["findings"])

    axes = [r["verdict"] for r in finish_results]
    axes.append(encapsulation["verdict"])
    axes.append(outgassing["verdict"])
    worst = min(axes, key=lambda v: MATERIAL_RANK[v])

    grouped = {}
    for result in finish_results:
        grouped.setdefault(result["verdict"], []).append(result["surface"])
    for names in grouped.values():
        names.sort()

    mitigations_owed = sorted(
        result["surface"]
        for result in finish_results
        if result["verdict"] == MATERIAL_MITIGATION_REQUIRED
    )
    return {
        "part_id": part_id,
        "finishes": finish_results,
        "encapsulation": encapsulation,
        "outgassing": outgassing,
        "grouped_surfaces": grouped,
        "mitigations_owed": mitigations_owed,
        "worst_axis": worst,
        "verdict": CONSTRUCTION_BY_RANK[worst],
        "findings": findings,
    }
