---
name: q6013-class-3-microwave-integrated-circuits
description: "Evaluate whether a microwave monolithic integrated circuit may be applied at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.5: refuse a part declaring no technology or package form, fold a pulsed duty cycle into an effective dissipation, raise the channel temperature from the baseplate along the thermal path, take the margin against the technology ceiling and the part rating with the lowest-class allowance removed, invert the same path into the dissipation and baseplate the application may still use, cap the applied drive, oblige humidity control behind a non-hermetic package, and size the lot sample. Use when an MMIC application has to become a verdict. Trigger: ecss, q-st-60-13c-clause-6-6-5, class-three-mmic-application-envelope, mmic-channel-temperature-margin, mmic-duty-cycle-effective-dissipation, non-hermetic-mmic-humidity-obligation, mmic-lot-sample-size."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-microwave-integrated-circuits, class-three-mmic-application-envelope, mmic-channel-temperature-margin, mmic-duty-cycle-effective-dissipation, non-hermetic-mmic-humidity-obligation, mmic-lot-sample-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Microwave Integrated Circuits (space-systems/ecss/q6013-class-3-microwave-integrated-circuits)

Use when the task is clause 6.6.5 of ECSS-Q-ST-60-13C at the lowest assurance
class: a commercial microwave monolithic integrated circuit has been selected,
nothing was bought behind it beyond what the manufacturer publishes, and the
question is the envelope inside which it may still be applied.

## Domain quick reference

- The lowest class buys no part-level evaluation, so the manufacturer's
  channel rating stands alone. That is why an allowance is held back from it:
  the number is a figure at a stated condition, not a measurement of the
  device that arrived in the delivery.
- Two ceilings apply and the lower one wins. The technology sets what the
  material system tolerates; the part rating sets what this device was sold
  against. Grading on whichever is more convenient is how a gallium arsenide
  part ends up run at a gallium nitride temperature.
- A pulsed part is graded on what it dissipates, not on what it peaks at. The
  duty cycle belongs in the dissipation before the thermal path sees it, and a
  part assessed at its peak is refused for stress it never applies.
- The verdict is worth less than the envelope. Inverting the same thermal path
  gives the dissipation the application may still spend at this baseplate and
  the baseplate it may still reach at this dissipation, which is what a
  thermal engineer can act on when the answer comes back negative.
- Drive is the second stress and it is independent of the first. A part inside
  its channel ceiling and over its derated input is over-driven, and the
  thermal margin does not buy that back.
- A non-hermetic package is not a lower grade of hermetic. It admits moisture,
  so it carries an obligation on assembly and storage rather than a deduction,
  and the obligation is discharged by the programme, not by the part.
- The lot sample replaces the lot acceptance the class did not buy. It scales
  with the delivery, floors at a few devices so a small lot is still looked
  at, and never asks for more devices than the lot contains.

## Workflow

1. Validate the record: a reference, the declared technology and package form,
   the part channel rating, the baseplate temperature, the peak dissipation
   and duty cycle, the thermal path, the rated and applied drive, the lot size.
2. Separate an input typing error from an undeclared construction. A number
   the caller mistyped is theirs to fix; a technology or package form outside
   the recognised set is a verdict this clause owes an answer to.
3. Fold the duty cycle into an effective dissipation.
4. Take the applied ceiling as the lower of the technology ceiling and the
   part rating, less the allowance the lowest class holds back.
5. Raise the channel temperature from the baseplate along the thermal path and
   take the margin against that ceiling through a named tolerance, counting an
   exact landing as met.
6. Invert the path twice to publish the envelope: the dissipation available at
   this baseplate and the baseplate available at this dissipation.
7. Cap the applied drive at the derated share of the rated input.
8. Raise the humidity obligation behind a non-hermetic package that has none
   in place, and size the lot sample by the exact integer rule.
9. Return one verdict in precedence order: undeclared construction, applied
   stress over a ceiling or cap, a moisture obligation, otherwise accepted.

## Pitfalls

- Grading the part against the manufacturer's rating with nothing held back.
  At this class there is no evaluation behind the rating, and the allowance is
  the only thing standing where the evaluation would have been.
- Taking whichever of the two ceilings is higher. The technology ceiling and
  the part rating answer different questions, and the application has to
  satisfy both, which means the lower one is the one that binds.
- Assessing a pulsed amplifier at its peak dissipation. The duty cycle belongs
  in the dissipation, and a part refused on a peak it applies for a fraction
  of the time is a design changed for no thermal reason.
- Returning a refusal with no envelope attached. The number a thermal engineer
  needs is the dissipation or baseplate that would have passed, and a verdict
  without it sends the same question round again.
- Reading thermal margin as cover for over-driving the part. The two stresses
  act through different mechanisms and neither margin pays for the other.
- Treating a plastic package as a cheaper hermetic one. It admits moisture,
  the obligation falls on assembly and storage, and a build that never wrote
  the obligation down has already discharged nothing.
- Sampling a fixed number of devices from every lot. A share that never floors
  leaves a small delivery unlooked-at, and one that never caps asks a ten-piece
  lot for more devices than it holds.

## Behavior contract (gate 3)

The construction validation, duty-cycle folding, channel-temperature rise,
dual-ceiling selection with the class allowance, tolerance handling on an
exact landing, envelope inversion for dissipation and baseplate, drive
derating, moisture obligation and exact-integer lot sample rule are exercised
by the gate 3 contract test:
scripts/test_q6013_class_3_microwave_integrated_circuits.py against
scripts/q6013_class_3_microwave_integrated_circuits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_microwave_integrated_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
