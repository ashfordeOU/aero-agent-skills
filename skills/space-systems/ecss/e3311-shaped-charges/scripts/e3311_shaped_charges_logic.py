"""Performance, standoff and safety screen for a shaped charge.

Anchor: ECSS-E-ST-33-11C clause 4.11.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A shaped charge does not push a target, it forms a jet and drives it
through one. That changes what has to be graded. The output is not a
force but a penetration depth, and the depth depends on geometry the
installation owns rather than on the charge alone: how far the liner
stands off the target when it fires, and how squarely the jet meets
it. A charge qualified to cut 60 mm is a charge that cuts rather less
mounted 20 percent off its optimum standoff and a few degrees off
normal.

The screen computes a capability and then grades it:

    standoff efficiency   falls away from the optimum standoff, at
                          the charge's declared sensitivity
    alignment efficiency  the cosine of the misalignment angle
    capability            nominal penetration times both efficiencies
    penetration margin    capability against the thickness that has
                          to be cut

and then the safety side, which is what makes a shaped charge
different from any other cutting device on a vehicle: a keep-out
radius scaled to the charge diameter, a residual jet that continues
past the cut and must not reach the next structure, and a spacing
between neighbouring charges that keeps one from setting off another.

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CHARGE_KINDS = ("conical-shaped-charge", "linear-shaped-charge")

GATES = (
    "performance",
    "standoff",
    "alignment",
    "keep-out",
    "backup-clearance",
)

VERDICT_MET = "shaped-charge-met"
VERDICT_NOT_MET = "shaped-charge-not-met"

DEFAULT_SHAPED_CHARGE_POLICY = {
    "min_penetration_margin": 1.50,
    "max_standoff_deviation_fraction": 0.20,
    "max_misalignment_deg": 5.0,
    "min_keep_out_charge_diameters": 10.0,
    "min_sympathetic_spacing_charge_diameters": 6.0,
    "min_residual_clearance_margin": 1.25,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A capability is a product of a nominal and two efficiencies, one of
    them a cosine, so a charge sitting exactly on a limit can land a
    few units in the last place the wrong side of it. The limit is
    never relaxed; only the comparison tolerates the representation
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


def validate_shaped_charge_policy(policy):
    """Check a policy carries every limit the shaped-charge gates need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "min_penetration_margin",
        "max_standoff_deviation_fraction",
        "max_misalignment_deg",
        "min_keep_out_charge_diameters",
        "min_sympathetic_spacing_charge_diameters",
        "min_residual_clearance_margin",
    ):
        _require_positive("policy %s" % key, policy.get(key))
    if not _at_least(policy["min_penetration_margin"], 1.0):
        raise ValueError(
            "policy min_penetration_margin must be at least 1.0, got %r"
            % (policy["min_penetration_margin"],)
        )
    if not _at_most(policy["max_misalignment_deg"], 90.0):
        raise ValueError(
            "policy max_misalignment_deg must not exceed 90, got %r"
            % (policy["max_misalignment_deg"],)
        )
    return policy


def validate_charge(record):
    """Normalize one shaped charge and its installation into a record."""
    if not isinstance(record, dict):
        raise ValueError("charge must be a mapping, got %r" % (record,))
    charge_id = _require_text("charge id", record.get("id"))
    misalignment = _require_non_negative(
        "charge %s misalignment_deg" % charge_id, record.get("misalignment_deg", 0.0)
    )
    if misalignment >= 90.0:
        raise ValueError(
            "charge %s is misaligned by %.2f degrees, so no jet reaches the "
            "target" % (charge_id, misalignment)
        )
    return {
        "id": charge_id,
        "kind": _require_choice(
            "charge %s kind" % charge_id, record.get("kind"), CHARGE_KINDS
        ),
        "charge_diameter_mm": _require_positive(
            "charge %s charge_diameter_mm" % charge_id,
            record.get("charge_diameter_mm"),
        ),
        "nominal_penetration_mm": _require_positive(
            "charge %s nominal_penetration_mm" % charge_id,
            record.get("nominal_penetration_mm"),
        ),
        "optimum_standoff_mm": _require_positive(
            "charge %s optimum_standoff_mm" % charge_id,
            record.get("optimum_standoff_mm"),
        ),
        "installed_standoff_mm": _require_positive(
            "charge %s installed_standoff_mm" % charge_id,
            record.get("installed_standoff_mm"),
        ),
        "standoff_sensitivity": _require_non_negative(
            "charge %s standoff_sensitivity" % charge_id,
            record.get("standoff_sensitivity", 0.0),
        ),
        "misalignment_deg": misalignment,
        "target_thickness_mm": _require_positive(
            "charge %s target_thickness_mm" % charge_id,
            record.get("target_thickness_mm"),
        ),
        "clearance_to_sensitive_mm": _require_non_negative(
            "charge %s clearance_to_sensitive_mm" % charge_id,
            record.get("clearance_to_sensitive_mm"),
        ),
        "clearance_behind_target_mm": _require_non_negative(
            "charge %s clearance_behind_target_mm" % charge_id,
            record.get("clearance_behind_target_mm"),
        ),
    }


def validate_charges(charges):
    """Normalize a charge list and reject duplicate identifiers."""
    if not isinstance(charges, (list, tuple)) or not charges:
        raise ValueError("charges must contain at least one charge")
    normalized = []
    seen = set()
    for raw in charges:
        record = validate_charge(raw)
        if record["id"] in seen:
            raise ValueError("duplicate charge id %r" % record["id"])
        seen.add(record["id"])
        normalized.append(record)
    return normalized


def standoff_deviation_fraction(record):
    """How far the installed standoff sits from the optimum, as a fraction."""
    charge = validate_charge(record)
    return (
        abs(charge["installed_standoff_mm"] - charge["optimum_standoff_mm"])
        / charge["optimum_standoff_mm"]
    )


def standoff_efficiency(record):
    """Penetration retained at the installed standoff, never below zero."""
    charge = validate_charge(record)
    loss = charge["standoff_sensitivity"] * standoff_deviation_fraction(record)
    return max(0.0, 1.0 - loss)


def alignment_efficiency(record):
    """Penetration retained at the installed misalignment angle."""
    charge = validate_charge(record)
    return math.cos(math.radians(charge["misalignment_deg"]))


def penetration_capability_mm(record):
    """Depth the charge actually reaches, as installed."""
    charge = validate_charge(record)
    return (
        charge["nominal_penetration_mm"]
        * standoff_efficiency(record)
        * alignment_efficiency(record)
    )


def residual_penetration_mm(record):
    """Jet capability left over once the target has been cut through."""
    charge = validate_charge(record)
    return max(0.0, penetration_capability_mm(record) - charge["target_thickness_mm"])


def keep_out_radius_mm(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Exclusion radius for sensitive hardware, scaled to the diameter."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    return policy["min_keep_out_charge_diameters"] * charge["charge_diameter_mm"]


def performance_verdict(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Grade the installed capability against the thickness to be cut."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    capability = penetration_capability_mm(record)
    margin = capability / charge["target_thickness_mm"]
    ok = _at_least(margin, policy["min_penetration_margin"])
    findings = []
    if not ok:
        findings.append(
            "%s reaches %.3f mm as installed against a %.3f mm target, a "
            "margin of %.3f below the required %.3f"
            % (
                charge["id"],
                capability,
                charge["target_thickness_mm"],
                margin,
                policy["min_penetration_margin"],
            )
        )
    return {
        "gate": "performance",
        "capability_mm": capability,
        "penetration_margin": margin,
        "compliant": ok,
        "findings": findings,
    }


def standoff_verdict(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Grade the installed standoff against its own tolerance band."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    deviation = standoff_deviation_fraction(record)
    ok = _at_most(deviation, policy["max_standoff_deviation_fraction"])
    findings = []
    if not ok:
        findings.append(
            "%s stands off %.3f mm against a %.3f mm optimum, a deviation of "
            "%.1f%% above the allowed %.1f%%"
            % (
                charge["id"],
                charge["installed_standoff_mm"],
                charge["optimum_standoff_mm"],
                100.0 * deviation,
                100.0 * policy["max_standoff_deviation_fraction"],
            )
        )
    return {
        "gate": "standoff",
        "deviation_fraction": deviation,
        "efficiency": standoff_efficiency(record),
        "compliant": ok,
        "findings": findings,
    }


def alignment_verdict(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Grade how squarely the jet meets the target."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    ok = _at_most(charge["misalignment_deg"], policy["max_misalignment_deg"])
    findings = []
    if not ok:
        findings.append(
            "%s meets the target %.3f degrees off normal, above the allowed "
            "%.3f degrees"
            % (
                charge["id"],
                charge["misalignment_deg"],
                policy["max_misalignment_deg"],
            )
        )
    return {
        "gate": "alignment",
        "efficiency": alignment_efficiency(record),
        "compliant": ok,
        "findings": findings,
    }


def keep_out_verdict(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Grade clearance to sensitive hardware against the keep-out radius."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    required = keep_out_radius_mm(record, policy)
    ok = _at_least(charge["clearance_to_sensitive_mm"], required)
    findings = []
    if not ok:
        findings.append(
            "%s sits %.2f mm from sensitive hardware, inside the %.2f mm "
            "keep-out radius its diameter demands"
            % (charge["id"], charge["clearance_to_sensitive_mm"], required)
        )
    return {
        "gate": "keep-out",
        "required_radius_mm": required,
        "compliant": ok,
        "findings": findings,
    }


def backup_clearance_verdict(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Grade the space behind the cut against the residual jet."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    residual = residual_penetration_mm(record)
    required = residual * policy["min_residual_clearance_margin"]
    ok = _at_least(charge["clearance_behind_target_mm"], required)
    findings = []
    if not ok:
        findings.append(
            "%s leaves %.3f mm of residual jet past the cut and only %.2f mm "
            "of clearance behind it, short of the %.2f mm required"
            % (
                charge["id"],
                residual,
                charge["clearance_behind_target_mm"],
                required,
            )
        )
    return {
        "gate": "backup-clearance",
        "residual_mm": residual,
        "required_clearance_mm": required,
        "compliant": ok,
        "findings": findings,
    }


def sympathetic_spacing_verdict(
    charge_a, charge_b, spacing_mm, policy=DEFAULT_SHAPED_CHARGE_POLICY
):
    """Grade the spacing between two charges against sympathetic initiation."""
    validate_shaped_charge_policy(policy)
    first = validate_charge(charge_a)
    second = validate_charge(charge_b)
    spacing = _require_positive("spacing_mm", spacing_mm)
    driver = max(first["charge_diameter_mm"], second["charge_diameter_mm"])
    required = policy["min_sympathetic_spacing_charge_diameters"] * driver
    ok = _at_least(spacing, required)
    findings = []
    if not ok:
        findings.append(
            "%s and %s sit %.2f mm apart, inside the %.2f mm their diameters "
            "demand against sympathetic initiation"
            % (first["id"], second["id"], spacing, required)
        )
    return {
        "gate": "sympathetic-spacing",
        "pair": tuple(sorted((first["id"], second["id"]))),
        "spacing_mm": spacing,
        "required_spacing_mm": required,
        "compliant": ok,
        "findings": findings,
    }


def assess_shaped_charge(record, policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Run the per-charge gates and group the outcome."""
    validate_shaped_charge_policy(policy)
    charge = validate_charge(record)
    gates = {
        "performance": performance_verdict(record, policy),
        "standoff": standoff_verdict(record, policy),
        "alignment": alignment_verdict(record, policy),
        "keep-out": keep_out_verdict(record, policy),
        "backup-clearance": backup_clearance_verdict(record, policy),
    }
    findings = []
    failed = []
    for name in GATES:
        gate = gates[name]
        findings.extend(gate["findings"])
        if not gate["compliant"]:
            failed.append(name)
    return {
        "id": charge["id"],
        "gates": gates,
        "failed_gates": failed,
        "compliant": not failed,
        "findings": findings,
    }


def assess_charge_array(charges, neighbours=(), policy=DEFAULT_SHAPED_CHARGE_POLICY):
    """Full clause 4.11.7 screen over an installed set of charges."""
    validate_shaped_charge_policy(policy)
    records = validate_charges(charges)
    by_id = {record["id"]: record for record in records}
    if not isinstance(neighbours, (list, tuple)):
        raise ValueError("neighbours must be a list of spacing declarations")
    pair_results = []
    seen_pairs = set()
    for entry in neighbours:
        if not isinstance(entry, dict):
            raise ValueError("neighbour entry must be a mapping, got %r" % (entry,))
        pair = entry.get("charges")
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("a neighbour entry must name exactly two charges")
        first, second = pair
        for ref in (first, second):
            if ref not in by_id:
                raise ValueError("neighbour entry names unknown charge %r" % (ref,))
        if first == second:
            raise ValueError("charge %r is declared as its own neighbour" % (first,))
        key = tuple(sorted((first, second)))
        if key in seen_pairs:
            raise ValueError("duplicate neighbour pair %s and %s" % key)
        seen_pairs.add(key)
        pair_results.append(
            sympathetic_spacing_verdict(
                by_id[first], by_id[second], entry.get("spacing_mm"), policy
            )
        )
    per_charge = [assess_shaped_charge(record, policy) for record in records]
    findings = []
    for result in per_charge:
        findings.extend(result["findings"])
    for result in pair_results:
        findings.extend(result["findings"])
    rejected = [r["id"] for r in per_charge if not r["compliant"]]
    failed_pairs = [r["pair"] for r in pair_results if not r["compliant"]]
    compliant = not rejected and not failed_pairs
    return {
        "charges": per_charge,
        "spacings": pair_results,
        "accepted": [r["id"] for r in per_charge if r["compliant"]],
        "rejected": rejected,
        "failed_pairs": failed_pairs,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }
