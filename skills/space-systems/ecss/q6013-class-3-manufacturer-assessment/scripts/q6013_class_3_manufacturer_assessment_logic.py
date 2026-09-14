"""Manufacturer capability assessment for commercial parts at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.2.3.2 (assessing the capability of a
commercial part manufacturer and the quality controls behind the product when
the part is used at the lowest assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Offline, deterministic, python3 standard library only.

Procedure implemented here
--------------------------
* The lowest assurance class accepts a lighter assessment, not a blank one.
  The control set is fixed; what the class changes is the level each control
  has to reach and the kind of evidence that may stand behind it.
* Every control is declared at a maturity level, from absent through informal
  and documented to documented and audited. The declared level is a claim; the
  evidence basis behind it puts a ceiling on what may be credited. A catalogue
  statement cannot credit a documented control, and a self-declaration or a
  third-party certificate cannot credit an audited one. The credited level is
  the lower of the two, and the gap is reported rather than silently absorbed.
* The capability level of the manufacturer is not an average. A core group of
  controls -- the quality system, the commitment to notify process changes and
  traceability back to a date-code lot -- is only as strong as its weakest
  member, so the capability level is the minimum credited level across that
  group, and the control that set it is named. Averaging would let a strong
  quality system pay for absent traceability, which is exactly the trade the
  minimum exists to refuse.
* The supporting controls do not set the level. They set the cadence: each one
  below the class floor shortens the surveillance interval, so a manufacturer
  with weak supporting controls is revisited sooner rather than downgraded.
* Evidence ages against that interval. Past it the assessment carries actions
  however well it scored, because the interval is the statement about how long
  the evidence was ever meant to hold.
"""

from __future__ import annotations

import math

# Controls the assessment covers, whatever the assurance class.
CAPABILITY_CONTROLS = (
    "quality-management-system",
    "process-change-notification",
    "date-code-lot-traceability",
    "outgoing-inspection-and-test",
    "failure-analysis-response",
    "discontinuance-notice",
)

# The controls whose weakest member fixes the capability level.
CORE_CONTROLS = (
    "quality-management-system",
    "process-change-notification",
    "date-code-lot-traceability",
)

# Declared maturity of one control.
MATURITY_LEVELS = {
    "control-absent": 0,
    "control-informal": 1,
    "control-documented": 2,
    "control-documented-and-audited": 3,
}

# Highest level the evidence basis behind a claim can support.
EVIDENCE_LEVEL_CEILING = {
    "on-site-audit": 3,
    "remote-audit": 3,
    "third-party-certificate": 2,
    "self-declared-questionnaire": 2,
    "catalogue-statement": 1,
    "no-evidence": 0,
}

# Level the core controls have to reach for use at the lowest assurance class.
CLASS_3_CAPABILITY_FLOOR = 2

# Months between surveillance visits, by the capability level reached.
SURVEILLANCE_BASE_MONTHS = {3: 36, 2: 24, 1: 12, 0: 6}

# Each supporting control under the floor pulls the next visit forward.
SURVEILLANCE_SHORTENING_MONTHS = 6

# No interval is shortened below this.
SURVEILLANCE_FLOOR_MONTHS = 6

VERDICTS = (
    "class-3-manufacturer-accepted",
    "class-3-manufacturer-accepted-with-actions",
    "class-3-manufacturer-rejected",
)

# Evidence age is a real quantity; an assessment landing exactly on its
# interval is inside it. The interval itself is never extended by this.
AGE_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def control_is_known(name):
    """Return the control name, rejecting anything outside the control set."""
    if name not in CAPABILITY_CONTROLS:
        raise ValueError(
            "unknown capability control %r (known: %s)"
            % (name, ", ".join(sorted(CAPABILITY_CONTROLS)))
        )
    return name


def maturity_level(maturity):
    """Numeric level of a declared control maturity."""
    if maturity not in MATURITY_LEVELS:
        raise ValueError(
            "unknown control maturity %r (known: %s)"
            % (maturity, ", ".join(sorted(MATURITY_LEVELS)))
        )
    return MATURITY_LEVELS[maturity]


def evidence_ceiling(basis):
    """Highest level the evidence basis behind a claim can support."""
    if basis not in EVIDENCE_LEVEL_CEILING:
        raise ValueError(
            "unknown evidence basis %r (known: %s)"
            % (basis, ", ".join(sorted(EVIDENCE_LEVEL_CEILING)))
        )
    return EVIDENCE_LEVEL_CEILING[basis]


def credited_level(maturity, basis):
    """Lower of the declared maturity and the ceiling its evidence supports."""
    return min(maturity_level(maturity), evidence_ceiling(basis))


def normalize_control(raw):
    """Validate one control declaration and fill in its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("control must be a mapping, got %r" % (type(raw).__name__,))
    name = control_is_known(raw.get("control"))
    maturity = raw.get("maturity", "control-absent")
    maturity_level(maturity)  # validation only
    basis = raw.get("evidence_basis", "no-evidence")
    evidence_ceiling(basis)  # validation only
    return {"control": name, "maturity": maturity, "evidence_basis": basis}


def assess_control(raw):
    """Grade one control into its credited level and its findings."""
    entry = normalize_control(raw)
    name = entry["control"]
    declared = maturity_level(entry["maturity"])
    ceiling = evidence_ceiling(entry["evidence_basis"])
    credited = min(declared, ceiling)
    is_core = name in CORE_CONTROLS
    findings = []
    if ceiling < declared:
        findings.append("control-level-capped-by-evidence")
    if credited < CLASS_3_CAPABILITY_FLOOR:
        findings.append(
            "core-control-below-class-3-floor" if is_core else "supporting-control-below-class-3-floor"
        )
    return {
        "control": name,
        "maturity": entry["maturity"],
        "evidence_basis": entry["evidence_basis"],
        "declared_level": declared,
        "evidence_ceiling": ceiling,
        "credited_level": credited,
        "core": is_core,
        "findings": findings,
    }


def governing_control(records):
    """Name the weakest core control and the level it fixes."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    core = [record for record in records if record.get("core")]
    if len(core) == 0:
        raise ValueError("an assessment must carry at least one core control")
    weakest = min(core, key=lambda record: (record["credited_level"], record["control"]))
    return (weakest["control"], weakest["credited_level"])


def surveillance_interval_months(capability_level, supporting_shortfalls):
    """Months to the next surveillance visit at this level and shortfall count."""
    if isinstance(capability_level, bool) or not isinstance(capability_level, int):
        raise ValueError(
            "capability_level must be an integer, got %r" % (capability_level,)
        )
    if capability_level not in SURVEILLANCE_BASE_MONTHS:
        raise ValueError(
            "capability_level %r is outside the level ladder" % (capability_level,)
        )
    if isinstance(supporting_shortfalls, bool) or not isinstance(
        supporting_shortfalls, int
    ):
        raise ValueError(
            "supporting_shortfalls must be an integer, got %r" % (supporting_shortfalls,)
        )
    if supporting_shortfalls < 0:
        raise ValueError(
            "supporting_shortfalls must not be negative, got %d" % (supporting_shortfalls,)
        )
    interval = SURVEILLANCE_BASE_MONTHS[capability_level]
    interval -= SURVEILLANCE_SHORTENING_MONTHS * supporting_shortfalls
    return max(SURVEILLANCE_FLOOR_MONTHS, interval)


def evidence_within_interval(age_months, interval_months):
    """True while the assessment evidence is inside its surveillance interval."""
    age = _real(age_months, "age_months")
    if age < 0.0:
        raise ValueError("age_months must not be negative, got %r" % (age_months,))
    limit = _real(interval_months, "interval_months")
    if limit <= 0.0:
        raise ValueError("interval_months must be positive, got %r" % (interval_months,))
    return age <= limit + AGE_TOLERANCE


def assess_manufacturer(manufacturer_id, controls, evidence_age_months=0.0):
    """Grade a commercial manufacturer for use at the lowest assurance class.

    Every control is graded, including the ones the submission left out
    entirely -- a control nobody mentioned is absent and unevidenced, not
    excused.
    """
    if not isinstance(manufacturer_id, str) or not manufacturer_id.strip():
        raise ValueError(
            "manufacturer_id must be a non-empty string, got %r" % (manufacturer_id,)
        )
    if not isinstance(controls, (list, tuple)):
        raise ValueError(
            "controls must be a list or tuple, got %r" % (type(controls).__name__,)
        )
    declared = {}
    for raw in controls:
        entry = normalize_control(raw)
        if entry["control"] in declared:
            raise ValueError("duplicate capability control %r" % (entry["control"],))
        declared[entry["control"]] = entry
    records = []
    for name in CAPABILITY_CONTROLS:
        records.append(
            assess_control(
                declared.get(
                    name,
                    {
                        "control": name,
                        "maturity": "control-absent",
                        "evidence_basis": "no-evidence",
                    },
                )
            )
        )
    weakest_control, capability_level = governing_control(records)
    shortfalls = [
        record["control"]
        for record in records
        if not record["core"] and record["credited_level"] < CLASS_3_CAPABILITY_FLOOR
    ]
    interval = surveillance_interval_months(capability_level, len(shortfalls))
    in_interval = evidence_within_interval(evidence_age_months, interval)
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"control": record["control"], "finding": finding})
    if not in_interval:
        findings.append(
            {"control": "assessment", "finding": "surveillance-evidence-overdue"}
        )
    meets_floor = capability_level >= CLASS_3_CAPABILITY_FLOOR
    if not meets_floor:
        verdict = "class-3-manufacturer-rejected"
    elif findings:
        verdict = "class-3-manufacturer-accepted-with-actions"
    else:
        verdict = "class-3-manufacturer-accepted"
    return {
        "manufacturer_id": manufacturer_id,
        "records": records,
        "capability_level": capability_level,
        "governing_control": weakest_control,
        "supporting_shortfalls": shortfalls,
        "surveillance_interval_months": interval,
        "evidence_within_interval": in_interval,
        "meets_class_3_floor": meets_floor,
        "findings": findings,
        "verdict": verdict,
    }
