---
name: e1012-segr-seb
description: "Use when estimate destructive heavy-ion, proton, and neutron Single Event Gate Rupture (SEGR) and Single Event Burnout (SEB) rates for power devices in a space radiation environment per ECSS-E-ST-10-12C §9.4.1.6: categorize the component as power MOSFET (susceptible to both SEGR and SEB) or bipolar transistor (SEB only), fit a Weibull cross-section model to device heavy-ion test data, integrate the fitted cross-section against the orbit LET spectrum, apply the bias-derating condition appropriate to each effect, compute the predicted destructive event rate in events per device per day, and compare against the mission destructive-SEE rate requirement with a design margin. Trigger: ecss, e-st-10-system-scope, segr, seb, single-event-burnout, single-event-gate-rupture, destructive-see, weibull, power-mosfet, heavy-ion-rate."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-system-scope, segr, seb, single-event-burnout, single-event-gate-rupture, destructive-see, weibull, power-mosfet, heavy-ion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — SEGR and SEB Destructive Rate Prediction (space-systems/ecss/e1012-segr-seb)

Use when the task is estimating destructive Single Event Gate Rupture (SEGR)
and Single Event Burnout (SEB) rates for power transistors in a space radiation
environment, following the procedure in ECSS-E-ST-10-12C §9.4.1.6 using
a Weibull cross-section model integrated against a mission heavy-ion LET
spectrum.

## Domain quick reference

- **SEGR (Single Event Gate Rupture)** is the permanent destruction of the gate
  oxide in a power MOSFET caused by a heavy-ion track traversing the gate region
  while a drain-source or gate-drain voltage is applied.  Once the oxide
  ruptures the device is shorted and non-recoverable.  SEGR is relevant only for
  power MOSFETs; bipolar transistors have no gate oxide and cannot experience
  SEGR.
- **SEB (Single Event Burnout)** is a catastrophic thermal runaway triggered
  when a heavy ion activates the parasitic bipolar structure inherent in a power
  MOSFET or a bipolar transistor.  If the supply can sustain the resulting
  current the device enters second breakdown and is destroyed.  Both power
  MOSFETs and bipolar transistors are susceptible to SEB.
- Both effects are **destructive**: a single qualifying particle strike
  permanently removes the device from service.  Unlike soft errors, they cannot
  be scrubbed or corrected.  The mission reliability budget must account for the
  probability that any device in the power subsystem fails before end-of-life.
- The **Weibull cross-section** parameterization σ(LET) = σ_sat × (1 − exp(
  −((LET − LET_th) / W)^s)) for LET > LET_th, else 0, describes how the
  probability of an event rises from zero at the threshold LET to the saturated
  cross-section σ_sat.  Four parameters are required: LET_th (threshold),
  W (width), s (shape exponent), and σ_sat (saturation cross-section, cm²).
  All four are extracted from device-level heavy-ion characterisation data at
  the bias conditions expected in service.
- **Bias condition** is critical: SEGR susceptibility increases sharply with
  applied gate or drain voltage; SEB susceptibility rises with drain-source
  voltage.  The Weibull parameters are only valid at the bias level at which
  the characterisation test was performed.  If the in-service bias differs,
  use the test data set closest to (or above) the in-service value and note
  the conservative assumption; do not interpolate uncritically.
- The predicted rate R (events/device/day) is obtained by integrating
  σ(LET) × φ(LET) over the differential LET spectrum φ(LET), expressed per
  unit LET and per day (ions/cm²/day per MeV·cm²/mg), using the trapezoidal
  rule.  Because the spectrum is already a per-day flux, the integral is the
  daily rate; divide by 86 400 only when a per-second figure is wanted.
  Keep the spectrum, the cross-section and the rate requirement on the same
  time base — a mismatched time base is a four-to-five order-of-magnitude
  error and is the most common arithmetic slip in this calculation.
- A **10× design margin** is standard: the design passes only when the
  predicted rate is ≤ one-tenth of the system destructive-SEE rate
  requirement.

## Workflow

1. Obtain the device data sheet and heavy-ion characterisation test report.
   Record the device type (power MOSFET or bipolar transistor), the applied
   bias during the test (V_DS and V_GS for MOSFETs; V_CE for bipolars), and
   the Weibull parameters (LET_th, W, s, σ_sat) for each applicable effect
   (SEGR for MOSFETs only; SEB for both types).  Verify that σ_sat has been
   reached within the test LET range; if not, flag the σ_sat as a lower bound
   and note that the actual saturation cross-section may be higher.

2. Determine which effects apply to the device under evaluation: power MOSFETs
   must be assessed for both SEGR and SEB; bipolar transistors for SEB only.
   Record this as the **effect set** for the device.  A device for which SEGR
   is attempted but the device type is not a power MOSFET must be rejected
   before the calculation proceeds.

3. Confirm the in-service bias against the test bias.  For SEB: note whether
   V_DS_service < V_DS_test (the test is conservative) or V_DS_service >
   V_DS_test (a test at the higher voltage is needed).  For SEGR: apply the
   same check to V_GS.  Record the bias margin (V_threshold − V_applied) /
   V_threshold; a negative margin means the device is operating above the
   characterisation point and the assessment is invalid until retested.

4. Obtain the differential heavy-ion LET spectrum for the shielded device
   location and mission duration.  Confirm the spectrum upper bound exceeds
   LET_th; if it does not, the predicted rate is zero and the device is
   immune to this effect in this environment — record as environment-limited,
   not a device pass.

5. Evaluate the Weibull cross-section at each LET point in the spectrum.
   For LET ≤ LET_th the cross-section is zero.  For LET > LET_th apply the
   Weibull formula.  Do not extrapolate σ above σ_sat.

6. Integrate σ(LET) × φ(LET) over LET using the trapezoidal rule.  With the
   per-day spectrum convention the integral is already the rate in
   events/device/day; divide by 86 400 for the equivalent per-second rate.
   For a mission spanning T days, multiply the daily rate by T to obtain the
   total expected events per device.

7. Apply the 10× design margin: the device passes if the predicted rate is ≤
   rate_requirement / 10.  Record the log₁₀ margin (positive = passing).
   A device that passes at the raw rate but fails the 10× margin is flagged
   as a margin shortfall, not a pass.

8. For each assessed device, compile a summary record containing: device type,
   effect assessed, Weibull parameters, test bias, in-service bias, bias margin,
   predicted rate (events/device/day), rate requirement, design margin status,
   and any assumptions or flags (σ_sat lower-bound, spectrum upper bound below
   LET_th, bias extrapolation).

## Pitfalls

- Applying SEGR to a bipolar transistor: bipolar devices have no gate oxide
  and therefore cannot experience SEGR; attempting the calculation anyway
  produces a meaningless number.
- Using Weibull parameters from a test at a lower bias than the in-service
  condition without flagging the extrapolation as non-conservative: SEGR and
  SEB thresholds both decrease at higher applied voltages, so a characterisation
  at low bias underestimates the cross-section at high bias.
- Treating a zero rate (spectrum maximum below LET_th) as a device pass rather
  than an environment-limited result: if the mission orbit changes, the same
  device may move into a regime where the spectrum does exceed LET_th.
- Forgetting the 10× design margin and reporting compliance based solely on
  the rate meeting the numerical requirement: the ECSS-E-ST-10-12C margin
  policy requires the additional margin factor.
- Confusing σ_sat (cm² per device) with σ_sat per bit or per cell: for SEGR
  and SEB the relevant area is the device-level sensitive area, not a per-cell
  value.
- Mixing time bases between the LET spectrum and the rate requirement: a
  per-second flux integrated and then scaled by 86 400 as though it were a
  per-day flux inflates the predicted rate by that same factor and turns a
  compliant device into an apparent failure.

## Behavior contract (gate 3)

The Weibull cross-section model, bias-condition check, heavy-ion rate integral,
SEGR and SEB assessment, device categorization, orbit environment lookup, and
margin-to-requirement calculation are exercised by the gate 3 contract test:
scripts/test_e1012_segr_seb.py against scripts/e1012_segr_seb_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_segr_seb.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the standard and clause
  as anchor only — no verbatim reproduction.
- compliance: STANDARDS-REF, gated: false.
