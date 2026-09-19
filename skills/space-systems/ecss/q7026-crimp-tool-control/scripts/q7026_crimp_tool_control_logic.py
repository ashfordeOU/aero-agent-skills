"""Certification and calibration control of crimp tools and dies.

Anchor: ECSS-Q-ST-70-26C, the tooling clause of the crimping practice —
which tool, die and positioner combinations are certified for which
contacts, and how their calibration is kept live (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. A crimp tool is certified as a set, not as a frame. Tool, die and
   positioner together are certified for a named contact family and a
   conductor cross-section range. Swapping a positioner off another
   bench leaves the frame certified and the set not, which is exactly
   the failure this control exists to catch.
2. Calibration is consumed two ways at once. Elapsed days eat the
   calendar allowance whether or not the tool was used; accumulated
   crimps eat the cycle allowance whether or not time passed. Whichever
   allowance runs out first governs, and reporting only the calendar
   date is how a heavily used tool stays nominally in date.
3. There are three live states, not two. Below the recall threshold a
   tool is released; between the threshold and the allowance it is
   still usable but has to be booked for calibration; past the
   allowance it is out and its work is suspect.
4. A withdrawn tool is out regardless of arithmetic. The register is
   authoritative over the calculation.
5. A pool answers a job, not a question in the abstract. Drawing a tool
   means naming the contact and the conductor in front of it and
   letting the certification decide.

Stdlib only, offline, deterministic.
"""

import datetime

TOLERANCE = 1.0e-9

# Fraction of the calibration allowance at which a tool is booked in.
RECALL_THRESHOLD = 0.9

RELEASED = "released-for-use"
RECALL = "usable-book-for-calibration"
OVERDUE = "calibration-overdue-withdraw"
NOT_CERTIFIED = "not-certified-for-this-job"
WITHDRAWN = "withdrawn-from-the-register"

CALENDAR = "calendar-days"
CYCLES = "accumulated-cycles"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _count(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def parse_date(label, value):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(label, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s %r is not an ISO calendar date" % (label, value))


def validate_tool(tool):
    """Validate one entry of the crimp tool register."""
    if not isinstance(tool, dict):
        raise ValueError("tool must be a mapping")
    contacts = tool.get("certified_contacts")
    if not isinstance(contacts, list) or not contacts:
        raise ValueError("certified_contacts must be a non-empty list")
    low = _numeric("certified_csa_min_mm2", tool.get("certified_csa_min_mm2"), 0.0)
    high = _numeric("certified_csa_max_mm2", tool.get("certified_csa_max_mm2"), 0.0)
    if low <= 0.0:
        raise ValueError("certified_csa_min_mm2 must be greater than zero")
    if high < low:
        raise ValueError("certified_csa_max_mm2 must not be below the minimum")
    interval_days = _count(
        "calibration_interval_days", tool.get("calibration_interval_days"), 1
    )
    interval_cycles = _count(
        "calibration_interval_cycles", tool.get("calibration_interval_cycles"), 1
    )
    return {
        "tool_id": _text("tool_id", tool.get("tool_id")),
        "die_part_number": _text("die_part_number", tool.get("die_part_number")).upper(),
        "positioner_part_number": _text(
            "positioner_part_number", tool.get("positioner_part_number")
        ).upper(),
        "certified_contacts": [
            _text("certified_contact", c).upper() for c in contacts
        ],
        "certified_csa_min_mm2": low,
        "certified_csa_max_mm2": high,
        "last_calibration_date": parse_date(
            "last_calibration_date", tool.get("last_calibration_date")
        ),
        "calibration_interval_days": interval_days,
        "calibration_interval_cycles": interval_cycles,
        "cycles_since_calibration": _count(
            "cycles_since_calibration", tool.get("cycles_since_calibration", 0), 0
        ),
        "withdrawn": _flag("withdrawn", tool.get("withdrawn", False)),
    }


def validate_job(job):
    """Validate the crimp about to be made."""
    if not isinstance(job, dict):
        raise ValueError("job must be a mapping")
    csa = _numeric("conductor_csa_mm2", job.get("conductor_csa_mm2"), 0.0)
    if csa <= 0.0:
        raise ValueError("conductor_csa_mm2 must be greater than zero")
    return {
        "contact_part_number": _text(
            "contact_part_number", job.get("contact_part_number")
        ).upper(),
        "conductor_csa_mm2": csa,
        "required_positioner": _text(
            "required_positioner", job.get("required_positioner")
        ).upper(),
    }


def certification_covers(tool, job):
    """Is this tool, die and positioner set certified for this crimp?"""
    checked_tool = validate_tool(tool)
    checked_job = validate_job(job)
    reasons = []
    if checked_job["contact_part_number"] not in checked_tool["certified_contacts"]:
        reasons.append("contact-not-in-the-tool-certification")
    if checked_job["required_positioner"] != checked_tool["positioner_part_number"]:
        reasons.append("positioner-does-not-match-the-job")
    csa = checked_job["conductor_csa_mm2"]
    if csa < checked_tool["certified_csa_min_mm2"] - TOLERANCE:
        reasons.append("conductor-below-the-certified-range")
    elif csa > checked_tool["certified_csa_max_mm2"] + TOLERANCE:
        reasons.append("conductor-above-the-certified-range")
    return {"certified": not reasons, "reasons": reasons}


def calibration_status(tool, as_of):
    """How much of the calibration allowance this tool has consumed."""
    checked = validate_tool(tool)
    today = parse_date("as_of", as_of)
    elapsed = (today - checked["last_calibration_date"]).days
    if elapsed < 0:
        raise ValueError("as_of precedes the last calibration date")
    calendar_used = elapsed / checked["calibration_interval_days"]
    cycles_used = (
        checked["cycles_since_calibration"] / checked["calibration_interval_cycles"]
    )
    if cycles_used > calendar_used:
        governing = CYCLES
        consumed = cycles_used
    else:
        governing = CALENDAR
        consumed = calendar_used
    if consumed > 1.0 + TOLERANCE:
        status = OVERDUE
    elif consumed >= RECALL_THRESHOLD - TOLERANCE:
        status = RECALL
    else:
        status = RELEASED
    return {
        "elapsed_days": elapsed,
        "calendar_fraction": calendar_used,
        "cycles_fraction": cycles_used,
        "governing_allowance": governing,
        "consumed_fraction": consumed,
        "status": status,
    }


def assess_tool(tool, job, as_of):
    """Decide whether this tool may be drawn for this crimp today."""
    checked = validate_tool(tool)
    certification = certification_covers(tool, job)
    calibration = calibration_status(tool, as_of)
    reasons = list(certification["reasons"])

    if checked["withdrawn"]:
        disposition = WITHDRAWN
        reasons.append("tool-withdrawn-in-the-register")
    elif not certification["certified"]:
        disposition = NOT_CERTIFIED
    else:
        disposition = calibration["status"]

    return {
        "tool_id": checked["tool_id"],
        "disposition": disposition,
        "reasons": reasons,
        "governing_allowance": calibration["governing_allowance"],
        "consumed_fraction": calibration["consumed_fraction"],
        "elapsed_days": calibration["elapsed_days"],
        "usable": disposition in (RELEASED, RECALL),
    }


def assess_tool_pool(tools, job, as_of):
    """Which tools in the pool may be drawn for this crimp today."""
    if not isinstance(tools, list) or not tools:
        raise ValueError("tools must be a non-empty list")
    results = [assess_tool(tool, job, as_of) for tool in tools]
    usable = [r["tool_id"] for r in results if r["usable"]]
    return {
        "results": results,
        "usable": usable,
        "released": [r["tool_id"] for r in results if r["disposition"] == RELEASED],
        "to_book": [r["tool_id"] for r in results if r["disposition"] == RECALL],
        "blocked": [r["tool_id"] for r in results if not r["usable"]],
        "job_can_proceed": bool(usable),
    }
