---
name: q7031-curing-conditions
description: "Verify that an applied paint system actually reached its cure state under ECSS-Q-ST-70-31C: read the logged profile hold by hold, award no credit below the minimum cure temperature and none plus an overbake finding above the qualified ceiling, convert every earning hold into equivalent hours at the reference temperature through the ten-degree rule, then test accumulated hours, continuous in-window dwell, the humidity window and the ramp rate between holds. Use when a cure log, an oven profile or a room-temperature dwell has to be signed off before the next coat or before handling. Trigger: ecss, q-st-70-31c-paint-cure, paint-cure-equivalent-hours, coating-cure-temperature-window, paint-cure-humidity-window, coating-overbake-ceiling, paint-cure-dwell-and-ramp."
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
  tags: [ecss, q-st-70-31c-paint-cure-scope, q7031-curing-conditions, paint-cure-equivalent-hours, coating-cure-temperature-window, paint-cure-humidity-window, coating-overbake-ceiling, paint-cure-dwell-and-ramp]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paint Application -- Curing Conditions (space-systems/ecss/q7031-curing-conditions)

Use when the task is the cure control of ECSS-Q-ST-70-31C: a coat has been
applied and the question is whether the time, temperature and humidity it
actually saw add up to the cure the paint system's process document requires,
before the next coat goes on or the hardware is handled.

## Domain quick reference

- Cure is a reaction, so it is paid for in time at temperature and not in
  elapsed time. The usual working model is the ten-degree rule: a ten kelvin
  rise multiplies the rate by a factor the system declares, so a short warm
  hold and a long cool one can be worth the same equivalent hours.
- The rule only applies inside a window. Below the system's minimum cure
  temperature the reaction has effectively stopped rather than merely slowed,
  so a cold hold earns nothing at all; extrapolating the rule downward is how
  an undercured film gets signed off.
- The ceiling is not a soft limit either. Above the qualified temperature the
  film changes rather than cures: binder degradation, thermo-optical drift
  and embrittlement. A hold above it earns no credit and is a finding in its
  own right, even when the rest of the profile carries the hours.
- Humidity is a cure input for part of the chemistry. A moisture-cure system
  will not advance in dry air, and a solvent-borne one blushes in wet air, so
  a hold whose humidity sat outside the declared window earns no credit; a
  hold with no humidity reading at all, where the system declares a window,
  is an evidence gap, not a pass.
- Continuous dwell and ramp rate carry separate requirements from the hour
  total. Twenty accumulated hours broken by a cold night are not the same as
  twenty continuous ones, and a steep ramp on a thick wet film drives solvent
  through a skinning surface.

## Workflow

1. Validate the profile: an ordered list of holds, each with a positive
   duration, a temperature inside any plausible cure range, and a humidity
   reading where the system declares a window.
2. Award credit hold by hold. Refuse credit below the minimum, refuse credit
   and raise an overbake finding above the ceiling, refuse credit outside the
   humidity window or where the reading is missing.
3. Convert every earning hold to equivalent hours at the reference
   temperature using the declared ten-degree factor, and sum them.
4. Derive the longest run of consecutive earning holds as the continuous
   in-window dwell, and the ramp rate between each pair of holds.
5. Test accumulated equivalent hours against the requirement, the dwell
   against its minimum, and each ramp against its limit, absorbing
   representation error at each boundary with a named tolerance.
6. Return one cure-complete verdict with the per-hold credits, the totals and
   every finding named.

## Pitfalls

- Counting wall-clock hours. Elapsed time and equivalent hours diverge as
  soon as the profile leaves the reference temperature, and the requirement
  is written against the latter.
- Extending the ten-degree rule below the minimum cure temperature. It
  predicts a small positive rate where the real one is effectively zero, and
  that is exactly the error that lets a cold weekend count as cure.
- Treating an overbake as surplus cure. Extra heat past the ceiling is a
  different failure mode, not more of the same success, and the hours it
  contributes are not credit.
- Signing off a profile that carries no humidity record when the system
  declares a window. An absent reading is an evidence gap; recording it as
  compliant converts an unknown into a pass.
- Reading the hour total and ignoring how it was accumulated. Dwell
  continuity and ramp rate are separate requirements, and a profile can meet
  the hours while failing both.

## Behavior contract (gate 3)

The profile validation, per-hold credit rules at both temperature limits and
the humidity window, the ten-degree equivalent-hour conversion, the
accumulated total, the longest continuous dwell, the ramp rates and the
combined cure verdict are exercised by the gate 3 contract test:
scripts/test_q7031_curing_conditions.py against
scripts/q7031_curing_conditions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7031_curing_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
