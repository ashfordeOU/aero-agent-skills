---
name: q6012-design-for-testability
description: "Assess whether an MMIC die carries the measurement access its acceptance flow needs. Use when a design has to be shown testable before tape-out, per ECSS-Q-ST-60-12C clause 7.2.7: map every parameter that will be characterised or screened onto the access the layout actually provides, check each probe pad against the probe card pitch and minimum landing area, categorize a parameter with no reachable access as assembly-level or unobservable, spend the touchdown budget and the die area the test structures cost, then return the on-wafer coverage fraction and the access a screening-critical parameter still lacks. Trigger: ecss, q-st-60-12-mmic-scope, mmic-design-for-testability, on-wafer-probe-access, probe-pad-pitch-compatibility, screening-parameter-coverage, process-control-monitor-structure, test-pad-area-overhead, probe-touchdown-budget."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-design-for-testability, mmic-design-for-testability, on-wafer-probe-access, probe-pad-pitch-compatibility, screening-parameter-coverage, process-control-monitor-structure, test-pad-area-overhead, probe-touchdown-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Die -- Design for Testability (space-systems/ecss/q6012-design-for-testability)

Use when the task is the testability provision of ECSS-Q-ST-60-12C clause
7.2.7: a monolithic microwave integrated circuit has an acceptance flow
that will have to measure a list of parameters, and the question is
whether the layout gives that flow anywhere to put a probe -- before the
mask set is committed, because after tape-out the answer cannot change.

## Domain quick reference

- A die is a sealed piece of semiconductor. Every internal node that
  was not deliberately brought out to a landing feature is gone the
  moment the part is mounted and lidded, so testability is a layout
  decision taken at design time, not a test-engineering decision taken
  later.
- Access kinds differ in where in the flow they can be used. A
  ground-signal-ground landing set, a bias pad, a sense route that reads
  a node without loading the working path, and a drop-in monitor
  structure in the scribe lane are all reachable while the die is still
  on the wafer. A feature that only works once the die sits in a carrier
  is not, and it is useless to any screen that has to run before
  assembly.
- Parameters split by role, and the split decides what counts as a gap.
  A screening-critical parameter grades every delivered die, so it has
  to be measurable at wafer or die level. A characterisation-only
  parameter describes the design from a sample, so assembly-level access
  is enough for it. A screening-critical parameter that only comes back
  after assembly is a gap even though it is measurable somewhere.
- A pad that exists is not a pad that can be probed. The landing
  geometry has to match the card: the pad pitch has to sit inside the
  card's pitch tolerance, and the pad's short side has to cover the tip
  diameter plus the alignment tolerance on both sides, or the tip
  overhangs and the contact is unrepeatable.
- Access is not free. Probe pads take die area that the circuit wanted,
  and each landing leaves a probe mark, so a pad is rated for a finite
  number of touchdowns that the screen plus its retest allowance has to
  fit inside.
- The output is a verdict with three levels, not a score. No access at
  all for a screening-critical parameter, or a pad the card cannot land
  on, is inadequate. An assembly-only screening parameter, an
  unobservable characterisation parameter, or an overspent area or
  touchdown budget is conditional. Everything reachable on wafer inside
  both budgets is adequate.

## Workflow

1. List every parameter the acceptance flow will measure and give each
   one a role and the access kind it needs. Reject an uncategorized role
   rather than defaulting it, because the role is what decides whether a
   missing access is a gap or a note.
2. List the access features the layout provides, with landing geometry
   on every probe pad. Reject a pad with no pitch, no size or a
   fractional count.
3. Resolve each parameter to on-wafer, assembly-level or unobservable
   against the access kinds actually present, allowing an assembly
   fallback only where the parameter declares one.
4. Check every probe pad against the probe card: pitch inside tolerance,
   short side at or above the minimum landing area. A design with pads
   and no declared card has not demonstrated anything.
5. Total the pad area against the die and the planned touchdowns against
   the pad rating, including the retest allowance the flow will really
   spend.
6. Group the results, name every screening-critical gap, and close with
   the three-level verdict and the on-wafer coverage fraction.

## Pitfalls

- Counting a parameter as covered because it is measurable somewhere. A
  screening-critical parameter reachable only in a carrier cannot grade
  a die before assembly, so the screen either moves downstream at much
  higher cost or does not happen.
- Adding probe pads late to a finished layout. The area they need comes
  out of the circuit, and the routing to reach an internal node changes
  the node, so a sense tap added after the design is frozen either
  loads the working path or does not reach it.
- Matching the pad pitch and stopping there. A pad on the right pitch
  that is smaller than the tip plus twice the alignment tolerance still
  cannot be landed on repeatably, and the contact resistance that
  results looks like a device problem.
- Budgeting one touchdown per pad per test step. Retests, alignment
  passes and the second insertion after a bin-out all land on the same
  pad, and the probe-mark rating is spent long before the flow expects.
- Treating a scribe-lane monitor structure as a substitute for
  measuring the die. It carries the foundry device parameters for the
  wafer, which is exactly the right evidence for a process question and
  no evidence at all for a circuit-level specification on one die.
- Grading the pad area fraction by bare arithmetic. The fraction is a
  ratio of two sums of products, so a layout sitting exactly on its
  budget can land a few units in the last place above it; the
  comparison absorbs that representation error while the budget stays
  untouched.

## Behavior contract (gate 3)

The access-point validation, probe landing check, parameter
observability resolution, coverage grouping, touchdown budget, pad-area
overhead and three-level verdict are exercised by the gate 3 contract
test: scripts/test_q6012_design_for_testability.py against
scripts/q6012_design_for_testability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_design_for_testability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
