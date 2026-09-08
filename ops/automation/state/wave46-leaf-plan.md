# Wave-46 leaf plan (ops manager, 12 whole-family FRESH probe receipts)

RECEIPTS OVER LISTS: all 10 planned leaves come from whole-family FRESH probe
receipts at HEAD 45931c16 (zero-owner greps + sibling fence reads + standards
id grep + corpus demand checks), NOT a candidate list. Probe history: wave-45
partial-prep receipts (task-0 flight-mechanics, task-1 SES, task-2 avionics,
task-3 MQ, task-4 FTO, task-6 space, task-8 aero) written at pre-rewrite HEAD
d4b4d590 and preserved through the history rewrite; re-validated at current
HEAD by git diff d4b4d590..HEAD restricted to skills/, eval/hit1-corpus.yaml,
standards-map.yaml = EMPTY (leaf counts verified on disk: FM 47, SES 47,
avionics 48, MQ 48, FTO 49, propulsion 50, space 52, gnc 55, VD 55, CC 56,
aero 57, structures 61; 625 total). Missing probes (propulsion task-5,
gnc task-7, vehicle-design task-9, cross-cutting task-10, structures task-11)
dispatched fresh at 45931c16 as 5 parallel read-only agents (batch
deleg_e97bed1d) + cross-cutting re-run (deleg_9bb0cc78); receipts written
2026-09-08 12:07-12:23 UTC.

## Probe outcome (12/12 receipts, all whole-family FRESH)

| Family | Receipt | Verdict |
|---|---|---|
| flight-mechanics 47 | task-0 | 1 GO: rotorcraft-forward-flight-flapping |
| systems-engineering-safety 47 | task-1 | NO_CANDIDATES (saturated reaffirmed, receipts) |
| avionics 48 | task-2 | 1 GO: mixed-criticality-scheduling |
| manufacturing-quality 48 | task-3 | NO_CANDIDATES (saturated reaffirmed, receipts) |
| flight-test-operations 49 | task-4 | NO_CANDIDATES (all 10 wave-45 declines stand, fresh greps) |
| propulsion 50 | task-5 | 2 GO: hydrogen-peroxide-monopropellant-thruster, piston-engine-cycle |
| space-systems 52 | task-6 | NO_CANDIDATES (saturated reaffirmed, receipts) |
| gnc-autonomy 55 | task-7 | 3 GO: ionospheric-delay-correction, impact-time-control-guidance, deadbeat-control |
| vehicle-design 55 | task-9 | 1 GO: landing-gear-height-sizing (extension, pool-drop rule) |
| cross-cutting 56 | task-10 | NO_CANDIDATES (default CLOSED reaffirmed fresh) |
| aerodynamics 57 | task-8 | NO_CANDIDATES (wave-41/43 declines stand) |
| structures 61 | task-11 | 2 GO: elliptical-hertz-contact, crack-tip-plasticity-correction (extension) |

Planned pool = 10 (MUST land >= 10 met with zero margin by design; all 10
carry full (a)-(f) gate evidence in their receipts). Extension probes for
vehicle-design/structures/cross-cutting were dispatched under the brief
decision rule (primary pool of 7 sat below the ~12 viability line); they
restored the pool from 7 to 10. No further family exists to extend to.

## Planned leaves (10), smallest-family order, receipts cited

1. flight-mechanics/performance/rotorcraft-forward-flight-flapping
   (FM 47; probe task-0 rank 1 GO: steady first-harmonic (1/rev) flapping
   equilibrium of the idealized centrally hinged rotor blade in forward
   flight under uniform inflow: longitudinal and lateral tip-path-plane
   tilt from advance ratio mu and inflow ratio lambda, Lock-number
   machinery in the sibling hover convention; rotorcraft-blade-flapping-
   dynamics owns hover coning + rotating flap frequency ratio only and its
   fence routes forward-flight flapping to "the forward-flight sibling"
   (quoted, lines 23-36/35-36); rotorcraft-forward-flight-performance is
   power/best-speeds only, no blade motion; Johnson Helicopter Theory ch.4
   + Leishman ch.4 (same chapters the sibling cites); far-29 ref-only;
   zero-owner on tip-path-plane/first-harmonic-flap/longitudinal-flapping
   tokens tree-wide and in corpus; spec-time: add fence line to
   rotorcraft-blade-flapping-dynamics + FM router row at close)
2. avionics/fsw/mixed-criticality-scheduling
   (AV 48; probe task-2 rank 1 GO: dual-criticality C_LO/C_HI task model
   schedulability: LO-mode fixed-point RTA over C_LO, HI-mode AMC-rtb fixed
   point R_i = C_i(HI) + sum_{hp LO} ceil(R_i/T_j)*C_j(LO) + sum_{hp HI}
   ceil(R_i/T_j)*C_j(HI) vs deadlines; Vestal 2007 + Baruah-Burns-Davis 2011
   AMC-rtb; do-178c ref-only (fsw pack convention); real-time-scheduling
   fences WCET/jitter/arbitrary-deadline out, none of the four fsw scheduling
   siblings claims criticality modes; zero-owner on mixed-criticality/
   amc-rtb/dual-criticality tokens; spec-time caveat: never tag bare
   criticality/dal/software-level/wcet; add fence line to real-time-
   scheduling + avionics router row at close)
3. propulsion/rocket/hydrogen-peroxide-monopropellant-thruster
   (PROP 50; probe task-5 GO-1: H2O2 catalytic decomposition over silver
   catalyst bed, 2 H2O2(l) -> 2 H2O(g) + O2(g), adiabatic decomposition
   chamber temperature from Hess-law energy balance at documented peroxide
   concentration, frozen-composition isentropic expansion to vacuum exhaust
   velocity and Isp; direct chemical sibling of wave-45 hydrazine leaf which
   is N2H4-specific end to end (quoted); zero-owner on peroxide/silver-
   catalyst tokens (H2O2 appears once as a bipropellant oxidizer example in
   propellant-selection); ecss ref-only; decomposition-temperature/impulse
   bands reference-only)
4. propulsion/reciprocating/piston-engine-cycle
   (PROP 50; probe task-5 GO-2: air-standard Otto cycle thermal efficiency
   from compression ratio + specific-heat ratio, four-stroke bookkeeping
   from IMEP/displacement/crankshaft speed to indicated power, brake power
   at mechanical efficiency, BSFC from fuel flow and brake power, published
   GA brake-thermal-efficiency/BSFC bands reference-only; NEW PACK
   propulsion/reciprocating/ (first leaf - router group row + guidance line
   added at close; flagged in receipt for the leaf-plan gate); far-33
   ref-only (aircraft-engine convention); zero-owner on reciprocat/otto/
   bsfc/mean-effective tokens tree-wide and in corpus; family router Domain
   enumerates only turbine/rocket/ramjet/electric classes)
5. gnc-autonomy/navigation/ionospheric-delay-correction
   (GNC 55; probe task-7 GO-1: Klobuchar broadcast ionospheric delay model:
   pierce-point geomagnetic latitude, amplitude/period polynomials from
   alpha/beta coefficients, vertical delay 5e-9 + sum A_n phi_m^n, obliquity
   factor to slant delay; wave-45 GO4 cleared every gate, dropped only on
   pool size - wave-46 pool needs it; gnss-carrier-smoothing owns the
   divergence MONITOR only (quoted), gnss-pseudorange-positioning consumes
   pseudoranges as given; Klobuchar 1987 / IS-GPS-200; rtca-do-229 ref-only;
   sim-verified Hit@1 both queries, 12.5+ point margins, zero theft)
6. gnc-autonomy/guidance/impact-time-control-guidance
   (GNC 55; probe task-7 GO-2: impact-time-constrained terminal guidance
   (salvo/cooperative simultaneous impact): guidance command that drives
   time-to-go to a commanded impact time along the PNG-derived intercept
   geometry, closed-form impact-time control law; zero-owner on
   impact-time/salvo/impact-angle tokens tree-wide AND zero in 1266-task
   corpus; no guidance sibling claims the time-constrained law (midcourse
   owns handover/trajectory shaping, impact-point-prediction is open-loop
   ballistic); published closed-form anchor (deterministic, stdlib);
   arp4754a ref-only; sim Hit@1 both queries, clean margins)
7. gnc-autonomy/control/deadbeat-control
   (GNC 55; probe task-7 GO-3: deadbeat digital control design: finite-
   settling controller placing ALL closed-loop poles at z = 0, direct
   deadbeat synthesis for a discrete plant (controller from plant pulse
   transfer function), settling in n samples, steady-state tracking check;
   digital-control-design owns discretization/emulation/discrete-PID/
   stability/sample-rate but never direct deadbeat synthesis (quoted);
   zero-owner on deadbeat/finite-settling tokens tree-wide and corpus;
   published closed-form anchor; arp4754a ref-only; sim Hit@1 both queries,
   7+ point margins)
8. vehicle-design/sizing/landing-gear-height-sizing
   (VD 55; probe task-9 rank 1 GO (extension, pool-drop rule): vertical
   landing-gear geometry: static ground line and main/nose gear heights
   from ground-clearance constraints, tail cone rotation clearance,
   nacelle/propeller clearances at level and rotated attitudes;
   landing-gear-layout uses heights as INPUTS (fence quoted), no vertical
   geometry owner exists; far-25 ref-only (family convention); same
   conceptual-design book set as sibling; zero-owner tree-wide, zero corpus;
   adds its own 2 corpus tasks at merge)
9. structures/fem/elliptical-hertz-contact
   (STR 61; probe task-11 GO-1 (extension): general Hertz elliptical contact
   patch between bodies with UNEQUAL principal radii: eccentricity solve,
   elliptic-integral semi-axes a != b, peak pressure p0 = 3P/(2 pi a b);
   hertzian-contact-stress covers circular-patch and line-contact
   degeneracies only and quotes "Unequal crossed radii give the general
   elliptical patch of the Hertz elliptic integrals, out of scope here"
   (lines 50-52; wave-43 spec repeats the carve-out); zero-owner on
   elliptical-contact tokens, zero corpus; far-25 + cs-25 ref-only (fem pack
   convention))
10. structures/materials/crack-tip-plasticity-correction
    (STR 61; probe task-11 GO-2 (extension): Irwin plastic-zone radius and
    effective-crack-length small-scale-yielding correction: r_p, a_eff =
    a + r_p, K_eff, plane-stress vs plane-strain zone, Dugdale strip-yield
    zone; fracture-toughness QUOTES the ASTM E399 size rule
    2.5*(K/sigma_ys)**2 but never computes r_p or a_eff (quoted);
    walker-forman declares linear-elastic small-scale-yielding scope with no
    correction; the empirical Elber-closure/da-dN-threshold slice wave-45
    declined STANDS (re-verified); mmpsd ref-only (materials pack
    convention); zero-owner on dugdale/plastic-zone/effective-crack)

## Family spread and post-landing counts

Per-family after (625 -> 635 leaves): flight-mechanics 48, avionics 49,
propulsion 52, gnc-autonomy 58, vehicle-design 56, structures 63; SES 47,
MQ 48, FTO 49, space-systems 52, cross-cutting 56, aerodynamics 57
unchanged. 6 families touched of 12. Corpus 1266 -> 1286 (+2 per leaf).
Ledger 625 rows -> 635 (rows 626-635 appended at creation, 9.5 each).
SKILL.md tracked 637 -> 647.

## Spec-time triage decisions

- Pool = 10 with zero margin: NO conditional items this wave. Every planned
  leaf is a firm GO from its receipt with full evidence; ionospheric-delay-
  correction (wave-45's pool-conditional drop) is REQUIRED now because the
  pool needs all 3 gnc leaves. No leaf may be dropped at spec time without
  a fresh hard blocker (receipt-level (a)-(f) evidence would need to fail).
- piston-engine-cycle requires the NEW pack propulsion/reciprocating/ (router
  group row + guidance bullet at close) - mechanical, flagged in receipt,
  accepted into the plan.
- Corpus-query discipline (wave-45 fir-bandpass lesson): all fragment queries
  must carry the leaf's own hyphenated name/tag tokens verbatim from the
  receipt gate (e); no reworded queries at build time.

## Build order

Leaves built sequentially (ONE builder at a time per resume doctrine) in the
numbered order above via aero-delegate.sh skills skill_build @brief
--max-turns 40 --budget 10. Each builder commits its own leaf (six artifacts
+ ledger row), then the ops manager runs the per-leaf gate battery
(leaf-create-gate, tests under both interpreters, completeness, attest),
commits any router/fence work per batch, and records spend after each leaf.
