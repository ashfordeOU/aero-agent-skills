---
name: rnp-anp-containment
description: "Use when you must assess the RNP containment of a performance based navigation segment: compute the actual navigation performance (ANP) as the 95 percent containment bound from a lateral position error sigma or accept a directly supplied ANP, apply the required navigation performance (RNP) for the segment with an optional margin fraction, and decide whether the ANP stays inside the RNP. Produces the ANP, the containment margin and the pass or fail verdict that gate FMS navigation dispatch. Trigger: required navigation performance, actual navigation performance, RNP containment, ANP comparison, lateral position error sigma, 95 percent containment, performance based navigation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: flight-management
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: flight-management
  tags: [rnp-anp-containment, required-navigation-performance, actual-navigation-performance, rnp-containment, anp-comparison, lateral-position-error, 95-percent-containment, performance-based-navigation]
  version: 0.1.0
  author: Aero Agent Skills
---

# RNP / ANP Containment (avionics/flight-management/rnp-anp-containment)

Use when the task is the navigation performance containment check of a
flight management system: compare the actual navigation performance
(ANP) of the position solution with the required navigation performance
(RNP) of the airspace or route segment and decide whether the aircraft
stays inside the containment bound. ANP is the 95th percentile lateral
position error, taken as two times the supplied 1-sigma lateral
position error or read directly from the navigation system, and a
required margin fraction of RNP can be applied before the comparison.
This leaf implements the standard RNP containment rule in pure Python,
stdlib only. It pairs with gnc-autonomy/navigation/dilution-of-precision
and gnc-autonomy/navigation/gnss-pseudorange-positioning, which produce
the position error inputs, and with lateral-navigation, the FMS lateral
function that consumes the containment verdict.

## Domain quick reference

- RNP is a 95 percent containment bound: the position must stay within
  the RNP distance for at least 95 percent of the flight time. RNP
  values are distances: RNP 0.3 NM equals 0.3 * 1852 = 555.6 m.
- ANP from sigma: anp = 2 * sigma_lateral_m, the 95th percentile
  lateral position error from a 1-sigma lateral position error
  (anp_from_sigma).
- Required margin: margin = rnp_m * margin_fraction, zero by default,
  set by operator or procedure policy (margin_m).
- Containment rule: pass when anp + margin <= rnp, boundary inclusive
  (containment_pass).
- Available margin: margin_available = rnp - margin - anp, the reserve
  left over after the required margin (margin_available_m).
- analyze() bundles the check: it takes sigma_lateral_m or anp_m,
  rnp_m and margin_fraction, and returns the anp_m, rnp_m, pass bool,
  margin_m and the PASS or FAIL verdict.
- The 1-sigma lateral position error is an input from the navigation
  error analysis; deriving it from geometry or ranging residuals is out
  of scope, as are obstacle clearance and route geometry.
- Units are meters for distances and fractions (0.05 means 5 percent)
  for the margin.

## Workflow

1. Fix the segment: read the RNP for the airspace or route segment and
   convert NM to meters (multiply by 1852) when the procedure gives NM.
2. Get the position error input: the 1-sigma lateral position error
   sigma_lateral_m from the navigation error estimate, or the ANP value
   reported by the navigation system.
3. Compute the ANP with anp_from_sigma when only sigma is available, or
   pass the reported ANP directly as anp_m.
4. Set the required margin fraction (default 0.0) and compute the
   margin in meters with margin_m when the operator demands a reserve.
5. Run containment_pass for the verdict and margin_available_m for the
   remaining reserve.
6. For the full record call analyze(sigma_lateral_m=..., anp_m=...,
   rnp_m=..., margin_fraction=...) and use the returned dict with the
   verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_rnp_anp_containment.py.

## Worked example

RNP 0.3 NM = 555.6 m on the approach with a 1-sigma lateral position
error of 120 m.

- ANP: anp_from_sigma(120) = 2 * 120 = 240 m (95 percent bound).
- Default margin: margin_m(555.6, 0.0) = 0 m.
- Verdict: containment_pass(240, 555.6) is True because 240 <= 555.6.
- Available margin: margin_available_m(240, 555.6) = 555.6 - 240 =
  315.6 m.
- Degraded case: sigma 300 m gives ANP 600 m; 600 > 555.6 so
  containment_pass(600, 555.6) is False and analyze returns verdict
  FAIL.
- Direct ANP case: analyze(anp_m=500, rnp_m=555.6,
  margin_fraction=0.05) applies margin_m = 555.6 * 0.05 = 27.78 m,
  checks 500 + 27.78 = 527.78 <= 555.6, passes with verdict PASS and
  27.82 m of margin still available.

## Verification

- Confirm anp_from_sigma(120) returns 240.0 m.
- Confirm containment_pass(240, 555.6) is True and
  containment_pass(600, 555.6) is False.
- Confirm margin_available_m(240, 555.6) returns 315.6 m within 0.1.
- Confirm analyze(anp_m=500, rnp_m=555.6, margin_fraction=0.05)
  returns pass True, margin_m 27.78 and verdict PASS.
- Confirm the boundary is inclusive: containment_pass(240, 240) is True.
- Confirm ValueError rejection of non-physical inputs: both sigma and
  anp missing, rnp_m <= 0, sigma_lateral_m < 0, anp_m < 0 and
  margin_fraction < 0.
- Run the contract test offline: python3
  scripts/test_rnp_anp_containment.py (32 tests, deterministic).

## Related leaves

- avionics/flight-management/lateral-navigation: the FMS lateral
  guidance function that consumes the containment verdict and the
  cross-track state.
- gnc-autonomy/navigation/dilution-of-precision: navigation geometry
  based error analysis that can feed the lateral position error sigma.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: the position
  fix whose residuals bound the navigation error for the sigma input.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rnp_anp_containment.py

The test covers the worked-example contract (ANP 240 m from a 120 m
sigma, pass verdict and 315.6 m available margin at RNP 555.6 m; fail
verdict at a 300 m sigma; direct ANP 500 m pass with the 5 percent
margin), the margin helper, the inclusive boundary, sigma and ANP input
agreement round trip, verdict typing, and ValueError rejection of both
missing inputs, non-positive RNP, negative sigma, negative ANP and
negative margin fraction.

## Compliance

- Standards referenced, not reproduced: DO-178C frames the flight
  management software context for this containment function; the RNP
  containment relations above are standard navigation methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
