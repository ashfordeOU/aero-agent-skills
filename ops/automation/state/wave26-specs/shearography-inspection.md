# Wave-26 leaf spec: shearography-inspection (manufacturing-quality, ndt pack)

- Path: skills/manufacturing-quality/ndt/shearography-inspection/
- Pack: ndt (existing siblings: ultrasonic-inspection, thermography,
  eddy-current-inspection, radiographic-inspection, liquid-penetrant-
  inspection, magnetic-particle-inspection, acoustic-emission-
  inspection, visual-inspection, computed-tomography, ndt-method-
  selection)
- Standards ids: as9100  (Ledger Standard: as9100)
- Family: manufacturing-quality

## Claim

Plan and interpret a laser shearography NDT inspection on an aerospace
composite or bonded part: compute the phase sensitivity of the
shearography setup from the laser wavelength and the shear distance,
select the shear distance for the minimum defect size of interest,
size the load step (vacuum, thermal, or vibration) for the part
stiffness, build the scan plan that covers the part with the required
overlap, convert a measured phase anomaly into a surface strain
gradient estimate, and disposition the anomaly against the maximum
allowable disbond or delamination size. Produces the setup parameters,
the scan plan, the anomaly strain estimate, and the disposition
verdict that gate the shearography inspection under an approved NDT
procedure.

Does NOT do: pick among the classic five NDT methods (ndt-method-
selection owns the RT/UT/ET/PT/MT screening; shearography is beyond
that leaf's method list), measure thermal contrast over time
(thermography owns flash and lock-in thermal methods), or size echoes
by time of flight (ultrasonic-inspection). This leaf is the
shearography-specific optics, loading, and strain-anomaly math.

## Model (implement exactly)

Principle (implement exactly):
- Shearography measures the out-of-plane displacement gradient
  d(w)/dx. The phase difference between the two sheared images under
  load is delta_phi = (4 * pi / lambda) * shear * strain_gradient
  where strain_gradient ~ d(w)/dx (radians), lambda is the laser
  wavelength, shear is the lateral shear distance (same length unit as
  the gradient denominator; document the consistent unit convention in
  the SKILL body).
Module constants:
- LASER_WAVELENGTH_NM = 532.0 (typical frequency-doubled Nd:YAG,
  documented as a typical value; input can override).
- NOISE_FLOOR_PHASE_RAD = 0.1 (typical phase noise floor, documented
  typical).
- MIN_SNR = 3.0 (a defect signal must exceed the noise floor by this
  factor to be detected).
- COVERAGE_MIN = 0.85 (fraction of the part area that must be imaged
  with valid phase data).
- TYPICAL_LOAD_STEPS = {"vacuum": {2.0: 20.0, 6.0: 40.0, 12.0: 60.0},
  "thermal": 5.0, "vibration": 30.0} where vacuum keyed by laminate
  thickness mm -> delta pressure in mbar (documented typical values
  for aerospace laminates; the procedure authority approves the real
  load), thermal = temperature rise deg C, vibration = frequency band
  index (Hz, documented typical 100-1000 Hz sweep).
Functions:
- strain_from_phase(phase_rad, shear_mm, wavelength_nm) -> strain
  (micron/m = 1e-6): strain = phase * wavelength_nm * 1e-9 /
  (4 * pi * shear_mm * 1e-3); ValueError on shear <= 0.
- phase_for_strain(strain, shear_mm, wavelength_nm) -> radians
  (inverse of the above; round-trip identity in the tests).
- min_detectable_strain(noise_floor_rad, shear_mm, wavelength_nm) ->
  strain = MIN_SNR * noise_floor / (4 pi shear...) (same form with
  the MIN_SNR factor).
- shear_for_defect(defect_size_mm) -> shear_mm = defect_size_mm /
  SHEAR_DIVISOR with SHEAR_DIVISOR = 2.0 (typical rule: shear about
  half the minimum defect size; documented typical).
- select_load(part_thickness_mm, load_type) -> load value from the
  TYPICAL_LOAD_STEPS table with linear interpolation between the
  vacuum thickness breakpoints (ValueError on thickness <= 0, unknown
  load_type).
- scan_plan(part_area_m2, fov_area_m2, overlap) -> dict {passes,
  overlap_area}: passes = ceil(part_area / (fov_area * (1 -
  overlap))); ValueError on area <= 0 or overlap outside [0, 0.95].
- anomaly_disposition(anomaly_size_mm, allow_size_mm, snr) -> dict
  {verdict (accept / reject / review), reasons}: reject when
  anomaly_size > allow_size_mm; accept when anomaly_size <=
  allow_size_mm and snr >= MIN_SNR; review when the anomaly is within
  20% of the limit (module constant REVIEW_BAND = 0.2) or snr below
  MIN_SNR; ValueError on negative sizes.
- summarize(...) -> dict for the SKILL worked example.
ValueError on: non-positive shear, thickness, area, or sizes;
unknown load_type; overlap outside the valid range; non-finite
values.

## Worked example

1. strain_from_phase(0.5 rad, shear 5 mm, 532 nm): compute and assert
   the module value (order 1e-5 relative strain); assert the
   round-trip phase_for_strain(strain_from_phase(...)) ~ 0.5 within
   1e-12.
2. min_detectable_strain with noise floor 0.1 rad and shear 5 mm:
   MIN_SNR factor makes it 3x the single-frame noise strain; assert
   the ratio 3.0 exactly.
3. shear_for_defect(10 mm) = 5.0 mm; shear_for_defect(6 mm) = 3.0 mm.
4. select_load(6.0, "vacuum") = 40.0 mbar; select_load(4.0, "vacuum")
   = 30.0 mbar (linear interpolation between the 2.0 and 6.0
   breakpoints, assert the module value); select_load(3.0,
   "thermal") = 5.0 deg C.
5. scan_plan(1.0 m2, 0.25 m2 fov, 0.2 overlap) -> passes 5 (assert);
   scan_plan with overlap 0.95 -> passes 80 (assert the module value).
6. anomaly_disposition(12.0, 10.0, 5.0) -> reject;
   anomaly_disposition(9.0, 10.0, 5.0) -> accept;
   anomaly_disposition(11.0, 10.0, 5.0) -> review (within 20% band);
   anomaly_disposition(8.0, 10.0, 2.0) -> review (low SNR).
7. ValueError on shear 0, unknown load_type "laser", overlap 1.0,
   negative anomaly size.
Keep at least 18 test methods (phase-strain conversions and round
trip, noise-floor sensitivity, shear selection, load table with
interpolation, scan plan math, disposition branches, ValueErrors).

## Corpus tasks (ids w26-shearography-inspection-1/2)

Distinctive tokens: laser shearography, shearography inspection,
phase map, shear distance, strain gradient, vacuum load step,
disbond detection, composite panel inspection, fringe anomaly,
minimum detectable strain. Avoid: thermography / flash / lock-in
(sibling), ultrasonic / time of flight (sibling), eddy current /
penetrant / magnetic particle method selection (ndt-method-selection).

1. "plan the laser shearography inspection of the composite panel:
   pick the shear distance for the 10 mm minimum disbond, size the
   vacuum load step for the 6 mm laminate, and build the scan plan
   with 20 percent overlap"
2. "convert the 0.5 radian phase anomaly from the shearography fringe
   map into a strain gradient estimate and disposition the 12 mm
   disbond against the 10 mm allowable size"

## SKILL body notes

Pair with ndt-method-selection (where shearography is an alternative
beyond the classic five), thermography and ultrasonic-inspection (the
sibling methods for disbond detection), and the manufacturing-quality
as9100 calibration-control leaf for the procedure controls.
Typical values (laser wavelength, noise floor, load steps) are
documented as typicals in the module constants; the approved NDT
procedure governs the real inspection. Standards referenced not
reproduced.
