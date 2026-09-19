"""Communication requirements stated per mission phase.

Anchor: ECSS-E-ST-50C Rev.2 clause 5.6.7 -- mission phases. Paraphrased into
an implementable procedure; no standard text is reproduced.

The single normative item is that the communication requirements are stated
per mission phase rather than once for the mission. A spacecraft that needs
an omnidirectional emergency path during early operations and a high gain
science downlink later has two different communication systems in the same
hardware, and one averaged requirement describes neither.

Three checks fall out of that and they fail independently:

  timeline   -- the phases cover the mission with no gap and no overlap. An
                uncovered interval is not a quiet period; it is a stretch of
                the mission for which nobody wrote a communication
                requirement at all. An overlap means two phases each believe
                they own the same hours, usually with different links.
  allocation -- every service a phase needs is allocated to a link that
                phase actually has. A service pointed at a link that only
                exists in a later phase reads as allocated and is not.
  criticality-- a phase marked critical carries the services that make it
                recoverable: essential telemetry and an emergency command
                path, on whatever link the phase does have.

Boundaries are compared with a relative tolerance, because phases are written
to abut exactly and a bare comparison decides that by rounding.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "COMPLIANT",
    "INCOMPLETE",
    "TIMELINE_DEFECT",
    "REL_TOL",
    "CRITICAL_PHASE_SERVICES",
    "validate_epoch_h",
    "validate_phase",
    "order_phases",
    "mission_span_h",
    "covered_duration_h",
    "timeline_coverage_fraction",
    "timeline_findings",
    "unallocated_services",
    "missing_critical_services",
    "assess_mission_phases",
]

COMPLIANT = "compliant"
INCOMPLETE = "incomplete"
TIMELINE_DEFECT = "timeline-defect"

# Relative tolerance on every boundary comparison, so phases written to abut
# exactly are contiguous on every machine.
REL_TOL = 1e-9

# What a phase marked critical has to be able to do, whatever link it has.
CRITICAL_PHASE_SERVICES = (
    "essential-telemetry",
    "emergency-telecommand",
)


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def validate_epoch_h(value, name="epoch_h"):
    """Return a mission elapsed time in hours."""
    return _validate_number(value, name)


def _validate_token(value, name):
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    token = value.strip()
    if not token:
        raise ValueError("%s must not be blank" % name)
    return token


def _validate_token_sequence(values, name):
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise ValueError("%s must be a sequence" % name)
    out = []
    for item in values:
        token = _validate_token(item, "%s entry" % name)
        if token not in out:
            out.append(token)
    return tuple(out)


def validate_phase(phase):
    """Return one normalised mission phase."""
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping")
    name = _validate_token(phase.get("name"), "phase name")
    start = validate_epoch_h(phase.get("start_h"), "start_h")
    end = validate_epoch_h(phase.get("end_h"), "end_h")
    if end <= start:
        raise ValueError(
            "phase %s ends at or before it starts (%r to %r)" % (name, start, end)
        )
    critical = phase.get("critical", False)
    if not isinstance(critical, bool):
        raise ValueError("phase %s: critical must be a boolean, got %r" % (name, critical))
    links = _validate_token_sequence(phase.get("links", ()), "links")
    allocation = phase.get("service_allocation", {})
    if not isinstance(allocation, dict):
        raise ValueError(
            "phase %s: service_allocation must map a service to a link" % name
        )
    services = {}
    for service, link in allocation.items():
        services[_validate_token(service, "service name")] = _validate_token(
            link, "link name"
        )
    return {
        "name": name,
        "start_h": start,
        "end_h": end,
        "duration_h": end - start,
        "critical": critical,
        "links": links,
        "service_allocation": services,
    }


def order_phases(phases):
    """Return the phases in timeline order, refusing a repeated name."""
    if isinstance(phases, (str, bytes)) or not hasattr(phases, "__iter__"):
        raise ValueError("phases must be a sequence of phase mappings")
    normalised = [validate_phase(p) for p in phases]
    if not normalised:
        raise ValueError("phases must name at least one mission phase")
    seen = set()
    for phase in normalised:
        if phase["name"] in seen:
            raise ValueError("phase %r is declared twice" % phase["name"])
        seen.add(phase["name"])
    return tuple(sorted(normalised, key=lambda p: (p["start_h"], p["name"])))


def mission_span_h(phases):
    """Return the hours between the first start and the last end."""
    ordered = order_phases(phases)
    return max(p["end_h"] for p in ordered) - ordered[0]["start_h"]


def covered_duration_h(phases):
    """Return the hours some phase covers, counting an overlap once."""
    ordered = order_phases(phases)
    total = 0.0
    reach = None
    for phase in ordered:
        if reach is None or phase["start_h"] > reach:
            total += phase["duration_h"]
            reach = phase["end_h"]
        elif phase["end_h"] > reach:
            total += phase["end_h"] - reach
            reach = phase["end_h"]
    return total


def timeline_coverage_fraction(phases):
    """Return the share of the mission span some phase covers."""
    span = mission_span_h(phases)
    if span <= 0.0:
        raise ValueError("the mission span is not positive")
    return covered_duration_h(phases) / span


def timeline_findings(phases):
    """Return the gaps and overlaps between consecutive phases."""
    ordered = order_phases(phases)
    findings = []
    for earlier, later in zip(ordered, ordered[1:]):
        scale = max(abs(earlier["end_h"]), abs(later["start_h"]), 1.0)
        tolerance = REL_TOL * scale
        if later["start_h"] > earlier["end_h"] + tolerance:
            findings.append(
                "no phase covers the %.6g h between %s and %s"
                % (later["start_h"] - earlier["end_h"], earlier["name"], later["name"])
            )
        elif later["start_h"] < earlier["end_h"] - tolerance:
            findings.append(
                "%s and %s both claim %.6g h"
                % (earlier["name"], later["name"], earlier["end_h"] - later["start_h"])
            )
    return tuple(findings)


def unallocated_services(phase):
    """Return services pointed at a link this phase does not have."""
    entry = validate_phase(phase)
    available = set(entry["links"])
    return tuple(
        sorted(
            service
            for service, link in entry["service_allocation"].items()
            if link not in available
        )
    )


def missing_critical_services(phase, required=CRITICAL_PHASE_SERVICES):
    """Return the recovery services a critical phase does not carry."""
    entry = validate_phase(phase)
    if not entry["critical"]:
        return ()
    present = set(entry["service_allocation"])
    return tuple(s for s in required if s not in present)


def assess_mission_phases(phases):
    """Grade a per-phase communication declaration against clause 5.6.7."""
    ordered = order_phases(phases)
    timeline = timeline_findings(ordered)
    findings = list(timeline)
    per_phase = {}
    declaration_short = False
    for phase in ordered:
        gaps = []
        if not phase["links"]:
            gaps.append("no communication link is declared")
            declaration_short = True
        if not phase["service_allocation"]:
            gaps.append("no communication service is allocated")
            declaration_short = True
        stranded = unallocated_services(phase)
        for service in stranded:
            gaps.append(
                "%s is allocated to %s, which this phase does not have"
                % (service, phase["service_allocation"][service])
            )
            declaration_short = True
        for service in missing_critical_services(phase):
            gaps.append("a critical phase without %s cannot be recovered" % service)
            declaration_short = True
        if gaps:
            per_phase[phase["name"]] = tuple(gaps)
            for gap in gaps:
                findings.append("%s: %s" % (phase["name"], gap))
    if timeline:
        verdict = TIMELINE_DEFECT
    elif declaration_short:
        verdict = INCOMPLETE
    else:
        verdict = COMPLIANT
    return {
        "phase_order": tuple(p["name"] for p in ordered),
        "mission_span_h": mission_span_h(ordered),
        "covered_duration_h": covered_duration_h(ordered),
        "timeline_coverage_fraction": timeline_coverage_fraction(ordered),
        "timeline_findings": timeline,
        "phase_findings": per_phase,
        "contiguous": not timeline,
        "declaration_complete": not declaration_short,
        "verdict": verdict,
        "findings": tuple(findings),
    }
