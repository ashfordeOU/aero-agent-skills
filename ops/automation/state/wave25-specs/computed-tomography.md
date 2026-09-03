# Wave-25 leaf spec: computed-tomography (manufacturing-quality, ndt pack)

- Path: skills/manufacturing-quality/ndt/computed-tomography/
- Pack: ndt (existing siblings: ndt-method-selection, radiographic-
  inspection, ultrasonic-inspection, eddy-current-inspection,
  liquid-penetrant-inspection, magnetic-particle-inspection,
  acoustic-emission-inspection, thermography, visual-inspection)
- Standards ids: as9100  (Ledger Standard: as9100)
- Family: manufacturing-quality

## Claim

Plan and interpret an X-ray computed tomography (CT) inspection of an
aerospace part: compute the geometric magnification and the voxel size
from the source, object, and detector geometry, check the spatial
resolution against the smallest flaw to detect, size the number of
projections for the scan, estimate the scan time and the required tube
energy for the part material and thickness, convert the measured linear
attenuation into the CT number scale, and measure porosity volume
fraction from a segmented region of interest. Produces the voxel size,
resolution verdict, projection count, scan settings, and the porosity
measurement that gate the CT inspection plan for castings, weldments,
and additive parts.

Does NOT do: 2D radiographic film/digital setup (radiographic-inspection
owns geometric unsharpness, IQI sensitivity, film density, inverse
square exposure), method selection among NDT families (ndt-method-
selection), ultrasonic or eddy current methods. This leaf is volumetric
CT only.

## Model (implement exactly)

- Geometric magnification: M = (SOD + ODD)/SOD where SOD is the
  source-object distance and ODD the object-detector distance; detector
  pixel pitch p_det maps to voxel size v = p_det / M (approx for the
  isotropic voxel).
- Spatial resolution: smallest detectable flaw ~ 2-3 voxels (use a
  module constant detect_factor = 3); resolution check: v * detect_factor
  <= required flaw size.
- Projection count (Nyquist-ish rule for cone beam): N_proj ~ pi/2 * N_col
  where N_col is the number of detector columns spanned by the object
  (standard rule of thumb; label reference-only).
- Tube energy: use a material/thickness rule of thumb: required kV ~
  60-80 kV per 10 mm of aluminum equivalent at moderate density, steel
  roughly 2x (paraphrased reference-only guidance with module constants;
  do not present as normative).
- Scan time: t_scan = N_proj * t_per_proj (exposure per projection input)
  plus the detector integration; return total seconds.
- CT number: for a voxel with measured linear attenuation mu, CT number
  (HU) = 1000 * (mu - mu_water)/mu_water; report the material class by
  the CT number band.
- Porosity: given the segmented voxel count of voids V_voids in a region
  of interest of total voxels V_total, porosity fraction = V_voids /
  V_total, reported as percent; plus the equivalent spherical void
  diameter from the void voxel count and voxel size.
Functions:
- magnification(sod, odd) -> M
- voxel_size(pixel_pitch, sod, odd) -> m
- resolution_check(voxel_size, required_flaw_m) -> verdict
- projection_count(columns_span) -> int
- tube_energy_kv(material, thickness_mm) -> kV (module material table)
- scan_time(num_projections, exposure_s_per_proj) -> s
- ct_number(mu, mu_water) -> HU
- material_class_from_ct_number(hu) -> str
- porosity_fraction(void_voxels, total_voxels) -> percent
- void_diameter(void_voxels, voxel_size) -> m
- ct_inspection_verdict(...) -> dict
ValueError on: negative distances, pixel pitch <= 0, SOD <= 0,
required flaw <= 0, void_voxels > total_voxels, unknown material.

## Worked example

Aluminum casting 50 mm diameter inspected on a 200 micron pixel detector
with SOD 300 mm and ODD 300 mm: M = 2, voxel ~100 micron; smallest
detectable ~0.3 mm; a required 0.5 mm flaw passes; projection count
with 1024 columns; tube energy for 50 mm aluminum; scan time at 0.1 s
per projection; porosity 0.8% in the ROI. Assert the module's real
numbers (compute them first and quote in the SKILL).

## Corpus tasks (ids w25-computed-tomography-1/2)

Distinctive tokens: computed tomography, CT scan, voxel size, cone beam,
CT number, porosity measurement, volumetric inspection, magnification,
projection count, additive part porosity. Avoid: geometric unsharpness,
IQI, penetrameter, film density, source to object (the 2D radiographic
tokens owned by radiographic-inspection).

1. "plan the computed tomography scan of the additive titanium bracket:
   compute the voxel size from the source and detector geometry and the
   projection count, then measure the porosity fraction in the build
   region"
2. "convert the CT attenuation values to CT numbers and check the voxel
   resolution against the 0.5 mm flaw requirement for the casting"

## SKILL body notes

Pair with ndt-method-selection (when CT is the chosen method),
radiographic-inspection (2D counterpart), additive qualification.
Worked example uses module constants and real outputs. Compliance:
AS9100 NDT process control referenced by name; CT physics standard forms
paraphrased; no reproduced tables.
