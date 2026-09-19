"""Reopening a sealed hybrid package, and what resealing then owes.

Anchor: ECSS-Q-ST-60-05C clause 10.5.5 (when a sealed hybrid may be reopened,
and the resealing and retest obligations that follow). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the package: how it was sealed, how much sealing land it started
   with and how many times it has already been opened and closed.
2. Decide whether the seal type can be reopened and reclosed at all. A
   fusible or mechanical seal can; a fired glass seal cannot be reinstated to
   the same condition and is not reopened for return to stock.
3. Spend the two budgets the package carries: the reopen-cycle count and the
   sealing land, which each reseal consumes a fixed width of. Either running
   out refuses the delid.
4. Read the reason. An approved repair can return the unit to deliverable
   stock once it is resealed and retested; opening a unit for analysis
   consumes it, and that unit does not go back whatever the reseal looks
   like.
5. Build the retest set the reseal owes, which grows with what was done
   inside the package and with the route the unit takes afterwards.

Sealing-land arithmetic subtracts fixed widths from a nominal dimension and
lands exactly on the minimum in ordinary cases, so that comparison carries a
tolerance instead of being a strict inequality.
"""

import math

__all__ = [
    "LENGTH_TOLERANCE",
    "SEAL_TYPES",
    "DELID_REASONS",
    "BASE_RESEAL_TESTS",
    "validate_seal_type",
    "validate_reason",
    "validate_package",
    "delid_cycles_remaining",
    "seal_land_after_cycles_mm",
    "projected_seal_land_mm",
    "seal_land_headroom_mm",
    "returns_to_deliverable_stock",
    "required_reseal_tests",
    "assess_delidding",
]

# A sealing land that has been consumed down to exactly its minimum is an
# ordinary result of fixed-width reseals on a nominal package.
LENGTH_TOLERANCE = 1e-9

# Per seal type: how many reopen-and-reseal cycles the seal supports, how
# much sealing land each reseal consumes, the land that must survive, and
# whether the seal can be reinstated at all.
SEAL_TYPES = {
    "seam-weld": {
        "cycle_allowance": 2,
        "land_consumed_mm": 0.15,
        "minimum_land_mm": 0.30,
        "resealable": True,
    },
    "solder-seal": {
        "cycle_allowance": 2,
        "land_consumed_mm": 0.10,
        "minimum_land_mm": 0.25,
        "resealable": True,
    },
    "glass-frit": {
        "cycle_allowance": 0,
        "land_consumed_mm": 0.0,
        "minimum_land_mm": 0.0,
        "resealable": False,
    },
}

# Why the package is being opened, and whether the unit can go back into
# deliverable stock afterwards.
DELID_REASONS = {
    "approved-repair": {"returns_to_stock": True, "internal_work_expected": True},
    "failure-analysis": {"returns_to_stock": False, "internal_work_expected": False},
    "destructive-physical-analysis": {"returns_to_stock": False, "internal_work_expected": False},
    "construction-analysis": {"returns_to_stock": False, "internal_work_expected": False},
}

BASE_RESEAL_TESTS = (
    "external-visual-inspection-of-the-reseal",
    "fine-leak-test",
    "gross-leak-test",
    "electrical-retest-of-the-resealed-unit",
    "delid-and-reseal-record-entry",
)


def _require_positive_number(value, label):
    """Return value as a strictly positive finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_non_negative_int(value, label):
    """Return value as a non-negative int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_seal_type(seal_type):
    """Return the normalised seal-type name, raising on an unknown one."""
    if not isinstance(seal_type, str) or not seal_type.strip():
        raise ValueError("seal_type must be a non-empty string, got %r" % (seal_type,))
    name = seal_type.strip().lower()
    if name not in SEAL_TYPES:
        raise ValueError(
            "unknown seal type %r; known: %s" % (seal_type, ", ".join(sorted(SEAL_TYPES)))
        )
    return name


def validate_reason(reason):
    """Return the normalised delid reason, raising on an unrecognised one."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string, got %r" % (reason,))
    name = reason.strip().lower()
    if name not in DELID_REASONS:
        raise ValueError(
            "unknown delid reason %r; known: %s" % (reason, ", ".join(sorted(DELID_REASONS)))
        )
    return name


def validate_package(package):
    """Return the normalised sealed-package record.

    A package that has already used its reopen allowance validates rather
    than raising: an over-opened unit is the case this assessment exists to
    catch, not a malformed input.
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("package_id", "seal_type", "initial_seal_land_mm"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)
    package_id = package["package_id"]
    if not isinstance(package_id, str) or not package_id.strip():
        raise ValueError("package['package_id'] must be a non-empty string")
    return {
        "package_id": package_id.strip(),
        "seal_type": validate_seal_type(package["seal_type"]),
        "initial_seal_land_mm": _require_positive_number(
            package["initial_seal_land_mm"], "package['initial_seal_land_mm']"
        ),
        "prior_delid_cycles": _require_non_negative_int(
            package.get("prior_delid_cycles", 0), "package['prior_delid_cycles']"
        ),
        "deliverable_stock": bool(package.get("deliverable_stock", True)),
    }


def delid_cycles_remaining(package, seal_types=None):
    """Return how many reopen-and-reseal cycles this package still supports."""
    record = validate_package(package)
    table = SEAL_TYPES if seal_types is None else seal_types
    allowance = table[record["seal_type"]]["cycle_allowance"]
    return max(0, allowance - record["prior_delid_cycles"])


def seal_land_after_cycles_mm(package, cycles, seal_types=None):
    """Return the sealing land left after the given number of reseals."""
    record = validate_package(package)
    spent = _require_non_negative_int(cycles, "cycles")
    table = SEAL_TYPES if seal_types is None else seal_types
    consumed = table[record["seal_type"]]["land_consumed_mm"]
    return record["initial_seal_land_mm"] - spent * consumed


def projected_seal_land_mm(package, seal_types=None):
    """Return the sealing land left once this delid has been resealed."""
    record = validate_package(package)
    return seal_land_after_cycles_mm(package, record["prior_delid_cycles"] + 1, seal_types)


def seal_land_headroom_mm(package, seal_types=None):
    """Return projected land minus the minimum; negative means over-consumed."""
    record = validate_package(package)
    table = SEAL_TYPES if seal_types is None else seal_types
    minimum = table[record["seal_type"]]["minimum_land_mm"]
    return projected_seal_land_mm(package, seal_types) - minimum


def returns_to_deliverable_stock(reason):
    """Return whether a unit opened for this reason can go back into stock."""
    return DELID_REASONS[validate_reason(reason)]["returns_to_stock"]


def required_reseal_tests(seal_type, reason, internal_work_done=False, extra=()):
    """Return the ordered retest set a reseal owes for this case."""
    seal = validate_seal_type(seal_type)
    why = validate_reason(reason)
    if not isinstance(internal_work_done, bool):
        raise ValueError("internal_work_done must be a boolean")
    if isinstance(extra, str) or not isinstance(extra, (list, tuple, set, frozenset)):
        raise ValueError("extra must be a sequence of test names")
    tests = []
    if internal_work_done:
        tests.append("internal-visual-inspection-before-reseal")
        tests.append("interconnect-verification-after-internal-work")
        tests.append("particle-contamination-check-before-reseal")
    tests.extend(BASE_RESEAL_TESTS)
    if seal == "seam-weld":
        tests.append("weld-land-dimensional-check")
    if seal == "solder-seal":
        tests.append("seal-fillet-visual-check")
    if DELID_REASONS[why]["returns_to_stock"]:
        tests.append("re-screening-before-return-to-deliverable-stock")
    ordered = []
    for name in list(tests) + [str(e).strip() for e in extra if str(e).strip()]:
        if name not in ordered:
            ordered.append(name)
    return ordered


def assess_delidding(spec):
    """Run the full clause 10.5.5 delid and reseal assessment.

    spec keys: package, reason; optional approved_procedure (default False),
    internal_work_done (default from the reason), reseal_capability
    (default False) and seal_types overriding SEAL_TYPES.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("package", "reason"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    approved = spec.get("approved_procedure", False)
    if not isinstance(approved, bool):
        raise ValueError("approved_procedure must be a boolean")
    reseal_capability = spec.get("reseal_capability", False)
    if not isinstance(reseal_capability, bool):
        raise ValueError("reseal_capability must be a boolean")

    package = validate_package(spec["package"])
    reason = validate_reason(spec["reason"])
    seal_types = spec.get("seal_types")
    table = SEAL_TYPES if seal_types is None else seal_types
    seal = table[package["seal_type"]]

    internal_work = spec.get("internal_work_done", DELID_REASONS[reason]["internal_work_expected"])
    if not isinstance(internal_work, bool):
        raise ValueError("internal_work_done must be a boolean")

    cycles_left = delid_cycles_remaining(spec["package"], seal_types)
    projected_land = projected_seal_land_mm(spec["package"], seal_types)
    headroom = seal_land_headroom_mm(spec["package"], seal_types)
    returns = DELID_REASONS[reason]["returns_to_stock"]

    blockers = []
    notes = []
    if not approved:
        blockers.append("no approved delid procedure covers this reopening")
    if not seal["resealable"]:
        blockers.append(
            "a %s seal cannot be reinstated; the package is not reopened for return"
            % package["seal_type"]
        )
    if cycles_left <= 0:
        blockers.append(
            "package %s has used its %d reopen cycle(s)"
            % (package["package_id"], seal["cycle_allowance"])
        )
    if headroom < -LENGTH_TOLERANCE:
        blockers.append(
            "reseal would leave %.3f mm of sealing land against a minimum of %.3f mm"
            % (projected_land, seal["minimum_land_mm"])
        )
    if returns and not reseal_capability:
        blockers.append(
            "unit is to return to deliverable stock but no qualified reseal capability is available"
        )

    if not returns:
        notes.append(
            "opening for %s consumes the unit; it does not return to deliverable stock" % reason
        )
    if package["deliverable_stock"] and not returns:
        notes.append(
            "package %s leaves deliverable stock on reopening" % package["package_id"]
        )

    if blockers:
        disposition = "reopen-not-permitted"
    elif not returns:
        disposition = "reopen-permitted-non-deliverable"
    else:
        disposition = "reopen-permitted"
    return {
        "package_id": package["package_id"],
        "seal_type": package["seal_type"],
        "reason": reason,
        "cycles_remaining": cycles_left,
        "projected_seal_land_mm": projected_land,
        "minimum_seal_land_mm": seal["minimum_land_mm"],
        "seal_land_headroom_mm": headroom,
        "returns_to_deliverable_stock": returns and not blockers,
        "blockers": blockers,
        "notes": notes,
        "disposition": disposition,
        "permitted": disposition != "reopen-not-permitted",
        "reseal_tests": (
            required_reseal_tests(package["seal_type"], reason, internal_work)
            if not blockers
            else []
        ),
    }
