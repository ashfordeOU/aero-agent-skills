#!/usr/bin/env python3
"""Whether a single junction gallium arsenide on germanium cell has an
active interface layer.

Anchor: ECSS-E-ST-20-08C clause 7.5.18. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A single junction gallium arsenide cell grown on a germanium substrate
can carry a second junction it was never meant to have, formed where the
epitaxial layer meets the substrate. An interface that is passive is
simply a mechanical carrier. One that is active sits in series with the
cell, generates its own photocurrent from the light the gallium arsenide
does not absorb, and changes how the cell behaves at temperature and
under a shifting spectrum for the whole mission.

No single measurement settles which of the two is in front of you, so
three independent lines are read and then weighed together:

    voltage      the open-circuit voltage the cell delivers, against the
                 voltage a gallium arsenide junction alone would give. An
                 active interface adds its own voltage in series
    spectral     the share of the spectral response that sits beyond the
                 gallium arsenide absorption edge, out in the band only
                 germanium can convert
    filtered     the current still produced under a long-pass filter that
                 removes everything the gallium arsenide junction
                 absorbs. A passive interface has almost nothing left

Each line is read against two thresholds rather than one. Above the
upper it indicates an active interface, below the lower a passive one,
and between them it has not decided -- that band is the declared
measurement uncertainty, not a place to round from.

The lines can disagree, and a disagreement is a result. An indeterminate
interface is reported as its own outcome rather than defaulting to
passive, because a passive default is the reading that lets an unplanned
junction reach a flight array.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LINE_VOLTAGE_EXCESS = "open-circuit-voltage-excess"
LINE_SUB_BANDGAP_RESPONSE = "sub-bandgap-response-share"
LINE_LONGPASS_CURRENT = "long-pass-filtered-current-ratio"

EVIDENCE_LINES = (
    LINE_VOLTAGE_EXCESS,
    LINE_SUB_BANDGAP_RESPONSE,
    LINE_LONGPASS_CURRENT,
)

LINE_INDICATES_ACTIVE = "line-indicates-active"
LINE_INDICATES_PASSIVE = "line-indicates-passive"
LINE_INCONCLUSIVE = "line-inconclusive"

LINE_READINGS = (LINE_INDICATES_ACTIVE, LINE_INDICATES_PASSIVE, LINE_INCONCLUSIVE)

INTERFACE_ACTIVE = "interface-active"
INTERFACE_PASSIVE = "interface-passive"
INTERFACE_INDETERMINATE = "interface-indeterminate"

INTERFACE_CATEGORIES = (
    INTERFACE_ACTIVE,
    INTERFACE_PASSIVE,
    INTERFACE_INDETERMINATE,
)

LOT_RESOLVED = "lot-resolved"
LOT_OPEN = "lot-open"

# Declared evaluation policy: project numbers, not physical constants.
DEFAULT_INTERFACE_POLICY = {
    "gallium_arsenide_cutoff_nm": 880.0,
    "sub_bandgap_start_nm": 950.0,
    "germanium_cutoff_nm": 1800.0,
    "min_spectral_samples": 6,
    "active_voltage_excess_v": 0.150,
    "passive_voltage_excess_v": 0.050,
    "active_sub_bandgap_share": 0.050,
    "passive_sub_bandgap_share": 0.010,
    "active_longpass_ratio": 0.020,
    "passive_longpass_ratio": 0.005,
    "min_conclusive_lines": 2,
    "min_agreeing_lines": 2,
}

LINE_THRESHOLD_KEYS = {
    LINE_VOLTAGE_EXCESS: ("active_voltage_excess_v", "passive_voltage_excess_v"),
    LINE_SUB_BANDGAP_RESPONSE: (
        "active_sub_bandgap_share",
        "passive_sub_bandgap_share",
    ),
    LINE_LONGPASS_CURRENT: ("active_longpass_ratio", "passive_longpass_ratio"),
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(
            "%s must be an integer of at least %d, got %r" % (name, minimum, value)
        )
    return value


def validate_interface_policy(policy):
    """Check an interface evaluation policy declares a usable threshold set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    cutoff = _require_positive(
        "gallium_arsenide_cutoff_nm", policy.get("gallium_arsenide_cutoff_nm")
    )
    start = _require_positive(
        "sub_bandgap_start_nm", policy.get("sub_bandgap_start_nm")
    )
    germanium = _require_positive(
        "germanium_cutoff_nm", policy.get("germanium_cutoff_nm")
    )
    if not start > cutoff:
        raise ValueError(
            "the sub-bandgap band must start clear of the gallium arsenide edge "
            "(%r nm against an edge at %r nm)" % (start, cutoff)
        )
    if not germanium > start:
        raise ValueError(
            "the germanium cutoff must sit above the sub-bandgap start (%r nm "
            "against %r nm)" % (germanium, start)
        )
    _require_count("min_spectral_samples", policy.get("min_spectral_samples"), 3)
    for line, (active_key, passive_key) in LINE_THRESHOLD_KEYS.items():
        active = _require_non_negative(active_key, policy.get(active_key))
        passive = _require_non_negative(passive_key, policy.get(passive_key))
        if not active > passive:
            raise ValueError(
                "the %s thresholds leave no undecided band (%r against %r)"
                % (line, active, passive)
            )
    conclusive = _require_count(
        "min_conclusive_lines", policy.get("min_conclusive_lines"), 1
    )
    agreeing = _require_count("min_agreeing_lines", policy.get("min_agreeing_lines"), 1)
    if conclusive > len(EVIDENCE_LINES) or agreeing > len(EVIDENCE_LINES):
        raise ValueError(
            "the policy asks for more lines than the %d this evaluation reads"
            % len(EVIDENCE_LINES)
        )
    if agreeing > conclusive:
        raise ValueError(
            "min_agreeing_lines cannot exceed min_conclusive_lines, or no reading "
            "could ever satisfy both"
        )
    return policy


def validate_spectral_response(samples, policy=DEFAULT_INTERFACE_POLICY):
    """Read a spectral response sweep and say what band it actually covered."""
    validate_interface_policy(policy)
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of mappings")
    read = []
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("sample must be a mapping, got %r" % (sample,))
        wavelength = _require_positive("wavelength_nm", sample.get("wavelength_nm"))
        response = _require_non_negative(
            "response_a_per_w", sample.get("response_a_per_w")
        )
        if any(_close(wavelength, taken) for taken in seen):
            raise ValueError("the sweep samples %r nm twice" % wavelength)
        seen.add(wavelength)
        read.append(
            {"wavelength_nm": wavelength, "response_a_per_w": response}
        )
    read.sort(key=lambda entry: entry["wavelength_nm"])
    minimum = int(policy["min_spectral_samples"])
    if len(read) < minimum:
        raise ValueError(
            "the sweep carries %d samples against the %d the policy declares"
            % (len(read), minimum)
        )
    low = read[0]["wavelength_nm"]
    high = read[-1]["wavelength_nm"]
    cutoff = float(policy["gallium_arsenide_cutoff_nm"])
    start = float(policy["sub_bandgap_start_nm"])
    if _at_least(low, cutoff):
        raise ValueError(
            "the sweep starts at %r nm, on or beyond the gallium arsenide edge, so "
            "it never measured the junction it is meant to compare against" % low
        )
    if _at_most(high, start):
        raise ValueError(
            "the sweep stops at %r nm, at or below the sub-bandgap band start, so "
            "there is no sub-bandgap evidence in it at all" % high
        )
    germanium = float(policy["germanium_cutoff_nm"])
    truncated = not _at_least(high, germanium)
    findings = []
    if truncated:
        findings.append(
            "the sweep stops at %.1f nm and the germanium response runs to %.1f nm, "
            "so the sub-bandgap band was only partly measured" % (high, germanium)
        )
    return {
        "samples": tuple(read),
        "lowest_wavelength_nm": low,
        "highest_wavelength_nm": high,
        "reaches_germanium_cutoff": not truncated,
        "findings": findings,
    }


def _interpolate(samples, wavelength):
    """Linear response at a wavelength inside the sampled span."""
    first = samples[0]["wavelength_nm"]
    last = samples[-1]["wavelength_nm"]
    if wavelength < first or wavelength > last:
        raise ValueError(
            "%r nm sits outside the sampled span %r to %r nm"
            % (wavelength, first, last)
        )
    for index in range(len(samples) - 1):
        left = samples[index]
        right = samples[index + 1]
        if _at_least(wavelength, left["wavelength_nm"]) and _at_most(
            wavelength, right["wavelength_nm"]
        ):
            span = right["wavelength_nm"] - left["wavelength_nm"]
            if _close(span, 0.0):
                return left["response_a_per_w"]
            share = (wavelength - left["wavelength_nm"]) / span
            return left["response_a_per_w"] + share * (
                right["response_a_per_w"] - left["response_a_per_w"]
            )
    return samples[-1]["response_a_per_w"]


def integrate_response(samples, low_nm, high_nm):
    """Trapezoidal area under the response curve between two wavelengths."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("samples must carry at least two points")
    low = _require_positive("low_nm", low_nm)
    high = _require_positive("high_nm", high_nm)
    if not high > low:
        raise ValueError(
            "the band closes at or below where it opens (%r to %r nm)" % (low, high)
        )
    points = [{"wavelength_nm": low, "response_a_per_w": _interpolate(samples, low)}]
    for sample in samples:
        if (
            sample["wavelength_nm"] > low
            and sample["wavelength_nm"] < high
            and not _close(sample["wavelength_nm"], low)
            and not _close(sample["wavelength_nm"], high)
        ):
            points.append(dict(sample))
    points.append(
        {"wavelength_nm": high, "response_a_per_w": _interpolate(samples, high)}
    )
    area = 0.0
    for index in range(len(points) - 1):
        left = points[index]
        right = points[index + 1]
        area += (
            (left["response_a_per_w"] + right["response_a_per_w"])
            / 2.0
            * (right["wavelength_nm"] - left["wavelength_nm"])
        )
    return area


def sub_bandgap_response_share(sweep, policy=DEFAULT_INTERFACE_POLICY):
    """The share of the whole response that sits beyond the gallium arsenide edge."""
    validate_interface_policy(policy)
    if not isinstance(sweep, dict) or "samples" not in sweep:
        raise ValueError("sweep must be a validated spectral response reading")
    samples = list(sweep["samples"])
    low = sweep["lowest_wavelength_nm"]
    high = sweep["highest_wavelength_nm"]
    band_start = float(policy["sub_bandgap_start_nm"])
    band_end = min(high, float(policy["germanium_cutoff_nm"]))
    total = integrate_response(samples, low, high)
    if _close(total, 0.0):
        raise ValueError(
            "the sweep integrates to zero response, so no share can be taken of it"
        )
    return integrate_response(samples, band_start, band_end) / total


def open_circuit_voltage_excess_v(measured_voc_v, single_junction_reference_v):
    """How much open-circuit voltage sits above the single junction reference."""
    measured = _require_positive("measured_voc_v", measured_voc_v)
    reference = _require_positive(
        "single_junction_reference_v", single_junction_reference_v
    )
    return measured - reference


def longpass_current_ratio(filtered_isc_a, unfiltered_isc_a):
    """The share of short-circuit current left under the long-pass filter."""
    filtered = _require_non_negative("filtered_isc_a", filtered_isc_a)
    unfiltered = _require_positive("unfiltered_isc_a", unfiltered_isc_a)
    if filtered > unfiltered and not _close(filtered, unfiltered):
        raise ValueError(
            "the filtered current of %r A exceeds the unfiltered %r A, so the "
            "filter added light it was meant to remove" % (filtered, unfiltered)
        )
    return filtered / unfiltered


def read_evidence_line(line, value, policy=DEFAULT_INTERFACE_POLICY):
    """Read one line of evidence against its own pair of thresholds."""
    validate_interface_policy(policy)
    if line not in LINE_THRESHOLD_KEYS:
        raise ValueError("unknown evidence line %r" % (line,))
    measured = _require_number(line, value)
    active_key, passive_key = LINE_THRESHOLD_KEYS[line]
    active = float(policy[active_key])
    passive = float(policy[passive_key])
    if _at_least(measured, active):
        reading = LINE_INDICATES_ACTIVE
    elif _at_most(measured, passive):
        reading = LINE_INDICATES_PASSIVE
    else:
        reading = LINE_INCONCLUSIVE
    return {
        "line": line,
        "value": measured,
        "active_threshold": active,
        "passive_threshold": passive,
        "reading": reading,
    }


def categorize_interface(readings, policy=DEFAULT_INTERFACE_POLICY):
    """Weigh the evidence lines together into one interface outcome."""
    validate_interface_policy(policy)
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of line readings")
    seen = []
    for reading in readings:
        if not isinstance(reading, dict) or reading.get("reading") not in LINE_READINGS:
            raise ValueError("reading must be a line reading, got %r" % (reading,))
        if reading["line"] in seen:
            raise ValueError("the line %s is read twice" % reading["line"])
        seen.append(reading["line"])
    active = [r for r in readings if r["reading"] == LINE_INDICATES_ACTIVE]
    passive = [r for r in readings if r["reading"] == LINE_INDICATES_PASSIVE]
    conclusive = len(active) + len(passive)
    findings = []
    if active and passive:
        findings.append(
            "the evidence lines contradict each other: %s indicate an active "
            "interface while %s indicate a passive one"
            % (
                ", ".join(sorted(r["line"] for r in active)),
                ", ".join(sorted(r["line"] for r in passive)),
            )
        )
        category = INTERFACE_INDETERMINATE
    elif conclusive < int(policy["min_conclusive_lines"]):
        findings.append(
            "only %d of the %d evidence lines decided, against the %d the policy "
            "asks to agree"
            % (conclusive, len(readings), int(policy["min_conclusive_lines"]))
        )
        category = INTERFACE_INDETERMINATE
    elif len(active) >= int(policy["min_agreeing_lines"]):
        category = INTERFACE_ACTIVE
    elif len(passive) >= int(policy["min_agreeing_lines"]):
        category = INTERFACE_PASSIVE
    else:
        findings.append(
            "no outcome reached the %d agreeing lines the policy asks for"
            % int(policy["min_agreeing_lines"])
        )
        category = INTERFACE_INDETERMINATE
    return {
        "category": category,
        "active_lines": sorted(r["line"] for r in active),
        "passive_lines": sorted(r["line"] for r in passive),
        "inconclusive_lines": sorted(
            r["line"] for r in readings if r["reading"] == LINE_INCONCLUSIVE
        ),
        "conclusive_line_count": conclusive,
        "findings": findings,
    }


def assess_cell(cell, policy=DEFAULT_INTERFACE_POLICY):
    """Evaluate one single junction cell for an active interface layer."""
    validate_interface_policy(policy)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = _require_text("cell_id", cell.get("cell_id"))
    sweep = validate_spectral_response(cell.get("spectral_response"), policy)
    excess = open_circuit_voltage_excess_v(
        cell.get("measured_voc_v"), cell.get("single_junction_reference_v")
    )
    share = sub_bandgap_response_share(sweep, policy)
    ratio = longpass_current_ratio(
        cell.get("filtered_isc_a"), cell.get("unfiltered_isc_a")
    )

    readings = [
        read_evidence_line(LINE_VOLTAGE_EXCESS, excess, policy),
        read_evidence_line(LINE_SUB_BANDGAP_RESPONSE, share, policy),
        read_evidence_line(LINE_LONGPASS_CURRENT, ratio, policy),
    ]
    if not sweep["reaches_germanium_cutoff"]:
        for reading in readings:
            if reading["line"] == LINE_SUB_BANDGAP_RESPONSE:
                reading["reading"] = LINE_INCONCLUSIVE
    grouped = categorize_interface(readings, policy)

    findings = ["%s: %s" % (cell_id, text) for text in sweep["findings"]]
    findings.extend("%s: %s" % (cell_id, text) for text in grouped["findings"])
    return {
        "cell_id": cell_id,
        "category": grouped["category"],
        "voltage_excess_v": excess,
        "sub_bandgap_share": share,
        "longpass_ratio": ratio,
        "line_readings": readings,
        "active_lines": grouped["active_lines"],
        "passive_lines": grouped["passive_lines"],
        "inconclusive_lines": grouped["inconclusive_lines"],
        "sweep_reaches_germanium_cutoff": sweep["reaches_germanium_cutoff"],
        "findings": findings,
    }


def assess_interface_evaluation(case, policy=DEFAULT_INTERFACE_POLICY):
    """Full clause 7.5.18 sweep over one batch of single junction cells."""
    validate_interface_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    cells = case.get("cells")
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("case cells must be a non-empty sequence of mappings")
    seen = set()
    records = []
    for cell in cells:
        record = assess_cell(cell, policy)
        if record["cell_id"] in seen:
            raise ValueError("case declares cell %s twice" % record["cell_id"])
        seen.add(record["cell_id"])
        records.append(record)
    records.sort(key=lambda entry: entry["cell_id"])

    findings = []
    for record in records:
        findings.extend(record["findings"])

    grouped = {category: [] for category in INTERFACE_CATEGORIES}
    for record in records:
        grouped[record["category"]].append(record["cell_id"])
    for category in grouped:
        grouped[category].sort()

    undecided = grouped[INTERFACE_INDETERMINATE]
    if undecided:
        findings.append(
            "the batch left %s undecided, and an undecided interface is not a "
            "passive one" % ", ".join(undecided)
        )
    mixed = bool(grouped[INTERFACE_ACTIVE]) and bool(grouped[INTERFACE_PASSIVE])
    if mixed:
        findings.append(
            "the batch carries both active and passive interfaces, so the cells did "
            "not all come from one substrate process"
        )
    return {
        "verdict": LOT_RESOLVED if not undecided and not mixed else LOT_OPEN,
        "cell_records": records,
        "cells_by_category": grouped,
        "cell_count": len(records),
        "batch_is_uniform": not mixed,
        "undecided_cell_ids": undecided,
        "findings": findings,
    }
