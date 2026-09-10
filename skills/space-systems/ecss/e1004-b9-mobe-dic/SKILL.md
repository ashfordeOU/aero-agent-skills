---
name: e1004-b9-mobe-dic
description: "Use when characterizing the directional transmission of galactic cosmic ray (GCR) and solar energetic particle (SEP) flux through the geomagnetic field under ECSS-E-ST-10-04C Annex B.9: compute the local vertical Stormer-type geomagnetic cutoff rigidity from geomagnetic latitude, apply the Mobius-class Directional Intensity Change (DIC) correction for a given arrival zenith angle and azimuth to obtain the directional cutoff rigidity (capturing the east-west asymmetry between eastward- and westward-arriving primaries), classify a candidate particle rigidity as forbidden, penumbra, or allowed transmission across that directional cutoff's penumbra band, and select the worst-case (lowest-cutoff) arrival direction to verify that a direction-resolved radiation environment case bounds the true geomagnetic shielding. Trigger: geomagnetic cutoff, Stormer cutoff, Directional Intensity Change, DIC, Mobius model, east-west effect, penumbra, geomagnetic transmission, rigidity, asymptotic direction, e-st-10-04, ecss."
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
  tags: [ecss, e-st-10-04c, annex-b9, mobius, dic, directional-intensity-change, geomagnetic-cutoff, stormer, east-west-effect, penumbra]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mobius/DIC Geomagnetic Transmission (space-systems/ecss/e1004-b9-mobe-dic)

Use when the task is characterizing how the geomagnetic field directionally
shields a spacecraft position from galactic cosmic ray (GCR) and solar
energetic particle (SEP) primaries under ECSS-E-ST-10-04C Annex B.9, to
determine the direction-resolved cutoff rigidity and the resulting particle
transmission for a radiation environment case.

## Domain quick reference

- A charged primary can only reach a given position from a given arrival
  direction if its magnetic rigidity (momentum per unit charge) exceeds a
  geomagnetic cutoff rigidity for that position and direction; the classic
  Stormer treatment gives a single vertical-incidence cutoff from geomagnetic
  latitude alone (`Cst * cos^4(latitude)`), with the Stormer constant fixed
  by the present-epoch geomagnetic dipole moment.
- The vertical-only cutoff understates the real directional dependence: for
  positive primaries the geomagnetic field's curvature makes the cutoff
  higher for particles arriving from local geomagnetic east and lower for
  particles arriving from local geomagnetic west -- the east-west effect --
  and the effect grows from zero at zenith angle 0 (straight up, no azimuth
  dependence) toward its largest magnitude near the horizon.
- A Mobius-class Directional Intensity Change (DIC) correction applies a
  zenith- and azimuth-dependent factor to the vertical cutoff to obtain the
  directional cutoff rigidity for an arbitrary arrival direction, rather than
  assuming every direction shares the vertical value.
- Real geomagnetic shielding is not a sharp allowed/forbidden step at the
  cutoff: a band of rigidities straddling the cutoff -- the penumbra --
  contains an alternating mix of allowed and forbidden trajectories. This
  leaf's engineering approximation represents the penumbra as a linear
  transmission-probability ramp across a fractional band around the
  directional cutoff rather than resolving the true trajectory-by-trajectory
  fine structure.
- The direction with the lowest cutoff rigidity is the easiest access
  direction for GCR/SEP primaries and therefore the worst case for a
  radiation environment case that must bound single-event or dose
  contributions; under this leaf's model that worst case is analytically the
  horizon-grazing, due-geomagnetic-west direction.
- This leaf scopes cutoff-rigidity geometry, the DIC directional correction,
  penumbra transmission probability, and worst-case direction selection only.
  It does not model actual trajectory tracing, real-epoch non-dipole field
  harmonics, or the GCR/SEP source spectra themselves (see sibling
  e1004-gcr and the SEP fluence/peak-flux leaves for the incident spectra
  this leaf's transmission is applied to).

## Workflow

1. For each radiation environment case, record its geomagnetic latitude
   (deg), the arrival zenith angle (deg, 0 = local vertical, 90 = horizon)
   and azimuth from geomagnetic north (deg, clockwise, east = 90) of
   interest, the candidate particle rigidity (GV) to be checked, and whether
   the case requires the worst-case arrival direction.
2. Compute the vertical Stormer-type cutoff rigidity from geomagnetic
   latitude alone.
3. Apply the DIC directional correction for the case's zenith angle and
   azimuth to obtain the directional cutoff rigidity at that position and
   direction.
4. Classify the case's candidate particle rigidity against the directional
   cutoff's penumbra band as forbidden (fully shielded), penumbra (partial,
   probabilistic transmission), or allowed (fully transmitted); when a full
   incident spectrum is available, weight each rigidity bin by its
   transmission probability rather than only checking the single candidate
   rigidity.
5. Select the worst-case arrival direction (lowest directional cutoff) for
   the case's geomagnetic latitude.
6. Verify, when the case requires worst-case coverage, that the direction
   actually evaluated is at least as conservative as (its directional cutoff
   does not exceed) the selected worst-case direction's cutoff; flag any
   case that instead evaluates a more sheltered direction while claiming
   worst-case coverage.
7. Roll every case's forbidden/penumbra/allowed classification and
   worst-case-coverage finding into the radiation environment assessment
   record, and do not close it while any required worst-case case remains
   unresolved.

## Pitfalls

- Using the vertical-incidence Stormer cutoff for a direction-resolved
  analysis (e.g. a wide field-of-view detector or an arbitrary spacecraft
  attitude) instead of applying the DIC directional correction, which
  understates access from the geomagnetic-west side and overstates it from
  the geomagnetic-east side.
- Treating the cutoff as a sharp allowed/forbidden step and ignoring the
  penumbra band, which discards the genuine partial transmission that
  occurs for rigidities straddling the cutoff.
- Selecting an arbitrary or convenient arrival direction for a "worst-case"
  radiation environment case instead of the direction with the lowest
  directional cutoff, which understates the true worst-case GCR/SEP access.
- Assuming the east-west asymmetry vanishes uniformly; under this leaf's
  model it is zero only at zenith angle 0 and grows toward the horizon, so a
  near-vertical case and a near-horizon case at the same latitude cannot
  share the same directional cutoff.

## Behavior contract (gate 3)

The cutoff-rigidity geometry, DIC directional correction, penumbra
transmission classification, spectrum-weighted transmitted flux, and
worst-case-direction compliance logic is exercised by the gate 3 contract
test: scripts/test_e1004_b9_mobe_dic.py against
scripts/e1004_b9_mobe_dic_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_b9_mobe_dic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
