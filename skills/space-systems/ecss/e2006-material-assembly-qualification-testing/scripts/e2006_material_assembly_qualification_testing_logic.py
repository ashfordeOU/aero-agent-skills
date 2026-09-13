#!/usr/bin/env python3
"""Both-polarity qualification of charging materials and assemblies.

Anchor: ECSS-E-ST-20-06C clause 6.6.3 (paraphrased into an implementable
procedure; no standard text is reproduced).

Rule implemented here: a dielectric material and the assembly it is built
into are qualified only when the campaign exercises BOTH potential-gradient
polarities -- the normal gradient (dielectric surface below the structure
potential) and the inverted gradient (dielectric surface above the structure
potential). A run qualifies one polarity for one item only when it is
qualification-grade, reaches the qualification stress and dwell, carries a
discharge-detection channel, and its detected-event record passes the
severity rule.

Deterministic, offline, stdlib only.
"""

import math

# Absorbs floating-point representation error when an applied value is
# compared against a derived limit (a product of stored floats). An exact
# match is compliant; this never relaxes the engineering limit itself.
REPR_TOL = 1e-9

NORMAL_GRADIENT = "normal-gradient"
INVERTED_GRADIENT = "inverted-gradient"
NO_GRADIENT = "no-gradient"
REQUIRED_POLARITIES = (NORMAL_GRADIENT, INVERTED_GRADIENT)

POLARITY_ALIASES = {
    "normal": NORMAL_GRADIENT,
    "normal-gradient": NORMAL_GRADIENT,
    "normal-potential-gradient": NORMAL_GRADIENT,
    "inverted": INVERTED_GRADIENT,
    "inverted-gradient": INVERTED_GRADIENT,
    "inverted-potential-gradient": INVERTED_GRADIENT,
}

# Campaign levels and whether they may close a qualification obligation.
CAMPAIGN_LEVELS = {
    "qualification": True,
    "protoflight": True,
    "acceptance": False,
    "development": False,
    "engineering-model": False,
}

ITEM_KINDS = ("material", "assembly")

DISCHARGE_CHANNELS = (
    "current-transient-probe",
    "optical-flash-detector",
    "rf-emission-antenna",
)

# An event above this energy is a sustained/high-energy event and fails the
# polarity condition on its own, whatever the programme count allowance is.
SUSTAINED_EVENT_ENERGY_MJ = 1.0

DEFAULT_QUALIFICATION_FACTOR = 1.25


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _reaches(applied, required):
    """True when applied >= required, an exact match included."""
    if applied >= required:
        return True
    return math.isclose(applied, required, rel_tol=REPR_TOL, abs_tol=0.0)


def normalize_polarity(token):
    """Canonicalize a declared polarity label.

    Raises ValueError for an unrecognized label. Used only to read a declared
    label; the authoritative polarity comes from derive_polarity().
    """
    if not isinstance(token, str) or not token.strip():
        raise ValueError("polarity label must be a non-empty string, got %r" % (token,))
    key = token.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in POLARITY_ALIASES:
        raise ValueError(
            "unrecognized polarity %r (known: %s)" % (token, ", ".join(sorted(POLARITY_ALIASES)))
        )
    return POLARITY_ALIASES[key]


def derive_polarity(surface_v, structure_v):
    """Derive the gradient polarity from the two measured potentials.

    Surface below structure -> normal gradient; surface above structure ->
    inverted gradient; an equal pair -> no gradient (qualifies neither).
    """
    surface = _as_float(surface_v, "surface potential")
    structure = _as_float(structure_v, "structure potential")
    delta = surface - structure
    if math.isclose(delta, 0.0, rel_tol=0.0, abs_tol=1e-9):
        return NO_GRADIENT
    return INVERTED_GRADIENT if delta > 0.0 else NORMAL_GRADIENT


def differential_potential(surface_v, structure_v):
    """Magnitude of the potential difference across the dielectric."""
    return abs(_as_float(surface_v, "surface potential") - _as_float(structure_v, "structure potential"))


def qualification_stress(predicted_v, factor=DEFAULT_QUALIFICATION_FACTOR):
    """Qualification stress = worst-case predicted differential x factor.

    Raises ValueError on a non-positive prediction or a factor below unity.
    """
    predicted = _as_float(predicted_v, "predicted differential-potential")
    if predicted <= 0.0:
        raise ValueError("predicted differential-potential must be positive, got %r" % (predicted,))
    fac = _as_float(factor, "qualification factor")
    if fac < 1.0:
        raise ValueError("qualification factor must be >= 1.0, got %r" % (fac,))
    return predicted * fac


def normalize_item(item):
    """Validate one qualification item (a material or an assembly)."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (type(item).__name__,))
    ident = item.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("item id must be a non-empty string, got %r" % (ident,))
    kind = item.get("kind")
    if not isinstance(kind, str) or kind.strip().lower() not in ITEM_KINDS:
        raise ValueError("item %s kind must be one of %s, got %r" % (ident, ", ".join(ITEM_KINDS), kind))
    factor = _as_float(
        item.get("qualification-factor", DEFAULT_QUALIFICATION_FACTOR),
        "item %s qualification-factor" % ident,
    )
    stress = qualification_stress(item.get("predicted-differential-v"), factor)
    dwell = _as_float(item.get("required-dwell-min"), "item %s required-dwell-min" % ident)
    if dwell <= 0.0:
        raise ValueError("item %s required-dwell-min must be positive" % ident)
    allowance = item.get("event-allowance", 0)
    if isinstance(allowance, bool) or not isinstance(allowance, int) or allowance < 0:
        raise ValueError("item %s event-allowance must be a non-negative integer" % ident)
    return {
        "id": ident.strip(),
        "kind": kind.strip().lower(),
        "qualification-factor": factor,
        "qualification-stress-v": stress,
        "required-dwell-min": dwell,
        "event-allowance": allowance,
    }


def normalize_run(run):
    """Validate one campaign run record."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (type(run).__name__,))
    ident = run.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("run id must be a non-empty string, got %r" % (ident,))
    item_ref = run.get("item")
    if not isinstance(item_ref, str) or not item_ref.strip():
        raise ValueError("run %s must reference an item id" % ident)
    level = run.get("level")
    if not isinstance(level, str) or level.strip().lower() not in CAMPAIGN_LEVELS:
        raise ValueError(
            "run %s has unknown level %r (known: %s)" % (ident, level, ", ".join(sorted(CAMPAIGN_LEVELS)))
        )
    level = level.strip().lower()
    surface = _as_float(run.get("surface-potential-v"), "run %s surface-potential-v" % ident)
    structure = _as_float(run.get("structure-potential-v"), "run %s structure-potential-v" % ident)
    dwell = _as_float(run.get("dwell-min"), "run %s dwell-min" % ident)
    if dwell < 0.0:
        raise ValueError("run %s dwell-min must be non-negative" % ident)
    channels_raw = run.get("instrumentation", [])
    if not isinstance(channels_raw, (list, tuple)):
        raise ValueError("run %s instrumentation must be a list" % ident)
    channels = set()
    for chan in channels_raw:
        if not isinstance(chan, str) or not chan.strip():
            raise ValueError("run %s instrumentation channel must be a non-empty string" % ident)
        channels.add(chan.strip().lower())
    events_raw = run.get("events", [])
    if not isinstance(events_raw, (list, tuple)):
        raise ValueError("run %s events must be a list" % ident)
    events = []
    for i, ev in enumerate(events_raw):
        if not isinstance(ev, dict):
            raise ValueError("run %s event %d must be a mapping" % (ident, i))
        energy = _as_float(ev.get("energy-mj"), "run %s event %d energy-mj" % (ident, i))
        if energy < 0.0:
            raise ValueError("run %s event %d energy-mj must be non-negative" % (ident, i))
        events.append({"energy-mj": energy})
    return {
        "id": ident.strip(),
        "item": item_ref.strip(),
        "level": level,
        "level-qualifying": CAMPAIGN_LEVELS[level],
        "surface-potential-v": surface,
        "structure-potential-v": structure,
        "polarity": derive_polarity(surface, structure),
        "differential-v": differential_potential(surface, structure),
        "dwell-min": dwell,
        "instrumentation": channels,
        "events": events,
    }


def has_discharge_detection(channels):
    """True when at least one recognized discharge-detection channel is present."""
    return any(chan in channels for chan in DISCHARGE_CHANNELS)


def grade_events(events, allowance):
    """Grade a detected-event record: 'none', 'within-allowance', 'over-allowance'
    or 'sustained'. A sustained/high-energy event outranks any count allowance.
    """
    if not events:
        return "none"
    if any(ev["energy-mj"] >= SUSTAINED_EVENT_ENERGY_MJ for ev in events):
        return "sustained"
    return "within-allowance" if len(events) <= allowance else "over-allowance"


def evaluate_run(run, item):
    """Categorize one run against one item.

    Returns the derived polarity, whether the run is qualifying (stress,
    dwell, level and instrumentation all satisfied), the event grade and the
    blocking findings.
    """
    rec = run if isinstance(run, dict) and "level-qualifying" in run else normalize_run(run)
    itm = item if isinstance(item, dict) and "qualification-stress-v" in item else normalize_item(item)
    findings = []
    if rec["item"] != itm["id"]:
        raise ValueError("run %s references item %r, not %r" % (rec["id"], rec["item"], itm["id"]))
    if not rec["level-qualifying"]:
        findings.append("level %r cannot close a qualification obligation" % rec["level"])
    if rec["polarity"] == NO_GRADIENT:
        findings.append("no potential gradient applied; the run qualifies neither polarity")
    if not _reaches(rec["differential-v"], itm["qualification-stress-v"]):
        findings.append(
            "applied differential %.6g V below qualification stress %.6g V"
            % (rec["differential-v"], itm["qualification-stress-v"])
        )
    if not _reaches(rec["dwell-min"], itm["required-dwell-min"]):
        findings.append(
            "dwell %.6g min below required %.6g min" % (rec["dwell-min"], itm["required-dwell-min"])
        )
    if not has_discharge_detection(rec["instrumentation"]):
        findings.append("no discharge-detection channel recording; the run is uninstrumented")
    grade = grade_events(rec["events"], itm["event-allowance"])
    qualifying = not findings
    passed = qualifying and grade in ("none", "within-allowance")
    if qualifying and not passed:
        findings.append("detected-event record graded %r" % grade)
    return {
        "run": rec["id"],
        "item": itm["id"],
        "polarity": rec["polarity"],
        "qualifying": qualifying,
        "event-grade": grade,
        "passed": passed,
        "findings": findings,
        "stress-margin-v": rec["differential-v"] - itm["qualification-stress-v"],
    }


def polarity_coverage(item, runs):
    """Map each required polarity to the passing run that closes it, or None."""
    itm = normalize_item(item)
    if not isinstance(runs, (list, tuple)):
        raise ValueError("runs must be a list")
    coverage = {polarity: None for polarity in REQUIRED_POLARITIES}
    evaluations = []
    for run in runs:
        rec = normalize_run(run)
        if rec["item"] != itm["id"]:
            continue
        result = evaluate_run(rec, itm)
        evaluations.append(result)
        if result["passed"] and coverage.get(result["polarity"]) is None:
            coverage[result["polarity"]] = result["run"]
    return {"item": itm["id"], "kind": itm["kind"], "coverage": coverage, "evaluations": evaluations}


def assess_item(item, runs):
    """Qualify one item: both polarity conditions need a passing run."""
    report = polarity_coverage(item, runs)
    gaps = [p for p in REQUIRED_POLARITIES if report["coverage"][p] is None]
    report["open-polarities"] = gaps
    report["qualified"] = not gaps
    return report


def assess_campaign(items, runs):
    """Aggregate the both-polarity verdict across every item in the campaign.

    Returns per-item reports, the residual (item, polarity) pairs, and a
    complete flag that is True only when no pair is left open.
    """
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty list")
    if not isinstance(runs, (list, tuple)):
        raise ValueError("runs must be a list")
    seen = set()
    reports = []
    residual = []
    for item in items:
        report = assess_item(item, runs)
        if report["item"] in seen:
            raise ValueError("duplicate item id %r" % report["item"])
        seen.add(report["item"])
        reports.append(report)
        for polarity in report["open-polarities"]:
            residual.append((report["item"], polarity))
    return {
        "reports": reports,
        "residual-pairs": residual,
        "qualified": sorted(r["item"] for r in reports if r["qualified"]),
        "complete": not residual,
    }
