---
name: v-tail-sizing
description: "Use when you must size a V-tail empennage from the equivalent horizontal and vertical tail volume requirements: convert each target volume coefficient into its equivalent area, resolve the two areas onto one canted surface pair under the planform-area projection convention, split the total area equally between the two panels, derive the panel span and chord from the surface aspect ratio, size the ruddervator control area as a fraction of the total, and verify the effective volume round trip at the dihedral angle. Produces the equivalent areas, total V-tail area, dihedral angle, per-surface area, span and chord, ruddervator area, and met verdicts. Trigger: v tail sizing, butterfly tail, vee tail, ruddervator, tail dihedral, projected tail area."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [v-tail-sizing, ruddervator, vee-tail-empennage, tail-volume-equivalence, tail-dihedral-angle, projected-tail-area]
  version: 0.1.0
  author: AeroSkills
---

# V-Tail Sizing (vehicle-design/sizing/v-tail-sizing)

Use when the task is sizing a V-tail (butterfly or vee tail) empennage
from equivalent horizontal and vertical tail volume requirements. The
V-tail is the single canted pair of aft surfaces that replaces the
conventional separate horizontal and vertical tails, combining the two
tail volume requirements on one surface pair whose ruddervators blend
the elevator and rudder functions. This leaf implements the
planform-area projection convention in pure Python, stdlib only,
deterministic. It pairs with vehicle-design/sizing/tail-sizing, which
owns the conventional separate-surface volume coefficients and their
typical ranges, and with vehicle-design/sizing/canard-sizing for the
forward surface; control-surface-sizing owns elevator and rudder areas
from moment requirements, and wing-planform-sizing owns the wing
geometry the volume coefficients reference.

## Domain quick reference

- Volume coefficient definition (inverse form): the required
  equivalent tail area for a target coefficient is
  S = V * S_ref * ref_len / tail_arm. The horizontal requirement uses
  the wing reference area S_ref, the wing reference chord c_bar and
  the tail arm l_h: S_h = V_h * S_ref * c_bar / l_h. The vertical
  requirement uses the wing span b and the tail arm l_v:
  S_v = V_v * S_ref * b / l_v.
- Projection convention (documented method, Raymer-style projected
  area for the volume coefficient formulas, name and paraphrase only):
  with the two panels canted up at the dihedral angle Gamma from the
  horizontal, the horizontal equivalent area entering the horizontal
  formula is the sum of the horizontal projections,
  S_h_eff = S_vt * cos(Gamma), and the vertical equivalent area is
  S_v_eff = S_vt * sin(Gamma). The cos^2/sin^2 loading convention is
  NOT used here.
- Vector-sum inversion: under that convention,
  S_vt = sqrt(S_h^2 + S_v^2) and Gamma = atan2(S_v, S_h), measured
  from the horizontal plane, are exact. The equal panel split makes
  the per-surface projections (S_vt / 2) * cos(Gamma) and
  (S_vt / 2) * sin(Gamma).
- Panel geometry: each panel carries area_per_surface = S_vt / 2 and
  is treated as a flat surface with its own aspect ratio
  (SURFACE_ASPECT_RATIO = 4.0 default), so
  span_per_surface = sqrt(aspect_ratio * area_per_surface) and
  chord_per_surface = area_per_surface / span_per_surface, the mean
  chord of one panel.
- Ruddervators: total movable control area =
  RUDDERVATOR_FRACTION * S_vt, with RUDDERVATOR_FRACTION = 0.35 (the
  documented engineering default), half on each panel. Area fraction
  only, no hinge-geometry output.
- Effective volume round trip: v_h_eff = S_vt * cos(Gamma) * l_h /
  (S_ref * c_bar) and v_v_eff = S_vt * sin(Gamma) * l_v / (S_ref * b).
  Met verdicts compare against the targets with VOLUME_TOL = 1e-9,
  which absorbs the cos/sin/atan2 round-trip error of order 1e-16.
- Units are SI throughout: m, m^2, rad, deg.
- FAR-25 frames the certification context for the empennage design
  requirements; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Gather the aircraft and requirement data: the wing reference area
   S_ref, the wing reference chord c_bar, the wing span b, the tail
   arms l_h and l_v (wing to V-tail root), and the target volume
   coefficients V_h and V_v. Pick targets inside the typical ranges
   quoted by the conventional tail-sizing leaf when starting from
   scratch.
2. Convert each target volume coefficient into the required
   equivalent area with tail_area_from_volume_coefficient:
   S_h = tail_area_from_volume_coefficient(V_h, c_bar, l_h, S_ref)
   for the horizontal requirement and
   S_v = tail_area_from_volume_coefficient(V_v, b, l_v, S_ref) for
   the vertical requirement.
3. Resolve the two equivalent areas onto the canted pair with
   vtail_geometry(S_h, S_v): read the total V-tail area S_vt, the
   dihedral angle gamma_rad and gamma_deg (from the horizontal), the
   equal panel split area_per_surface, and the per-surface
   span_per_surface and chord_per_surface at SURFACE_ASPECT_RATIO.
4. Size the ruddervators with
   ruddervator_sizing(S_vt, control_fraction): the default 0.35
   fraction of the total V-tail area, split half per surface.
5. Verify the effective volume round trip with
   effective_volume_check(S_vt, gamma_rad, V_h, V_v, S_ref, c_bar,
   b, l_h, l_v): the projected S_h_eff and S_v_eff recover the
   targets within VOLUME_TOL, and read the met verdicts v_h_met and
   v_v_met. If either flag is False the tail is undersized for its
   requirement at the given arm.
6. Confirm the deterministic checks with the contract test
   python3 scripts/test_v_tail_sizing.py.

## Worked example

Light aircraft: S_ref = 16 m2, c_bar = 1.5 m, b = 11 m, tail arms
l_h = l_v = 4.5 m, targets V_h = 0.7 and V_v = 0.04 (both inside the
typical ranges quoted by the tail-sizing leaf).

- Required equivalent areas (step 2): S_h = 0.7 * 16 * 1.5 / 4.5 =
  3.73333 m2 and S_v = 0.04 * 16 * 11 / 4.5 = 1.56444 m2.
- V-tail resolution (step 3): S_vt = sqrt(3.73333^2 + 1.56444^2) =
  4.04787 m2, gamma_rad = atan2(1.56444, 3.73333) = 0.396818 rad,
  gamma_deg = 22.7360 deg from the horizontal. The included vee
  angle between the two panels is 2 * Gamma = 45.472 deg.
- Per-surface geometry (step 3) at aspect ratio 4.0: each panel
  carries area_per_surface = 2.02394 m2, span_per_surface =
  sqrt(4.0 * 2.02394) = 2.84530 m, chord_per_surface = 2.02394 /
  2.84530 = 0.711325 m.
- Ruddervators (step 4) at the 0.35 fraction:
  ruddervator_area_total = 0.35 * 4.04787 = 1.41676 m2,
  ruddervator_area_per_surface = 0.708378 m2.
- Effective volume round trip (step 5): S_h_eff = 3.73333 m2 and
  S_v_eff = 1.56444 m2 recover v_h_eff = 0.700 (0.6999999999999998)
  and v_v_eff = 0.04, so v_h_met and v_v_met are both True under
  VOLUME_TOL. A 10% smaller S_vt = 3.64308 m2 at the same Gamma
  gives v_h_eff = 0.63, below the tolerance band, and both met flags
  read False.

## Pitfalls

- Using the cos^2/sin^2 loading convention: some V-tail treatments
  size the horizontal projection with cos^2(Gamma) and the vertical
  with sin^2(Gamma). This leaf uses the Raymer-style planform-area
  projection (cos and sin on the total), and its vector-sum inversion
  and round trip are exact only under that documented convention.
- Treating S_h and S_v as physical tail areas: they are equivalent
  areas entering the volume coefficient formulas. Building two
  separate physical surfaces from them, one horizontal and one
  vertical, is the conventional tail-sizing path, not the V-tail
  resolution onto the single canted pair.
- Swapping the reference lengths: the horizontal requirement runs on
  the wing reference chord c_bar (S_v = V_v * S_ref * b / l_v uses
  the span b). Mixing the two reference lengths corrupts both the
  dihedral angle and the round trip.
- Rating the met verdicts without the tolerance: the round-trip error
  is of order 1e-16, so an exact comparison would spuriously fail a
  correctly sized tail; VOLUME_TOL = 1e-9 absorbs it while a
  genuinely undersized tail (for example 10% smaller area) still
  fails both flags.
- Sizing the panel span on the total area: the aspect ratio
  convention applies to ONE panel of area S_vt / 2, so
  span_per_surface = sqrt(AR * S_vt / 2). Using S_vt in its place
  overstates the panel span by sqrt(2).
- Reading the dihedral as the included vee angle: Gamma is measured
  from the horizontal plane, so the angle between the two panels is
  2 * Gamma (45.472 deg in the worked example, not 22.736 deg).

## Verification

- Confirm tail_area_from_volume_coefficient(0.7, 1.5, 4.5, 16.0)
  returns 3.73333 m2 and (0.04, 11.0, 4.5, 16.0) returns 1.56444 m2.
- Confirm vtail_geometry on those areas returns S_vt = 4.04787 m2,
  gamma_deg = 22.7360, area_per_surface = 2.02394 m2,
  span_per_surface = 2.84530 m, chord_per_surface = 0.711325 m.
- Confirm the symmetric identity: vtail_geometry(1.0, 1.0) gives
  gamma_deg = 45.0 and S_vt = sqrt(2) * S_h.
- Confirm the arm identity: doubling the tail arm halves the required
  equivalent area.
- Confirm the projection identity: S_h_eff^2 + S_v_eff^2 equals
  S_vt^2 within 1e-12.
- Confirm the round trip recovers the target coefficients within
  1e-9 with both met verdicts True, and that a 10% smaller S_vt at
  the same dihedral gives v_h_eff = 0.63 with both verdicts False.
- Confirm every non-positive area, arm, span, reference quantity,
  volume coefficient and every control fraction outside (0, 1)
  raises ValueError.

## Related leaves

- skills/vehicle-design/sizing/tail-sizing: the conventional
  separate-surface horizontal and vertical tail volume coefficients,
  their required-area inverse and the typical transport ranges that
  seed the V-tail targets.
- skills/vehicle-design/sizing/canard-sizing: the forward surface
  alternative to the aft empennage pair.
- skills/vehicle-design/sizing/control-surface-sizing: elevator and
  rudder control areas sized from pitch and yaw moment requirements
  rather than from the volume-coefficient equivalence.
- skills/vehicle-design/sizing/wing-planform-sizing: the wing
  reference quantities (area, chord, span) the volume coefficients
  are built on.

## Contract test

Run the deterministic stdlib unittest offline from the repo root:

    python3 skills/vehicle-design/sizing/v-tail-sizing/scripts/test_v_tail_sizing.py

The 34-method suite covers the equivalent-area conversion for both
targets with its arm and reference-area scalings and its ValueError
rejections, the canted-pair resolution with the vector-sum total, the
dihedral in radians and degrees, the equal panel split, the panel
span and chord at the aspect ratio, the fixed result keys, the 45
degree symmetric identity and the quadrant bound, the ruddervator
fraction sizing with its out-of-range rejections, the effective
volume round trip with the met verdicts, the undersized-tail flip,
the projection identity and determinism, and the ValueError rejection
of every non-physical verification input.

## Compliance

- Standards referenced, not reproduced: FAR-25 is the certification
  context (empennage design and control requirements); the sizing
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/vehicle-design/sizing/v-tail-sizing/scripts/test_v_tail_sizing.py

The test exercises the full SKILL.md Workflow: the worked-example
data gathering (step 1), the equivalent-area conversion from the
volume targets (step 2), the canted-pair resolution and per-surface
geometry (step 3), the ruddervator area fraction (step 4), and the
effective volume round trip with its met verdicts (step 5), plus the
projection and arm identities and ValueError rejection of every
non-physical input. Exit code 0 with all tests passing is the gate.
