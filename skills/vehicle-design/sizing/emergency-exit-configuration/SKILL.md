---
name: emergency-exit-configuration
description: "Use when you must configure passenger emergency exits against the discrete exit-type rules: look up each exit type's minimum rectangular opening and per-exit seating credit from the constant table, verify that the exits on each side of the fuselage alone cover the passenger capacity, check the capacity-band minimum exit counts and minimum types, apply the two-C-or-larger rule when a type-a, type-b or type-c exit is installed, check the 60-foot adjacent-exit spacing rule on the same side with the implied maximum seat distance to an exit, and compute the aggregate evacuation demand ratio. Produces the per-side capacity sums, the adequacy verdict with the failing-rule list, the required per-side exit set, and the demand ratio that gate the exit configuration. Trigger: emergency-exit-configuration, exit-type-requirements, exit-count-check, exit-placement-rule, per-side-exit-capacity, evacuation-demand-ratio."
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
  tags: [emergency-exit-configuration, exit-type-requirements, exit-count-check, exit-placement-rule, per-side-exit-capacity, evacuation-demand-ratio]
  version: 0.1.0
  author: AeroSkills
---

# Emergency Exit Configuration (vehicle-design/sizing/emergency-exit-configuration)

Use when the task is checking a passenger emergency exit configuration
against the discrete certification rules: each exit type carries a
minimum rectangular opening and a per-exit seating credit, the exits on
EACH side of the fuselage alone must cover the passenger capacity (an
emergency can make one side unusable, so a side that relies on the other
side is not adequate), the capacity band sets minimum exit counts and
minimum types, a Type A, B or C exit forces a second Type C or larger
exit on the same side, consecutive same-side exits must sit within the
60 ft adjacent-exit spacing rule, and the aggregate evacuation demand
ratio closes the check. The per-side capacity sums, the adequacy verdict
with the failing-rule list, the required per-side exit set, and the
demand ratio gate the exit configuration. It pairs with fuselage-sizing,
which sizes the cabin from the seat layout and names exits only as
certification context, and with aircraft-oxygen-system-sizing, the other
emergency provision; evacuation dynamics, aisle and assist-space access
layout, exit door mechanisms, and ditching, ventral, tailcone and
flightcrew exit provisions are out of scope (access rules and those
provisions are not encoded, disclosed below).

## Domain quick reference

- Exit type table (module constant, paraphrase of the public regulatory
  type definitions and the per-exit credit table; far-25 referenced, not
  reproduced): type id, minimum rectangular opening width x height in
  inches, per-exit seating credit: A 42 x 72, credit 110; B 32 x 72,
  credit 75; C 30 x 48, credit 55; I 24 x 48, credit 45; II 20 x 44,
  credit 40; III 20 x 36, credit 35; IV 19 x 26, credit 9. The credit
  encodes the maximum seating that follows from the type and number of
  exits installed on that side.
- Per-side rule: the exit credit sum on each side of the fuselage alone
  must cover the passenger capacity, because an emergency can make one
  side unusable.
- Capacity bands (paraphrase of the discrete type-and-number rules):
  1-9 seats, one exit per side of Type IV or larger; 10-19 seats, one
  Type III or larger per side; 20-40 seats, two exits per side with one
  Type II or larger; 41-110 seats, two exits per side with one Type I or
  larger; more than 110 seats, at least two Type I or larger exits per
  side with every exit Type III or larger.
- Two-C-or-larger rule: when any Type A, B or C exit is installed on a
  side, that side must carry at least two exits of Type C or larger.
- Spacing rule: consecutive exits on the same side are separated by the
  row difference times the seat pitch converted to feet; a centerline
  gap above 60 ft is a spacing violation. The implied maximum seat
  distance to an exit is half the largest adjacent gap, the farthest any
  seat between two exits can sit from the nearer one.
- Aggregate evacuation demand ratio: passenger capacity over the sum of
  the exit credits, at or below 1.0 when the aggregate exit capacity
  covers the cabin.
- FAR-25 (14 CFR Part 25) sets the certification context for transport
  emergency exit types and counts and is referenced, not reproduced
  (standards-map.yaml, far-25).

## Workflow

1. Collect the configuration: the passenger capacity, the exit types
   installed on the left and right sides of the fuselage, and the row
   numbers of the exits on the side checked for spacing.
2. Look up each installed type with exit_type_dimensions, confirming the
   minimum rectangular opening (width_in, height_in) and the per-exit
   seating credit from the module constant table.
3. Sum the per-side seating credits with side_exit_capacity: each side
   alone must cover the passenger capacity.
4. Read the capacity band and the required per-side exit set with
   capacity_band and required_exits_by_capacity: the band label, the
   minimum exit count per side, and the smallest-count per-side type
   multiset whose credit sum covers the capacity honoring the band
   minimum types (exact enumeration over combinations with replacement
   up to 12 exits per side, ties broken by the smaller excess).
5. Run the exit-count-check with exit_count_check(passenger_capacity,
   left_exits, right_exits): the verdict dict reports each side's
   capacity sum and failing-rule list, the adequate flag, and the
   shortfall (capacity minus the smaller of the two side sums). Failures
   are capacity, minimum-exit-count, all-exits-minimum-type,
   one-exit-minimum-type, two-exits-minimum-type, and
   two-C-or-larger-when-ABC-installed.
6. Check the 60 ft adjacent-exit spacing rule with
   exit_placement_check(exit_row_numbers, seat_pitch_in): adjacent gaps
   in feet, spacing violations above the 60 ft limit, the adequate flag,
   and the implied maximum seat distance to an exit (half the largest
   adjacent gap).
7. Compute the aggregate evacuation demand ratio with
   evacuation_demand_ratio(passenger_capacity, exit_capacity_sum):
   capacity over the exit credit sum, adequate aggregate at or below
   1.0.

## Worked example

180-seat single-aisle cabin (real module outputs):

- required_exits_by_capacity(180): band ">110", required per side
  ["A", "B"], covered 185, excess seats 5.
- exit_count_check(180, ["A", "C"], ["A", "C"]): left and right
  capacity 165, adequate False, failures ["capacity"] on both sides,
  shortfall 15.
- exit_count_check(180, ["A", "B"], ["A", "B"]): capacities 185 both
  sides, adequate True, no failures.
- evacuation_demand_ratio(180, 165) = 1.090909 (inadequate aggregate);
  evacuation_demand_ratio(180, 185) = 0.972973 (adequate aggregate).

60-seat regional:

- required_exits_by_capacity(60): band "41-110", required per side
  ["I", "III"], covered 80, excess 20 (one Type I floor-level exit plus
  one Type III overwing exit per side).
- exit_count_check(60, ["C", "I"], ["C", "I"]): adequate False,
  failures ["two-C-or-larger-when-ABC-installed"] both sides: the Type C
  door forces a second Type C or larger exit on that side.
- exit_count_check(60, ["C", "C"], ["C", "C"]): adequate True.
- exit_count_check(60, ["C"], ["C"]): left capacity 55, failures
  ["capacity", "minimum-exit-count",
  "two-C-or-larger-when-ABC-installed"].

Placement at 32 inch seat pitch: exits at rows 1, 12, 23 and 32 give
adjacent gaps 29.3333, 29.3333 and 24.0 ft, adequate True, implied
maximum seat distance 14.667 ft. Exits only at rows 1 and 32 leave an
82.6667 ft gap: adequate False, spacing_violations [(1, 82.6667)].
Regional 20 rows at 31 inch pitch with exits at rows 1 and 20 give a
49.0833 ft gap: adequate True, implied maximum seat distance 24.542 ft.

## Pitfalls

- Treating the two sides as shared capacity: the per-side rule demands
  that each side alone covers the passenger capacity; a configuration
  whose sides only cover the cabin together fails the check.
- Checking the credit sum but skipping the type rules: a Type A pair on
  60 seats may cover the capacity while a Type C plus Type I pair fails
  the two-C-or-larger rule that the Type C install triggers.
- Reading the band minimum count as optional: a single exit of any type
  per side always fails the 41-110 and 20-40 bands, however large the
  door.
- Forgetting the over-110 minimum types: on more than 110 seats every
  exit must be Type III or larger, so a Type IV anywhere on a side fails
  all-exits-minimum-type even when the credits look generous.
- Mixing the spacing rule across sides: the 60 ft limit applies to
  consecutive exits on the SAME side, never across the fuselage.
- Forgetting the unit conversion: adjacent gaps are the row difference
  times the pitch in inches divided by 12; 32 inches of pitch is
  2.6667 ft per row.
- Confusing the per-side required exit set with the aggregate demand
  ratio: the first is a per-side minimum configuration, the second
  totals the installed credits over the cabin.
- Passing non-physical inputs (capacity 0, empty row lists, zero pitch,
  unknown exit types); the module raises ValueError instead of
  returning a nonsense verdict.

## Verification

Deterministic, offline checks (scripts/test_emergency_exit_configuration.py):
the worked-example anchors above with the module's real outputs as
assert targets; the full seven-type exit type table; the two Type A
credit identity (220) and the single Type IV credit identity (9); the
capacity-band boundary mapping; the covered minus capacity equals excess
identity; the exit-count-check verdicts of the worked example with the
failing-rule lists asserted exactly; the one-exit-minimum-type and
two-exits-minimum-type band checks; the independence of the two sides;
the adjacent-gap anchors 29.3333, 24.0, 82.6667 and 49.0833 ft with the
implied maximum seat distance; evacuation demand ratio anchors 1.090909
and 0.972973 within 1e-5 and the unity ratio at equal credit sums;
ValueError rejection of unknown exit types, capacity below 1, exit
capacity sum 0, empty or non-positive row lists and zero pitch; and
repeated-call determinism with the documented dict keys.

## Related leaves

- vehicle-design/sizing/fuselage-sizing
- vehicle-design/sizing/aircraft-oxygen-system-sizing
- vehicle-design/sizing/fire-protection-sizing

## Behavior contract (gate 3)

The discrete emergency exit configuration logic is exercised by the gate
3 contract test: scripts/test_emergency_exit_configuration.py against
scripts/emergency_exit_configuration_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_emergency_exit_configuration.py

## Compliance

- Standards referenced, not reproduced: the exit type definitions and
  the per-exit credit table are paraphrased into the module constant
  table per standards-map.yaml; far-25 regulation text is never
  reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.
