---
name: e1004-stormer
description: "Use when scoping geomagnetic shielding for LEO solar-energetic-particle (SEP) and galactic-cosmic-ray (GCR) environments under ECSS-E-ST-10-04C clause 9.2.4 and Annex B.8: compute the Stormer vertical cutoff rigidity at a point from its geomagnetic latitude and radial distance, determine whether a particle of given rigidity is geomagnetically excluded or allowed to reach that point, build the exposure-fraction profile across an LEO ground track, and verify the assessment before escalating to full trajectory tracing when the vertical-cutoff approximation cannot be trusted. Trigger: Stormer cutoff, vertical cutoff rigidity, geomagnetic shielding, geomagnetic cutoff, trajectory tracing, penumbra, LEO SEP shielding, GCR geomagnetic cutoff, rigidity cutoff, e-st-10-04, ecss."
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
  tags: [ecss, e-st-10-04c, space-environment, geomagnetic-shielding, stormer-cutoff, trajectory-tracing, leo, sep, gcr]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Geomagnetic Shielding — Stormer Cutoffs (space-systems/ecss/e1004-stormer)

Use when the task is applying geomagnetic shielding to solar energetic
particle (SEP) and galactic cosmic ray (GCR) environments for a LEO
mission under ECSS-E-ST-10-04C clause 9.2.4 and Annex B.8: deciding how
much of the unshielded SEP/GCR spectrum actually reaches a given point
in LEO once Earth's magnetic field is accounted for, and choosing
between the closed-form vertical cutoff approximation and full
trajectory tracing.

## Domain quick reference

- Earth's internal magnetic field deflects lower-rigidity charged
  particles away from a given point; a particle can only arrive there
  if its rigidity (momentum per unit charge) is at or above that
  point's cutoff rigidity. The unshielded SEP/GCR environment (from the
  sibling leaves e1004-sep-fluence, e1004-sep-peakflux, e1004-gcr) is
  the input this leaf attenuates for a specific point or orbit.
- The Stormer vertical cutoff rigidity is the standard first-order
  approximation: it assumes a dipole field and a particle arriving
  exactly along the local vertical (zenith) direction. It depends only
  on the point's geomagnetic latitude and its radial distance from the
  dipole center, falling off with cos(latitude)^4 and with 1/r^2 --
  highest at the geomagnetic equator, lowest (near zero) at the
  geomagnetic poles.
- The vertical cutoff is an approximation, not the true cutoff. Annex
  B.8 flags two conditions where it is not sufficient and the rigorous
  alternative -- trajectory tracing (numerically integrating candidate
  particle trajectories backward through a realistic, non-dipole field
  model) -- is required: (1) resolving the penumbra, the band of
  rigidities straddling the vertical cutoff where some trajectories are
  allowed and others forbidden even though the simple formula gives one
  number, and (2) particle arrival directions other than local
  vertical, which real angular distributions include.
- A LEO orbit's ground track sweeps a range of geomagnetic latitudes
  (more of that range for higher inclinations), so the local cutoff --
  and therefore SEP/GCR exposure -- varies continuously along the
  orbit; a single-point cutoff is not representative of the mission
  unless the orbit is confined to a narrow latitude band.

## Workflow

1. Obtain the unshielded SEP or GCR rigidity spectrum for the mission
   from the applicable sibling leaf (e1004-sep-fluence, e1004-sep-
   peakflux, or e1004-gcr) -- this leaf does not derive that spectrum,
   it attenuates it for geomagnetic shielding.
2. For each point of interest (or each sampled point along the orbit
   ground track), obtain its geomagnetic latitude and radial distance
   in Earth radii from the geomagnetic field leaf (e1004-geomag, B,L
   coordinates), then compute the Stormer vertical cutoff rigidity at
   that point.
3. For a given particle rigidity, determine whether it is allowed to
   reach each point (rigidity at or above the local cutoff) or excluded
   (below cutoff); tabulate this across the orbit ground track to get
   the exposure-fraction profile for that rigidity.
4. Decide the required shielding method before reporting a result:
   default to the vertical Stormer cutoff; escalate to trajectory
   tracing whenever the penumbra must be resolved (e.g. rigidities close
   to the local cutoff drive a pass/fail result) or whenever the
   analysis needs arrival directions other than local vertical (e.g.
   detailed single-event-effect worst-case or dose mapping).
5. Apply the resulting access/exclusion test to attenuate the
   unshielded spectrum at each point or orbit-averaged, producing the
   geomagnetically-shielded SEP/GCR environment that feeds dose and
   single-event-effect analyses.
6. Verify the assessment before use: confirm the method actually
   matches step 4's decision, and that the exposure fraction reported
   is consistent with the per-point allowed/excluded results (not an
   independently guessed number).

## Pitfalls

- Applying one single-point vertical cutoff rigidity to an entire LEO
  orbit that actually sweeps a wide latitude range, instead of
  profiling the cutoff along the ground track.
- Treating the vertical Stormer cutoff as exact near the cutoff
  rigidity, where the real penumbra means some trajectories at that
  rigidity are allowed and others are forbidden -- reporting a single
  pass/fail without flagging that trajectory tracing is needed there.
- Using the vertical-cutoff approximation for analyses that depend on
  off-vertical arrival directions (it only models local-zenith
  incidence).
- Forgetting that this leaf attenuates an already-derived unshielded
  SEP/GCR spectrum; it does not select or compute that spectrum itself
  (see e1004-sep-fluence, e1004-sep-peakflux, e1004-gcr).

## Behavior contract (gate 3)

The cutoff-rigidity calculation, access/exclusion test, orbit exposure
profile, flux attenuation, and method-selection logic are exercised by
the gate 3 contract test: scripts/test_e1004_stormer.py against
scripts/e1004_stormer_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_stormer.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
