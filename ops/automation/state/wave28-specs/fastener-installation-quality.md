# Wave-28 leaf spec: fastener-installation-quality (manufacturing-quality, assembly pack - NEW PACK)

- Path: skills/manufacturing-quality/assembly/fastener-installation-quality/
- Pack: assembly (NEW pack - first leaf in it; the router row path is
  manufacturing-quality/assembly/fastener-installation-quality)
- Standards ids: as9100  (Ledger Standard: as9100)
- Family: manufacturing-quality

## Claim

Verify the installation quality of aerospace structural fasteners
(bolts, Hi-Loks, rivets) during assembly: select the correct grip
length for the clamped stack from the available grip increments, check
the thread protrusion after installation, compute the clamp load from
the applied torque with the torque coefficient, verify the clamp load
and the torque scatter band against the joint allowables, check the
countersink flushness for flush-head fasteners, confirm swage-collar
engagement for lock-bolt fasteners, and classify the installation
verdict (pass, rework, or scrap) with the specific defect. Produces the
selected grip, the protrusion check, the clamp-load estimate, the
flushness and engagement checks, and the installation verdict that gate
the assembly quality assessment.

Does NOT do: analyze bearing/bypass stresses of a composite bolted
joint (structures composite-bolted-joints); screen fatigue cracks at
fastener holes (structures widespread-fatigue-damage); control
calibration or MSA (as9100 pack siblings); design the fastener pattern
or edge distances (engineering inputs here).

## Model (implement exactly)

Module constants:
- PROTRUSION_MIN_MM = 0.5, PROTRUSION_MAX_MM = 3.0 (typical thread
  protrusion band for structural bolts, labeled typical).
- THREADS_MIN = 2 (minimum full threads engaged past the nut for
  lock-bolt/collar types, labeled typical).
- K_TYPICAL = 0.2 (default torque coefficient, lubricated; input).

Inputs:
- stack_thicknesses_mm (list of floats, the clamped stack),
- available_grips_mm (list of floats, sorted grip increments),
- fastener_diameter_m (float, nominal diameter),
- applied_torque_Nm (float),
- k_factor (float, default K_TYPICAL),
- min_clamp_N (float, joint minimum required clamp),
- max_clamp_N (float, joint allowable clamp; embedment/pull-out
  limit),
- fastener_type (str in {"bolt-nut", "lock-bolt", "rivet"}),
- head_style (str in {"protruding", "flush"}),
- measured_flushness_mm (float, only for flush heads: positive =
  proud, negative = recessed),
- flushness_tolerance_mm (float, default 0.13),
- collar_engaged_threads (int or None, for lock-bolt),
- installed_torque_actual_Nm (float or None, when the actual applied
  torque is known for scatter checks).

Functions:
- select_grip(stack_thicknesses_mm, available_grips_mm) -> dict:
  total = sum(stack); choose the smallest available grip >= total;
  if none, grip = None; return {stack_total_mm, grip_mm (or None),
  protrusion_mm (grip - total when grip chosen)}.
  ValueError on empty stack, negative thickness, empty grips, grips
  not sorted ascending.
- protrusion_ok(protrusion_mm) -> bool: PROTRUSION_MIN_MM <=
  protrusion <= PROTRUSION_MAX_MM.
- clamp_load_N(torque_Nm, k_factor, fastener_diameter_m) -> float:
  torque/(k_factor*fastener_diameter). ValueError on torque <= 0,
  k_factor <= 0, diameter <= 0.
- clamp_verdict(clamp_N, min_clamp_N, max_clamp_N) -> str:
  "clamp-ok" when min <= clamp <= max, "under-clamp" when below min,
  "over-clamp" when above max. ValueError on min <= 0, max < min.
- flushness_ok(measured_mm, tolerance_mm) -> bool: abs(measured) <=
  tolerance.
- collar_engagement_ok(engaged_threads, min_threads=THREADS_MIN) ->
  bool (None input -> None). ValueError on engaged < 0.
- installation_verdict(inputs) -> dict: grip selection result, then:
  - if grip None -> verdict "rework", defect "no-grip-fits";
  - protrusion check fails -> "rework", "protrusion-out-of-band";
  - clamp verdict not ok -> "rework"/"scrap" by defect ("over-clamp"
    -> "scrap", "under-clamp" -> "rework");
  - flush head and flushness not ok -> "rework",
    "flushness-out-of-tolerance";
  - lock-bolt and collar engagement below min -> "rework",
    "collar-engagement";
  - else "pass", defect None.
  Include clamp_N, clamp verdict string, and a torque-scatter note:
  when installed_torque_actual_Nm is given, scatter_pct =
  abs(actual - applied)/applied*100 and scatter_ok = scatter_pct <=
  15.0 (typical torque scatter band, labeled typical).
ValueError on: fastener_diameter <= 0, applied_torque <= 0,
fastener_type not in the set, head_style not in the set.

## Worked example

Stack [4.0, 6.0, 4.0] mm = 14.0 mm; available grips [12.7, 15.875,
19.05] mm; D = 0.00635 m (1/4 inch); torque 24 N m; k = 0.2;
min clamp 12000 N, max clamp 25000 N; bolt-nut protruding head.
- select_grip: total 14.0; smallest grip >= 14.0 is 15.875; grip
  15.875 mm; protrusion 1.875 mm (assert within 1e-9). protrusion_ok
  True (within [0.5, 3.0]).
- clamp_load = 24/(0.2*0.00635) = 24/0.00127 = 18897.6 N (assert
  within 0.5); clamp verdict "clamp-ok".
- installation_verdict -> "pass".
- Fail cases: (a) stack [10.0, 8.0] with grips [12.7, 15.875]: total
  18.0 -> grip 19.05? no 19.05 not in list -> choose max available?
  available [12.7, 15.875]: no grip >= 18 -> grip None -> verdict
  "rework" defect "no-grip-fits". Use grips [12.7, 15.875, 19.05, 22.0]
  to make (a) pass and instead test protrusion fail with stack 15.9
  and grip 15.875 -> protrusion -0.025 -> "rework"
  "protrusion-out-of-band" (protrusion below min; treat negative as
  out-of-band by the same check). (b) torque 40 N m -> clamp 31496 N
  > max -> "scrap" "over-clamp". (c) flush head with measured
  flushness +0.22 mm, tolerance 0.13 -> "rework"
  "flushness-out-of-tolerance". (d) lock-bolt collar 1 thread ->
  "rework" "collar-engagement". (e) scatter: actual 26.4 -> scatter
  10.0% scatter_ok True; actual 30 -> 25% -> False.
- ValueErrors on torque 0, D 0, empty stack, fastener_type "screw".
Keep at least 18 test methods: grip selection boundaries (exact match,
between grips, no grip), protrusion checks, clamp load value, clamp
verdict branches, flushness, collar, each verdict/defect path, scatter,
ValueErrors.

## Corpus tasks (ids w28-fastener-installation-quality-1/2)

Distinctive tokens: fastener installation quality, grip length
selection, thread protrusion, clamp load from torque, countersink
flushness, collar engagement, Hi-Lok installation check. Avoid:
bearing and bypass stress, bolt bearing stress (structures
composite-bolted-joints); fatigue crack screening at fastener holes
(structures widespread-fatigue-damage); torque calibration (as9100
calibration-control).

1. "verify the structural fastener installation: select the grip for
   the clamped stack, check the thread protrusion, and confirm the
   clamp load from the applied torque stays inside the joint limits"
2. "inspect the Hi-Lok installation quality: check the collar
   engagement and the countersink flushness and classify the
   installation as pass rework or scrap"

## SKILL body notes

First leaf of the new assembly pack (join the pack table row and a
routing bullet in the manufacturing-quality router). Pair with
structures composite-bolted-joints (stress analysis of the same joint)
and the as9100 process-control siblings. The protrusion band, thread
count, torque coefficient, and scatter band are documented typical
values, not standard reproductions; the body must say to confirm
against the fastener manufacturer data and the governing code. AS9100
cited reference-only.
