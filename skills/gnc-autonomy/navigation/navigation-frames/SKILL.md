---
name: navigation-frames
description: "Use when you must convert navigation coordinate frames for an aircraft or spacecraft: transform geodetic latitude, longitude, and altitude on the WGS-84 ellipsoid into ECEF position, build the ECEF to NED rotation matrix at a reference point, resolve velocity into north, east, and down components, and compute the Earth rotation angle from a Julian date for inertial to Earth-fixed frames. Produces ECEF coordinates in meters, the NED rotation matrix, NED velocity, and GMST rotation angle in radians. Trigger: navigation frames, ecef, ned, geodetic, wgs 84, earth rotation, coordinate conversion."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [navigation-frames, ecef, ned, geodetic, wgs-84, earth-rotation, coordinate-conversion, gmst]
  version: 0.1.0
  author: AeroSkills
---

# Navigation Coordinate Frames (gnc-autonomy/navigation/navigation-frames)

Use when you need coordinate frame conversions for navigation: WGS-84
geodetic position to ECEF, the ECEF to NED rotation at a reference
point, and the Earth rotation angle for inertial to Earth-fixed frames.

## Domain quick reference

- WGS-84 (World Geodetic System 1984) defines the reference ellipsoid
  with semi-major axis a = 6378137.0 m and flattening
  f = 1/298.257223563.
- Geodetic coordinates (latitude, longitude, altitude) locate a point
  relative to the ellipsoid; ECEF is a Cartesian Earth-fixed frame with
  the Z axis along the spin axis toward the north pole.
- NED is the local tangent-plane frame at a reference latitude and
  longitude: north, east, and down axes, with down positive.
- The GMST Earth rotation angle relates inertial and Earth-fixed frames;
  it advances about 360.9856 degrees per mean solar day, and the Earth
  rotation rate is 7.2921159e-5 rad/s.
- Units: meters, radians, days (UT1), m/s. Angles enter as radians;
  GMST is returned in radians in [0, 2*pi).

## Workflow

1. Convert the geodetic position with
   geodetic_to_ecef(lat_rad, lon_rad, alt_m) to ECEF position in meters.
2. Build the frame rotation with ecef_to_ned(lat_ref_rad, lon_ref_rad)
   at the navigation reference point.
3. Transform the ECEF velocity with ned_velocity(vecef, r) into north,
   east, and down components in m/s.
4. For inertial to Earth-fixed alignment, compute
   gmst_rotation_angle(jd_ut1) from the Julian date (UT1), returned in
   radians mod 2*pi.

## Pitfalls

- Mixing degrees and radians: all angles are radians in the logic
  functions, so convert degrees with math.radians before calling.
- Using the geodetic position as the reference point for the NED
  rotation instead of the navigation reference point.
- Forgetting that altitude is height above the ellipsoid, not mean sea
  level, so geoid undulation can bias the result.
- Confusing GMST with a full 360 degree day: the sidereal rotation is
  about 360.9856 degrees per day.
- Reading NED signs loosely: down is positive, so a climbing vehicle has
  a negative vd component.

## Behavior contract (gate 3)

The frame conversion logic is exercised by the gate 3 contract test:
scripts/test_navigation_frames_logic.py against
scripts/navigation_frames_logic.py (stdlib unittest, offline).
Run:
python3 skills/gnc-autonomy/navigation/navigation-frames/scripts/test_navigation_frames_logic.py

## Compliance

- The ECSS series (E-ST-10C, E-ST-40C, Q-ST-80C, M-ST-40C) covers space
  engineering and software; it is free to download and summarized and
  referenced only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
