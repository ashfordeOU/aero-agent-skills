---
name: q6005-approval-of-recurrent-circuits
description: "Evaluate whether a repeat order for a hybrid microcircuit may ride on an earlier approval under the reduced procedure of ECSS-Q-ST-60-05C clause 7.3.4, and state what the new lot still owes. Use when the same part is ordered again from the same house: confirm part number, manufacturer and production line have not moved, measure the continuity gap in whole months against the window, check the earlier lot stayed inside its allowable defective percentage and carries no open alert, then rank the declared changes, since paperwork keeps the reduced route, a process change re-opens the groups it touched, and a design change ends it. Trigger: ecss, q-st-60-05-hybrid-microcircuits, recurrent-hybrid-approval, repeat-order-reduced-procedure, production-continuity-window, process-change-requalification, lot-acceptance-carry-forward."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuits, recurrent-hybrid-approval, repeat-order-reduced-procedure, production-continuity-window, process-change-requalification, lot-acceptance-carry-forward]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Approval of Recurrent Circuits (space-systems/ecss/q6005-approval-of-recurrent-circuits)

Use when the task is the reduced approval procedure of ECSS-Q-ST-60-05C clause
7.3.4: a hybrid circuit already approved on an earlier order is ordered again,
and the question is how much of the approval programme the repeat build owes.

## Domain quick reference

- The reduced procedure is credit carried forward from one specific earlier
  approval, and that approval covers four things at once: a part number, a
  drawing issue, a manufacturer and a production line. If any of the four has
  moved, the repeat order is a different article and the credit does not
  transfer, however similar the drawing looks.
- Continuity is a condition, not a formality. The gap between the approved lot
  and the new order is counted in whole months against the continuity window.
  An idle line loses the process evidence the approval rested on: operators
  move, fixtures drift, materials are re-sourced, and none of that shows in
  the paperwork.
- Credit is only as sound as the lot that earned it. A previous lot whose
  defective percentage sat above its allowable never demonstrated a controlled
  process, and an open alert or nonconformance against the design withdraws
  the credit until it is closed.
- Declared changes are ranked, not merely listed. No change and a
  documentation-only change leave the reduced route intact. A process change
  keeps the route but re-opens exactly the test groups that process area
  touches -- a changed seal owes hermeticity and residual gas, a changed bond
  owes bond pull and operating life. A design change ends the route.
- A drawing issue that has advanced while every declared change is paperwork
  deserves a finding of its own. It does not block the order, but an issue
  that moved with nothing behind it usually means a change went undeclared.
- The output is a route plus an evidence set. The reduced route still owes a
  change declaration, a lot acceptance record and traceability; the partial
  route adds the re-opened groups on top.

## Workflow

1. Name the repeat order and the single earlier approval it rides on. Record
   the part number, drawing issue, manufacturer and line on both sides.
2. Record the approved lot date, its size, its defective count, the allowable
   defective percentage, the order date and any open alert.
3. Reject the order outright when a date is malformed, when the order predates
   the approval, when a lot count is not a whole number, or when a declared
   process change names no process area.
4. Compare the identity fields. Any of the part number, manufacturer or line
   moving is a blocking finding on its own.
5. Measure the continuity gap in whole months and compare it against the
   window; a gap exactly on the window is still inside it.
6. Recompute the previous lot's defective percentage and compare it against
   the allowable, absorbing representation error with a named tolerance
   rather than relaxing the limit.
7. Take the most disruptive declared change. Derive the re-opened test groups
   from the process areas only, then read off the route and build the evidence
   set from it.
8. Across an order book, count the routes, list the orders pushed back to a
   full approval with their reasons, and carry the union of re-opened groups
   as the work the campaign has to schedule.

## Pitfalls

- Reading "same part number" as "same article". The line and the manufacturer
  are part of what was approved, and both move more often than the drawing.
- Counting the continuity gap in calendar years, or rounding a part month up.
  A gap is whole months elapsed, and a day short of the month does not count.
- Carrying credit forward from a lot that failed its own acceptance. The
  earlier lot is the evidence; a lot above the allowable is evidence against.
- Letting a process change pass as documentation because the drawing did not
  change. The drawing is not the process, and the test groups re-open on the
  process.
- Treating the partial route as the reduced route with a note attached. It is
  a requalification limited in scope, and the re-opened groups are real work.
- Silently accepting an advanced drawing issue behind a paperwork-only change
  declaration. Raise it; an undeclared change is the usual explanation.

## Behavior contract (gate 3)

The identity comparison, continuity-gap arithmetic, lot acceptance carry
forward, change ranking, re-opened group derivation, route selection and
order-book roll-up are exercised by the gate 3 contract test:
scripts/test_q6005_approval_of_recurrent_circuits.py against
scripts/q6005_approval_of_recurrent_circuits_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6005_approval_of_recurrent_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
