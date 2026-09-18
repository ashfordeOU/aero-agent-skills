---
name: e2020-output-current-telemetry-provision
description: "Audit the output-current telemetry provision of ECSS-E-ST-20-20C clause 5.2.8.2.1. Use when every limiter in a distribution unit has to put the current it delivers into the housekeeping stream and that provision must be shown complete and worth reading: confirm one dedicated channel per limiter, reject a channel that sums several outputs, check the full scale spans the limitation current with headroom, check the quantisation step resolves the load change the mission needs to see, sum the offset, gain and quantisation terms at the operating point against the declared accuracy, and name the limiter whose channel governs the verdict. Trigger: ecss, e-st-20-20c, limiter-output-current-telemetry, housekeeping-current-channel, telemetry-full-scale-headroom, current-channel-quantisation-step, current-telemetry-error-budget, shared-current-channel-defect."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-output-current-telemetry-provision, limiter-output-current-telemetry, housekeeping-current-channel, telemetry-full-scale-headroom, current-channel-quantisation-step, current-telemetry-error-budget, shared-current-channel-defect]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Output Current Telemetry Provision (space-systems/ecss/e2020-output-current-telemetry-provision)

Use when the task is the output-current telemetry of ECSS-E-ST-20-20C
clause 5.2.8.2.1 -- showing that every limiter in a distribution unit
reports the current it is actually delivering to its own load, and that
the channel reporting it is good enough for the ground and the onboard
software to act on.

## Domain quick reference

- The clause is per limiter, not per unit. A channel that sums several
  outputs reports the unit's draw, which is a different quantity: it
  cannot tell a healthy load from a failed one beside an overdrawing
  neighbour, so it covers none of the limiters individually.
- Coverage is the first question and it is binary. A limiter with no
  channel at all delivers current nobody can see, and no amount of
  quality in the other channels makes up for it.
- Three properties decide whether a channel is worth reading: the full
  scale it spans, the step it resolves, and the error it carries at the
  point the load actually sits.
- Full scale has to reach past the limitation current with headroom.
  A channel that pins at or below the limiting point goes blind exactly
  when the current is most interesting -- during the rise into
  limitation, which is the event the telemetry was fitted to witness.
- The quantisation step is the full-scale span divided by the code
  count, one less than two to the power of the bit depth. A load change
  smaller than one step leaves no trace in the stream at all, so the
  step is judged against the smallest change the mission needs to see,
  not against the full scale.
- The error budget has three terms: an offset that is a fraction of
  full scale and is there at any reading, a gain error that is a
  fraction of the reading itself, and half a step of quantisation.
  They are summed at worst case, because one unit's channel is a single
  draw from the population and the consumer sees that draw.
- Offset dominates at a light load and gain dominates near full scale,
  so a channel judged only at its top reading can be far outside its
  accuracy at the operating point the load really occupies.

## Workflow

1. Enumerate the limiters in the unit and resolve coverage first:
   which have a current channel and which do not. Reject a duplicate or
   missing identifier rather than guessing, because every later finding
   is attributed by identifier.
2. For each channel, confirm it serves exactly one limiter. A channel
   declared across several outputs fails here regardless of how good
   its converter is.
3. Derive the full scale the limitation current plus headroom demands,
   and compare the declared span against it.
4. Derive the quantisation step from the span and the bit depth, and
   compare it against the smallest load change the mission needs to
   resolve.
5. Build the worst-case error at the declared operating current from
   the offset, gain and quantisation terms, and compare it against the
   declared accuracy.
6. Close with an adequate or inadequate verdict for the provision as a
   whole. It is adequate only when coverage is complete and every
   channel passes on its own, and each finding names the limiter it
   belongs to.

## Pitfalls

- Counting a unit-level current channel as covering its limiters. It
  measures the sum, so a load that has failed open is hidden by any
  other load that has drifted up, and the clause's per-limiter question
  is never answered.
- Setting full scale at the limitation current. The channel then pins
  at the top of its range through the whole limiting event and reports
  a constant, which reads on the ground as a channel that has stopped
  responding.
- Judging the error budget at full scale only. The gain term is largest
  there and the offset term is proportionally smallest, so a channel
  that looks accurate at its top reading can be well outside its
  requirement at a light load.
- Quoting bit depth as if it were resolution. The step is the span over
  the code count, so adding bits to a channel whose span was widened
  for headroom can leave the resolution exactly where it started.
- Ignoring the offset term because it is small in percent. It is a
  fraction of full scale, not of the reading, so on a lightly loaded
  limiter it can be a large fraction of the current being reported.
- Comparing a budget against its requirement by bare arithmetic. The
  total is a sum of three products and a division, so a channel
  designed to sit exactly on its accuracy requirement can land a few
  units in the last place above it; the comparison absorbs that
  representation error while the requirement stays untouched.

## Behavior contract (gate 3)

The coverage resolution, dedicated-channel check, full-scale headroom,
quantisation step, worst-case error budget, per-channel grading and the
adequate/inadequate provision verdict are exercised by the gate 3
contract test:
scripts/test_e2020_output_current_telemetry_provision.py against
scripts/e2020_output_current_telemetry_provision_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_output_current_telemetry_provision.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
