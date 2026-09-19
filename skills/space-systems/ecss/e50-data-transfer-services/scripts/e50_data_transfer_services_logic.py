"""Data transfer services offered by an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.2.1 -- data transfer services on the on-board
network. Paraphrased into an implementable procedure; no standard text is
reproduced.

The clause carries two normative items and they fail in different ways. The
first is existence: the network offers a data transfer service for every flow
it is required to carry, so a flow with nothing behind it is a hole in the
design rather than a slow flow. The second is adequacy: the service a flow is
carried by actually meets what that flow asked for -- sustained rate, an upper
bound on transfer latency, and assured delivery where the flow needs it.

Adequacy is a property of the service under its whole load, not of the flow in
isolation. Two flows that each fit a service can together exceed it, so the
rate test is run against the aggregate the service carries once every flow has
been assigned.

Assignment is best fit by spare capacity among the services that already meet
the latency bound and the assurance need, with the name as the tie-break, so
the same inputs give the same answer on every run and on every machine.
"""

import math

__all__ = [
    "SERVED",
    "UNSERVED",
    "INADEQUATE",
    "REL_TOL",
    "validate_name",
    "validate_rate",
    "validate_latency",
    "normalise_service",
    "normalise_flow",
    "eligible_services",
    "assign_flows",
    "service_load",
    "assess_flow",
    "assess_data_transfer_services",
]

SERVED = "served"
UNSERVED = "unserved"
INADEQUATE = "inadequate"

# Relative tolerance for the rate and latency comparisons, so a flow sized to
# exactly fill a service, or sitting exactly on its latency bound, is adequate
# on every platform rather than on whichever one rounded the friendly way.
REL_TOL = 1e-9


def _within(value, bound):
    """True when value is at or below bound, with a relative tolerance."""
    scale = max(abs(value), abs(bound), 1.0)
    return value <= bound + REL_TOL * scale


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_name(value, name="name"):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def validate_rate(value, name="rate_bps"):
    """Return a non-negative rate in bits per second."""
    rate = _number(value, name)
    if rate < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return rate


def validate_latency(value, name="latency_s"):
    """Return a strictly positive latency bound in seconds."""
    latency = _number(value, name)
    if latency <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return latency


def normalise_service(service):
    """Return a validated copy of one declared network transfer service."""
    if not isinstance(service, dict):
        raise ValueError("service must be a mapping, got %r" % type(service).__name__)
    assured = service.get("assured", False)
    if not isinstance(assured, bool):
        raise ValueError("service 'assured' must be a boolean, got %r" % (assured,))
    return {
        "name": validate_name(service.get("name"), "service name"),
        "capacity_bps": validate_rate(service.get("capacity_bps"), "capacity_bps"),
        "latency_bound_s": validate_latency(
            service.get("latency_bound_s"), "latency_bound_s"
        ),
        "assured": assured,
    }


def normalise_flow(flow):
    """Return a validated copy of one flow the network has to carry."""
    if not isinstance(flow, dict):
        raise ValueError("flow must be a mapping, got %r" % type(flow).__name__)
    needs_assured = flow.get("needs_assured", False)
    if not isinstance(needs_assured, bool):
        raise ValueError(
            "flow 'needs_assured' must be a boolean, got %r" % (needs_assured,)
        )
    rate = validate_rate(flow.get("rate_bps"), "rate_bps")
    if rate <= 0.0:
        raise ValueError("flow rate_bps must be greater than zero, got %r" % (rate,))
    return {
        "name": validate_name(flow.get("name"), "flow name"),
        "rate_bps": rate,
        "deadline_s": validate_latency(flow.get("deadline_s"), "deadline_s"),
        "needs_assured": needs_assured,
    }


def _normalise_all(services, flows):
    if not isinstance(services, (list, tuple)):
        raise ValueError("services must be a list")
    if not isinstance(flows, (list, tuple)):
        raise ValueError("flows must be a list")
    if not flows:
        raise ValueError("at least one flow must be declared")
    norm_services = [normalise_service(s) for s in services]
    names = [s["name"] for s in norm_services]
    if len(set(names)) != len(names):
        raise ValueError("duplicate service name in the declared service set")
    norm_flows = [normalise_flow(f) for f in flows]
    fnames = [f["name"] for f in norm_flows]
    if len(set(fnames)) != len(fnames):
        raise ValueError("duplicate flow name in the declared flow set")
    return norm_services, norm_flows


def eligible_services(flow, services):
    """Return the services that meet this flow's latency and assurance need.

    Capacity is deliberately not part of eligibility: it is a property of the
    service under its whole load, and a flow that fits alone can still break
    the service once the other flows are on it.
    """
    flow = normalise_flow(flow)
    out = []
    for service in services:
        if not _within(service["latency_bound_s"], flow["deadline_s"]):
            continue
        if flow["needs_assured"] and not service["assured"]:
            continue
        out.append(service)
    return out


def assign_flows(services, flows):
    """Return {flow name: service name or None}, best fit by spare capacity.

    Flows are placed largest first so the hardest one is not left over, and the
    chosen service is the eligible one whose spare capacity is smallest once
    the flow is on it, with the service name as a deterministic tie-break.
    """
    spare = dict((s["name"], s["capacity_bps"]) for s in services)
    order = sorted(flows, key=lambda f: (-f["rate_bps"], f["name"]))
    assignment = {}
    for flow in order:
        best = None
        for service in eligible_services(flow, services):
            left = spare[service["name"]] - flow["rate_bps"]
            if left < 0.0 and not _within(flow["rate_bps"], spare[service["name"]]):
                continue
            key = (left, service["name"])
            if best is None or key < best[0]:
                best = (key, service["name"])
        if best is None:
            assignment[flow["name"]] = None
        else:
            assignment[flow["name"]] = best[1]
            spare[best[1]] -= flow["rate_bps"]
    # Anything eligible but unplaceable still belongs to the service that was
    # closest, so the report can say "over capacity" instead of "no service".
    for flow in order:
        if assignment[flow["name"]] is not None:
            continue
        candidates = eligible_services(flow, services)
        if candidates:
            pick = max(candidates, key=lambda s: (s["capacity_bps"], s["name"]))
            assignment[flow["name"]] = pick["name"]
            spare[pick["name"]] -= flow["rate_bps"]
    return assignment


def service_load(services, flows, assignment):
    """Return {service name: aggregate bit/s assigned to it}."""
    load = dict((s["name"], 0.0) for s in services)
    for flow in flows:
        target = assignment.get(flow["name"])
        if target is None:
            continue
        if target not in load:
            raise ValueError("flow %r assigned to unknown service %r" % (flow["name"], target))
        load[target] += flow["rate_bps"]
    return load


def assess_flow(flow, service, load_on_service):
    """Judge one flow against the service carrying it and that service's load.

    service is None when nothing carries the flow at all.
    """
    if service is None:
        return {
            "flow": flow["name"],
            "service": None,
            "verdict": UNSERVED,
            "reasons": ["no declared service carries this flow"],
            "latency_margin_s": None,
            "rate_shortfall_bps": None,
        }
    reasons = []
    latency_ok = _within(service["latency_bound_s"], flow["deadline_s"])
    if not latency_ok:
        reasons.append(
            "service latency bound %.6g s exceeds the flow deadline %.6g s"
            % (service["latency_bound_s"], flow["deadline_s"])
        )
    assurance_ok = service["assured"] or not flow["needs_assured"]
    if not assurance_ok:
        reasons.append("flow needs assured delivery and the service does not offer it")
    rate_ok = _within(load_on_service, service["capacity_bps"])
    shortfall = load_on_service - service["capacity_bps"]
    if not rate_ok:
        reasons.append(
            "service carries %.6g bit/s against a %.6g bit/s capacity"
            % (load_on_service, service["capacity_bps"])
        )
    return {
        "flow": flow["name"],
        "service": service["name"],
        "verdict": SERVED if not reasons else INADEQUATE,
        "reasons": reasons,
        "latency_margin_s": flow["deadline_s"] - service["latency_bound_s"],
        "rate_shortfall_bps": shortfall if shortfall > 0.0 else 0.0,
    }


def assess_data_transfer_services(services, flows, assignment=None):
    """Assess a declared service set against the flows an on-board network carries."""
    norm_services, norm_flows = _normalise_all(services, flows)
    if assignment is None:
        assignment = assign_flows(norm_services, norm_flows)
    elif not isinstance(assignment, dict):
        raise ValueError("assignment must be a mapping of flow name to service name")
    load = service_load(norm_services, norm_flows, assignment)
    by_name = dict((s["name"], s) for s in norm_services)
    findings = []
    per_flow = []
    for flow in norm_flows:
        target = assignment.get(flow["name"])
        service = by_name.get(target) if target is not None else None
        per_flow.append(assess_flow(flow, service, load.get(target, 0.0)))
    unserved = [r["flow"] for r in per_flow if r["verdict"] == UNSERVED]
    inadequate = [r["flow"] for r in per_flow if r["verdict"] == INADEQUATE]
    if unserved:
        findings.append(
            "clause item 1 not met: no data transfer service is declared for %s"
            % ", ".join(unserved)
        )
    if inadequate:
        findings.append(
            "clause item 2 not met: the service carrying %s does not meet what the "
            "flow asked for" % ", ".join(inadequate)
        )
    utilisation = {}
    for service in norm_services:
        capacity = service["capacity_bps"]
        carried = load.get(service["name"], 0.0)
        utilisation[service["name"]] = {
            "carried_bps": carried,
            "capacity_bps": capacity,
            "spare_bps": capacity - carried,
            "utilisation": (carried / capacity) if capacity > 0.0 else None,
        }
    return {
        "services": [s["name"] for s in norm_services],
        "flows": [f["name"] for f in norm_flows],
        "assignment": assignment,
        "per_flow": per_flow,
        "utilisation": utilisation,
        "unserved": unserved,
        "inadequate": inadequate,
        "coverage_met": not unserved,
        "adequacy_met": not inadequate,
        "compliant": not unserved and not inadequate,
        "findings": findings,
    }
