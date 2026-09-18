"""Telecommand acknowledgement coverage for an uplinked command batch.

Anchor: ECSS-E-ST-50C clause 5.4.8 (telecommand acknowledgement). One
normative item, paraphrased into an implementable procedure; no standard text
is reproduced.

The ground has to learn the fate of every telecommand it sends, at the
verification stages that command subscribed to. This module takes a batch of
uplinked commands and the acknowledgement reports that came back, and decides
per command whether the fate is known, unknown, or known and bad.

Procedure implemented here
--------------------------
1. Validate the stage ladder: acceptance, start, progress and completion are
   ordered, and a later stage cannot be subscribed without the earlier ones.
2. Compute the deadline for each subscribed stage as the uplink epoch plus the
   round-trip light time plus that stage's own timeout, because a deep-space
   deadline is dominated by propagation and a near-Earth one is not.
3. Match the acknowledgement reports to their command and stage, rejecting a
   report for a stage the command never subscribed to and a duplicate report
   for the same stage.
4. Decide each command: covered, missing a stage, late on a stage, failed on a
   stage, or out of order.
5. Roll the per-command verdicts into batch coverage and a finding list.
"""

import math

__all__ = [
    "DEADLINE_TOLERANCE_S",
    "STAGE_LADDER",
    "STATUS_COVERED",
    "STATUS_MISSING",
    "STATUS_LATE",
    "STATUS_FAILED",
    "STATUS_OUT_OF_ORDER",
    "validate_stage",
    "validate_subscription",
    "stage_deadline_s",
    "match_reports",
    "evaluate_command",
    "assess_acknowledgement_coverage",
]

# A report arriving exactly on its deadline is on time; the sum of three
# floats can land a few ULPs past it.
DEADLINE_TOLERANCE_S = 1e-9

# Ordered verification stages. A completion report is worthless if the ground
# never learned the command was accepted, so the ladder is cumulative.
STAGE_LADDER = ("acceptance", "start", "progress", "completion")

STATUS_COVERED = "covered"
STATUS_MISSING = "missing"
STATUS_LATE = "late"
STATUS_FAILED = "failed"
STATUS_OUT_OF_ORDER = "out-of-order"


def _require_number(value, label, positive=True, allow_zero=True):
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


def validate_stage(stage):
    """Return the canonical name of a verification stage."""
    if not isinstance(stage, str):
        raise ValueError("stage must be a string, got %r" % (stage,))
    name = stage.strip().lower()
    if name not in STAGE_LADDER:
        raise ValueError(
            "unknown verification stage %r; known: %s" % (stage, ", ".join(STAGE_LADDER))
        )
    return name


def validate_subscription(stages):
    """Return the subscribed stages in ladder order, refusing a gapped ladder."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("stages must be a non-empty sequence of verification stages")
    canonical = []
    for stage in stages:
        name = validate_stage(stage)
        if name in canonical:
            raise ValueError("stage %r subscribed twice" % name)
        canonical.append(name)
    ordered = [name for name in STAGE_LADDER if name in canonical]
    if "acceptance" not in ordered:
        raise ValueError(
            "acceptance is the base of the ladder; %r cannot be subscribed without it"
            % (ordered[0],)
        )
    if "progress" in ordered and "start" not in ordered:
        raise ValueError(
            "progress is subscribed but start is not; a progress report the ground "
            "cannot time against an execution start says nothing"
        )
    return ordered


def stage_deadline_s(uplink_epoch_s, round_trip_light_time_s, stage_timeout_s):
    """Return the absolute deadline for one stage report to be back on the ground."""
    epoch = _require_number(uplink_epoch_s, "uplink_epoch_s")
    rtlt = _require_number(round_trip_light_time_s, "round_trip_light_time_s")
    timeout = _require_number(stage_timeout_s, "stage_timeout_s", allow_zero=False)
    return epoch + rtlt + timeout


def match_reports(command_name, subscribed, reports):
    """Return a mapping stage -> report for one command, rejecting stray reports."""
    if not isinstance(reports, (list, tuple)):
        raise ValueError("reports must be a sequence of report records")
    matched = {}
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            raise ValueError("reports[%d] must be a mapping" % index)
        for key in ("command", "stage", "received_at_s", "success"):
            if key not in report:
                raise ValueError("reports[%d] missing '%s'" % (index, key))
        if report["command"] != command_name:
            continue
        stage = validate_stage(report["stage"])
        if stage not in subscribed:
            raise ValueError(
                "report for stage %r on command %r which never subscribed to it"
                % (stage, command_name)
            )
        if stage in matched:
            raise ValueError(
                "duplicate %r report for command %r" % (stage, command_name)
            )
        if not isinstance(report["success"], bool):
            raise ValueError("reports[%d] 'success' must be a bool" % index)
        _require_number(report["received_at_s"], "reports[%d] received_at_s" % index)
        matched[stage] = report
    return matched


def evaluate_command(command, reports, round_trip_light_time_s):
    """Return the acknowledgement verdict for one uplinked command."""
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping")
    for key in ("name", "uplink_epoch_s", "stages", "stage_timeouts_s"):
        if key not in command:
            raise ValueError("command missing '%s'" % key)
    name = command["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("command name must be a non-empty string")
    subscribed = validate_subscription(command["stages"])
    timeouts = command["stage_timeouts_s"]
    if not isinstance(timeouts, dict):
        raise ValueError("stage_timeouts_s must be a mapping stage -> seconds")
    for stage in subscribed:
        if stage not in timeouts:
            raise ValueError("stage_timeouts_s has no timeout for subscribed stage %r" % stage)
    epoch = _require_number(command["uplink_epoch_s"], "uplink_epoch_s")
    matched = match_reports(name, subscribed, reports)

    stage_results = {}
    previous_time = None
    status = STATUS_COVERED
    for stage in subscribed:
        deadline = stage_deadline_s(epoch, round_trip_light_time_s, timeouts[stage])
        report = matched.get(stage)
        if report is None:
            stage_results[stage] = {"status": STATUS_MISSING, "deadline_s": deadline}
            status = STATUS_MISSING
            continue
        received = float(report["received_at_s"])
        on_time = received < deadline or math.isclose(
            received, deadline, rel_tol=0.0, abs_tol=DEADLINE_TOLERANCE_S
        )
        if not report["success"]:
            stage_status = STATUS_FAILED
        elif not on_time:
            stage_status = STATUS_LATE
        elif previous_time is not None and received < previous_time:
            stage_status = STATUS_OUT_OF_ORDER
        else:
            stage_status = STATUS_COVERED
        stage_results[stage] = {
            "status": stage_status,
            "deadline_s": deadline,
            "received_at_s": received,
            "latency_s": received - epoch,
        }
        previous_time = received
        if stage_status != STATUS_COVERED and status == STATUS_COVERED:
            status = stage_status
        elif stage_status == STATUS_FAILED:
            status = STATUS_FAILED

    return {
        "name": name,
        "subscribed": subscribed,
        "stages": stage_results,
        "status": status,
        "covered": status == STATUS_COVERED,
    }


def assess_acknowledgement_coverage(spec):
    """Run the full clause 5.4.8 acknowledgement-coverage assessment.

    spec keys: commands (sequence of {name, uplink_epoch_s, stages,
    stage_timeouts_s}), reports (sequence of {command, stage, received_at_s,
    success}), round_trip_light_time_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("commands", "reports", "round_trip_light_time_s"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    commands = spec["commands"]
    if not isinstance(commands, (list, tuple)) or not commands:
        raise ValueError("commands must be a non-empty sequence")
    rtlt = _require_number(spec["round_trip_light_time_s"], "round_trip_light_time_s")

    records = []
    seen = set()
    for command in commands:
        if isinstance(command, dict) and command.get("name") in seen:
            raise ValueError("duplicate command name %r in the batch" % command.get("name"))
        record = evaluate_command(command, spec["reports"], rtlt)
        seen.add(record["name"])
        records.append(record)

    covered = [r["name"] for r in records if r["covered"]]
    findings = []
    for record in records:
        if record["covered"]:
            continue
        offending = [
            stage for stage, result in record["stages"].items()
            if result["status"] != STATUS_COVERED
        ]
        findings.append(
            "command %s is %s at stage(s) %s" % (record["name"], record["status"], ", ".join(offending))
        )
    return {
        "records": records,
        "covered": covered,
        "coverage_ratio": len(covered) / len(records),
        "compliant": len(covered) == len(records),
        "findings": findings,
    }
