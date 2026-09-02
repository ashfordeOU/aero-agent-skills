---
name: fuselage-sizing
description: "Use when you must size a transport fuselage from the payload: compute the cabin length from the seat count and the seat pitch, compute the cabin width and the fuselage diameter from the seats-abreast layout and the aisle width, judge the overall fuselage length to diameter ratio against the typical transport band, and check the underfloor cargo volume against the required baggage volume. Produces the cabin length, fuselage diameter, and cross-section layout that feed the conceptual sizing loop, with the sanity band and cargo verdicts. Trigger: fuselage sizing, cabin length, fuselage diameter, seats abreast, seat pitch, cabin width, aisle width, cargo volume."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [fuselage-sizing, cabin-length, fuselage-diameter, seats-abreast, seat-pitch, cabin-width, aisle-width, cargo-volume]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fuselage Sizing (vehicle-design/sizing/fuselage-sizing)

Use when the task is fuselage sizing for a transport or civil
aeroplane starting from the payload: cabin length from the seat
count and seat pitch, cabin width and fuselage diameter from the
cross-section layout, the length to diameter ratio sanity band, and
the underfloor cargo volume check against the required baggage
volume.

## Domain quick reference

- Cabin length from the payload: L_cabin = rows * pitch, with rows
  the number of seat rows and pitch the seat pitch in m. Example:
  30 rows at 0.81 m pitch (about 32 in) give 24.3 m. Typical
  economy pitch is 0.76 to 0.84 m (30 to 33 in).
- Cabin width from the cross-section layout: W_cabin =
  seats_abreast * seat_width + aisle_width, with seat width and
  aisle width in m. Example: 6 abreast with 0.48 m seats (about
  19 in) and one 0.51 m aisle (about 20 in) give 3.39 m.
- Fuselage diameter: D = W_cabin + sidewall_allowance, the cabin
  width plus a total allowance for trim, insulation, and structure
  on both sides (typical 0.15 to 0.25 m, default 0.18 m). Example:
  the 3.39 m cabin above gives a 3.57 m diameter.
- Length to diameter sanity band: ratio = L_fuselage / D, with the
  OVERALL fuselage length (nose to tailcone, not just the cabin).
  A ratio from 6 to 12 is typical for transport jets; below 6 the
  layout is stubby, above 12 it is slender. The band is sizing
  guidance, not a certification requirement.
- Cargo volume check: required baggage volume V_req = passengers *
  0.12 m^3 per passenger (typical range 0.10 to 0.15 m^3 per
  passenger); the available underfloor cargo volume must meet or
  exceed it.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  for transport-category aeroplane design (cabin layout, exits,
  emergency provisions); the geometric relations above are common
  conceptual sizing practice.

## Workflow

1. Set the payload layout: seats abreast, seat width, aisle width,
   seat pitch, and row count.
2. Compute the cabin length with cabin_length(rows, pitch).
3. Compute the interior cabin width with cabin_width(seats_abreast,
   seat_width, aisle_width).
4. Compute the outer fuselage diameter with
   fuselage_diameter(seats_abreast, seat_width, aisle_width),
   adjusting sidewall_allowance for the structure and insulation
   concept.
5. Judge the length to diameter ratio with
   length_diameter_verdict(fuselage_length, diameter) using the
   overall fuselage length, and rework the layout until the verdict
   is within the typical band.
6. Estimate the required baggage volume with
   required_baggage_volume(passengers) and compare it with the
   available underfloor cargo volume using cargo_volume_verdict;
   rework the underfloor layout until the check passes.

## Pitfalls

- Using the cabin length where the overall fuselage length belongs:
  the length to diameter ratio uses nose-to-tailcone length, which
  exceeds the cabin length by the cockpit, tailcone, and closures.
- Mixing units: pitch in inches, seat width in cm, or aisle width
  in ft with a row count in meters; keep everything SI (m).
- Forgetting the sidewall allowance: the fuselage diameter is
  larger than the cabin width; sizing the diameter equal to the
  cabin width leaves no room for trim, insulation, and structure.
- Treating the 6 to 12 length to diameter band as a hard limit: it
  is a conceptual sanity band that flags layouts for rework, not a
  certification requirement.
- Skipping the cargo check: a passenger-feasible cabin can still be
  cargo-limited, so the underfloor volume must be verified against
  the baggage volume per passenger.
- Counting the aisle once per side: the aisle width enters the
  cabin width once for a single-aisle layout, not multiplied by the
  number of seat columns.
- Passing zero or negative inputs; the module raises ValueError
  instead of returning a nonsense dimension.

## Behavior contract (gate 3)

The cabin length, cabin width, fuselage diameter, length to
diameter verdict, and cargo volume check relations are exercised by
the gate 3 contract test: scripts/test_fuselage_sizing.py against
scripts/fuselage_sizing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fuselage_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the geometric
  fuselage sizing relations are common conceptual sizing
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
