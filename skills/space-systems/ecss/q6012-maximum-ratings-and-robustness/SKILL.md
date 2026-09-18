---
name: q6012-maximum-ratings-and-robustness
description: "Verify that the absolute maximum ratings declared for a MMIC die sit below the measured degradation onset by the required factor, that every rating is backed by a robustness demonstration driven at or above its own boundary on a large enough sample, and that worst-case application stress stays inside the derated envelope, per ECSS-Q-ST-60-12C clause 7.2.9. Use when a die specification proposes maximum ratings and the evidence file has to accept or hold them. Refuses a non-positive boundary, a safety factor below one and a derating factor above one. Trigger: ecss, q-st-60-12c, mmic-absolute-maximum-rating, mmic-die-robustness-demonstration, degradation-onset-margin, mmic-derating-envelope, worst-case-applied-stress, step-stress-evidence, mmic-die-boundary-condition."
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
  tags: [ecss, q-st-60-12-mmic-die-scope, q6012-maximum-ratings-and-robustness, mmic-absolute-maximum-rating, mmic-die-robustness-demonstration, degradation-onset-margin, mmic-derating-envelope, worst-case-applied-stress]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Die -- Absolute Maximum Ratings and Robustness (space-systems/ecss/q6012-maximum-ratings-and-robustness)

Use when the task is the maximum-rating step of ECSS-Q-ST-60-12C clause 7.2.9:
a MMIC die has a proposed set of absolute limits -- drain-source voltage, gate
current, channel temperature, RF drive -- and the question is whether those
limits were drawn correctly from stress data and whether the die has been shown
to survive at them.

## Domain quick reference

- A maximum rating is a boundary condition, not a target. It is drawn from a
  measured degradation onset and placed below that onset by a safety factor, so
  a rating quoted level with the onset is not a rating at all, it is the point
  at which the part stops working.
- The rating and the application limit are two different numbers. The rating is
  the die boundary; the application is held below it by a derating factor, and
  the stress that is compared against the derated envelope is the worst case --
  nominal inflated by its tolerance and by any transient factor -- not the
  nominal itself.
- Robustness is a demonstration, not an assertion. Each rating owes evidence
  driven at or above its own boundary, on a sample large enough to be a sample,
  for long enough to expose a wear-out mechanism, with no device lost and no
  parameter drift beyond the allowed fraction.
- Evidence driven below the boundary demonstrates the stress applied, not the
  rating. A soak at ninety per cent of a limit supports a rating at ninety per
  cent of that limit and nothing higher.
- Ratings are magnitudes here. A boundary that is physically negative, such as
  a gate-source floor, is entered as its absolute value together with the
  applied stress, so a single comparison direction covers every rating.

## Workflow

1. Validate each rating: a name, a positive boundary, the onset it was drawn
   from, a safety factor of at least one, and a derating factor in the interval
   above zero up to one. A duplicate rating name is an input error.
2. Form the onset headroom as the ratio of onset to boundary and compare it
   with the required safety factor, absorbing floating-point representation
   error at the boundary with a named tolerance rather than by relaxing the
   required factor.
3. Gather the robustness demonstrations that name this rating and review the
   strongest one -- highest stress, then largest sample, then longest soak --
   against the boundary, the minimum sample size, the minimum duration, the
   device losses and the drift allowance, in that order.
4. Build the worst-case applied stress from the nominal, its tolerance fraction
   and its transient factor, form the derated envelope from the boundary and
   the derating factor, and take the usage ratio between them.
5. Record every broken rule for the rating, not just the first, so one report
   closes the whole gap instead of exposing it one run at a time.
6. Group the ratings by outcome with findings ordered ahead of acceptance, and
   accept the file only when every rating is accepted.

## Pitfalls

- Quoting the degradation onset as the maximum rating. The onset is where the
  die changes; the rating has to sit below it by the declared factor, and a
  specification that publishes the onset has published a failure point.
- Comparing the nominal application condition against the rating. The
  comparison is worst case against the derated envelope; a supply tolerance and
  a switching transient both sit between the two, and either can turn a
  comfortable nominal into an over-stress.
- Accepting a robustness soak run below the boundary because it passed. A pass
  at a lower stress is evidence for the lower stress only, and reading it as
  coverage of the boundary is how a rating ships unproven.
- Counting a demonstration that lost a device as a pass because the sample
  still met its accept number. At a boundary condition a loss is the result:
  the boundary is above where this population survives.
- Widening the derating factor to clear an over-stress finding. The derating
  factor comes from the design rules, and moving it to fit the application
  converts a documented over-stress into an undocumented one.

## Behavior contract (gate 3)

The rating validation, onset-headroom comparison, robustness-evidence review,
worst-case stress and derated-envelope check and the grouped verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_maximum_ratings_and_robustness.py against
scripts/q6012_maximum_ratings_and_robustness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_maximum_ratings_and_robustness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
