---
name: aeroelastic-analysis
description: "Use when determine aeroelastic stability margins for aerodynamic surfaces
  on a launch vehicle or atmospheric segment under ECSS-E-ST-32C clause 4.6.2.17:
  categorize each surface as flutter-critical or divergence-critical, compute the
  flutter speed margin and divergence speed margin against the design envelope, verify
  each margin exceeds the 15 % required clearance, evaluate frequency separation
  between structural eigenfrequencies and aerodynamic forcing, and flag any surface
  where flutter speed, divergence speed, or frequency separation falls short of the
  required threshold. Trigger: ecss, e-st-32c, aeroelastic, flutter, divergence,
  dynamic-response, frequency-separation, launch-vehicle-structures."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32c, aeroelastic, flutter, divergence, dynamic-response, frequency-separation, launch-vehicle-structures]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Aeroelastic Analysis (space-systems/ecss/aeroelastic-analysis)

Use when the task is the aeroelastic stability and response assessment of
ECSS-E-ST-32C clause 4.6.2.17 — determining flutter speed margin and
divergence speed margin for each aerodynamic surface of a launch vehicle
or atmospheric segment, checking frequency separation between structural
eigenmodes and aerodynamic forcing, and flagging surfaces that fall short
of any required clearance.

## Domain quick reference

- Clause 4.6.2.17 addresses two primary aeroelastic instability mechanisms
  for surfaces operating in the atmosphere: flutter (a dynamic instability
  arising from the coupling of aerodynamic lift and moment forces with
  the elastic and inertial properties of the structure, which can lead to
  diverging oscillations) and divergence (a static instability in which
  aerodynamic loads produce structural deformation that amplifies the
  forcing beyond what the restoring elastic stiffness can arrest).
- Both instabilities are governed by a speed margin requirement: the
  predicted flutter onset speed and the predicted divergence speed must
  each exceed the design equivalent airspeed (VD) by at least 15 %. A
  surface meeting both thresholds clears the aeroelastic speed envelope;
  any surface below either threshold is a finding and must be redesigned
  or its design speed reduced.
- A third criterion guards against resonant coupling between a structural
  eigenfrequency and the dominant aerodynamic forcing frequency at
  maximum dynamic pressure. The fractional separation —
  |f_struct − f_aero| / min(f_struct, f_aero) — must be at least 10 %.
  A surface with adequate speed margins but insufficient frequency
  separation is still a coupled-aeroelastic-risk finding.
- Maximum dynamic pressure (max-Q) is the critical trajectory point.
  Flutter and divergence speeds must be checked at max-Q conditions
  (density, Mach number, and equivalent airspeed) and not solely at
  sea-level conditions.
- Four regime labels are used in this leaf: stable (all three criteria
  met), flutter-risk (flutter margin violated), divergence-risk
  (divergence margin violated), coupled-aeroelastic-risk (multiple
  margins violated, or frequency separation alone violated while speed
  margins are adequate).

## Workflow

1. Inventory all aerodynamic surfaces on the vehicle that experience
   significant aerodynamic loading during atmospheric flight: fins, grid
   fins, fairings, control surfaces, protruding brackets, and any
   structural panel with a non-negligible aerodynamic pressure
   coefficient. Assign each surface a name and record its design speed
   (VD), the analysis-predicted flutter onset speed, the
   analysis-predicted divergence speed, the lowest structural elastic
   eigenfrequency (from the structural finite-element model), and the
   dominant aerodynamic forcing frequency at max-Q (from the unsteady
   aerodynamic model or wind-tunnel data).
2. For each surface compute the flutter speed margin:
   margin = (V_flutter − VD) / VD. A result below 0.15 is a finding.
3. For each surface compute the divergence speed margin:
   margin = (V_div − VD) / VD. A result below 0.15 is a finding.
4. For each surface compute the frequency separation:
   sep = |f_struct − f_aero| / min(f_struct, f_aero). A result below
   0.10 is a finding even when both speed margins pass.
5. Categorize each surface using the regime labels: stable (all criteria
   met), flutter-risk, divergence-risk, or coupled-aeroelastic-risk.
   A surface is not aeroelastically compliant until it reaches the
   stable category.
6. Aggregate the per-surface findings into an assessment report. The
   vehicle is aeroelastically compliant for the atmospheric-flight
   phase only when every surface in the inventory is in the stable
   category.

## Pitfalls

- Checking flutter and divergence speed margins only at sea-level
  conditions and reading a pass — max-Q typically occurs at altitude
  where density and Mach number differ from sea level, and the flutter
  speed envelope must span the full trajectory.
- Treating flutter risk and divergence risk as independent findings when
  both margins are violated on the same surface — their combined
  presence indicates a coupled structural–aerodynamic interaction that
  is not adequately described by either single-mode margin alone.
- Using structural frequencies from the fixed-base finite-element model
  without accounting for propellant mass variation — fuel depletion
  shifts eigenfrequencies during flight, and the worst-case
  aeroelastic coupling may occur mid-trajectory rather than at liftoff
  or engine cutoff.
- Reading a surface with inadequate frequency separation as compliant
  because its speed margins are both above threshold — the frequency
  criterion is a separate gate; a near-resonant condition between a
  structural mode and aerodynamic forcing can produce large
  aeroelastic response amplitudes even when flutter and divergence
  speed margins are satisfied.
- Omitting the divergence check for stiffness-dominated surfaces on the
  assumption that flutter governs — on surfaces with high torsional
  stiffness relative to bending stiffness, divergence can be the
  critical instability and may occur at a lower speed than flutter.

## Behavior contract (gate 3)

The flutter margin, divergence margin, frequency separation, and regime
categorization logic is exercised by the gate 3 contract test:
scripts/test_aeroelastic_analysis.py against
scripts/aeroelastic_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_aeroelastic_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the standard and
  clause as the anchor; paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
