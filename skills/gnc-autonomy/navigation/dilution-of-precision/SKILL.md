---
name: dilution-of-precision
description: "Use when you must evaluate GNSS positioning accuracy from satellite geometry: build the geometry matrix H from satellite line-of-sight unit vectors, form the normal matrix H^T H, invert it, and read the dilution of precision values (GDOP, PDOP, HDOP, VDOP, TDOP) off the diagonal. Applies to GPS/GNSS receiver analysis, elevation mask studies, and satellite subset selection. Produces the DOP values, the 1-sigma position error from a user equivalent range error, the elevation mask filter, and the k-satellite subset with the lowest PDOP. Trigger: dilution of precision, gdop, pdop, hdop, vdop, tdop, satellite geometry, elevation mask, uere, gps, gnss, satellite selection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arinc-429
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [dilution-of-precision, gdop, pdop, hdop, vdop, tdop, satellite-geometry, elevation-mask, uere, gnss, satellite-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Dilution of Precision (gnc-autonomy/navigation/dilution-of-precision)

Use when the task is evaluating GNSS position accuracy from satellite
geometry: DOP values, the elevation mask, position error from UERE,
and best satellite subset selection.

## Domain quick reference

- With N satellite line-of-sight unit vectors (east, north, up in a
  local ENU frame), the N x 4 geometry matrix H has one row
  [e, n, u, 1] per satellite; the unit column carries the receiver
  clock bias solved together with the three position components.
- The normal matrix A = H^T H is 4 x 4; its inverse G maps pseudorange
  error variance onto the state covariance.
- DOP values are square roots of diagonal sums of G:
  gdop = sqrt(g00+g11+g22+g33), pdop = sqrt(g00+g11+g22),
  hdop = sqrt(g00+g11), vdop = sqrt(g22), tdop = sqrt(g33).
- A pseudorange error with standard deviation sigma gives a position
  error standard deviation of pdop * sigma.
- The elevation mask excludes low satellites whose pseudoranges carry
  larger atmospheric errors; satellite selection picks the k-subset
  with the lowest PDOP by exhaustive search over combinations.

## Workflow

1. Build the geometry matrix H from the satellite unit vectors
   (at least 4 satellites required).
2. Form the normal matrix A = H^T H and invert it by Gauss-Jordan
   with partial pivoting; singular geometry raises a clear error.
3. Read the DOP values off the diagonal and the position error from
   the user equivalent range error.
4. Apply the elevation mask and filter low satellites.
5. Select the k-satellite subset with the best geometry (lowest PDOP).

## Pitfalls

- Reporting a DOP for a singular geometry (collinear satellites);
  the inversion must fail loudly, not silently.
- Using the same elevation for every satellite in a synthetic set,
  which makes the normal matrix singular in (e, n, u, 1) space.
- Confusing HDOP with PDOP (horizontal vs total position).
- Reading position error from GDOP instead of PDOP (GDOP includes the
  clock term).

## Behavior contract (gate 3)

The DOP logic is exercised by the gate 3 contract test:
scripts/test_dop.py against scripts/dop_logic.py (stdlib unittest,
offline). Run:

    python3 scripts/test_dop.py
