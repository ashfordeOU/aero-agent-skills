---
name: q6013-class-3-connectors
description: "Evaluate whether a connector family and the contacts going into it may be adopted at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.6: derate each candidate's rated contact current for the class and again for the share of positions loaded, refuse a family short of current, short of spare positions or standing on no specification, rank the admissible families and pick one, then settle contact sourcing: refuse an unidentified lot outright, credit an alternative source below the connector manufacturer only where an interchangeability record exists, and score the selection evidence, crediting a supplier declaration below a project record. Use when a harness connector choice has to become a documented decision. Trigger: ecss, q-st-60-13c-clause-6-6-6, class-three-connector-family-selection, connector-contact-sourcing-credit, contact-interchangeability-record, connector-contact-current-derating, connector-spare-position-share, class-three-connector-selection-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c-clause-6-6-6, q6013-class-3-connectors, class-three-connector-family-selection, connector-contact-sourcing-credit, contact-interchangeability-record, connector-contact-current-derating, connector-spare-position-share, class-three-connector-selection-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Connectors (space-systems/ecss/q6013-class-3-connectors)

Use when the task is the clause 6.6.6 connector question of
ECSS-Q-ST-60-13C at the lowest assurance class: a harness needs a
connector family, the contacts that go into it have to come from
somewhere, and the question is whether the family that was picked and
the parts that were bought hold up as a decision the class can accept.

## Domain quick reference

- Two decisions hide inside one word. Choosing the family is a design
  act, taken from a wire list; sourcing the contacts is a purchasing
  act, taken from what a distributor had. At this class both are allowed
  to rest on lighter standing than the classes above accept, which is
  precisely why each has to be written down rather than assumed.
- A family is admissible or it is not, and the test is arithmetic. Its
  derated contact current has to cover the worst circuit in the list,
  its insert has to keep positions free once every circuit is placed,
  and it has to stand on some recognised specification. A family failing
  two of those reports two findings, because fixing one leaves the other
  waiting.
- The allowed contact current is derived, not read. The rated current of
  one contact is derated for the class and derated again for the share
  of positions carrying current at once, since an insert with every
  position loaded heats itself and every contact in it. Applying the
  loading to the fraction rather than the count keeps one policy working
  for a nine-way and a sixty-one-way insert.
- Spare positions are the design margin nobody budgets. An insert filled
  to its last position has no room for the circuit that appears at
  integration, and by then the family is fixed by every backshell and
  bracket around it.
- A catalogue-only family is permitted here and the class above does not
  permit it. That permission is a project decision recorded in policy,
  not a default nobody voted on, so a project may still declare it
  insufficient and have the ranking honour that.
- Contact sourcing carries the insert's real quality. A contact from the
  connector manufacturer inherits the insert's retention and plating
  basis. A contact from an alternative source may be used at this class
  where an interchangeability record exists, and it is credited below a
  manufacturer part because the record covers the dimensions rather than
  the process behind them.
- An unidentified lot closes the question rather than lowering a score.
  A contact nobody can name cannot be reordered, compared or replaced,
  and an insert repaired with one is an insert nobody can account for.
- Evidence is scored, not ticked. A subject may be carried on a supplier
  declaration at this class, and a declaration is credited below a
  project record so that a selection documented entirely by what a
  supplier says about itself cannot read as a documented selection.

## Workflow

1. Validate the selection policy first: the class derating, the loading
   slope, the spare position floor, the manufacturer sourcing floor, the
   alternative source credit and its floor, the declaration credit, the
   evidence share and credited floors, the marginal band and the
   catalogue-only decision. A loading slope of one, a credit of zero or
   one, or a credited floor above the plain one is refused rather than
   used.
2. Validate the harness demand: a reference, a whole positive circuit
   count and a positive worst-case circuit current. A harness with no
   reference closes the assessment on selection not declared.
3. Validate every candidate family: a reference, a recognised family, a
   recognised qualification standing, whole positive insert positions
   and a positive rated contact current. A repeated candidate is refused.
4. Take each candidate's loading fraction, loading factor and derated
   contact allowance, then its current headroom and spare position
   share, and collect every finding against it rather than the first.
   Compare with a tolerance that absorbs representation error so a value
   landing on a bound is admissible.
5. Rank the candidates that draw no finding on standing, current
   headroom and spare positions, breaking a tie on the reference so the
   ranking repeats, and take the top one. No admissible candidate closes
   the assessment with every reason reported.
6. Validate every contact lot and settle sourcing: name each
   unidentified lot and each alternative lot with no interchangeability
   record, check the contacts in hand against the circuits to place, and
   take the manufacturer share and the credited sourcing against their
   floors.
7. Dispose each required evidence subject as held as a project record,
   held as a supplier declaration, declared without a record, or absent,
   then report every failing list in full rather than truncating at the
   first entry.
8. Report the selected family, its allowance, headroom and spare share,
   the rejected candidates, the sourced count, the manufacturer share
   and credited sourcing, the evidence share and credited evidence, and
   raise an advisory for an admissible family inside the marginal band.
   Close on one verdict: selection not declared, no admissible
   candidate, contact sourcing not established, contact supply short,
   contact sourcing credit short, selection evidence short, or selection
   meets class three scope.

## Pitfalls

- Sizing the family on the single-contact rating. That rating describes
  a connector with one wire in it, and the insert being bought will run
  with most of its positions live.
- Filling the insert to the last position because the wire list fits
  today. The circuit that appears at integration then needs a different
  connector, and the connector is the part every backshell, bracket and
  harness length was built around.
- Reading a catalogue entry as a specification. It states what the
  manufacturer currently sells, not what the part is held to, and it can
  change between two deliveries that carry the same order number.
- Buying contacts on price and fitting them without an interchangeability
  record. Dimensionally similar is not dimensionally interchangeable, and
  the difference shows up as a retention failure under vibration rather
  than on the bench.
- Treating an unidentified lot as a scoring problem. It is a traceability
  failure: the part cannot be reordered, compared against the insert, or
  matched to the one that failed.
- Crediting a supplier declaration in full. A declaration is permitted
  here and it is thinner than a record this project holds, which is what
  the credit records; a declaration naming no supplier is grouped with
  the subjects that hold no record at all.

## Behavior contract (gate 3)

The policy validation, the harness demand validation, the candidate
validation, the loading fraction and factor, the derated contact
allowance, the current headroom, the spare position share, the candidate
findings, the ranking and its tie-break, the contact lot validation, the
unidentified and unsupported lot lists, the sourced count, the
manufacturer share, the credited sourcing, the project-record,
declaration, unrecorded and absent evidence dispositions, the evidence
share, the credited evidence, the marginal advisories and the selection
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_connectors.py against
scripts/q6013_class_3_connectors_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_connectors.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
