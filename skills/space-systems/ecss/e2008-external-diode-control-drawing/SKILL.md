---
name: e2008-external-diode-control-drawing
description: "Evaluate the source control drawing an external protection diode is bought against, the content ECSS-E-ST-20-08C Annex E expects fixed before order: name the heading the drawing leaves silent, check the stated reverse breakdown stands far enough above the applied reverse working voltage, hold the applied forward current against the rating once the declared derating is taken off, compute the junction temperature from the dissipation and the stated thermal path and test it against the rated maximum, and rank an absent heading above a stated limit that is not met. Use when an external diode source control drawing or procurement content review is on the table. Trigger: ecss, e-st-20-08c-annex-e, external-diode-source-control-drawing, external-diode-reverse-blocking-margin, external-diode-forward-current-derating, external-diode-junction-temperature-margin, external-diode-procurement-drawing-content."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-external-diode-control-drawing, e-st-20-08c-annex-e, external-diode-source-control-drawing, external-diode-reverse-blocking-margin, external-diode-forward-current-derating, external-diode-junction-temperature-margin, external-diode-procurement-drawing-content]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS External Protection Diode -- Source Control Drawing Content (space-systems/ecss/e2008-external-diode-control-drawing)

Use when the task is Annex E of ECSS-E-ST-20-08C: external protection diode
hardware is procured against a source control drawing, and somebody has to
decide whether that drawing actually buys a diode that survives the string it
protects. A part number and a package buy a diode. The limits the part is held
to -- how much reverse voltage it stands off, how much forward current it
carries after derating, how hot its junction gets doing so -- exist only if the
drawing states them. This leaf grades the drawing on content, on blocking, on
derating and on junction temperature.

## Domain quick reference

- The drawing is the limit set, not a description. A parameter the drawing
  does not state is a parameter nobody can hold the delivered part to, and the
  gap only becomes visible when a lot is rejected and there is nothing written
  to reject it against.
- Reverse blocking is a ratio question, not a comparison. A breakdown above
  the working voltage is necessary and nowhere near sufficient; the margin is
  what absorbs temperature coefficient, ageing and the transients the string
  actually applies.
- A breakdown equal to the working voltage is the same defect as one below it.
  Both describe a part operated at its own limit, so they are reported as one
  finding rather than as a pass sitting on a boundary.
- Derating is subtraction before comparison. The rating on the data sheet is
  not the allowance; the allowance is the rating times the declared factor,
  and the applied current is judged against that.
- Junction temperature is computed, never quoted. Forward drop times forward
  current gives the dissipation, the thermal resistance turns it into a rise,
  and the case temperature the assembly actually runs at sets where that rise
  starts.
- The margin sits below the rating, not at it. A junction landing exactly on
  the rated maximum has no margin left for the thermal model being slightly
  optimistic, so the limit the part is tested against is the rating less the
  margin.
- ESD sensitivity is a category, not a sentence. A free-text note about
  electrostatic care does not tell handling which controls apply; a category
  does, and it is a required heading for that reason.

## Workflow

1. Read the drawing identifier and the content mapping; the identifier is what
   every later finding is reported against.
2. Audit the content against the required heading set, treating an empty
   string, an empty list and an empty mapping as absent.
3. Assess reverse blocking: refuse a working voltage at or above the
   breakdown, then compute the margin as breakdown over working and test it
   against the policy floor.
4. Assess derating: compute the derated allowance from the rating and the
   factor, then report the applied current as a utilisation of that allowance.
5. Compute the junction temperature from the forward drop, the forward
   current, the thermal resistance and the case temperature, and test it
   against the rated maximum less the required margin.
6. Place the stated ESD sensitivity in a category, refusing anything the
   drawing's category set does not contain.
7. Return a drawing verdict that is releasable only when every heading is
   stated, blocking is adequate, derating is met and the junction holds its
   margin, with all findings in one list.

## Pitfalls

- Accepting a breakdown voltage that merely exceeds the working voltage. The
  comparison passes and the margin is still one temperature excursion wide.
- Comparing the applied current to the rated current directly. That skips the
  derating factor entirely, and the part reads compliant at twice its
  allowance.
- Quoting a junction temperature from the supplier's data sheet. The data
  sheet's case temperature is not the one the assembly runs at, and the number
  that matters is the one computed from this application's dissipation.
- Testing the junction against the rated maximum itself. The rating is where
  the part stops being qualified, so a design landing on it has consumed the
  whole margin before the first thermal cycle.
- Reading a free-text electrostatic note as an ESD declaration. Handling needs
  the category to pick controls, and prose does not resolve to one.
- Merging the arms into one pass or fail. An absent heading asks the purchaser
  to decide something; a breached limit asks the designer to change something,
  and a merged verdict sends both requests to whoever reads it first.

## Behavior contract (gate 3)

The required content set, the content audit, the reverse blocking margin, the
forward current derating, the junction temperature computation and its margin
test, the ESD category and the whole drawing verdict are exercised by the gate
3 contract test: scripts/test_e2008_external_diode_control_drawing.py against
scripts/e2008_external_diode_control_drawing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_external_diode_control_drawing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
