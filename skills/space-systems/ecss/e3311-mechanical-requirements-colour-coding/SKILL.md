---
name: e3311-mechanical-requirements-colour-coding
description: "Verify the two obligations ECSS-E-ST-33-11C clause 4.8.1 puts on the same explosive component: a pressure-bearing body that holds up, and a marking that cannot be misread. Use when an initiator, detonator or pyrotechnic device is designed or reviewed: build proof and burst pressures from the operating pressure, take the hoop stress and the margins against yield and ultimate, confirm the thin-wall form is even applicable, then check the project colour-code scheme for duplicated, reserved or readily confused colours and confirm each unit carries a text identifier beside its colour. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-component-mechanical-design, explosive-colour-code-scheme, pyrotechnic-marking-verification, proof-and-burst-pressure, explosive-body-hoop-stress, live-versus-inert-marking."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-mechanical-requirements-colour-coding, explosive-component-mechanical-design, explosive-colour-code-scheme, pyrotechnic-marking-verification, proof-and-burst-pressure, explosive-body-hoop-stress, live-versus-inert-marking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Mechanical Requirements and Colour Coding (space-systems/ecss/e3311-mechanical-requirements-colour-coding)

Use when the task is clause 4.8.1 of ECSS-E-ST-33-11C on an explosive
component -- the mechanical design of the pressure-bearing body and the
colour-code marking that separates a live unit from an inert, training
or expended one. The two obligations sit on the same hardware and are
usually handled by different people, which is why they are closed
together here.

## Domain quick reference

- The body of an explosive component is a pressure part. The
  combustion or deflagration pressure is contained by the case, so the
  case is sized the same way any pressure part is: a proof pressure and
  a burst pressure built up from the maximum expected operating
  pressure, a hoop stress at each, and a positive margin against yield
  at proof and against ultimate at burst.
- The thin-wall form is the one usually written down, and it is only
  valid while the radius is large against the wall. On a stubby,
  thick-walled initiator body it understates the stress at the bore,
  so the ratio is checked before the margin is believed rather than
  after.
- Marking is a safety function, not a finish. It is what tells a
  technician on a pad, in poor light, whether the unit in their hand
  can fire. That is why a colour is never the only discriminator: a
  text identifier is carried beside it, and a live unit also carries a
  serial number that ties it to its lot.
- A colour scheme is only a safety feature if it is unambiguous. Two
  functions sharing a colour, a colour reserved for a hazard meaning
  elsewhere on the vehicle being reused for something ordinary, or a
  readily confused pair separating a live unit from an inert one are
  defects of the scheme, not of any single unit, and they are found by
  checking the scheme rather than by checking units one at a time.
- Confusability is directional in consequence. Two easily confused
  colours between a training unit and an expended one is a nuisance;
  the same pair between a live unit and an inert one is the hazard the
  scheme exists to prevent.
- Both halves have to close. A unit with a sound body and an unreadable
  marking is not compliant, and neither is a correctly marked unit with
  a negative margin.

## Workflow

1. Take the maximum expected operating pressure and build the proof and
   burst pressures from the declared factors. Reject a factor set where
   burst does not sit above proof.
2. Check the radius to wall ratio and record whether the thin-wall form
   is applicable before any stress is computed with it.
3. Compute the hoop stress at proof and at burst, and take the margin
   against yield at proof and against ultimate at burst, each with its
   own design factor.
4. Reject an ultimate strength below the yield strength rather than
   carrying the pair forward -- the material data is wrong, and every
   margin downstream of it is meaningless.
5. Check the project colour-code scheme as a whole: every function
   covered, every colour used once, no reserved colour reused, and no
   readily confused pair separating a live unit from anything else.
6. Check the unit's own marking against the scheme, confirm a text
   identifier is present, and require a serial number on a live unit.
   Close with a verdict that says which half failed, or that both did.

## Pitfalls

- Sizing the case on the operating pressure alone. The requirement is
  against proof and burst, so a body that is comfortable at the
  operating pressure can have no margin at all where the requirement
  actually sits.
- Using the thin-wall hoop stress on a thick-walled body. It understates
  the bore stress, and the error runs the wrong way: the margin looks
  better exactly where the geometry is worst.
- Treating the colour as the marking. Colour fails in poor light,
  through a dusty or oiled surface, and for a technician with a
  colour-vision difference; the text identifier is what survives all
  three, and a unit carrying colour alone has no marking at the moment
  it matters.
- Reviewing unit markings without ever reviewing the scheme. A unit can
  match its scheme perfectly while the scheme itself gives two
  functions the same colour, and no amount of unit-level checking will
  surface that.
- Reusing a colour that means something else on the vehicle. The
  technician reads one colour vocabulary, not one per subsystem, and a
  colour reserved for a hazard meaning elsewhere carries that meaning
  into the hand.
- Comparing a margin of safety with zero by bare arithmetic. The margin
  is a quotient less one, so a part sized exactly to its allowable can
  land a few units in the last place below zero; the comparison absorbs
  that representation error while the allowable stays untouched.

## Behavior contract (gate 3)

The proof and burst build-up, hoop stress, thin-wall applicability,
margins of safety, colour-scheme validation and unit marking check are
exercised by the gate 3 contract test:
scripts/test_e3311_mechanical_requirements_colour_coding.py against
scripts/e3311_mechanical_requirements_colour_coding_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_mechanical_requirements_colour_coding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
