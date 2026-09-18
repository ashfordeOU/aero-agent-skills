---
name: e2020-memory-cell-upset-tolerance
description: "Assess whether an upset in a limiter's retrigger or status memory cells can cost the load its power, under ECSS-E-ST-20-20C clause 5.2.18.2.1. Use when a design has to show that a flipped bit stays inside the housekeeping: group each cell by what its flip actually does to the output, refuse a coverage figure claimed for a mechanism that only detects, compute the residual upset rate every load-losing cell still carries after mitigation, project it across the mission duration, and name the cell that dominates the total. Trigger: ecss, e-st-20-20c-clause-5-2-18-2-1, retrigger-memory-cell-upset-tolerance, limiter-status-cell-upset-effect, single-event-upset-load-retention, memory-cell-upset-residual-rate, limiter-memory-cell-mitigation-coverage."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-18-2-1, e2020-memory-cell-upset-tolerance, retrigger-memory-cell-upset-tolerance, limiter-status-cell-upset-effect, single-event-upset-load-retention, memory-cell-upset-residual-rate, limiter-memory-cell-mitigation-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Limiters -- Memory Cell Upset Tolerance (space-systems/ecss/e2020-memory-cell-upset-tolerance)

Use when the task is the clause 5.2.18.2.1 question of ECSS-E-ST-20-20C:
a retriggerable limiter holds a little state -- whether retrigger is
armed, what the limiter is currently reporting -- and an upset in that
state must not take away the power the load already has.

## Domain quick reference

- The effect of an upset is a property of the design, not of the cell. A
  flip read as an open command costs the load immediately; a flip that
  disarms retrigger costs it at the next disturbance; a flip that only
  mis-reports costs nothing until somebody believes the reading. The
  population is grouped by that effect before anything is counted.
- The retrigger-disarm case is the one that hides. Nothing happens when
  the bit flips, the telemetry looks normal, and the loss arrives later
  under a transient the limiter should have ridden through. A review
  looking only for an immediate output change will not see it.
- A mitigation has to be able to do what is claimed for it. Parity that
  raises a flag has detected an upset, not repaired it, and a coverage
  of one claimed for detection alone is refused rather than carried into
  a rate.
- Coverage from periodic scrubbing is conditional. It holds while the
  scrub runs and while its interval stays shorter than the spacing
  between upsets, and both of those are operational facts rather than
  design properties.
- A rate needs a duration before it means anything. The same cell is
  tolerable across six months and not across fifteen years, and the
  mission projection is where that difference becomes visible.
- The dominant cell is worth naming even when the total passes. A total
  built from one weak cell is one change away from being comfortable; a
  total spread evenly across a dozen is not.
- Command latches and housekeeping counters sit outside this clause.
  They are grouped so the denominators are honest, not so they are
  judged here.

## Workflow

1. Validate the upset policy first: the mitigation coverage the project
   demands of a load-losing cell, the load-loss events it allows across
   the mission, the mission duration itself, and the share at which one
   cell dominating the total earns an advisory. A coverage floor above
   one, or a dominance advisory of zero, is refused rather than used.
2. Validate every cell record: identifier, the function it holds, what
   an upset of it does to the output, the upset rate, the mitigation and
   its coverage. A coverage claimed with no mechanism behind it, and
   full coverage claimed for a detect-only mechanism, are both refused
   before any arithmetic starts.
3. Group the population into the cells this clause speaks about --
   retrigger and status -- and the rest, and close on population not
   established when nothing in the record holds either.
4. Name the in-scope cells whose upset reaches the powered load, whether
   it opens the switch now or disarms the recovery for later.
5. Compare each of those against the coverage floor and report all that
   fall short, not the first.
6. Compute the residual rate each load-losing cell still carries, sum
   it, project it over the mission, and find the cell holding the
   largest share, breaking a tie on the identifier so the result is
   reproducible.
7. Close on one verdict: population not established, an unmitigated
   load-loss path, a residual rate over the allowance, or upset
   tolerance demonstrated -- with the projection, the dominant cell and
   any advisory beside it.

## Pitfalls

- Reading tolerance as "the cell is protected". The question is what the
  load does when the cell flips anyway, and a protected cell with a
  load-losing effect still needs its residual counted.
- Treating a status cell as harmless by definition. It is harmless to
  the load directly, and the risk moves to whatever acts on the reading,
  which is a real path with a different owner.
- Accepting full coverage from detection. A flag is not a repair, and a
  coverage of one behind a parity bit is the single most common way this
  assessment comes out green for free.
- Comparing rates without a duration. Upsets per day and a mission in
  years are different units of worry, and only the projection puts them
  on the same page.
- Reporting a total without its shape. One cell at ninety percent of the
  residual and twelve cells sharing it evenly are different problems
  with the same number on the front.
- Widening the assessment to every latch on the die. Command latches are
  covered elsewhere, and dragging them in here makes the findings that
  do belong easier to dismiss.

## Behavior contract (gate 3)

The policy validation, cell-record validation including both refused
coverage claims, the scope grouping, the load-losing determination, the
coverage floor comparison, the residual rate, the mission projection,
the dominant-cell selection and the advisories are exercised by the gate
3 contract test:
scripts/test_e2020_memory_cell_upset_tolerance.py against
scripts/e2020_memory_cell_upset_tolerance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_memory_cell_upset_tolerance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
