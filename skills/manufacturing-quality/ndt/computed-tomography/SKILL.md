---
name: computed-tomography
description: "Use when you must plan and interpret a volumetric X-ray computed tomography (CT) inspection of an aerospace part: compute the geometric magnification and the voxel size from the source, object and detector geometry, check the spatial resolution against the smallest flaw to detect, size the cone beam projection count for the scan, estimate the scan time and the required tube energy for the part material and thickness, convert the measured linear attenuation into CT numbers and classify the material, and measure the porosity volume fraction with the equivalent spherical void diameter from a segmented region of interest. Produces the voxel size, resolution verdict, projection count, scan settings and porosity measurement that gate the CT inspection plan for castings, weldments and additive parts. Trigger: computed tomography, CT scan, voxel size, cone beam, CT number, volumetric inspection, porosity volume fraction, magnification, projection count, additive part porosity."
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
  tags: [computed-tomography, ct-scan, voxel-size, cone-beam, ct-number, porosity-volume-fraction, magnification-ratio, projection-count, additive-part-porosity, volumetric-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Computed Tomography (manufacturing-quality/ndt/computed-tomography)

Use when you must plan and interpret a volumetric X-ray computed
tomography (CT) inspection of an aerospace part: turning the source,
object and detector geometry into the magnification and voxel size,
checking the achievable spatial resolution against the smallest flaw to
detect, sizing the cone beam projection count, estimating the scan time
and the required tube energy, converting measured attenuation into CT
numbers, and measuring the porosity volume fraction in a segmented
region of interest. This leaf is volumetric CT only; 2D radiographic
film and digital setup (geometric unsharpness, IQI sensitivity, film
density, inverse square exposure) belongs to
manufacturing-quality/ndt/radiographic-inspection. It pairs with
manufacturing-quality/ndt/ndt-method-selection, which decides when CT is
the chosen method for an internal defect class. This leaf implements the
planning model in pure Python, stdlib only.

## Domain quick reference

- Geometric magnification: M = (SOD + ODD) / SOD, with SOD the
  source to object distance and ODD the object to detector distance.
- Voxel size: the detector pixel pitch p_det maps to the approximate
  isotropic voxel size v = p_det / M.
- Spatial resolution: the smallest reliably detected feature spans
  about 2 to 3 voxels; this module uses the module constant
  detect_factor = 3, so the check passes when v * detect_factor is at
  or below the required flaw size.
- Projection count (Nyquist-ish rule of thumb for cone beam):
  N_proj ~= pi / 2 * N_col, where N_col is the number of detector
  columns spanned by the object projection (reference-only guidance).
- Tube energy (rule of thumb, paraphrased reference-only guidance):
  roughly 60 to 80 kV per 10 mm of aluminum equivalent at moderate
  density, with steel about 2 times that; this module uses a
  representative kV per mm material table (aluminum 7, titanium 9,
  steel 14, nickel 16 kV per mm).
- Scan time: t_scan = N_proj * t_per_proj with the exposure time per
  projection as input; total in seconds.
- CT number: HU = 1000 * (mu - mu_water) / mu_water for a voxel with
  measured linear attenuation mu against the water attenuation
  mu_water; the material class follows the CT number band
  (air-or-gas, low-density-void, polymer-composite, light-alloy,
  high-density-metal).
- Porosity: porosity fraction = V_voids / V_total from the segmented
  void voxel count and the region of interest total voxel count,
  reported as percent; the equivalent spherical void diameter follows
  from the void voxel count and the voxel size by volume conservation.
- Units are SI throughout (m, s) except thickness in mm for the tube
  energy rule and porosity in percent.
- AS9100 frames the NDT process control context; the relations above
  are standard engineering methodology and reference-only guidance,
  summary-only.

## Workflow

1. Fix the scan geometry: SOD and ODD in m, detector pixel pitch p_det
   in m. Compute magnification with magnification(sod, odd) and the
   voxel size with voxel_size(pixel_pitch, sod, odd).
2. State the smallest required flaw and run resolution_check(voxel, flaw)
   for the pass or fail verdict on spatial resolution.
3. Span the object on the detector: with the number of detector
   columns crossed by the object projection, size the scan with
   projection_count(columns_span).
4. Estimate the tube energy with tube_energy_kv(material,
   thickness_mm) using the material table, and the total scan time
   with scan_time(num_projections, exposure_s_per_proj).
5. Convert measured attenuation to the CT scale with ct_number(mu,
   mu_water) and classify the voxel population with
   material_class_from_ct_number(hu).
6. Measure porosity: porosity_fraction(void_voxels, total_voxels)
   gives the percent, void_diameter(void_voxels, voxel_size) the
   equivalent spherical void diameter.
7. For the planning summary call ct_inspection_verdict(...) once; it
   returns the magnification, voxel size, resolution verdict,
   projection count, tube energy, and any scan time, porosity and CT
   number fields supplied.
8. Confirm the deterministic checks with the contract test
   scripts/test_computed_tomography.py.

## Worked example

Aluminum casting 50 mm diameter on a 200 micron pixel detector with
SOD 300 mm and ODD 300 mm, required flaw 0.5 mm, 1024 detector
columns, 0.1 s per projection, 0.8 percent porosity in a region of
interest of 8,000,000 voxels.

- Magnification: M = (300 + 300) / 300 = 2.0
  (magnification(0.300, 0.300)).
- Voxel size: v = 200 micron / 2 = 1.000e-4 m (100 micron)
  (voxel_size(200e-6, 0.300, 0.300)).
- Spatial resolution: smallest detectable feature 3 * 1.000e-4 =
  3.000e-4 m, at or below the required 5.000e-4 m flaw, verdict PASS.
- Projection count: N_proj = ceil(pi / 2 * 1024) = 1609
  (projection_count(1024)).
- Tube energy: 7.0 kV per mm * 50 mm = 350.0 kV
  (tube_energy_kv("aluminum", 50.0)).
- Scan time: 1609 * 0.1 s = 160.9 s (scan_time(1609, 0.1)).
- Porosity: 64,000 void voxels over 8,000,000 total voxels = 0.8
  percent (porosity_fraction(64000, 8000000)); equivalent spherical
  void diameter void_diameter(64000, 1.000e-4) = 4.963e-3 m.
- CT number example: mu = 1.4 * mu_water gives
  ct_number(28.0, 20.0) = 400 HU, material class light-alloy.

## Verification

- Confirm magnification(0.300, 0.300) returns 2.0 and
  voxel_size(200e-6, 0.300, 0.300) returns 1.000e-4 m.
- Confirm resolution_check(1.000e-4, 5.000e-4) returns a PASS verdict
  and resolution_check(1.000e-4, 2.000e-4) returns FAIL.
- Confirm projection_count(1024) returns 1609 and scan_time(1609, 0.1)
  returns 160.9 s.
- Confirm tube_energy_kv("aluminum", 50.0) returns 350.0 kV and that
  the steel value is about 2 times the aluminum value per mm.
- Confirm ct_number round-trips: ct_number(mu, mu_water) then
  mu_water * (1 + hu / 1000) recovers mu.
- Confirm porosity_fraction(64000, 8000000) returns 0.8 percent and
  the void volume conserved by void_diameter equals the voxel count
  times the voxel volume.
- Confirm every non-positive distance, pitch, flaw size, thickness,
  exposure and projection count, void count above the total, and
  unknown material raises ValueError.
- Run the contract test offline: python3
  scripts/test_computed_tomography.py (59 tests, deterministic).

## Related leaves

- manufacturing-quality/ndt/ndt-method-selection: decides when CT is
  the chosen method among the NDT families for an internal defect
  class on a cast or additive part.
- manufacturing-quality/ndt/radiographic-inspection: the 2D
  radiographic counterpart (geometric unsharpness, IQI sensitivity,
  film density and exposure), used when planar radiography is chosen
  over the volumetric CT scan.
- manufacturing-quality/additive/lpbf-parameter-development: the
  build process context for additive parts whose build region
  porosity this leaf measures volumetrically.

## Pitfalls

- Trusting a resolution verdict for flaws smaller than the voxel
  rule: the smallest reliably detected feature spans about 2 to 3
  voxels (detect_factor = 3 here), so a 0.2 mm flaw under a
  1.000e-4 m voxel scan FAILS while the same flaw passes at 0.5 mm -
  features below 3 voxels are not a valid claim.
- Treating the planning rules as exact standards: the projection count
  (pi / 2 * N_col) and the tube energy table (aluminum 7, titanium 9,
  steel 14, nickel 16 kV per mm, steel about 2 times aluminum) are
  reference-only rules of thumb for moderate density, not a substitute
  for the scan developer's validated technique.
- Reading a CT number band as material identification: HU = 1000 *
  (mu - mu_water) / mu_water classifies a voxel into a band
  (air-or-gas through high-density-metal) - two materials can share a
  band, so the class is not a chemical identification.
- Mixing units: the geometry and exposure inputs are SI (m, s) while
  thickness enters the tube energy rule in mm and porosity is reported
  in percent, so a cm source distance or a fraction porosity silently
  corrupts the plan.
- Quoting porosity without the segmentation: the fraction is
  void voxels over the region-of-interest total (0.8 percent from
  64,000 of 8,000,000 voxels in the worked example), and a void count
  above the total raises ValueError - the ROI definition is part of
  the measurement.
- Reaching for this leaf for 2D setups: it is volumetric CT only;
  geometric unsharpness, IQI sensitivity, film density and inverse
  square exposure belong to radiographic-inspection.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_computed_tomography.py

The test covers the worked example contract (magnification 2.0, voxel
1.000e-4 m, PASS at the 0.5 mm flaw, 1609 projections, 350 kV, 160.9 s,
0.8 percent porosity, void diameter 4.963e-3 m), magnification and
voxel scaling, the resolution boundary at exactly 3 voxels, the
projection count rule of thumb, the tube energy material table and
scaling, scan time scaling, CT number conversion with the round trip,
material class bands, porosity fraction bounds, void diameter volume
conservation, the combined ct_inspection_verdict, and ValueError
rejection of non-physical inputs and unknown materials.

## Compliance

- Standards referenced, not reproduced: AS9100 frames the NDT process
  control and personnel qualification context; CT physics standard
  forms (magnification, voxel mapping, cone beam sampling rule, tube
  energy rule, Hounsfield scale) are paraphrased reference-only
  guidance, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
