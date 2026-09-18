"""General GSE quality assurance logic: identification, records and safety provisions.

Anchor: ECSS-Q-ST-20C clause 5.8.8 -- the general quality assurance
requirements that apply to ground support equipment whatever it is for: the
equipment is identifiable, the records that follow it are kept for as long as
they are needed, and equipment whose failure would hurt people or flight
hardware carries the provisions its category demands. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each item's identification mark against a durable marking scheme
   and check it across the register, since a mark repeated on two items
   identifies neither.
2. Reconcile the mark carried on the item with the mark held in the register.
3. Derive the record set the item owes from its own category and states, and
   name every record the file does not hold.
4. Compare the retention actually applied with the retention the item's life
   demands, and report the shortfall in years rather than as a verdict alone.
5. Check the handling provisions a safety-critical item owes: a written
   operating procedure, restriction to trained operators, a periodic
   inspection interval and a hazard notice at the point of use.
"""

import math
import re

__all__ = [
    "GSE_CATEGORIES",
    "BASE_RECORDS",
    "SAFETY_PROVISIONS",
    "IDENTIFICATION_PATTERN",
    "RETENTION_TOLERANCE",
    "normalize_token",
    "validate_item",
    "identification_findings",
    "required_records",
    "record_findings",
    "retention_shortfall",
    "safety_provision_findings",
    "assess_gse_general",
]

# How much the equipment matters if it fails while it is being used.
GSE_CATEGORIES = ("safety-critical", "mission-critical", "general-purpose")

# Records that follow every piece of ground support equipment through its life.
BASE_RECORDS = (
    "identification-register-entry",
    "acceptance-record",
    "usage-log",
    "maintenance-history",
    "nonconformance-history",
    "modification-history",
)

# Provisions an item in the safety-critical category carries at its point of use.
SAFETY_PROVISIONS = (
    "written-operating-procedure",
    "trained-operator-restriction",
    "periodic-inspection-interval",
    "point-of-use-hazard-notice",
)

# A durable identification mark: a letter type prefix and a numeric serial.
IDENTIFICATION_PATTERN = re.compile(r"^[a-z]{2,8}-[0-9]{3,8}$")

# Retention is compared in years and can land a few ULPs short of its target.
RETENTION_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _non_negative(value, label):
    v = _real(value, label)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_item(item):
    """Return the validated GSE register entry for one item."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("register_mark", "category"):
        if key not in item:
            raise ValueError("item is missing '%s'" % key)
    category = normalize_token(item["category"], "category")
    if category not in GSE_CATEGORIES:
        raise ValueError("category %r is not a GSE category" % category)
    marked = item.get("marked_on_item")
    if marked is not None:
        marked = normalize_token(marked, "marked_on_item")
    return {
        "register_mark": normalize_token(item["register_mark"], "register_mark"),
        "marked_on_item": marked,
        "category": category,
        "mark_is_durable": _flag(item.get("mark_is_durable", True), "mark_is_durable"),
        "software_driven": _flag(item.get("software_driven", False), "software_driven"),
        "calibrated": _flag(item.get("calibrated", False), "calibrated"),
    }


def identification_findings(items):
    """Return the identification findings across a GSE register."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of register entries")
    seen = {}
    findings = []
    for i, item in enumerate(items):
        record = validate_item(item)
        mark = record["register_mark"]
        if not IDENTIFICATION_PATTERN.match(mark):
            findings.append(
                "identification mark %s does not follow the marking scheme" % mark
            )
        if mark in seen:
            findings.append(
                "identification mark %s is carried by more than one item" % mark
            )
        else:
            seen[mark] = i
        if not record["mark_is_durable"]:
            findings.append("identification mark %s is not applied durably" % mark)
        if record["marked_on_item"] is None:
            findings.append("item registered as %s carries no mark" % mark)
        elif record["marked_on_item"] != mark:
            findings.append(
                "item carries %s while the register holds %s"
                % (record["marked_on_item"], mark)
            )
    return findings


def required_records(item):
    """Return the records this item's category and states make mandatory."""
    record = validate_item(item)
    records = list(BASE_RECORDS)
    if record["category"] == "safety-critical":
        records.extend(["safety-critical-gse-inspection-record", "operator-training-record"])
    if record["calibrated"]:
        records.append("calibration-history")
    if record["software_driven"]:
        records.append("software-configuration-record")
    return records


def record_findings(records_held, required):
    """Return the mandatory records the item's file does not hold."""
    if not isinstance(records_held, (list, tuple)):
        raise ValueError("records_held must be a sequence of record names")
    if not isinstance(required, (list, tuple)):
        raise ValueError("required must be a sequence of record names")
    have = {normalize_token(r, "held record") for r in records_held}
    findings = []
    for name in required:
        token = normalize_token(name, "required record")
        if token not in have:
            findings.append("item file holds no %s" % token)
    return findings


def retention_shortfall(applied_years, service_life_years, margin_years=2.0):
    """Return the years by which the applied record retention falls short."""
    applied = _non_negative(applied_years, "applied_years")
    life = _non_negative(service_life_years, "service_life_years")
    margin = _non_negative(margin_years, "margin_years")
    needed = life + margin
    shortfall = needed - applied
    if shortfall < 0.0 or math.isclose(
        shortfall, 0.0, rel_tol=0.0, abs_tol=RETENTION_TOLERANCE
    ):
        return 0.0
    return shortfall


def safety_provision_findings(item, provisions_in_place):
    """Return the handling provisions a safety-critical item is missing."""
    record = validate_item(item)
    if not isinstance(provisions_in_place, (list, tuple)):
        raise ValueError("provisions_in_place must be a sequence of provision names")
    if record["category"] != "safety-critical":
        return []
    have = {normalize_token(p, "provision") for p in provisions_in_place}
    findings = []
    for provision in SAFETY_PROVISIONS:
        if provision not in have:
            findings.append(
                "safety-critical item %s has no %s" % (record["register_mark"], provision)
            )
    return findings


def assess_gse_general(spec):
    """Run the full clause 5.8.8 general GSE quality assurance assessment.

    spec keys: items, records_held, provisions_in_place, applied_retention_years,
    service_life_years.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "items",
        "records_held",
        "provisions_in_place",
        "applied_retention_years",
        "service_life_years",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    items = spec["items"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    identification = identification_findings(items)
    subject = items[0]
    required = required_records(subject)
    records = record_findings(spec["records_held"], required)
    shortfall = retention_shortfall(
        spec["applied_retention_years"], spec["service_life_years"]
    )
    retention = []
    if shortfall > 0.0:
        retention.append(
            "record retention falls %.1f year(s) short of the item's service life plus margin"
            % shortfall
        )
    safety = safety_provision_findings(subject, spec["provisions_in_place"])
    findings = list(identification) + list(records) + retention + list(safety)
    return {
        "identification_findings": identification,
        "required_records": required,
        "record_findings": records,
        "retention_shortfall_years": shortfall,
        "retention_findings": retention,
        "safety_provision_findings": safety,
        "findings": findings,
        "fit_for_registered_use": not findings,
    }
