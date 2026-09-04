---
name: control-allocation
description: "Use when you must allocate a commanded roll, pitch, yaw moment vector across redundant aerodynamic and propulsive effectors: assemble the control effectiveness matrix, solve the pseudoinverse allocation or the weighted least squares problem, enforce the position limits with the redistributed pseudoinverse, distribute the moment between the aerodynamic and thrust vectoring groups with the daisy chain scheme, and report the achieved moment, allocation error and saturated effectors. Produces the effector command vector and the saturation verdict for output distribution. Trigger: control allocation, control effectiveness matrix, pseudoinverse allocation, weighted least squares, daisy chain, redistributed pseudoinverse, actuator limits, saturated effectors, redundant effectors."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [control-allocation, effector-allocation, control-effectiveness-matrix, pseudoinverse-allocation, weighted-least-squares, daisy-chain, redistributed-pseudoinverse, actuator-limits, saturated-effectors, moment-command-distribution, redundant-effectors, rate-limit-command]
  version: 0.1.0
  author: Aero Agent Skills
---

# Control Allocation (gnc-autonomy/control/control-allocation)

Use when a commanded moment or acceleration vector must be distributed
among redundant aerodynamic and propulsive effectors of an aircraft or
spacecraft: this leaf is the static allocation math. It builds the
control effectiveness matrix B that maps effector deflections u to the
moment m through m = B u, solves the minimum-norm pseudoinverse or the
weighted least squares problem, enforces position and rate limits with
the redistributed pseudoinverse and clipping, splits the moment between
effector groups with the daisy chain scheme, scales the commanded
direction for the direct allocation comparison, and returns the
achieved moment, the allocation error norm, and the saturated effector
list. Pure Python, stdlib only. It pairs with pid-control-design (which
produces the moment command) and observer-design; it does not size
control surfaces, model single-surface aerodynamic effectiveness, or
design the loop gains themselves.

## Domain quick reference

- Effectiveness model: m = B u, with B the n x m control effectiveness
  matrix (n moment axes, typically 3: roll, pitch, yaw; m effectors,
  n <= m for redundancy). Column i of B is the moment vector produced
  by a unit deflection of effector i.
- Pseudoinverse allocation: u = B^+ m with B^+ = B^T (B B^T)^-1 when B
  has full row rank. This is the minimum-norm solution among all
  deflections that reproduce m exactly. When B B^T is singular the
  solve is regularized with the module constant EPSILON = 1e-9.
- Damped least squares: u = B^T (B B^T + lambda I)^-1 m, the
  regularized variant that trades exact moment reproduction against
  command magnitude.
- Weighted allocation: minimize u^T W u subject to B u = m with W the
  diagonal cost matrix, closed form u = W^-1 B^T (B W^-1 B^T)^-1 m. An
  effector with a smaller cost weight w_i is cheaper to deflect and
  takes the larger share of the command; raising w_i pushes command off
  effector i. Convention note: the module reads the weight as a cost,
  so the low-cost effector is the one favored by the allocator.
- Position limits: clip u to [u_min, u_max]; residual redistribution
  re-solves the leftover moment m - B u_clipped on the unsaturated
  effector set only (pseudoinverse restricted to the free columns),
  iterating up to the module constant MAX_ITER = 5. Saturated effectors
  stay pinned at their limits.
- Rate limits: u_dot = (u - u_prev) / dt clipped componentwise to
  +/-rate_max; the returned command moves at most rate_max * dt.
- Daisy chain: allocate the primary group (aerodynamic surfaces) up to
  its limits, then pass the residual moment to the secondary group
  (thrust vectoring or RCS).
- Direct allocation: scale the commanded direction m_hat = m / ||m||
  through its minimum-norm preimage u_dir = B^+ m_hat up to the
  actuator box; the per-axis limits bound the scale linearly, so
  s_box = min(||m||, box bound) gives the exact largest feasible
  scaling in closed form.
- Report: achieved moment m_ach = B u, error norm ||m - m_ach||, and
  the saturated effector list.
- Units are consistent command units (rad or normalized) and moment
  units (N m); keep B, m and the limits in one coherent set.
- ARP4754A frames the control law development context; the allocation
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the effector set and geometry: assemble B as the n x m matrix of
   per-effector moment coefficients (roll, pitch, yaw per column) and
   confirm n <= m.
2. Get the commanded moment vector m from the control law, then solve
   the unconstrained problem with pseudoinverse_alloc.
3. For prioritized effort, solve weighted_alloc with the diagonal cost
   weights; use damped_least_squares_alloc when B B^T is ill
   conditioned and a regularized command is acceptable.
4. Enforce the position limits: clip_to_limits for the plain verdict,
   or redistribute_pseudoinverse to re-solve the residual on the
   unsaturated effectors.
5. Enforce the deflection rate: rate_limit with the previous command,
   the time step dt and the per-effector rate_max.
6. For mixed effector families, run daisy_chain_alloc with the primary
   group (aerodynamic surfaces) and the secondary group (thrust
   vectoring, RCS), each with its own limits.
7. For the strategy comparison, run direct_alloc and compare its
   achieved moment with the pseudoinverse and daisy chain results.
8. Close with allocation_verdict on the chosen command: achieved
   moment, error norm, saturated effector list.
9. Confirm the deterministic checks with the contract test
   scripts/test_control_allocation.py.

## Worked example

Two-effector roll control with B = [[1, 1]] (both ailerons produce
roll) and commanded roll moment m = 0.8:

- Pseudoinverse allocation: u = [0.4, 0.4], the minimum-norm split.
- With position limits u_min = [0, 0] and u_max = [0.3, 0.6], clipping
  gives [0.3, 0.4]; the redistributed pseudoinverse re-solves the
  residual 0.1 on the free effector and returns u = [0.3, 0.5] with
  zero allocation error. The verdict lists effector 0 as saturated.
- Rate limit from u_prev = [0, 0] with dt = 0.1 s and rate_max =
  [2, 3] per second: step 1 gives [0.2, 0.3], step 2 reaches [0.4,
  0.4].

Three-axis case with six effectors (two per axis, coefficients [1,
0.5] per axis), effectiveness matrix

- B = [[1, 0.5, 0, 0, 0, 0], [0, 0, 1, 0.5, 0, 0], [0, 0, 0, 0, 1,
  0.5]], commanded m = [0.9, -0.6, 0.3]:

- Pseudoinverse allocation u = [0.72, 0.36, -0.48, -0.24, 0.24, 0.12]
  reproduces the moment within 1e-9, and its norm 1.0040 is below the
  norm 1.0102 of any nullspace-perturbed feasible alternative, the
  minimum-norm property.

Weighted allocation on the roll case with w = [1, 4] (effector 2 is
four times as costly): u = [0.64, 0.16], so the command moves to the
lower-cost effector 1; with w = [4, 1] the split mirrors to [0.16,
0.64].

Daisy chain: primary ailerons B_p = [[1, 1]] limited to 0.3 each and
thrust vectoring B_s = [[2]] for m = 1.0: the primary group saturates
at u_p = [0.3, 0.3] giving 0.6, the residual 0.4 goes to the secondary
group as u_s = [0.2], total achieved moment 1.0, zero error.

Direct allocation for m = 0.8 in the box [0, 0] to [0.3, 0.6]:
the commanded-direction scaling saturates at u = [0.3, 0.3] with
achieved moment 0.6 and error norm 0.2, the box bound case.

## Verification

- Confirm pseudoinverse_alloc([[1, 1]], [0.8]) returns [0.4, 0.4] and
  redistribute_pseudoinverse with u_max [0.3, 0.6] returns [0.3, 0.5]
  with error norm 0.0 and saturated list [0].
- Confirm the three-axis six-effector allocation reproduces m within
  1e-9 and beats the nullspace-perturbed alternative on norm.
- Confirm weighted_alloc with w = [1, 4] returns [0.64, 0.16] and
  achieves the commanded moment exactly.
- Confirm rate_limit reaches the command after two steps of 0.1 s at
  rate_max [2, 3] per second.
- Confirm daisy_chain_alloc closes the loop: primary moment plus
  secondary moment equals the command when the secondary is not
  saturated.
- Confirm every dimension mismatch, non-finite input, inverted limit
  (u_min > u_max), negative rate_max, and non-positive dt or weight
  raises ValueError.
- Run the contract test offline: python3
  scripts/test_control_allocation.py (35 tests, deterministic).

## Pitfalls

- Reading the weight vector backwards: the module treats the diagonal weight
  as a cost, so a smaller w_i favors effector i (w = [1, 4] sends command to
  effector 1: u = [0.64, 0.16]); raising w_i pushes command off that
  effector.
- Mixing units across B, m and the limits: keep deflection units (rad or
  normalized), moment units and the limit bounds in one coherent set or the
  allocation error norm is meaningless.
- Expecting exact reproduction after clipping: plain clip_to_limits leaves
  residual error (the [0.3, 0.6] example clips to [0.3, 0.4] with error
  0.1); use redistribute_pseudoinverse when you need the residual re-solved
  on the free effectors.
- Calling rate_limit without the previous command: u_dot = (u - u_prev)/dt
  clips to +/-rate_max, so the returned command moves at most rate_max*dt
  from u_prev; the first call needs a defined u_prev.
- Daisy chain order matters: the primary group allocates first up to its
  limits and the residual goes to the secondary group; swapping the groups
  changes the achieved allocation.
- Dimension mismatches, non-finite inputs, inverted limits (u_min > u_max),
  negative rate_max and non-positive dt or weight raise ValueError.

## Related leaves

- gnc-autonomy/control/pid-control-design: produces the moment command
  that this leaf distributes to the effectors.
- gnc-autonomy/control/observer-design: state feedback for the
  control law upstream of the allocation.
- gnc-autonomy/control/python-control-design: control law margin checks
  in the same ARP4754A development context.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_control_allocation.py

The test covers the pseudoinverse split and minimum-norm property on
the two-effector roll case and the three-axis six-effector case, the
singular-gram regularization path, damped least squares values and the
lambda = 0 delegation, weighted allocation pushing the command to the
lower-cost effector, clipping masks at both limits, the redistributed
pseudoinverse worked example ([0.3, 0.5], zero error, saturated list),
full-saturation residual retention, the max-iter bound, rate-limit step
progression and reversal, daisy chain primary and secondary saturation
behavior, direct allocation inside the box and at the box bound, the
allocation verdict fields, and ValueError rejection of dimension
mismatch, non-finite input, inverted limits, negative rate_max,
non-positive dt and non-positive weights.

## Compliance

- Standards referenced, not reproduced: ARP4754A (Aerospace
  Recommended Practice, SAE) frames the control law development and
  validation context; the allocation mathematics above is standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
