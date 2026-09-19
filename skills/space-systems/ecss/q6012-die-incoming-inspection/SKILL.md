---
name: q6012-die-incoming-inspection
description: "Determine what an arriving bare die batch is checked for at goods inwards and what happens to it, per ECSS-Q-ST-60-12C clause 10.3: validate the arrival record, reconcile ordered against packing list against counted quantity, derive the applicable checks with the severity each carries, compute the quantity outcome rather than accept it, and walk the disposition ladder from reject through quarantine and deviation to release. Refuses an incomplete inspection record and treats an unperformed check as unperformed. Use when a die delivery is on the goods inwards bench. Trigger: ecss, q-st-60-12c-clause-10-3, die-batch-goods-inwards-check, die-quantity-reconciliation, incoming-batch-quarantine-ladder, die-identity-lot-match, die-arrival-packaging-integrity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-12-die-incoming-inspection, q6012-die-incoming-inspection, die-batch-goods-inwards-check, die-quantity-reconciliation, incoming-batch-quarantine-ladder, die-identity-lot-match, die-arrival-packaging-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die Incoming Inspection (space-systems/ecss/q6012-die-incoming-inspection)

Use when a bare die batch has physically arrived and somebody at goods
inwards has to decide what happens to it. The batch is not production
material yet; it is material with a claim attached, and the checks here are
what turns the claim into a release, a quarantine or a rejection.

## Domain quick reference

- There are three independent quantities and they fail in two different ways.
  A count that disagrees with the packing list means something happened to
  the shipment; a packing list that agrees with the count but not with the
  order means the foundry shipped a different amount than was bought. Rolling
  them into one shortage number loses which of the two it is.
- The quantity check is arithmetic, so it is computed here rather than taken
  from the inspection report. Every other check is a judgement and comes from
  the inspector, but a check a machine can do is not left to an assertion.
- Severity is a property of the check, not of the mood of the day. Identity,
  documentation, packaging integrity and the visual sample are critical
  because a failure of any of them means the batch may not be the batch;
  quantity, seal condition and handling evidence are major; the map
  cross-check and the transit record are minor.
- An unperformed check is not a pass. It is reported at the severity of the
  check that was skipped and it moves the disposition exactly as a failure
  would, because the buyer has no more knowledge than if it had failed.
- The disposition ladder is worst-wins. One critical failure rejects a batch
  whose other twelve checks were clean, and the ladder is walked rather than
  scored so a pile of minor findings never adds up to a rejection.

## Workflow

1. Validate the arrival: whole-die quantities that cannot be negative, a real
   batch identity, and condition flags with no unknown key smuggled in.
2. Reconcile counted against packing list against ordered, naming the
   mismatch rather than reporting a single delta.
3. Derive the applicable checks from the arrival conditions — a batch that did
   not arrive sealed has no seal to read — keeping the reason and severity.
4. Refuse the inspection record if it is incomplete, reports a check that does
   not apply, or reports the check this module computes.
5. Assemble the outcome set, computing the quantity outcome and taking the
   rest from the inspector.
6. Report findings worst severity first and return the disposition: reject,
   quarantine, accept with deviation, or accept and release to production.

## Pitfalls

- Reporting one shortage figure. Short against the order and short against
  the packing list send the buyer to two different people; the single number
  sends them to neither.
- Letting the inspector tick the quantity box. It is the one check with an
  arithmetic answer, and a ticked box over an uncounted carrier is the most
  common way a short shipment reaches the line.
- Scoring the checks. A pass rate of ninety percent with the identity check
  among the failures is a batch that may not be the batch that was bought.
- Recording a skipped check as not applicable. Not applicable is a property
  of the arrival; skipped is a property of the inspection, and conflating
  them removes the check from the record entirely.
- Releasing a batch with a minor finding open. A deviation is a decision
  somebody has to take; accept-with-deviation is deliberately not the same
  answer as release to production.

## Behavior contract (gate 3)

The arrival validation, three-way quantity reconciliation, condition-driven
check applicability, refusal of an incomplete or over-complete inspection
record, the computed quantity outcome, unperformed-is-not-pass handling and
the worst-wins disposition ladder are exercised by the gate 3 contract test:
scripts/test_q6012_die_incoming_inspection.py against
scripts/q6012_die_incoming_inspection_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_die_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
