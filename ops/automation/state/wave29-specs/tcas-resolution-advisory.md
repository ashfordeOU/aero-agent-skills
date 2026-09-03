# Wave-29 leaf spec: tcas-resolution-advisory (avionics, surveillance pack - NEW PACK)

- Path: skills/avionics/surveillance/tcas-resolution-advisory/
- Pack: surveillance (NEW pack, first leaf; the sibling pack list is
  empty at wave-29 prep)
- Standards ids: rtca-do-185 (reference-only; new id added to
  standards-map.yaml at wave-29 prep). Ledger Standard: rtca-do-185.
- Family: avionics

## Claim

Evaluate a TCAS II traffic alert and collision avoidance resolution
advisory for an own aircraft against a single intruder: select the
sensitivity level from the own altitude, compute the modified tau
closing-time metric with the distance-modified DMOD term, apply the
horizontal threat test and the altitude test, and choose the RA sense
(climb or descend) from the intruder position. Produces the
sensitivity level, the modified tau, the threat verdict, and the
resolution advisory sense that gate a TCAS logic assessment.

Does NOT do: compute DME/VOR/ILS position fixes or navaid geometry
(radio-navigation-aids owns navaid usage); compute RNP/ANP containment
(rnp-anp-containment owns containment bounds); manage flight plans or
lateral navigation legs (flight-planning and lateral-navigation own
the FMS route functions); handle airborne surveillance data buses
(arinc-429 and arinc-664 data-bus leaves own the datalink transport);
compute radar/transponder RF behavior (do-160 RF leaves own
electromagnetic qualification). This leaf runs the TCAS II threat and
RA logic on already-measured range, range rate, and altitude state.

## Model (implement exactly)

Module constants (TCAS II sensitivity level table, paraphrased from
DO-185B; values in seconds, nautical miles, and feet):
- SENSITIVITY_TABLE = {
    2: {"tau": 20.0, "dmod": 0.30, "alim": 300.0},
    3: {"tau": 25.0, "dmod": 0.33, "alim": 300.0},
    4: {"tau": 30.0, "dmod": 0.48, "alim": 300.0},
    5: {"tau": 40.0, "dmod": 0.75, "alim": 350.0},
    6: {"tau": 45.0, "dmod": 1.00, "alim": 400.0},
    7: {"tau": 48.0, "dmod": 1.10, "alim": 600.0}}
- ALTITUDE_BANDS = [(0, 1000, 2), (1000, 2350, 3), (2350, 5000, 4),
  (5000, 10000, 5), (10000, 20000, 6), (20000, inf, 7)] (band lower,
  band upper, sensitivity level; upper bound exclusive except inf).

Functions (pure stdlib, floats):
- sensitivity_level(own_altitude_ft) -> int: first band where
  own_altitude_ft < upper (lower inclusive, upper exclusive).
  ValueError on negative altitude.
- modified_tau(range_nmi, range_rate_nmi_s, dmod_nmi) -> float:
  tau_mod = -(range_nmi^2 - dmod_nmi^2) / (range_nmi *
  range_rate_nmi_s). Valid for closing encounters (range_rate < 0);
  returns 0.0 when range_nmi <= dmod_nmi (range already inside the
  DMOD cylinder, immediate threat). ValueError on range_nmi <= 0,
  dmod_nmi <= 0, or range_rate >= 0 (not closing; callers gate first).
- threat_verdict(range_nmi, range_rate_nmi_s, own_altitude_ft,
  intruder_altitude_ft) -> dict:
  sl = sensitivity_level(own_altitude_ft); tau_t =
  SENSITIVITY_TABLE[sl]["tau"]; dmod = ...["dmod"]; alim =
  ...["alim"].
  if range_rate_nmi_s >= 0: return {sensitivity_level: sl,
  tau_threshold: tau_t, dmod: dmod, alim: alim, modified_tau: None,
  threat: False, reason: "not-closing"}.
  tau_mod = modified_tau(range_nmi, range_rate_nmi_s, dmod);
  dh = intruder_altitude_ft - own_altitude_ft;
  horizontal_ok = tau_mod <= tau_t; vertical_ok = abs(dh) <= alim;
  if horizontal_ok and vertical_ok: sense = "descend" if dh > 0 else
  "climb"; return {..., modified_tau: tau_mod, threat: True,
  vertical_separation_ft: dh, sense: sense}.
  else: return {..., modified_tau: tau_mod, threat: False,
  reason: "tau-exceeded" if not horizontal_ok else "altitude-exceeded",
  vertical_separation_ft: dh}.
- ra_sense(intruder_altitude_ft, own_altitude_ft) -> str:
  "descend" if intruder_altitude_ft > own_altitude_ft else "climb"
  (ties resolve to climb; the RA moves own away from the intruder).
- evaluate_encounter(range_nmi, range_rate_nmi_s, own_altitude_ft,
  intruder_altitude_ft) -> dict: full chain returning
  {sensitivity_level, modified_tau, threat, reason or sense,
  resolution_advisory: "climb" | "descend" | "none",
  parameters: {tau, dmod, alim}}. ValueErrors propagate.

## Worked example

Own aircraft at 8000 ft (sensitivity level 5), closing at 300 kt
(range rate -0.08333 nmi/s).
Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- sensitivity_level(8000) = 5; sensitivity_level(500) = 2;
  sensitivity_level(30000) = 7.
- Case 1: range 3.0 nmi, intruder at 8200 ft (above by 200 ft):
  tau_mod = -(9 - 0.5625) / (3 * -0.08333) = 33.75 s (within 0.01)
  <= tau 40 and |dh| 200 <= ALIM 350: threat True, sense "descend",
  resolution_advisory "descend".
- Case 2: range 8.0 nmi, intruder at 8200 ft:
  tau_mod = 95.16 s (within 0.01) > 40: threat False,
  reason "tau-exceeded", resolution_advisory "none".
- Case 3: range 2.0 nmi, intruder at 7800 ft (below by 200 ft):
  tau_mod = 20.63 s (within 0.01) <= 40: threat True, sense "climb".
- Case 4 (high altitude): own 30000 ft (SL 7), range 5.0 nmi closing
  180 kt (range rate -0.05 nmi/s), intruder 500 ft below:
  tau_mod = 95.16 s (within 0.01) > tau 48: threat False despite
  |dh| 500 <= ALIM 600, reason "tau-exceeded" (the tau gate protects
  at long range).
- Case 5: own 5000 ft, range 1.0 nmi closing 300 kt, intruder 100 ft
  above: range inside DMOD influence, tau_mod = 5.25 s (within 0.01),
  threat True, sense "descend".
- ValueErrors: negative altitude, range <= 0, range_rate >= 0 passed
  directly to modified_tau.

Keep at least 18 test methods: sensitivity level band edges (999,
1000, 2349, 2350, 4999, 5000, 9999, 10000, 19999, 20000), the five
worked cases above, not-closing gate, tau-exceeded vs
altitude-exceeded reasons, sense selection both directions, ties to
climb, ValueErrors. Runs offline in under 20 s.

## Corpus tasks (ids w29-tcas-resolution-advisory-1/2)

Distinctive tokens: TCAS II, traffic alert and collision avoidance,
resolution advisory, modified tau, DMOD, sensitivity level, intruder
threat logic, climb descend advisory. Avoid: navaid, VOR, DME, ILS
fix (radio-navigation-aids); RNP, ANP, containment bound
(rnp-anp-containment); flight plan legs, lateral navigation route
(lateral-navigation); ARINC 429 message words (arinc-429-protocol).

1. "evaluate a TCAS II resolution advisory at 8000 ft with an intruder
   at 3 nmi closing at 300 kt and 200 ft above: modified tau, threat
   verdict, and climb or descend sense"
2. "which TCAS sensitivity level applies at 30000 ft and does a 5 nmi
   closing intruder trigger a resolution advisory under the DMOD and
   tau thresholds?"

## SKILL body notes

Pair with rnp-anp-containment (separation assurance in the FMS),
lateral-navigation (route guidance the RA overrides), radio-navigation-
aids (other surveillance/sensors). New pack avionics/surveillance:
this first leaf frames airborne surveillance logic; future siblings
may add ADS-B or transponder functions. State the boundary: this leaf
is the threat and sense logic, not the transponder waveform, not the
FMS route, and the MOPS parameters are paraphrased values, never
reproduced tables (gated: true in standards-map.yaml). Mirror the
avionics pack SKILL body style (SI units plus flight units where the
standard uses them: nmi, ft, kt; stdlib only, deterministic offline).
