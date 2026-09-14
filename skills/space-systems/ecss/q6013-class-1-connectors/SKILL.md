---
name: q6013-class-1-connectors
description: "Verify the connector contacts of a Class 1 commercial procurement against ECSS-Q-ST-60-13C clause 4.6.6: group the contact source as qualified contact manufacturer, integrated connector manufacturer, traced distributor or open market, read the minimum gold thickness the finish needs for the declared mating cycles off a durability table, grade the measured gold and nickel barrier against it, derate the contact current rating for contact size and for the fraction of contacts energised together, convert the contact resistance into a millivolt drop, then return an accept, accept-with-deviation or reject disposition. Use when connector contacts and their sourcing must be judged before a Class 1 lot is accepted. Trigger: ecss, q-st-60-13c, class-1-connector-contacts, contact-gold-plating-durability, contact-bundle-current-derating, contact-millivolt-drop, contact-lot-traceability, connector-contact-sourcing."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-connectors, class-1-connector-contacts, contact-gold-plating-durability, contact-bundle-current-derating, contact-millivolt-drop, connector-contact-sourcing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Connectors — Contacts and Contact Sourcing (space-systems/ecss/q6013-class-1-connectors)

Use when the task is judging the contacts of a connector bought under the
highest assurance class of ECSS-Q-ST-60-13C clause 4.6.6 — where the
contacts came from, whether the finish survives the declared mating life,
and how much current one contact may actually carry in the connector it
sits in.

## Domain quick reference

- The connector and its contacts are two procurements. A qualified
  contact manufacturer, or a connector manufacturer that makes its own
  contacts, closes the sourcing question on its own; a distributor
  closes it only against a traced contact lot, and an open-market buy
  does not close it at all.
- The finish is a system, not a number. Gold carries the mating life and
  the nickel barrier underneath it stops base-metal diffusion into the
  gold; a thick gold layer over a thin or absent barrier is not a
  compliant finish, so the two are graded separately and reported
  separately.
- The gold thickness required is a function of the declared number of
  mating cycles, read off a durability table. A durability figure
  outside the tabulated span is not a small extrapolation, because the
  wear behaviour changes at both ends, so the correct response is to
  refuse the point and obtain table data that covers it.
- Contact current is derated twice. The highest assurance class takes a
  fixed fraction of the single-contact rating, and a bundle derating
  then takes a further fraction that depends on how much of the
  connector is energised at once. A contact rated in isolation says
  almost nothing about what it may carry in a fully loaded shell.
- The contact drop is the product of the applied current and the contact
  resistance, in millivolts when the resistance is in milliohms. It is a
  separate finding from the current allowance: a contact can be inside
  its derated current and still exceed the drop the circuit tolerates.
- Traceability is a disposition input. A contact lot identifier is what
  ties the measured finish to the parts being delivered, and its absence
  is a refusal even when every measurement is clean.

## Workflow

1. Group the contact source and record whether it stands on its own,
   needs the traced lot, or closes the acceptance path outright.
2. Read the minimum gold thickness for the declared mating cycles off
   the durability table, refusing a durability figure the table does not
   cover.
3. Grade the measured gold against that minimum and the measured nickel
   against the barrier minimum, absorbing representation error at the
   boundary with a named tolerance rather than by thinning the
   requirement.
4. Take the single-contact rating for the contact size, apply the class
   current fraction, then apply the bundle derating for the fraction of
   contacts energised together.
5. Compare the applied current with that allowance.
6. Convert the contact resistance into a millivolt drop at the applied
   current and compare it with the circuit allowance.
7. Confirm the contact lot identifier, then return the disposition —
   accept, accept-with-deviation or reject — with every finding that
   drove it.

## Pitfalls

- Quoting the catalogue contact rating as the usable current. It is the
  isolated single-contact figure; the class fraction and the bundle
  derating both sit between it and what the contact may carry.
- Grading gold thickness against a fixed number. The minimum belongs to
  the declared mating life, so a connector specified for many mating
  cycles needs a thicker finish than the same contact in a
  mate-once harness.
- Accepting a thick gold layer over a missing nickel barrier. The
  barrier is what keeps the gold a gold surface over life; the two
  layers are graded separately for that reason.
- Treating the current allowance and the contact drop as one check. A
  contact inside its derated current can still drop more millivolts than
  the circuit budget allows, and that is its own finding.
- Extrapolating the durability table to keep an unusual mating-cycle
  figure in the assessment. That invents wear data; refuse the point and
  obtain table coverage instead.
- Buying contacts on the connector manufacturer's standing when a
  distributor supplied them. The standing follows the contacts, and
  without the traced contact lot the finish measurements belong to no
  identified parts.

## Behavior contract (gate 3)

The source grouping, durability-table lookup, plating grading, bundle
derating, current-allowance comparison, contact-drop conversion and
disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_connectors.py against
scripts/q6013_class_1_connectors_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_1_connectors.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
