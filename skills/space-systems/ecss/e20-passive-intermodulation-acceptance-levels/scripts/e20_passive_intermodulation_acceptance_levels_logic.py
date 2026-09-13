#!/usr/bin/env python3
"""Passive-intermodulation acceptance levels -- ECSS-E-ST-20C clause 7.4.2.

Deterministic, offline, stdlib-only logic for deriving and agreeing the
passive-intermodulation interference a development may present to a victim
receive-chain, and for binding that agreement to the carrier-plan it was
derived for.

Reference plane convention
--------------------------
Two planes are used and never mixed:

* receiver input      -- where the tolerable interference is defined
                         (receiver-noise-floor + interference-to-noise
                         allowance);
* transmit antenna port -- where the hardware requirement is written; it
                         sits `isolation_db` above the receiver-input level,
                         less the verification measurement-uncertainty and
                         the retained design-margin.

All levels are dBm; all allowances, isolations and margins are dB.
"""

import math

# dB/dBm comparisons are between sums and power-sums of floats, so an exactly
# compliant case can land a few ULPs on the wrong side of the limit. This
# tolerance absorbs the representation error only -- it never widens the
# engineering limit (1e-9 dB is ~2 parts in 10^10 of power).
DB_TOL = 1e-9

MIN_CARRIERS = 2
MAX_INR_DB = 0.0          # an interference-to-noise allowance is a desense
MIN_INR_DB = -60.0        # allowance; below this it is a transcription slip
STATUS_AGREED = "agreed"
STATUS_NEGOTIABLE = "negotiable"
STATUS_WAIVER_REQUIRED = "waiver-required"


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(value, label):
    """Return `value` as a float or raise ValueError naming the field."""
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _require_non_negative(value, label):
    number = _require_number(value, label)
    if number < 0.0:
        raise ValueError("%s must be >= 0 dB, got %r" % (label, value))
    return number


def _le(left, right, tol=DB_TOL):
    """`left <= right`, tolerant of float representation error only."""
    return left <= right or math.isclose(left, right, rel_tol=0.0, abs_tol=tol)


def dbm_to_mw(level_dbm):
    """Convert a dBm level to milliwatts."""
    return 10.0 ** (_require_number(level_dbm, "level_dbm") / 10.0)


def mw_to_dbm(power_mw):
    """Convert milliwatts to dBm; a non-positive power has no dB value."""
    power = _require_number(power_mw, "power_mw")
    if power <= 0.0:
        raise ValueError("power_mw must be > 0 to express in dBm, got %r" % (power_mw,))
    return 10.0 * math.log10(power)


def power_sum_dbm(levels_dbm):
    """Power-sum a non-empty sequence of dBm levels (they add as powers)."""
    levels = list(levels_dbm)
    if not levels:
        raise ValueError("levels_dbm must contain at least one level")
    total_mw = 0.0
    for index, level in enumerate(levels):
        total_mw += dbm_to_mw(_require_number(level, "levels_dbm[%d]" % index))
    return mw_to_dbm(total_mw)


def tolerable_interference_dbm(noise_floor_dbm, allowed_inr_db):
    """Tolerable interference at the victim receiver input.

    noise-floor + interference-to-noise allowance. The allowance is the
    agreed desensitisation the link-budget absorbs and is therefore <= 0 dB.
    """
    floor = _require_number(noise_floor_dbm, "noise_floor_dbm")
    inr = _require_number(allowed_inr_db, "allowed_inr_db")
    if inr > MAX_INR_DB:
        raise ValueError(
            "allowed_inr_db must be <= %.1f dB (it is a desensitisation "
            "allowance), got %r" % (MAX_INR_DB, allowed_inr_db)
        )
    if inr < MIN_INR_DB:
        raise ValueError(
            "allowed_inr_db below %.1f dB is not a credible allowance, got %r"
            % (MIN_INR_DB, allowed_inr_db)
        )
    return floor + inr


def acceptance_level_dbm(
    tolerable_dbm, isolation_db, measurement_uncertainty_db, design_margin_db
):
    """Refer a receiver-input tolerable level to the transmit antenna port."""
    tolerable = _require_number(tolerable_dbm, "tolerable_dbm")
    isolation = _require_non_negative(isolation_db, "isolation_db")
    uncertainty = _require_non_negative(
        measurement_uncertainty_db, "measurement_uncertainty_db"
    )
    margin = _require_non_negative(design_margin_db, "design_margin_db")
    return tolerable + isolation - uncertainty - margin


def validate_victim_band(band):
    """Normalise one victim-band record, raising ValueError on bad input."""
    if not isinstance(band, dict):
        raise ValueError("victim band must be a mapping, got %r" % (type(band).__name__,))
    name = band.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("victim band needs a non-empty 'name'")
    f_low = _require_number(band.get("f_low_hz"), "%s.f_low_hz" % name)
    f_high = _require_number(band.get("f_high_hz"), "%s.f_high_hz" % name)
    if f_low <= 0.0:
        raise ValueError("%s.f_low_hz must be > 0, got %r" % (name, f_low))
    if f_high <= f_low:
        raise ValueError(
            "%s band edges inverted: f_high_hz %r must exceed f_low_hz %r"
            % (name, f_high, f_low)
        )
    return {
        "name": name,
        "f_low_hz": f_low,
        "f_high_hz": f_high,
        "noise_floor_dbm": _require_number(
            band.get("noise_floor_dbm"), "%s.noise_floor_dbm" % name
        ),
        "allowed_inr_db": _require_number(
            band.get("allowed_inr_db"), "%s.allowed_inr_db" % name
        ),
        "isolation_db": _require_non_negative(
            band.get("isolation_db"), "%s.isolation_db" % name
        ),
    }


def validate_carrier_plan(plan):
    """Normalise a transmit carrier-plan and derive its aggregate figures."""
    if not isinstance(plan, dict):
        raise ValueError("carrier plan must be a mapping, got %r" % (type(plan).__name__,))
    frequencies = plan.get("carrier_frequencies_hz")
    powers = plan.get("carrier_powers_dbm")
    if not isinstance(frequencies, (list, tuple)) or not isinstance(powers, (list, tuple)):
        raise ValueError(
            "carrier plan needs list 'carrier_frequencies_hz' and 'carrier_powers_dbm'"
        )
    if len(frequencies) != len(powers):
        raise ValueError(
            "carrier plan length mismatch: %d frequencies vs %d powers"
            % (len(frequencies), len(powers))
        )
    if len(frequencies) < MIN_CARRIERS:
        raise ValueError(
            "passive-intermodulation needs at least %d carriers, got %d"
            % (MIN_CARRIERS, len(frequencies))
        )
    clean_freqs = []
    for index, freq in enumerate(frequencies):
        value = _require_number(freq, "carrier_frequencies_hz[%d]" % index)
        if value <= 0.0:
            raise ValueError(
                "carrier_frequencies_hz[%d] must be > 0, got %r" % (index, freq)
            )
        clean_freqs.append(value)
    if len(set(clean_freqs)) != len(clean_freqs):
        raise ValueError("carrier frequencies must be distinct")
    clean_powers = [
        _require_number(p, "carrier_powers_dbm[%d]" % i) for i, p in enumerate(powers)
    ]
    return {
        "carrier_count": len(clean_freqs),
        "carrier_frequencies_hz": clean_freqs,
        "carrier_powers_dbm": clean_powers,
        "max_carrier_power_dbm": max(clean_powers),
        "aggregate_power_dbm": power_sum_dbm(clean_powers),
        "f_low_hz": min(clean_freqs),
        "f_high_hz": max(clean_freqs),
    }


def derive_acceptance_levels(victim_bands, measurement_uncertainty_db, design_margin_db):
    """Derive the transmit-port acceptance-level for every victim band."""
    bands = list(victim_bands)
    if not bands:
        raise ValueError("victim_bands must contain at least one band")
    uncertainty = _require_non_negative(
        measurement_uncertainty_db, "measurement_uncertainty_db"
    )
    margin = _require_non_negative(design_margin_db, "design_margin_db")
    derived = []
    seen = set()
    for band in bands:
        record = validate_victim_band(band)
        if record["name"] in seen:
            raise ValueError("duplicate victim band name %r" % (record["name"],))
        seen.add(record["name"])
        tolerable = tolerable_interference_dbm(
            record["noise_floor_dbm"], record["allowed_inr_db"]
        )
        record["tolerable_interference_dbm"] = tolerable
        record["acceptance_level_dbm"] = acceptance_level_dbm(
            tolerable, record["isolation_db"], uncertainty, margin
        )
        record["measurement_uncertainty_db"] = uncertainty
        record["design_margin_db"] = margin
        derived.append(record)
    return derived


def reconcile_level(supplier_dbm, customer_dbm, negotiation_band_db=0.0):
    """Reconcile a supplier-proposed level against the customer requirement."""
    supplier = _require_number(supplier_dbm, "supplier_dbm")
    customer = _require_number(customer_dbm, "customer_dbm")
    band = _require_non_negative(negotiation_band_db, "negotiation_band_db")
    if _le(supplier, customer):
        status = STATUS_AGREED
    elif _le(supplier, customer + band):
        status = STATUS_NEGOTIABLE
    else:
        status = STATUS_WAIVER_REQUIRED
    return {
        "supplier_dbm": supplier,
        "customer_dbm": customer,
        "agreed_level_dbm": min(supplier, customer),
        "exceedance_db": max(0.0, supplier - customer),
        "status": status,
    }


def check_plan_validity(agreed_plan, as_flown_plan):
    """Findings raised when an as-flown carrier-plan outgrows the agreed one."""
    agreed = validate_carrier_plan(agreed_plan)
    flown = validate_carrier_plan(as_flown_plan)
    findings = []
    if flown["carrier_count"] > agreed["carrier_count"]:
        findings.append(
            "carrier count grew from %d to %d"
            % (agreed["carrier_count"], flown["carrier_count"])
        )
    if not _le(flown["aggregate_power_dbm"], agreed["aggregate_power_dbm"]):
        findings.append(
            "aggregate carrier-power grew by %.3f dB"
            % (flown["aggregate_power_dbm"] - agreed["aggregate_power_dbm"])
        )
    if not _le(flown["max_carrier_power_dbm"], agreed["max_carrier_power_dbm"]):
        findings.append(
            "per-carrier-power grew by %.3f dB"
            % (flown["max_carrier_power_dbm"] - agreed["max_carrier_power_dbm"])
        )
    for freq in flown["carrier_frequencies_hz"]:
        if not (
            _le(agreed["f_low_hz"], freq) and _le(freq, agreed["f_high_hz"])
        ):
            findings.append("carrier %.6g Hz sits outside the agreed transmit span" % freq)
    return findings


def assess_acceptance_agreement(
    victim_bands,
    carrier_plan,
    supplier_levels_dbm,
    measurement_uncertainty_db,
    design_margin_db,
    expected_products_dbm=None,
    negotiation_band_db=0.0,
    as_flown_plan=None,
):
    """Full clause 7.4.2 assessment across every victim band.

    Returns a mapping with the per-band derivation and reconciliation, the
    validated carrier-plan, any carrier-plan findings, and the overall
    agreement verdict.
    """
    if not isinstance(supplier_levels_dbm, dict):
        raise ValueError("supplier_levels_dbm must be a mapping of band name -> dBm")
    expected = expected_products_dbm or {}
    if not isinstance(expected, dict):
        raise ValueError("expected_products_dbm must be a mapping of band name -> levels")
    plan = validate_carrier_plan(carrier_plan)
    derived = derive_acceptance_levels(
        victim_bands, measurement_uncertainty_db, design_margin_db
    )
    plan_findings = (
        check_plan_validity(carrier_plan, as_flown_plan) if as_flown_plan else []
    )
    results = []
    for record in derived:
        name = record["name"]
        if name not in supplier_levels_dbm:
            raise ValueError("no supplier level proposed for victim band %r" % (name,))
        reconciliation = reconcile_level(
            supplier_levels_dbm[name], record["acceptance_level_dbm"], negotiation_band_db
        )
        band_findings = []
        aggregate_dbm = None
        products = expected.get(name)
        if products:
            aggregate_dbm = power_sum_dbm(products)
            if not _le(aggregate_dbm, reconciliation["agreed_level_dbm"]):
                band_findings.append(
                    "aggregate product level %.3f dBm exceeds agreed %.3f dBm"
                    % (aggregate_dbm, reconciliation["agreed_level_dbm"])
                )
        if reconciliation["status"] != STATUS_AGREED:
            band_findings.append(
                "supplier level %s (%.3f dB above requirement)"
                % (reconciliation["status"], reconciliation["exceedance_db"])
            )
        results.append(
            {
                "name": name,
                "tolerable_interference_dbm": record["tolerable_interference_dbm"],
                "acceptance_level_dbm": record["acceptance_level_dbm"],
                "agreed_level_dbm": reconciliation["agreed_level_dbm"],
                "status": reconciliation["status"],
                "aggregate_product_dbm": aggregate_dbm,
                "findings": band_findings,
                "agreed": not band_findings,
            }
        )
    return {
        "carrier_plan": plan,
        "bands": results,
        "plan_findings": plan_findings,
        "agreed": not plan_findings and all(band["agreed"] for band in results),
    }
