#!/usr/bin/env python3
"""Delivered coverglasses against the route their process document fixes.

Anchor: ECSS-E-ST-20-08C clause 8.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass delivery is not a quantity of glass. It is a population
produced by an ordered processing route and released by the inspections
that route calls for, so the build paperwork decides the delivery before
a single piece is counted.

Coverglasses arrive as batches -- a forming batch, a coating run, a
cutting run -- each with its own route record, its own inspection
records and its own piece count. The release question is answered per
batch and then weighted by the pieces each batch carries.

Process document standing
    approved    the document binds the supplier
    superseded  it bound the supplier once, and something replaced it
    draft       nobody signed it
    withdrawn   it was taken back

Route steps, in the order a coverglass is normally taken through
    glass-forming
    cutting-and-sizing
    edge-finishing
    cleaning
    ar-coating-deposition
    uv-filter-deposition
    conductive-coating-deposition
    marking-and-packaging

Order is load-bearing here in a way it is not for a piece part. A
coating laid down before the clean that was meant to precede it is a
different article from the one the document describes, even though both
routes list the same two steps.

Inspection modes
    per-coverglass-screen  run on every piece; failures simply do not ship
    sampled-inspection     run on a few; they speak for the rest

A sample cannot discharge a screen, and a screen run on a sample is a
screen that did not happen. The two also fail differently: yield loss
inside a screen is normal, while one failure inside a sample is evidence
about every piece the sample stood for.

The sampling floor, the required inspection set and their owed modes
below are declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DOCUMENT_STATUSES = ("approved", "superseded", "draft", "withdrawn")

STANDING_CURRENT = "document-governing-at-built-issue"
STANDING_OFF_ISSUE = "document-governing-off-issue"
STANDING_NOT_GOVERNING = "document-not-governing"

ROUTE_STEPS = (
    "glass-forming",
    "cutting-and-sizing",
    "edge-finishing",
    "cleaning",
    "ar-coating-deposition",
    "uv-filter-deposition",
    "conductive-coating-deposition",
    "marking-and-packaging",
)

_ROUTE_INDEX = {step: i for i, step in enumerate(ROUTE_STEPS)}

INSPECTION_MODES = ("per-coverglass-screen", "sampled-inspection")

BATCH_RELEASED = "batch-released"
BATCH_CONCESSION = "batch-released-under-concession"
BATCH_WITHHELD = "batch-withheld"

BATCH_RANK = {
    BATCH_WITHHELD: 0,
    BATCH_CONCESSION: 1,
    BATCH_RELEASED: 2,
}

DEFAULT_DELIVERY_POLICY = {
    "min_sample_size": 3,
    "required_inspections": {
        "visual-defect-screen": "per-coverglass-screen",
        "dimensional-check": "sampled-inspection",
        "coating-transmission-check": "sampled-inspection",
    },
    "min_release_share": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("%s must be a non-empty sequence, got %r" % (name, value))
    return list(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A release share is a quotient of two counts and the threshold is a
    round fraction, so a delivery cut exactly to the threshold can
    evaluate a unit in the last place under it and read as short on one
    platform and as met on another. The comparison absorbs that; the
    threshold stays as declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_document_standing(status, approved_issue, built_issue):
    """Decide whether the cited process document governs the batch.

    Three outcomes, not two. An approved document at the issue the glass
    was built to governs outright. A draft or a withdrawn document
    governs nothing. A superseded document, or an approved one at an
    issue the batch was not built to, governs enough to release under a
    written concession once the difference is dispositioned.
    """
    state = _require_choice("status", status, DOCUMENT_STATUSES)
    approved = _require_label("approved_issue", approved_issue)
    built = _require_label("built_issue", built_issue)
    findings = []

    if state == "draft":
        standing = STANDING_NOT_GOVERNING
        findings.append(
            "the cited process document is a draft; nothing binds the supplier "
            "to keep building the route it describes"
        )
    elif state == "withdrawn":
        standing = STANDING_NOT_GOVERNING
        findings.append(
            "the cited process document has been withdrawn, so the batch was "
            "built against a route nobody now stands behind"
        )
    elif state == "superseded":
        standing = STANDING_OFF_ISSUE
        findings.append(
            "the cited process document was superseded; it was approved once, "
            "which is exactly why the difference between the issues has to be "
            "dispositioned"
        )
    elif approved != built:
        standing = STANDING_OFF_ISSUE
        findings.append(
            "the approved issue is %s and the batch was built to %s; the "
            "difference needs a written concession" % (approved, built)
        )
    else:
        standing = STANDING_CURRENT

    return {
        "status": state,
        "approved_issue": approved,
        "built_issue": built,
        "standing": standing,
        "governs": standing != STANDING_NOT_GOVERNING,
        "findings": findings,
    }


def route_conformance(declared_route, executed_route):
    """Compare the route actually run against the route the document fixes.

    Three separate readings come out of one comparison: a step run that
    the document never declares, a declared step the batch did not need,
    and a declared step run out of the declared sequence.
    """
    declared = _require_sequence("declared_route", declared_route)
    executed = _require_sequence("executed_route", executed_route)

    seen = []
    for step in declared:
        name = _require_choice("declared route step", step, ROUTE_STEPS)
        if name in seen:
            raise ValueError("declared route step %r appears twice" % name)
        seen.append(name)
    declared = seen

    ran = []
    for step in executed:
        name = _require_choice("executed route step", step, ROUTE_STEPS)
        if name in ran:
            raise ValueError("executed route step %r appears twice" % name)
        ran.append(name)
    executed = ran

    undeclared = [s for s in executed if s not in declared]
    not_run = [s for s in declared if s not in executed]

    position = {s: i for i, s in enumerate(declared)}
    covered = [s for s in executed if s in position]
    out_of_order = []
    highest = -1
    for step in covered:
        if position[step] < highest:
            out_of_order.append(step)
        else:
            highest = position[step]

    findings = []
    for step in undeclared:
        findings.append(
            "%s was run and the process document never declares it; the batch "
            "is off document whatever the merits of the step" % step
        )
    for step in out_of_order:
        findings.append(
            "%s was run out of the declared sequence; the same steps in a "
            "different order do not make the same article" % step
        )
    for step in not_run:
        findings.append(
            "%s is declared and was not run; the document covers more than this "
            "batch needed, which is a note and not a defect" % step
        )

    return {
        "declared_route": declared,
        "executed_route": executed,
        "undeclared_steps": undeclared,
        "declared_not_run": not_run,
        "out_of_order_steps": out_of_order,
        "conforms": not undeclared and not out_of_order,
        "findings": findings,
    }


def sampling_floor(batch_count, policy=None):
    """Smallest sample the policy accepts for a batch of this size.

    Deliberately integer arithmetic end to end: a sampling floor derived
    through a square root in floating point lands on different integers
    on different platforms when the count is a perfect square.
    """
    count = _require_count("batch_count", batch_count, minimum=1)
    settings = _policy(policy)
    minimum = _require_count(
        "min_sample_size", settings.get("min_sample_size"), minimum=1
    )
    floor = math.isqrt(count) + 1
    if floor < minimum:
        floor = minimum
    if floor > count:
        floor = count
    return floor


def _policy(policy):
    settings = dict(DEFAULT_DELIVERY_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    return settings


def grade_inspection_record(record, batch_count, policy=None):
    """Grade one inspection record against the batch it was run on."""
    _require_mapping("record", record)
    count = _require_count("batch_count", batch_count, minimum=1)
    settings = _policy(policy)
    required = _require_mapping(
        "required_inspections", settings.get("required_inspections")
    )

    name = _require_label("inspection", record.get("inspection"))
    mode = _require_choice("mode", record.get("mode"), INSPECTION_MODES)
    covered = _require_count("pieces_inspected", record.get("pieces_inspected"))
    failures = _require_count("pieces_failed", record.get("pieces_failed"))

    if covered > count:
        raise ValueError(
            "an inspection cannot cover %d pieces in a batch of %d" % (covered, count)
        )
    if failures > covered:
        raise ValueError(
            "%d failures cannot come out of %d pieces inspected" % (failures, covered)
        )

    owed = required.get(name)
    findings = []
    mode_ok = True
    if owed is None:
        findings.append(
            "%s is not an inspection the release policy asks for; it is carried "
            "as extra evidence and discharges nothing" % name
        )
    elif owed != mode:
        mode_ok = False
        findings.append(
            "%s is owed as a %s and was run as a %s" % (name, owed, mode)
        )

    floor = sampling_floor(count, settings)
    coverage_ok = True
    if mode == "per-coverglass-screen":
        if covered < count:
            coverage_ok = False
            findings.append(
                "%s screened %d of %d pieces; the pieces it never looked at are "
                "about to ship unscreened" % (name, covered, count)
            )
        failure_kind = "screen-yield-loss" if failures else "none"
        if failures:
            findings.append(
                "%s removed %d piece(s) as yield loss; they are simply not "
                "delivered" % (name, failures)
            )
    else:
        if covered < floor:
            coverage_ok = False
            findings.append(
                "%s sampled %d pieces against a floor of %d for a batch of %d"
                % (name, covered, floor, count)
            )
        failure_kind = "sample-evidence" if failures else "none"
        if failures:
            findings.append(
                "%s failed %d sampled piece(s); that is evidence about every "
                "piece the sample stood for, not yield" % (name, failures)
            )

    return {
        "inspection": name,
        "mode": mode,
        "owed_mode": owed,
        "pieces_inspected": covered,
        "pieces_failed": failures,
        "sampling_floor": floor,
        "mode_ok": mode_ok,
        "coverage_ok": coverage_ok,
        "failure_kind": failure_kind,
        "acceptable": mode_ok and coverage_ok and failure_kind != "sample-evidence",
        "findings": findings,
    }


def deliverable_count_bracket(batch_count, screen_records):
    """Bracket how many pieces passed every per-coverglass screen.

    Counts alone cannot settle this. Two screens reporting two and five
    failures may have failed the same pieces or different ones, so the
    answer is a bracket: at most the smallest pass count, at least the
    batch less every failure and every screen coverage gap. The lower
    bound is what the batch is released against.
    """
    count = _require_count("batch_count", batch_count, minimum=1)
    if not isinstance(screen_records, (list, tuple)):
        raise ValueError("screen_records must be a sequence of screen records")

    pass_counts = []
    total_failures = 0
    uncovered = 0
    for record in screen_records:
        _require_mapping("screen record", record)
        covered = _require_count("pieces_inspected", record.get("pieces_inspected"))
        failures = _require_count("pieces_failed", record.get("pieces_failed"))
        if covered > count:
            raise ValueError(
                "a screen cannot cover %d pieces in a batch of %d" % (covered, count)
            )
        if failures > covered:
            raise ValueError(
                "%d failures cannot come out of %d pieces screened"
                % (failures, covered)
            )
        pass_counts.append(covered - failures)
        total_failures += failures
        uncovered += count - covered

    if not pass_counts:
        return {
            "batch_count": count,
            "screens": 0,
            "at_most": 0,
            "at_least": 0,
            "total_failures": 0,
            "uncovered_slots": 0,
            "findings": [
                "no per-coverglass screen recorded a result, so no piece in the "
                "batch is known to have passed one"
            ],
        }

    at_most = min(pass_counts)
    at_least = count - total_failures - uncovered
    if at_least < 0:
        at_least = 0
    if at_least > at_most:
        at_least = at_most

    findings = []
    if at_least < at_most:
        findings.append(
            "between %d and %d pieces passed every screen; the failures may or "
            "may not overlap, and %d is what the batch releases against"
            % (at_least, at_most, at_least)
        )
    if uncovered:
        findings.append(
            "%d screen coverage gap(s) leave pieces that are neither passes nor "
            "failures; counting them as either is a choice made by accident"
            % uncovered
        )
    return {
        "batch_count": count,
        "screens": len(pass_counts),
        "at_most": at_most,
        "at_least": at_least,
        "total_failures": total_failures,
        "uncovered_slots": uncovered,
        "findings": findings,
    }


def assess_coverglass_batch(batch, policy=None):
    """Disposition one delivered coverglass batch against clause 8.3.2."""
    _require_mapping("batch", batch)
    settings = _policy(policy)
    required = _require_mapping(
        "required_inspections", settings.get("required_inspections")
    )

    batch_id = _require_label("batch_id", batch.get("batch_id"))
    count = _require_count("piece_count", batch.get("piece_count"), minimum=1)

    document = _require_mapping("process_document", batch.get("process_document"))
    standing = resolve_document_standing(
        document.get("status"),
        document.get("approved_issue"),
        document.get("built_issue"),
    )
    route = route_conformance(
        batch.get("declared_route"), batch.get("executed_route")
    )

    records = batch.get("inspections")
    if not isinstance(records, (list, tuple)):
        raise ValueError("batch must carry an inspections sequence")
    graded = [grade_inspection_record(r, count, settings) for r in records]

    present = {g["inspection"] for g in graded}
    missing = sorted(name for name in required if name not in present)

    findings = ["%s: %s" % (batch_id, f) for f in standing["findings"]]
    findings.extend("%s: %s" % (batch_id, f) for f in route["findings"])
    for grade in graded:
        findings.extend("%s: %s" % (batch_id, f) for f in grade["findings"])
    for name in missing:
        findings.append(
            "%s: %s is owed and no record carries a result for it; a listed "
            "inspection with no result is a missing one" % (batch_id, name)
        )

    screens = [
        r
        for r, g in zip(records, graded)
        if g["mode"] == "per-coverglass-screen" and g["owed_mode"] is not None
    ]
    bracket = deliverable_count_bracket(count, screens)
    findings.extend("%s: %s" % (batch_id, f) for f in bracket["findings"])

    sample_evidence = [g for g in graded if g["failure_kind"] == "sample-evidence"]
    wrong_mode = [g for g in graded if not g["mode_ok"]]
    undersized = [
        g
        for g in graded
        if g["mode"] == "sampled-inspection" and not g["coverage_ok"]
    ]
    partial_screen = [
        g
        for g in graded
        if g["mode"] == "per-coverglass-screen" and not g["coverage_ok"]
    ]

    if (
        not standing["governs"]
        or route["undeclared_steps"]
        or route["out_of_order_steps"]
        or missing
        or wrong_mode
        or undersized
        or sample_evidence
    ):
        disposition = BATCH_WITHHELD
        released = 0
    elif standing["standing"] == STANDING_OFF_ISSUE or partial_screen:
        disposition = BATCH_CONCESSION
        released = bracket["at_least"]
    else:
        disposition = BATCH_RELEASED
        released = bracket["at_least"]

    return {
        "batch_id": batch_id,
        "piece_count": count,
        "document_standing": standing["standing"],
        "route": route,
        "inspections": graded,
        "missing_inspections": missing,
        "deliverable_bracket": bracket,
        "released_pieces": released,
        "disposition": disposition,
        "findings": findings,
    }


def assess_coverglass_delivery(case):
    """Full clause 8.3.2 roll-up over a coverglass delivery.

    The delivery is rolled up on pieces, never on batches. One bad batch
    of twenty pieces and one clean batch of two thousand is not half a
    delivery.
    """
    _require_mapping("case", case)
    delivery_id = _require_label("delivery_id", case.get("delivery_id"))
    batches = case.get("batches")
    if not isinstance(batches, (list, tuple)) or not batches:
        raise ValueError("case must carry a non-empty batches sequence")
    policy = case.get("policy")
    settings = _policy(policy)
    threshold = settings.get("min_release_share")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("min_release_share must be a number, got %r" % (threshold,))
    threshold = float(threshold)

    assessments = [assess_coverglass_batch(b, settings) for b in batches]
    seen = set()
    for assessment in assessments:
        if assessment["batch_id"] in seen:
            raise ValueError(
                "batch %r appears twice in the delivery" % assessment["batch_id"]
            )
        seen.add(assessment["batch_id"])

    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    total = sum(a["piece_count"] for a in assessments)
    released = sum(a["released_pieces"] for a in assessments)
    share = released / total

    withheld = sorted(
        a["batch_id"] for a in assessments if a["disposition"] == BATCH_WITHHELD
    )
    concession = sorted(
        a["batch_id"] for a in assessments if a["disposition"] == BATCH_CONCESSION
    )

    worst = min(BATCH_RANK[a["disposition"]] for a in assessments)
    verdict = next(k for k, v in BATCH_RANK.items() if v == worst)

    weakest = min(
        assessments,
        key=lambda a: (
            BATCH_RANK[a["disposition"]],
            -a["piece_count"],
            a["batch_id"],
        ),
    )

    return {
        "delivery_id": delivery_id,
        "assessments": assessments,
        "total_pieces": total,
        "released_pieces": released,
        "release_share": share,
        "withheld_batches": withheld,
        "concession_batches": concession,
        "verdict": verdict,
        "weakest_batch": weakest["batch_id"],
        "meets_release_threshold": _at_least(share, threshold),
        "findings": findings,
    }
