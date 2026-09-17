---
name: q60-class-3-incoming-inspection
description: "Determine how deep the arrival examination of a Class 3 EEE delivery goes under ECSS-Q-ST-60C clause 6.3.7: set the depth from the supply chain the pieces came through, push it a step deeper when the seal or the static-protective bag arrived breached, size the draw in integer arithmetic from the pieces that survived transit, demand the traceability and authenticity evidence an unfranchised source owes, and group the defects found by severity so a cosmetic mark and a cracked body are not one tally. Use when a Class 3 goods-in bench has to become a bonded-store, conditional-release or quarantine disposition. Trigger: ecss, q-st-60c-clause-6-3-7, class-3-arrival-examination-depth, class-3-supply-chain-tier, class-3-authenticity-marking-permanency, class-3-arrival-defect-severity-tally, class-3-bonded-store-entry-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-3-incoming-inspection, class-3-arrival-examination-depth, class-3-supply-chain-tier, class-3-authenticity-marking-permanency, class-3-arrival-defect-severity-tally, class-3-bonded-store-entry-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Incoming Inspection (space-systems/ecss/q60-class-3-incoming-inspection)

Use when the task is the arrival examination of ECSS-Q-ST-60C clause 6.3.7 —
the checks performed when Class 3 parts reach the premises of the procuring
entity, and the decision about where the pieces go next.

## Domain quick reference

- Class 3 parts reach the door through very different chains, and the chain is
  what sets the depth of the examination. Bought from the manufacturer or its
  franchised distributor, the pieces arrive with an unbroken link behind them
  and earn a reduced look. Bought from an independent distributor or on the
  open market, they do not, and the extended examination is what closes the
  gap the paperwork leaves open.
- A broken shipping seal or an open static-protective bag is evidence **about
  the pieces**, not about the bag. It pushes the examination one step deeper,
  because whatever handled the bag also handled what was inside it.
- The draw is sized in **integer arithmetic** — integer square root of the
  surviving quantity plus one, scaled by the depth — so the same delivery gives
  the same draw on every platform rather than depending on how a square root
  rounded at the last bit.
- Defects are **grouped by severity** before anything is decided. A cosmetic
  mark and a cracked body carry different consequences, and a single tally
  either quarantines a delivery over scratches or lets a cracked body through
  on a generous allowance. A severity the project never declared is refused,
  because an ungraded defect belongs to no tally at all.
- The extended examination carries an acceptance number of **zero major
  defects**. That depth was reached over a doubt about the pieces themselves,
  and tolerating a major defect at that point would give the doubt nowhere to
  land.
- Marking permanency is part of what makes the examination extended. An
  extended examination reported without that result is incomplete evidence, so
  the missing result is refused rather than defaulted to a pass.
- Transit damage leaves the accepted count before anything is drawn. Sampling
  against the delivery note rather than the surviving pieces over-states the
  coverage of every number downstream.

## Workflow

1. Normalize the supply chain tier and read the base depth from it, refusing a
   chain the project never declared.
2. Take the packaging record, and escalate the depth one step when the seal or
   the bag arrived breached.
3. Reconcile the bench count against the note and take transit damage out of
   the accepted quantity.
4. Size the draw from the accepted quantity and the depth, and read the
   acceptance numbers for each severity off the draw.
5. Assemble the evidence the chain owes — the base pack, plus traceability and
   an authenticity report for an unfranchised source — and name every document
   that did not arrive.
6. Group the defects found on the draw by severity and compare each tally with
   its acceptance number.
7. Settle the disposition in precedence: quarantine on a critical or major
   overrun, a missing document, a failed marking permanency test or nothing
   undamaged left; conditional release on a minor overrun, unsound packaging, a
   count discrepancy or transit damage; otherwise bonded-store entry.

## Pitfalls

- Reading the chain off the purchase order value rather than the source. A
  cheap part from a franchised distributor and an expensive one from a broker
  carry opposite risks, and only the source tells you which is which.
- Recording a breached bag as a packaging remark. It is a reason to look harder
  at the pieces, and an examination that does not deepen has not used it.
- Drawing against the delivery note. Damaged pieces are not available to
  examine, so the note over-states what the draw actually covered.
- Pooling severities into one defect count. The tally then hides the one defect
  class that should have ended the delivery.
- Defaulting a missing marking permanency result to a pass. The test is part of
  the extended examination, and an unreported result is a gap, not a pass.
- Grading a defect at the bench because its severity is not in the register. A
  register gap is a refusal and a register update, not a field call.

## Behavior contract (gate 3)

The supply chain tier normalization, depth escalation on a breached seal or
bag, integer draw sizing, tier-dependent evidence pack, severity grouping
against the acceptance numbers and the disposition precedence are exercised by
the gate 3 contract test: scripts/test_q60_class_3_incoming_inspection.py
against scripts/q60_class_3_incoming_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
