"""Baseline provisions carried by every active die purchase for hybrids.

Anchor: ECSS-Q-ST-60-05C clause 8.3.1 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Separate the baseline from the conditioned. A provision is baseline
   only when it holds for every active die purchase whatever the device
   does and whatever process made it. A provision that names a
   technology, or that only bites for one class of device function, is a
   conditioned addition, and a record that claims to apply to everything
   while carrying a condition is internally inconsistent rather than
   merely generous.
2. Resolve what a given purchase owes. The baseline set applies in full,
   and the conditioned provisions join it only when the purchase matches
   the condition they name. The two sets add; the conditioned one never
   replaces a member of the baseline.
3. Measure coverage of the declaration. A purchase declaration lists the
   provisions it carries, and the gap is whatever the baseline holds
   that the declaration does not, less anything covered by a waiver that
   is actually valid.
4. Test a waiver rather than counting it. A waiver has to name a
   provision that may be waived at all, be granted by an authority
   entitled to grant it, and still be inside its validity date on the
   day the purchase is assessed. A waiver failing any of those is not a
   weaker waiver, it is an open gap.
5. Refuse a substitution. Offering a device-specific provision in place
   of a baseline one trades a requirement that holds everywhere for one
   that holds in a single case, so the baseline member stays open and
   the substitution itself is reported.

Stdlib only, offline, deterministic.
"""

import datetime

SCOPE_ALL_ACTIVE_DICE = "all-active-dice"
SCOPE_TECHNOLOGY = "technology-conditioned"
SCOPE_FUNCTION = "function-conditioned"
PROVISION_SCOPES = (SCOPE_ALL_ACTIVE_DICE, SCOPE_TECHNOLOGY, SCOPE_FUNCTION)

# Provisions carried by every active die purchase, and whether each one
# may be waived at all. A provision protecting the identity of the dice
# themselves cannot be waived, because waiving it removes the ability to
# review anything else about them.
BASELINE_PROVISIONS = {
    "wafer-lot-traceability-to-diffusion-lot": {"waivable": False},
    "die-visual-inspection-before-encapsulation": {"waivable": False},
    "electrostatic-discharge-controlled-handling": {"waivable": False},
    "die-storage-under-controlled-atmosphere": {"waivable": True},
    "supplier-change-notification-agreement": {"waivable": True},
    "die-deliverable-documentation-set": {"waivable": True},
}

# Provisions that join the baseline only when the purchase matches the
# condition they name.
CONDITIONED_PROVISIONS = {
    "compound-semiconductor-backside-metal-inspection": {
        "scope": SCOPE_TECHNOLOGY,
        "condition": "gallium-arsenide-mmic",
    },
    "wide-bandgap-die-attach-void-limit": {
        "scope": SCOPE_TECHNOLOGY,
        "condition": "gallium-nitride-hemt",
    },
    "linear-device-parametric-drift-screen": {
        "scope": SCOPE_FUNCTION,
        "condition": "linear",
    },
    "memory-device-pattern-sensitivity-screen": {
        "scope": SCOPE_FUNCTION,
        "condition": "memory",
    },
}

DIE_TECHNOLOGIES = (
    "silicon-bipolar",
    "silicon-cmos",
    "silicon-bicmos",
    "silicon-germanium",
    "gallium-arsenide-mmic",
    "gallium-nitride-hemt",
)

DEVICE_FUNCTIONS = ("digital", "linear", "memory", "mixed-signal", "discrete")

# Authorities entitled to grant a waiver. A supplier cannot grant itself
# relief from a provision written to constrain it.
APPROVAL_AUTHORITIES = (
    "customer-product-assurance",
    "procurement-authority",
)

WAIVER_VALID = "waiver-valid"
WAIVER_EXPIRED = "waiver-expired"
WAIVER_UNAUTHORIZED = "waiver-authority-not-entitled"
WAIVER_NOT_WAIVABLE = "provision-may-not-be-waived"

# Coverage is a quotient of two small integers, so a fully covered
# declaration can land a unit in the last place under one. This
# tolerance absorbs that representation error without ever reporting a
# real gap as covered.
COVERAGE_TOLERANCE = 1.0e-12

COMPLIANT = "declaration-covers-the-baseline"
DEFICIENT = "baseline-provisions-open"


def _iso_date(label, value):
    """Coerce an ISO date string to a date; an already-coerced date passes."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO date: %r" % (label, value))


def validate_provision(record):
    """Validate one provision record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("provision must be a mapping")
    provision_id = record.get("id")
    if not isinstance(provision_id, str) or not provision_id.strip():
        raise ValueError("provision needs a non-empty string id")
    scope = record.get("scope")
    if scope not in PROVISION_SCOPES:
        raise ValueError(
            "provision %s has unknown scope %r (expected one of %s)"
            % (provision_id, scope, ", ".join(PROVISION_SCOPES))
        )
    condition = record.get("condition")
    if scope == SCOPE_ALL_ACTIVE_DICE and condition is not None:
        raise ValueError(
            "provision %s claims to cover every active die purchase while "
            "naming the condition %r" % (provision_id, condition)
        )
    if scope != SCOPE_ALL_ACTIVE_DICE:
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                "provision %s is %s and needs a condition" % (provision_id, scope)
            )
        if scope == SCOPE_TECHNOLOGY and condition not in DIE_TECHNOLOGIES:
            raise ValueError(
                "provision %s names unknown technology %r"
                % (provision_id, condition)
            )
        if scope == SCOPE_FUNCTION and condition not in DEVICE_FUNCTIONS:
            raise ValueError(
                "provision %s names unknown device function %r"
                % (provision_id, condition)
            )
    return {"id": provision_id, "scope": scope, "condition": condition}


def is_baseline(record):
    """True when a provision holds for every active die purchase."""
    norm = validate_provision(record)
    return norm["scope"] == SCOPE_ALL_ACTIVE_DICE


def baseline_provision_ids():
    """Identifiers of the provisions every active die purchase carries."""
    return tuple(sorted(BASELINE_PROVISIONS))


def provision_is_waivable(provision_id):
    """True when a baseline provision may be waived at all."""
    if provision_id not in BASELINE_PROVISIONS:
        raise ValueError(
            "unknown baseline provision %r (expected one of %s)"
            % (provision_id, ", ".join(baseline_provision_ids()))
        )
    return BASELINE_PROVISIONS[provision_id]["waivable"]


def conditioned_provisions_for(technology, device_function):
    """Conditioned provisions that join the baseline for this purchase."""
    if technology not in DIE_TECHNOLOGIES:
        raise ValueError(
            "unknown technology %r (expected one of %s)"
            % (technology, ", ".join(DIE_TECHNOLOGIES))
        )
    if device_function not in DEVICE_FUNCTIONS:
        raise ValueError(
            "unknown device_function %r (expected one of %s)"
            % (device_function, ", ".join(DEVICE_FUNCTIONS))
        )
    matched = []
    for provision_id, meta in CONDITIONED_PROVISIONS.items():
        if meta["scope"] == SCOPE_TECHNOLOGY and meta["condition"] == technology:
            matched.append(provision_id)
        elif meta["scope"] == SCOPE_FUNCTION and meta["condition"] == device_function:
            matched.append(provision_id)
    return tuple(sorted(matched))


def applicable_provisions(technology, device_function):
    """Everything a purchase owes: the baseline plus what it conditions in."""
    return tuple(
        sorted(
            set(baseline_provision_ids())
            | set(conditioned_provisions_for(technology, device_function))
        )
    )


def validate_waiver(waiver):
    """Validate one waiver record and return a normalized copy."""
    if not isinstance(waiver, dict):
        raise ValueError("waiver must be a mapping")
    provision_id = waiver.get("provision")
    if provision_id not in BASELINE_PROVISIONS:
        raise ValueError(
            "waiver names unknown baseline provision %r" % (provision_id,)
        )
    authority = waiver.get("authority")
    if not isinstance(authority, str) or not authority.strip():
        raise ValueError(
            "waiver on %s needs a non-empty authority" % provision_id
        )
    valid_until = _iso_date(
        "waiver on %s valid_until" % provision_id, waiver.get("valid_until")
    )
    return {
        "provision": provision_id,
        "authority": authority,
        "valid_until": valid_until,
    }


def waiver_status(waiver, as_of):
    """Status of one waiver on the day the purchase is assessed."""
    norm = validate_waiver(waiver)
    day = _iso_date("as_of", as_of)
    if not provision_is_waivable(norm["provision"]):
        return WAIVER_NOT_WAIVABLE
    if norm["authority"] not in APPROVAL_AUTHORITIES:
        return WAIVER_UNAUTHORIZED
    if day > norm["valid_until"]:
        return WAIVER_EXPIRED
    return WAIVER_VALID


def validate_declaration(declaration):
    """Validate one active die purchase declaration and normalize it."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")
    decl_id = declaration.get("id")
    if not isinstance(decl_id, str) or not decl_id.strip():
        raise ValueError("declaration needs a non-empty string id")
    technology = declaration.get("technology")
    device_function = declaration.get("device_function")
    conditioned_provisions_for(technology, device_function)
    declared = declaration.get("declared_provisions", [])
    if not isinstance(declared, (list, tuple)):
        raise ValueError(
            "declaration %s declared_provisions must be a sequence" % decl_id
        )
    known = set(BASELINE_PROVISIONS) | set(CONDITIONED_PROVISIONS)
    for item in declared:
        if item not in known:
            raise ValueError(
                "declaration %s names unknown provision %r" % (decl_id, item)
            )
    waivers = declaration.get("waivers", [])
    if not isinstance(waivers, (list, tuple)):
        raise ValueError("declaration %s waivers must be a sequence" % decl_id)
    substitutions = declaration.get("substitutions", {})
    if not isinstance(substitutions, dict):
        raise ValueError(
            "declaration %s substitutions must be a mapping" % decl_id
        )
    for baseline_id, offered in substitutions.items():
        if baseline_id not in BASELINE_PROVISIONS:
            raise ValueError(
                "declaration %s substitutes for unknown baseline provision %r"
                % (decl_id, baseline_id)
            )
        if offered not in CONDITIONED_PROVISIONS:
            raise ValueError(
                "declaration %s offers unknown provision %r" % (decl_id, offered)
            )
    return {
        "id": decl_id,
        "technology": technology,
        "device_function": device_function,
        "declared_provisions": sorted(set(declared)),
        "waivers": [validate_waiver(w) for w in waivers],
        "substitutions": dict(substitutions),
        "assessment_date": declaration.get("assessment_date", "2026-01-01"),
    }


def waived_provision_ids(declaration):
    """Baseline provisions genuinely relieved by a valid waiver."""
    norm = validate_declaration(declaration)
    relieved = []
    for waiver in norm["waivers"]:
        if waiver_status(waiver, norm["assessment_date"]) == WAIVER_VALID:
            relieved.append(waiver["provision"])
    return sorted(set(relieved))


def waiver_findings(declaration):
    """Findings about waivers that do not do what they claim."""
    norm = validate_declaration(declaration)
    findings = []
    for waiver in norm["waivers"]:
        status = waiver_status(waiver, norm["assessment_date"])
        if status != WAIVER_VALID:
            findings.append("%s:%s" % (status, waiver["provision"]))
    return findings


def baseline_gaps(declaration):
    """Baseline provisions neither declared nor validly waived."""
    norm = validate_declaration(declaration)
    held = set(norm["declared_provisions"]) | set(waived_provision_ids(norm))
    return [pid for pid in baseline_provision_ids() if pid not in held]


def substitution_findings(declaration):
    """Findings where a conditioned provision was offered for a baseline one."""
    norm = validate_declaration(declaration)
    return [
        "device-specific-provision-offered-for-baseline:%s" % baseline_id
        for baseline_id in sorted(norm["substitutions"])
    ]


def baseline_coverage_fraction(declaration):
    """Share of the baseline the declaration covers, between zero and one."""
    norm = validate_declaration(declaration)
    total = len(baseline_provision_ids())
    return (total - len(baseline_gaps(norm))) / total


def conditioned_gaps(declaration):
    """Conditioned provisions this purchase conditions in but omits."""
    norm = validate_declaration(declaration)
    owed = conditioned_provisions_for(norm["technology"], norm["device_function"])
    held = set(norm["declared_provisions"])
    return [pid for pid in owed if pid not in held]


def assess_general_provisions(declaration):
    """Assess one active die purchase declaration against clause 8.3.1."""
    norm = validate_declaration(declaration)
    gaps = baseline_gaps(norm)
    findings = ["baseline-provision-open:%s" % pid for pid in gaps]
    findings.extend(waiver_findings(norm))
    findings.extend(substitution_findings(norm))
    findings.extend(
        "conditioned-provision-open:%s" % pid for pid in conditioned_gaps(norm)
    )
    coverage = baseline_coverage_fraction(norm)
    return {
        "id": norm["id"],
        "technology": norm["technology"],
        "device_function": norm["device_function"],
        "baseline_provisions": list(baseline_provision_ids()),
        "applicable_provisions": list(
            applicable_provisions(norm["technology"], norm["device_function"])
        ),
        "baseline_gaps": gaps,
        "waived_provisions": waived_provision_ids(norm),
        "conditioned_gaps": conditioned_gaps(norm),
        "baseline_coverage": coverage,
        "findings": findings,
        "status": DEFICIENT if gaps else COMPLIANT,
        "acceptable": not findings,
    }


def assess_purchase_set(declarations):
    """Run the clause 8.3.1 assessment over several purchase declarations."""
    if not isinstance(declarations, list) or not declarations:
        raise ValueError("declarations must be a non-empty list")
    results = []
    seen = set()
    for declaration in declarations:
        result = assess_general_provisions(declaration)
        if result["id"] in seen:
            raise ValueError("duplicate declaration id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    open_ids = [r["id"] for r in results if not r["acceptable"]]
    worst = min(results, key=lambda r: (r["baseline_coverage"], r["id"]))
    return {
        "declarations": results,
        "acceptable_ids": [r["id"] for r in results if r["acceptable"]],
        "open_ids": open_ids,
        "weakest_declaration": worst["id"],
        "weakest_coverage": worst["baseline_coverage"],
        "set_acceptable": not open_ids,
    }
