---
name: q7053-acceptance-criteria
description: "Determine whether an item passes the acceptance criteria its own material or hardware category carries, in the acceptance clauses of ECSS-Q-ST-70-53C. Use when a sterilization-compatibility exposure is finished and a per-item accept, accept-with-deviation or reject decision has to be written down. Selects the criteria set from the declared category instead of a blanket default, refuses a category the table does not carry, applies each criterion in its own direction, resolves a mixed assembly to the most severe constituent category, treats an unmeasured criterion as unevidenced rather than as a pass, routes a breach inside the deviation band only when a deviation reference exists, and names the governing criterion. Trigger: ecss, q-st-70-53-sterilization-compatibility-scope, sterilization-acceptance-criteria, material-category-criteria-set, mixed-assembly-category-resolution, accept-with-deviation-routing, governing-acceptance-criterion."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-acceptance-criteria, sterilization-acceptance-criteria, material-category-criteria-set, mixed-assembly-category-resolution, accept-with-deviation-routing, governing-acceptance-criterion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Acceptance Criteria (space-systems/ecss/q7053-acceptance-criteria)

Use when the task is the acceptance step of an ECSS-Q-ST-70-53C
compatibility evaluation — turning the measured post-exposure figures
of one item into an accept, accept-with-deviation or reject decision
against the criteria its own category carries.

## Domain quick reference

- The criteria set belongs to the category, not to the campaign. A
  polymer seal, a metallic bracket, a structural adhesive, an optical
  window and an electronic assembly are held to different limits after
  the same exposure, and a single blanket percentage across the list
  either passes a degraded polymer or rejects a healthy bracket.
- A criterion has a direction. A retention fraction is a floor, a mass
  loss or a dimensional change is a ceiling; grading a floor as a
  ceiling inverts the decision for every item in the set.
- A mixed assembly is graded against the most severe category among its
  constituents. A bracket with a bonded polymer insert is not a metal
  item because most of its mass is metal.
- A criterion with no measurement behind it is unevidenced, not
  satisfied. Silence is the most common route to a false accept, so a
  missing measurement stops the item at reject until the value exists.
- The deviation band is the only route to an accept above a limit, and
  it is not automatic: it needs a deviation reference recorded against
  the item. A breach inside the band with no reference is a reject that
  can be reopened, not an accept.
- The governing criterion is the one with the highest utilisation of
  its own limit, which is what the decision has to quote — not the
  largest raw number in the measurement set.

## Workflow

1. Resolve the category: a declared single category, or the most severe
   of the declared constituent categories by the declared severity
   order. Refuse a category the criteria table does not carry rather
   than falling back to a default set.
2. Pull the criteria set for that category and check that every
   criterion in it has a measurement; list the ones that do not.
3. Apply each criterion in its own direction, absorbing representation
   error at the limit with a named tolerance rather than relaxing the
   limit.
4. For each breach, test whether it falls inside the criterion's
   deviation band; a breach beyond the band can never be accepted.
5. Compute each criterion's utilisation of its own limit and name the
   governing criterion, breaking an exact tie on the criterion name.
6. Decide: accept when everything is inside its limit and evidenced;
   accept-with-deviation when every breach is inside its band and a
   deviation reference exists; reject otherwise.
7. Report findings naming each breach with its band verdict, each
   unevidenced criterion, and each measurement that no criterion in the
   category claims.

## Pitfalls

- Carrying one pair of limits across a mixed materials list. The
  category selects the criteria set, and using the wrong set is not a
  conservative error in either direction.
- Reading a missing measurement as a pass. An unevidenced criterion is
  reported and blocks the accept; it is not absorbed into the decision.
- Treating the deviation band as extra limit. The band only says which
  breaches are reopenable; without a recorded deviation reference the
  item is still rejected.
- Resolving a mixed assembly by mass fraction or by the part number's
  first material. The severity order over the constituents decides,
  because the weakest constituent governs the compatibility statement.
- Quoting the biggest percentage as the reason for the decision.
  Utilisation against each criterion's own limit is what identifies the
  governing criterion.

## Behavior contract (gate 3)

The category resolution, criteria-set selection, direction-aware
criterion application, deviation-band routing, unevidenced-criterion
handling and governing-criterion selection are exercised by the gate 3
contract test: scripts/test_q7053_acceptance_criteria.py against
scripts/q7053_acceptance_criteria_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7053_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
