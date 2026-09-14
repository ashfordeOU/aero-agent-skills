---
name: e2008-blocking-diode-contact-adherence
description: "Evaluate the contact adherence of planar blocking diodes and sentence the lot from it: size the sample the lot owes against its population, convert every pull reading into a stress over the bonded pad area so pads of different size are comparable, hold the pull angle and crosshead rate that make a reading a pull test, group each anode and cathode pad as adherent, below limit or lifted, sentence a device by its weakest pad, and refuse a verdict drawn from an undersized sample. Use when running or auditing a planar blocking diode contact adherence test. Trigger: ecss, e-st-20-08c-clause-12-6-6, planar-blocking-diode-contact-adherence, blocking-diode-pad-pull-stress, blocking-diode-adherence-sample-size, blocking-diode-contact-lift-off, blocking-diode-weakest-pad-sentence."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-blocking-diode-contact-adherence, planar-blocking-diode-contact-adherence, blocking-diode-pad-pull-stress, blocking-diode-adherence-sample-size, blocking-diode-contact-lift-off, blocking-diode-weakest-pad-sentence, blocking-diode-pull-fixture-conformance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Blocking Diode Contact Adherence (space-systems/ecss/e2008-blocking-diode-contact-adherence)

Use when the task is the durability check of ECSS-E-ST-20-08C clause
12.6.6 -- the contacts on a planar blocking diode pulled off their pads
to see whether they stay attached. The pull reading is the easy part.
What decides the result is how many devices were pulled, how the pull
was applied, and what the load is divided by before anyone compares it
to a limit.

## Domain quick reference

- A raw pull load is not portable between part numbers. A wider pad
  holds more newtons for exactly the same metallurgy, so the load is
  turned into a stress over the bonded pad area and the limit lives in
  those units.
- A planar device is pulled at both bonded pads, and it is sentenced by
  whichever one is weakest. A string does not care which pad let go, so
  the best pad and the average of the two are both the wrong answer.
- The sample is evidence, not paperwork. The lot owes a share of itself
  with a floor underneath it, and a lot smaller than the floor owes all
  of itself. Fewer devices than that closes the run as an insufficient
  sample rather than as an acceptance.
- A pull is a pull only near normal to the pad. Off angle it becomes a
  peel, which fails at a fraction of the load and puts a real number
  about a different experiment into the record.
- The crosshead rate is part of the definition too. Too slow and the
  joint creeps, too fast and it is shock loaded; either way the reading
  belongs to another test.
- A lifted pad is a different event from a low reading. It rejects the
  lot outright rather than being diluted into a reject fraction, because
  a fraction describes a spread of strengths and a lift-off describes a
  bond that was never made.
- The reject fraction is the last gate. It means nothing until the
  sample was the size the lot owed and the fixture was conforming.

## Workflow

1. Validate the sampling and pull policy first: adherence stress limit,
   lift-off threshold, sample fraction and floor, pull angle tolerance,
   crosshead rate band and reject cap. A lift-off threshold sitting at or
   above the adherence limit is refused rather than used.
2. Size the sample the lot owes -- its declared share, rounded up, held
   at the floor, and never more than the lot itself -- and compare it
   against the devices actually pulled. Anything short closes the run as
   an insufficient sample, whatever the readings say.
3. Take the pull angle deviation from normal and the crosshead rate, and
   check both against their bounds before any load is interpreted.
4. Divide each pad load by its bonded area to get a stress, then group
   the pad as adherent, below limit or lifted. A value landing exactly on
   a bound passes; the comparison tolerance absorbs representation error
   and the bound itself does not move.
5. Sentence each device by its weakest pad and keep the per-pad grouping
   and stress beside it.
6. Count the rejects, take the fraction against the cap, and close on one
   verdict: sample insufficient, fixture deficient, lot rejected, or lot
   accepted. Report every finding, not the first.

## Pitfalls

- Comparing raw newtons across part numbers. The device with the bigger
  pad wins every time, and the metallurgy that is actually weaker passes
  on geometry alone.
- Pulling whatever devices were convenient and calling it the sample. A
  lot sentenced from four devices has a number that describes four
  devices.
- Holding a small lot to the percentage instead of the floor. Ten
  percent of a lot of thirty is three devices, which is a gesture rather
  than evidence.
- Letting the fixture drift off normal because the part is awkward to
  grip. Past the angle tolerance the pad is being peeled, and a peel
  fails low, so the lot is rejected for the fixture's geometry.
- Speeding the crosshead to get through a sample before a shift ends.
  The joint is then shock loaded and the reading belongs to a different
  test.
- Sentencing a device on its better pad, or on the mean of the two. The
  weak pad is the one that opens the string.
- Folding a lift-off into the reject fraction. One pad in twenty that
  came away is inside any sane fraction and outside any sane lot.
- Comparing a stress or a reject fraction against its bound by bare
  arithmetic. Both come out of divisions that land a few units in the
  last place either side of a limit on different hosts, so the comparison
  absorbs that error while the bound is never relaxed.

## Behavior contract (gate 3)

The policy validation, the lot-sized sample requirement and its floor,
the pull angle and crosshead rate conformance, the load-to-stress
conversion, the per-pad grouping, the weakest-pad device sentence, the
lift-off override, the reject fraction and the run verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_blocking_diode_contact_adherence.py against
scripts/e2008_blocking_diode_contact_adherence_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_contact_adherence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
