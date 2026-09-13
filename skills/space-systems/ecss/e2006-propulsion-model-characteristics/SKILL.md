---
name: e2006-propulsion-model-characteristics
description: "Use when verify that a spacecraft-propulsion-interaction simulation represents every model element ECSS-E-ST-20-06C clause 11.3.2 enumerates: categorize each declared element into its family - outer-geometry, thruster-source, power-subsystem or grounding-reference - list the required elements no declaration covers, check the computational-mesh cell-size against the Debye-length of the modelled plasma, reconcile the declared beam-current with the thrust and beam-voltage the thruster model asserts, sum the grounding return-path resistance against its limit, and confirm the structure potential is free to float rather than clamped to an artificial reference. Trigger: ecss, e-st-20-electrical-scope, propulsion-model-characteristics, plume-interaction-simulation, debye-resolved-mesh, beam-current-consistency, grounding-return-path, structure-potential-reference."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-propulsion-model-characteristics, plume-interaction-simulation, debye-resolved-mesh, beam-current-consistency, grounding-return-path, structure-potential-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electric Propulsion — Propulsion Model Characteristics (space-systems/ecss/e2006-propulsion-model-characteristics)

Use when the task is the clause 11.3.2 content check of ECSS-E-ST-20-06C: the
simulation that predicts the interaction between an electric-propulsion plume
and its spacecraft has to represent a named set of elements, and the model
declaration is audited against that set before any result of the simulation is
used as evidence.

## Domain quick reference

- The enumerated elements group into four families. Outer-geometry covers the
  spacecraft envelope, the solar-array panel surfaces, the thruster location
  and orientation, and the surfaces whose potential or contamination is being
  predicted. Thruster-source covers the beam ion energy distribution, the
  beam-current and divergence, the neutral efflux, the charge-exchange ion
  population it feeds, and the neutralizer electron source. Power-subsystem
  covers the solar-array string voltage distribution, the exposed-conductor
  inventory and the deliberately-biased surface potentials. Grounding-reference
  covers the structure ground reference, the return-path resistance, the
  neutralizer coupling to the ambient plasma and the boundary condition that
  lets the structure potential float.
- Optional elements exist in the same families (appendage booms, harness
  routing, beam-dump surfaces) and are recognized without being required, so a
  declaration that names them is categorized rather than rejected. What makes
  a declaration incomplete is a required element with nothing covering it.
- A plume-interaction solver resolves space-charge only when the mesh
  cell-size is at or below the Debye-length of the modelled plasma. The
  Debye-length follows from the plasma density and the electron temperature,
  so the mesh criterion is derived from the physics the model itself declares,
  never assumed from the geometry scale.
- The thruster-source declaration is internally checkable: the beam-current
  that produces a stated thrust at a stated beam-voltage follows from the ion
  mass, so a declared beam-current that disagrees with the declared thrust is
  a model defect visible before the solver runs.
- The grounding-reference declaration is checkable the same way: the
  return-path resistance is the sum of its segments against the limit, and a
  structure potential clamped to an artificial reference reproduces a ground
  facility, not a free-flying spacecraft.

## Workflow

1. Categorize every declared element into its family and reject an element
   identifier that is not recognized in any family.
2. List, per family, the required elements that no declaration covers; a model
   with any uncovered required element is incomplete regardless of how well
   the remaining elements are resolved.
3. Compute the Debye-length from the declared plasma density and electron
   temperature, and check the mesh cell-size against it at the declared cells
   per Debye-length; a cell-size that equals the limit is resolved.
4. Derive the beam-current implied by the declared thrust, beam-voltage and
   ion mass, and compare it with the declared beam-current at the agreed
   relative tolerance.
5. Sum the grounding return-path segment resistances and compare the total
   against the declared limit.
6. Check the structure potential boundary condition: only a floating reference
   represents the flight case; a clamped or fixed reference is recorded as a
   finding.
7. The model is representative only when the element list is complete, the
   mesh is Debye-resolved, the beam-current is consistent, the return path is
   within its limit and the potential floats.

## Pitfalls

- Auditing the element list and stopping there. A complete list with a mesh
  coarser than the Debye-length predicts a smoothed sheath and understates
  every local potential the clause cares about.
- Assuming the mesh criterion from the spacecraft size. The Debye-length
  depends on the plasma density and electron temperature the model declares,
  and a denser plume shortens it by the square root of the density ratio.
- Accepting a declared beam-current because it "looks right". It is fixed by
  the declared thrust, beam-voltage and ion mass, so the check costs nothing
  and catches a transposed unit or a wrong propellant immediately.
- Declaring a structure ground reference and calling grounding represented.
  The return-path resistance and the neutralizer coupling are separate
  required elements, and a model with a ground node but no coupling cannot
  produce a floating potential at all.
- Relaxing the Debye or resistance limit to clear a case that sits exactly on
  it. A value that equals its limit to within the named representation
  tolerance passes by absorbing floating-point error - a summed segment list
  routinely lands a few units in the last place above its own total - never by
  moving the limit.

## Behavior contract (gate 3)

The element categorization, completeness, Debye-length, mesh-resolution,
beam-current consistency, grounding return-path and potential-reference logic
is exercised by the gate 3 contract test:
scripts/test_e2006_propulsion_model_characteristics.py against
scripts/e2006_propulsion_model_characteristics_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_propulsion_model_characteristics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
