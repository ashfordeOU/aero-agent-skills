#!/usr/bin/env python3
"""Tuneable-equipment frequency selection for ECSS-E-ST-20-07C clause 5.2.7.2.

Paraphrased, implementable procedure (no verbatim standard text):

* A unit that tunes across a band, or hops between channels, behaves
  differently at each setting: filter skirts, synthesizer spurs and amplifier
  match all move with the tuning. One measurement at one convenient setting
  therefore characterizes one setting and nothing else.
* Each tuning band or channel range is measured at several settings spread
  across the range. Spread is the requirement, not count: three points
  crowded into the middle of a band satisfy an arithmetic minimum and leave
  both edges, where the filters roll off and the match degrades, unmeasured.
* The default plan for a continuously tuneable band is a set of evenly
  spaced settings that includes both band edges. For a channelized range the
  settings are real channel centres, evenly spread over the channel index
  range, because a frequency between two channels is not a setting the unit
  can take.
* A proposed plan is graded on three independent things: enough points in the
  band, a lowest point close enough to the bottom edge and a highest point
  close enough to the top edge, and no gap between consecutive points wider
  than the allowed fraction of the band.
* A frequency outside the band it is meant to cover is a data error rather
  than a poor plan, and is rejected instead of being scored.
* Any under-covered band holds the run until its plan is extended.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance absorbing binary representation error in hertz sums and in
# normalized band positions. It is NOT an engineering allowance: the coverage
# limits themselves are never widened.
FREQ_EPS = 1e-9

DEFAULT_TUNING_SPEC = {
    "min_points_per_band": 3.0,
    "edge_tolerance_fraction": 0.05,
    "max_gap_fraction": 0.5,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _not_above(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=FREQ_EPS)


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=FREQ_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard coverage specification."""
    spec = dict(DEFAULT_TUNING_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_TUNING_SPEC:
            raise ValueError("unrecognized tuning specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number < 0.0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def normalize_band(band):
    """Validate one tuning band or channel range."""
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %r" % (band,))
    name = band.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("band needs a non-empty 'name', got %r" % (name,))
    start = _require_number(band.get("start_hz"), "band %r start_hz" % name)
    stop = _require_number(band.get("stop_hz"), "band %r stop_hz" % name)
    if start <= 0.0:
        raise ValueError("band %r start_hz must be positive, got %r" % (name, start))
    if not stop > start:
        raise ValueError(
            "band %r stop_hz (%r) must lie above start_hz (%r)" % (name, stop, start)
        )
    normalized = {"name": name, "start_hz": start, "stop_hz": stop}
    if "channel_spacing_hz" in band or "channel_count" in band:
        spacing = _require_number(
            band.get("channel_spacing_hz"), "band %r channel_spacing_hz" % name
        )
        count = band.get("channel_count")
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("band %r channel_count must be an integer, got %r" % (name, count))
        if spacing <= 0.0:
            raise ValueError(
                "band %r channel_spacing_hz must be positive, got %r" % (name, spacing)
            )
        if count < 1:
            raise ValueError("band %r channel_count must be at least 1, got %r" % (name, count))
        top = start + spacing * (count - 1)
        if not _not_above(top, stop):
            raise ValueError(
                "band %r channel plan reaches %r Hz, above stop_hz %r" % (name, top, stop)
            )
        normalized["channel_spacing_hz"] = spacing
        normalized["channel_count"] = count
    return normalized


def band_span_hz(band):
    """Width of one tuning band."""
    normalized = normalize_band(band)
    return normalized["stop_hz"] - normalized["start_hz"]


def select_band_frequencies(band, points=None, spec=None):
    """Evenly spread settings across a continuously tuneable band."""
    resolved = resolve_spec(spec)
    normalized = normalize_band(band)
    if points is None:
        points = int(math.ceil(resolved["min_points_per_band"] - FREQ_EPS))
    if isinstance(points, bool) or not isinstance(points, int):
        raise ValueError("points must be an integer, got %r" % (points,))
    if points < 2:
        raise ValueError("a spread needs at least 2 points, got %r" % (points,))
    span = normalized["stop_hz"] - normalized["start_hz"]
    step = span / float(points - 1)
    return [normalized["start_hz"] + step * i for i in range(points)]


def channel_centres_hz(band):
    """Every channel centre of a channelized range."""
    normalized = normalize_band(band)
    if "channel_count" not in normalized:
        raise ValueError(
            "band %r declares no channel plan; use select_band_frequencies"
            % (normalized["name"],)
        )
    spacing = normalized["channel_spacing_hz"]
    return [normalized["start_hz"] + spacing * i for i in range(normalized["channel_count"])]


def select_channel_frequencies(band, points=None, spec=None):
    """Channel centres spread evenly over the channel index range."""
    resolved = resolve_spec(spec)
    centres = channel_centres_hz(band)
    if points is None:
        points = int(math.ceil(resolved["min_points_per_band"] - FREQ_EPS))
    if isinstance(points, bool) or not isinstance(points, int):
        raise ValueError("points must be an integer, got %r" % (points,))
    if points < 1:
        raise ValueError("a channel selection needs at least 1 point, got %r" % (points,))
    if points > len(centres):
        raise ValueError(
            "asked for %d channels but the range holds %d" % (points, len(centres))
        )
    if points == 1:
        return [centres[0]]
    last = len(centres) - 1
    chosen = []
    for i in range(points):
        index = int(round(last * i / float(points - 1)))
        if index not in chosen:
            chosen.append(index)
    return [centres[i] for i in chosen]


def normalized_positions(band, frequencies):
    """Positions of chosen settings within the band, as fractions of its span."""
    normalized = normalize_band(band)
    if not isinstance(frequencies, (list, tuple)) or not frequencies:
        raise ValueError("frequencies must be a non-empty sequence")
    span = normalized["stop_hz"] - normalized["start_hz"]
    positions = []
    for i, value in enumerate(frequencies):
        hz = _require_number(value, "frequencies[%d]" % i)
        position = (hz - normalized["start_hz"]) / span
        if position < -FREQ_EPS or position > 1.0 + FREQ_EPS:
            raise ValueError(
                "frequency %r lies outside band %r" % (hz, normalized["name"])
            )
        positions.append(min(1.0, max(0.0, position)))
    return sorted(positions)


def largest_normalized_gap(band, frequencies):
    """Widest untested stretch of the band, edges included, as a fraction."""
    positions = normalized_positions(band, frequencies)
    boundaries = [0.0] + positions + [1.0]
    return max(boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1))


def check_band_coverage(band, frequencies, spec=None):
    """Grade one band plan on point count, edge reach and internal gaps."""
    resolved = resolve_spec(spec)
    normalized = normalize_band(band)
    positions = normalized_positions(band, frequencies)
    required = int(math.ceil(resolved["min_points_per_band"] - FREQ_EPS))
    edge = resolved["edge_tolerance_fraction"]
    gap = largest_normalized_gap(band, frequencies)
    enough = len(positions) >= required
    bottom_ok = _not_above(positions[0], edge)
    top_ok = _at_least(positions[-1], 1.0 - edge)
    gap_ok = _not_above(gap, resolved["max_gap_fraction"])
    return {
        "band": normalized["name"],
        "points": len(positions),
        "required_points": required,
        "enough_points": enough,
        "lowest_position": positions[0],
        "highest_position": positions[-1],
        "edge_tolerance_fraction": edge,
        "bottom_edge_ok": bottom_ok,
        "top_edge_ok": top_ok,
        "largest_gap_fraction": gap,
        "max_gap_fraction": resolved["max_gap_fraction"],
        "gap_ok": gap_ok,
        "compliant": enough and bottom_ok and top_ok and gap_ok,
    }


def tuning_plan_readiness(findings):
    """Gate token for the finding list of one tuning plan."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "ready-for-measurement" if not findings else "hold-tuning-plan"


def evaluate_tuning_plan(config):
    """End-to-end clause 5.2.7.2 frequency-selection check for one unit."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("bands", "plan"):
        if key not in config:
            raise ValueError("config missing required key %r" % (key,))
    bands = config["bands"]
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty sequence")
    plan = config["plan"]
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of band name to frequencies")

    normalized = [normalize_band(b) for b in bands]
    names = [b["name"] for b in normalized]
    if len(set(names)) != len(names):
        raise ValueError("band names must be unique, got %r" % (names,))
    unknown = sorted(set(plan) - set(names))
    if unknown:
        raise ValueError("plan names bands that were not declared: %r" % (unknown,))

    coverage = []
    recommended = {}
    findings = []
    for band, raw in zip(normalized, bands):
        name = band["name"]
        if name not in plan:
            findings.append("band %s has no measurement frequencies at all" % name)
            recommended[name] = _recommend(raw, config.get("spec"))
            continue
        check = check_band_coverage(raw, plan[name], config.get("spec"))
        coverage.append(check)
        if not check["enough_points"]:
            findings.append("band %s is measured at too few settings" % name)
        if not check["bottom_edge_ok"]:
            findings.append("band %s is not measured near its lower edge" % name)
        if not check["top_edge_ok"]:
            findings.append("band %s is not measured near its upper edge" % name)
        if not check["gap_ok"]:
            findings.append("band %s leaves an oversized untested gap" % name)
        if not check["compliant"]:
            recommended[name] = _recommend(raw, config.get("spec"))

    return {
        "bands": normalized,
        "coverage": coverage,
        "recommended_frequencies_hz": recommended,
        "findings": findings,
        "status": tuning_plan_readiness(findings),
        "ready": not findings,
    }


def _recommend(band, spec=None):
    """Default plan for a band: channel centres when channelized, else a spread."""
    normalized = normalize_band(band)
    if "channel_count" in normalized:
        return select_channel_frequencies(band, None, spec)
    return select_band_frequencies(band, None, spec)
