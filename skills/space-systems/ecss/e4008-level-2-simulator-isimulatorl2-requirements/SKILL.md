---
name: e4008-level-2-simulator-isimulatorl2-requirements
description: "Evaluate a level 2 simulator interface against the requirements of ECSS-E-ST-40-08C clause 5.5.4.2. Use when the task is confirming that the level 2 interface still offers every level 1 operation it extends, that hold, resume, store, restore, step, time scale and abort are all present, that no invented operation is passed off as part of the set, that each operation declares only the states it can really be called from, and that hold, resume, a step duration and a time scale all have a defined answer at their bounds. Grades an interface against the seven normative items. Trigger: ecss, e-st-40-08c, isimulatorl2, level2-simulator-interface, simulator-operation-state-guard, simulator-hold-resume-idempotence, simulator-step-duration-bound, simulator-time-scale."
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
  tags: [ecss, e-st-40-08-simulation-scope, e4008-level-2-simulator-isimulatorl2-requirements, isimulatorl2, level2-simulator-interface, simulator-operation-state-guard, simulator-hold-resume-idempotence, simulator-step-duration-bound]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Infrastructure — Level 2 Simulator (ISimulatorL2) Requirements (space-systems/ecss/e4008-level-2-simulator-isimulatorl2-requirements)

Use when the task is the level 2 simulator interface of ECSS-E-ST-40-08C
clause 5.5.4.2 -- what an implementation has to offer beyond the level 1
set, which states each added operation may be called from, and what the
bounded arguments of those operations are allowed to be. The clause
carries seven normative items and an interface is graded against all of
them.

## Domain quick reference

- Level 2 extends level 1; it does not replace it. An interface that
  offers hold, store and step but quietly drops one of the level 1
  operations is not a superset, and a harness written against level 1
  will fail on it at the point the missing operation is called.
- The added operations are the ones an operator or a test harness
  needs: suspend and continue a run, serialise the whole tree and bring
  it back, advance by a bounded amount, change the ratio between
  simulated and wall-clock time, and give up.
- Every operation is state-dependent. Holding a simulator that is not
  executing, or storing one mid-execution, has no defined meaning; the
  interface declares the states each operation is callable from and the
  declaration is graded against what the state model actually allows.
- Declaring a narrower state set than the model permits is a design
  choice, not a defect. Declaring a wider one is a defect, because the
  extra state is one the implementation has promised to handle and the
  model has no answer for.
- Hold from hold and resume from run are the cases that get left
  undefined. Making them idempotent is what lets a harness call them
  without first reading the state back, which is the whole point of
  having them.
- A step is a bounded advance. A non-positive duration is meaningless
  and an unbounded one is a run under another name, so both ends of the
  range need a defined answer rather than whatever the scheduler does.
- The time scale is a positive finite ratio. Zero stops simulated time
  while the run continues, a negative value runs it backwards, and
  neither is a mode the infrastructure offers.

## Workflow

1. Canonicalise the offered operation names so a spelling difference
   does not read as a missing operation.
2. Compare the offered set with the level 1 set and report every level 1
   operation that is absent, by name.
3. Compare it with the level 2 set and report every added operation that
   is absent, by name.
4. Report any offered operation that belongs to neither set rather than
   accepting it as a vendor extension inside the graded interface.
5. For each declared state guard, resolve the operation and its states
   and separate a narrowed declaration from a widened one; only the
   widened one is a finding.
6. Grade the idempotence evidence for hold and resume, the step duration
   against zero and against the upper bound, and the time scale against
   zero, negative and non-finite values.
7. Report the seven items separately with the offending operation,
   state or value named, so the finding points at what to change.

## Pitfalls

- Grading only the added operations. The level 1 operation that went
  missing during the extension is invisible to a check that looks at
  the level 2 list alone.
- Accepting an extra operation because it is useful. Inside a graded
  interface an unlisted operation is a compatibility hazard: a harness
  that finds it will use it, and the next implementation will not have
  it.
- Treating a narrowed state guard as a defect. An implementation that
  refuses abort while restoring is being conservative, and flagging it
  buries the widened declaration that actually matters.
- Leaving hold from hold undefined. The harness then has to read the
  state back before every call, and the read-then-act pair is a race
  the idempotent operation exists to remove.
- Allowing a step of zero as a no-op. It looks harmless, but a harness
  loop that steps zero ticks never advances and never terminates.
- Letting the time scale reach zero. Simulated time stops while the run
  keeps going, so every timeout in the model tree becomes unreachable
  and the run hangs with nothing obviously wrong.
- Comparing an operation name raw. A hyphenated or capitalised spelling
  then reads as both a missing operation and an unexpected one, which
  turns one cosmetic difference into two findings.

## Behavior contract (gate 3)

Operation-name canonicalisation, level 1 and level 2 completeness, the
unexpected-operation check, state-guard widening versus narrowing, hold
and resume idempotence, the bounded step duration, the positive finite
time scale and the seven-item grading are exercised by the gate 3
contract test:
scripts/test_e4008_level_2_simulator_isimulatorl2_requirements.py against
scripts/e4008_level_2_simulator_isimulatorl2_requirements_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e4008_level_2_simulator_isimulatorl2_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
