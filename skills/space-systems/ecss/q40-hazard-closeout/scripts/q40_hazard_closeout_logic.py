"""Hazard reporting, review and close-out against the safety verification log.

Anchor: ECSS-Q-ST-40C clauses on hazard reporting and hazard review, on
safety-assurance verification of hazard close-out, and on the safety
verification tracking log (SVTL) whose content is given in the standard's
annex. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. A hazard closes through its controls, never directly. Each control carries
   one SVTL entry, and a control with no entry is untracked: it is not an open
   item, it is an item nobody is holding.
2. An SVTL entry discharges its control only when it is closed, carries an
   evidence reference, and the evidence has been accepted. Closed-with-no-
   evidence and closed-but-not-accepted are separate defects and read
   differently to the board.
3. The severity of the hazard decides what the close-out needs on top of the
   controls: a board endorsement at the severe end, and an acceptance
   reference wherever a residual risk is declared.
4. A close-out is all-or-nothing per hazard. A partial control set produces a
   closure fraction for tracking, but the hazard stays open.
5. Emit a close-out statement per hazard and an SVTL rollup over the log, so
   the review has the counts and the reasons in one place.
"""

__all__ = [
    "SEVERITIES",
    "SVTL_STATUSES",
    "ENDORSEMENT_REQUIRED_SEVERITIES",
    "validate_hazard",
    "svtl_entries",
    "untracked_controls",
    "control_findings",
    "hazard_level_findings",
    "closure_fraction",
    "close_out_hazard",
    "close_out_log",
]

SEVERITIES = ("catastrophic", "critical", "major", "minor")

SVTL_STATUSES = ("open", "in-work", "closed")

# Severities whose close-out needs the safety review board behind it.
ENDORSEMENT_REQUIRED_SEVERITIES = ("catastrophic", "critical")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _member(value, label, allowed):
    token = _text(value, label).lower()
    if token not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return token


def _flag(record, key):
    value = record.get(key, False)
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (key, value))
    return value


def _optional_text(value, label):
    if value is None:
        return None
    return _text(value, label)


def validate_hazard(record):
    """Return a normalised hazard report with its controls and SVTL entries."""
    if not isinstance(record, dict):
        raise ValueError("hazard report must be a mapping")
    raw_controls = record.get("controls", [])
    if not isinstance(raw_controls, (list, tuple)):
        raise ValueError("controls must be a sequence")
    if not raw_controls:
        raise ValueError("a hazard report needs at least one control")

    controls = []
    seen = set()
    for entry in raw_controls:
        if not isinstance(entry, dict):
            raise ValueError("each control must be a mapping, got %r" % (entry,))
        cid = _text(entry.get("id"), "control id")
        if cid in seen:
            raise ValueError("control id %r appears twice" % cid)
        seen.add(cid)
        svtl = entry.get("svtl_entry")
        if svtl is not None:
            if not isinstance(svtl, dict):
                raise ValueError("svtl_entry must be a mapping, got %r" % (svtl,))
            svtl = {
                "status": _member(svtl.get("status"), "svtl status", SVTL_STATUSES),
                "evidence_ref": _optional_text(svtl.get("evidence_ref"), "evidence_ref"),
                "evidence_accepted": _flag(svtl, "evidence_accepted"),
                "verification_method": _optional_text(
                    svtl.get("verification_method"), "verification_method"
                ),
            }
        controls.append({"id": cid, "svtl_entry": svtl})

    residual = _flag(record, "residual_risk_declared")
    acceptance = _optional_text(
        record.get("residual_risk_acceptance_ref"), "residual_risk_acceptance_ref"
    )

    return {
        "id": _text(record.get("id"), "id"),
        "severity": _member(record.get("severity"), "severity", SEVERITIES),
        "controls": controls,
        "residual_risk_declared": residual,
        "residual_risk_acceptance_ref": acceptance,
        "review_board_endorsed": _flag(record, "review_board_endorsed"),
    }


def svtl_entries(record):
    """Return the SVTL rows this hazard's tracked controls contribute."""
    norm = validate_hazard(record)
    rows = []
    for control in norm["controls"]:
        if control["svtl_entry"] is None:
            continue
        row = dict(control["svtl_entry"])
        row["hazard_id"] = norm["id"]
        row["control_id"] = control["id"]
        rows.append(row)
    return rows


def untracked_controls(record):
    """Return the control ids that have no SVTL entry holding them."""
    norm = validate_hazard(record)
    return [c["id"] for c in norm["controls"] if c["svtl_entry"] is None]


def control_findings(record):
    """Return one finding per control that does not discharge cleanly."""
    norm = validate_hazard(record)
    findings = []
    for control in norm["controls"]:
        entry = control["svtl_entry"]
        if entry is None:
            findings.append(
                {
                    "control_id": control["id"],
                    "reason": "control has no SVTL entry, so nobody is holding it",
                }
            )
            continue
        if entry["status"] != "closed":
            findings.append(
                {
                    "control_id": control["id"],
                    "reason": "SVTL entry is %s, not closed" % entry["status"],
                }
            )
            continue
        if entry["evidence_ref"] is None:
            findings.append(
                {
                    "control_id": control["id"],
                    "reason": "SVTL entry is closed with no evidence reference",
                }
            )
            continue
        if not entry["evidence_accepted"]:
            findings.append(
                {
                    "control_id": control["id"],
                    "reason": "evidence is cited but has not been accepted",
                }
            )
    return findings


def hazard_level_findings(record):
    """Return the findings that sit on the hazard rather than on a control."""
    norm = validate_hazard(record)
    findings = []
    if (
        norm["severity"] in ENDORSEMENT_REQUIRED_SEVERITIES
        and not norm["review_board_endorsed"]
    ):
        findings.append(
            "a %s hazard cannot be closed without the safety review board behind it"
            % norm["severity"]
        )
    if norm["residual_risk_declared"] and norm["residual_risk_acceptance_ref"] is None:
        findings.append(
            "a residual risk is declared with no acceptance reference against it"
        )
    if not norm["residual_risk_declared"] and norm["residual_risk_acceptance_ref"]:
        findings.append(
            "an acceptance reference is recorded but no residual risk is declared"
        )
    return findings


def closure_fraction(record):
    """Return the fraction of this hazard's controls that discharge cleanly."""
    norm = validate_hazard(record)
    blocked = set(item["control_id"] for item in control_findings(norm))
    clean = len(norm["controls"]) - len(blocked)
    return clean / float(len(norm["controls"]))


def close_out_hazard(record):
    """Return the close-out disposition and statement for one hazard report."""
    norm = validate_hazard(record)
    per_control = control_findings(norm)
    per_hazard = hazard_level_findings(norm)
    fraction = closure_fraction(norm)

    findings = [
        "%s: %s" % (item["control_id"], item["reason"]) for item in per_control
    ] + list(per_hazard)

    closed = not findings
    if closed:
        statement = (
            "hazard %s (%s): every control is closed in the SVTL on accepted evidence"
            % (norm["id"], norm["severity"])
        )
    else:
        statement = (
            "hazard %s (%s): close-out withheld, %d of %d controls discharge cleanly"
            % (
                norm["id"],
                norm["severity"],
                len(norm["controls"]) - len(set(i["control_id"] for i in per_control)),
                len(norm["controls"]),
            )
        )

    return {
        "id": norm["id"],
        "severity": norm["severity"],
        "svtl_entries": svtl_entries(norm),
        "untracked_controls": untracked_controls(norm),
        "control_findings": per_control,
        "hazard_findings": per_hazard,
        "closure_fraction": fraction,
        "findings": findings,
        "closed": closed,
        "disposition": "hazard-closed" if closed else "hazard-open",
        "close_out_statement": statement,
    }


def close_out_log(records):
    """Return the SVTL rollup and review status across a set of hazard reports."""
    items = list(records)
    if not items:
        raise ValueError("at least one hazard report is needed")
    reports = [close_out_hazard(item) for item in items]
    seen = set()
    for report in reports:
        if report["id"] in seen:
            raise ValueError("duplicate hazard id %r" % report["id"])
        seen.add(report["id"])

    open_ids = [r["id"] for r in reports if not r["closed"]]
    severe_open = [
        r["id"]
        for r in reports
        if not r["closed"] and r["severity"] in ENDORSEMENT_REQUIRED_SEVERITIES
    ]
    rows = []
    for report in reports:
        rows.extend(report["svtl_entries"])
    status_counts = dict((status, 0) for status in SVTL_STATUSES)
    for row in rows:
        status_counts[row["status"]] += 1
    closed_ratio = sum(1 for r in reports if r["closed"]) / float(len(reports))

    if severe_open:
        disposition = "log-blocked"
    elif open_ids:
        disposition = "log-open"
    else:
        disposition = "log-closed"

    return {
        "hazards": reports,
        "svtl_rows": rows,
        "svtl_status_counts": status_counts,
        "untracked_control_count": sum(len(r["untracked_controls"]) for r in reports),
        "open_hazard_ids": open_ids,
        "severe_open_hazard_ids": severe_open,
        "closed_ratio": closed_ratio,
        "disposition": disposition,
    }
