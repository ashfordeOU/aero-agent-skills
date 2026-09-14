---
name: e2008-ionising-irradiation-test-process
description: "Validate an ionising irradiation exposure of diodes run in a cobalt gamma field or, alternatively, an accelerator electron beam under ECSS-E-ST-20-08C clause 12.6.11.1.1: hold a third facility outside the process, refuse a run whose bias condition is unrecorded, check each segment rate against the window for the chosen facility and an accelerator beam energy against its own, accumulate dose segment by segment rather than off the wall clock, take the sample plane spread across its monitors, and hold the total against the target. Use when such an exposure is planned or read back. Trigger: ecss, e-st-20-08c-clause-12-6-11-1-1, diode-ionising-dose-exposure-run, cobalt-gamma-irradiation-facility, accelerator-electron-beam-irradiation, sample-plane-dose-uniformity-spread, accumulated-ionising-dose-against-target."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-ionising-irradiation-test-process, diode-ionising-dose-exposure-run, cobalt-gamma-irradiation-facility, accelerator-electron-beam-irradiation, sample-plane-dose-uniformity-spread, accumulated-ionising-dose-against-target]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Diodes -- Ionising Irradiation Test Process (space-systems/ecss/e2008-ionising-irradiation-test-process)

Use when the task is clause 12.6.11.1.1 of ECSS-E-ST-20-08C -- running
the ionising exposure of diode devices in a cobalt gamma field, or in an
accelerator electron beam as the alternative. Two facilities are
admitted and they are not run the same way. The gamma cell soaks the
whole sample volume in a broadly uniform photon field and delivers dose
slowly; the accelerator paints the sample plane, delivers the same dose
in a small fraction of the time, and carries a beam energy the gamma
cell does not have.

## Domain quick reference

- Facility comes first because it decides the rest. A facility that is
  neither of the two admitted is outside this process, and grading its
  run here produces a confident verdict about evidence the clause does
  not govern.
- Dose is accumulated, never read. A rate held for a duration, segment
  by segment, with beam-off gaps that deliver nothing. Summing the
  segments is the whole measurement.
- Which is why wall-clock length is not exposure time. A run reported by
  the hours it occupied the facility has counted every gap, every
  realignment and every dosimetry pause as dose.
- Rate is bounded on both sides and for different reasons. Run too slow,
  and the device anneals about as fast as it damages, so the endpoint
  understates what a mission profile would do. Run too fast, and the
  damage arrives faster than the lattice relaxes and the endpoint
  overstates it. Neither error shows in the total dose.
- The two windows are different windows. An accelerator rate is normal
  for an accelerator and far too fast for a gamma cell, so the window is
  resolved from the facility rather than declared once.
- Beam energy belongs to the accelerator alone, and it sets the depth
  the dose is deposited at. An accelerator run with no energy on record
  has not said where in the device the dose went.
- Uniformity decides what the total describes. A spread across the
  sample plane monitors means the devices at one end of the tray were
  given a different exposure from the devices at the other, and the
  average is a dose no individual device received.
- Bias during exposure is part of the exposure. An unbiased junction and
  a reverse-biased one accumulate charge differently in the same field,
  so a run with no bias condition on record cannot be compared with any
  other run however well its dose was measured.

## Workflow

1. Validate the exposure policy first: both rate windows, the beam
   energy window, the uniformity allowance and the dose tolerance. A
   window whose floor sits above its ceiling admits nothing and is
   refused rather than used.
2. Read the facility and close immediately when it is neither the gamma
   field nor the electron beam; label case is absorbed, the facility is
   not.
3. Read the bias condition the devices were held at and close when it is
   absent or is not one of the two recognised conditions.
4. Read the target dose and the beam-on segments, refusing a segment
   with no rate or no duration and a run with no segment at all.
5. Accumulate dose over the segments, take the beam-on hours, the
   dose-weighted mean rate and the hours a steady run at that rate would
   have needed to reach the target.
6. Resolve the rate window from the facility and grade every segment
   against it, naming each offending segment by its position so a long
   run is not repaired one pass at a time.
7. On an accelerator run only, grade the beam energy against its window
   and report an absent energy as a finding rather than a refusal.
8. Take the sample plane spread across its monitors as a share of their
   mean, refusing a single monitor, and hold it against the allowance.
9. Hold the accumulated dose against the target within the declared
   tolerance, with a comparison that absorbs representation error, and
   close on one verdict: facility not admitted, bias condition not
   stated, beam conditions invalid, uniformity out of band, dose off
   target, or exposure accepted.

## Pitfalls

- Reporting the run by its calendar length. The gaps between segments
  delivered nothing, and counting them inflates the apparent exposure
  time while leaving the dose untouched.
- Carrying one rate window across both facilities. The accelerator rate
  that is normal for an accelerator is an order of magnitude past what
  a gamma cell should ever run at.
- Treating a low rate as conservative. A slow exposure lets the device
  anneal while it is being damaged, so the endpoint is optimistic and
  the dose on the certificate is still correct.
- Treating a high rate as efficient. The damage outruns the relaxation
  and the endpoint is pessimistic, which costs margin the design did
  not need to spend.
- Accepting an accelerator run with no beam energy. The energy sets the
  deposition depth, and without it the dose is a number with no place
  in the device attached to it.
- Averaging an uneven sample plane. A tray dose taken as a mean across
  a wide spread describes no device that was on the tray.
- Reading uniformity off one monitor. One monitor measures a point; the
  spread is a property of the plane and needs at least two.
- Leaving the bias condition to the rig. Charge accumulates differently
  under reverse bias than unbiased, so the same dose produces different
  devices and the record cannot say which was produced.
- Comparing a rate, a spread or a dose against its bound by bare
  arithmetic. All three are quotients or products of declared numbers,
  so a run planned exactly to a bound can land in the last place the
  wrong side of it; the comparison absorbs that while the bound stays
  as written.

## Behavior contract (gate 3)

The policy validation with its window ordering, the two-facility
admission and label normalisation, the bias condition check, the segment
reading, the accumulated dose, beam-on hours, mean rate and nominal
exposure time, the facility-resolved rate window applied per segment,
the accelerator beam energy window, the sample plane spread against its
allowance, the accumulated dose against its target and the single run
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_ionising_irradiation_test_process.py against
scripts/e2008_ionising_irradiation_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_ionising_irradiation_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
