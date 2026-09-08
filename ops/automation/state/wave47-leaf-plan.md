# Wave-47 leaf plan (ops manager, 10 whole-family FRESH probe receipts)

RECEIPTS OVER LISTS: all 10 planned leaves come from whole-family FRESH
probe receipts at HEAD a544f421/a4ae6d1e (brief commit a544f421 + sibling
doc-fix a4ae6d1e touching only the brief; skills tree byte-identical at
both). Probe run 2026-09-08 15:40-16:10 CEST: 4 primary changed-family
probes (task-0..3: FM/AV/PROP/GNC) + 6 extension probes (task-4 VD,
task-5 STRUCT, task-6 CC, task-7 SES, task-8 MQ, task-9 FTO) under the
pool-drop rule. Space-systems + aerodynamics receipts STAND from wave-46
(same-day 12:07-12:23 UTC whole-family NO_CANDIDATES; zero family changes
since — wave-46 added no space/aero leaves), per declines-stand doctrine.

## Probe outcome (10/10 receipts)

| Family (leaves) | Receipt | Verdict |
|---|---|---|
| flight-mechanics 48 | task-0 | 1 GO: rotorcraft-cyclic-pitch-trim |
| avionics 49 | task-1 | 1 GO: virtual-deadline-scheduling |
| propulsion 52 | task-2 | 1 GO: diesel-cycle (NEW reciprocating pack sibling) |
| gnc-autonomy 58 | task-3 | 4 GO: tropospheric-delay-correction, impact-angle-control-guidance, smith-predictor, h-infinity-control (4th conditional: Hit@1 margin fragile 1.5pt — spec-time hardening) |
| vehicle-design 56 | task-4 | 1 GO: component-weight-estimation |
| structures 63 | task-5 | 2 GO: unidirectional-lamina-micromechanics (strong), creep-stress-relaxation (conditional) |
| cross-cutting 56 | task-6 | NO_CANDIDATES (fresh; 5 new seams declined with receipts) |
| systems-engineering-safety 47 | task-7 | NO_CANDIDATES (saturated reaffirmed FRESH) |
| manufacturing-quality 48 | task-8 | NO_CANDIDATES (saturated reaffirmed FRESH) |
| flight-test-operations 49 | task-9 | NO_CANDIDATES (saturated reaffirmed FRESH) |
| space-systems 52 | (wave-46 task-6) | NO_CANDIDATES stands (unchanged since same-day probe) |
| aerodynamics 57 | (wave-46 task-8) | NO_CANDIDATES stands (unchanged since same-day probe) |

Planned pool = 10 (MUST land >= 10 met with zero margin by design, wave-46
precedent; 8 strong + 2 conditional carried for spec-time triage). All 12
families covered FRESH or standing same-day receipts — no family remains
to extend to. Each planned leaf carries full (a)-(f) gate evidence in its
receipt.

## Planned leaves (10), family spread, receipts cited

1. flight-mechanics/performance/rotorcraft-cyclic-pitch-trim
   (FM 48; task-0 rank 1 GO: control-channel completion of wave-46
   rotorcraft-forward-flight-flapping — steady first-harmonic flap
   equilibrium WITH longitudinal/lateral cyclic inputs + trim inversion
   (cyclic/swashplate inputs to hold target TPP attitude); sibling owns
   collective-only flap equilibrium; Johnson Helicopter Theory + Leishman
   anchors; far-29 ref-only; spec-time: fence line + router row at close)
2. avionics/fsw/virtual-deadline-scheduling
   (AV 49; task-1 rank 1 GO: EDF-VD dual-criticality schedulability —
   virtual deadlines + mode switch, Baruah et al. IEEE ToC 61(8) 2012
   anchor; next sibling of mixed-criticality-scheduling (AMC-rtb);
   do-178c ref-only; never tag bare criticality/dal/wcet)
3. propulsion/reciprocating/diesel-cycle
   (PROP 52; task-2 GO-1: compression-ignition air-standard Diesel cycle
   thermal efficiency from cutoff ratio + compression ratio + gamma;
   spark-ignition sibling of wave-46 piston-engine-cycle (Otto) — own
   constants, no avgas-only assumptions; far-33; anchor-verified eta =
   0.6137 @ r17/rc2.2 in receipt)
4. vehicle-design/sizing/component-weight-estimation
   (VD 56; task-4 rank 1 GO: class-II statistical airframe group-weight
   producer seam — Raymer/Torenbeek closed-form regressions; weight-
   estimation/mass-budget/tow-estimation consume component weights as
   inputs (fence quotes in receipt); far-25/cs-25)
5. gnc-autonomy/navigation/tropospheric-delay-correction
   (GNC 58; task-3 GO-1: Saastamoinen tropospheric slant delay — next
   sibling of wave-46 ionospheric-delay-correction; per-source delay
   model seam; closed-form, deterministic)
6. gnc-autonomy/guidance/impact-angle-control-guidance
   (GNC 58; task-3 GO-2: impact-angle-constrained guidance law with
   closed-form identity (e.g. biased PN / trajectory shaping)
   distinguishable from impact-time-control-guidance)
7. gnc-autonomy/control/smith-predictor
   (GNC 58; task-3 GO-3: Smith predictor for time-delayed plants —
   dead-time compensation closed-form; sibling of pid-control-design /
   digital-control-design fences)
8. gnc-autonomy/control/h-infinity-control
   (GNC 58; task-3 GO-4 CONDITIONAL: H-infinity loop shaping / mixed-
   sensitivity S/KS design — conditional on spec-time Hit@1 query
   hardening; drop if margin cannot be lifted above ~3pt)
9. structures/composites/unidirectional-lamina-micromechanics
   (STRUCT 63; task-5 GO-1 strong: rule-of-mixtures + Halpin-Tsai +
   Voigt/Reuss/Hashin-Shtrikman bounds predicting lamina E1/E2/nu12/G12
   from fiber/matrix constituents; laminate-stiffness consumes those as
   inputs; cmh-17 ref-only; Jones/Halpin-Tsai/Hashin anchors)
10. structures/materials/creep-stress-relaxation
    (STRUCT 63; task-5 GO-2 CONDITIONAL: stress relaxation under creep —
    drop if the deterministic-anchor gate cannot be held at spec time)

## Spec phase order (batches <=4 concurrent)

Batch A (anchor-verified receipts): 1 rotorcraft-cyclic-pitch-trim,
2 virtual-deadline-scheduling, 3 diesel-cycle, 4 component-weight-
estimation.
Batch B: 5 tropospheric-delay-correction, 6 impact-angle-control-guidance,
7 smith-predictor, 9 unidirectional-lamina-micromechanics.
Batch C: 8 h-infinity-control (conditional — hardened Hit@1 or DROP),
10 creep-stress-relaxation (conditional — anchor gate or DROP).

## Close-out notes

- New pack? No (all 10 land in existing packs).
- Router rows to add at close: FM rotorcraft guidance bullet +
  rotorcraft-forward-flight-flapping fence add; avionics fsw row +
  real-time-scheduling fence add; propulsion reciprocating diesel row +
  piston-engine-cycle fence add; VD sizing row + weight-estimation fence
  add; GNC navigation/guidance/control rows + ionospheric-delay /
  impact-time-control / pid fences; STRUCT composites row + laminate-
  stiffness fence add + materials row.
- Ledger rows 636-645 at creation, rated >= 9.5 in-turn.
- Corpus merge 1286 + 2N (N = landed leaves).
