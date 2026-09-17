---
name: q60-class-2-connector-contacts
description: "Verify that a removable contact may be fitted into a class 2 connector under ECSS-Q-ST-60C clause 5.6.6: fold the offered maker name onto the key the approved source list is matched on, resolve a recorded alias, name the lot code, date code, conformance certificate and detail specification the delivery is missing, demand pair evidence when contact and shell come from different sources, test the conductor cross-section against the crimp range of the size and the applied current against the class 2 allowance derated for a populated shell. Use when a class 2 harness is crimped with bought-in removable contacts. Trigger: ecss, q-st-60c-clause-5-6-6, class-2-contact-approved-source-fold, class-2-contact-traceability-gap, class-2-contact-shell-intermix-evidence, class-2-contact-bundle-current-derating."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-2-connector-contacts, class-2-contact-approved-source-fold, class-2-contact-traceability-gap, class-2-contact-shell-intermix-evidence, class-2-contact-bundle-current-derating, class-2-contact-crimp-range-fit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Connector Contacts (space-systems/ecss/q60-class-2-connector-contacts)

Use when the task is clause 5.6.6 of ECSS-Q-ST-60C: a class 2 connector takes
removable contacts, and the question is whether the contacts in the bag may be
fitted at all — a sourcing decision made before any bench measurement, and one
that no bench measurement overturns.

## Domain quick reference

- A removable contact is bought separately, fitted by hand and invisible once
  the backshell is on, yet it carries the current and forms the only
  metal-to-metal interface in the mated pair. The clause closes that gap the
  simplest way available: at class 2 as at class 1, the contact comes from an
  approved manufacturer, full stop.
- An approved source is a name on a list, and a name is a fragile key. Case,
  punctuation, separator runs and a trailing legal wrapper all change the
  string without changing the company, so the comparison is made on a folded
  key. A fold that is too loose is as wrong as one that is too tight: it maps
  two different makers onto one entry and admits a source nobody approved.
- An alias is a record, not a guess. A division or a renamed entity reaches an
  approved source only when somebody wrote the alias down; inferring one from a
  shared first word is how an unapproved maker gets in.
- Approval covers the manufacturer; traceability covers the parts in hand. The
  lot code, the date code, the conformance certificate and the detail
  specification are what tie this bag to that approved source, and a missing
  one is evidence outstanding rather than a design defect.
- A contact and a shell from different makers are two qualified parts and one
  unqualified pair. The mating geometry, the retention and the insertion force
  were each demonstrated at home, not against the other maker's part.
- The allowance a contact carries is not the number on its own datasheet. The
  class 2 derating takes a share of the rated current, and a densely populated
  shell takes another share again, because a contact in a crowded insert cannot
  shed its own heat.

## Workflow

1. Validate the case: the contact maker, the shell maker, the contact size,
   the conductor cross-section, the number of energised contacts, the applied
   current, the approved source list and the traceability records held.
2. Fold the offered maker name and every approved entry onto the comparison
   key, and decide whether the offered name reaches an approved source
   directly or through a recorded alias.
3. Name the traceability records the delivery does not carry.
4. Decide whether contact and shell come from different sources, and whether
   the pair evidence that would then be owed is held.
5. Test the conductor against the crimp range of the size, and the applied
   current against the allowance derated for the class and the populated
   shell.
6. Return the disposition in precedence order: source not approved first;
   then application nonconforming when the crimp range or the current fails;
   then traceability outstanding when a record or the pair evidence is
   missing; admissible otherwise.

## Pitfalls

- Matching maker names as raw strings. Two spellings of one company read as
  two companies, and the approved one gets rejected while the bag on the bench
  is the right bag.
- Folding so hard the key stops distinguishing. Dropping a real word, not just
  a legal wrapper, collapses two makers onto one entry, and the fold that was
  meant to admit an approved source admits an unapproved one.
- Accepting a plausible alias nobody recorded. A shared first word is not a
  corporate relationship, and the contact that arrives on that reasoning has no
  approval behind it.
- Reading a full set of paperwork as approval. The certificate shows the parts
  match their specification; it does not show the maker is on the list, and the
  two findings sit at different points in the precedence order.
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

The name fold, approved source and alias match, policy merge, case validation,
traceability gaps, intermix pair evidence, crimp range fit, bundle derating
factor, derated current allowance, utilisation and the four-way disposition in
precedence order are exercised by the gate 3 contract test:
scripts/test_q60_class_2_connector_contacts.py against
scripts/q60_class_2_connector_contacts_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_2_connector_contacts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
