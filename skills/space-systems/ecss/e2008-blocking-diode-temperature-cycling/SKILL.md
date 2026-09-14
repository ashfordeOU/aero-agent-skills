---
name: e2008-blocking-diode-temperature-cycling
description: "Determine the eclipse-cycle count a blocking diode temperature cycling run must deliver, then judge the run against it: size the required cycles from the mission eclipse rate, the design life and the declared test margin, check the hot and cold plateaus, the dwell that lets the stack reach them and the transition that keeps a cycle from becoming a shock, refuse a sentence drawn from fewer cycles than the mission owes, and group every sample by its forward-voltage and reverse-leakage drift and by any crack the run opened. Use when planning, running or auditing a blocking diode temperature cycling campaign. Trigger: ecss, e-st-20-08c-clause-12-6-5, blocking-diode-temperature-cycling, solar-array-eclipse-cycle-equivalence, blocking-diode-cycle-count-sizing, blocking-diode-thermal-plateau-dwell, blocking-diode-post-cycling-drift."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-blocking-diode-temperature-cycling, blocking-diode-temperature-cycling, solar-array-eclipse-cycle-equivalence, blocking-diode-cycle-count-sizing, blocking-diode-thermal-plateau-dwell, blocking-diode-post-cycling-drift, blocking-diode-cycling-reject-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Blocking Diode Temperature Cycling (space-systems/ecss/e2008-blocking-diode-temperature-cycling)

Use when the task is the thermal stress of ECSS-E-ST-20-08C clause
12.6.5 -- a mission of eclipse cycles put onto blocking diode test
samples inside a chamber, in weeks rather than years. Two questions
decide the run: how many cycles the mission actually owes the samples,
and whether what the chamber ran was a cycle at all.

## Domain quick reference

- The cycle count is derived, not chosen. The eclipse rate the orbit
  produces, the years the array has to last and the declared test margin
  give a number, and that number is rounded up. Rounding down quietly
  shortens the mission the samples were asked to survive.
- A run that stopped short has not tested a mission. It closes as not
  evaluated rather than being sentenced on the cycles it did manage,
  because the cycles it skipped are where the fatigue would have shown.
- A cycle is four things, not two temperatures: a hot plateau, a cold
  plateau, a dwell long enough at each for the whole diode stack to
  reach them, and a transition slow enough that the sample sees a cycle
  rather than a shock. Miss any one and the count is of something else.
- Amplitude is the stressor. Two plateaus that both drift inward leave a
  profile that still has the right shape and a fraction of the strain
  energy per cycle.
- A sample is sentenced on movement, not on an absolute reading. Forward
  voltage and reverse leakage are each compared against where that same
  sample started, so a part that began slightly off is not penalised for
  its starting point.
- A crack is a different event from a drift. A part that came apart
  fails the lot outright rather than being diluted into a reject
  fraction, because a fraction describes a spread and a crack describes
  a joint that stopped existing.
- The reject fraction is the last gate, not the first. It means nothing
  until the mission-equivalent count was delivered under a profile that
  was really a cycle.

## Workflow

1. Validate the profile and acceptance policy first: hot and cold
   plateau floors, minimum amplitude, plateau dwell, ramp ceiling, test
   margin floor, drift cap and reject cap. A minimum amplitude wider
   than the declared plateaus span is refused rather than used.
2. Size the requirement from the mission -- eclipse rate times design
   life times test margin -- and round it up. A margin below the policy
   floor is refused, because it would test less mission than the array
   flies.
3. Compare the cycles applied against that requirement. Anything short
   closes the run as not evaluated, whatever the samples read.
4. Derive the amplitude from the plateaus and the ramp rate from the
   amplitude and the transition time, then check plateaus, amplitude,
   dwell and ramp against their bounds. A value landing exactly on a
   bound passes; the comparison tolerance absorbs representation error
   and the bound itself does not move.
5. Take each sample's forward-voltage and reverse-leakage drift relative
   to its own starting reading, and group the sample as within drift,
   drift exceeded or cracked. Keep the per-parameter detail beside the
   grouping.
6. Count the rejects, take the fraction against the cap, and close on
   one verdict: cycling not evaluated, profile deficient, samples
   failed, or samples passed. Report every finding, not the first.

## Pitfalls

- Running a familiar round number of cycles. A thousand cycles is a
  number, not a mission; the orbit and the design life decide, and the
  round number is right only by accident.
- Rounding the derived count down to something the chamber schedule
  liked. The fraction dropped is real mission the samples never saw.
- Sentencing a run that stopped early. The samples that survived nine
  tenths of the requirement have a reading; what they do not have is the
  last tenth, which is where thermal fatigue usually arrives.
- Treating dwell as dead time and trimming it. A plateau the stack never
  reached is a plateau in the log only, and the cycle count then counts
  excursions rather than cycles.
- Ramping as fast as the chamber allows. Past the ramp ceiling the
  sample is being shock tested, which is a real test of a different
  thing and reads in the record like this one.
- Judging drift against a catalogue value instead of the sample's own
  pre-test reading. A part that started a little high is then rejected
  for its starting point, and a part that started low hides real
  movement.
- Diluting a cracked sample into the reject fraction. One cracked part
  in twenty is inside any sane fraction and outside any sane lot.
- Comparing a ramp rate, a drift or a reject fraction against its bound
  by bare arithmetic. All three come out of divisions that land a few
  units in the last place either side of a limit on different hosts, so
  the comparison absorbs that error while the bound is never relaxed.

## Behavior contract (gate 3)

The policy validation, the mission-derived cycle count and its rounding,
the completeness check against that count, the amplitude and ramp-rate
derivations, the plateau, dwell and ramp bounds, the per-parameter drift
grouping, the crack override, the reject fraction and the run verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_temperature_cycling.py against
scripts/e2008_blocking_diode_temperature_cycling_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_temperature_cycling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
