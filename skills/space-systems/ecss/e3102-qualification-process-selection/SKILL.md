---
name: e3102-qualification-process-selection
description: "Determine whether a two-phase heat transport item owes a full qualification programme, a delta programme, or none at all under ECSS-E-ST-31-02C clauses 5.3 and 5.4. Use when the task is weighing a heritage qualification record against the design modifications a new application introduces, deciding which of those modifications are fundamental enough to reopen the whole programme on their own, confirming the requested operating envelope still sits inside the envelope the predecessor was qualified over, and deriving the delta test scope the remaining modifications owe. Trigger: ecss, e-st-31-02c, two-phase-heat-transport-qualification, heritage-qualification-envelope, delta-qualification-scope, full-qualification-trigger, design-modification-extent, qualification-path-decision."
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
  tags: [ecss, e-st-31-02-two-phase-scope, e3102-qualification-process-selection, two-phase-heat-transport-qualification, heritage-qualification-envelope, delta-qualification-scope, design-modification-extent, qualification-path-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Qualification Process Selection (space-systems/ecss/e3102-qualification-process-selection)

Use when the task is the qualification-path decision of ECSS-E-ST-31-02C
clauses 5.3 and 5.4 -- routing a heat pipe, loop or capillary pumped item
to a full qualification programme, to a delta programme over a named test
scope, or to no new qualification at all because heritage already covers
it.

## Domain quick reference

- The decision has three outcomes, not two. Heritage that covers the new
  application with no design change carries the qualification outright; a
  bounded change buys a delta programme over the reopened items only; and
  a change that touches the physics, or an application outside the
  qualified envelope, goes back through a full programme. Collapsing this
  to "delta or full" throws away the cheapest legitimate answer and also
  hides the case where heritage is being claimed without evidence.
- Heritage is a record, not a reputation. A predecessor counts only when
  it was actually qualified, when its qualification evidence is complete,
  and when the envelope it was qualified over is written down. An item
  "flown before" with no stated envelope contributes nothing, because
  there is no span to compare the new application against.
- Modifications divide into fundamental and bounded. Working fluid,
  envelope material, wick type and the closure weld process change what
  the two-phase loop physically is: fluid compatibility, transport limit
  and long-term non-condensable-gas generation all reset, so one of them
  alone sends the item back through a full programme. Diameter, length,
  charge mass, groove geometry, reservoir volume, bend layout, saddle and
  manufacturing site move a quantity inside the same physics, and each
  reopens a named subset of the test matrix.
- Bounded changes still accumulate. Six small modifications at once are
  not six small deltas: the interactions between them are exactly what a
  delta programme does not test. A weighted extent index over the distinct
  categories, compared with a stated threshold, is what keeps a stack of
  individually harmless changes from being waved through.
- An envelope parameter the heritage record never mentions is an
  exceedance, not a pass. Silence in a qualification envelope is absence
  of evidence, and the request has to be treated as outside it.

## Workflow

1. Validate the heritage record: qualified flag, evidence-complete flag
   and a stated qualification envelope of parameter ranges. A missing
   flag or an inverted range is an input error, not a default.
2. Compare the requested application envelope against the qualified one
   parameter by parameter. A request equal to a qualified bound is inside
   it, with only the representation error of the comparison absorbed by a
   named tolerance; a parameter absent from the qualified envelope is an
   exceedance.
3. Categorize each declared modification, rejecting a category the
   matrix does not know rather than scoring it as harmless. Collapse
   repeats so the same change declared twice is weighted once.
4. Separate the fundamental categories from the bounded ones and
   accumulate the extent index over the distinct bounded categories.
5. Route the item: full when heritage is absent or incomplete, when any
   envelope exceedance exists, when any fundamental modification is
   present, or when the extent index reaches the full-programme
   threshold; delta when bounded modifications remain; none otherwise.
6. Derive the test scope: the union of the reopened items for a delta,
   and that union widened to the baseline qualification matrix for a
   full programme.
7. Report the path with the explicit list of reasons that produced it,
   so a reviewer can see which single driver would have to change for
   the cheaper path to become available.

## Pitfalls

- Reading "similar to a qualified unit" as heritage. Similarity without a
  written envelope and complete evidence gives nothing to compare, and the
  correct output is a full programme, not an optimistic delta.
- Treating a fluid change as a bounded modification because the geometry
  is untouched. The fluid sets the transport limit, the compatibility
  couple and the gas-generation rate; none of the predecessor's life
  evidence transfers.
- Scoring the same modification twice because it was declared once per
  drawing. The extent index is over distinct categories, or a paperwork
  artefact inflates the path.
- Letting a stack of small changes through one at a time. Each passes the
  fundamental test and each has a low weight; the threshold exists because
  their interaction is what neither delta covers.
- Widening the qualified envelope on paper so the new application fits.
  The envelope is what was demonstrated; an application outside it is a
  full-qualification driver, and an exact equality at a bound is a
  representation question handled inside the comparison.

## Behavior contract (gate 3)

The heritage validation, envelope comparison, modification categorization,
extent-index accumulation, path routing and scope derivation are exercised
by the gate 3 contract test:
scripts/test_e3102_qualification_process_selection.py against
scripts/e3102_qualification_process_selection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3102_qualification_process_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
