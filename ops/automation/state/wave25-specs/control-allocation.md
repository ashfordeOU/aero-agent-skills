# Wave-25 leaf spec: control-allocation (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/control-allocation/
- Pack: control (existing siblings: pid-control-design, lead-lag-
  compensation, root-locus-design, frequency-response-design,
  state-space-analysis, observer-design, gain-scheduling,
  python-control-design, optimal-control leaves in their own pack)
- Standards ids: arp4754a  (Ledger Standard: arp4754a)
- Family: gnc-autonomy

## Claim

Allocate a commanded moment or acceleration vector among redundant
aerodynamic and propulsive effectors of an aircraft or spacecraft: build
the control effectiveness matrix B from the per-effector moment
coefficients, compute the pseudoinverse allocation (or the weighted
least squares solution), apply the effector position and rate limits
with iterative redistribution or clipping, compare the pseudo-inverse,
daisy-chain, and direct allocation strategies on the achieved versus
commanded moment, and report the allocation error and the saturated
effector list. Produces the effector command vector, the achieved moment,
the allocation error, and the saturation verdict that gate the control
law output distribution.

Does NOT do: sizing the control surfaces (vehicle-design
control-surface-sizing), the aerodynamic effectiveness of a single
surface (flight-mechanics control-surface-effectiveness), PID/root locus
loop design (control siblings), or effector fault detection and
reconfiguration logic beyond a simple saturation flag. The leaf is the
static allocation math.

## Model (implement exactly)

- Control effectiveness: commanded moment m (dimension nx1, typically
  3: roll, pitch, yaw) from effector deflections u (mx1) with
  m = B u, B the n x m effectiveness matrix (n <= m for redundancy).
- Pseudoinverse allocation: u = B^+ m with B^+ = B^T (B B^T)^-1 when B
  has full row rank (right inverse); handle B B^T singularity with a
  small regularization (module constant epsilon) or fall back to the
  damped least squares u = B^T (B B^T + lambda I)^-1 m; assert the
  minimum-norm property on a solvable case.
- Weighted allocation: minimize u^T W u subject to B u = m; closed form
  u = W^-1 B^T (B W^-1 B^T)^-1 m; W diagonal weights (effector priority).
- Position limits: clip u to [u_min, u_max] and compute the residual
  moment m_res = m - B u_clipped; redistribute the residual over the
  unsaturated effectors with the pseudoinverse restricted to the free
  set (iterate up to a module max_iter, e.g. 5, or use the "redistributed
  pseudoinverse" one-pass method with the scaling factor; implement a
  documented deterministic scheme).
- Rate limits: given the previous command u_prev and the time step dt,
  limit the increment to rate_max: u_dot = (u - u_prev)/dt clipped to
  +/-rate_max.
- Daisy-chain: prioritize a primary group (aerodynamic surfaces) up to
  its limits, then pass the residual to a secondary group (thrust
  vectoring / RCS); return the split commands.
- Direct allocation: for n=2 or n=3, compute the largest scaling of the
  commanded direction within the actuator box (implement the simple
  iterative bisection or the standard 2D/3D polygon scaling; document
  the method).
- Report: achieved moment m_ach = B u, error norm |m - m_ach|, saturated
  list.
Functions:
- effectiveness_matrix(...) or accept B as input (primary: accept B)
- pseudoinverse_alloc(b, m) -> u
- damped_least_squares_alloc(b, m, lam) -> u
- weighted_alloc(b, w_diag, m) -> u
- clip_to_limits(u, u_min, u_max) -> (u_clipped, saturated_mask)
- redistribute_pseudoinverse(b, m, u_min, u_max, max_iter) -> u
- rate_limit(u, u_prev, dt, rate_max) -> u
- daisy_chain_alloc(b_primary, b_secondary, m, limits...) -> (u_p, u_s)
- allocation_verdict(b, m, u, ...) -> dict (achieved moment, error norm,
  saturated list)
ValueError on: dimension mismatch (B n x m vs m n x 1), non-finite
inputs, u_min > u_max elementwise, rate_max < 0, dt <= 0.

## Worked example

- Simple 2-effector roll control: B = [[1, 1]] (both effectors produce
  roll), command m = 0.8. Pseudoinverse gives u = [0.4, 0.4]; with
  limits u_max = [0.3, 0.6], clipping then redistribution gives
  u = [0.3, 0.5] and zero error (assert).
- 3-axis with 6 effectors (2 per axis): choose a B, command a moment,
  assert B u ~ m within 1e-9 and the minimum norm.
- Rate limit case and the saturated verdict.
- Weighted allocation pushes command to the higher-weight (lower-cost)
  effector.
Keep at least 20 test methods.

## Corpus tasks (ids w25-control-allocation-1/2)

Distinctive tokens: control allocation, effector allocation, control
effectiveness matrix, pseudoinverse allocation, weighted least squares,
daisy chain, redistributed pseudoinverse, actuator limits, saturation,
moment command distribution, redundant effectors. Avoid: PID tuning,
root locus, control surface sizing, aileron area (control/vehicle
siblings).

1. "allocate the commanded roll pitch yaw moment across the redundant
   control surfaces with the redistributed pseudoinverse and report the
   saturated effectors against their position limits"
2. "distribute the moment command between the aerodynamic surfaces and
   the thrust vectoring with the daisy chain scheme and check the
   allocation error"

## SKILL body notes

Pair with pid-control-design (produces the moment command), observer-
design, and the vehicle control leaves that need effector distribution.
Worked example uses module constants and real outputs. Compliance:
ARP4754A control law development referenced by name, no reproduced text.
