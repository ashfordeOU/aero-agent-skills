---
name: e2020-rlcl-repetitive-overload-endurance
description: "Assess whether a retriggerable latching current limiter holds its derating limits through an autonomous retrigger train, for ECSS-E-ST-20-20C clause 5.2.10.2.1: form the retrigger duty cycle from the limitation and off intervals, settle a single-pole junction model over the repeating train, count the retriggers a persistent fault produces inside the declared window, then solve the shortest off time and the highest duty cycle that still hold the junction limit and grade average dissipation and retrigger count against the rating. Use when a fault persists and the limiter re-arms itself unattended. Trigger: ecss, e-st-20-20c, retriggerable-latching-current-limiter, rlcl-retrigger-duty-cycle, rlcl-repetitive-overload, retrigger-off-time-solve, rlcl-junction-temperature, rlcl-derating-limits."
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
  tags: [ecss, e-st-20-20c, e2020-rlcl-repetitive-overload-endurance, retriggerable-latching-current-limiter, rlcl-retrigger-duty-cycle, rlcl-repetitive-overload, retrigger-off-time-solve, rlcl-junction-temperature, rlcl-derating-limits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution — RLCL Repetitive-Overload Endurance (space-systems/ecss/e2020-rlcl-repetitive-overload-endurance)

Use when the task is the repetitive-overload endurance of a retriggerable
limiter under ECSS-E-ST-20-20C clause 5.2.10.2.1 -- showing that an outlet
which re-arms itself after every trip still sits inside its derating limits
through the whole unattended train a fault that refuses to clear will produce.

## Domain quick reference

- The retriggerable case is a design question, not an operations question. A
  plain latching limiter waits for a command, so the interval between overloads
  belongs to whoever is at the console. A retriggerable one re-arms after a
  fixed off time, so the duty cycle of the overload train was fixed when the
  off time was chosen and nobody is in the loop to slow it down.
- The train is therefore characterised by two intervals: the limitation time
  the part spends regulating into the fault, and the off time it waits before
  trying again. Their sum is the retrigger period and their ratio is the duty
  cycle that every average quantity scales with.
- The junction does not return to the case between retriggers unless the off
  time is long against the thermal time constant. The repeating train settles
  on a peak given by the single-interval rise divided by one minus the product
  of the heating and cooling exponentials, which is unbounded in the useful
  sense: as the off time goes to zero the settled peak walks up to the full
  steady-state rise of continuous conduction.
- That expression inverts. Given the headroom the case temperature leaves under
  the derated junction limit, there is a shortest off time whose settled peak
  lands exactly on the limit, and a corresponding highest duty cycle. A failing
  design should be handed that number rather than just a red verdict.
- The inversion has a genuine no-solution branch. If one limitation interval on
  its own already uses up the headroom, no off time however long recovers it,
  because the first interval breaks the limit before any cooling happens. The
  answer then is a shorter limitation time or a better thermal path, and
  returning a very large off time instead would hide that.
- A persistent fault also accumulates retriggers. The count of complete cycles
  inside the declared fault-persistence window is what the rated retrigger
  capability is spent against, and it is a life limit independent of how
  comfortable the temperature margin looks.

## Workflow

1. Validate the bus, the limiter setting, the faulted load, the limitation and
   off intervals, the fault-persistence window and the pass-element thermal and
   rating data. Refuse a load too light to draw the limiting current, since it
   never enters limitation and therefore never retriggers.
2. Form the retrigger period and duty cycle, and the pass-element dissipation
   of one limitation interval at the regulated output voltage.
3. Settle the single-pole junction model over the repeating train and add the
   case temperature to get the peak junction temperature the derating limit
   applies to.
4. Count the complete retrigger cycles inside the fault window, treating a
   window shorter than one period as a reportable condition rather than as
   zero stress silently accepted.
5. Solve the shortest off time and the highest duty cycle the junction headroom
   permits, and report the no-solution branch explicitly when a single
   limitation interval already exhausts the headroom.
6. Grade junction temperature, duty cycle, limiting-current derating, average
   dissipation and retrigger capability, each against its declared limit with
   representation error absorbed by a named tolerance, and report the verdict
   with the off-time shortfall the design has to close.

## Pitfalls

- Carrying the plain latching limiter's recovery interval into the
  retriggerable case. The operator's pause is not the design's off time, and a
  part that re-arms in milliseconds runs a duty cycle an operator would never
  produce.
- Reading the settled peak off a single limitation interval. The train stacks
  whenever the off time is short against the thermal time constant, and the
  single-interval number is exactly the reassuring one a failing design shows.
- Returning an enormous off time when the headroom is already gone. That branch
  has no solution at all, and presenting one invites a designer to lengthen the
  off time forever instead of shortening the limitation time.
- Grading only the temperature. The rated retrigger capability is a separate
  life limit, and a persistent fault inside a long window can spend it while
  every thermal check still passes.
- Averaging the dissipation over the fault window instead of over the retrigger
  period. The derated power rating is written against the repeating cycle, and
  a window that happens to be long makes any duty cycle look harmless.
- Moving a derated limit so an exactly-on-the-bound case passes. An equality at
  a limit is a representation question, handled by the tolerance inside the
  comparison; the policy value stays where it was declared.

## Behavior contract (gate 3)

The input validation, retrigger timing, dissipation resolution, settled
junction-temperature train, off-time and duty-cycle inversion, retrigger
counting and derating verdict are exercised by the gate 3 contract test:
scripts/test_e2020_rlcl_repetitive_overload_endurance.py against
scripts/e2020_rlcl_repetitive_overload_endurance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_rlcl_repetitive_overload_endurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
