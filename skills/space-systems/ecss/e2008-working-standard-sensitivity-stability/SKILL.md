---
name: e2008-working-standard-sensitivity-stability
description: "Use when repeat intercomparison readings must become a per-standard stability verdict. Determine whether a group of secondary working standards has drifted in sensitivity under ECSS-E-ST-20-08C clause 10.2.2.3.2: normalise every short-circuit-current reading to the reference temperature, require at least five standards read in each session, ratio each device against the session median so an unknown source level cancels out, track that ratio across sessions, derive total and per-year drift by least squares, and separate a common-mode shift of the whole group, which belongs to the source, from one device walking away from its peers. Trigger: ecss, e-st-20-08c, clause-10-2-2-3-2, working-standard-sensitivity-drift, five-standard-intercomparison, short-circuit-current-session-ratio, common-mode-source-shift."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-working-standard-sensitivity-stability, e-st-20-08c, clause-10-2-2-3-2, working-standard-sensitivity-drift, five-standard-intercomparison, short-circuit-current-session-ratio, common-mode-source-shift, photovoltaic-working-standard-drift-tracking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Working Standard Sensitivity Stability (space-systems/ecss/e2008-working-standard-sensitivity-stability)

Use when the task is clause 10.2.2.3.2 of ECSS-E-ST-20-08C: deciding
whether secondary working standards still have the sensitivity they were
calibrated with, from short-circuit-current readings taken across a group
of at least five of them on several occasions. This leaf reads the
campaign and returns a per-standard drift disposition plus the group
verdict.

## Domain quick reference

- A single standard cannot answer this question about itself. Read twice,
  it gives one number that moved, and nothing in that number says whether
  the device changed or the light did. The group is what supplies the
  reference.
- Five is the working minimum, and the reason is the median. A median of
  five or more devices does not move when one of them moves, so the
  device that drifted is measured against the four that did not.
- The median, not the mean. One device that has genuinely walked would
  drag a mean toward itself and hide a share of its own drift in the
  reference it is being compared with.
- Normalise before you compare. Short-circuit current rises with cell
  temperature, so a reading taken warm looks like a more sensitive
  device. Two sessions months apart are otherwise a comparison of
  thermometers.
- The ratio is the measurement. Dividing each normalised reading by the
  session median multiplies out whatever the source was doing that day,
  which is what makes an uncalibrated session usable at all.
- Three numbers come out of one ratio series and they answer different
  questions. Total change says where the device ended up. The
  least-squares slope over elapsed days, annualised, says how fast it is
  going and uses every session rather than only the two ends. The largest
  excursion says how far it ever went.
- A device can pass two of those and fail the third. One that wandered
  out and came back reads as perfectly stable first-to-last and is not
  stable; the excursion is what catches it.
- The ratio method has one blind spot and it has to be handled
  separately: if every device moved together, the ratios do not move,
  because they are ratios. Tracking the absolute group level is the only
  thing that sees it.
- A session in which the group does not agree with itself is a finding
  about the session, not yet about any device. It is flagged before any
  individual disposition is trusted.

## Workflow

1. Resolve the campaign: identifier, temperature coefficient and the
   sessions in strict time order. Reject a campaign with too few
   sessions to show a trend.
2. Normalise every reading to the reference temperature, rejecting a
   temperature factor that is not physical.
3. Per session, take the median of the normalised currents and ratio each
   device against it. Reject a session carrying fewer than the group
   minimum or the same device twice.
4. Flag any session whose ratios scatter past the allowance; that session
   is in question before its devices are.
5. Check the group membership is identical across sessions, so a ratio
   series belongs to one device throughout.
6. Per device, derive total drift, annualised least-squares drift and
   maximum excursion, and disposition each against its own band.
7. Compare the first and last group level. A shift of the whole group
   refers the campaign, because the ratios are blind to it.
8. Take the worst disposition, add the session and common-mode findings,
   and name the devices that are not stable.

## Pitfalls

- Judging one standard against its own calibration certificate and
  calling the difference drift. Without the group there is no way to tell
  the device from the source.
- Comparing raw currents from sessions at different temperatures. The
  temperature correction has to come first or the trend reported is the
  laboratory thermostat.
- Using the group mean as the reference. The device you are trying to
  measure is inside it, pulling the reference after itself.
- Running the comparison on three or four devices because five were not
  available. The median stops being robust and one drifting device moves
  the reference it is judged against.
- Judging drift from the first and last session only. A device that
  wandered out and came back passes that test, and a two-point comparison
  throws away every session in between.
- Reporting a stable group when every ratio is flat and the absolute
  level has moved. Ratios cannot see a shift they all share, which is
  exactly what a correlated drift of the whole group looks like.
- Dispositioning devices from a session the group itself disagreed in.
  Flag the session first; a bad source or a bad setup is not a property
  of the devices.
- Comparing a drift figure with its limit by bare arithmetic. Both sides
  come out of divisions and a least-squares sum, so a device sitting
  exactly on a limit can evaluate a few units in the last place above it;
  the comparison absorbs that representation error while the limit stays
  untouched.

## Behavior contract (gate 3)

The criteria validation including the five-device minimum, the
temperature normalisation and its non-physical-factor guard, the session
median and ratio construction, the session scatter flag, the
least-squares slope, the total, annualised and excursion drift metrics,
the per-device disposition bands, the group membership check, the
common-mode level shift and the group verdict are exercised by the gate 3
contract test:
scripts/test_e2008_working_standard_sensitivity_stability.py against
scripts/e2008_working_standard_sensitivity_stability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_working_standard_sensitivity_stability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
