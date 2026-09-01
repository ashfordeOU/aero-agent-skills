#!/usr/bin/env python3
"""ARP4761A zonal safety analysis logic (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4761a: proprietary
SAE, summary only): zonal safety analysis (ZSA) is one of the three
common cause analyses in ARP4761A, alongside particular risk analysis
and common mode analysis. ZSA examines each physical zone of the
aircraft: the components installed in the zone, the structure, the
wiring, the plumbing, and the external threats that can enter the
zone such as fire, fluid leaks, and impacts. Each zone hazard is
classified by severity, separation and containment keep protected
components away from the hazard sources, the zonal hazard checklist
must be complete, and the ZSA report rolls the findings up for the
safety assessment.
"""

# Severity classes used by the zonal hazard checklist, ordered from
# least to most severe. Values follow the ARP4761A severity ladder
# (minor, major, hazardous, catastrophic).
SEVERITY_ORDER = ("minor", "major", "hazardous", "catastrophic")


def zone_identification(zone_id):
    """Normalize and validate a physical zone identifier.

    ARP4761A zones are keyed by zone number, commonly the ATA
    chapter plus a zone suffix (for example '141' for the forward
    fuselage nose zone or '241' for the forward cargo area). The
    identifier must be a non-empty string of digits with an optional
    letter suffix, such as '141', '141A', or '241'. Returns the
    normalized uppercase form. Anything else raises ValueError.

    Anchor example: '141a' normalizes to '141A'; '241' stays '241'.
    """
    if not isinstance(zone_id, str):
        raise ValueError("zone_id must be a string, got %r" % (zone_id,))
    cleaned = zone_id.strip().upper()
    if not cleaned:
        raise ValueError("zone_id must be non-empty, got %r" % (zone_id,))
    if not all(ch.isalnum() for ch in cleaned):
        raise ValueError(
            "zone_id must be digits with an optional letter suffix, got %r"
            % (zone_id,)
        )
    head = cleaned[:-1] if cleaned[-1].isalpha() else cleaned
    if not head.isdigit():
        raise ValueError(
            "zone_id must be digits with an optional letter suffix, got %r"
            % (zone_id,)
        )
    return cleaned


def severity_rank(severity):
    """Rank of a severity class on the 1..4 ladder.

    severity must be one of 'minor', 'major', 'hazardous',
    'catastrophic' (case-insensitive). Unknown values raise
    ValueError.
    """
    if not isinstance(severity, str):
        raise ValueError("severity must be a string, got %r" % (severity,))
    key = severity.strip().lower()
    if key not in SEVERITY_ORDER:
        raise ValueError(
            "severity must be one of %s, got %r"
            % (", ".join(SEVERITY_ORDER), severity)
        )
    return SEVERITY_ORDER.index(key) + 1


def zone_severity_rollup(findings):
    """Highest severity present in a list of zonal hazard findings.

    findings is a list of severity strings (each validated by
    severity_rank). An empty list returns 'none' (no hazard
    identified). Non-string entries raise ValueError.

    Anchor example: ['minor', 'major', 'hazardous'] rolls up to
    'hazardous'; ['major', 'minor'] rolls up to 'major'; [] returns
    'none'.
    """
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a list, got %r" % (findings,))
    if len(findings) == 0:
        return "none"
    best = None
    best_rank = 0
    for f in findings:
        rank = severity_rank(f)
        if rank > best_rank:
            best_rank = rank
            best = f.strip().lower()
    return best


def checklist_coverage(assessed, total):
    """Fraction of the zonal hazard checklist items assessed.

    assessed and total are non-negative integers with assessed <=
    total. Returns assessed / total as a float. Violations raise
    ValueError.

    Anchor example: 9 of 12 items assessed gives 0.75; 12 of 12 gives
    1.0; 0 of 5 gives 0.0.
    """
    for name, n in (("assessed", assessed), ("total", total)):
        if not isinstance(n, int) or isinstance(n, bool):
            raise ValueError("%s must be an int, got %r" % (name, n))
        if n < 0:
            raise ValueError("%s must be >= 0, got %r" % (name, n))
    if assessed > total:
        raise ValueError(
            "assessed (%d) cannot exceed total (%d)" % (assessed, total)
        )
    if total == 0:
        return 0.0
    return assessed / total


def checklist_complete(assessed, total):
    """True when every zonal hazard checklist item is assessed.

    Delegates validation to checklist_coverage; complete means
    coverage of exactly 1.0.
    """
    return checklist_coverage(assessed, total) == 1.0


def separation_verdict(actual_gap, required_gap):
    """Separation verdict between a hazard source and protected zone.

    actual_gap is the measured clearance in the zone (millimeters),
    required_gap the minimum clearance the analysis calls for.
    actual_gap >= required_gap means the separation holds: verdict
    'ok'. Any shortfall gives 'action'. Negative inputs raise
    ValueError.

    Anchor example: 50.0 mm actual against 50.0 mm required is 'ok';
    49.0 against 50.0 is 'action'.
    """
    for name, v in (("actual_gap", actual_gap), ("required_gap", required_gap)):
        if v < 0.0:
            raise ValueError("%s must be >= 0, got %r" % (name, v))
    return "ok" if actual_gap >= required_gap else "action"


def containment_verdict(barrier_rating, hazard_energy):
    """Containment verdict for a zone barrier against a hazard.

    barrier_rating is the barrier resistance class (1..5), hazard_
    energy the energy class of the hazard source (1..5). The barrier
    contains the hazard when its rating is at least the energy:
    verdict 'ok'. Otherwise 'action'. Out-of-range values raise
    ValueError.

    Anchor example: rating 3 against energy 2 is 'ok'; rating 2
    against energy 3 is 'action'.
    """
    for name, v in (("barrier_rating", barrier_rating), ("hazard_energy", hazard_energy)):
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("%s must be an int, got %r" % (name, v))
        if not 1 <= v <= 5:
            raise ValueError("%s must be in 1..5, got %r" % (name, v))
    return "ok" if barrier_rating >= hazard_energy else "action"


def zsa_report(zones):
    """Roll the zone findings up into the ZSA report summary.

    zones is a list of zone dicts, each with keys:
      id           zone identifier string (required)
      findings     list of severity strings (validated)
      assessed     int, checklist items assessed in the zone
      total        int, checklist items required for the zone
      separation   'ok' or 'action' (validated)
      containment  'ok' or 'action' (validated)
    Returns a dict with: total_zones, action_zones, severity_counts
    (per severity class), checklist_assessed, checklist_total,
    coverage, and verdict. A zone needs action when its rollup is
    hazardous or catastrophic, any checklist item is unassessed, or
    either separation or containment verdict is 'action'. The report
    verdict is 'accept' when no zone needs action, else 'action'.
    """
    if not isinstance(zones, list):
        raise ValueError("zones must be a list, got %r" % (zones,))
    severity_counts = {s: 0 for s in SEVERITY_ORDER}
    checklist_assessed = 0
    checklist_total = 0
    action_zones = []
    for z in zones:
        if not isinstance(z, dict):
            raise ValueError("each zone must be a dict, got %r" % (z,))
        if not z.get("id"):
            raise ValueError("zone dict needs a non-empty 'id', got %r" % (z,))
        rollup = zone_severity_rollup(z["findings"])
        if rollup != "none":
            severity_counts[rollup] += 1
        assessed = z["assessed"]
        total = z["total"]
        coverage = checklist_coverage(assessed, total)
        checklist_assessed += assessed
        checklist_total += total
        if z["separation"] not in ("ok", "action"):
            raise ValueError(
                "zone %s: separation must be 'ok' or 'action', got %r"
                % (z["id"], z["separation"])
            )
        if z["containment"] not in ("ok", "action"):
            raise ValueError(
                "zone %s: containment must be 'ok' or 'action', got %r"
                % (z["id"], z["containment"])
            )
        needs_action = (
            rollup in ("hazardous", "catastrophic")
            or not checklist_complete(assessed, total)
            or z["separation"] == "action"
            or z["containment"] == "action"
        )
        if needs_action:
            action_zones.append(z["id"])
    coverage = (
        checklist_assessed / checklist_total if checklist_total > 0 else 0.0
    )
    verdict = "accept" if not action_zones else "action"
    return {
        "total_zones": len(zones),
        "action_zones": sorted(action_zones),
        "severity_counts": severity_counts,
        "checklist_assessed": checklist_assessed,
        "checklist_total": checklist_total,
        "coverage": coverage,
        "verdict": verdict,
    }
