# WAVE-48 FLIGHT-MECHANICS PROBE RECEIPT (task-0, whole-family FRESH)

- Repo: the local AeroSkills repo. HEAD verified `git log --oneline -1` =
  92d84a48 ("ops: stage wave-48 brief (planning only — daylight dispatch
  10:00 CEST)"). Working tree clean before and after (only this receipt
  untracked). Family state matches the wave-47 close baseline (645 leaves,
  1306 corpus tasks, 30 standards) plus the wave-47 landing the brief names.
- Scope: ENTIRE flight-mechanics family, 49 leaves (2 flight-dynamics-sim +
  4 handling-qualities + 32 performance + 11 stability-control), probed
  FRESH with the wave-48 focus on rotorcraft + performance seams. Read-only
  probe: no writes to skills/, eval/, standards-map.yaml, scripts/,
  Makefile, or any ops/automation brief. One write only: this receipt
  (ops/automation/state/wave48-recon/).
- Corpus baseline: eval/hit1-corpus.yaml = 1306 task blocks (regex parser
  recovered 1306/1306: id, query, intent, expected_skill); 98 tasks target
  the 49 flight-mechanics leaves, exactly 2 per leaf including the wave-47
  leaf (w47-rotorcraft-cyclic-pitch-trim-1/-2). Standards map: 30 ids
  (grep '^  - id:' = 30); far-25 line 16, cs-25 line 27, far-29 line 270.
- Doctrine: the wave-47 ranked GO (rotorcraft-cyclic-pitch-trim, the
  control-channel completion of the wave-46 flapping equilibrium) is now a
  LANDED leaf and its blade-pitch/control token space is owned. Every
  wave-43/45/46/47 decline was re-probed FRESH this wave with fresh greps
  over skills/ + eval/ (battery below). The wave-48 brief's named rotorcraft
  veins (autorotation, ground-effect hover, blade-element theory) all have
  live owners; the un-owned remainders of each vein fail the deterministic-
  anchor or FTO-measured gates on fresh evidence.

## Verdict

**NO_CANDIDATES.** Flight-mechanics at 49 is saturated at its leaf margins.
The wave-47 receipt's closing claim ("this one control-channel seam is the
family's remaining yielding point") is confirmed: that seam landed, and the
whole-family FRESH probe this wave found no remaining seam with a clean
deterministic closed-form identity that no sibling owns, a published anchor,
and an un-owned router/corpus surface. Two marginal seams were probed to
the anchor gate (rotorcraft vertical climb in ground effect; rotor blade
twist in hover) and decline with concrete fresh evidence + reopen triggers
below. All 24 wave-47 decline rows re-verified FRESH with zero counter-
evidence; the fixed-wing and rotorcraft performance veins re-confirm
saturated. No wave-46/47 decline was overturned.

## Whole-family enumeration (49 leaves, all probed)

`find skills/flight-mechanics -mindepth 3 -name SKILL.md` = 49 files; router
parity 49 rows confirmed in skills/flight-mechanics/SKILL.md.

```
flight-dynamics-sim (2): point-mass-trajectory, six-dof-simulation
handling-qualities (4): cooper-harper-rating, mil-std-1797a,
  pilot-induced-oscillation, pitch-bandwidth-criteria
performance (32): balanced-field-length, breguet-endurance, breguet-range,
  climb-performance, descent-performance, energy-height, glide-performance,
  landing-performance, oei-climb-gradient, propeller-range,
  rotorcraft-autorotative-descent, rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance, rotorcraft-blade-flapping-dynamics,
  rotorcraft-cyclic-pitch-trim (wave-47), rotorcraft-forward-flight-flapping (wave-46),
  rotorcraft-forward-flight-performance, rotorcraft-hover-ground-effect,
  rotorcraft-hover-performance, rotorcraft-lead-lag-dynamics,
  rotorcraft-main-rotor-sizing, rotorcraft-range-endurance,
  rotorcraft-tail-rotor-sizing, rotorcraft-turn-performance,
  rotorcraft-vertical-climb-performance, specific-range, speed-stability,
  takeoff-performance, thrust-required, turn-performance, wind-effects,
  windshear-analysis
stability-control (11): aileron-reversal, control-surface-effectiveness,
  deep-stall-analysis, dynamic-stability, lateral-directional-stability,
  longitudinal-stability, phugoid-mode-analysis, short-period-mode-analysis,
  spin-recovery, stability-derivatives-avl, trim-analysis
```

Wave-48 focus seams, leaf status at probe time: autorotation ->
rotorcraft-autorotative-descent (steady glide, min descent rate) + axial-
descent-flow-states (windmill-brake momentum root) + FTO measured slots;
ground-effect hover -> rotorcraft-hover-ground-effect (Cheeseman IGE);
blade-element theory -> rotorcraft-blade-element-hover-performance (hover
BEMT, Betz tip loss). Control-channel blade dynamics -> the wave-47 leaf.

## Declines table (all probed FRESH this wave)

Gates: a = zero-owner (skills/ + eval/, rg exit-1 or 0-hit scans), b =
sibling-fence clean, c = standards-map id, d = published deterministic
anchor, e = Hit@1 wordability, f = tag hygiene. Demand = corpus task signal.

| Candidate seam | Gate result + fresh evidence |
|---|---|
| rotorcraft vertical climb in ground effect (IGE climb power / IGE ceiling at climb rate) | a PASS (no leaf computes it), b AMBIGUOUS-deferral, d FAIL, demand ZERO. Both siblings fence it out with deferrals: rotorcraft-hover-ground-effect "No recirculation, no partial ground contact, no vertical climb and no forward flight: those belong to sibling leaves."; rotorcraft-vertical-climb-performance "Axial momentum theory only: uniform inflow, no ground effect, vertical climb only with climb rates zero or positive". But no canonical published closed form combines the Cheeseman-style hover GE correction with the axial-climb momentum closure: GE induced-power at climb rate is wake-distortion territory (empirical/test-derived), the same anchor failure class as wave-47 nonuniform-inflow. FTO rotorcraft-performance-flight-test line 221 references the analytic IGE power model only behind the measured IGE ceiling reduction. No corpus task (skills "ige climb"/"ground effect climb" = the two fence lines above only; corpus 0 hits excluding changelog). Reopen trigger: a published deterministic IGE-climb formula set with magnitudes. |
| rotor blade twist in hover (BEMT with linear twist; ideal hyperbolic twist for uniform inflow) | a PASS (rotor twist zero tree-wide: the only skills hit for twist is aerodynamics/wing-design/wing-planform-design fixed-wing washout; corpus "ideal twist" task is structures torsion of an I-section, no theft), b FAIL-as-extension, e FAIL-marginal, demand ZERO. The identity family is the BEMT sibling's own recorded specialization boundary: rotorcraft-blade-element-hover-performance lines 73-75 "Modelled twist is zero (untwisted, constant-chord blade integral); the assumption is recorded here because the spec formula integrates theta0 as constant along the blade." A twist leaf generalizes that same pitch-schedule integral (theta0 -> theta0 + theta_tw*r) — at theta_tw = 0 it degenerates to the sibling's own closed forms, giving no independent in-repo cross-check identity, and its body would be thinner than the wave-47-transient-response precedent the family already declined on thinness. The ideal-twist optimum (hyperbolic theta ~ 1/r for uniform inflow, Leishman Principles of Helicopter Aerodynamics fig 3.8; confirmed citable) is a rotor DESIGN identity — the tree analogue is the fixed-wing washout owned by aerodynamics wing-planform-design, and main-rotor-sizing's design point is the untwisted rectangular blade — not a performance-analysis identity; the anchor literature is rotor-optimization/flight-test (e.g. JUVS 2017; NASA AIAA 2020 ideally-twisted-rotor hover tests), not an analysis closed form. Reopen trigger: corpus demand, or spec-phase folding of a theta_tw parameter into the BEMT sibling instead of a new leaf. |
| autorotative entry / power-off rotor-RPM decay transient | a PASS (0 skills + 0 corpus for rpm-decay/entry tokens), d FAIL, b FAIL (measured slot). Entry rotor-RPM decay is a transient dynamics identity, not closed form (wave-47 flapping-transient-response precedent: no chapter-continuous equilibrium derivation, unhosted transient dynamics). FTO measured owner live: rotorcraft-autorotation-flight-test description covers "the rotor-RPM checks across the entry decay, steady descent and flare recovery against the declared floor" (verbatim) — measured-slot doctrine. Demand ZERO (corpus rpm token = the FTO task only). |
| autorotative flare (analytic rotor-kinetic-energy flare) | a PASS for FM (autorot-flare tokens: only FTO leaves; FM corpus 0), d FAIL, b FAIL (wave-43 H-V closure + measured slot). rotorcraft-autorotative-descent fence: "the descent rate that the airframe reaches in a steady autorotative glide, before any flare" — but the flare itself is the wave-43-declined height-velocity ANALYSIS surface: FTO rotorcraft-height-velocity-diagram-test owns "the height loss and time to establish autorotation and complete the flare... interpolate the dead-man-curve boundary height where height loss plus recovery altitude equals the starting height" (verbatim), and rotorcraft-autorotation-flight-test owns the measured flare-altitude-loss verdict. Rotor-KE flare trades rotor inertia/rpm/height-loss with no canonical magnitude set. Demand ZERO. |
| rotorcraft forward-flight ground effect (IGE power reduction at advance ratio) | a PASS, d FAIL, demand ZERO. The GE power reduction at speed is empirical/test-derived (OGE->IGE transition with speed), no canonical closed form; rotorcraft-hover-ground-effect applies the Cheeseman correction "to the induced power only" for hover (its own fence), and explicitly excludes forward flight. No corpus task. |
| blade-element theory in climb / forward flight (BEMT with climb inflow; azimuthal BEMT with reverse flow) | a PASS, d FAIL, b FAIL. Climb BEMT mixes the pitch-schedule closure with the climb momentum closure the vertical-climb leaf already owns; forward-flight BEMT needs azimuthal integration over the reverse-flow region — not closed form. rotorcraft-forward-flight-performance fence: "Uniform inflow only: no reverse-flow region, no blade-element section polars, no compressibility." Demand ZERO. |
| fixed-wing ground-effect takeoff/landing distance application | a FAIL (cross-family owner): aerodynamics/ground-effects/ground-effect owns the sigma ground-effect induced-drag identity (its description: fixed-wing wing-in-ground-effect configuration); an FM distance application needs a height-varying sigma integration (numeric, not closed form) and collides on ground-effect/induced-drag-reduction tokens; FM takeoff/landing leaves own distances with GE excluded by fence. Demand ZERO. |

## Wave-43/45/46/47 STAY rows re-verified FRESH (fresh greps this wave, zero counter-evidence)

| Candidate seam (prior wave) | Fresh evidence this wave |
|---|---|
| rotorcraft-flapping-nonuniform-inflow | 0 skills + 0 corpus for nonuniform-inflow / inflow-gradient / inflow-distribution tokens; anchor failure stands (NASA TP: linear-gradient models underpredict lateral flapping below mu~0.2) |
| rotorcraft-flapping-in-maneuvers | 0 skills + 0 corpus for maneuver/body-rate flapping tokens; research/aeroelastic level only |
| rotorcraft-lag-dynamics-forward-flight | 0 skills + 0 corpus for forward-flight lag tokens; periodic-coefficient aeroelastic response, not closed form |
| rotorcraft-flapping-transient-response | 0 skills + 0 corpus for flap-transient / rotor-time-constant tokens; no chapter-continuous anchor; thinness precedent |
| fixed-wing level-flight Vmax/Vmin | No FM Vmax leaf anywhere: the only skills hits are aerodynamics/wind-tunnel/wind-tunnel-model-design q = 0.5 rho Vmax^2 (dynamic pressure, not flight envelope); thrust-required owns the TR/PR level-flight envelope (v_md/v_mp/T_min), vehicle-design owns thrust-lapse tokens, FTO owns measured maximum-speed slots; corpus 0 |
| cruise-climb / optimum-cruise-altitude | avionics/flight-management/performance-computation owns step-climb logic + cost-index + ECON cruise (11 files hit; corpus tasks route to it); vehicle-design sizing-mission-profile owns mission fuel segments; corpus demand owned elsewhere |
| analytic stick-force-per-g | control-surface-effectiveness (FM) owns stick-force magnitude at the FAR 25.143 gate; vehicle-design control-surface-sizing and FTO measured slots own force-per-g tokens; corpus tasks route to existing owners |
| max specific-range / optimum cruise speed | avionics performance-computation owns cost-index / ECON speed (20 files hit, live tags cost-index, econ-cruise-speed); FTO cruise-performance-flight-test owns maximum-range/long-range cruise Mach measured; corpus routes there |
| best-climb-speed Vx/Vy | FTO climb-performance-flight-test / rotorcraft-forward-flight-climb-test own the measured best-rate slots (Vy-schedule, ceilings); FM climb-performance owns ROC/gradient/ceiling closed forms; no FM analytic Vx/Vy identity; corpus routes to FTO |
| hydroplaning / wet-runway stopping | Only FM hit is landing-performance line 64 wet-runway footnote ("wet-runway a..." braking factor); single semi-empirical NASA formula V_p = 9 sqrt(psi); no independent closed-form identity; FTO landing-distance-determination measured |
| rotorcraft power-limited max level speed Vmax | High-speed available-power intersection needs a numeric root; engine power lapse empirical; retreating-blade-stall side semi-empirical (wave-43 envelope-limits closure); rotorcraft-turn-performance "power-limited" hits are its bank-angle gate, not a speed leaf; FTO rotorcraft-forward-flight-performance-test measured; corpus 0 for FM |
| rotorcraft-height-velocity-diagram | FTO rotorcraft-height-velocity-diagram-test live leaf (29 file hits incl. FM phugoid height-velocity-exchange false positive); wave-43 ANALYSIS-vs-FTO closure stands; corpus tasks route to FTO |
| rotorcraft-forward-flight-envelope-limits | retreating-blade-stall / envelope-limit tokens: zero rotorcraft hits (hits are avionics envelope-limit Mach + FTO flight-test-safety); wave-43 closure stands (fabricated-table risk without a published closed-form anchor) |
| hover ceiling OGE density-altitude root | rotorcraft-hover-ground-effect owns the IGE ceiling height; FTO rotorcraft-performance-flight-test reduces measured OGE/IGE ceilings; rotorcraft-vertical-climb-performance re-runs climb checks at any density altitude |
| rotorcraft forward-flight climb Vy / ceilings | FTO rotorcraft-forward-flight-climb-test live leaf owns Vy-schedule and ceiling reduction; rotorcraft-forward-flight-performance owns the level-flight power sweep; vertical-climb owns VROC |
| drift-down / OEI en-route ceiling | 0 skills + 0 corpus for drift-down tokens; standards-map-blocked (no far-121 / ac-120-42b among the 30 ids); energy integration, not closed form |
| balked-landing / go-around gradient | oei-climb-gradient owns the 25.121(d) approach-climb/go-around rows; FTO vmcl-determination measured; windshear-analysis only cites go-around excess-thrust ratio as context; corpus routes to FTO/FM owners |
| autorotative forward-flight glide range | rotorcraft-autorotative-descent owns the steady autorotative glide; the only "autorotative band" skills hit outside it is fixed-wing spin-recovery (stalled-wing autorotation, different identity); STAY wave-31/45/46 |
| rotorcraft Category A OEI takeoff | No Category-A-OEI leaf anywhere in skills/ (FTO grep: only noise-certification and cruise-performance false positives) — the wave-43 "FTO designated reserve" slot is still unfilled, not a live owner; FM-analytic side is a decision-point envelope procedure, not closed form; corpus 0 |
| translation-lift / ETL onset | 0 skills + 0 corpus for translation-lift / ETL / edgewise tokens; empirical onset band; Glauert induced-power falloff already inside rotorcraft-forward-flight-performance |
| absolute/cruise ceiling, time-to-climb, climb fuel/distance | climb-performance owns ROC-lapse ceilings (service ceiling at 0.5 m/s ROC), time-to-climb; mission fuel segments route to vehicle-design sizing-mission-profile |
| corner velocity / instantaneous turn | FTO envelope-expansion owns corner speed VA = VS sqrt(n_max) (live leaf, tags corner-speed); V-n owned by structures loads + FTO load-factor-envelope |
| rotorcraft tail-rotor yaw trim in forward flight / vertical-fin offload | 0 skills + 0 corpus for fin-offload / vertical-fin tokens; semi-empirical fin/tail-rotor interference; rotorcraft-tail-rotor-sizing owns the anti-torque thrust/power identities |
| wind-corrected range / still-air-range scaling | breguet-range and propeller-range own the still-air cruise equations; wind-effects owns wind corrections; thin extension with no independent identity; corpus 0 |
| rotor speed governing / rpm droop | 0 rotorcraft hits (only FIR-filter "droop" and midcourse-guidance false positives); engine/RPM governing is propulsion-adjacent, unhosted in FM; not a performance closed form |

## Marginal-seam ledger (probed, not promoted)

- rotorcraft-ige-climb and rotor-blade-twist are the ONLY seams this wave
  that reached a two-sided evidence review (zero-owner + explicit sibling
  deferral for the first; zero-owner + canonical published law for the
  second). Both decline above: IGE-climb on the anchor gate (no canonical
  published closed form; FTO measured ceilings), blade-twist on the
  extension/thinness gate (the BEMT sibling's own specialization boundary)
  plus rotor-design flavor and zero demand. Reopen triggers recorded
  inline. Everything else fails earlier (owner present, measured slot, or
  no anchor).

## Closed veins list (fresh confirmations this wave)

- Rotorcraft vertical-flight group: hover momentum (hover-performance),
  hover BEMT pitch-to-coefficients with Betz tip loss (blade-element-hover),
  IGE hover/ceiling (hover-ground-effect), vertical climb (vertical-climb),
  axial descent flow states + windmill-brake zero-shaft-power momentum root
  (axial-descent-flow-states), steady autorotative glide + empirical min
  descent rate (autorotative-descent). Un-owned remainders (IGE climb,
  twist, climb/forward-flight BEMT) fail anchor/thinness gates above.
- Rotorcraft blade dynamics: hover coning + flap frequency (blade-flapping),
  steady 1/rev collective-only equilibrium (w46 forward-flight-flapping),
  cyclic/swashplate control channel + trim inversion (w47 cyclic-pitch-trim),
  lead-lag modes + ground-resonance clearance (lead-lag-dynamics). Nonuniform
  inflow, maneuver flapping, transient response, forward-flight lag all
  still anchor-blocked (fresh 0/0 this wave).
- Rotorcraft performance: fwd-flight power (Glauert), range/endurance,
  banked turn, main/tail rotor sizing, autorotation — all owned; Vmax,
  ceilings, Vy, H-V, envelope limits, Category A, ETL, fin-offload all stay
  FTO-measured or anchor-blocked (rows above).
- Fixed-wing performance: climb/descent/glide/energy, range/endurance/SAR,
  takeoff/landing/BFL/OEI, turn, wind, windshear, speed-stability all
  owned; Vmax/Vmin, Vx/Vy, cruise optimization, stick-free, hydroplaning,
  drift-down, balked landing, corner speed all owned elsewhere or
  anchor-blocked (rows above). Vref/approach-speed: landing-performance owns
  the FM side (1.3 x Vs, FAR/CS 25.125) and FTO v-speeds the test side.
- Stall-speed surface: no gap (FM takeoff/landing/BFL/thrust-required
  consume Vs; FTO stall-speed-determination + stall-characteristics-testing
  measured; aerodynamics high-lift/planform and vehicle-design own the
  CL_max side).

## Standards-map check

30 ids present in standards-map.yaml (grep-verified '^  - id:' = 30):
far-25 line 16, cs-25 line 27, far-29 line 270, arp4754a line 38,
rtca-do-229 line 303, plus arinc-429, arinc-664, arp4761a, as9100, as9102,
asme-y14-5, cmh-17, do-160, do-178c, do-254, do-330, ecss, far-107, far-33,
itar-ear, mil-std-1553, mil-std-1797a, mmpsd, msg-3, naca-tn-902, naca-tr-824,
nas-410, rtca-do-185, rtca-do-260b, sep-2640. far-25 / cs-25 / far-29 are
the FM family conventions. No NO_CANDIDATES row needed a new id; drift-down
stays map-blocked (no far-121), rotorcraft HQ stays map-blocked (no ads-33).
No new ids proposed (reference-only conventions unchanged).

## Method note

All greps and scans above were read-only terminal/search_files runs; the
corpus parser recovered 1306/1306 task blocks (id, query, intent,
expected_skill), so the FM inventory of 98 tasks (2 per leaf, verified per
leaf) and every token-demand scan are complete-file scans. The wave-47
receipt (ops/automation/state/wave47-recon/task-0-receipt.md) and the
wave-46 receipt were read first; every wave-46/47 decline row was re-verified
with FRESH greps this wave (battery of ~26 token patterns over skills/ +
eval/, outputs summarized above with file-level hits). Fence quotes are
verbatim from the named SKILL.md files. Web lookup used only to confirm the
existence/citability of the ideal-twist published anchor for the blade-twist
marginal seam (Leishman fig 3.8; JUVS 2017; NASA AIAA 2020); no candidate
was ranked from memory. No repo file was modified except this receipt.
