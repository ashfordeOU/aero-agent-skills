"""Ground equipment: applicable EU legislation, CE marking and the declaration.

Anchor: ECSS-Q-ST-40C clause on declarations of conformity for ground
equipment, with the annex that points at CE marking and the applicability of EU
legislation. Paraphrased into an implementable procedure; no standard text is
reproduced, and the thresholds below are the publicly stated bounds of the EU
instruments, restated for screening only.

Procedure implemented here
--------------------------
1. Work out WHICH EU instruments an item falls under from what the item is and
   does, not from what it is called. A test bench is not a category; a moving
   assembly with a power drive, a vessel above a pressure-volume product, and
   a mains-fed electrical enclosure each are.
2. A pressure item below the pressure-volume product is not exempt from care.
   It falls to sound engineering practice, which is a real route with real
   duties -- and no CE marking under that instrument, which is where screening
   usually goes wrong in the other direction.
3. Decide the assessment route. Some combinations cannot be self-declared and
   need a notified body, and that is a schedule and cost fact, not a formality.
4. A declaration of conformity can only be issued when the things it asserts
   exist: a named responsible entity, an identified item, a technical file, a
   listed set of applicable instruments, and either the standards applied or
   the notified body certificate when one is required.
5. Report what applies, the route, whether the mark is required, and what is
   still missing before the declaration can be signed.
"""

__all__ = [
    "INSTRUMENTS",
    "PRESSURE_VOLUME_THRESHOLD_BAR_LITRE",
    "MIN_PRESSURE_BAR",
    "AC_LOW_VOLTAGE_BAND_V",
    "DC_LOW_VOLTAGE_BAND_V",
    "EXPLOSIVE_ZONES",
    "NOTIFIED_BODY_ZONES",
    "THRESHOLD_TOLERANCE",
    "validate_item",
    "pressure_volume_product",
    "applicable_instruments",
    "notified_body_required",
    "ce_marking_required",
    "declaration_blockers",
    "assess_conformity",
    "assess_equipment_set",
]

INSTRUMENTS = (
    "machinery",
    "pressure-equipment",
    "sound-engineering-practice",
    "low-voltage",
    "electromagnetic-compatibility",
    "equipment-for-explosive-atmospheres",
    "lifting-accessory",
)

# Pressure times volume, in bar-litre, above which the pressure instrument
# bites rather than the sound-engineering-practice route.
PRESSURE_VOLUME_THRESHOLD_BAR_LITRE = 50.0

# Below this gauge pressure the item is not pressure equipment at all.
MIN_PRESSURE_BAR = 0.5

# Voltage bands, in volts, inside which the low-voltage instrument applies.
AC_LOW_VOLTAGE_BAND_V = (50.0, 1000.0)
DC_LOW_VOLTAGE_BAND_V = (75.0, 1500.0)

EXPLOSIVE_ZONES = ("zone-0", "zone-1", "zone-2", "none")

# Explosive-atmosphere zones whose equipment cannot be self-declared.
NOTIFIED_BODY_ZONES = ("zone-0", "zone-1")

# Thresholds are compared against products and sums of floats; carry slack so
# an item sitting exactly on a bound grades the same on every machine.
THRESHOLD_TOLERANCE = 1e-9


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _optional_text(value, label):
    if value is None:
        return None
    return _text(value, label)


def _number(value, label, minimum=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < minimum:
        raise ValueError("%s must be at least %g, got %g" % (label, minimum, number))
    return number


def _flag(record, key):
    value = record.get(key, False)
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (key, value))
    return value


def validate_item(record):
    """Return a normalised ground-equipment item description."""
    if not isinstance(record, dict):
        raise ValueError("item must be a mapping")
    zone = record.get("explosive_atmosphere_zone", "none")
    zone = _text(zone, "explosive_atmosphere_zone").lower()
    if zone not in EXPLOSIVE_ZONES:
        raise ValueError(
            "explosive_atmosphere_zone must be one of %s, got %r"
            % (", ".join(EXPLOSIVE_ZONES), zone)
        )
    standards = record.get("harmonised_standards", [])
    if not isinstance(standards, (list, tuple)):
        raise ValueError("harmonised_standards must be a sequence")
    standards = [_text(item, "harmonised standard") for item in standards]
    return {
        "id": _text(record.get("id"), "id"),
        "powered_moving_assembly": _flag(record, "powered_moving_assembly"),
        "annex_iv_machinery": _flag(record, "annex_iv_machinery"),
        "design_pressure_bar": _number(record.get("design_pressure_bar", 0.0),
                                       "design_pressure_bar"),
        "volume_litre": _number(record.get("volume_litre", 0.0), "volume_litre"),
        "lifting_accessory": _flag(record, "lifting_accessory"),
        "ac_supply_v": _number(record.get("ac_supply_v", 0.0), "ac_supply_v"),
        "dc_supply_v": _number(record.get("dc_supply_v", 0.0), "dc_supply_v"),
        "contains_electronics": _flag(record, "contains_electronics"),
        "explosive_atmosphere_zone": zone,
        "responsible_entity": _optional_text(record.get("responsible_entity"),
                                             "responsible_entity"),
        "technical_file_ref": _optional_text(record.get("technical_file_ref"),
                                             "technical_file_ref"),
        "notified_body_certificate_ref": _optional_text(
            record.get("notified_body_certificate_ref"), "notified_body_certificate_ref"
        ),
        "harmonised_standards": standards,
    }


def pressure_volume_product(record):
    """Return the pressure-volume product, in bar-litre, that sets the route."""
    norm = validate_item(record)
    return norm["design_pressure_bar"] * norm["volume_litre"]


def applicable_instruments(record):
    """Return the EU instruments this ground-equipment item falls under."""
    norm = validate_item(record)
    found = []

    if norm["powered_moving_assembly"] or norm["annex_iv_machinery"]:
        found.append("machinery")

    if norm["design_pressure_bar"] > MIN_PRESSURE_BAR + THRESHOLD_TOLERANCE:
        product = pressure_volume_product(norm)
        if product > PRESSURE_VOLUME_THRESHOLD_BAR_LITRE + THRESHOLD_TOLERANCE:
            found.append("pressure-equipment")
        else:
            found.append("sound-engineering-practice")

    if norm["lifting_accessory"]:
        found.append("lifting-accessory")

    ac_low, ac_high = AC_LOW_VOLTAGE_BAND_V
    dc_low, dc_high = DC_LOW_VOLTAGE_BAND_V
    ac_in_band = (
        norm["ac_supply_v"] + THRESHOLD_TOLERANCE >= ac_low
        and norm["ac_supply_v"] <= ac_high + THRESHOLD_TOLERANCE
    )
    dc_in_band = (
        norm["dc_supply_v"] + THRESHOLD_TOLERANCE >= dc_low
        and norm["dc_supply_v"] <= dc_high + THRESHOLD_TOLERANCE
    )
    if ac_in_band or dc_in_band:
        found.append("low-voltage")

    if norm["contains_electronics"]:
        found.append("electromagnetic-compatibility")

    if norm["explosive_atmosphere_zone"] != "none":
        found.append("equipment-for-explosive-atmospheres")

    return found


def notified_body_required(record):
    """Return whether the assessment route needs a third party involved."""
    norm = validate_item(record)
    instruments = applicable_instruments(norm)
    if norm["annex_iv_machinery"]:
        return True
    if "pressure-equipment" in instruments:
        return True
    if norm["explosive_atmosphere_zone"] in NOTIFIED_BODY_ZONES:
        return True
    return False


def ce_marking_required(record):
    """Return whether the item carries the conformity mark at all."""
    instruments = applicable_instruments(record)
    marked = [item for item in instruments if item != "sound-engineering-practice"]
    return bool(marked)


def declaration_blockers(record):
    """Return what is still missing before a declaration can be signed."""
    norm = validate_item(record)
    instruments = applicable_instruments(norm)
    blockers = []

    if not ce_marking_required(norm):
        if "sound-engineering-practice" in instruments:
            blockers.append(
                "item falls only to sound engineering practice, so there is no"
                " declaration of conformity to issue under that route"
            )
        else:
            blockers.append(
                "no EU instrument was found applicable, so nothing is being declared"
            )
        return blockers

    if norm["responsible_entity"] is None:
        blockers.append("no responsible entity is named to sign the declaration")
    if norm["technical_file_ref"] is None:
        blockers.append("no technical file is referenced behind the declaration")
    if notified_body_required(norm) and norm["notified_body_certificate_ref"] is None:
        blockers.append(
            "the route needs a notified body and no certificate is referenced"
        )
    if not notified_body_required(norm) and not norm["harmonised_standards"]:
        blockers.append(
            "a self-declared route needs the standards applied to be listed"
        )
    return blockers


def assess_conformity(record):
    """Return the conformity screening and declaration status for one item."""
    norm = validate_item(record)
    instruments = applicable_instruments(norm)
    needs_body = notified_body_required(norm)
    blockers = declaration_blockers(norm)
    route = "notified-body-assessment" if needs_body else "manufacturer-self-assessment"
    if not ce_marking_required(norm):
        route = (
            "sound-engineering-practice"
            if "sound-engineering-practice" in instruments
            else "no-route-identified"
        )
    return {
        "id": norm["id"],
        "applicable_instruments": instruments,
        "pressure_volume_product_bar_litre": pressure_volume_product(norm),
        "ce_marking_required": ce_marking_required(norm),
        "notified_body_required": needs_body,
        "conformity_route": route,
        "blockers": blockers,
        "declaration_issuable": not blockers,
        "disposition": "declaration-issuable" if not blockers else "declaration-blocked",
    }


def assess_equipment_set(records):
    """Return the conformity rollup across a set of ground-equipment items."""
    items = list(records)
    if not items:
        raise ValueError("at least one ground-equipment item is needed")
    reports = [assess_conformity(item) for item in items]
    seen = set()
    for report in reports:
        if report["id"] in seen:
            raise ValueError("duplicate item id %r" % report["id"])
        seen.add(report["id"])
    blocked = [r["id"] for r in reports if not r["declaration_issuable"]]
    third_party = [r["id"] for r in reports if r["notified_body_required"]]
    issuable_ratio = sum(1 for r in reports if r["declaration_issuable"]) / float(len(reports))
    return {
        "items": reports,
        "blocked_ids": blocked,
        "notified_body_ids": third_party,
        "issuable_ratio": issuable_ratio,
        "disposition": "set-declarable" if not blocked else "set-blocked",
    }
