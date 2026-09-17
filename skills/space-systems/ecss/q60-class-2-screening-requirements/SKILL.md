---
name: q60-class-2-screening-requirements
description: "Assess the screening regime applied to Class 2 EEE parts before they enter flight standard hardware. Use when a lot is screened or its screening record is reviewed: decide from the destination whether flight screening is owed or non-flight marking is, take the screen set the package family carries, name any screen omitted, confirm each stress precedes the measurement that judges it, convert a burn-in run off its reference temperature into equivalent hours through an Arrhenius factor, and compare the percent defective produced with the allowable. Trigger: ecss, ecss-q-st-60c-clause-5-3-3, class-2-screening-requirements, class-2-screening-sequence-order, class-2-burn-in-equivalent-hours, class-2-percent-defective-allowable, class-2-flight-standard-lot-marking."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-2-screening-requirements, ecss-q-st-60c-clause-5-3-3, class-2-screening-requirements, class-2-screening-sequence-order, class-2-burn-in-equivalent-hours, class-2-percent-defective-allowable, class-2-flight-standard-lot-marking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts — Screening Requirements (space-systems/ecss/q60-class-2-screening-requirements)

Use when the task is the screening duty of ECSS-Q-ST-60C clause 5.3.3 — the
screening regime a Class 2 part owes before it is fitted to flight standard
hardware.

## Domain quick reference

- The destination decides what is owed. A lot routed to ground support
  equipment or an engineering model owes marking that keeps it out of flight,
  not the flight screening sequence; an unmarked one is a flight part waiting
  for somebody to reach into the wrong drawer.
- The screen set belongs to the package family, not to the project. A cavity
  package owes a hermeticity check; an encapsulated part has no cavity for
  that check to mean anything, and a set copied between families either
  over-tests or leaves a real failure mode unscreened.
- Screening is a sequence, not a checklist. Every stress exists to be
  measured afterwards, so a final electrical taken before burn-in and a leak
  check taken before temperature cycling both pass parts the sequence was
  built to remove.
- Burn-in is judged on what it achieved, not on the clock. Hours at one
  temperature convert to hours at another through an Arrhenius acceleration
  factor, so a short hot burn-in can satisfy a long nominal one and a
  full-length cool one can fail it.
- A burn-in landing exactly on its requirement has met it. The comparison
  carries a representation-sized tolerance so an exponential evaluated on two
  machines does not produce two verdicts.
- The percent defective allowable judges the lot, not the part. A lot that
  rejects heavily at screening has told you something about the whole
  population, and the surviving devices carry that history.
- A rate landing on the allowable is within it. Expressed two ways, the same
  ratio differs in the last bit, and the finding would be an artefact.
- The findings are reported together. The parts engineer closes the lot once
  and needs the omitted screen, the mis-ordered stress and the reject rate in
  the same list.

## Workflow

1. Read the destination and, for a non-flight lot, require the marking that
   keeps it out of flight hardware.
2. For a flight lot, take the screen set its package family owes.
3. Name every owed screen the recorded sequence does not carry, rejecting a
   sequence that records the same screen twice.
4. Check each precedence rule against the recorded order and report a stress
   that ran after the measurement judging it.
5. Convert the burn-in actually run to its equivalent at the reference
   temperature through the Arrhenius factor and compare with the hours
   required, within a representation-sized tolerance.
6. Compute the percent defective from the devices screened and rejected and
   compare it with the allowable, within the same kind of tolerance.
7. Report the per-lot records, the flight-ready fraction across flight lots
   only, and a verdict carrying every finding.

## Pitfalls

- Screening a lot and leaving the non-flight lots unmarked next to it. The
  screening record is correct and the wrong reel still reaches the board.
- Applying one screen set to every package. The encapsulated parts are
  charged for a hermeticity check that cannot fail, and the cavity parts
  escape the one that can.
- Treating the sequence as an unordered list. Each stress is only worth the
  measurement that follows it, and re-ordering silently removes that worth.
- Counting burn-in in clock hours across temperatures. Sixty hours hot and
  one hundred and sixty-eight hours cool are not comparable until both are
  expressed at one reference.
- Failing a burn-in that landed on its requirement. The shortfall is in the
  last bit of an exponential, not in the oven.
- Judging the reject rate part by part. The allowable is about the lot, which
  is the thing the surviving devices came from.
- Reporting the first finding and stopping. A lot usually fails in more than
  one way, and each way is a separate corrective action.

## Behavior contract (gate 3)

The destination and non-flight marking rule, the per-family screen sets, the
omitted-screen naming, the precedence checks on the recorded order, the
Arrhenius conversion of burn-in to equivalent hours with its
representation-sized tolerance, the percent defective against the allowable,
the flight-ready fraction and the overall verdict are exercised by the gate 3
contract test: scripts/test_q60_class_2_screening_requirements.py against
scripts/q60_class_2_screening_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_screening_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
