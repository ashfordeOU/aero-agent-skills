# Wave-35 leaf spec: fire-protection-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/fire-protection-sizing/
- Pack: sizing. Closest siblings: systems-engineering-safety/
  arp4761a/zonal-safety-analysis (the HAZARD ANALYSIS leaf that
  identifies fire zones and ZSA hazards; it never sizes agent),
  vehicle-design/sizing/nacelle-sizing (nacelle aerodynamic geometry
  only), ice-protection-sizing (surface thermal, not zone
  protection), avionics/do160/lightning-protection (induced
  transients, unrelated). Whole-tree grep proves ZERO owners for
  fire protection sizing, extinguishing agent, Halon, firewall agent
  mass; no leaf cites 25.851/25.855/25.1191.
- Standards id: far-25 (reference-only; 25.851/25.855/25.1191
  compartment context, framing only). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the aircraft fire protection extinguishing agent for a
protected compartment at the conceptual level: fix the protected
zone (Class C cargo compartment or powerplant/APU fire zone), take
the zone free volume and the design agent concentration by volume,
compute the total-flooding agent mass from the agent vapor specific
volume at the discharge temperature with the concentration closure
check, roll up the installed agent from the bottle and shot count,
and set the discharge nozzle count from the zone coverage. Produces
the required agent mass per shot, the installed agent mass, the
concentration closure fraction, the nozzle count, and a coverage
verdict that gate the fire protection system layout (FAR 25.851
cargo class, 25.855, 25.1191 powerplant zone context).

Does NOT do: zonal hazard analysis and fire zone identification
(zonal-safety-analysis owns the ZSA); fire DETECTION loop wiring and
annunciation; smoke detector siting; nacelle aerodynamic geometry
(nacelle-sizing); firewall structural panel analysis (structures);
agent toxicity and environmental assessment.

## Model (implement exactly)

Module constants:
- S_AGENT_DEFAULT = 0.158 (m3/kg, Halon-1301-class agent vapor
  specific volume at about 20 C, design value).
- C_CARGO_DEFAULT = 5.0 (percent by volume, Class C cargo design
  concentration in the 25.855 context).
- C_POWERPLANT_DEFAULT = 6.0 (percent by volume, powerplant fire
  zone design concentration in the 25.1191 context).
- NOZZLE_M3_PER_NOZZLE = 4.0 (one discharge nozzle per 4 m3 of free
  volume, design value).
- MIN_ENGINE_ZONE_NOZZLES = 2.

Conventions: free volume in m3; agent concentration in percent by
volume of the compartment; agent mass in kg. The total-flooding
relation: the agent vapor volume at the discharge temperature is
W * S, and the concentration closure requires
W * S / (V + W * S) = C/100.

Functions (pure stdlib):
- agent_mass(free_volume_m3, concentration_pct, spec_volume_m3_kg =
  S_AGENT_DEFAULT) -> dict {mass_kg, vapor_volume_m3,
  closure_fraction} solving W = (V/S) * C/(100 - C); closure =
  W S / (V + W S). ValueErrors: V <= 0; C outside (0, 100);
  S <= 0.
- concentration_closure(free_volume_m3, mass_kg, spec_volume_m3_kg)
  -> fraction = mass * S / (V + mass * S). ValueErrors: V <= 0;
  mass < 0; S <= 0.
- installed_agent(mass_per_shot_kg, n_bottles, shots_per_bottle) ->
  dict {installed_kg, mass_per_shot_kg} = per_shot * bottles *
  shots. ValueErrors: per_shot <= 0; n_bottles < 1;
  shots_per_bottle < 1.
- nozzle_count(free_volume_m3, is_powerplant_zone = False) ->
  max(ceil(V / NOZZLE_M3_PER_NOZZLE), MIN_ENGINE_ZONE_NOZZLES if
  is_powerplant_zone else 1). ValueErrors: V <= 0.
- fire_protection_summary(free_volume_m3, concentration_pct,
  is_powerplant_zone, spec_volume_m3_kg = S_AGENT_DEFAULT,
  n_bottles = 1, shots_per_bottle = 1) -> dict with required mass,
  closure, installed mass, nozzle count, coverage verdict (PASS when
  installed >= required).

Identity to test: the closure fraction of the computed agent mass
equals the target concentration fraction to 1e-4; agent mass scales
linearly with free volume at fixed concentration.

## Worked example

Reference installation: a Class C cargo compartment of 40 m3 free
volume at 5% concentration, and an engine nacelle core fire zone of
1.8 m3 at 6% with two bottles of two shots each.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- cargo agent_mass: (40 / 0.158) * 5/95 = 253.16 * 0.052632 = 13.32
  kg; vapor volume = 13.32 * 0.158 = 2.105 m3; closure = 2.105 /
  (40 + 2.105) = 0.0500 (5.00%).
- engine zone agent_mass: (1.8 / 0.158) * 6/94 = 11.392 * 0.063830 =
  0.727 kg per shot; installed = 0.727 * 2 * 2 = 2.91 kg.
- nozzle_count cargo: ceil(40/4) = 10; engine zone:
  max(ceil(1.8/4), 2) = 2.

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: V <= 0; C outside (0, 100); S <= 0; negative mass;
  n_bottles < 1; shots_per_bottle < 1.
- Closure identity: for the cargo case closure == 0.0500 within
  1e-4; doubling V at the same concentration doubles the mass.
- Scaling: agent mass linear in V (40 vs 80 m3 doubles 13.32 to
  26.64 kg).
- Installed: engine case 0.727 * 2 * 2 = 2.91 kg within 1e-2;
  single bottle single shot equals the per-shot mass.
- Nozzles: 40 m3 cargo -> 10; 1.8 m3 engine zone -> 2 (floor at 2);
  1 m3 cargo -> 1.
- Coverage: installed below required -> FAIL; installed equal ->
  PASS.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-fire-protection-sizing.yaml)

Query 1 (copy verbatim):
  "size the extinguishing agent mass for a class C cargo compartment at the design concentration by volume"
  intent: "vehicle-design; cargo compartment extinguishing agent total flooding mass"
  expected_skill: "vehicle-design/sizing/fire-protection-sizing"
Query 2 (copy verbatim):
  "compute the powerplant fire zone extinguishing agent per shot and the installed bottle mass for the nacelle"
  intent: "vehicle-design; powerplant fire zone agent per shot and bottle count"
  expected_skill: "vehicle-design/sizing/fire-protection-sizing"
Task ids: w35-fire-protection-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the aircraft fire
protection extinguishing agent:" and include the outputs in the
Claim. First tag: fire-protection-sizing. Additional tags ONLY:
extinguishing-agent-mass, total-flooding-agent,
cargo-compartment-fire, powerplant-fire-zone,
fire-extinguisher-bottle-sizing. NEVER single generic words (fire,
agent, extinguisher, bottle, compartment, nozzle, protection).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): zonal safety analysis, zsa,
fire zone hazard (arp4761a zonal-safety-analysis); inlet capture,
fan face, cowl wetted area (nacelle-sizing); lightning, induced
transient (do160 lightning-protection); detection loop, smoke
detector (out of scope).
