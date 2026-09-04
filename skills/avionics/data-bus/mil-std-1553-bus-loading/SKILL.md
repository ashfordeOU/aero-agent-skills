---
name: mil-std-1553-bus-loading
description: "Use when you must compute the MIL-STD-1553 bus loading: convert a minor-frame message schedule into wire-word counts per message type (command and status overhead plus data words), apply the fixed 24 microsecond word slot at the 1 Mbps data rate, sum the schedule time, and return the bus utilization against the minor-frame length with an 80 percent loading guideline verdict. Produces per-message wire words and time, the schedule total, the percent utilization, the headroom to the 80 percent budget, and a FITS or OVER verdict. Trigger: mil std 1553 bus loading, minor frame schedule, wire word count, bus utilization, data bus load, bc to rt, rt to bc, rt to rt, message overhead, loading headroom."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mil-std-1553
    reference-only: true
gated: false
domain: avionics
pack: data-bus
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: data-bus
  tags: [mil-std-1553-bus-loading, 1553-minor-frame-load, 1553-wire-word-time, 1553-bus-utilization, bc-rt-message-overhead, 1553-schedule-budget]
  version: 0.1.0
  author: AeroSkills
---

# MIL-STD-1553 Bus Loading (avionics/data-bus/mil-std-1553-bus-loading)

Use when the task is MIL-STD-1553 bus loading at the schedule level: how
many wire words each message type puts on the 1 Mbps bus, how long the
message occupies the bus, and whether the whole minor-frame schedule fits
an 80 percent loading guideline. The model converts each message into
command and status overhead plus data words, charges a fixed 24
microsecond word slot per wire word, and returns the utilization and the
headroom to the budget. It pairs with avionics/data-bus/mil-std-1553,
which owns the 20-bit word encode/decode and format classification side,
and with avionics/data-bus/arinc429-bus-loading, the per-channel sibling
loading model.

## Domain quick reference

- Wire words per message (command and status overhead plus data words):
  BC-to-RT: 1 command + data_words + 1 status = data_words + 2;
  RT-to-BC: 1 command + 1 status + data_words = data_words + 2;
  RT-to-RT: 2 commands + 1 status + data_words = data_words + 3.
  A message carries 1 to 32 data words.
- Word slot: WORD_TIME_US = 20.0 us (20 bit times per word at the 1 Mbps
  data rate) plus WORD_GAP_US = 4.0 us inter-word gap gives WORD_SLOT_US
  = 24.0 us per wire word.
- Message time: message_time_us = wire_words * WORD_SLOT_US, exact.
- Schedule total: sum of the per-message times over the minor-frame
  schedule.
- Utilization: utilization_pct = total_us / frame_us * 100, with the
  default minor frame FRAME_US_DEFAULT = 5000.0 us (5 ms).
- Loading guideline: LOAD_BUDGET_FRACTION = 0.80, budget_us = 0.80 *
  frame_us; verdict is FITS when total_us <= budget_us, OVER otherwise.
- Headroom: headroom_us = budget_us - total_us; headroom_pct =
  (budget_us - total_us) / frame_us * 100, negative when OVER.
- Identity examples: BCRT 16 data words = 18 wire words; RTRT 8 data
  words = 11 wire words; each wire word costs exactly 24 us.

## Workflow

1. Lay out the minor-frame message schedule as (kind, data_words) pairs,
   with kind one of BCRT, RTBC, RTRT and data_words in 1..32.
2. Convert each message to wire words with wire_words: the function adds
   the command and status overhead (2 for BCRT and RTBC, 3 for RTRT).
3. Convert each message to bus time with message_time_us (wire words
   times the 24 us slot), or read the per-message times from the
   schedule summary.
4. Sum the schedule against the minor frame with schedule_utilization:
   it returns total_us, utilization_fraction, utilization_pct, budget_us,
   headroom_us, headroom_pct and the verdict. Pass frame_us only when the
   minor frame is not the default 5000 us.
5. Read the headroom percent directly from the summary, or call
   schedule_headroom for the scalar (0.80 * frame - total) / frame * 100.
6. Confirm the deterministic checks with the contract test
   scripts/test_mil_std_1553_bus_loading.py.

## Worked example

Reference schedule on a 5 ms minor frame (5000 us, budget 4000 us):

- BC-to-RT 16 data words: 18 wire words = 432.0 us.
- RT-to-BC 32 data words: 34 wire words = 816.0 us.
- RT-to-RT 8 data words: 11 wire words = 264.0 us.
- BC-to-RT 4 data words: 6 wire words = 144.0 us.

Module outputs for this schedule:

- total_us = 1656.0 us (432 + 816 + 264 + 144).
- utilization_pct = 33.12 percent (1656 / 5000 * 100), verdict FITS.
- budget_us = 4000.0 us, headroom_us = 2344.0 us.
- headroom_pct = 46.88 percent ((4000 - 1656) / 5000 * 100).
- A schedule four times larger totals 6624 us = 132.48 percent,
  verdict OVER, headroom_pct = -52.48 percent.
- Hand check: RT-to-RT 32 data words = 35 wire words = 840.0 us.

## Verification

- Confirm wire_words("BCRT", 16) returns 18 and message_time_us("BCRT",
  16) returns 432.0 us exactly.
- Confirm schedule_utilization on the reference schedule returns total_us
  1656.0, utilization_pct 33.12, verdict FITS, headroom_pct 46.88.
- Confirm the four-times schedule returns 132.48 percent with verdict
  OVER and a negative headroom_pct.
- Confirm dict keys are exactly total_us, utilization_fraction,
  utilization_pct, budget_us, headroom_us, headroom_pct, verdict.
- Confirm unknown kinds, data_words outside 1..32, frame_us <= 0 and an
  empty schedule all raise ValueError.
- Confirm utilization_pct equals total_us / frame_us * 100 and message
  time equals wire_words * 24 exactly (identity checks).
- Run the contract test offline: python3
  scripts/test_mil_std_1553_bus_loading.py (35 tests, deterministic).

## Related leaves

- avionics/data-bus/mil-std-1553: the protocol leaf for the 20-bit word
  encode/decode and format classification side of the same bus.
- avionics/data-bus/arinc429-bus-loading: the per-channel loading model
  for the other avionics data bus standard.
- avionics/data-bus/arinc664-afdx: switched network utilization for the
  Ethernet-based avionics backbone.

## Pitfalls

- Counting data words only: the wire-word count must include the command
  and status overhead (data_words + 2 for BCRT and RTBC, data_words + 3
  for RTRT), so a 16-data-word BC-to-RT message costs 18 wire words and
  432 us, not 16 words and 384 us.
- Charging only the word time: the bus is occupied for the word time
  plus the inter-word gap, 24 us per wire word; quoting 20 us per word
  understates a 1656 us schedule by 276 us.
- Forgetting the RT-to-RT second command: an RT-to-RT message carries two
  command words, one more wire word than the BC-to-RT or RT-to-BC forms
  at equal data words (35 against 34 at 32 data words).
- Treating the 80 percent budget as a frame fill target: the guideline
  leaves 20 percent of the frame as margin, so a 33.12 percent load on a
  5 ms frame has 46.88 percent headroom to the 4000 us budget, not 66.88
  percent to the frame end.
- Judging FITS against 100 percent: a schedule can exceed 100 percent of
  the frame (132.48 percent in the four-times case) and still be judged
  only OVER; report the percent utilization and the headroom, not just
  the verdict.
- Reading headroom as microseconds: headroom_pct is expressed as a
  percentage of the frame length, so it does not equal headroom_us
  divided by 100 on a 5 ms frame.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mil_std_1553_bus_loading.py

The test covers the wire-word contract for every message kind at the
worked-example data-word counts (BCRT 16 = 18, RTBC 32 = 34, RTRT 8 =
11, BCRT 4 = 6, RTRT 32 = 35), the 1..32 data-word bounds, message times
(432, 816, 264, 144 us) within 1e-9, the time identity wire_words * 24,
the reference schedule summary (total 1656 us, 33.12 percent, FITS, 46.88
percent headroom, budget 4000 us) within 1e-4, the four-times OVER case
(132.48 percent, negative headroom), exact dict keys, determinism, custom
frame scaling, the exact-budget FITS boundary, and ValueError rejection
of unknown kinds, out-of-range data words, non-positive frames and empty
schedules.

## Compliance

- Standards referenced, not reproduced: MIL-STD-1553B is the protocol
  framing standard cited here in reference-only mode; the loading model
  above is standard bus-scheduling methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
