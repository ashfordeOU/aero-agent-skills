---
name: fire-protection-sizing
description: "Use when you must size the aircraft fire protection extinguishing agent: fix the protected zone (Class C cargo compartment or powerplant fire zone), take zone free volume and agent concentration by volume, compute total-flooding agent mass and closure check from agent vapor specific volume at discharge temperature, roll up installed agent from bottle and shot count, and set discharge nozzle count from zone coverage. Produces the required agent mass per shot, the installed agent mass, the closure fraction, the nozzle count, and a coverage verdict that gate the layout (FAR 25.851, 25.855, 25.1191 context). Trigger: extinguishing agent mass, total flooding agent, class C cargo compartment, powerplant fire zone, agent bottle sizing, discharge nozzle count."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [fire-protection-sizing, extinguishing-agent-mass, total-flooding-agent, cargo-compartment-fire, powerplant-fire-zone, fire-extinguisher-bottle-sizing]
  version: 0.1.0
  author: AeroSkills
---

# Fire Protection Extinguishing Agent Sizing (vehicle-design/sizing/fire-protection-sizing)

Use when you must size the aircraft fire protection extinguishing agent
at the conceptual level for a protected compartment: the total-flooding
agent mass from the zone free volume and the design agent concentration
by volume, the concentration closure check, the installed agent rollup
from the bottle and shot count, and the discharge nozzle count from the
zone coverage. This leaf implements the standard total-flooding model
(pure Python, stdlib only). It pairs with
vehicle-design/sizing/nacelle-sizing for the nacelle geometry that
bounds the engine fire zone and with
vehicle-design/sizing/ice-protection-sizing for the other nacelle
systems. The zone identification itself belongs to the zonal hazard
analysis leaf, which never sizes agent.

## Domain quick reference

- Total-flooding closure: the agent vapor volume at the discharge
  temperature is W * S, where W is the agent mass in kg and S the agent
  vapor specific volume in m3/kg. The concentration closure requires
  W * S / (V + W * S) = C / 100, with V the zone free volume in m3 and C
  the design concentration in percent by volume.
- Required agent mass per shot: W = (V / S) * C / (100 - C), solved from
  the closure relation. S_AGENT_DEFAULT = 0.158 m3/kg (Halon-1301-class
  agent vapor specific volume at about 20 C, design value).
- Design concentrations: C_CARGO_DEFAULT = 5.0% by volume for a Class C
  cargo compartment (FAR 25.855 context) and C_POWERPLANT_DEFAULT = 6.0%
  for a powerplant fire zone (FAR 25.1191 context).
- Closure check: closure_fraction = W * S / (V + W * S) must return the
  target C / 100 for the computed mass (identity to 1e-4).
- Installed agent rollup: installed = mass_per_shot * n_bottles *
  shots_per_bottle; one bottle of one shot carries exactly one required
  discharge.
- Discharge nozzles: one nozzle per NOZZLE_M3_PER_NOZZLE = 4.0 m3 of
  free volume, rounded up, with a floor of MIN_ENGINE_ZONE_NOZZLES = 2
  nozzles for an engine/APU fire zone.
- Coverage verdict: PASS when the installed agent mass meets the
  required agent mass per shot; an installation that carries less than
  the requirement FAILS and the layout is reworked (more bottles or
  shots, or a higher-capacity bottle).
- Units are SI: m3 free volume, percent by volume concentration, kg
  agent mass. FAR 25.851/25.855/25.1191 give compartment and fire zone
  context only; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the protected zone: Class C cargo compartment (25.855 context,
   C_CARGO_DEFAULT) or powerplant/APU fire zone (25.1191 context,
   C_POWERPLANT_DEFAULT), and its free volume in m3.
2. Compute the required agent mass per shot with agent_mass, which also
   returns the agent vapor volume and the achieved closure fraction.
3. Check the closure: the returned closure_fraction must equal
   C / 100 within 1e-4; concentration_closure cross-checks any proposed
   mass directly.
4. Roll up the installation: installed_agent with the per-shot mass,
   the bottle count and the shots per bottle gives the installed agent
   mass.
5. Set the discharge layout: nozzle_count from the free volume (and the
   powerplant zone flag for the two-nozzle floor).
6. Gate the layout: coverage_verdict compares the installed mass with
   the required mass, and fire_protection_summary returns the whole
   sizing in one dict with the coverage verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_fire_protection_sizing.py.

## Worked example

Reference installation: a Class C cargo compartment of 40 m3 free volume
at 5% concentration, and an engine nacelle core fire zone of 1.8 m3 at
6% with two bottles of two shots each.

- Cargo agent_mass(40, 5.0): mass_kg = 13.32445 kg (bound 13.32 kg),
  vapor_volume_m3 = 2.10526 m3 (bound 2.105 m3), closure_fraction =
  0.05000 (5.00%).
- Engine zone agent_mass(1.8, 6.0): mass_kg = 0.72717 kg per shot
  (bound 0.727 kg), vapor_volume_m3 = 0.11489 m3, closure_fraction =
  0.06000 (6.00%).
- Installed rollup installed_agent(0.72717, 2, 2): installed_kg =
  2.90870 kg (bound 2.91 kg), mass_per_shot_kg = 0.72717 kg.
- Nozzles: nozzle_count(40, False) = 10; nozzle_count(1.8, True) = 2
  (ceiling of 0.45 raised to the floor of 2).
- Summary fire_protection_summary(1.8, 6.0, True, n_bottles = 2,
  shots_per_bottle = 2): required_mass_kg = 0.72717 kg,
  closure_fraction = 0.06000, installed_kg = 2.90870 kg, nozzle_count =
  2, coverage_verdict = PASS.


## Pitfalls

- Using the wrong concentration for the zone: a Class C cargo
  compartment defaults to 5.0% and a powerplant fire zone to 6.0%
  by volume; the required agent mass W = (V/S) * C/(100 - C) is
  nonlinear in C, so the zone type must match the concentration.
- Skipping the closure check: the computed mass must satisfy
  W * S / (V + W * S) = C / 100 to 1e-4 (13.32445 kg in 40 m3 at 5%
  closes to 0.05000); a mass that does not close the identity does
  not meet the concentration.
- Rolling up installed agent below the requirement: the coverage
  verdict FAILs when the installed mass (bottles * shots * per-shot
  mass) is less than the required mass per shot - an installation
  that looks plumbed but under-carries fails the gate.
- Forgetting the nozzle floor on a small powerplant zone: an engine/
  APU fire zone takes at least 2 nozzles even when the volume
  suggests one (1.8 m3 gives a ceiling of 0.45 raised to 2), while a
  1 m3 cargo compartment legitimately takes 1.
- Sizing agent for a zone that was never identified: the protected
  zone and its class come from the zonal hazard analysis leaf; this
  leaf sizes the agent, it does not identify the zones.
- Feeding non-physical inputs: a non-positive free volume,
  out-of-range concentration, non-positive specific volume, negative
  mass, or bottle and shot counts below one all raise ValueError.
## Verification

- Confirm agent_mass(40, 5.0) returns 13.32445 kg with closure 0.05000
  within 1e-4, and that doubling the free volume to 80 m3 doubles the
  mass to 26.64890 kg at the same concentration.
- Confirm the closure identity: concentration_closure(40, 13.32445,
  0.158) returns 0.05000, the target concentration fraction.
- Confirm the engine rollup: installed_agent(0.72717, 2, 2) returns
  2.90870 kg, and one bottle of one shot equals the per-shot mass.
- Confirm nozzles: 40 m3 cargo gives 10, a 1.8 m3 engine zone gives 2
  (floor), and a 1 m3 cargo compartment gives 1.
- Confirm coverage: 10 kg installed against the 13.32445 kg cargo
  requirement returns FAIL; installed equal to required returns PASS.
- Confirm every non-positive free volume, out-of-range concentration,
  non-positive specific volume, negative mass, and bottle or shot count
  below one raises ValueError.
- Run the contract test offline: python3
  scripts/test_fire_protection_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/nacelle-sizing: nacelle aerodynamic geometry
  that bounds the engine bay; it never sizes fire protection agent.
- vehicle-design/sizing/ice-protection-sizing: nacelle surface thermal
  anti-icing, a separate nacelle system from zone fire protection.
- systems-engineering-safety/arp4761a/zonal-safety-analysis: fire zone
  identification and zonal hazard analysis, the upstream source of the
  protected zones this leaf sizes.
- avionics/do160/lightning-protection: equipment electrical transient
  protection on the avionics side, unrelated to extinguishing agent
  sizing.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fire_protection_sizing.py

The test covers the two worked examples (cargo 13.32445 kg at 5%,
engine 0.72717 kg per shot at 6%), the closure identity and linear
volume scaling, the installed rollup from bottles and shots, the nozzle
count with the powerplant floor, the coverage PASS/FAIL comparison, the
fire_protection_summary convenience dict with its key convention,
determinism, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: FAR 25.851 (cargo compartment
  class context), FAR 25.855 (compartment context) and FAR 25.1191
  (powerplant fire zone context) are regulatory framing only; the
  total-flooding relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
