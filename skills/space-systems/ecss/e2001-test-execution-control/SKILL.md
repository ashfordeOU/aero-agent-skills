---
name: e2001-test-execution-control
description: "Use when execute a multipactor-test under the detailed written procedure ECSS-E-ST-20-01C clause 8.1 demands, and grade the run it produced: confirm the procedure carries every content element the clause expects, validate the declared step order against the precedence the setup imposes (path-calibration and detection-baseline before any radio-frequency-power reaches the item, venting only after power-down), size the power-step schedule for monotonic level progression, dwell length and arrival at the level the test-margin sets, and categorize every step skipped or run out of order as covered by an authorised deviation or as uncontrolled. Trigger: ecss, e-st-20-01c, test-execution-control, multipactor-test-procedure, step-precedence-check, power-step-schedule, deviation-authorisation, execution-log-grading."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-test-execution-control, test-execution-control, multipactor-test-procedure, step-precedence-check, power-step-schedule, deviation-authorisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Test Execution Control (space-systems/ecss/e2001-test-execution-control)

Use when the task is the execution-control duty of ECSS-E-ST-20-01C
clause 8.1 -- running a multipactor-test from a written detailed
procedure rather than from operator judgement, and showing afterwards
that the run followed it or that every departure was authorised.

## Domain quick reference

- The controlling artefact is the detailed procedure, and it is graded
  on content before anyone applies power: item identity and
  configuration, vacuum conditions, the calibration of the
  radio-frequency-path, the detection method with its sensitivity check,
  the power profile, abort criteria, data recording, pass-fail criteria,
  nonconformance handling, and who is authorised to do what. A missing
  element is a procedure finding, independent of how the run went.
- Step order is not a preference; parts of it are physics and parts are
  evidence. Pumpdown precedes any powered step. Path-calibration and the
  detection-baseline check precede the first application of
  radio-frequency-power, or the run has no traceable power level and no
  demonstrated detection floor. Venting follows power-down, never
  precedes it. Data archiving closes the run. A declared order that
  breaks one of those pairs is invalid before execution starts.
- The power profile is a staircase, not a single set point: levels rise
  monotonically so that an onset is bracketed between the last quiet
  level and the first level that showed activity, each level is held long
  enough for the detection chain and the item to settle, and the top of
  the staircase reaches the level the test-margin puts above nominal
  (a margin in dB scales power by ten to the tenth of that margin).
- Departures happen: an instrument fails, a level is skipped, a step is
  run out of order. The clause does not forbid them -- it requires them
  to be controlled. A departure with a recorded reason and a named
  authoriser is a deviation; the same departure with no reason or no
  authoriser is uncontrolled, and uncontrolled departures are what
  invalidate the run.
- Grading therefore has two halves that fail independently: the
  procedure as written, and the execution log against it. A perfect
  procedure executed loosely and a loose procedure executed exactly are
  both non-compliant.

## Workflow

1. Grade the written procedure for content: compare its declared
   elements against the expected set and list what is absent.
2. Validate the declared step order. Reject an unknown step identifier
   or a repeated one outright, then check every precedence pair the
   setup imposes; report each violated pair rather than only the first.
3. Validate the power-step schedule: monotonic non-decreasing levels,
   every dwell at or above the minimum, and a top level that reaches
   nominal raised by the test-margin. Absorb representation error when
   the achieved level is a sum of measured contributions; never lower
   the margin to make a level fit.
4. Walk the execution log against the procedure order. Record each step
   as executed in order, executed out of order, or not executed.
5. Categorise every departure against the deviation records: covered by
   an authorised deviation, recorded but unauthorised, or uncontrolled.
6. Aggregate. The run is execution-controlled only when the procedure
   content is complete, the declared order is valid, the schedule is
   sound, and no departure is left uncontrolled or unauthorised.

## Pitfalls

- Grading the execution log alone. A log that matches an incomplete
  procedure step for step proves obedience, not control; the content
  check is the other half and fails on its own.
- Accepting a power staircase that steps down and back up. Onset
  bracketing depends on monotonic progression -- a dip in the middle
  leaves the onset attributable to either crossing.
- Letting the detection-baseline check drift after the first powered
  step "because the chain was checked yesterday". Precedence puts it
  before power for this run, not before some earlier run.
- Treating a deviation note with no named authoriser as control. A
  reason without an authorisation is a record of what happened, not a
  decision that it was acceptable.
- Rounding the test-margin down so the achieved top level qualifies.
  Absorb the representation error of a summed measurement in the
  comparison, and leave the margin exactly where the verification-plan
  put it.

## Behavior contract (gate 3)

The procedure-content, step-precedence, power-schedule, execution-log
and deviation-categorisation logic is exercised by the gate 3 contract
test: scripts/test_e2001_test_execution_control.py against
scripts/e2001_test_execution_control_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_test_execution_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
