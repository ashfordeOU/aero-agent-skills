---
name: e2007-launch-system-compatibility-verification
description: "Verify launch-system electromagnetic compatibility, or justify waiving it. Use when the ascent case of ECSS-E-ST-20-07C clause 5.3.3 has to be closed: rebuild the powered-state timeline of every spacecraft unit between liftoff and separation, merge the declared phases to prove the unpowered claim covers the whole ascent window with no gap, categorize each unit as unpowered, passively-powered, actively-powered or rf-transmitting, and grant the testing waiver only when no unit ever leaves the unpowered state. Otherwise size the radiated-emission margin against the launcher susceptibility limit and name the verification method each surviving powered state still owes. Trigger: ecss, e-st-20-07c, e-st-20-electrical-scope, launch-system-compatibility, ascent-unpowered-waiver, powered-state-timeline, launcher-radiated-emission-margin, separation-event-window, spacecraft-verification-method-selection."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-launch-system-compatibility-verification, launch-system-compatibility, ascent-unpowered-waiver, powered-state-timeline, launcher-radiated-emission-margin, separation-event-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Launch-System Compatibility Verification (space-systems/ecss/e2007-launch-system-compatibility-verification)

Use when the task is the launch-system compatibility verification of
ECSS-E-ST-20-07C clause 5.3.3 — deciding whether the spacecraft owes a
compatibility test against the launcher electromagnetic environment at
all, because the clause releases that obligation for a spacecraft that
stays unpowered for the whole ascent.

## Domain quick reference

- The waiver is not a property of the spacecraft, it is a property of
  the ascent timeline. It holds only while every unit is unpowered for
  every instant between liftoff and separation, so the evidence is a
  timeline, not a statement of intent.
- Four powered states are recognised and only the first supports the
  waiver. Unpowered is no current drawn at all. Passively-powered is a
  survival heater, a thermostat loop or a battery trickle path — small,
  but a real switching current with a real emission spectrum.
  Actively-powered is an avionics unit running off the bus.
  Rf-transmitting is a beacon or transponder radiating by design. An
  unrecognised state is refused rather than folded into the nearest one.
- A declaration that leaves part of the ascent window undescribed is not
  a silent unpowered period. The union of the declared phases has to
  cover the window from liftoff to separation; whatever it does not
  cover is an open coverage finding, and the waiver cannot rest on it.
  Two abutting phases meet without a gap; a numerical hair between them
  is absorbed by a named time tolerance, never by stretching a phase.
- Once the waiver is refused, the clause reverts to an ordinary
  compatibility case: the spacecraft radiated emission is compared with
  the launcher susceptibility limit and the difference is the achieved
  margin in dB. An exactly compliant case is a representation question
  and is settled by tolerance inside the comparison.
- The verification method owed follows the surviving powered state. An
  unpowered configuration is confirmed by inspection of the power-off
  arrangement; a passive heater path can be closed by analysis backed by
  test; an actively-powered or transmitting unit owes a test, because
  neither its spectrum nor its duty cycle is predictable from drawings.

## Workflow

1. Normalize the ascent window and reject a separation event that does
   not follow liftoff; a zero-length window is an input error, not a
   degenerate ascent.
2. Normalize every unit record: resolve each declared phase state
   against the recognised set, clip each phase to the ascent window, and
   drop a phase that lies entirely outside it. A unit left with no phase
   inside the window is a declaration error.
3. Merge each unit's phases and compare the union with the window.
   Record every unit whose declaration leaves a gap.
4. Sum the time each unit spends outside the unpowered state and record
   every unit with a non-zero powered duration together with the states
   it passes through.
5. Grant the waiver only when no unit has a coverage gap and no unit has
   powered time. Emit one finding per gap and one per powered state so
   the refusal names its own cause.
6. When the waiver is refused, take the union of the surviving states,
   map it to the owed verification methods, and require an emission
   record; compute the margin as the launcher limit less the spacecraft
   emission and compare it with the required margin under tolerance.
7. Report the ascent duration, the waiver verdict, the powered duration,
   the owed methods, the margin and the finding list; the case closes
   only when the finding list is empty.

## Pitfalls

- Reading "unpowered at separation" as "unpowered throughout". The
  clause releases the test for the whole ascent phase, so a unit powered
  for ninety seconds early in the flight destroys the waiver just as
  surely as one powered the whole way.
- Treating survival heaters as not powered. A thermostat loop switches,
  and a switching current inside the fairing is exactly the emission the
  launcher authority is asking about; it is a powered state.
- Letting an undeclared stretch of the timeline pass as unpowered. The
  absence of a declaration is the absence of evidence, which is why a
  coverage gap is a finding in its own right and not a default.
- Deciding an exactly-at-limit emission case with a bare inequality. The
  margin is a difference of decibel quantities, so an exactly compliant
  spacecraft can land a unit in the last place on the wrong side of the
  requirement. Absorb that in the comparison, never by lowering the
  required margin.
- Naming inspection as the method for a transmitting unit because the
  unit is switched off in the flight procedure. The method follows the
  state the timeline actually declares, not the state the procedure
  intends.

## Behavior contract (gate 3)

The powered-state categorization, ascent-window normalization, interval
merging and gap detection, waiver decision, verification-method
selection and emission-margin comparison are exercised by the gate 3
contract test:
`scripts/test_e2007_launch_system_compatibility_verification.py` against
`scripts/e2007_launch_system_compatibility_verification_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_launch_system_compatibility_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
