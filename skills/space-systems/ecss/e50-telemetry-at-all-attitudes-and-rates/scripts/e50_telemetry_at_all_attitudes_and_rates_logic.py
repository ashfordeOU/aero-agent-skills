"""Telemetry availability over the attitude sphere and the body-rate range.

Anchor: ECSS-E-ST-50C clause 5.5.1 (telemetry at all attitudes and rates). One
normative item, paraphrased into an implementable procedure; no standard text
is reproduced.

Essential telemetry has to reach the ground whatever the spacecraft is doing --
tumbling after separation, spinning in a safe mode, pointing its high-gain
antenna at nothing. Two distinct things can break that: a pattern hole at some
attitude, and a body rate that sweeps the ground through a hole faster than the
receiver can ride it out.

Procedure implemented here
--------------------------
1. Close the link at every sampled attitude on the antenna pattern: EIRP from
   transmit power, losses and the sampled gain; received energy per bit from
   the station figure of merit, the path loss and the data rate; margin against
   the required value.
2. Report the worst sample, the coverage fraction and the attitudes that fail.
3. Convert the angular width of each failing region into an outage duration at
   the declared body rate, and compare it with how long the receiver holds lock
   through a fade.
4. Decide availability: full pattern coverage, or every outage short enough for
   the receiver to ride through at every rate in the declared range.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_DB",
    "BOLTZMANN_DBW_PER_K_HZ",
    "validate_pattern",
    "eirp_dbw",
    "received_ebno_db",
    "link_margin_db",
    "evaluate_pattern",
    "coverage_fraction",
    "outage_duration_s",
    "assess_telemetry_availability",
]

# Margins are differences of logarithms; an exact equality can land a few ULPs
# on the wrong side of zero.
MARGIN_TOLERANCE_DB = 1e-9

# Boltzmann's constant expressed in dBW/(K*Hz).
BOLTZMANN_DBW_PER_K_HZ = -228.6


def _require_number(value, label, positive=False, allow_zero=True):
    """Return value as a float after rejecting bools, non-numbers and non-finites."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if number < 0.0:
                raise ValueError("%s must be non-negative, got %r" % (label, value))
        elif number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_pattern(samples):
    """Return a validated antenna pattern as a list of sample records.

    Each sample carries the off-boresight angle in degrees, the angular width
    in degrees the sample stands for, and the gain in dBi at that angle.
    """
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of pattern samples")
    validated = []
    total_width = 0.0
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError("samples[%d] must be a mapping" % index)
        for key in ("angle_deg", "width_deg", "gain_dbi"):
            if key not in sample:
                raise ValueError("samples[%d] missing '%s'" % (index, key))
        angle = _require_number(sample["angle_deg"], "samples[%d] angle_deg" % index, positive=True)
        if angle > 180.0:
            raise ValueError("samples[%d] angle_deg %g exceeds 180 deg" % (index, angle))
        width = _require_number(
            sample["width_deg"], "samples[%d] width_deg" % index, positive=True, allow_zero=False
        )
        gain = _require_number(sample["gain_dbi"], "samples[%d] gain_dbi" % index)
        total_width += width
        validated.append({"angle_deg": angle, "width_deg": width, "gain_dbi": gain})
    if total_width <= 0.0:
        raise ValueError("pattern samples carry no angular width between them")
    return validated


def eirp_dbw(tx_power_dbw, circuit_loss_db, gain_dbi):
    """Return the effective isotropic radiated power at one pattern sample."""
    power = _require_number(tx_power_dbw, "tx_power_dbw")
    loss = _require_number(circuit_loss_db, "circuit_loss_db", positive=True)
    gain = _require_number(gain_dbi, "gain_dbi")
    return power - loss + gain


def received_ebno_db(eirp, path_loss_db, station_g_over_t_db, data_rate_bps):
    """Return the received energy per bit over noise density in dB."""
    eirp_value = _require_number(eirp, "eirp")
    path_loss = _require_number(path_loss_db, "path_loss_db", positive=True, allow_zero=False)
    g_over_t = _require_number(station_g_over_t_db, "station_g_over_t_db")
    rate = _require_number(data_rate_bps, "data_rate_bps", positive=True, allow_zero=False)
    rate_db = 10.0 * math.log10(rate)
    return eirp_value - path_loss + g_over_t - BOLTZMANN_DBW_PER_K_HZ - rate_db


def link_margin_db(ebno, required_ebno_db, implementation_loss_db=0.0):
    """Return the margin of a received Eb/N0 over the value the link needs."""
    received = _require_number(ebno, "ebno")
    required = _require_number(required_ebno_db, "required_ebno_db")
    implementation = _require_number(
        implementation_loss_db, "implementation_loss_db", positive=True
    )
    return received - required - implementation


def evaluate_pattern(samples, budget):
    """Return one margin record per pattern sample."""
    validated = validate_pattern(samples)
    if not isinstance(budget, dict):
        raise ValueError("budget must be a mapping")
    for key in (
        "tx_power_dbw",
        "circuit_loss_db",
        "path_loss_db",
        "station_g_over_t_db",
        "data_rate_bps",
        "required_ebno_db",
    ):
        if key not in budget:
            raise ValueError("budget missing required key '%s'" % key)
    records = []
    for sample in validated:
        eirp = eirp_dbw(budget["tx_power_dbw"], budget["circuit_loss_db"], sample["gain_dbi"])
        ebno = received_ebno_db(
            eirp,
            budget["path_loss_db"],
            budget["station_g_over_t_db"],
            budget["data_rate_bps"],
        )
        margin = link_margin_db(
            ebno, budget["required_ebno_db"], budget.get("implementation_loss_db", 0.0)
        )
        closes = margin > 0.0 or math.isclose(
            margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
        )
        record = dict(sample)
        record.update({"eirp_dbw": eirp, "ebno_db": ebno, "margin_db": margin, "closes": closes})
        records.append(record)
    return records


def coverage_fraction(records):
    """Return the share of the sampled angular width over which the link closes."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of margin records")
    total = 0.0
    closed = 0.0
    for record in records:
        if not isinstance(record, dict) or "closes" not in record or "width_deg" not in record:
            raise ValueError("each record must carry 'closes' and 'width_deg'")
        total += record["width_deg"]
        if record["closes"]:
            closed += record["width_deg"]
    return closed / total


def outage_duration_s(outage_width_deg, body_rate_deg_s):
    """Return how long the ground stays inside an outage region at a body rate."""
    width = _require_number(
        outage_width_deg, "outage_width_deg", positive=True, allow_zero=False
    )
    rate = _require_number(body_rate_deg_s, "body_rate_deg_s", positive=True, allow_zero=False)
    return width / rate


def assess_telemetry_availability(spec):
    """Run the full clause 5.5.1 telemetry-availability assessment.

    spec keys: samples (pattern), budget (link budget), body_rate_range_deg_s
    (pair, min and max), receiver_hold_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("samples", "budget", "body_rate_range_deg_s", "receiver_hold_s"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    rate_range = spec["body_rate_range_deg_s"]
    if not isinstance(rate_range, (list, tuple)) or len(rate_range) != 2:
        raise ValueError("body_rate_range_deg_s must be a (min, max) pair")
    rate_min = _require_number(rate_range[0], "body_rate_min", positive=True, allow_zero=False)
    rate_max = _require_number(rate_range[1], "body_rate_max", positive=True, allow_zero=False)
    if rate_min > rate_max:
        raise ValueError("body rate minimum %g exceeds maximum %g" % (rate_min, rate_max))
    hold = _require_number(spec["receiver_hold_s"], "receiver_hold_s", positive=True, allow_zero=False)

    records = evaluate_pattern(spec["samples"], spec["budget"])
    coverage = coverage_fraction(records)
    failing = [record for record in records if not record["closes"]]
    outage_width = sum(record["width_deg"] for record in failing)

    findings = []
    ride_through = True
    slowest_outage_s = 0.0
    if failing:
        # The slowest rate spends the longest inside the outage, so it is the
        # case the receiver has to survive.
        slowest_outage_s = outage_duration_s(outage_width, rate_min)
        ride_through = slowest_outage_s < hold or math.isclose(
            slowest_outage_s, hold, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
        )
        findings.append(
            "link does not close over %g deg of the sampled pattern (worst margin %.3f dB)"
            % (outage_width, min(record["margin_db"] for record in failing))
        )
        if not ride_through:
            findings.append(
                "at %g deg/s the outage lasts %.3f s, beyond the %.3f s the receiver holds lock"
                % (rate_min, slowest_outage_s, hold)
            )
    return {
        "records": records,
        "coverage_fraction": coverage,
        "worst_margin_db": min(record["margin_db"] for record in records),
        "outage_width_deg": outage_width,
        "worst_outage_s": slowest_outage_s,
        "receiver_hold_s": hold,
        "rides_through": ride_through,
        "compliant": not failing,
        "available_with_hold": ride_through,
        "findings": findings,
    }
