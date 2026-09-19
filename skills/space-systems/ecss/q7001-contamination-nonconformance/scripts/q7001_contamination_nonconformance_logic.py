#!/usr/bin/env python3
"""Disposition of a contamination nonconformance: impact, re-clean, re-verify.

Anchor: ECSS-Q-ST-70-01C, nonconformance handling for cleanliness. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A measured level over the cleanliness limit is an input, not a
verdict. What decides the case is the performance the deposit costs,
reached from the measured level through a declared surface
sensitivity: a transmittance loss on an optical path, an absorptance
rise on a radiator, a contact resistance on a mating surface.

Re-cleaning is bounded. Every cycle works the surface, so coatings and
optical finishes carry a cycle budget. And a case whose penalty
computed at the limit already exceeds the performance allowance cannot
be cleaned out of at all -- cleaning back to the limit still leaves
the item unacceptable, which makes it a requirement or design matter.

All arithmetic is multiply-and-divide on the declared sensitivity, so
the result is identical on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

MOLECULAR = "molecular"
PARTICULATE = "particulate"
CONTAMINANT_KINDS = (MOLECULAR, PARTICULATE)

UNITS = {
    MOLECULAR: "mg/m2",
    PARTICULATE: "percent-area-coverage",
}

CRITICALITY_CRITICAL = "contamination-critical"
CRITICALITY_SENSITIVE = "contamination-sensitive"
CRITICALITY_STANDARD = "standard"

CRITICALITY_LEVELS = (
    CRITICALITY_CRITICAL,
    CRITICALITY_SENSITIVE,
    CRITICALITY_STANDARD,
)

# Re-verification that can actually see the contaminant in question.
REVERIFICATION_METHODS = {
    MOLECULAR: ("solvent-rinse-gravimetric-residue", "witness-plate-residue-reading"),
    PARTICULATE: ("tape-lift-obscuration-count", "witness-plate-particle-count"),
}

# Additional method the most sensitive hardware owes.
CRITICAL_EXTRA_METHOD = {
    MOLECULAR: "direct-surface-spectroscopic-reading",
    PARTICULATE: "direct-surface-obscuration-imaging",
}

# Exceedance ratio up to which use-as-is may be considered at all.
MINOR_EXCEEDANCE_RATIO = 1.25

SEVERITY_NONE = "within-limit"
SEVERITY_MINOR = "minor-exceedance"
SEVERITY_MAJOR = "major-exceedance"

DISPOSITION_NO_ACTION = "no-action-required"
DISPOSITION_USE_AS_IS = "use-as-is-under-concession"
DISPOSITION_RECLEAN = "re-clean-and-re-verify"
DISPOSITION_ESCALATE = "escalate-to-nonconformance-board"

TOL = 1e-9


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_number(name, value, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %s, got %r" % (name, minimum, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def contaminant_unit(kind):
    """Unit the level is quoted in; the two ledgers never convert."""
    _require_choice("kind", kind, CONTAMINANT_KINDS)
    return UNITS[kind]


def exceedance(measured, limit):
    """Overrun against the limit, with a level on the limit read as compliant."""
    level = _require_number("measured", measured, minimum=0.0)
    cap = _require_number("limit", limit, minimum=0.0)
    if cap <= 0.0:
        raise ValueError("limit must be greater than zero, got %r" % (limit,))
    over = level - cap
    return {
        "measured": level,
        "limit": cap,
        "over_by": over if over > TOL else 0.0,
        "ratio": level / cap,
        "exceeded": over > TOL,
    }


def performance_penalty(measured, sensitivity, allowance, limit):
    """Function cost of the deposit, and the part of it cleaning can recover."""
    level = _require_number("measured", measured, minimum=0.0)
    slope = _require_number("sensitivity", sensitivity, minimum=0.0)
    allowed = _require_number("allowance", allowance, minimum=0.0)
    cap = _require_number("limit", limit, minimum=0.0)
    at_measured = slope * level
    at_limit = slope * cap
    return {
        "sensitivity": slope,
        "allowance": allowed,
        "penalty_at_measured": at_measured,
        "penalty_at_limit": at_limit,
        "recoverable_penalty": at_measured - at_limit,
        "margin_at_measured": allowed - at_measured,
        "margin_at_limit": allowed - at_limit,
        "within_allowance": at_measured <= allowed + TOL,
        "recoverable_by_cleaning": at_limit <= allowed + TOL,
    }


def severity_of(exceedance_result, penalty_result):
    """Severity from the overrun ratio and whether the penalty still fits."""
    if not exceedance_result["exceeded"]:
        return SEVERITY_NONE
    if exceedance_result["ratio"] > MINOR_EXCEEDANCE_RATIO + TOL:
        return SEVERITY_MAJOR
    if not penalty_result["within_allowance"]:
        return SEVERITY_MAJOR
    return SEVERITY_MINOR


def reclean_budget(cycles_used, max_cycles):
    """Cycles the substrate and finish still permit on this item."""
    used = _require_count("cycles_used", cycles_used, minimum=0)
    allowed = _require_count("max_cycles", max_cycles, minimum=0)
    if used > allowed:
        raise ValueError(
            "cycles_used (%d) exceeds max_cycles (%d); the item is already past "
            "its cleaning budget" % (used, allowed)
        )
    return {
        "cycles_used": used,
        "max_cycles": allowed,
        "cycles_remaining": allowed - used,
        "cycles_available": allowed - used > 0,
    }


def reverification_methods(kind, criticality):
    """Methods that can see this contaminant at this criticality."""
    _require_choice("kind", kind, CONTAMINANT_KINDS)
    _require_choice("criticality", criticality, CRITICALITY_LEVELS)
    methods = list(REVERIFICATION_METHODS[kind])
    if criticality == CRITICALITY_CRITICAL:
        methods.append(CRITICAL_EXTRA_METHOD[kind])
    return tuple(methods)


def required_records(disposition):
    """Records the chosen route owes behind it."""
    _require_choice(
        "disposition",
        disposition,
        (
            DISPOSITION_NO_ACTION,
            DISPOSITION_USE_AS_IS,
            DISPOSITION_RECLEAN,
            DISPOSITION_ESCALATE,
        ),
    )
    base = ["contamination-nonconformance-report"]
    if disposition == DISPOSITION_USE_AS_IS:
        base.extend(
            ["cleanliness-concession-approval", "as-built-cleanliness-record"]
        )
    elif disposition == DISPOSITION_RECLEAN:
        base.extend(
            [
                "cleaning-procedure-record",
                "re-verification-measurement-record",
                "cleaning-cycle-count-update",
            ]
        )
    elif disposition == DISPOSITION_ESCALATE:
        base.extend(
            ["performance-impact-analysis", "nonconformance-board-minutes"]
        )
    return tuple(base)


def handle_contamination_nonconformance(case):
    """Full disposition decision for one contamination nonconformance."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    item = _require_text("item", case.get("item"))
    kind = case.get("kind")
    unit = contaminant_unit(kind)
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITY_LEVELS
    )
    over = exceedance(case.get("measured"), case.get("limit"))
    penalty = performance_penalty(
        case.get("measured"),
        case.get("sensitivity"),
        case.get("allowance"),
        case.get("limit"),
    )
    budget = reclean_budget(
        case.get("cycles_used", 0), case.get("max_cycles", 0)
    )
    severity = severity_of(over, penalty)
    rationale = []
    if not over["exceeded"] and penalty["within_allowance"]:
        disposition = DISPOSITION_NO_ACTION
        rationale.append(
            "measured %.6g %s is within the limit of %.6g %s"
            % (over["measured"], unit, over["limit"], unit)
        )
    elif not penalty["recoverable_by_cleaning"]:
        disposition = DISPOSITION_ESCALATE
        rationale.append(
            "cleaning back to the limit still costs %.6g against an allowance of "
            "%.6g, so the case is a requirement or design matter"
            % (penalty["penalty_at_limit"], penalty["allowance"])
        )
    elif severity == SEVERITY_MINOR and penalty["within_allowance"]:
        disposition = DISPOSITION_USE_AS_IS
        rationale.append(
            "overrun of %.6g %s is %.4f of the limit and the penalty of %.6g still "
            "fits the allowance of %.6g"
            % (
                over["over_by"],
                unit,
                over["ratio"],
                penalty["penalty_at_measured"],
                penalty["allowance"],
            )
        )
    elif budget["cycles_available"]:
        disposition = DISPOSITION_RECLEAN
        rationale.append(
            "%d cleaning cycle(s) remain of %d, and cleaning to the limit recovers "
            "%.6g of penalty"
            % (
                budget["cycles_remaining"],
                budget["max_cycles"],
                penalty["recoverable_penalty"],
            )
        )
    else:
        disposition = DISPOSITION_ESCALATE
        rationale.append(
            "the cleaning budget of %d cycle(s) is spent, so no re-clean route "
            "remains" % budget["max_cycles"]
        )
    methods = (
        reverification_methods(kind, criticality)
        if disposition == DISPOSITION_RECLEAN
        else ()
    )
    return {
        "item": item,
        "kind": kind,
        "unit": unit,
        "criticality": criticality,
        "exceedance": over,
        "penalty": penalty,
        "reclean_budget": budget,
        "severity": severity,
        "disposition": disposition,
        "reverification_methods": methods,
        "required_records": required_records(disposition),
        "rationale": tuple(rationale),
        "board_required": disposition == DISPOSITION_ESCALATE
        or severity == SEVERITY_MAJOR,
    }
