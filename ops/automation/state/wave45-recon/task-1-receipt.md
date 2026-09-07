# WAVE-45 FLIGHT-MECHANICS FAMILY PROBE RECEIPT (task-1)

Repo: the local AeroSkills repo, git HEAD 5cc8fef3 (verified `git log --oneline -1` = 5cc8fef3 ops: wave-45 prep kit + runbook, publish-context notes).
Probe date: 2026-09-07. Read-only probe: no skills/, eval/, docs/, Makefile, scripts/, brief, or standards-map.yaml writes. One write only: this receipt.
Doctrine honored: wave-43/44 adjudications stand unless fresh counter-evidence found (none found). RECEIPTS OVER LISTS. NO_CANDIDATES with decline reasons is a correct outcome.

## Verdict: NO_CANDIDATES

Zero GO candidates. flight-mechanics (47 leaves) is saturated at the leaf margins on a FRESH whole-family probe: every suggested performance-mechanics seam (rate-of-climb ceilings, range/payload trades, takeoff/landing distance, turn performance, energy height, specific excess power, rotorcraft hover/climb/ground-effect) has a live owner inside flight-mechanics, flight-test-operations, or vehicle-design, or is standards-map-blocked / anchorless. Consistent with the wave-44 whole-family NO_CANDIDATES receipt.

## Whole-family enumeration (47 leaves, all probed)

`find skills/flight-mechanics -mindepth 3 -name SKILL.md` returned 47 files (quoted in full below), router parity 47 rows confirmed in skills/flight-mechanics/SKILL.md (`grep -c` router rows = 47; packs performance 30, stability-control 11, handling-qualities 4, flight-dynamics-sim 2).

```
flight-dynamics-sim: point-mass-trajectory, six-dof-simulation
handling-qualities: cooper-harper-rating, mil-std-1797a, pilot-induced-oscillation, pitch-bandwidth-criteria
performance (30): balanced-field-length, breguet-endurance, breguet-range, climb-performance,
  descent-performance, energy-height, glide-performance, landing-performance, oei-climb-gradient,
  propeller-range, rotorcraft-autorotative-descent, rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance, rotorcraft-blade-flapping-dynamics,
  rotorcraft-forward-flight-performance, rotorcraft-hover-ground-effect, rotorcraft-hover-performance,
  rotorcraft-lead-lag-dynamics, rotorcraft-main-rotor-sizing, rotorcraft-range-endurance,
  rotorcraft-tail-rotor-sizing, rotorcraft-turn-performance, rotorcraft-vertical-climb-performance,
  specific-range, speed-stability, takeoff-performance, thrust-required, turn-performance,
  wind-effects, windshear-analysis
stability-control (11): aileron-reversal, control-surface-effectiveness, deep-stall-analysis,
  dynamic-stability, lateral-directional-stability, longitudinal-stability, phugoid-mode-analysis,
  short-period-mode-analysis, spin-recovery, stability-derivatives-avl, trim-analysis
```

## Suggested-seam sweep (every example in the wave-45 brief, probed FRESH)

| Seam (brief example) | Owner (leaf + evidence) | Verdict |
|---|---|---|
| rate-of-climb ceilings | climb-performance: service ceiling closed form h = (roc_sl - 0.5) / lapse_rate, linear ROC lapse; absolute ceiling is the same identity at ROC = 0; FTO climb-performance-flight-test measures ceilings | CLOSED |
| range/payload trades | vehicle-design/conceptual/payload-range-diagram (14 payload-range hits) + sizing-mission-profile (reserve-fuel policy, 26 hits); corpus w8 payload-range tasks 2 route there | CLOSED (cross-family owner) |
| takeoff/landing distance | takeoff-performance (all-engine ground roll), balanced-field-length (OEI rotation + 35-ft air segment), landing-performance (50-ft + flare + stopping), FTO takeoff/landing-distance-determination (measured), vehicle-design constraint-analysis / ws-tw-trade (sizing constraint) | CLOSED |
| turn performance | turn-performance (fixed wing, sustained verdict); rotorcraft-turn-performance (rotorcraft banked-turn power) | CLOSED |
| energy height | energy-height (Ps, zoom-climb, corpus eh1/eh2) | CLOSED |
| specific excess power | energy-height (19 hits) + climb-performance (6) + FTO level-acceleration-test | CLOSED |
| rotorcraft hover/climb/ground-effect | rotorcraft-hover-performance, rotorcraft-hover-ground-effect (incl. IGE hover ceiling height), rotorcraft-vertical-climb-performance (max VROC for available power), rotorcraft-forward-flight-performance, FTO rotorcraft-performance-flight-test (measured OGE/IGE hover ceilings) | CLOSED |

## Declines table (all fresh probes; one-line reasons)

| Candidate seam | Reason |
|---|---|
| rotorcraft-height-velocity-diagram | STAY (wave-43): FTO rotorcraft-height-velocity-diagram-test now fills the H-V function incl. failure-height-loss boundary analysis; no fresh counter-evidence |
| rotorcraft-forward-flight-envelope-limits | STAY (wave-43): retreating-blade-stall boundary is semi-empirical, fabricated-table risk without published closed-form anchor; no fresh counter-evidence |
| absolute-ceiling determination | climb-performance owns the service-ceiling closed form under the same linear ROC lapse; absolute ceiling is that identity at ROC = 0, not a distinct seam; FTO climb-performance-flight-test measures ceilings; wave-43 rejected with owners; zero corpus tasks |
| corner-velocity / instantaneous turn | STAY (wave-43): FTO envelope-expansion owns corner speed (corpus task ee1 routes there); V-n diagram owned by structures/loads/gust-maneuver-loads and FTO load-factor-envelope |
| time-to-climb | climb-performance owns it: t = delta_h / ((roc_a + roc_b) / 2); corpus roc2 routes there |
| service-ceiling extension into cruise-ceiling | no published deterministic definition; same ROC-lapse identity as climb-performance; zero corpus tasks |
| fixed-wing all-engine takeoff distance to the 35-ft screen | FTO takeoff-distance-determination already computes ground roll + rotation distance + airborne climb segment to 35 ft (measured); balanced-field-length owns the 35-ft obstacle air segment on the engine-out gradient and its fence assigns the all-engine analysis side to takeoff-performance's ground roll only; vehicle-design constraint-analysis / ws-tw-trade own the analytical takeoff-distance constraint; corpus tkd1/tkd2 route to FTO |
| runway-limited / max-takeoff-weight | vehicle-design (payload-range-diagram MTOW, mass-budget, brake-energy-sizing, fuel-jettison) plus FTO fuel-jettison-flight-test; takeoff-performance reverses its own ground roll with weight |
| drift-down / OEI cruise ceiling | standards-map-blocked: no far-121 or ac-120-42b id in standards-map.yaml (30 ids verified); map-block precedents: MIL-HDBK-217 parts-count, ISO 15530 CMM; the drift-down path to ceiling is an energy integration, not clean closed form; zero corpus tasks |
| balked-landing / go-around gradient analysis | oei-climb-gradient owns the landing-configuration rows: approach climb gear down go-around power (2.1/2.4/2.7 by engine count) and landing climb all engines 3.2%; FTO balked-landing-flight-test stands as the designated measurement reserve (wave-43 plan); zero corpus tasks; tag overlap with landing-climb |
| propeller-endurance | breguet-endurance already carries the propeller branch: prop_endurance with PSFC in kg/(W s) (quoted fence below); propeller-range's Does NOT do list confirms endurance of either propulsion type belongs to breguet-endurance |
| wind-corrected range / still-air-range scaling | thin extension of wind-effects groundspeed bookkeeping over breguet-range/propeller-range/specific-range; no independent closed-form identity; zero corpus tasks; range/wind generic-tag overlap |
| level-flight Vmax/Vmin speed envelope | thrust-required owns the level-flight TR/PR envelope (v_md, v_mp, T_min closed forms) and speed-stability owns level-flight trim-speed classification on the same curve; propeller Vmax root has no clean closed form; zero corpus tasks; generic-tag overlap |
| hover-ceiling (OGE density-altitude root) | FTO rotorcraft-performance-flight-test reduces measured OGE/IGE hover ceilings (corpus w31 task); FM hover-ground-effect computes the IGE hover ceiling height; rotorcraft-vertical-climb-performance re-runs the climb check at any chosen density altitude; engine power lapse needs an empirical exponent (fabricated-correlation risk, rotorcraft-forward-flight-envelope-limits precedent) |
| rotorcraft forward-flight climb Vy / ceilings analysis | FTO rotorcraft-forward-flight-climb-test owns Vy-schedule and ceiling reduction; FM rotorcraft-forward-flight-performance owns the analytic power-required sweep (best endurance/range speeds) and rotorcraft-vertical-climb-performance the VROC for available power; wave-43 H-V precedent on FM analysis vs FTO measured slot |
| translation-lift / ETL onset | empirical onset band, no published closed-form anchor; Glauert momentum inflow in rotorcraft-forward-flight-performance already models the induced-power falloff with speed; zero corpus tasks |
| rotorcraft autorotative glide range / vortex-ring-windmill transition range | wave-31 review declined (Leishman receipts cited in rotorcraft-autorotative-descent context note); rotorcraft-axial-descent-flow-states owns the windmill-brake band |
| rotorcraft Category A OEI takeoff | decision-point envelope procedure, not clean closed form; FTO rotorcraft-category-a-oei-flight-test designated measurement reserve (wave-43 plan) |
| climb fuel / mission fuel segments | vehicle-design sizing-mission-profile owns mission segment fuel fractions and reserve policy; FM climb-performance owns time-to-climb only by family fence |
| fuel-to-climb / block-fuel | vehicle-design owner (sizing-mission-profile, tow-estimation fuel-fraction method, corpus to1) |

## Wave-43 stays confirmed (no fresh counter-evidence found)

rotorcraft-height-velocity-diagram and rotorcraft-forward-flight-envelope-limits stays stand. Both FTO measurement slots are now filled leaves (skills/flight-test-operations/performance/rotorcraft-height-velocity-diagram-test, rotorcraft-forward-flight-climb-test) and no new published closed-form anchor appeared that would rescue the retreated-blade-stall boundary from fabricated-table risk.

## Closed veins list

- Climb/descent/glide family: ROC, gradient, time-to-climb, service ceiling, descent planning, glide ratio/sink rate/best glide all owned (climb-performance, descent-performance, glide-performance); windshear F-factor owned (windshear-analysis).
- Energy family: Ps, energy height, zoom-climb owned (energy-height); level acceleration measured side owned (FTO level-acceleration-test).
- Range/endurance family: jet range (breguet-range), prop range (propeller-range), jet+prop endurance (breguet-endurance incl. prop branch), specific air range (specific-range), rotorcraft hover endurance + cruise range (rotorcraft-range-endurance), payload-range diagram and ferry range (vehicle-design conceptual payload-range-diagram). Vein closed on both propulsion branches.
- Takeoff/landing field length family: stall/liftoff/ground roll (takeoff-performance), balanced field V1 with accelerate-stop/accelerate-go and 35-ft OEI air segment (balanced-field-length), OEI gradients vs FAR-25.121 tables (oei-climb-gradient), landing approach/flare/50-ft/stopping (landing-performance), measured takeoff/landing distance (FTO takeoff-distance-determination, landing-distance-determination), takeoff-distance sizing constraint (vehicle-design constraint-analysis, ws-tw-trade). Vein closed.
- Turn/maneuver family: fixed-wing sustained turn (turn-performance), rotorcraft banked turn power (rotorcraft-turn-performance), corner speed measured (FTO envelope-expansion), V-n (structures gust-maneuver-loads, FTO load-factor-envelope). Vein closed.
- Rotorcraft performance family: hover (momentum + figure of merit, rotorcraft-hover-performance), blade-element hover (rotorcraft-blade-element-hover-performance), IGE hover + IGE ceiling height (rotorcraft-hover-ground-effect), vertical climb VROC (rotorcraft-vertical-climb-performance), forward flight power + best speeds (rotorcraft-forward-flight-performance), turn (rotorcraft-turn-performance), autorotation (rotorcraft-autorotative-descent), axial descent/vortex-ring/windmill (rotorcraft-axial-descent-flow-states), range/endurance (rotorcraft-range-endurance), main/tail rotor sizing (rotorcraft-main-rotor-sizing, rotorcraft-tail-rotor-sizing), lead-lag/ground-resonance-adjacent (rotorcraft-lead-lag-dynamics). Vein closed.
- Speed stability: TR/PR curves, back side, v_md (speed-stability, thrust-required). Vein closed.
- Zero-token seams tree-wide (fresh scan) that still failed the GO bar: cruise-ceiling, drift-down, balked-landing, zero-fuel-weight, translation-lift: each map-blocked, anchorless, cross-family-owned, or thin-extension (reasons above).

## Zero-owner / ownership grep evidence (whole skills/ tree, 623 SKILL.md scanned, case-insensitive)

- `python3 /tmp/fm_tokens.py` (regex concept scan of every skills/**/SKILL.md):
  - drift-down: ZERO files tree-wide (still declined: standards-map-blocked, no far-121/ac-120-42b id; path to ceiling is an energy integration)
  - balked-landing: ZERO files tree-wide (still declined: oei-climb-gradient owns the landing-climb gradient rows; FTO measurement reserve designated)
  - translation-lift: ZERO files tree-wide (declined: no closed-form anchor)
  - cruise-ceiling: ZERO files tree-wide (declined: no deterministic definition)
  - payload-range: 3 files :: vehicle-design/conceptual/payload-range-diagram/SKILL.md(14), vehicle-design/conceptual/sizing-mission-profile/SKILL.md(10), vehicle-design/SKILL.md(8)
  - corner-velocity: 2 files :: flight-test-operations/envelope/envelope-expansion/SKILL.md(8), flight-test-operations/SKILL.md(3)
  - hover-ceiling: 7 files :: flight-test-operations/performance/rotorcraft-performance-flight-test/SKILL.md(9), flight-mechanics/performance/rotorcraft-hover-ground-effect/SKILL.md(3) + router/FTO others
  - service-ceiling: 4 files :: flight-mechanics/performance/climb-performance/SKILL.md(9), flight-test-operations/performance/climb-performance-flight-test/SKILL.md(8), flight-test-operations/performance/rotorcraft-forward-flight-climb-test/SKILL.md(6)
  - takeoff-distance: 15 files :: flight-test-operations/performance/takeoff-distance-determination/SKILL.md(12), vehicle-design/sizing/ws-tw-trade/SKILL.md(10), vehicle-design/conceptual/constraint-analysis/SKILL.md(9), flight-test-operations/performance/engine-failure-takeoff-flight-test/SKILL.md(9)
  - specific-excess-power: 11 files :: flight-mechanics/performance/energy-height/SKILL.md(19), flight-test-operations/performance/level-acceleration-test/SKILL.md(11), flight-mechanics/performance/climb-performance/SKILL.md(6)
- Corpus scan (1238 tasks in eval/hit1-corpus.yaml, query+intent+id tokens): zero tasks for drift-down, balked, go-around, absolute-ceiling, translation-lift, zero-fuel, Vx/Vy analysis, hover-ceiling beyond the two owners; ee1 corner-speed routes to flight-test-operations/envelope/envelope-expansion; tkd1/tkd2 takeoff-distance route to FTO takeoff-distance-determination; roc1/roc2 route to FM climb-performance; eh1/eh2 to energy-height; ocg1/ocg2 to oei-climb-gradient; ben1/ben2 to breguet-endurance; w40 balanced-field tasks to balanced-field-length; w31 ige-hover-ceiling task to rotorcraft-hover-ground-effect; w31 hover-ceiling measured task to FTO rotorcraft-performance-flight-test.

## Sibling fence quotes (nearest owning leaves, verbatim)

- climb-performance: "Service ceiling: the altitude where the rate of climb decays to 0.5 m/s (100 ft/min); h = (roc_sea_level - 0.5) / lapse_rate, assuming a linear ROC lapse with altitude."
- oei-climb-gradient: "Approach climb, gear down, go-around power (25.121(d)): 2.1 for 2 engines, 2.4 for 3 engines, 2.7 for 4 engines. Landing climb, all engines, landing configuration (25.121(e)): 3.2 for every engine count."
- propeller-range: "the endurance leaf (flight-mechanics/performance/breguet-endurance) already carries the propeller branch on the endurance side" and "Does NOT do: ... endurance of either propulsion type (breguet-endurance)".
- breguet-endurance: "E = (1 / sfc) * (L/D) * ln(W0 / W1) ... kg of fuel per watt of shaft power per second for a propeller" and workflow "Compute the endurance with jet_endurance (or prop_endurance for a propeller aircraft)."
- balanced-field-length: "It pairs with takeoff-performance (the all-engine ground roll ... stall speed, lift-off speed, and the all-engine ground roll from wing loading)" and "climb over the 35-ft obstacle on the engine-out climb gradient".
- takeoff-performance: "estimate the ground roll distance with rolling friction. Produces the stall speed, the lift off speed, and the ground roll distance that gate the takeoff field-length check."
- FTO takeoff-distance-determination: "integrate the measured ground speed samples over the ground roll, add the rotation distance at the rotation speed, and close the airborne climb segment to the 35 ft obstacle height with the climb rate."
- energy-height: "derive the specific excess power Ps from thrust, drag, speed, and weight ... convert between kinetic and potential energy in climb and cruise trades with the zoom climb gain".
- turn-performance: "compute sustained turn performance for a fixed-wing aircraft ... check whether the available thrust sustains the turn against the increased drag."
- rotorcraft-hover-ground-effect: "the power margin against an available power, and the maximum rotor height at which the rotorcraft can still hover with that available power."
- FTO rotorcraft-performance-flight-test: "reduce hover power-required points measured across density altitudes to a hover ceiling against the available power ... (the OGE ceiling run against the manual OGE available power, the IGE ceiling against the ground-effect-incremented value)".
- rotorcraft-autorotative-descent: "Context: the wave-31 review declined a momentum-theory autorotation vortex-ring and windmill transition range (Leishman receipts)."
- speed-stability: "Minimum drag speed: v_md = (2 * W / (rho * S))^0.5 * (k / cd0)^0.25" and "classifies each candidate trim speed" on the thrust-required curve.
- thrust-required: "Minimum drag speed: V_md ... Minimum power speed: V_mp ... Maximum lift to drag ratio: (L/D)_max = 1 / (2 sqrt(cd0 k))".

## Standards-map check

30 ids present in standards-map.yaml (verified by grep): arinc-429, arinc-664, arp4754a, arp4761a, as9100, as9102, asme-y14-5, cmh-17, cs-25, do-160, do-178c, do-254, do-330, ecss, far-107, far-25, far-29, far-33, itar-ear, mil-std-1553, mil-std-1797a, mmpsd, msg-3, naca-tn-902, naca-tr-824, nas-410, rtca-do-185, rtca-do-229, rtca-do-260b, sep-2640. No far-121, no ac-120-42b, no iso-15530, no mil-hdbk-217 (drift-down and parts-count style seams stay map-blocked). far-25, far-29, cs-25 exist and are the FM family conventions.

## Note for the wave-45 plan

flight-mechanics contributes 0 leaves this wave. Pool must come from the other smallest-family probes (avionics, SES, propulsion, MQ, FTO) per the smallest-first order in the wave-45 brief. If the viable pool drops below ~12, the brief's extension rule (vehicle-design 55, structures 59) applies; do not re-open flight-mechanics veins adjudicated here.
