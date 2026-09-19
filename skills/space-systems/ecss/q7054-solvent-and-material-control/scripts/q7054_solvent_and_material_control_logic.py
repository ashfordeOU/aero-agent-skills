#!/usr/bin/env python3
"""Control of solvents and cleaning agents used for ultracleaning.

Anchor: ECSS-Q-ST-70-54C methods clause, agent control. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

A cleaning agent is the last thing to touch an ultraclean surface, so
whatever the agent carries is what the surface ends up wearing. Three
properties govern whether an agent may be used:

    purity        the residue left behind when the agent evaporates,
                  declared as a grade and evidenced by a batch
                  certificate figure in milligram per litre.

    residue       what that concentration actually deposits on the
                  hardware. The concentration alone says nothing: the
                  same fluid leaves ten times the residue when ten times
                  the volume is drained over the same area, so the
                  deposition is computed from volume and wetted area and
                  then graded against the surface allowance.

    compatibility what the agent does to the substrate. A prohibited
                  pairing is not traded against cleaning performance,
                  and a restricted pairing carries its control into the
                  procedure rather than into a note nobody reads.

The deposition arithmetic is the part that is usually skipped. An
electronic-grade solvent is not automatically clean enough; it is clean
enough for a stated volume over a stated area, and changing either one
changes the answer.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Declared purity grades and the residue-on-evaporation each one bounds,
# in milligram per litre of agent.
PURITY_GRADES = (
    ("technical", 50.0),
    ("reagent", 5.0),
    ("electronic", 1.0),
    ("semiconductor", 0.10),
    ("ultrapure", 0.01),
)

AGENT_FAMILIES = (
    "chlorinated-solvent",
    "hydrocarbon-solvent",
    "alcohol",
    "ketone",
    "fluorinated-solvent",
    "aqueous-neutral-detergent",
    "aqueous-alkaline-detergent",
)

SUBSTRATES = (
    "aluminium-alloy",
    "stainless-steel",
    "titanium-alloy",
    "magnesium-alloy",
    "polymer-composite",
    "optical-glass",
    "silver-coating",
    "gold-coating",
)

COMPATIBLE = "compatible"
RESTRICTED = "restricted"
PROHIBITED = "prohibited"

# Pairings that are not simply compatible. Everything absent is compatible.
COMPATIBILITY_EXCEPTIONS = {
    ("chlorinated-solvent", "titanium-alloy"): (
        PROHIBITED,
        "chlorinated residue on a stressed titanium surface risks stress "
        "corrosion cracking; no rinse regime makes the pairing acceptable",
    ),
    ("chlorinated-solvent", "polymer-composite"): (
        PROHIBITED,
        "the matrix absorbs the solvent and swells; the absorbed fraction "
        "outgasses later and the mechanical properties do not recover",
    ),
    ("ketone", "polymer-composite"): (
        PROHIBITED,
        "ketones craze thermoplastic matrices and soften a partially cured "
        "thermoset",
    ),
    ("hydrocarbon-solvent", "polymer-composite"): (
        RESTRICTED,
        "absorption into the matrix is slow but real; limit contact time and "
        "bake out before any residue measurement",
    ),
    ("aqueous-alkaline-detergent", "magnesium-alloy"): (
        PROHIBITED,
        "alkaline attack on magnesium is rapid and leaves a loose corrosion "
        "product that no rinse removes",
    ),
    ("aqueous-alkaline-detergent", "aluminium-alloy"): (
        RESTRICTED,
        "alkaline etching of aluminium is time and temperature dependent; "
        "carry an inhibited bath with a bounded immersion time",
    ),
    ("aqueous-alkaline-detergent", "optical-glass"): (
        RESTRICTED,
        "alkaline chemistry leaches an optical surface; hold the pH and the "
        "contact time inside the qualified window",
    ),
    ("aqueous-neutral-detergent", "magnesium-alloy"): (
        RESTRICTED,
        "any aqueous route on magnesium needs an immediate dry; do not allow "
        "the surface to stand wet",
    ),
    ("alcohol", "silver-coating"): (
        RESTRICTED,
        "alcohol carries dissolved sulphur species that tarnish silver; use a "
        "certified low-sulphur batch",
    ),
}

QUALIFIED = "qualified"
QUALIFIED_WITH_RESTRICTION = "qualified-with-restriction"
REJECTED = "rejected"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, with an exact landing on the limit read as met."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def grade_residue_limit(grade):
    """Residue-on-evaporation bound a declared purity grade carries."""
    for name, limit in PURITY_GRADES:
        if name == grade:
            return limit
    raise ValueError(
        "purity grade must be one of %s, got %r"
        % (", ".join(name for name, _ in PURITY_GRADES), grade)
    )


def deposited_nvr_mg_per_01m2(residue_mg_per_l, wetted_volume_l, wetted_area_m2):
    """Residue the agent leaves on the hardware, per 0.1 square metre.

    Concentration alone decides nothing: the deposition scales with the
    volume drained over the surface and falls with the area it is spread
    across.
    """
    residue = _require_positive("residue_mg_per_l", residue_mg_per_l)
    volume = _require_positive("wetted_volume_l", wetted_volume_l)
    area = _require_positive("wetted_area_m2", wetted_area_m2)
    return residue * volume * 0.1 / area


def permissible_residue_mg_per_l(allowance_mg_per_01m2, wetted_volume_l, wetted_area_m2):
    """Highest agent residue concentration the surface allowance tolerates."""
    allowance = _require_positive("allowance_mg_per_01m2", allowance_mg_per_01m2)
    volume = _require_positive("wetted_volume_l", wetted_volume_l)
    area = _require_positive("wetted_area_m2", wetted_area_m2)
    return allowance * area / (volume * 0.1)


def minimum_purity_grade(allowance_mg_per_01m2, wetted_volume_l, wetted_area_m2):
    """Least stringent grade whose bound still meets the allowance.

    Reaching past it buys margin at a cost; falling short of it cannot be
    recovered by procedure.
    """
    permissible = permissible_residue_mg_per_l(
        allowance_mg_per_01m2, wetted_volume_l, wetted_area_m2
    )
    sufficient = [
        (name, limit) for name, limit in PURITY_GRADES if _at_most(limit, permissible)
    ]
    if not sufficient:
        raise ValueError(
            "no tabulated purity grade meets %g mg per litre; reduce the wetted "
            "volume, increase the spread area, or qualify a purer agent"
            % permissible
        )
    return max(sufficient, key=lambda pair: pair[1])[0]


def compatibility_verdict(agent_family, substrate):
    """What the agent does to the substrate, and the control it implies."""
    family = _require_choice("agent_family", agent_family, AGENT_FAMILIES)
    material = _require_choice("substrate", substrate, SUBSTRATES)
    verdict, reason = COMPATIBILITY_EXCEPTIONS.get(
        (family, material),
        (COMPATIBLE, "no adverse interaction catalogued for this pairing"),
    )
    return {"verdict": verdict, "reason": reason, "pairing": (family, material)}


def validate_agent(agent):
    """Check an agent declaration carries a family, a grade and a certificate."""
    if not isinstance(agent, dict):
        raise ValueError("agent must be a mapping, got %r" % (agent,))
    family = _require_choice("agent_family", agent.get("agent_family"), AGENT_FAMILIES)
    grade = agent.get("declared_grade")
    limit = grade_residue_limit(grade)
    measured = _require_positive(
        "certificate_residue_mg_per_l", agent.get("certificate_residue_mg_per_l")
    )
    return {
        "agent_family": family,
        "declared_grade": grade,
        "grade_residue_limit_mg_per_l": limit,
        "certificate_residue_mg_per_l": measured,
    }


def validate_use(use):
    """Check the use describes a real wetted volume, area and allowance."""
    if not isinstance(use, dict):
        raise ValueError("use must be a mapping, got %r" % (use,))
    substrate = _require_choice("substrate", use.get("substrate"), SUBSTRATES)
    volume = _require_positive("wetted_volume_l", use.get("wetted_volume_l"))
    area = _require_positive("wetted_area_m2", use.get("wetted_area_m2"))
    allowance = _require_positive(
        "surface_allowance_mg_per_01m2", use.get("surface_allowance_mg_per_01m2")
    )
    return {
        "substrate": substrate,
        "wetted_volume_l": volume,
        "wetted_area_m2": area,
        "surface_allowance_mg_per_01m2": allowance,
    }


def qualify_cleaning_agent(agent, use):
    """Full agent control decision: purity, deposited residue, compatibility."""
    checked_agent = validate_agent(agent)
    checked_use = validate_use(use)
    findings = []
    restrictions = []

    certificate_supports_grade = _at_most(
        checked_agent["certificate_residue_mg_per_l"],
        checked_agent["grade_residue_limit_mg_per_l"],
    )
    if not certificate_supports_grade:
        findings.append(
            "batch certificate reports %g mg per litre against a %s bound of "
            "%g; the declared grade is not evidenced"
            % (
                checked_agent["certificate_residue_mg_per_l"],
                checked_agent["declared_grade"],
                checked_agent["grade_residue_limit_mg_per_l"],
            )
        )

    deposited = deposited_nvr_mg_per_01m2(
        checked_agent["certificate_residue_mg_per_l"],
        checked_use["wetted_volume_l"],
        checked_use["wetted_area_m2"],
    )
    residue_within_allowance = _at_most(
        deposited, checked_use["surface_allowance_mg_per_01m2"]
    )
    if not residue_within_allowance:
        findings.append(
            "the agent deposits %.4g mg per 0.1 m2 against an allowance of "
            "%.4g; reduce the drained volume, spread it over more area, or "
            "move up a purity grade"
            % (deposited, checked_use["surface_allowance_mg_per_01m2"])
        )

    compatibility = compatibility_verdict(
        checked_agent["agent_family"], checked_use["substrate"]
    )
    if compatibility["verdict"] == PROHIBITED:
        findings.append(
            "pairing %s with %s is prohibited: %s"
            % (
                checked_agent["agent_family"],
                checked_use["substrate"],
                compatibility["reason"],
            )
        )
    elif compatibility["verdict"] == RESTRICTED:
        restrictions.append(compatibility["reason"])

    if (
        certificate_supports_grade
        and residue_within_allowance
        and compatibility["verdict"] != PROHIBITED
    ):
        verdict = QUALIFIED_WITH_RESTRICTION if restrictions else QUALIFIED
    else:
        verdict = REJECTED

    return {
        "verdict": verdict,
        "agent": checked_agent,
        "use": checked_use,
        "deposited_nvr_mg_per_01m2": deposited,
        "permissible_residue_mg_per_l": permissible_residue_mg_per_l(
            checked_use["surface_allowance_mg_per_01m2"],
            checked_use["wetted_volume_l"],
            checked_use["wetted_area_m2"],
        ),
        "compatibility": compatibility,
        "restrictions": restrictions,
        "findings": findings,
    }
