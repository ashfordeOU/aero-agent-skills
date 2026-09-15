---
name: q60-class-1-connector-contacts
description: "Verify a removable contact may be fitted into a class 1 connector under ECSS-Q-ST-60C clause 4.6.6: fold the contact manufacturer name and test it against the approved source list, check the lot code, date code, conformance certificate and detail specification tie the delivery to that source, demand pair evidence when contact and shell come from different makers, test the wire gauge against the range the contact size accommodates and the applied current against the derated allowance, then return a verdict in precedence order with every finding. Use when a class 1 harness needs crimp contacts. Trigger: ecss, q-st-60c-clause-4-6-6, class-1-removable-contact-sourcing, approved-contact-manufacturer-list, contact-lot-traceability, contact-shell-intermix-qualification, contact-size-wire-gauge-range, contact-current-derating-allowance."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-1-connector-contacts, class-1-removable-contact-sourcing, approved-contact-manufacturer-list, contact-lot-traceability, contact-shell-intermix-qualification, contact-size-wire-gauge-range, contact-current-derating-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Connector Contacts (space-systems/ecss/q60-class-1-connector-contacts)

Use when the task is clause 4.6.6 of ECSS-Q-ST-60C: a class 1 connector takes
removable contacts, and the question is whether the contacts in the bag may be
fitted at all — a sourcing decision that is made before any bench measurement,
and that no bench measurement can overturn.

## Domain quick reference

- A removable contact is the one part of a connector bought separately, fitted
  by hand, and invisible once the backshell is on. It also carries the current
  and forms the only metal-to-metal interface in the mated pair. The clause
  closes that gap the simplest way available: the contact comes from an
  approved manufacturer, full stop.
- An approved source is a name on a list, and a name is a fragile key. Spacing,
  capitalization and a trailing legal suffix all change the string without
  changing the company, so the comparison is made on a folded name rather than
  a raw one — and a fold that is too loose is as wrong as one that is too
  tight.
- Approval covers the manufacturer; traceability covers the parts in hand. A
  lot code, a date code, a certificate of conformance and a detail
  specification reference are what tie this bag of contacts to that approved
  source. Without them the approval is a statement about somebody else's
  contacts.
- A contact from one maker in another maker's shell is an intermix, and the
  two were qualified apart. Retention, plating compatibility and insertion
  force are properties of the pair, so the pair needs evidence of its own.
- Contact size is an application constraint in two directions at once. The
  barrel accommodates a band of wire gauges — too large a conductor will not
  enter it, too small a one crimps without grip — and the contact carries a
  rated current that class 1 derating cuts to a fraction before the harness
  may use it.
- Crimping is a controlled process, not a hand operation. The tool, the
  positioner, the calibration record and the acceptance record are what make
  a crimp repeatable; without them each termination is an individual event
  with no evidence behind it.

## Workflow

1. Validate the case: the contact and connector manufacturers, the contact
   size and finish, the wire gauge, the applied current and the approved
   source list. An empty approved list is an input error, not an automatic
   rejection.
2. Fold both manufacturer names and test the contact manufacturer against the
   approved source list. At class 1 there is no alternate-source route, so
   this outranks every other finding.
3. Check the traceability record ties the delivery to that manufacturer, and
   treat a blank field exactly as an absent one.
4. Where contact and shell come from different manufacturers, demand a
   qualification reference for the pair.
5. Test the wire gauge against the range the contact size accommodates, and
   the applied current against the derated allowance, absorbing
   representation error exactly at the allowance.
6. Check the crimp tooling and acceptance record.
7. Return the verdict in precedence order — source, traceability, intermix,
   application, tooling, accepted — together with the derated allowance, the
   current margin, the gauge range and every finding raised along the way.

## Pitfalls

- Accepting a contact because it measures correctly. Retention force and
  contact resistance on a sample say nothing about the source of the rest of
  the bag, and the clause is a rule about sourcing, not about bench results.
- Matching manufacturer names by raw string comparison. Extra spacing or a
  different capitalization turns an approved source into an unlisted one, and
  a review then spends its time on a defect that never existed.
- Treating an approved manufacturer as covering untraceable stock. Approval
  attaches to the maker; the lot code, date code and conformance certificate
  are what attach it to the parts actually in hand.
- Mixing contacts and shells from different makers on the strength of a shared
  size designation. The size fixes the geometry, not the plating system or the
  retention interface, and the pair was never qualified together.
- Sizing a contact from its rated current. The rating is the bare component
  figure; the class 1 derating cuts it to a fraction, and a harness designed
  against the rated figure rather than the derated one runs every contact at
  roughly twice its allowance.
- Comparing the applied current with the derated allowance by bare arithmetic.
  The allowance is a rating multiplied by a policy share, so a circuit sitting
  exactly on it can land a few units in the last place above it; the
  comparison absorbs that representation error while the allowance stays
  untouched.

## Behavior contract (gate 3)

The policy merge, manufacturer name folding, approved-source test,
traceability and tooling gap checks, intermix qualification, wire gauge range,
derated current allowance and margin, and the verdict precedence are exercised
by the gate 3 contract test:
scripts/test_q60_class_1_connector_contacts.py against
scripts/q60_class_1_connector_contacts_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_1_connector_contacts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
