#!/usr/bin/env python3
"""Method choice for infrared contamination measurement of hardware.

Anchor: ECSS-Q-ST-70-05C, the clauses covering the choice between the
available infrared measurement methods. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Applicability says which methods could work in principle. Selection is
the narrower question of which one this piece of hardware, in this
configuration, with this contaminant, can actually be measured by.

It is a gate and then a ranking, in that order. The gates are hard and
each carries a reason: can the surface be reached in the way the method
needs, does the substrate survive what the method does to it, and does
the solvent the method relies on actually dissolve the contaminant. A
candidate failing any gate is out, and no sensitivity argument brings it
back.

Only the survivors are ranked, and they are ranked on the margin between
the cleanliness level required and the detection limit the method
reaches. A method whose limit sits on the requirement has zero margin:
it is admissible and it is fragile, and the ranking says so by ordering
it last rather than by excluding it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIRECT_CONTACT_PROBE = "direct-contact-reflection-probe"
DIRECT_STANDOFF = "direct-standoff-reflection"
INDIRECT_WIPE = "indirect-solvent-wipe"
INDIRECT_RINSE = "indirect-solvent-rinse"
METHODS = (
    DIRECT_CONTACT_PROBE,
    DIRECT_STANDOFF,
    INDIRECT_WIPE,
    INDIRECT_RINSE,
)

ACCESS_OPEN = "open"
ACCESS_LINE_OF_SIGHT = "line-of-sight-only"
ACCESS_ENCLOSED = "enclosed"
ACCESS_CLASSES = (ACCESS_OPEN, ACCESS_LINE_OF_SIGHT, ACCESS_ENCLOSED)

# Which access classes each method can be performed under. A standoff
# reflection needs a sight line and nothing more; a wipe needs a hand on
# the surface; a rinse needs the surface to be open enough to flood and
# drain, or enclosed in a way that lets the solvent be recovered.
METHOD_ACCESS = {
    DIRECT_CONTACT_PROBE: (ACCESS_OPEN,),
    DIRECT_STANDOFF: (ACCESS_OPEN, ACCESS_LINE_OF_SIGHT),
    INDIRECT_WIPE: (ACCESS_OPEN,),
    INDIRECT_RINSE: (ACCESS_OPEN, ACCESS_ENCLOSED),
}

# Methods that put solvent on the hardware; a substrate that does not
# tolerate solvent rules these out whatever their sensitivity.
SOLVENT_METHODS = (INDIRECT_WIPE, INDIRECT_RINSE)

# Methods that touch the surface; a surface that must not be touched
# rules these out.
CONTACT_METHODS = (DIRECT_CONTACT_PROBE, INDIRECT_WIPE)

DEFAULT_SOLVENT_COMPATIBILITY = {
    "silicone": {"hexane": 0.9, "toluene": 0.95, "isopropanol": 0.15},
    "hydrocarbon-oil": {"hexane": 0.95, "isopropanol": 0.7, "toluene": 0.9},
    "ester-plasticizer": {"isopropanol": 0.85, "acetone": 0.9, "hexane": 0.4},
    "fluorinated-oil": {"hfe": 0.9, "hexane": 0.2, "isopropanol": 0.1},
}

DEFAULT_SELECTION_POLICY = {
    "min_recovery_fraction": 0.6,
    "min_sensitivity_margin": 0.0,
    "fragile_margin": 0.2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError("%s must sit in (0, 1], got %r" % (name, value))
    return number


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_selection_policy(policy):
    """Check a selection policy carries usable gates and thresholds."""
    _require_mapping("policy", policy)
    _require_fraction(
        "min_recovery_fraction", policy.get("min_recovery_fraction")
    )
    _require_number(
        "min_sensitivity_margin", policy.get("min_sensitivity_margin")
    )
    fragile = _require_number("fragile_margin", policy.get("fragile_margin"))
    if fragile < policy["min_sensitivity_margin"]:
        raise ValueError(
            "fragile_margin %g sits below min_sensitivity_margin %g, so no "
            "admissible method could ever be flagged fragile"
            % (fragile, policy["min_sensitivity_margin"])
        )
    return policy


def access_gate(method, access_class):
    """Whether the hardware can be reached the way the method needs."""
    if method not in METHODS:
        raise ValueError(
            "unknown method %r; declare it rather than assuming an access rule"
            % (method,)
        )
    if access_class not in ACCESS_CLASSES:
        raise ValueError(
            "access_class must be one of %s, got %r"
            % (", ".join(ACCESS_CLASSES), access_class)
        )
    allowed = METHOD_ACCESS[method]
    if access_class in allowed:
        return {"passed": True, "reason": None}
    return {
        "passed": False,
        "reason": "access is %s and the method needs one of %s"
        % (access_class, ", ".join(allowed)),
    }


def substrate_gate(method, solvent_tolerant, contact_permitted):
    """Whether the substrate survives what the method does to it."""
    if method not in METHODS:
        raise ValueError("unknown method %r" % (method,))
    tolerant = _require_bool("solvent_tolerant", solvent_tolerant)
    contact = _require_bool("contact_permitted", contact_permitted)
    if method in SOLVENT_METHODS and not tolerant:
        return {
            "passed": False,
            "reason": "the substrate does not tolerate solvent and the method "
            "wets it",
        }
    if method in CONTACT_METHODS and not contact:
        return {
            "passed": False,
            "reason": "the surface may not be touched and the method contacts it",
        }
    return {"passed": True, "reason": None}


def solvent_gate(
    method,
    contaminant_type,
    solvent,
    compatibility=DEFAULT_SOLVENT_COMPATIBILITY,
    policy=DEFAULT_SELECTION_POLICY,
):
    """Whether the chosen solvent actually takes the contaminant up."""
    validate_selection_policy(policy)
    _require_mapping("compatibility", compatibility)
    if method not in METHODS:
        raise ValueError("unknown method %r" % (method,))
    if method not in SOLVENT_METHODS:
        return {"passed": True, "reason": None, "recovery_fraction": None}
    if contaminant_type not in compatibility:
        raise ValueError(
            "no solvent compatibility data for contaminant type %r; obtain it "
            "rather than assuming a recovery" % (contaminant_type,)
        )
    table = compatibility[contaminant_type]
    if solvent not in table:
        raise ValueError(
            "no recovery datum for solvent %r against contaminant type %r"
            % (solvent, contaminant_type)
        )
    recovery = _require_fraction("recovery_fraction", table[solvent])
    if not _at_least(recovery, policy["min_recovery_fraction"]):
        return {
            "passed": False,
            "reason": "solvent %s recovers only %.2f of a %s contaminant against "
            "a required %.2f"
            % (solvent, recovery, contaminant_type, policy["min_recovery_fraction"]),
            "recovery_fraction": recovery,
        }
    return {"passed": True, "reason": None, "recovery_fraction": recovery}


def sensitivity_margin(detection_limit_ug_cm2, required_level_ug_cm2):
    """How much headroom a method's detection limit leaves on the requirement.

    A margin of zero means the limit sits exactly on the requirement:
    admissible, and with nothing left for a bad day.
    """
    limit = _require_positive("detection_limit_ug_cm2", detection_limit_ug_cm2)
    required = _require_positive(
        "required_level_ug_cm2", required_level_ug_cm2
    )
    return required / limit - 1.0


def evaluate_candidate(method, case, policy=DEFAULT_SELECTION_POLICY):
    """Run every gate against one method and measure its margin."""
    validate_selection_policy(policy)
    _require_mapping("case", case)
    if method not in METHODS:
        raise ValueError("unknown method %r" % (method,))
    limits = _require_mapping(
        "case detection_limits_ug_cm2", case.get("detection_limits_ug_cm2")
    )
    if method not in limits:
        raise ValueError(
            "case declares no detection limit for method %r" % (method,)
        )
    gates = {
        "access": access_gate(method, case.get("access_class")),
        "substrate": substrate_gate(
            method,
            case.get("solvent_tolerant"),
            case.get("contact_permitted"),
        ),
        "solvent": solvent_gate(
            method,
            case.get("contaminant_type"),
            case.get("solvent"),
            case.get("compatibility", DEFAULT_SOLVENT_COMPATIBILITY),
            policy,
        ),
    }
    blocked_by = tuple(
        sorted(name for name, gate in gates.items() if not gate["passed"])
    )
    margin = sensitivity_margin(
        limits[method], case.get("required_level_ug_cm2")
    )
    admissible = not blocked_by and _at_least(
        margin, policy["min_sensitivity_margin"]
    )
    if not blocked_by and not admissible:
        blocked_by = ("sensitivity",)
        gates["sensitivity"] = {
            "passed": False,
            "reason": "detection limit %.4g ug/cm2 leaves margin %.3f against a "
            "required %.3f"
            % (
                limits[method],
                margin,
                policy["min_sensitivity_margin"],
            ),
        }
    return {
        "method": method,
        "gates": gates,
        "blocked_by": blocked_by,
        "detection_limit_ug_cm2": limits[method],
        "sensitivity_margin": margin,
        "admissible": admissible,
        "fragile": admissible and not _at_least(margin, policy["fragile_margin"]),
    }


def rank_candidates(case, policy=DEFAULT_SELECTION_POLICY):
    """Every declared method, gated and then ordered by margin."""
    validate_selection_policy(policy)
    _require_mapping("case", case)
    limits = _require_mapping(
        "case detection_limits_ug_cm2", case.get("detection_limits_ug_cm2")
    )
    candidates = [
        evaluate_candidate(method, case, policy)
        for method in METHODS
        if method in limits
    ]
    if not candidates:
        raise ValueError(
            "the case declares a detection limit for no known method"
        )
    admissible = [c for c in candidates if c["admissible"]]
    admissible.sort(key=lambda c: (-c["sensitivity_margin"], c["method"]))
    rejected = [c for c in candidates if not c["admissible"]]
    rejected.sort(key=lambda c: c["method"])
    return {"admissible": admissible, "rejected": rejected}


def select_method(case, policy=DEFAULT_SELECTION_POLICY):
    """Retain one method for the measurement, with the reasons for the rest."""
    validate_selection_policy(policy)
    ranking = rank_candidates(case, policy)
    findings = []
    duties = []
    retained = ranking["admissible"][0] if ranking["admissible"] else None
    if retained is None:
        findings.append(
            "no method survives the access, substrate, solvent and sensitivity "
            "gates for this configuration; the measurement needs a design "
            "change or a witness plate rather than a different operator"
        )
    elif retained["fragile"]:
        findings.append(
            "the retained method %s clears the requirement by only %.3f, so a "
            "small loss of recovery or a dirtier blank puts the result under "
            "the limit" % (retained["method"], retained["sensitivity_margin"])
        )
    for candidate in ranking["rejected"]:
        for gate_name in candidate["blocked_by"]:
            findings.append(
                "%s is out on the %s gate: %s"
                % (
                    candidate["method"],
                    gate_name,
                    candidate["gates"][gate_name]["reason"],
                )
            )
    duties.append(
        "record the gate that excluded each method, not only the method kept; "
        "a later configuration change can reopen a gate"
    )
    if retained is not None and retained["gates"]["solvent"]["recovery_fraction"]:
        duties.append(
            "carry the solvent recovery fraction of %.2f into the quantitative "
            "result rather than reporting the extracted mass as the surface mass"
            % retained["gates"]["solvent"]["recovery_fraction"]
        )
    return {
        "retained": retained,
        "ranking": ranking,
        "duties": duties,
        "findings": findings,
        "selected": retained is not None,
    }
