---
name: e20-solar-array-sizing-and-design
description: "Use when size a spacecraft solar array against ECSS-E-ST-20C clause 5.5.2: walk every operational mission phase, categorize its illumination regime as continuous-sunlight, eclipse-cycling or dark-coast, derive the array power each phase demands from its sunlit load, its eclipse load and the battery recharge energy that must be returned inside the remaining sunlit time, degrade the reference cell power density for accumulated life, operating temperature and sun-incidence angle, then size the array area on the driving phase with a design margin and re-check the per-phase energy balance so no phase closes negative. Trigger: ecss, e-st-20-electrical-scope, solar-array-sizing, power-budget-closure, eclipse-recharge-energy, orbit-average-energy-balance, end-of-life-power-density, array-area-sizing, mission-phase-power-demand."
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
  tags: [ecss, e-st-20-electrical-scope, e20-solar-array-sizing-and-design, solar-array-sizing, power-budget-closure, eclipse-recharge-energy, orbit-average-energy-balance, end-of-life-power-density]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Solar Array Sizing and Design (space-systems/ecss/e20-solar-array-sizing-and-design)

Use when the task is the solar array sizing of ECSS-E-ST-20C clause
5.5.2 -- proving the array can meet the power and energy balance of
every operational mission phase, not just the phase that happens to be
in the baseline power budget.

## Domain quick reference

- Clause 5.5.2 is a per-phase obligation. Launch and early orbit,
  transfer, commissioning, nominal operations, each payload mode,
  safe/survival mode and end-of-life disposal are separate phases with
  their own orbit period, eclipse fraction, load profile and sun
  geometry. The array is sized on the phase that drives the largest
  area, and the other phases are then re-checked against that area.
- Each phase is categorized by illumination regime before any number
  is computed: continuous-sunlight (no eclipse in the orbit),
  eclipse-cycling (a finite eclipse inside a finite orbit) or
  dark-coast (the whole interval is in shadow). A dark-coast phase
  cannot be closed by the array at all -- it is a battery-capacity
  problem and is reported as such rather than silently sized to zero.
- The array power an eclipse-cycling phase demands has two parts: the
  sunlit load referred back through the sunlit distribution path
  efficiency, plus the battery energy consumed in eclipse referred
  back through the eclipse discharge path and the charge efficiency
  and then spread over the remaining sunlit time. The recharge term
  grows as the sunlit window shrinks, so a long eclipse can drive the
  array harder than a larger load in full sun.
- Reference cell power density is a beginning-of-life, normal-incidence,
  reference-temperature number. It is degraded by an inherent assembly
  factor (packing, interconnect, mismatch), by cumulative life
  degradation to the epoch of the phase, by the power temperature
  coefficient at the actual operating temperature, and by the cosine
  of the sun-incidence angle. Later phases see a lower density than
  earlier ones, which is why the driving phase is decided on required
  area and not on required power.

## Workflow

1. Build the phase inventory. Every phase carries a name, an orbit
   period, an eclipse duration, a sunlit load, an eclipse load, a
   phase length and a sun-incidence angle. Reject a phase whose orbit
   period is non-positive, whose eclipse exceeds the orbit period,
   whose loads are negative or whose loads are both zero.
2. Categorize each phase as continuous-sunlight, eclipse-cycling or
   dark-coast from the eclipse duration relative to the orbit period.
3. For each non-dark phase compute the required array power: sunlit
   load divided by the sunlit path efficiency, plus the eclipse energy
   divided by the eclipse path efficiency and the charge efficiency
   and divided by the sunlit duration.
4. Compute the end-of-life power density seen by that phase: reference
   density times the inherent assembly factor, times the life
   retention at the cumulative elapsed years to the end of the phase,
   times the temperature factor, times the cosine of the incidence
   angle. Reject a temperature factor that has fallen to or below
   zero -- the operating point is outside the model.
5. Convert each phase to a required area: required power times one
   plus the design margin, divided by that phase's density. The
   driving phase is the one with the largest required area.
6. Re-run the energy balance of every phase against the selected area:
   energy generated in sunlight against energy consumed over the orbit
   referred to the array. Report the margin of each phase and flag any
   phase that closes negative or that is dark-coast.

## Pitfalls

- Sizing on peak load instead of on required area. A late phase with a
  smaller load can still drive the array because its life-degraded and
  off-normal density is lower; comparing watts across phases hides it.
- Dropping the recharge term because the phase "has enough sun". The
  battery energy spent in eclipse has to be returned inside the same
  orbit, and dividing it by the sunlit duration rather than the orbit
  period is what makes a short sunlit window expensive.
- Applying the charge efficiency once. The eclipse energy crosses the
  discharge path and the charge path; both losses belong in the
  referred energy, and collapsing them to one factor understates the
  array by roughly the missing efficiency.
- Treating a dark-coast phase as sized because the computed array
  power came out at zero. Zero required array power is not a pass; it
  means the phase is closed by stored energy and belongs in the
  battery sizing case, and it is reported as an unsized phase.
- Leaving the incidence angle at zero for every phase. The cosine
  factor is a first-order term on a body-mounted or seasonally-offset
  array and moving a phase from normal incidence to sixty degrees
  halves its usable density.

## Behavior contract (gate 3)

The phase-validation, illumination-categorization, required-power,
end-of-life-density, area-sizing and per-phase energy-balance logic is
exercised by the gate 3 contract test:
scripts/test_e20_solar_array_sizing_and_design.py against
scripts/e20_solar_array_sizing_and_design_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_solar_array_sizing_and_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
