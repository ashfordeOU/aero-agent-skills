"""Dispatch of ordered blocking diodes with the documentation due at delivery.

Anchor: ECSS-E-ST-20-08C clause 12.9. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A blocking diode shipment is not releasable because the counts add up. The
count is the cheapest arm of the check and the only one a picking list can
answer on its own; three further arms have to close with it, and each of
them has a way of going quietly green.

    documentation   every diode comes from a batch, and that batch's data
                    package has to be RELEASED, not merely registered. An
                    entry whose release is still pending is an entry, and
                    reading the register for presence rather than for state
                    puts untraceable hardware on the pallet
    traceability    blocking diodes ship serialized. A serial that is not
                    on the delivered-serial list of the batch it claims is
                    not a labelling slip: the part and the batch record
                    disagree about what was built, and neither can be
                    trusted until that is settled
    storage life    a released package does not stop the clock. A batch
                    dispatched past its storage life is held unless a
                    revalidation was performed after the life ran out and
                    before the shipment left. A revalidation predating the
                    expiry revalidated nothing
    allocation      diodes are ordered by part number AND by blocking
                    voltage class. A line may be filled from a HIGHER
                    class when the order permits the upgrade, because the
                    customer receives a part that blocks more than was
                    bought. It may never be filled from a lower class,
                    which is a downgrade of the article dressed up as a
                    substitution, and never from another part number at
                    all, which is not a substitution of any kind

Allocation order matters as much as the rule: exact class is spent first
and only then is a permitted upgrade drawn on, or a high line goes short
because its parts were consumed by a low line that had its own stock.

What is left over is not slack, and a partial dispatch is a decision. The
order declares the fraction of a line below which a partial delivery is
refused outright; a line that clears that floor without being complete
still goes, and is still named as partial.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

__all__ = [
    "BLOCKING_VOLTAGE_CLASSES",
    "DISPATCH_HELD",
    "DISPATCH_RELEASABLE",
    "DIODE_HELD",
    "DIODE_SHIPPABLE",
    "FILL_TOLERANCE",
    "HOLD_DOCUMENTATION",
    "HOLD_STORAGE_LIFE",
    "HOLD_TRACEABILITY",
    "HOLD_UNKNOWN_BATCH",
    "LINE_COMPLETE",
    "LINE_PARTIAL",
    "LINE_REFUSED",
    "allocate_diodes_to_lines",
    "assess_diode",
    "assess_diodes",
    "batch_storage_state",
    "class_rank",
    "evaluate_dispatch",
    "normalize_class",
    "parse_delivery_date",
    "validate_batch_register",
    "validate_order",
    "validate_order_line",
]

# Lowest blocking capability first. Rank is the index, so a higher rank is
# a part that blocks more and an upgrade is a move up this ladder.
BLOCKING_VOLTAGE_CLASSES = ("bv-100v", "bv-200v", "bv-400v")

DIODE_SHIPPABLE = "diode-shippable"
DIODE_HELD = "diode-held"

HOLD_UNKNOWN_BATCH = "batch-absent-from-register"
HOLD_DOCUMENTATION = "batch-data-package-not-released"
HOLD_TRACEABILITY = "serial-not-on-batch-delivered-list"
HOLD_STORAGE_LIFE = "batch-storage-life-expired"

LINE_COMPLETE = "line-complete"
LINE_PARTIAL = "line-partial-within-floor"
LINE_REFUSED = "line-below-partial-delivery-floor"

DISPATCH_RELEASABLE = "dispatch-releasable"
DISPATCH_HELD = "dispatch-held"

# A fill fraction is a ratio of two small integers, but the declared floor
# arrives as a decimal literal. Comparing them without a tolerance makes a
# line that exactly meets its floor pass on one platform and fail on
# another, so the comparison absorbs representation error by name.
FILL_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _count(value, label):
    """Return a positive integer count, refusing a bool or a float."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def parse_delivery_date(value, label):
    """Return an ISO-8601 calendar date, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO-8601 date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO-8601 date: %r" % (label, value))


def normalize_class(value, label="blocking voltage class"):
    """Return a recognized blocking voltage class."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = value.strip().lower()
    if cleaned not in BLOCKING_VOLTAGE_CLASSES:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, value, ", ".join(BLOCKING_VOLTAGE_CLASSES))
        )
    return cleaned


def class_rank(value):
    """Return the ladder position of a class; higher blocks more."""
    return BLOCKING_VOLTAGE_CLASSES.index(normalize_class(value))


def validate_order_line(line, label="order line"):
    """Return one validated order line."""
    if not isinstance(line, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("line_id", "part_number", "blocking_voltage_class", "ordered_count"):
        if key not in line:
            raise ValueError("%s missing required key '%s'" % (label, key))
    allow = line.get("allow_class_upgrade", False)
    if not isinstance(allow, bool):
        raise ValueError(
            "%s allow_class_upgrade must be a boolean, got %r" % (label, allow)
        )
    return {
        "line_id": _identifier(line["line_id"], "%s line_id" % label),
        "part_number": _identifier(line["part_number"], "%s part_number" % label),
        "blocking_voltage_class": normalize_class(
            line["blocking_voltage_class"], "%s blocking_voltage_class" % label
        ),
        "ordered_count": _count(line["ordered_count"], "%s ordered_count" % label),
        "allow_class_upgrade": allow,
    }


def validate_order(order):
    """Return the validated order, with its partial-delivery floor."""
    if not isinstance(order, dict):
        raise ValueError("order must be a mapping")
    for key in ("order_id", "lines", "partial_delivery_floor"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    floor = order["partial_delivery_floor"]
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("partial_delivery_floor must be a number, got %r" % (floor,))
    floor = float(floor)
    if not 0.0 <= floor <= 1.0:
        raise ValueError(
            "partial_delivery_floor must lie between 0 and 1, got %r" % (floor,)
        )
    lines = order["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("order must carry at least one line")
    validated = []
    seen = set()
    for index, line in enumerate(lines):
        entry = validate_order_line(line, "order line[%d]" % index)
        if entry["line_id"] in seen:
            raise ValueError("order line %s appears twice" % entry["line_id"])
        seen.add(entry["line_id"])
        validated.append(entry)
    return {
        "order_id": _identifier(order["order_id"], "order_id"),
        "lines": tuple(validated),
        "partial_delivery_floor": floor,
    }


def validate_batch_register(batches):
    """Return the batch register keyed by batch id.

    Release is read as a STATE. A batch listed with its release still
    pending is a batch without a released package, and reading the entry
    rather than the state is the quiet way the documentation arm goes
    green.
    """
    if not isinstance(batches, (list, tuple)) or not batches:
        raise ValueError("batch_register must be a non-empty sequence of batches")
    register = {}
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            raise ValueError("batch_register[%d] must be a mapping" % index)
        for key in (
            "batch_id",
            "data_package_released",
            "delivered_serials",
            "storage_life_expiry",
        ):
            if key not in batch:
                raise ValueError("batch_register[%d] missing key '%s'" % (index, key))
        batch_id = _identifier(batch["batch_id"], "batch_register[%d] batch_id" % index)
        if batch_id in register:
            raise ValueError("batch %s has two register entries" % batch_id)
        released = batch["data_package_released"]
        if not isinstance(released, bool):
            raise ValueError(
                "batch %s data_package_released must be a boolean, got %r"
                % (batch_id, released)
            )
        serials = batch["delivered_serials"]
        if not isinstance(serials, (list, tuple)) or not serials:
            raise ValueError("batch %s must list at least one delivered serial" % batch_id)
        listed = set()
        for position, serial in enumerate(serials):
            value = _identifier(serial, "batch %s serial[%d]" % (batch_id, position))
            if value in listed:
                raise ValueError("batch %s lists serial %s twice" % (batch_id, value))
            listed.add(value)
        revalidation = batch.get("revalidation")
        if revalidation is not None:
            if not isinstance(revalidation, dict):
                raise ValueError(
                    "batch %s revalidation must be a mapping or None" % batch_id
                )
            for key in ("reference", "date"):
                if key not in revalidation:
                    raise ValueError(
                        "batch %s revalidation missing key '%s'" % (batch_id, key)
                    )
            revalidation = {
                "reference": _identifier(
                    revalidation["reference"], "batch %s revalidation reference" % batch_id
                ),
                "date": parse_delivery_date(
                    revalidation["date"], "batch %s revalidation date" % batch_id
                ),
            }
        register[batch_id] = {
            "batch_id": batch_id,
            "data_package_released": released,
            "delivered_serials": frozenset(listed),
            "storage_life_expiry": parse_delivery_date(
                batch["storage_life_expiry"], "batch %s storage_life_expiry" % batch_id
            ),
            "revalidation": revalidation,
        }
    return register


def batch_storage_state(entry, dispatch_date):
    """Decide whether a batch may leave on storage-life grounds.

    Within life is the ordinary case. Past life, a revalidation counts only
    when it was performed AFTER the life ran out and on or before the day
    the shipment leaves: a revalidation predating the expiry revalidated a
    batch that had not yet expired.
    """
    if not isinstance(entry, dict):
        raise ValueError("batch register entry must be a mapping")
    expiry = entry["storage_life_expiry"]
    if dispatch_date <= expiry:
        return {"within_life": True, "revalidated": False, "reason": None}
    revalidation = entry["revalidation"]
    if revalidation is None:
        return {
            "within_life": False,
            "revalidated": False,
            "reason": "batch %s passed its storage life on %s with no revalidation"
            % (entry["batch_id"], expiry),
        }
    if revalidation["date"] < expiry:
        return {
            "within_life": False,
            "revalidated": False,
            "reason": "batch %s was revalidated on %s, before its storage life ran "
            "out on %s, so nothing was revalidated"
            % (entry["batch_id"], revalidation["date"], expiry),
        }
    if revalidation["date"] > dispatch_date:
        return {
            "within_life": False,
            "revalidated": False,
            "reason": "batch %s carries a revalidation dated %s, after the shipment "
            "left on %s" % (entry["batch_id"], revalidation["date"], dispatch_date),
        }
    return {"within_life": True, "revalidated": True, "reason": None}


def assess_diode(diode, register, dispatch_date):
    """Disposition one blocking diode against all three hold arms."""
    if not isinstance(diode, dict):
        raise ValueError("diode must be a mapping")
    for key in ("serial", "part_number", "blocking_voltage_class", "batch_id"):
        if key not in diode:
            raise ValueError("diode missing required key '%s'" % key)
    serial = _identifier(diode["serial"], "diode serial")
    part_number = _identifier(diode["part_number"], "diode %s part_number" % serial)
    voltage_class = normalize_class(
        diode["blocking_voltage_class"], "diode %s blocking_voltage_class" % serial
    )
    batch_id = _identifier(diode["batch_id"], "diode %s batch_id" % serial)

    holds = []
    reasons = []
    entry = register.get(batch_id)
    if entry is None:
        holds.append(HOLD_UNKNOWN_BATCH)
        reasons.append(
            "diode %s claims batch %s, which has no register entry, so nothing "
            "states what was built" % (serial, batch_id)
        )
    else:
        if not entry["data_package_released"]:
            holds.append(HOLD_DOCUMENTATION)
            reasons.append(
                "diode %s comes from batch %s, whose data package is not released, "
                "so nothing downstream can trace it" % (serial, batch_id)
            )
        if serial not in entry["delivered_serials"]:
            holds.append(HOLD_TRACEABILITY)
            reasons.append(
                "diode %s is not on the delivered-serial list of batch %s, so the "
                "part and the batch record disagree" % (serial, batch_id)
            )
        storage = batch_storage_state(entry, dispatch_date)
        if not storage["within_life"]:
            holds.append(HOLD_STORAGE_LIFE)
            reasons.append("diode %s is held: %s" % (serial, storage["reason"]))

    disposition = DIODE_HELD if holds else DIODE_SHIPPABLE
    return {
        "serial": serial,
        "part_number": part_number,
        "blocking_voltage_class": voltage_class,
        "class_rank": BLOCKING_VOLTAGE_CLASSES.index(voltage_class),
        "batch_id": batch_id,
        "hold_codes": tuple(holds),
        "reasons": tuple(reasons),
        "disposition": disposition,
        "shippable": disposition == DIODE_SHIPPABLE,
    }


def assess_diodes(diodes, register, dispatch_date):
    """Disposition every offered diode, refusing a repeated serial."""
    if not isinstance(diodes, (list, tuple)) or not diodes:
        raise ValueError("diodes must be a non-empty sequence of offered parts")
    seen = set()
    out = []
    for diode in diodes:
        result = assess_diode(diode, register, dispatch_date)
        if result["serial"] in seen:
            raise ValueError("diode %s is offered twice" % result["serial"])
        seen.add(result["serial"])
        out.append(result)
    return tuple(out)


def allocate_diodes_to_lines(assessed, order):
    """Fill each order line from the shippable diodes, exact class first.

    The part number has to match outright: another part number is not a
    substitution of any kind. Inside a part number, exact class is spent
    before any permitted upgrade so a higher-class part is not consumed by
    a lower line while the higher line goes short. A lower class never
    fills a higher line.
    """
    validated = validate_order(order)
    pool = [d for d in assessed if d["shippable"]]
    taken = set()
    lines = []
    for line in validated["lines"]:
        wanted = line["ordered_count"]
        line_rank = BLOCKING_VOLTAGE_CLASSES.index(line["blocking_voltage_class"])
        candidates = sorted(
            (
                d
                for d in pool
                if d["part_number"] == line["part_number"] and d["serial"] not in taken
            ),
            key=lambda d: (d["class_rank"], d["serial"]),
        )
        allocated = []
        for diode in candidates:
            if len(allocated) >= wanted:
                break
            if diode["class_rank"] == line_rank:
                allocated.append(diode)
                taken.add(diode["serial"])
        if len(allocated) < wanted and line["allow_class_upgrade"]:
            for diode in candidates:
                if len(allocated) >= wanted:
                    break
                if diode["serial"] in taken:
                    continue
                if diode["class_rank"] > line_rank:
                    allocated.append(diode)
                    taken.add(diode["serial"])
        shipped = len(allocated)
        fill = shipped / float(wanted)
        upgraded = tuple(
            d["serial"] for d in allocated if d["class_rank"] > line_rank
        )
        if shipped >= wanted:
            state = LINE_COMPLETE
        elif fill + FILL_TOLERANCE >= validated["partial_delivery_floor"]:
            state = LINE_PARTIAL
        else:
            state = LINE_REFUSED
        lines.append(
            {
                "line_id": line["line_id"],
                "part_number": line["part_number"],
                "blocking_voltage_class": line["blocking_voltage_class"],
                "ordered_count": wanted,
                "shipped_count": shipped,
                "short_count": max(0, wanted - shipped),
                "fill_fraction": fill,
                "upgraded_serials": upgraded,
                "allocated_serials": tuple(d["serial"] for d in allocated),
                "state": state,
                "accepted": state != LINE_REFUSED,
            }
        )
    surplus = tuple(d["serial"] for d in pool if d["serial"] not in taken)
    return {"lines": tuple(lines), "surplus_serials": surplus}


def evaluate_dispatch(spec):
    """Run the clause 12.9 dispatch check over one offered shipment.

    spec keys: dispatch_id, dispatch_date, order, batch_register, diodes.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("dispatch_id", "dispatch_date", "order", "batch_register", "diodes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    dispatch_id = _identifier(spec["dispatch_id"], "dispatch_id")
    dispatch_date = parse_delivery_date(spec["dispatch_date"], "dispatch_date")
    order = validate_order(spec["order"])
    register = validate_batch_register(spec["batch_register"])
    assessed = assess_diodes(spec["diodes"], register, dispatch_date)
    allocation = allocate_diodes_to_lines(assessed, order)

    findings = []
    for diode in assessed:
        findings.extend(diode["reasons"])
    for line in allocation["lines"]:
        if line["state"] == LINE_REFUSED:
            findings.append(
                "order line %s shipped %d of %d ordered diodes, below the declared "
                "partial-delivery floor"
                % (line["line_id"], line["shipped_count"], line["ordered_count"])
            )
    for serial in allocation["surplus_serials"]:
        findings.append(
            "dispatch %s offers diode %s, which no line of order %s asks for"
            % (dispatch_id, serial, order["order_id"])
        )

    ordered_total = sum(l["ordered_count"] for l in allocation["lines"])
    shipped_total = sum(l["shipped_count"] for l in allocation["lines"])
    return {
        "dispatch_id": dispatch_id,
        "dispatch_date": dispatch_date,
        "order_id": order["order_id"],
        "diodes": assessed,
        "lines": allocation["lines"],
        "surplus_serials": allocation["surplus_serials"],
        "held_serials": tuple(d["serial"] for d in assessed if not d["shippable"]),
        "hold_codes": tuple(
            sorted({code for d in assessed for code in d["hold_codes"]})
        ),
        "upgraded_serials": tuple(
            s for l in allocation["lines"] for s in l["upgraded_serials"]
        ),
        "ordered_total": ordered_total,
        "shipped_total": shipped_total,
        "dispatch_fill_fraction": shipped_total / float(ordered_total),
        "partial": shipped_total < ordered_total,
        "findings": findings,
        "verdict": DISPATCH_RELEASABLE if not findings else DISPATCH_HELD,
        "accepted": not findings,
    }
