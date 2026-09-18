"""Destructive pull-off verification of a lot of wire wraps.

Anchor: ECSS-Q-ST-70-30C, wrapping quality clauses (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Size the sample from the lot. The pull-off test destroys the wrap it
   grades, so it is a sampling test: the sample grows with the lot, but
   far more slowly, because what is being demonstrated is the setting
   of a process, not the strength of one connection.
2. Hold a first-article wrap for every distinct setup. A setup is the
   combination of operator, wrapping tool and conductor gauge; a change
   to any of the three is a different process and owes its own first
   article before production continues.
3. Read the minimum unwrap force the conductor gauge owes. A coarser
   conductor presses harder on the post corners and carries more metal,
   so the force it must survive is larger.
4. Grade each sample against that minimum and state the margin, so a
   lot that passed by a hair is distinguishable from one that passed
   comfortably.
5. Refuse a sample taken from flight hardware. A destroyed wrap on a
   deliverable assembly is damage, not evidence; the sample comes from
   a process coupon made alongside the work.
6. Return the lot disposition: acceptance, full re-verification, or
   rewrap of the lot.

Every threshold is a declared project policy value the caller may
override, because the sampling plan a programme adopts belongs to its
own process specification.

Stdlib only, offline, deterministic.
"""

# Minimum unwrap force by conductor gauge, in newtons. Declared
# acceptance schedule, not a reproduction of the standard's table.
MIN_PULL_OFF_FORCE_N = {
    20: 35.6,
    22: 26.7,
    24: 17.8,
    26: 13.3,
    28: 10.0,
    30: 6.7,
}

# Sampling plan: (largest lot size covered, samples owed). The final
# entry covers every larger lot.
SAMPLING_PLAN = (
    (25, 3),
    (90, 5),
    (500, 8),
    (None, 13),
)

ORIGIN_COUPON = "process-coupon"
ORIGIN_FLIGHT = "flight-hardware"
VALID_ORIGINS = (ORIGIN_COUPON, ORIGIN_FLIGHT)

ACCEPT = "lot-accepted"
REVERIFY = "lot-held-for-full-reverification"
REWRAP = "lot-rejected-rewrap-required"

# Forces are measured floats, so a sample landing exactly on its
# minimum can sit a few units in the last place below it. A micronewton
# is far below any pull tester's resolution and absorbs that
# representation error without relaxing the minimum.
FORCE_TOLERANCE_N = 1.0e-9


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


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def required_pull_off_force_n(gauge):
    """Minimum unwrap force one conductor gauge owes, in newtons."""
    if not isinstance(gauge, int) or isinstance(gauge, bool):
        raise ValueError("gauge must be an integer, got %r" % (gauge,))
    if gauge not in MIN_PULL_OFF_FORCE_N:
        raise ValueError(
            "gauge %r is outside the pull-off schedule (have %s)"
            % (gauge, ", ".join(str(g) for g in sorted(MIN_PULL_OFF_FORCE_N)))
        )
    return MIN_PULL_OFF_FORCE_N[gauge]


def sample_size(lot_size):
    """Number of wraps the sampling plan owes for one lot size."""
    size = _whole("lot_size", lot_size, 1)
    for ceiling, samples in SAMPLING_PLAN:
        if ceiling is None or size <= ceiling:
            return min(samples, size)
    raise ValueError("sampling plan has no open-ended entry")


def setup_key(sample):
    """Identity of the process setup one sample came from."""
    norm = validate_sample(sample)
    return (norm["operator_id"], norm["tool_id"], norm["gauge"])


def force_margin(measured_force_n, gauge):
    """Measured force divided by the minimum the gauge owes."""
    measured = _numeric("measured_force_n", measured_force_n, 0.0)
    return measured / required_pull_off_force_n(gauge)


def validate_sample(sample):
    """Validate one pull-off sample and return a normalized copy."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    sample_id = _text("sample id", sample.get("id"))
    gauge = sample.get("gauge")
    required_pull_off_force_n(gauge)
    origin = sample.get("origin", ORIGIN_COUPON)
    if origin not in VALID_ORIGINS:
        raise ValueError(
            "sample %s origin %r is unknown (expected one of %s)"
            % (sample_id, origin, ", ".join(VALID_ORIGINS))
        )
    first_article = sample.get("first_article", False)
    if not isinstance(first_article, bool):
        raise ValueError("sample %s first_article must be a boolean" % sample_id)
    return {
        "id": sample_id,
        "gauge": gauge,
        "operator_id": _text("sample %s operator_id" % sample_id, sample.get("operator_id")),
        "tool_id": _text("sample %s tool_id" % sample_id, sample.get("tool_id")),
        "origin": origin,
        "first_article": first_article,
        "measured_force_n": _numeric(
            "sample %s measured_force_n" % sample_id, sample.get("measured_force_n"), 0.0
        ),
    }


def assess_sample(sample):
    """Grade one pull-off sample against the gauge minimum."""
    norm = validate_sample(sample)
    required = required_pull_off_force_n(norm["gauge"])
    findings = []
    if norm["measured_force_n"] + FORCE_TOLERANCE_N < required:
        findings.append("unwrap-force-below-gauge-minimum")
    if norm["origin"] == ORIGIN_FLIGHT:
        findings.append("destructive-sample-taken-from-flight-hardware")
    return {
        "id": norm["id"],
        "gauge": norm["gauge"],
        "setup": (norm["operator_id"], norm["tool_id"], norm["gauge"]),
        "required_force_n": required,
        "measured_force_n": norm["measured_force_n"],
        "margin": force_margin(norm["measured_force_n"], norm["gauge"]),
        "first_article": norm["first_article"],
        "findings": findings,
        "passed": not findings,
    }


def missing_first_articles(samples):
    """Setups present in the samples with no first-article wrap among them."""
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list")
    covered = set()
    seen = set()
    for sample in samples:
        norm = validate_sample(sample)
        key = (norm["operator_id"], norm["tool_id"], norm["gauge"])
        seen.add(key)
        if norm["first_article"]:
            covered.add(key)
    return sorted(seen - covered)


def assess_pull_off_verification(lot_size, samples):
    """Run the pull-off verification over one lot and its samples."""
    owed = sample_size(lot_size)
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list")
    results = []
    seen = set()
    for sample in samples:
        result = assess_sample(sample)
        if result["id"] in seen:
            raise ValueError("duplicate sample id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    findings = []
    if len(results) < owed:
        findings.append("sample-count-below-plan")
    uncovered = missing_first_articles(samples)
    if uncovered:
        findings.append("setup-without-a-first-article-wrap")
    failed = [r["id"] for r in results if not r["passed"]]
    weak = [r["id"] for r in results if "unwrap-force-below-gauge-minimum" in r["findings"]]
    if weak:
        disposition = REWRAP
    elif failed or findings:
        disposition = REVERIFY
    else:
        disposition = ACCEPT
    margins = [r["margin"] for r in results]
    return {
        "lot_size": lot_size,
        "samples_owed": owed,
        "samples_taken": len(results),
        "results": results,
        "failed_ids": failed,
        "below_minimum_ids": weak,
        "setups_without_first_article": uncovered,
        "lot_findings": findings,
        "worst_margin": min(margins),
        "disposition": disposition,
        "accepted": disposition == ACCEPT,
    }
