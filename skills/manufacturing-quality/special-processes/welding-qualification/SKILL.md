---
name: welding-qualification
description: "Use when you must build and check the engineering content of an aerospace weld procedure qualification record (WPS/PQR): compute the weld heat input in kJ per mm from voltage, current, travel speed, and process efficiency; verify heat input, preheat, and interpass temperature against the qualified procedure ranges; confirm the production weld thickness and joint configuration sit inside the qualified coverage; and list the qualification test coupons required for the process and joint type. Produces the heat input, the preheat and interpass margins, the thickness and variable coverage verdicts, and the coupon test matrix that gate the weld procedure qualification. Trigger: weld procedure qualification, WPS PQR, heat input, kJ per mm, preheat, interpass temperature, thickness coverage, coupon test matrix, GTAW, GMAW, qualification test coupons."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: special-processes
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: special-processes
  tags: [welding-qualification, weld-procedure-qualification, wps-pqr, heat-input, preheat-interpass, thickness-coverage, coupon-matrix, qualification-test-coupons]
  version: 0.1.0
  author: Aero Agent Skills
---

# Weld Procedure Qualification (manufacturing-quality/special-processes/welding-qualification)

Use when the task is building and checking the engineering content of an
aerospace weld procedure qualification record (WPS/PQR): computing the
weld heat input in kJ per mm from the voltage, current, travel speed and
process efficiency, verifying that the heat input, preheat and interpass
temperature sit inside the qualified procedure values, confirming that
the production weld thickness and joint configuration are covered by the
qualified ranges, and listing the qualification test coupons required
for the process and joint type. This leaf implements the checks in pure
Python, stdlib only. It pairs with
manufacturing-quality/special-processes/special-process-qualification,
the change-driven neighbor that decides when a process change requires
requalification. Welder personnel qualification and weld NDT
interpretation are out of scope here.

## Domain quick reference

- Heat input: HI = V * I * eta / (v * 1000), with V in volts, I in
  amperes, v in mm/s and eta the arc efficiency, giving kJ per mm. Heat
  input drives the weld cooling rate, bead geometry and heat affected
  zone, so the PQR records a qualified heat input window for the
  production run.
- Arc efficiency (typical practice values, confirm against the
  governing code): gtaw 1.0, gmaw 0.8, gma-pulse 0.85. GTAW is
  effectively direct energy delivery; the short circuit and pulsed
  modes lose part of the electrical power to radiation and spatter.
- Preheat: measured preheat must be at least the required minimum;
  margin = measured minus required. Interpass: measured interpass
  temperature must stay at or below the qualified maximum.
- Thickness coverage: a production weld thickness is covered when it
  falls inside the typical fraction window 0.75x to 2.0x of the
  qualified coupon thickness (typical practice, confirm against the
  governing code).
- Coupon matrix (documented typical aerospace practice set, confirm
  against the governing code, which for aerospace welding is commonly
  AWS D17.1): butt joints qualify with tensile x2, guided bend x4 and a
  volumetric acceptance (radiography at 100 percent; macro etch is the
  code-permitted substitute where radiography is impractical); fillet
  joints with macro etch x2 and fillet break x2; pipe joints with
  tensile x2, guided bend x4 and macro etch.
- AS9100 frames special process control within production control
  (clause context, referenced not reproduced); the module constants
  above are typical engineering practice, not standard text.
- Units: V, A, mm/s, kJ/mm, degC, mm.

## Workflow

1. Identify the process (gtaw, gmaw, gma-pulse) and joint type (butt,
   fillet, pipe), and gather the electricals, travel speed, thicknesses
   and temperatures from the WPS/PQR and the production record.
2. Compute the heat input with heat_input_kj_mm using the process
   efficiency (default 1.0 gtaw, 0.8 gmaw, 0.85 gma-pulse).
3. Compare current, voltage and heat input against their qualified
   ranges with coverage_verdict; a None range means no window was
   stated and the check passes.
4. Verify the thermal requirements: preheat_margin_degC (non-negative
   margin means the minimum was met) and interpass_ok against the
   qualified maximum.
5. Confirm the production thickness sits inside the qualified coverage
   window with thickness_coverage on the coupon thickness.
6. Read the required test coupons for the process and joint from
   TYPICAL_COUPON_MATRIX.
7. Run qualification_summary for the combined verdict: all_ok and the
   findings list name each failed check (thickness-coverage,
   heat-input, current-range, voltage-range, interpass).
8. Validate inputs first: unknown process or joint, non-positive
   voltage, current, travel speed or thickness, a reversed qualified
   range, a required minimum preheat below absolute zero, or a
   non-positive interpass maximum raise ValueError instead of returning
   a silent verdict.

## Worked example

GTAW butt weld, V = 11.5 V, I = 190 A, travel 1.8 mm/s, efficiency 1.0.

- Heat input: 11.5 * 190 * 1.0 / (1.8 * 1000) = 2185 / 1800 = 1.2139
  kJ/mm.
- Qualified coupon thickness 6.35 mm, production 8.0 mm: covered when
  4.7625 <= 8.0 <= 12.7, True. Production 4.0 mm is not covered (below
  4.7625).
- Required minimum preheat 15 degC, measured 22 degC: margin +7 degC.
  Max interpass 150 degC, measured 96 degC: interpass_ok True.
- Qualified heat input range (0.8, 2.0): 1.2139 in-range. Current range
  (160, 220) A: 190 in-range. Voltage range (10.5, 13.0) V: 11.5
  in-range.
- Coupon matrix gtaw/butt: ["tensile-x2", "guided-bend-x4",
  "radiography-100pct"].
- Summary: all_ok True, findings [].
- Fail case (production 4.0 mm, measured interpass 160 degC): all_ok
  False, findings ["thickness-coverage", "interpass"].
- GMA-pulse with the same electricals uses the 0.85 default: 11.5 * 190
  * 0.85 / 1800 = 1.0318 kJ/mm.

## Verification

- Confirm heat_input_kj_mm(11.5, 190, 1.8, 1.0) returns 1.2139 kJ/mm
  within 1e-4, and the gma-pulse default case returns 1.0318.
- Confirm thickness_coverage(6.35, 8.0) gives lo_mm 4.7625, hi_mm
  12.7, covered True, and thickness_coverage(6.35, 4.0) gives covered
  False.
- Confirm preheat_margin_degC(22, 15) returns 7 and interpass_ok(96,
  150) is True; interpass_ok(160, 150) is False.
- Confirm the gtaw/butt coupon list equals ["tensile-x2",
  "guided-bend-x4", "radiography-100pct"].
- Confirm the passing worked example gives all_ok True with findings []
  and the fail case gives all_ok False with findings
  ["thickness-coverage", "interpass"].
- Confirm ValueError rejection of non-physical inputs: voltage 0,
  current -1, travel speed 0, process "smaw", joint "lap", production
  or qualified thickness 0, reversed qualified ranges, efficiency
  outside (0, 1], interpass maximum 0, and a required preheat below
  absolute zero.
- Run the contract test offline: python3
  scripts/test_welding_qualification.py (33 tests, deterministic).

## Related leaves

- manufacturing-quality/special-processes/special-process-qualification:
  the change-driven neighbor; it owns the requalification decision when
  a parameter, equipment or personnel change moves a welding process
  outside its qualified envelope. This leaf builds and checks the weld
  procedure qualification record content; that leaf decides whether a
  change re-triggers control.

## Pitfalls

- Using the wrong arc efficiency: gtaw defaults to 1.0 while gmaw
  (0.8) and gma-pulse (0.85) lose part of the electrical power to
  radiation and spatter - the same electricals give 1.2139 kJ/mm on
  GTAW and 1.0318 kJ/mm on GMA-pulse, so an efficiency mismatch
  mis-qualifies the heat input window.
- Judging preheat and interpass as one rule: preheat needs the
  measured value at least at the required minimum (margin >= 0), while
  interpass must stay at or below the qualified maximum - the two
  bounds fail in opposite directions and both appear in the findings.
- Releasing a production weld outside the thickness window: coverage
  is 0.75x to 2.0x of the qualified coupon thickness, so an 8.0 mm
  weld qualifies off a 6.35 mm coupon but a 4.0 mm weld does not.
- Reading an unstated range as a failure: a None range means no window
  was declared and the coverage check passes - only a stated,
  reversed or exceeded range fails.
- Treating the coupon matrix as code text: the tensile x2, guided bend
  x4, radiography and macro etch set is documented typical aerospace
  practice commonly governed by AWS D17.1 - confirm the matrix against
  the governing code, and note macro etch only substitutes where
  radiography is impractical.
- Confusing this leaf with the requalification decision: it builds and
  checks the WPS/PQR engineering content; whether a process,
  equipment or personnel change re-triggers control belongs to
  special-process-qualification, and welder personnel qualification
  and weld NDT interpretation are out of scope here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_welding_qualification.py

The test covers the worked example anchors (gtaw heat input 1.2139
kJ/mm, gma-pulse 1.0318 kJ/mm at the 0.85 efficiency default), the
efficiency defaults per process, coverage verdict branches including
the inclusive boundaries and the None range, thickness coverage bounds
4.7625 and 12.7 mm with the 4.0 mm failure case, the preheat margin +7
and interpass checks, the coupon matrix contents per process and joint,
the qualification_summary passing and failing cases with their findings,
and ValueError rejection of every non-physical input class.

## Compliance

- AS9100 is referenced for special process control context only, not
  reproduced; standards-map.yaml governs the citation form.
- The coupon matrix, arc efficiencies and thickness fractions are
  documented typical aerospace engineering practices, paraphrased from
  common industry practice; they are not reproductions of AWS D17.1 or
  AS9100 text. Confirm each against the governing code for the program
  before releasing a procedure.
- compliance: STANDARDS-REF, gated: false.
