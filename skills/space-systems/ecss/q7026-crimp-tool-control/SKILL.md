---
name: q7026-crimp-tool-control
description: "Verify that a crimp tool, die and positioner set is certified for the contact in front of it and that its calibration is still live under ECSS-Q-ST-70-26C. Use when a tool is drawn from the pool for a flight harness and both the calendar interval and the crimp count since last calibration have to be honoured. Matches die and positioner to the contact part number and conductor range, consumes the allowance on whichever of elapsed days or accumulated cycles runs out first, honours a withdrawal in the register, and returns released, book-for-calibration, overdue or not-certified. Trigger: ecss, q-st-70-26, crimp-tool-certification, crimp-die-positioner-match, crimp-tool-calibration-interval, crimp-cycle-count-allowance, crimp-tool-withdrawal."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-crimp-tool-control, crimp-tool-certification, crimp-die-positioner-match, crimp-tool-calibration-interval, crimp-cycle-count-allowance, crimp-tool-withdrawal]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Tool, Die and Calibration Control (space-systems/ecss/q7026-crimp-tool-control)

Use when the task is the tooling step of ECSS-Q-ST-70-26C — deciding
whether a particular tool, die and positioner set may be drawn for a
particular crimp today, and whether its calibration is still live on
both the clock and the counter.

## Domain quick reference

- A crimp tool is certified as a set, not as a frame. Tool, die and
  positioner together are certified for a named contact family and a
  conductor cross-section range. Fitting a positioner borrowed from the
  next bench leaves the frame certified and the set not, and that is
  the failure this control exists to catch.
- Certification and calibration are separate questions asked in order.
  An uncertified set is wrong for this job whatever its calibration
  says, and reporting it as a calibration matter sends it to the wrong
  queue.
- Calibration is consumed two ways at once. Elapsed days eat the
  calendar allowance whether or not the tool was used; accumulated
  crimps eat the cycle allowance whether or not time passed. Whichever
  runs out first governs. A tool checked only against its date sticker
  can be six thousand crimps past its real allowance.
- There are three live states, not two. Below the recall threshold the
  tool is released; between the threshold and the full allowance it is
  still usable but has to be booked in; past the allowance it is out
  and the work it did is suspect.
- The allowance exactly consumed is a recall, not an overdue. A tool
  landing precisely on its interval has not yet exceeded it, and a
  strict comparison against a computed fraction is where this decision
  goes wrong on one machine and not another.
- A withdrawal in the register beats the arithmetic. The register
  records what a person decided; the fractions only say what the
  numbers allow.

## Workflow

1. Validate the register entry: identifiers, die and positioner part
   numbers, the certified contact list, the certified conductor range,
   both calibration intervals, the cycle counter and the withdrawal
   flag.
2. Validate the job: contact part number, conductor cross-section and
   the positioner the job calls for, folding part-number case.
3. Test certification first — contact in the list, positioner matching,
   conductor inside the range inclusive of both bounds — and collect
   every reason rather than stopping at the first.
4. Compute elapsed days from the last calibration date, refusing a date
   that precedes it.
5. Express both allowances as consumed fractions and take the larger as
   governing, naming which one it was.
6. Categorize the consumed fraction as released, book-for-calibration
   or overdue, treating the allowance exactly consumed as a booking.
7. Let a withdrawal override everything, then an uncertified set, then
   the calibration state.
8. Roll the pool up into released, to-book, blocked and whether the job
   can proceed at all today.

## Pitfalls

- Checking the frame and not the die or positioner. The set is the
  certified item.
- Reading the date sticker alone on a high-volume bench. The counter is
  the allowance that runs out first there.
- Reporting an uncertified set as a calibration problem, which books a
  tool in and still leaves the wrong die on it.
- Blocking a tool that is merely past its recall threshold. It is
  usable; it just has to be booked.
- Treating the allowance exactly consumed as overdue through a strict
  comparison on a computed fraction.
- Letting the arithmetic release a tool somebody withdrew.

## Behavior contract (gate 3)

Register and job validation, set certification with all reasons,
elapsed-day computation, both consumed fractions, the governing
allowance, the three calibration states including the exactly-consumed
boundary, withdrawal precedence and the pool roll-up are exercised by
the gate 3 contract test:
scripts/test_q7026_crimp_tool_control.py against
scripts/q7026_crimp_tool_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7026_crimp_tool_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
