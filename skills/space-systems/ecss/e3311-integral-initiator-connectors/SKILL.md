---
name: e3311-integral-initiator-connectors
description: "Verify an initiator that carries its own integral connector against ECSS-E-ST-33-11C clause 4.11.3. Use when the task is deciding whether a connector built into the initiator body can be trusted: adding the mated contact resistances into the firing loop and grading the delivered current against the all-fire current, confirming the pins stay shorted until mate and that pin-to-shell insulation holds, grading rated mate-demate cycles against the planned handling count plus margin, reading shell bonding continuity and integral-seal leak rate, and proving the keying makes a cross-connection between two firing circuits impossible by hand. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, integral-initiator-connector, initiator-firing-loop-resistance, initiator-connector-keying-uniqueness, initiator-pin-shorting-provision, initiator-connector-mate-demate-life, initiator-connector-seal-leak-rate."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-integral-initiator-connectors, integral-initiator-connector, initiator-firing-loop-resistance, initiator-connector-keying-uniqueness, initiator-pin-shorting-provision, initiator-connector-mate-demate-life, initiator-connector-seal-leak-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Integral Initiator Connectors (space-systems/ecss/e3311-integral-initiator-connectors)

Use when the task is the connector screen of ECSS-E-ST-33-11C clause
4.11.3 -- an initiator whose electrical interface is built into the
device rather than terminated onto it, so the connector cannot be
inspected, reworked or replaced without handling live explosive.

## Domain quick reference

- An integral connector is part of the initiator, and that single fact
  drives the whole clause. Everything that would be a harness problem
  elsewhere becomes a device problem here, because the remedy for a
  bad connector is scrapping an energetic part, not re-terminating a
  cable.
- The mated contact resistances sit inside the firing loop. They are
  graded twice: once for their own value, and once as a share of the
  loop, because a connector that is within its own limit can still be
  the dominant term in a low-resistance bridgewire circuit.
- The delivered current is the quantity the clause actually cares
  about, and it is computed, not declared: the source voltage divided
  by the summed series resistance, then read against the all-fire
  current with the required margin on top.
- The pin shorting provision is the only barrier between a handling
  discharge and the bridgewire while the unit is demated. It is a
  boolean, but it is the boolean that most often turns out to be
  absent on a connector that was chosen for its contact count.
- Mate-demate life is graded against the planned handling count with
  a margin, because integration, retest and launch-site work each
  consume cycles that the design count was never told about.
- Keying is a set-level property, never a unit-level one. A key is
  only a barrier if no second circuit accepts it, so the check runs
  across the whole set and reports the pair, not the code.
- Shell bonding and the integral seal close the two paths that do not
  run through the contacts: the shield return, and the leak path into
  a device whose internal atmosphere is part of its qualification.

## Workflow

1. Normalize the unit list, rejecting a duplicate identifier, a
   connector declaring fewer than two contacts, or a unit with no
   circuit and keying declaration, because an unkeyed unit cannot be
   graded against its neighbours.
2. Build the firing loop for each unit -- source, harness, contacts,
   bridgewire -- and divide the source voltage by it to get the
   delivered current rather than accepting a quoted figure.
3. Grade that current against the all-fire current with the required
   margin, then grade the contact resistance on its own value and as
   a share of the loop, reporting the three findings separately.
4. Check the pin shorting provision, the pin-to-shell insulation, the
   rated mate-demate cycles against the planned count plus margin, the
   shell bonding resistance and the integral-seal leak rate.
5. Walk the whole set for keying: group the units by keying code and
   report any code serving more than one firing circuit, naming the
   units and the circuits involved.
6. Close with the accepted and rejected units, the keying conflicts,
   and the overall verdict, treating a keying conflict as fatal even
   when every individual unit passed its own gates.

## Pitfalls

- Grading the connector against a contact-resistance limit alone. The
  limit is a component specification; what the clause needs is the
  effect on the firing loop, and a 5 milliohm contact is negligible in
  a 5 ohm loop and dominant in a 50 milliohm one.
- Accepting a quoted delivered current. The figure usually predates
  the harness routing, and the connector contacts are the term that
  gets added last and recorded least.
- Reading the all-fire current as the level to reach. It is the level
  to clear with margin, and a design that merely reaches it has a
  circuit whose worst case is a dud.
- Treating keying as a per-unit property. A keying code is only a
  barrier relative to the other connectors in reach, so a unit-level
  review passes every unit and still leaves two circuits swappable.
- Skipping the shorting provision because the ground procedure calls
  for a shorting cap. The procedure is a control, not a design
  feature, and the clause asks what the device does when the cap is in
  somebody's pocket.
- Comparing a margin with its requirement by bare arithmetic. A loop
  that lands exactly on the required margin can fall a few units in
  the last place below it; the comparison absorbs that while the
  requirement stays untouched.

## Behavior contract (gate 3)

The unit normalization, firing-loop build and delivered-current
computation, all-fire margin, contact-share, shorting, insulation,
mate-life, bonding and sealing gates, the set-level keying conflict
walk and the overall verdict are exercised by the gate 3 contract
test: scripts/test_e3311_integral_initiator_connectors.py against
scripts/e3311_integral_initiator_connectors_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3311_integral_initiator_connectors.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
