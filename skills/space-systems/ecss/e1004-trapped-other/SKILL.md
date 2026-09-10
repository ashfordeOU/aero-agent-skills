---
name: e1004-trapped-other
description: "Use when determining how the trapped-radiation environment applies to a non-LEO/GEO/MEO orbit (HEO, GTO, interplanetary transfer) under ECSS-E-ST-10-04C: determine the orbit regime from perigee/apogee altitude, split the trajectory into segments inside versus beyond the geomagnetically trapped domain using the magnetopause standoff distance, verify both trapped species (proton and electron) are covered wherever trapped-domain dwell exists, and hand off out-of-domain segments to the interplanetary radiation leaves rather than silently dropping them. Trigger: HEO, GTO, geostationary transfer orbit, highly elliptical orbit, interplanetary trajectory, escape trajectory, trapped radiation, magnetopause standoff, Van Allen belt crossing, e-st-10-04, ecss, space environment, radiation environment."
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
  tags: [ecss, e-st-10-04c, trapped-radiation, heo, gto, interplanetary, magnetopause, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Trapped Radiation Environment for Other Orbits (space-systems/ecss/e1004-trapped-other)

Use when the task is categorizing the trapped-radiation environment under
ECSS-E-ST-10-04C clause 9.2 for a mission orbit that does not sit wholly
inside a single trapped-belt region already covered by a dedicated leaf --
highly elliptical orbits (HEO), geostationary transfer orbits (GTO), and
trajectories that eventually leave the magnetosphere entirely
(interplanetary transfer, lunar transfer, escape trajectories).

## Domain quick reference

- The dedicated sibling leaves (`e1004-trapped-leo`, `e1004-meo-meov2`,
  and the GEO leaf) each assume the spacecraft stays within one
  characteristic band of the trapped-belt structure for the whole orbit.
  HEO and GTO instead sweep radially through the slot region, the outer
  electron belt, and the inner proton belt on every revolution, and an
  interplanetary transfer additionally leaves the trapped-belt structure
  behind entirely partway through the mission.
- The Earth's magnetosphere -- and with it the trapped-radiation
  population -- does not extend indefinitely. Its outer boundary, the
  magnetopause, sits at a nominal subsolar standoff distance on the
  order of 10 Earth radii, compressed to roughly 6 Earth radii or less
  under strong solar-wind/storm forcing. Beyond that boundary there is
  no trapped population to characterize; the applicable environment
  becomes the interplanetary one (GCR, SEP -- see the sibling
  `e1004-gcr` and SEP leaves), not a trapped-belt model.
- A trajectory segment's dwell must therefore be split into two
  domains: inside the magnetopause standoff distance ("trapped
  domain", where a trapped-belt flux model applies) and outside it
  ("interplanetary domain", where it does not). Treating a
  beyond-magnetopause segment as still trapped overstates trapped dose;
  silently dropping it instead of handing it to the interplanetary
  leaves understates total mission radiation exposure.
- Wherever trajectory dwell falls inside the trapped domain, both
  trapped species -- proton and electron -- must be covered by the
  analysis, since HEO/GTO/interplanetary-transfer trajectories cross
  both the proton and electron belt structure on every pass through the
  trapped domain, unlike an orbit confined to a single belt where one
  species can sometimes dominate.
- This leaf scopes orbit-regime categorization, trapped-domain segment
  splitting against the magnetopause boundary, and required-species
  coverage verification only. Per-segment flux/fluence table lookup for
  the crossed L-shells is the same interpolation problem already solved
  by the LEO/MEO/GEO leaves and should be reused per segment, not
  reimplemented here.

## Workflow

1. Record the mission's perigee and apogee altitude (apogee `None` for
   an escape/hyperbolic trajectory with no bounded apogee), and whether
   the assessment should use the nominal or storm-compressed
   magnetopause standoff distance.
2. Categorize the orbit regime from perigee/apogee altitude: reject
   (and redirect to the dedicated leaf) an orbit that lies wholly
   within the LEO, MEO, or GEO band; otherwise categorize it as `"gto"`
   (low perigee, apogee near the geosynchronous band), `"heo"` (apogee
   above the geosynchronous band), or `"interplanetary_transfer"`
   (unbounded apogee).
3. Break the trajectory into radial-distance/dwell-time segments (one
   per sampled point along the orbit or transfer trajectory) and split
   their total dwell time into trapped-domain seconds and
   interplanetary-domain seconds using the magnetopause standoff
   distance for the chosen (nominal or compressed) solar-wind
   condition.
4. Feed each trapped-domain segment's radial distance (converted to
   McIlwain L-shell) into the same per-L-shell flux interpolation used
   by the LEO/MEO/GEO leaves to get its differential flux, then
   dwell-time-weight across the trapped-domain segments the same way
   the MEO leaf dwell-weights L-shell crossings.
5. Verify that both required trapped species (proton and electron) are
   covered by the analysis case wherever trapped-domain dwell is
   nonzero; flag missing species coverage as a finding rather than
   silently omitting one species from the resulting spectrum.
6. Route every interplanetary-domain segment's dwell time to the
   interplanetary radiation leaves (GCR, SEP) instead of discarding it,
   and record the excluded-segment count so the hand-off is auditable.
7. Mark the mission's trapped-environment assessment compliant only
   when the orbit regime was successfully categorized, at least one
   trajectory segment was supplied, and no required-species-coverage
   finding remains open.

## Pitfalls

- Applying a single-L-shell LEO/MEO/GEO flux lookup to a GTO/HEO orbit
  without dwell-time weighting across the full range of L-shells it
  crosses each revolution, which misrepresents both the flux magnitude
  and which belt region dominates.
- Treating trajectory dwell beyond the magnetopause standoff distance
  as still part of the trapped-belt population, overstating trapped
  proton/electron dose for the mission's interplanetary-transfer
  segments.
- Silently dropping beyond-magnetopause dwell time instead of routing
  it to the GCR/SEP leaves, which understates total mission radiation
  exposure even though the trapped-belt contribution for that segment
  is correctly excluded.
- Using the nominal (uncompressed) magnetopause standoff distance for a
  worst-case radiation design margin instead of the storm-compressed
  distance, which understates trapped-domain dwell time for segments
  near the nominal boundary.
- Covering only the proton or only the electron trapped population for
  an HEO/GTO/interplanetary-transfer trajectory, when both belts are
  crossed on every pass through the trapped domain.

## Behavior contract (gate 3)

The orbit-regime categorization, magnetopause-domain segment splitting,
and required-species-coverage logic is exercised by the gate 3 contract
test: scripts/test_e1004_trapped_other.py against
scripts/e1004_trapped_other_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_trapped_other.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
