---
name: e1004-b8-stormer
description: "Use when computing the Størmer vertical cutoff rigidity for a spacecraft location under ECSS-E-ST-10-04C Annex B.8: apply the dipole-field Størmer formula scaled by an epoch-dependent geomagnetic dipole moment coefficient to derive the cutoff rigidity at a geomagnetic latitude and radial distance, verify whether a given charged-particle rigidity penetrates the geomagnetic field at that location, and roll per-orbit-sample penetration results into a geomagnetic-shielding assessment for low-inclination low-Earth-orbit missions. Trigger: Stormer cutoff, Størmer cutoff, vertical cutoff rigidity, geomagnetic cutoff, dipole moment epoch, geomagnetic shielding, cosmic ray cutoff, rigidity spectrum, e-st-10-04, ecss, space environment, radiation environment."
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
  tags: [ecss, e-st-10-04c, stormer, cutoff-rigidity, geomagnetic-shielding, dipole, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Størmer Vertical Cutoff (space-systems/ecss/e1004-b8-stormer)

Use when the task is deriving the Størmer vertical cutoff rigidity under
ECSS-E-ST-10-04C Annex B.8, to determine how much a spacecraft location's
geomagnetic field excludes low-rigidity charged particles (GCR, SEP,
trapped-proton leakage) before they can reach that location.

## Domain quick reference

- The Størmer theory treats Earth's magnetic field as a centered dipole
  and gives, for a location at geomagnetic latitude and radial distance
  from the dipole center, a vertical cutoff rigidity: the minimum
  particle rigidity (momentum per unit charge) that can arrive from the
  zenith direction. Particles below the cutoff are deflected away and
  never reach that location; particles at or above the cutoff penetrate.
- The cutoff scales as cos^4(geomagnetic latitude) divided by the
  square of the radial distance (Earth radii): cutoff is maximal at the
  geomagnetic equator (most shielding) and falls to zero at the
  geomagnetic poles (no shielding, cos^4(90 deg) = 0), and falls off
  with altitude as a location moves outward from the dipole center.
- The scale of the cutoff is set by a Størmer constant that is
  proportional to Earth's geomagnetic dipole moment. The dipole moment
  is not fixed -- it decays secularly over time (a well-known
  multi-decade trend) -- so the same geomagnetic latitude and altitude
  yield a lower cutoff (less shielding) at a later epoch than at an
  earlier one. Annex B.8 calls for an epoch coefficient on the dipole
  moment/Størmer constant rather than a single fixed value across all
  mission years.
- Because the dipole moment secularly decreases, the cutoff at a fixed
  location decreases over time; the conservative (least-shielded,
  highest-penetrating-flux) epoch for a mission's radiation worst case
  is therefore its latest epoch (end of mission life), not its launch
  epoch.
- Low-inclination LEO ground tracks stay close to the geomagnetic
  equator, where the cutoff is highest, so most of the orbit is
  well-shielded from low-rigidity GCR/SEP flux; higher-inclination and
  polar orbits cross high geomagnetic latitudes where the cutoff falls
  toward zero, so shielding cannot be credited there regardless of
  orbit altitude.
- This leaf scopes the vertical-cutoff-rigidity formula, its epoch
  scaling, and per-location/per-orbit penetration and shielding
  accounting only. Selecting the GCR/SEP reference spectra that the
  cutoff is applied against is the sibling e1004-gcr leaf; rolling the
  shielded result into the mission radiation environment specification
  is the sibling e1004-rad-env-spec leaf.

## Workflow

1. For each location or orbit sample of interest, record the
   geomagnetic latitude (degrees), the radial distance from the dipole
   center (Earth radii), and the mission epoch (calendar year) the
   sample applies to.
2. Compute the epoch-scaled Størmer constant by applying the dipole
   moment's secular decay coefficient to the reference-epoch constant;
   reject an epoch so far removed from the reference that the scaled
   constant would be non-physical (zero or negative).
3. Apply the Størmer vertical cutoff formula (Størmer constant times
   cos^4(geomagnetic latitude), divided by radial distance squared) to
   get the cutoff rigidity at that location and epoch.
4. For a charged-particle population of a given rigidity (or rigidity
   threshold of interest for the analysis), verify whether that
   rigidity is at or above the local cutoff; mark it as penetrating
   (unshielded) if so, excluded (shielded) otherwise.
5. For a full orbit, repeat steps 1-4 across equal-time-weighted ground-
   track samples and compute the fraction of orbit time the location is
   unshielded (penetrating) for the threshold rigidity of interest.
6. When the mission specifies an allowable unshielded-time budget for
   the analysis case, compare the computed unshielded fraction against
   it; when no budget has been captured yet, treat any nonzero
   unshielded fraction as itself a finding needing that budget defined
   rather than silently passing.
7. For a worst-case mission-lifetime assessment, select the epoch that
   minimizes the cutoff (given the secular decay direction, the later
   of the mission start/end epochs) and use that epoch's cutoff, not
   the launch epoch's, as the conservative case.

## Pitfalls

- Using the mission launch epoch's Størmer constant for a worst-case
  radiation assessment instead of the end-of-mission epoch, understating
  the unshielded fraction because the field has weakened by then.
- Treating a single-epoch cutoff calculation as valid for an entire
  multi-year mission rather than re-deriving it (or bounding it) per the
  epoch's dipole moment.
- Assuming an orbit's inclination alone implies adequate shielding
  without checking the actual geomagnetic-latitude excursion of the
  ground track -- a nominally "low-inclination" orbit whose ground track
  still reaches moderate geomagnetic latitude retains a materially lower
  cutoff there than at the equator.
- Applying the vertical cutoff formula (zenith-arrival rigidity) to
  off-zenith arrival directions, which have a different, direction-
  dependent Størmer cutoff (the east-west asymmetry) not covered by this
  leaf's vertical-cutoff-only scope.

## Behavior contract (gate 3)

The dipole-moment epoch scaling, Størmer constant, vertical cutoff
rigidity, penetration, orbit-level unshielded-fraction, and worst-case-
epoch-selection logic is exercised by the gate 3 contract test:
scripts/test_e1004_b8_stormer.py against
scripts/e1004_b8_stormer_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_b8_stormer.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
