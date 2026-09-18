#!/usr/bin/env python3
"""Assembly review item for a microwave die design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The review item asks one question about the die that is otherwise only
asked about the circuit: how does this piece of semiconductor become
part of a module. Three physical chains carry the answer.

Attach chain
    The die sits on a carrier through an attach medium. Die and carrier
    expand at different rates, so every temperature excursion loads the
    medium. Each medium absorbs a different amount of that free
    expansion mismatch before the joint needs a stress case of its own.

Thermal chain
    The same attach medium is the heat path. Its thickness, its
    conductivity and the attached footprint set a junction-to-case
    resistance, and the dissipated power turns that resistance into a
    junction temperature that has to sit under a derated limit.

Interconnect chain
    Bias and radio-frequency currents leave the die through bond wires.
    Each wire carries a derated share, so the current demand fixes a
    minimum wire count that the layout has to provide.

An item closes only when all three chains are answered and the host
module integration is defined.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIE_ATTACH_METHODS = (
    "eutectic-die-attach",
    "solder-die-attach",
    "conductive-epoxy-die-attach",
    "adhesive-film-die-attach",
)

# Free expansion mismatch, in parts per million of the die span, that each
# attach medium is taken to absorb before the review owes a joint stress
# case. A declared project value may replace this table.
ATTACH_MISMATCH_ALLOWANCE_PPM = {
    "eutectic-die-attach": 300.0,
    "solder-die-attach": 900.0,
    "conductive-epoxy-die-attach": 2500.0,
    "adhesive-film-die-attach": 3500.0,
}

INTEGRATION_STATES = (
    "module-integration-defined",
    "module-integration-partial",
    "module-integration-undefined",
)

VERDICT_CLOSED = "assembly-item-closed"
VERDICT_ACTIONED = "assembly-item-open-with-actions"
VERDICT_REJECTED = "assembly-item-rejected"

DEFAULT_DERATING_MARGIN_K = 20.0
CAUTION_MARGIN_K = 10.0

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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def expansion_mismatch_ppm(die_cte_ppm_per_k, carrier_cte_ppm_per_k, delta_t_k):
    """Free expansion mismatch the attach medium has to absorb.

    Both expansion coefficients are properties, so either may be the
    larger one; only the magnitude of the difference loads the joint.
    """
    die_cte = _require_non_negative("die_cte_ppm_per_k", die_cte_ppm_per_k)
    carrier_cte = _require_non_negative("carrier_cte_ppm_per_k", carrier_cte_ppm_per_k)
    swing = _require_positive("delta_t_k", delta_t_k)
    return abs(die_cte - carrier_cte) * swing


def attach_mismatch_allowance_ppm(die_attach_method, allowances=None):
    """Mismatch the declared attach medium is credited with absorbing."""
    _require_choice("die_attach_method", die_attach_method, DIE_ATTACH_METHODS)
    table = ATTACH_MISMATCH_ALLOWANCE_PPM if allowances is None else allowances
    if not isinstance(table, dict):
        raise ValueError("allowances must be a mapping, got %r" % (table,))
    missing = set(DIE_ATTACH_METHODS) - set(table)
    if missing:
        raise ValueError(
            "allowances is missing entries: %s" % ", ".join(sorted(missing))
        )
    return _require_positive(
        "allowance for %s" % die_attach_method, table[die_attach_method]
    )


def assess_attach_stress(
    die_attach_method,
    die_cte_ppm_per_k,
    carrier_cte_ppm_per_k,
    delta_t_k,
    joint_stress_analysis_ref=None,
    allowances=None,
):
    """Decide whether the attach chain is answered by the data in hand."""
    mismatch = expansion_mismatch_ppm(
        die_cte_ppm_per_k, carrier_cte_ppm_per_k, delta_t_k
    )
    allowance = attach_mismatch_allowance_ppm(die_attach_method, allowances)
    within = _at_most(mismatch, allowance)
    findings = []
    if within:
        status = "attach-mismatch-within-allowance"
    elif joint_stress_analysis_ref:
        status = "attach-mismatch-covered-by-analysis"
        findings.append(
            "mismatch %.1f ppm exceeds the %.1f ppm credited to %s; the joint "
            "stress case %s is the only thing holding the item"
            % (mismatch, allowance, die_attach_method, joint_stress_analysis_ref)
        )
    else:
        status = "attach-mismatch-unsupported"
        findings.append(
            "mismatch %.1f ppm exceeds the %.1f ppm credited to %s and no joint "
            "stress case is referenced"
            % (mismatch, allowance, die_attach_method)
        )
    return {
        "status": status,
        "mismatch_ppm": mismatch,
        "allowance_ppm": allowance,
        "within_allowance": within,
        "findings": findings,
    }


def die_attach_thermal_resistance_k_per_w(
    bondline_thickness_m, conductivity_w_per_m_k, attached_area_m2
):
    """Junction-to-case resistance contributed by the attach medium."""
    thickness = _require_positive("bondline_thickness_m", bondline_thickness_m)
    conductivity = _require_positive(
        "conductivity_w_per_m_k", conductivity_w_per_m_k
    )
    area = _require_positive("attached_area_m2", attached_area_m2)
    return thickness / (conductivity * area)


def junction_temperature_c(case_temperature_c, dissipated_power_w, rth_k_per_w):
    """Junction temperature the dissipated power drives through the path."""
    case = _require_number("case_temperature_c", case_temperature_c)
    power = _require_non_negative("dissipated_power_w", dissipated_power_w)
    rth = _require_positive("rth_k_per_w", rth_k_per_w)
    return case + power * rth


def derated_junction_limit_c(rated_max_junction_c, derating_margin_k=None):
    """Junction limit after the programme derating is taken off the rating."""
    rated = _require_number("rated_max_junction_c", rated_max_junction_c)
    margin = (
        DEFAULT_DERATING_MARGIN_K
        if derating_margin_k is None
        else _require_non_negative("derating_margin_k", derating_margin_k)
    )
    return rated - margin


def assess_thermal_path(
    case_temperature_c,
    dissipated_power_w,
    bondline_thickness_m,
    conductivity_w_per_m_k,
    attached_area_m2,
    rated_max_junction_c,
    derating_margin_k=None,
    spreading_rth_k_per_w=0.0,
):
    """Decide whether the thermal chain closes with margin to spare."""
    attach_rth = die_attach_thermal_resistance_k_per_w(
        bondline_thickness_m, conductivity_w_per_m_k, attached_area_m2
    )
    spreading = _require_non_negative("spreading_rth_k_per_w", spreading_rth_k_per_w)
    total_rth = attach_rth + spreading
    junction = junction_temperature_c(
        case_temperature_c, dissipated_power_w, total_rth
    )
    limit = derated_junction_limit_c(rated_max_junction_c, derating_margin_k)
    margin = limit - junction
    findings = []
    if margin < 0.0 and not _close(margin, 0.0):
        status = "junction-over-derated-limit"
        findings.append(
            "junction reaches %.1f C against a derated limit of %.1f C"
            % (junction, limit)
        )
    elif margin < CAUTION_MARGIN_K and not _close(margin, CAUTION_MARGIN_K):
        status = "junction-margin-thin"
        findings.append(
            "junction margin is only %.1f K; the attach bondline dominates the "
            "path at %.2f K/W" % (margin, attach_rth)
        )
    else:
        status = "junction-margin-adequate"
    return {
        "status": status,
        "attach_rth_k_per_w": attach_rth,
        "total_rth_k_per_w": total_rth,
        "junction_temperature_c": junction,
        "derated_limit_c": limit,
        "margin_k": margin,
        "findings": findings,
    }


def bond_wire_count_required(total_current_a, per_wire_rating_a, derating_factor=0.5):
    """Wires the current demand forces once each wire is derated."""
    current = _require_non_negative("total_current_a", total_current_a)
    rating = _require_positive("per_wire_rating_a", per_wire_rating_a)
    factor = _require_positive("derating_factor", derating_factor)
    if factor > 1.0 and not _close(factor, 1.0):
        raise ValueError("derating_factor must not exceed one, got %r" % (factor,))
    if current == 0.0:
        return 0
    allowable = rating * factor
    exact = current / allowable
    rounded = round(exact)
    if rounded >= 1 and _close(exact, float(rounded)):
        return int(rounded)
    return int(math.ceil(exact))


def assess_interconnect(
    total_current_a, per_wire_rating_a, provided_wire_count, derating_factor=0.5
):
    """Decide whether the interconnect chain carries the declared current."""
    required = bond_wire_count_required(
        total_current_a, per_wire_rating_a, derating_factor
    )
    if not isinstance(provided_wire_count, int) or isinstance(
        provided_wire_count, bool
    ):
        raise ValueError(
            "provided_wire_count must be an integer, got %r" % (provided_wire_count,)
        )
    if provided_wire_count < 0:
        raise ValueError(
            "provided_wire_count must not be negative, got %r"
            % (provided_wire_count,)
        )
    findings = []
    if provided_wire_count < required:
        status = "interconnect-under-provisioned"
        findings.append(
            "layout shows %d wires against the %d the derated current demands"
            % (provided_wire_count, required)
        )
    elif provided_wire_count == required and required > 0:
        status = "interconnect-without-spare"
        findings.append(
            "wire count sits exactly on the demand with no redundant wire for a "
            "lifted bond"
        )
    else:
        status = "interconnect-adequate"
    return {
        "status": status,
        "required_wire_count": required,
        "provided_wire_count": provided_wire_count,
        "findings": findings,
    }


def review_assembly_item(case, allowances=None):
    """Full clause 7.3.9 assembly review item with a closure verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    integration_state = _require_choice(
        "integration_state", case.get("integration_state"), INTEGRATION_STATES
    )
    attach = assess_attach_stress(
        _require_choice(
            "die_attach_method", case.get("die_attach_method"), DIE_ATTACH_METHODS
        ),
        case.get("die_cte_ppm_per_k"),
        case.get("carrier_cte_ppm_per_k"),
        case.get("delta_t_k"),
        case.get("joint_stress_analysis_ref"),
        allowances,
    )
    thermal = assess_thermal_path(
        case.get("case_temperature_c"),
        case.get("dissipated_power_w"),
        case.get("bondline_thickness_m"),
        case.get("conductivity_w_per_m_k"),
        case.get("attached_area_m2"),
        case.get("rated_max_junction_c"),
        case.get("derating_margin_k"),
        case.get("spreading_rth_k_per_w", 0.0),
    )
    interconnect = assess_interconnect(
        case.get("total_current_a"),
        case.get("per_wire_rating_a"),
        case.get("provided_wire_count"),
        case.get("derating_factor", 0.5),
    )
    findings = (
        list(attach["findings"])
        + list(thermal["findings"])
        + list(interconnect["findings"])
    )
    actions = []
    blocking = (
        attach["status"] == "attach-mismatch-unsupported"
        or thermal["status"] == "junction-over-derated-limit"
        or interconnect["status"] == "interconnect-under-provisioned"
    )
    if integration_state == "module-integration-undefined":
        blocking = True
        findings.append(
            "the host module integration is not defined, so the assembly data "
            "cannot be reviewed against anything"
        )
    if integration_state == "module-integration-partial":
        actions.append("complete the host module integration definition")
    if attach["status"] == "attach-mismatch-covered-by-analysis":
        actions.append("carry the joint stress case into the qualification evidence")
    if thermal["status"] == "junction-margin-thin":
        actions.append("reduce the bondline or widen the attached footprint")
    if interconnect["status"] == "interconnect-without-spare":
        actions.append("add a redundant bond wire on the highest current pad")
    if blocking:
        verdict = VERDICT_REJECTED
    elif actions:
        verdict = VERDICT_ACTIONED
    else:
        verdict = VERDICT_CLOSED
    return {
        "verdict": verdict,
        "integration_state": integration_state,
        "attach": attach,
        "thermal": thermal,
        "interconnect": interconnect,
        "actions": actions,
        "findings": findings,
    }
