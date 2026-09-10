---
name: e1002-simulators
description: "Use when a simulator (functional, real-time, or closed-loop / hardware-in-the-loop) is used to generate verification evidence under ECSS-E-ST-10-02C and its own qualification status needs to be established before that evidence can be credited: which fidelity evidence a simulator's role requires, whether it is currently qualified, and whether a design or interface change triggers re-qualification. Trigger: simulator qualification, functional simulator, real-time simulator, closed-loop simulator, hardware-in-the-loop, HIL simulator, verification tool qualification, e1002, e-st-10-02, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, e-st-10-02, simulator-qualification, verification-tools, hardware-in-the-loop]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulator Qualification for Verification (space-systems/ecss/e1002-simulators)

Use when the task is qualifying a simulator that will be used to
produce verification evidence under ECSS-E-ST-10-02C, ahead of
crediting any verification activity that relies on it.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.6.4 requires that simulators used for
  verification be qualified for the role they play: functional
  behaviour, real-time behaviour, or closed-loop (hardware-in-the-loop)
  operation, consistent with the general verification-tool
  classification of clause 5.2.6.1.
- A simulator can assert more than one capability at once (a real-time
  closed-loop simulator asserts all three); each asserted capability
  carries its own evidence obligation, and a simulator's full
  obligation is the union of the obligations of every capability it
  asserts.
- Functional capability needs functional-correctness evidence (the
  simulator reproduces the specified behaviour of the element or
  environment it stands in for). Real-time capability additionally
  needs timing-performance evidence (latency, throughput, determinism
  against the unit-under-test's real-time requirements). Closed-loop
  capability additionally needs interface-representativeness evidence
  (sensor/actuator/interface fidelity) and loop-stability evidence
  (nominal and off-nominal loop behaviour).
- A simulator is qualified only once every evidence item required by
  its asserted capabilities has been obtained; verification activities
  may only be credited against a qualified simulator.
- A qualified simulator is not qualified forever: a change to its
  model, to the environment interface it simulates, or to the
  interface of the unit under test invalidates the prior qualification
  and triggers re-qualification before further verification credit can
  be taken.

## Workflow

1. For each simulator used in verification, record the capabilities it
   is asserted to provide: functional, real-time, closed-loop (one or
   more).
2. Derive the required evidence set as the union of the evidence
   obligations of every asserted capability.
3. Compare required evidence against evidence already obtained; a
   simulator is qualified only when nothing is missing.
4. Build the qualification register: one assessment per simulator id,
   and treat a duplicate simulator id as an error rather than silently
   overwriting an entry.
5. Before crediting a verification activity that relied on a
   simulator, check that simulator's current status -- an activity may
   only be credited against a qualified simulator.
6. After any change to the simulator's model, its environment
   interface, or the unit-under-test interface it drives, flag the
   simulator for re-qualification even if it was previously qualified;
   an already-unqualified simulator remains flagged regardless of the
   change.

## Pitfalls

- Qualifying a real-time or closed-loop simulator against functional
  correctness alone and skipping the timing or interface/stability
  evidence its extra capabilities demand.
- Crediting a verification activity against a simulator that is
  documented but not yet qualified.
- Treating qualification as a one-time event and not re-qualifying
  after the simulator model or an interface it drives changes.
- Silently merging two simulator entries that share an id instead of
  flagging the duplicate for disposition.

## Behavior contract (gate 3)

The capability-classification, required-evidence, qualification, and
re-qualification-trigger logic is exercised by the gate 3 contract
test: scripts/test_e1002_simulators.py against
scripts/e1002_simulators_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_simulators.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
