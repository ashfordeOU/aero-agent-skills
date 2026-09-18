---
name: q7030-wire-and-terminal-specification
description: "Verify that a conductor and a terminal post can carry a solderless wrapped connection under ECSS-Q-ST-70-30. Use when a wire gauge, a post section or a backplane terminal is being specified or substituted. Derive the bare conductor diameter from the gauge and the bare turns that gauge owes, take the post diagonal as a multiple of that diameter, budget the post length the planned turns, insulated turns and wrap levels consume plus end clearance, refuse an unalloyed tin finish on either part, name any finish outside the qualified set, and close with compatible, compatible-with-actions or not-compatible. Trigger: ecss, q-st-70-30, wire-wrap-conductor-gauge-diameter, wire-wrap-required-turn-count, wire-wrap-post-diagonal-ratio, wire-wrap-post-length-budget, wire-wrap-prohibited-tin-finish, wire-wrap-level-stacking."
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
  tags: [ecss, q-st-70-30-wire-wrapping, q-st-70-30, q7030-wire-and-terminal-specification, wire-wrap-conductor-gauge-diameter, wire-wrap-required-turn-count, wire-wrap-post-diagonal-ratio, wire-wrap-post-length-budget, wire-wrap-prohibited-tin-finish, wire-wrap-level-stacking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Wire and Terminal Specification (space-systems/ecss/q7030-wire-and-terminal-specification)

Use when the task is the materials clause of ECSS-Q-ST-70-30: which conductor
gauge and finish, and which terminal post section, length and finish, a wrapped
connection may be built from. This leaf grades one wire against one post; the
applicability leaf decides whether the connection belongs here at all.

## Domain quick reference

- Gauge is geometry, not a label. AWG is a geometric series, so a diameter can
  be derived from the gauge number rather than looked up, and every length in
  the wrap budget is a multiple of that one diameter.
- The turn count owed falls as the wire gets thicker. A thick conductor stores
  the contact force the joint needs in fewer turns; a fine one reaches the same
  stored force only by taking more of them, which is why the count comes from
  the gauge and is not a workmanship preference.
- The post has to be large enough relative to the wire. Expressed as the post
  diagonal in conductor diameters, a section too close to the wire lets the wire
  ride across the corner instead of deforming over it, and the contact area
  never forms.
- Post length is a budget, and levels are what spend it. Each level takes its
  own turns times the conductor diameter, an insulated turn takes the insulated
  diameter rather than the bare one, and the end of the post has to stay clear
  so the top wrap is not formed against it.
- Finish is a long-term question the joint cannot answer for itself. Unalloyed
  tin on the wire or the post grows whiskers across a backplane whose posts sit
  at fixed spacing, and the failure appears years after the wrap passed every
  inspection it was ever given.
- A finish outside the qualified set is not automatically wrong, but it is
  unassessed, which is a different finding from a prohibited one and carries a
  different action.

## Workflow

1. Validate the gauge against the wrappable span and derive the bare conductor
   diameter and the bare turn count that gauge owes.
2. Take the post diagonal from its width and thickness, and express it as a
   multiple of the conductor diameter against the owed ratio.
3. Budget the post length: turns times conductor diameter per level, plus the
   insulated diameter for any insulated turns, times the number of levels, plus
   end clearance. Compare against the post length actually available, counting a
   post landing exactly on the budget as sufficient by a named tolerance.
4. Grade both finishes: prohibited unalloyed tin is critical, a finish outside
   the qualified set is a major unassessed finding.
5. Rank findings by severity and close with one disposition: compatible,
   compatible-with-actions, or not-compatible.

## Pitfalls

- Carrying a turn count across a gauge change. A substitution from one gauge to
  a finer one changes the turns owed and the post length budget together, and a
  drawing that fixes the turn count hides both.
- Budgeting post length on turns alone. Levels multiply the budget, and a second
  or third level on a post sized for one is the common way a wrap ends up formed
  over the end of the post.
- Charging an insulated turn at the bare diameter. The insulation is what makes
  the modified wrap work and it is also what makes it longer, by a diameter that
  is not the conductor's.
- Sizing the post from the wire alone. The ratio that matters is the diagonal in
  conductor diameters, so a fine post can be correct for a fine wire and quite
  wrong for the thicker wire someone substitutes into the same backplane later.
- Treating an unalloyed tin finish as a cosmetic or cost choice. The whisker
  appears long after acceptance, so no inspection at build time can catch it and
  the control has to sit at specification.
- Collapsing prohibited and unqualified finishes into one verdict. One is
  refused outright; the other needs assessment, and reporting them the same way
  loses the action each of them owes.

## Behavior contract (gate 3)

The gauge-to-diameter derivation, the owed turn count, the post diagonal ratio,
the per-level and total post length budget with insulated turns and end
clearance, the prohibited and unqualified finish findings and the compatibility
disposition are exercised by the gate 3 contract test:
scripts/test_q7030_wire_and_terminal_specification.py against
scripts/q7030_wire_and_terminal_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7030_wire_and_terminal_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
