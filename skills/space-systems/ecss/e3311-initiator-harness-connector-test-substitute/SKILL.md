---
name: e3311-initiator-harness-connector-test-substitute
description: "Validate the initiator harness connector and the initiator test substitute against ECSS-E-ST-33-11C clauses 4.10.12 and 4.10.13. Use when the task is sizing the contact rating the all-fire current demands once the derating factor is applied, proving no keying code is repeated across two firing circuits, walking the closed connector control set of shielded shell, contacts shorted and grounded when unmated, scoop-proof sockets and segregated firing contacts, and confirming the inert substitute sits inside the bridge-resistance tolerance of the flight initiator, meets insulation resistance at a valid test voltage, is serialised, and carries a colour flight hardware never uses. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, initiator-harness-connector-controls, initiator-contact-current-derating, firing-circuit-keying-uniqueness, initiator-test-substitute-fidelity, substitute-identification-colour."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-initiator-harness-connector-test-substitute, initiator-harness-connector-controls, initiator-contact-current-derating, firing-circuit-keying-uniqueness, initiator-test-substitute-fidelity, substitute-identification-colour]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Initiator Harness Connector and Test Substitute (space-systems/ecss/e3311-initiator-harness-connector-test-substitute)

Use when the task is ECSS-E-ST-33-11C clauses 4.10.12 and 4.10.13 --
two clauses that share one interface. The connector is the last
removable joint between the firing circuit and the device that fires;
the test substitute is what occupies that joint for most of the
campaign.

## Domain quick reference

- The contact rating is the only number in the connector clause, and
  it is derived rather than declared. The required rating is the
  all-fire current divided by the derating factor, so a tighter
  derating raises the bar on the same device. Comparing a rating with
  the bare all-fire current is what lets a derating policy exist on
  paper and nowhere else.
- Keying uniqueness is a property of the circuit list, not of a
  connector. One connector cannot tell you whether its code is
  repeated three racks away, which is why the check groups the whole
  declared set and names the circuits that collide.
- The remaining connector requirements are a closed control set. An
  undeclared control is rejected rather than assumed, because the
  silent entry is the one nobody inspected.
- The substitute exists for two opposite reasons and they pull against
  each other. Electrically it has to look like the initiator, or the
  checkout it supports proves nothing about the flight circuit.
  Physically it has to be unmistakable, or it flies. Resistance
  tolerance serves the first; identification colour serves the second.
- Insulation resistance is two numbers, not one. A resistance quoted
  without the voltage it was measured at does not demonstrate the
  requirement, because the same specimen reads differently at fifty
  volts and five hundred.
- Keying on the substitute is a fidelity requirement rather than a
  safety one: a substitute that bypasses the flight keying exercises a
  mating the flight article will never see.

## Workflow

1. Compute the required contact rating from the all-fire current and
   the derating factor first, then grade the declared rating against
   it, treating a contact sitting exactly on the requirement as
   compliant rather than failing it on representation error.
2. Group the whole firing-circuit keying map by code and name every
   code carried by more than one circuit.
3. Walk the connector control set, rejecting an undeclared control and
   naming each one absent.
4. Turn to the substitute and take the resistance deviation as a
   fraction of the flight value, then grade it against the tolerance.
5. Grade insulation resistance and the voltage it was measured at
   separately; a valid figure needs both.
6. Compare the substitute identification colour with the flight
   colour and raise a finding when they match.
7. Walk the substitute control set, then close with the overall
   verdict and the parts that produced it.

## Pitfalls

- Comparing the contact rating with the all-fire current directly. The
  derating factor is the whole point of the requirement; dropping it
  turns a two-times margin into no margin and the arithmetic still
  looks like it passed.
- Checking keying one connector at a time. A code is unique or it is
  not, and that is a statement about the set. A per-connector review
  cannot see the collision it is looking for.
- Treating an undeclared connector control as satisfied. The set is
  closed, and a connector whose contacts are not shorted and grounded
  when unmated is hazardous in exactly the state nobody looked at.
- Accepting a substitute resistance that is merely in the same decade.
  The substitute stands in for the initiator during circuit checkout,
  so a resistance well outside tolerance means the current the
  checkout measured is not the current the flight device will see.
- Quoting an insulation resistance with no test voltage. The number is
  meaningless on its own, and a comfortable reading taken at a low
  voltage is the reading that hides a weak insulation path.
- Giving the substitute the flight identification colour because it is
  what the paint shop had. Colour is the last barrier between a test
  item and a flight configuration, and it is the one a tired
  technician actually uses.
- Assuming a substitute that fits is a substitute that is keyed the
  same. Fitting proves the shell matches; keying is what proves the
  mating being exercised is the flight mating.

## Behavior contract (gate 3)

The derated contact-rating computation, the circuit-wide keying
grouping, the connector control walk, the resistance-deviation
tolerance, the insulation resistance and test-voltage pair, the
identification-colour rule and the overall verdict are exercised by
the gate 3 contract test:
scripts/test_e3311_initiator_harness_connector_test_substitute.py
against
scripts/e3311_initiator_harness_connector_test_substitute_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3311_initiator_harness_connector_test_substitute.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
