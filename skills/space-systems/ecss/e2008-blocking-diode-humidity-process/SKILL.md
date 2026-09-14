---
name: e2008-blocking-diode-humidity-process
description: "Verify how a lot of solar array blocking diodes is sealed into an ambient pressure chamber for its humidity exposure under ECSS-E-ST-20-08C clause 12.6.4.1.2: derive the closure leak rate from a pressure decay hold and read it again as chamber volumes exchanged per day, hold the closed volume inside its ambient pressure band, reconcile the devices actually sealed in against the declared lot, check the free volume left around the fixture, and hold the seal proof dwell and the exposure duration. Use when a blocking diode humidity chamber closure is prepared or audited before the soak starts. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c-clause-12-6-4-1-2, blocking-diode-humidity-chamber-sealing, blocking-diode-chamber-seal-leak-rate, blocking-diode-lot-sealed-population, blocking-diode-chamber-free-volume, blocking-diode-humidity-exposure-duration."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c-clause-12-6-4-1-2, e2008-blocking-diode-humidity-process, blocking-diode-humidity-chamber-sealing, blocking-diode-chamber-seal-leak-rate, blocking-diode-lot-sealed-population, blocking-diode-chamber-free-volume, blocking-diode-humidity-exposure-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Humidity Chamber Sealing (space-systems/ecss/e2008-blocking-diode-humidity-process)

Use when the task is clause 12.6.4.1.2 of ECSS-E-ST-20-08C -- how a
blocking diode lot is actually closed into an ambient pressure chamber
before its humidity exposure runs. The purpose clause says why the
devices are stored damp; this one says how the volume around them is
shut, and the closure is the step usually written as a single word in a
procedure and then never evidenced.

## Domain quick reference

- A blocking diode sits in series with a whole string, so the thing
  going into the chamber is a lot rather than a coupon. A device left on
  the bench does not simply miss the exposure -- the lot result speaks
  for it anyway, and nothing downstream records that it was absent.
- The seal is a measurement, not a state. A pressure decay hold before
  the soak gives a drop over an elapsed time, and that ratio is the
  closure's leak rate.
- A raw leak rate in kilopascals per hour is hard to sentence, so it is
  taken again against the working pressure and expressed as chamber
  volumes exchanged per day. A volume that turns its air over daily is a
  room with a humidifier in it, and the setpoint inside it describes the
  laboratory rather than the test.
- The chamber runs inside a band around ambient. That is a positive
  requirement, not an absence of one: a closed volume that drifts out of
  the band drives moisture through a package seal by a route the ambient
  soak never exercises.
- Free volume around the fixture is part of the exposure. Packed to the
  walls, the damp air reaches the outside of the stack and merely warms
  the inside of it, and the pass belongs to the outer devices.
- The exposure clock is not the closure clock. The seal proof hold has
  to have run long enough for a decay reading to mean anything before
  the soak is allowed to start at all.

## Workflow

1. Validate the sealing policy first: leak allowance, exchange cap,
   ambient pressure band, sealed population floor, free volume floor,
   seal proof dwell and exposure duration. A band whose lower edge sits
   above its upper edge is refused rather than used.
2. Derive the leak rate from the decay hold, refusing a hold in which
   the chamber rose rather than fell -- that is an instrumentation
   result, not a leak. Then take the exchanges per day against the
   working pressure.
3. Reconcile the devices sealed in against the lot the plan declared,
   refusing a sealed count larger than the lot itself.
4. Derive the free volume the fixture and the devices leave, refusing a
   load that does not fit the chamber.
5. Check the leak against both its forms, the population against its
   floor, the pressure against its band, and the free volume, proof
   dwell and exposure against theirs. A value landing exactly on a floor
   passes; the comparison tolerance absorbs representation error and the
   floor does not move.
6. Report every finding, not the first, and close on one verdict, the
   leak outranking the rest because it changes what the exposure is:
   seal leak excessive, sealed population incomplete, chamber enclosure
   deficient, or chamber sealing accepted.

## Pitfalls

- Recording the closure as done rather than as measured. "Chamber
  sealed" is a sentence; a decay hold is evidence, and only one of the
  two survives a review.
- Sentencing a leak in kilopascals per hour alone. The same drop means
  something different in a small chamber at low pressure than in a large
  one at ambient, which is why the exchange form exists.
- Reading a rising chamber as a very good seal. Pressure that climbs
  during a decay hold is a transducer, a thermal transient or an open
  supply line, and taking the negative drop as zero leak hides all
  three.
- Loading a convenient subset and letting the lot result stand for the
  rest. Blocking diodes are sentenced by lot, so an absent device is
  covered by a pass it never earned.
- Filling the chamber because the fixture fits. Fit is a geometry
  question; circulation is the test question, and a chamber packed to
  its walls conditions its outer row only.
- Letting the closed volume hold a small overpressure because the seal
  is easier that way. It is a different ingress mechanism through the
  package, and nothing downstream will say which one produced the drift.
- Starting the exposure clock at closure. Without the proof hold the
  leak figure rests on a few minutes of settling, and a chamber that
  passes on noise is a chamber that was never checked.
- Comparing a derived rate, share or fraction against its limit by bare
  arithmetic. All three come out of divisions that land a few units in
  the last place either side of a limit on different hosts, so the
  comparison absorbs that error while the limit itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, the decay leak rate and its daily exchange form,
the sealed population share against the declared lot, the chamber free
volume fraction, the ambient pressure band, the seal proof dwell and
exposure duration checks, the finding inventory and the closure verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_humidity_process.py against
scripts/e2008_blocking_diode_humidity_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_humidity_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
