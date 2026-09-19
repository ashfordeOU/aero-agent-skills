"""Run lengths and transition densities on a space communication link.

Anchor: ECSS-E-ST-50C clause 5.6.11.3 -- tolerance of run lengths and
transition densities. Paraphrased into an implementable procedure; no standard
text is reproduced.

Two normative items, both about the same receiver and both measurable on the
stream itself:

  1. the link tolerates the run lengths the stream contains -- the longest
     stretch of identical symbols must stay inside what the clock recovery can
     coast through without losing bit synchronisation;
  2. the link tolerates the transition densities the stream offers -- there
     must be enough symbol edges to keep that recovery loop fed, and enough of
     them everywhere, not merely on average.

The second obligation is the one an average hides. A stream can carry plenty
of transitions overall and still starve the loop inside one window, so the
density is measured over the whole stream and over the worst sliding window of
the length the receiver's loop actually integrates over.

Counting convention: a stream of n symbols offers n-1 places where a
transition can occur, so a density is transitions over n-1. A one-symbol
stream offers none and has no density at all.
"""

import math

__all__ = [
    "COMPLIANT",
    "RUN_TOO_LONG",
    "DENSITY_TOO_LOW",
    "REL_TOL",
    "validate_stream",
    "validate_positive_int",
    "validate_density",
    "run_lengths",
    "longest_run",
    "runs_over_limit",
    "transition_count",
    "transition_density",
    "worst_window",
    "transitions_needed",
    "transition_shortfall",
    "randomisation_needed",
    "assess_bit_stream",
]

COMPLIANT = "compliant"
RUN_TOO_LONG = "run-too-long"
DENSITY_TOO_LOW = "density-too-low"

# Relative tolerance for every density comparison, so a stream sized to land
# exactly on the limit is accepted on every platform rather than on some.
REL_TOL = 1e-9


def validate_stream(stream, name="stream"):
    """Return the symbol stream as a tuple of zeros and ones.

    Accepts a text of '0' and '1' or a sequence of integers. Anything else is
    an input error rather than something to coerce: a stream that silently
    became all zeros would be reported as the worst run in the design.
    """
    if isinstance(stream, str):
        symbols = []
        for index, character in enumerate(stream):
            if character == "0":
                symbols.append(0)
            elif character == "1":
                symbols.append(1)
            else:
                raise ValueError("%s position %d is %r, not a binary symbol" % (name, index, character))
    elif isinstance(stream, (list, tuple)):
        symbols = []
        for index, value in enumerate(stream):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("%s position %d must be the integer 0 or 1" % (name, index))
            if value not in (0, 1):
                raise ValueError("%s position %d is %r, not a binary symbol" % (name, index, value))
            symbols.append(value)
    else:
        raise ValueError("%s must be a binary text or a sequence of 0 and 1" % name)
    if not symbols:
        raise ValueError("%s must not be empty" % name)
    return tuple(symbols)


def validate_positive_int(value, name="limit"):
    """Return a strictly positive whole number."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % name)
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def validate_density(value, name="min_density"):
    """Return a density in the closed interval zero to one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    density = float(value)
    if math.isnan(density) or math.isinf(density):
        raise ValueError("%s must be finite" % name)
    if density < 0.0 or density > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return density


def run_lengths(stream):
    """Return every run as a dict of symbol, length and start position."""
    symbols = validate_stream(stream)
    runs = []
    start = 0
    for index in range(1, len(symbols) + 1):
        if index == len(symbols) or symbols[index] != symbols[start]:
            runs.append({"symbol": symbols[start], "length": index - start, "start": start})
            start = index
    return runs


def longest_run(stream):
    """Return the longest run, earliest one first when two tie.

    Ties go to the earlier position so the answer is stable and points at the
    first place in the stream a reviewer should look.
    """
    runs = run_lengths(stream)
    best = runs[0]
    for run in runs[1:]:
        if run["length"] > best["length"]:
            best = run
    return best


def runs_over_limit(stream, max_run):
    """Return every run longer than the receiver tolerates."""
    limit = validate_positive_int(max_run, "max_run")
    return [run for run in run_lengths(stream) if run["length"] > limit]


def transition_count(stream):
    """Return the number of places the symbol changes."""
    symbols = validate_stream(stream)
    return sum(1 for index in range(1, len(symbols)) if symbols[index] != symbols[index - 1])


def transition_density(stream):
    """Return transitions over the places a transition could have occurred.

    None means the question is not asked: a single symbol offers no place for
    a transition, and reporting zero there would read as a starved loop.
    """
    symbols = validate_stream(stream)
    places = len(symbols) - 1
    if places <= 0:
        return None
    return transition_count(symbols) / float(places)


def worst_window(stream, window_bits):
    """Return the leanest sliding window of this length in the stream.

    Reports the density, the transition count and where the window starts, so
    the finding points at a position rather than at the stream as a whole.
    Ties go to the earliest window.
    """
    symbols = validate_stream(stream)
    width = validate_positive_int(window_bits, "window_bits")
    if width < 2:
        raise ValueError("window_bits must be at least 2 to contain a transition")
    if width > len(symbols):
        raise ValueError("window_bits must not exceed the stream length")
    places = width - 1
    best = None
    for start in range(0, len(symbols) - width + 1):
        count = 0
        for index in range(start + 1, start + width):
            if symbols[index] != symbols[index - 1]:
                count += 1
        if best is None or count < best["transitions"]:
            best = {"start": start, "transitions": count, "density": count / float(places)}
    return best


def transitions_needed(window_bits, min_density):
    """Return the fewest transitions a window of this length must contain."""
    width = validate_positive_int(window_bits, "window_bits")
    if width < 2:
        raise ValueError("window_bits must be at least 2 to contain a transition")
    density = validate_density(min_density)
    places = width - 1
    exact = density * places
    whole = math.ceil(exact - REL_TOL * max(places, 1))
    if whole < 0:
        return 0
    return int(whole)


def transition_shortfall(stream, window_bits, min_density):
    """Return how many transitions the leanest window is missing."""
    lean = worst_window(stream, window_bits)
    needed = transitions_needed(window_bits, min_density)
    missing = needed - lean["transitions"]
    if missing < 0:
        return 0
    return missing


def randomisation_needed(stream, max_run, min_density, window_bits):
    """Return True when the raw stream cannot be sent without conditioning."""
    if runs_over_limit(stream, max_run):
        return True
    return transition_shortfall(stream, window_bits, min_density) > 0


def assess_bit_stream(stream, max_run, min_density, window_bits):
    """Assess one stream against both obligations of the clause."""
    symbols = validate_stream(stream)
    limit = validate_positive_int(max_run, "max_run")
    density_limit = validate_density(min_density)
    width = validate_positive_int(window_bits, "window_bits")
    if width < 2:
        raise ValueError("window_bits must be at least 2 to contain a transition")
    if width > len(symbols):
        raise ValueError("window_bits must not exceed the stream length")
    worst = longest_run(symbols)
    offenders = [run for run in run_lengths(symbols) if run["length"] > limit]
    overall = transition_density(symbols)
    lean = worst_window(symbols, width)
    needed = transitions_needed(width, density_limit)
    run_ok = not offenders
    density_tolerance = REL_TOL * max(density_limit, 1.0)
    overall_ok = overall is None or overall >= density_limit - density_tolerance
    window_ok = lean["density"] >= density_limit - density_tolerance
    density_ok = overall_ok and window_ok
    if not run_ok:
        verdict = RUN_TOO_LONG
    elif not density_ok:
        verdict = DENSITY_TOO_LOW
    else:
        verdict = COMPLIANT
    findings = []
    if not run_ok:
        findings.append(
            "a run of %d identical symbols starts at position %d against a tolerated %d; "
            "randomise the stream or use a transition-rich line code"
            % (worst["length"], worst["start"], limit)
        )
    if not window_ok:
        findings.append(
            "the leanest %d symbol window starts at position %d with %d transitions, %d "
            "short of the %d the density limit asks for"
            % (
                width,
                lean["start"],
                lean["transitions"],
                needed - lean["transitions"],
                needed,
            )
        )
    elif not overall_ok:
        findings.append(
            "overall transition density is %.6g against a %.6g limit" % (overall, density_limit)
        )
    return {
        "length": len(symbols),
        "runs": len(run_lengths(symbols)),
        "longest_run": worst["length"],
        "longest_run_start": worst["start"],
        "longest_run_symbol": worst["symbol"],
        "max_run": limit,
        "runs_over_limit": offenders,
        "transitions": transition_count(symbols),
        "transition_density": overall,
        "min_density": density_limit,
        "window_bits": width,
        "worst_window_start": lean["start"],
        "worst_window_transitions": lean["transitions"],
        "worst_window_density": lean["density"],
        "window_transitions_needed": needed,
        "window_transition_shortfall": max(0, needed - lean["transitions"]),
        "run_ok": run_ok,
        "overall_density_ok": overall_ok,
        "window_density_ok": window_ok,
        "density_ok": density_ok,
        "randomisation_needed": not (run_ok and density_ok),
        "verdict": verdict,
        "findings": findings,
    }
