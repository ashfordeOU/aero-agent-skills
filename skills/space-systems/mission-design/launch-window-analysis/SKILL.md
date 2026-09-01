---
name: launch-window-analysis
description: "Use when computing launch windows and launch geometry for orbital missions: launch azimuth for a target inclination from cos(inc) = cos(lat) * sin(az), the daily launch window when the target orbit plane passes through the launch site (window center and half-width from the plane-crossing geometry), sun-synchronous LTAN to RAAN conversion, the plane change delta-v penalty for out-of-plane launches, window duration from the orbit plane regression rate versus Earth rotation, and pass elevation and lighting checks. Produces the azimuth, window open/close times, RAAN, delta-v penalty, and constraint verdicts for the launch. Trigger: launch window, launch azimuth, inclination, sun-synchronous, ltan, raan, plane change, delta-v, orbital plane, direct injection, ksc."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: mission-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: mission-design
  tags: [launch-window, launch-azimuth, launch, azimuth, window, inclination, sun-synchronous, ltan, raan, delta-v, plane-change, direct-injection, elevation, beta-angle, ksc, mission-design]
  version: 0.1.0
  author: AeroSkills
---

# Launch Window Analysis (space-systems/mission-design/launch-window-analysis)

Use when the task is launch geometry for an orbital mission: finding the
launch azimuth that direct-injects into a target inclination, locating
the daily launch window when the target orbit plane sweeps through the
launch site, converting a sun-synchronous local time of ascending node
(LTAN) into a RAAN, sizing the plane change delta-v penalty for an
out-of-plane launch, computing the window duration from the orbit plane
regression rate versus Earth rotation, and checking pass elevation and
lighting constraints.

Units convention (stated once): angles in degrees, time in seconds,
speed in km/s, altitude and radius in km. The geometry is classical
two-body plus the rotating Earth; it is a mission design tool, not a
flight dynamics product. A real program validates against the actual
orbit determination and the launch vehicle ascent profile.

## Domain quick reference

- Launch azimuth for direct injection: cos(inc) = cos(lat) * sin(az),
  so az = asin(cos(inc) / cos(lat)). Due east (az = 90 deg) gives
  inc = lat. Direct injection requires |lat| <= inc <= 180 - |lat|;
  outside that range the azimuth formula has no real solution and the
  function raises ValueError. Retrograde targets (inc > 90) launch
  westward: az = 180 - asin(cos(inc) / cos(lat)). From KSC (28.5 N):
  inc 28.5 gives az 90.0; inc 51.6 gives az 44.98; inc 98 gives
  az 189.11.
- Daily window geometry: the launch site is in the orbit plane when its
  local sidereal time LST = GMST + site_lon equals the plane crossing
  right ascension. Ascending-side crossing at raan + asin(t), descending
  side at raan + 180 - asin(t), with t = tan(lat) / tan(inc). The window
  center is that instant; the half-width is the time the site stays
  within the out-of-plane tolerance. For KSC into 51.6 deg with raan 100
  and a 5 deg tolerance: center 49326 s after the reference epoch,
  half-width 1865 s, window duration about 62 min.
- Sun-synchronous LTAN to RAAN: raan = sun_ra + 15 * (LTAN - 12), mod
  360. LTAN 10:30 gives raan 337.5 at sun_ra 0; LTAN 18:00 gives 90;
  LTAN 06:00 (dawn-dusk) gives 270; LTAN 12:00 gives sun_ra.
- Plane change delta-v: dv = 2 * v * sin(di / 2). A 10 deg plane change
  at 7.8 km/s costs 1.360 km/s; a 20 deg change costs 2.709 km/s (the
  2.72 km/s figure sometimes quoted for a "10 deg" change is
  2 * v * sin(10 deg), which is the half-angle formula applied at 20 deg).
- Window period and regression: successive windows recur every
  360 / (earth_rate - node_regression) days with earth_rate 360.9856
  deg/day (sidereal). A sun-synchronous orbit (node_regression
  +0.9856 deg/day) gives a period of exactly 1.0 day: the window falls
  at the same local solar time every day. With no regression the period
  is 0.99727 days.
- Pass elevation: at the crossing instant the site lies on the ground
  track (a zenith pass), so the satellite elevation is 90 deg there.
  Near the crossing, e = atan2(cos(mu) - R / r, sin(mu)) with
  mu = v * t / r and v = sqrt(mu_earth / r). The horizon is at
  mu = acos(R / r), about 305 s either side for a 400 km orbit.
- Lighting (beta angle): sin(beta) = n_hat . s_hat between the orbit
  normal and the sun. Dawn-dusk orbits sit near |beta| = 90 deg at
  equinox (sun in the plane); noon-midnight orbits near 0. For LTAN
  10:30 at equinox, beta is about -22.3 deg.

## Workflow

1. State the target inclination, the launch site latitude and longitude,
   and (for sun-synchronous orbits) the LTAN or the RAAN.
2. Get the direct-injection azimuth with
   launch_azimuth_for_inclination, or check feasibility first with
   direct_injection_feasible. If the inclination is below the site
   latitude the function raises ValueError: the orbit cannot be
   direct-injected, and the alternative is a plane change (step 5).
3. Convert a sun-synchronous LTAN to the RAAN with
   sun_sync_ltan_to_raan (sun_ra 0 at the vernal equinox; use the
   actual sun right ascension otherwise).
4. Compute the window with daily_window_center_halfwidth or
   window_open_close from the inclination, site latitude/longitude,
   RAAN, GMST at the reference epoch, and the out-of-plane tolerance.
   Pass node_regression_deg_per_day = 0.9856 for sun-synchronous
   orbits. The center and half-width come back in seconds from the
   reference epoch; the open/close times and duration in
   window_open_close, with the repeat period.
5. If the launch is out of plane (dogleg or inclination below the
   direct-injection limit), size the penalty with plane_change_delta_v
   from the inclination change and the orbital speed.
6. Check the pass with elevation_angle_at_crossing (visibility around
   the crossing, horizon crossing time) and the lighting with
   beta_angle (sun relative to the plane). Compare against the mission
   constraints: elevation mask, beta limits for power and thermal.
7. Sanity-check: an eastward launch from KSC into 51.6 deg flies at
   about 45 deg azimuth; a sun-synchronous 10:30 window repeats at the
   same local time daily; a 10 deg plane change at LEO speeds costs
   about 1.36 km/s.

## Worked example

Mission: launch from KSC (28.5 N, 80.6 W) into a 51.6 deg orbit with
raan 100 deg, GMST 0 deg at the reference epoch, 5 deg out-of-plane
tolerance, orbital speed 7.8 km/s.

- launch_azimuth_for_inclination(51.6, 28.5) = 44.98 deg (about
  45 deg, northeast).
- window_open_close(51.6, 28.5, 100.0, -80.6, 0.0, 5.0): center
  49326 s, open 47462 s, close 51191 s, duration 3729 s (about
  62 min), period 0.99727 days (sidereal repeat).
- With node_regression 0.9856 deg/day (a sun-synchronous-like plane)
  the period becomes exactly 1.0 day.
- plane_change_delta_v(10.0, 7.8) = 1.360 km/s if the launch must be
  corrected by a 10 deg plane change.
- elevation_angle_at_crossing(400.0, 0.0) = 90 deg at the crossing,
  falling to 24.97 deg at 100 s and below the horizon after about
  305 s.

Sun-synchronous variant: LTAN 10:30 gives raan 337.5 (sun_ra 0); with
gmst 45 the window center is 2088 s after the reference epoch with a
half-width of 1384 s (about 46 min total).

## Verification checklist

- Azimuth for inc equal to the site latitude is exactly 90 deg (due
  east), and inc 51.6 from KSC lands in 40 to 45 deg.
- An inclination below the site latitude raises ValueError, for the
  azimuth function and for the window function (the plane never crosses
  the site).
- plane_change_delta_v matches 2 * v * sin(di / 2): 1.360 km/s at
  (10 deg, 7.8 km/s) and 2.709 km/s at (20 deg, 7.8 km/s), within 1%
  of the 2.72 km/s reference.
- LTAN conversions: 10:30 to 337.5, 18:00 to 90, 06:00 to 270 at
  sun_ra 0.
- The sun-synchronous window period is exactly 1.0 day; the no-regression
  period is 0.99727 days.
- Elevation at the crossing instant is 90 deg; the 400 km horizon
  crossing sits at about 305 s.
- Run the gate 3 contract test: scripts/test_launch_window.py must
  pass offline with all assertions green.

## Scripts

- scripts/launch_window_logic.py: the six core functions plus
  direct_injection_feasible and beta_angle. Pure Python 3, stdlib only.
- scripts/test_launch_window.py: gate 3 behavior contract test (stdlib
  unittest, offline, deterministic, 22 tests). Run from the repo root:
  python3 skills/space-systems/mission-design/launch-window-analysis/scripts/test_launch_window.py

## References

- references/launch-window-engineering-notes.md: derivations of the
  crossing geometry, the half-width expansion, the LTAN/RAAN
  relationship, and the ECSS framing of mission analysis.

## Related skills

- mission-delta-v-budget (../mission-delta-v-budget): the plane change
  delta-v from this skill feeds the mission delta-v budget.
- radiation-debris (../radiation-debris): environment assessment for
  the orbit the launch window targets.
- entry-descent-landing (../entry-descent-landing): the other end of
  the mission, descent and landing of the spacecraft.

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (space
  engineering, system engineering general requirements) frames the
  mission analysis and the ECSS lifecycle around launch window work;
  the formulas above are common space engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
