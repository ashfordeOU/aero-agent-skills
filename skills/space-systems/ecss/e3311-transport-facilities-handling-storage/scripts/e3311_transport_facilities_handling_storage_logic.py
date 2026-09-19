"""Transport, facilities, handling and storage control for explosive items.

Anchor: ECSS-E-ST-33-11C Rev.1 clause 4.15 (transport, facilities, handling and
storage of explosive subsystems and devices). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Group the items held in a facility by compatibility group and report every
   pair that must not share a magazine.
2. Aggregate the net explosive quantity actually present and compare it with
   the quantity the facility is licensed to hold.
3. Derive the quantity-distance separation from the cube-root scaling law and
   grade the real distance to the exposed site against it.
4. Grade the storage environment against the item's own storage envelope.
5. Grade a handling operation on the controls that keep an item inert while
   people are near it: bonding, personnel limit, radio-frequency exclusion and
   the safing device.
6. Grade a shipment on its qualified container, its safed state and a declared
   net explosive quantity that matches what is in the package.
"""

import math

__all__ = [
    "DISTANCE_TOLERANCE",
    "COMPATIBILITY_GROUPS",
    "ISOLATION_GROUPS",
    "SELF_AND_S_GROUPS",
    "MIXABLE_GROUPS",
    "validate_positive",
    "validate_non_negative",
    "normalize_group",
    "groups_compatible",
    "cube_root",
    "net_explosive_quantity",
    "quantity_distance_m",
    "magazine_compatibility",
    "licensed_limit_verdict",
    "separation_verdict",
    "environment_verdict",
    "handling_verdict",
    "transport_verdict",
    "assess_storage_site",
]

# Distances come out of a cube root, which is not correctly rounded. Absorb the
# representation error at the comparison instead of padding the distance.
DISTANCE_TOLERANCE = 1e-9

# Compatibility groups used for explosive stores.
COMPATIBILITY_GROUPS = ("A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "N", "S")

# Stored on their own: nothing else shares the magazine.
ISOLATION_GROUPS = frozenset({"A", "K", "L"})

# Stored with their own group, and with group S.
SELF_AND_S_GROUPS = frozenset({"B", "F", "H", "J", "N"})

# Stored with each other and with group S.
MIXABLE_GROUPS = frozenset({"C", "D", "E", "G"})


def validate_positive(label, value):
    """Return value as a strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_non_negative(label, value):
    """Return value as a non-negative finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _validate_flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def normalize_group(code):
    """Return the canonical compatibility-group letter."""
    if not isinstance(code, str):
        raise ValueError("compatibility group must be a string, got %r" % (code,))
    letter = code.strip().upper()
    if letter not in COMPATIBILITY_GROUPS:
        raise ValueError(
            "unknown compatibility group %r; known groups are %s"
            % (code, ", ".join(COMPATIBILITY_GROUPS))
        )
    return letter


def groups_compatible(first, second):
    """True when two compatibility groups may share one magazine."""
    a = normalize_group(first)
    b = normalize_group(second)
    if a == b:
        return True
    if a in ISOLATION_GROUPS or b in ISOLATION_GROUPS:
        return False
    if a == "S" or b == "S":
        return True
    if a in MIXABLE_GROUPS and b in MIXABLE_GROUPS:
        return True
    return False


def cube_root(value):
    """Return the cube root of a non-negative value, snapped to an exact root."""
    number = validate_non_negative("value", value)
    if number == 0.0:
        return 0.0
    root = number ** (1.0 / 3.0)
    nearest = round(root)
    if nearest > 0 and math.isclose(
        float(nearest) ** 3, number, rel_tol=1e-12, abs_tol=0.0
    ):
        return float(nearest)
    return root


def net_explosive_quantity(items):
    """Return the total net explosive quantity in kilograms of a set of items."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a sequence of item mappings")
    total = 0.0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        for key in ("neq_kg", "count"):
            if key not in item:
                raise ValueError("items[%d] missing '%s'" % (index, key))
        count = item["count"]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("items[%d]['count'] must be a non-negative integer" % index)
        total += validate_non_negative("items[%d]['neq_kg']" % index, item["neq_kg"]) * count
    return total


def quantity_distance_m(neq_kg, k_factor):
    """Return the separation distance required by the cube-root scaling law."""
    neq = validate_non_negative("neq_kg", neq_kg)
    k = validate_positive("k_factor", k_factor)
    return k * cube_root(neq)


def magazine_compatibility(items):
    """Report every pair of items in one magazine that must not share it."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of item mappings")
    entries = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        for key in ("item_id", "compatibility_group"):
            if key not in item:
                raise ValueError("items[%d] missing '%s'" % (index, key))
        if not isinstance(item["item_id"], str) or not item["item_id"].strip():
            raise ValueError("items[%d]['item_id'] must be a non-empty string" % index)
        entries.append((item["item_id"].strip(), normalize_group(item["compatibility_group"])))
    findings = []
    conflicts = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            if not groups_compatible(entries[i][1], entries[j][1]):
                conflicts.append((entries[i][0], entries[j][0]))
                findings.append(
                    "%s (group %s) must not share a magazine with %s (group %s)"
                    % (entries[i][0], entries[i][1], entries[j][0], entries[j][1])
                )
    return {
        "groups": sorted({group for _, group in entries}),
        "conflicts": conflicts,
        "segregated": not findings,
        "findings": findings,
    }


def licensed_limit_verdict(neq_kg, licensed_limit_kg):
    """Grade the explosive quantity held against the facility licence."""
    held = validate_non_negative("neq_kg", neq_kg)
    limit = validate_positive("licensed_limit_kg", licensed_limit_kg)
    over = held > limit and not math.isclose(
        held, limit, rel_tol=DISTANCE_TOLERANCE, abs_tol=0.0
    )
    findings = []
    if over:
        findings.append(
            "facility holds %.6g kg against a licensed %.6g kg" % (held, limit)
        )
    return {
        "held_kg": held,
        "licensed_kg": limit,
        "within_licence": not over,
        "findings": findings,
    }


def separation_verdict(neq_kg, k_factor, actual_distance_m, exposed_site="exposed site"):
    """Grade the real distance to an exposed site against the required separation."""
    required = quantity_distance_m(neq_kg, k_factor)
    actual = validate_non_negative("actual_distance_m", actual_distance_m)
    if not isinstance(exposed_site, str) or not exposed_site.strip():
        raise ValueError("exposed_site must be a non-empty string")
    short = actual < required and not math.isclose(
        actual, required, rel_tol=DISTANCE_TOLERANCE, abs_tol=0.0
    )
    findings = []
    if short:
        findings.append(
            "%s sits %.6g m away against a required %.6g m"
            % (exposed_site.strip(), actual, required)
        )
    return {
        "exposed_site": exposed_site.strip(),
        "required_m": required,
        "actual_m": actual,
        "adequate": not short,
        "findings": findings,
    }


def environment_verdict(measured, limits):
    """Grade a storage environment against the item's storage envelope."""
    for label, mapping in (("measured", measured), ("limits", limits)):
        if not isinstance(mapping, dict):
            raise ValueError("%s must be a mapping" % label)
    for key in ("temperature_c", "humidity_pct"):
        if key not in measured:
            raise ValueError("measured missing '%s'" % key)
    for key in ("temperature_min_c", "temperature_max_c", "humidity_max_pct"):
        if key not in limits:
            raise ValueError("limits missing '%s'" % key)
    temperature = measured["temperature_c"]
    if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
        raise ValueError("measured['temperature_c'] must be a real number")
    temperature = float(temperature)
    if not math.isfinite(temperature):
        raise ValueError("measured['temperature_c'] must be finite")
    humidity = validate_non_negative("measured['humidity_pct']", measured["humidity_pct"])
    t_min = float(limits["temperature_min_c"])
    t_max = float(limits["temperature_max_c"])
    if t_min > t_max:
        raise ValueError("limits temperature range is inverted")
    h_max = validate_positive("limits['humidity_max_pct']", limits["humidity_max_pct"])
    findings = []
    if temperature < t_min and not math.isclose(temperature, t_min, rel_tol=0.0, abs_tol=DISTANCE_TOLERANCE):
        findings.append("storage temperature %.6g C is below the envelope %.6g C" % (temperature, t_min))
    if temperature > t_max and not math.isclose(temperature, t_max, rel_tol=0.0, abs_tol=DISTANCE_TOLERANCE):
        findings.append("storage temperature %.6g C is above the envelope %.6g C" % (temperature, t_max))
    if humidity > h_max and not math.isclose(humidity, h_max, rel_tol=0.0, abs_tol=DISTANCE_TOLERANCE):
        findings.append("storage humidity %.6g %% is above the envelope %.6g %%" % (humidity, h_max))
    return {
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "within_envelope": not findings,
        "findings": findings,
    }


def handling_verdict(operation):
    """Grade one handling operation on its inertness controls."""
    if not isinstance(operation, dict):
        raise ValueError("operation must be a mapping")
    for key in ("operation_id", "bonded", "personnel_present", "personnel_limit",
                "rf_transmitter_distance_m", "rf_exclusion_m", "safing_device_fitted"):
        if key not in operation:
            raise ValueError("operation missing '%s'" % key)
    if not isinstance(operation["operation_id"], str) or not operation["operation_id"].strip():
        raise ValueError("operation['operation_id'] must be a non-empty string")
    bonded = _validate_flag("bonded", operation["bonded"])
    safed = _validate_flag("safing_device_fitted", operation["safing_device_fitted"])
    for key in ("personnel_present", "personnel_limit"):
        value = operation[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("operation['%s'] must be a non-negative integer" % key)
    distance = validate_non_negative(
        "operation['rf_transmitter_distance_m']", operation["rf_transmitter_distance_m"]
    )
    exclusion = validate_positive(
        "operation['rf_exclusion_m']", operation["rf_exclusion_m"]
    )
    findings = []
    if not bonded:
        findings.append("handling point is not bonded, so an electrostatic path is open")
    if not safed:
        findings.append("item handled without its safing device fitted")
    if operation["personnel_present"] > operation["personnel_limit"]:
        findings.append(
            "%d people present against a limit of %d"
            % (operation["personnel_present"], operation["personnel_limit"])
        )
    if distance < exclusion and not math.isclose(
        distance, exclusion, rel_tol=DISTANCE_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "radio transmitter %.6g m away against an exclusion of %.6g m"
            % (distance, exclusion)
        )
    return {
        "operation_id": operation["operation_id"].strip(),
        "controlled": not findings,
        "findings": findings,
    }


def transport_verdict(shipment):
    """Grade one shipment of explosive items."""
    if not isinstance(shipment, dict):
        raise ValueError("shipment must be a mapping")
    for key in ("shipment_id", "container_qualified", "safing_device_fitted",
                "declared_neq_kg", "items"):
        if key not in shipment:
            raise ValueError("shipment missing '%s'" % key)
    if not isinstance(shipment["shipment_id"], str) or not shipment["shipment_id"].strip():
        raise ValueError("shipment['shipment_id'] must be a non-empty string")
    qualified = _validate_flag("container_qualified", shipment["container_qualified"])
    safed = _validate_flag("safing_device_fitted", shipment["safing_device_fitted"])
    declared = validate_non_negative("declared_neq_kg", shipment["declared_neq_kg"])
    actual = net_explosive_quantity(shipment["items"])
    findings = []
    if not qualified:
        findings.append("shipment travels in a container that is not qualified for it")
    if not safed:
        findings.append("shipment travels without the safing device fitted")
    if not math.isclose(declared, actual, rel_tol=1e-9, abs_tol=1e-9):
        findings.append(
            "declared net explosive quantity %.6g kg does not match the %.6g kg packed"
            % (declared, actual)
        )
    compat = magazine_compatibility(shipment["items"]) if shipment["items"] else None
    if compat is not None:
        findings.extend(
            f.replace("share a magazine", "travel in one load") for f in compat["findings"]
        )
    return {
        "shipment_id": shipment["shipment_id"].strip(),
        "declared_neq_kg": declared,
        "actual_neq_kg": actual,
        "acceptable": not findings,
        "findings": findings,
    }


def assess_storage_site(spec):
    """Run the full clause 4.15 transport, facility, handling and storage assessment.

    spec keys: magazine (items, licensed_limit_kg, k_factor, exposed_sites),
    environment (measured, limits), optional handling (sequence of operations)
    and shipments (sequence of shipment mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("magazine", "environment"):
        if key not in spec or not isinstance(spec[key], dict):
            raise ValueError("spec['%s'] must be a mapping" % key)
    magazine = spec["magazine"]
    for key in ("items", "licensed_limit_kg", "k_factor", "exposed_sites"):
        if key not in magazine:
            raise ValueError("spec['magazine'] missing '%s'" % key)
    compat = magazine_compatibility(magazine["items"])
    held = net_explosive_quantity(magazine["items"])
    licence = licensed_limit_verdict(held, magazine["licensed_limit_kg"])
    separations = []
    if not isinstance(magazine["exposed_sites"], (list, tuple)):
        raise ValueError("spec['magazine']['exposed_sites'] must be a sequence")
    for site in magazine["exposed_sites"]:
        if not isinstance(site, dict) or "name" not in site or "distance_m" not in site:
            raise ValueError("each exposed site needs 'name' and 'distance_m'")
        separations.append(
            separation_verdict(held, magazine["k_factor"], site["distance_m"], site["name"])
        )
    environment = environment_verdict(
        spec["environment"].get("measured", {}), spec["environment"].get("limits", {})
    )
    handling = []
    for operation in spec.get("handling") or []:
        handling.append(handling_verdict(operation))
    shipments = []
    for shipment in spec.get("shipments") or []:
        shipments.append(transport_verdict(shipment))
    findings = list(compat["findings"]) + list(licence["findings"])
    for item in separations:
        findings.extend(item["findings"])
    findings.extend(environment["findings"])
    for item in handling:
        findings.extend(item["findings"])
    for item in shipments:
        findings.extend(item["findings"])
    return {
        "compatibility": compat,
        "net_explosive_quantity_kg": held,
        "licence": licence,
        "separations": separations,
        "environment": environment,
        "handling": handling,
        "shipments": shipments,
        "controlled": not findings,
        "findings": findings,
    }
