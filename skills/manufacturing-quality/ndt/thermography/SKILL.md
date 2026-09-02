---
name: thermography
description: "Use when you must plan or interpret an infrared thermography (IRT) inspection on an aerospace part: decide between active and passive thermography, choose pulsed or flash thermography versus lock-in thermography, compute the surface temperature rise of a semi-infinite solid under a heating pulse, estimate the time of maximum thermal contrast and the observation window for a disbond, delamination, void, or corrosion at depth, evaluate thermal contrast against the noise floor, and size the inspection parameters of heating pulse energy, acquisition rate, and observation time window. Compares thermography with ultrasonic, radiographic, and eddy current methods and produces the inspection plan and contrast results that gate the acceptance disposition under an approved NDT procedure. Trigger: thermography, infrared thermography, flash thermography, pulsed thermography, lock-in thermography, thermal contrast, disbond, delamination, void, corrosion, composite panel."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [thermography, infrared-thermography, flash-thermography, pulsed-thermography, lock-in, thermal-contrast, thermal, contrast, disbond, delamination, void, corrosion, active-thermography, passive-thermography, semi-infinite-solid, thermal-diffusivity, heating-pulse, pulse-energy, observation-window, acquisition-rate, composite, composite-panel, subsurface-defect]
  version: 0.1.0
  author: Aero Agent Skills
---

# Thermography (manufacturing-quality/ndt/thermography)

Use when the task is planning or interpreting an infrared
thermography inspection on an aerospace part: choosing the
excitation mode, computing the thermal response of a subsurface
defect, and sizing the acquisition parameters that make the
inspection valid.

## Domain quick reference

- Active versus passive thermography: active methods apply a
  controlled thermal stimulus (flash lamp, hot air, induction) and
  record the material response; passive methods image temperature
  differences that already exist, for example heat from a running
  engine or an in-service thermal gradient, without applying any
  stimulus.
- Pulsed (flash) thermography: a short, high-power light pulse
  heats the surface; subsurface features that trap heat (disbond,
  delamination, void) cool more slowly than sound material and
  appear as hot spots in the image sequence. Suited to thin
  structures, large areas, and contact-free scanning of composite
  and metallic skins.
- Lock-in thermography: the heating source is modulated at a fixed
  frequency and the camera records the periodic surface
  temperature; amplitude and phase images are extracted by
  correlation (lock-in) analysis. Phase images tolerate emissivity
  variations and nonuniform heating better than amplitude images,
  and lowering the modulation frequency probes deeper.
- Semi-infinite solid response: for a constant surface heat flux q
  on a semi-infinite solid, the surface temperature rise is
  delta_T = (2 * q / k) * sqrt(alpha * t / pi), where k is the
  thermal conductivity, alpha = k / (rho * c) is the thermal
  diffusivity, and t is the time. The rise scales with sqrt(t):
  fast right after the pulse, slower later.
- Thermal contrast: contrast(t) = T_defect(t) - T_sound(t), the
  temperature difference between the defect region and the sound
  region; the normalized contrast is (T_defect - T_sound) /
  T_sound. An indication is visible when the contrast exceeds the
  camera and analysis noise floor, commonly at a signal-to-noise
  ratio of 2 or more.
- Time of maximum contrast: the temperature difference between a
  flat subsurface defect at depth z and the sound region peaks
  near t_max ~ z^2 / (2 * alpha). The diffusion time z^2 / alpha
  bounds the observation window: record from roughly half the
  diffusion time to a few times it, before lateral heat spreading
  washes the contrast out.
- What thermography finds: disbonds and delaminations (air gaps
  with low thermal conductivity trap heat), voids, and corroded or
  thinned regions. Detection depends on the defect being close
  enough to the surface to build contrast inside the observation
  window; deeper defects need longer observation times and lower
  lock-in frequencies.
- Inspection parameters: heating pulse energy (raise the surface a
  few kelvin without damage; more energy density improves contrast
  but risks overheating the part), acquisition rate (the frame
  rate must resolve the fastest expected contrast peak, typically
  50 Hz to 100 Hz for thin high-diffusivity skins), and the
  observation time window (set from the defect depth and the
  thermal diffusivity, with z^2 / alpha as the reference time).
- Emissivity and surface treatment: the camera measures radiance,
  not temperature; a uniform, known emissivity (matt paint or
  tape) is required or the contrast is corrupted. Dull coatings
  are preferred; bare shiny metal is a poor emitter.
- Comparison with other methods: thermography is fast, large-area,
  non-contact, and safe (no radiation), and suits composites; it
  is limited to near-surface defects (roughly the first
  centimeters), gives lower resolution than ultrasonic, and
  depends on surface emissivity. Ultrasonic penetrates deeper with
  better depth and size resolution but needs couplant and scan
  time; radiography finds volumetric flaws but needs radiation
  safety controls and two-sided access; eddy current is fast and
  quantitative for surface and near-surface cracks in conductors
  but only on electrically conductive materials. The approved NDT
  procedure selects the method by defect class, material, and
  access, not by preference.
- Standards framing: AS9100 clause 8.5.1.3 treats NDT as a special
  process under controlled procedures, qualified personnel, and
  records; thermography work follows the same control discipline
  as every other NDT method.

## Workflow

1. Define the inspection goal: defect type (disbond, delamination,
   void, corrosion), material and thickness, expected depth, and
   the acceptance criteria from the approved NDT procedure.
2. Choose active or passive excitation, then pulsed or lock-in
   mode: pulsed for fast large-area screening of thin skins,
   lock-in for depth discrimination and phase analysis on
   composites.
3. Compute the surface temperature rise with
   surface_temperature_rise() for the planned heating pulse energy
   and check that it stays inside the part damage limit; size the
   pulse with heating_pulse_energy_density() when a target rise is
   given.
4. Estimate the time of maximum contrast with
   time_of_max_contrast() and the diffusion time with
   characteristic_diffusion_time() to set the observation window
   and the acquisition rate.
5. During the inspection, extract defect and sound region
   temperatures, compute the contrast with thermal_contrast() and
   normalized_thermal_contrast(), and compare with the noise floor
   using detectability_verdict().
6. Report the contrast, the peak time, and the disposition, and
   record the inspection under the special-process control the
   procedure requires.

## Pitfalls

- Routing method-selection questions here: choosing among NDT
  methods by defect class and material belongs to
  ndt-method-selection; this leaf assumes thermography was already
  selected and plans the inspection.
- Routing ultrasonic questions here: time of flight, transducer,
  and near-field calculations belong to ultrasonic-inspection.
- Routing radiography questions here: exposure, film, and density
  calculations belong to radiographic-inspection.
- Ignoring emissivity: radiance contrast is not temperature
  contrast unless the emissivity is uniform and known; bare shiny
  metal and untreated carbon surfaces need surface treatment.
- Observing too short or too late: a defect at depth z peaks near
  z^2 / (2 * alpha); stopping the recording before the peak or
  after lateral spreading hides the indication.
- Undersampling the peak: an acquisition rate too low for the
  material smears the contrast peak; thin high-diffusivity skins
  need high frame rates.
- Using the semi-infinite formula for thin parts: the sqrt(t)
  solution assumes a semi-infinite solid; once the thermal wave
  reaches the back wall the response departs from it.
- Overheating the part: pulse energy that raises the surface past
  the material limit damages the part; verify the rise with
  surface_temperature_rise() before firing.
- Comparing contrast at different times: contrast evolves with
  time; compare frames at the same time after the pulse, near the
  expected peak.
- Forgetting the reference region: a hot spot is only an
  indication when the sound region baseline is established;
  nonuniform heating and varying thickness create false hot spots.

## Behavior contract (gate 3)

The thermography math is exercised by the gate 3 contract test:
scripts/test_thermography.py against
scripts/thermography_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_thermography.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3
  frames NDT as a special process requiring controlled procedures,
  qualified personnel, and records; the formulas and practice
  above are common infrared thermography methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
