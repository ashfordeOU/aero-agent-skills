---
name: q6013-class-2-connectors
description: "Assess whether a connector with removable contacts may be applied at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.6.6: refuse a connector naming no insert arrangement or removal tool, name every contact worked past the insertion limit, derate the rated contact current for the class and again for the share of positions energised at once, name every position over that allowance, take the planned matings as a share of the rated durability, check the spare provision, and score the build evidence, crediting a heritage claim below a direct record. Use when a harness connector has to become an application verdict. Trigger: ecss, q-st-60-13c-clause-5-6-6, class-two-removable-contact-connector, removable-contact-insertion-limit, connector-contact-current-derating, connector-insert-loading-factor, connector-mating-cycle-durability, connector-spare-contact-provision."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-connectors, class-two-removable-contact-connector, removable-contact-insertion-limit, connector-contact-current-derating, connector-insert-loading-factor, connector-mating-cycle-durability, connector-spare-contact-provision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Connectors (space-systems/ecss/q6013-class-2-connectors)

Use when the task is the clause 5.6.6 connector question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a connector whose
contacts can be taken out of the insert and put back has been picked for
a harness, and the question is whether the way it is loaded, the way it
has been worked and the way it was documented keep it inside what the
class allows.

## Domain quick reference

- Removability is the feature that makes the connector repairable and it
  is the feature that wears it out. Every insertion works the retention
  clip that holds the contact in the insert, and a clip worked too many
  times releases under vibration rather than under the extraction tool.
- The insertion count is carried per position, not per connector. One
  position reworked four times is a failure waiting in an otherwise
  untouched insert, and the finding has to name that position so the
  contact is replaced rather than pushed back in again.
- The allowed contact current is derived, not read. The rated current of
  a single contact is derated for the class, then derated again for the
  share of positions carrying current at once, because a fully loaded
  insert heats itself and every contact in it.
- The loading factor is applied to the fraction of positions energised
  rather than to their count, so one policy works for a nine-way and a
  sixty-one-way insert without a table per shell size.
- Durability is spent before launch, not during flight. Integration, test
  and retest matings come out of the same rated mating life, and a
  connector arriving at launch with its durability already spent has no
  margin for a late demate.
- Spare positions are the repair budget. A harness with every position
  used has nowhere to move a wire when a contact is damaged, and the
  repair becomes a connector change rather than a contact change.
- Evidence is scored, not ticked. A subject may be carried against a
  heritage connector of the same insert arrangement at this class, which
  the class above does not allow, and heritage is credited below a direct
  record so that a build documented entirely by what an earlier programme
  did cannot read as a documented build.

## Workflow

1. Validate the connector policy first: the insertion limit, the class
   current derating, the loading slope, the mating-cycle cap, the spare
   floor, the evidence share and credited floors, the heritage credit and
   the marginal band. A limit below one insertion, a zero derating or
   credit, a loading slope of one, or a credited floor above the plain
   one is refused rather than used.
2. Validate the connector identity: a reference, an insert arrangement, a
   positive rated contact current, a positive rated mating life, a
   non-negative planned mating count and a removal tool reference. A
   connector with no reference, no arrangement or no tool closes the
   assessment on connector not identified.
3. Validate every contact position: a named position, a recognised
   removable termination, a whole non-negative insertion count, and a
   consistent loading declaration. A position declared both spare and
   energised, or energised and carrying nothing, is refused.
4. Name every position worked past the insertion limit. That list closes
   the assessment on its own, because a released contact is a harness
   fault rather than a derating margin.
5. Take the loading fraction, apply the loading factor on top of the
   class derating, and name every position over the resulting allowance.
   Compare with a tolerance that absorbs representation error so a
   current landing on the allowance is admissible.
6. Take the planned matings as a share of the rated durability and the
   spare positions as a share of the insert, and compare each against its
   limit.
7. Dispose each required evidence subject as held directly, held against
   heritage, declared without a record, or absent, then report every
   failing list in full rather than truncating at the first entry.
8. Report the loading fraction, the allowance, the overloaded and
   over-inserted positions, the consumed durability, the spare share, the
   evidence share and the credited evidence, and raise an advisory for
   every energised position inside the marginal band. Close on one
   verdict: connector not identified, contact insertion limit exceeded,
   contact current derating exceeded, mating durability consumed, spare
   provision short, evidence short, or connector meets class two scope.

## Pitfalls

- Sizing the harness on the single-contact rating. That rating describes
  a connector with one wire in it; the same insert with every position
  energised runs hotter and carries less per contact.
- Counting insertions per connector rather than per position. The
  connector average is fine while one position is on its fifth rework,
  and the average is not the position that lets go.
- Reinserting a contact that has passed the limit because it still feels
  tight. Retention is measured in a pull test, not in the fingers, and
  the limit exists because the clip has already been worked.
- Counting only flight matings against the rated durability. Integration
  and test matings come out of the same life, and they are the ones
  nobody logs.
- Filling every position because the wire list fits. A repair then needs
  a new connector rather than a new contact, and the schedule discovers
  that at the worst moment.
- Crediting a heritage claim in full. Heritage is permitted here and it
  is thinner than a record from this build with these tools and this
  operator, which is what the credit records; a heritage claim naming no
  connector is grouped with the subjects that hold no record at all.

## Behavior contract (gate 3)

The policy validation, the connector identity validation, the contact
validation, the loading fraction and factor, the derated contact
allowance, the overloaded and over-inserted position lists, the consumed
mating durability, the spare share, the held, heritage, unrecorded and
absent evidence dispositions, the evidence share, the credited evidence,
the marginal advisories and the connector verdict are exercised by the
gate 3 contract test: scripts/test_q6013_class_2_connectors.py against
scripts/q6013_class_2_connectors_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_2_connectors.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
