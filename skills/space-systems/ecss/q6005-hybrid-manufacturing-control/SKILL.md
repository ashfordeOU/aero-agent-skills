---
name: q6005-hybrid-manufacturing-control
description: "Audit the in-process controls a hybrid microcircuit line runs while it assembles and seals units, under ECSS-Q-ST-60-05 clause 10.1. Use when an assembly flow needs its production controls graded: test each operation against the cleanliness grade it may be worked in, size the pre-seal bakeout dwell from its plateau, judge the sealing atmosphere moisture and the stand time before the seal, read bond-strength monitoring from the pull sample spread, grade every control element, and return the manufacturing-control index with one verdict. Trigger: ecss, q-st-60-05, hybrid-assembly-process-control, hybrid-assembly-environment-grade, pre-seal-bakeout-dwell, hybrid-sealing-atmosphere-moisture, hybrid-bond-pull-monitoring, manufacturing-control-index, hybrid-line-control-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-hybrid-manufacturing-control, hybrid-assembly-process-control, hybrid-assembly-environment-grade, pre-seal-bakeout-dwell, hybrid-sealing-atmosphere-moisture, hybrid-bond-pull-monitoring, hybrid-line-control-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Manufacturing Control (space-systems/ecss/q6005-hybrid-manufacturing-control)

Use when the task is clause 10.1 of ECSS-Q-ST-60-05: the controls a hybrid
manufacturer keeps over the production environment and over the assembly and
sealing operations carried out inside it, so that what leaves the line is the
article the design describes rather than whatever the room allowed that day.

## Domain quick reference

- A hybrid is open to the room for most of its build, so the environment is
  not a background condition, it is part of every operation. Each operation
  therefore carries the dirtiest air it may be worked in, and an operation run
  in a dirtier area than its own limit is uncontrolled however carefully the
  step itself was performed.
- Sealing is the strictest operation of all, because whatever is in the room
  at that moment is inside the package for the rest of its life. Nothing
  downstream removes it, and no later inspection sees it.
- The pre-seal bakeout is a dwell, not a temperature. A hotter plateau drives
  the same moisture out in less time, so the required dwell falls as the
  plateau rises, down to a floor below which the mechanism has no time to work
  at all. A bake too hot for the attach materials is a finding, not credit.
- Moisture inside the package is decided twice over: by the atmosphere the
  unit is sealed in, and by how long it stood between the bakeout and the
  seal. A dry gas cannot rescue a unit left open on the bench for an
  afternoon.
- Bond-strength monitoring is read from the spread of the pull sample, not
  from its mean. A sample whose average is comfortable and whose spread is
  wide will put bonds under the minimum strength on the lots nobody pulled.
- A few control elements are the reason the line is controllable at all —
  environment monitoring, electrostatic protection, bond-strength monitoring,
  pre-seal inspection, the bakeout and the sealing atmosphere. A line missing
  one of those is not graded low, it is not graded.

## Workflow

1. Name the line and collect the assembly operations it declares, the
   environment each is worked in, and the control elements it claims to run.
2. Validate the flow: an operation appears once, every operation and grade is
   a known one, and the mandatory operations are all named — a flow that never
   mentions sealing cannot be graded at all.
3. Compare each operation with the dirtiest environment it is allowed, and
   name every operation worked in air below its own limit.
4. Size the required bakeout dwell from the declared plateau, refuse a plateau
   under the minimum, and raise a finding for one above the material limit
   rather than crediting it as a faster bake.
5. Test the sealing atmosphere moisture and the stand time between bakeout and
   seal separately, absorbing the comparison at each bound with a named
   tolerance.
6. Read the bond pull sample: its spread against the minimum strength gives
   the capability, and any single reading under the floor is its own finding.
7. Grade every control element against the full element set, so an element
   nobody mentioned is graded as not implemented, and mark the mandatory ones.
8. Take weighted credit over total weight as the manufacturing-control index
   and name the verdict — incomplete while a mandatory element or operation is
   absent, not under control on a failed seal condition, a wrong environment,
   a mandatory element out of control or a low index, under control with open
   actions when findings remain, under control only when none do.

## Pitfalls

- Reading the environment as a site property rather than an operation
  property. One certified room does not make every step in it compliant; the
  step with the tightest limit sets what that room has to be.
- Crediting a hotter bake as a shorter one without a floor. Below the floor
  the moisture has no time to leave whatever the plateau, and past the
  material limit the attach is being damaged to dry the package.
- Sealing a unit that has stood open since its bakeout. The bake is undone by
  the room in hours, so the stand time is a control in its own right and not a
  scheduling convenience.
- Judging bond monitoring on the sample mean. The mean says the process is
  centred; only the spread says whether the tail is above the minimum
  strength, and the tail is what fails in flight.
- Letting a high index carry a line whose pre-seal inspection was never
  implemented. The index averages; the mandatory elements do not.
- Grading a rework loop by the state of the units that came out of it. An
  unauthorised rework is a control finding even when the rebuilt unit is
  faultless, because the next one will not be.

## Behavior contract (gate 3)

The operation and environment validation, the mandatory-operation rule, the
bakeout dwell sizing, the sealing atmosphere and stand-time checks, the bond
pull capability, the control-element grading, the manufacturing-control index
and the line verdict are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_manufacturing_control.py against
scripts/q6005_hybrid_manufacturing_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hybrid_manufacturing_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
