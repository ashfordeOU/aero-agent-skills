---
name: arinc429-bus-loading
description: "Use when you must budget the ARINC 429 bus loading: sum the per-label transmission rates in labels per second into the total word rate, price each transmitted word at 36 bit-times (32 data bits plus the 4-bit gap) for the bus load in bits per second, compute the percent utilization of the 100 kbps or 12.5 kbps link, flag schedules that exceed the word-per-second capacity (about 2778 words per second at 100 kbps), and report the headroom against the common 80 percent design guideline. Produces the total word rate, bus load, percent utilization, capacity verdict, and design headroom that gate the ARINC 429 label rate table. Trigger: arinc 429 bus loading, label rate budget, percent bus utilization, word rate capacity, transmit schedule headroom, 100 kbps link."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arinc-429
    reference-only: true
gated: false
domain: avionics
pack: data-bus
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: data-bus
  tags: [arinc429-bus-loading, label-rate-budget, bus-utilization-percent, word-rate-capacity, transmit-schedule-headroom]
  version: 0.1.0
  author: AeroSkills
---

# ARINC 429 Bus Loading (avionics/data-bus/arinc429-bus-loading)

Use when the task is budgeting an ARINC 429 transmit schedule for a
civil avionics data bus: how many words per second the label rate
table asks the transmitter to send, what that costs in bus occupancy,
and whether the schedule fits the link with headroom. Every
transmitted ARINC 429 word occupies 36 bit-times on the bus, 32 data
bits plus the 4-bit gap between words, so a schedule of label rates
sums into a total word rate and the word rate prices the bus directly
at 36 bits per word. The module is pure Python stdlib and
deterministic; you supply the label rate schedule (a list of rates in
labels per second, or a dict mapping a label to its rate) and it
returns the load, utilization, capacity verdict and design headroom.
It pairs with avionics/data-bus/arinc429-protocol, which covers the
32-bit word layout and parameter coding itself (this leaf never builds
or interprets a word), and with avionics/data-bus/arinc664-afdx and
mil-std-1553 for the other civil and military bus loading models.

## Domain quick reference

- Every ARINC 429 word occupies BITS_PER_WORD = 36.0 bit-times (32
  data bits plus a 4-bit gap), whatever the label content, so the word
  rate alone determines bus occupancy.
- Total word rate: total_word_rate(label_rates) = sum of the per-label
  rates. A schedule of 3 labels at 50 Hz, 4 at 20 Hz and 2 at 10 Hz
  totals 3*50 + 4*20 + 2*10 = 250 words/s.
- Bus load: bus_load_bps(words_per_s) = words_per_s * 36. The 250
  words/s schedule loads 250 * 36 = 9000 bps.
- Percent utilization: percent_utilization(load, link_rate) = load /
  link_rate * 100. Against the 100 kbps link (RATE_100_KBPS =
  100000.0) the 9000 bps load is 9.0 percent.
- Word capacity: word_capacity(link_rate) = link_rate / 36. The 100
  kbps link carries 100000 / 36 = 2777.8 words/s; the 12.5 kbps link
  (RATE_12_5_KBPS = 12500.0) carries 347.2 words/s.
- Verdict rule: OVER when the utilization exceeds 100 percent, FITS
  otherwise. A 3000 words/s schedule at 100 kbps loads 108000 bps,
  108.0 percent, so it needs a second bus or a rate reduction.
- Headroom: headroom = max(0, DESIGN_GUIDELINE_PCT - utilization)
  with DESIGN_GUIDELINE_PCT = 80.0, the common design guideline that
  keeps about 20 percent of the bus free for growth.
- The identity: a schedule at exactly the word capacity sits at 100
  percent utilization; at exactly the 80 percent design load the
  headroom is zero; doubling every label rate doubles the utilization.
- ARINC 429 (Mark 33 DITS) frames the bus context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Collect the transmit schedule: every label on the bus and its
   transmission rate in labels per second (a list of rates, or a dict
   {label: rate}).
2. Sum the schedule with total_word_rate to get the total words per
   second the transmitter must emit.
3. Price the bus with bus_load_bps (words per second times 36 bits per
   word) to get the load in bits per second.
4. Normalize to the link with percent_utilization, using the default
   RATE_100_KBPS or the explicit RATE_12_5_KBPS low-speed link.
5. Get the capacity with word_capacity and the verdict dict with
   capacity_verdict(total_words_per_s): capacity_wps, utilization_pct,
   verdict (OVER when utilization exceeds 100 percent, else FITS) and
   headroom_pct against the 80 percent guideline.
6. For the full budget in one call, run bus_loading_summary(label_rates)
   and read total_words_per_s, load_bps, utilization_pct, capacity_wps,
   verdict and headroom_pct.
7. If the verdict is OVER, cut label rates, merge low-rate labels, or
   split the schedule across a second bus, then re-run the summary.
8. Confirm the deterministic checks with the contract test
   scripts/test_arinc429_bus_loading.py.

## Worked example

Reference schedule on the 100 kbps link: 3 labels at 50 Hz, 4 labels
at 20 Hz, 2 labels at 10 Hz.

- total_word_rate: 3*50 + 4*20 + 2*10 = 250.0 words/s.
- bus_load_bps: 250.0 * 36.0 = 9000.0 bps.
- percent_utilization: 9000.0 / 100000.0 * 100 = 9.0 percent.
- word_capacity: 100000.0 / 36.0 = 2777.78 words/s.
- capacity_verdict(250.0): utilization 9.0 percent, verdict FITS,
  headroom 80 - 9 = 71.0 percent. The schedule uses well under the
  guideline.
- Adding one 100 Hz label: 350.0 words/s, 12600.0 bps, 12.6 percent,
  still FITS.
- Over-capacity check: 30 labels at 100 Hz total 3000.0 words/s,
  108000.0 bps, 108.0 percent utilization, verdict OVER, headroom 0.0:
  the schedule needs a second bus or a rate reduction.
- Low-speed link at 12.5 kbps: capacity 12500.0 / 36.0 = 347.2
  words/s; a 300 words/s schedule is 86.4 percent (FITS, but above the
  guideline so headroom is 0.0), and 350 words/s is 100.8 percent,
  OVER.

## Verification

- Confirm total_word_rate of the reference schedule is 250.0 words/s
  and of a single 1 Hz label is 1.0 word/s.
- Confirm bus_load_bps(250.0) is 9000.0 bps and bus_load_bps(100.0) is
  3600.0 bps.
- Confirm percent_utilization at the word capacity is 100.0 percent
  within 1e-6, and 108.0 percent for 3000 words/s.
- Confirm capacity_verdict(300.0, RATE_12_5_KBPS) gives 86.4 percent
  FITS and capacity_verdict(350.0, RATE_12_5_KBPS) gives 100.8 percent
  OVER.
- Confirm the headroom is 71.0 at the 9 percent reference load, 0.0 at
  the 80 percent design load and 0.0 over capacity.
- Confirm bus_loading_summary returns exactly the documented keys.
- Confirm ValueError on an empty schedule, a negative rate, a
  non-positive link rate and non-positive bits per word.
- Run the contract test offline: python3
  scripts/test_arinc429_bus_loading.py (34 tests, deterministic).

## Related leaves

- avionics/data-bus/arinc429-protocol: the companion leaf for the
  32-bit word layout and parameter coding of the words this leaf
  schedules; it states the 36 bit-time occupancy fact but does not sum
  a per-label schedule or compute utilization.
- avionics/data-bus/arinc664-afdx: the switched network companion
  leaf whose 100 Mbps link utilization budget is the symmetry anchor
  for this utilization calculation.
- avionics/data-bus/mil-std-1553: the military multiplex bus
  scheduling companion with its 1 Mbps dual-redundant bus and message
  timing model.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_arinc429_bus_loading.py

The test covers the reference schedule totals and bounds, the 36
bits-per-word load pricing, percent utilization at and beyond the
word-per-second capacity, the 12.5 kbps link capacity and verdicts,
the headroom boundaries at the 80 percent guideline, the
bus_loading_summary convenience dict keys and values, the doubling
and determinism identities, the module constants, and ValueError
rejection of an empty schedule, negative rates, non-positive link
rates and non-positive bits per word.

## Compliance

- Standards referenced, not reproduced: ARINC 429 (Mark 33 DITS) is
  the ARINC standard for civil avionics point-to-point buses; the bus
  loading relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
