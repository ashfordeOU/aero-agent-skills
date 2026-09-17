---
name: q60-class-3-part-material-restrictions
description: "Evaluate a candidate Class 3 part's packaging and material content against the ECSS-Q-ST-60C clause 6.2.2.2 limits: decide whether the case is hermetic, and for a non-hermetic one spend the moisture floor-life budget against the exposure already taken, accelerated by the humidity it sat in, then require a recorded bake once that budget is gone; grade every surface finish against the near-pure-tin whisker threshold; grade each organic against the mass-loss and condensable limits separately; grade each restricted metal against the trace it is allowed at; and list the bakes, re-works and deviations the part carries into purchase. Use when a Class 3 build has to justify a plastic-encapsulated part. Trigger: ecss, q-st-60c, q60-c3-non-hermetic-packaging-limit, q60-c3-moisture-floor-life-budget, q60-c3-pure-tin-whisker-restriction, q60-c3-outgassing-limit-check, q60-c3-restricted-metal-trace."
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
  tags: [ecss, q-st-60c, q60-class-3-part-material-restrictions, q60-c3-non-hermetic-packaging-limit, q60-c3-moisture-floor-life-budget, q60-c3-pure-tin-whisker-restriction, q60-c3-outgassing-limit-check, q60-c3-restricted-metal-trace, q60-c3-dry-pack-and-bake-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Part and Material Restrictions (space-systems/ecss/q60-class-3-part-material-restrictions)

Use when the task is the limit set of ECSS-Q-ST-60C clause 6.2.2.2 --
deciding whether a candidate Class 3 part's case style and material
content can be taken to a flight build, and what handling, re-work and
paperwork the part carries with it.

## Domain quick reference

- Class 3 is the class where non-hermetic parts are actually chosen, so
  this clause is not a ban on plastic. It is the set of conditions a
  plastic-encapsulated part has to meet, plus the material limits that
  hold whatever the case is made of.
- A hermetic case keeps the die away from moisture on its own and
  closes the packaging question. A non-hermetic case does not: the
  mould compound takes up water on the shelf and in the workshop, and
  that water flashes to steam at reflow and lifts the die pad.
- What controls the non-hermetic case is a budget, not a verdict. Each
  moisture sensitivity level carries a floor life -- the hours the part
  may sit outside a dry pack before it has to be baked again -- and the
  exposure already taken is measured against it. Damp air spends the
  budget faster than the rated condition, so exposure is accelerated by
  the humidity the part was actually held in.
- A part whose budget is spent is not rejected. It is baked, and the
  bake has to be on record; a spent budget with no bake behind it is
  the finding, not the exposure itself. A part that arrived outside a
  dry pack has an exposure nobody measured, which is worse than a large
  one somebody did.
- Tin is not a banned metal. Tin is the solderability of the finish.
  What is restricted is tin that is nearly pure, because a near-pure
  finish grows whiskers years after acceptance and no incoming test
  finds them, so tin is graded against a mass fraction and a finish
  over the threshold can be brought back by re-working it.
- Organics are the third limit and a hermetic case does not escape it.
  An encapsulant, conformal coat or die attach that loses too much of
  itself in vacuum, or condenses what it loses onto a cold surface,
  contaminates optics and detectors far from the part it came from.
  Mass loss and condensable fraction are graded separately because a
  material can pass one and fail the other.
- The useful output is the floor-life budget left, the whisker margin
  on each finish, the tighter of the two outgassing margins on each
  organic, and the list of bakes, re-works and agreed deviations the
  part carries into its procurement file.

## Workflow

1. Name the candidate part and its case style. A case style outside the
   known set is rejected rather than guessed at.
2. For a hermetic case, close the packaging question there. For a
   non-hermetic one, take the moisture sensitivity level, the exposure
   hours and the storage humidity, and spend the floor-life budget.
3. Require the dry-pack record and, once the budget is spent, the bake
   record. A missing bake on a spent budget stops the part.
4. Grade each surface finish against the near-pure-tin threshold and
   report the whisker margin; an accepted re-work turns a near-pure
   finish into a procurement condition rather than a stop.
5. Grade each organic against both outgassing limits and name the one
   that binds.
6. Grade each restricted metal against the trace. Above the trace it is
   a stop unless a named deviation has been agreed.
7. Close with the verdict, the tightest finish, and the bakes, re-works
   and deviations the part needs before purchase.

## Pitfalls

- Reading the clause as a plastic ban and reselecting a ceramic part
  the project cannot afford. Class 3 exists so that a plastic part can
  be used under stated conditions; the conditions are the work.
- Treating floor life as a shelf life. It is the time outside the dry
  pack, it resets on a bake, and it is spent faster in damp air than
  the rated figure suggests.
- Accepting a part delivered outside a dry pack because it looks fresh.
  The exposure it arrived with is unknown, not zero, and an unknown
  exposure cannot be subtracted from a budget.
- Banning tin outright. That bans solderability; the restriction is on
  a nearly pure finish, and an alloyed finish well under the threshold
  is exactly what the rule wants.
- Grading an organic on mass loss alone. A material can lose little and
  still condense most of what it loses, which is the failure that
  reaches the optics.
- Comparing a consumption ratio or a mass fraction with its limit by
  bare arithmetic. Both are quotients while the limits are decimal
  literals, so a value built to sit exactly on a limit can land a few
  units in the last place off it; the comparison absorbs that while the
  limit stays untouched.

## Behavior contract (gate 3)

The case-style lookup, floor-life table and humidity acceleration, the
budget spend with dry-pack and bake evidence, the near-pure-tin
threshold and whisker margin, the accepted finish re-works, the two
outgassing limits and the binding one, the restricted-metal trace
comparison with named deviations, the mitigation list and the overall
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_3_part_material_restrictions.py against
scripts/q60_class_3_part_material_restrictions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_3_part_material_restrictions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
