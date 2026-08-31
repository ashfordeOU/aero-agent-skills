#!/usr/bin/env python3
"""Flight test program planning logic (paraphrase, common flight-test
methodology).

Common-knowledge summary (standards-map.yaml, far-25/cs-25 reference-only
context): a flight test program follows the build-up approach, in which
risk is added incrementally and the envelope is expanded step by step,
so a test point may only be flown after its prerequisites. The planning
artifacts are the risk-ordered build-up sequence, the instrumentation
completeness check, the test matrix coverage check, and the go/no-go
gate that releases or blocks each flight.
"""


def build_up_order(test_points):
    """Order test points by ascending risk and flag missing prerequisites.

    Each point is a dict with:
      - "id": str, unique point identifier
      - "risk": int or float >= 0, risk level (higher = riskier, flown later)
      - "prerequisites": list of point ids that must be flown before
        this point (may be empty)

    Returns a dict with:
      - "ordered": points sorted by risk ascending (ties keep input
        order, so the result is deterministic)
      - "missing_prerequisites": list of {"point", "missing"} entries
        for prerequisites that are not part of the point set
      - "verdict": "ok" or "missing-prerequisites"

    Raises ValueError on an empty list, a non-dict point, a missing or
    empty id, a duplicate id, a non-numeric, boolean, or negative risk,
    or a prerequisites value that is not a list of strings.
    """
    if not isinstance(test_points, list) or len(test_points) == 0:
        raise ValueError("test_points must be a non-empty list, got %r" % (test_points,))
    seen = set()
    for pt in test_points:
        if not isinstance(pt, dict):
            raise ValueError("each test point must be a dict, got %r" % (pt,))
        pid = pt.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError("test point id must be a non-empty string, got %r" % (pid,))
        if pid in seen:
            raise ValueError("duplicate test point id %r" % (pid,))
        seen.add(pid)
        risk = pt.get("risk")
        if isinstance(risk, bool) or not isinstance(risk, (int, float)):
            raise ValueError(
                "test point %r risk must be numeric, got %r" % (pid, risk)
            )
        if risk < 0:
            raise ValueError("test point %r risk must be >= 0, got %r" % (pid, risk))
        prereqs = pt.get("prerequisites")
        if prereqs is None:
            raise ValueError("test point %r has no prerequisites key" % (pid,))
        if not isinstance(prereqs, list) or not all(
            isinstance(p, str) and p for p in prereqs
        ):
            raise ValueError(
                "test point %r prerequisites must be a list of strings, got %r"
                % (pid, prereqs)
            )
    known = set(pt["id"] for pt in test_points)
    ordered = [
        pt
        for _, pt in sorted(
            enumerate(test_points), key=lambda t: (t[1]["risk"], t[0])
        )
    ]
    missing = []
    for pt in ordered:
        gone = sorted(p for p in pt["prerequisites"] if p not in known)
        if gone:
            missing.append({"point": pt["id"], "missing": gone})
    verdict = "ok" if not missing else "missing-prerequisites"
    return {"ordered": ordered, "missing_prerequisites": missing, "verdict": verdict}


def instrumentation_complete(required, provided):
    """Check that every required instrument is in the provided set.

    required and provided are lists of instrument names (strings).
    Comparison is exact after stripping surrounding whitespace.
    Returns a dict with:
      - "missing": sorted list of required names not provided
      - "verdict": "complete" or "incomplete"

    Raises ValueError on an empty required list, a provided value that
    is not a list, or a non-string (or blank) entry in either list.
    """
    if not isinstance(required, list) or len(required) == 0:
        raise ValueError("required must be a non-empty list, got %r" % (required,))
    if not isinstance(provided, list):
        raise ValueError("provided must be a list, got %r" % (provided,))
    for name in required + provided:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "instrument names must be non-empty strings, got %r" % (name,)
            )
    req = [n.strip() for n in required]
    prov = [n.strip() for n in provided]
    missing = sorted(set(req) - set(prov))
    verdict = "complete" if not missing else "incomplete"
    return {"missing": missing, "verdict": verdict}


def test_matrix_complete(points, objectives):
    """Check that every test objective has at least one covering point.

    points: list of dicts with:
      - "id": str, unique test point identifier
      - "covers": list of objective ids the point exercises
    objectives: list of objective ids (strings).
    Returns a dict with:
      - "uncovered": sorted list of objectives with no covering point
      - "coverage": mapping of each objective to its covering point ids
      - "verdict": "complete" or "incomplete"

    Raises ValueError on empty inputs, a non-dict point, a missing or
    empty id, a duplicate point id, a covers value that is not a list
    of strings, or a non-string objective id.
    """
    if not isinstance(points, list) or len(points) == 0:
        raise ValueError("points must be a non-empty list, got %r" % (points,))
    if not isinstance(objectives, list) or len(objectives) == 0:
        raise ValueError("objectives must be a non-empty list, got %r" % (objectives,))
    for obj in objectives:
        if not isinstance(obj, str) or not obj:
            raise ValueError("objective ids must be non-empty strings, got %r" % (obj,))
    seen = set()
    for pt in points:
        if not isinstance(pt, dict):
            raise ValueError("each test point must be a dict, got %r" % (pt,))
        pid = pt.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError("test point id must be a non-empty string, got %r" % (pid,))
        if pid in seen:
            raise ValueError("duplicate test point id %r" % (pid,))
        seen.add(pid)
        covers = pt.get("covers")
        if not isinstance(covers, list) or not all(
            isinstance(c, str) and c for c in covers
        ):
            raise ValueError(
                "test point %r covers must be a list of strings, got %r"
                % (pid, covers)
            )
    coverage = {}
    for obj in objectives:
        coverage[obj] = [pt["id"] for pt in points if obj in pt["covers"]]
    uncovered = sorted(o for o in objectives if not coverage[o])
    verdict = "complete" if not uncovered else "incomplete"
    return {"uncovered": uncovered, "coverage": coverage, "verdict": verdict}


def go_no_gate(weather_ok, aircraft_ready, instrumentation_ok, safety_review_ok):
    """Go/no-go gate verdict before a flight test point.

    All four inputs must be bool. The flight is released only when
    every check is True. Returns a dict with:
      - "go": True when all checks pass, else False
      - "blockers": names of the checks that are False
      - "verdict": "GO" or "NO-GO"

    Raises ValueError if any input is not a bool.
    """
    checks = {
        "weather_ok": weather_ok,
        "aircraft_ready": aircraft_ready,
        "instrumentation_ok": instrumentation_ok,
        "safety_review_ok": safety_review_ok,
    }
    for name, val in checks.items():
        if not isinstance(val, bool):
            raise ValueError("%s must be a bool, got %r" % (name, val))
    blockers = [name for name, val in checks.items() if not val]
    go = len(blockers) == 0
    return {"go": go, "blockers": blockers, "verdict": "GO" if go else "NO-GO"}
