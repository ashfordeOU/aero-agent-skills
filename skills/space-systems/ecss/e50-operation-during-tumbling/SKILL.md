---
name: e50-operation-during-tumbling
description: "Assess whether a space communication link can still be worked while the spacecraft tumbles, under ECSS-E-ST-50C clause 5.6.11.2: the rotating antenna beam has to sweep the ground station at all, and each sweep has to last long enough to set the link up and get a message through. Compute the visibility arc from the cone geometry, the window and outage per rotation, the whole messages a window carries, and the tumble rate or beam width that would restore a workable window. Use when reviewing link availability for a tumbling or uncontrolled spacecraft. Trigger: ecss, e-st-50-communications, tumbling-link-availability, antenna-beam-visibility-window, tumble-rate-outage-gap, link-setup-within-window, uncontrolled-attitude-communications."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.11.2
    items: [a, b]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-operation-during-tumbling, tumbling-link-availability, antenna-beam-visibility-window, tumble-rate-outage-gap, link-setup-within-window, uncontrolled-attitude-communications]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Operation During Tumbling (space-systems/ecss/e50-operation-during-tumbling)

Use when a space communication link has to be worked while the body is
rotating, per ECSS-E-ST-50C clause 5.6.11.2 — whether the beam reaches the
station at all, and whether the sweep it gives is long enough to use.

## Domain quick reference

- Two obligations that fail differently. The first is geometric: does
  the rotating beam ever cross the ground station. The second is
  temporal: does each crossing last long enough for setup plus at least
  one message, and is the gap between crossings survivable. A design
  can satisfy either one alone and still be unusable.
- The geometry is a cone sweep, not a fraction of a sphere. The spin
  carries the boresight round a cone about the rotation axis; the
  station sits at its own aspect angle from that axis; the separation
  swings between the sum and the difference of those angles. What
  matters is whether the beam half-width covers any part of that swing.
- Two geometries are degenerate and both are real. A station on the
  spin axis, or a boresight along it, sees a separation that does not
  change with rotation at all — so the link is up for the whole
  rotation or for none of it, and no tumble rate changes that.
- A zero-length window is not a short window. It is a geometry failure,
  and reporting a tumble rate as the remedy sends someone to detumble a
  spacecraft that would still be blind when it stopped.
- The outage between windows is the number operations cares about. A
  ten-second window every four minutes may be perfectly workable for
  telecommanding and useless for a recovery sequence.
- The two remedies are a slower tumble and a wider beam, and both fall
  out of the same model read backwards.

## Workflow

1. State the geometry as three angles: the station aspect from the spin
   axis, the antenna boresight cone from the same axis, and the beam
   width. Two of the three are spacecraft design, one is the pass.
   Take the tumble rate from the worst conditions the spacecraft is
   expected to reach rather than a nominal figure, since that is the
   case the link has to be designed to work in.
2. Compute the visibility arc over one rotation. Handle the degenerate
   cone explicitly — an all-or-nothing answer, not a division that
   happens not to raise.
3. Where the arc is zero, stop and say so as a geometry finding. No
   timing remedy applies.
4. Convert the arc to a window and the remainder to an outage at the
   declared tumble rate, and report the duty fraction alongside.
5. Compare the window against setup plus one message, with a relative
   tolerance so a window sized exactly to the need comes out workable.
6. Compare the outage against what the operations concept allows, and
   report how many whole messages each window actually carries.
7. Where the window is short, report both remedies as numbers: the
   tumble rate at or below which this arc suffices, and the beam width
   that would give a long enough arc at the rate that exists.
8. Record how the link's ability to cope with those conditions is
   shown by simulation, and check that the simulation is run again as
   the design moves through analysis, implementation and verification
   rather than once at the start. The geometry here sizes the case a
   simulation has to reproduce; it does not stand in for one.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.11.2a | 5 |
| ECSS-E-ST-50C Rev.2 5.6.11.2b | 8 |

## Pitfalls

- Treating antenna coverage as a solid-angle percentage. A beam that
  covers a fifth of the sphere may still never point at the station,
  because the tumble sweeps a cone rather than the whole sky.
- Reporting a very long gap when the station is never visible. There is
  no next window, and a number there implies the link comes back.
- Sizing the window against message time and forgetting setup. On a
  tumbling spacecraft the link is re-acquired every rotation, so the
  setup is paid every window, not once.
- Counting a partial message. A window that holds setup plus most of a
  message delivers nothing, so the count has to be whole messages.
- Deciding the window verdict with a bare inequality against setup plus
  message. Two arithmetically identical geometries can straddle the
  bound on different machines, so the verdict follows the build host.

## Behavior contract (gate 3)

Angle, beam-width, rate and duration validation, the cone-sweep
separation and visibility arc including both degenerate geometries, the
window, outage and duty fraction, the whole-message count, the
four-way verdict with a tolerance at the window and outage bounds, and
the tumble-rate and beam-width inverses checked against the same model
are exercised by the gate 3 contract test:
scripts/test_e50_operation_during_tumbling.py against
scripts/e50_operation_during_tumbling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_operation_during_tumbling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
