#!/usr/bin/env python3
"""Passive intermodulation of metal based antennas.

Anchor: ECSS-E-ST-20C clause 7.2.2.4.1 (paraphrased into an implementable
procedure; no verbatim standard text).

The module turns the clause into four checkable steps:

1. categorize every metal junction on the radiating path and say whether it
   must carry a control action;
2. enumerate the intermodulation products of the transmit carrier set with
   their coefficient vector, order and frequency;
3. isolate the products that land inside a receive band, scale each one from
   the measured reference level and carry it through the transmit-to-receive
   isolation;
4. combine the in-band products and check the receiver-noise-floor
   degradation against the allowance that band holds.

Deterministic, offline, python3 standard library only.
"""

import math

BOLTZMANN_J_PER_K = 1.380649e-23
REFERENCE_NOISE_TEMPERATURE_K = 290.0

# Junction families found on the radiating path of a metal based antenna.
# value = (intermodulation risk, control action required on record)
JUNCTION_FAMILIES = {
    "loose-metal-contact": ("high", True),
    "pressure-contact-joint": ("high", True),
    "ferromagnetic-plating": ("high", True),
    "dissimilar-metal-contact": ("elevated", True),
    "oxidised-surface": ("elevated", True),
    "contaminated-surface": ("elevated", True),
    "welded-joint": ("low", False),
    "brazed-joint": ("low", False),
    "monolithic-machined-surface": ("low", False),
}

# These tolerances absorb the representation error of a frequency that is a
# signed sum of carrier frequencies, and of a decibel value that is a sum of
# logarithms. They never move an engineering limit.
FREQUENCY_TOLERANCE_REL = 1e-12
DECIBEL_TOLERANCE_DB = 1e-9


def _finite(value, label):
    """Return value as a float, rejecting a non-number or a non-finite one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _finite(value, label)
    if out <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return out


def categorize_pim_source(source_type, mitigation_on_record=False):
    """Categorize one metal junction and say whether it is left uncontrolled.

    Returns a mapping with the risk the family carries, whether a control
    action is required, and a finding string when a required action is
    missing (None when nothing is owed).
    """
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError("source_type must be a non-empty string, got %r" % (source_type,))
    key = source_type.strip().lower()
    if key not in JUNCTION_FAMILIES:
        raise ValueError(
            "uncategorized junction family %r; known families: %s"
            % (source_type, ", ".join(sorted(JUNCTION_FAMILIES)))
        )
    if not isinstance(mitigation_on_record, bool):
        raise ValueError(
            "mitigation_on_record must be a boolean, got %r" % (mitigation_on_record,)
        )
    risk, control_required = JUNCTION_FAMILIES[key]
    finding = None
    if control_required and not mitigation_on_record:
        finding = (
            "junction %s carries %s intermodulation risk with no control action on record"
            % (key, risk)
        )
    return {
        "source_type": key,
        "risk": risk,
        "control_required": control_required,
        "mitigation_on_record": mitigation_on_record,
        "finding": finding,
    }


def intermodulation_products(carrier_frequencies_hz, max_order=7, min_order=3):
    """Enumerate the intermodulation products of a transmit carrier set.

    A product is a signed integer combination of the carriers; its order is
    the sum of the absolute coefficients. Only products with a strictly
    positive frequency survive, and a frequency reachable at more than one
    order is kept at its lowest order.
    """
    if not isinstance(carrier_frequencies_hz, (list, tuple)):
        raise ValueError("carrier_frequencies_hz must be a list or tuple")
    freqs = [_positive(f, "carrier frequency") for f in carrier_frequencies_hz]
    if len(freqs) < 2:
        raise ValueError("at least two carriers are needed to form a product")
    if len(freqs) > 6:
        raise ValueError("at most six carriers are supported, got %d" % len(freqs))
    for label, value in (("max_order", max_order), ("min_order", min_order)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if min_order < 2:
        raise ValueError("min_order must be at least 2, got %d" % min_order)
    if max_order < min_order:
        raise ValueError(
            "max_order %d is below min_order %d" % (max_order, min_order)
        )
    if max_order > 11:
        raise ValueError("max_order above 11 is not supported, got %d" % max_order)

    n = len(freqs)
    coefficients = [0] * n
    best = {}

    def walk(index, used):
        if index == n:
            if used < min_order or used > max_order:
                return
            frequency = math.fsum(c * f for c, f in zip(coefficients, freqs))
            if frequency <= 0.0:
                return
            key = round(frequency, 6)
            current = best.get(key)
            if current is None or used < current["order"]:
                best[key] = {
                    "coefficients": tuple(coefficients),
                    "order": used,
                    "frequency_hz": frequency,
                }
            return
        budget = max_order - used
        for value in range(-budget, budget + 1):
            coefficients[index] = value
            walk(index + 1, used + abs(value))
        coefficients[index] = 0

    walk(0, 0)
    return sorted(best.values(), key=lambda p: (p["frequency_hz"], p["order"]))


def _validate_band(band):
    if not isinstance(band, dict):
        raise ValueError("each receive band must be a mapping, got %r" % (band,))
    label = band.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("receive band needs a non-empty label, got %r" % (label,))
    low = _positive(band.get("low_hz"), "receive band low_hz")
    high = _positive(band.get("high_hz"), "receive band high_hz")
    if high <= low:
        raise ValueError(
            "receive band %s has high_hz %r not above low_hz %r" % (label, high, low)
        )
    return label.strip(), low, high


def _inside(frequency, low, high):
    """Band membership that absorbs the rounding of a summed frequency."""
    if low <= frequency <= high:
        return True
    if math.isclose(frequency, low, rel_tol=FREQUENCY_TOLERANCE_REL, abs_tol=0.0):
        return True
    return math.isclose(frequency, high, rel_tol=FREQUENCY_TOLERANCE_REL, abs_tol=0.0)


def products_in_receive_bands(products, receive_bands):
    """Keep only the products whose frequency lands inside a receive band."""
    if not isinstance(products, (list, tuple)):
        raise ValueError("products must be a list or tuple")
    if not isinstance(receive_bands, (list, tuple)) or not receive_bands:
        raise ValueError("receive_bands must be a non-empty list")
    bands = [_validate_band(b) for b in receive_bands]
    hits = []
    for product in products:
        if not isinstance(product, dict) or "frequency_hz" not in product:
            raise ValueError("each product must be a mapping with frequency_hz")
        frequency = _positive(product["frequency_hz"], "product frequency_hz")
        for label, low, high in bands:
            if _inside(frequency, low, high):
                hit = dict(product)
                hit["band"] = label
                hits.append(hit)
    return hits


def intermodulation_product_power_dbm(
    coefficients,
    carrier_powers_dbm,
    reference_carrier_power_dbm,
    reference_pim_dbm,
):
    """Scale a measured reference product level to the flight carrier powers.

    Each carrier contributes its absolute coefficient in decibels per decibel
    of departure from the reference tone power, which reduces to the familiar
    order-times-delta law when every tone sits at the same level.
    """
    if not isinstance(coefficients, (list, tuple)) or not coefficients:
        raise ValueError("coefficients must be a non-empty sequence")
    if not isinstance(carrier_powers_dbm, (list, tuple)) or not carrier_powers_dbm:
        raise ValueError("carrier_powers_dbm must be a non-empty sequence")
    if len(coefficients) != len(carrier_powers_dbm):
        raise ValueError(
            "coefficients (%d) and carrier_powers_dbm (%d) must be the same length"
            % (len(coefficients), len(carrier_powers_dbm))
        )
    reference_power = _finite(reference_carrier_power_dbm, "reference_carrier_power_dbm")
    reference_level = _finite(reference_pim_dbm, "reference_pim_dbm")
    total = reference_level
    order = 0
    for coefficient, power in zip(coefficients, carrier_powers_dbm):
        if isinstance(coefficient, bool) or not isinstance(coefficient, int):
            raise ValueError("coefficient must be an integer, got %r" % (coefficient,))
        level = _finite(power, "carrier power_dbm")
        order += abs(coefficient)
        total += abs(coefficient) * (level - reference_power)
    if order < 2:
        raise ValueError("a product needs an order of at least 2, got %d" % order)
    return total


def receiver_noise_floor_dbm(
    bandwidth_hz, noise_figure_db, noise_temperature_k=REFERENCE_NOISE_TEMPERATURE_K
):
    """Thermal noise floor of the victim receiver in dBm."""
    bandwidth = _positive(bandwidth_hz, "bandwidth_hz")
    noise_figure = _finite(noise_figure_db, "noise_figure_db")
    if noise_figure < 0.0:
        raise ValueError("noise_figure_db cannot be negative, got %r" % (noise_figure_db,))
    temperature = _positive(noise_temperature_k, "noise_temperature_k")
    density_dbm_per_hz = 10.0 * math.log10(
        BOLTZMANN_J_PER_K * temperature * 1000.0
    )
    return density_dbm_per_hz + 10.0 * math.log10(bandwidth) + noise_figure


def combine_powers_dbm(levels_dbm):
    """Add decibel-milliwatt levels in the linear domain."""
    if not isinstance(levels_dbm, (list, tuple)) or not levels_dbm:
        raise ValueError("levels_dbm must be a non-empty sequence")
    linear = math.fsum(10.0 ** (_finite(v, "level_dbm") / 10.0) for v in levels_dbm)
    if linear <= 0.0:
        raise ValueError("combined power collapsed to zero, which cannot happen")
    return 10.0 * math.log10(linear)


def noise_floor_degradation_db(interferer_dbm, noise_floor_dbm):
    """Rise of the receiver noise floor caused by an in-band interferer."""
    interferer = _finite(interferer_dbm, "interferer_dbm")
    floor = _finite(noise_floor_dbm, "noise_floor_dbm")
    ratio = 10.0 ** ((interferer - floor) / 10.0)
    return 10.0 * math.log10(1.0 + ratio)


def assess_metal_antenna_pim(
    carriers,
    receive_bands,
    junctions,
    reference_pim_dbm,
    reference_carrier_power_dbm,
    transmit_to_receive_isolation_db,
    receiver_bandwidth_hz,
    receiver_noise_figure_db,
    max_order=7,
):
    """Run the whole clause 7.2.2.4.1 assessment and return the findings."""
    if not isinstance(carriers, (list, tuple)) or len(carriers) < 2:
        raise ValueError("at least two transmit carriers are required")
    frequencies = []
    powers = []
    for carrier in carriers:
        if not isinstance(carrier, dict):
            raise ValueError("each carrier must be a mapping, got %r" % (carrier,))
        frequencies.append(_positive(carrier.get("frequency_hz"), "carrier frequency_hz"))
        powers.append(_finite(carrier.get("power_dbm"), "carrier power_dbm"))
    isolation = _finite(transmit_to_receive_isolation_db, "transmit_to_receive_isolation_db")
    if isolation < 0.0:
        raise ValueError(
            "transmit_to_receive_isolation_db cannot be negative, got %r"
            % (transmit_to_receive_isolation_db,)
        )
    if not isinstance(junctions, (list, tuple)):
        raise ValueError("junctions must be a list or tuple")

    junction_reports = []
    findings = []
    for junction in junctions:
        if not isinstance(junction, dict):
            raise ValueError("each junction must be a mapping, got %r" % (junction,))
        report = categorize_pim_source(
            junction.get("source_type"),
            bool(junction.get("mitigation_on_record", False)),
        )
        junction_reports.append(report)
        if report["finding"]:
            findings.append(report["finding"])

    noise_floor = receiver_noise_floor_dbm(receiver_bandwidth_hz, receiver_noise_figure_db)
    products = intermodulation_products(frequencies, max_order=max_order)
    in_band = products_in_receive_bands(products, receive_bands)

    allowances = {}
    for band in receive_bands:
        label, _low, _high = _validate_band(band)
        allowances[label] = _positive(
            band.get("allowed_degradation_db"), "allowed_degradation_db"
        )

    critical = []
    per_band = {}
    for product in in_band:
        at_junction = intermodulation_product_power_dbm(
            product["coefficients"],
            powers,
            reference_carrier_power_dbm,
            reference_pim_dbm,
        )
        at_receiver = at_junction - isolation
        entry = {
            "band": product["band"],
            "order": product["order"],
            "frequency_hz": product["frequency_hz"],
            "coefficients": product["coefficients"],
            "pim_at_junction_dbm": at_junction,
            "pim_at_receiver_dbm": at_receiver,
            "degradation_db": noise_floor_degradation_db(at_receiver, noise_floor),
        }
        critical.append(entry)
        per_band.setdefault(product["band"], []).append(at_receiver)

    band_reports = []
    for label in sorted(per_band):
        combined = combine_powers_dbm(per_band[label])
        degradation = noise_floor_degradation_db(combined, noise_floor)
        allowance = allowances[label]
        compliant = degradation <= allowance or math.isclose(
            degradation, allowance, rel_tol=0.0, abs_tol=DECIBEL_TOLERANCE_DB
        )
        if not compliant:
            findings.append(
                "receive band %s degrades by %.3f dB against an allowance of %.3f dB"
                % (label, degradation, allowance)
            )
        band_reports.append(
            {
                "band": label,
                "combined_pim_at_receiver_dbm": combined,
                "degradation_db": degradation,
                "allowed_degradation_db": allowance,
                "compliant": compliant,
            }
        )

    return {
        "noise_floor_dbm": noise_floor,
        "junctions": junction_reports,
        "product_count": len(products),
        "critical_products": sorted(
            critical, key=lambda e: (e["band"], e["frequency_hz"])
        ),
        "bands": band_reports,
        "findings": findings,
        "compliant": not findings,
    }
