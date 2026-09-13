---
name: e20-lens-material-properties
description: "Use when compute the reflective and transmissive behaviour of a lens-antenna dielectric material and the resulting antenna impact under ECSS-E-ST-20C clause 7.2.2.3.3: categorize the lens material as a low-loss-thermoplastic, dielectric-foam, ceramic-dielectric or artificial-dielectric, read its relative-permittivity and loss-tangent, compute the air-to-dielectric interface-reflectance at the illuminated and exit faces, design or check a quarter-wave matching-layer, turn the loss-tangent and the ray-path-length into a dielectric-absorption-loss, convert a permittivity-tolerance into a lens-aperture-phase-error and its gain-loss, translate the reflected wave into a feed-return-loss, and compare the summed lens-loss against its allocation. Trigger: ecss, e-st-20-electrical-scope, e-st-20c-clause-7-2-2-3-3, lens-material-properties, relative-permittivity, dielectric-loss-tangent, quarter-wave-matching-layer, dielectric-absorption-loss, lens-aperture-phase-error."
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
  tags: [ecss, e-st-20-electrical-scope, e20-lens-material-properties, relative-permittivity, dielectric-loss-tangent, quarter-wave-matching-layer, dielectric-absorption-loss, lens-aperture-phase-error, feed-return-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Lens Material Properties (space-systems/ecss/e20-lens-material-properties)

Use when the task is the clause 7.2.2.3.3 lens-material step of
ECSS-E-ST-20C -- quantifying how much of the wave a lens material
reflects at its faces and how much it absorbs on the way through, and
turning both, together with the spread on its permittivity, into the
loss and the phase error the antenna prediction has to carry.

## Domain quick reference

- A lens material is categorized once into a family, because the
  family sets the range of behaviour to expect. A
  low-loss-thermoplastic sits a little above the permittivity of free
  space with a small loss-tangent. A dielectric-foam sits just above
  free space, so its faces barely reflect, at the cost of a weak
  refracting power that demands a thick lens. A ceramic-dielectric
  refracts strongly in a thin part and reflects hard at both faces. An
  artificial-dielectric synthesises an effective permittivity from a
  lattice, and that effective value can sit below free space, which
  changes what a matching-layer can be made of. A material outside the
  families is rejected.
- Both faces matter and they behave differently from a reflecting
  surface. The fraction reflected at an air-to-dielectric interface
  follows from the contrast in refractive index, that index being the
  square root of the relative-permittivity, so the reflected fraction
  grows quickly with permittivity: a foam gives a fraction of a
  percent per face and a ceramic gives a quarter of the power. What is
  reflected is lost twice over, once from the transmitted beam and
  once because the illuminated face sends a wave straight back at the
  feed, where it appears as a feed-return-loss and pulls the feed off
  its match.
- A quarter-wave matching-layer cancels the face reflection when its
  permittivity is the geometric mean of the two media it sits between
  and its thickness is a quarter wavelength measured inside that
  layer. The mean condition is the whole design: a layer of the wrong
  permittivity leaves a residual reflection even at exact quarter-wave
  thickness. A lens whose effective permittivity sits below free space
  needs a matching-layer permittivity below free space too, which no
  natural dielectric provides.
- Dielectric-absorption-loss is the loss-tangent working along the ray
  path. It scales with the loss-tangent, with the square root of
  permittivity and with the path length in wavelengths, so the same
  material is negligible in a thin low-frequency lens and a real term
  in a thick high-frequency one. The ray path, not the axial
  thickness, is the length that counts.
- The spread on the permittivity is a phase error, not a loss. A batch
  tolerance changes the electrical length of the lens, the error grows
  with thickness in wavelengths, and the resulting
  lens-aperture-phase-error costs gain by the same square-law relation
  used for a reflector surface error. Absorption, face reflection and
  phase error then sum into the lens-loss compared against the
  allocation.

## Workflow

1. Categorize the lens material into its family and take its
   relative-permittivity and loss-tangent; reject a material outside
   the family set.
2. Compute the interface reflectance of the illuminated face, either
   bare or through the proposed matching-layer, and convert it into
   the wave returned toward the feed.
3. Compute the transmission loss of both faces from the same
   reflectance.
4. Where a matching-layer is required, derive its permittivity as the
   geometric mean and its thickness as a quarter wavelength inside it;
   reject a design whose required permittivity is below free space.
5. Convert the loss-tangent, the permittivity and the ray-path-length
   into a dielectric-absorption-loss.
6. Convert the permittivity tolerance and the lens thickness into a
   lens-aperture-phase-error and that error into a gain-loss.
7. Sum the face, absorption and phase-error terms into the lens-loss,
   compare it against the allocation, and compare the feed-return-loss
   against its requirement.
8. Aggregate the findings; the lens material is acceptable only when
   the list is empty.

## Pitfalls

- Counting the face reflection once. A lens has an illuminated face
  and an exit face, and the transmitted beam pays at both.
- Treating the reflected wave as only a loss term. It travels back
  along the axis into the feed, so a bare ceramic face can wreck a
  feed match that looked comfortable on its own.
- Designing the matching-layer thickness in free-space wavelengths.
  The quarter wave is measured inside the layer, so the physical part
  is thinner by the square root of the layer permittivity.
- Choosing a matching-layer permittivity by what is available in the
  workshop. Away from the geometric mean the residual reflection comes
  straight back, and a layer a long way off can be worse than no layer
  at all.
- Using the axial thickness as the absorption path. Off-axis rays
  travel farther through the material, so the axial figure understates
  the loss at the aperture edge.
- Reading a permittivity tolerance as a loss. It is a phase error, it
  scales with lens thickness in wavelengths, and a batch spread that
  is harmless in a thin lens dominates the budget in a thick one.

## Behavior contract (gate 3)

The material-family categorization, interface-reflectance,
quarter-wave matching-layer, face transmission loss,
dielectric-absorption-loss, permittivity-tolerance phase error,
phase-error gain loss, feed-return-loss and lens-loss allocation logic
is exercised by the gate 3 contract test:
scripts/test_e20_lens_material_properties.py against
scripts/e20_lens_material_properties_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e20_lens_material_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
