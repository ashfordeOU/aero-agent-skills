"""Layout review item of a device design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.7 (design review -- the layout review
item). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Check the drawing set: every required drawing kind present, released, and
   standing at the design baseline issue rather than above or below it.
2. Check the terminal pad placement against the interface definition: every
   required pad present exactly once, every pad centre inside the outline
   with its keep-out respected, and the closest pad pair no tighter than the
   declared minimum pitch.
3. Check the rule-check status: every required check run, and every residual
   error either cleared or covered by an approved waiver.
4. Close the review item only when none of the three leaves an open action.
"""

import math

__all__ = [
    "GEOMETRY_TOLERANCE_UM",
    "validate_outline",
    "validate_pad",
    "pad_separation",
    "minimum_pad_separation",
    "pads_outside_outline",
    "pad_set_findings",
    "drawing_findings",
    "rule_check_findings",
    "assess_layout_review",
]

# Pad geometry is compared after a square root and a subtraction, so a pair
# sitting exactly on the minimum pitch can land a few units in the last place
# on either side. Absorb that here, never by relaxing the pitch itself.
GEOMETRY_TOLERANCE_UM = 1e-9


def _real(value, label, positive=False, non_negative=False):
    """Return value as a finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    if non_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a non-empty stripped identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _index(value, label, minimum=0):
    """Return value as an integer index, raising on anything else."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_outline(outline):
    """Return the validated (x_min, y_min, x_max, y_max) die outline in micrometres."""
    if not isinstance(outline, (list, tuple)) or len(outline) != 4:
        raise ValueError("outline must be an (x_min, y_min, x_max, y_max) quadruple")
    x_min = _real(outline[0], "outline x_min")
    y_min = _real(outline[1], "outline y_min")
    x_max = _real(outline[2], "outline x_max")
    y_max = _real(outline[3], "outline y_max")
    if x_max <= x_min:
        raise ValueError("outline x_max %g must exceed x_min %g" % (x_max, x_min))
    if y_max <= y_min:
        raise ValueError("outline y_max %g must exceed y_min %g" % (y_max, y_min))
    return (x_min, y_min, x_max, y_max)


def validate_pad(pad):
    """Return the validated (name, x, y) of one terminal pad in micrometres."""
    if not isinstance(pad, dict):
        raise ValueError("pad must be a mapping, got %r" % (pad,))
    for key in ("name", "x", "y"):
        if key not in pad:
            raise ValueError("pad missing required key '%s'" % key)
    return (_name(pad["name"], "pad name"), _real(pad["x"], "pad x"), _real(pad["y"], "pad y"))


def pad_separation(first, second):
    """Return the centre-to-centre distance between two pads in micrometres."""
    _, x1, y1 = validate_pad(first)
    _, x2, y2 = validate_pad(second)
    return math.hypot(x2 - x1, y2 - y1)


def minimum_pad_separation(pads):
    """Return the closest pad pair and its centre-to-centre distance."""
    if not isinstance(pads, (list, tuple)) or len(pads) < 2:
        raise ValueError("a separation search needs at least two pads")
    entries = [validate_pad(p) for p in pads]
    closest = None
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            distance = math.hypot(
                entries[j][1] - entries[i][1], entries[j][2] - entries[i][2]
            )
            pair = (entries[i][0], entries[j][0])
            if closest is None or distance < closest["distance"]:
                closest = {"distance": distance, "pair": pair}
    return closest


def pads_outside_outline(pads, outline, keep_out=0.0):
    """Return the names of pads whose centre breaks the outline keep-out."""
    x_min, y_min, x_max, y_max = validate_outline(outline)
    edge = _real(keep_out, "keep_out", non_negative=True)
    if 2.0 * edge >= (x_max - x_min) or 2.0 * edge >= (y_max - y_min):
        raise ValueError("keep_out %g leaves no usable area inside the outline" % edge)
    if not isinstance(pads, (list, tuple)):
        raise ValueError("pads must be a sequence of pad mappings")
    offenders = []
    for pad in pads:
        name, x, y = validate_pad(pad)
        slack = GEOMETRY_TOLERANCE_UM * max(1.0, abs(x), abs(y))
        if (
            x < x_min + edge - slack
            or x > x_max - edge + slack
            or y < y_min + edge - slack
            or y > y_max - edge + slack
        ):
            offenders.append(name)
    return offenders


def pad_set_findings(pads, required_names):
    """Return the missing, repeated and unexpected pads against the interface set."""
    if not isinstance(pads, (list, tuple)):
        raise ValueError("pads must be a sequence of pad mappings")
    if not isinstance(required_names, (list, tuple)):
        raise ValueError("required_names must be a sequence of pad names")
    required = []
    for item in required_names:
        text = _name(item, "required pad name")
        if text not in required:
            required.append(text)
    seen = []
    repeated = []
    for pad in pads:
        name, _, _ = validate_pad(pad)
        if name in seen:
            if name not in repeated:
                repeated.append(name)
        else:
            seen.append(name)
    missing = [n for n in required if n not in seen]
    unexpected = [n for n in seen if n not in required]
    return {"missing": missing, "repeated": repeated, "unexpected": unexpected}


def drawing_findings(drawings, required_kinds, baseline_issue):
    """Return the drawing-set findings against the design baseline issue."""
    if not isinstance(drawings, (list, tuple)):
        raise ValueError("drawings must be a sequence of drawing mappings")
    if not isinstance(required_kinds, (list, tuple)) or not required_kinds:
        raise ValueError("required_kinds must be a non-empty sequence of drawing kinds")
    baseline = _index(baseline_issue, "baseline_issue", minimum=1)
    required = []
    for item in required_kinds:
        text = _name(item, "required drawing kind").lower()
        if text not in required:
            required.append(text)
    present = {}
    duplicates = []
    unreleased = []
    behind = []
    ahead = []
    for drawing in drawings:
        if not isinstance(drawing, dict):
            raise ValueError("each drawing must be a mapping")
        for key in ("kind", "id", "issue", "released"):
            if key not in drawing:
                raise ValueError("drawing missing required key '%s'" % key)
        kind = _name(drawing["kind"], "drawing kind").lower()
        ident = _name(drawing["id"], "drawing id")
        issue = _index(drawing["issue"], "drawing issue", minimum=1)
        released = drawing["released"]
        if not isinstance(released, bool):
            raise ValueError("drawing released flag must be a boolean")
        if kind in present:
            duplicates.append(kind)
        else:
            present[kind] = ident
        if not released:
            unreleased.append(ident)
        if issue < baseline:
            behind.append(ident)
        elif issue > baseline:
            ahead.append(ident)
    missing = [k for k in required if k not in present]
    return {
        "missing_kinds": missing,
        "duplicate_kinds": duplicates,
        "unreleased": unreleased,
        "behind_baseline": behind,
        "ahead_of_baseline": ahead,
    }


def rule_check_findings(checks, required_checks):
    """Return the rule-check findings: checks not run, and errors left standing."""
    if not isinstance(checks, (list, tuple)):
        raise ValueError("checks must be a sequence of rule-check mappings")
    if not isinstance(required_checks, (list, tuple)) or not required_checks:
        raise ValueError("required_checks must be a non-empty sequence of check names")
    required = []
    for item in required_checks:
        text = _name(item, "required check name").lower()
        if text not in required:
            required.append(text)
    seen = []
    residual = []
    unapproved = []
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("each rule check must be a mapping")
        for key in ("check", "error_count"):
            if key not in check:
                raise ValueError("rule check missing required key '%s'" % key)
        name = _name(check["check"], "check name").lower()
        if name in seen:
            raise ValueError("rule check '%s' is reported more than once" % name)
        seen.append(name)
        errors = _index(check["error_count"], "%s error_count" % name, minimum=0)
        waived = 0
        for waiver in check.get("waivers", []) or []:
            if not isinstance(waiver, dict):
                raise ValueError("each waiver must be a mapping")
            for key in ("id", "approved", "covers"):
                if key not in waiver:
                    raise ValueError("waiver missing required key '%s'" % key)
            waiver_id = _name(waiver["id"], "waiver id")
            approved = waiver["approved"]
            if not isinstance(approved, bool):
                raise ValueError("waiver approved flag must be a boolean")
            covers = _index(waiver["covers"], "waiver covers", minimum=1)
            if approved:
                waived += covers
            else:
                unapproved.append(waiver_id)
        if waived > errors:
            raise ValueError(
                "%s waives %d errors but only %d were reported" % (name, waived, errors)
            )
        if errors - waived > 0:
            residual.append({"check": name, "errors": errors - waived})
    not_run = [c for c in required if c not in seen]
    return {"not_run": not_run, "residual": residual, "unapproved_waivers": unapproved}


def assess_layout_review(spec):
    """Run the clause 7.3.7 layout review item end to end.

    spec keys: drawings, required_drawing_kinds, baseline_issue, pads,
    required_pads, outline, minimum_pitch_um, optional keep_out_um, checks,
    required_checks.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "drawings",
        "required_drawing_kinds",
        "baseline_issue",
        "pads",
        "required_pads",
        "outline",
        "minimum_pitch_um",
        "checks",
        "required_checks",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    pitch = _real(spec["minimum_pitch_um"], "minimum_pitch_um", positive=True)
    drawings = drawing_findings(
        spec["drawings"], spec["required_drawing_kinds"], spec["baseline_issue"]
    )
    pad_sets = pad_set_findings(spec["pads"], spec["required_pads"])
    outside = pads_outside_outline(
        spec["pads"], spec["outline"], spec.get("keep_out_um", 0.0)
    )
    closest = minimum_pad_separation(spec["pads"])
    slack = GEOMETRY_TOLERANCE_UM * max(1.0, pitch)
    pitch_met = closest["distance"] >= pitch - slack
    rule_checks = rule_check_findings(spec["checks"], spec["required_checks"])
    findings = []
    for kind in drawings["missing_kinds"]:
        findings.append("required %s drawing is absent from the reviewed set" % kind)
    for kind in drawings["duplicate_kinds"]:
        findings.append("drawing kind %s is presented twice; one set has to govern" % kind)
    for ident in drawings["unreleased"]:
        findings.append("drawing %s is presented unreleased" % ident)
    for ident in drawings["behind_baseline"]:
        findings.append("drawing %s stands behind the design baseline issue" % ident)
    for ident in drawings["ahead_of_baseline"]:
        findings.append(
            "drawing %s stands ahead of the baseline issue; the baseline record is stale"
            % ident
        )
    for name in pad_sets["missing"]:
        findings.append("interface pad %s is not placed in the layout" % name)
    for name in pad_sets["repeated"]:
        findings.append("pad name %s is placed more than once" % name)
    for name in pad_sets["unexpected"]:
        findings.append("pad %s is placed but is not in the interface definition" % name)
    for name in outside:
        findings.append("pad %s breaks the outline keep-out" % name)
    if not pitch_met:
        findings.append(
            "pads %s and %s sit %.6g um apart, inside the %.6g um minimum pitch"
            % (closest["pair"][0], closest["pair"][1], closest["distance"], pitch)
        )
    for name in rule_checks["not_run"]:
        findings.append("required rule check %s was not run for this review" % name)
    for entry in rule_checks["residual"]:
        findings.append(
            "%s leaves %d error(s) neither cleared nor waived"
            % (entry["check"], entry["errors"])
        )
    for waiver_id in rule_checks["unapproved_waivers"]:
        findings.append("waiver %s is cited but carries no approval" % waiver_id)
    return {
        "drawings": drawings,
        "pad_set": pad_sets,
        "pads_outside_outline": outside,
        "closest_pad_pair": closest,
        "minimum_pitch_um": pitch,
        "pitch_met": pitch_met,
        "rule_checks": rule_checks,
        "findings": findings,
        "disposition": "closed" if not findings else "open",
    }
