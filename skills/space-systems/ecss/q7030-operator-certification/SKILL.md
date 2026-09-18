---
name: q7030-operator-certification
description: "Validate that a wrapping operator is certified for the job in hand under ECSS-Q-ST-70-30C personnel rules. Use when an assignment or a certification file is reviewed: treat every wire-gauge and terminal-type pair as its own endorsement, weigh the theory result and the accepted practical wraps behind it, hold the certification period and the vision check in date, suspend an endorsement whose combination has gone unworked past its continuity window, and return the status of each endorsement with a permitted or refused verdict for the assignment. Trigger: ecss, q-st-70-30c, wire-wrap-operator-endorsement, wire-wrap-gauge-terminal-combination, wire-wrap-practical-demonstration, wire-wrap-continuity-lapse, wire-wrap-certification-validity, wire-wrap-operator-vision-check."
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
  tags: [ecss, q-st-70-30c, q7030-operator-certification, wire-wrap-operator-endorsement, wire-wrap-gauge-terminal-combination, wire-wrap-practical-demonstration, wire-wrap-continuity-lapse, wire-wrap-certification-validity, wire-wrap-operator-vision-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Operator Certification (space-systems/ecss/q7030-operator-certification)

Use when the task is the certification of wrapping operators under
ECSS-Q-ST-70-30C -- establishing what each operator is actually
endorsed to wrap, whether those endorsements are still live today, and
whether a particular assignment may go ahead.

## Domain quick reference

- A wrapping certification is granted per combination, not per person.
  The demonstrated skill is a hand set for one conductor gauge on one
  terminal geometry; move either variable and the tension, the tool
  bit and the feel of a correct wrap all change, so the endorsement
  does not travel with the operator to the new combination.
- The evidence behind an endorsement has two halves that fail
  differently. The theory result shows the operator knows what a
  defect is; the practical demonstration -- enough wraps visually
  accepted and enough of them surviving the pull test -- shows the
  hand can produce one. A file strong in one and thin in the other is
  not qualified.
- Three clocks run at once and they are not interchangeable. The
  certification period runs from the examination or the last
  requalification; the vision check runs on its own cycle and belongs
  to the operator rather than to any endorsement; the continuity
  window runs from the last production work on that specific
  combination.
- Expiry and suspension are different answers. An elapsed
  certification period means the qualification itself has run out and
  is re-examined; an elapsed continuity window means the qualification
  stands but the currency has gone, and a fresh demonstration on the
  combination restores it.
- The vision check is operator-level, so it suspends every live
  endorsement at once rather than any one of them. An operator who
  cannot resolve a lifted turn cannot inspect their own work on any
  combination.
- The operational question is narrow and dated: may this operator wrap
  this gauge on this terminal type today. Everything above exists to
  answer it with a reason attached.

## Workflow

1. Read the operator file: the identity, the vision check date, and one
   endorsement record per gauge and terminal-type combination. Refuse a
   file with two records for the same combination rather than merging
   them.
2. Grade the evidence behind each endorsement against the theory pass
   mark, the accepted-wrap count and the passed pull-test count. Any
   shortfall makes the endorsement not qualified, whatever its dates
   say.
3. Age the certification period from the examination date and expire
   the endorsement past it.
4. Age the continuity window from the last production date on that
   combination and suspend the endorsement past it.
5. Age the vision check at operator level, and suspend every otherwise
   current endorsement while it is out of date.
6. Answer the assignment question for one combination on one date,
   returning the endorsement status, the findings behind it, and a
   permitted or refused verdict. A combination with no record at all is
   refused for absence of an endorsement, not for a lapse.

## Pitfalls

- Certifying the operator rather than the combination. A file that
  reads "certified for wire wrapping" cannot answer whether the fine
  gauge in front of the operator was ever demonstrated, and that is the
  only question the assignment asks.
- Treating a lapsed continuity window as an expiry. Re-examining an
  operator who simply has not worked that combination for six months
  costs the qualification scheme its credibility and buys nothing; the
  answer is a demonstration on the combination.
- Letting the vision check ride on the certification date. They are
  separate clocks, and an operator whose certification is fresh can
  still be working past a lapsed vision check.
- Counting practical wraps without counting the pull tests behind them.
  Wraps accepted visually and wraps that survived a pull are different
  evidence, and a demonstration that never went to the pull tester
  shows only that the wrap looks right.
- Answering the assignment question without a date. Every status here
  is a function of elapsed days, so a verdict with no assessment date
  is undefined rather than conservative.

## Behavior contract (gate 3)

The combination key, the evidence thresholds, the certification,
continuity and vision clocks, the expired-versus-suspended distinction
and the dated assignment verdict are exercised by the gate 3 contract
test: scripts/test_q7030_operator_certification.py against
scripts/q7030_operator_certification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7030_operator_certification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
