---
name: q7080-ndt-of-am-parts
description: "Determine the non-destructive inspection suite an additively manufactured part needs, and whether the declared setup can actually find the flaw that matters. Use when a build is released against ECSS-Q-ST-70-80C inspection and the ECSS-Q-ST-70-15C method set: size the tomography voxel from the cone-beam geometry, take the ultrasonic resolution from the wavelength, grow the radiographic limit with the flaw tilt, strike out methods a rough as-built surface or an enclosed channel defeats, then compare the smallest detectable flaw against the fracture-control critical flaw on the coverage the criticality category demands. Trigger: ecss, q-st-70-80-additive-manufacturing-scope, am-part-ndt-suite, ct-voxel-detectability, ultrasonic-lack-of-fusion-detection, radiographic-flaw-tilt, am-enclosed-channel-inspectability, am-volumetric-coverage-category."
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
  tags: [ecss, q-st-70-80-additive-manufacturing-scope, q7080-ndt-of-am-parts, am-part-ndt-suite, ct-voxel-detectability, ultrasonic-lack-of-fusion-detection, radiographic-flaw-tilt, am-enclosed-channel-inspectability, am-volumetric-coverage-category]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — NDT of Built Parts (space-systems/ecss/q7080-ndt-of-am-parts)

Use when the task is the inspection step of ECSS-Q-ST-70-80C on an
additively manufactured part -- choosing the non-destructive methods,
in the method set of ECSS-Q-ST-70-15C, that a criticality category
demands, and showing that the setup actually named in the procedure
resolves a flaw smaller than the one fracture control calls critical.

## Domain quick reference

- A built part carries defect populations a wrought part does not:
  lack-of-fusion between tracks or layers, gas porosity carried in from
  the feedstock, unfused powder trapped in an internal channel, and
  cracking driven by the thermal gradient of the build. The volumetric
  requirement exists because of those populations, and they also decide
  which method can see them.
- Tomography is the only method that reaches the wall of an enclosed
  channel. Its resolution is geometric: the voxel is the detector pixel
  divided by the magnification, and the magnification is the detector
  distance over the object distance. A bulky part cannot be brought
  close to the source, so size costs resolution before any setting is
  touched, and a long radiographic path starves the reconstruction in
  the core whatever the voxel says.
- Ultrasound is the sharpest instrument against a planar lack-of-fusion
  flaw, and the least tolerant of an as-built surface. A shot-blasted
  or unmachined skin does not couple, and an enclosed channel gives no
  clean back-wall path, so the method is credited only on a machined,
  externally swept feature.
- Radiographic contrast comes from the material the flaw removes along
  the beam. A planar flaw lying square to the beam is nearly invisible,
  and the smallest flaw still visible grows with the reciprocal cosine
  of the tilt between beam and flaw plane. The build orientation
  therefore fixes the radiographic sensitivity, because it fixes where
  the lack-of-fusion planes lie.
- Detectability is only half the verdict. The other half is coverage:
  the criticality category says whether every part is volumetrically
  inspected, a sampled fraction is, or the surface alone is enough.
- Where the smallest detectable flaw is larger than the critical flaw,
  the answer is never a looser acceptance limit. It is a better setup,
  a machined scan surface, a different build orientation, or a proof
  test that substitutes for the inspection.

## Workflow

1. Declare the part criticality category and read the coverage it
   demands. Reject an uncategorized part rather than defaulting it,
   because coverage and sampling both hang off this one value.
2. Take the critical flaw size from the fracture-control assessment.
   This is the requirement the inspection is measured against, and it
   is an input to the inspection, never an output of it.
3. Size each candidate method from its declared setup: the voxel from
   the cone-beam geometry, the ultrasonic limit from the wavelength at
   the probe frequency, the radiographic limit from the section
   thickness and the flaw tilt.
4. Strike out the methods this part defeats -- a radiographic path
   beyond what the source penetrates, a surface too rough to couple, an
   enclosed channel with no back-wall path -- and record the reason,
   not just the exclusion.
5. Credit only a method that is both applicable and resolving, and
   compare the best credited detectable flaw with the critical flaw.
6. Close with a verdict: coverage demonstrated, surface inspection
   sufficient for the category, or coverage not demonstrated with the
   named shortfall and the setup change that would close it.

## Pitfalls

- Reading a tomography scan as if resolution were a machine property.
  It is a geometry: the same machine gives a coarse voxel on a large
  part because the part cannot be brought near the source, and quoting
  the machine's best voxel on a bulky bracket overstates detectability
  by the whole magnification ratio.
- Crediting ultrasound on an as-built surface. The coupling is lost
  before the pulse enters, so the procedure passes with no sensitivity
  at all, and the failure is silent because a clean scan and a blind
  scan look alike.
- Taking a radiographic sensitivity figure as if flaw orientation did
  not matter. Lack-of-fusion is planar and lies with the layers, so a
  build orientation chosen for support reasons can render the dominant
  defect population invisible to the very method chosen to find it.
- Treating an enclosed channel as inspected because the part was
  scanned. Powder left unfused inside a channel reads as parent
  material on a projection, so the evidence that the channel is clear
  comes from tomography or from flow and endoscopic checks, not from a
  radiograph.
- Comparing the detectable flaw with the critical flaw by bare
  arithmetic. Both are built from divisions and a cosine, so a setup
  meant to sit exactly on the limit can land a few units in the last
  place above it; the comparison absorbs that representation error
  while the critical flaw size stays untouched.

## Behavior contract (gate 3)

The voxel geometry, ultrasonic and radiographic detectability, method
applicability, coverage selection and the inspection verdict are
exercised by the gate 3 contract test:
scripts/test_q7080_ndt_of_am_parts.py against
scripts/q7080_ndt_of_am_parts_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7080_ndt_of_am_parts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
