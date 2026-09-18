---
name: q2030-comp-branching
description: "Assess a breakout in a metallic braid-shielded bundle against the complementary branching rules of ECSS-Q-ST-20-30C clause 7.7. Use when the task is computing the braid angle, filling factor and optical coverage each branch braid achieves from its construction, holding every branch to the coverage the trunk already carried rather than only to a floor, adding the trunk, junction and branch segments into one shield-continuity resistance and grading it, refusing a takeoff whose junction is not bonded, and limiting the unshielded length a breakout leaves exposed. Trigger: ecss, q-st-20-30c, braid-shielded-bundle-branching, breakout-shielding-continuity, braid-optical-coverage, braid-filling-factor, shield-continuity-resistance-budget, unbonded-breakout-junction, unshielded-takeoff-length."
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
  tags: [ecss, q-st-20-electrical-harness-scope, q-st-20-30c, q2030-comp-branching, braid-shielded-bundle-branching, breakout-shielding-continuity, braid-optical-coverage, shield-continuity-resistance-budget, unshielded-takeoff-length]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary Branching of Braid-Shielded Bundles (space-systems/ecss/q2030-comp-branching)

Use when the task is the complementary branching layer of ECSS-Q-ST-20-30C
clause 7.7 -- the space-specific rules for taking a branch out of a bundle
that carries a metallic braid shield, and for keeping the shielding
continuous through the breakout instead of ending it there.

## Domain quick reference

- A braid is not a solid shield; it is a mesh whose effectiveness follows
  from its geometry. The pick density, the carrier count, the ends per
  carrier, the braid wire diameter and the diameter the braid rides on
  together set the braid angle, and the braid angle sets how much surface
  one direction of the weave fills. Optical coverage follows from that
  filling factor, and it is the number a coverage requirement is written
  against.
- The same braid behaves differently on different bundles. Laid over a
  smaller diameter the weave lies at a shallower angle and covers more, so
  a branch braid taken from the same spool as the trunk is usually better,
  not worse -- which is exactly why a downgrade is easy to miss when a
  thinner braid is substituted at the breakout.
- The coverage requirement at a breakout is therefore two-sided: the
  branch owes the project floor AND the coverage the trunk already had.
  A branch that meets the floor but falls below the trunk has silently
  downgraded the shield for everything downstream of the breakout.
- Continuity is a resistance budget, not a continuity beep. The path a
  branch presents is the trunk run plus the junction plus the branch run,
  and the junction is normally the dominant and the most variable term.
  Grading the segments separately and the total against the end-to-end
  limit is what makes a marginal junction visible.
- A junction that is not bonded at all is not a high-resistance finding,
  it is a different defect: the trunk shield stops at the breakout and the
  branch shield floats, which is worse than an unshielded branch because
  the floating braid becomes an antenna rather than a return.
- A shield that stops short of the takeoff leaves an aperture, and no
  coverage figure compensates for an aperture. The unshielded length is
  measured and limited in its own right.

## Workflow

1. Compute the trunk braid geometry from its construction: braid angle,
   filling factor and optical coverage.
2. Compute the same three quantities for every branch braid, refusing a
   construction whose filling factor exceeds unity rather than reporting a
   coverage the expression no longer describes.
3. Grade each branch coverage against the greater of the project floor and
   the trunk coverage, absorbing an exact equality with a tolerance.
4. Add the trunk, junction and branch segments into one shield-continuity
   resistance and grade the total against the end-to-end limit.
5. Refuse a branch whose junction carries no bond at all, separately from
   the resistance grading, so the two defects do not merge into one
   finding.
6. Grade the unshielded length the breakout leaves against its limit.
7. Where the project caps how many branches leave one point, grade the
   branch count too, then roll every finding into one breakout verdict
   carrying the worst branch coverage.

## Pitfalls

- Grading a braid by its stated coverage percentage. That figure belongs
  to the braid laid on the diameter it was specified for; re-laid over a
  different bundle it is a different number, so it is recomputed from the
  construction and the diameter actually used.
- Holding a branch only to the coverage floor. The floor is the project
  minimum, not the trunk's achieved value, so a branch between the two is
  a downgrade that passes a floor-only check.
- Reading continuity with a two-wire beep. The junction resistance that
  matters sits well below what lead resistance masks, so the budget needs
  segment values, not a continuity indication.
- Treating an unbonded junction as a large resistance. An unbonded braid
  is a floating conductor, which couples rather than returns; it belongs
  in its own finding so it is not closed by improving a contact.
- Ignoring the unshielded length because coverage passed. Coverage
  describes the braid that is there; the aperture is the length where
  there is none, and it dominates at the frequencies the shield exists for.
- Reporting only the best branch. A breakout is as shielded as its worst
  branch, so the verdict carries the worst coverage, not the average.
- Failing a continuity total that lands exactly on the limit. The equality
  is a representation question, settled with a tolerance inside the
  comparison and never by moving the limit.

## Behavior contract (gate 3)

The braid-angle and filling-factor computation, the optical-coverage
expression and its unity refusal, the two-sided coverage grading against
the trunk and the floor, the three-segment continuity budget, the unbonded
junction refusal, the unshielded-takeoff grading, the branch-count cap and
the rolled-up breakout verdict are exercised by the gate 3 contract test:
scripts/test_q2030_comp_branching.py against
scripts/q2030_comp_branching_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_branching.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
