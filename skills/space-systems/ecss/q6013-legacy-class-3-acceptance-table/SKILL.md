---
name: q6013-legacy-class-3-acceptance-table
description: "Verify a legacy lot against the ECSS-Q-ST-60-13C Table 8-15 acceptance list. Use when an active commercial part is being accepted at the lowest assurance class and a reduced campaign has to become an accept-or-hold verdict: run the core groups on the delivered lot itself, let a non-consuming group carry an accept number while a consuming one stays accept-on-zero, admit heritage evidence for the remaining groups only when it covers the same part type from the same site inside its validity window, and cap how much of the set that evidence may stand in for. Trigger: ecss, q-st-60-13c-table-8-15, legacy-class-3-lot-acceptance-list, class-3-core-acceptance-groups, heritage-evidence-credit-admissibility, heritage-evidence-validity-window, acceptance-credit-budget-cap, consuming-group-accept-on-zero."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-3-acceptance-table, q-st-60-13c-table-8-15, legacy-class-3-lot-acceptance-list, class-3-core-acceptance-groups, heritage-evidence-credit-admissibility, heritage-evidence-validity-window, acceptance-credit-budget-cap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Legacy Class 3 Acceptance Table (space-systems/ecss/q6013-legacy-class-3-acceptance-table)

Use when the task is the legacy lot acceptance test list of ECSS-Q-ST-60-13C
Table 8-15 — taking the reduced group set the table allows for an active
commercial part at the lowest assurance class, deciding which groups have to
be run on the delivered lot and which heritage evidence may stand in for, and
turning the campaign into an accept-or-hold verdict.

## Domain quick reference

- The lowest assurance class is a reduced list, not an absent one. A small
  core is still run on the lot in hand; the relief is in what the remainder
  may be satisfied by, never in whether the core happens.
- Evidence is transferable only under conditions. Heritage or supplier data
  describes a part type built at a site at a time; change any of the three
  and the data describes something else, whatever its own quality was.
- A core group cannot be credited at any age. The core exists to say
  something about the devices being shipped, and no amount of history about a
  previous build substitutes for measuring the ones in the box.
- The relaxation at this class is in the accept numbers, not in destruction.
  A non-consuming group may carry an accept number above zero here; a group
  that takes its devices apart still has no rate to tolerate.
- Credit needs a budget. Each individually admissible credit looks reasonable,
  and a set that is mostly credit has quietly become a documentation review,
  so the share standing on evidence is capped and reported.
- Coverage and acceptance are different findings. A group nobody ran is not a
  group that failed, and the record separates the two so the gap is closed by
  running the group rather than by arguing about a verdict.

## Workflow

1. Validate each group: an unknown group name, an unknown satisfaction route,
   a credited group with no evidence mapping, an accept number above the
   sample, more failures than devices sampled, or an accept number above zero
   on a consuming group is an input error, not a case to clamp.
2. Judge a tested group against its required sample and accept number,
   carrying the shortfall in devices rather than as a bare failure.
3. Judge a credited group against admissibility: refuse credit on a core
   group outright, and otherwise require the same part type, the same site
   and an age inside the validity window, absorbing representation error at
   the boundary with a named tolerance rather than by widening the window.
4. Count the share of the set standing on evidence and compare it with the
   cap, reporting the credited and tested counts rather than a bare ratio.
5. Name the absent core groups separately from the merely absent groups, so
   the two gaps are closed by different actions.
6. Hold the lot when any single group rejects, rather than trading a tested
   group off against a credited one.

## Pitfalls

- Reading the lowest assurance class as permission to skip the core. The
  reduction is in the group set and the accept numbers, and a campaign that
  ran nothing on the delivered lot has accepted it on paper only.
- Accepting heritage data because it is about the same part number. Same part
  number from a different site is a different device, and the evidence then
  certifies a build that is not being shipped.
- Letting an accept number above zero onto a group that destroys its devices.
  The relaxation at this class applies to the non-consuming groups; a rate on
  a consumed sample is still not a rate.
- Approving credits one at a time. Each looks defensible in isolation, and
  the set ends up mostly documentary without any single decision saying so —
  which is exactly what the cap on the credited share is there to catch.
- Reporting an unrun group as a failed group. The first is closed by running
  it, the second by dispositioning a lot, and collapsing them sends the
  campaign down the wrong route.
- Widening the validity window to absorb an exact-equality case. Evidence
  landing exactly on the window is a representation question handled by the
  tolerance inside the comparison; the declared window stays as specified.

## Behavior contract (gate 3)

The group validation and satisfaction routes, the accept number a
non-consuming group may carry against the accept-on-zero rule for a consuming
one, credit admissibility with its core-group refusal and validity window,
the cap on the credited share, the separation of absent core groups from
absent coverage and the overall accept-or-hold disposition are exercised by
the gate 3 contract test:
scripts/test_q6013_legacy_class_3_acceptance_table.py against
scripts/q6013_legacy_class_3_acceptance_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_3_acceptance_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
