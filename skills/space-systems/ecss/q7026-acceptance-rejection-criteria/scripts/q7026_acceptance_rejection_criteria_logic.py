"""Acceptance and rejection criteria for crimped terminations.

Anchor: ECSS-Q-ST-70-26C, the acceptance clause of the crimping
practice -- turning what an inspector wrote down into a disposition,
one defect category at a time (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Findings are graded per defect category, not as a heap. Each
   category carries its own severity, and the severity decides the
   route: scrap, back to the bench, accept with the finding on the
   record, or accept outright.
2. The worst finding governs the termination. Severities are not
   averaged and they do not cancel; a single major finding takes the
   termination out whatever else passed.
3. A defect code nobody declared a severity for is unknown, not
   harmless. Guessing it accepts a termination on a category that was
   never agreed.
4. Pull-off force is graded against the minimum tabulated for that
   conductor size, and an untabulated size is refused rather than
   interpolated: the table is a stepped requirement, not a curve.
5. The strand-damage allowance scales with the conductor. A fraction
   of a fat conductor's strands is a real allowance; the same fraction
   of a thin one rounds to nothing, and below a stated strand count no
   damage is allowed at all.
6. A rejected sample says something about the lot, not only about the
   sample. Sampled inspection escalates to full inspection on a
   rejection instead of discarding the one bad unit.

Stdlib only, offline, deterministic.
"""

TOLERANCE = 1.0e-9

MAJOR = "major-reject"
REWORKABLE = "reworkable"
MINOR = "minor-accept-with-record"
COSMETIC = "cosmetic-accept"

SEVERITY_RANK = {COSMETIC: 0, MINOR: 1, REWORKABLE: 2, MAJOR: 3}

ACCEPTED = "accepted"
ACCEPTED_WITH_RECORD = "accepted-with-record"
REWORK = "returned-for-rework"
REJECTED = "rejected"

SEVERITY_TO_DISPOSITION = {
    COSMETIC: ACCEPTED,
    MINOR: ACCEPTED_WITH_RECORD,
    REWORKABLE: REWORK,
    MAJOR: REJECTED,
}

LOT_ACCEPTED = "lot-accepted"
LOT_ACCEPTED_WITH_FINDINGS = "lot-accepted-with-findings"
LOT_ESCALATED = "lot-escalated-to-full-inspection"
LOT_REJECTED = "lot-rejected"


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


def validate_criteria(criteria):
    """Validate the declared per-category acceptance criteria."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping")

    severities = criteria.get("defect_severities")
    if not isinstance(severities, dict) or not severities:
        raise ValueError("defect_severities must be a non-empty mapping")
    graded = {}
    for code, severity in severities.items():
        key = _text("defect_code", code).lower()
        if severity not in SEVERITY_RANK:
            raise ValueError(
                "severity %r for defect %r is not a declared severity"
                % (severity, key)
            )
        graded[key] = severity

    table = criteria.get("pull_off_minimum_n")
    if not isinstance(table, list) or not table:
        raise ValueError("pull_off_minimum_n must be a non-empty list")
    rows = []
    seen = []
    for row in table:
        if not isinstance(row, dict):
            raise ValueError("each pull_off_minimum_n row must be a mapping")
        csa = _numeric("csa_mm2", row.get("csa_mm2"), 0.0)
        if csa <= 0.0:
            raise ValueError("csa_mm2 must be greater than zero")
        force = _numeric("minimum_n", row.get("minimum_n"), 0.0)
        if force <= 0.0:
            raise ValueError("minimum_n must be greater than zero")
        for previous in seen:
            if abs(previous - csa) <= TOLERANCE:
                raise ValueError("csa_mm2 %r is tabulated twice" % csa)
        seen.append(csa)
        rows.append({"csa_mm2": csa, "minimum_n": force})
    rows.sort(key=lambda r: r["csa_mm2"])

    fraction = _numeric(
        "max_damaged_strand_fraction",
        criteria.get("max_damaged_strand_fraction"),
        0.0,
    )
    if fraction > 1.0:
        raise ValueError("max_damaged_strand_fraction must not exceed one")

    return {
        "defect_severities": graded,
        "pull_off_minimum_n": rows,
        "max_damaged_strand_fraction": fraction,
        "min_strands_for_any_damage": _count(
            "min_strands_for_any_damage",
            criteria.get("min_strands_for_any_damage", 1),
            1,
        ),
        "sample_size": _count("sample_size", criteria.get("sample_size", 1), 1),
    }


def validate_termination(termination):
    """Validate one inspected termination."""
    if not isinstance(termination, dict):
        raise ValueError("termination must be a mapping")
    csa = _numeric("conductor_csa_mm2", termination.get("conductor_csa_mm2"), 0.0)
    if csa <= 0.0:
        raise ValueError("conductor_csa_mm2 must be greater than zero")
    strands = _count("strand_count", termination.get("strand_count"), 1)
    damaged = _count(
        "damaged_strands", termination.get("damaged_strands", 0), 0
    )
    if damaged > strands:
        raise ValueError("damaged_strands cannot exceed strand_count")
    defects = termination.get("defect_codes", [])
    if not isinstance(defects, list):
        raise ValueError("defect_codes must be a list")
    pull = termination.get("pull_off_force_n")
    return {
        "termination_id": _text(
            "termination_id", termination.get("termination_id")
        ),
        "conductor_csa_mm2": csa,
        "strand_count": strands,
        "damaged_strands": damaged,
        "defect_codes": [_text("defect_code", d).lower() for d in defects],
        "pull_off_force_n": (
            None if pull is None else _numeric("pull_off_force_n", pull, 0.0)
        ),
    }


def minimum_pull_off_force(csa_mm2, criteria):
    """Look the tabulated minimum pull-off force up for a conductor size."""
    checked = validate_criteria(criteria)
    size = _numeric("csa_mm2", csa_mm2, 0.0)
    for row in checked["pull_off_minimum_n"]:
        if abs(row["csa_mm2"] - size) <= TOLERANCE:
            return row["minimum_n"]
    raise ValueError(
        "conductor size %r is not tabulated; obtain the criterion rather "
        "than interpolating it" % size
    )


def grade_pull_off(force_n, csa_mm2, criteria):
    """Grade a measured pull-off force against its tabulated minimum."""
    minimum = minimum_pull_off_force(csa_mm2, criteria)
    measured = _numeric("force_n", force_n, 0.0)
    return {
        "minimum_n": minimum,
        "measured_n": measured,
        "margin_n": measured - minimum,
        "pass": measured >= minimum - TOLERANCE,
    }


def strand_damage_allowance(strand_count, criteria):
    """How many damaged strands this conductor is allowed."""
    checked = validate_criteria(criteria)
    strands = _count("strand_count", strand_count, 1)
    if strands < checked["min_strands_for_any_damage"]:
        return 0
    return int(strands * checked["max_damaged_strand_fraction"] + TOLERANCE)


def grade_strand_damage(damaged_strands, strand_count, criteria):
    """Grade the number of damaged strands against the allowance."""
    allowed = strand_damage_allowance(strand_count, criteria)
    damaged = _count("damaged_strands", damaged_strands, 0)
    if damaged > _count("strand_count", strand_count, 1):
        raise ValueError("damaged_strands cannot exceed strand_count")
    return {
        "allowed": allowed,
        "damaged": damaged,
        "pass": damaged <= allowed,
    }


def categorize_defect(defect_code, criteria):
    """Return the declared severity of one defect category."""
    checked = validate_criteria(criteria)
    code = _text("defect_code", defect_code).lower()
    if code not in checked["defect_severities"]:
        raise ValueError(
            "defect category %r has no declared severity" % code
        )
    return checked["defect_severities"][code]


def governing_severity(severities):
    """The worst severity in a set of findings governs the termination."""
    if not isinstance(severities, list):
        raise ValueError("severities must be a list")
    worst = None
    for severity in severities:
        if severity not in SEVERITY_RANK:
            raise ValueError("%r is not a declared severity" % severity)
        if worst is None or SEVERITY_RANK[severity] > SEVERITY_RANK[worst]:
            worst = severity
    return worst


def assess_termination(termination, criteria):
    """Decide the disposition of one inspected termination."""
    checked = validate_termination(termination)
    findings = []
    severities = []

    for code in checked["defect_codes"]:
        severity = categorize_defect(code, criteria)
        severities.append(severity)
        findings.append("%s:%s" % (code, severity))

    pull = None
    if checked["pull_off_force_n"] is not None:
        pull = grade_pull_off(
            checked["pull_off_force_n"], checked["conductor_csa_mm2"], criteria
        )
        if not pull["pass"]:
            severities.append(MAJOR)
            findings.append("pull-off-force-below-the-minimum:%s" % MAJOR)

    strands = grade_strand_damage(
        checked["damaged_strands"], checked["strand_count"], criteria
    )
    if not strands["pass"]:
        severities.append(MAJOR)
        findings.append("damaged-strands-above-the-allowance:%s" % MAJOR)

    worst = governing_severity(severities)
    disposition = ACCEPTED if worst is None else SEVERITY_TO_DISPOSITION[worst]

    return {
        "termination_id": checked["termination_id"],
        "disposition": disposition,
        "governing_severity": worst,
        "findings": findings,
        "pull_off": pull,
        "strand_damage": strands,
        "conforming": disposition in (ACCEPTED, ACCEPTED_WITH_RECORD),
    }


def assess_lot(terminations, criteria, sampled=False):
    """Roll graded terminations up into a lot disposition."""
    if not isinstance(terminations, list) or not terminations:
        raise ValueError("terminations must be a non-empty list")
    if not isinstance(sampled, bool):
        raise ValueError("sampled must be a boolean")
    checked = validate_criteria(criteria)
    if sampled and len(terminations) < checked["sample_size"]:
        raise ValueError(
            "a sampled inspection needs at least %d terminations"
            % checked["sample_size"]
        )

    results = [assess_termination(t, criteria) for t in terminations]
    rejected = [r["termination_id"] for r in results if r["disposition"] == REJECTED]
    rework = [r["termination_id"] for r in results if r["disposition"] == REWORK]
    recorded = [
        r["termination_id"]
        for r in results
        if r["disposition"] == ACCEPTED_WITH_RECORD
    ]

    if rejected or rework:
        lot = LOT_ESCALATED if sampled else LOT_REJECTED
    elif recorded:
        lot = LOT_ACCEPTED_WITH_FINDINGS
    else:
        lot = LOT_ACCEPTED

    return {
        "results": results,
        "lot_disposition": lot,
        "rejected": rejected,
        "returned_for_rework": rework,
        "accepted_with_record": recorded,
        "inspected": len(results),
    }
