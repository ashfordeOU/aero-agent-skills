---
name: gain-scheduling
description: "Use when you must design and schedule controller gains against dynamic-pressure across nonlinear flight envelope, interpolate gain schedule breakpoint table across Mach-number operating points, and select the scheduling variable (dynamic-pressure, Mach number, angle of attack, or altitude). Choose nearest, linear, or spline interpolation, apply scheduling-variable rate limiting, and distinguish gain scheduling from gain updating. Verify stability between operating points and handle anti-windup interaction when scheduling autopilot and flight control gains across the envelope. Produces the interpolated gain at the current operating point and the rate-limited scheduling variable value. Trigger: gain scheduling, gain-scheduling, scheduling variable, dynamic pressure, Mach number, angle of attack, altitude, breakpoint table, schedule table, interpolation, rate limiting, gain updating, anti-windup, flight envelope."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [gain-scheduling, gain-schedule, scheduling-variable, dynamic-pressure, mach-number, angle-of-attack, altitude, breakpoint-table, schedule-table, interpolation, nearest, linear, spline, rate-limiting, gain-updating, anti-windup, flight-envelope, autopilot-gains, flight-control-gains]
  version: 0.1.0
  author: AeroSkills
---

# Gain Scheduling (gnc-autonomy/control/gain-scheduling)

Use when the task is scheduling controller gains across a nonlinear
flight envelope: picking the scheduling variable, building the
breakpoint/gain schedule table, interpolating the gain at the current
operating point, and rate limiting the scheduling variable so gain
changes stay smooth between operating points.

## Domain quick reference

- Scheduling variables: dynamic pressure (Pa), Mach number
  (dimensionless), angle of attack (deg), and altitude (m). Pick the
  variable that captures the nonlinearity that moves the plant
  dynamics, typically control effectiveness or hinge moment growth
  with dynamic pressure, or compressibility effects with Mach number.
- Breakpoint/schedule table: strictly increasing breakpoints, each
  paired with a gain tuned at that operating point. The table is the
  schedule; gains between breakpoints come from interpolation.
- Interpolation methods: nearest (stepwise, keeps the tuned gain
  until the midpoint), linear (default, straight segments between
  breakpoints), spline (overview: smoother across breakpoints but can
  overshoot between them; not implemented in the logic module).
- Out-of-range behavior: clamp to the end gains (default) or raise an
  error when the flight condition sits outside the tuned envelope and
  must be flagged rather than silently held.
- Rate limiting: limit how fast the scheduling variable can change, so
  the gain itself cannot step faster than the actuators can follow.
  Apply the rate limit to the scheduling variable, then interpolate.
- Gain scheduling vs gain updating: scheduling is a deterministic
  function of the measured operating state; gain updating is online
  adjustment from adaptation or system identification. They differ in
  mechanism and in verification burden.
- Stability between operating points: each operating point is locally
  stable by design; the transitions must be slow enough (rate limited)
  that the time-varying closed loop stays stable between points.
- Anti-windup interaction: scheduled gains change the integrator
  authority; when gains are scheduled up, the integrator clamp should
  follow, or the loop winds up at the scheduled authority limit.
- Application: autopilot and flight control gains across the envelope
  (pitch rate and roll rate gains scheduled against dynamic pressure,
  damper gains scheduled against Mach number, and so on).

## Workflow

1. Pick the scheduling variable for the nonlinearity at hand and the
   operating-point values it will take (dynamic pressure in Pa, Mach
   number, angle of attack in deg, or altitude in m).
2. Build the breakpoint/gain table from gains tuned at each operating
   point (for example with root-locus-design or pid-control-design),
   keeping the breakpoints strictly increasing.
3. Rate limit the commanded scheduling variable with
   rate_limited_scheduling_variable(prev_value, new_value, max_rate,
   dt) so gain changes stay within the actuator capability.
4. Interpolate the gain at the current operating point with
   schedule_gain(table, sched_var_value, method="linear",
   out_of_range="clamp").
5. Choose the out-of-range policy: clamp for benign conditions, error
   mode when the flight condition must be flagged as outside the tuned
   envelope.
6. Before enabling the scheduled gains in the autopilot, check
   stability between adjacent operating points and re-check the
   anti-windup clamps against the scheduled authority limits.

## Pitfalls

- Routing PID tuning questions here: Ziegler-Nichols gains, ultimate
  gain and period, and fixed-point tuning belong to
  pid-control-design.
- Routing root locus gain selection here: choosing the gain K for a
  single operating point belongs to root-locus-design; gain
  scheduling sits on top of that per-point design.
- Routing frequency response margin questions here: gain and phase
  margins at one flight condition belong to frequency-response-design.
- Using a non-monotonic breakpoint list: the schedule table must be
  strictly increasing, or the interpolation is ambiguous; the logic
  module raises ValueError.
- Interpolating without rate limiting: a fast gain step can destabilize
  the loop between operating points even when every point is locally
  stable.
- Rate limiting after interpolation: limit the scheduling variable
  first, then interpolate, so the applied gain moves smoothly.
- Clamping silently at the envelope edge: clamping hides the loss of
  tuned coverage; use error mode when the condition must be flagged.
- Confusing scheduling with updating: a scheduled gain is a
  deterministic function of the operating state; adaptive gain
  updating is a different mechanism with its own verification burden.
- Forgetting anti-windup: when gains are scheduled up, the integrator
  clamp must follow, or the loop winds up against the scheduled
  authority.
- Treating spline as implemented: spline interpolation is covered as
  an overview only; the logic module raises NotImplementedError for
  method="spline", use linear or nearest for a concrete gain.

## Behavior contract (gate 3)

The interpolation, clamping, monotonicity validation, and rate limiting
logic is exercised by the gate 3 contract test:
scripts/test_gain_scheduling_logic.py against
scripts/gain_scheduling_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_gain_scheduling_logic.py

## Compliance

- ARP4754A is proprietary (SAE); name + paraphrase only per
  standards-map.yaml. Gain scheduling interpolation math is standard
  control practice, summary only.
- compliance: STANDARDS-REF, gated: false.
