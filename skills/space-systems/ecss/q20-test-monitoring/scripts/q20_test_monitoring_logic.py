"""Quality-assurance surveillance of a test while it runs.

Anchor: ECSS-Q-ST-20C clause 5.6.4 (monitoring of test performance: quality
surveillance during execution, mandatory hold points, and the witnessing of
anomalies). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Normalise the run timeline: each step with its sequence number, window,
   criticality and whether the customer witnesses it.
2. Derive the surveillance demand: which steps need a product-assurance
   presence, and which additionally need the customer.
3. Compare the demand with the attendance record and compute the fraction of
   demanded steps that were actually covered end to end.
4. Grade the hold points: released at all, released by the authority that owns
   them, and released before the following step was allowed to start.
5. Grade the anomalies raised during the run: logged, attributable to a step
   in the timeline, and witnessed by the roles that were meant to be present.
6. Return the surveillance verdict with every finding named.
"""

from datetime import datetime

__all__ = [
    "SURVEILLANCE_ROLE",
    "CUSTOMER_ROLE",
    "CRITICALITIES",
    "normalise_identifier",
    "parse_timestamp",
    "validate_timeline",
    "validate_attendance",
    "surveillance_demand",
    "attendance_covers",
    "surveillance_coverage",
    "hold_point_findings",
    "anomaly_findings",
    "assess_test_monitoring",
]

# The role that carries the quality surveillance of the run itself.
SURVEILLANCE_ROLE = "product-assurance"

# Added to the demand for a step the customer has reserved as witnessed.
CUSTOMER_ROLE = "customer"

# A step is either routine or critical; a critical step is the one that
# consumes the article's margin or that cannot be repeated.
CRITICALITIES = ("routine", "critical")

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M"


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_timestamp(value, label):
    """Return a datetime from a 'yyyy-mm-ddThh:mm' stamp or a datetime."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be a 'yyyy-mm-ddThh:mm' timestamp, got %r" % (label, value))
    try:
        return datetime.strptime(value.strip(), _TIMESTAMP_FORMAT)
    except ValueError:
        raise ValueError("%s is not a 'yyyy-mm-ddThh:mm' timestamp: %r" % (label, value))


def validate_timeline(steps):
    """Return the run timeline ordered by sequence number."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence")
    timeline = []
    seen_ids = set()
    seen_sequences = set()
    for index, item in enumerate(steps):
        if not isinstance(item, dict):
            raise ValueError("steps[%d] must be a mapping" % index)
        step_id = normalise_identifier(item.get("id"), "steps[%d].id" % index)
        if step_id in seen_ids:
            raise ValueError("duplicate step id %r" % step_id)
        seen_ids.add(step_id)
        sequence = item.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise ValueError("steps[%d].sequence must be an integer" % index)
        if sequence in seen_sequences:
            raise ValueError("duplicate step sequence %d" % sequence)
        seen_sequences.add(sequence)
        criticality = normalise_identifier(
            item.get("criticality", "routine"), "steps[%d].criticality" % index
        )
        if criticality not in CRITICALITIES:
            raise ValueError(
                "steps[%d].criticality must be one of %s, got %r"
                % (index, "/".join(CRITICALITIES), criticality)
            )
        started = parse_timestamp(item.get("start"), "steps[%d].start" % index)
        ended = parse_timestamp(item.get("end"), "steps[%d].end" % index)
        if ended < started:
            raise ValueError("steps[%d] ends before it starts" % index)
        timeline.append(
            {
                "id": step_id,
                "sequence": sequence,
                "criticality": criticality,
                "start": started,
                "end": ended,
                "customer_witnessed": bool(item.get("customer_witnessed", False)),
            }
        )
    timeline.sort(key=lambda entry: entry["sequence"])
    return timeline


def validate_attendance(attendance):
    """Return the normalised attendance record of the surveillance roles."""
    if attendance is None:
        attendance = []
    if not isinstance(attendance, (list, tuple)):
        raise ValueError("attendance must be a sequence")
    entries = []
    for index, item in enumerate(attendance):
        if not isinstance(item, dict):
            raise ValueError("attendance[%d] must be a mapping" % index)
        role = normalise_identifier(item.get("role"), "attendance[%d].role" % index)
        arrived = parse_timestamp(item.get("from"), "attendance[%d].from" % index)
        left = parse_timestamp(item.get("to"), "attendance[%d].to" % index)
        if left < arrived:
            raise ValueError("attendance[%d] leaves before it arrives" % index)
        entries.append({"role": role, "from": arrived, "to": left})
    return entries


def surveillance_demand(timeline):
    """Return, per step id, the roles whose presence that step demands."""
    demand = {}
    for step in timeline:
        roles = []
        if step["criticality"] == "critical":
            roles.append(SURVEILLANCE_ROLE)
        if step["customer_witnessed"]:
            if SURVEILLANCE_ROLE not in roles:
                roles.append(SURVEILLANCE_ROLE)
            roles.append(CUSTOMER_ROLE)
        if roles:
            demand[step["id"]] = roles
    return demand


def attendance_covers(step, role, attendance):
    """Return True when one attendance entry spans the whole step window."""
    for entry in attendance:
        if entry["role"] != role:
            continue
        if entry["from"] <= step["start"] and entry["to"] >= step["end"]:
            return True
    return False


def surveillance_coverage(timeline, attendance):
    """Return the covered fraction of the demanded role-step pairs."""
    demand = surveillance_demand(timeline)
    by_id = {step["id"]: step for step in timeline}
    demanded = 0
    covered = 0
    gaps = []
    for step_id in sorted(demand):
        for role in demand[step_id]:
            demanded += 1
            if attendance_covers(by_id[step_id], role, attendance):
                covered += 1
            else:
                gaps.append("%s uncovered by %s" % (step_id, role))
    ratio = 1.0 if demanded == 0 else covered / float(demanded)
    return {
        "demanded_pairs": demanded,
        "covered_pairs": covered,
        "coverage_ratio": ratio,
        "gaps": gaps,
    }


def hold_point_findings(timeline, hold_points):
    """Return the findings of the mandatory hold points on the run."""
    if hold_points is None:
        hold_points = []
    if not isinstance(hold_points, (list, tuple)):
        raise ValueError("hold_points must be a sequence")
    by_id = {step["id"]: step for step in timeline}
    ordered = list(timeline)
    findings = []
    seen = set()
    for index, item in enumerate(hold_points):
        if not isinstance(item, dict):
            raise ValueError("hold_points[%d] must be a mapping" % index)
        point_id = normalise_identifier(item.get("id"), "hold_points[%d].id" % index)
        if point_id in seen:
            raise ValueError("duplicate hold point id %r" % point_id)
        seen.add(point_id)
        after = normalise_identifier(item.get("after_step"), "hold_points[%d].after_step" % index)
        if after not in by_id:
            raise ValueError(
                "hold point %s sits after unknown step %r" % (point_id, after)
            )
        authority = normalise_identifier(
            item.get("authority"), "hold_points[%d].authority" % index
        )
        if not bool(item.get("released", False)):
            findings.append("hold point %s was never released" % point_id)
            continue
        released_by = normalise_identifier(
            item.get("released_by"), "hold_points[%d].released_by" % index
        )
        if released_by != authority:
            findings.append(
                "hold point %s was released by %s, not by the %s that owns it"
                % (point_id, released_by, authority)
            )
        release_time = parse_timestamp(
            item.get("release_time"), "hold_points[%d].release_time" % index
        )
        held_step = by_id[after]
        if release_time < held_step["end"]:
            findings.append(
                "hold point %s was released before step %s finished" % (point_id, after)
            )
        following = [s for s in ordered if s["sequence"] > held_step["sequence"]]
        if following:
            nxt = following[0]
            if nxt["start"] < release_time:
                findings.append(
                    "step %s started before hold point %s was released" % (nxt["id"], point_id)
                )
    return findings


def anomaly_findings(timeline, anomalies, attendance):
    """Return the findings of the anomalies raised while the test ran."""
    if anomalies is None:
        anomalies = []
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError("anomalies must be a sequence")
    demand = surveillance_demand(timeline)
    findings = []
    seen = set()
    for index, item in enumerate(anomalies):
        if not isinstance(item, dict):
            raise ValueError("anomalies[%d] must be a mapping" % index)
        anomaly_id = normalise_identifier(item.get("id"), "anomalies[%d].id" % index)
        if anomaly_id in seen:
            raise ValueError("duplicate anomaly id %r" % anomaly_id)
        seen.add(anomaly_id)
        raised = parse_timestamp(item.get("time"), "anomalies[%d].time" % index)
        if not bool(item.get("logged", False)):
            findings.append("anomaly %s was not entered in the run log" % anomaly_id)
        raw_witnesses = item.get("witnessed_by", [])
        if not isinstance(raw_witnesses, (list, tuple)):
            raise ValueError("anomalies[%d].witnessed_by must be a sequence" % index)
        witnesses = {
            normalise_identifier(role, "anomalies[%d].witnessed_by[%d]" % (index, j))
            for j, role in enumerate(raw_witnesses)
        }
        host = None
        for step in timeline:
            if step["start"] <= raised <= step["end"]:
                host = step
                break
        if host is None:
            findings.append(
                "anomaly %s is stamped outside every step window and cannot be attributed"
                % anomaly_id
            )
            continue
        for role in demand.get(host["id"], []):
            if role not in witnesses:
                findings.append(
                    "anomaly %s in step %s was not witnessed by %s"
                    % (anomaly_id, host["id"], role)
                )
        if SURVEILLANCE_ROLE in witnesses and not attendance_covers(
            host, SURVEILLANCE_ROLE, attendance
        ):
            findings.append(
                "anomaly %s records a %s witness with no attendance covering step %s"
                % (anomaly_id, SURVEILLANCE_ROLE, host["id"])
            )
    return findings


def assess_test_monitoring(plan):
    """Run the whole clause 5.6.4 surveillance assessment for one test."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    timeline = validate_timeline(plan.get("steps"))
    attendance = validate_attendance(plan.get("attendance"))
    coverage = surveillance_coverage(timeline, attendance)
    findings = []
    out_of_order = [
        timeline[i]["id"]
        for i in range(1, len(timeline))
        if timeline[i]["start"] < timeline[i - 1]["start"]
    ]
    if out_of_order:
        findings.append(
            "steps ran out of their sequence order: %s" % ", ".join(out_of_order)
        )
    findings.extend("surveillance gap: %s" % gap for gap in coverage["gaps"])
    findings.extend(hold_point_findings(timeline, plan.get("hold_points")))
    findings.extend(anomaly_findings(timeline, plan.get("anomalies"), attendance))
    return {
        "step_count": len(timeline),
        "demanded_pairs": coverage["demanded_pairs"],
        "covered_pairs": coverage["covered_pairs"],
        "coverage_ratio": coverage["coverage_ratio"],
        "findings": findings,
        "verdict": "surveillance-complete" if not findings else "surveillance-gap",
    }
