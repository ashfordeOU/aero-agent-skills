---
name: q7030-wire-stripping-and-prep
description: "Evaluate a stripped wire end before it goes on a wrapping post under ECSS-Q-ST-70-30. Use when a strip length is set on the tool, or a bared conductor is questioned at inspection. Derive the strip length the planned bare turns, insulated turns and tail allowance need, compare the measured strip against it with a symmetric tolerance, return any nick or scrape as a fraction of the conductor diameter, return the diameter the jaws took out, grade the insulation set-back and damage, count the re-strips the end has left, and close with accept, restrip-required or reject-wire-end. Trigger: ecss, q-st-70-30, wire-wrap-strip-length-requirement, wire-wrap-conductor-nick-fraction, wire-wrap-conductor-deformation, wire-wrap-insulation-setback, wire-wrap-restrip-allowance, wire-wrap-prepared-end-disposition."
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
  tags: [ecss, q-st-70-30-wire-wrapping, q-st-70-30, q7030-wire-stripping-and-prep, wire-wrap-strip-length-requirement, wire-wrap-conductor-nick-fraction, wire-wrap-conductor-deformation, wire-wrap-insulation-setback, wire-wrap-restrip-allowance, wire-wrap-prepared-end-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Stripping and End Preparation (space-systems/ecss/q7030-wire-stripping-and-prep)

Use when the task is the preparation clause of ECSS-Q-ST-70-30: how much
conductor a wrapped connection needs bared, and what condition the bared
conductor has to be in before it reaches the post. This leaf grades one prepared
wire end; the tool leaf grades the machine that stripped it.

## Domain quick reference

- Strip length is derived, not chosen. It is the bare turns times the conductor
  diameter, plus the insulated diameter for any insulated turns, plus a tail
  allowance, so a change of gauge or turn count moves it and a fixed number on a
  drawing goes quietly wrong.
- The two ways to miss are not symmetric in consequence. A short strip cannot
  produce the turn count at all, which is a connection that was never made; a
  long one leaves bare conductor standing above the finished wrap, which is a
  clearance and shorting question on a dense backplane.
- A nick is a fraction, not a depth. The same stripper setting that leaves a
  harmless mark on a thick conductor can take a tenth of a fine one, so damage
  is always reported against the diameter it is in.
- Deformation is separate from nicking. Jaws that close too far leave the
  conductor undamaged in appearance and reduced in section, and it is that
  reduced section the wrap will ask to carry its tension through.
- The insulation matters at the strip point. A set-back beyond its allowance
  leaves the wrap starting on unsupported conductor, and insulation that was
  cut, melted or dragged reports a tool or a technique problem that the next
  hundred ends will share.
- A wire end has a finite number of re-strips. Each one spends slack, so the
  useful question is not only whether this end is acceptable but whether there
  is enough wire left to make it acceptable.

## Workflow

1. Validate the gauge and turn count, and derive the strip length the connection
   needs including insulated turns and the tail allowance.
2. Compare the measured strip length with a symmetric tolerance, separating the
   short case from the long case because they carry different severities. A
   strip landing exactly on a tolerance edge counts as inside by a named
   tolerance rather than by widening the band.
3. Express any nick, scrape or gouge as a fraction of the conductor diameter and
   split the shallow case from the one past the limit.
4. Express the measured conductor diameter as the fraction the jaws removed,
   floored at zero so an oversize reading is not a negative reduction.
5. Grade the insulation set-back against its allowance and record insulation
   that was cut, melted or dragged.
6. Take the re-strips the end has left, rank findings by severity, and close
   with accept, restrip-required, or reject-wire-end.

## Pitfalls

- Fixing a strip length on the drawing. It follows the gauge and the turn count,
  so a substitution to a finer wire silently over-strips every end made after
  it.
- Treating over-strip and under-strip as the same defect. One is a wrap that
  cannot reach its turns, the other is exposed conductor next to a neighbouring
  post, and reporting them together loses both actions.
- Reading nick depth in millimetres. A hundredth of a millimetre is nothing on a
  thick conductor and a serious reduction on a fine one; only the fraction of
  the diameter compares across gauges.
- Passing an undamaged-looking conductor that the jaws flattened. There is no
  mark to see, and the section the wrap has to hold tension through is gone.
- Re-stripping an end indefinitely. Each re-strip spends slack, and an end with
  none left cannot be made acceptable by trying again.
- Ignoring insulation damage because the conductor is clean. A cut or dragged
  insulation reports a tool or technique fault, and the next hundred ends will
  carry it too.

## Behavior contract (gate 3)

The derived strip length with insulated turns and tail allowance, the symmetric
strip-length comparison, the nick fraction and its limit, the diameter reduction
fraction, the insulation set-back and damage findings, the re-strip allowance
and the prepared-end disposition are exercised by the gate 3 contract test:
scripts/test_q7030_wire_stripping_and_prep.py against
scripts/q7030_wire_stripping_and_prep_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7030_wire_stripping_and_prep.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
