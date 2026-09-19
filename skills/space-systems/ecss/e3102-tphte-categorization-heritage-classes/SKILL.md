---
name: e3102-tphte-categorization-heritage-classes
description: "Determine the type grouping and heritage category of two-phase heat transport equipment, and the qualification depth that follows, per ECSS-E-ST-31-02C clause 4.1 and clause 5.4. Use when a heat pipe, variable conductance pipe, diode pipe or capillary driven loop is offered against a qualified predecessor: compare fluid, envelope, wick, type, application, length and power scaling and operating range, place the item in the unchanged, modified or new-development category, and derive the test set and unit count it owes including the demonstrations its own type carries. Trigger: ecss, e-st-31-02-two-phase-heat-transport, e3102-tphte-categorization-heritage-classes, heat-pipe-heritage-category, variable-conductance-heat-pipe-reservoir-test, diode-heat-pipe-reverse-mode-test, capillary-driven-loop-start-up-test, tphte-qualification-depth-selection."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport, e3102-tphte-categorization-heritage-classes, heat-pipe-heritage-category, variable-conductance-heat-pipe-reservoir-test, diode-heat-pipe-reverse-mode-test, capillary-driven-loop-start-up-test, tphte-qualification-depth-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Equipment — Type and Heritage Grouping (space-systems/ecss/e3102-tphte-categorization-heritage-classes)

Use when the task is the grouping step of ECSS-E-ST-31-02C clause 4.1 and
the qualification depth table of clause 5.4 -- placing a two-phase heat
transport item by equipment type and by heritage against a qualified
predecessor, and reading off how much qualification the pairing owes.

## Domain quick reference

- Two axes decide the depth, and they are independent. The equipment type
  says which demonstrations the hardware carries inherently; the heritage
  category says how much of the common programme can be stood down.
- The four types are not variations on one part. A constant conductance
  pipe transports; a variable conductance pipe additionally controls, so it
  owes a reservoir inventory and a control-range demonstration; a diode
  owes a reverse-mode shut-off; a capillary driven loop owes start-up and
  load-sharing runs. These are owed in every heritage category, including
  the unchanged one.
- Heritage has three categories: unchanged against a qualified item in the
  same application, modified within the qualified envelope, and new
  development. The first two are the ones that get argued about, and the
  argument is settled attribute by attribute.
- Some changes are categorical, not incremental. A different working fluid,
  envelope material, wick type or equipment type is a new development
  whatever the size of the change -- the qualification evidence does not
  transfer across a fluid or a capillary structure.
- Other changes are scaling questions with a boundary. A length or
  transport-power ratio inside the qualified envelope is a modification; a
  ratio outside it is a new development. The ratio is taken in both
  directions, because a shorter pipe at lower power is also outside a
  qualified envelope when it is far enough outside.
- An operating range extension is measured at both ends, and the larger of
  the two extensions governs. A small extension is a modification; a large
  one is a new development.
- Changing the application alone, with no hardware change at all, is a
  modification. The item is unchanged; what it is being asked to do is not.
- Ratios and temperature extensions are float quotients and differences, so
  an item dimensionally identical to its reference has to land on unity on
  every platform. That is what the named tolerance is for, and the envelope
  boundary is graded with the same tolerance so a ratio exactly on it stays
  on the shallower side.

## Workflow

1. Record the candidate and the qualified reference across the same eight
   attributes: equipment type, working fluid, envelope material, wick type,
   application, length, transport power and operating range.
2. Refuse a register naming a type outside the four, carrying a blank
   attribute, or giving an inverted operating range.
3. Take the length and power scaling ratios and the operating range
   extension, measured at both ends with the larger governing.
4. Apply the categorical changes first: type, fluid, envelope, wick, or a
   scaling ratio or range extension outside the envelope, each places the
   item in new development.
5. Apply the incremental changes next: a scaling ratio off unity but inside
   the envelope, a small range extension, or a changed application, each
   places the item in the modified category.
6. With neither present, the item is unchanged and carries acceptance only.
7. Derive the depth: the common test set of the category, unioned with the
   demonstrations the equipment type owes, plus the unit count.
8. Roll a set up: category counts, the item driving the deepest
   qualification, the total unit count and the combined test set.

## Pitfalls

- Reading the heritage category off the equipment type. A capillary driven
  loop identical to a flown one is an unchanged item; a heat pipe with a
  new fluid is a new development. The two axes do not substitute.
- Standing down a type demonstration because the category is the shallowest
  one. A variable conductance pipe owes its reservoir inventory check
  whatever its heritage.
- Treating a fluid or wick change as a scaling question. There is no ratio
  small enough to make a different fluid a modification.
- Taking the scaling ratio in one direction only, so a much shorter or much
  lower-power item reads as inside the envelope.
- Measuring the range extension at the hot end alone. The cold end fails
  differently and is just as far outside.
- Reading a changed application as no change because the drawing is the
  same. The qualified evidence is evidence about an application.
- Reporting a category without the reasons. The reasons are the negotiation
  with the customer, and a bare letter cannot be argued.
- Using a strict comparison at the envelope ratio or the extension
  threshold. A value sitting exactly on the boundary must land on the same
  side on every platform, which is what the named tolerances do.

## Behavior contract (gate 3)

The four equipment types with their inherent demonstrations, the three
heritage categories with their common test sets and unit counts, the
categorical-change rules, the two-directional scaling envelope with its
on-boundary case, the two-ended range extension with its threshold case,
the application-only modification, and the set roll-up with category
counts, deepest item, total units and combined test set are exercised by
the gate 3 contract test:
scripts/test_e3102_tphte_categorization_heritage_classes.py against
scripts/e3102_tphte_categorization_heritage_classes_logic.py (stdlib
unittest, offline). Boundary cases are built from the published thresholds
rather than from a second copy of the comparison.
Run: python3 scripts/test_e3102_tphte_categorization_heritage_classes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
