---
name: q60-class-3-connector-contacts
description: "Verify that a removable contact may be fitted into a Class 3 connector under ECSS-Q-ST-60C clause 6.6.6: fold the offered maker name onto the key the approved source list is matched on, decide whether it arrives by the list, by a recorded alias or by a project-approved addition carrying both a justification and a qualification reference, name the traceability records the delivery is missing, demand pair evidence when contact and shell come from different makers, grade the plating pair and refuse a near-pure tin finish, then test the conductor against the crimp range of the size and the applied current against the Class 3 allowance derated for a populated shell. Use when a Class 3 harness is crimped with bought-in removable contacts. Trigger: ecss, q-st-60c, q60-class-3-connector-contacts, q60-c3-contact-approved-source-route, q60-c3-contact-plating-pair-compatibility, q60-c3-contact-bundle-current-derating."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-3-connector-contacts, q60-c3-contact-approved-source-route, q60-c3-contact-traceability-gap, q60-c3-contact-plating-pair-compatibility, q60-c3-contact-crimp-range-fit, q60-c3-contact-bundle-current-derating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — Connector Contacts (space-systems/ecss/q60-class-3-connector-contacts)

Use when the task is clause 6.6.6 of ECSS-Q-ST-60C: a Class 3 connector takes
removable contacts, and the question is whether the contacts in the bag may be
fitted at all — a sourcing decision made before any bench measurement, and one
that no bench measurement overturns.

## Domain quick reference

- A removable contact is bought separately, fitted by hand and invisible once
  the backshell is on, yet it carries the current and forms the only
  metal-to-metal interface in the mated pair. The clause closes that gap the
  simplest way available: the contact comes from an approved manufacturer, and
  Class 3 widens who may be one rather than removing the list.
- An approved source is a name on a list, and a name is a fragile key. Case,
  punctuation, separator runs and a trailing legal wrapper all change the
  string without changing the company, so the comparison is made on a folded
  key. A fold that is too loose is as wrong as one that is too tight: it maps
  two different makers onto one entry and admits a source nobody approved.
- Class 3 opens a third route the tighter classes do not. The project may add
  a source itself — but the addition is a record, not a decision taken in a
  meeting: a justification for why this maker, and a qualification reference
  behind it. An addition missing either is not an approved source, and the
  finding should name the record to go and write rather than the maker.
- An alias is a record too. A division or a renamed entity reaches an approved
  source only when somebody wrote the alias down; inferring one from a shared
  first word is how an unapproved maker gets in.
- Approval covers the manufacturer; traceability covers the parts in hand. The
  lot code, the date code, the conformance certificate and the detail
  specification are what tie this bag to that approved source, and a missing
  one is evidence outstanding rather than a design defect.
- A contact and a shell from different makers are two qualified parts and one
  unqualified pair. The mating geometry, the retention and the insertion force
  were each demonstrated at home, not against the other maker's part.
- Plating is part of the pair, not a cosmetic choice. A noble finish mated to
  a solderable one wears through and frets where the two slide, and a
  near-pure tin finish grows whiskers whatever it mates with — that one is
  refused rather than traded against schedule.
- The allowance a contact carries is not the number on its own datasheet. The
  Class 3 derating takes a share of the rated current, and a densely populated
  shell takes another share again, because a contact in a crowded insert
  cannot shed its own heat.

## Workflow

1. Validate the case: the contact maker, the shell maker, the contact size,
   the conductor cross-section, the number of energised contacts, the applied
   current, both plating finishes, the approved source list and the
   traceability records held.
2. Fold the offered maker name and every candidate onto the comparison key,
   and decide which route it arrives by — the list, a recorded alias, or a
   project addition with both of its records written down.
3. Name the traceability records the delivery does not carry.
4. Decide whether contact and shell come from different makers, and whether
   the pair evidence that would then be owed is held.
5. Grade the plating pair: name a restricted finish first, then a dissimilar
   family pair.
6. Test the conductor against the crimp range of the size, and the applied
   current against the allowance derated for the class and the populated
   shell.
7. Return the disposition in precedence order: source not approved first; then
   application nonconforming when the plating, the crimp range or the current
   fails; then evidence outstanding when a record or the pair evidence is
   missing; admissible otherwise.

## Pitfalls

- Matching maker names as raw strings. Two spellings of one company read as
  two companies, and the approved one gets rejected while the bag on the bench
  is the right bag.
- Folding so hard the key stops distinguishing. Dropping a real word, not just
  a legal wrapper, collapses two makers onto one entry, and the fold that was
  meant to admit an approved source admits an unapproved one.
- Treating the Class 3 project-addition route as a formality. An addition with
  no justification and no qualification reference behind it is a preference,
  not an approval, and the part arrives with nothing to show an auditor.
- Accepting a plausible alias nobody recorded. A shared first word is not a
  corporate relationship, and the contact that arrives on that reasoning has
  no approval behind it.
- Reading a full set of paperwork as approval. The certificate shows the parts
  match their specification; it does not show the maker is reachable on any
  route, and the two findings sit at different points in the precedence order.
- Trading a near-pure tin finish against schedule. A whisker is a short that
  appears years after every acceptance test has passed, and no amount of
  screening buys the finish back.
- Sizing a contact from the conductor alone. The crimp range has a lower bound
  as well as an upper one, and a conductor too thin for the barrel makes a
  joint that passes a pull test and opens on vibration.
- Taking the datasheet current as the allowance. The class derating and the
  bundle derating both apply, and a contact sized against the bare rating runs
  hot in exactly the dense insert that has no margin to give.
- Comparing a computed utilisation or a crimp bound by bare arithmetic. Both
  sides are computed, so a case sitting exactly on its bound can land a few
  units in the last place the wrong side of it.

## Behavior contract (gate 3)

The name fold, the three approval routes and the project-addition record gaps,
policy merge, case validation, traceability gaps, intermix pair evidence,
plating pair grading, crimp range fit, bundle derating factor, derated current
allowance, utilisation and the four-way disposition in precedence order are
exercised by the gate 3 contract test:
scripts/test_q60_class_3_connector_contacts.py against
scripts/q60_class_3_connector_contacts_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_3_connector_contacts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
