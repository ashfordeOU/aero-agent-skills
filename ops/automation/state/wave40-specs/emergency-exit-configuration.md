# Wave-40 leaf spec: emergency-exit-configuration (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/emergency-exit-configuration/
- Pack: sizing. Closest siblings: fuselage-sizing (its quick reference
  sizes the cabin from seats abreast and seat pitch and checks passenger
  baggage volume; it names "exits, emergency provisions" only as
  certification context, with no exit type, count or placement logic),
  aircraft-oxygen-system-sizing (crew/passenger oxygen demand, a different
  emergency provision), fire-protection-sizing, evacuation-content leaves
  elsewhere in the tree: none. Whole-tree greps at prep: "25.807",
  "25.813", "emergency exit", "exit type" = 0 hits in skills/; no leaf
  encodes the discrete passenger exit type rules. The rules are discrete
  and tabular (type sizes, per-exit seating credits, capacity bands), the
  same deterministic-table pattern the repo already encodes for other
  constant sets. GENUINE VEHICLE gap (fresh probe).
- Standards id: far-25 (reference-only; sizing pack convention). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Check a passenger emergency exit configuration against the discrete
certification rules: look up each exit type's minimum rectangular opening
(width x height, inches) and its per-exit seating credit from a module
constant table (paraphrase of the public regulatory type definitions and
the per-exit credit table; no regulation text reproduced), verify that the
exits on EACH side of the fuselage alone cover the passenger capacity
(an emergency can make one side unusable, so each side must suffice),
check the capacity-band minimum exit counts and minimum exit types, apply
the two-C-or-larger rule that activates when a Type A/B/C exit is
installed, check the 60 ft adjacent-exit spacing rule on the same side
with the implied maximum seat distance to an exit, and compute the
aggregate evacuation demand ratio. Produces the per-side capacity sums,
the adequacy verdict with the failing-rule list, the required per-side
exit set and the demand ratio that gate the exit configuration. Does NOT
do: evacuation dynamics or timing analysis (evacuation demonstration
analysis is out of scope); aisle, passageway and assist-space access
layout (access rules are not encoded); seat and row structural design;
exit door mechanisms and actuation; ditching, ventral, tailcone and
flightcrew exit provisions (not encoded, disclosed below).

## Model (implement exactly)

Module constants: EXIT_TYPES dict type id -> (width_in, height_in,
seating_credit), public regulatory table values paraphrased into the table:
"A" (42, 72, 110), "B" (32, 72, 75), "C" (30, 48, 55), "I" (24, 48, 45),
"II" (20, 44, 40), "III" (20, 36, 35), "IV" (19, 26, 9). The credits
encode the rule that the maximum seating for each side follows from the
type and number of exits installed on that side (110 for a Type A on a
side, 75 for a Type B, and so on); the builder keeps these table constants
exactly as given. TYPE_RANK size ordering
IV < III < II < I < C < B < A. MAX_ADJACENT_EXIT_SPACING_FT = 60.0.
Capacity bands (paraphrase of the discrete type-and-number rules): 1-9
seats, at least one exit per side of Type IV or larger; 10-19 seats, one
Type III or larger per side; 20-40 seats, two exits per side with one
Type II or larger; 41-110 seats, two exits per side with one Type I or
larger; more than 110 seats, at least two Type I or larger exits per side
with every exit Type III or larger. Disclosed simplifications: the
corner-radius and step-up/step-down geometry of the types, the combined
Type III credit caps, and the ventral/tailcone/ditching/flightcrew
provisions are not encoded; the leaf checks dims and credits only.

Functions (pure stdlib):
- exit_type_dimensions(exit_type) -> dict with keys width_in, height_in,
  seating_credit; ValueError for an unknown type.
- side_exit_capacity(exits) -> int: sum of the seating credits of the
  installed types.
- required_exits_by_capacity(passenger_capacity) -> dict with keys band
  (string), min_exits_per_side, required_per_side (list of type ids,
  sorted largest first), covered (int), excess_seats: the smallest-count
  per-side type multiset whose credit sum covers the capacity, honoring
  the band minimum count and minimum types (exact enumeration over
  combinations with replacement up to 12 exits per side; ties broken by
  smaller excess). ValueError if capacity < 1.
- exit_count_check(passenger_capacity, left_exits, right_exits) -> dict
  with keys passenger_capacity, left_exits, left_capacity, left_failures,
  right_exits, right_capacity, right_failures, adequate (bool), shortfall
  (max(0, capacity - min of the two side sums)). Per side: the credit sum
  must cover the capacity; the count and minimum-type band rules must
  hold; when any Type A/B/C exit is installed the side must carry at least
  two exits of Type C or larger. Failures are reported as short strings
  ("capacity", "minimum-exit-count", "all-exits-minimum-type",
  "one-exit-minimum-type", "two-exits-minimum-type",
  "two-C-or-larger-when-ABC-installed"). ValueErrors: unknown type,
  capacity < 1.
- exit_placement_check(exit_row_numbers, seat_pitch_in) -> dict with keys
  exit_row_numbers (sorted ints), adjacent_gap_ft (list of centerline
  gaps between consecutive exits in feet), spacing_violations (list of
  (index, gap_ft) for gaps above 60 ft), adequate (bool),
  max_implied_seat_distance_ft (half the largest adjacent gap: the
  farthest any seat between two exits can sit from the nearer one).
  ValueErrors: empty or non-positive rows, pitch <= 0.
- evacuation_demand_ratio(passenger_capacity, exit_capacity_sum) -> float
  capacity / sum (a ratio at or below 1.0 means the aggregate exit
  capacity covers the cabin); ValueError if the sum <= 0 or capacity < 1.
Module constants as above; no other magic numbers.

Identities to test: two Type A exits per side credit 220; the required set
for 9 seats is a single Type IV per side (credit exactly 9, excess 0);
a single-exit side always fails the 41-110 and 20-40 bands regardless of
type; the demand ratio is 1.0 when the capacity equals the exit credit sum.

## Worked example

Real module outputs (anchor script run at prep):

180-seat single aisle:
- required_exits_by_capacity(180): band ">110", required_per_side
  ["A", "B"], covered 185, excess 5.
- exit_count_check(180, ["A", "C"], ["A", "C"]): left/right capacity 165,
  adequate False, failures ["capacity"] on both sides, shortfall 15.
- exit_count_check(180, ["A", "B"], ["A", "B"]): capacities 185 both
  sides, adequate True, no failures.
- evacuation_demand_ratio(180, 165) = 1.090909 (inadequate aggregate);
  evacuation_demand_ratio(180, 185) = 0.972973 (adequate).

60-seat regional:
- required_exits_by_capacity(60): band "41-110", required_per_side
  ["I", "III"], covered 80, excess 20 (one Type I floor-level exit plus
  one Type III overwing exit per side).
- exit_count_check(60, ["C", "I"], ["C", "I"]): adequate False,
  failures ["two-C-or-larger-when-ABC-installed"] both sides (installing
  a Type C forces a second Type C or larger exit on that side).
- exit_count_check(60, ["C", "C"], ["C", "C"]): adequate True.
- exit_count_check(60, ["C"], ["C"]): left capacity 55, failures
  ["capacity", "minimum-exit-count", "two-C-or-larger-when-ABC-installed"].

Placement (32 in seat pitch): exits at rows 1, 12, 23, 32: adjacent gaps
29.3333, 29.3333, 24.0 ft, adequate True, max implied seat distance
14.667 ft. Exits only at rows 1 and 32: gap 82.6667 ft, adequate False,
spacing_violations [(1, 82.6667)]. Regional 20 rows at 31 in pitch with
exits at rows 1 and 20: gap 49.0833 ft, adequate True, max implied seat
distance 24.542 ft.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (reproduced at prep with stdlib math).

## Validation list (contract test must include)

- exit_type_dimensions("A") = (42, 72, 110); the full EXIT_TYPES table
  matches the constants above exactly (all 7 types).
- side_exit_capacity(["A", "C"]) = 165; (["A", "A"]) = 220.
- required_exits_by_capacity(180) -> ["A", "B"], covered 185, excess 5;
  (60) -> ["I", "III"], covered 80, excess 20; (9) -> ["IV"] excess 0;
  (853) -> eight Type A, covered 880, excess 27.
- exit_count_check verdicts of the worked example (adequate flags and
  failure lists exactly as printed).
- Band identity: capacity 60 with one Type A per side fails
  "minimum-exit-count"; capacity 25 with ["III", "III"] fails
  "one-exit-minimum-type"; capacity 180 with ["I", "I"] per side fails
  "capacity" (90 < 180) and "two-exits-minimum-type" is not triggered
  (two Type I or larger ARE present, but the credit sum still fails).
- exit_placement_check anchors: gaps 29.3333/29.3333/24.0 ft, adequate
  True; single 82.6667 ft gap flagged; 49.0833 ft gap passes.
- evacuation_demand_ratio anchors 1.090909 and 0.972973 within 1e-5;
  ratio 1.0 at capacity equal to the credit sum.
- ValueErrors: unknown type "F", empty or non-positive row lists, pitch 0,
  capacity 0, exit capacity sum 0.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave40-emergency-exit-configuration.yaml)

Query 1 (copy verbatim):
  "check the emergency-exit-configuration against the far-25 exit-type-requirements for the 180-seat cabin with type-a and type-c doors on each side"
  intent: "vehicle-design; per-side exit capacity and type rules verdict"
  expected_skill: "vehicle-design/sizing/emergency-exit-configuration"
Query 2 (copy verbatim):
  "run the exit-count-check and the adjacent-exit spacing rule on the proposed per-side exit types and row locations of the single-aisle cabin"
  intent: "vehicle-design; exit count adequacy and 60 foot spacing verdict"
  expected_skill: "vehicle-design/sizing/emergency-exit-configuration"
Task ids: w40-emergency-exit-configuration-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must configure passenger emergency
exits against the discrete exit-type rules:" and include the outputs in
the Claim. First tag: emergency-exit-configuration. Additional tags ONLY:
exit-type-requirements, exit-count-check, exit-placement-rule,
per-side-exit-capacity, evacuation-demand-ratio. NEVER single generic
words (exit, door, emergency, evacuation, seat, cabin, capacity, type,
config, rule). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): seats-abreast, seat-pitch,
baggage-volume (fuselage-sizing); oxygen-demand, oxygen-mask,
crew-oxygen (aircraft-oxygen-system-sizing); extinguishing-agent
(fire-protection-sizing); evacuation-time, evacuation-analysis,
evacuation-demonstration, flow-rate (evacuation dynamics leaves; this
leaf is the discrete configuration check only).
