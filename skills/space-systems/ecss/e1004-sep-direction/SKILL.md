---
name: e1004-sep-direction
description: "Use when characterizing the directional solar particle flux for a mission under ECSS-E-ST-10-04C 9.2.2.5: compute the interplanetary magnetic field connection geometry (Parker spiral angle) to categorize a solar particle event's magnetic connection, classify the event's arrival phase (anisotropic onset versus later quasi-isotropic diffusion), compute the cone angle between a look/arrival direction and the field-aligned streaming direction, apply the anisotropy scaling to an omnidirectional-equivalent flux, and verify that a case's magnetospheric entry channel has its required cutoff-rigidity check before closing the directional assessment. Trigger: solar particle event, SEP, SPE, anisotropy, cone angle, pitch angle, Parker spiral, magnetic connection, well-connected, directional flux, magnetospheric entry, polar cusp, E-ST-10-04C 9.2.2.5, ecss, space environment, radiation environment."
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
  tags: [ecss, e-st-10-04c, sep, solar-particle-event, anisotropy, directional-flux, cone-angle, magnetosphere, parker-spiral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Directional Solar Particle Flux (space-systems/ecss/e1004-sep-direction)

Use when the task is characterizing the directional (anisotropic) solar
particle flux under ECSS-E-ST-10-04C clause 9.2.2.5, for cases where a
sensor look direction, a shielded aperture, or a magnetospheric-entry
channel needs the flux arriving from a specific direction rather than
an omnidirectional-equivalent value.

## Domain quick reference

- A solar particle event (SPE) does not arrive from all directions
  equally, especially near onset. Particles stream outward along the
  interplanetary magnetic field (IMF) line connecting the event's solar
  source region to the observation point, so the flux measured (or
  incident on a surface) depends strongly on the angle between that
  field-aligned streaming direction and the direction being evaluated
  -- the cone angle.
- The IMF line is not radial: solar rotation winds it into a Parker
  spiral. The spiral angle at 1 AU depends on solar wind speed (a
  slower wind winds tighter, giving a larger spiral angle from the
  Sun-Earth radial line). An event whose solar source longitude lines
  up with the spiral's magnetic footpoint is "well connected" and
  typically produces the fastest onset and the sharpest early
  anisotropy; a poorly connected event's particles arrive later and
  more weakly beamed.
- Anisotropy decays over the course of an event: pitch-angle scattering
  on IMF turbulence progressively randomizes the particles' arrival
  directions, so the event transitions from a strongly anisotropic
  onset phase to a later, quasi-isotropic diffusive phase. A directional
  flux case therefore always carries an elapsed-time-since-onset value,
  not just a cone angle.
- Magnetospheric entry is direction-dependent too, but at a different
  geometry: a particle's access to a given point inside the
  magnetosphere depends on whether its arrival direction is close to
  locally field-aligned (streaming down open field lines into the
  polar cusp region, effectively unimpeded) or quasi-perpendicular
  (requiring the point's cutoff rigidity to be met, which is Stormer
  cutoff geometry -- the sibling e1004-stormer leaf, clause 9.2.4). This
  leaf categorizes which entry channel a given cone angle falls into
  and flags when the cutoff-rigidity check has not yet been recorded;
  it does not compute the cutoff rigidity itself.
- This leaf scopes IMF connection geometry, event-phase classification,
  cone-angle geometry, and anisotropy scaling of an already-available
  omnidirectional-equivalent flux. Selecting or fitting that
  omnidirectional SPE flux/fluence model is the sibling e1004-sep-fluence
  and e1004-sep-peakflux leaves; rolling the directional result into the
  radiation environment specification is the sibling e1004-rad-env-spec
  leaf (clause 9.3).

## Workflow

1. For each directional SEP case, record the solar wind speed assumed
   for the event, the event source region's heliolongitude (degrees
   west of central meridian), the elapsed time since event onset
   (hours), the look/arrival direction and the field-aligned streaming
   direction (both as a consistent angle convention), and, if already
   quantified, a peak anisotropy ratio (onset-peak flux over the
   quasi-isotropic flux level).
2. Compute the Parker spiral angle from the solar wind speed and
   categorize the event's magnetic connection by comparing the source
   heliolongitude to that spiral angle within a connection tolerance.
3. Classify the case's arrival phase from elapsed time since onset:
   anisotropic onset while still inside the onset window, quasi-
   isotropic diffusive beyond it.
4. Compute the cone angle between the look/arrival direction and the
   field-aligned streaming direction.
5. Apply the anisotropy scaling: during the anisotropic-onset phase,
   scale the omnidirectional-equivalent flux by a cone-angle-dependent
   factor peaking along the field-aligned direction and falling off
   with increasing cone angle (floored, never driven to zero, since
   scattering keeps some flux arriving off-axis); during the
   quasi-isotropic phase, use the omnidirectional-equivalent flux
   unscaled.
6. Categorize the cone angle into a magnetospheric entry channel
   (field-aligned polar access, oblique transitional, or
   quasi-perpendicular access) and determine whether that channel
   requires a Stormer cutoff-rigidity check.
7. Flag a case when: it is in the anisotropic-onset phase but is
   missing either the cone angle or the peak anisotropy ratio needed
   to scale the flux, or its entry channel requires a cutoff-rigidity
   check that has not been recorded. Mark a case compliant only when
   no flags remain, and do not close the directional assessment while
   any case remains flagged.

## Pitfalls

- Applying an omnidirectional-equivalent flux directly to a
  narrow-field-of-view sensor or a specific shielded aperture during
  the anisotropic-onset phase, understating or overstating the actual
  incident flux depending on how the look direction sits relative to
  the field-aligned streaming direction.
- Treating a poorly connected event as if it were well connected (or
  vice versa) without comparing the source heliolongitude against the
  Parker spiral angle for the event's actual solar wind speed --
  connection quality is speed-dependent, not a fixed offset.
- Assuming anisotropy has decayed away without checking elapsed time
  since onset; using an isotropic assumption too early understates the
  field-aligned peak and overstates the off-axis flux.
- Treating field-aligned magnetospheric entry (polar cusp access) as
  needing the same cutoff-rigidity gate as quasi-perpendicular entry,
  or conversely skipping the cutoff-rigidity check for a
  quasi-perpendicular case because the event is otherwise well
  characterized directionally.

## Behavior contract (gate 3)

The IMF connection geometry, event-phase classification, cone-angle
geometry, anisotropy scaling, and entry-channel/cutoff-check logic is
exercised by the gate 3 contract test: scripts/test_e1004_sep_direction.py
against scripts/e1004_sep_direction_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e1004_sep_direction.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
