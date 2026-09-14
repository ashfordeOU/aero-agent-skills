---
name: e2008-coverglass-normal-emittance
description: "Compute the normal emittance of a solar-cell coverglass per ECSS-E-ST-20-08C clause 8.7.6 by the method the referenced thermal control standard fixes: hold the nominated instrument and the specimen temperature inside that standard's calibrated band, weight every measured spectral band by the blackbody exitance share it spans rather than by its width, close the unmeasured spectral coverage before any average is quoted, reduce an opaque reflectometer reading through Kirchhoff, and judge the figure against the drawing band and its uncertainty. Use when a coverglass emittance number is about to be quoted from a scan nobody checked for spectral coverage. Trigger: ecss, e-st-20-08c-clause-8-7-6, coverglass-normal-emittance-measurement, coverglass-thermal-control-reference-method, blackbody-band-weighted-emittance, coverglass-emittance-spectral-coverage, coverglass-emittance-drawing-band."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-normal-emittance, coverglass-normal-emittance-measurement, coverglass-thermal-control-reference-method, blackbody-band-weighted-emittance, coverglass-emittance-spectral-coverage, coverglass-emittance-drawing-band, solar-cell-assembly-radiative-balance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Normal Emittance (space-systems/ecss/e2008-coverglass-normal-emittance)

Use when the task is clause 8.7.6 of ECSS-E-ST-20-08C -- the normal
emittance of a coverglass, taken the way the referenced thermal control
standard fixes rather than the way the laboratory usually takes one.
The clause is a pointer, and a pointer is easy to nod at: the emittance
gets measured, a number gets written down, and nobody asks whether the
instrument and the article were inside the band the referenced method
actually covers, or what share of the emitted energy the scan reached.
The coverglass front face is the radiator of the whole solar cell
assembly, so this number sets the operating temperature the cell runs
at, and a number biased by a truncated scan biases the thermal model in
the same direction every time.

## Domain quick reference

- Normal emittance is a weighted average, not a spectrum. The weight is
  the blackbody spectral exitance at the specimen temperature, so a band
  is important in proportion to the energy the article emits there, not
  in proportion to how wide it looks on the wavelength axis.
- At around 293 K the exitance peaks near 10 um and the long tail runs
  out past 50 um. A scan that stops at 15 um has left a real share of
  the emitted energy unmeasured, and the average taken over what it did
  reach is an average over the instrument's reach.
- The exitance share of a band comes from the blackbody fractional
  function, a closed-form series in c2 / (lambda T). It needs no
  quadrature, so no step size chosen on one machine travels to another,
  and the share of two bands with the same lambda T product is the same
  share.
- Two reduction routes exist and they need different evidence. A
  spectrometer or an integrating-sphere reflectometer feeds a band
  average. A calorimetric rig or a portable emissometer returns one
  total figure and reduces through Kirchhoff, emittance being what an
  opaque specimen neither reflects nor transmits.
- A coverglass is not opaque everywhere. Where it transmits, the
  Kirchhoff reduction has to carry the transmitted share too, and a
  reflectance and transmittance that sum above unity mean the reading
  did not close rather than that the article emits a negative amount.
- The referenced method is calibrated over a temperature band. An
  instrument set up near ambient does not become a cryogenic instrument
  because the article was cold, and an emittance taken outside that band
  is outside the method the clause points at.

## Workflow

1. Take the nominated instrument and confirm the referenced method
   allows it. An instrument the method omits stops the run rather than
   being reduced by the nearest available route.
2. Place the specimen temperature inside the band the referenced method
   covers, and record the failure as a finding when it sits outside,
   because the reduction that follows is still arithmetically valid and
   will otherwise look clean.
3. Order the measured bands and refuse an overlapping pair. Overlap
   counts the same exitance share twice and pulls the average toward
   whichever band was duplicated.
4. Compute the exitance share of every band at the specimen temperature
   and sum them. Hold the total against the coverage floor before
   forming any average, since the coverage shortfall is the defect the
   average itself cannot show.
5. Reduce by the route the instrument feeds -- exitance-weighted band
   average, or Kirchhoff on a total reading with its transmitted share
   carried.
6. Place the reduced figure inside the band the coverglass drawing
   declares, hold the reported uncertainty against the required one, and
   close with a verdict that stays open while any finding stands.

## Pitfalls

- Averaging the band emittances arithmetically. Four bands are rarely
  four equal shares of the emitted energy, and a plain mean hands the
  long-wave tail the same authority as the region around the peak.
- Weighting by bandwidth instead of by exitance. A 25 um to 90 um band
  is the widest on the axis and one of the smallest in energy at room
  temperature, so bandwidth weighting inverts the ranking.
- Quoting an average from a truncated scan. The average is a real
  number computed from real data; nothing in it reveals that a fifth of
  the emitted energy was never looked at. Only the coverage sum does.
- Reducing a transmitting coverglass as though it were opaque. Dropping
  the transmitted share raises the derived emittance by exactly that
  share, in the direction that makes the article look better.
- Taking the emittance at whatever temperature the article happened to
  be at. The referenced method fixes a band; outside it the instrument
  calibration no longer applies and the figure is not the clause's.
- Comparing a coverage sum or a weighted average against a limit by
  bare arithmetic. Both are sums of series terms that can land a few
  units in the last place either side of a limit, so the comparison
  absorbs that error while the limit itself is never relaxed.
- Treating a drawing band as a single target value. The band has a
  floor as well as a ceiling, and an emittance above the ceiling is as
  much a departure from the declared article as one below the floor.

## Behavior contract (gate 3)

The accepted-instrument list, reduction routing, reference temperature
band, blackbody fractional function, band ordering and overlap refusal,
exitance-weighted average, spectral coverage floor, Kirchhoff reduction
with its transmitted share, drawing-band placement and uncertainty
comparison are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_normal_emittance.py against
scripts/e2008_coverglass_normal_emittance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_normal_emittance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
