---
name: q60-class-1-part-material-restrictions
description: "Use when a Class 1 build has to show a chosen part's case and finish are allowed. Evaluate a candidate Class 1 part's packaging and material content against the ECSS-Q-ST-60C clause 4.2.2.2 restrictions: decide whether the case is hermetic, and for a non-hermetic one grade the agreed justification, the moisture sensitivity level and the demonstrated damp life against the humid hours the mission asks for; grade every surface finish against the near-pure-tin whisker threshold; grade each restricted metal against the trace it is allowed at; then list the re-work and deviations the part needs before purchase. Trigger: ecss, q-st-60c-eee-selection-scope, class-1-non-hermetic-packaging-limit, class-1-pure-tin-whisker-restriction, class-1-restricted-material-check, moisture-sensitivity-level-ceiling, class-1-finish-rework-mitigation."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q60-class-1-part-material-restrictions, class-1-non-hermetic-packaging-limit, class-1-pure-tin-whisker-restriction, class-1-restricted-material-check, moisture-sensitivity-level-ceiling, class-1-finish-rework-mitigation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Part and Material Restrictions (space-systems/ecss/q60-class-1-part-material-restrictions)

Use when the task is the limit set of ECSS-Q-ST-60C clause 4.2.2.2 --
deciding whether a candidate Class 1 part's case style and material
content are allowed at all, and what re-work the part needs before it
can be bought.

## Domain quick reference

- Two different kinds of limit sit on the choice. One is about the
  case: how long the die stays away from moisture. The other is about
  what the part is made of: what leaves the part and attacks what is
  around it.
- A hermetic case keeps the die dry for the whole mission and needs no
  further argument. A non-hermetic case does not, so it is allowed only
  on a justification the customer agreed, and only when two numbers
  back that justification: a moisture sensitivity level inside the
  ceiling the build works to, and a demonstrated damp life covering the
  humid hours the mission asks for with margin on top. A justification
  with no numbers behind it is an opinion.
- Some metals are kept out of a flight part outright, at anything above
  a trace. Cadmium and zinc sublime in vacuum and re-deposit on optics
  and contacts; mercury embrittles aluminium; unalloyed magnesium
  corrodes. A trace is tolerated because no analysis reports a true
  zero; anything above it is a finding.
- Tin is not on that list and must not be treated as if it were. Tin is
  wanted -- it is the solderability of the finish. What is restricted
  is tin that is nearly pure, because a near-pure tin finish grows
  whiskers, and a whisker is a short circuit that appears years after
  the board was accepted. So tin is graded against a mass-fraction
  threshold and a finish over it can be brought back by re-working it.
- A whisker is not an inspection escape. It is not there at acceptance
  and no incoming test finds it, which is why the restriction sits at
  selection rather than at goods-in.
- The useful output is not permitted or not. It is the whisker margin
  on each finish, the packaging number that fails when one does, and
  the list of re-work steps and agreed deviations the part carries into
  its procurement file.

## Workflow

1. Name the candidate part and its case style. A case style outside the
   known set is rejected rather than guessed at.
2. For a hermetic case, close the packaging question there. For a
   non-hermetic one, require the agreed justification, the moisture
   sensitivity level and both damp-life figures, and reject the case
   when any of them is absent -- a missing number is not a pass.
3. Grade the damp life as a ratio of demonstrated life to the humid
   hours asked for with the margin applied. A ratio sitting exactly on
   unity passes.
4. Grade each surface finish against the near-pure-tin threshold and
   report the whisker margin. A finish on or above the threshold is
   near-pure; an accepted re-work turns it into a procurement condition
   rather than a stop.
5. Grade each restricted metal against the trace. Above the trace it is
   a stop unless a named deviation has been agreed, which is carried
   into the file rather than silently allowed.
6. Close with the verdict, the tightest finish, and the mitigations and
   deviations the part needs before purchase.

## Pitfalls

- Treating tin as a banned metal. Banning tin bans solderability; the
  restriction is on a finish that is nearly pure, and an alloyed finish
  well under the threshold is exactly what the rule wants.
- Passing a near-pure tin finish because incoming inspection is clean.
  The whisker is not there yet. It grows on the shelf and in orbit, so
  this is a selection-time decision and no goods-in test replaces it.
- Accepting a non-hermetic case on an agreed justification alone. The
  agreement is the permission to argue, not the argument; without the
  moisture level and the damp life the case is unassessed.
- Reading a missing moisture level as a low one. An absent figure is
  rejected, because the commonest non-hermetic escape is a part nobody
  ever rated.
- Grading damp life against the bare mission hours. The margin is part
  of the rule, so a demonstrated life equal to the humid hours is half
  of what is needed, not a pass.
- Comparing a mass fraction or a life ratio with its threshold by bare
  arithmetic. Both are quotients while the thresholds are decimal
  literals, so a value built to sit exactly on a threshold can land a
  few units in the last place off it; the comparison absorbs that while
  the threshold stays untouched.

## Behavior contract (gate 3)

The case-style lookup, non-hermetic justification and moisture checks,
damp-life ratio with margin, near-pure-tin threshold and whisker
margin, accepted finish re-work, restricted-metal trace comparison,
named deviations, mitigation list and overall verdict are exercised by
the gate 3 contract test:
scripts/test_q60_class_1_part_material_restrictions.py against
scripts/q60_class_1_part_material_restrictions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_part_material_restrictions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
