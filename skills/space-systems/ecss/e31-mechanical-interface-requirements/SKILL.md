---
name: e31-mechanical-interface-requirements
description: "Define the thermal-control to structure mechanical interface requirements of ECSS-E-ST-31C clause 4.3.2. Use when a unit baseplate, bracket or radiator mount has to be specified rather than assumed: turn bolt preload and contact area into a contact pressure, read the declared filler conductance off its pressure curve, compare the conductance the joint offers against the one the dissipation and the allowed baseplate rise demand, convert the expansion-coefficient mismatch over the qualification swing into an interface slip and an arcsecond alignment contribution, and roll interface hardware mass against its allocation. Refuses an undeclared filler or an undeclared interface mass. Trigger: ecss, e-st-31c, tcs-structure-mechanical-interface, mounting-interface-conductance, bolted-mount-thermal-conductance, interface-cte-mismatch, tcs-alignment-input, interface-hardware-mass-allocation."
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
  tags: [ecss, e-st-31-thermal-scope, e31-mechanical-interface-requirements, tcs-structure-mechanical-interface, mounting-interface-conductance, bolted-mount-thermal-conductance, interface-cte-mismatch, tcs-alignment-input, interface-hardware-mass-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Mechanical Interface Requirements (space-systems/ecss/e31-mechanical-interface-requirements)

Use when the task is writing or checking what the thermal control subsystem
requires of the structure subsystem under ECSS-E-ST-31C clause 4.3.2 — how a
dissipating item is mounted, how much heat that mount will actually pass,
what the expansion mismatch across it does to slip and alignment, and what
interface hardware mass the structure has to carry for it.

## Domain quick reference

- A mounting interface is a conductance, not a contact. The joint passes
  G = h(p) * A_eff watts per kelvin, where the coefficient h depends on the
  contact pressure the bolt pattern develops and on whatever filler is
  declared between the surfaces. Bare metal on metal, a filler pad, grease
  and an insulating washer stack sit two orders of magnitude apart at the
  same pressure, so naming the filler is part of the requirement.
- The conductance the design owes is set from the other side:
  G_req = Q / dT_allowed, the dissipation divided by the baseplate rise the
  thermal requirement permits above its mounting panel. Specifying a bolt
  torque without stating G_req leaves the structure free to satisfy the
  drawing and miss the thermal intent.
- Contact pressure is total preload over contact area, so bolt count and
  footprint are thermal parameters. Doubling the bolts at fixed area roughly
  doubles the pressure and moves the joint up its conductance curve; this is
  the cheapest lever the interface has and the one most often left implicit.
- An expansion-coefficient mismatch between an aluminium item and a
  carbon-fibre panel produces a differential growth |da| * dT * L at the
  outermost fastener over the qualification swing. That growth appears twice:
  as a slip the joint has to survive, and, divided by the lever arm to the
  reference feature, as an angular alignment contribution in arcseconds.
- Interface hardware — brackets, shims, fillers, fasteners, doublers — is
  thermal-control mass carried in the structure budget. An interface with no
  declared mass is unknown, not zero, and is refused rather than summed as
  nothing.

## Workflow

1. Validate every mounting interface record: bolt count as an integer of at
   least one, positive preload, positive contact and effective areas, a
   filler named in the declared option set.
2. Form the contact pressure from total preload over contact area, and
   interpolate the filler coefficient on its characterized pressure range.
   A pressure outside that range is refused, not extrapolated.
3. Multiply the coefficient by the effective contact area for the achieved
   conductance, form the required conductance from dissipation and allowed
   rise, and compare them with a named tolerance so an interface sized
   exactly on its requirement is not failed by representation error.
4. Compute the differential expansion at the outermost fastener from the two
   expansion coefficients, the qualification temperature swing and the
   footprint; grade it against the allowable interface slip.
5. Convert the same growth into an angular contribution about the lever arm
   to the reference feature and grade it against the arcsecond allocation
   the alignment budget gives the thermal interface.
6. Roll interface hardware mass across all mounts, apply the declared
   contingency, and compare with the structure subsystem allocation.
7. Report per-mount records, the mass roll-up and every finding: conductance
   shortfall, slip overrun, alignment overrun, mass overrun, or two mounts
   sharing a name so their records cannot be traced.

## Pitfalls

- Specifying a torque instead of a conductance. Torque is one input to the
  pressure, which is one input to the coefficient; the requirement the
  structure must meet is the W/K, and the torque is how it is achieved.
- Leaving the filler out of the interface control document. The same bolt
  pattern with an insulating washer stack instead of a filler pad drops the
  joint conductance by more than an order of magnitude and turns a compliant
  mount into a hot unit without a single drawing change.
- Sizing the joint on nominal contact area. The effective area that carries
  heat is smaller than the machined footprint; using the drawing area
  inflates the conductance and hides the shortfall.
- Treating the expansion mismatch as a stress problem only. The same growth
  is an alignment error for any item whose pointing is referenced through
  its mount, and the arcsecond contribution has to be handed to the
  alignment budget, not absorbed silently.
- Summing an interface with no declared hardware mass as zero. That
  understates the mass the structure carries for thermal control and is
  exactly the kind of silent omission a budget review cannot recover.

## Behavior contract (gate 3)

Interface record validation, contact pressure, filler-curve interpolation
with extrapolation refused, achieved and required conductance, differential
expansion, arcsecond alignment contribution, hardware mass roll-up and the
aggregate assessment are exercised by the gate 3 contract test:
scripts/test_e31_mechanical_interface_requirements.py against
scripts/e31_mechanical_interface_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e31_mechanical_interface_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
