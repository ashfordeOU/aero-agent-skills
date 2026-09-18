---
name: q6012-derating-review-item
description: "Verify at a design review that every declared device stress stays inside the reduced limit its derating rule sets, not merely inside the absolute maximum rating. Use when an ECSS-Q-ST-60-12C clause 7.3.6 derating review item has to close or stay open: resolve each rule into a derated limit by permitted-fraction or absolute-offset reduction in the conservative direction of the bound, open a nominal stress up to its worst case with the declared uncertainty, judge it on margin so a scale running negative still decides, and report a stress carrying no rule, or a required stress never declared, as an open item rather than a pass. Trigger: ecss, q-st-60-12c-clause-7-3-6, derating-review-item, derated-stress-limit, device-stress-utilisation, worst-case-stress-uncertainty, uncovered-derating-rule, derating-review-disposition."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-derating-review-item, q-st-60-12c-clause-7-3-6, derating-review-item, derated-stress-limit, device-stress-utilisation, worst-case-stress-uncertainty, uncovered-derating-rule, derating-review-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Design Review -- Derating Review Item (space-systems/ecss/q6012-derating-review-item)

Use when the task is the derating review item of ECSS-Q-ST-60-12C clause
7.3.6: a design has declared the stresses its devices see, a derating
standard has set reduced limits for them, and the review has to decide
whether the item closes or carries an action.

## Domain quick reference

- The absolute maximum rating is not the limit the review judges against.
  The derating rule moves the rating away from the failure point, and the
  derated limit it produces is the only number a stress is compared with.
  A stress quoted as a percentage of the rating has already answered the
  wrong question.
- A rule reduces in one of two shapes. A permitted fraction scales the
  rating, which suits voltage, current and power; an absolute offset steps
  away from it, which suits a temperature whose scale has no physical zero
  at its origin. Both move in the conservative direction of the bound they
  guard: down for an upper bound, up for a lower one.
- The stress that matters is the worst case, not the nominal. Tolerance,
  ageing and end-of-life drift open the nominal value up, and the widening
  goes away from the bound, so a stress quoted on a scale that runs
  negative is still widened towards its limit rather than away from it.
- The verdict is a margin, and the utilisation ratio is reporting. A ratio
  needs a denominator with a physical zero, so a junction temperature in
  degrees Celsius has a margin but no meaningful utilisation; judging it on
  the ratio invents a number the reviewer would then act on.
- A stress with no rule behind it is an open item. So is a stress the
  device owed the review and never declared. Neither is silence that can be
  read as a pass, because the review is a coverage statement as much as a
  comparison.

## Workflow

1. Validate the declared rules first: a fraction outside its interval, an
   offset that is negative, or an unknown bound direction is an input error
   that stops the item rather than a rule to be clamped.
2. Resolve each cited rule into the derated limit for the device's rating,
   refusing a fraction rule against a rating that is not positive.
3. Open every nominal stress up to its worst case with the declared
   uncertainty, widening it towards the bound it is judged against.
4. Take the signed margin to the derated limit and absorb an exact equality
   at the limit with a named tolerance scaled to the limit, rather than by
   relaxing the derating rule.
5. Report the utilisation ratio only where the scale admits one, and carry
   the item on margin alone where it does not.
6. Collect the open items: each exceedance named individually, each stress
   with no rule behind it, and each required stress a listed device never
   declared.
7. Close the review item only when nothing is open, and report the tightest
   normalised margin as the item the next design change has to protect.

## Pitfalls

- Comparing the stress with the absolute maximum rating. That is the number
  the derating rule exists to move; a stress inside the rating and outside
  the derated limit is the defect this item was written to catch.
- Judging the nominal stress. The nominal is one point of a distribution
  the tolerance stack and end-of-life drift widen, and the review item
  covers the worst case of that spread.
- Reporting a utilisation ratio on a scale whose zero is arbitrary. The
  ratio looks authoritative and is meaningless, and the reviewer cannot see
  from the number that the scale was the problem.
- Treating a stress with no derating rule as compliant because nothing
  failed. An unjudged stress is an open coverage item; a rule has to exist
  before a verdict can.
- Widening the permitted fraction to pass an exact-equality case. An
  equality at the derated limit is a representation question handled by the
  tolerance inside the comparison; the declared rule stays as specified.

## Behavior contract (gate 3)

The rule validation, derated-limit resolution in both shapes and both bound
directions, worst-case stress widening, margin and utilisation reporting,
the uncovered and undeclared stress findings and the review disposition are
exercised by the gate 3 contract test:
scripts/test_q6012_derating_review_item.py against
scripts/q6012_derating_review_item_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6012_derating_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
