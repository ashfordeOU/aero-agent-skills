---
name: e2008-coverglass-humidity-test-process
description: "Configure the way subgroup O coverglasses are held inside an ambient pressure chamber under ECSS-E-ST-20-08C clause 8.7.11.1.2: restrict the load to recorded subgroup members, stand every article on edge supports so both faces meet the vapour, size the rack pitch and the clearance the rack really leaves, bound the face area a holder masks, keep the glass above the chamber dew point so a soak never becomes condensation, and count only settled time toward the dwell. Use when a humidity soak fixture is being laid out, or an as-run holding arrangement has to be judged. Trigger: ecss, e-st-20-08c-clause-8-7-11-1-2, coverglass-subgroup-o-humidity-holding, ambient-pressure-humidity-chamber-fixture, coverglass-rack-slot-clearance, coverglass-face-masking-fraction, humidity-chamber-dew-point-margin, humidity-soak-dwell-accounting."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-humidity-test-process, coverglass-subgroup-o-humidity-holding, ambient-pressure-humidity-chamber-fixture, coverglass-rack-slot-clearance, coverglass-face-masking-fraction, humidity-chamber-dew-point-margin, humidity-soak-dwell-accounting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Humidity Test Process (space-systems/ecss/e2008-coverglass-humidity-test-process)

Use when the task is clause 8.7.11.1.2 of ECSS-E-ST-20-08C -- the
holding arrangement itself. The designated subgroup of coverglasses is
exposed to humid air in a chamber that stays at the pressure of the
room around it, and the clause's substance is how the articles are held
while that happens.

## Domain quick reference

- The chamber has no pressure lever. Air temperature, relative humidity
  and time are the whole exposure, and each of them reaches the
  coverglass only through the way the article is held.
- Population comes first. The soak is run on the coverglasses of the
  designated subgroup, and an article whose subgroup is not recorded is
  not a member -- unknown membership is not membership, and it cannot
  be read as non-membership either.
- A humidity soak is a surface exposure. A coverglass lying on a tray
  has shelved the face it rests on, and what reaches that face is
  whatever diffused into the gap the tray left, which is not the
  chamber condition. Articles therefore stand on edge supports.
- What the holder touches is masked, and a masked area is an unexposed
  area being reported as an exposed one. The masked fraction of a face
  is bounded rather than merely recorded.
- Rack pitch is the article thickness plus the clearance each face
  needs, and capacity is the usable length divided by that pitch,
  floored. A rack loaded past its capacity buys articles that touch.
- Two articles in contact lose the contact patch on both of them at
  once, which is why contact is its own finding and not a clearance
  rounding error.
- Condensation is the failure the ambient pressure chamber invites. The
  dew point of the chamber air is fixed by its temperature and
  humidity, and an article that sits below it is under liquid water,
  not humid air, which is a different exposure with a different result.
- The dwell is settled time at the set point. The ramp is elapsed time
  the articles spent in the chamber reaching a condition they were not
  yet at, and counting it turns a short soak into a compliant record.
- Holder material travels with the fixture: a holder that leaches or
  corrodes onto a coating contributes a contaminant the soak then
  drives into the surface.

## Workflow

1. Validate the holding policy first: subgroup minimum, face clearance,
   masked-fraction ceiling, dew point margin, humidity and temperature
   bands, the ambient pressure tolerance, the dwell minimum and the
   qualified holder materials. A humidity band reaching saturation is
   refused rather than used.
2. Split the inventory into subgroup members and non-members, refusing
   an article that records no subgroup at all, and stop on a population
   that is blank, empty or short of the sampling minimum.
3. Judge every member's holding before looking at the chamber: edge
   support, qualified holder material, masked face fraction, clearance
   to the neighbour and contact. Every defect is listed, on every
   article, not only the one that set the verdict.
4. Size the rack from the article thickness and the clearance, and take
   the realised clearance back out of the loaded length, so a rack that
   met the pitch on paper and was then overfilled is still caught.
5. Judge the chamber next: air temperature and humidity inside their
   bands, the gauge pressure within tolerance of the room in both
   directions, and the article surface a declared margin above the dew
   point those two imply.
6. Take the ramp back out of the elapsed chamber time and hold the
   settled remainder against the dwell minimum. A dwell landing exactly
   on the minimum is held; the comparison tolerance absorbs
   representation error and the minimum does not move.
7. Close on one verdict: population not established, holding not
   acceptable, chamber conditions invalid, exposure incomplete, or
   subgroup humidity exposure held.

## Pitfalls

- Laying the coverglasses flat because the rack was full. It converts a
  two-face exposure into a one-face exposure and the record does not
  say so; the support check is what catches it.
- Reading elapsed chamber time as dwell. A soak that took six hours to
  reach the set point delivered six hours less exposure than its log
  shows, and the shortfall is invisible without the ramp subtraction.
- Treating a near-saturation set point as the strongest test. The dew
  point closes on the air temperature as humidity rises, so the more
  aggressive set point is also the one most likely to put liquid water
  on the article and test something else.
- Accepting a holder because it is inert at room temperature. The
  fixture spends the soak at the chamber condition, which is the
  condition that mobilises what it leaches.
- Counting an article whose subgroup nobody wrote down. It is not a
  member, and it is not a proven non-member either; only the record
  settles it.
- Comparing a derived clearance or dwell against its limit by bare
  arithmetic. Both are differences of floats that can land a few units
  in the last place either side of a limit, so the comparison absorbs
  that error while the limit itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, subgroup population split, edge-support
recognition, holder material check, masked face fraction, clearance and
contact findings, rack pitch, capacity and realised clearance, the
Magnus dew point and its margin, the chamber band and ambient pressure
checks, the settled dwell accounting and the holding verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_humidity_test_process.py against
scripts/e2008_coverglass_humidity_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_humidity_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
