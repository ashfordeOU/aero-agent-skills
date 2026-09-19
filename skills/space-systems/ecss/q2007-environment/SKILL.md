---
name: q2007-environment
description: "Evaluate test-centre infrastructure suitability and work-environment control, ECSS-Q-ST-20-07C clauses 5.5.1-5.5.2. Use when a facility has to show it can hold the environment a test asks for and then that it did: check the declared capability band contains the required band for temperature, humidity, supply voltage and frequency, purge media and coolant, report the containment margin at each end, derive power-quality bands from nominal plus percentage tolerance, count monitored excursions with side and magnitude, time the longest unbroken one, and flag sampling too slow to see it. Trigger: ecss, q-st-20-07-test-centre, q2007-environment, test-facility-capability-band-containment, test-centre-environmental-excursion, power-quality-tolerance-band, environmental-monitoring-interval-adequacy, test-centre-media-purity-control."
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
  tags: [ecss, q-st-20-07-test-centre, q2007-environment, test-facility-capability-band-containment, test-centre-environmental-excursion, power-quality-tolerance-band, environmental-monitoring-interval-adequacy, test-centre-media-purity-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Infrastructure and Work Environment (space-systems/ecss/q2007-environment)

Use when the task is the facility step of ECSS-Q-ST-20-07C clauses 5.5.1 and
5.5.2 -- showing that the buildings, services and media a test centre offers
are suitable for the tests booked into them, and that the environment was
actually held inside its band while the test ran.

## Domain quick reference

- Suitability and control are two questions, not one. Suitability asks
  whether the facility can hold the environment at all; control asks whether
  it did. A centre can be perfectly suitable and still have lost the band
  for six minutes at 02:00, and a single pass/fail hides exactly that.
- Suitability is band containment. The facility declares a capability band
  per parameter, the test declares a required band, and the capability has
  to cover the requirement at both ends. The amount by which it does is the
  containment margin, and the margin is the operator's room before the
  facility is running against its own limit.
- A facility whose capability exactly equals the requirement is suitable and
  has zero margin. Those are different statements. Report both, because the
  second is what predicts the excursion.
- The margin is reported at each end separately. A capability that is
  generous at the top and short at the bottom is a real and common case --
  a chamber that can go hot more easily than cold -- and one aggregate
  number hides which end to fix.
- Power quality arrives as a nominal value plus a tolerance in percent, not
  as a band, so the band is derived: a 230 V supply held to 10 percent is
  compared as 207 V to 253 V. Derive it once and compare against the derived
  limits; comparing a reading against "230 V plus or minus 10 percent" in
  prose is how two engineers reach two answers.
- Media -- a purge gas dew point, a chilled-water temperature, a cleanroom
  overpressure -- are ordinary parameters with their own bands. The failure
  mode is identical: drifting out of band with nobody watching.
- Monitoring cadence is graded on its own. A parameter sampled every fifteen
  minutes against a ten-minute requirement can hold a clean record through
  an excursion nobody saw, so a slow interval is a finding even when every
  recorded reading is inside the band.
- Excursions carry a side and a magnitude, and the longest unbroken run
  carries a duration. A brief touch of the limit and a half-hour outside it
  are not the same event and should not aggregate into one count.
- Every band comparison carries a small relative slack, so a reading landing
  exactly on a derived limit reads as inside on any platform. The slack
  absorbs representation error in a multiplied limit; it does not loosen
  the requirement.

## Workflow

1. List the parameters in scope. For each, state the required band the test
   asks for and the capability band the facility declares. Derive a band
   from nominal plus tolerance for anything specified that way.
2. Refuse the specification when a parameter name is unrecognised, a band is
   not a two-limit pair, a limit is not numeric, a lower limit sits above
   its upper limit, or a parameter appears twice.
3. Test containment per parameter and record the margin at each end. A
   negative margin at either end is the suitability finding, and the end is
   named.
4. Walk the monitored series against the required band. Record each
   excursion with its index, side and magnitude; take the worst band
   utilisation across the series as the single control figure.
5. Multiply the longest unbroken run of out-of-band readings by the sample
   interval to get the excursion duration.
6. Compare the sample interval against the required interval and flag a slow
   cadence separately from any excursion it might have hidden.
7. Roll the facility up into two independent verdicts: suitable, and
   controlled. Report the parameters failing each.

## Pitfalls

- Collapsing suitability and control into one verdict. The remedies are
  different -- one is a facility change, the other is an operations change.
- Reading a zero containment margin as a comfortable pass. It is the
  narrowest possible pass and it predicts the first excursion.
- Comparing a reading against a percentage tolerance in prose instead of
  against the derived absolute limits.
- Counting excursions and never timing them, so a single touch of the limit
  and a sustained half-hour outside it look alike in the report.
- Accepting a clean record from a parameter sampled too slowly to see an
  excursion. The clean record is evidence about the sampling, not the
  environment.
- Using a strict comparison against a limit that was produced by a
  multiplication. The limit is not exactly representable and the same series
  then passes on one machine and fails on another.

## Behavior contract (gate 3)

The band validation, tolerance-derived bands, containment and margin
arithmetic, excursion detection with side and magnitude, longest-excursion
timing, monitoring-cadence check and the two-verdict facility roll-up are
exercised by the gate 3 contract test: scripts/test_q2007_environment.py
against scripts/q2007_environment_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_environment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
