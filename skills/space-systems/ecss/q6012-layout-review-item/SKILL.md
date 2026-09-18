---
name: q6012-layout-review-item
description: "Review the physical layout a device design review is presented with and decide whether the item closes or carries an action. Use when an ECSS-Q-ST-60-12C clause 7.3.7 layout review item has to reach a verdict: confirm every required drawing kind is present, released and standing at the design baseline issue rather than above or below it; take each interface pad as placed once, inside the outline keep-out, with the closest pad pair no tighter than the declared minimum pitch; and carry a residual rule-check error, a check never run or a waiver cited without approval as an open action instead of a pass. Trigger: ecss, q-st-60-12c-clause-7-3-7, layout-review-item, terminal-pad-placement, layout-drawing-baseline-issue, minimum-pad-pitch-check, design-rule-check-residual, layout-waiver-approval."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-layout-review-item, q-st-60-12c-clause-7-3-7, layout-review-item, terminal-pad-placement, layout-drawing-baseline-issue, minimum-pad-pitch-check, design-rule-check-residual, layout-waiver-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Design Review -- Layout Review Item (space-systems/ecss/q6012-layout-review-item)

Use when the task is the layout review item of ECSS-Q-ST-60-12C clause
7.3.7: the physical drawing set, the terminal pad placement and the
rule-check status are on the table, and the review has to decide whether the
item closes or carries an action.

## Domain quick reference

- The item has three independent leaves and a pass needs all three. The
  drawing set says what is being built, the pad placement says how it meets
  the world outside it, and the rule-check status says whether the geometry
  obeys the process. A clean rule check over an incomplete drawing set is
  not a layout that has been reviewed.
- A drawing is only evidence at the right issue. Below the design baseline
  it describes an older design; above it, the drawing is not the problem --
  the baseline record is stale, and the review is being shown a
  configuration nobody has agreed to. Both are findings, and they call for
  opposite corrective actions, so they are reported apart.
- Pad placement is a set question before it is a geometry question. Every
  pad the interface definition names has to be placed, placed once, and
  nothing else placed beside it; a pad present twice makes the net it
  carries ambiguous, and a pad nobody asked for is either a probe point that
  escaped or a name that drifted.
- The geometry then adds two limits. A pad centre has to sit inside the
  outline with the keep-out respected, and the closest pad pair has to stand
  at or beyond the minimum pitch. The closest pair is found by searching
  every pair, because the tightest spacing is rarely between neighbours in
  the order the pads were listed.
- A rule check is cleared, waived or open, and nothing else. An approved
  waiver removes the errors it covers and no more; an unapproved waiver
  removes none, and a waiver covering more errors than were reported is a
  bookkeeping error that stops the item rather than clearing it.
- A required check that was never run is not a clean check. Its absence is
  its own finding, distinct from a check that ran and found errors.

## Workflow

1. Validate the outline and the declared minimum pitch first; a collapsed
   outline, or a keep-out wider than the die it is cut from, is an input
   error that stops the item.
2. Take the drawing set against the required kinds and the baseline issue,
   separating missing kinds, duplicated kinds, unreleased sheets, drawings
   behind the baseline and drawings ahead of it.
3. Take the placed pads against the interface definition, reporting missing,
   repeated and unexpected names separately.
4. Check outline containment with the keep-out, absorbing a pad sitting
   exactly on the keep-out line with a named tolerance scaled to the
   coordinate rather than by shrinking the keep-out.
5. Search every pad pair for the closest separation and compare it with the
   minimum pitch, absorbing an exact equality at the pitch the same way.
6. Reduce each rule check to its residual: reported errors less the errors
   covered by approved waivers, with unapproved waivers named.
7. Close the item only when all three leaves are clean, and report every
   finding rather than the first, because the actions go to different owners.

## Pitfalls

- Accepting a drawing at a higher issue than the baseline because newer
  looks safer. The review then has no agreed configuration, and the finding
  belongs to the baseline record, not to the drawing.
- Comparing only neighbouring pads for the minimum pitch. The closest pair
  is a property of the placement, not of the listing order, so the search
  covers every pair.
- Reading an unapproved waiver as a waiver. It cites a route to closure that
  nobody has taken; the errors it names are still standing.
- Letting a waiver cover more errors than were reported. That is a
  bookkeeping error whose effect is a silently clean check, so it stops the
  item instead of clearing it.
- Reporting a required rule check that was never run as clean. Absence and
  zero errors are different states and lead to different actions.
- Shrinking the keep-out or the pitch to pass a pad sitting exactly on the
  line. The equality is a representation question handled by the tolerance
  inside the comparison; the declared geometry stays as specified.

## Behavior contract (gate 3)

The outline and pad validation, the pad-set difference, outline containment
with keep-out, the all-pairs minimum-pitch search, the drawing-set findings
against the baseline issue, the waiver-adjusted rule-check residual and the
review disposition are exercised by the gate 3 contract test:
scripts/test_q6012_layout_review_item.py against
scripts/q6012_layout_review_item_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6012_layout_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
