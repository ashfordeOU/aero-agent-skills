#!/usr/bin/env python3
"""Critical interface data in the array PMP list (ECSS-E-ST-20-08C, 4.4).

Offline, deterministic, standard-library only. The module decides which
entries of a photovoltaic-array parts, materials and processes list sit at
a critical interface, and checks that each such entry carries the interface
data the list owes:

* per-kind identification data every entry carries,
* the drivers that make an entry interface-critical,
* the interface data a critical entry additionally owes,
* outgassing figures for a non-metallic item at a bonded joint,
* the anodic-index separation of a metal-to-metal couple,
* per-entry and whole-list completeness of the declaration.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "ENTRY_KINDS",
    "BASE_FIELDS",
    "INTERFACE_DATA_FIELDS",
    "CRITICAL_INTERFACE_ROLES",
    "BULK_INTERFACE_ROLE",
    "INTERFACE_TYPES",
    "BONDED_INTERFACE_TYPES",
    "INTERFACE_ENVIRONMENTS",
    "EXPOSED_ENVIRONMENTS",
    "MATERIAL_FAMILIES",
    "NON_METALLIC_FAMILIES",
    "ANODIC_INDEX_V",
    "GALVANIC_LIMIT_V",
    "OUTGASSING_TML_LIMIT_PERCENT",
    "OUTGASSING_CVCM_LIMIT_PERCENT",
    "interface_criticality",
    "required_entry_fields",
    "missing_entry_fields",
    "check_outgassing",
    "anodic_separation",
    "check_galvanic_couple",
    "evaluate_list_entry",
    "assess_pmp_list",
]

# Absorbs binary-representation error when a declared figure lands a few ULPs
# outside an exactly-met limit. It never widens the limit itself.
REL_TOL = 1e-9

# A list entry is a delivered part, a bulk material or a process applied to
# one of them. The kind fixes the identification data the entry carries.
ENTRY_KINDS = ("part", "material", "process")

BASE_FIELDS = {
    "part": ("designation", "supplier", "specification", "part_number"),
    "material": ("designation", "supplier", "specification", "material_family"),
    "process": ("designation", "supplier", "specification", "process_reference"),
}

# The data an entry owes once it is found to sit at a critical interface.
INTERFACE_DATA_FIELDS = (
    "mating_item",
    "interface_type",
    "interface_environment",
    "qualification_reference",
)

# Array interfaces the clause treats as critical by name.
CRITICAL_INTERFACE_ROLES = (
    "cell-to-coverglass",
    "cell-to-interconnect",
    "interconnect-to-substrate",
    "substrate-to-structure",
    "harness-to-array-connector",
    "coating-to-substrate",
)

# An entry that joins nothing and is declared for its bulk properties alone.
BULK_INTERFACE_ROLE = "bulk"

INTERFACE_TYPES = (
    "bonded",
    "welded",
    "soldered",
    "crimped",
    "mechanical",
    "connector",
    "coated",
)

# The joint types whose strength depends on an organic layer, so that the
# non-metallic item in the joint owes its outgassing figures.
BONDED_INTERFACE_TYPES = ("bonded", "coated")

INTERFACE_ENVIRONMENTS = (
    "vacuum-thermal-cycling",
    "launch-vibration",
    "atomic-oxygen",
    "ultraviolet",
    "ground-storage",
    "humidity",
)

# Environments that act on an exposed front-face interface rather than a
# buried one, and so make the entry critical on their own.
EXPOSED_ENVIRONMENTS = ("atomic-oxygen", "ultraviolet")

MATERIAL_FAMILIES = (
    "metal",
    "polymer",
    "adhesive",
    "glass",
    "ceramic",
    "composite",
    "none",
)

NON_METALLIC_FAMILIES = ("polymer", "adhesive", "composite")

# Anodic index in volts, gold taken as the reference. A couple is judged on
# the separation between the two entries, not on either value alone.
ANODIC_INDEX_V = {
    "gold": 0.00,
    "silver": 0.15,
    "titanium": 0.15,
    "nickel": 0.30,
    "copper": 0.35,
    "brass": 0.40,
    "molybdenum": 0.45,
    "stainless-steel-passive": 0.50,
    "tin": 0.65,
    "solder-tin-lead": 0.65,
    "lead": 0.70,
    "aluminium": 0.90,
    "zinc": 1.25,
    "magnesium": 1.75,
}

# Separation a controlled-environment couple is allowed to show.
GALVANIC_LIMIT_V = 0.25

# Screening limits for a non-metallic item at a bonded or coated joint.
OUTGASSING_TML_LIMIT_PERCENT = 1.0
OUTGASSING_CVCM_LIMIT_PERCENT = 0.10

_ENTRY_KEYS = (
    "id",
    "kind",
    "designation",
    "supplier",
    "specification",
    "part_number",
    "material_family",
    "process_reference",
    "interface_role",
    "mating_item",
    "mating_material_family",
    "interface_type",
    "interface_environment",
    "qualification_reference",
    "outgassing_tml_percent",
    "outgassing_cvcm_percent",
    "metal",
    "mating_metal",
)


def _finding(code, subject, detail):
    """Build one list finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_non_negative_float(value, label):
    number = _as_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _within(value, limit):
    """Upper-bound comparison that absorbs binary-representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0)


def _carried(entry, field):
    """True when the entry actually states the field rather than gesturing at it."""
    if field not in entry:
        return False
    value = entry[field]
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _require_known(value, allowed, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-blank string" % label)
    token = value.strip()
    if token not in allowed:
        raise ValueError(
            "%s is %r, expected one of %s" % (label, token, ", ".join(allowed))
        )
    return token


def interface_criticality(entry):
    """Derive whether a list entry sits at a critical array interface.

    Criticality is derived from what the entry declares, never taken from a
    criticality flag the compiler of the list set by hand. Any one driver is
    enough; the drivers are reported so a reviewer can see which fired.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %s" % type(entry).__name__)
    role = entry.get("interface_role", BULK_INTERFACE_ROLE)
    role = _require_known(
        role,
        tuple(CRITICAL_INTERFACE_ROLES) + (BULK_INTERFACE_ROLE,),
        "interface_role",
    )
    drivers = []
    if role in CRITICAL_INTERFACE_ROLES:
        drivers.append("named-critical-interface")

    interface_type = None
    if _carried(entry, "interface_type"):
        interface_type = _require_known(
            entry["interface_type"], INTERFACE_TYPES, "interface_type"
        )

    environment = None
    if _carried(entry, "interface_environment"):
        environment = _require_known(
            entry["interface_environment"],
            INTERFACE_ENVIRONMENTS,
            "interface_environment",
        )
        if environment in EXPOSED_ENVIRONMENTS:
            drivers.append("exposed-surface-environment")

    family = None
    if _carried(entry, "material_family"):
        family = _require_known(
            entry["material_family"], MATERIAL_FAMILIES, "material_family"
        )
    if (
        family in NON_METALLIC_FAMILIES
        and interface_type in BONDED_INTERFACE_TYPES
    ):
        drivers.append("non-metallic-at-a-bonded-joint")

    if _carried(entry, "mating_metal") and not _carried(entry, "metal"):
        raise ValueError(
            "entry declares a mating metal but not the metal it couples to"
        )
    if _carried(entry, "metal") and _carried(entry, "mating_metal"):
        base = _require_known(entry["metal"], tuple(ANODIC_INDEX_V), "metal")
        partner = _require_known(
            entry["mating_metal"], tuple(ANODIC_INDEX_V), "mating_metal"
        )
        if base != partner:
            drivers.append("dissimilar-metal-couple")

    return {
        "interface_role": role,
        "interface_type": interface_type,
        "interface_environment": environment,
        "material_family": family,
        "drivers": drivers,
        "critical": bool(drivers),
    }


def required_entry_fields(entry):
    """List the fields this entry owes, identification plus interface data."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %s" % type(entry).__name__)
    if "kind" not in entry:
        raise ValueError("entry is missing required key 'kind'")
    kind = _require_known(entry["kind"], ENTRY_KINDS, "kind")
    fields = list(BASE_FIELDS[kind])
    criticality = interface_criticality(entry)
    if criticality["critical"]:
        fields.extend(INTERFACE_DATA_FIELDS)
        if criticality["material_family"] in NON_METALLIC_FAMILIES and (
            criticality["interface_type"] in BONDED_INTERFACE_TYPES
        ):
            fields.append("outgassing_tml_percent")
            fields.append("outgassing_cvcm_percent")
        if "dissimilar-metal-couple" in criticality["drivers"]:
            fields.append("mating_material_family")
    ordered = []
    for field in fields:
        if field not in ordered:
            ordered.append(field)
    return tuple(ordered)


def missing_entry_fields(entry):
    """Return the owed fields the entry does not actually state."""
    return tuple(
        field for field in required_entry_fields(entry) if not _carried(entry, field)
    )


def check_outgassing(tml_percent, cvcm_percent):
    """Screen a non-metallic item against the two outgassing limits."""
    tml = _as_non_negative_float(tml_percent, "outgassing_tml_percent")
    cvcm = _as_non_negative_float(cvcm_percent, "outgassing_cvcm_percent")
    if cvcm > tml and not math.isclose(cvcm, tml, rel_tol=REL_TOL, abs_tol=0.0):
        raise ValueError(
            "collected volatile fraction %r cannot exceed the total mass loss %r"
            % (cvcm_percent, tml_percent)
        )
    tml_ok = _within(tml, OUTGASSING_TML_LIMIT_PERCENT)
    cvcm_ok = _within(cvcm, OUTGASSING_CVCM_LIMIT_PERCENT)
    return {
        "quantity": "outgassing",
        "tml_percent": tml,
        "cvcm_percent": cvcm,
        "tml_limit_percent": OUTGASSING_TML_LIMIT_PERCENT,
        "cvcm_limit_percent": OUTGASSING_CVCM_LIMIT_PERCENT,
        "tml_within": tml_ok,
        "cvcm_within": cvcm_ok,
        "within": tml_ok and cvcm_ok,
    }


def anodic_separation(metal, mating_metal):
    """Separation in volts between the anodic indices of a metal couple."""
    base = _require_known(metal, tuple(ANODIC_INDEX_V), "metal")
    partner = _require_known(mating_metal, tuple(ANODIC_INDEX_V), "mating_metal")
    return abs(ANODIC_INDEX_V[base] - ANODIC_INDEX_V[partner])


def check_galvanic_couple(metal, mating_metal, limit_v=GALVANIC_LIMIT_V):
    """Check a metal-to-metal interface against the separation allowance."""
    allowance = _as_non_negative_float(limit_v, "limit_v")
    separation = anodic_separation(metal, mating_metal)
    return {
        "quantity": "galvanic-couple",
        "metal": metal.strip(),
        "mating_metal": mating_metal.strip(),
        "separation_v": separation,
        "limit_v": allowance,
        "margin_v": allowance - separation,
        "within": _within(separation, allowance),
    }


def evaluate_list_entry(entry):
    """Evaluate one PMP list entry against the interface-data obligation."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %s" % type(entry).__name__)
    unknown = [key for key in entry if key not in _ENTRY_KEYS]
    if unknown:
        raise ValueError(
            "entry carries unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    if "id" not in entry:
        raise ValueError("entry is missing required key 'id'")
    if not isinstance(entry["id"], str) or not entry["id"].strip():
        raise ValueError("entry id must be a non-blank string")
    identifier = entry["id"].strip()

    criticality = interface_criticality(entry)
    required = required_entry_fields(entry)
    missing = missing_entry_fields(entry)
    checks = {"criticality": criticality}
    findings = []

    if missing:
        findings.append(
            _finding(
                "interface-data-missing",
                identifier,
                "does not state %s" % ", ".join(missing),
            )
        )

    if _carried(entry, "outgassing_tml_percent") != _carried(
        entry, "outgassing_cvcm_percent"
    ):
        raise ValueError(
            "entry %s states one outgassing figure without the other" % identifier
        )
    if _carried(entry, "outgassing_tml_percent"):
        outgassing = check_outgassing(
            entry["outgassing_tml_percent"], entry["outgassing_cvcm_percent"]
        )
        checks["outgassing"] = outgassing
        if not outgassing["within"]:
            findings.append(
                _finding(
                    "outgassing-over-limit",
                    identifier,
                    "total mass loss %.4f %% and collected volatile fraction "
                    "%.4f %% against limits of %.4f %% and %.4f %%"
                    % (
                        outgassing["tml_percent"],
                        outgassing["cvcm_percent"],
                        outgassing["tml_limit_percent"],
                        outgassing["cvcm_limit_percent"],
                    ),
                )
            )

    if "dissimilar-metal-couple" in criticality["drivers"]:
        galvanic = check_galvanic_couple(entry["metal"], entry["mating_metal"])
        checks["galvanic"] = galvanic
        if not galvanic["within"]:
            findings.append(
                _finding(
                    "galvanic-couple-excessive",
                    identifier,
                    "%s against %s separates by %.3f V, above the %.3f V allowed"
                    % (
                        galvanic["metal"],
                        galvanic["mating_metal"],
                        galvanic["separation_v"],
                        galvanic["limit_v"],
                    ),
                )
            )

    if (
        criticality["critical"]
        and isinstance(entry.get("mating_item"), str)
        and isinstance(entry.get("designation"), str)
    ):
        if entry["mating_item"].strip() == entry["designation"].strip():
            findings.append(
                _finding(
                    "interface-mates-with-itself",
                    identifier,
                    "names its own designation as the mating item, so no "
                    "interface is described",
                )
            )

    return {
        "id": identifier,
        "kind": _require_known(entry.get("kind", ""), ENTRY_KINDS, "kind"),
        "criticality": criticality,
        "required_fields": required,
        "missing_fields": missing,
        "checks": checks,
        "findings": findings,
        "complete": not findings,
    }


def assess_pmp_list(entries):
    """Assess a whole array parts, materials and processes list."""
    if isinstance(entries, (str, bytes)) or not hasattr(entries, "__iter__"):
        raise ValueError("entries must be an iterable of list entries")
    evaluated = [evaluate_list_entry(entry) for entry in entries]
    if not evaluated:
        raise ValueError("a PMP list must carry at least one entry")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("list entry %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    critical = [record["id"] for record in evaluated if record["criticality"]["critical"]]
    by_kind = {}
    for kind in ENTRY_KINDS:
        by_kind[kind] = sum(1 for record in evaluated if record["kind"] == kind)
    accepted = not findings
    return {
        "verdict": "interface-data-complete" if accepted else "interface-data-incomplete",
        "accepted": accepted,
        "findings": findings,
        "entries": evaluated,
        "entry_count": len(evaluated),
        "critical_entries": critical,
        "critical_count": len(critical),
        "counts_by_kind": by_kind,
        "complete_fraction": sum(1 for record in evaluated if record["complete"])
        / float(len(evaluated)),
    }
