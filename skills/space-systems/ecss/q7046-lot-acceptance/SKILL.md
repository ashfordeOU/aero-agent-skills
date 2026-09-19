---
name: q7046-lot-acceptance
description: "Determine the acceptance sampling plan a procured fastener lot owes and judge the lot against it. Use when a manufacturing lot has arrived and someone must say how many parts are drawn, how many defectives that draw may carry, and what the supplier's recent record does to the next lot: inspect a critical lot whole because no sample stands for the parts it never touched, take the general-level-two code letter for the lot size, step up when that sample cannot discriminate at the quality limit asked for, collapse to whole-lot inspection when the sample reaches the lot, then carry severity forward so repeated rejects tighten and a clean run relaxes. Trigger: ecss, q-st-70-46-fasteners, fastener-lot-acceptance-sampling, fastener-aql-code-letter, fastener-criticality-quality-limit, fastener-inspection-severity-switching."
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
  tags: [ecss, q-st-70-46-fasteners, q7046-lot-acceptance, fastener-lot-acceptance-sampling, fastener-aql-code-letter, fastener-criticality-quality-limit, fastener-inspection-severity-switching]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Lot Acceptance (space-systems/ecss/q7046-lot-acceptance)

Use when the task is the acceptance clause of ECSS-Q-ST-70-46: settling
how much of a procured fastener lot is inspected, how many defectives
the draw may carry, and what the supplier's recent record does to the
plan applied to the next lot.

## Domain quick reference

- Acceptance runs per manufacturing lot, not per delivery and not per
  purchase order. A lot is the parts made from one heat on one machine
  setting, so it is the smallest unit whose result actually transfers
  between parts.
- A critical fastener is inspected whole. Sampling asserts that the
  parts not drawn resemble the parts drawn, and that assertion is
  exactly what cannot be made where losing one fastener loses the
  function.
- The sample comes from the code letter for the lot size, not from a
  percentage. A flat percentage over-samples a small lot into
  uselessness and under-samples a large one at the same time.
- The acceptance number comes from the quality limit and the sample
  together. Where the letter's sample is too small to discriminate at
  the quality limit asked for, the plan steps up to the next larger
  sample; accepting on the small one would be accepting on a draw that
  could not have found the defect rate under discussion.
- A sample that reaches or passes the lot is whole-lot inspection, and
  the acceptance number collapses to zero with it. There is no residue
  left for a sample to stand for.
- Severity belongs to the supplier, not to the lot. Repeated rejects
  tighten the limit applied to the next lot, a run of clean lots
  relaxes it, and a tightened supplier that does not recover has
  inspection suspended rather than continued indefinitely.
- Suspension does not lift itself on a good lot. It lifts on a process
  review, which is a different event from a delivery.

## Workflow

1. Take the criticality. A critical fastener goes to whole-lot
   inspection with a zero acceptance number and the plan is finished.
2. For the rest, take the supplier's current severity, or the default
   entry severity for that criticality, and move the quality limit one
   step finer for tightened or one coarser for reduced.
3. Read the sample size code letter from the lot size at general
   inspection level two, and take the sample the letter calls for.
4. Look up the acceptance number at that sample and quality limit. If
   the sample cannot discriminate there, step to the next larger sample
   and record that the plan stepped up, so the sample on the paperwork
   is explained.
5. If the resolved sample reaches the lot, report whole-lot inspection
   with a zero acceptance number rather than a sample larger than the
   population it came from.
6. Judge the defectives found against the acceptance number, refusing a
   count larger than the sample itself, then carry severity forward from
   the trailing window of the supplier's dispositions.

## Pitfalls

- Sampling a critical lot because the lot is large and whole-lot
  inspection is expensive. The cost argument is real and it is not an
  acceptance argument; the parts not drawn are the ones that fly.
- Drawing a flat percentage of every lot. The discriminating power of a
  sample grows with its absolute size, not with its ratio to the lot, so
  a percentage plan is tightest exactly where it matters least.
- Accepting on a sample the quality limit cannot be read at. A sample of
  eight has no acceptance number at a tight quality limit because it
  could not have detected that rate, and defaulting it to zero
  defectives is a different plan with a different producer's risk.
- Reading severity off the lot in hand. Severity is the supplier's
  running record; resetting it per delivery discards the only signal
  that a process is drifting.
- Letting one clean delivery lift a suspension. Suspension is closed by
  a process review, and a single accepted lot from a suspended supplier
  is the weakest possible evidence that anything changed.
- Recording a sample larger than the lot. It happens whenever the step-up
  runs past a small lot, and it makes the acceptance record
  self-contradicting; the plan collapses to whole-lot inspection instead.

## Behavior contract (gate 3)

The code letter bands, the letter sample sizes, the quality limit by
criticality and severity, the step-up when a sample cannot discriminate,
the collapse to whole-lot inspection, the lot disposition and the
severity switching rules are exercised by the gate 3 contract test:
scripts/test_q7046_lot_acceptance.py against
scripts/q7046_lot_acceptance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_lot_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
