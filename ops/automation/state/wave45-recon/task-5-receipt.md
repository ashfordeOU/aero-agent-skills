# WAVE-45 FLIGHT-TEST-OPERATIONS PROBE RECEIPT (task-5, whole family FRESH)

HEAD `5cc8fef3`, read-only probe except this receipt. Family = flight-test-operations.
Wave history: wave-42 13/14 saturation, wave-43 +3, wave-44 +1 (vmcg-determination,
envelope). Brief mandate: envelope + performance measurement/planning gaps, clean
deterministic reduction math only, heavy saturation expected, receipts over lists.

## Count and enumeration

`find skills/flight-test-operations -mindepth 3 -name SKILL.md` returns exactly 48
leaves (matches the 48 baseline; per-pack counts at this HEAD):

- envelope 13: buffet-boundary-testing, envelope-expansion, flight-loads-survey,
  high-angle-of-attack-testing, icing-flight-test, load-factor-envelope,
  spin-testing, stall-characteristics-testing, structural-coupling-test, v-speeds,
  vmc-determination, vmcg-determination (wave-44), vmu-determination.
- flutter 4: flight-vibration-survey, flutter-testing, ground-vibration-testing,
  limit-cycle-oscillation.
- performance 17: accelerate-stop-distance, climb-performance-flight-test,
  cruise-performance-flight-test, engine-failure-takeoff-flight-test,
  engine-flight-test, fuel-jettison-flight-test, glide-flight-test,
  in-flight-engine-relight-test, landing-distance-determination,
  level-acceleration-test, rotorcraft-autorotation-flight-test,
  rotorcraft-forward-flight-climb-test, rotorcraft-forward-flight-performance-test,
  rotorcraft-height-velocity-diagram-test, rotorcraft-performance-flight-test,
  stall-speed-determination, takeoff-distance-determination.
- planning 9: flight-test-data-reduction, flight-test-instrumentation,
  flight-test-planning, flight-test-safety, noise-certification-test,
  pcm-telemetry-decommutation, position-error-calibration, telemetry-data-acquisition,
  test-point-matrix-design.
- stability 4: control-force-flight-test, dynamic-stability-flight-test,
  lateral-directional-stability-flight-test, static-stability-flight-test.
- uas 1: part107-sora.

Total 13+4+17+9+4+1 = 48. Enumerated list above is authoritative for this receipt
(planning now carries 9 leaves, performance 17; the 48-leaf total matches the brief).

## Verdict

1 GO candidate: `vmcl-determination` (envelope pack, VMC family landing-leg).
Heavy saturation confirmed across the whole family. The measurement-side seam has
thinned to the last unfilled VMC-family regulatory leg: FAR 25.149 defines four
distinct minimum-control-speed legs; three are now owned (airborne takeoff-config
VMC in vmc-determination, ground VMCG in vmcg-determination, and the rotation/unstick
boundary in vmu-determination is 25.107, not 25.149), while the approach/landing leg
VMCL (25.149(f)) and the 3+ engine second-failure leg VMCL-2 (25.149(g)) have zero
owner, zero fence, zero corpus presence anywhere in skills/ or eval/. Wave-44's "do
NOT also build Vmcl" (wave44-continuation-brief.md:42, wave44-leaf-plan.md:57,158)
was wave-44 scope discipline: vmcg was that wave's single VMC-family build, chosen
over vmcl, with no dead-end rationale on the record. VMCL is the fresh wave-45 find;
after it the VMC-family vein closes. No performance-pack GO: every deterministic
performance reduction seam (climb, cruise, field length, energy, engine, rotorcraft)
is owned; remaining lookalikes are config variants of owned leaves or
deterministic-light demonstrations.

## Ranked GO candidates

### GO-1 (rank 1): flight-test-operations/envelope/vmcl-determination (suggested leaf name: vmcl-determination)

Reduce the approach-and-landing minimum-control-speed demonstration runs of a
transport airplane to VMCL in the spirit of the FAR/CS 25.149(f) method, summary-only:
build the asymmetric yawing moment from the critical-engine cut during the approach,
solve the rudder-authority-limited and 150 lbf pedal-force-limited airspeeds at the
landing configuration with go-around thrust on the operating engines, classify each
approach-cut run by the bank-5-degree and 20-degree-heading-change control criteria,
correct the demonstrated speeds to the reference condition, and for three-plus-engine
airplanes add the VMCL-2 second-cut leg (25.149(g)) with the three-degree-path thrust
to go-around thrust change. Produces the predicted and demonstrated VMCL, the
run-classified verdict, and the margin against the operating approach speed set.

(a) Zero-owner grep, whole skills/ tree:

    $ grep -rin 'vmcl' skills/
    (no matches, exit 1)

    $ grep -rwin 'vmca' skills/
    (no matches, exit 1)

    $ grep -rin 'vmcl' eval/hit1-corpus.yaml
    (no matches, exit 1)

Zero hits across every skills/ leaf, script, and packed router, and zero hits in the
1238-query eval corpus. The FAA-leg acronyms (VMCL, VMCA) appear nowhere in the
corpus; the existing leaves speak only of "Vmc" (vmc-determination, airborne
takeoff-config) and "Vmcg" (vmcg-determination). Wave-44's own prep grep in
state/wave44-specs/vmcg-determination.md line 79 records the same:
"vmcg|vmcl|ground-minimum-control" returns vmcl count 0.

(b) Quoted sibling fence from nearest owning SKILL.md. Nearest owner
vmc-determination SKILL.md, "Related leaves" block (lines 177-189):

    - flight-test-operations/envelope/v-speeds: the V-speed set beside
      which the Vmc result sits.
    - flight-mechanics/performance/oei-climb-gradient: the engine-out
      climb performance sibling; this leaf does not compute climb
      gradients.
    - vehicle-design/sizing/control-surface-sizing: sizing the rudder area
      from the yaw moment requirement, upstream of this check.
    - flight-mechanics/stability-control/control-surface-effectiveness:
      elevator hinge moments and stick force, out of scope here.
    - flight-test-operations/envelope/stall-characteristics-testing:
      stall demonstration testing behind the stall-protection guard.

The air-leg owner lists five neighbors and claims no approach/landing-configuration
leg. Second fence, vmcg-determination SKILL.md Related leaves first bullet (the VMC
family organizes by leg, air and ground claimed, landing unclaimed):

    - flight-test-operations/envelope/vmc-determination: the airborne
      minimum control speed demonstration with the windmilling drag
      contribution and the air-side stall protection guard; this leaf owns
      the ground leg only.

Third fence, pack router skills/flight-test-operations/SKILL.md line 140 and line
166: "Vmc determination questions ... route to the vmc-determination sub-skill" and
"Ground-leg minimum-control-speed questions ... route to the envelope
vmcg-determination sub-skill, not the air-side vmc-determination." Air leg and ground
leg are routed; no router row names an approach/landing control-speed leg.

(c) Standards-map id that EXISTS:

    $ grep -n '^  - id: far-25\|^  - id: cs-25' standards-map.yaml
    16:  - id: far-25
    27:  - id: cs-25

Both far-25 and cs-25 exist in standards-map.yaml (30 ids total), matching the
STANDARDS-REF pattern of every sibling leaf (vmc-determination and vmcg-determination
each carry far-25 + cs-25 reference-only).

(d) Published deterministic anchor. FAR 25.149(f), verified text from the eCFR
versioner API (2025-11-20 edition, fetched this probe):

    "(f) VMCL, the minimum control speed during approach and landing with
    all engines operating, is the calibrated airspeed at which, when the
    critical engine is suddenly made inoperative, it is possible to
    maintain control of the airplane with that engine still inoperative,
    and maintain straight flight with an angle of bank of not more than 5
    degrees. VMCL must be established with: (1) the airplane in the most
    critical configuration (or, at the option of the applicant, each
    configuration) for approach and landing with all engines operating;
    (2) the most unfavorable center of gravity; (3) the airplane trimmed
    for approach with all engines operating; (4) the most favorable
    weight, or, at the option of the applicant, as a function of weight;
    (5) for propeller airplanes, the propeller of the inoperative engine
    in the position it achieves without pilot action ...; and (6)
    go-around power or thrust setting on the operating engines."

And 25.149(g) defines VMCL-2 for airplanes with three or more engines: a second
critical engine cut during approach with one engine already inoperative, the
operating engines at three-degree-path thrust, then "the power or thrust on the
operating engine(s) rapidly changed ... to go-around power" (25.149(g)(6)-(7)).
Deterministic content is real and distinct: the closed-form asymmetric-yaw balance
and rudder-authority/150 lbf pedal-force-limited speed solve (the family forms
already implemented in vmc-determination and vmcg-determination, with the landing
configuration, approach trim, go-around thrust, and most-favorable-weight condition
set of 25.149(f)), plus run classification of approach cuts against the bank and
20-degree-heading criteria of 25.149(b)/(d), and for the (g) leg a second-cut thrust
sequence. CS-25.149(f)/(g) mirrors (verify against current EASA text at spec time,
per sibling convention). AC 25-7D documents the demonstration method; no proprietary
text needed, FAR text is public domain, summary-only per standards-map.yaml.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:

    Q1: "reduce the landing-configuration VMCL demonstration runs to the
        approach minimum-control-speed after the critical-engine cut with
        go-around thrust"
    Q2: "VMCL-2 second-critical-engine cut on approach, three-degree path
        thrust change to go-around, directional control speed reduction"

Distinctive hyphenated tokens: landing-configuration, critical-engine-cut,
go-around-thrust, minimum-control-speed (with the landing modifier, matching the
vmcg precedent ground-minimum-control-speed). Any query carrying the vmcl token
lands uniquely: vmcl appears nowhere else in skills/ or the eval corpus.

(f) No generic single-word tag overlap. Proposed tags:
[vmcl-determination, landing-minimum-control-speed, approach-configuration-control,
go-around-thrust, critical-engine-cut, most-favorable-weight, second-engine-cut].
Sibling tags are all hyphenated multi-word family vocabulary (vmc-determination:
[minimum-control-speed, critical-engine, rudder-pedal-force, asymmetric-yawing-moment,
engine-inoperative-flight-test, rudder-authority]; vmcg-determination:
[ground-minimum-control-speed, nosewheel-steering-authority, steering-cutout-speed]).
No bare single-word tags (speed, stall, engine, rudder) are added.

Spec-time cautions carried forward (mirror wave-44 handling): (1) verify the body of
vmc-determination before spec'ing so the shared closed-form core is reused, not
duplicated, and the distinct content is the 25.149(f)/(g) condition set plus run
classification; if genuine overlap is judged at spec time, decline and rely on the
wave-45 viable pool. (2) Token discipline per the wave-44 FTO-3762 steal lesson:
description front and tags must carry vmcl/landing/go-around qualifiers, never bare
minimum-control-speed or vmc tokens, or the vmc-determination leaf steals the hit.

## Declines table

| Candidate (seam probed) | One-line reason |
|---|---|
| wat-limit / climb-limit takeoff-weight curve (perf) | Downstream AFM analysis of corrected gradients already owned by climb-performance-flight-test (25.121 margin checks); no new measurement or closed-form reduction. |
| time-to-climb / service and absolute ceiling (perf) | Owned in full by climb-performance-flight-test (ceiling thresholds, trapezoid time-to-climb integration). |
| landing climb / approach climb config gradient checks (perf) | climb-performance-flight-test gradient_from_roc plus margin machinery already consumes any 25.119/25.121(d) requirement constant; config variant, no new reduction. |
| measured stall-run reduction to Vs1g per 25.103 (perf) | sqrt-weight correction and margin owned by stall-speed-determination; matrix, entry, warning, recovery owned by stall-characteristics-testing; residual math is averaging plus the same correction. |
| high-speed dive demonstration VDF/MDF (envelope) | Deterministic-light (max-hold recording and generic air-data Mach reduction); flutter-testing owns the VD relation and v-speeds owns the speed-set guards. |
| VMCA at altitude / OEI cruise control speed (envelope) | Config variant of vmc-determination's method without a distinct regulatory paragraph (25.149(c) fixes the takeoff-configuration condition set). |
| gust-loads flight test response reduction (envelope) | Discrete-gust design/analysis owned analytically by structures gust-maneuver-loads (25.341); no deterministic 25.20x flight-test reduction anchor. |
| artificial ice-shape performance reduction (envelope) | icing-flight-test owns the App C classification, campaign planning and ice-protection test point screen; aero-degradation reduction is analysis-domain with no closed-form anchor. |
| endurance / holding fuel performance (perf) | Not a FAR/CS 25 certification reduction item; cruise-performance-flight-test owns the fuel-flow and range machinery. |
| crosswind takeoff/landing limit demonstration (perf) | No deterministic closed-form method in the 25-series; operational demonstration, pass/fail recording only. |

## Closed veins

- VMC family (25.149): air leg (vmc-determination), ground leg (vmcg-determination)
  built; landing leg VMCL and second-failure leg VMCL-2 are this receipt's GO. After
  vmcl-determination the family vein closes; do not re-probe for further 25.149 legs.
- Climb (25.115/25.119/25.121): ROC measurement, pressure-to-geometric conversion,
  weight/density corrections, ceilings, time to climb, gradient margins all inside
  climb-performance-flight-test. Closed.
- Stall speed (25.103/25.207): predictor (stall-speed-determination) plus matrix,
  warning, recovery (stall-characteristics-testing) split is complete. Closed.
- Takeoff/landing field length (25.109/25.113/25.125): all-engine stop
  (accelerate-stop-distance), OEI continued plus balanced V1
  (engine-failure-takeoff-flight-test), all-engine distance (takeoff-distance-
  determination), landing (landing-distance-determination). Analytical sibling
  balanced-field-length lives in flight-mechanics. Closed.
- Envelope expansion and speed set (25.335/25.253/25.107): corner speed, expansion
  steps, Vref/V2/Vr ordering, Vno/Vne guard, Vmu rotation boundary all owned. Closed.
- Rotorcraft performance: autorotation, H-V diagram, forward-flight climb,
  forward-flight level performance, hover figure of merit and ceilings all owned.
  Closed.
- Flutter and loads: 4 flutter leaves plus structural-coupling-test and
  flight-loads-survey (strain calibration, symmetric and rolling maneuver survey)
  complete. Closed.
- Planning/measurement infrastructure: instrumentation, DAQ/telemetry/PCM
  decommutation, generic data reduction, PEC, test-point-matrix design, safety,
  program planning, noise all owned. Closed.

## Read-only verification note

Only this file was written: ops/automation/state/wave45-recon/task-5-receipt.md.
No git add/commit/push, no edits to skills/, eval/, docs/, Makefile, scripts, or
ops/automation briefs, no standards-map.yaml changes. No em dashes in this receipt.
Probe was fresh at HEAD 5cc8fef3: leaves re-read (climb-performance-flight-test,
stall-speed-determination, stall-characteristics-testing, vmc-determination,
vmcg-determination, v-speeds, engine-failure-takeoff-flight-test, pack router),
whole-tree ownership greps run, FAR 25.149 text verified from the eCFR API.
