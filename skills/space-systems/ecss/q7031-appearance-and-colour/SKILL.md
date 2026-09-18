---
name: q7031-appearance-and-colour
description: "Verify the colour and appearance of an applied space-hardware paint against what the drawing specified. Use when a painted panel has to be graded before acceptance: compute the CIELAB difference against the reference chip and test it against the contract tolerance, test specular gloss against its band, tally appearance defects by mechanism family and by density over the inspected area, and, on a thermal-control finish, test solar absorptance and infrared emittance against their bands because a colour match alone never proves the radiative property the coating exists for. Trigger: ecss, q-st-70-31c-painting-scope, paint-appearance-verification, thermal-control-paint-colour, coating-colour-difference-tolerance, paint-specular-gloss-band, coating-appearance-defect-density, paint-solar-absorptance-emittance-band."
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
  tags: [ecss, q-st-70-31c-painting-scope, q7031-appearance-and-colour, paint-appearance-verification, thermal-control-paint-colour, coating-colour-difference-tolerance, paint-specular-gloss-band, coating-appearance-defect-density, paint-solar-absorptance-emittance-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Painting — Appearance and Colour (space-systems/ecss/q7031-appearance-and-colour)

Use when the task is the appearance and colour verification ECSS-Q-ST-70-31C
asks for on painted space hardware: a coat has been applied and cured, a
colour or finish was specified for it, and the question is whether the surface
in front of the inspector is the surface the drawing called out.

## Domain quick reference

- Colour is verified against a reference, never against an impression. The
  measurement and the reference are both CIELAB triples and the difference
  between them is a single number that can be put against a contract
  tolerance, which is what makes the check repeatable between inspectors and
  between sites.
- A difference sitting exactly on the tolerance is accepted. The tolerance is
  the last accepted value, not the first rejected one, and a decimal tolerance
  compared against a square root lands either side of the bound depending on
  the maths library, so the comparison absorbs that noise and nothing more.
- Gloss is a separate specification from colour. Two panels can match the
  chip and differ in specular gloss, which changes how a surface scatters and
  how the same pigment reads to the eye, so gloss carries its own band.
- Appearance defects are grouped by the mechanism that produced them, because
  the mechanism names the fix. Runs, sags and curtains are flow defects from
  too much wet film; orange-peel and dry-spray are atomization defects from
  gun setting or distance; craters, fish-eyes and blisters point at surface
  contamination; inclusions and fibres at facility cleanliness; mottling and
  streaking at pigment dispersion.
- Two defect rules run side by side. A density limit per square metre grades
  the cosmetic population, while defects that betray a broken film -- blister,
  pinhole, crater, fish-eye -- are refused on a count of one, because a
  discontinuity is not made acceptable by being rare.
- On a thermal-control finish the colour is the visible half of a radiative
  specification. The panel also owes measured solar absorptance and infrared
  emittance against their bands, and a panel that matches its chip while
  sitting outside either band has failed the property the coating is for.

## Workflow

1. Confirm what was specified for the area: reference colour, colour
   tolerance, gloss band, defect density limit, and -- when the finish is
   thermal-control -- the absorptance and emittance bands.
2. Validate each measurement before using it. A lightness outside the closed
   zero-to-hundred scale or an opponent axis past any real gamut is a
   transcription error and is refused rather than graded.
3. Compute the CIELAB colour difference against the reference and put it
   against the tolerance, treating a value on the bound as a pass.
4. Put the specular gloss reading against its band. Record a missing band or a
   missing reading as an unverified finding, never as a pass.
5. Tally appearance defects by name, resolve each to its mechanism family,
   divide the total by the inspected area for the density, and raise every
   film-integrity defect individually alongside any density exceedance.
6. On a thermal-control finish, grade absorptance and emittance against their
   bands and raise an unmeasured property as its own finding.
7. Disposition the area: accepted with no findings; rework where colour,
   gloss, band or film integrity failed; review where only the evidence is
   incomplete. Aggregate across the survey, which passes only when every area
   carries no open finding.

## Pitfalls

- Signing off colour by eye against a chip under whatever light the bay has,
  which cannot produce a number a second inspector reproduces.
- Reading a difference that lands on the tolerance as a failure, or widening
  the tolerance to make a genuine miss pass. Neither is the clause.
- Treating a colour match as proof of a thermal-control finish. Absorptance
  and emittance are the specification; the colour is how it happens to look.
- Averaging film-integrity defects into the cosmetic density, where a single
  blister disappears into a per-square-metre number that still reads green.
- Grading a large panel on one measurement point and a small fitting on the
  same point count, so the density has no comparable basis.
- Leaving gloss unmeasured because the colour matched, then discovering at
  system level that the finish scatters differently from the qualification
  coupon.

## Behavior contract (gate 3)

The CIELAB colour difference and tolerance comparison, gloss band check,
appearance defect grouping and density, film-integrity refusal, thermo-optical
band grading and the area and survey dispositions are exercised by the gate 3
contract test: scripts/test_q7031_appearance_and_colour.py against
scripts/q7031_appearance_and_colour_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_appearance_and_colour.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
