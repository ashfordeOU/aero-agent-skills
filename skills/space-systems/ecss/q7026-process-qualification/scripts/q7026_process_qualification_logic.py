"""Qualification of a crimping process for one terminal and wire pairing.

Anchor: ECSS-Q-ST-70-26C, the process-control clause of the crimping
practice -- demonstrating that a named tool, die and setting produces
a conforming crimp on a named terminal and conductor, repeatably, and
saying when that demonstration expires (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Qualification is a statement about a combination, not about a shop.
   Terminal part number, conductor construction, tool, die and setting
   together are the qualified item, so changing any one of them asks
   the question again rather than inheriting the answer.
2. Repeatability needs consecutive setup runs. One good batch shows
   the shop managed it once with the tool as it happened to be set
   that morning, which is weaker than the claim being made.
3. The runs have to be consecutive. Picking the good runs out of a
   longer campaign and ignoring the ones between them demonstrates
   selection, not a controlled process.
4. Every sample is graded on crimp height, pull-off force and visual
   together. Height without force misses an undersized conductor;
   force without height misses a die that is slowly closing.
5. A process centred near a window edge is a finding, not a failure.
   Every sample conformed, so the qualification stands, but the
   campaign has recorded that half the tolerance is already spent.
6. Qualification expires. A die regrind, a tool replacement, a setting
   change, a change of conductor construction or simple elapsed time
   each put the combination back in front of the campaign.
7. A value landing exactly on a bound has met it. The comparison
   absorbs representation error from the gauge conversion; the window
   itself is never widened to take a sample in.

Stdlib only, offline, deterministic.
"""

import datetime

TOLERANCE = 1.0e-9

QUALIFIED = "qualified"
CONDITIONAL = "qualified-with-a-finding"
NOT_QUALIFIED = "not-qualified"

# Fraction of the crimp-height window treated as well centred.
CENTRED_FRACTION = 0.5


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


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def parse_date(label, value):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(label, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s %r is not an ISO calendar date" % (label, value))


def validate_specification(spec):
    """Validate the declared qualification specification for a combination."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")

    low = _numeric("crimp_height_min_mm", spec.get("crimp_height_min_mm"), 0.0)
    high = _numeric("crimp_height_max_mm", spec.get("crimp_height_max_mm"), 0.0)
    if low <= 0.0:
        raise ValueError("crimp_height_min_mm must be greater than zero")
    if high <= low:
        raise ValueError("crimp_height_max_mm must exceed the minimum")

    force = _numeric("pull_off_minimum_n", spec.get("pull_off_minimum_n"), 0.0)
    if force <= 0.0:
        raise ValueError("pull_off_minimum_n must be greater than zero")

    triggers = spec.get("requalification_triggers", [])
    if not isinstance(triggers, list):
        raise ValueError("requalification_triggers must be a list")

    return {
        "terminal_part_number": _text(
            "terminal_part_number", spec.get("terminal_part_number")
        ).upper(),
        "conductor_construction": _text(
            "conductor_construction", spec.get("conductor_construction")
        ).lower(),
        "tool_setting": _text("tool_setting", spec.get("tool_setting")).lower(),
        "crimp_height_min_mm": low,
        "crimp_height_max_mm": high,
        "pull_off_minimum_n": force,
        "samples_per_run": _count(
            "samples_per_run", spec.get("samples_per_run"), 1
        ),
        "consecutive_runs_required": _count(
            "consecutive_runs_required", spec.get("consecutive_runs_required"), 1
        ),
        "validity_days": _count("validity_days", spec.get("validity_days"), 1),
        "requalification_triggers": sorted(
            {_text("requalification_trigger", t).lower() for t in triggers}
        ),
    }


def validate_sample(sample):
    """Validate one campaign sample."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    return {
        "run_index": _count("run_index", sample.get("run_index"), 1),
        "crimp_height_mm": _numeric(
            "crimp_height_mm", sample.get("crimp_height_mm"), 0.0
        ),
        "pull_off_force_n": _numeric(
            "pull_off_force_n", sample.get("pull_off_force_n"), 0.0
        ),
        "visual_pass": _flag("visual_pass", sample.get("visual_pass")),
    }


def grade_sample(sample, spec):
    """Grade one sample on height, force and visual together."""
    checked = validate_sample(sample)
    window = validate_specification(spec)
    height = checked["crimp_height_mm"]
    height_pass = (
        height >= window["crimp_height_min_mm"] - TOLERANCE
        and height <= window["crimp_height_max_mm"] + TOLERANCE
    )
    force_pass = (
        checked["pull_off_force_n"] >= window["pull_off_minimum_n"] - TOLERANCE
    )
    reasons = []
    if not height_pass:
        reasons.append("crimp-height-outside-the-window")
    if not force_pass:
        reasons.append("pull-off-force-below-the-minimum")
    if not checked["visual_pass"]:
        reasons.append("visual-inspection-failed")
    return {
        "run_index": checked["run_index"],
        "height_pass": height_pass,
        "force_pass": force_pass,
        "visual_pass": checked["visual_pass"],
        "reasons": reasons,
        "pass": not reasons,
    }


def group_samples_by_run(samples):
    """Group campaign samples by the setup run they came from."""
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list")
    runs = {}
    for sample in samples:
        checked = validate_sample(sample)
        runs.setdefault(checked["run_index"], []).append(sample)
    return runs


def grade_run(run_samples, spec):
    """Grade one setup run: enough samples, and all of them conforming."""
    window = validate_specification(spec)
    if not isinstance(run_samples, list) or not run_samples:
        raise ValueError("run_samples must be a non-empty list")
    graded = [grade_sample(s, spec) for s in run_samples]
    enough = len(graded) >= window["samples_per_run"]
    failures = [g for g in graded if not g["pass"]]
    reasons = []
    if not enough:
        reasons.append("fewer-samples-than-the-declared-run-size")
    if failures:
        reasons.append("non-conforming-sample-in-the-run")
    return {
        "samples": graded,
        "sample_count": len(graded),
        "failures": len(failures),
        "reasons": reasons,
        "conforming": not reasons,
    }


def longest_consecutive_conforming(run_results):
    """Longest streak of consecutive conforming run indices."""
    if not isinstance(run_results, dict) or not run_results:
        raise ValueError("run_results must be a non-empty mapping")
    best = 0
    streak = 0
    previous = None
    for index in sorted(run_results):
        conforming = run_results[index]["conforming"]
        if conforming and previous is not None and index == previous + 1:
            streak += 1
        elif conforming:
            streak = 1
        else:
            streak = 0
        previous = index
        if streak > best:
            best = streak
    return best


def process_centring(samples, spec):
    """Where the campaign sat inside the crimp-height window."""
    window = validate_specification(spec)
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list")
    heights = [validate_sample(s)["crimp_height_mm"] for s in samples]
    mean = sum(heights) / len(heights)
    low = window["crimp_height_min_mm"]
    high = window["crimp_height_max_mm"]
    span = high - low
    centre = (low + high) / 2.0
    half_band = span * CENTRED_FRACTION / 2.0
    return {
        "mean_height_mm": mean,
        "window_centre_mm": centre,
        "centred": abs(mean - centre) <= half_band + TOLERANCE,
    }


def assess_qualification(spec, samples):
    """Grade a qualification campaign for one terminal and wire pairing."""
    window = validate_specification(spec)
    runs = group_samples_by_run(samples)
    run_results = {i: grade_run(runs[i], spec) for i in runs}
    streak = longest_consecutive_conforming(run_results)
    centring = process_centring(samples, spec)

    reasons = []
    if streak < window["consecutive_runs_required"]:
        reasons.append("too-few-consecutive-conforming-runs")
    for index in sorted(run_results):
        for reason in run_results[index]["reasons"]:
            reasons.append("run-%d-%s" % (index, reason))

    findings = []
    if not centring["centred"]:
        findings.append("process-centred-near-a-crimp-height-window-edge")

    if reasons:
        verdict = NOT_QUALIFIED
    elif findings:
        verdict = CONDITIONAL
    else:
        verdict = QUALIFIED

    return {
        "combination": "%s/%s/%s"
        % (
            window["terminal_part_number"],
            window["conductor_construction"],
            window["tool_setting"],
        ),
        "verdict": verdict,
        "reasons": reasons,
        "findings": findings,
        "runs_submitted": len(run_results),
        "consecutive_conforming_runs": streak,
        "centring": centring,
        "qualified": verdict in (QUALIFIED, CONDITIONAL),
    }


def requalification_due(spec, qualified_on, as_of, changes=None):
    """Whether a standing qualification has lapsed or been invalidated."""
    window = validate_specification(spec)
    start = parse_date("qualified_on", qualified_on)
    today = parse_date("as_of", as_of)
    elapsed = (today - start).days
    if elapsed < 0:
        raise ValueError("as_of precedes the qualification date")
    if changes is None:
        changes = []
    if not isinstance(changes, list):
        raise ValueError("changes must be a list")
    seen = [_text("change", c).lower() for c in changes]

    reasons = []
    if elapsed > window["validity_days"]:
        reasons.append("validity-period-elapsed")
    for change in sorted(set(seen)):
        if change in window["requalification_triggers"]:
            reasons.append("declared-trigger-%s" % change)
    return {
        "elapsed_days": elapsed,
        "reasons": reasons,
        "due": bool(reasons),
    }
