#!/usr/bin/env python3
"""Test programme for the qualification and procurement of bare solar cells.

Anchor: ECSS-E-ST-20-08C clause 7.1.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A bare cell is the cell before any coverglass, interconnector or adhesive is
put on it, and the tests it goes through serve two different errands that are
easy to confuse because they share a test list.

Qualification asks: can this cell design, from this line, survive the
    mission? It is answered once per design and process baseline, largely by
    destructive and environmental testing, on cells drawn from a lot set aside
    for the purpose.

Procurement asks: is this delivery batch the same as the cell that was
    qualified? It is answered on every batch, by measurement rather than by
    environment, on a sample drawn from the batch being bought.

Three things therefore decide whether a declared programme is worth anything.

Does each activity run on a specimen its errand allows?
    A qualification result read off a procurement sample proves nothing about
    the design, and a destructive test run on a cell that is going to be
    delivered destroys the deliverable.

Is the sample big enough for the lot it speaks for?
    A procurement sample scales with the batch; a qualification sample does
    not, because it speaks for a design and not for a batch.

Does the programme cover what each errand needs covered?
    Coverage is per errand. A programme can be complete for procurement and
    empty for qualification while still looking busy.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "PURPOSES",
    "SPECIMEN_KINDS",
    "ALLOWED_SPECIMENS",
    "REQUIRED_ACTIVITIES",
    "DESTRUCTIVE_ACTIVITIES",
    "QUALIFICATION_MIN_SAMPLE",
    "PROCUREMENT_MIN_SAMPLE",
    "PROGRAMME_ACCEPTABLE",
    "PROGRAMME_WITH_FINDINGS",
    "PROGRAMME_NOT_ACCEPTABLE",
    "ceil_sqrt",
    "policy_sample_size",
    "specimen_allowed",
    "evaluate_activity",
    "programme_coverage",
    "qualification_share",
    "assess_bare_cell_programme",
]

PURPOSES = ("qualification", "procurement")

SPECIMEN_KINDS = (
    "qualification-lot-cell",
    "witness-cell",
    "procurement-lot-sample-cell",
    "delivered-cell",
)

# Which specimen kinds each errand may draw on. A delivered cell appears on
# neither list: it is the thing being bought, not a test article.
ALLOWED_SPECIMENS = {
    "qualification": ("qualification-lot-cell", "witness-cell"),
    "procurement": ("procurement-lot-sample-cell", "witness-cell"),
}

# The activity set each errand owes. Qualification carries the environments;
# procurement carries the measurements that show a batch matches the design.
REQUIRED_ACTIVITIES = {
    "qualification": (
        "visual-inspection",
        "dimensional-measurement",
        "electrical-performance",
        "spectral-response",
        "thermo-optical-measurement",
        "contact-adherence",
        "humidity-exposure",
        "thermal-cycling",
        "particle-irradiation",
        "ultraviolet-exposure",
        "reverse-bias",
    ),
    "procurement": (
        "visual-inspection",
        "dimensional-measurement",
        "electrical-performance",
        "mass-measurement",
    ),
}

# Activities that consume or alter the specimen beyond re-use.
DESTRUCTIVE_ACTIVITIES = (
    "contact-adherence",
    "humidity-exposure",
    "thermal-cycling",
    "particle-irradiation",
    "ultraviolet-exposure",
    "reverse-bias",
)

# A qualification sample speaks for a design, so its floor is fixed. A
# procurement sample speaks for a batch, so its floor grows with the batch.
QUALIFICATION_MIN_SAMPLE = 6
PROCUREMENT_MIN_SAMPLE = 5

PROGRAMME_ACCEPTABLE = "programme-acceptable"
PROGRAMME_WITH_FINDINGS = "programme-acceptable-with-findings"
PROGRAMME_NOT_ACCEPTABLE = "programme-not-acceptable"

# Shares are ratios of small counts, but they are still compared with
# fractional thresholds, so the comparison absorbs representation error while
# the threshold itself stays as written.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _positive_int(label, value):
    """Return value as a positive integer count, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _at_least(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    return value > bound or math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def ceil_sqrt(count):
    """Return the smallest integer whose square is at least count.

    Done in integer arithmetic on purpose: math.sqrt of a perfect square can
    land a hair under the exact root on one platform and exactly on it on
    another, which would move a sample-size floor by one cell.
    """
    n = _positive_int("count", count)
    root = math.isqrt(n)
    return root if root * root == n else root + 1


def policy_sample_size(lot_size, purpose):
    """Return the minimum specimen count an errand owes for a lot of this size."""
    if purpose not in PURPOSES:
        raise ValueError("purpose must be one of %s, got %r" % (PURPOSES, purpose))
    size = _positive_int("lot_size", lot_size)
    if purpose == "qualification":
        floor = QUALIFICATION_MIN_SAMPLE
    else:
        floor = max(PROCUREMENT_MIN_SAMPLE, ceil_sqrt(size))
    return min(floor, size)


def specimen_allowed(purpose, specimen, activity=None):
    """Decide whether a specimen kind may carry an activity for this errand."""
    if purpose not in PURPOSES:
        raise ValueError("purpose must be one of %s, got %r" % (PURPOSES, purpose))
    if specimen not in SPECIMEN_KINDS:
        raise ValueError(
            "specimen must be one of %s, got %r" % (SPECIMEN_KINDS, specimen)
        )
    if specimen == "delivered-cell":
        reason = (
            "a cell destined for delivery is not a test article; running "
            "%s on it consumes the deliverable"
            % (activity if activity else "an activity")
        )
        return {"allowed": False, "reason": reason}
    if specimen not in ALLOWED_SPECIMENS[purpose]:
        return {
            "allowed": False,
            "reason": "a %s specimen cannot answer a %s question"
                      % (specimen, purpose),
        }
    if activity in DESTRUCTIVE_ACTIVITIES and specimen == "procurement-lot-sample-cell":
        return {
            "allowed": True,
            "reason": "destructive activity consumes the procurement sample; "
                      "the sampled cells do not return to the batch",
        }
    return {"allowed": True, "reason": None}


def evaluate_activity(activity, lot_size):
    """Grade one declared programme activity against its errand.

    activity keys: name, purpose, specimen, sample_size.
    """
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    for key in ("name", "purpose", "specimen", "sample_size"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    name = activity["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("activity name must be a non-empty string")
    name = name.strip()
    purpose = activity["purpose"]
    if purpose not in PURPOSES:
        raise ValueError("purpose must be one of %s, got %r" % (PURPOSES, purpose))
    specimen = activity["specimen"]
    declared = _positive_int("sample_size", activity["sample_size"])
    size = _positive_int("lot_size", lot_size)

    findings = []
    placement = specimen_allowed(purpose, specimen, name)
    if not placement["allowed"]:
        findings.append("%s: %s" % (name, placement["reason"]))

    if declared > size:
        findings.append(
            "%s draws %d specimens from a lot of %d" % (name, declared, size)
        )

    floor = policy_sample_size(size, purpose)
    undersized = declared < floor
    if undersized:
        findings.append(
            "%s runs on %d specimens where the %s policy floor for a lot of %d "
            "is %d" % (name, declared, purpose, size, floor)
        )

    off_list = name not in REQUIRED_ACTIVITIES[purpose]
    return {
        "name": name,
        "purpose": purpose,
        "specimen": specimen,
        "sample_size": declared,
        "policy_sample_size": floor,
        "destructive": name in DESTRUCTIVE_ACTIVITIES,
        "specimen_allowed": placement["allowed"],
        "sample_adequate": not undersized and declared <= size,
        "off_required_list": off_list,
        "acceptable": placement["allowed"] and not undersized and declared <= size,
        "findings": findings,
    }


def programme_coverage(records):
    """Return per-errand coverage of the required activity sets."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of evaluated activities")
    coverage = {}
    for purpose in PURPOSES:
        required = REQUIRED_ACTIVITIES[purpose]
        present = set()
        for record in records:
            if not isinstance(record, dict) or "name" not in record:
                raise ValueError("each record must be a mapping carrying 'name'")
            if record.get("purpose") != purpose:
                continue
            if record["name"] in required and record.get("acceptable", False):
                present.add(record["name"])
        missing = [item for item in required if item not in present]
        coverage[purpose] = {
            "required": list(required),
            "covered": sorted(present),
            "missing": missing,
            "fraction": float(len(present)) / float(len(required)),
        }
    return coverage


def qualification_share(records):
    """Return the share of declared activities that serve qualification."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    total = 0
    qualification = 0
    for record in records:
        if not isinstance(record, dict) or "purpose" not in record:
            raise ValueError("each record must be a mapping carrying 'purpose'")
        if record["purpose"] not in PURPOSES:
            raise ValueError("unknown purpose %r" % (record["purpose"],))
        total += 1
        if record["purpose"] == "qualification":
            qualification += 1
    return float(qualification) / float(total)


def assess_bare_cell_programme(spec):
    """Grade one declared bare-cell test programme.

    spec keys: lot_size, activities, optional required_coverage (a fraction
    each errand's coverage must reach) and errands (the errands the programme
    claims to serve; defaults to both).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "activities"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    activities = spec["activities"]
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("spec['activities'] must be a non-empty sequence")

    errands = spec.get("errands", PURPOSES)
    if not isinstance(errands, (list, tuple)) or not errands:
        raise ValueError("spec['errands'] must be a non-empty sequence")
    for errand in errands:
        if errand not in PURPOSES:
            raise ValueError("errand must be one of %s, got %r" % (PURPOSES, errand))

    required_coverage = spec.get("required_coverage", 1.0)
    if isinstance(required_coverage, bool) or not isinstance(
        required_coverage, (int, float)
    ):
        raise ValueError("required_coverage must be a real number")
    required_coverage = float(required_coverage)
    if not math.isfinite(required_coverage) or not 0.0 < required_coverage <= 1.0:
        raise ValueError(
            "required_coverage must lie in (0, 1], got %r" % (spec.get("required_coverage"),)
        )

    lot_size = _positive_int("lot_size", spec["lot_size"])
    records = [evaluate_activity(item, lot_size) for item in activities]
    seen = set()
    for record in records:
        key = (record["purpose"], record["name"])
        if key in seen:
            raise ValueError(
                "activity %s is declared twice for the %s errand"
                % (record["name"], record["purpose"])
            )
        seen.add(key)

    coverage = programme_coverage(records)
    share = qualification_share(records)

    findings = []
    for record in records:
        findings.extend(record["findings"])
    for errand in errands:
        fraction = coverage[errand]["fraction"]
        if not _at_least(fraction, required_coverage):
            findings.append(
                "%s coverage is %.3f against a required %.3f; %s not covered"
                % (errand, fraction, required_coverage,
                   ", ".join(coverage[errand]["missing"]))
            )
    off_list = [r["name"] for r in records if r["off_required_list"]]
    if off_list:
        findings.append(
            "declared outside the required set and carried as supplementary: %s"
            % ", ".join(sorted(set(off_list)))
        )

    blocking = any(not r["acceptable"] for r in records) or any(
        not _at_least(coverage[e]["fraction"], required_coverage) for e in errands
    )
    if blocking:
        verdict = PROGRAMME_NOT_ACCEPTABLE
    elif findings:
        verdict = PROGRAMME_WITH_FINDINGS
    else:
        verdict = PROGRAMME_ACCEPTABLE

    return {
        "lot_size": lot_size,
        "records": records,
        "coverage": coverage,
        "qualification_share": share,
        "errands": list(errands),
        "required_coverage": required_coverage,
        "verdict": verdict,
        "findings": findings,
    }
