---
name: e2008-ultraviolet-exposure-test-process
description: "Use when a dosimetry record behind an ultraviolet exposure is being written or reviewed. Determine whether an accelerated ultraviolet exposure actually measured the integrated ultraviolet photon intensity at the test item position, per ECSS-E-ST-20-08C clause 6.4.3.15.2: integrate the spectral irradiance over the reported band with interpolated edges, convert those watts into a photon rate, refer the sensor reading to the item plane through the inverse-square distance ratio and the plane tilt, accumulate dose and equivalent sun hours, then screen beam uniformity, calibration currency and sampling cadence. Trigger: ecss, e-st-20-08c-clause-6-4-3-15-2, ultraviolet-photon-intensity-measurement, test-item-plane-ultraviolet-radiometry, ultraviolet-spectral-band-integration, ultraviolet-beam-non-uniformity, ultraviolet-radiometer-calibration-validity."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-ultraviolet-exposure-test-process, ultraviolet-photon-intensity-measurement, test-item-plane-ultraviolet-radiometry, ultraviolet-spectral-band-integration, ultraviolet-beam-non-uniformity, ultraviolet-radiometer-calibration-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Ultraviolet Intensity Measurement Process (space-systems/ecss/e2008-ultraviolet-exposure-test-process)

Use when the task is clause 6.4.3.15.2 of ECSS-E-ST-20-08C -- measuring
the integrated ultraviolet photon intensity at the position the test
item occupies, while the exposure is running. The article never reports
the dose it received; the radiometry does, and an exposure whose
dosimetry cannot be defended has qualified nothing however long it ran.

## Domain quick reference

- Photon intensity is not irradiance. A watt of 400 nm light carries
  twice the photons of a watt at 200 nm, and it is photons that break
  bonds, so the band integral is carried in both currencies: watts per
  square metre for the dose bookkeeping and photons per square metre per
  second for the quantity the clause names.
- The band is part of the measurement, not a label on it. Spectral
  irradiance is integrated between the declared edges, and the edges are
  interpolated inside the sampled spectrum rather than snapped out to
  the nearest sample -- a ramp integrated over a span wider than the
  band can report double the intensity that is really there.
- Position is the other half of the clause. Irradiance falls with the
  square of the distance from the lamp and with the cosine of the angle
  between the beam and the item plane normal, so a sensor at a chamber
  port reads a different exposure from the one the article receives, and
  its reading has to be referred before it can be integrated.
- One reading stands for the whole article only while the beam is flat
  across it. The spread across the item plane, taken as the difference
  of the extremes over their sum, is what says whether a single number
  describes an edge cell as well as a centre cell.
- An integrated figure is an integral over time as well as wavelength.
  Lamp output drifts and lamps fail, so the exposure is sampled through
  the run; a figure built from a single reading at the start is an
  extrapolation with no error bar.
- Provenance closes it. A sensor whose calibration has lapsed reports a
  number with no traceable scale behind it, and no amount of downstream
  arithmetic recovers one.

## Workflow

1. Validate the dosimetry policy first: band edges, position and tilt
   allowances, uniformity allowance, calibration interval, sampling
   floor and the one-ultraviolet-sun irradiance. An inverted band or an
   edge-on tilt allowance is refused rather than used.
2. Validate the recorded spectrum: at least two samples, strictly
   increasing wavelengths, no negative spectral irradiance, and a span
   that covers the reported band. A spectrum short of the band stops the
   judgement instead of being extrapolated.
3. Integrate the spectral irradiance across the band by the trapezoidal
   rule over the sampled bins, with the band edges interpolated into the
   sample list first.
4. Integrate the same band as a photon rate, weighting each bin by
   wavelength over the product of the Planck constant and the speed of
   light. This is the quantity the clause asks to be measured.
5. Refer both integrals to the test item plane through the square of the
   sensor-to-item distance ratio and the cosine of the plane tilt, and
   record the correction factor alongside the corrected values so the
   referral is visible rather than buried.
6. Accumulate over the exposure: dose in joules per square metre, photon
   fluence in photons per square metre, and the same dose expressed in
   equivalent ultraviolet sun hours for comparison with the mission.
7. Screen the record: sensor within the position and tilt allowances,
   beam uniformity inside its allowance, calibration inside its
   interval, sample count at or above the floor. Close with one verdict
   -- intensity not measured, record deficient, or record traceable --
   listing every deficiency, not only the first.

## Pitfalls

- Quoting a broadband radiometer reading as the band intensity. The
  detector passband and the reported band are different things, and the
  difference is a multiplicative error that repeats on every run.
- Snapping the band edges to the nearest spectral sample. The error is
  silent, it scales with how coarse the spectrum is, and it always
  points the same way for a spectrum that is rising across the edge.
- Leaving the sensor where the chamber has a port. The inverse square
  over a few hundred millimetres is a large factor, and a reading that
  was never referred to the item plane understates or overstates the
  whole campaign.
- Converting watts to photons with a single mean wavelength. The photon
  weighting is linear in wavelength across a band that spans a factor of
  two, so a mean-wavelength shortcut biases the count.
- Taking one reading at the start of the run. The integrated figure is
  an integral over time; a lamp that drifted or failed halfway through
  leaves no trace in a single sample.
- Comparing a uniformity or a sample count against its limit by bare
  arithmetic. Both come out of derived quantities that can land a few
  units in the last place either side of a bound, so the comparison
  absorbs that error while the bound itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, spectrum validation, band integration with
interpolated edges, the photon-rate integral, the inverse-square and
cosine referral to the item plane, the accumulated dose, photon fluence
and equivalent sun hours, the uniformity, calibration and sampling
screens and the measurement verdict are exercised by the gate 3 contract
test: scripts/test_e2008_ultraviolet_exposure_test_process.py against
scripts/e2008_ultraviolet_exposure_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_ultraviolet_exposure_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
