---
name: shearography-inspection
description: "Use when you must plan and interpret a laser shearography NDT inspection on an aerospace composite or bonded part: compute the phase sensitivity of the shearography setup from the laser wavelength and the shear distance, select the shear distance for the minimum defect size of interest, size the vacuum, thermal, or vibration load step for the part stiffness, build the scan plan covering the part with the required overlap, convert a measured phase anomaly from the fringe map into a strain gradient estimate, and disposition the anomaly against the maximum allowable disbond or delamination size. Produces the setup parameters, the scan plan, the anomaly strain estimate, and the disposition verdict that gate the inspection under an approved NDT procedure. Trigger: laser shearography, shearography inspection, phase map, shear distance, strain gradient, vacuum load step, fringe anomaly, disbond detection, composite panel inspection, minimum detectable strain."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: ndt
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [shearography-inspection, laser-shearography, shear-distance, phase-map, strain-gradient, vacuum-load-step, thermal-load-step, vibration-load-step, fringe-anomaly, minimum-detectable-strain, disbond-detection, composite-panel-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Shearography Inspection (manufacturing-quality/ndt/shearography-inspection)

Use when you must plan and interpret a laser shearography NDT inspection on
an aerospace composite or bonded part: turning the laser wavelength and the
lateral shear distance into the phase sensitivity of the interferometer,
selecting the shear distance for the minimum defect size of interest,
sizing the vacuum, thermal, or vibration load step that excites the
defect, building the scan plan that covers the part with the required
overlap, converting a measured phase anomaly into an out-of-plane
displacement gradient (strain) estimate, and dispositioning that anomaly
against the maximum allowable disbond or delamination size. Shearography
is the full-field optical alternative for disbond detection that goes
beyond the classic five NDT methods; this leaf owns the optics, loading,
and strain-anomaly math only. It pairs with
manufacturing-quality/ndt/ndt-method-selection, where shearography is an
alternative method outside the RT, UT, ET, PT, and MT screening list, and
with manufacturing-quality/ndt/thermography and
manufacturing-quality/ndt/ultrasonic-inspection, the sibling methods that
also hunt disbonds and delaminations in composite panels. This leaf
implements the planning and interpretation model in pure Python, stdlib
only.

## Domain quick reference

- Shearography phase: delta_phi = (4 * pi / lambda) * shear *
  strain_gradient, where delta_phi is the phase difference between the two
  sheared images under load (radians), lambda is the laser wavelength,
  shear is the lateral shear distance, and strain_gradient ~ d(w)/dx is
  the out-of-plane displacement gradient. All lengths must share one unit;
  this module converts nm and mm inputs to meters consistently.
- Strain from a phase anomaly: strain = phase * lambda / (4 * pi * shear).
  strain_from_phase(0.5, 5.0, 532.0) returns about 4.23e-6 relative
  strain, that is about 4.23 micron/m (1 micron/m = 1e-6 strain).
- Phase from a strain estimate (inverse): phase_for_strain(strain, shear,
  wavelength) recovers the phase; the round trip holds within 1e-12.
- Minimum detectable strain: min_detectable_strain(noise_floor_rad, shear,
  wavelength) = MIN_SNR * noise_floor * lambda / (4 * pi * shear). With
  the module noise floor of 0.1 rad at 5 mm shear, the minimum is exactly
  MIN_SNR (3.0) times the single-frame noise-equivalent strain.
- Shear distance rule: shear_for_defect(defect_size_mm) =
  defect_size_mm / SHEAR_DIVISOR, about half the minimum defect size
  (10 mm defect to 5 mm shear, 6 mm defect to 3 mm shear).
- Load steps (documented typical values for aerospace laminates; the
  approved procedure governs the real load): vacuum delta pressure in mbar
  keyed by laminate thickness in mm with linear interpolation between the
  2.0 mm (20 mbar), 6.0 mm (40 mbar), and 12.0 mm (60 mbar) breakpoints,
  thermal temperature rise 5 deg C, and vibration frequency band index 30
  of a typical 100 to 1000 Hz sweep.
- Scan plan: passes = ceil(part_area_m2 / (fov_area_m2 * (1 - overlap))),
  with overlap_area = passes * fov_area_m2 * overlap. The planned passes
  image at least COVERAGE_MIN (0.85) of the part area with valid phase
  data, so the coverage check in summarize passes when the plan covers the
  part.
- Disposition: reject when the anomaly size reaches or exceeds the
  allowable plus the REVIEW_BAND (0.2) margin; review when the anomaly
  exceeds the allowable but stays inside the band, or when the signal to
  noise ratio falls below MIN_SNR (3.0); accept when the anomaly is within
  the allowable and the SNR meets MIN_SNR.
- Units: wavelength nm, shear mm, thickness mm, pressure mbar, temperature
  rise deg C, areas m2, phase radians, strain relative (m/m, reported
  against the 1e-6 micron/m scale).
- AS9100 frames the special process control and procedure approval
  context; the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. State the inspection task: minimum defect size of interest, part area,
   field of view, laminate thickness, and the load type available
   (vacuum, thermal, or vibration).
2. Select the shear distance with shear_for_defect(min_defect_mm): about
   half the minimum defect size, so the defect strains the full shear
   step.
3. Check the minimum detectable strain against the expected defect strain:
   min_detectable_strain(noise_floor_rad, shear_mm, wavelength_nm) gives
   the floor the defect signal must clear at MIN_SNR.
4. Size the load step with select_load(part_thickness_mm, load_type):
   vacuum pressure interpolated over the thickness breakpoints, or the
   thermal and vibration typical values. The procedure authority approves
   the real load.
5. Build the scan plan with scan_plan(part_area_m2, fov_area_m2,
   overlap): the pass count and the redundant overlap area that gate the
   mechanical scan.
6. Interpret the measured fringe anomaly: strain_from_phase(phase_rad,
   shear_mm, wavelength_nm) converts the phase map value into a strain
   gradient estimate; phase_for_strain recovers the phase for a
   cross-check.
7. Disposition the anomaly with anomaly_disposition(anomaly_size_mm,
   allow_size_mm, snr) against the maximum allowable disbond or
   delamination size: accept, review, or reject with reasons.
8. Call summarize(...) once for the complete planning record: shear
   distance, minimum detectable strain, load value, scan plan, coverage
   check, anomaly strain estimate, and verdict.
9. Confirm the deterministic checks with the contract test
   scripts/test_shearography_inspection.py.

## Worked example

Composite panel inspection for disbonds: minimum defect 10 mm, part area
1.0 m2, field of view 0.25 m2, 20 percent overlap, 6 mm laminate under
vacuum load, 0.5 rad phase anomaly measured at the shear distance, 12 mm
anomaly against a 10 mm allowable, SNR 5.0, 532 nm laser, 0.1 rad noise
floor.

- Shear distance: shear_for_defect(10.0) = 5.0 mm (6 mm defect to 3 mm).
- Phase sensitivity: 0.5 rad at 5 mm shear and 532 nm is a strain
  gradient of 4.23e-6 relative strain (4.23 micron/m):
  strain_from_phase(0.5, 5.0, 532.0); the inverse phase_for_strain
  recovers 0.5 rad within 1e-12.
- Minimum detectable strain: with the 0.1 rad noise floor at 5 mm shear,
  min_detectable_strain(0.1, 5.0, 532.0) is exactly 3.0 times the
  noise-equivalent single-frame strain (the MIN_SNR contract), about
  2.54e-6 relative strain, well below the 4.23e-6 measured anomaly.
- Load step: select_load(6.0, "vacuum") = 40.0 mbar; for a 4 mm laminate
  the interpolation gives 30.0 mbar between the 20 mbar (2 mm) and
  40 mbar (6 mm) breakpoints. Thermal would be 5.0 deg C, vibration
  30.0.
- Scan plan: scan_plan(1.0, 0.25, 0.2) gives 5 passes with 0.25 m2 of
  overlap area; the same part at 95 percent overlap needs 80 passes.
- Disposition: anomaly_disposition(12.0, 10.0, 5.0) rejects (12 mm is at
  the allowable plus the 20 percent band), (9.0, 10.0, 5.0) accepts,
  (11.0, 10.0, 5.0) reviews because it exceeds the allowable inside the
  band, and (8.0, 10.0, 2.0) reviews on low SNR (2.0 below MIN_SNR 3.0).
- Summarize: summarize(part_thickness_mm=6.0, part_area_m2=1.0,
  fov_area_m2=0.25, overlap=0.2, min_defect_mm=10.0, load_type="vacuum",
  phase_rad=0.5, anomaly_size_mm=12.0, allow_size_mm=10.0, snr=5.0)
  returns shear 5.0 mm, load 40.0 mbar, 5 passes, coverage OK, anomaly
  strain 4.23e-6, verdict reject.

## Verification

- Confirm strain_from_phase(0.5, 5.0, 532.0) returns 4.23e-6 and that
  phase_for_strain of that strain recovers 0.5 rad within 1e-12.
- Confirm min_detectable_strain(0.1, 5.0, 532.0) is exactly MIN_SNR
  (3.0) times strain_from_phase(0.1, 5.0, 532.0).
- Confirm shear_for_defect(10.0) returns 5.0 mm and shear_for_defect(6.0)
  returns 3.0 mm.
- Confirm select_load(6.0, "vacuum") returns 40.0 mbar, select_load(4.0,
  "vacuum") returns 30.0 mbar by interpolation, and select_load(3.0,
  "thermal") returns 5.0 deg C.
- Confirm scan_plan(1.0, 0.25, 0.2) returns 5 passes and scan_plan(1.0,
  0.25, 0.95) returns 80 passes.
- Confirm the disposition branches: 12 mm over 10 mm rejects, 9 mm over
  10 mm accepts, 11 mm over 10 mm reviews, 8 mm at SNR 2 reviews.
- Confirm every non-positive shear, thickness, area, defect, anomaly and
  allowable size, every unknown load_type, every overlap outside
  [0, 0.95], and every non-finite input raises ValueError.
- Run the contract test offline: python3
  scripts/test_shearography_inspection.py (29 tests, deterministic).

## Related leaves

- manufacturing-quality/ndt/ndt-method-selection: the classic five NDT
  method screening (RT, UT, ET, PT, MT); shearography is the alternative
  method this leaf sizes and interprets.
- manufacturing-quality/ndt/thermography: the thermal contrast method for
  the same disbond and delamination defect classes.
- manufacturing-quality/ndt/ultrasonic-inspection: the time of flight
  echo sizing method for disbond and delamination detection.
- manufacturing-quality/as9100/calibration-control: the calibration
  system, test accuracy ratio, and due date controls that cover the
  shearography instrument under the AS9100 process.

## Pitfalls

- Mixing wavelength and shear units: the phase and strain relations
  require all lengths in one unit, and the module converts nm and mm
  inputs to meters consistently — a 532 nm wavelength fed against mm
  shear without conversion corrupts the strain estimate by orders of
  magnitude.
- Selecting shear larger than the defect: the rule sizes shear at
  about half the minimum defect (10 mm defect to 5 mm shear), so a
  shear distance near or above the defect size under-strains the
  anomaly and drops the signal toward the noise floor.
- Reading an anomaly without the SNR gate: an accept requires the
  anomaly within the allowable AND the signal to noise at MIN_SNR
  (3.0) — (8.0, 10.0, 2.0) reviews on low SNR even though the size is
  inside the allowable.
- Treating the module load values as release authority: the vacuum
  breakpoints (20/40/60 mbar), 5 deg C thermal rise and vibration
  sweep band are documented typical values for aerospace laminates —
  the approved procedure governs the real load.
- Dispositioning without the review band: an anomaly between the
  allowable and the allowable plus the 0.2 band (11 mm over a 10 mm
  allowable) reviews, and only an anomaly at or beyond the band edge
  rejects.
- Letting overlap blow up the scan: coverage needs at least 0.85 of
  the part with valid phase data, but overlap is capped at 0.95 — the
  same 1.0 m2 part needs 5 passes at 20 percent overlap and 80 passes
  at 95 percent, so an unnecessary overlap costs real scan time.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_shearography_inspection.py

The test covers the worked example contract (4.23e-6 strain at 0.5 rad,
5 mm shear and 532 nm, round trip within 1e-12, minimum detectable
strain ratio exactly 3.0, shear_for_defect 10 mm to 5 mm, vacuum load
interpolation 6 mm to 40 mbar and 4 mm to 30 mbar, scan plan 5 passes at
20 percent overlap and 80 passes at 95 percent, accept / review / reject
dispositions), phase and strain scaling, the noise floor sensitivity, the
shear selection rule, the load table constants, scan plan boundary cases,
the summarize record, and ValueError rejection of non-physical inputs,
unknown load types, and out-of-range overlap.

## Compliance

- Standards referenced, not reproduced: AS9100 frames the NDT special
  process control and procedure approval context; the shearography
  relations above (phase sensitivity, shear selection rule, load step
  guidance, scan plan, disposition band) are standard engineering
  methodology and documented typical values, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
