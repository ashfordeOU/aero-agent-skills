"""The packing a finished hybrid microcircuit lot travels in.

Anchor: ECSS-Q-ST-60-05 clause 13.3 (protective packing, electrostatic
precautions and the despatch arrangements for finished hybrid microcircuits,
so that a lot that passed every test at the manufacturer is still that lot
when it is unpacked).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Electrostatic protection is demanded by the part, not chosen by the packer.
  The withstand voltage of the most sensitive device in the shipment sets a
  protection level, and the packaging either reaches that level or it does
  not; a bag that merely does not itself generate charge is not a shield.
* Cushioning is a calculation, not a habit. The drop height the shipment has
  to survive and the deceleration the units can take give a thickness through
  the efficiency of the cushion, and any thinner is decorative.
* Moisture is a budget over time. What is sealed in at packing plus what
  crosses the barrier over the storage period has to fit inside the desiccant
  actually enclosed, and the units are counted up, never rounded down.
* A desiccant with no humidity indicator cannot be checked on arrival, so the
  receiver has to open the barrier to learn whether the barrier held.
* The transport mode carries its own envelope. Its temperature range has to
  sit inside the product limits, and a sealed container that is not vented
  will not survive the pressure change of an air leg.
* The packing-provision index is weighted credit over total weight. It ranks
  what is outstanding; a protection level below the demand, a cushion under
  thickness, a desiccant shortfall or a transport envelope outside the limits
  decides the outcome on its own, at any index.
"""

from __future__ import annotations

import math

# Withstand voltage bands and the electrostatic protection level each demands:
# 3 is a shielded, immobilised package, 1 is a dissipative wrap.
ESD_SENSITIVITY_BANDS = (
    (250.0, 3),
    (1000.0, 2),
    (4000.0, 1),
)

# Protection level above the highest band, where the part is robust.
ESD_BASE_PROTECTION_LEVEL = 0

# Electrostatic protection each packaging build actually provides.
PACKAGING_PROTECTION_LEVEL = {
    "shielding-bag-with-dissipative-rigid-carrier": 3,
    "shielding-bag": 2,
    "dissipative-bag-with-rigid-carrier": 2,
    "dissipative-bag": 1,
    "ordinary-polyethylene-bag": 0,
    "unprotected-tray": 0,
}

# Transport modes and the envelope each one exposes the shipment to.
TRANSPORT_MODES = {
    "road-freight": {"min_temp_c": -20.0, "max_temp_c": 45.0, "reduced_pressure": False},
    "rail-freight": {"min_temp_c": -25.0, "max_temp_c": 45.0, "reduced_pressure": False},
    "sea-freight": {"min_temp_c": -10.0, "max_temp_c": 55.0, "reduced_pressure": False},
    "air-freight": {"min_temp_c": -40.0, "max_temp_c": 40.0, "reduced_pressure": True},
    "courier-parcel": {"min_temp_c": -30.0, "max_temp_c": 50.0, "reduced_pressure": True},
}

# Moisture sealed into the barrier at packing, per litre of enclosed volume.
INITIAL_MOISTURE_G_PER_LITRE = 0.6

# Packing provisions and the share of the arrangement each supplies.
PACKING_PROVISION_WEIGHTS = {
    "electrostatic-protective-packaging": 1.0,
    "unit-immobilisation-in-the-carrier": 1.0,
    "cushioning-against-the-declared-drop": 1.0,
    "moisture-barrier-and-desiccant": 0.9,
    "humidity-indicator": 0.7,
    "outer-container-specification": 0.9,
    "handling-and-electrostatic-labelling": 0.9,
    "packing-list-enclosed": 0.8,
    "transport-mode-and-route-declared": 0.7,
    "unpacking-and-receiving-instruction": 0.6,
}

MANDATORY_PACKING_PROVISIONS = (
    "electrostatic-protective-packaging",
    "unit-immobilisation-in-the-carrier",
    "cushioning-against-the-declared-drop",
    "handling-and-electrostatic-labelling",
)

PROVISION_STATE_CREDIT = {
    "specified": 1.0,
    "specified-with-observation": 0.7,
    "deficient": 0.0,
    "not-specified": 0.0,
}

# Packing-provision index an acceptable arrangement has to reach.
ACCEPTANCE_PACKING_INDEX = 0.90

# Thicknesses, masses and indices are sums of products; a case meant to sit
# exactly on a bound can land a few units in the last place away from it.
PACKING_TOLERANCE = 1e-9

VERDICTS = (
    "packaging-and-despatch-acceptable",
    "packaging-and-despatch-acceptable-with-open-actions",
    "packaging-and-despatch-rejected",
    "packaging-and-despatch-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a finite positive float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite non-negative float or raise."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def required_esd_protection_level(withstand_volts):
    """Protection level the most sensitive device in the shipment demands."""
    volts = _positive(withstand_volts, "withstand_volts")
    for edge, level in ESD_SENSITIVITY_BANDS:
        if volts <= edge + PACKING_TOLERANCE:
            return level
    return ESD_BASE_PROTECTION_LEVEL


def packaging_protection_level(packaging):
    """Protection level one packaging build actually provides."""
    if packaging not in PACKAGING_PROTECTION_LEVEL:
        raise ValueError(
            "unknown packaging build %r (known: %s)"
            % (packaging, ", ".join(sorted(PACKAGING_PROTECTION_LEVEL)))
        )
    return PACKAGING_PROTECTION_LEVEL[packaging]


def esd_protection_is_sufficient(packaging, withstand_volts):
    """True when the packaging reaches the level the device demands."""
    return packaging_protection_level(packaging) >= required_esd_protection_level(
        withstand_volts
    )


def required_cushion_thickness_mm(drop_height_mm, allowable_deceleration_g, cushion_efficiency):
    """Cushion thickness the declared drop and allowable shock demand."""
    height = _positive(drop_height_mm, "drop_height_mm")
    deceleration = _positive(allowable_deceleration_g, "allowable_deceleration_g")
    efficiency = _positive(cushion_efficiency, "cushion_efficiency")
    if efficiency > 1.0:
        raise ValueError("cushion_efficiency must not exceed 1, got %r" % (cushion_efficiency,))
    return height / (deceleration * efficiency)


def cushion_findings(drop_height_mm, allowable_deceleration_g, cushion_efficiency, fitted_mm):
    """Whether the fitted cushion reaches the thickness the drop demands."""
    required = required_cushion_thickness_mm(
        drop_height_mm, allowable_deceleration_g, cushion_efficiency
    )
    fitted = _positive(fitted_mm, "fitted cushion thickness")
    findings = []
    if fitted < required - PACKING_TOLERANCE:
        findings.append("cushion-thinner-than-the-declared-drop-demands")
    return {
        "required_thickness_mm": required,
        "fitted_thickness_mm": fitted,
        "margin_mm": fitted - required,
        "sufficient": len(findings) == 0,
        "findings": findings,
    }


def required_desiccant_units(
    internal_volume_litres, barrier_transmission_g_per_month, storage_months, unit_capacity_g
):
    """Desiccant units the sealed-in moisture and the barrier leak demand."""
    volume = _positive(internal_volume_litres, "internal_volume_litres")
    transmission = _non_negative(
        barrier_transmission_g_per_month, "barrier_transmission_g_per_month"
    )
    months = _positive(storage_months, "storage_months")
    capacity = _positive(unit_capacity_g, "unit_capacity_g")
    sealed_in = INITIAL_MOISTURE_G_PER_LITRE * volume
    ingress = transmission * months
    demand_g = sealed_in + ingress
    units = int(math.ceil(demand_g / capacity - PACKING_TOLERANCE))
    if units < 1:
        units = 1
    return {
        "sealed_in_moisture_g": sealed_in,
        "ingress_moisture_g": ingress,
        "moisture_demand_g": demand_g,
        "unit_capacity_g": capacity,
        "required_units": units,
    }


def moisture_findings(demand, fitted_units, humidity_indicator_fitted):
    """Findings raised by the desiccant actually enclosed."""
    if not isinstance(demand, dict):
        raise ValueError("demand must be a mapping, got %r" % (type(demand).__name__,))
    if isinstance(fitted_units, bool) or not isinstance(fitted_units, int):
        raise ValueError("fitted_units must be a whole number, got %r" % (fitted_units,))
    if fitted_units < 0:
        raise ValueError("fitted_units must not be negative, got %r" % (fitted_units,))
    if not isinstance(humidity_indicator_fitted, bool):
        raise ValueError("humidity_indicator_fitted must be a boolean")
    required = demand["required_units"]
    findings = []
    if fitted_units < required:
        findings.append("desiccant-below-the-moisture-demand")
    if fitted_units > 0 and not humidity_indicator_fitted:
        findings.append("desiccant-enclosed-with-no-humidity-indicator")
    return {
        "required_units": required,
        "fitted_units": fitted_units,
        "shortfall_units": max(0, required - fitted_units),
        "sufficient": len(findings) == 0,
        "findings": findings,
    }


def transport_envelope(mode):
    """The envelope one transport mode exposes a shipment to."""
    if mode not in TRANSPORT_MODES:
        raise ValueError(
            "unknown transport mode %r (known: %s)" % (mode, ", ".join(sorted(TRANSPORT_MODES)))
        )
    return dict(TRANSPORT_MODES[mode])


def despatch_findings(mode, product_limits, container):
    """Findings raised by sending this container by this mode."""
    envelope = transport_envelope(mode)
    if not isinstance(product_limits, dict):
        raise ValueError(
            "product_limits must be a mapping, got %r" % (type(product_limits).__name__,)
        )
    if not isinstance(container, dict):
        raise ValueError("container must be a mapping, got %r" % (type(container).__name__,))
    lower = _real(product_limits.get("min_storage_temp_c"), "min_storage_temp_c")
    upper = _real(product_limits.get("max_storage_temp_c"), "max_storage_temp_c")
    if upper <= lower:
        raise ValueError("the product storage range must rise from its lower limit")
    findings = []
    if envelope["min_temp_c"] < lower - PACKING_TOLERANCE:
        findings.append("transport-cold-end-below-the-product-limit")
    if envelope["max_temp_c"] > upper + PACKING_TOLERANCE:
        findings.append("transport-hot-end-above-the-product-limit")
    if envelope["reduced_pressure"] and _flag(container, "sealed") and not _flag(
        container, "pressure_vented"
    ):
        findings.append("sealed-container-not-vented-for-a-reduced-pressure-leg")
    if not _flag(container, "packing_list_enclosed"):
        findings.append("no-packing-list-enclosed-with-the-shipment")
    if not _flag(container, "electrostatic_label_applied"):
        findings.append("no-electrostatic-handling-label-on-the-container")
    return {
        "mode": mode,
        "envelope": envelope,
        "product_min_temp_c": lower,
        "product_max_temp_c": upper,
        "acceptable": len(findings) == 0,
        "findings": findings,
    }


def packing_provision_weight(name):
    """Weight of one packing provision; unknown names are rejected."""
    if name not in PACKING_PROVISION_WEIGHTS:
        raise ValueError(
            "unknown packing provision %r (known: %s)"
            % (name, ", ".join(sorted(PACKING_PROVISION_WEIGHTS)))
        )
    return PACKING_PROVISION_WEIGHTS[name]


def provision_state_credit(state):
    """Credit a packing-provision state earns."""
    if state not in PROVISION_STATE_CREDIT:
        raise ValueError(
            "unknown provision state %r (known: %s)"
            % (state, ", ".join(sorted(PROVISION_STATE_CREDIT)))
        )
    return PROVISION_STATE_CREDIT[state]


def normalize_provision(raw):
    """Validate one packing-provision record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("provision must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("provision")
    packing_provision_weight(name)  # validation only
    state = raw.get("state", "not-specified")
    provision_state_credit(state)  # validation only
    return {"provision": name, "state": state}


def assess_provision(raw):
    """Grade one packing provision into a credit and its findings."""
    record = normalize_provision(raw)
    name = record["provision"]
    state = record["state"]
    weight = packing_provision_weight(name)
    credit = provision_state_credit(state)
    findings = []
    if state == "specified-with-observation":
        findings.append("packing-provision-observation-open")
    elif state == "deficient":
        findings.append("packing-provision-deficient")
    elif state == "not-specified":
        findings.append("packing-provision-not-specified")
    mandatory = name in MANDATORY_PACKING_PROVISIONS
    return {
        "provision": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "not-specified",
        "mandatory_deficient": mandatory and state == "deficient",
        "findings": findings,
    }


def packing_provision_index(records):
    """Weighted credit of a set of graded provisions over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a packing arrangement must specify at least one provision")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total packing provision weight must be positive")
    return earned / total_weight


def assess_packaging_and_despatch(
    shipment_id, device, packaging, drop, moisture, despatch, provisions
):
    """Grade a whole packing and despatch arrangement and name one verdict."""
    if not isinstance(shipment_id, str) or not shipment_id.strip():
        raise ValueError("shipment_id must be a non-empty string, got %r" % (shipment_id,))
    for label, value in (
        ("device", device),
        ("packaging", packaging),
        ("drop", drop),
        ("moisture", moisture),
        ("despatch", despatch),
    ):
        if not isinstance(value, dict):
            raise ValueError("%s must be a mapping, got %r" % (label, type(value).__name__))
    if not isinstance(provisions, (list, tuple)):
        raise ValueError(
            "provisions must be a list or tuple, got %r" % (type(provisions).__name__,)
        )

    build = packaging.get("build")
    withstand = device.get("withstand_volts")
    demanded_level = required_esd_protection_level(withstand)
    provided_level = packaging_protection_level(build)
    esd_ok = provided_level >= demanded_level

    cushion = cushion_findings(
        drop.get("drop_height_mm"),
        drop.get("allowable_deceleration_g"),
        drop.get("cushion_efficiency"),
        drop.get("fitted_thickness_mm"),
    )
    demand = required_desiccant_units(
        moisture.get("internal_volume_litres"),
        moisture.get("barrier_transmission_g_per_month"),
        moisture.get("storage_months"),
        moisture.get("unit_capacity_g"),
    )
    desiccant = moisture_findings(
        demand, moisture.get("fitted_units"), _flag(moisture, "humidity_indicator_fitted")
    )
    transport = despatch_findings(
        despatch.get("mode"), device.get("limits"), despatch.get("container")
    )

    declared = {}
    for raw in provisions:
        record = normalize_provision(raw)
        if record["provision"] in declared:
            raise ValueError("duplicate packing provision %r" % (record["provision"],))
        declared[record["provision"]] = record
    graded = []
    for name in sorted(PACKING_PROVISION_WEIGHTS):
        graded.append(assess_provision(declared.get(name, {"provision": name})))
    index = packing_provision_index(graded)

    findings = []
    if not esd_ok:
        findings.append(
            {
                "item": build,
                "finding": "electrostatic-protection-below-the-level-the-device-demands",
                "detail": "level %d against %d demanded" % (provided_level, demanded_level),
            }
        )
    for finding in cushion["findings"]:
        findings.append({"item": "cushioning", "finding": finding, "detail": shipment_id})
    for finding in desiccant["findings"]:
        findings.append({"item": "desiccant", "finding": finding, "detail": shipment_id})
    for finding in transport["findings"]:
        findings.append({"item": transport["mode"], "finding": finding, "detail": shipment_id})
    for record in graded:
        for finding in record["findings"]:
            findings.append(
                {"item": record["provision"], "finding": finding, "detail": record["state"]}
            )

    incomplete = any(record["mandatory_missing"] for record in graded)
    rejected = (
        not esd_ok
        or not cushion["sufficient"]
        or not desiccant["sufficient"]
        or not transport["acceptable"]
        or any(record["mandatory_deficient"] for record in graded)
        or index < ACCEPTANCE_PACKING_INDEX - PACKING_TOLERANCE
    )
    if incomplete:
        verdict = "packaging-and-despatch-assessment-incomplete"
    elif rejected:
        verdict = "packaging-and-despatch-rejected"
    elif findings:
        verdict = "packaging-and-despatch-acceptable-with-open-actions"
    else:
        verdict = "packaging-and-despatch-acceptable"
    return {
        "shipment_id": shipment_id,
        "required_esd_protection_level": demanded_level,
        "provided_esd_protection_level": provided_level,
        "esd_protection_sufficient": esd_ok,
        "cushion": cushion,
        "moisture_demand": demand,
        "desiccant": desiccant,
        "despatch": transport,
        "provisions": graded,
        "packing_provision_index": index,
        "findings": findings,
        "verdict": verdict,
        "shipment_released": verdict
        in (
            "packaging-and-despatch-acceptable",
            "packaging-and-despatch-acceptable-with-open-actions",
        ),
    }
