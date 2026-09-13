#!/usr/bin/env python3
"""When surface provisions are unmet, sample testing becomes mandatory.

Anchor: ECSS-E-ST-20-06C clause 6.6.1 (paraphrased into an implementable
procedure; no verbatim standard text).

The clause is a trigger rule, not a method: whenever the material and
analysis provisions for an external surface are not met, that surface
goes to sample testing.  Implementing it means deciding, provision by
provision and on the strength of the evidence offered, whether the
provision is actually met, and turning every shortfall into the sample
campaign it demands.

Offline, deterministic, standard-library only:

1. normalise each surface item and the status of every provision;
2. downgrade a claim whose evidence cannot carry it;
3. trigger the sample kind each unmet provision demands;
4. size and sequence the resulting campaign;
5. report invalid waivers, missing statuses and unsupported claims.
"""

import math

# Provision registry.  analysis_acceptable says whether an analytical
# demonstration can discharge the provision at all: a material property
# provision needs measured data, an analysis provision does not.
PROVISIONS = {
    "conductive-surface-material-rule": {
        "sample_kind": "material-characterisation-sample",
        "analysis_acceptable": False,
        "sequence_rank": 1,
    },
    "surface-resistivity-limit": {
        "sample_kind": "resistivity-measurement-sample",
        "analysis_acceptable": False,
        "sequence_rank": 2,
    },
    "electrical-continuity-bonding": {
        "sample_kind": "bonding-continuity-sample",
        "analysis_acceptable": False,
        "sequence_rank": 3,
    },
    "surface-potential-analysis-coverage": {
        "sample_kind": "electron-beam-exposure-sample",
        "analysis_acceptable": True,
        "sequence_rank": 4,
    },
    "biased-surface-disturbance-analysis": {
        "sample_kind": "biased-plasma-exposure-sample",
        "analysis_acceptable": True,
        "sequence_rank": 5,
    },
}

DECLARED_STATES = ("met", "not-met", "not-applicable")
EVIDENCE_SOURCES = ("measurement", "qualified-heritage", "analysis",
                    "declaration", "none")

TRIGGERING_STATES = ("not-met", "not-demonstrated")

BASE_SAMPLE_COUNT = 3
MAX_SAMPLE_COUNT = 10
LIMIT_REL_TOL = 1e-9


def _number(value, label, minimum=None, strict=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if strict and out <= minimum:
            raise ValueError("%s must be > %g, got %g" % (label, minimum, out))
        if not strict and out < minimum:
            raise ValueError("%s must be >= %g, got %g" % (label, minimum, out))
    return out


def _covered(severity, envelope):
    """True when the envelope reaches the severity, absorbing float error."""
    return severity <= envelope or math.isclose(
        severity, envelope, rel_tol=LIMIT_REL_TOL
    )


def normalize_provision_status(provision_id, status):
    """Validate one provision status row for one surface item."""
    if provision_id not in PROVISIONS:
        raise ValueError(
            "unknown provision %r (known: %s)"
            % (provision_id, ", ".join(sorted(PROVISIONS)))
        )
    if not isinstance(status, dict):
        raise ValueError(
            "provision %s: status must be a mapping, got %r" % (provision_id, status)
        )
    state = status.get("state")
    if state not in DECLARED_STATES:
        raise ValueError(
            "provision %s: state must be one of %s, got %r"
            % (provision_id, ", ".join(DECLARED_STATES), state)
        )
    if state == "met" and "source" not in status:
        raise ValueError(
            "provision %s: declared met without an evidence source" % provision_id
        )
    source = status.get("source", "none")
    if source not in EVIDENCE_SOURCES:
        raise ValueError(
            "provision %s: source must be one of %s, got %r"
            % (provision_id, ", ".join(EVIDENCE_SOURCES), source)
        )
    envelope = status.get("heritage_envelope_severity")
    if source == "qualified-heritage":
        if envelope is None:
            raise ValueError(
                "provision %s: heritage evidence needs "
                "heritage_envelope_severity" % provision_id
            )
        envelope = _number(
            envelope, "provision %s: heritage_envelope_severity" % provision_id, 0.0
        )
    elif envelope is not None:
        envelope = _number(
            envelope, "provision %s: heritage_envelope_severity" % provision_id, 0.0
        )
    waived = status.get("waived", False)
    if not isinstance(waived, bool):
        raise ValueError("provision %s: waived must be a boolean" % provision_id)
    justification = status.get("justification")
    if waived and (not isinstance(justification, str) or not justification.strip()):
        raise ValueError(
            "provision %s: a waiver needs a non-empty justification" % provision_id
        )
    return {
        "provision": provision_id,
        "state": state,
        "source": source,
        "heritage_envelope_severity": envelope,
        "waived": waived,
        "justification": justification,
    }


def normalize_surface_item(item):
    """Validate one external surface item and all of its provisions."""
    if not isinstance(item, dict):
        raise ValueError("surface item must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("surface item needs a non-empty string id")
    material = item.get("material")
    if not isinstance(material, str) or not material.strip():
        raise ValueError("item %s: material must be a non-empty string" % item_id)
    provisions = item.get("provisions")
    if not isinstance(provisions, dict) or not provisions:
        raise ValueError(
            "item %s: provisions must be a non-empty mapping" % item_id
        )
    rows = {}
    for provision_id, status in provisions.items():
        rows[provision_id] = normalize_provision_status(provision_id, status)
    return {"id": item_id, "material": material, "provisions": rows}


def build_surface_set(items):
    """Normalise every surface item; reject an empty set or a repeat id."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("surface-item set must be a non-empty list")
    out = []
    seen = set()
    for item in items:
        row = normalize_surface_item(item)
        if row["id"] in seen:
            raise ValueError("duplicate surface-item id %r" % row["id"])
        seen.add(row["id"])
        out.append(row)
    return out


def effective_provision_state(status, mission_severity):
    """Resolve a declared state against the evidence actually offered.

    A claim is only as good as its evidence: measured data carries any
    provision, an analytical demonstration carries only the provisions
    that permit one, heritage carries a provision only inside its
    qualified envelope, and a bare declaration carries nothing.
    """
    severity = _number(mission_severity, "mission_severity", 0.0)
    provision_id = status["provision"]
    entry = PROVISIONS[provision_id]
    if status["state"] == "not-applicable":
        return {"state": "not-applicable", "reason": "declared-not-applicable"}
    if status["state"] == "not-met":
        return {"state": "not-met", "reason": "declared-not-met"}
    source = status["source"]
    if source == "measurement":
        return {"state": "met", "reason": "measured-evidence"}
    if source == "analysis":
        if entry["analysis_acceptable"]:
            return {"state": "met", "reason": "analytical-demonstration"}
        return {
            "state": "not-demonstrated",
            "reason": "analysis-cannot-carry-a-material-provision",
        }
    if source == "qualified-heritage":
        if _covered(severity, status["heritage_envelope_severity"]):
            return {"state": "met", "reason": "heritage-envelope-covers-the-mission"}
        return {
            "state": "not-demonstrated",
            "reason": "heritage-envelope-shortfall",
        }
    return {"state": "not-demonstrated", "reason": "declaration-only-evidence"}


def provision_rows_for_item(item, mission_severity):
    """Resolved state, reason and trigger for every registry provision."""
    severity = _number(mission_severity, "mission_severity", 0.0)
    rows = []
    for provision_id in sorted(PROVISIONS):
        entry = PROVISIONS[provision_id]
        status = item["provisions"].get(provision_id)
        if status is None:
            resolved = {"state": "not-demonstrated", "reason": "no-status-on-record"}
            waived = False
        else:
            resolved = effective_provision_state(status, severity)
            waived = status["waived"]
        rows.append(
            {
                "item_id": item["id"],
                "provision": provision_id,
                "state": resolved["state"],
                "reason": resolved["reason"],
                "waived": waived,
                "sample_kind": entry["sample_kind"],
                "sequence_rank": entry["sequence_rank"],
                "triggered": resolved["state"] in TRIGGERING_STATES,
            }
        )
    return rows


def triggered_sample_kinds(rows):
    """Sample kinds demanded by the triggered provisions, in rank order."""
    triggered = [row for row in rows if row["triggered"]]
    triggered.sort(key=lambda row: (row["sequence_rank"], row["sample_kind"]))
    kinds = []
    for row in triggered:
        if row["sample_kind"] not in kinds:
            kinds.append(row["sample_kind"])
    return kinds


def sample_count_for_kind(sample_kind, material_count):
    """Sample count for one kind: a base set plus one per extra material."""
    known = {entry["sample_kind"] for entry in PROVISIONS.values()}
    if sample_kind not in known:
        raise ValueError(
            "unknown sample kind %r (known: %s)"
            % (sample_kind, ", ".join(sorted(known)))
        )
    if not isinstance(material_count, int) or isinstance(material_count, bool):
        raise ValueError("material_count must be an integer, got %r" % (material_count,))
    if material_count < 1:
        raise ValueError("material_count must be >= 1, got %d" % material_count)
    return min(BASE_SAMPLE_COUNT + material_count - 1, MAX_SAMPLE_COUNT)


def build_sample_campaign(surface_set, mission_severity):
    """Group every triggered surface into the campaign it demands."""
    severity = _number(mission_severity, "mission_severity", 0.0)
    campaign = {}
    for item in surface_set:
        rows = provision_rows_for_item(item, severity)
        for row in rows:
            if not row["triggered"]:
                continue
            entry = campaign.setdefault(
                row["sample_kind"],
                {
                    "sample_kind": row["sample_kind"],
                    "sequence_rank": row["sequence_rank"],
                    "item_ids": [],
                    "materials": [],
                    "provisions": [],
                },
            )
            if item["id"] not in entry["item_ids"]:
                entry["item_ids"].append(item["id"])
            if item["material"] not in entry["materials"]:
                entry["materials"].append(item["material"])
            if row["provision"] not in entry["provisions"]:
                entry["provisions"].append(row["provision"])
    for entry in campaign.values():
        entry["sample_count"] = sample_count_for_kind(
            entry["sample_kind"], len(entry["materials"])
        )
    return campaign


def campaign_sequence(campaign):
    """Sample kinds in the order the campaign runs them."""
    entries = sorted(
        campaign.values(), key=lambda e: (e["sequence_rank"], e["sample_kind"])
    )
    return [entry["sample_kind"] for entry in entries]


def assess_evidence(surface_set, mission_severity):
    """Findings on waivers, missing statuses and unsupported claims."""
    severity = _number(mission_severity, "mission_severity", 0.0)
    findings = []
    for item in surface_set:
        for row in provision_rows_for_item(item, severity):
            if row["waived"] and row["state"] != "not-applicable":
                findings.append(
                    {
                        "kind": "invalid-sample-waiver",
                        "item_id": item["id"],
                        "provision": row["provision"],
                        "detail": row["reason"],
                    }
                )
            if row["reason"] == "no-status-on-record":
                findings.append(
                    {
                        "kind": "provision-status-missing",
                        "item_id": item["id"],
                        "provision": row["provision"],
                        "detail": row["reason"],
                    }
                )
            elif row["reason"] == "heritage-envelope-shortfall":
                findings.append(
                    {
                        "kind": "heritage-envelope-shortfall",
                        "item_id": item["id"],
                        "provision": row["provision"],
                        "detail": row["reason"],
                    }
                )
            elif row["reason"] == "declaration-only-evidence":
                findings.append(
                    {
                        "kind": "unsupported-compliance-claim",
                        "item_id": item["id"],
                        "provision": row["provision"],
                        "detail": row["reason"],
                    }
                )
    return findings


def evaluate_charging_test_trigger(items, mission_severity):
    """Full clause 6.6.1 product: per-item triggers, campaign, findings."""
    surface_set = build_surface_set(items)
    severity = _number(mission_severity, "mission_severity", 0.0)
    item_rows = []
    for item in surface_set:
        rows = provision_rows_for_item(item, severity)
        kinds = triggered_sample_kinds(rows)
        item_rows.append(
            {
                "id": item["id"],
                "material": item["material"],
                "provisions": rows,
                "sample_kinds": kinds,
                "sample_required": bool(kinds),
            }
        )
    campaign = build_sample_campaign(surface_set, severity)
    findings = assess_evidence(surface_set, severity)
    return {
        "item_count": len(surface_set),
        "mission_severity": severity,
        "items": item_rows,
        "campaign": campaign,
        "campaign_sequence": campaign_sequence(campaign),
        "findings": findings,
        "sample_required": any(row["sample_required"] for row in item_rows),
        "provisions_met_without_sampling": not any(
            row["sample_required"] for row in item_rows
        ),
    }


def summarize_findings(report):
    """Count findings by kind for the trigger summary table."""
    if not isinstance(report, dict) or "findings" not in report:
        raise ValueError(
            "report must be the mapping returned by evaluate_charging_test_trigger"
        )
    counts = {}
    for finding in report["findings"]:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1
    return counts
