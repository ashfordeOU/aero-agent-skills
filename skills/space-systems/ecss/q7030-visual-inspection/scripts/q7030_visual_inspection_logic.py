"""Visual acceptance of finished solid-wire wraps.

Anchor: ECSS-Q-ST-70-30C, wrapping quality clauses (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Take the observation as recorded at the bench: how many bare and
   insulated turns are actually on the post, how many turns overlap a
   turn below them, how many turns stand off the post instead of
   seating on it, the width of each gap between adjacent turns, and how
   far the cut end of the wire overhangs the last turn.
2. Grade each observation against a limit that scales with the
   conductor, because a gap that is invisible on a coarse wire is a
   full conductor width on a fine one.
3. Group each finding by severity. A major finding is one that removes
   contact area or creates a short-circuit risk -- an overlapping turn,
   a lifted turn, too few bare turns, a nicked conductor. A minor
   finding is one that degrades the wrap without removing joint area,
   such as an over-long end tail.
4. Return a verdict per wrap and the rework list the lot owes, so the
   set is graded rather than a running impression of it.

Every threshold is a declared project policy value the caller may
override, because the acceptance limits a programme adopts belong to
its own process specification.

Stdlib only, offline, deterministic.
"""

# Conductor diameter per gauge, in millimetres. The visual limits are
# fractions of it, so the table is the unit of every length here.
CONDUCTOR_DIAMETER_MM = {
    20: 0.813,
    22: 0.643,
    24: 0.511,
    26: 0.404,
    28: 0.320,
    30: 0.254,
}

MIN_BARE_TURNS = {20: 4, 22: 5, 24: 5, 26: 6, 28: 7, 30: 7}

# Gap between two adjacent turns, and the sum of the gaps over a whole
# wrap, as fractions of the conductor diameter.
MAX_SINGLE_GAP_FRACTION = 0.5
MAX_TOTAL_GAP_FRACTION = 1.0

# Overhang of the cut end beyond the last turn, as a fraction of the
# conductor diameter.
MAX_END_TAIL_FRACTION = 1.0

# Minor findings tolerated on one wrap before it goes to rework.
MAX_MINOR_FINDINGS = 1

MAJOR = "major"
MINOR = "minor"

# Severity of each finding code. Major findings remove contact area or
# create a short-circuit risk; minor findings degrade the wrap without
# taking joint area away.
FINDING_SEVERITY = {
    "overlapping-turn": MAJOR,
    "lifted-turn-not-seated": MAJOR,
    "bare-turn-count-below-minimum": MAJOR,
    "single-turn-gap-above-limit": MAJOR,
    "cumulative-turn-gap-above-limit": MAJOR,
    "nicked-or-scraped-conductor": MAJOR,
    "post-damaged-by-wrapping": MAJOR,
    "end-tail-above-limit": MINOR,
    "insulation-turn-missing-on-modified-wrap": MINOR,
}

ACCEPTED = "wrap-accepted"
REWORK = "wrap-to-rework"

# Gap widths and tail lengths are measured floats, so a wrap sitting
# exactly on a limit can land a few units in the last place above it. A
# nanometre is far below any bench measurement and absorbs that
# representation error without relaxing the limit.
LENGTH_TOLERANCE_MM = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _whole(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %r" % (label, minimum, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def conductor_diameter_mm(gauge):
    """Conductor diameter for one wire gauge, in millimetres."""
    if not isinstance(gauge, int) or isinstance(gauge, bool):
        raise ValueError("gauge must be an integer, got %r" % (gauge,))
    if gauge not in CONDUCTOR_DIAMETER_MM:
        raise ValueError(
            "gauge %r is outside the inspection schedule (have %s)"
            % (gauge, ", ".join(str(g) for g in sorted(CONDUCTOR_DIAMETER_MM)))
        )
    return CONDUCTOR_DIAMETER_MM[gauge]


def minimum_bare_turns(gauge):
    """Minimum bare turns a wrap of this gauge must show."""
    conductor_diameter_mm(gauge)
    return MIN_BARE_TURNS[gauge]


def single_gap_limit_mm(gauge):
    """Largest gap allowed between two adjacent turns, in millimetres."""
    return conductor_diameter_mm(gauge) * MAX_SINGLE_GAP_FRACTION


def total_gap_limit_mm(gauge):
    """Largest cumulative gap allowed over one wrap, in millimetres."""
    return conductor_diameter_mm(gauge) * MAX_TOTAL_GAP_FRACTION


def end_tail_limit_mm(gauge):
    """Largest overhang allowed beyond the last turn, in millimetres."""
    return conductor_diameter_mm(gauge) * MAX_END_TAIL_FRACTION


def severity_of(code):
    """Severity group of one finding code."""
    if code not in FINDING_SEVERITY:
        raise ValueError("unknown finding code %r" % (code,))
    return FINDING_SEVERITY[code]


def validate_observation(observation):
    """Validate one bench observation and return a normalized copy."""
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping")
    wrap_id = observation.get("id")
    if not isinstance(wrap_id, str) or not wrap_id.strip():
        raise ValueError("observation needs a non-empty string id")
    gauge = observation.get("gauge")
    conductor_diameter_mm(gauge)
    wrap_type = observation.get("wrap_type", "modified")
    if wrap_type not in ("modified", "conventional"):
        raise ValueError(
            "observation %s wrap_type %r is unknown" % (wrap_id, wrap_type)
        )
    gaps = observation.get("turn_gaps_mm", [])
    if not isinstance(gaps, (list, tuple)):
        raise ValueError("observation %s turn_gaps_mm must be a sequence" % wrap_id)
    return {
        "id": wrap_id,
        "gauge": gauge,
        "wrap_type": wrap_type,
        "bare_turns": _whole(
            "observation %s bare_turns" % wrap_id, observation.get("bare_turns", 0)
        ),
        "insulated_turns": _numeric(
            "observation %s insulated_turns" % wrap_id,
            observation.get("insulated_turns", 0.0),
            0.0,
        ),
        "overlapping_turns": _whole(
            "observation %s overlapping_turns" % wrap_id,
            observation.get("overlapping_turns", 0),
        ),
        "lifted_turns": _whole(
            "observation %s lifted_turns" % wrap_id, observation.get("lifted_turns", 0)
        ),
        "turn_gaps_mm": [
            _numeric("observation %s turn gap" % wrap_id, g, 0.0) for g in gaps
        ],
        "end_tail_mm": _numeric(
            "observation %s end_tail_mm" % wrap_id, observation.get("end_tail_mm", 0.0), 0.0
        ),
        "conductor_damaged": _boolean(
            "observation %s conductor_damaged" % wrap_id,
            observation.get("conductor_damaged", False),
        ),
        "post_damaged": _boolean(
            "observation %s post_damaged" % wrap_id,
            observation.get("post_damaged", False),
        ),
    }


def finding_codes(observation):
    """Finding codes raised by one observation, in a stable order."""
    norm = validate_observation(observation)
    codes = []
    if norm["bare_turns"] < minimum_bare_turns(norm["gauge"]):
        codes.append("bare-turn-count-below-minimum")
    if norm["overlapping_turns"] > 0:
        codes.append("overlapping-turn")
    if norm["lifted_turns"] > 0:
        codes.append("lifted-turn-not-seated")
    single_limit = single_gap_limit_mm(norm["gauge"])
    if any(g > single_limit + LENGTH_TOLERANCE_MM for g in norm["turn_gaps_mm"]):
        codes.append("single-turn-gap-above-limit")
    if sum(norm["turn_gaps_mm"]) > total_gap_limit_mm(norm["gauge"]) + LENGTH_TOLERANCE_MM:
        codes.append("cumulative-turn-gap-above-limit")
    if norm["conductor_damaged"]:
        codes.append("nicked-or-scraped-conductor")
    if norm["post_damaged"]:
        codes.append("post-damaged-by-wrapping")
    if norm["end_tail_mm"] > end_tail_limit_mm(norm["gauge"]) + LENGTH_TOLERANCE_MM:
        codes.append("end-tail-above-limit")
    if norm["wrap_type"] == "modified" and norm["insulated_turns"] <= 0.0:
        codes.append("insulation-turn-missing-on-modified-wrap")
    return codes


def group_findings(codes):
    """Group finding codes by severity."""
    if not isinstance(codes, (list, tuple)):
        raise ValueError("codes must be a sequence")
    grouped = {MAJOR: [], MINOR: []}
    for code in codes:
        grouped[severity_of(code)].append(code)
    return grouped


def assess_wrap(observation):
    """Assess one wrap against the visual acceptance rules."""
    norm = validate_observation(observation)
    codes = finding_codes(norm)
    grouped = group_findings(codes)
    accepted = not grouped[MAJOR] and len(grouped[MINOR]) <= MAX_MINOR_FINDINGS
    return {
        "id": norm["id"],
        "gauge": norm["gauge"],
        "required_bare_turns": minimum_bare_turns(norm["gauge"]),
        "findings": codes,
        "major_findings": grouped[MAJOR],
        "minor_findings": grouped[MINOR],
        "status": ACCEPTED if accepted else REWORK,
        "accepted": accepted,
    }


def assess_visual_inspection(observations):
    """Run the visual inspection over a set of wraps."""
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations must be a non-empty list")
    results = []
    seen = set()
    for observation in observations:
        result = assess_wrap(observation)
        if result["id"] in seen:
            raise ValueError("duplicate wrap id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rework = [r["id"] for r in results if not r["accepted"]]
    major_total = sum(len(r["major_findings"]) for r in results)
    minor_total = sum(len(r["minor_findings"]) for r in results)
    return {
        "wraps": results,
        "accepted_ids": [r["id"] for r in results if r["accepted"]],
        "rework_ids": rework,
        "major_finding_count": major_total,
        "minor_finding_count": minor_total,
        "accepted": not rework,
    }
