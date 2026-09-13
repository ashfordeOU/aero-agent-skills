---
name: e2008-thermal-cycling-general-provisions
description: "Verify that the continuity evidence taken across a solar-array thermal-cycling run really shows the cells and the wiring conducting from the first cycle to the last, anchored at ECSS-E-ST-20-08C clause 5.5.1.3.2. Use when the task is judging or planning that evidence: validate each monitored channel's baseline and checkpoint readings, measure the resistance drift against the allowed fraction, detect an open standing at the end of the run and an intermittent open that closed again before the next checkpoint, group every channel as continuous, drifting, intermittent or open, and flag an unwitnessed stretch of cycles or a missing cell-string or wiring channel. Trigger: ecss, e-st-20-08c, solar-array-thermal-cycling, cell-string-continuity-monitoring, interconnect-resistance-drift, intermittent-open-detection, continuity-checkpoint-coverage, cycling-continuity-evidence."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-thermal-cycling-general-provisions, solar-array-thermal-cycling, cell-string-continuity-monitoring, interconnect-resistance-drift, intermittent-open-detection, continuity-checkpoint-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Thermal Cycling General Provisions (space-systems/ecss/e2008-thermal-cycling-general-provisions)

Use when the task is the general-provision rule of ECSS-E-ST-20-08C
clause 5.5.1.3.2 — establishing, or judging, the evidence that the cells
and the wiring of a photovoltaic assembly kept electrical continuity for
the whole cycle count, rather than only at the two moments somebody
happened to measure.

## Domain quick reference

- The evidence is a series, not a pair of endpoints. A cycling failure
  is a joint working itself apart, so the interesting quantity is how
  the resistance of each channel moved over the run. Two readings taken
  before and after can be identical either side of a fracture that
  opened and re-closed on the way.
- Two quantities are read from each channel: the resistance itself,
  against an open-circuit threshold, and its drift from the channel's
  own baseline as a fraction. A rising fraction well under the open
  threshold is a joint degrading, which the clause wants visible before
  it becomes a break.
- An open seen at an intermediate checkpoint that is closed again at the
  next one is an intermittent, and it is evidence. A cold joint closes
  when the assembly returns to ambient, so treating the reading as noise
  because the final measurement is healthy throws away the only record
  of the failure.
- Channels are grouped so the summary is readable: continuous when every
  reading stayed inside the allowed drift, drifting when the drift went
  past it, intermittent when an open appeared and cleared, open when the
  channel is open at the end of the run. Continuity is maintained only
  when every channel is continuous.
- Coverage has two halves. In cycles: a reading before the run, a reading
  at the end, and no stretch between checkpoints wider than the allowed
  gap. In hardware: at least one cell-string channel and one wiring
  channel, because the clause asks about both and an interconnect
  channel substitutes for neither.

## Workflow

1. Validate each channel: a non-empty identifier, a known kind, a
   positive baseline resistance and an open-circuit threshold above that
   baseline. A threshold at or below the baseline cannot detect
   anything and is an input error.
2. Validate the reading series: whole cycle numbers inside the run, in
   increasing order, with no repeated cycle, and non-negative
   resistances.
3. Measure the drift of every reading from the channel baseline and keep
   the largest. A drift landing exactly on the allowed fraction is
   allowed — the tolerance sits on the comparison, never on the limit.
4. Mark every checkpoint whose reading reached the open threshold, and
   note whether the final reading is one of them.
5. Group the channel: open when the final reading is open, intermittent
   when an earlier reading was open and the final one is not, drifting
   when the largest drift went past the allowance, continuous otherwise.
6. Check the checkpoint series of each channel for a missing start, a
   missing end and any gap wider than the allowance, and check the
   channel set for a missing cell-string or wiring channel.
7. Report the per-channel records, the counts by group and every
   finding. Continuity is maintained only when the finding list is
   empty.

## Pitfalls

- Measuring only before and after the run. An intermittent open that
  closes on cool-down leaves no trace in an endpoint pair, so a pass
  built on two readings is a statement about two moments, not about the
  cycle count.
- Dismissing a single open reading as instrumentation noise. The
  clause's subject is continuity; an open that appeared once is the
  evidence, and discarding it needs a demonstrated measurement fault,
  not the fact that the next reading was healthy.
- Watching resistance only against the open threshold. A joint on its
  way to failure sits far below that threshold for most of its life, and
  the drift fraction is what makes the degradation visible while the
  channel still conducts.
- Monitoring the cell strings and calling the wiring covered. The
  terminations and the harness see the same cycling and fail in the same
  way; a run that never instrumented them produces no evidence for them.
- Leaving a long unwitnessed stretch in the middle of the run. A gap
  wider than the allowance means the cycles in it carry no evidence,
  whatever the readings either side of it show.
- Widening the drift allowance to absorb a channel that went past it. A
  drift exactly on the allowance is already accepted by the comparison
  tolerance; a drift past it is a finding about the hardware.

## Behavior contract (gate 3)

The channel validation, reading-series validation, drift measurement,
open and intermittent detection, channel grouping, checkpoint-gap and
channel-kind coverage checks are exercised by the gate 3 contract test:
scripts/test_e2008_thermal_cycling_general_provisions.py against
scripts/e2008_thermal_cycling_general_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_thermal_cycling_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
