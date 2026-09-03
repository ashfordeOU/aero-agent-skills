# Wave-30 leaf spec: ads-b-surveillance (avionics, surveillance pack)

- Path: skills/avionics/surveillance/ads-b-surveillance/
- Pack: surveillance (sibling: tcas-resolution-advisory only; this is the
  second leaf in the pack, opened at wave-29).
- Standards ids: rtca-do-260b (reference-only; NEW id added to standards-map
  at wave-30 prep). Ledger Standard: rtca-do-260b.
- Family: avionics

## Claim

Assess an ADS-B Out installation and ADS-B In reception geometry against the
DO-260B-style performance categories: map the navigation integrity category
(NIC) to its containment radius, map the navigation accuracy category for
position (NACp) to its 95-percent accuracy bound, map the source integrity
level (SIL) to its per-flight-hour probability bound, select the NIC and NACp
category whose bound covers a required containment or accuracy value, and
compute the 1090 MHz extended squitter radio line-of-sight range between two
altitudes. Produces the containment radius, accuracy bound, integrity
probability, chosen categories, and coverage range that gate an ADS-B
surveillance assessment.

Does NOT do: evaluate TCAS II resolution advisories or threat detection
(tcas-resolution-advisory owns sensitivity levels, modified tau, DMOD);
compute GNSS position fixes, DOP, or RAIM (gnc-autonomy navigation leaves own
those); design the transponder hardware or encode 1090ES message bit fields
(out of scope; message formats are only referenced by name); model radar or
multilateration surveillance. Category bounds are the published DO-260B-style
values used in equipage assessments, stated as a paraphrase table, never as
reproduced MOPS tables.

## Model (implement exactly)

Module constants (published DO-260B-style category bounds; treat as data):
- NIC_RADIUS_M = {11: 7.5, 10: 25.0, 9: 75.0, 8: 185.2, 7: 370.4, 6: 1111.2,
  5: 1852.0, 4: 3704.0, 3: 7408.0, 2: 14816.0, 1: 37040.0, 0: None}
  (containment radius in m; 0 = unknown).
- NACp_95_M = {11: 3.0, 10: 10.0, 9: 30.0, 8: 92.6, 7: 185.2, 6: 370.4,
  5: 926.0, 4: 1852.0, 3: 3704.0, 2: 7408.0, 1: 18520.0, 0: None}
  (95-percent horizontal accuracy bound in m).
- SIL_PROB = {3: 1e-7, 2: 1e-5, 1: 1e-3, 0: None}
  (maximum integrity probability per flight hour; 0 = unknown).
- RANGE_COEFF = 4.12 (km per sqrt(m), standard-atmosphere radio horizon).
- FT_TO_M = 0.3048.

Functions (pure stdlib):
- nic_containment_radius(nic) -> float or None (dictionary lookup; valid ints
  0-11). ValueError if nic outside 0-11.
- nacp_accuracy(nacp) -> float or None. ValueError if nacp outside 0-11.
- sil_probability(sil) -> float or None. ValueError if sil outside 0-3.
- nic_for_radius(required_radius_m) -> int: the SMALLEST NIC whose
  containment radius is >= required radius (choose the least-integrity
  category that still bounds the requirement; iterate categories 0-11,
  skipping None; if even NIC 1 is too small return 0). ValueError if
  required_radius_m <= 0.
- nacp_for_accuracy(required_95_m) -> int: same rule over NACp.
- adsb_range_km(alt_ft_own, alt_ft_other=0.0) -> float:
  d = RANGE_COEFF * (sqrt(alt_own * FT_TO_M) + sqrt(alt_other * FT_TO_M)).
  ValueError if either altitude < 0.
- adsb_assessment(nic, nacp, sil, alt_ft_own, alt_ft_other=0.0) -> dict:
  {containment_radius_m, accuracy_95_m, integrity_prob, range_km}. ValueErrors
  propagate.

## Worked example

Own ship at 10 000 ft, ADS-B In receiver of a target at 30 000 ft; NIC 8,
NACp 9, SIL 2.

Deterministic anchors (EXACT values from the tables; assert equal within 1e-9
relative):
- nic_containment_radius(8) == 185.2 m; nacp_accuracy(9) == 30.0 m;
  sil_probability(2) == 1e-5.
- nic_for_radius(100.0) == 9 (75 m is too small, 185.2 covers); NIC 9.
- nacp_for_accuracy(50.0) == 8 (30 m too small, 92.6 covers); NACp 8.
- adsb_range_km(10000, 30000): sqrt(3048) = 55.21, sqrt(9144) = 95.62,
  sum 150.83 * 4.12 = 621.4 km (bound 600-650 km; assert module value).
- adsb_range_km(0, 0) == 0.0.
- SIL 3 < SIL 2 probability (1e-7 < 1e-5).
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: nic outside 0-11, nacp outside 0-11, sil outside 0-3,
  negative altitude, required radius <= 0.
- nic_for_radius(7.5) == 11; nic_for_radius(1e6) == 0 (no category covers).
- Table spot checks above.
- Determinism.

## Corpus fragment (eval/hit1-wave30-ads-b-surveillance.yaml)

Forbidden tokens (siblings/other leaves): tcas, resolution-advisory, tau,
dmod, sensitivity-level, intruder (tcas-resolution-advisory); pseudorange,
dop, raim, protection-level (gnc leaves); transponder-mode-s, radar.
Distinctive tokens ONLY: ads-b, ads-b-out, ads-b-in, extended-squitter,
nic, nacp, sil, containment-radius.

Query 1: "Check an ADS-B Out equipage: what containment-radius does NIC 8 give
and which NIC covers a 100 m required containment radius" (id
w30-ads-b-surveillance-1).
Query 2: "Estimate 1090 extended-squitter ADS-B In range between 10000 ft and
30000 ft and look up NACp accuracy for category 9" (id w30-ads-b-surveillance-2).
intent: "avionics; ADS-B surveillance category and coverage assessment".

## Description/tag guidance

Description opens "Use when you must assess an ADS-B Out installation and
ADS-B In reception geometry against the DO-260B-style performance
categories:" and lists the outputs in the Claim. First tag: ads-b-surveillance.
Additional tags: extended-squitter, containment-radius, nacp-accuracy,
sil-integrity, ads-b-range. No generic single words. 50-150 words, <=1000
chars, no em dash, no "classified".
