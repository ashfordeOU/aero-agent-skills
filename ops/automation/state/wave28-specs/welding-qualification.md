# Wave-28 leaf spec: welding-qualification (manufacturing-quality, special-processes pack)

- Path: skills/manufacturing-quality/special-processes/welding-qualification/
- Pack: special-processes (existing sibling:
  special-process-qualification)
- Standards ids: as9100  (Ledger Standard: as9100)
- Family: manufacturing-quality

## Claim

Build and check the engineering content of an aerospace weld procedure
qualification record (WPS/PQR): compute the weld heat input in kJ/mm
from the voltage, current, and travel speed with the process
efficiency, verify that the heat input, preheat, and interpass
temperature stay inside the qualified procedure ranges, check that the
production weld thickness and joint configuration are covered by the
qualified ranges, and confirm the required qualification test coupons
for the process and joint type. Produces the heat input, the preheat
and interpass margins, the thickness and variable coverage verdicts,
and the coupon test matrix that gate the weld procedure qualification.

Does NOT do: decide whether a process change requires requalification
(special-process-qualification owns change-driven requalification
decisions); select the filler metal or joint design (engineering
judgment inputs here); certify welders (personnel qualification is out
of scope).

## Model (implement exactly)

Module constants:
- HEAT_INPUT_UNITS = "kJ/mm".
- TYPICAL_COUPON_MATRIX = {process: {joint: [test list]}} with
  process keys "gtaw", "gmaw", "gma-pulse" and joints "butt", "fillet",
  "pipe": butt -> ["tensile-x2", "guided-bend-x4", "radiography-100pct"
  or "macro-etch"], fillet -> ["macro-etch-x2", "fillet-break-x2"],
  pipe -> ["tensile-x2", "guided-bend-x4", "macro-etch"]. The SKILL
  body must label this matrix as a documented typical aerospace
  practice set, not a standard reproduction.
- THICKNESS_RANGE_DEFAULT = (0.75, 2.0) (fractions of the qualified
  thickness that a production thickness must fall inside; labeled
  typical practice, confirm against the governing code).

Inputs:
- process (str in {"gtaw", "gmaw", "gma-pulse"}),
- joint_type (str in {"butt", "fillet", "pipe"}),
- voltage_V (float), current_A (float), travel_speed_mm_s (float),
- process_efficiency (float, default 1.0 for gtaw, 0.8 for gmaw,
  0.85 for gma-pulse - documented typical arc efficiencies),
- qualified_thickness_mm (float, thickness of the PQR coupon),
- production_thickness_mm (float),
- required_min_preheat_degC (float), measured_preheat_degC (float),
- max_interpass_degC (float), measured_interpass_degC (float),
- qualified_heat_input_range_kj_mm (tuple (lo, hi) or None),
- qualified_current_range_A (tuple or None),
- qualified_voltage_range_V (tuple or None).

Functions:
- heat_input_kj_mm(voltage_V, current_A, travel_speed_mm_s,
  process_efficiency) -> float: voltage*current*efficiency /
  (travel_speed_mm_s*1000.0). ValueError on voltage <= 0, current <= 0,
  travel <= 0, efficiency <= 0 or > 1.
- coverage_verdict(value, qrange) -> str: "in-range" when qrange is
  None (no stated range) or lo <= value <= hi, else "out-of-range".
  ValueError on qrange with lo > hi.
- thickness_coverage(qualified_thickness_mm, production_thickness_mm,
  range_fractions=None) -> dict: with default fractions (0.75, 2.0):
  covered = 0.75*qt <= pt <= 2.0*qt; return {covered: bool, lo_mm,
  hi_mm, verdict}. ValueError on either thickness <= 0.
- preheat_margin_degC(measured, required_min) -> float: measured -
  required_min. ValueError on required_min < -273.15.
- interpass_ok(measured, max_allowed) -> bool. ValueError on max <= 0.
- qualification_summary(inputs) -> dict: heat input, current and
  voltage coverage verdicts, heat-input coverage verdict (when the
  qualified range is given), preheat margin, interpass ok, thickness
  coverage, coupon matrix (list of required tests), all_ok (bool:
  thickness covered AND heat input in range (or None) AND current and
  voltage in range (or None) AND interpass ok), findings (list of
  short strings for each failed check).
ValueError on: process not in the set, joint_type not in the set,
voltage <= 0, current <= 0, travel <= 0, production_thickness <= 0,
qualified_thickness <= 0.

## Worked example

Process gtaw, joint butt, V = 11.5, I = 190, travel 1.8 mm/s,
efficiency 1.0:
- heat_input = 11.5*190*1.0/(1.8*1000) = 2185/1800 = 1.2139 kJ/mm
  (assert within 1e-4).
- qualified thickness 6.35 mm; production 8.0 mm: covered (4.76 <=
  8.0 <= 12.7) True; assert lo 4.7625, hi 12.7.
- production 4.0 mm -> covered False (below 4.7625); assert.
- required min preheat 15 C, measured 22 -> margin +7 C (assert);
  max interpass 150 C, measured 96 -> interpass_ok True.
- qualified heat-input range (0.8, 2.0) -> 1.2139 in-range; current
  range (160, 220) -> 190 in-range; voltage range (10.5, 13.0) ->
  11.5 in-range.
- coupon matrix for gtaw/butt -> ["tensile-x2", "guided-bend-x4",
  "radiography-100pct"] (assert list equality).
- all_ok True, findings [] for the passing case; a fail case with
  production thickness 4.0 and interpass 160 -> all_ok False and
  findings contain "thickness-coverage" and "interpass".
- gmaw/gma-pulse efficiency defaults: heat input drops by the
  efficiency factor; assert gma-pulse with same electricals returns
  11.5*190*0.85/1800 = 1.0318 (within 1e-4).
- ValueErrors on V 0, I -1, travel 0, process "smaw", joint "lap",
  production thickness 0.
Keep at least 16 test methods: heat input per process, efficiency
defaults, coverage verdict branches, thickness range boundaries,
preheat margin, interpass, coupon matrix contents per process/joint,
summary all-ok and findings, ValueErrors.

## Corpus tasks (ids w28-welding-qualification-1/2)

Distinctive tokens: weld procedure qualification, WPS PQR heat input,
kJ per mm, preheat and interpass verification, weld coupon test
matrix, thickness coverage. Avoid: requalification trigger, process
change, NADCAP change assessment (special-process-qualification);
welding NDT interpretation (ndt leaves).

1. "build the aerospace weld procedure qualification record: compute
   the heat input in kJ per mm from voltage current and travel speed
   and verify preheat and interpass against the procedure"
2. "check the weld procedure covers the production joint: confirm the
   thickness range, the heat input window, and the coupon test matrix
   for the GTAW butt weld"

## SKILL body notes

Pair with special-process-qualification (the change-driven neighbor).
The coupon matrix, arc efficiencies, and thickness fractions are
documented typical engineering practices (paraphrased common industry
practice), not reproductions of AWS D17.1 or AS9100 text; the body must
say to confirm against the governing code. AS9100 cited reference-only
for special-process control context.
