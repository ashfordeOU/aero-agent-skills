---
name: q2007-process-design
description: "Design the test process a centre will actually run, under ECSS-Q-ST-20-07C clause 5.7.3: turn a request into TSPE-level content by fixing each controlled parameter's nominal and tolerance band, checking the measurement uncertainty is small enough against that band to decide conformance, guard-banding the acceptance limits by that uncertainty, confirming every controlled parameter has an instrument whose range brackets it, and ordering the load steps with dwells and ramp rates the facility can hold. Use when a test procedure, set-up definition or acceptance criterion is being written or reviewed before the run. Trigger: ecss, q-st-20-07c-clause-5-7-3, test-specification-procedure-design, test-parameter-tolerance-band, test-accuracy-ratio, acceptance-limit-guard-band, test-load-step-ramp-rate."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-process-design, test-specification-procedure-design, test-parameter-tolerance-band, test-accuracy-ratio, acceptance-limit-guard-band, test-load-step-ramp-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Design of the Test Process (space-systems/ecss/q2007-process-design)

Use when the task is the design-and-development clause of
ECSS-Q-ST-20-07C clause 5.7.3 -- converting an accepted request into the
procedure, set-up, loads, tolerances and acceptance criteria that the
run will be held to, at the level of detail a test specification and
procedure carries.

## Domain quick reference

- A parameter without a tolerance band is not a designed parameter. The
  nominal says what is aimed at; the band says what still counts as the
  test having been performed, and only the band makes a deviation
  reportable rather than arguable after the fact.
- Uncertainty has to be small against the band before conformance can be
  decided. The ratio of the band's half-width to the measurement
  uncertainty is the usable figure: at a ratio near one the instrument
  cannot tell an in-band reading from an out-of-band one, so the design
  either buys a better instrument or widens a band the customer has to
  agree to.
- Guard-banding moves the decision limits inward, not the requirement.
  Accepting only inside nominal plus or minus the band less the
  uncertainty keeps a false accept off the report; the requirement the
  customer wrote is untouched, and the shrunken limits belong in the
  procedure so the operator sees them.
- Every controlled parameter needs an instrument whose range brackets
  the whole band, not just the nominal. A channel that saturates at the
  top of the band records a clipped value exactly when the run is
  closest to failing.
- Load steps are a sequence, not a set. Levels that do not advance leave
  the specimen twice at the same condition with no reason recorded, and
  a ramp between steps that outruns what the facility can hold turns a
  designed step into an overshoot the specimen sees but the plan never
  described.
- Dwell time at each step is what makes the step mean something. A level
  reached and immediately left has not been applied in any sense the
  acceptance criterion can use.

## Workflow

1. Validate each controlled parameter: finite nominal, strictly positive
   tolerance half-width, non-negative measurement uncertainty, and an
   instrument range whose upper bound genuinely exceeds its lower.
2. Compute the test accuracy ratio per parameter and compare it against
   the minimum the design is held to, absorbing float representation
   error at the bound with a named tolerance.
3. Derive the guard-banded acceptance limits from nominal, band and
   uncertainty, and refuse a guard band that has eaten the whole band --
   that is an instrument decision, not an acceptance criterion.
4. Confirm the instrument range brackets nominal plus and minus the full
   band for every controlled parameter.
5. Validate the load steps: at least the declared minimum count, dwell
   and transition times strictly positive, and levels advancing step to
   step.
6. Compute each transition's ramp rate and compare it with the rate the
   facility can hold.
7. Aggregate into findings and return an approved-or-rework verdict with
   the per-parameter table the procedure is written from.

## Pitfalls

- Copying the customer's tolerance into the procedure and stopping
  there. The procedure has to say what the operator accepts, which is
  the guard-banded limit, and those differ by the uncertainty.
- Sizing the instrument on the nominal. The band, not the nominal, sets
  the range the channel has to cover without clipping.
- Reading a high test accuracy ratio as permission to skip the guard
  band. A comfortable ratio makes the guard band narrow; it does not
  make it zero, and writing it down costs nothing.
- Letting two consecutive load steps sit at the same level. Either the
  second step has a purpose the level does not express, or it is a
  duplicate that inflates the run time and the specimen's exposure.
- Specifying a ramp the facility cannot hold and calling the overshoot a
  transient. The specimen sees the overshoot, and nothing in the record
  says what it was exposed to.

## Behavior contract (gate 3)

The parameter validation, test accuracy ratio, guard-banded limits,
instrument range coverage, load-step sequence validation, ramp-rate
comparison and the approved-or-rework verdict are exercised by the gate
3 contract test: scripts/test_q2007_process_design.py against
scripts/q2007_process_design_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_process_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
