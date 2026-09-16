---
name: e2008-blocking-diode-esd-sensitivity
description: "Use when an ESD-sensitive blocking diode is handled, transferred or stored. Assess whether the handling route and store carrying an electrostatic-discharge-sensitive blocking diode keep it under the voltage it survives, per ECSS-E-ST-20-08C clause 12.10.2: derive the sensitivity band from the withstand voltage and its discharge model, grade every station on protected-area status, obliged controls and arrival packaging, name the station of first exposure, measure the store against a two-sided humidity band whose floor is the ESD limit, and turn residual charge into delivered volts with the margin applied. Trigger: ecss, e-st-20-08c, clause-12-10-2, blocking-diode-esd-sensitivity-band, blocking-diode-esd-station-route-grading, blocking-diode-esd-transfer-packaging, blocking-diode-esd-storage-humidity-floor, blocking-diode-esd-residual-charge-voltage."
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
  tags: [ecss, e-st-20-08-blocking-diode-scope, e2008-blocking-diode-esd-sensitivity, e-st-20-08c-clause-12-10-2, blocking-diode-esd-sensitivity-band, blocking-diode-esd-station-route-grading, blocking-diode-esd-transfer-packaging, blocking-diode-esd-storage-humidity-floor, blocking-diode-esd-residual-charge-voltage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- ESD-Sensitive Handling and Storage (space-systems/ecss/e2008-blocking-diode-esd-sensitivity)

Use when the task is clause 12.10.2 of ECSS-E-ST-20-08C: a blocking diode
has been found sensitive to electrostatic discharge, and whether the way
it was handled, transferred and stored actually kept the voltage it could
see below the voltage it is known to survive.

## Domain quick reference

- A sensitive part is not protected by the best bench it ever sat on. It
  travels a route -- goods-in, kitting, the test bench, staking, the store
  -- and the voltage it can see is set by the worst place it passed
  through, not by the average of them. So the route is graded, and the
  station where the part was first exposed is named: every station after
  that one inherited a part that had already seen a field.
- Sensitivity is derived, not declared, and it is derived against a named
  discharge model. The same withstand voltage places a part in a different
  band under a human body model than under a machine model, so a number
  quoted without its model places nothing at all.
- A withstand voltage sitting exactly on a band limit belongs to the less
  sensitive band, and the comparison absorbs representation error rather
  than moving the limit.
- Each station is graded on three things, not one. Whether it is a
  designated protected area at all is the coarsest. Whether each obliged
  control is present, inside its own measured band and verified recently
  enough for that measurement to still stand is the middle. Presence is
  the weakest third: a ground path measured outside its band is not a
  ground path, and a wrist strap measured in band eleven months ago is not
  a verified wrist strap.
- The third thing is the one a station-by-station audit routinely drops:
  the packaging the part travelled in to REACH that station. A shielded
  bench reached by an unshielded walk is a part that was already stressed
  before it arrived, and the bench will measure perfectly.
- Shielding and dissipative are different claims, not two grades of one
  claim. A dissipative bag bleeds charge off its own surface; it does not
  keep an external field off the part inside, so the two sensitive bands
  oblige shielding outright.
- The obliged set grows with sensitivity, and a discrete diode owes a
  control a bonded article does not: its leads are shorted together, so
  they stop being an antenna for a field the package would otherwise never
  see. That control is itself graded in a band -- a shorting clip
  measuring kilohms is not a short.
- Four compliant stations out of five is not a compliant route, and four
  passes out of five obliged controls is not a compliant station. A
  control nobody offered is graded absent rather than skipped, or a
  station that owes five and reports four reads as green.
- The storage envelope is two-sided on both axes, and the humidity FLOOR
  is the one an ESD regime exists for. A store that is too humid is a
  corrosion problem; a store that is too dry is the ESD problem, because
  dry air is what lets ordinary handling build the charge everything else
  is there to bleed away. A ceiling without a floor is half a check. Shelf
  life already spent is graded alongside it.
- Residual charge measured on the part is not the finding. The finding is
  the voltage that charge delivers across the package capacitance, and a
  smaller package turns the same charge into more volts. That voltage is
  taken against the withstand voltage with the declared margin applied, so
  a part that clears the limit only on the nose is still reported.

## Workflow

1. Derive the sensitivity band from the withstand voltage and the
   discharge model it was measured with, validating that the threshold
   table names every model and rises.
2. Resolve which controls, which minimum arrival packaging and whether a
   designated protected area that band obliges.
3. Walk the route in order. For each station, grade the protected-area
   status, grade each obliged control on presence, on its own measured
   band and on the age of the measurement against its verification
   interval, and grade the packaging the part arrived in.
4. Grade any control that was never offered as absent rather than skipping
   it, and report separately any offered control the band does not oblige.
5. Take the route verdict as the conjunction and name the first deficient
   station as the point of first exposure, alongside the compliant station
   count so one weak link is visible rather than a bare rejection.
6. Measure the store against two-sided temperature and humidity bands,
   naming which side a reading fell out of, and grade the shelf life
   already spent against the declared life.
7. Convert the residual charge and the package capacitance into the
   voltage the charge delivers, apply the declared margin factor, and
   compare with the withstand voltage under a named tolerance.
8. Report every arm's findings together and call the regime compliant only
   when the finding list is empty.

## Pitfalls

- Grading the bench and calling it the regime. The part saw every station
  on its route, and the weakest one set the voltage it could reach.
- Ignoring how the part got there. Transfer packaging is the arm a
  station-by-station audit drops, and an unshielded walk between two
  perfect benches is exactly the exposure nobody logs.
- Quoting a withstand voltage without its discharge model. The number on
  its own places the part in no band, and the model it came from is what
  makes the band mean anything.
- Grading a control as present and stopping. Presence is a third of the
  question; the measured value and the age of that measurement are the
  other two thirds, and staleness is the one routinely dropped.
- Treating the verification interval as paperwork. A ground path verified
  outside its interval is an unverified ground path today, whatever it
  measured last year.
- Skipping a control nobody offered. An obliged control absent from the
  record is a deficiency, not an omission from the report, and a set that
  grades four of five has graded four.
- Accepting a dissipative bag as shielding. Bleeding surface charge and
  excluding an external field are different jobs, and only one of them is
  what a sensitive part in a stores rack needs.
- Putting a ceiling on humidity and no floor. The dry end is the ESD end;
  a one-sided humidity limit passes exactly the store most likely to
  charge the part during handling.
- Reporting residual charge as the finding. Charge is not a stress; the
  voltage it delivers across the package capacitance is, and a small
  package turns a small charge into a large voltage.
- Dropping the margin factor to make a part clear. A part that clears its
  withstand voltage only without the declared margin has not cleared it.
- Moving a band limit to pass a reading that sits exactly on it. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the declared band stays as declared.

## Behavior contract (gate 3)

The discharge model set and the rising withstand-voltage threshold table
with its project override, the band derivation with an exact limit falling
to the less sensitive band, the per-band obliged control set including
lead shorting, the three-way control grading on presence, own band and
verification age with absent controls graded rather than skipped, the
per-station protected-area and arrival-packaging grading against the
minimum the band obliges, the route conjunction with its first-exposure
station named, the two-sided temperature and humidity bands with the
humidity floor named and shelf life graded alongside, the
charge-to-voltage conversion and its margin-applied comparison under a
named tolerance, and the conjunctive regime verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_blocking_diode_esd_sensitivity.py against
scripts/e2008_blocking_diode_esd_sensitivity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_esd_sensitivity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
