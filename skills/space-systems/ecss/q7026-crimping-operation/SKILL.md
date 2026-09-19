---
name: q7026-crimping-operation
description: "Perform and grade one crimp cycle on a high-reliability electrical connection. Use when a crimp is being made and the setup has to be defensible before the handles move: match the die and positioner to the contact part number, take the selector setting from the wire gauge inside that contact, refuse a tool whose calibration has lapsed on date or on cycle count, confirm the ratchet released only on a completed cycle and that the barrel took exactly one, then grade the resulting height against its two-sided band and split remake from reject on the wire left. Trigger: ecss, q-st-70-26-crimping, crimp-die-and-positioner-match, crimp-selector-setting-by-gauge, crimp-tool-calibration-currency, crimp-ratchet-full-cycle, crimp-over-and-under-compression."
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
  tags: [ecss, q-st-70-26-crimping, q7026-crimping-operation, crimp-die-and-positioner-match, crimp-selector-setting-by-gauge, crimp-tool-calibration-currency, crimp-ratchet-full-cycle, crimp-over-and-under-compression]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Crimping Operation (space-systems/ecss/q7026-crimping-operation)

Use when the Process clause of ECSS-Q-ST-70-26 is the task: running the
crimp cycle itself, with the tooling, the setting and the completion of
the cycle all decided before the handles move and none of them
recoverable afterwards.

## Domain quick reference

- The cycle is not adjustable. Everything that decides whether the joint
  is a cold weld or a mechanical clamp is settled by the setup, so the
  grading here is mostly a grading of the setup.
- The die and the positioner belong to the contact part number. The die
  closes a profile and the positioner decides where along the barrel it
  closes, so a die from a neighbouring contact produces a crimp whose
  height the band does not describe at all.
- The selector setting belongs to the wire gauge inside that contact,
  not to the contact alone. One setting carried across a mixed-gauge
  harness over-compresses the fine wire and under-compresses the heavy
  one, and both crimps come out looking finished.
- Calibration has two clocks. A tool is due on a date and on a cycle
  count, whichever arrives first, and a busy tool reaches the cycle
  limit long before the date. Either lapsing makes the compression
  applied unknown rather than wrong, which is why the crimps taken
  afterwards have no disposition rather than a bad one.
- The ratchet is the only thing enforcing a full cycle. A cycle released
  by hand applied part of the compression and left a crimp that looks
  complete, which is exactly why the tool has a ratchet instead of a
  stop.
- A barrel takes one cycle. A second pass work-hardens the material
  along a different profile, and more compression is not better
  compression.
- Crimp height fails in two opposite directions. Below the band the
  barrel has been driven into the strands and cut them; above it the
  barrel never closed and the joint is mechanical.
- A failed crimp is cut off, not adjusted. What separates a remake from
  a reject is therefore the wire length that is left, not anything about
  the crimp.

## Workflow

1. Validate the setup table: a die and positioner per contact part, and
   per gauge inside it a selector setting, a height target and a
   tolerance that stays below the target.
2. Resolve the (contact, gauge) entry, refusing a contact the table does
   not carry and a gauge the contact does not accept rather than
   borrowing a neighbouring setting.
3. Authorize the cycle before it runs: die and positioner against the
   contact, selector against the gauge, calibration against both its
   date and its cycle interval. Collect every blocker rather than
   stopping at the first.
4. Grade the cycle: completion, exactly one crimp on the barrel, and a
   ratchet that was actually fitted.
5. Grade the compression: the measured height against the band either
   side of the target, naming over-crimp and under-crimp separately
   because they are opposite process errors.
6. Take the worst disposition, then convert a remake into a reject where
   the wire margin left is short of what a re-termination needs.
7. Roll the run up: accepted, remake and rejected counts, first-pass
   yield, the number of cycles that ran unauthorized, and the crimps the
   record never covered.

## Pitfalls

- Selecting tooling by wire gauge alone. The die and positioner are
  properties of the contact, and the gauge only chooses the setting
  inside it.
- Carrying one selector setting across a mixed-gauge harness. The
  setting that is right for the heavy wire crushes the fine one.
- Checking the calibration date and not the cycle count. A tool in a
  production cell reaches its cycle interval months before its date, and
  the date sticker still reads current.
- Treating a lapsed calibration as a failed crimp. The crimps taken
  afterwards have unknown compression, which is a records problem with a
  different remedy from a bad crimp.
- Releasing a ratchet by hand to free a jammed contact and keeping the
  crimp. The compression that was applied is whatever the handles
  reached.
- Running a second cycle to correct a light crimp. The barrel is already
  work-hardened and the second profile does not undo the first.
- Reading crimp height as a single-sided limit. A check written one way
  round passes every barrel that never closed.
- Offering a remake without looking at the wire. In a harness whose
  routed length is already cut, the contact can come off and nothing can
  go back on.
- Comparing a crimp height with a band edge, or a cycle count with its
  interval, by bare arithmetic. A height specified to land exactly on
  the limit can evaluate a few units in the last place past it after a
  unit conversion, so the comparison absorbs that representation error
  while the limit stays untouched.

## Behavior contract (gate 3)

The setup table validation, the (contact, gauge) resolution and its
refusals, the die and positioner match, the selector check, the two-clock
calibration check, the pre-cycle authorization with its collected
blockers, the cycle completion and single-crimp rules, the two-sided
compression grading, the remake-to-reject conversion on wire margin and
the run rollup with first-pass yield are exercised by the gate 3 contract
test: scripts/test_q7026_crimping_operation.py against
scripts/q7026_crimping_operation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7026_crimping_operation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
