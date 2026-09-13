#!/usr/bin/env python3
"""Passive-intermodulation qualification logic (ECSS-E-ST-20C clause 7.4.5).

Deterministic, offline, stdlib-only helpers that:

* validate a spacecraft transmit carrier-plan,
* enumerate the odd-order mixing products of that carrier-plan,
* map each product onto a declared own receive-band or third-party
  protected-band,
* predict the arriving product level from a measured
  passive-intermodulation reference, and
* derive the qualification carrier-level and dwell-duration that
  envelope the flight carrier-plan.

The clause is cited as the anchor only; the procedure below is a
paraphrase, no normative text is reproduced.
"""

import math

# Level arithmetic sums several dB terms, so an exactly-met limit can
# land a few ULPs on the wrong side of zero. The engineering limit is
# unchanged; only the representation error is absorbed.
LEVEL_TOLERANCE_DB = 1e-9

BAND_KINDS = ("own-receive", "third-party-protected")

MAX_CARRIERS = 8
MAX_PRODUCT_ORDER = 15
DEFAULT_MAX_ORDER = 7
DEFAULT_ORDER_ROLLOFF_DB = 8.0
DEFAULT_QUALIFICATION_MARGIN_DB = 3.0


def _finite(value, label):
    """Return value as a float, rejecting non-numeric and non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def normalize_carrier(carrier):
    """Validate one transmit carrier and return its canonical form.

    Expected keys: id (non-empty string), frequency_hz (> 0),
    power_dbm (finite level at the generating junction).
    """
    if not isinstance(carrier, dict):
        raise ValueError("carrier must be a mapping, got %r" % (carrier,))
    cid = carrier.get("id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError("carrier id must be a non-empty string, got %r" % (cid,))
    freq = _finite(carrier.get("frequency_hz"), "carrier %s frequency_hz" % cid)
    if freq <= 0.0:
        raise ValueError("carrier %s frequency_hz must be > 0, got %r" % (cid, freq))
    level = _finite(carrier.get("power_dbm"), "carrier %s power_dbm" % cid)
    return {"id": cid.strip(), "frequency_hz": freq, "power_dbm": level}


def normalize_carrier_plan(carriers):
    """Validate the whole carrier-plan; at least two carriers must mix."""
    if not isinstance(carriers, (list, tuple)):
        raise ValueError("carrier-plan must be a list, got %r" % (carriers,))
    plan = [normalize_carrier(c) for c in carriers]
    if len(plan) < 2:
        raise ValueError(
            "carrier-plan needs at least 2 carriers to mix, got %d" % len(plan)
        )
    if len(plan) > MAX_CARRIERS:
        raise ValueError(
            "carrier-plan holds %d carriers, max %d" % (len(plan), MAX_CARRIERS)
        )
    seen = set()
    for entry in plan:
        if entry["id"] in seen:
            raise ValueError("duplicate carrier id %r in carrier-plan" % entry["id"])
        seen.add(entry["id"])
    return plan


def normalize_band(band):
    """Validate one victim band (own receive-band or protected-band)."""
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %r" % (band,))
    bid = band.get("id")
    if not isinstance(bid, str) or not bid.strip():
        raise ValueError("band id must be a non-empty string, got %r" % (bid,))
    kind = band.get("kind")
    if kind not in BAND_KINDS:
        raise ValueError(
            "band %s kind %r unknown; expected one of %s" % (bid, kind, list(BAND_KINDS))
        )
    low = _finite(band.get("low_hz"), "band %s low_hz" % bid)
    high = _finite(band.get("high_hz"), "band %s high_hz" % bid)
    if low <= 0.0:
        raise ValueError("band %s low_hz must be > 0, got %r" % (bid, low))
    if high <= low:
        raise ValueError(
            "band %s high_hz (%r) must exceed low_hz (%r)" % (bid, high, low)
        )
    limit = _finite(band.get("limit_dbm"), "band %s limit_dbm" % bid)
    isolation = _finite(band.get("isolation_db", 0.0), "band %s isolation_db" % bid)
    if isolation < 0.0:
        raise ValueError("band %s isolation_db must be >= 0, got %r" % (bid, isolation))
    return {
        "id": bid.strip(),
        "kind": kind,
        "low_hz": low,
        "high_hz": high,
        "limit_dbm": limit,
        "isolation_db": isolation,
    }


def normalize_reference(reference):
    """Validate the measured passive-intermodulation reference."""
    if not isinstance(reference, dict):
        raise ValueError("reference must be a mapping, got %r" % (reference,))
    ref_level = _finite(reference.get("carrier_power_dbm"), "reference carrier_power_dbm")
    pim_level = _finite(reference.get("pim_dbm"), "reference pim_dbm")
    order = reference.get("order", 3)
    if isinstance(order, bool) or not isinstance(order, int):
        raise ValueError("reference order must be an integer, got %r" % (order,))
    if order < 3 or order % 2 == 0:
        raise ValueError("reference order must be an odd integer >= 3, got %d" % order)
    rolloff = _finite(
        reference.get("order_rolloff_db", DEFAULT_ORDER_ROLLOFF_DB),
        "reference order_rolloff_db",
    )
    if rolloff < 0.0:
        raise ValueError("reference order_rolloff_db must be >= 0, got %r" % (rolloff,))
    return {
        "carrier_power_dbm": ref_level,
        "pim_dbm": pim_level,
        "order": order,
        "order_rolloff_db": rolloff,
    }


def _coefficient_vectors(n_carriers, order):
    """Every integer vector of length n_carriers whose absolute sum is order."""
    out = []

    def walk(index, remaining, acc):
        if index == n_carriers - 1:
            if remaining == 0:
                out.append(tuple(acc + [0]))
            else:
                out.append(tuple(acc + [remaining]))
                out.append(tuple(acc + [-remaining]))
            return
        for magnitude in range(remaining + 1):
            if magnitude == 0:
                walk(index + 1, remaining, acc + [0])
            else:
                walk(index + 1, remaining - magnitude, acc + [magnitude])
                walk(index + 1, remaining - magnitude, acc + [-magnitude])

    walk(0, order, [])
    return out


def intermodulation_products(carriers, max_order=DEFAULT_MAX_ORDER):
    """Enumerate the odd-order mixing products of a carrier-plan.

    Returns a list of {coefficients, order, frequency_hz} sorted by
    frequency then order; only combinations landing at a positive
    frequency are kept.
    """
    plan = normalize_carrier_plan(carriers)
    if isinstance(max_order, bool) or not isinstance(max_order, int):
        raise ValueError("max_order must be an integer, got %r" % (max_order,))
    if max_order < 3:
        raise ValueError("max_order must be >= 3, got %d" % max_order)
    if max_order > MAX_PRODUCT_ORDER:
        raise ValueError(
            "max_order %d exceeds the enumeration cap %d" % (max_order, MAX_PRODUCT_ORDER)
        )
    freqs = [c["frequency_hz"] for c in plan]
    products = []
    for order in range(3, max_order + 1, 2):
        for vector in _coefficient_vectors(len(plan), order):
            frequency = math.fsum(m * f for m, f in zip(vector, freqs))
            if frequency <= 0.0:
                continue
            products.append(
                {"coefficients": vector, "order": order, "frequency_hz": frequency}
            )
    products.sort(key=lambda p: (p["frequency_hz"], p["order"], p["coefficients"]))
    return products


def predict_product_level_dbm(coefficients, carriers, reference):
    """Predict the generated level of one product from the measurement anchor."""
    plan = normalize_carrier_plan(carriers)
    ref = normalize_reference(reference)
    if not isinstance(coefficients, (list, tuple)):
        raise ValueError("coefficients must be a sequence, got %r" % (coefficients,))
    if len(coefficients) != len(plan):
        raise ValueError(
            "coefficients length %d does not match the %d-carrier plan"
            % (len(coefficients), len(plan))
        )
    for m in coefficients:
        if isinstance(m, bool) or not isinstance(m, int):
            raise ValueError("coefficient %r must be an integer" % (m,))
    order = sum(abs(m) for m in coefficients)
    if order < ref["order"]:
        raise ValueError(
            "product order %d is below the reference order %d" % (order, ref["order"])
        )
    terms = [
        abs(m) * (c["power_dbm"] - ref["carrier_power_dbm"])
        for m, c in zip(coefficients, plan)
    ]
    rolloff = ref["order_rolloff_db"] * (order - ref["order"])
    return math.fsum([ref["pim_dbm"]] + terms) - rolloff


def band_containing(frequency_hz, bands):
    """Return the first declared band holding the frequency, else None."""
    freq = _finite(frequency_hz, "frequency_hz")
    if freq <= 0.0:
        raise ValueError("frequency_hz must be > 0, got %r" % (freq,))
    if not isinstance(bands, (list, tuple)):
        raise ValueError("bands must be a list, got %r" % (bands,))
    for raw in bands:
        band = normalize_band(raw)
        if band["low_hz"] <= freq <= band["high_hz"]:
            return band
    return None


def evaluate_product(product, carriers, bands, reference):
    """Map one product onto a band and evaluate its margin there."""
    band = band_containing(product["frequency_hz"], bands)
    if band is None:
        return None
    generated = predict_product_level_dbm(product["coefficients"], carriers, reference)
    arriving = generated - band["isolation_db"]
    margin = band["limit_dbm"] - arriving
    return {
        "band_id": band["id"],
        "band_kind": band["kind"],
        "coefficients": tuple(product["coefficients"]),
        "order": product["order"],
        "frequency_hz": product["frequency_hz"],
        "generated_dbm": generated,
        "arriving_dbm": arriving,
        "limit_dbm": band["limit_dbm"],
        "margin_db": margin,
        "compliant": margin >= -LEVEL_TOLERANCE_DB,
    }


def qualification_envelope(
    carriers, margin_db=DEFAULT_QUALIFICATION_MARGIN_DB, dwell_hours=1.0
):
    """Derive the qualification carrier-level and dwell that bound flight."""
    plan = normalize_carrier_plan(carriers)
    margin = _finite(margin_db, "margin_db")
    if margin < 0.0:
        raise ValueError("qualification margin_db must be >= 0, got %r" % (margin,))
    dwell = _finite(dwell_hours, "dwell_hours")
    if dwell <= 0.0:
        raise ValueError("dwell_hours must be > 0, got %r" % (dwell,))
    levels = []
    for carrier in plan:
        levels.append(
            {
                "id": carrier["id"],
                "frequency_hz": carrier["frequency_hz"],
                "nominal_dbm": carrier["power_dbm"],
                "qualification_dbm": carrier["power_dbm"] + margin,
            }
        )
    composite_mw = math.fsum(10.0 ** (item["qualification_dbm"] / 10.0) for item in levels)
    return {
        "margin_db": margin,
        "dwell_hours": dwell,
        "carriers": levels,
        "composite_qualification_dbm": 10.0 * math.log10(composite_mw),
    }


def assess_passive_intermodulation_qualification(plan):
    """Top-level clause 7.4.5 assessment of one carrier-plan."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    carriers = normalize_carrier_plan(plan.get("carriers"))
    raw_bands = plan.get("bands")
    if not isinstance(raw_bands, (list, tuple)):
        raise ValueError("plan bands must be a list, got %r" % (raw_bands,))
    bands = [normalize_band(b) for b in raw_bands]
    reference = normalize_reference(plan.get("reference"))
    max_order = plan.get("max_order", DEFAULT_MAX_ORDER)
    qualification = plan.get("qualification", {})
    if not isinstance(qualification, dict):
        raise ValueError("plan qualification must be a mapping, got %r" % (qualification,))

    products = intermodulation_products(carriers, max_order)
    findings = []
    for product in products:
        finding = evaluate_product(product, carriers, bands, reference)
        if finding is not None:
            findings.append(finding)
    findings.sort(key=lambda f: (f["margin_db"], f["frequency_hz"]))
    violations = [f for f in findings if not f["compliant"]]

    defects = []
    if not bands:
        defects.append("no receive-band or protected-band declared for the assessment")

    envelope = qualification_envelope(
        carriers,
        qualification.get("margin_db", DEFAULT_QUALIFICATION_MARGIN_DB),
        qualification.get("dwell_hours", 1.0),
    )
    return {
        "carrier_count": len(carriers),
        "band_count": len(bands),
        "product_count": len(products),
        "in_band_count": len(findings),
        "findings": findings,
        "violations": violations,
        "worst_margin_db": findings[0]["margin_db"] if findings else None,
        "defects": defects,
        "qualification": envelope,
        "compliant": not violations and not defects,
    }
