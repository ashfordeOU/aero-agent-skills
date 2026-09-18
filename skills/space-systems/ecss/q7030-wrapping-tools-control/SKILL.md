---
name: q7030-wrapping-tools-control
description: "Audit a wrapping tool set before it is released to production under ECSS-Q-ST-70-30. Use when a wrapping gun, bit or sleeve is issued, recalled or questioned after a loose wrap. Test that the fitted bit is certified and covers both the conductor gauge and the post diagonal in hand, return the calibration standing against the interval and its recall grace, return bit life consumed as a fraction of its wrap limit, grade the set-up sample on turns, overlap and end play, ratio the delivered tension against nominal, and close with release-for-use, release-with-actions or withdraw-from-service. Trigger: ecss, q-st-70-30, wire-wrap-bit-coverage, wire-wrap-tool-calibration-standing, wire-wrap-bit-life-consumed, wire-wrap-setup-sample-grading, wire-wrap-delivered-tension-ratio, wire-wrap-tool-disposition."
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
  tags: [ecss, q-st-70-30-wire-wrapping, q-st-70-30, q7030-wrapping-tools-control, wire-wrap-bit-coverage, wire-wrap-tool-calibration-standing, wire-wrap-bit-life-consumed, wire-wrap-setup-sample-grading, wire-wrap-delivered-tension-ratio, wire-wrap-tool-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Wrapping Tool Control (space-systems/ecss/q7030-wrapping-tools-control)

Use when the task is the tooling clause of ECSS-Q-ST-70-30: which wrapping bits
and sleeves may be fitted, how their calibration and wear are tracked, and what
the set-up sample has to show before the tool is released to production. This
leaf grades one tool set at one moment, not the wraps it has already made.

## Domain quick reference

- The bit and sleeve are the specification made physical. The bit bore sets the
  wire the tool can drive and the sleeve bore sets the post it can index down;
  a bit outside its coverage still turns the wire round the post and still looks
  like a wrap, and it is the tension that quietly goes missing.
- Calibration has three states, not two. A tool inside its interval is usable, a
  tool inside its recall grace is usable while it owes a calibration, and a tool
  past both is not evidence of anything it made since the interval lapsed. A
  two-state model loses the middle case and either grounds a usable tool or runs
  an expired one.
- Wear is counted in wraps, not in days. A bit used all week on one backplane is
  further through its life than one used occasionally for a year, and a warning
  band short of the limit is what gives stores time to issue a replacement.
- The set-up sample is the only direct evidence the tool works today. Turn
  count, overlapping turns and end play are what it can show, and overlap in
  particular is a sleeve indexing fault rather than an operator error.
- Delivered tension is the property the whole connection depends on and the one
  nothing downstream can see. It is expressed as a fraction of nominal so a tool
  slightly soft and a tool half strength are separable, and it is bounded on
  both sides because an over-tensioned wrap thins the wire at the corner.

## Workflow

1. Validate the tool record and test the fitted bit: certification standing,
   conductor gauge coverage, and post diagonal coverage, all three separately.
2. Return the calibration standing from days since calibration, the interval and
   the recall grace, as in-calibration, due, or out-of-calibration, with a tool
   landing exactly on a boundary counted as inside by a named tolerance.
3. Return the bit life consumed as a fraction of its wrap limit and split the
   warning band from the withdrawal limit.
4. Grade the set-up sample: turn count against what the gauge owes, overlapping
   turns, and end play against its allowance.
5. Ratio the measured tension against nominal and test it against the band on
   both sides.
6. Rank findings by severity and close with one disposition: release-for-use,
   release-with-actions, or withdraw-from-service.

## Pitfalls

- Treating the bit as a size and the sleeve as a formality. The sleeve is what
  indexes each turn down the post, so a mismatched sleeve produces exactly the
  overlapping turns that the set-up sample exists to catch.
- Assuming a bit that fits the wire fits the post. Gauge coverage and post
  diagonal coverage are separate spans and a tool can pass one and fail the
  other, which is common when one backplane carries two post sizes.
- Running a two-state calibration model. Losing the recall grace means a tool
  one day past its interval is either grounded or, more often in practice,
  quietly kept in service until someone notices.
- Counting bit life in calendar time. Wear follows use, and a bit that made ten
  thousand wraps this month is nowhere near a bit that made two hundred.
- Reading a soft tool as a pass because the wrap looked right. Tension is not
  visible in a finished wrap, which is why it is measured on the tool rather
  than inferred from the product.
- Bounding tension on one side only. An over-tensioned wrap thins the wire where
  it crosses the corner, so the high side is a limit as much as the low side is.

## Behavior contract (gate 3)

The bit certification and coverage tests, the three-state calibration standing,
the bit life fraction and its warning band, the set-up sample turn count,
overlap and end play findings, the delivered tension ratio and band, and the
tool disposition are exercised by the gate 3 contract test:
scripts/test_q7030_wrapping_tools_control.py against
scripts/q7030_wrapping_tools_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7030_wrapping_tools_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
