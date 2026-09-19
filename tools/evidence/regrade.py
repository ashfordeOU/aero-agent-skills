#!/usr/bin/env python3
"""Regrade: re-verdict stored evidence against a changed checker.

Nothing here opens the corpus.  The only inputs are the record on disk and
the checker set being applied, which is what makes a checker fix cost one
pass over a directory of JSON instead of a re-engagement with every customer
whose dossier was issued under the old rule.

A regrade never mutates the record it reads.  It issues a SUCCESSOR record
that carries the same observations, the new checker set, the new outcomes,
and a derivation block naming its parent by digest.  The original dossier
stays exactly as issued - which matters, because "we quietly re-decided the
verdict you were given" is not a thing a conformance mark can survive.

Three self-checks run as part of every regrade:

  * the parent's seal is verified before it is read.  A tampered record is
    not refreshed, it is refused.
  * a gate whose checker id, version, parameter digest AND observation digest
    are all unchanged must return the same verdict.  If it does not, the
    checker is not pure, and the regrade says so instead of publishing the
    new answer.
  * any gate that comes back INDETERMINATE is listed as needing
    re-observation, at the leaf level, so the work order is explicit.
"""

from . import canonical, checkers, record as record_module, schema

REPORT_KIND = "aero.evidence.regrade-report"
REPORT_VERSION = "1.0.0"


def _describe_change(key, old_value, new_value):
    """One readable line for one changed parameter.

    A list parameter is summarised by what entered and left it.  Printing
    both copies of a seventy-entry allowlist buries the one word that
    actually changed, and the cause of a flip is the whole point of the line.
    """
    if isinstance(old_value, list) and isinstance(new_value, list):
        old_set, new_set = set(map(repr, old_value)), set(map(repr, new_value))
        added = sorted(x.strip("'\"") for x in new_set - old_set)
        removed = sorted(x.strip("'\"") for x in old_set - new_set)
        parts = []
        if added:
            parts.append("+%d (%s)" % (len(added), ", ".join(added[:12])))
        if removed:
            parts.append("-%d (%s)" % (len(removed), ", ".join(removed[:12])))
        return "%s: %s" % (key, "; ".join(parts) or "reordered")
    return "%s: %r -> %r" % (key, old_value, new_value)


def _params_delta(before, after):
    if before is None:
        return ["checker was not in the issuing set"]
    changes = []
    if before["version"] != after["version"]:
        changes.append("checker %s -> %s" % (before["version"], after["version"]))
    old, new = before.get("params", {}), after.get("params", {})
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            changes.append(_describe_change(key, old.get(key), new.get(key)))
    return changes


def regrade(parent, checker_set, issuer="unattributed", at=None):
    """Re-decide one stored record.  Returns (successor_record, entry)."""
    errors = schema.validate(parent)
    if errors:
        raise ValueError(
            "refusing to regrade %s: %s" % (parent.get("record_id"), "; ".join(errors))
        )
    body = parent["body"]
    observations = body["observations"]
    prior_gates = {gate["gate"]: gate for gate in body["gates"]}
    prior_entries = {e["id"]: e for e in body["checker_set"]["checkers"]}
    new_entries = {e["id"]: e for e in checker_set["checkers"]}

    gates = checkers.apply_set(checker_set, observations)
    gate_changes = []
    anomalies = []

    for gate in gates:
        gate_id = gate["gate"]
        prior = prior_gates.get(gate_id)
        after = gate["outcome"]["verdict"]
        before = prior["outcome"]["verdict"] if prior else None
        delta = _params_delta(prior_entries.get(gate_id), new_entries[gate_id])
        if prior is None:
            change = "added"
        elif before != after:
            change = "flipped"
        else:
            change = "held"
        if prior is not None:
            gate["prior"] = {
                "verdict": before,
                "reason": prior["outcome"]["reason"],
                "checker_version": prior["checker_version"],
                "params_digest": prior["params_digest"],
            }
            identical = (
                prior["checker_version"] == gate["checker_version"]
                and prior["params_digest"] == gate["params_digest"]
                and prior["observation_digest"] == gate["observation_digest"]
            )
            if identical and before != after:
                anomalies.append(
                    "gate %s flipped %s -> %s with an identical checker version, "
                    "parameter digest and observation digest; a pure checker "
                    "cannot do that" % (gate_id, before, after)
                )
        gate_changes.append(
            {
                "gate": gate_id,
                "before": before,
                "after": after,
                "change": change,
                "cause": delta or ["no change to this checker"],
                "reason_after": gate["outcome"]["reason"],
            }
        )

    for gate_id, prior in sorted(prior_gates.items()):
        if gate_id in new_entries:
            continue
        gates.append(
            {
                "gate": gate_id,
                "checker_version": prior["checker_version"],
                "params_digest": prior["params_digest"],
                "observation": prior["observation"],
                "observation_digest": prior["observation_digest"],
                "outcome": {
                    "verdict": checkers.WITHDRAWN,
                    "reason": "retired from checker set '%s'" % checker_set["label"],
                    "findings": [],
                },
                "prior": {
                    "verdict": prior["outcome"]["verdict"],
                    "reason": prior["outcome"]["reason"],
                    "checker_version": prior["checker_version"],
                    "params_digest": prior["params_digest"],
                },
            }
        )
        gate_changes.append(
            {
                "gate": gate_id,
                "before": prior["outcome"]["verdict"],
                "after": checkers.WITHDRAWN,
                "change": "withdrawn",
                "cause": ["checker retired from the applied set"],
                "reason_after": "retired from checker set '%s'" % checker_set["label"],
            }
        )

    gates.sort(key=lambda g: g["gate"])
    verdict = checkers.roll_up(gates)
    needs_reobservation = sorted(
        {
            gate["gate"]
            for gate in gates
            if gate["outcome"]["verdict"] == checkers.INDETERMINATE
        }
    )

    successor_body = {
        "issued": {
            "at": record_module.now_iso(at),
            "by": issuer,
            "tool": "%s/%s" % (record_module.TOOL_ID, record_module.TOOL_VERSION),
        },
        "subject": body["subject"],
        "corpus": body["corpus"],
        "leaf": body["leaf"],
        "versions": body["versions"],
        "standards": body["standards"],
        # The environment block keeps describing the run that produced the
        # observations.  A regrade re-ran no float work, so replacing it with
        # the regrading host's facts would be a lie about what was measured.
        "environment": body["environment"],
        "checker_set": checker_set,
        "observations": observations,
        "gates": gates,
        "verdict": verdict,
        "derivation": {
            "kind": "regrade",
            "parent": {
                "record_id": parent["record_id"],
                "body_digest": parent["seal"]["body_digest"],
                "issued_at": body["issued"]["at"],
                "amendments_at_regrade": len(parent.get("amendments") or []),
            },
            "checker_set_before": {
                "label": body["checker_set"]["label"],
                "digest": body["checker_set"]["digest"],
            },
            "checker_set_after": {
                "label": checker_set["label"],
                "digest": checker_set["digest"],
            },
            "corpus_re_executed": False,
            "performed_with": {
                "tool": "%s/%s" % (record_module.TOOL_ID, record_module.TOOL_VERSION),
                "note": (
                    "no observation was re-taken, so no environment fingerprint "
                    "is claimed for this step"
                ),
            },
            "verdict_before": body["verdict"]["overall"],
            "gate_changes": gate_changes,
            "anomalies": anomalies,
            "reobservation_required": needs_reobservation,
        },
    }
    successor = record_module.seal(
        successor_body,
        telemetry={
            "note": "regrade executed no work; run telemetry lives on the parent",
            "parent_record_id": parent["record_id"],
        },
    )
    entry = {
        "record_id": successor["record_id"],
        "parent_record_id": parent["record_id"],
        "subject": body["subject"]["ref"],
        "verdict_before": body["verdict"]["overall"],
        "verdict_after": verdict["overall"],
        "verdict_changed": body["verdict"]["overall"] != verdict["overall"],
        "gates": gate_changes,
        "anomalies": anomalies,
        "reobservation_required": needs_reobservation,
    }
    return successor, entry


def regrade_many(records, checker_set, issuer="unattributed", at=None):
    """Regrade a batch.  Returns (successors, report)."""
    successors, entries = [], []
    for parent in records:
        successor, entry = regrade(parent, checker_set, issuer=issuer, at=at)
        successors.append(successor)
        entries.append(entry)
    before_labels = {
        (
            parent["body"]["checker_set"]["label"],
            parent["body"]["checker_set"]["digest"],
        )
        for parent in records
    }
    flipped_gates = sum(
        1 for e in entries for g in e["gates"] if g["change"] == "flipped"
    )
    report = {
        "kind": REPORT_KIND,
        "version": REPORT_VERSION,
        "at": record_module.now_iso(at),
        "by": issuer,
        "canonicalization": canonical.CANONICALIZATION,
        "checker_set_before": [
            {"label": label, "digest": digest} for label, digest in sorted(before_labels)
        ],
        "checker_set_after": {
            "label": checker_set["label"],
            "digest": checker_set["digest"],
        },
        "corpus_re_executed": False,
        "records": entries,
        "summary": {
            "records": len(entries),
            "verdict_changed": sum(1 for e in entries if e["verdict_changed"]),
            "verdict_held": sum(1 for e in entries if not e["verdict_changed"]),
            "gate_outcomes_flipped": flipped_gates,
            "gates_added": sum(
                1 for e in entries for g in e["gates"] if g["change"] == "added"
            ),
            "gates_withdrawn": sum(
                1 for e in entries for g in e["gates"] if g["change"] == "withdrawn"
            ),
            "records_needing_reobservation": sum(
                1 for e in entries if e["reobservation_required"]
            ),
            "anomalies": sum(len(e["anomalies"]) for e in entries),
        },
    }
    return successors, report
