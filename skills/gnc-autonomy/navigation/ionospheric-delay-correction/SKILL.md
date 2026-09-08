---
name: ionospheric-delay-correction
description: "Use when you must correct the L1 pseudorange for the broadcast ionospheric delay: apply the klobuchar-broadcast-model to the user position and the satellite line of sight, compute the geomagnetic latitude of the ionospheric pierce point from the earth-centred angle and the azimuth, evaluate the amplitude and period quartic polynomials in the broadcast alpha and beta coefficients at that geomagnetic latitude, form the vertical delay from the 5 ns base and the day-curve shape about the 14:00 local-time peak, and map the vertical delay to the slant delay with the elevation obliquity factor. Produces the pierce-point geomagnetic latitude, the amplitude and period coefficients, the vertical delay in seconds and the slant ionospheric delay in seconds and metres that gate the L1 pseudorange correction before positioning. Trigger: klobuchar broadcast model, ionospheric delay correction, slant delay correction, pierce point geometry, broadcast alpha and beta coefficients."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [ionospheric-delay-correction, klobuchar-broadcast-model, slant-delay-correction, pierce-point-geometry, broadcast-alpha-beta-coefficients]
  version: 0.1.0
  author: AeroSkills
---

# Ionospheric Delay Correction (gnc-autonomy/navigation/ionospheric-delay-correction)

Use when a GNSS single-frequency navigation chain must correct an L1
pseudorange for the broadcast ionospheric delay before it is passed to a
position fix. This leaf implements the Klobuchar broadcast ionospheric
delay algorithm in pure Python, stdlib only: the earth-centred angle to
the ionospheric pierce point, the subionospheric point and its
geomagnetic latitude, the local time of day, the amplitude and period
quartic polynomials in the broadcast alpha and beta coefficients, the
day-curve shape about the 14:00 local-time peak, the vertical delay with
its 5 ns night floor, and the elevation obliquity factor mapping the
vertical delay to the slant delay. It pairs with
gnc-autonomy/navigation/gnss-pseudorange-positioning, which consumes the
corrected pseudorange in its iterated least squares fix, and
gnc-autonomy/navigation/gnss-carrier-smoothing, whose ionospheric
divergence monitor tracks the code-carrier growth rate rather than the
per-source delay magnitude computed here.

## Domain quick reference

- Earth-centred angle: with E_SC = el/180 (semicircles), psi_SC =
  0.0137/(E_SC + 0.11) - 0.022; psi_deg = 180 * psi_SC.
- Subionospheric point: lat_i_SC = clamp(lat_SC + psi_SC*cos(az_rad),
  -0.416, 0.416), lon_i_SC = lon_SC + psi_SC*sin(az_rad)/cos(pi*lat_i_SC),
  with the returned longitude normalized into [-180, 180) because a
  low-elevation pierce point near the antimeridian can wrap past it.
- Pierce-point geomagnetic latitude: phi_m_SC = lat_i_SC + 0.064 *
  cos(pi*(lon_i_SC - 1.617)), the pole offset and pole longitude of the
  broadcast model in semicircles.
- Local time of day: t_local = (43200 * lon_i_SC + tow) mod 86400
  seconds, periodic in the pierce-point longitude and the GPS time of
  week.
- Amplitude and period: A = sum alpha_n * phi_m_SC^n clamped to >= 0.0,
  P = sum beta_n * phi_m_SC^n clamped to >= 72000 s, both quartic
  polynomials evaluated at phi_m in semicircles.
- Day-curve shape: x = 2*pi*(t_local - 50400)/P; for |x| < pi/2,
  c = 1 - x^2/2 + x^4/24 (day branch); otherwise c = 0.0 (night branch).
- Vertical delay: T_vert = 5e-9 + A*c seconds, never below the 5 ns base.
- Obliquity factor: F = 1 + 2*((96 - el)/90)^3, el in degrees
  (Klobuchar 1987 practical form), strictly decreasing on (0, 90].
- Slant delay: T_slant = F * T_vert; metres = seconds * c (vacuum speed
  of light, 299792458.0 m/s).
- Units: latitudes in degrees north, longitudes in degrees east
  (negative west) in [-180, 180], elevation and azimuth in degrees
  (azimuth from north, clockwise, [0, 360)), times in seconds, one
  semicircle = 180 degrees. IS-GPS-200 section 20.3.3.5.1 and RTCA
  DO-229 frame the broadcast context; the relations above are the
  standard engineering method, summary-only.

## Workflow

1. Fix the geometry: user latitude and longitude, satellite elevation
   and azimuth. Compute the earth-centred angle with
   earth_center_angle_deg, then the subionospheric point with
   subionospheric_point_deg.
2. Compute the pierce-point geomagnetic latitude with
   geomagnetic_latitude_deg, and the local time of day at the pierce
   point with local_time_seconds using the GPS time of week.
3. Evaluate the broadcast-alpha-beta-coefficient polynomials at that
   geomagnetic latitude: amplitude_seconds for A and period_seconds for
   P, each clamped per the model.
4. Form the day-curve shape with day_shape_factor at the local time and
   period, then the vertical delay with vertical_delay_seconds.
5. Map the vertical delay to the slant delay with slant_factor and
   slant_delay_seconds, the full klobuchar-broadcast-model pipeline from
   raw geometry and coefficients to the slant ionospheric delay.
6. Convert to metres with delay_meters or the slant_delay_meters
   convenience wrapper before subtracting the correction from the L1
   pseudorange.
7. Confirm the deterministic checks with the contract test
   scripts/test_ionospheric_delay_correction.py.

## Worked example

Mid-latitude user at 40.0 deg N, -105.0 deg (105 deg W), GPS time of
week 0.0 s, satellite at 40.0 deg elevation and 160.0 deg azimuth, with
the documented Klobuchar example broadcast set alpha =
[0.8382e-08, -0.7451e-08, -0.5960e-07, 0.1192e-06] and beta =
[0.1306e+06, -0.3277e+05, -0.6554e+05, 0.1311e+06].

- Earth-centred angle: earth_center_angle_deg(40.0) = 3.46274247491639
  deg.
- Subionospheric point: subionospheric_point_deg(40.0, -105.0, 40.0,
  160.0) = (36.7460864486391 deg N, -103.521982351049 deg), no latitude
  clamp engaged.
- Pierce-point geomagnetic latitude: geomagnetic_latitude_deg(36.74609,
  -103.52198) = 46.2306740519375 deg (0.256837 SC).
- Local time of day: local_time_seconds(-103.521982351049, 0.0) =
  61554.7242357482 s (17:06 local, afternoon).
- Amplitude: amplitude_seconds(alpha, 46.2306740519375) =
  4.55630181644608e-09 s. Period: period_seconds(beta, 46.2306740519375)
  = 120081.223784471 s, above the 72000 s clamp.
- Day curve: day_shape_factor(61554.7242357482, 120081.223784471) =
  0.834503142819751 (day branch).
- Vertical delay: vertical_delay_seconds(alpha, beta, 46.2306740519375,
  61554.7242357482) = 8.80224818545959e-09 s (8.802248 ns), the 5 ns
  base plus 4.556302 ns times 0.834503.
- Obliquity factor: slant_factor(40.0) = 1.48179972565158.
- Slant delay: slant_delay_seconds(alpha, beta, 40.0, -105.0, 40.0,
  160.0, 0.0) = 1.30431689463311e-08 s (13.043169 ns), and
  slant_delay_meters gives 3.910244 m.

Elevation sweep at the same user and azimuth (T_slant grows steeply
toward the horizon through the obliquity factor while the vertical
delay stays nearly flat): 10 deg gives 25.268371 ns / 7.575267 m (F
2.745010); 30 deg gives 15.879641 ns / 4.760597 m (F 1.788741); 40 deg
gives 13.043169 ns / 3.910244 m (F 1.481800); 60 deg gives 9.827876 ns /
2.946323 m (F 1.128000); 90 deg gives 8.648579 ns / 2.592779 m (F
1.000593, the zenith slant-to-vertical ratio).

## Verification

- Confirm the worked-example chain (earth-centred angle, subionospheric
  point, geomagnetic latitude, local time, amplitude, period, day
  shape, vertical delay, slant delay and slant delay in metres) matches
  the anchors above within 1e-6 relative.
- Confirm slant_factor(90.0) equals the closed form
  1 + 2*(6/90)^3 = 1.00059259259259 within 1e-12, that slant_factor is
  strictly decreasing on (0, 90], and that it approaches
  1 + 2*(96/90)^3 = 3.4272592592592593 as elevation approaches zero.
- Confirm day_shape_factor(50400, P) = 1.0 exactly (the 14:00 peak) and
  that vertical_delay_seconds at t_local 3600 returns exactly the 5e-9 s
  night floor.
- Confirm amplitude_seconds and period_seconds collapse to alpha0 and
  beta0 at the geomagnetic equator (phi_m = 0), and that a negative raw
  amplitude clamps to 0.0 while a raw period below 72000 s clamps to
  72000.0.
- Confirm subionospheric_point_deg normalizes a longitude that wraps
  past the antimeridian into [-180, 180) without raising.
- Confirm every non-physical input (elevation outside (0, 90], user
  latitude/longitude/azimuth out of range, GPS time of week out of
  [0, 604800), a malformed or negative-constant coefficient set, an
  out-of-range geomagnetic latitude or local time, a negative delay)
  raises ValueError, including through the full slant_delay_seconds
  pipeline.
- Run the contract test offline: python3
  scripts/test_ionospheric_delay_correction.py (35 tests,
  deterministic).

## Related leaves

- gnc-autonomy/navigation/gnss-carrier-smoothing: owns the carrier
  smoothing recursion and the ionospheric divergence monitor on the
  code-carrier growth rate, not the per-source delay magnitude.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: consumes the
  corrected pseudorange in its iterated least squares fix and residual
  statistics.
- gnc-autonomy/navigation/gnss-rtk-positioning: the differential
  technique that cancels most of the ionospheric delay through double
  differences instead of modeling it per source.

## Pitfalls

- Feeding the vertical delay straight into the pseudorange correction:
  the model corrects a slant line of sight, so vertical_delay_seconds
  must always be mapped through slant_factor before it is subtracted
  from a real pseudorange (3.910244 m slant against 2.638848 m vertical
  in the worked example).
- Treating psi_SC or phi_m_SC in degrees: the amplitude and period
  polynomials and the pole-offset relations are pinned in semicircles
  (1 SC = 180 deg); feeding degree values directly into the polynomial
  sum inflates every coefficient term by a factor of 180.
- Skipping the longitude normalization: a low-elevation pierce point
  near the antimeridian (subionospheric_point_deg(0.0, 179.0, 5.0,
  90.0) unwraps to -167.061613 deg) must be wrapped into [-180, 180)
  before it feeds local_time_seconds or geomagnetic_latitude_deg, or
  the periodic pole and local-time relations see the wrong branch.
- Reporting the raw polynomial sum instead of the clamped model value:
  a negative raw amplitude clamps to 0.0 and a raw period below 72000 s
  clamps to 72000.0 by model definition, not as an error condition.
- Confusing this leaf with gnss-carrier-smoothing's ionospheric
  divergence monitor: that sibling tracks the code-minus-carrier growth
  rate of an already-smoothed range, never the per-source delay
  magnitude computed here, and this leaf never touches the Hatch
  recursion or a smoothed range.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ionospheric_delay_correction.py

The test covers the worked-example chain through every step of the
Workflow above (earth-centred angle, subionospheric point, geomagnetic
latitude, local time, amplitude and period polynomials, day-curve
shape, vertical and slant delay, metre conversion), the elevation sweep
with its per-row obliquity factors and monotone slant metres, the
obliquity closed-form and low-elevation limit, the zenith
slant-to-vertical ratio, the peak and night-floor identities, the
geomagnetic-equator polynomial collapse, the amplitude and period
clamps, longitude normalization, determinism, physical sanity bounds,
and ValueError rejection of every non-physical input including through
the full pipeline.

## Compliance

- Standards referenced, not reproduced: RTCA DO-229 and IS-GPS-200
  section 20.3.3.5.1 define the broadcast ionospheric correction
  algorithm; the relations above are a summary paraphrase per
  standards-map.yaml, never verbatim text.
- compliance: STANDARDS-REF, gated: false.
