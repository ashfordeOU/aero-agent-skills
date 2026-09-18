---
name: q7036-alloy-selection-criteria
description: "Evaluate candidate alloy states against the stress-corrosion-cracking acceptance rules of ECSS-Q-ST-70-36C. Use when a field of alloys has to be narrowed for an application whose SCC criticality is already known: read the published resistance rating of each state, take a rating step off any candidate whose sustained tensile stress acts along the short-transverse grain direction, apply the acceptance rule the criticality imposes so a critical item needs a resistant state outright and takes an intermediate one only against documented test evidence, then rank what survives by rating, strength and identifier. Trigger: ecss, q-st-70-36c, scc-alloy-selection, scc-resistance-rating, short-transverse-rating-downgrade, scc-acceptance-rule, scc-candidate-ranking."
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
  tags: [ecss, q-st-70-materials-scope, q-st-70-36c, q7036-alloy-selection-criteria, scc-alloy-selection, scc-resistance-rating, short-transverse-rating-downgrade, scc-acceptance-rule, scc-candidate-ranking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Materials — SCC Alloy Selection Criteria (space-systems/ecss/q7036-alloy-selection-criteria)

Use when the task is the selection step of ECSS-Q-ST-70-36C -- deciding
which candidate alloy states may be used in an application whose
stress-corrosion-cracking criticality has already been established, and
which of them owe evidence or an approval first.

## Domain quick reference

- Alloy states carry a published SCC resistance rating in three grades:
  resistant, intermediate and susceptible. The rating belongs to the
  state -- the alloy together with its temper or heat-treatment
  condition -- not to the alloy designation, so two tempers of one alloy
  routinely sit in different grades.
- The published ratings are direction-sensitive. Sustained tensile
  stress acting along the short-transverse grain direction of a wrought
  product is the weak case, and a state loaded that way is treated one
  grade less resistant than its published rating. Longitudinal and
  long-transverse loading keep the published grade.
- The acceptance rule is the criticality's, not the alloy's. An SCC
  critical application takes a resistant state outright, takes an
  intermediate one only against documented test evidence for that exact
  state, and cannot take a susceptible one without a formal approval. A
  monitored application relaxes each of those by one grade, and an
  application already cleared of criticality is unconstrained here.
- Ranking is a selection aid, not the decision. The order is effective
  rating first -- resistance is what the clause buys -- then the yield
  strength the state delivers, then the identifier, so that a rerun on
  the same field produces the same recommendation.
- Two strengths an engineer intends to be equal must tie. Ordering them
  on a representation difference makes the recommendation depend on how
  the number was typed, so the comparison is quantised to a named
  tolerance before the identifier breaks the tie.

## Workflow

1. Normalize the resistance rating, the criticality grade and the grain
   direction of every candidate; refuse a value that maps to none of the
   known tokens rather than defaulting it.
2. Derive the effective rating: apply the one-grade downgrade when the
   loaded direction is short-transverse, floored at the lowest grade.
3. Look up the acceptance verdict for the effective rating at the
   application's criticality -- accepted, accepted-with-evidence, or
   rejected -- and attach the note that says what the verdict costs.
4. Rank the field by effective rating, then descending yield strength
   quantised to the named tolerance, then identifier.
5. Recommend the best outright-acceptable state; fall back to the best
   evidence-only state and raise that fallback as a finding, and report
   no recommendation at all when the whole field is rejected.
6. Raise a finding for every candidate that lost a grade to
   short-transverse loading, so the direction assumption is visible to
   whoever reviews the choice.

## Pitfalls

- Selecting on the alloy designation instead of the state. The rating
  moves with the temper; quoting an alloy family rating for a part
  procured in a different condition imports the wrong grade into the
  whole selection.
- Ignoring the loaded direction. A resistant state loaded
  short-transverse is treated as intermediate, which at critical
  criticality turns an outright acceptance into an evidence obligation.
- Reading "accepted-with-evidence" as accepted. It is a commitment to
  produce state-specific test data; recording it as a pass leaves the
  application with no substantiation at review.
- Ranking on strength before resistance. The highest-strength state is
  very often the least resistant one, and a strength-first order
  recommends exactly the candidate the clause exists to avoid.
- Letting a floating-point difference order two equal strengths. The
  recommendation then flips between runs and between machines, which
  reads as an unexplained change of design.

## Behavior contract (gate 3)

The token normalization, the rating algebra and its floor, the
short-transverse downgrade, the criticality acceptance table, the
candidate evaluation and the tolerance-quantised ranking and
recommendation are exercised by the gate 3 contract test:
scripts/test_q7036_alloy_selection_criteria.py against
scripts/q7036_alloy_selection_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7036_alloy_selection_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
