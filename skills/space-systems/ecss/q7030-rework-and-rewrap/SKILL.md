---
name: q7030-rework-and-rewrap
description: "Evaluate whether a wrapping post may be rewrapped under ECSS-Q-ST-70-30C rework rules. Use when a wrap has been removed and the connection has to be remade: count the removals the post has already taken against its allowance, require an unwrapping tool rather than a wrap dragged off with pliers, refuse a post whose corners the removal rounded or deformed, insist the used length of wire is cut away instead of wrapped again, size the wire the new wrap needs from the post perimeter and the turn count, and return the disposition with its reasons. Trigger: ecss, q-st-70-30c, wire-wrap-rewrap-allowance, wire-wrap-removal-tool, wrapping-post-corner-damage, wire-wrap-used-length-cut-off, wire-wrap-remaining-wire-length, wire-wrap-rework-disposition."
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
  tags: [ecss, q-st-70-30c, q7030-rework-and-rewrap, wire-wrap-rewrap-allowance, wire-wrap-removal-tool, wrapping-post-corner-damage, wire-wrap-used-length-cut-off, wire-wrap-remaining-wire-length, wire-wrap-rework-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Rework and Rewrap (space-systems/ecss/q7030-rework-and-rewrap)

Use when the task is the rework of a wrapped connection under
ECSS-Q-ST-70-30C -- deciding whether the post in front of you may take
another wrap at all, and if it may, what has to be replaced first.

## Domain quick reference

- A rewrap is not free. Taking a wrap off drags work-hardened conductor
  back across the corners that formed the joint, so both the post and
  the wire come out of the operation worse than they went in. The
  allowance exists because the damage accumulates, not because three
  is a round number.
- The allowance belongs to the post. A post that has been unwrapped
  twice carries that history whatever connection is made on it next, so
  the count is held against the terminal rather than against the wire
  or the work order.
- The removal method decides how much damage was done. An unwrapping
  tool unwinds the turns along the path they were laid; a wrap dragged
  off with pliers rolls the corners over, and rounded corners cannot
  make a gas-tight joint however well the next wrap is executed.
- The used length of wire is scrap. Those turns are work-hardened and
  carry the impressions of the corners, so they are cut away and the
  new wrap is made on wire that has never been wrapped -- which means
  the real question is whether enough wire is left.
- How much is left is arithmetic, not eyeball. A turn consumes the post
  perimeter plus an allowance for climbing the post, and the wrap owes
  a strip length beyond the last turn plus whatever service loop the
  routing needs. Compare that against the length remaining after the
  cut before committing to the rework.
- The two blocking answers differ in kind. A post finding ends the
  terminal's life and the disposition is replacement; a wire or method
  finding leaves the post usable and the disposition is a new length of
  wire.

## Workflow

1. Declare the post: the removals it has already taken, the levels
   currently on it, the state of its corners after the removal, and how
   the last wrap came off.
2. Spend the allowance: compute the removals remaining, and raise a
   finding when the post is out of allowance or already carrying its
   full complement of levels.
3. Grade the post itself. Deformed or rounded corners are a post
   finding regardless of what the allowance says, because the joint
   geometry is gone.
4. Grade the removal method, separating a wrap that was unwound from
   one that was pulled off and from one with no method on record at
   all.
5. Confirm the used length was cut away, then compute the wire the new
   wrap needs from the gauge, the turn count, the post cross-section
   and the service loop, and compare it against what remains.
6. Check the planned turn count against the gauge schedule, so a
   rework is not quietly made shorter than the original.
7. Return the disposition -- proceed, replace the wire, replace the
   terminal -- with the findings that produced it, and aggregate a set
   of posts into the three lists the rework order needs.

## Pitfalls

- Counting rewraps against the connection instead of the post. Two
  different wires unwrapped from the same terminal have spent two of
  that terminal's removals, and a count kept per connection resets to
  zero every time the design changes.
- Rewrapping over used wire because it looks undamaged. The impressions
  of the corners are exactly where the next wrap needs fresh metal, and
  work-hardened conductor cracks rather than deforming into the corner.
- Treating rounded corners as cosmetic. The gas-tight joint is made by
  the corner cutting into the conductor; once the corner is rolled over
  there is nothing to cut with, and no amount of turn count recovers
  it.
- Discovering the wire is short after the cut. The length needed is
  computable before anything is removed, and a rework that runs out of
  wire mid-operation turns a repairable connection into a harness
  change.
- Comparing available wire against the requirement by bare arithmetic.
  Both are sums of measured floats, so a length that is exactly
  sufficient can read a few units in the last place short; the
  comparison absorbs that representation error while the requirement
  itself stays untouched.

## Behavior contract (gate 3)

The removal allowance, the post-condition grading, the removal-method
finding, the used-length rule, the wire-length computation, the turn
schedule check and the three dispositions are exercised by the gate 3
contract test: scripts/test_q7030_rework_and_rewrap.py against
scripts/q7030_rework_and_rewrap_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7030_rework_and_rewrap.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
