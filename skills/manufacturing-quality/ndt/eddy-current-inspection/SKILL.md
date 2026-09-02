---
name: eddy-current-inspection
description: "Use when you must plan and execute an eddy current inspection (ET) of an aerospace part and turn probe impedance readings into defect findings: compute the standard depth of penetration from test frequency, electrical conductivity, and magnetic permeability; select the frequency that places a surface or subsurface flaw within the usable penetration band; convert percent IACS conductivity to siemens per meter; estimate the eddy current density ratio and the phase lag at the flaw depth; and interpret the impedance plane to separate lift-off, conductivity changes, and crack indications. Produces the depth of penetration, the selected test frequency, and the density and phase values that gate eddy current acceptance dispositions. Trigger: eddy current, eddy-current testing, depth of penetration, impedance plane, subsurface flaw, surface crack, lift-off, IACS conductivity, phase lag."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [eddy-current-inspection, eddy-current, depth-of-penetration, impedance-plane, standard-depth-of-penetration, subsurface-flaw, surface-crack, lift-off, phase-lag, iacs-conductivity, test-frequency, skin-effect, coil-impedance, flaw-depth]
  version: 0.1.0
  author: Aero Agent Skills
---

# Eddy Current Inspection (manufacturing-quality/ndt/eddy-current-inspection)

Use when the task is executing eddy current inspection (ET) on a part:
computing the standard depth of penetration from frequency,
conductivity, and permeability, selecting the test frequency that keeps
a surface or subsurface flaw within the usable penetration band, and
interpreting the probe response on the impedance plane.

## Domain quick reference

- Standard depth of penetration:
  delta = 1 / sqrt(pi * f * mu * sigma), with frequency f in Hz, mu =
  mu0 * mu_r in H/m (mu0 = 4 * pi * 1e-7), and conductivity sigma in
  S/m; delta is in meters. At one standard depth of penetration the
  eddy current density falls to 1/e, about 37 percent of its surface
  value. Higher frequency, higher conductivity, and higher permeability
  all shrink delta.
- Percent IACS to conductivity: 100 percent IACS equals the annealed
  copper reference of 5.8e7 S/m, so sigma = (percent / 100) * 5.8e7.
  Aluminum alloys sit near 30 percent IACS (1.74e7 S/m) and titanium
  alloys near 5 percent IACS.
- Frequency selection: choose the frequency so the flaw depth sits
  within one standard depth of penetration, where the current density
  is still strong. For a subsurface flaw at depth d, use a frequency
  whose delta is at least 1 to 2 times d (factor 2.0 is common), which
  keeps the current density at the flaw above 37 percent. For a surface
  crack use a smaller delta (factor below 1.0), concentrating the
  current near the surface for sharp response.
- Eddy current density ratio: J / J0 = exp(-depth / delta). At one
  delta the ratio is 0.368, at two deltas it is 0.135.
- Phase lag: the eddy current lags the surface current by depth / delta
  radians, so phase_lag_degrees = (depth / delta) * 180 / pi. At one
  standard depth of penetration the lag is one radian, about 57.3
  degrees.
- Impedance plane: the probe coil response plots normalized reactance
  against normalized resistance. Lift-off moves the point along the
  lift-off trajectory, a conductivity change moves it along a curve
  toward the material point, and a crack rotates the trajectory with a
  characteristic phase angle. Reading which trajectory the point follows
  separates the indications.
- Skin effect: eddy currents concentrate at the surface and decay
  exponentially with depth; the standard depth of penetration is the
  characteristic length of that decay.
- Acceptance: indications are compared with reference standards and the
  engineering specification, recorded, and dispositioned under
  special-process control by NAS 410 qualified personnel.

## Workflow

1. Establish the material: its electrical conductivity in S/m (convert
   from percent IACS with conductivity_from_iacs) and its relative
   magnetic permeability (1.0 for aluminum, titanium, and austenitic
   steels; above 1 for ferromagnetic materials).
2. Pick the inspection frequency: for a subsurface flaw compute
   select_frequency_for_flaw with a penetration factor of 2.0 or more;
   for a surface crack use a factor below 1.0.
3. Compute the standard depth of penetration with
   standard_depth_of_penetration and confirm the flaw depth sits within
   one delta, or compute the frequency for a given depth directly with
   frequency_for_depth.
4. Estimate the current density at the flaw depth with
   eddy_current_density_ratio and the phase lag with
   phase_lag_degrees; both support the impedance-plane reading.
5. Interpret the probe response on the impedance plane: identify the
   lift-off trajectory, the conductivity trajectory, and the crack
   trajectory, and separate the crack indication from lift-off and
   conductivity drift.
6. Compare the indication with the acceptance criteria in the
   engineering specification, record the results, and disposition the
   part.

## Pitfalls

- Forgetting the mu0 factor: mu in the depth of penetration formula is
  mu0 * mu_r, not mu_r; skipping mu0 (4 * pi * 1e-7) makes delta come
  out far too small.
- Using percent IACS directly as S/m: 30 percent IACS is 1.74e7 S/m,
  not 30 S/m; always convert with the 5.8e7 reference.
- Choosing a frequency that buries the flaw: a subsurface flaw beyond
  one delta sees a density ratio below 0.37 and may be missed; lower
  the frequency or raise the penetration factor.
- Using one frequency for surface and subsurface flaws: the same setup
  cannot serve both; surface cracks need a small delta, subsurface
  flaws need delta at least 1 to 2 times the flaw depth.
- Reading lift-off as a crack: on the impedance plane lift-off follows
  its own trajectory and is a routine part of the scan, not a defect;
  separate the trajectories before dispositioning.
- Ignoring permeability: a ferromagnetic part with mu_r above 1 shrinks
  delta sharply, so a frequency that works on aluminum gives a shallow
  skin effect on steel.
- Treating the phase lag as a fixed 90 degrees: the lag is depth /
  delta in radians, one radian at one delta, and it is the angle that
  sizes the depth reading on the impedance plane.
- Skipping calibration and personnel qualification: ET results are
  dispositioned under special-process control with NAS 410 qualified
  personnel, and the setup is verified on reference standards before
  the scan.

## Behavior contract (gate 3)

The inspection math is exercised by the gate 3 contract test:
scripts/test_eddy_current_inspection.py against
scripts/eddy_current_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_eddy_current_inspection.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  NDT as a special process requiring controlled procedures and
  qualified personnel, and NAS 410 sets the qualification and
  certification requirements for the NDT personnel who execute eddy
  current inspection; the formulas and impedance-plane practice above
  are common ET methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
