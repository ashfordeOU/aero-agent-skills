---
name: wing-planform-sizing
description: "Use when you must size the wing planform geometry at the design point: compute the wing area from the takeoff gross weight and the chosen wing loading, convert the aspect ratio into the span, set the taper ratio and derive the root chord, tip chord, and mean aerodynamic chord with its spanwise station, and select the sweep angle from the cruise Mach so the section normal Mach stays at or below the section critical Mach. Produces the planform dimensions that feed weight estimation, fuel tank volume, control surface sizing, and the aerodynamic analysis leaves. Trigger: wing planform, wing area, aspect ratio, taper ratio, mean aerodynamic chord, sweep angle, cruise Mach."
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
  tags: [wing-planform-sizing, wing-area, wing-loading, aspect-ratio, span-sizing, taper-ratio, mean-aerodynamic-chord, sweep-angle, cruise-mach, takeoff-gross-weight]
  version: 0.1.0
  author: Aero Agent Skills
---

# Wing Planform Sizing (vehicle-design/sizing/wing-planform-sizing)

Use when the task is sizing the geometric wing planform for a given
design point: the reference wing area from the wing loading and the
takeoff gross weight, the span from the aspect ratio, the root and
tip chord and the mean aerodynamic chord from the taper ratio, and
the sweep angle selected from the cruise Mach. The output is the set
of planform dimensions, not the aerodynamic or structural evaluation
of those dimensions.

## Domain quick reference

- Units: forces in N, areas in m^2, wing loading in N/m^2, spans and
  chords in m, Mach numbers unitless, sweep angles in degrees,
  g = 9.80665 m/s^2.
- Wing area from wing loading and takeoff gross weight:
  S = W / (W/S). Anchor: W = 480000 N and W/S = 6000 N/m^2 give
  S = 480000 / 6000 = 80.0 m^2.
- Wing loading from the area: W/S = W / S. Anchor: 480000 N over
  80.0 m^2 gives 6000.0 N/m^2 (round trip check).
- Span from the aspect ratio: b = sqrt(AR * S). Anchor: S = 80.0 m^2
  and AR = 9 give b = sqrt(720) = 26.8328 m.
- Aspect ratio from span and area: AR = b^2 / S. Anchor: the
  26.8328 m span over 80.0 m^2 gives AR = 9.0 (round trip check).
- Taper ratio: lambda = c_tip / c_root, conventional planforms keep
  0 < lambda <= 1. Anchor: c_root = 5.0 m and c_tip = 1.5 m give
  lambda = 0.3.
- Root chord from area, span, and taper:
  c_root = 2 * S / (b * (1 + lambda)). Anchor: S = 80.0 m^2,
  b = 26.8328 m, lambda = 0.3 give c_root = 160 / (26.8328 * 1.3) =
  4.5868 m.
- Tip chord: c_tip = lambda * c_root. Anchor: 0.3 * 4.5868 =
  1.3760 m.
- Mean aerodynamic chord (MAC):
  MAC = (4 * S / (3 * b)) * (1 + lambda + lambda^2) / (1 + lambda)^2.
  Anchor: 80.0 m^2, 26.8328 m, lambda = 0.3 give MAC = 3.2696 m,
  about 0.713 of the root chord.
- MAC spanwise station from the root:
  y_mac = (b / 6) * (1 + 2 * lambda) / (1 + lambda). Anchor:
  26.8328 m and lambda = 0.3 give y_mac = 5.5042 m outboard of the
  root.
- Sweep angle from cruise Mach: the section sees the Mach component
  normal to the quarter-chord line, M_n = M_cruise * cos(Lambda).
  Keeping M_n at or below the section critical Mach number selects
  the minimum sweep Lambda = arccos(M_crit_section / M_cruise) when
  M_cruise > M_crit_section, and 0 degrees otherwise. Anchor:
  M_cruise = 0.8 and M_crit_section = 0.7 give
  Lambda = arccos(0.875) = 28.96 degrees, and the check
  M_n = 0.8 * cos(28.96 deg) = 0.7 returns the section critical Mach.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  (reference geometry and flight envelope for transport-category
  aeroplanes); the planform relations are common conceptual sizing
  practice.

## Workflow

1. Set the design point: takeoff gross weight W, chosen wing loading
   W/S, aspect ratio AR, taper ratio lambda, cruise Mach, and section
   critical Mach.
2. Compute the reference wing area with wing_area_from_wing_loading.
3. Compute the span with span_from_aspect_ratio.
4. Set the taper ratio and compute the root chord with
   root_chord_from_taper, then the tip chord with
   tip_chord_from_taper.
5. Compute the mean aerodynamic chord with mean_aerodynamic_chord and
   its spanwise station with mac_spanwise_station.
6. Select the sweep angle with sweep_angle_from_cruise_mach and check
   the result with mach_normal_component.
7. Summarize the planform with planform_geometry, then hand the
   reference area, span, and MAC to the sibling leaves: weight
   estimation (wing mass), fuel tank sizing (tank volume fit),
   control surface sizing (aileron span), and tail sizing (tail arm
   and volume coefficients).

## Pitfalls

- Confusing this leaf with ws-tw-trade: ws-tw-trade selects the wing
  loading W/S and the thrust to weight T/W from the matching chart;
  wing-planform-sizing takes the chosen W/S as given and converts it
  into the geometric planform. The W/S trade comes first, the
  planform geometry second.
- Confusing the direction of the data flow with weight estimation:
  weight-estimation predicts component masses from the geometry;
  wing-planform-sizing consumes the takeoff gross weight and produces
  the geometry. Use the weight budget to size the area, do not
  re-estimate the weight here.
- Confusing this leaf with the aerodynamics airfoil leaves:
  airfoil-geometry works on the two-dimensional section (camber,
  thickness, coordinates); swept-wing-aerodynamics evaluates the aero
  effects of a given sweep (effective Mach, critical Mach increase);
  lift-curve-slope applies the aspect ratio and sweep corrections to
  the lift slope. This leaf selects the planform numbers, the aero
  leaves evaluate their consequences.
- Mixing units: wing loading must be in N/m^2, not kg/m^2; a loading
  given in kg/m^2 must be multiplied by g = 9.80665 before dividing
  the weight.
- Forgetting that the MAC changes with taper at fixed area and span:
  a more tapered planform (lower lambda) has a longer MAC, and the
  rectangular planform (lambda = 1) has MAC equal to the average
  chord S / b.
- Treating the sweep relation as exact for all planforms: the
  arccos relation gives the minimum sweep from simple sweep theory;
  in practice round the sweep up for margin, and a supercritical
  section (supercritical-airfoil leaf) raises the section critical
  Mach and reduces the sweep needed.
- Applying the sweep formula when the section critical Mach already
  meets or exceeds the cruise Mach: the module returns 0 degrees
  (no sweep needed), which is the correct design answer, not an
  error.
- Passing a reverse taper (tip chord larger than root chord): the
  module raises ValueError because conventional planforms taper
  toward the tip; check the chord order before calling.

## Behavior contract (gate 3)

The wing area from wing loading and takeoff gross weight, aspect
ratio and span, taper ratio with root and tip chord, mean aerodynamic
chord with its spanwise station, sweep angle from cruise Mach, and
the planform summary are exercised by the gate 3 contract test:
scripts/test_wing_planform_sizing.py against
scripts/wing_planform_sizing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_wing_planform_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the planform
  relations are common conceptual sizing methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
