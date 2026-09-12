---
name: e20-attitude-control-magnetic-cleanliness
description: "Use when derive a spacecraft magnetic cleanliness requirement from the attitude control need under ECSS-E-ST-20C clause 6.3.7.3: evaluate the ambient geomagnetic field at the orbit, convert the control system's allowable magnetic disturbance torque into an allowable spacecraft residual dipole moment, split that allowance across the steady, switching-transient and long-term-drift contributions, categorize every contributor into exactly one of those three families, grow the drifting ones to end of life, check each family against its allocated share, and confirm the accumulated momentum over an orbit stays inside the desaturation capacity. Trigger: ecss, e-st-20c-clause-6-3-7-3, magnetic-cleanliness, residual-dipole-moment, magnetic-disturbance-torque, attitude-control-magnetic-requirement, transient-magnetic-variation, long-term-magnetic-drift, momentum-desaturation-capacity."
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
  tags: [ecss, e-st-20-electrical-scope, e20-attitude-control-magnetic-cleanliness, magnetic-cleanliness, residual-dipole-moment, magnetic-disturbance-torque, attitude-control-magnetic-requirement, transient-magnetic-variation, long-term-magnetic-drift]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Attitude Control Magnetic Cleanliness (space-systems/ecss/e20-attitude-control-magnetic-cleanliness)

Use when the task is the clause 6.3.7.3 magnetic cleanliness
requirement of ECSS-E-ST-20C -- deriving the spacecraft's magnetic
requirements from what the attitude control system can absorb, and
bounding both the switching transients and the long-term variation of
the residual moment rather than only its steady value.

## Domain quick reference

- The requirement is derived, not asserted. The attitude control
  system states how much magnetic disturbance torque it can absorb
  without eating into its pointing or momentum budget; the ambient
  field at the orbit turns that torque allowance into an allowable
  spacecraft residual dipole moment, because the disturbance torque is
  the residual moment crossed into the ambient field. A cleanliness
  number written down before that derivation is a guess.
- The ambient field is taken from a centred-dipole approximation: the
  equatorial surface value scaled by the cube of the Earth radius over
  the orbit radius, raised by the latitude term that makes the field
  roughly twice as strong over the poles as over the equator. Low
  orbits therefore impose a far tighter dipole allowance than high
  ones for the same torque allowance -- a cleanliness requirement
  copied from a geostationary programme into a low orbit is wrong by
  more than an order of magnitude.
- The torque is a cross product, so only the component of the residual
  moment perpendicular to the field produces torque. An alignment
  factor between zero and one carries that geometry; leaving it at one
  is the worst case and the right default before the orientation of
  the residual moment is known.
- The clause explicitly bounds variation, not just magnitude, so the
  allowance is split three ways before any contributor is checked. The
  steady family covers permanent magnets, ferromagnetic brackets,
  structural remanence and soft-magnetic cores. The transient family
  covers what switches: heater loops, magnetorquer duty cycling,
  latching relay states, payload mode currents, valve solenoids. The
  long-term family covers what drifts over the mission: array current
  degradation, battery current drift, magnet ageing, radiation-induced
  remanence change. The three allocated shares must sum to the whole
  allowance and no more.
- A long-term contributor is assessed at end of life, not at delivery.
  Its declared fractional drift per year compounds over the mission
  duration, so a contributor that is comfortable at launch can be the
  one that breaks the budget in the extended mission.
- The last check is momentum, not torque. The residual torque
  integrated over an orbit is the worst-case momentum the wheels have
  to take up before the next desaturation; if that exceeds the
  desaturation capacity the system saturates regardless of how the
  instantaneous torque compares to the allowance.

## Workflow

1. Evaluate the ambient geomagnetic field at the orbit altitude and
   the magnetic latitude of interest; reject a negative altitude or a
   latitude outside the pole-to-pole range.
2. Convert the attitude control system's allowable magnetic
   disturbance torque into an allowable residual dipole moment using
   that field and the alignment factor.
3. Split the allowance into steady, transient and long-term shares;
   reject a fraction set that is negative, incomplete or does not sum
   to the whole.
4. Categorize every contributor into exactly one family and reject a
   contributor kind that is not a recognized magnetic source.
5. Grow each long-term contributor to end of life from its declared
   fractional drift per year over the mission duration, and flag a
   long-term contributor with no drift rate on record.
6. Sum each family and flag a family whose end-of-life sum exceeds its
   allocated share.
7. Compute the residual torque from the total end-of-life moment,
   integrate it over one orbit period, and flag an accumulated
   momentum above the desaturation capacity; flag a missing capacity
   rather than assuming one.
8. Aggregate the budget, momentum and record findings; the design is
   magnetically clean only when all three lists are empty.

## Pitfalls

- Specifying a residual dipole moment without naming the orbit. The
  same moment is benign at geostationary altitude and unacceptable in
  a low orbit, because the ambient field differs by roughly two orders
  of magnitude.
- Checking only the steady residual moment. Clause 6.3.7.3 asks for
  the transient and long-term variation to be limited too, and a
  switching loop that never appears in the static measurement can
  dominate the disturbance the controller actually sees.
- Assessing long-term contributors at beginning of life. Drift
  compounds, so the end-of-life value is the one the budget must hold,
  and an undeclared drift rate is a finding rather than a zero.
- Allocating more than the whole allowance across the three families
  because each looks affordable on its own -- the shares must sum to
  one, and an over-allocated split silently authorises a
  non-compliant design.
- Setting the alignment factor below one to make a tight budget close,
  before the residual moment's orientation with respect to the field
  is actually established by design or measurement.
- Stopping at the torque comparison. Torque within the allowance can
  still integrate to more momentum over an orbit than the desaturation
  scheme can shed, and saturation is the failure that is actually
  observed in flight.

## Behavior contract (gate 3)

The geomagnetic field model, torque-to-dipole derivation, allowance
split, contributor categorization, end-of-life drift growth, family
budget check and orbit momentum accumulation logic is exercised by the
gate 3 contract test:
scripts/test_e20_attitude_control_magnetic_cleanliness.py against
scripts/e20_attitude_control_magnetic_cleanliness_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_attitude_control_magnetic_cleanliness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
