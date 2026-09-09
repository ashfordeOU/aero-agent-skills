# WAVE-49 FLIGHT-MECHANICS PROBE RECEIPT (task-8, whole-family FRESH extension probe)

- Repo: the local AeroSkills repo. HEAD verified `git log --oneline -1` =
  9c2b3fe4 ("ops: stage wave-49 brief (655 baseline, daylight gate 11:45
  UTC)"). Working tree clean except the wave49-recon receipts directory
  (git status --porcelain: 1 untracked entry, this receipt).
- Scope: ENTIRE flight-mechanics family, 49 leaves (2 flight-dynamics-sim +
  4 handling-qualities + 32 performance + 11 stability-control), probed
  FRESH at wave-49 HEAD. This is an EXTENSION probe under the brief's
  smallest-first extension tier (SES 47 -> MQ 48 -> FM 49): wave-48
  (task-0, NO_CANDIDATES) stands only if fresh evidence confirms it.
- Family delta since wave-48: ZERO leaves (49 -> 49; the wave-48 brief
  added leaves to AV/SPACE/PROP/VD/GNC/STRUCT only, none to FM). Router
  parity re-verified: 49 rows in skills/flight-mechanics/SKILL.md = 49
  leaves (`find skills/flight-mechanics -mindepth 3 -name SKILL.md` = 49;
  +1 family router SKILL.md at family root).
- Corpus delta since wave-48: 1306 -> 1326 (+20). All 20 new tasks
  (w48-cyclic-executive-scheduling-1/-2, w48-dual-cycle-1/-2,
  w48-feedback-linearization-1/-2, w48-fuel-system-weight-estimation-1/-2,
  w48-h-infinity-synthesis-1/-2, w48-honeycomb-core-micromechanics-1/-2,
  w48-laminate-bending-stiffness-1/-2, w48-landing-gear-weight-estimation-1/-2,
  w48-mmod-shielding-sizing-1/-2, w48-sliding-mode-control-1/-2) parse and
  route to the ten wave-48 leaves in avionics, propulsion, gnc-autonomy,
  vehicle-design, structures, space-systems. ZERO new corpus tasks touch
  any FM surface: the FM routing inventory is byte-intact at 98 tasks over
  49 leaves, exactly 2 per leaf (full-file parse of eval/hit1-corpus.yaml
  = 1326/1326 task blocks recovered; per-leaf counts printed and verified,
  0 orphans, 0 unserved). Corpus growth therefore creates NO new demand
  signal for any FM candidate seam.
- Standards map: 30 ids (`grep '^  - id:' standards-map.yaml` = 30);
  far-25 line 16, cs-25 line 27, mil-std-1797a line 248, far-29 line 270
  (FM family conventions; no new id proposed).
- Doctrine: wave-48 flight-mechanics receipt
  (ops/automation/state/wave48-recon/task-0-receipt.md) and wave-47
  (ops/automation/state/wave47-recon/task-0-receipt.md) read in full
  first, plus wave-46 (ops/automation/state/wave46-recon/task-0-receipt.md)
  and wave-45 (ops/automation/state/wave45-recon/task-1-receipt.md) for
  the full adjudication lineage. Every wave-43/45/46/47/48 decline and
  STAY row was re-verified with FRESH greps at this HEAD (batteries
  below). No prior decline was overturned.

## Verdict

**NO_CANDIDATES.** Flight-mechanics at 49 is saturated at its leaf margins
on a FRESH whole-family probe at the wave-49 HEAD. The wave-48
NO_CANDIDATES verdict and its closing claim (only the two marginal
seams — IGE-climb and blade twist — reached a two-sided review, both
declined) are confirmed on fresh evidence; both reopen triggers are
adjudicated below and neither has fired (corpus demand zero, no new
published deterministic anchor). The tree is unchanged since wave-48, so
the only possible new seams are (a) surfaces prior waves never
adjudicated, and (b) reopen triggers. This probe swept both: eleven
never-before-adjudicated seams were probed to the gates (roll
performance, wing divergence, payload-range diagram, steady-heading-
sideslip trim, radius of action, adverse yaw, maneuver point, CG-limit
derivation, wind-corrected field length, delta-3 coupling, blade
sailing); every one fails zero-owner (live cross-family or in-family
owner), the deterministic-anchor gate (no canonical closed form), or the
thin-extension gate on fresh evidence below. No wave-43/45/46/47/48
decline is overturned; the family remains a no-yield extension target.

## Whole-family enumeration (49 leaves, all probed)

```
flight-dynamics-sim (2): point-mass-trajectory, six-dof-simulation
handling-qualities (4): cooper-harper-rating, mil-std-1797a,
  pilot-induced-oscillation, pitch-bandwidth-criteria
performance (32): balanced-field-length, breguet-endurance, breguet-range,
  climb-performance, descent-performance, energy-height, glide-performance,
  landing-performance, oei-climb-gradient, propeller-range,
  rotorcraft-autorotative-descent, rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance, rotorcraft-blade-flapping-dynamics,
  rotorcraft-cyclic-pitch-trim (w47), rotorcraft-forward-flight-flapping (w46),
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

## Wave-48 reopen triggers — adjudicated at wave-49 HEAD (none fired)

- IGE vertical climb (rotorcraft vertical climb in ground effect): reopen
  trigger was "a published deterministic IGE-climb formula set with
  magnitudes". Not fired. Fresh web check confirms the published ground
  effect treatments are hover-state (Cheeseman-style height correction)
  and forward-flight (ARC R&M 3021 disc-incidence ground effect); climb-
  in-ground-effect power remains wake-distortion territory modeled only
  in comprehensive numerical codes, no canonical closed form. Corpus
  demand zero (fresh token scan ige-climb/ground-effect-climb: 0 corpus
  hits; the only tree hits are the two sibling fence lines in
  rotorcraft-hover-ground-effect and rotorcraft-vertical-climb-performance,
  both of which explicitly defer the combination). Decline stands.
- Rotor blade twist in hover (BEMT with linear twist): reopen trigger was
  "corpus demand, or spec-phase folding of a theta_tw parameter into the
  BEMT sibling". Not fired: corpus demand zero (fresh scan ideal-twist/
  blade-twist: 0 corpus hits); the extension/thinness decline stands —
  at theta_tw = 0 the identity degenerates to the BEMT sibling's own
  closed forms (rotorcraft-blade-element-hover-performance records the
  untwisted assumption as its own specialization boundary), giving no
  independent in-repo cross-check identity.
- Rotorcraft flapping transient response (wave-47): reopen trigger was "a
  verified textbook equation set with magnitudes AND any demand signal".
  Not fired: demand zero (fresh scan flap-transient/rotor-time-constant/
  rpm-decay: 0 skills + 0 corpus). Decline stands.

## Newly probed seams this wave (never adjudicated in waves 43-48)

| Candidate seam | Gate result + fresh evidence |
|---|---|
| fixed-wing roll performance (steady roll rate / time-to-bank from aileron deflection and roll damping) | a FAIL (identity split between two live owners), corpus routed. vehicle-design/sizing/control-surface-sizing publishes the steady roll rate p = -2 V C_l_delta delta / (b C_l_p) verbatim and sizes the aileron from the roll-rate-requirement (corpus css1/css2 route there on aileron-sizing/roll-rate tokens); flight-mechanics handling-qualities/mil-std-1797a owns the roll-performance grading band including the first-order roll response phi(t) = p_ss (t - tau (1 - exp(-t/tau))) to a 60 deg bank (its own domain content). FM dynamic-stability owns the roll-subsidence time-constant check. No un-owned identity segment remains; a new FM roll-performance leaf would collide with both owners at token level (roll-rate, time-to-bank, roll-mode-time-constant). |
| wing torsional divergence speed | a FAIL (cross-family owner): aerodynamics/aeroelasticity/divergence-speed is a live leaf for the torsional-divergence dynamic pressure; FM stability-control/aileron-reversal owns the sibling control-reversal identity only and the aerodynamics family hosts the aeroelastic side. No gap. |
| payload-range diagram (FM performance home) | a FAIL (cross-family owner): vehicle-design/conceptual/payload-range-diagram owns the full corner-point identity (max payload / max fuel / ferry range / reserve policy with Breguet closure); corpus tasks payload-range-diagram-w8-1/-2 route there. Wave-45/46 closed this surface; re-confirmed live. |
| steady-heading-sideslip / directional trim (rudder-aileron trim in crosswind, sideslip from crosswind) | a FAIL (measured + derivative owners): flight-test-operations/stability/lateral-directional-stability-flight-test owns the measured steady-heading-sideslip reduction (corpus w32 tasks: measured rudder/aileron gradients to Cn_beta/Cl_beta estimates); FM lateral-directional-stability owns Cn_beta/Cl_beta geometry closures; stability-derivatives-avl owns the derivative estimation. A trim-application leaf adds no independent derivative identity and collides on the sideslip token surface (corpus sideslip tasks all route to the FTO reduction). |
| radius of action (fuel out-and-return mission radius) | a PASS (0 skills + 0 corpus for radius-of-action tokens), d FAIL (thin-extension gate). It is a Breguet application over breguet-range/breguet-endurance with an out-and-back fuel split; reserve policy and mission segments are owned by vehicle-design sizing-mission-profile / payload-range-diagram; no standards-map id carries a mission-reserve policy (no far-121/ac-120-42b among the 30). Same decline class as wind-corrected range (wave-45): thin extension with no independent closed-form identity, corpus 0. |
| adverse yaw / yaw-due-to-aileron (Cn_delta_a) | a PASS (0 skills + 0 corpus), d FAIL. No canonical published magnitude set: Cn_delta_a estimates are semi-empirical (differential induced drag + spanwise profile-drag increments with empirical weighting), the fabricated-correlation risk class of the wave-43 rotorcraft-forward-flight-envelope-limits precedent; FM aileron-reversal (roll) and lateral-directional-stability (Cn_beta) own the adjacent identities; corpus 0. |
| maneuver point / stick-free static margin (analytic pull-up margin) | a FAIL (wave-45/47 row re-verified FRESH): flight-test-operations/stability/control-force-flight-test owns force-per-g/stick-force-gradient measured tokens with corpus task support; FM control-surface-effectiveness owns the stick-force magnitude at the FAR 25.143 gate; FTO flight-loads-survey owns the measured maneuver-point reduction (corpus task: maneuver point feasibility at dynamic pressure). Corpus scan: all maneuver-point hits route to FTO. |
| stability/controllability-derived CG limits (aft limit from minimum static margin, forward limit from elevator authority) | a FAIL (token owner + soft magnitudes): vehicle-design/mass-properties/cg-envelope owns the CG-envelope/forward-aft-limit token surface (corpus tasks route there; canard-sizing and landing-gear-layout consume the same envelope), and the required minimum static margin has no canonical published magnitude (design margin choice) while the forward limit needs the CL_max/elevator-deflection limit interplay — no deterministic anchor set. FM longitudinal-stability and control-surface-effectiveness own the input identities; a derivation leaf would be an application of owned closed forms. |
| wind-corrected takeoff/landing field length (ground roll with steady wind) | a FAIL (numeric-class + FTO measured). Fresh check: takeoff-performance, landing-performance and balanced-field-length contain ZERO wind content (no fence, no correction); wind-effects owns only the component-resolution identity (its corpus task we1 covers the headwind/crosswind components for the takeoff wind check, not a distance correction). But the distance-with-wind identity is an energy/numeric integration (variable acceleration with drag) whose textbook forms are approximation correction factors — the same no-clean-closed-form class as the wave-48 fixed-wing ground-effect takeoff/landing distance application decline; FTO measured slots are live leaves: flight-test-operations/performance/takeoff-distance-determination, landing-distance-determination, accelerate-stop-distance, engine-failure-takeoff-flight-test (corpus tkd1/tkd2 route to FTO per wave-45). Corpus 0 for FM distance-wind tokens. |
| delta-3 pitch-flap coupling (flap-pitch hinge geometry in the 1/rev equilibrium) | a PASS (0 skills + 0 corpus for delta-3/pitch-flap-coupling), d FAIL (extension gate, wave-48 blade-twist precedent): at delta-3 = 0 the modified flap equation degenerates exactly to the flap siblings' own closed forms (rotorcraft-blade-flapping-dynamics, rotorcraft-forward-flight-flapping, rotorcraft-cyclic-pitch-trim), giving no independent in-repo cross-check identity, and the body would be a parameter generalization thinner than the family's transient-response thinness precedent; corpus 0. |
| rotor blade sailing (rotor start/shutdown blade response in wind) | a PASS (0 skills + 0 corpus), d FAIL: transient aeroelastic response to a wind profile during start/shutdown, not a closed-form equilibrium; no chapter-continuous deterministic anchor in the FM family's cited texts; corpus 0. |

## Wave-43/45/46/47/48 STAY rows re-verified FRESH (fresh greps at wave-49 HEAD, zero counter-evidence)

| Seam class | Fresh evidence |
|---|---|
| rotorcraft-flapping-nonuniform-inflow | 0 skills + 0 corpus (nonuniform-inflow/inflow-gradient/inflow-distribution); anchor failure stands (NASA TP: linear-gradient models underpredict lateral flapping below mu ~0.2) |
| rotorcraft-flapping-in-maneuvers | 0 skills + 0 corpus (maneuver-flapping/hub-roll-rate); research/aeroelastic level only |
| rotorcraft-lag-dynamics-forward-flight | 0 skills; corpus 0 (only tree hit for the pattern is a systems-engineering event-tree false positive); periodic-coefficient response, not closed form |
| rotorcraft-flapping-transient-response | 0 skills + 0 corpus; unhosted transient dynamics (see reopen trigger above, not fired) |
| autorotative entry / rotor-RPM decay transient + autorotative flare | 0 skills + 0 corpus for FM (only tree hit: flight-test-operations/performance/rotorcraft-autorotation-flight-test measured flare/descent slot); rotorcraft-autorotative-descent fence ("before any flare") and FTO height-velocity/flare measured slots stand |
| fixed-wing Vmax/Vmin, Vx/Vy, cruise optimization, stick-force-per-g, max-specific-range, hydroplaning | owners re-confirmed live (thrust-required/speed-stability; FTO climb/cruise/control-force tests; avionics performance-computation ECON; landing-performance wet-runway footnote), corpus routes there |
| rotorcraft Vmax, H-V diagram, fwd-flight envelope limits, hover ceilings, fwd-flight Vy, ETL/translation-lift, fin-offload, Category A OEI, autorotative range, rotor-speed governing | 0 skills + 0 corpus on each token class (fin-offload/vertical-fin: 0/0; translation-lift/etl: 0/0); FTO measured leaves live (rotorcraft-performance-flight-test, rotorcraft-height-velocity-diagram-test, rotorcraft-forward-flight-climb-test, rotorcraft-category-a-oei designated reserve, rotorcraft-autorotation-flight-test); anchor/semi-empirical failures stand |
| drift-down / OEI en-route ceiling | 0 skills + 0 corpus; standards-map-blocked (no far-121/ac-120-42b); energy integration not closed form |
| balked-landing / go-around | oei-climb-gradient owns the 25.121 rows; FTO balked-landing reserve; corpus routes to FM/FTO owners |
| wind-corrected range / still-air scaling | thin-extension decline stands (wind-effects + breguet/propeller/specific-range owners); corpus 0 |
| corner velocity / V-n | FTO envelope-expansion + structures loads owners live; corpus ee1 routes there |
| absolute/cruise ceiling, time-to-climb, climb fuel/distance | climb-performance + vehicle-design sizing-mission-profile owners live |
| stick-free stability / analytic stick-force-per-g | FTO control-force-flight-test + FM control-surface-effectiveness (see newly-probed maneuver-point row) |

## Closed veins list (fresh confirmations at wave-49 HEAD)

- Fixed-wing performance: takeoff (ground roll/liftoff), balanced field
  (V1/ASD/AGD/35-ft OEI air segment), landing (approach/flare/stopping),
  OEI gradients, climb/descent/glide, energy height/Ps/zoom, jet+prop
  range/endurance/SAR, speed stability/TR-PR, turn, wind triangle,
  windshear — all owned; cruise-speed/altitude optimization, Vx/Vy, Vmax,
  corner speed, field-length sizing constraints and measured distance
  slots owned by avionics/vehicle-design/FTO as documented in the stays
  above. Newly swept wind-corrected field length fails the closed-form
  gate (row above).
- Stability/control and flight dynamics: static longitudinal
  (NP/static margin), lateral-directional (dihedral, Cn_beta, Dutch
  roll/roll/spiral), dynamic modes (short period, phugoid, roll
  subsidence), trim (stick-fixed), stick force at the limit gate,
  deep stall, spin recovery, aileron reversal, AVL derivative estimation,
  six-DOF/point-mass simulation, HQ (Cooper-Harper, 1797A incl. roll
  performance band, PIO, pitch bandwidth) — all owned. Newly swept roll-
  performance, divergence, SHSS-trim, maneuver-point, CG-limit seams all
  fence to live owners (rows above).
- Rotorcraft: hover momentum/BEMT/IGE, vertical climb, axial descent
  flow states, steady autorotation, forward-flight power + best speeds,
  range/endurance, banked turn, main/tail rotor sizing, and the full
  blade-dynamics chain (hover coning/frequency, collective-only fwd
  flapping, cyclic-pitch trim, lead-lag/ground-resonance-adjacent) —
  all owned. Un-owned remainders (IGE climb, twist, transient entry/
  flare, delta-3, blade sailing, nonuniform inflow, maneuver flapping,
  fwd-flight lag, fin offload, ETL, Vmax/ceilings/H-V/Category A)
  fail the anchor/thinness/FTO-measured gates as documented.

## Standards-map check

30 ids present (grep-verified '^  - id:' = 30): far-25 line 16, cs-25
line 27, mil-std-1797a line 248, far-29 line 270 are the FM family
conventions. No NO_CANDIDATES row needed a new id; drift-down stays
map-blocked (no far-121/ac-120-42b), rotorcraft HQ stays map-blocked (no
ads-33). No new ids proposed.

## Method note

All greps and scans were read-only terminal/search_files runs at HEAD
9c2b3fe4; helper parser runs were read-only python over eval/hit1-corpus.yaml
(recovered 1326/1326 task blocks; FM inventory 98 tasks / 49 leaves
printed per leaf, exactly 2 each; the +20 wave-48 tasks verified to route
to the ten wave-48 leaves in six non-FM families). The wave-48, wave-47,
wave-46 and wave-45 FM receipts were read in full first; every prior
decline/STAY row was re-verified with fresh greps (token batteries above,
each reporting file-level hits). Sibling fence quotes are verbatim from
the named SKILL.md files. Web lookup used only to adjudicate the wave-48
IGE-climb reopen trigger (published ground-effect treatments are
hover-state Cheeseman and forward-flight R&M 3021; no climb-GE closed
form). No candidate was ranked from memory. No repo file was modified
except this receipt.
