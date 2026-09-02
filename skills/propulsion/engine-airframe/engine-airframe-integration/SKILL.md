---
name: engine-airframe-integration
description: "Use when you must account for how an engine behaves once it is installed on an airframe: compute installed thrust from uninstalled gross thrust minus intake momentum (ram) drag, nacelle and pylon drag, and bleed and accessory power extraction losses, and reconcile the thrust-drag bookkeeping convention with the airframe drag count. Produces the per-term installation loss split, the installed thrust lapse and misalignment effects, and the performance verdict that feeds aircraft sizing and FAR-25/33 certification framing. Trigger: installed thrust, installation drag, ram drag, intake momentum drag, nacelle drag, pylon drag, thrust-drag bookkeeping, engine-airframe integration."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: engine-airframe
  tags: [engine-airframe-integration, installed-thrust, ram-drag, intake-momentum-drag, nacelle-drag, pylon-drag, thrust-drag-bookkeeping]
  version: 0.1.0
  author: Aero Agent Skills
---

# Engine-Airframe Integration (propulsion/engine-airframe/engine-airframe-integration)

Use when the task is the interface discipline between the engine and
the airframe: translating the uninstalled (cycle) thrust of the
propulsion family leaves into installed thrust at the airframe, and
accounting for the installation drag and power off-takes that the
aircraft performance model must carry.

## Domain quick reference

Units are SI: mass flow in kg/s, velocity in m/s, thrust and drag in
N, power in W, area in m^2, density in kg/m^3.

- Uninstalled gross thrust Fg = mdot_e*Vj + (Pe - P0)*Ae: the nozzle
  exit momentum plus the pressure term; mdot_e is the exhaust flow
  (captured air plus fuel), Vj the jet velocity.
- Intake momentum (ram) drag D_ram = mdot_0*V0: the momentum of the
  captured stream that the engine must supply; mdot_0 is the captured
  air flow, V0 the flight velocity.
- Uninstalled net thrust F_uninst = Fg - D_ram: the cycle bookkeeping
  carried by the turbofan-cycle and nozzle-design leaves. The ram drag
  is already netted here, never subtracted again.
- Nacelle drag D_nac = 0.5*rho*V0^2*Cd_nac*A_nac: external skin
  friction and pressure drag on the cowl, boat-tail, and cooling
  flow exits, written against a reference area A_nac.
- Pylon drag D_pyl = 0.5*rho*V0^2*Cd_pyl*A_pyl: the strut that carries
  the nacelle off the wing or fuselage, sized on its frontal area.
- Bleed loss dF_b = mdot_b*(Vj - V0): bleed air taken from the
  compressor for anti-ice, pressurization, or cooling removes its
  specific-thrust contribution from the propulsive stream.
- Accessory loss dF_a = P_ext/V0: shaft power drawn by generators and
  gearboxes costs propulsive power, so roughly dF_a = P_ext/V0.
- Installed thrust F_inst = F_uninst - D_nac - D_pyl - dF_b - dF_a,
  and the installation loss fraction is 1 - F_inst/F_uninst.
- Thrust vector misalignment theta trims the axial component to
  F_axial = F_inst*cos(theta).

Worked anchor (mdot_0 = 100 kg/s, mdot_e = 102 kg/s, Vj = 600 m/s,
V0 = 250 m/s, fully expanded nozzle, rho = 0.36, Cd_nac = 0.35,
A_nac = 1.2 m^2, Cd_pyl = 0.30, A_pyl = 0.5 m^2, bleed 1.5 kg/s,
accessory 500 kW): Fg = 61200 N, D_ram = 25000 N,
F_uninst = 36200 N, D_nac = 4725 N, D_pyl = 1687.5 N, dF_b = 525 N,
dF_a = 2000 N, F_inst = 27262.5 N, loss fraction 24.7%.

## Workflow

1. Fix the flight point and engine reference: V0, rho, captured flow
   mdot_0, exhaust flow mdot_e, jet velocity Vj, and the nozzle
   pressure term (Pe - P0)*Ae.
2. Form the uninstalled terms with gross_thrust and
   intake_momentum_drag, then uninstalled_net_thrust. This is the
   cycle result the propulsion family leaves hand over.
3. Estimate the external drag with nacelle_drag and pylon_drag at the
   flight dynamic pressure.
4. Estimate the power off-takes with bleed_thrust_loss and
   accessory_thrust_loss.
5. Sum the bookkeeping with thrust_drag_summary and read the per-term
   ledger plus the installation loss fraction.
6. Fold misalignment in with axial_thrust and carry the installed
   thrust into the aircraft performance model (installed thrust
   lapse, climb and cruise sizing).

## Pitfalls

- Confusing installed with uninstalled thrust: the turbofan-cycle
  family leaves quote cycle (uninstalled) thrust; this leaf subtracts
  the installation losses the airframe actually feels.
- Double-counting ram drag: F = mdot*(Vj - V0) already contains the
  intake momentum drag subtraction, so subtracting D_ram again
  charges the installation twice.
- Treating the intake as a thrust source: the ramjet-inlet leaf
  recovers ram pressure for a ramjet, while here the intake is purely
  a momentum drag term on the captured stream.
- Mixing gross and net nozzle thrust: the nozzle-design leaf computes
  ideal gross thrust with the pressure term; the installed
  bookkeeping nets ram drag and external drag against it.
- Carrying the air-breathing bookkeeping into rocket staging: the
  rocket-staging leaf has no captured air, no ram drag, and no
  intake; its installation losses are thrust-structure and boat-tail
  drag, not intake losses.
- Netting bleed and accessory losses twice: they appear once as power
  off-takes here, not again as airframe drag items.
- Mixing mdot_0 (captured air) with mdot_e (exhaust, includes fuel)
  in the momentum terms.
- Dropping the pressure term when the nozzle is not fully expanded,
  or using V0^2 instead of the dynamic pressure 0.5*rho*V0^2.

## Behavior contract (gate 3)

The installed thrust bookkeeping is exercised by the gate 3 contract
test: scripts/test_engine_airframe_integration.py against
scripts/engine_airframe_integration_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_engine_airframe_integration.py

## Compliance

- FAR-33 (engine certification) and FAR-25 (airframe certification)
  are referenced, not reproduced: US government work (public
  domain); the installation bookkeeping is common propulsion
  methodology, summary only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
