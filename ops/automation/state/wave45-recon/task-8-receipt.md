# WAVE-45 AERODYNAMICS FAMILY PROBE RECEIPT (task-8)

Repo: the local AeroSkills repo, git HEAD 5cc8fef3 (verified `git rev-parse HEAD` = 5cc8fef33ffa3bd5530847040ef891299dde107d).
Probe date: 2026-09-07. Read-only probe: no skills/, eval/, docs/, Makefile, scripts/, ops/automation brief, or standards-map.yaml writes; no git writes. One write only: this receipt.
Wave-44 baseline honored: stokes-creeping-flow-drag (boundary-layer), ackeret-linearized-supersonic and hypersonic-piston-theory (high-speed), added-mass-coefficients-potential-flow (aeroelasticity) are ON DISK and fenced as owners. Wave-41/43 standing declines not re-opened without fresh counter-evidence (none found). RECEIPTS OVER LISTS.

## Whole-family enumeration (53 leaves, 10 packs, all probed)

`find skills/aerodynamics -mindepth 3 -name SKILL.md` returns 53 files. Disk pack split (authoritative; the wave-45 brief pack figures of boundary-layer 6 / high-speed 23 do not match disk, totals agree at 53):
aeroelasticity 4 (added-mass-coefficients-potential-flow, aeroelastic-gust-response, divergence-speed, flutter-speed-prediction), airfoil 5 (airfoil-geometry, airfoil-optimization, airfoil-selection, thin-airfoil-section-theory, xfoil-analysis), boundary-layer 7 (boundary-layer-separation, boundary-layer-theory, boundary-layer-transition, rough-wall-skin-friction, stagnation-flow-boundary-layer, stokes-creeping-flow-drag, unsteady-laminar-stokes-layers), cfd 7 (cfd-convergence, cfd-mesh-generation, cfd-turbulence-modeling, cfd-validation, delta-wing-vortex-lift, panel-method, vortex-lattice-method), drag-polars 3 (drag-polar, lift-curve-slope, parasite-drag), ground-effects 1 (ground-effect), high-lift 1 (high-lift-systems), high-speed 20 (ackeret-linearized-supersonic, aerodynamic-heating, bow-shock-standoff, compressible-couette-flow, fanno-flow, flat-plate-skin-friction-heating, hypersonic-flow, hypersonic-piston-theory, isentropic-flow-relations, normal-shock, oblique-shock, prandtl-meyer, rayleigh-flow, regular-shock-reflection, shock-expansion-airfoil, shock-tube, supercritical-airfoil, swept-wing-aerodynamics, transonic-similarity, wave-drag-area-rule), wind-tunnel 3 (wind-tunnel-model-design, windtunnel-data-reduction, windtunnel-wall-corrections), wing-design 2 (wing-planform-design, winglet-design).
Router parity: `grep -c "^| aerodynamics/" skills/aerodynamics/SKILL.md` = 53.

## Verdict

4 GO candidates, all clean deterministic closed-form slots with zero-owner tokens in the high-speed/boundary-layer/aeroelasticity veins: sears-function-gust-lift (aeroelasticity), squire-young-profile-drag (boundary-layer), laminar-far-wake (boundary-layer), mangler-axisymmetric-transform (boundary-layer). GO-1 and GO-2 are the strongest (named published results, zero-owner greps, existing standards ids, wordable corpus); GO-3 carries the wave-43 reserve precedent; GO-4 is LOW confidence and may drop at spec time (van-Driest-II-style function-dup adjudication risk, thinnest corpus pull). Everything else declines with reasons; no standing wave-41/43 adjudication was overturned.

## Ranked GO candidates

### GO-1 (rank 1, HIGH): aerodynamics/aeroelasticity/sears-function-gust-lift (suggested leaf name, family pattern like ackeret-linearized-supersonic)

Frequency-domain unsteady thin-airfoil response to a convected sinusoidal gust: complex Sears function S(k) from Bessel J0/J1/Y0/Y1 series, gain and phase lag versus reduced frequency k, unsteady gust-load amplitude against the 2 pi rho V b w_g quasi-steady reference, and the k to 0 quasi-steady and large-k roll-off limits. Rigid airfoil, no structure; complements the flexible-section time-domain discrete-gust sibling.

(a) Zero-owner greps across the whole skills/ tree (quoted, case-insensitive):
- `grep -rilE "sears-function|sears function|sinusoidal-gust|gust-transfer-function" skills/` -> rc=1, zero files
- `grep -ril "sears" skills/` -> hits only aerodynamics/high-speed/wave-drag-area-rule (SKILL.md, logic, tests: the Sears-Haack body, unrelated) and its router row
- `grep -rilE "harmonic gust|frequency-domain" skills/` -> zero files
- `grep -rilE "kussner|wagner|indicial" skills/` -> aeroelastic-gust-response (time-domain indicial owner) and added-mass-coefficients-potential-flow only
Corpus: "sears" matches 2 tasks, both the Sears-Haack-body tasks (id wd1/wd2) expected_skill wave-drag-area-rule; "theodorsen" 2 tasks to flutter-speed-prediction; no task carries sears-function or sinusoidal-gust.

(b) Quoted sibling fence, aeroelastic-gust-response SKILL.md: "Use when you must compute the dynamic aeroelastic response of a flexible two-degree-of-freedom typical wing section to a discrete gust with indicial unsteady aerodynamics: run the Wagner and Kussner lag-state lift model in the time domain, produce the plunge and pitch response histories for a one-minus-cosine gust, and report the dynamic magnification factor of the peak lift over the quasi-steady value". Body states "apparent-mass and full Theodorsen noncirculatory terms are neglected at this level" and pairs the model with flutter-speed-prediction ("the same typical-section machinery, a different question (stability there, forced response here)"). The file contains zero occurrences of frequency, harmonic, sinusoidal, or Sears. Frequency-domain gust response is neither produced nor fenced.

(c) Standards-map id that EXISTS: `grep -nE "^  - id: (far-25|cs-25|naca-tr-824)$" standards-map.yaml` -> line 16 far-25, line 27 cs-25, line 171 naca-tr-824. far-25/cs-25 reference-only matches the aeroelasticity convention (aeroelastic-gust-response and flutter-speed-prediction both carry far-25 + cs-25).

(d) Published deterministic anchor: Sears function S(k), the frequency response of a rigid thin airfoil to a sinusoidal vertical gust convected in incompressible flow; transcendental in k with Bessel J0, J1, Y0, Y1, computable by the Abramowitz and Stegun 9.1 series form that the sibling flutter leaf already uses for C(k); |S| = 1 at k = 0 (quasi-steady limit consistent with the gust leaf's documented L_qs = 2 pi rho V b w_g) and monotone roll-off with k. Source: Sears, "Some Aspects of Non-Stationary Airfoil Theory and Its Practical Application", Journal of the Aeronautical Sciences 8(3), 1941; standard treatments in Bisplinghoff, Ashley and Halfman, "Aeroelasticity" (unsteady incompressible gust chapter) and Fung, "An Introduction to the Theory of Aeroelasticity".

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "evaluate the sears-function lift response of the rigid airfoil to a sinusoidal-gust field at reduced frequency 0.5: compute the complex sears-function from the Bessel series, the gust gain and phase lag, and the unsteady gust-load amplitude against the quasi-steady 2 pi rho V b w_g reference"
2. "sweep the sears-function gain of the thin airfoil in the sinusoidal-gust encounter across reduced frequencies 0.1 to 2.0 and report the reduced frequency where the unsteady gust-load amplitude falls to half the quasi-steady value"
Tokens sears-function, sinusoidal-gust, gust-load-amplitude exist on no router row or leaf today.

(f) Tag discipline: proposed tags all distinctive hyphenated compounds: sears-function, sinusoidal-gust, unsteady-gust-load, gust-transfer-function, reduced-frequency-gust. No bare sears (collides with sears-haack on wave-drag-area-rule), no bare gust, no bare airfoil, no bare unsteady.

### GO-2 (rank 2, HIGH): aerodynamics/boundary-layer/squire-young-profile-drag

Section profile-drag coefficient of a 2-D body or airfoil from the boundary-layer momentum thickness at the trailing edge: the Squire-Young formula c_d,p = 2 (theta_TE / c) (U_TE / U_inf)^((H_TE + 5) / 2) with documented H_TE (about 1.4), the zero-pressure-gradient reduction to the Blasius flat-plate drag 2 theta / c = 1.328 / sqrt(Re_c), and the fully laminar chain (laminar integral growth of theta to the TE, Squire-Young mapping). Pairs with boundary-layer-separation and boundary-layer-transition, which stop their Thwaites traverses at the separation flag and the Michel transition onset respectively; neither maps the TE momentum state to drag.

(a) Zero-owner greps across the whole skills/ tree (quoted):
- `grep -ril "squire" skills/` -> rc=1, zero files
- `grep -rilE "profile-drag|profile drag" skills/` -> rc=1, zero files
- `grep -ril "trailing-edge" skills/` -> zero aerodynamic leaves (only unrelated hits, none drag-related)
- `grep -rilE "wake-survey|wake rake|momentum-deficit|momentum deficit" skills/` -> rc=1, zero files
Corpus: "squire" 0 tasks, "profile drag" 0 tasks.

(b) Quoted sibling fences. boundary-layer-transition SKILL.md: "grow the laminar layer with the Thwaites relation to get the momentum thickness theta at each station, then apply the Michel empirical criterion on the local Reynolds numbers to locate the natural transition point... no roughness, sweep or suction inputs and no Tollmien-Schlichting wave-growth integration". boundary-layer-separation SKILL.md: "grows the laminar layer with the Thwaites integral relation along the edge-velocity traverse and flags the first station where the Thwaites lambda parameter crosses -0.09... and evaluates the Stratford-style pressure recovery criterion to estimate the turbulent separation station". parasite-drag SKILL.md owns the whole-aircraft CD0 buildup (flat-plate Cf times form factor times interference factor over wetted area) and never computes a section profile-drag coefficient from a boundary-layer momentum state. xfoil-analysis is the numerical polar tool-adjacent leaf, no closed-form formula.

(c) Standards-map id that EXISTS: `grep -n "^  - id: naca-tr-824" standards-map.yaml` -> line 171, exists (NACA Report 824, Abbott-von Doenhoff-Stivers airfoil data). naca-tr-824 reference-only matches the whole boundary-layer pack convention (separation, transition, rough-wall-skin-friction, stagnation-flow-boundary-layer all carry it).

(d) Published deterministic anchor: Squire-Young profile-drag formula family, the momentum-integral trailing-edge relation c_D,p = 2 (theta_TE / c) (U_TE / U_inf)^((H_TE + 5) / 2); source: Squire and Young, "The Calculation of the Profile Drag of Aerofoils", ARC R&M 1838, 1938; Schlichting, Boundary-Layer Theory, 7th ed., McGraw-Hill, pp. 158-162 (the reference cited for the method in Coder and Maughmer, "Numerical Validation of the Squire-Young Formula for Profile-Drag Prediction", Journal of Aircraft 52(3), 2015). Deterministic check anchor: with U_TE = U_inf the formula must reproduce the Blasius flat-plate drag 1.328 / sqrt(Re_c), so the leaf's own contract can be anchored without any external data.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens (worded to avoid the momentum-thickness tag of boundary-layer-theory and the polar wording of xfoil-analysis):
1. "compute the section profile-drag coefficient of the airfoil with the squire-young-formula from the trailing-edge momentum thickness, the trailing-edge to freestream edge-velocity ratio, and the shape factor 1.4 at the trailing edge"
2. "estimate the profile drag of the fully laminar 2-D section at low Reynolds number with the squire-young-formula: grow the boundary-layer momentum thickness to the trailing edge on the integral growth relation and apply the edge-velocity-ratio exponent to the profile-drag coefficient"
Tokens squire-young-formula, profile-drag-coefficient, trailing-edge-momentum-thickness, edge-velocity-ratio exist nowhere today. Build-time caution: boundary-layer-theory tags carry momentum-thickness and boundary-layer-transition carries thwaites-integral, so both queries avoid those literal tokens and lean on squire-young-formula.

(f) Tag discipline: proposed tags squire-young-formula, profile-drag-coefficient, trailing-edge-momentum-thickness, laminar-profile-drag, momentum-integral-drag. No bare drag, no bare boundary-layer, no bare momentum, no bare airfoil.

### GO-3 (rank 3, MED): aerodynamics/boundary-layer/laminar-far-wake (suggested scope mirrors the wave-43 reserve item laminar-far-wake-free-shear)

Closed-form 2-D laminar far wake downstream of a body or flat plate: Goldstein small-defect similarity wake (Gaussian cross-stream defect profile, centerline defect decaying as x^-1/2, half-width growing as x^1/2), the momentum-deficit drag identity D = rho U_inf integral u1 dy across the wake (the closed-form basis of wake-survey drag), and the far-wake profile shape as a drag diagnostic.

(a) Zero-owner greps across the whole skills/ tree (quoted):
- `grep -rilE "far-wake|far wake|velocity-defect|velocity defect|goldstein" skills/` -> rc=1, zero files
- `grep -ril "wake" skills/` -> hits only windtunnel-wall-corrections and windtunnel-data-reduction (wake-blockage correction terms, unrelated to wake-profile drag) and an incidental script comment in stokes-creeping-flow-drag
Corpus: "wake-survey|wake rake|momentum deficit" 0 tasks, "wake" tasks are the tunnel wake-blockage tasks to windtunnel-wall-corrections.

(b) Quoted sibling fence: boundary-layer-theory SKILL.md "Use when the task is boundary-layer thickness estimation, displacement or momentum thickness, skin-friction coefficient on a surface, Reynolds-number regime classification, or transition location on a smooth surface" (attached flat-plate boundary layer only); boundary-layer-separation body pairs itself with the attached-side leaves and stops at separation. No leaf owns the downstream free-shear wake region; stokes-creeping-flow-drag owns the low-Re attached sphere flow, unsteady-laminar-stokes-layers owns the unsteady Stokes layers. The wave-43 leaf plan carried laminar-far-wake-free-shear on its reserve pool (never built because reserves were unused), a prior GO-quality signal.

(c) Standards-map id that EXISTS: line 171 naca-tr-824 (same grep as GO-2), boundary-layer pack convention.

(d) Published deterministic anchor: laminar wake similarity family: the 1933 Goldstein wake solution behind a flat plate and the far-wake small-defect Gaussian profile with x^-1/2 centerline decay, plus the exact momentum-integral drag identity D = rho U_inf integral_-inf^+inf u1 dy. Source: Schlichting, Boundary-Layer Theory (wakes and free-shear-layer chapter, wake-after-a-flat-plate treatment); White, Viscous Fluid Flow (laminar free shear layers section, plane wake defect solution). Constants are fixed textbook values (0.664 Blasius drag link, pi-scaled Gaussian spreading), fully deterministic offline.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "compute the drag of the thin plate from the measured laminar far-wake velocity-defect profile at the traverse station: integrate the momentum deficit across the wake with the wake-momentum-integral identity and report the drag coefficient"
2. "predict the laminar far-wake velocity-defect profile downstream of the flat plate: the Gaussian similarity defect shape, the centerline-defect decay with downstream distance, and the wake half-width growth from the similarity solution"
Tokens far-wake-velocity-defect, wake-momentum-integral, centerline-defect-decay, laminar-far-wake exist nowhere today.

(f) Tag discipline: proposed tags laminar-far-wake, far-wake-velocity-defect, wake-momentum-integral, velocity-defect-profile, wake-survey-drag. No bare wake, no bare drag, no bare profile.

### GO-4 (rank 4, LOW): aerodynamics/boundary-layer/mangler-axisymmetric-transform

Mangler transformation mapping a steady laminar boundary layer on an axisymmetric body to an equivalent 2-D flow, with the sharp-cone closed-form ratios: laminar boundary-layer thickness, wall shear and skin friction on a cone sqrt(3) times the flat-plate values at the same running length, plus the transformed coordinate machinery for slender axisymmetric bodies.

(a) Zero-owner greps across the whole skills/ tree (quoted):
- `grep -ril "mangler" skills/` -> rc=1, zero files
- `grep -rilE "axisymmetric body|bodies of revolution" skills/` -> hits only stagnation-flow-boundary-layer (axisymmetric Homann stagnation point, leading-edge nose sizing) and no cone-surface or transform content
Corpus: "mangler" 0 tasks; the single cone task in the corpus is w28-hypersonic-flow-2 (Newtonian cone axial force, expected_skill hypersonic-flow), pressure side not viscous side.

(b) Quoted sibling fence: flat-plate-skin-friction-heating SKILL.md owns the 2-D plate station Cf: "Use when you must estimate the surface skin friction heating on a flat plate or vehicle skin at high Mach... local skin friction coefficient and Reynolds-analogy heat transfer coefficient... for a laminar or turbulent boundary layer" with the flat-plate forms Cf = 0.664 / sqrt(Re_star) laminar and Cf = 0.0592 / Re_star^0.2 turbulent. stagnation-flow-boundary-layer SKILL.md owns the low-speed stagnation point only ("size the laminar boundary layer, wall shear and skin friction at a low-speed 2-D or axisymmetric stagnation point or leading edge"). Neither leaf produces cone-surface or general-axisymmetric laminar values; the Mangler transform is a geometry mapping with no thermodynamic or compressibility content, distinct from the wave-42 van-Driest-II/Chapman-Rubesin decline (compressible-Cf function dup of flat-plate-skin-friction-heating). Flagged LOW because that wave-42 adjudication shows the adjudicator fences Cf-producing neighbors to flat-plate-skin-friction-heating; a spec-time boundary sentence stating the leaf consumes sibling Cf machinery and outputs only the transform ratios mitigates it.

(c) Standards-map id that EXISTS: line 171 naca-tr-824, boundary-layer pack convention (same grep as GO-2/GO-3).

(d) Published deterministic anchor: Mangler transformation of the steady laminar boundary-layer equations onto an axisymmetric body into a 2-D equivalent flow; for the sharp cone (radius proportional to running length) the exact closed-form ratios delta_cone = sqrt(3) delta_plate and tau_w,cone = sqrt(3) tau_w,plate at equal running length. Source: Schlichting, Boundary-Layer Theory (boundary layers on bodies of revolution, Mangler transformation); White, Viscous Fluid Flow (Mangler transformation section of the boundary-layer chapter).

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "apply the mangler-transformation to the laminar boundary layer on the sharp cone: report the cone boundary-layer thickness and skin friction versus the flat-plate values at the same running length with the sqrt-3 cone factor"
2. "transform the axisymmetric-body boundary layer into the equivalent 2-D flow with the mangler-transformation coordinate mapping and compute the cone wall-shear ratio against the flat plate for the laminar case"
Tokens mangler-transformation, cone-boundary-layer, axisymmetric-body-boundary-layer, cone-wall-shear-factor exist nowhere today.

(f) Tag discipline: proposed tags mangler-transformation, cone-boundary-layer, axisymmetric-body-boundary-layer, laminar-cone-factor, body-of-revolution-bl. No bare cone, no bare transformation, no bare boundary-layer.

## Declines (one-line reasons)

| Candidate seam | One-line reason |
|---|---|
| theodorsen-oscillating-airfoil standalone | Function dup: Theodorsen C(k) Bessel machinery is already implemented and owned inside flutter-speed-prediction (V-g owner), the w21 corpus tasks already route Theodorsen content there, and a standalone leaf has no separated purpose |
| e-n-method transition prediction | Not closed form (needs Tollmien-Schlichting growth integration over a stability database) and the transition sibling explicitly fences it: "no Tollmien-Schlichting wave-growth integration; the Michel criterion replaces an eN envelope" |
| colburn-analogy / j-factor heat transfer | Function dup: flat-plate-skin-friction-heating already owns the Reynolds-analogy heat transfer coefficient h_c = 0.5 Cf rho_star U_e Cp at the documented Pr 0.71, Colburn St Pr^2/3 = Cf/2 is the same transfer rewritten |
| compressible-boundary-layer-transforms (Illingworth-Stewartson, van-Driest-II, Chapman-Rubesin) | Standing wave-42 decline: function dup of the flat-plate-skin-friction-heating Eckert reference-temperature method |
| laminar thermal-boundary-layer Nu correlation (Pohlhausen) | Same heat-transfer-analogy dup as colburn above, flat-plate-skin-friction-heating owns the laminar and turbulent plate flux |
| turbulent-BL-integral (Head entrainment, Truckenbrodt) | Standing wave-41/42 decline, turbulent-BL-integral not reopened; boundary-layer-separation owns the Stratford turbulent-separation side |
| thwaites-method standalone / Pohlhausen laminar integral | Dup of the Thwaites machinery embedded in boundary-layer-separation and boundary-layer-transition (wave-42 Pohlhausen-dup adjudication) |
| roughness and trip-strip effects on transition | Owned: rough-wall-skin-friction carries the trip-criterion verdict and trip-strip sizing (TRIP_RE_K = 600) |
| attachment-line contamination (Poll criterion) | Genuine zero-owner mechanism but corpus pull is thin for AeroSkills demand, and stagnation-flow-boundary-layer already tags attachment-line flow for the nose region |
| turbulent flat-plate Cf refinements (Schoenherr, Prandtl-Schlichting) | Owned at the needed level: boundary-layer-theory (1/7-power law) plus parasite-drag (0.455 / (log10 Re)^2.58) |
| supersonic cone flow (Taylor-Maccoll, Kopal tables) | Standing wave-42 decline: ODE integration, not closed form |
| tangent-wedge / tangent-cone methods | Standing wave-41/43 decline, not reopened |
| SWBLI / real-gas / hypersonic-viscous-interaction | Standing wave-41/43 declines, not reopened |
| supersonic-linearized-theory (Ackeret) | Now OWNED by wave-44 ackeret-linearized-supersonic, vein closed by ownership |
| hypersonic similarity parameter (van Dyke similitude) | Thin scaling law adjacent to hypersonic-flow (Newtonian forces) and transonic-similarity (which owns the similarity-parameter slot), zero corpus demand |
| second-order supersonic airfoil theory (Busemann) | Thin refinement of the owned ackeret leaf, no separated corpus demand |
| von Karman slender-body wave drag for general area distributions | Adjacent function of wave-drag-area-rule (Sears-Haack drag-area formulas, corpus tasks wd1/wd2 already route slender-body wave drag there), zero corpus demand |
| bow-shock inverse (Mach from measured standoff) | Inverse of the owned bow-shock-standoff Billig correlation, no separated purpose |
| Kantrowitz supersonic-inlet-starting | Owned content: the kantrowitz token matches propulsion/ramjet/ramjet-inlet logic; inlet family home is propulsion, not aerodynamics/high-speed |
| supersonic inlet multi-shock / mixed-compression systems | Assembly of owned normal-shock + oblique-shock leaves plus the propulsion inlet owner |
| shock-shock interference patterns (Edney types) | Classification and numerical in nature, no closed-form anchor |
| base drag | Empirical correlations only, no canonical closed-form anchor in the required book set; parasite-drag buildup owns the CD0 context |
| interference drag standalone | parasite-drag owns the interference-factor Q in the buildup; standalone interference drag is empirical |
| vortex-induced vibration / Strouhal lock-in | Anchors are Blevins-type semi-empirical amplitude models outside the required canonical book set, aerospace corpus demand nil, no clean closed form |
| panel flutter | Needs plate structural modes plus Galerkin, not clean closed-form aerodynamics; hybrid with the structures family |
| control-surface (3-DOF) flutter | Adjacent dup of the flutter-speed-prediction V-g machinery with one added DOF, thin corpus |
| whirl flutter | Standing wave-42 decline, not reopened |
| asymptotic suction / LFC-NLF laminarization | Standing wave-41/43 decline, LFC/NLF adjacency, not reopened |
| reflected-shock-tube-wall unsteady interaction | Standing wave-43 decline: HIGH overlap with the owned shock-tube leaf |
| continuous-turbulence PSD gust loads (Dryden / von Karman spectra) | Family home is structures/loads (random-vibration-analysis and gust-maneuver-loads own the PSD load machinery), not aerodynamics section theory |

## Closed veins (this probe)

- high-speed: single-wave gas dynamics closed by ownership (normal-shock, oblique-shock, prandtl-meyer, isentropic-flow-relations, fanno-flow, rayleigh-flow, shock-tube, regular-shock-reflection); supersonic section aero closed (shock-expansion-airfoil for diamond sections, ackeret-linearized-supersonic for thin sections); hypersonic forces closed (hypersonic-flow Newtonian, hypersonic-piston-theory, bow-shock-standoff); heating closed (aerodynamic-heating stagnation, flat-plate-skin-friction-heating plate, compressible-couette-flow gap); transonic wave drag closed (supercritical-airfoil, swept-wing-aerodynamics, transonic-similarity, wave-drag-area-rule).
- boundary-layer: attached laminar/turbulent flat plate closed (boundary-layer-theory); separation and transition closed (boundary-layer-separation, boundary-layer-transition); roughness and trips closed (rough-wall-skin-friction); stagnation closed (stagnation-flow-boundary-layer); low-Re and unsteady Stokes closed (stokes-creeping-flow-drag, unsteady-laminar-stokes-layers); compressible plate Cf and analogy closed by the wave-42 van-Driest adjudication against flat-plate-skin-friction-heating.
- aeroelasticity: static divergence, classical flutter (Theodorsen + V-g), discrete-gust indicial response, and added-mass/apparent-mass all owned by the four existing leaves; gust frequency-domain (Sears) was the one unowned named function and is GO-1.

## Notes

- Corpus baseline: eval/hit1-corpus.yaml = 1238 tasks; 2 per leaf; the four GO candidates need 8 new tasks at the corpus merge, ids following the wave fragment convention, each worded per (e) so the wave-22 stealer-tag lesson applies (boundary-layer-theory momentum-thickness and xfoil-analysis polar tags are the live steal risks for GO-2 wording).
- All four candidates map to existing standards-map ids only (far-25, cs-25, naca-tr-824); no standards-map.yaml edit needed.
- No em dashes in this receipt.
