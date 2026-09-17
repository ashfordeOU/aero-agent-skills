---
name: q6003-configuration-item-data-lists
description: "Verify that a device item data list and its as-built record together identify every delivered element under ECSS-Q-ST-60-03C clause 8.2.2. Use when a delivery is being cleared and each listed item still needs an identifier, part number, revision and source, with a serial number for every individually traceable unit. Reconciles the two lists in both directions and reports duplicate item identifiers, listed items never built, delivered elements never listed, revision drift between list and record, serialised units shipped without a serial, and deviations cited against no approved waiver, then scores identification coverage against its floor. Trigger: ecss, q-st-60-03, configuration-item-data-list, as-built-configuration-record, delivered-element-identification, item-revision-drift, serialised-unit-serial-number, unbacked-deviation-reference."
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
  tags: [ecss, q-st-60-device-assurance-scope, q6003-configuration-item-data-lists, configuration-item-data-list, as-built-configuration-record, delivered-element-identification, item-revision-drift, serialised-unit-serial-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Assurance — Item Data List and As-Built Record (space-systems/ecss/q6003-configuration-item-data-lists)

Use when the task is the identification step of ECSS-Q-ST-60-03C clause
8.2.2 — deciding whether the item data list and the as-built record of a
device delivery, taken together, actually identify every element that
leaves the supplier.

## Domain quick reference

- The two lists answer different questions. The item data list is the
  intended configuration: what the delivery is supposed to consist of,
  item by item, at a stated revision. The as-built record is the
  delivered configuration: what was physically built and shipped,
  including the individual units. A delivery is identified only when the
  two agree, so the assessment is a two-way reconciliation, never a
  single pass down one of them.
- Identification is field-level, and the fields depend on what the item
  is. Every item carries an identifier, a part number, a revision and a
  responsible source. A programmable device additionally carries the
  device technology it was built in, a software load its build
  identifier, a mechanical part its material reference, and a delivered
  document its issue reference. A missing kind-specific field is an
  incomplete item, not a formatting preference.
- Only some kinds are individually traceable. A hardware assembly and a
  programmable device ship as units whose serial numbers have to appear
  in the as-built record; a document or a material reference identifies
  a type, so demanding a serial there is a false finding. The same
  serial recorded twice against one item is a real one.
- Revision drift is the quiet failure. An item listed at one revision
  and built at another still appears in both lists, so a count-based
  check passes it. The comparison has to be on the revision value, and
  both revisions are reported so the review can tell a late approved
  change from an uncontrolled build.
- A deviation is identifiable only through the waiver that carries it.
  An item citing a deviation reference with no approved waiver behind it
  is an unresolved delivery item, whatever its revision agreement looks
  like.

## Workflow

1. Validate every data-list entry against the fields its item kind
   demands, normalising identifiers so that padding and letter case
   cannot disguise a match or a duplicate.
2. Index the data list by item identifier and refuse a duplicate
   outright; a repeated identifier makes the reconciliation ambiguous
   rather than merely untidy.
3. Normalise the as-built record, keeping repeated lines for one item
   because multiple delivered units are the normal case, not an error.
4. Reconcile in both directions: listed items with no as-built line,
   as-built elements in no data-list item, revision disagreements naming
   both values, and serial numbers repeated against one item.
5. Apply the delivery obligations: a serialised kind delivered without a
   serial number, and every deviation reference without an approved
   waiver behind it.
6. Score identification coverage as the fraction of listed items that
   are present, revision-agreeing and, where serialised, serialled; then
   compare it with the required floor, absorbing representation error at
   the equality with a named tolerance rather than lowering the floor.
7. Report the item and line counts, the reconciliation, the obligation
   gaps, the coverage and its verdict, and the findings that name each
   defect kind separately.

## Pitfalls

- Reconciling by count. Equal item counts on both sides say nothing
  about which items they are; a listed item missing and an unlisted
  element delivered cancel out perfectly in a count.
- Walking the data list only. An element that was delivered but never
  listed is invisible from that direction, and it is the direction that
  hides an undocumented part in a shipped assembly.
- Treating a revision difference as a documentation tidy-up. Until the
  change behind it is shown to be approved, an item built at a revision
  other than the listed one is an uncontrolled configuration.
- Demanding a serial number from every item. Documents and material
  references identify types; a blanket serial rule turns an acceptable
  record into a page of false findings and hides the real gaps.
- Accepting a deviation reference as its own evidence. The reference is
  a pointer; without the approved waiver it points at nothing, and the
  item remains unidentified for delivery purposes.
- Lowering the coverage floor to clear a delivery that lands exactly on
  it. The equality is a representation question, handled by the
  tolerance inside the comparison; the floor stays where the review set
  it.

## Behavior contract (gate 3)

The entry validation, kind-specific field rules, duplicate-identifier
refusal, two-way reconciliation, revision-drift detection, serial and
waiver obligations and the coverage comparison are exercised by the gate
3 contract test:
scripts/test_q6003_configuration_item_data_lists.py against
scripts/q6003_configuration_item_data_lists_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6003_configuration_item_data_lists.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
