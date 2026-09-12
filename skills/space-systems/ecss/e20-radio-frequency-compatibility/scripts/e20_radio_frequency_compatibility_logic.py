#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.6 radio frequency compatibility of
antenna-connected equipment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the spacecraft to be shown
compatible with every unit connected to an antenna, and requires the
judgement to be made against the mission performance criteria rather
than against an abstract emission limit. This module implements the
checkable part of that clause: categorization of a unit as a
transmitter, a receiver or a transceiver, propagation of transmitter
power to a victim receiver input through antenna-to-antenna isolation
and front-end filter rejection, generation of the intermodulation
products of an emitter pair up to a chosen order and screening of those
products against the victim receive band, the interference margin
against the victim susceptibility threshold, and conversion of the
coupled power into a noise-floor degradation checked against the
mission budget. It does not synthesise a filter, does not compute
antenna patterns, and does not perform a link budget.
"""

import math

TRANSMIT_ONLY_KINDS = frozenset(
    {
        "telemetry_transmitter",
        "payload_downlink_transmitter",
        "radar_altimeter_transmitter",
        "beacon_transmitter",
    }
)
RECEIVE_ONLY_KINDS = frozenset(
    {
        "telecommand_receiver",
        "navigation_signal_receiver",
        "radiometer_receiver",
        "science_antenna_receiver",
    }
)
TRANSCEIVER_KINDS = frozenset(
    {
        "coherent_transponder",
        "inter_satellite_link_terminal",
        "proximity_link_transceiver",
    }
)

DEFAULT_REQUIRED_MARGIN_DB = 6.0
DEFAULT_MAX_DEGRADATION_DB = 0.5
DEFAULT_MAX_PRODUCT_ORDER = 5

RF_REL_TOL = 1e-9
RF_ABS_TOL = 1e-9


def categorize_rf_equipment(equipment_kind):
    """Role of an antenna-connected unit: "transmitter", "receiver" or
    "transceiver". Raises ValueError for a kind that is not a clause
    6.3.6 antenna-connected unit."""
    if equipment_kind in TRANSMIT_ONLY_KINDS:
        return "transmitter"
    if equipment_kind in RECEIVE_ONLY_KINDS:
        return "receiver"
    if equipment_kind in TRANSCEIVER_KINDS:
        return "transceiver"
    raise ValueError(
        "unrecognized antenna-connected equipment %r under "
        "E-ST-20C clause 6.3.6" % (equipment_kind,)
    )


def can_emit(equipment_kind):
    """True when the unit puts power into an antenna. Raises ValueError
    through categorize_rf_equipment."""
    return categorize_rf_equipment(equipment_kind) in (
        "transmitter",
        "transceiver",
    )


def can_receive(equipment_kind):
    """True when the unit takes power from an antenna and can therefore
    be a victim. Raises ValueError through categorize_rf_equipment."""
    return categorize_rf_equipment(equipment_kind) in (
        "receiver",
        "transceiver",
    )


def role_findings(victim_id, victim_kind, emitters):
    """Findings (empty when the roles are consistent) for the scenario
    roles: a victim that cannot receive, and any emitter in the list
    that cannot transmit. Raises ValueError through
    categorize_rf_equipment for an unrecognized unit."""
    findings = []
    if not can_receive(victim_kind):
        findings.append(
            {
                "issue": "victim_unit_has_no_receive_role",
                "victim": victim_id,
                "equipment_kind": victim_kind,
            }
        )
    for emitter in emitters:
        if not can_emit(emitter["equipment_kind"]):
            findings.append(
                {
                    "issue": "emitter_unit_has_no_transmit_role",
                    "victim": victim_id,
                    "emitter": emitter["emitter_id"],
                    "equipment_kind": emitter["equipment_kind"],
                }
            )
    return findings


def dbm_to_watt(power_dbm):
    """Convert dBm to watts. Raises ValueError for a value that is not
    finite."""
    if not math.isfinite(power_dbm):
        raise ValueError("power_dbm must be a finite value")
    return 10.0 ** ((power_dbm - 30.0) / 10.0)


def watt_to_dbm(power_w):
    """Convert watts to dBm. Raises ValueError for a non-positive
    power (there is no decibel value for zero power)."""
    if power_w <= 0:
        raise ValueError("power_w must be > 0")
    return 10.0 * math.log10(power_w) + 30.0


def coupled_power_dbm(
    transmit_power_dbm, isolation_db, filter_rejection_db
):
    """Power arriving at a victim receiver input from one emitter:
    transmit power less the antenna-to-antenna isolation and less the
    victim front-end rejection at the emitter frequency. Raises
    ValueError for a non-finite transmit power or a negative isolation
    or rejection (both are losses and cannot be gains here)."""
    if not math.isfinite(transmit_power_dbm):
        raise ValueError("transmit_power_dbm must be a finite value")
    if isolation_db < 0:
        raise ValueError("isolation_db must be >= 0")
    if filter_rejection_db < 0:
        raise ValueError("filter_rejection_db must be >= 0")
    return transmit_power_dbm - isolation_db - filter_rejection_db


def interference_margin_db(coupled_dbm, susceptibility_threshold_dbm):
    """Margin in decibels between the victim susceptibility threshold
    and the power actually coupled into it. Positive means the victim
    sits below the level that disturbs it. Raises ValueError for a
    non-finite input."""
    for name, value in (
        ("coupled_dbm", coupled_dbm),
        ("susceptibility_threshold_dbm", susceptibility_threshold_dbm),
    ):
        if not math.isfinite(value):
            raise ValueError("%s must be a finite value" % (name,))
    return susceptibility_threshold_dbm - coupled_dbm


def noise_floor_degradation_db(noise_floor_dbm, interference_dbm):
    """Rise of the victim noise floor in decibels once the interference
    power adds to it: ten times the base-ten logarithm of one plus the
    interference-to-noise power ratio. Raises ValueError for a
    non-finite input."""
    for name, value in (
        ("noise_floor_dbm", noise_floor_dbm),
        ("interference_dbm", interference_dbm),
    ):
        if not math.isfinite(value):
            raise ValueError("%s must be a finite value" % (name,))
    ratio = 10.0 ** ((interference_dbm - noise_floor_dbm) / 10.0)
    return 10.0 * math.log10(1.0 + ratio)


def combined_interference_dbm(power_list_dbm):
    """Total interference power in dBm from a list of uncorrelated
    contributions, summed in linear power. Raises ValueError for an
    empty list or a non-finite entry."""
    if not power_list_dbm:
        raise ValueError("power_list_dbm must carry at least one entry")
    total_w = 0.0
    for power_dbm in power_list_dbm:
        total_w += dbm_to_watt(power_dbm)
    return watt_to_dbm(total_w)


def intermodulation_products_hz(
    first_frequency_hz, second_frequency_hz, max_order=DEFAULT_MAX_PRODUCT_ORDER
):
    """Sorted intermodulation products of two emitter frequencies up to
    max_order.

    Every combination of positive integer coefficients whose sum does
    not exceed max_order contributes a sum product and a difference
    product; a difference of zero is dropped because it carries no
    frequency. Returns a list of {"frequency_hz", "order",
    "coefficients"} ordered by frequency then order then the first
    coefficient, so the result is stable. Raises ValueError for a
    non-positive frequency or an order below two."""
    for name, value in (
        ("first_frequency_hz", first_frequency_hz),
        ("second_frequency_hz", second_frequency_hz),
    ):
        if value <= 0:
            raise ValueError("%s must be > 0" % (name,))
    if not isinstance(max_order, int):
        raise ValueError("max_order must be an integer")
    if max_order < 2:
        raise ValueError("max_order must be >= 2")
    products = []
    for first_coefficient in range(1, max_order):
        for second_coefficient in range(1, max_order - first_coefficient + 1):
            order = first_coefficient + second_coefficient
            first_term = first_coefficient * first_frequency_hz
            second_term = second_coefficient * second_frequency_hz
            for frequency in (
                first_term + second_term,
                abs(first_term - second_term),
            ):
                if frequency <= 0:
                    continue
                products.append(
                    {
                        "frequency_hz": frequency,
                        "order": order,
                        "coefficients": (
                            first_coefficient,
                            second_coefficient,
                        ),
                    }
                )
    products.sort(
        key=lambda p: (p["frequency_hz"], p["order"], p["coefficients"])
    )
    return products


def products_in_band(products, band_low_hz, band_high_hz):
    """Subset of products falling inside a victim receive band, edges
    included. A product sitting on an edge within representation error
    is kept -- a product built from sums and multiples can land a few
    units outside a band it physically falls in. Raises ValueError for
    a non-positive lower edge or a band that does not increase."""
    if band_low_hz <= 0:
        raise ValueError("band_low_hz must be > 0")
    if band_high_hz <= band_low_hz:
        raise ValueError("band_high_hz must be > band_low_hz")
    inside = []
    for product in products:
        frequency = product["frequency_hz"]
        below = frequency < band_low_hz and not math.isclose(
            frequency, band_low_hz, rel_tol=RF_REL_TOL, abs_tol=RF_ABS_TOL
        )
        above = frequency > band_high_hz and not math.isclose(
            frequency, band_high_hz, rel_tol=RF_REL_TOL, abs_tol=RF_ABS_TOL
        )
        if not below and not above:
            inside.append(product)
    return inside


def intermodulation_findings(
    victim_id, emitters, band_low_hz, band_high_hz,
    max_order=DEFAULT_MAX_PRODUCT_ORDER,
):
    """Findings (empty when the band is clear) for every emitter pair
    whose intermodulation lands inside the victim receive band. Pairs
    are taken in list order so the result is stable. Raises ValueError
    through the helpers for a bad frequency, band or order."""
    findings = []
    for first_index in range(len(emitters)):
        for second_index in range(first_index + 1, len(emitters)):
            first = emitters[first_index]
            second = emitters[second_index]
            products = intermodulation_products_hz(
                first["frequency_hz"], second["frequency_hz"], max_order
            )
            for product in products_in_band(
                products, band_low_hz, band_high_hz
            ):
                findings.append(
                    {
                        "issue": "intermodulation_product_in_receive_band",
                        "victim": victim_id,
                        "emitters": (
                            first["emitter_id"],
                            second["emitter_id"],
                        ),
                        "frequency_hz": product["frequency_hz"],
                        "order": product["order"],
                    }
                )
    return findings


def coupling_findings(
    victim_id, emitters, susceptibility_threshold_dbm,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Findings (empty when every emitter is quiet enough at the victim)
    for the per-emitter interference margin. A margin equal to the
    requirement within representation error passes, because the margin
    is a chain of decibel sums. Raises ValueError for a non-positive
    required margin or through the coupling helpers."""
    if required_margin_db <= 0:
        raise ValueError("required_margin_db must be > 0")
    findings = []
    for emitter in emitters:
        coupled = coupled_power_dbm(
            emitter["transmit_power_dbm"],
            emitter["isolation_db"],
            emitter["filter_rejection_db"],
        )
        margin = interference_margin_db(
            coupled, susceptibility_threshold_dbm
        )
        if margin < required_margin_db and not math.isclose(
            margin, required_margin_db, rel_tol=RF_REL_TOL,
            abs_tol=RF_ABS_TOL,
        ):
            findings.append(
                {
                    "issue": "insufficient_interference_margin",
                    "victim": victim_id,
                    "emitter": emitter["emitter_id"],
                    "coupled_dbm": coupled,
                    "margin_db": margin,
                    "required_margin_db": required_margin_db,
                }
            )
    return findings


def performance_findings(
    victim_id, emitters, noise_floor_dbm,
    max_degradation_db=DEFAULT_MAX_DEGRADATION_DB,
):
    """Findings (empty when the mission criterion holds) for the rise of
    the victim noise floor caused by all emitters together. This is the
    clause's mission-performance judgement: the aggregate effect on the
    victim, not the compliance of any one emitter. Raises ValueError
    for an empty emitter list, a non-positive degradation budget, or
    through the coupling helpers."""
    if not emitters:
        raise ValueError("emitters must carry at least one entry")
    if max_degradation_db <= 0:
        raise ValueError("max_degradation_db must be > 0")
    coupled_list = [
        coupled_power_dbm(
            emitter["transmit_power_dbm"],
            emitter["isolation_db"],
            emitter["filter_rejection_db"],
        )
        for emitter in emitters
    ]
    total_interference_dbm = combined_interference_dbm(coupled_list)
    degradation_db = noise_floor_degradation_db(
        noise_floor_dbm, total_interference_dbm
    )
    if degradation_db > max_degradation_db and not math.isclose(
        degradation_db, max_degradation_db, rel_tol=RF_REL_TOL,
        abs_tol=RF_ABS_TOL,
    ):
        return [
            {
                "issue": "noise_floor_degradation_above_budget",
                "victim": victim_id,
                "degradation_db": degradation_db,
                "max_degradation_db": max_degradation_db,
                "interference_dbm": total_interference_dbm,
            }
        ]
    return []


def rf_compatibility_review(scenario):
    """Full clause 6.3.6 review for one victim against every emitter.

    scenario: {"victim_id": str, "victim_kind": str, "band_low_hz":
    float, "band_high_hz": float, "susceptibility_threshold_dbm":
    float, "noise_floor_dbm": float, "emitters": [{"emitter_id",
    "equipment_kind", "frequency_hz", "transmit_power_dbm",
    "isolation_db", "filter_rejection_db"}], "required_margin_db":
    float (optional), "max_degradation_db": float (optional),
    "max_product_order": int (optional)}.

    Returns {"roles": [...], "coupling": [...], "intermodulation":
    [...], "performance": [...]}. Raises ValueError through the helpers
    for an unrecognized unit, a bad band, frequency, order or budget.
    Does not mutate scenario."""
    victim_id = scenario["victim_id"]
    emitters = scenario["emitters"]
    return {
        "roles": role_findings(
            victim_id, scenario["victim_kind"], emitters
        ),
        "coupling": coupling_findings(
            victim_id,
            emitters,
            scenario["susceptibility_threshold_dbm"],
            scenario.get("required_margin_db", DEFAULT_REQUIRED_MARGIN_DB),
        ),
        "intermodulation": intermodulation_findings(
            victim_id,
            emitters,
            scenario["band_low_hz"],
            scenario["band_high_hz"],
            scenario.get("max_product_order", DEFAULT_MAX_PRODUCT_ORDER),
        ),
        "performance": performance_findings(
            victim_id,
            emitters,
            scenario["noise_floor_dbm"],
            scenario.get("max_degradation_db", DEFAULT_MAX_DEGRADATION_DB),
        ),
    }


def is_rf_compatible(review):
    """True when every finding list in an rf_compatibility_review result
    is empty -- the victim keeps its mission performance with every
    antenna-connected unit on the spacecraft operating."""
    return all(len(findings) == 0 for findings in review.values())
