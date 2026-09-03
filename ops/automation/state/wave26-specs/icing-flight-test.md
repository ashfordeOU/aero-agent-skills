# Wave-26 leaf spec: icing-flight-test (flight-test-operations, envelope pack)

- Path: skills/flight-test-operations/envelope/icing-flight-test/
- Pack: envelope (existing siblings: envelope-expansion, v-speeds,
  stall-characteristics-testing, spin-testing, high-angle-of-attack-
  testing, load-factor-envelope, flight-loads-survey,
  structural-coupling-test)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-test-operations

## Claim

Plan an icing certification flight test campaign for an airplane under
the FAR/CS 25 Appendix C icing envelopes: classify the natural icing
environment (continuous maximum and intermittent maximum) from liquid
water content, median volumetric diameter, and total air temperature,
judge whether an icing encounter is inside the certification envelope,
screen natural-icing search conditions, build the artificial ice shape
test matrix that simulates the critical in-flight and runback ice
shapes on the unprotected surfaces, and assess the ice protection
system effectiveness test points. Produces the envelope verdict per
encounter, the natural-icing search criteria, the artificial shape
matrix, and the effectiveness test verdict that gate the icing flight
test program.

Does NOT do: size or design the ice protection system (vehicle-design
sizing ice-protection-sizing owns the thermal design, heat flux, catch
efficiency and bleed-air sizing math), qualify equipment in a ground
environmental chamber (avionics do160 environmental-qualification owns
equipment-level test), or fly the stall/vibration envelopes
(envelope-pack siblings). This leaf is the icing-condition
classification and flight test matrix layer for the airplane-level
icing campaign.

## Model (implement exactly)

Icing envelope model (module constants, documented as a simplified
typical summary of the FAR/CS 25 Appendix C envelope at reference
level, NOT the regulation's full table; the SKILL body must say the
full appendix C table is authority-controlled and this module uses
paraphrased representative boundary points):
- Continuous maximum (stratiform) at the reference altitude band:
  TAT range -30 C to 0 C; representative LWC limit at -10 C:
  LWC_CM_MAX = 0.44 g/m3 (module constant), MVD range 15 to 40
  micron (CM_MVD_MIN = 15.0, CM_MVD_MAX = 40.0); LWC scales linearly
  down to 0.2 g/m3 at 0 C and to 0.15 g/m3 at -30 C (two linear
  segments; module constants LWC_CM_0C = 0.2, LWC_CM_N30C = 0.15).
- Intermittent maximum (cumuliform): representative LWC limit at
  -10 C: LWC_IM_MAX = 1.4 g/m3, MVD range 15 to 50 micron
  (IM_MVD_MIN = 15.0, IM_MVD_MAX = 50.0); LWC scales linearly to
  0.65 g/m3 at 0 C and to 0.35 g/m3 at -30 C (module constants
  LWC_IM_0C = 0.65, LWC_IM_N30C = 0.35).
Functions:
- cm_lwc_limit(tat) / im_lwc_limit(tat) -> float by the piecewise
  linear segments (clamp TAT to [-30, 0]); ValueError outside the
  clamp range is not raised (clamp), but non-finite TAT raises.
- envelope_verdict(lwc, mvd, tat) -> dict {in_envelope (bool),
  regime ("continuous-max" | "intermittent-max" | "outside"),
  margin (limit_lwc - lwc), reasons}: regime continuous-max when
  lwc <= cm_lwc_limit(tat) and mvd within CM band; intermittent-max
  when lwc <= im_lwc_limit(tat) and mvd within IM band (and above the
  continuous limit); outside otherwise; margin reported against the
  governing limit. A drizzle/SLD encounter (mvd > 50 micron) is
  outside the Appendix C envelope by this model (module constant
  SLD_MVD_MIN = 50.0) with an explicit reason "supercooled-large-
  droplet conditions exceed the appendix C envelope".
- encounter_severity(lwc, tat, duration_min) -> (severity index 0..3,
  label): index from the ratio lwc / cm_lwc_limit(tat): < 0.5 trace
  (0), < 1.0 light (1), < 1.5 moderate (2) when also within the
  intermittent envelope (else severe), >= 1.5 severe (3); duration
  scales the label up one step when duration_min > 30 (module constant
  SEVERE_DURATION_MIN = 30.0) capped at severe.
- natural_icing_search_ok(tat, cloud_base_ft, freezing_level_ft,
  lwc_forecast) -> (ok_bool, reasons): ok when tat <= 0 C and tat >=
  -30 C and lwc_forecast >= 0.1 * cm_lwc_limit(tat) (module constant
  SEARCH_LWC_FRACTION = 0.1) and the freezing level is below the test
  altitude band (freezing_level_ft < cloud_base_ft check as input);
  ValueError on non-finite.
- artificial_shape_check(shapes) -> dict: each artificial shape
  dict {surface (str), type ("glaze" | "rime" | "runback" | "mixed"),
  coverage_frac (0..1), roughness_ok (bool)}; issue list when a
  critical unprotected surface (module constant CRITICAL_SURFACES =
  ["wing", "horizontal-tail", "vertical-tail", "windshield", "probe"])
  is missing from the shapes or has coverage_frac < 0.8 (module
  constant COVERAGE_MIN = 0.8) or roughness_ok False; verdict pass
  when no issues.
- effectiveness_test_points(configs, envelope_rows) -> list of rows
  {config, condition, expected_regime}: pairs each test configuration
  (anti-ice on/off, de-ice cycle setting from inputs) with the
  envelope rows that must be flown; used by the SKILL workflow.
- summarize(...) -> dict for the SKILL worked example.
ValueError on: negative lwc/mvd, non-finite values, coverage_frac
outside [0, 1], unknown surface in an artificial shape.

## Worked example

1. Encounter at TAT -10 C, LWC 0.30 g/m3, MVD 20 micron:
   cm_lwc_limit(-10) = 0.44; 0.30 <= 0.44 and MVD in CM band ->
   in_envelope True, regime continuous-max, margin 0.14.
2. TAT -10 C, LWC 1.0 g/m3, MVD 25 micron: above CM limit,
   im_lwc_limit(-10) = 1.4 -> regime intermittent-max, margin 0.4.
3. TAT -10 C, LWC 1.6 g/m3, MVD 25 micron: above both -> outside.
4. TAT -5 C, LWC 0.3 g/m3, MVD 60 micron: outside with the
   supercooled-large-droplet reason (SLD).
5. encounter_severity at TAT -10 C with LWC 0.22 (ratio 0.5) ->
   light (1); duration 45 min -> moderate (2).
6. artificial_shape_check with shapes covering wing and horizontal-
   tail but missing the vertical-tail -> issue; with all critical
   surfaces at coverage 0.9 and roughness_ok True -> pass.
7. natural_icing_search_ok(tat -8, cloud_base 3000, freezing_level
   2000, lwc_forecast 0.1) -> ok False (freezing level below cloud
   base); with freezing_level 4000 and lwc 0.1 -> ok True.
8. ValueError on negative LWC and on coverage_frac 1.2.
Keep at least 16 test methods (LWC limit segments at the three anchor
temperatures, envelope verdict regimes, SLD exclusion, severity with
the duration step, search criteria, artificial shape matrix checks,
ValueErrors).

## Corpus tasks (ids w26-icing-flight-test-1/2)

Distinctive tokens: icing flight test, natural icing, artificial ice
shapes, appendix C envelope, liquid water content, median volumetric
diameter, icing encounter severity, ice protection effectiveness test,
runback ice, supercooled large droplet. Avoid: ice protection sizing,
anti-ice heat flux, catch efficiency, bleed air, protected area
(vehicle-design ice-protection-sizing), thermal de-ice design,
equipment environmental qualification (do160).

1. "classify the icing encounter at minus 10 C with 0.3 grams per
   cubic meter liquid water content and 20 micron median volumetric
   diameter against the appendix C continuous maximum envelope and
   rate the severity for the icing flight test log"
2. "plan the artificial ice shape matrix for the icing certification
   flight test: check the critical surface coverage for the glaze and
   runback shapes and list the ice protection effectiveness test
   points that must be flown"

## SKILL body notes

Pair with envelope-expansion (program sequencing) and v-speeds (test
speed reference), and cite vehicle-design ice-protection-sizing as the
design-side sibling this leaf does not replace. Envelope boundaries
are a simplified typical summary at reference level; the full
Appendix C table is authority-controlled and must not be reproduced.
Standards referenced not reproduced.
