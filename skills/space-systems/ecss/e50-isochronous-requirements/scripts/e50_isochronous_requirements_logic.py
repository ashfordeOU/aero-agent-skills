"""Isochronous requirement-set conformance for a space communication service.

Anchor: ECSS-E-ST-50C clause 5.6.14.5 -- isochronous requirements.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item sits one level above the service itself: where an
isochronous service is required, the requirements placed on it are stated. A
stated requirement is only a requirement when it is complete and when it does
not contradict itself, so this module grades the specification rather than an
observed run. The two are different jobs -- a run can be measured against a
specification that was never satisfiable in the first place, and the measurement
then blames the implementation for an arithmetic impossibility.

Three questions are asked of a requirement set:

  complete    -- is every figure an isochronous service needs actually present,
                 with an absent figure named rather than defaulted;
  consistent  -- do the figures permit each other, or does one of them rule
                 another out before any hardware exists;
  implied     -- what does the set already commit to that nobody wrote down:
                 the minimum link rate, the link utilisation, the playout
                 buffer, and the clock stability the jitter bound demands.
"""

import math

__all__ = [
    "COMPLETE",
    "INCOMPLETE",
    "INCONSISTENT",
    "REQUIRED_FIELDS",
    "REL_TOL",
    "validate_requirements",
    "missing_requirements",
    "serialisation_time_s",
    "minimum_link_rate_bps",
    "link_utilisation",
    "max_permissible_jitter_s",
    "required_playout_buffer_bits",
    "required_clock_stability_ppm",
    "consistency_findings",
    "assess_isochronous_requirements",
]

COMPLETE = "complete"
INCOMPLETE = "incomplete"
INCONSISTENT = "inconsistent"

REQUIRED_FIELDS = (
    "period_s",
    "jitter_bound_s",
    "latency_bound_s",
    "payload_bits",
    "link_rate_bps",
)

# Relative tolerance for every bound comparison, so a requirement set written to
# sit exactly on a derived limit is accepted on every platform, not on some.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def _positive(value, name):
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _non_negative(value, name):
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def missing_requirements(spec):
    """Return the required figures this specification never states."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of requirement names to values")
    return [field for field in REQUIRED_FIELDS if spec.get(field) is None]


def validate_requirements(spec):
    """Return the stated figures as floats, raising on a malformed value.

    Absence is not malformed -- it is reported by missing_requirements, because
    a requirement nobody wrote down and a requirement written down wrongly are
    different findings with different owners.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of requirement names to values")
    checked = {}
    if spec.get("period_s") is not None:
        checked["period_s"] = _positive(spec["period_s"], "period_s")
    if spec.get("jitter_bound_s") is not None:
        checked["jitter_bound_s"] = _non_negative(spec["jitter_bound_s"], "jitter_bound_s")
    if spec.get("latency_bound_s") is not None:
        checked["latency_bound_s"] = _positive(spec["latency_bound_s"], "latency_bound_s")
    if spec.get("payload_bits") is not None:
        checked["payload_bits"] = _positive(spec["payload_bits"], "payload_bits")
    if spec.get("link_rate_bps") is not None:
        checked["link_rate_bps"] = _positive(spec["link_rate_bps"], "link_rate_bps")
    if spec.get("service_duration_s") is not None:
        checked["service_duration_s"] = _positive(
            spec["service_duration_s"], "service_duration_s"
        )
    return checked


def serialisation_time_s(payload_bits, link_rate_bps):
    """Return the seconds the link needs to clock one payload out."""
    payload = _positive(payload_bits, "payload_bits")
    rate = _positive(link_rate_bps, "link_rate_bps")
    return payload / rate


def minimum_link_rate_bps(payload_bits, period_s):
    """Return the link rate below which one payload per period is impossible."""
    payload = _positive(payload_bits, "payload_bits")
    period = _positive(period_s, "period_s")
    return payload / period


def link_utilisation(payload_bits, link_rate_bps, period_s):
    """Return the fraction of each period spent clocking the payload out."""
    period = _positive(period_s, "period_s")
    return serialisation_time_s(payload_bits, link_rate_bps) / period


def max_permissible_jitter_s(period_s):
    """Return the jitter bound beyond which slot ordering stops being decidable.

    Half a period: past that, a delivery late in its slot and one early in the
    next can swap, and no receiver can tell which slot either belonged to.
    """
    return _positive(period_s, "period_s") / 2.0


def required_playout_buffer_bits(payload_bits, jitter_bound_s, period_s):
    """Return the buffer the stated jitter bound already commits the design to."""
    payload = _positive(payload_bits, "payload_bits")
    jitter = _non_negative(jitter_bound_s, "jitter_bound_s")
    period = _positive(period_s, "period_s")
    return payload * (1.0 + jitter / period)


def required_clock_stability_ppm(jitter_bound_s, service_duration_s):
    """Return the clock stability the jitter bound demands over the service.

    None means the question cannot be asked: with no service duration stated
    there is no interval over which a frequency error accumulates.
    """
    jitter = _non_negative(jitter_bound_s, "jitter_bound_s")
    if service_duration_s is None:
        return None
    duration = _positive(service_duration_s, "service_duration_s")
    return 1.0e6 * jitter / duration


def consistency_findings(spec):
    """Return every way this requirement set rules itself out."""
    checked = validate_requirements(spec)
    findings = []
    period = checked.get("period_s")
    jitter = checked.get("jitter_bound_s")
    latency = checked.get("latency_bound_s")
    payload = checked.get("payload_bits")
    rate = checked.get("link_rate_bps")
    if period is not None and jitter is not None:
        ceiling = max_permissible_jitter_s(period)
        if jitter > ceiling + REL_TOL * max(ceiling, jitter, 1.0):
            findings.append(
                "jitter bound %.9g s exceeds half the %.9g s period, so a late "
                "delivery and the next early one can swap slots and no receiver "
                "can order them" % (jitter, period)
            )
    if latency is not None and jitter is not None:
        if latency + REL_TOL * max(latency, jitter, 1.0) < jitter:
            findings.append(
                "latency bound %.9g s is below the %.9g s jitter it permits, so "
                "the worst delivery the jitter bound allows already breaks it"
                % (latency, jitter)
            )
    if payload is not None and rate is not None and period is not None:
        serial = serialisation_time_s(payload, rate)
        if serial > period + REL_TOL * max(serial, period, 1.0):
            findings.append(
                "clocking %.9g bit out at %.9g bit/s takes %.9g s against a "
                "%.9g s period; a link rate of at least %.9g bit/s is needed"
                % (payload, rate, serial, period, minimum_link_rate_bps(payload, period))
            )
    if payload is not None and rate is not None and latency is not None:
        serial = serialisation_time_s(payload, rate)
        if serial > latency + REL_TOL * max(serial, latency, 1.0):
            findings.append(
                "serialisation alone takes %.9g s against a %.9g s latency "
                "bound, before any propagation or processing" % (serial, latency)
            )
    return findings


def assess_isochronous_requirements(spec):
    """Grade one stated isochronous requirement set and derive what it implies."""
    absent = missing_requirements(spec)
    checked = validate_requirements(spec)
    findings = consistency_findings(spec)
    period = checked.get("period_s")
    jitter = checked.get("jitter_bound_s")
    payload = checked.get("payload_bits")
    rate = checked.get("link_rate_bps")
    duration = checked.get("service_duration_s")
    derived = {
        "serialisation_time_s": None,
        "minimum_link_rate_bps": None,
        "link_utilisation": None,
        "max_permissible_jitter_s": None,
        "required_playout_buffer_bits": None,
        "required_clock_stability_ppm": None,
    }
    if payload is not None and rate is not None:
        derived["serialisation_time_s"] = serialisation_time_s(payload, rate)
    if payload is not None and period is not None:
        derived["minimum_link_rate_bps"] = minimum_link_rate_bps(payload, period)
    if payload is not None and rate is not None and period is not None:
        derived["link_utilisation"] = link_utilisation(payload, rate, period)
    if period is not None:
        derived["max_permissible_jitter_s"] = max_permissible_jitter_s(period)
    if payload is not None and jitter is not None and period is not None:
        derived["required_playout_buffer_bits"] = required_playout_buffer_bits(
            payload, jitter, period
        )
    if jitter is not None and duration is not None:
        derived["required_clock_stability_ppm"] = required_clock_stability_ppm(
            jitter, duration
        )
    if absent:
        verdict = INCOMPLETE
        findings = [
            "requirement set does not state %s" % ", ".join(absent)
        ] + findings
    elif findings:
        verdict = INCONSISTENT
    else:
        verdict = COMPLETE
    return {
        "stated": checked,
        "missing": absent,
        "derived": derived,
        "satisfiable": verdict == COMPLETE,
        "verdict": verdict,
        "findings": findings,
    }
