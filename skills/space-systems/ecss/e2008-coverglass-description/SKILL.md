---
name: e2008-coverglass-description
description: "Use when a coverglass datasheet, drawing callout or procurement description has to be shown complete and self-consistent. Validate a coverglass description against ECSS-E-ST-20-08C clause 8.1.2: confirm the declared substrate is fused silica or a glass of that family rather than a transparent film, derive the areal mass and the shielding areal density the declared thickness actually buys, compute the Fresnel transmittance ceiling the substrate refractive index allows, and hold the declared transmittance against it so an impossible optical claim or an undeclared antireflective coating is caught instead of recorded. Trigger: ecss, e-st-20-08c-clause-8-1-2, coverglass-transparent-shield-description, fused-silica-substrate-admissibility, coverglass-fresnel-transmittance-ceiling, coverglass-areal-shielding-mass, coverglass-substrate-refractive-index."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c-clause-8-1-2, e2008-coverglass-description, coverglass-transparent-shield-description, fused-silica-substrate-admissibility, coverglass-fresnel-transmittance-ceiling, coverglass-areal-shielding-mass, coverglass-substrate-refractive-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Description (space-systems/ecss/e2008-coverglass-description)

Use when the task is to state what a coverglass is under
ECSS-E-ST-20-08C clause 8.1.2 and to show the description holds
together -- an admissible substrate, a thickness that buys real
shielding, and an optical claim the substrate can actually deliver.

## Domain quick reference

- A coverglass does two jobs at once and the description has to carry
  both. It passes the useful spectrum through to the junction, and it
  takes the particle and ultraviolet environment on itself so the cell
  and the adhesive underneath do not.
- The substrate is the description, not a footnote to it. Fused silica
  is the reference; a cerium-doped borosilicate, a drawn borosilicate
  microsheet and sapphire behave like it and belong to the same family.
  A transparent polymer film does not, however good its transmittance
  reads, and a description resting on one is rejected rather than
  graded.
- Thickness is bought in two currencies simultaneously. It sets the
  areal mass the array carries, density times thickness, and the same
  number converted into grams per square centimetre is what a shielding
  curve is read against. One multiplication gives both, and quoting a
  thickness without either is an incomplete description.
- The substrate fixes an optical ceiling before any coating exists. At
  normal incidence the two air-glass surfaces of a non-absorbing slab
  pass 2n/(n**2+1) of the incident light -- about 0.933 for fused
  silica, and noticeably less for sapphire because the higher index
  reflects harder at every surface.
- A claim above that ceiling with no antireflective coating declared is
  not an optimistic number, it is a description of something that does
  not exist. The usual cause is a coating the datasheet has and the
  description forgot, which is exactly the omission worth catching.
- An antireflective coating raises the ceiling but does not remove it.
  No coating cancels both surface reflections across the band, so a
  coated claim is still held against a policy ceiling short of unity.
- A transmittance under the policy floor and a thickness outside the
  usual coverglass band are queries, not rejections. They mean the item
  described may be something else; they do not make the description
  internally false.

## Workflow

1. Validate the description policy first: a thickness band with the
   high edge above the low one, a transmittance floor and a coated
   ceiling both inside the unit interval.
2. Check every required field is present -- substrate, thickness,
   average transmittance, coating stack -- and close as incomplete if
   any is absent, because nothing downstream can be derived without
   them.
3. Look the substrate up and stop on an inadmissible one, naming why it
   falls outside the fused-silica family rather than grading it anyway.
4. Normalise the coating stack, rejecting an unrecognised coating
   rather than dropping it silently.
5. Derive the areal mass from the declared or library density and the
   thickness, convert it to the shielding unit, and take the piece mass
   where a footprint was given.
6. Compute the uncoated ceiling from the substrate refractive index,
   pick the limit that applies -- the Fresnel ceiling bare, the policy
   ceiling once an antireflective coating is declared -- and compare.
   A claim landing exactly on the ceiling passes; the comparison
   absorbs representation error and the ceiling does not move.
7. Close on one verdict: incomplete, substrate not admissible,
   non-physical, queried, or complete -- reporting every finding, not
   only the one that set the verdict.

## Pitfalls

- Describing a coverglass by its coatings and leaving the substrate
  implicit. The substrate sets the optical ceiling, the density and the
  shielding, so a description without it cannot be checked at all.
- Accepting any transparent material because the transmittance looks
  good. A polymer film passes light and fails the job: it is not the
  glass shield the clause describes, and its admissibility is decided
  before any number is graded.
- Quoting transmittance with no coating statement. The same figure is
  physical on a coated glass and impossible on a bare one, so the
  coating stack is part of the optical claim rather than a separate
  line item.
- Treating an antireflective coating as licence for any number. The
  coated ceiling is lower than unity, and a claim near perfect
  transmission is a measurement or transcription error whatever the
  coating.
- Reading thickness as a purely optical parameter. It is the shielding
  variable, and a description that trims it for transmittance has moved
  the radiation margin without saying so.
- Comparing the declared transmittance with the ceiling by bare
  arithmetic. The ceiling comes out of a division, so a claim sitting
  exactly on it can land a unit in the last place above; the comparison
  tolerates that while the ceiling itself stays untouched.

## Behavior contract (gate 3)

The policy validation, substrate lookup and admissibility, coating
normalisation, surface reflectance and uncoated transmittance ceiling,
areal mass, shielding areal density, piece mass, transmittance
admissibility and the description verdict are exercised by the gate 3
contract test: scripts/test_e2008_coverglass_description.py against
scripts/e2008_coverglass_description_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
