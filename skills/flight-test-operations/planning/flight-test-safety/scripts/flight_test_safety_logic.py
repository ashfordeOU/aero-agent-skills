#!/usr/bin/env python3
"""Flight test safety logic (paraphrase, common flight-test practice).

Common-knowledge summary (standards-map.yaml, far-25/cs-25 reference-only
context): a flight test program manages safety through a risk assessment
on a severity by likelihood matrix, flight envelope limits that bound
every test point, emergency procedures for the foreseeable conditions, a
safety pilot with assigned duties, go/no-go criteria that release or
block each flight, and mitigations for the identified risks.
"""

SEVERITY_MIN = 1
SEVERITY_MAX = 5
LIKELIHOOD_MIN = 1
LIKELIHOOD_MAX = 5
HIGH_RISK_INDEX = 15  # risk index >= 15 is high risk (5x5 matrix, upper band)
MEDIUM_RISK_INDEX = 6  # risk index >= 6 is medium risk


def _blank(text):
    return not isinstance(text, str) or not text.strip()


def assess_risks(hazards):
    """Score hazards on the severity by likelihood risk matrix.

    Each hazard is a dict with:
      - "id": str, unique hazard identifier
      - "severity": int in 1..5, consequence of the hazard
      - "likelihood": int in 1..5, probability of the hazard

    The risk index is severity times likelihood (1..25). A hazard is
    "high" when the index is >= 15, "medium" when >= 6, else "low".

    Returns a dict with:
      - "hazards": the scored hazards as {id, severity, likelihood,
        index, level}
      - "high_risk": sorted ids of the high-risk hazards
      - "verdict": "all-low-or-medium" or "high-risk-present"

    Raises ValueError on an empty list, a non-dict hazard, a missing or
    empty id, a duplicate id, or a severity or likelihood that is not an
    int in 1..5 (bools rejected).
    """
    if not isinstance(hazards, list) or len(hazards) == 0:
        raise ValueError("hazards must be a non-empty list, got %r" % (hazards,))
    seen = set()
    scored = []
    for h in hazards:
        if not isinstance(h, dict):
            raise ValueError("each hazard must be a dict, got %r" % (h,))
        hid = h.get("id")
        if _blank(hid):
            raise ValueError("hazard id must be a non-empty string, got %r" % (hid,))
        if hid in seen:
            raise ValueError("duplicate hazard id %r" % (hid,))
        seen.add(hid)
        for key, lo, hi in (
            ("severity", SEVERITY_MIN, SEVERITY_MAX),
            ("likelihood", LIKELIHOOD_MIN, LIKELIHOOD_MAX),
        ):
            val = h.get(key)
            if isinstance(val, bool) or not isinstance(val, int) or not (
                lo <= val <= hi
            ):
                raise ValueError(
                    "hazard %r %s must be an int in %d..%d, got %r"
                    % (hid, key, lo, hi, val)
                )
        index = h["severity"] * h["likelihood"]
        if index >= HIGH_RISK_INDEX:
            level = "high"
        elif index >= MEDIUM_RISK_INDEX:
            level = "medium"
        else:
            level = "low"
        scored.append(
            {
                "id": hid,
                "severity": h["severity"],
                "likelihood": h["likelihood"],
                "index": index,
                "level": level,
            }
        )
    high = sorted(h["id"] for h in scored if h["level"] == "high")
    verdict = "high-risk-present" if high else "all-low-or-medium"
    return {"hazards": scored, "high_risk": high, "verdict": verdict}


def envelope_violations(limits, points):
    """Check that every test point stays inside the flight envelope limits.

    limits: dict with "v_min", "v_max", "n_min", "n_max" (numeric, with
    v_min <= v_max and n_min <= n_max). Each point is a dict with:
      - "id": str, unique point identifier
      - "speed": numeric, airspeed of the point
      - "load_factor": numeric, load factor of the point

    A point on the boundary counts as inside; only a strict crossing is
    a violation. Returns a dict with:
      - "violations": sorted list of {point, limit, value, bound} for
        every point outside a limit
      - "verdict": "within-envelope" or "limit-violations"

    Raises ValueError on non-numeric or bool limit values, an inverted
    limit pair, an empty points list, a non-dict point, a missing or
    empty id, a duplicate id, or a non-numeric or bool speed or
    load_factor.
    """
    if not isinstance(limits, dict):
        raise ValueError("limits must be a dict, got %r" % (limits,))
    bounds = {}
    for key in ("v_min", "v_max", "n_min", "n_max"):
        val = limits.get(key)
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("limits %s must be numeric, got %r" % (key, val))
        bounds[key] = val
    if bounds["v_min"] > bounds["v_max"]:
        raise ValueError("v_min must be <= v_max, got %r" % (bounds,))
    if bounds["n_min"] > bounds["n_max"]:
        raise ValueError("n_min must be <= n_max, got %r" % (bounds,))
    if not isinstance(points, list) or len(points) == 0:
        raise ValueError("points must be a non-empty list, got %r" % (points,))
    seen = set()
    for pt in points:
        if not isinstance(pt, dict):
            raise ValueError("each test point must be a dict, got %r" % (pt,))
        pid = pt.get("id")
        if _blank(pid):
            raise ValueError("test point id must be a non-empty string, got %r" % (pid,))
        if pid in seen:
            raise ValueError("duplicate test point id %r" % (pid,))
        seen.add(pid)
        for key in ("speed", "load_factor"):
            val = pt.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    "test point %r %s must be numeric, got %r" % (pid, key, val)
                )
    violations = []
    for pt in points:
        for limit, broken in (
            ("v_min", pt["speed"] < bounds["v_min"]),
            ("v_max", pt["speed"] > bounds["v_max"]),
            ("n_min", pt["load_factor"] < bounds["n_min"]),
            ("n_max", pt["load_factor"] > bounds["n_max"]),
        ):
            if broken:
                value = pt["speed"] if limit.startswith("v") else pt["load_factor"]
                violations.append(
                    {"point": pt["id"], "limit": limit, "value": value, "bound": bounds[limit]}
                )
    violations.sort(key=lambda v: (v["point"], v["limit"]))
    verdict = "within-envelope" if not violations else "limit-violations"
    return {"violations": violations, "verdict": verdict}


def procedure_coverage(required, library):
    """Check that every required emergency condition has a procedure.

    required: list of condition names (strings). library: dict mapping a
    condition name to a non-empty list of non-empty step strings.
    Comparison is exact after stripping surrounding whitespace.

    Returns a dict with:
      - "missing": sorted condition names with no procedure in the
        library
      - "verdict": "complete" or "incomplete"

    Raises ValueError on an empty required list, a required value that
    is not a list, a blank required condition, an empty or non-dict
    library, a blank library key, or a steps value that is not a
    non-empty list of non-empty strings.
    """
    if not isinstance(required, list) or len(required) == 0:
        raise ValueError("required must be a non-empty list, got %r" % (required,))
    for name in required:
        if _blank(name):
            raise ValueError(
                "required condition names must be non-empty strings, got %r" % (name,)
            )
    if not isinstance(library, dict) or len(library) == 0:
        raise ValueError("library must be a non-empty dict, got %r" % (library,))
    cleaned = {}
    for name, steps in library.items():
        if _blank(name):
            raise ValueError("condition names must be non-empty strings, got %r" % (name,))
        if not isinstance(steps, list) or len(steps) == 0:
            raise ValueError(
                "condition %r steps must be a non-empty list, got %r" % (name, steps)
            )
        if not all(isinstance(s, str) and s.strip() for s in steps):
            raise ValueError(
                "condition %r steps must be non-empty strings, got %r" % (name, steps)
            )
        cleaned[name.strip()] = [s.strip() for s in steps]
    req = [n.strip() for n in required]
    missing = sorted(n for n in req if n not in cleaned)
    verdict = "complete" if not missing else "incomplete"
    return {"missing": missing, "verdict": verdict}


def safety_pilot_assignment(required_duties, assigned):
    """Check that every required safety pilot duty is assigned.

    required_duties and assigned are lists of duty names (strings).
    Comparison is exact after stripping surrounding whitespace.

    Returns a dict with:
      - "missing": sorted duty names required but not assigned
      - "verdict": "covered" or "missing-duties"

    Raises ValueError on an empty required_duties list, an assigned
    value that is not a list, or a non-string (or blank) entry in
    either list.
    """
    if not isinstance(required_duties, list) or len(required_duties) == 0:
        raise ValueError(
            "required_duties must be a non-empty list, got %r" % (required_duties,)
        )
    if not isinstance(assigned, list):
        raise ValueError("assigned must be a list, got %r" % (assigned,))
    for name in required_duties + assigned:
        if _blank(name):
            raise ValueError("duty names must be non-empty strings, got %r" % (name,))
    req = [n.strip() for n in required_duties]
    asg = [n.strip() for n in assigned]
    missing = sorted(set(req) - set(asg))
    verdict = "covered" if not missing else "missing-duties"
    return {"missing": missing, "verdict": verdict}


def go_no_go(criteria):
    """Go/no-go verdict from the named criteria checks.

    criteria: list of dicts with:
      - "name": str, criterion name
      - "passed": bool, whether the criterion is satisfied

    The flight is released only when every criterion passes. Returns a
    dict with:
      - "go": True when all criteria pass, else False
      - "failed": names of the criteria that failed, in input order
      - "verdict": "GO" or "NO-GO"

    Raises ValueError on an empty criteria list, a non-dict entry, a
    missing or blank name, a duplicate name, or a passed value that is
    not a bool.
    """
    if not isinstance(criteria, list) or len(criteria) == 0:
        raise ValueError("criteria must be a non-empty list, got %r" % (criteria,))
    seen = set()
    for c in criteria:
        if not isinstance(c, dict):
            raise ValueError("each criterion must be a dict, got %r" % (c,))
        name = c.get("name")
        if _blank(name):
            raise ValueError("criterion name must be a non-empty string, got %r" % (name,))
        if name in seen:
            raise ValueError("duplicate criterion name %r" % (name,))
        seen.add(name)
        passed = c.get("passed")
        if not isinstance(passed, bool):
            raise ValueError(
                "criterion %r passed must be a bool, got %r" % (name, passed)
            )
    failed = [c["name"] for c in criteria if not c["passed"]]
    go = len(failed) == 0
    return {"go": go, "failed": failed, "verdict": "GO" if go else "NO-GO"}


def mitigation_gaps(risks, mitigations):
    """Check that every risk has at least one assigned mitigation.

    risks: list of risk ids (strings). mitigations: dict mapping a risk
    id to a list of mitigation descriptions (non-empty strings).

    Returns a dict with:
      - "unmitigated": sorted risk ids with no mitigation assigned
      - "verdict": "all-mitigated" or "unmitigated-risks"

    Raises ValueError on an empty risks list, a risks value that is not
    a list, a blank risk id, a non-dict mitigations value, a mitigation
    entry for a risk id not in risks, or a mitigations value that is
    not a non-empty list of non-empty strings.
    """
    if not isinstance(risks, list) or len(risks) == 0:
        raise ValueError("risks must be a non-empty list, got %r" % (risks,))
    for rid in risks:
        if _blank(rid):
            raise ValueError("risk ids must be non-empty strings, got %r" % (rid,))
    if not isinstance(mitigations, dict):
        raise ValueError("mitigations must be a dict, got %r" % (mitigations,))
    risk_set = set(risks)
    cleaned = {}
    for rid, items in mitigations.items():
        if _blank(rid):
            raise ValueError("mitigation risk ids must be non-empty strings, got %r" % (rid,))
        if rid not in risk_set:
            raise ValueError(
                "mitigation for unknown risk id %r (not in risks)" % (rid,)
            )
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError(
                "risk %r mitigations must be a non-empty list, got %r" % (rid, items)
            )
        if not all(isinstance(m, str) and m.strip() for m in items):
            raise ValueError(
                "risk %r mitigations must be non-empty strings, got %r" % (rid, items)
            )
        cleaned[rid] = [m.strip() for m in items]
    unmitigated = sorted(r for r in risks if r not in cleaned)
    verdict = "all-mitigated" if not unmitigated else "unmitigated-risks"
    return {"unmitigated": unmitigated, "verdict": verdict}
