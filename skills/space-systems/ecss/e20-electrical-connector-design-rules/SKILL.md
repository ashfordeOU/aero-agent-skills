---
name: e20-electrical-connector-design-rules
description: "Use when verify the safety features of a separable electrical connector under ECSS-E-ST-20C clause 4.2.3, so that no energized contact is exposed during a mating or demating operation: categorize the connection as power, test, signal or ordnance, determine which side stays energized once demated and require recessed socket contacts there, derive the full safety-feature set the connection demands and report every feature not implemented, decide whether a scoop-proof shroud is required from working voltage and contact count, check the first-mate-last-break contact sequence, and detect two mateable connectors that share a keying arrangement. Trigger: ecss, e-st-20-electrical-scope, connector-mating-safety, exposed-energized-contact, socket-contact-on-live-side, scoop-proof-shroud, first-mate-last-break, connector-keying-uniqueness, test-connector-isolation."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-connector-design-rules, connector-mating-safety, exposed-energized-contact, scoop-proof-shroud, first-mate-last-break, connector-keying-uniqueness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Connector Design Rules (space-systems/ecss/e20-electrical-connector-design-rules)

Use when the task is the connector safety review of ECSS-E-ST-20C
clause 4.2.3 -- confirming that a separable power or test connection
carries the features that keep energized contacts unreachable while
the connection is being mated, demated or left open on the bench.

## Domain quick reference

- The clause is about the open connection, not the mated one. A mated
  connector is safe almost by construction; the hazard lives in the
  window where one half is exposed with the circuit behind it still
  live. Every rule below exists to shrink or eliminate that window.
- The governing rule is contact gender on the live side. Whichever
  half stays energized after separation carries socket contacts, whose
  conducting surfaces sit recessed inside the insert, while the
  de-energized half carries pins. Getting this backwards leaves a row
  of energized pins at finger and tool reach, and it is the single
  most common finding on a harness design review.
- A scoop-proof shroud stops a misaligned mating attempt from letting
  a pin touch a neighbouring contact or the shell before the two
  inserts align. It is demanded once the working voltage or the
  contact count crosses a project threshold -- higher voltage makes a
  brush contact dangerous, higher contact density makes it likely.
- Contact sequencing is the other half of mating safety. The chassis
  and bonding path engages first and separates last, then the power
  return, then the power line, with signals last on mate. The rule is
  expressed as a non-decreasing rank over the contacts in mating
  order, so it holds whether or not every role is present on a given
  connector.
- Test and umbilical connections attract extra features because they
  are handled by people, repeatedly, on a powered vehicle: an
  isolation or current-limiting element so a ground-support fault
  cannot back-drive flight circuits, and a positive means of verifying
  demate before flight. Ordnance connections attract a shorting
  feature on the initiator side.
- Keying is an assembly-level property, not a connector-level one. Two
  connectors of the same shell size and insert arrangement, reachable
  by the same harness branch, must carry different keying or clocking,
  otherwise cross-mating is a matter of time. The check needs the set
  of connectors in a zone, never a single connector.

## Workflow

1. Categorize the connection as power, test, signal or ordnance.
   Reject an unrecognized connection type before the review proceeds.
2. Determine which half stays energized after separation and derive
   the contact style it must carry: socket on the energized half, pin
   on the de-energized half. Compare against the declared style and
   flag a mismatch as an exposed-energized-contact finding.
3. Decide whether a scoop-proof shroud is demanded, from the working
   voltage and the contact count against the project thresholds.
4. Derive the full feature set the connection demands -- keying,
   socket contacts and a protective cover on a live half, a
   de-energized demate inhibit on any power-bearing connection, a
   shroud where required, the isolation element and demate
   verification on a test connection, a shorting feature on an
   ordnance connection -- and subtract what the design implements.
   Report each remaining feature as its own finding.
5. Check the mating sequence: walk the contacts in mate order and
   confirm their roles never move backwards through the required
   rank. Report the first contact that breaks the order.
6. Across the connectors of one zone, group by shell size and insert
   arrangement and flag any group whose keying is not unique.
7. The connector is not compliant until its finding list is empty and
   the zone-level keying check is clean.

## Pitfalls

- Applying the socket-on-live-side rule to the load half by habit. The
  rule follows the energy, not the position in the diagram; on a
  connection fed from the load side during ground test, the load half
  is the live half.
- Treating a protective cover as a substitute for socket contacts. A
  cover protects the stowed connector, not the one in a technician's
  hand mid-mate, and the two features answer different moments.
- Assuming a connector is scoop-proof because it has a shroud. The
  shroud has to be deep enough to align the inserts before any contact
  can touch; a shallow decorative shell satisfies the drawing and not
  the rule. Record the feature only when the depth was checked.
- Checking the mating sequence only for the presence of a chassis
  contact. Presence is not order -- the contact has to be the first to
  engage and the last to separate, which is a statement about relative
  contact lengths, not about the pinout list.
- Running the keying check per connector. A single connector can never
  fail it; the failure is a pair, and it only appears when the zone's
  connectors are compared against each other.

## Behavior contract (gate 3)

The connection categorization, live-side contact style, scoop-proof
threshold, safety-feature derivation, mating-sequence and zone keying
logic is exercised by the gate 3 contract test:
scripts/test_e20_electrical_connector_design_rules.py against
scripts/e20_electrical_connector_design_rules_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electrical_connector_design_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
