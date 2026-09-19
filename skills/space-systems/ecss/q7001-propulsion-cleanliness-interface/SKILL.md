---
name: q7001-propulsion-cleanliness-interface
description: "Derive the governing cleanliness requirement at each propulsion fluid interface and say which specification imposed it. Use when a system cleanliness plan meets the propulsion subsystem and the two particle-size and non-volatile-residue limits have to be reconciled interface by interface, the filter sized from the smallest flow passage behind it, the passage-area blockage of a governing-limit particle quantified, and the tightest interface rolled up into the single pair the flushing and acceptance tests are built around. Trigger: ecss, q-st-70-01c, e-st-35-06c, propulsion-cleanliness-interface, governing-particle-size-limit, propellant-filter-rating-sizing, flow-passage-blockage-fraction, non-volatile-residue-reconciliation."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-propulsion-cleanliness-interface, governing-particle-size-limit, propellant-filter-rating-sizing, flow-passage-blockage-fraction, non-volatile-residue-reconciliation, propulsion-interface-flow-down]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Propulsion Interface (space-systems/ecss/q7001-propulsion-cleanliness-interface)

Use when the task sits on the boundary between the sensitive-hardware
cleanliness provisions of ECSS-Q-ST-70-01C and the propulsion-subsystem
cleanliness requirements of ECSS-E-ST-35-06C: deciding, per fluid interface,
which document's limit actually governs, whether the installed filter earns
that limit, and what the tightest interface makes the system-level number.

## Domain quick reference

- Two specifications meet at every fluid interface and they are written for
  different reasons. The system cleanliness specification flows a limit down
  from a vehicle-level allocation; the propulsion specification imposes one
  from the physics of the smallest passage it has to protect. Neither is
  automatically the stricter.
- The answer per interface is a pair — the governing particle-size limit and
  the governing non-volatile-residue limit — each with the document it came
  from. An interface where the propulsion side governs is not closed by
  argument; it is a flow-down that has to be tightened.
- The filter is sized by the passage, not by the limit. The coarsest usable
  rating is the smallest flow passage divided by a declared safety factor, and
  the installed filter has to satisfy both that rating and the governing
  particle limit. Those two can disagree, and both are findings.
- Particle size only becomes an engineering consequence through area. A
  particle at the governing limit blocks the square of its diameter ratio of
  the passage, which is what turns a cleanliness statement into a flow-rate or
  thrust-degradation statement the propulsion engineer can use.
- Residue is the other half and is often the binding one. A non-volatile
  residue that is harmless on a bracket can be a propellant-compatibility or
  catalyst-poisoning problem in a feed line, so it is reconciled on its own
  and not folded into the particle argument.

## Workflow

1. Validate every declared fluid interface: name, smallest flow passage,
   installed filter rating, both particle-size limits, both residue limits,
   the filter safety factor and the allowable passage blockage.
2. Per interface, take the more stringent particle limit and the more
   stringent residue limit, recording which document each came from and
   resolving a genuine tie to the system specification.
3. Size the filter the passage needs from the passage and the safety factor,
   and check the installed rating against that number and against the
   governing particle limit separately.
4. Compute the passage-area fraction a governing-limit particle occupies and
   compare it with the allowable blockage.
5. Raise a finding wherever the propulsion side governs, the filter is too
   coarse for the passage, the filter passes particles above the governing
   limit, or the blockage exceeds its allowable.
6. Roll the interfaces up: the tightest governing particle limit and the
   tightest governing residue limit become the system numbers, each named
   with the interface that drove it, and every propulsion-driven interface is
   listed for the flow-down update.
7. Refuse duplicate interface names; a roll-up nobody can trace back to one
   interface is not a roll-up.

## Pitfalls

- Assuming the system specification is always the stricter. It is an
  allocation, not a physics limit, and a small thruster orifice routinely
  demands more than the vehicle-level number ever asked for.
- Sizing the filter from the cleanliness limit alone. The limit says what may
  be present; the passage says what may pass. A filter that satisfies the
  limit can still be too coarse for the orifice behind it.
- Reporting a governing limit without its source. The number alone cannot
  tell the next reviewer whether the flow-down needs changing or whether the
  interface was already covered.
- Folding residue into the particle argument. Residue drives propellant
  compatibility and catalyst life, not blockage, and a combined cleanliness
  statement hides which of the two is actually binding.
- Taking the tightest number as the system requirement and stopping. The
  interface that drove it has to be named, or the next design change quietly
  moves the driver and nobody notices the system number is now wrong.

## Behavior contract (gate 3)

The interface validation, governing particle and residue selection with
source attribution and tie handling, filter rating sizing, filter checks
against both the passage and the governing limit, passage-blockage fraction,
and the multi-interface roll-up with its duplicate-name refusal are exercised
by the gate 3 contract test:
scripts/test_q7001_propulsion_cleanliness_interface.py against
scripts/q7001_propulsion_cleanliness_interface_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_propulsion_cleanliness_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
