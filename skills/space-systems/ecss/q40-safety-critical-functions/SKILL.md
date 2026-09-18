---
name: q40-safety-critical-functions
description: "Identify and control the safety-critical functions of an ECSS-Q-ST-40C clause 6.5 design: decide criticality from the worst credible consequence, derive the failure tolerance that severity demands and the inhibits it needs, count only independent inhibits toward the tolerance achieved so a shared common-cause group collapses three inhibits into one, and assess the clause's control set - inadvertent-operation prevention, operator status information, safe shutdown, EEE component selection and safety-critical software. Use when a function list is screened for criticality, an inhibit chain is argued, or a design review asks what a critical function still lacks. Trigger: ecss, q-st-40c, ecss-safety-critical-function, inadvertent-operation-prevention, independent-inhibit-count, ecss-safe-shutdown-control, safety-critical-software-function."
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
  tags: [ecss, q-st-40c-safety-assurance-scope, q40-safety-critical-functions, ecss-safety-critical-function, inadvertent-operation-prevention, independent-inhibit-count, ecss-safe-shutdown-control, safety-critical-software-function, ecss-failure-tolerance-derivation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety-Critical Functions (space-systems/ecss/q40-safety-critical-functions)

Use when the task is clause 6.5 of ECSS-Q-ST-40C: a function list has to be
sorted into what is safety-critical and what is not, and each critical
function then has to carry the failure tolerance and the control set the
clause puts on it.

## Domain quick reference

- Criticality is read off the consequence, not off the subsystem. A function
  whose loss or inadvertent operation is catastrophic or critical is
  safety-critical wherever it lives, and an explicit declaration can promote
  a lower-severity function that commands a hazardous event.
- Failure tolerance is a count of failures survived, not of parts fitted. Two
  failure tolerance needs three inhibits, one needs two, so the inhibit count
  is always one more than the tolerance the severity demands.
- Only independent inhibits count. Three inhibits on one power bus, in one
  box or driven from one command path are one inhibit between them, and
  grouping them by common cause before counting is the whole point of the
  exercise.
- The control areas are separate obligations, not a single checklist entry. A
  function can be fully tolerant and still owe inadvertent-operation
  prevention, status information to the operator and a safe shutdown path.
- Two of the areas are conditional on how the function is built. EEE
  component selection applies where the function sits in hardware, and the
  software control area where it sits in software; a function in both owes
  both.
- Status information is a control, not reporting. Without it the operator
  cannot tell an armed function from a safed one, so the safe shutdown path
  has nothing to act on.

## Workflow

1. Refuse a function record carrying an unknown key, an unknown control area,
   a non-boolean control value or a repeated inhibit identifier.
2. Decide criticality from the severity, honouring an explicit declaration
   where one is given.
3. Derive the demanded failure tolerance from the severity and the inhibit
   count that tolerance needs.
4. Group the declared inhibits by common cause and count the groups plus the
   ungrouped inhibits; the tolerance achieved is one less than that count.
5. Work out the control areas the function owes: the three universal areas
   plus EEE component selection where it is in hardware and the software area
   where it is in software.
6. Compare owed against provided and record the areas still open.
7. Roll the set up: the safety-critical count, the union of open control
   areas, and the findings - every tolerance shortfall and every open area.

## Pitfalls

- Counting inhibits instead of independent inhibits. Three switches on one
  bus read as two-failure tolerant and are not tolerant at all.
- Deriving tolerance from the subsystem rather than the consequence. The same
  valve driver is critical on one function and not on another.
- Treating the control areas as satisfied once the tolerance is met. They are
  separate obligations, and a tolerant function with no shutdown path is
  still open.
- Applying the EEE and software areas to everything. A function owes the area
  its implementation puts on it; demanding both of every function buries the
  real gaps in noise.
- Reading an absent control area as not applicable. An area that is owed and
  simply not mentioned is open, and it is reported as open.

## Behavior contract (gate 3)

The record validation and unknown-key refusal, the criticality decision with
its declared override, the tolerance and inhibit-count derivation, the
common-cause grouping of inhibits, the conditional control-area set, the
missing-area detection and the roll-up verdict are exercised by the gate 3
contract test: scripts/test_q40_safety_critical_functions.py against
scripts/q40_safety_critical_functions_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q40_safety_critical_functions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
