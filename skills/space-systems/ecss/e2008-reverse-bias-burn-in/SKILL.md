---
name: e2008-reverse-bias-burn-in
description: "Assess whether a reverse bias burn-in under ECSS-E-ST-20-08C clause 12.6.7.3.1 is the high temperature blocking soak the clause describes or a differently stressed run wearing its name: confirm the cathode is held positive with respect to the anode, size the applied blocking voltage against the rating, derive the junction temperature the leakage self-heating produces, hold the soak inside its window up to the forty-eight hour ceiling, and separate devices whose leakage drifted past the drift limit from a lot whose drift share condemns the build. Use when planning or reviewing a diode reverse bias soak before the lot is accepted. Trigger: ecss, e-st-20-08c-clause-12-6-7-3-1, reverse-bias-burn-in-cathode-positive, reverse-bias-burn-in-forty-eight-hour-ceiling, reverse-bias-burn-in-voltage-ratio, reverse-bias-burn-in-leakage-drift, reverse-bias-burn-in-junction-temperature."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reverse-bias-burn-in, reverse-bias-burn-in-cathode-positive, reverse-bias-burn-in-forty-eight-hour-ceiling, reverse-bias-burn-in-voltage-ratio, reverse-bias-burn-in-leakage-drift, reverse-bias-burn-in-junction-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reverse Bias Burn-in (space-systems/ecss/e2008-reverse-bias-burn-in)

Use when the task is to plan or defend a reverse bias soak on a diode lot
under ECSS-E-ST-20-08C clause 12.6.7.3.1 -- held which way round, how
hard, how hot, for how long, and what the leakage afterwards says.

## Domain quick reference

- The soak holds the junction blocking, not conducting: the cathode is
  positive with respect to the anode for the whole run. Reverse that
  connection and the devices get a forward soak with a reverse bias
  label on it, stressing a different mechanism entirely.
- This screen is bounded above, and that is what separates it from a
  forward burn-in. A forward soak is sized by a floor -- run it long
  enough. A reverse bias soak carries a ceiling: no more than forty-eight
  hours.
- The ceiling is not administrative. The stress is the blocking field
  across the junction plus the temperature, and nothing about the run
  self-limits, so a soak left going degrades the passivation it was
  meant to interrogate and the lot arrives worse than it started.
- The applied blocking voltage is judged as a share of the rating.
  Screening wants a high share; a share reaching the rating is a
  breakdown test, and the devices that fail it were not defective.
- A blocking junction is not a cold one. Reverse leakage across a large
  blocking voltage still dissipates power, and at a high case
  temperature that self-heating is what carries the junction past its
  limit.
- The soak has to be hot to work at all. Below the case temperature
  floor the leakage mechanisms the screen depends on are not activated
  and the run is a long wait.
- Leakage drift is the reading that matters. A junction with a
  passivation flaw or an ionic contaminant leaks further after the soak
  than before it, and the ratio of the two readings is the screen.
- Removing drifted devices is the exercise working. A lot that sheds
  more than a small share is a different finding: the build is in
  question, and the survivors do not inherit a clean sheet from it.

## Workflow

1. Validate the soak policy first: soak window, voltage-ratio limit,
   case temperature floor, junction ceiling, drift limit and lot reject
   limit. A ratio limit reaching the rating is refused rather than used,
   because it would make a breakdown test pass as a burn-in.
2. Take polarity before anything else and stop there if it is wrong. A
   forward or unbiased connection makes every later quantity a
   description of a run that was not this run.
3. Derive the blocking voltage from the terminal difference and size it
   against the rating.
4. Derive the leakage dissipation and the junction temperature it
   produces on top of the case temperature, and compare both the
   junction and the voltage share against their limits.
5. Check the case temperature against its floor separately: a soak can be
   correctly biased and simply too cool to screen anything.
6. Hold the duration inside the window, both ends. A run landing exactly
   on the forty-eight hour ceiling is accepted; the comparison tolerance
   absorbs representation error and the limit does not move.
7. Take the leakage readings last: name every device past the drift
   limit, then compare the removed share against the lot reject limit.
8. Close on one verdict -- soak not applied, polarity wrong,
   overstressed, temperature low, duration out of window, lot rejected,
   or soak complete -- reporting every inadequacy found, not only the
   first.

## Pitfalls

- Assuming the bench wired it the way the procedure says. Polarity is a
  measurement, not an assumption, and a swapped pair produces a
  plausible-looking log of the wrong test.
- Treating the forty-eight hours as a target to reach rather than a
  ceiling not to cross. Longer is not safer here; longer is damage.
- Turning the blocking voltage up towards the rating to buy margin. Past
  the share limit the run measures breakdown, and the devices it removes
  were not the defective ones.
- Calling a blocking junction thermally quiet. Leakage times a large
  blocking voltage is real dissipation, and it lands on a junction
  already sitting at a high case temperature.
- Reading a single post-soak leakage value. The screen is the ratio
  against that same device before the soak; an absolute reading alone
  cannot tell a leaky-by-design part from a part that moved.
- Letting the survivors inherit the lot conclusion. A lot beyond the
  reject limit is a lot finding, and screening the rest of it does not
  answer it.

## Behavior contract (gate 3)

The policy validation, the bias polarity and blocking voltage, the
voltage ratio against the rating, the leakage dissipation and junction
temperature, the soak window check at both ends, the per-device leakage
drift ratio, the drifted-device list and lot drift share, and the soak
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_reverse_bias_burn_in.py against
scripts/e2008_reverse_bias_burn_in_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_reverse_bias_burn_in.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
