---
name: q60-class-2-evaluation-testing
description: "Derive the inspection and test programme a Class 2 part evaluation actually owes under ECSS-Q-ST-60C clause 5.2.3.4: start from the core every evaluated part owes whatever it is, add each item a declared condition asks for — mission length, mission dose, a particle environment on an active technology, a sealed or moisture-absorbing package, a termination finish with a known failure mode, an operating span nobody characterised, a mechanical environment nobody covered higher up — keep the triggering condition attached to each item, and credit a performed test only on the same procurement lot inside its validity window. Use when an evaluation needs a defensible test list rather than a template. Trigger: ecss, q-st-60c-clause-5-2-3-4, class-2-evaluation-test-selection, class-2-inspection-and-test-matrix, class-2-use-condition-triggers, class-2-prior-test-credit, class-2-outstanding-test-programme."
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
  tags: [ecss, q-st-60c-class-2-eee-scope, q-st-60c, q60-class-2-evaluation-testing, q-st-60c-clause-5-2-3-4, class-2-evaluation-test-selection, class-2-inspection-and-test-matrix, class-2-use-condition-triggers, class-2-prior-test-credit, class-2-outstanding-test-programme]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Evaluation Testing (space-systems/ecss/q60-class-2-evaluation-testing)

Use when the task is clause 5.2.3.4 of ECSS-Q-ST-60C: deciding which
inspections and tests an evaluated Class 2 electrical, electronic and
electromechanical part actually requires — the selection question, ahead of
how any one of those tests is later run or read.

## Domain quick reference

- The programme has two halves and they are decided differently. A small core
  is owed by every evaluated part whatever it is and wherever it flies, and
  nothing in the use conditions removes it. Everything else is owed only
  because some declared condition asked for it.
- An item without its triggering condition cannot be defended. Each triggered
  item therefore carries the condition that produced it, so the programme is
  argued item by item instead of cited as a template somebody once approved.
- The conditions are independent of one another and are read independently. A
  long mission, a hard dose, a particle environment, a package that can be
  opened or that takes up moisture, a termination finish with a known failure
  mode, an operating span beyond what was characterised, and a mechanical
  environment nobody covered at a higher level each reach a different item.
- A particle environment only reaches a technology that can be upset by one.
  Declaring the orbit is not on its own a reason to characterise a resistor.
- Package type is exclusive in its effect: a sealed cavity asks to be proven
  sealed, an encapsulated part asks to be proven dry. Asking for both is a
  sign the package was never really declared.
- An operating span is a comparison, not a number. What matters is whether the
  application reaches beyond what the manufacturer already characterised, so a
  wide span that was fully characterised triggers nothing.
- Delegating the mechanical environment to a higher level of assembly is a
  legitimate answer and is recorded as one, so the delegation can be checked
  against what the assembly test actually covered.
- A performed test carries credit only for the lot it was performed on, and
  only while it is still inside its validity window. Credit offered for an
  item the programme never asked for usually means the wrong programme ran.

## Workflow

1. Declare the part: family, package type and termination finish. An
   unrecognised value is an input error, not a default.
2. Declare the use conditions: mission duration, the operating span the
   application demands against the span already characterised, the mission
   dose, whether a particle environment applies, and whether the mechanical
   environment is covered at a higher level of assembly.
3. Lay down the core items first; they are owed unconditionally.
4. Read each condition independently and add the item it asks for, keeping the
   condition attached as the reason.
5. Absorb a condition that lands exactly on a trigger with a named tolerance
   rather than by moving the trigger; a mission exactly at the endurance
   trigger does not ask for the life test.
6. Report the conditional items nothing asked for, so a reviewer can see what
   was considered and set aside rather than what was forgotten.
7. Match every performed test against the lot and the validity window before
   granting credit, and name each record that fails either rule.
8. Return the outstanding list: what is owed, minus only what genuinely
   carried.

## Pitfalls

- Copying a programme from a previous part because the part number looked
  similar. Without the triggering conditions the list cannot be defended, and
  the one item this part needed is the one that was never on it.
- Reading the orbit as a reason to characterise everything in the box. Single
  particle effects reach active technologies, not every component in a slot.
- Asking for a seal test and a moisture bake on the same part. The package is
  one thing or the other, and asking for both means it was never declared.
- Treating a wide operating span as the trigger. The trigger is the span the
  application demands beyond what was already characterised.
- Letting a mission exactly on the endurance trigger pull in a life test by
  way of a floating-point comparison. The bound is absorbed, not moved.
- Accepting a test performed on a different procurement lot. A lot is the unit
  the evidence attaches to, and a nearby lot is a different population.
- Keeping an expired record because nothing about the part changed. The window
  exists because the process behind the record drifts.
- Silently dropping credit that was offered for an item nobody required. That
  offer is itself evidence that the programme run was not the programme owed.
- Delegating the mechanical environment upward without recording the
  delegation, so nobody later checks what the assembly test really covered.

## Behavior contract (gate 3)

The unconditional core, the independent condition triggers with their
attached reasons, the absorbed trigger bounds, the not-required reporting and
the lot-and-validity prior-test credit rule are exercised by the gate 3
contract test: scripts/test_q60_class_2_evaluation_testing.py against
scripts/q60_class_2_evaluation_testing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_2_evaluation_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
