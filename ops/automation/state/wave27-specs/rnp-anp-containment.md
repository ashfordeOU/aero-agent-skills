# Wave-27 leaf spec: rnp-anp-containment (avionics, flight-management pack)

- Path: skills/avionics/flight-management/rnp-anp-containment/
- Pack: flight-management (existing siblings: flight-planning,
  lateral-navigation, vertical-navigation, performance-computation,
  radio-navigation-aids)
- Standards ids: do-178c  (Ledger Standard: do-178c)
- Family: avionics

## Claim

Check navigation performance containment against a required
navigation performance (RNP) value: compute the actual navigation
performance (ANP) as the 95th-percentile lateral position error from
a supplied 1-sigma position error or from an ANP input, compare it
with the RNP for the airspace/route segment, apply the containment
factor (typically 2 sigma for RNP) and a required margin, and produce
the pass or fail verdict with the margin. Produces the ANP, the RNP
comparison, the containment verdict, and the margin that gate
performance-based navigation dispatch.

Does NOT do: compute the dilution-of-precision geometry matrix or the
GDOP/PDOP values from satellite line-of-sight geometry
(gnc-autonomy navigation dilution-of-precision); estimate the 1-sigma
position error from a UERE budget (dilution-of-precision); or solve
the position fix from pseudoranges (gnss-pseudorange-positioning).
This leaf consumes a position-error sigma (or an ANP) and applies the
RNP containment rule only.

## Model (implement exactly)

Module constants:
- CONTAINMENT_SIGMA = 2.0 (RNP is a 95% containment bound; ANP is
  computed as 2 * sigma),
- DEFAULT_MARGIN_FRACTION = 0.0 (no required margin by default; an
  optional margin can be passed as a fraction of RNP).

Inputs:
- sigma_lateral_m (float, 1-sigma lateral position error, required
  unless anp_m is provided),
- anp_m (float or None, directly supplied ANP; when None it is
  computed as CONTAINMENT_SIGMA * sigma_lateral_m),
- rnp_m (float, required navigation performance for the segment),
- margin_fraction (float, default 0.0).

Functions:
- anp_from_sigma(sigma_lateral_m) -> float: 2 * sigma.
- margin_m(rnp_m, margin_fraction) -> float: rnp * margin_fraction.
- containment_pass(anp_m, rnp_m, margin_fraction) -> bool: anp +
  margin <= rnp.
- margin_available_m(anp_m, rnp_m, margin_fraction) -> float:
  rnp - margin - anp.
- analyze(sigma_lateral_m=None, anp_m=None, rnp_m=..., margin_fraction
  =0.0) -> dict {anp_m, rnp_m, pass (bool), margin_m, verdict (str)}:
  ValueError when both sigma and anp are None, or rnp <= 0, or sigma
  < 0, or margin_fraction < 0.

## Worked example

RNP 0.3 NM = 555.6 m, sigma_lateral 120 m.
- ANP = 2*120 = 240 m (assert),
- margin = 0, pass when 240 <= 555.6 -> pass True (assert),
- margin_available = 315.6 m (assert within 0.1).
RNP 0.3 NM, sigma 300 m: ANP 600 m > 555.6 -> pass False (assert).
Direct ANP case: anp_m 500, rnp 555.6, margin 0.05 (27.8 m): 500+27.8
= 527.8 <= 555.6 -> pass True (assert).
ValueErrors: both inputs None, rnp 0, sigma -1.
Keep at least 15 test methods.

## Corpus tasks (ids w27-rnp-anp-containment-1/2)

Distinctive tokens: required navigation performance, actual navigation
performance, RNP containment, ANP comparison, lateral position error
sigma, 95 percent containment, performance based navigation. Avoid:
gdop pdop satellite geometry elevation mask (dilution-of-precision);
pseudorange least squares fix (gnss-pseudorange-positioning).

1. "check the RNP 0.3 containment for the approach: 120 m 1 sigma
   lateral position error, compute the ANP at 95 percent and the
   margin against the required navigation performance"
2. "verify the performance based navigation segment: is the 600 m ANP
   within the 555.6 m RNP with the 5 percent margin, and what is the
   available margin"

## SKILL body notes

Pair with dilution-of-precision and gnss-pseudorange-positioning
(position error sources) and lateral-navigation (the FMS lateral
function that uses the containment verdict). The 2-sigma ANP model is
the standard RNP containment rule; obstacle clearance and route
geometry are out of scope. DO-178C referenced (FMS software context)
not reproduced.
