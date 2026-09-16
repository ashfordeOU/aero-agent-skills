---
name: e2008-coverglass-abrasion-resistance
description: "Use when an abrasion result is about to be recorded from a run whose dose nobody pinned down. Assess an eraser abrasion run on the coated face of a coverglass per ECSS-E-ST-20-08C clause 8.7.17: hold the delivered stroke count at the twenty the procedure fixes, in both directions, hold the applied load inside its band, turn load and tip diameter into a contact pressure so a worn-flat eraser cannot stand in for the specified dose, size the rubbed track the optical change has to belong to, and read transmittance loss, haze rise and coating removal against their ceilings. Trigger: ecss, e-st-20-08c-clause-8-7-17, coverglass-eraser-abrasion-resistance, coated-face-abrasion-stroke-count, eraser-contact-pressure-band, coverglass-abrasion-transmittance-loss, coverglass-coating-removal-fraction, abrasion-run-void-criteria."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-abrasion-resistance, coverglass-eraser-abrasion-resistance, coated-face-abrasion-stroke-count, eraser-contact-pressure-band, coverglass-abrasion-transmittance-loss, coverglass-coating-removal-fraction, abrasion-run-void-criteria]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Abrasion Resistance (space-systems/ecss/e2008-coverglass-abrasion-resistance)

Use when the task is clause 8.7.17 of ECSS-E-ST-20-08C -- twenty
loaded eraser strokes drawn across the coated face of a coverglass to
gauge how well the coating survives being touched. The check is
deliberately crude, and all of its value sits in the fact that the dose
is fixed. A run that improvises any part of that dose does not produce
a gentler or a harsher result; it produces a result with nothing to
attach the optical change to.

## Domain quick reference

- Three numbers define the run: the face, the stroke count and the
  load. Change any of them and the outcome stops being comparable with
  the outcome of any other article, including the same article measured
  last month.
- The stroke count is held in both directions. A short run under-tests
  and a long run over-tests, and a lot accepted on eighteen strokes is
  not conservatively accepted -- it is accepted on an unstated dose.
- The load alone does not describe the contact. An eraser worn flat to
  twice its diameter spreads the same load over four times the area, so
  the coating sees a quarter of the pressure while the load reading on
  the fixture stays exactly right.
- The rubbed track is what the optical change belongs to. A
  transmittance drop read over the whole article dilutes damage
  confined to a narrow band, and a removed-coating area quoted in
  square millimetres means nothing until it is a share of that track.
- The coated face is the subject. Strokes on the uncoated side abrade
  bare glass, and bare glass under a rubber eraser at a few newtons
  will usually come through clean whatever the coating would have done.
- Transmittance, haze and coating removal fail differently. A coating
  can hold its transmittance while scattering badly, and it can hold
  both while lifting in patches, so all three are read rather than the
  most convenient one.
- A face that reads brighter after abrasion than before has not gained
  transmittance. It was dirty at the start, and the run cleaned it;
  that is a reason to distrust the before reading, not a result.

## Workflow

1. Collect the run evidence and refuse to judge anything until face,
   stroke count, load, tip diameter, stroke length and both optical
   readings are all present.
2. Separate the dose checks from the result checks. Face, count, load
   and contact pressure decide whether the run happened as specified;
   they void it rather than fail it.
3. Convert load and tip diameter into a contact pressure and hold it
   inside its band, so a worn or a re-cut tip is caught while the load
   reading still looks correct.
4. Size the rubbed track from the tip and the stroke length, and carry
   the travel and the frictional work as the record of what the run
   actually put into the coating.
5. Read the transmittance loss relative to the before value, the haze
   as a plain difference, and the removed coating as a share of the
   track, each against its own ceiling.
6. Close with a verdict that separates void from not accepted, so a
   run that has to be repeated is never filed as a coating that failed.

## Pitfalls

- Treating a short run as conservative. Nineteen strokes is not a
  safety margin, it is a different test, and the coating that passes it
  has not been shown to pass the specified one.
- Reading the load off the fixture and stopping there. The pressure is
  what the coating experiences, and it moves with the square of the tip
  diameter while the load stays put.
- Quoting removed coating in absolute area. Half a square millimetre is
  trivial on a wide track and most of the damage on a narrow one, so
  the number only means something as a share.
- Reading transmittance over the whole coverglass. The run touched a
  band a few millimetres wide, and averaging across the article buries
  exactly the change the strokes were meant to reveal.
- Recording a brightness gain as a result. It is a dirty before
  reading; carrying it forward produces a negative loss that flatters
  the coating and poisons any trend built on the lot.
- Filing a void run as a failed coating. The two have different
  consequences: one is repeated, the other is rejected, and conflating
  them loses articles that were never actually tested.
- Comparing a derived pressure against its band by bare arithmetic. It
  is a load divided by a squared diameter and rescaled between
  millimetres and metres, so the comparison absorbs a few units in the
  last place while the band itself is never widened.

## Behavior contract (gate 3)

The required run evidence, coated-face subject, two-directional stroke
count, load band, contact pressure band, rubbed track area, travel and
frictional work, relative transmittance loss, haze difference, coating
removal share and the void-versus-not-accepted split are exercised by
the gate 3 contract test:
scripts/test_e2008_coverglass_abrasion_resistance.py against
scripts/e2008_coverglass_abrasion_resistance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_abrasion_resistance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
