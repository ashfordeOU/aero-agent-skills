---
name: q60-class-1-preferred-component-sources
description: "Assess where each Class 1 part sits on the European preferred parts list, and what a step away from part one costs, under ECSS-Q-ST-60C clause 4.2.2.3: grade every candidate's listing tier, test whether a part one equivalent was searched for before a lower tier was taken and whether one was known to exist, dock the assurance for a missing procurement specification, then measure the part one share of the declared list against the project floor, pick a selection route per part, and name the justification, board approval or evaluation each departure buys. Use when a Class 1 parts list has to show it was drawn preferentially from part one. Trigger: ecss, q-st-60-eee-selection-scope, class-1-preferred-parts-listing, eppl-part-one-selection, eppl-part-two-justification, parts-control-board-approval-route, preferred-list-share-floor, unlisted-part-evaluation-burden."
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
  tags: [ecss, q-st-60-eee-selection-scope, q60-class-1-preferred-component-sources, class-1-preferred-parts-listing, eppl-part-one-selection, eppl-part-two-justification, parts-control-board-approval-route, preferred-list-share-floor, unlisted-part-evaluation-burden, part-one-alternative-search]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Preferred Component Sources (space-systems/ecss/q60-class-1-preferred-component-sources)

Use when the task is the selection direction of ECSS-Q-ST-60C clause
4.2.2.3 -- deciding, for a Class 1 design, whether each part is drawn
from part one of the European preferred parts list, and what has to be
recorded, approved or evaluated wherever it is not.

## Domain quick reference

- On a Class 1 design, the list a part comes from is a design decision
  rather than a purchasing detail. Part one of the European preferred
  parts list is the directed source; every other tier is a departure
  that has to be bought back with evidence.
- The tiers run from part one, through part two, through a part
  qualified against an agency component specification but on neither
  list part, through a part qualified under another agency's scheme,
  down to a maker's catalogue item with no space qualification behind
  it at all.
- Preference is not a tier lookup on its own. A lower tier taken with
  no search for a part one equivalent, or taken while a part one
  equivalent was known to be available, departs from the direction of
  the clause even when the part itself is perfectly sound.
- A part with no procurement specification reference has nothing to be
  bought against, so the departure loses further assurance: the tier
  says what the part is, the specification says what will be delivered.
- The design-level answer is a share, not a verdict per part. The share
  of the declared list drawn from part one is what shows the preference
  was exercised; a list where every single departure is separately
  justified can still miss the direction of the clause.
- The useful output names the route each departure has to travel --
  a recorded justification, a parts control board approval, or a full
  evaluation programme -- and the one part sitting on the least
  assurance, because that is where the next reselection lands.

## Workflow

1. Declare each candidate with its part reference, its listing tier,
   whether a part one equivalent was searched for, whether one was
   available, and the procurement specification it is bought against.
   Reject an uncategorized tier rather than defaulting it.
2. Take the tier assurance, then dock it for each departure signal: no
   search performed, an available part one equivalent passed over, and
   a missing procurement specification reference.
3. Pick the route from the tier, then escalate it where an available
   part one equivalent was passed over or where the docked assurance
   falls under the board approval threshold. Treat assurance sitting
   exactly on a threshold as meeting it, not as breaching it.
4. Send a candidate back for reselection only when the docked assurance
   falls under the reselect threshold; a weak tier with clean evidence
   is an evaluation task, not a rejection.
5. Measure the part one share across the declared list against the
   project floor, and report a share landing exactly on the floor as
   met.
6. Close with one list verdict, the departures, the approvals and
   evaluations owed, and the weakest part by assurance.

## Pitfalls

- Reading the clause as a per-part gate. Each departure can carry a
  clean justification while the list as a whole drifts off part one,
  so the share against the floor is the measurement that matters.
- Treating a lower tier as automatically unacceptable. A part
  qualified under another agency's scheme is usable; what it costs is
  an evaluation programme, and calling it a rejection hides that work
  rather than scheduling it.
- Passing a departure that was never compared with part one. If no
  search was performed the preference was not exercised at all, and no
  amount of later paperwork reconstructs a comparison that never ran.
- Taking the tier as the whole record. Without a procurement
  specification the project has no statement of what will actually be
  delivered against that tier, so the assurance is lower than the tier
  alone suggests.
- Comparing a share with its floor by bare arithmetic. The share is a
  quotient and the floor is a policy constant, so a list built to sit
  exactly on its floor can land a few units in the last place below
  it; the comparison absorbs that representation error while the floor
  stays untouched.

## Behavior contract (gate 3)

The policy validation, tier assurance lookup, departure penalties,
docked selection assurance, route escalation, reselect threshold,
part one share, list rollup and weakest-part selection are exercised by
the gate 3 contract test:
scripts/test_q60_class_1_preferred_component_sources.py against
scripts/q60_class_1_preferred_component_sources_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_preferred_component_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
