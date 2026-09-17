"""Configuration item data list and as-built record for a delivered device.

Anchor: ECSS-Q-ST-60-03C clause 8.2.2 (the item data list and the as-built
record that together identify every delivered element). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every data-list entry: an entry has to carry the identification
   fields its item kind demands, and a kind that is serialised has to be
   deliverable as an individually traceable unit.
2. Index the data list, refusing a duplicated item identifier, because a
   duplicate makes the as-built reconciliation ambiguous rather than merely
   untidy.
3. Reconcile the as-built record against the data list in both directions:
   a listed item never built, an element delivered but never listed, and a
   revision that moved between the two are three different findings.
4. Check the delivery-side obligations: a serialised item needs its serial
   number in the as-built record, and a referenced deviation needs an
   approved waiver behind it.
5. Score identification coverage and compare it with the required floor
   under a named tolerance, so an exactly-compliant delivery is not failed
   by representation error.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "ITEM_KINDS",
    "SERIALISED_KINDS",
    "BASE_FIELDS",
    "EXTRA_FIELDS_BY_KIND",
    "normalize_identifier",
    "normalize_kind",
    "required_fields",
    "validate_item",
    "build_data_list",
    "validate_as_built_entry",
    "build_as_built_index",
    "reconcile_lists",
    "missing_serial_numbers",
    "unbacked_deviations",
    "identification_coverage",
    "assess_data_list",
]

# Coverage is a ratio of two exact integer counts, but it is compared with a
# floor that a caller may express as a decimal. Absorb the representation
# error here; the required floor stays where the delivery review put it.
COVERAGE_TOLERANCE = 1e-12

ITEM_KINDS = (
    "hardware-assembly",
    "programmable-device",
    "mechanical-part",
    "software-load",
    "delivered-document",
)

# Kinds delivered as individually traceable units, so the as-built record has
# to name the unit that actually shipped, not only the type.
SERIALISED_KINDS = ("hardware-assembly", "programmable-device")

BASE_FIELDS = ("item_id", "part_number", "revision", "supplier")

EXTRA_FIELDS_BY_KIND = {
    "hardware-assembly": (),
    "programmable-device": ("device_technology",),
    "mechanical-part": ("material_reference",),
    "software-load": ("build_identifier",),
    "delivered-document": ("issue_reference",),
}


def normalize_identifier(value, label):
    """Return an upper-cased, whitespace-trimmed identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).upper()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_kind(value):
    """Return the canonical item-kind key, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("item kind must be a string, got %r" % (value,))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("item kind must not be empty")
    if key not in ITEM_KINDS:
        raise ValueError("unknown item kind '%s'" % key)
    return key


def required_fields(kind):
    """Return the identification fields a data-list entry of this kind needs."""
    key = normalize_kind(kind)
    return BASE_FIELDS + EXTRA_FIELDS_BY_KIND[key]


def validate_item(entry):
    """Return a normalized data-list item, raising on an unusable entry."""
    if not isinstance(entry, dict):
        raise ValueError("data-list entry must be a mapping, got %r" % (entry,))
    if "kind" not in entry:
        raise ValueError("data-list entry is missing 'kind'")
    kind = normalize_kind(entry["kind"])
    item = {"kind": kind}
    for field in required_fields(kind):
        if field not in entry:
            raise ValueError(
                "data-list entry of kind '%s' is missing '%s'" % (kind, field)
            )
        item[field] = normalize_identifier(entry[field], field)
    deviation = entry.get("deviation_reference")
    if deviation is None:
        item["deviation_reference"] = None
    else:
        item["deviation_reference"] = normalize_identifier(
            deviation, "deviation_reference"
        )
    item["serialised"] = kind in SERIALISED_KINDS
    return item


def build_data_list(entries):
    """Return the item index keyed by item identifier, or raise on a duplicate."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("data list must be a sequence of entries")
    if not entries:
        raise ValueError("data list must contain at least one item")
    index = {}
    for entry in entries:
        item = validate_item(entry)
        if item["item_id"] in index:
            raise ValueError(
                "duplicate item identifier '%s' in the data list" % item["item_id"]
            )
        index[item["item_id"]] = item
    return index


def validate_as_built_entry(entry):
    """Return a normalized as-built record line, raising on an unusable one."""
    if not isinstance(entry, dict):
        raise ValueError("as-built entry must be a mapping, got %r" % (entry,))
    for field in ("item_id", "revision"):
        if field not in entry:
            raise ValueError("as-built entry is missing '%s'" % field)
    record = {
        "item_id": normalize_identifier(entry["item_id"], "item_id"),
        "revision": normalize_identifier(entry["revision"], "revision"),
    }
    serial = entry.get("serial_number")
    if serial is None:
        record["serial_number"] = None
    else:
        record["serial_number"] = normalize_identifier(serial, "serial_number")
    return record


def build_as_built_index(entries):
    """Return {item_id: [records]} for the as-built record, preserving order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("as-built record must be a sequence of entries")
    index = {}
    for entry in entries:
        record = validate_as_built_entry(entry)
        index.setdefault(record["item_id"], []).append(record)
    return index


def reconcile_lists(data_list, as_built_index):
    """Return the two-way reconciliation between the list and the record."""
    if not isinstance(data_list, dict) or not data_list:
        raise ValueError("data_list must be a non-empty mapping")
    if not isinstance(as_built_index, dict):
        raise ValueError("as_built_index must be a mapping")
    not_built = [key for key in sorted(data_list) if key not in as_built_index]
    not_listed = [key for key in sorted(as_built_index) if key not in data_list]
    revision_drift = []
    for key in sorted(data_list):
        for record in as_built_index.get(key, []):
            if record["revision"] != data_list[key]["revision"]:
                revision_drift.append(
                    {
                        "item_id": key,
                        "listed_revision": data_list[key]["revision"],
                        "as_built_revision": record["revision"],
                    }
                )
    repeated_serials = []
    seen = {}
    for key in sorted(as_built_index):
        for record in as_built_index[key]:
            serial = record["serial_number"]
            if serial is None:
                continue
            token = (key, serial)
            if token in seen:
                repeated_serials.append({"item_id": key, "serial_number": serial})
            seen[token] = True
    return {
        "not_built": not_built,
        "not_listed": not_listed,
        "revision_drift": revision_drift,
        "repeated_serials": repeated_serials,
    }


def missing_serial_numbers(data_list, as_built_index):
    """Return the serialised items delivered without a serial number."""
    if not isinstance(data_list, dict) or not data_list:
        raise ValueError("data_list must be a non-empty mapping")
    if not isinstance(as_built_index, dict):
        raise ValueError("as_built_index must be a mapping")
    missing = []
    for key in sorted(data_list):
        if not data_list[key]["serialised"]:
            continue
        records = as_built_index.get(key, [])
        for record in records:
            if record["serial_number"] is None:
                missing.append(key)
                break
    return missing


def unbacked_deviations(data_list, approved_waivers):
    """Return the items whose deviation reference has no approved waiver."""
    if not isinstance(data_list, dict) or not data_list:
        raise ValueError("data_list must be a non-empty mapping")
    if approved_waivers is None:
        approved_waivers = []
    if not isinstance(approved_waivers, (list, tuple, set, frozenset)):
        raise ValueError("approved_waivers must be a sequence")
    approved = set()
    for waiver in approved_waivers:
        approved.add(normalize_identifier(waiver, "approved waiver"))
    unbacked = []
    for key in sorted(data_list):
        reference = data_list[key]["deviation_reference"]
        if reference is not None and reference not in approved:
            unbacked.append({"item_id": key, "deviation_reference": reference})
    return unbacked


def identification_coverage(data_list, as_built_index):
    """Return the fraction of listed items identified in the as-built record."""
    if not isinstance(data_list, dict) or not data_list:
        raise ValueError("data_list must be a non-empty mapping")
    if not isinstance(as_built_index, dict):
        raise ValueError("as_built_index must be a mapping")
    total = len(data_list)
    identified = 0
    for key, item in data_list.items():
        records = as_built_index.get(key, [])
        if not records:
            continue
        if any(record["revision"] != item["revision"] for record in records):
            continue
        if item["serialised"] and any(
            record["serial_number"] is None for record in records
        ):
            continue
        identified += 1
    return identified / float(total)


def assess_data_list(spec):
    """Run the full clause 8.2.2 data-list and as-built assessment.

    spec keys: items (data-list entries), as_built (as-built record entries),
    optional approved_waivers and required_coverage (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "as_built"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = spec.get("required_coverage", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_coverage must lie in [0, 1], got %g" % required)

    data_list = build_data_list(spec["items"])
    as_built_index = build_as_built_index(spec["as_built"])
    reconciliation = reconcile_lists(data_list, as_built_index)
    serial_gaps = missing_serial_numbers(data_list, as_built_index)
    deviation_gaps = unbacked_deviations(data_list, spec.get("approved_waivers"))
    coverage = identification_coverage(data_list, as_built_index)
    coverage_ok = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )

    findings = []
    for key in reconciliation["not_built"]:
        findings.append("listed item '%s' has no as-built record line" % key)
    for key in reconciliation["not_listed"]:
        findings.append("as-built element '%s' appears in no data-list item" % key)
    for drift in reconciliation["revision_drift"]:
        findings.append(
            "item '%s' listed at revision %s was built at revision %s"
            % (drift["item_id"], drift["listed_revision"], drift["as_built_revision"])
        )
    for repeat in reconciliation["repeated_serials"]:
        findings.append(
            "serial number %s is recorded twice against item '%s'"
            % (repeat["serial_number"], repeat["item_id"])
        )
    for key in serial_gaps:
        findings.append("serialised item '%s' was delivered without a serial number" % key)
    for gap in deviation_gaps:
        findings.append(
            "item '%s' cites deviation %s with no approved waiver behind it"
            % (gap["item_id"], gap["deviation_reference"])
        )
    if not coverage_ok:
        findings.append(
            "identification coverage %.4f is below the required %.4f"
            % (coverage, required)
        )
    return {
        "item_count": len(data_list),
        "as_built_line_count": sum(len(v) for v in as_built_index.values()),
        "reconciliation": reconciliation,
        "missing_serial_numbers": serial_gaps,
        "unbacked_deviations": deviation_gaps,
        "identification_coverage": coverage,
        "required_coverage": required,
        "coverage_ok": coverage_ok,
        "findings": findings,
        "deliverable": not findings,
    }
