---
name: e20-susceptible-payload-magnetic-limits
description: "Use when determine the maximum static magnetic field a direct-current-sensitive payload unit may be exposed to under ECSS-E-ST-20C clause 6.3.7.2: categorize the unit by how strongly a steady field degrades it, take the allowable static field at its reference point, convert every onboard source (permanent magnet, harness current loop, magnetorquer remanence, latching relay, soft-magnetic part) into an equivalent dipole moment, propagate each dipole to the unit along its axial or equatorial direction, combine the contributions worst-case or by root-sum-square, apply the required design margin, and solve the minimum separation distance a dominant source needs to respect the limit. Trigger: ecss, e-st-20c-clause-6-3-7-2, static-magnetic-field-limit, dc-magnetic-susceptibility, magnetic-dipole-moment, payload-magnetic-limit, magnetic-separation-distance, magnetic-source-inventory, magnetorquer-remanence."
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
  tags: [ecss, e-st-20-electrical-scope, e20-susceptible-payload-magnetic-limits, static-magnetic-field-limit, dc-magnetic-susceptibility, magnetic-dipole-moment, payload-magnetic-limit, magnetic-separation-distance, magnetorquer-remanence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Susceptible Payload Magnetic Limits (space-systems/ecss/e20-susceptible-payload-magnetic-limits)

Use when the task is the clause 6.3.7.2 static magnetic limit of
ECSS-E-ST-20C -- fixing the largest steady (direct current) magnetic
field that may appear at a payload unit whose performance degrades in
such a field, and checking the onboard magnetic sources against it.

## Domain quick reference

- The clause is about the *static* field only: the steady component
  produced by permanent magnets, remanent magnetization and
  direct-current loops, not the alternating emissions covered by the
  radiated-susceptibility clauses. A unit that passes a radiated
  susceptibility sweep can still be out of specification here, because
  the sweep never dwells at zero hertz.
- Each payload unit is categorized once by how strongly a steady field
  degrades it, and that category sets a default allowable field at the
  unit's reference point: a science magnetometer or fluxgate sensor
  sits at the single-nanotesla level, an atomic frequency standard or
  an optically pumped sensor around ten nanotesla, a star tracker head
  or a charged-particle analyser around a hundred, an imaging detector
  or wheel drive electronics around a thousand, and a purely digital
  processing unit an order beyond that. A unit-specific limit supplied
  by the payload provider always supersedes the category default; the
  default exists so an unanswered unit still gets a number.
- Every magnetic source is reduced to one equivalent dipole moment in
  ampere square metres. A permanent magnet, a magnetorquer's remanent
  moment, a latching relay and a soft-magnetic part carry that moment
  directly from measurement; a harness or circuit current loop has a
  moment equal to its turns, its enclosed area and its steady current
  multiplied together, which is why a single badly routed return
  conductor can dominate the whole budget.
- A dipole's static field falls with the cube of distance. On the
  dipole axis the field is twice the equatorial value at the same
  distance, so an unresolved orientation must be treated axially --
  that is the worst case, and it is the default. Contributions are
  combined either by direct sum (no orientation knowledge, the
  conservative reading) or by root-sum-square (independent, randomly
  oriented sources).
- Because the field scales as the inverse cube, the useful design
  output is a separation distance: the cube root of the dipole moment
  and the orientation factor over the target field. Halving a
  requirement moves the source only about twenty-six percent further
  out, which is why distance alone rarely rescues a source that is an
  order of magnitude over.

## Workflow

1. Categorize each direct-current-sensitive payload unit by its kind
   and take its allowable static field: the unit-specific number if
   the payload provider supplied one, otherwise the category default.
   Reject a unit kind that is not on the susceptibility list.
2. Inventory every static magnetic source with its distance to the
   unit reference point and its orientation, and reduce each one to an
   equivalent dipole moment -- directly for a magnet, a remanent
   moment or a relay, and as turns times area times current for a
   circuit loop. Reject an unrecognized source kind.
3. Propagate each dipole to the unit: axial for a source whose axis
   points at the unit, equatorial for a source known to be broadside,
   worst case (axial) whenever the orientation is not established.
4. Combine the contributions -- direct sum when orientations are
   unknown, root-sum-square when the sources are independent -- and
   compare the total against the allowable field divided by the
   required design margin factor.
5. For each source individually, solve the minimum separation distance
   that meets the margined limit and flag any source mounted closer
   than that distance; this is the finding that drives layout.
6. Flag a sensitive unit that carries magnetic sources but no
   unit-specific allowable field on record -- the category default
   kept the assessment running, it did not close the requirement.
7. Aggregate the field, separation and record findings; the unit is
   magnetically acceptable only when all three lists are empty.

## Pitfalls

- Reading a radiated-susceptibility pass as covering this clause. The
  swept susceptibility campaign starts well above zero hertz; the
  static limit is a separate requirement with a separate verification.
- Taking the equatorial field because the source is "roughly to the
  side". Until the orientation is fixed by layout, the axial factor of
  two applies, and using the equatorial value understates every
  contribution by half.
- Root-sum-squaring contributions whose orientations are unknown. The
  statistical combination is only legitimate for independent, randomly
  oriented sources; with an unknown but possibly common orientation
  the direct sum is the honest number.
- Comparing the summed field against the bare allowable limit and
  calling a result at ninety-nine percent a pass. The margin factor is
  part of the requirement, so the comparison is always against the
  limit divided by that factor.
- Solving a separation distance from the unmargined limit and then
  quoting it as the mounting rule -- the distance must be derived from
  the same margined target as the field check, or the layout silently
  consumes the margin.
- Treating a current loop's moment as fixed. It scales with the steady
  current, so a unit that is compliant in a low-power mode can breach
  the limit in the high-current mode nobody assessed.

## Behavior contract (gate 3)

The unit categorization, allowable-field selection, dipole-moment
reduction, inverse-cube propagation, contribution combination,
separation-distance and margin logic is exercised by the gate 3
contract test:
scripts/test_e20_susceptible_payload_magnetic_limits.py against
scripts/e20_susceptible_payload_magnetic_limits_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_susceptible_payload_magnetic_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
