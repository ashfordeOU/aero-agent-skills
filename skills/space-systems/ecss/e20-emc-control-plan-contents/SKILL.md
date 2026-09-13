---
name: e20-emc-control-plan-contents
description: "Use when verify that an electromagnetic-compatibility control plan carries the content ECSS-E-ST-20C Annex A calls for: check every content block is declared and non-empty, confirm the organisation block names the compatibility owner, its reporting path and its control-board interface, categorize each register entry by interference mechanism and control measure and reject a measure that does not act on the coupling path it claims to control, power-sum the emitter levels behind each victim and compare the resulting margin against the required one, and hold every milestone far enough ahead of the review it anchors to. Trigger: ecss, e-st-20-electrical-scope, e20-emc-control-plan-contents, emc-control-plan-content-blocks, control-measure-register, electromagnetic-budget-margin, grounding-and-bonding-scheme, interference-coupling-path, control-plan-milestone-lead."
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
  tags: [ecss, e-st-20-electrical-scope, e20-emc-control-plan-contents, emc-control-plan-content-blocks, control-measure-register, electromagnetic-budget-margin, grounding-and-bonding-scheme, control-plan-milestone-lead]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — EMC Control Plan Contents (space-systems/ecss/e20-emc-control-plan-contents)

Use when the task is the content of the electromagnetic-compatibility control
plan described by the ECSS-E-ST-20C Annex A data-requirement -- who owns
compatibility control, which design measures are being applied, what
electromagnetic budgets those measures have to buy, and when each piece of
that work lands against the programme reviews. The check is on the plan
document itself, not on the delivery date of the plan and not on the
verification activities it points to.

## Domain quick reference

- Six content blocks make up the plan: organisation-and-responsibility,
  control-measure-register, electromagnetic-budget-table,
  verification-approach-reference, schedule-and-milestone-list and
  deviation-handling-route. A block that is present as a heading but carries
  no content counts as undeclared -- an empty section is not a content
  block, and reading it as one lets an unplanned area pass the review.
- The organisation block has to name three distinct things: the engineer or
  authority that owns compatibility control, the reporting path by which
  findings reach project management, and the interface to the board that
  arbitrates changes. A delegate named without a scope is a finding, because
  an unscoped delegation cannot be checked against the work breakdown.
- The control-measure register pairs an interference mechanism with the
  measure that controls it. Mechanisms split into conducted-emission,
  conducted-susceptibility, radiated-emission, radiated-susceptibility,
  electrostatic-discharge and lightning-induced-transient; measures into a
  grounding-scheme, a bonding-scheme, a shielding-scheme,
  cable-category-segregation, a filtering-scheme and a
  galvanic-isolation-scheme. A measure only buys margin on the coupling
  paths it physically acts on: filtering and galvanic isolation act on the
  conducted paths, shielding, bonding and cable-category-segregation act on
  the radiated paths, bonding and grounding carry the discharge path.
- Levels in the budget table are in dB, so several emitters seen by one
  victim combine by a power sum (10 log10 of the summed linear powers), not
  by arithmetic addition. Two equal emitters sit about 3 dB above one of
  them, never twice the level. The margin a victim holds is its
  susceptibility level minus that aggregate, compared against the margin the
  programme requires.
- Schedule entries anchor to a named review -- preliminary-design-review,
  critical-design-review, qualification-review, acceptance-review or
  flight-readiness-review -- and carry the lead in days by which the
  milestone precedes it. A negative lead means the work lands after the
  review it is meant to feed.

## Workflow

1. Resolve every declared block name to its canonical token and reject a
   block the data-requirement does not recognise; then list the required
   blocks the plan leaves undeclared or empty.
2. Read the organisation block and record a finding for each of the three
   mandatory roles it does not name, and for every delegate declared
   without a scope.
3. Walk the control-measure register. Resolve the mechanism and the measure
   of each entry, record an unnamed owner, and reject any pairing whose
   measure does not act on that mechanism's coupling path -- a rejected
   pairing does not count as coverage.
4. After the register walk, list every mechanism in scope that no surviving
   entry controls. Narrow the scope list explicitly if the programme has
   argued a mechanism away; never let an absent entry imply an absent
   mechanism.
5. For each budget row, power-sum the emitter levels, subtract the aggregate
   from the victim's susceptibility level, and compare the margin against
   the required one. Absorb float representation error at an exactly met
   requirement rather than lowering the required margin.
6. Report the worst margin and its victim so the table has a single number
   the review can carry, alongside the full breach list.
7. Check each milestone anchors to a known review and leads it by at least
   the minimum lead, and that the reviews the plan must serve all carry at
   least one milestone.
8. The plan is acceptable only when no block, role, mechanism, budget row
   or milestone finding remains open.

## Pitfalls

- Adding emitter levels in dB. Levels are logarithmic; two 40 dB emitters
  aggregate to about 43 dB, and summing them to 80 dB turns a compliant
  budget into a fictional breach that costs real shielding mass.
- Counting an empty heading as a declared block. The plan then reads as
  complete while an entire control area -- most often the
  deviation-handling-route -- has no owner at all.
- Accepting a register entry that pairs a mechanism with a measure that
  does not act on it, such as a filtering-scheme offered against a radiated
  path. The entry looks like coverage in a table count but buys nothing,
  and it hides the mechanism that is genuinely uncontrolled.
- Treating the absence of a register entry as evidence that the mechanism
  does not apply. Scope is declared, not inferred; a mechanism argued away
  belongs in the scope list with its argument, not silently missing.
- Confusing the control plan with the verification plan. Annex A content is
  the control side -- organisation, measures, budgets, schedule -- and it
  points at the verification approach rather than restating its activities.
- Letting a milestone carry a negative lead because the anchor slipped. A
  milestone that lands after the review it feeds leaves that review with no
  compatibility evidence, which is a schedule finding, not a rounding
  detail.

## Behavior contract (gate 3)

The block-presence rule, the organisation-role check, the
mechanism-to-measure effectiveness rule, the dB power-sum aggregation, the
budget-margin comparison and the milestone-lead check are exercised by the
gate 3 contract test: scripts/test_e20_emc_control_plan_contents.py against
scripts/e20_emc_control_plan_contents_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e20_emc_control_plan_contents.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
