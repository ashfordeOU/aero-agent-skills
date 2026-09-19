---
name: q7054-cleaning-process-execution
description: "Execute an ultracleaning process to ECSS-Q-ST-70-54C and prove the sequence closes: order the steps so coarse removal precedes precision work and a rinse follows every chemical step, size the rinse cascade from the carryover fraction so the retained liquor reaches its target concentration, confirm the drying method reaches the geometry and clears the volatility of the fluid present, and refuse a wet part to inspection or to a bag. Use when running or reviewing a precision cleaning sequence on flight hardware. Trigger: ecss, q-st-70-54c, ultracleaning-process-execution, rinse-cascade-sizing, rinse-carryover-fraction, ultracleaning-drying-adequacy, cleaning-step-ordering."
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
  tags: [ecss, q-st-70-54c-ultracleaning-of-flight-hardware, q-st-70-54c, q7054-cleaning-process-execution, rinse-cascade-sizing, rinse-carryover-fraction, ultracleaning-drying-adequacy, cleaning-step-ordering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Ultracleaning — Cleaning Process Execution (space-systems/ecss/q7054-cleaning-process-execution)

Use when the task is the process clause of ECSS-Q-ST-70-54C: running the
chosen method as an ordered sequence of steps, and showing that the sequence
as written actually reaches the state the plan claims.

## Domain quick reference

- Three things decide the outcome: the order of the steps, the size of the
  rinse cascade, and whether the drying reaches the fluid. A qualified method
  executed in the wrong order delivers a part no cleaner than it started.
- Coarse before precision, never the reverse. Gross precleaning removes bulk
  soil that would overwhelm a precision bath; running it after a chemical step
  puts the contamination back on a surface that had already been cleaned, and
  the record still shows both steps completed.
- A rinse dilutes, it does not remove. The part carries a fraction of each
  bath's liquor into the next stage, so the retained concentration falls
  geometrically with the number of stages and the whole cascade is fixed by
  that carryover fraction, the starting concentration and the target.
- The stage count is computed, not chosen. Three rinses is a habit; the number
  that reaches the target from a given carryover is arithmetic, and the same
  cascade that is generous at one carryover is short by two stages at another.
- The stage count is also a quotient of logarithms, so a cascade that lands
  exactly on its target can compute a hair either side of a whole number. The
  near-integer is snapped before the ceiling is taken, or an exact four-stage
  cascade silently becomes five on one machine and four on another.
- Drying is a transport problem twice over. The method has to reach the
  geometry — ambient evaporation does nothing inside a blind hole — and it has
  to handle the volatility of the fluid actually present, because a gentle
  purge takes the surface film and leaves the rest.
- Nothing wet is inspected or bagged. A wet surface cannot be graded for
  particles or residue, and a bag closed over solvent traps it against the
  hardware for the whole of storage and transport.

## Workflow

1. Validate the ordered step list. Reject an unknown step type rather than
   passing it through as an unrecognised operation.
2. Run the ordering rules in sequence order: the sequence opens with coarse or
   chemical work, gross precleaning never follows a chemical step, every
   chemical step has a rinse behind it before anything dries it on, and
   packaging closes the sequence exactly once.
3. Track wetness through the sequence rather than by step name. A step is wet
   until a drying step clears it, and inspection or packaging reached while
   wet is a finding wherever in the list it sits.
4. Size the cascade: from the starting retained concentration, the target and
   the carryover fraction, compute the stages required, snapping a near
   integer before taking the ceiling.
5. Count the rinse stages the written sequence actually provides and compare.
   Fewer than required is a finding that names both numbers and the carryover
   they were computed at.
6. Compute the residual the written sequence achieves and grade it against the
   target, treating an exact landing on the target as met.
7. Check the drying method against the geometry and the fluid volatility, and
   close with one verdict: the process closes with no finding open, or it
   stays open with every finding named.

## Pitfalls

- Counting rinses instead of computing them. The number of stages that reaches
  a target depends on the carryover fraction, so a standard three-rinse recipe
  is right for one bath geometry and short for the next.
- Reading a rinse as removal. If a rinse removed the liquor, one would be
  enough; the cascade exists precisely because each stage only dilutes, and
  that is why the residual is a geometric series and not a subtraction.
- Taking the ceiling of a raw logarithm quotient. An exact cascade computes to
  a value indistinguishable from a whole number, and taking the ceiling of it
  adds a stage on some platforms and not others, so the recipe stops being
  reproducible.
- Choosing a drying method by throughput. The fastest method that fits the
  schedule is irrelevant if it cannot reach inside the geometry; the fluid
  left in a blind hole comes out later, on orbit, onto something that minds.
- Inspecting before drying to save a cycle. A wet surface hides the particles
  and dissolves the residue the inspection exists to find, so the measurement
  is not merely early, it is wrong in the optimistic direction.
- Treating a well-ordered sequence as a clean part. Order and cascade size are
  separate failures; a faultless sequence with two rinses too few delivers
  hardware that looks fully processed and is not clean.

## Behavior contract (gate 3)

The sequence validation, ordering rules, wetness tracking, carryover fraction
bounds, cascade sizing with the integer snap, achieved residual comparison,
drying reach and volatility check and the combined verdict are exercised by
the gate 3 contract test:
scripts/test_q7054_cleaning_process_execution.py against
scripts/q7054_cleaning_process_execution_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7054_cleaning_process_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
