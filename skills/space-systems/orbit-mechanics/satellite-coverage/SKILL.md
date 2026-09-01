---
name: satellite-coverage
description: "Use when you must analyze satellite ground coverage and access geometry: compute the instantaneous access circle central angle for a satellite from the orbital altitude and the minimum elevation angle constraint, estimate the swath width and the coverage fraction of a region or the globe, derive the maximum off-nadir angle and the elevation and look-angle geometry at a ground station, and evaluate the access time per pass and the revisit time. Produces the central angle, swath width, off-nadir angle, access time, and coverage fraction that gate ground station visibility and constellation coverage analysis. Trigger: satellite coverage, coverage analysis, access circle, central angle, swath width, off-nadir angle, elevation angle, revisit time, coverage fraction, ground station visibility."
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
  subdomain: orbit-mechanics
  tags: [satellite-coverage, coverage-analysis, access-circle, central-angle, swath-width, off-nadir-angle, elevation-angle, coverage-fraction, revisit-time, access-time, minimum-elevation, constellation-coverage]
  version: 0.1.0
  author: AeroSkills
---

# Satellite Ground Coverage (space-systems/orbit-mechanics/satellite-coverage)

Use when the task is satellite ground coverage and access analysis:
compute the instantaneous access circle from the orbital altitude and
the minimum elevation angle, estimate the swath width and the coverage
fraction, or evaluate the access time per pass, the revisit time, and
the off-nadir and elevation geometry at a ground station.

## Domain quick reference

- Spherical Earth model: Re = 6371 km, orbit radius r = Re +
  altitude_km. Coverage numbers shift only a few percent against an
  oblate (WGS84) Earth, which matters for precise station masks, not
  for first-order coverage sizing.
- Minimum elevation angle eps (deg) is the mask at the ground point;
  eps = 0 is horizon access, typical masks run 5-10 deg to clear
  terrain and atmosphere.
- Earth central angle eta (deg) of the access circle edge:
  eta = 90 - eps - asin((Re / r) * cos(eps)). This is the angular
  radius at the Earth center of the circle of ground points that see
  the satellite at or above eps.
- Maximum off-nadir angle theta_max = asin((Re / r) * cos(eps)) is the
  look angle at the satellite to the access circle edge. The limb
  triangle closes with eta + eps + theta_max = 90 deg.
- Swath width: the full access strip across nadir, the spherical arc
  W = 2 * Re * eta_rad. The access circle ground radius is Re *
  eta_rad.
- Global coverage fraction of one access circle over the whole sphere:
  (1 - cos(eta_rad)) / 2. A geostationary satellite at horizon access
  covers 42.4% of the globe; a 400 km satellite covers 2.95% at any
  instant.
- Worked anchors: 400 km altitude with eps = 0 gives eta = 19.79 deg,
  swath 4401.7 km; 500 km with eps = 10 deg gives eta = 14.06 deg,
  swath 3126.0 km; GEO (35786 km) with eps = 5 deg gives eta = 76.34
  deg, swath 16977.5 km.
- Access time per pass (first-order): T_orbit * (2 * eta_deg / 360)
  for a ground point crossing the access circle center; off-center
  crossings give shorter times, and the fraction is exact only for a
  polar pass over the subsatellite track.
- Revisit time is set by the orbit repeat cycle and the constellation
  phasing: a single satellite revisits after the repeat cycle from
  ground-track-repeat; adding planes and phasing in a Walker-delta
  constellation shortens the worst-case gap to the constellation
  revisit time.

## Workflow

1. Take the orbital altitude in km and the minimum elevation angle in
   degrees (0 to 90, usually 5-10).
2. Compute the access circle with central_angle and
   access_circle_radius_km.
3. Estimate the ground coverage width with swath_width and the
   off-nadir limit with max_off_nadir.
4. Evaluate the coverage fraction with coverage_fraction_global for
   globe coverage or coverage_fraction_region for a target region.
5. Convert to access time per pass with access_time_per_pass using the
   orbital period; compare the revisit time against the orbit repeat
   cycle for the mission gap requirement.
6. For constellations, treat the Walker-delta pattern (N satellites, P
   planes, F phasing) as a coverage ensemble: each satellite carries
   its own access circle and the joint coverage fraction rises toward
   1.0 as the circles overlap, with the revisit gap set by the largest
   hole between circles.

## Pitfalls

- Routing link-budget questions here: EIRP, path loss, C/N0, Eb/N0,
  and margin belong to communication-link-budget; coverage analysis
  sizes geometry, not the radio link.
- Routing repeat-cycle questions here: nodal period, revolutions per
  day, and integer repeat cycles belong to ground-track-repeat; the
  revisit time read from this leaf assumes the repeat cycle is already
  known.
- Routing shadow questions here: beta angle, shadow fraction, and
  eclipse duration belong to eclipse-time; an access circle is about
  visibility geometry, not sunlight.
- Using degrees in the arc formulas: swath and radius take eta in
  radians; feeding the degree value in directly overstates the swath
  by a factor of pi / 180.
- Forgetting the elevation mask: the access circle shrinks fast with
  eps (500 km: 19.2 deg at eps = 0, 14.1 deg at eps = 10), so a
  horizon assumption overstates coverage.
- Treating swath as chord instead of arc: the spherical arc length
  2 * Re * eta_rad is the ground distance; the straight-line chord is
  shorter and is not the covered strip.
- Summing coverage fractions: instantaneous single-satellite fractions
  overlap; global coverage over time needs the ensemble geometry, not
  a per-satellite sum.
- Using the solar day instead of the orbital period for access time:
  access time per pass scales with the orbital period, not 86400 s.

## Behavior contract (gate 3)

The access circle central angle, swath width, off-nadir angle, access
circle radius, coverage fractions, and access time per pass logic is
exercised by the gate 3 contract test: scripts/test_satellite_coverage.py
against scripts/satellite_coverage_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_satellite_coverage.py

## Compliance

- Standards referenced, not reproduced: ECSS series text is copyright
  ESA; the access circle, swath, and coverage fraction geometry is
  common astrodynamics, summary-only per standards-map.yaml (ecss is a
  free ESA download).
- compliance: STANDARDS-REF, gated: false.
