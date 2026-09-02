---
name: ndt-method-selection
description: "Use when you must select a non-destructive testing (NDT) method for an aerospace part from its defect class and material: determine whether the defect is surface, near-surface, or internal, classify the material as ferromagnetic, non-ferromagnetic, or non-conductive, and pick among radiography (RT), ultrasonic (UT), eddy current (ET), liquid penetrant (PT), and magnetic particle (MT) by sensitivity with cost as secondary reporting. Produces the recommended method, the alternates, and the selection rationale that gate the NDT inspection planning for special processes. Trigger: non-destructive testing, ndt, radiography, ultrasonic, eddy current, penetrant, magnetic particle, defect class, ferromagnetic."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [ndt, radiography, ultrasonic, eddy, current, penetrant, magnetic, particle, ferromagnetic, conductive]
  version: 0.1.0
  author: Aero Agent Skills
---

# NDT Method Selection (manufacturing-quality/ndt/ndt-method-selection)

Use when the task is choosing a non-destructive testing method for an
aerospace part: defect class (surface, near-surface, internal) and
material class (ferromagnetic, non-ferromagnetic, non-conductive) drive
the applicable method set, and sensitivity ranks the pick.

## Domain quick reference

- Methods: RT radiography, UT ultrasonic, ET eddy current, PT liquid
  penetrant, MT magnetic particle.
- Defect classes: surface, near-surface, internal.
- Material classes: ferromagnetic, non-ferromagnetic, non-conductive.
- Decision table (module-level DECISION_TABLE): internal maps to RT,
  UT; near-surface maps to ET, UT; surface maps to MT, PT on
  ferromagnetic, ET, PT on non-ferromagnetic, PT on non-conductive.
- Physical constraints: eddy current needs a conductive material,
  magnetic particle needs a ferromagnetic material, liquid penetrant
  needs a non-porous surface and works on all three material classes.
- Sensitivity rank (5 highest): UT 5, RT 4, ET 4, MT 3, PT 3.
- Cost rank (1 cheapest, reporting only): RT 4, UT 3, ET 2, MT 2,
  PT 1. Cost never overrides sensitivity.
- Tie-break: equal sensitivity prefers the later method in the fixed
  order RT < UT < ET < MT < PT; the only reachable tie is MT vs PT,
  which picks PT (also the alphabetically-later method).
- AS9100 frames NDT as a special process; NDT personnel follow common
  aerospace practice (level certification, written procedures, records)
  without reproducing clause text here.

## Workflow

1. Classify the defect location: surface, near-surface, or internal.
2. Classify the material: ferromagnetic, non-ferromagnetic, or
   non-conductive.
3. Call applicable_methods(defect_class, material) for the sorted
   method list valid for the combination.
4. Rank the applicable methods with sensitivity_rank and call
   select_method(defect_class, material) for the top pick, the
   alternates, and the rationale.
5. Report cost_rank(method) as secondary information only; it never
   overrides sensitivity.
6. Validate inputs first: an unknown defect class or material class
   raises ValueError from applicable_methods and select_method.

## Pitfalls

- Eddy current on a non-conductive material: ET needs conductivity;
  on a composite use PT for surface defects.
- Magnetic particle on a non-ferromagnetic part: MT needs a
  ferromagnetic material; use PT or ET instead.
- Cost as the primary driver: cost_rank is reporting only and must not
  override sensitivity in the pick.
- Surface defects do not get RT or UT: only PT, plus MT on
  ferromagnetic or ET on non-ferromagnetic material, apply.
- Tie handling: MT and PT both rank 3, so surface plus ferromagnetic
  picks PT, not MT, per the fixed tie-break order.
- Misspelled class names: an unknown class or material raises
  ValueError instead of silently returning an empty list.

## Behavior contract (gate 3)

The selection logic is exercised by the gate 3 contract test:
scripts/test_ndt_selection.py against
scripts/ndt_selection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ndt_selection.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  special-process control; the method table is common NDT methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
