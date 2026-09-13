#!/usr/bin/env python3
"""Parameters tracked for the parts, materials and processes of a PVA.

Anchor: ECSS-E-ST-20-08C clause 5.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A photovoltaic assembly (PVA) is built from parts, materials and
processes, and each of them carries a parameter set that has to be
tracked from procurement through to the as-built record. The parameter
set is not the same for the three kinds:

    part       identity, manufacturer, lot or batch, the specification
               it was bought against, and the procurement level
    material   the same identity trail plus the shelf life, the age it
               will have reached at the point of use, and the
               outgassing data
    process    identity, the process specification, the qualification
               that supports it and the certification of the operator

Three numbers then decide what the entry is worth. A material is
screened on its outgassing data against the mass-loss and condensable
limits the project declares; it is screened again on how much of its
shelf life is still unspent at the planned point of use; and a part is
dispositioned on its procurement level. An entry whose parameter set is
incomplete is not screened at all, because there is nothing to screen.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ENTRY_KINDS = ("part", "material", "process")

REQUIRED_PARAMETERS = {
    "part": (
        "identification",
        "manufacturer",
        "lot-or-batch",
        "specification-reference",
        "procurement-level",
    ),
    "material": (
        "identification",
        "manufacturer",
        "lot-or-batch",
        "specification-reference",
        "shelf-life-days",
        "age-at-use-days",
        "outgassing-data",
    ),
    "process": (
        "identification",
        "process-specification-reference",
        "qualification-reference",
        "operator-certification",
    ),
}

PROCUREMENT_LEVELS = ("space-qualified", "upscreened-commercial", "commercial")

PARAMETERS_TRACKED = "parameters-tracked"
PARAMETERS_INCOMPLETE = "parameters-incomplete"
WAIVER_REQUIRED = "waiver-required"
NOT_ACCEPTABLE = "not-acceptable"

LIST_TRACKED = "pmp-parameters-tracked"
LIST_NOT_TRACKED = "pmp-parameters-not-tracked"

DEFAULT_PMP_POLICY = {
    "max_total_mass_loss_percent": 1.0,
    "max_collected_volatile_percent": 0.10,
    "min_shelf_life_margin_fraction": 0.10,
    "procurement_disposition": {
        "space-qualified": PARAMETERS_TRACKED,
        "upscreened-commercial": WAIVER_REQUIRED,
        "commercial": NOT_ACCEPTABLE,
    },
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A screening limit is declared as a round percentage and the measured
    value is read back from a report, so a result meant to sit exactly on
    the limit can land a few units in the last place above it. The limit
    is never widened; only the comparison tolerates the representation
    error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _is_declared(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def validate_pmp_policy(policy):
    """Check a parts, materials and processes policy carries sane limits."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "max_total_mass_loss_percent", policy.get("max_total_mass_loss_percent")
    )
    _require_positive(
        "max_collected_volatile_percent", policy.get("max_collected_volatile_percent")
    )
    margin = _require_non_negative(
        "min_shelf_life_margin_fraction", policy.get("min_shelf_life_margin_fraction")
    )
    if margin >= 1.0:
        raise ValueError(
            "min_shelf_life_margin_fraction must be below one, got %r" % (margin,)
        )
    table = policy.get("procurement_disposition")
    if not isinstance(table, dict):
        raise ValueError("policy procurement_disposition must be a mapping")
    missing = set(PROCUREMENT_LEVELS) - set(table)
    if missing:
        raise ValueError(
            "policy procurement_disposition is missing levels: %s"
            % ", ".join(sorted(missing))
        )
    for level in PROCUREMENT_LEVELS:
        _require_choice(
            "policy procurement_disposition[%s]" % level,
            table[level],
            (PARAMETERS_TRACKED, WAIVER_REQUIRED, NOT_ACCEPTABLE),
        )
    return policy


def required_parameters(kind):
    """Parameter set the clause expects for an entry of this kind."""
    _require_choice("kind", kind, ENTRY_KINDS)
    return REQUIRED_PARAMETERS[kind]


def missing_parameters(entry):
    """Required parameters the entry leaves undeclared or blank."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    kind = _require_choice("entry kind", entry.get("kind"), ENTRY_KINDS)
    parameters = entry.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("entry parameters must be a mapping, got %r" % (parameters,))
    return sorted(
        name
        for name in required_parameters(kind)
        if not _is_declared(parameters.get(name))
    )


def parameter_completeness_fraction(entry):
    """Share of the required parameter set the entry actually declares."""
    kind = _require_choice("entry kind", (entry or {}).get("kind"), ENTRY_KINDS)
    expected = required_parameters(kind)
    absent = missing_parameters(entry)
    return (len(expected) - len(absent)) / float(len(expected))


def outgassing_screen(
    total_mass_loss_percent, collected_volatile_percent, policy=DEFAULT_PMP_POLICY
):
    """Screen a material against the mass-loss and condensable limits."""
    validate_pmp_policy(policy)
    mass_loss = _require_non_negative(
        "total_mass_loss_percent", total_mass_loss_percent
    )
    condensable = _require_non_negative(
        "collected_volatile_percent", collected_volatile_percent
    )
    mass_loss_ok = _at_most(mass_loss, float(policy["max_total_mass_loss_percent"]))
    condensable_ok = _at_most(
        condensable, float(policy["max_collected_volatile_percent"])
    )
    findings = []
    if not mass_loss_ok:
        findings.append(
            "total mass loss %.4f%% exceeds the %.4f%% screening limit"
            % (mass_loss, policy["max_total_mass_loss_percent"])
        )
    if not condensable_ok:
        findings.append(
            "collected volatile condensable %.4f%% exceeds the %.4f%% screening limit"
            % (condensable, policy["max_collected_volatile_percent"])
        )
    return {
        "total_mass_loss_percent": mass_loss,
        "collected_volatile_percent": condensable,
        "mass_loss_ok": mass_loss_ok,
        "condensable_ok": condensable_ok,
        "passes": mass_loss_ok and condensable_ok,
        "findings": findings,
    }


def shelf_life_status(shelf_life_days, age_at_use_days, policy=DEFAULT_PMP_POLICY):
    """How much shelf life is still unspent at the planned point of use."""
    validate_pmp_policy(policy)
    shelf_life = _require_positive("shelf_life_days", shelf_life_days)
    age = _require_non_negative("age_at_use_days", age_at_use_days)
    remaining = shelf_life - age
    fraction = remaining / shelf_life
    required = float(policy["min_shelf_life_margin_fraction"])
    sufficient = _at_least(fraction, required)
    findings = []
    if not sufficient:
        findings.append(
            "shelf life leaves %.4f of its span at the point of use against a "
            "required %.4f" % (fraction, required)
        )
    return {
        "remaining_days": remaining,
        "remaining_fraction": fraction,
        "required_fraction": required,
        "sufficient": sufficient,
        "expired": remaining < 0.0 and not math.isclose(remaining, 0.0, abs_tol=_ABS_TOL),
        "findings": findings,
    }


def procurement_disposition(level, policy=DEFAULT_PMP_POLICY):
    """Disposition a part attracts from the level it was procured at."""
    validate_pmp_policy(policy)
    _require_choice("procurement level", level, PROCUREMENT_LEVELS)
    return policy["procurement_disposition"][level]


def assess_pmp_entry(entry, policy=DEFAULT_PMP_POLICY):
    """Verdict for one parts, materials or processes entry."""
    validate_pmp_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    kind = _require_choice("entry kind", entry.get("kind"), ENTRY_KINDS)
    parameters = entry.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("entry parameters must be a mapping, got %r" % (parameters,))
    name = parameters.get("identification")
    if not _is_declared(name):
        name = "<unidentified %s>" % kind
    else:
        name = str(name).strip()
    absent = missing_parameters(entry)
    completeness = parameter_completeness_fraction(entry)
    record = {
        "name": name,
        "kind": kind,
        "missing_parameters": absent,
        "completeness_fraction": completeness,
        "outgassing": None,
        "shelf_life": None,
        "procurement_level": None,
        "findings": [],
    }
    if absent:
        record["verdict"] = PARAMETERS_INCOMPLETE
        record["findings"].append(
            "%s %s declares %d of %d required parameters"
            % (
                kind,
                name,
                len(required_parameters(kind)) - len(absent),
                len(required_parameters(kind)),
            )
        )
        return record
    if kind == "material":
        data = parameters["outgassing-data"]
        if not isinstance(data, dict):
            raise ValueError(
                "outgassing-data must be a mapping for material %s" % name
            )
        screen = outgassing_screen(
            data.get("total_mass_loss_percent"),
            data.get("collected_volatile_percent"),
            policy,
        )
        shelf = shelf_life_status(
            parameters["shelf-life-days"], parameters["age-at-use-days"], policy
        )
        record["outgassing"] = screen
        record["shelf_life"] = shelf
        record["findings"].extend(screen["findings"])
        record["findings"].extend(shelf["findings"])
        if not screen["passes"]:
            record["verdict"] = NOT_ACCEPTABLE
        elif shelf["expired"]:
            record["verdict"] = NOT_ACCEPTABLE
        elif not shelf["sufficient"]:
            record["verdict"] = WAIVER_REQUIRED
        else:
            record["verdict"] = PARAMETERS_TRACKED
        return record
    if kind == "part":
        level = _require_choice(
            "procurement-level", parameters["procurement-level"], PROCUREMENT_LEVELS
        )
        record["procurement_level"] = level
        verdict = procurement_disposition(level, policy)
        record["verdict"] = verdict
        if verdict != PARAMETERS_TRACKED:
            record["findings"].append(
                "part %s is procured as %s and is dispositioned %s"
                % (name, level, verdict)
            )
        return record
    record["verdict"] = PARAMETERS_TRACKED
    return record


def audit_pmp_list(case, policy=DEFAULT_PMP_POLICY):
    """Full clause 5.3.2 sweep over a declared PVA parts and materials list."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    entries = case.get("entries")
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("case entries must be a non-empty sequence of mappings")
    records = [assess_pmp_entry(entry, policy) for entry in entries]
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["name"])
    tracked = [record for record in records if record["verdict"] == PARAMETERS_TRACKED]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    open_entries = [
        record["name"] for record in records if record["verdict"] != PARAMETERS_TRACKED
    ]
    total_completeness = sum(record["completeness_fraction"] for record in records)
    return {
        "verdict": LIST_TRACKED if not open_entries else LIST_NOT_TRACKED,
        "entry_records": records,
        "grouped_by_verdict": grouped,
        "entry_count": len(records),
        "tracked_count": len(tracked),
        "tracked_fraction": len(tracked) / float(len(records)),
        "mean_completeness_fraction": total_completeness / float(len(records)),
        "open_entries": open_entries,
        "findings": findings,
    }
