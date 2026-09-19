---
name: e3301-mechanisms-thermal-control-thermal-sizing
description: "Size the passive thermal design that keeps a mechanism inside its operational temperature band under ECSS-E-ST-33-01C clauses 4.7.4.1 and 4.7.4.2. Use when the task is solving the hot and cold steady-state mechanism temperature from its own dissipation, the absorbed flux, a conductive path and a radiative coupling to the sink, sizing the conductance an interface would need to hold a failing case at its limit, converting the interface gradient into a thermo-elastic distortion and grading it against the alignment allowance, and naming the case that governs. Trigger: ecss, e-st-33-01c, mechanism-thermal-sizing, mechanism-conductive-path-conductance, mechanism-radiative-coupling, mechanism-operational-temperature-band, mechanism-interface-gradient, mechanism-thermoelastic-distortion, mechanism-hot-and-cold-case."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-mechanisms-thermal-control-thermal-sizing, mechanism-thermal-sizing, mechanism-conductive-path-conductance, mechanism-radiative-coupling, mechanism-operational-temperature-band, mechanism-thermoelastic-distortion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Thermal Control and Thermal Sizing (space-systems/ecss/e3301-mechanisms-thermal-control-thermal-sizing)

Use when the task is the mechanism thermal sizing of ECSS-E-ST-33-01C clauses
4.7.4.1 and 4.7.4.2 — holding a mechanism inside the temperature band it was
designed to work in by passive means alone, sizing the conductive and
radiative paths that do it, and keeping the gradients those paths leave below
the distortion the mechanism can tolerate.

This is the mechanism-level question, and it is narrower than a general
thermal-design method: the algebra of conduction and radiation is the same,
but the limit is not an equipment survival range. It is the band the
lubricant regime, the bearing preload and the alignment budget were sized
for, and a failing case is expected to come back with the conductance that
would fix it, not only with a verdict.

## Domain quick reference

- A mechanism is a thermally awkward item: it dissipates in bursts at the
  motor and the bearings, it is often mounted on a low-conductance interface
  to isolate it structurally, and the part whose temperature actually matters
  is usually the contact pair, not the housing the sensor is on.
- The one-node balance is dissipation plus absorbed flux on one side, and
  conduction plus radiation to the sink on the other. Because the radiative
  term is quartic, the balance has to be solved rather than inverted, and a
  bracketed bisection is the safe way to do it: it cannot diverge and it does
  not hide a hot case behind a linearisation taken at the cold one.
- Conductances in series are dominated by their softest member. A well-chosen
  bracket bolted through a poor interface conducts like the interface, which
  is why joint conductance belongs in the path and not in a margin.
- Temperature limits come in pairs, and so do the design actions. The hot case
  asks for more conductance or more radiating area; the cold case asks for
  less of both, or for the dissipation to be kept on. A design verified at one
  end only has been verified at neither.
- The gradient is a requirement in its own right. A mechanism can sit inside
  its temperature band and still fail, because the gradient across its
  mounting interface distorts the structure that carries its alignment.

## Workflow

1. Build the conductive path: section, length and conductivity per member,
   combined in series with the joint conductances, so the number carried into
   the balance is the whole path and not its best member.
2. Build the radiative coupling as emittance times area times view factor,
   refusing an emittance or a view factor above unity.
3. For each declared case, sum the dissipation and the absorbed environmental
   flux, then solve the steady-state balance for the mechanism temperature by
   bracketed bisection against the case sink temperature.
4. Grade each solved temperature against the operational floor and ceiling,
   absorbing an exact equality at either bound with a named tolerance.
5. For a case above the ceiling, size the conductance that would hold it at
   the limit, crediting the radiative path, and report zero when radiation
   alone already suffices rather than reporting a negative conductance.
6. Convert the conductive temperature rise into an interface gradient, and
   the gradient into a thermo-elastic distortion over the alignment length.
   Grade the magnitude against the allowance.
7. Report every case, the hottest and coldest of them, both margins and every
   finding.

## Pitfalls

- Sizing on the average dissipation. A mechanism's motor and bearing losses
  are duty-cycle quantities; the case that decides the design is the one where
  the peak duty coincides with the hot environment.
- Linearising the radiative term at the cold case and reusing it hot. The term
  is quartic, so a linearisation fitted at one end under-predicts losses at
  the other, and the hot case it hides is the one that mattered.
- Putting the joint conductance in a margin instead of in the path. A margin
  on a conductance that is already the softest member of a series chain is
  not conservatism, it is a second guess at the same unknown.
- Verifying the hot case only. A mechanism below its floor has a stiff
  lubricant, a shifted preload and a running torque nothing was sized for;
  the cold case is a functional case, not a survival one.
- Treating the temperature band as the whole requirement. The gradient across
  the mounting interface can break an alignment budget while every node sits
  comfortably inside its limits.
- Reporting a failing case without the conductance that would fix it. The
  clause is a design clause; the sized action is the deliverable, and a
  verdict on its own leaves the next reader to redo the solve.

## Behavior contract (gate 3)

The series conductive path, radiative coupling, bracketed steady-state solve,
temperature-band grading, required-conductance sizing, interface gradient and
thermo-elastic distortion check are exercised by the gate 3 contract test:
scripts/test_e3301_mechanisms_thermal_control_thermal_sizing.py against
scripts/e3301_mechanisms_thermal_control_thermal_sizing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_mechanisms_thermal_control_thermal_sizing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
