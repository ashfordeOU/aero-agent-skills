---
name: gnss-raim-fde
description: "Use when you must run receiver autonomous integrity monitoring (RAIM) fault detection and exclusion on an overdetermined GNSS pseudorange measurement set: build the geometry matrix H from satellite line-of-sight unit vectors, solve the overdetermined least-squares navigation solution, form the residual test statistic and compare it against a chi-square threshold at 1e-5 false-alarm probability, compute the horizontal protection level from the worst-case satellite slope, and identify the faulty satellite by the largest normalized residual for exclusion. Produces the detection verdict, the horizontal protection level, and the excluded-satellite recommendation that gate a GNSS integrity and availability assessment. Trigger: RAIM, receiver autonomous integrity monitoring, fault detection and exclusion, horizontal protection level, chi-square threshold, normalized residual, GNSS integrity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [gnss-raim-fde, raim, receiver-autonomous-integrity-monitoring, fault-detection-and-exclusion, horizontal-protection-level, chi-square-threshold, normalized-residual, gnss-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# GNSS RAIM Fault Detection and Exclusion (gnc-autonomy/navigation/gnss-raim-fde)

Use when the task is GNSS integrity monitoring on an overdetermined
pseudorange geometry: detect a faulty satellite through the residual
test statistic, bound the horizontal position error with the horizontal
protection level (HPL), and exclude the worst satellite by normalized
residual so the remaining set can be re-solved. This leaf implements
receiver autonomous integrity monitoring (RAIM) fault detection and
exclusion (FDE) in pure Python, stdlib only, following the RTCA DO-229
MOPS protection level concepts in paraphrased summary form. It guards
the position fix produced by gnss-pseudorange-positioning, sits beside
dilution-of-precision for geometry quality, and feeds the protected
position into kalman-filter-design for time-domain fusion. All math is
deterministic and offline; units are SI (metres).

## Domain quick reference

- Geometry matrix: H has n rows [ux, uy, uz, 1.0] from the satellite
  line-of-sight unit vectors plus the clock column; n >= 5 gives one
  spare satellite so RAIM residuals exist. H^T H is the 4x4 normal
  matrix and the least-squares state is x_hat = (H^T H)^-1 H^T y.
- Residuals: r = y - H x_hat with sse = sum r_i^2, so the test
  statistic is T = sse / sigma^2, sigma the pseudorange 1-sigma noise
  (default 6.0 m).
- Detection: compare T against the chi-square threshold
  chi2_quantile(n - 4, 1 - PFA) at false-alarm probability PFA = 1e-5;
  detected when T exceeds the threshold. The chi-square quantile uses
  the Wilson-Hilferty approximation and the standard normal quantile
  uses the Acklam rational approximation, both implemented here.
- Protection level: with A = (H^T H)^-1 H^T and the residual
  sensitivity S = I - H A, the satellite slope is
  slope_j = sqrt(A[0][j]^2 + A[1][j]^2) / sqrt(S[j][j]) and
  HPL = max_j slope_j * sigma * sqrt(chi2_quantile(n - 4, 1 - PFA)).
- Fault exclusion: normalized residual nr_i = |r_i| / (sigma *
  sqrt(S[i][i])); the worst satellite is the argmax, exclusion leaves
  n - 1 satellites, and the test is re-run on the re-solved subset
  (needs n >= 6, at least one spare).
- Availability: available when HPL <= HAL, otherwise unavailable, with
  HAL the horizontal alert limit of the operation (556 m for
  non-precision approach per DO-229 summary).
- RAIM protection level and threshold relations are standard engineering
  methodology paraphrased from the RTCA DO-229 MOPS; no MOPS table or
  algorithm text is reproduced (gated standard in standards-map.yaml).

## Workflow

1. Collect the satellite line-of-sight unit vectors from the
   overdetermined set (n >= 5) and build the geometry matrix with
   geometry_matrix(sat_dirs); non-unit directions are rejected and
   renormalized internally.
2. Solve the overdetermined least-squares navigation problem with
   lsq_solve(H, y), which returns the 4-state x_hat, the residuals and
   the sum of squared residuals sse.
3. Run fault_detect(sse, n, sigma, pfa) to get the test statistic, the
   chi-square threshold and the detected verdict at the chosen
   false-alarm probability (default 1e-5).
4. When detected, bound the horizontal error with
   raim_hpl(H, sigma, pfa), the worst-case-satellite protection level.
5. Identify the faulty satellite with exclude_faulty(H, y), which
   returns the worst satellite index and the normalized residual list.
6. Re-solve on the remaining n - 1 satellites with lsq_solve and re-run
   fault_detect to confirm the alarm clears.
7. Judge the operation with availability_verdict(hpl, hal) against the
   phase-appropriate alert limit, then confirm the deterministic checks
   with the contract test scripts/test_gnss_raim_fde.py.

## Worked example

Six satellites with unit directions u1 = [0.4082, 0.8165, 0.4082],
u2 = [-0.4082, 0.8165, 0.4082], u3 = [0.0, -0.7071, 0.7071],
u4 = [0.7071, 0.0, 0.7071], u5 = [-0.7071, 0.0, 0.7071],
u6 = [0.0, 0.7071, -0.7071], true user state
x_true = [10.0, -20.0, 30.0, 0.0] m (position offset and clock bias),
and noise drawn with random.Random(42) at sigma 6.0 m (draw
[-0.9, -1.0, -0.7, 4.2, -0.8, -9.0] m to one decimal).

- Clean set (no bias): T = 0.143 against the threshold 24.669
  (chi2_quantile(2, 0.99999), df = n - 4 = 2), detected False.
- A 200 m bias on satellite 1 (index 0): T = 495.2, detected True.
- Protection level: HPL = 44.5 m (worst-case slope times sigma times
  the threshold root).
- Exclusion: normalized residuals peak at 22.3 on satellite 0 against
  19.3 on the runner-up, a margin above 10%, so satellite 0 is the
  faulty one.
- After excluding satellite 0 and re-solving with the remaining 5
  satellites: T = 0.013 against the df = 1 threshold 21.68, detected
  False, the alarm clears.
- Availability: availability_verdict(44.5, 556) = "available" for the
  556 m non-precision approach alert limit, and
  availability_verdict(44.5, 30.0) = "unavailable" under a 30 m limit.

## Verification

- Confirm geometry_matrix builds 6 rows of [ux, uy, uz, 1.0] and
  rejects fewer than 5 satellites, non-unit directions and malformed
  vectors with ValueError.
- Confirm lsq_solve recovers an exact state on a round trip (residuals
  near zero, residuals orthogonal to the H columns) and that the clean
  case gives T = 0.143 within 0.01 with detected False.
- Confirm the bias case gives T = 495.2 within 0.5 with detected True,
  HPL = 44.5 m within 0.3, worst satellite index 0 with normalized
  residual 22.3, and that the re-solved 5-satellite set gives T = 0.013
  within 0.01 with detected False.
- Confirm chi2_quantile(2, 0.99999) = 24.669 within 0.01,
  chi2_quantile(6, 0.99999) = 34.052 within 0.05 and
  normal_quantile(0.99999) = 4.2649 within 1e-3.
- Confirm the threshold grows as the false-alarm probability shrinks,
  availability_verdict returns available/unavailable around the alert
  limit, and non-physical inputs (fewer than 5 satellites, non-unit
  directions, pfa outside (0, 1), df below 1, zero residual
  sensitivity) raise ValueError.
- Run the contract test offline: python3
  scripts/test_gnss_raim_fde.py (34 tests, deterministic).

## Related leaves

- gnc-autonomy/navigation/gnss-pseudorange-positioning: the position
  fix and clock solution this monitor guards.
- gnc-autonomy/navigation/dilution-of-precision: geometry quality
  (GDOP/PDOP/HDOP) and subset selection for the same satellite sets.
- gnc-autonomy/navigation/kalman-filter-design: filtering the protected
  position over time.
- gnc-autonomy/navigation/navigation-frames: coordinate conventions for
  the ECEF geometry.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gnss_raim_fde.py

The test covers the six-satellite worked example (clean case T = 0.143
no alarm, 200 m bias case T = 495.2 alarm, HPL = 44.5 m, worst
satellite identification with margin over the runner-up, and the
re-solved exclusion rerun), the geometry matrix build and its ValueError
rejections, the least-squares round trip and residual orthogonality, the
Acklam normal quantile and Wilson-Hilferty chi-square anchors and their
monotonicity, threshold behavior in the false-alarm probability, the
residual sensitivity projection properties, the degenerate-geometry
rejection, the exclusion guard below six satellites, the availability
verdicts, and ValueError rejection of non-physical inputs.

## Compliance

- RTCA DO-229 (Minimum Operational Performance Standards for GPS/GNSS
  Airborne Equipment) is referenced, not reproduced: RAIM detection
  thresholds and protection level relations above are paraphrased
  summary methodology per standards-map.yaml (gated: true, never
  reproduce MOPS tables or appendix text verbatim).
- compliance: STANDARDS-REF, gated: false.
