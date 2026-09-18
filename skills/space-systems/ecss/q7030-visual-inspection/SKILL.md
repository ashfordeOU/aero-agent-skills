---
name: q7030-visual-inspection
description: "Assess the visual condition of finished wire wraps under ECSS-Q-ST-70-30C quality rules. Use when wraps are graded at the bench or on a sampling review: count the bare turns actually laid against the gauge minimum, raise an overlapping turn and a turn lifted off the post, measure each spiral gap against the conductor diameter and cap the gaps summed over the wrap, bound the overhanging end tail, group every finding as major or minor by whether it takes joint area away, and return per-wrap verdicts with the rework list the lot owes. Trigger: ecss, q-st-70-30c, wire-wrap-visual-acceptance, wire-wrap-overlapping-turn, wire-wrap-lifted-turn, wire-wrap-turn-spacing, wire-wrap-end-tail, wire-wrap-finding-severity."
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
  tags: [ecss, q-st-70-30c, q7030-visual-inspection, wire-wrap-visual-acceptance, wire-wrap-overlapping-turn, wire-wrap-lifted-turn, wire-wrap-turn-spacing, wire-wrap-end-tail, wire-wrap-finding-severity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Visual Inspection (space-systems/ecss/q7030-visual-inspection)

Use when the task is the visual acceptance of finished wraps under
ECSS-Q-ST-70-30C -- turning what the inspector sees on the post into a
verdict, and turning the verdicts into the rework list the lot owes.

## Domain quick reference

- The visual inspection is not a tidiness check. Every accept-reject
  rule on the list exists because the defect it names either removes
  contact area from the joint or puts the conductor somewhere it can
  short, and the ones that do neither are graded as minor and counted
  rather than scrapped.
- An overlapping turn is a turn laid on top of the turn below it
  instead of beside it. It contributes no corner contact of its own and
  it lifts the turns after it off the post, so one overlap costs more
  than one turn of joint.
- A lifted turn stands off the post rather than seating on it. The
  count still reads correctly from a distance, which is why the lifted
  turn is inspected for separately and not inferred from the number of
  turns present.
- Spacing is graded against the conductor, not against a fixed
  millimetre. A gap that is a hairline on a coarse wire is a full
  conductor width on a fine one, so the single-gap limit and the
  cumulative limit are both fractions of the conductor diameter. A wrap
  can hold every individual gap and still fail on their sum.
- The end tail is the cut end overhanging the last turn. It takes no
  joint area away, so it is a minor finding, but an overhang longer
  than the conductor is free to move and reach the neighbouring post.
- Minor findings accumulate. One is tolerated on a wrap; two together
  describe a wrap that was not made to the process even though no
  single rule was broken badly, and it goes to rework.

## Workflow

1. Record the observation as it was seen: bare and insulated turns,
   overlapping turns, lifted turns, each gap width, the end tail, and
   whether the conductor or the post was damaged in the making.
2. Read the limits from the gauge -- minimum bare turns, single gap,
   cumulative gap, end tail -- rather than from a fixed sheet, because
   every one of them scales with the conductor.
3. Raise the finding codes the observation earns, in a stable order so
   two inspectors reporting the same wrap produce the same list.
4. Group the codes by severity: major where joint area is lost or a
   short is possible, minor where the wrap is degraded but the joint is
   intact.
5. Decide the wrap: accepted when there is no major finding and the
   minor findings stay inside their cap, otherwise to rework.
6. Aggregate the lot: list the accepted wraps, list the rework wraps,
   and total the findings at each severity so the process problem
   behind them is visible rather than averaged away.

## Pitfalls

- Grading spacing in absolute millimetres. The same 0.2 mm gap is
  inside the limit on the coarse end of the range and well past it on
  the fine end, so a fixed number silently passes fine-gauge wraps that
  should have been rejected.
- Reading the turn count as proof of contact. Turns that overlapped or
  lifted are still turns, and they still count; only the separate
  overlap and lift observations show that the joint is smaller than the
  count suggests.
- Passing a wrap because no single gap was out of limit. The gaps add
  up over the wrap, and a spiral made of legal gaps is still an open
  spiral that has moved turns off the post corners.
- Treating an over-long end tail as cosmetic because it is minor. Minor
  means the joint is intact, not that the wrap may ship with several of
  them; the cap on minor findings per wrap is what keeps a drifting
  process visible.
- Reporting a lot as a percentage. A single major finding is a rejected
  wrap, and a pass rate averages it against wraps that were never at
  risk; the lot verdict is the presence of a rework list, not its size.

## Behavior contract (gate 3)

The gauge-scaled limits, the finding codes, the severity grouping, the
per-wrap accept-or-rework verdict and the lot aggregation are exercised
by the gate 3 contract test:
scripts/test_q7030_visual_inspection.py against
scripts/q7030_visual_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7030_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
