# Wave-42 leaf spec: landing-gear-layout (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/landing-gear-layout/
- Pack: sizing (present with landing-gear-sizing,
  landing-gear-retraction-sizing, tire-sizing, tail-sizing, canard-sizing
  and the rest of the vehicle-design sizing pack). Closest siblings and
  their fences:
  - landing-gear-sizing owns the strut weight split and the landing energy
    demand for a GIVEN wheelbase: its frontmatter claim is "split the
    maximum landing weight over the struts, compute the nose and main gear
    loads from the CG position and the wheelbase", its body gives the
    statics "with the CG a distance aft of the main gear, static
    equilibrium about the main gear gives nose load = W * cg_aft /
    wheelbase and main load = W - nose load", and its workflow closes on
    the energy and rating margins; the probe receipt (GO4) records the
    sibling as owning the weight split for a GIVEN wheelbase with pure
    load and landing-energy equations, and as having no CG-limit placement
    and no angular clearances. Nothing in its body positions the
    gear against the CG travel limits or computes any angle.
  - landing-gear-retraction-sizing owns the mechanism once the layout
    exists: its frontmatter claim opens "size the landing gear retraction
    mechanism: the gear moment about the retract pivot", and its body
    states it "pairs with vehicle-design/sizing/landing-gear-sizing, which
    sizes the static strut demand at touchdown and stops before the
    mechanism". No arrangement-angle vocabulary anywhere in the leaf.
  - tire-sizing owns the tire selection from the per-tire load: its body
    states "The required number of tires on a gear is the gear load total
    divided by the maximum load capacity per tire, rounded up"; it never
    produces vehicle-level angles.
  - mass-properties/cg-envelope (probe receipt, GO4) owns the CG travel
    band from longitudinal stability (neutral point and static margin),
    not from gear placement constraints; the arrangement angles here take
    the CG travel limits as given inputs.
  Whole-tree greps at prep (probe receipt GO4): "tipback", "turnover
  angle", "ground clearance angle", "tail strike angle" = 0 hits across
  ALL skills; "nose gear load fraction", "tail-down angle" = 0 hits. The
  arrangement geometry vocabulary is a GENUINE gap: no leaf positions the
  gear relative to the CG envelope or computes the tipback, tail strike
  and lateral turnover clearances.
- Standards id: far-25 and cs-25 (both present in standards-map.yaml,
  lines 16 and 27; the vehicle-design sizing siblings landing-gear-sizing
  and tire-sizing carry both ids reference-only). Ledger Standard:
  far-25, cs-25.
- Family: vehicle-design

## Claim

Lay out a tricycle landing gear arrangement against the CG envelope:
compute the tipback angle at the aft CG limit (the nose-up rotation about
the main gear contact at which the vertical line through the aft CG passes
through the contact and the aircraft would tip back onto its tail), the
tail strike clearance angle at rotation (the same rotation measured until
the tail cone lowest point touches the ground), the lateral turnover angle
at the forward CG limit from the wheel track (main gear pair convention,
with the nose-to-main diagonal refinement), and the nose gear static load
fraction at the forward and aft CG limits from the moment balance about
the main gear contact, reporting the fraction band across the CG travel
with per-limit verdicts against the documented 5 to 20 percent typical
band. Produces the three arrangement angles in degrees, the lateral
turnover tricycle refinement, the nose gear fraction band with its
verdicts, and the main gear position check against the CG travel limits.
Does NOT do: the weight split over the struts and the landing energy
demand for a given wheelbase (landing-gear-sizing); the retraction
mechanism after the layout exists (landing-gear-retraction-sizing); tire
selection from the per-tire load (tire-sizing); the CG travel limits
themselves from longitudinal stability (cg-envelope). Deterministic stdlib
trigonometry and statics only; the rotation and station conventions are
fixed and documented below, so outputs are reproducible.

## Model (implement exactly)

Pinned conventions (documented method): stations x are measured in metres
aft of a fuselage datum; the ground plane is z = 0 at the tire contacts
with the static deflection; rotations are nose-up about the main gear
contact point; all angles are returned in degrees. The aircraft is level
on the ground in the reference attitude, and the aft CG limit sits forward
of the main gear contact by the margin d = x_mg - x_cg_aft.

- Tipback convention: rotating nose-up about the main gear contact by the
  tipback angle brings the aft CG onto the vertical through the contact;
  beyond that attitude the vertical CG line passes aft of the contact and
  gravity rolls the aircraft onto its tail. The rotation obeys
  tan(theta_tip) = (x_mg - x_cg_aft) / h_cg, so theta_tip =
  atan((x_mg - x_cg_aft) / h_cg); the angle grows with the aft-CG margin
  and vanishes when the aft CG reaches the contact station. This is the
  standard tipback check (name and paraphrase only, common conceptual
  design methodology).
- Tail strike convention: the tail cone lowest point sits at station
  x_tail at height h_tail_contact above the ground in the reference
  attitude (gear deflected at the rotation condition). Rotating nose-up by
  theta about the main gear contact, the point at horizontal arm a =
  x_tail - x_mg descends as z(theta) = h_tail_contact * cos(theta) -
  a * sin(theta), which vanishes at tan(theta_ts) = h_tail_contact / a, so
  theta_ts = atan(h_tail_contact / (x_tail - x_mg)). The rotation attitude
  is tail-strike limited when theta_ts sits below the tipback angle, which
  is the transport-typical ordering.
- Lateral turnover conventions: the simplified main gear pair check rolls
  the aircraft about the line joining the two main gear contacts, with the
  CG height h_cg over the half track arm, tan(theta_lat) = h_cg /
  (track / 2) = 2 * h_cg / track. The full tricycle check rolls about the
  diagonal line joining the nose gear contact and the nearer main gear
  contact; the perpendicular ground-plane distance from the CG vertical to
  that diagonal is d_perp = (x_cg - x_ng) * (track / 2) /
  sqrt(wheelbase^2 + (track / 2)^2) with wheelbase = x_mg - x_ng, and
  theta = atan(d_perp / h_cg). The diagonal arm is shorter than the half
  track, so the tricycle angle is the lower (binding) lateral check at a
  forward CG.
- Nose fraction convention: the moment balance about the main gear contact
  gives P_n / W = (x_mg - x_cg) / (x_mg - x_ng); the nose gear carries
  more when the CG is forward, so the aft CG limit gives the lower
  fraction and the forward CG limit the upper one. Band verdicts compare
  both fractions against NOSE_FRACTION_MIN and NOSE_FRACTION_MAX. The
  fraction is dimensionless and layout-level only; the strut loads
  themselves are never computed here.

Functions (pure stdlib, math only), module landing_gear_layout_logic.py:
- tipback_angle(h_cg, x_mg, x_cg_aft) -> float degrees(h_cg > 0, main
  gear aft of the aft CG) = degrees(atan((x_mg - x_cg_aft) / h_cg)).
  ValueError if h_cg <= 0 or x_cg_aft >= x_mg (a statically tipped
  arrangement: the aft CG not forward of the main gear contact).
- tail_strike_clearance_angle(h_tail_contact, x_tail, x_mg) -> float
  degrees = degrees(atan(h_tail_contact / (x_tail - x_mg))). ValueError if
  h_tail_contact <= 0 or x_tail <= x_mg.
- lateral_turnover_angle(h_cg, track) -> float degrees =
  degrees(atan(2 * h_cg / track)), the simplified main gear pair check.
  ValueError if h_cg <= 0 or track <= 0.
- lateral_turnover_tricycle_angle(h_cg, x_cg, x_mg, x_ng, track) -> float
  degrees = degrees(atan(d_perp / h_cg)) with d_perp as pinned above, the
  nose-to-main diagonal check at the CG station x_cg. ValueError if
  h_cg <= 0, track <= 0, or x_cg outside (x_ng, x_mg).
- nose_gear_static_load_fraction(x_cg, x_mg, x_ng) -> float in (0, 1) =
  (x_mg - x_cg) / (x_mg - x_ng). ValueError if x_cg outside (x_ng, x_mg):
  a CG at or aft of the main gear station drives the nose fraction to zero
  or negative and a CG at or forward of the nose gear station drives it to
  one or above.
Module constants: NOSE_FRACTION_MIN = 0.05, NOSE_FRACTION_MAX = 0.20,
ROTATION_REF_DEG = 10.0 (typical transport unstick rotation, used only for
the rotation margin print in the worked case).

Identity to test: doubling the aft-CG margin (x_mg - x_cg_aft) at fixed
h_cg doubles tan(tipback_angle); the tipback angle tends to 0 as the aft
CG approaches the main gear station and the model raises ValueError at and
past it; the tail strike angle vanishes as the tail contact height tends
to 0 and grows with h_tail_contact at fixed arm; doubling the track halves
tan(lateral_turnover_angle); the tricycle diagonal angle lies below the
simplified main-pair angle at the forward CG and grows as the CG moves aft
within the wheelbase; the nose fraction at the aft CG limit is lower than
at the forward CG limit, the two fractions complement the main gear share
to 1, and a CG moved aft of the mid-wheelbase keeps the fraction below
0.5; all non-positive or out-of-range inputs raise ValueError; dict-free
scalar returns keep the model deterministic.

## Worked example

Transport-class aircraft: W = 60000 kg, wheelbase 15 m with the nose gear
at x_ng = 3 m and the main gear at x_mg = 18 m from the datum, CG travel
from the forward limit x_cg_fwd = 14 m to the aft limit x_cg_aft = 16.5 m,
CG height h_cg = 2.8 m, main gear track = 6.5 m, tail cone lowest point at
x_tail = 30 m at h_tail_contact = 3.5 m above the ground.

- Nose fractions: fwd = (18 - 14) / 15 = 0.266667 (26.6667 %) and aft =
  (18 - 16.5) / 15 = 0.1 (10.0 %); the nose gear carries 16000 kg at the
  forward CG limit and 6000 kg at the aft CG limit of the 60000 kg weight.
- Tipback: the aft CG sits d = 18 - 16.5 = 1.5 m forward of the main gear
  contact, so theta_tip = atan(1.5 / 2.8) = 28.18 deg.
- Tail strike at rotation: arm a = 30 - 18 = 12 m, theta_ts =
  atan(3.5 / 12) = 16.26 deg; the margin against the 10 deg unstick
  rotation reference is 6.26 deg. Tail strike precedes tipback (16.26 <
  28.18), so rotation is tail-strike limited, matching transport practice.
- Lateral turnover: simplified main gear pair theta_lat = atan(2 * 2.8 /
  6.5) = atan(0.861538) = 40.75 deg, inside the 40-50 deg transport band;
  the tricycle diagonal check at the forward CG gives d_perp = 11 * 3.25 /
  sqrt(15^2 + 3.25^2) = 2.32908 m and theta = atan(2.32908 / 2.8) = 39.76
  deg, marginally below the main-pair value as the binding lateral case.
- Verdicts: the aft CG fraction of 10.0 % sits inside the 5-20 % typical
  band (True), the forward CG fraction of 26.6667 % sits above it (False)
  and flags the arrangement: with the forward CG limit 4 m ahead of the
  main gear the nose gear is over-weighted, so the main gear station or
  the forward CG limit must move before the layout closes; the lateral
  turnover angle sits inside the 40-50 deg band (True).

Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor script
/tmp/w42spec/anchor_landing_gear_layout.py (prep-verified by stdlib math).
Real prep outputs: tipback_angle 28.17859010995917,
tail_strike_clearance_angle 16.26020470831196, rotation margin vs the 10.0
deg unstick rotation reference 6.26020470831196, lateral_turnover_angle
40.74616356388081, lateral_turnover_tricycle_angle 39.756669023138734,
nose_gear_static_load_fraction fwd CG 0.26666666666666666
(26.666666666666668 %, 16000.0 kg), nose_gear_static_load_fraction aft CG
0.1 (10.0 %, 6000.0 kg), nose fraction band 10.0 % (aft CG) to
26.666666666666668 % (fwd CG), tail strike precedes tipback True, aft CG
fraction in the 5-20 % band True, fwd CG fraction in the band False,
lateral turnover in the 40-50 deg band True.

## Validation list (contract test must include)

- tipback_angle(2.8, 18.0, 16.5) = 28.1786 within 1e-4; doubling the
  aft-CG margin to 3.0 m at fixed h_cg gives atan(3.0 / 2.8) = 46.9686
  deg; the angle tends to 0 as x_cg_aft approaches 18.0; ValueErrors at
  h_cg 0 and negative and at x_cg_aft 18.0 and above.
- tail_strike_clearance_angle(3.5, 30.0, 18.0) = 16.2602 within 1e-4;
  doubling the tail contact height doubles tan(theta_ts), atan(7.0 / 12.0)
  = 30.2557 deg; ValueErrors at h_tail_contact 0 and at x_tail 18.0 and
  below.
- lateral_turnover_angle(2.8, 6.5) = 40.7462 within 1e-4; doubling the
  track halves tan(theta_lat), atan(5.6 / 13.0) = 23.2954 deg; ValueErrors
  at h_cg 0 and track 0 and negative.
- lateral_turnover_tricycle_angle(2.8, 14.0, 18.0, 3.0, 6.5) = 39.7567
  within 1e-4 of the real prep value; the angle at the aft CG limit
  (16.5 m) exceeds the forward CG value (the diagonal arm grows as the CG
  moves aft); the angle tends to 0 as x_cg approaches the nose gear
  station; ValueErrors at x_cg at and outside the (3.0, 18.0) station pair
  and at non-positive h_cg or track.
- nose_gear_static_load_fraction(14.0, 18.0, 3.0) = 0.266667 and
  (16.5, 18.0, 3.0) = 0.1 within 1e-9; the aft CG fraction is below the
  forward CG fraction (the nose gear carries more when the CG is forward);
  the fractions complement the main gear share to 1 (0.266667 + 0.733333
  and 0.1 + 0.9); a mid-wheelbase CG at 10.5 m gives exactly 0.5;
  ValueErrors at x_cg 18.0, 3.0 and outside the station pair.
- Determinism: repeated calls return identical scalars; angles are always
  returned in degrees and fractions are dimensionless; every invalid input
  class raises ValueError rather than returning a plausible number.

## Corpus fragment (eval/hit1-wave42-landing-gear-layout.yaml)

Query 1 (copy verbatim):
  "Lay out the main and nose gear of an aircraft against the CG envelope: compute the tipback angle at the aft CG limit, the lateral turnover angle at the forward CG limit from the wheel track, and the tail strike clearance angle at rotation about the main gear contact"
  intent: "vehicle design; landing gear arrangement geometry against the CG envelope with the tipback angle, the lateral turnover angle from the wheel track, and the tail strike clearance angle at rotation"
  expected_skill: "vehicle-design/sizing/landing-gear-layout"
Query 2 (copy verbatim):
  "Position the main gear relative to the CG travel limits for a transport: check the nose gear load fraction band at the forward and aft CG limits and the main gear station choice that keeps the fraction band inside its limits"
  intent: "vehicle design; main gear position check against the CG travel limits with the nose gear load fraction band at the forward and aft CG limits"
  expected_skill: "vehicle-design/sizing/landing-gear-layout"
Task ids: w42-landing-gear-layout-1 and -2. Both queries are collision-free
at prep: no "tipback", "turnover angle", "tail strike angle" or "nose gear
load fraction" token exists anywhere in eval/hit1-corpus.yaml (probe
receipt GO4, whole-tree greps = 0 hits), and the routing vocabulary
(rotation about the main gear contact, CG travel limits, wheel track,
arrangement angles) is absent from the landing-gear-sizing,
landing-gear-retraction-sizing and tire-sizing tasks.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must lay out the landing gear
arrangement of an aircraft against its center-of-gravity envelope:" and
include the outputs in the Claim (tipback angle, tail strike clearance
angle, lateral turnover angle, nose gear load fraction band, main gear
position check). Draft description (119 words): "Use when you
must lay out the landing gear arrangement of an aircraft against its
center-of-gravity envelope: compute the tipback angle at the aft CG limit
about the main gear contact, the tail strike clearance angle at rotation,
the lateral turnover angle from the wheel track at the forward CG limit,
and the nose gear load fraction band across the CG travel. Produces the
three layout angles in degrees, the nose gear load fraction at the forward
and aft CG limits with band verdicts, and the main gear position check
that gate the landing gear configuration. Trigger: landing gear layout,
tipback angle, tail strike clearance, lateral turnover, nose gear load
fraction, main gear position, wheel track, CG travel limits."
First tag: landing-gear-layout. Additional tags ONLY: tipback-angle,
lateral-turnover-angle, tail-strike-clearance-angle, nose-gear-load-fraction,
main-gear-positioning. NEVER single generic words (landing, gear, layout,
angle, position, load, fraction, turnover, strike, clearance, tail, nose,
main, wheel, track, center, gravity). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): static-load-split,
shock-absorber-stroke, sink-speed, landing-load-factor, oleo-sizing,
tire-rating-margin (landing-gear-sizing); retraction-actuator-force,
retraction-moment, up-lock, down-lock, lock-hold-load, gear-bay-stowage,
landing-gear-kinematics (landing-gear-retraction-sizing); tire-diameter,
tire-width, tire-ply-rating, inflation-pressure, footprint,
rolling-radius, power-law-fit (tire-sizing).
