#!/usr/bin/env python3
"""Budgeting the voltage lost between the bus and the load across a
protected distribution line, at the current the line's protection class
is rated for.

Anchor: ECSS-E-ST-20-20C clause 5.4.5.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The load does not see the bus. It sees the bus minus everything the
protection line takes on the way: the conducting element of the limiter,
the current-sense shunt it regulates on, the harness out and back, every
connector contact in the path, and any series blocking device. Each of
those is small. Their sum decides whether the load is inside its input
range at the end of the line, which is why the clause puts a ceiling on
the sum rather than on any one of them.

Three things decide the number and each of them is a place designs go
wrong:

    the current    the budget is evaluated at the current the protection
                   class is rated for, not at the load's quiet operating
                   point. A line sized on the operating current has no
                   budget left the moment the load does what its class
                   allows
    the temperature a copper path at the hot end of its range carries
                   noticeably more resistance than the same path on the
                   bench, so every resistive contributor is taken to its
                   hot value before it is summed
    the spread     parts are not their data-sheet typicals for ever, so
                   the summed drop carries a declared tolerance factor
                   before it meets the ceiling

Fixed drops and resistive drops do not behave alike. A junction's
forward voltage barely moves with current while a resistance scales with
it, so they are summed separately and reported separately: a line that
is dominated by a fixed drop is fixed by changing the part, and one
dominated by resistance is fixed by shortening or fattening the path.

The result is reported as a breakdown and not only as a total, grouped
by element kind, with the dominant contributor named. A budget that
fails tells the designer nothing; a budget that fails because two
connector contacts carry half of it tells the designer what to do.

The temperatures, tolerance factor and advisory floors below are a
declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ELEMENT_SWITCH = "limiter-switch-element"
ELEMENT_SENSE_SHUNT = "current-sense-shunt"
ELEMENT_HARNESS = "distribution-harness"
ELEMENT_CONNECTOR = "connector-contact"
ELEMENT_BLOCKING_DEVICE = "series-blocking-device"

ELEMENT_KINDS = (
    ELEMENT_SWITCH,
    ELEMENT_SENSE_SHUNT,
    ELEMENT_HARNESS,
    ELEMENT_CONNECTOR,
    ELEMENT_BLOCKING_DEVICE,
)

DROP_WITHIN_BUDGET = "line-voltage-drop-within-budget"
DROP_MARGIN_THIN = "line-voltage-drop-margin-thin"
DROP_EXCEEDS_BUDGET = "line-voltage-drop-exceeds-budget"

DROP_VERDICTS = (
    DROP_WITHIN_BUDGET,
    DROP_MARGIN_THIN,
    DROP_EXCEEDS_BUDGET,
)

DEFAULT_LINE_DROP_POLICY = {
    "hot_temperature_c": 70.0,
    "reference_temperature_c": 20.0,
    "tolerance_factor": 1.05,
    "thin_margin_fraction": 0.10,
    "dominant_share_fraction": 0.50,
}

COPPER_ALPHA_PER_K = 0.00393

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


def _require_unit_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number < 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or _close(value, bound)


def _at_most(value, bound):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or _close(value, bound)


def validate_line_drop_policy(policy):
    """Check a drop-budget policy is usable before any line is summed."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    hot_c = _require_number("hot_temperature_c", policy.get("hot_temperature_c"))
    reference_c = _require_number(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    if hot_c < reference_c and not _close(hot_c, reference_c):
        raise ValueError(
            "hot_temperature_c %r sits below reference_temperature_c %r, so the "
            "budget would be taken at a temperature that flatters it"
            % (hot_c, reference_c)
        )
    factor = _require_number("tolerance_factor", policy.get("tolerance_factor"))
    if not _at_least(factor, 1.0):
        raise ValueError(
            "tolerance_factor %r must be at least one; a factor below one "
            "shrinks the drop instead of covering its spread" % (factor,)
        )
    _require_unit_fraction("thin_margin_fraction", policy.get("thin_margin_fraction"))
    _require_unit_fraction(
        "dominant_share_fraction", policy.get("dominant_share_fraction")
    )
    return policy


def categorize_element_kind(kind):
    """Name a line element kind and refuse one the budget does not model."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("element kind must be a non-empty string, got %r" % (kind,))
    name = kind.strip()
    if name not in ELEMENT_KINDS:
        raise ValueError(
            "unrecognised element kind %r; known kinds are %s"
            % (name, ", ".join(ELEMENT_KINDS))
        )
    return name


def validate_class_table(table):
    """Check the protection class table the line takes its current from."""
    if not isinstance(table, (list, tuple)) or not table:
        raise ValueError("class table must be a non-empty sequence, got %r" % (table,))
    entries = []
    seen = set()
    for entry in table:
        if not isinstance(entry, dict):
            raise ValueError("class entry must be a mapping, got %r" % (entry,))
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("class entry is missing a non-empty name, got %r" % (name,))
        key = name.strip()
        if key in seen:
            raise ValueError("class named twice in the table: %r" % (key,))
        seen.add(key)
        current_a = _require_positive("class_current_a", entry.get("class_current_a"))
        record = {"name": key, "class_current_a": current_a}
        if "allowed_drop_v" in entry and entry["allowed_drop_v"] is not None:
            if "allowed_drop_fraction" in entry and (
                entry["allowed_drop_fraction"] is not None
            ):
                raise ValueError(
                    "class %r declares both an absolute allowed drop and a "
                    "fraction of the bus; exactly one of them is the budget"
                    % (key,)
                )
            record["allowed_drop_v"] = _require_positive(
                "allowed_drop_v", entry.get("allowed_drop_v")
            )
        elif "allowed_drop_fraction" in entry and (
            entry["allowed_drop_fraction"] is not None
        ):
            record["allowed_drop_fraction"] = _require_unit_fraction(
                "allowed_drop_fraction", entry.get("allowed_drop_fraction")
            )
        else:
            raise ValueError(
                "class %r declares no allowed drop, so there is no budget to "
                "grade the line against" % (key,)
            )
        entries.append(record)
    return tuple(entries)


def class_entry(table, class_name):
    """The class table row a line is assigned to."""
    entries = validate_class_table(table)
    if not isinstance(class_name, str) or not class_name.strip():
        raise ValueError("class_name must be a non-empty string, got %r" % (class_name,))
    wanted = class_name.strip()
    for entry in entries:
        if entry["name"] == wanted:
            return entry
    raise ValueError(
        "class %r is not in the table; the table holds %s"
        % (wanted, ", ".join(entry["name"] for entry in entries))
    )


def allowed_drop_v(entry, bus_voltage_v):
    """The ceiling the summed drop is graded against, absolute or fractional."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a class mapping, got %r" % (entry,))
    bus_v = _require_positive("bus_voltage_v", bus_voltage_v)
    if "allowed_drop_v" in entry:
        return _require_positive("allowed_drop_v", entry["allowed_drop_v"])
    if "allowed_drop_fraction" in entry:
        return bus_v * _require_unit_fraction(
            "allowed_drop_fraction", entry["allowed_drop_fraction"]
        )
    raise ValueError("class entry %r carries no allowed drop" % (entry,))


def hot_resistance_ohm(
    reference_resistance_ohm,
    alpha_per_k=COPPER_ALPHA_PER_K,
    policy=DEFAULT_LINE_DROP_POLICY,
):
    """A resistance taken from its reference temperature to the hot case."""
    validate_line_drop_policy(policy)
    reference_ohm = _require_non_negative(
        "reference_resistance_ohm", reference_resistance_ohm
    )
    alpha = _require_number("alpha_per_k", alpha_per_k)
    if alpha < 0.0:
        raise ValueError(
            "alpha_per_k %r must not be negative; a conductor that loses "
            "resistance when hot is not what this budget models" % (alpha_per_k,)
        )
    rise_k = float(policy["hot_temperature_c"]) - float(
        policy["reference_temperature_c"]
    )
    return reference_ohm * (1.0 + alpha * rise_k)


def contributor_drop(contributor, current_a, policy=DEFAULT_LINE_DROP_POLICY):
    """Resistive and fixed drop one element takes at the graded current."""
    validate_line_drop_policy(policy)
    if not isinstance(contributor, dict):
        raise ValueError("contributor must be a mapping, got %r" % (contributor,))
    identifier = contributor.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("contributor is missing a non-empty id, got %r" % (identifier,))
    kind = categorize_element_kind(contributor.get("kind"))
    current = _require_positive("current_a", current_a)

    reference_ohm = _require_non_negative(
        "resistance_ohm", contributor.get("resistance_ohm", 0.0)
    )
    fixed_v = _require_non_negative(
        "forward_drop_v", contributor.get("forward_drop_v", 0.0)
    )
    if reference_ohm == 0.0 and fixed_v == 0.0:
        raise ValueError(
            "contributor %r declares neither a resistance nor a forward drop, "
            "so it contributes nothing and is an incomplete entry rather than "
            "a lossless part" % (identifier.strip(),)
        )
    alpha = contributor.get("alpha_per_k", COPPER_ALPHA_PER_K)
    hot_ohm = hot_resistance_ohm(reference_ohm, alpha, policy)
    resistive_v = hot_ohm * current
    return {
        "id": identifier.strip(),
        "kind": kind,
        "hot_resistance_ohm": hot_ohm,
        "resistive_drop_v": resistive_v,
        "fixed_drop_v": fixed_v,
        "drop_v": resistive_v + fixed_v,
    }


def line_drop_breakdown(contributors, current_a, policy=DEFAULT_LINE_DROP_POLICY):
    """Every element's drop at the graded current, with shares and totals."""
    validate_line_drop_policy(policy)
    if not isinstance(contributors, (list, tuple)) or not contributors:
        raise ValueError(
            "contributors must be a non-empty sequence, got %r" % (contributors,)
        )
    records = [
        contributor_drop(contributor, current_a, policy) for contributor in contributors
    ]
    identifiers = [record["id"] for record in records]
    duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
    if duplicates:
        raise ValueError("contributor declared twice: %s" % (", ".join(duplicates),))

    nominal_v = math.fsum(record["drop_v"] for record in records)
    resistive_v = math.fsum(record["resistive_drop_v"] for record in records)
    fixed_v = math.fsum(record["fixed_drop_v"] for record in records)
    for record in records:
        record["share"] = 0.0 if nominal_v == 0.0 else record["drop_v"] / nominal_v

    grouped = {}
    for record in records:
        grouped[record["kind"]] = grouped.get(record["kind"], 0.0) + record["drop_v"]

    worst = max(records, key=lambda record: record["drop_v"])
    return {
        "contributors": tuple(records),
        "by_kind": grouped,
        "nominal_drop_v": nominal_v,
        "resistive_drop_v": resistive_v,
        "fixed_drop_v": fixed_v,
        "worst_case_drop_v": nominal_v * float(policy["tolerance_factor"]),
        "dominant": worst["id"],
        "dominant_share": worst["share"],
    }


def assess_line_voltage_drop(design, policy=DEFAULT_LINE_DROP_POLICY):
    """Full clause 5.4.5.1.1 judgement of one protected line's drop budget."""
    validate_line_drop_policy(policy)
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (design,))
    entry = class_entry(design.get("class_table"), design.get("class_name"))
    bus_v = _require_positive("bus_voltage_v", design.get("bus_voltage_v"))
    ceiling_v = allowed_drop_v(entry, bus_v)
    graded_current_a = entry["class_current_a"]

    operating_a = design.get("operating_current_a")
    findings = []
    if operating_a is not None:
        operating_a = _require_positive("operating_current_a", operating_a)
        if not _at_most(operating_a, graded_current_a):
            raise ValueError(
                "operating_current_a %.4f A sits above the %.4f A its class is "
                "rated for, so the line is on the wrong class before any drop "
                "is summed" % (operating_a, graded_current_a)
            )

    breakdown = line_drop_breakdown(
        design.get("contributors"), graded_current_a, policy
    )
    worst_case_v = breakdown["worst_case_drop_v"]
    margin_v = ceiling_v - worst_case_v
    margin_fraction = margin_v / ceiling_v
    within = _at_most(worst_case_v, ceiling_v)
    thin = within and not _at_least(
        margin_fraction, float(policy["thin_margin_fraction"])
    )

    if not within:
        findings.append(
            "the line loses %.4f V at the %.4f A class current against the "
            "%.4f V the class allows, so the load sits outside its input range "
            "at the end of the line" % (worst_case_v, graded_current_a, ceiling_v)
        )
    elif thin:
        findings.append(
            "only %.2f%% of the %.4f V budget is left after the line is summed "
            "at its hot, worst-case value"
            % (100.0 * margin_fraction, ceiling_v)
        )
    if not _at_most(
        breakdown["dominant_share"], float(policy["dominant_share_fraction"])
    ):
        findings.append(
            "%s carries %.1f%% of the drop on its own, so the budget moves by "
            "changing that element and not by trimming the rest"
            % (breakdown["dominant"], 100.0 * breakdown["dominant_share"])
        )

    result = {
        "class_name": entry["name"],
        "graded_current_a": graded_current_a,
        "bus_voltage_v": bus_v,
        "allowed_drop_v": ceiling_v,
        "breakdown": breakdown,
        "margin_v": margin_v,
        "margin_fraction": margin_fraction,
        "load_input_v": bus_v - worst_case_v,
        "findings": findings,
    }
    if not within:
        result["verdict"] = DROP_EXCEEDS_BUDGET
    elif thin:
        result["verdict"] = DROP_MARGIN_THIN
    else:
        result["verdict"] = DROP_WITHIN_BUDGET
    return result


def dominant_kind(breakdown):
    """The element kind carrying most of a line's drop."""
    if not isinstance(breakdown, dict) or not breakdown.get("by_kind"):
        raise ValueError("breakdown must carry a by_kind mapping, got %r" % (breakdown,))
    grouped = breakdown["by_kind"]
    best = None
    for kind in sorted(grouped):
        if best is None or grouped[kind] > grouped[best]:
            best = kind
    return best
