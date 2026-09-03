# Wave-25 leaf spec: control-moment-gyro (space-systems, adcs pack)

- Path: skills/space-systems/adcs/control-moment-gyro/
- Pack: adcs (existing siblings: attitude-control-sizing,
  attitude-determination-triad, magnetorquer-control,
  reaction-wheel-control, star-tracker, sun-pointing)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: space-systems

## Claim

Size and analyze a control moment gyro (CMG) cluster for spacecraft
attitude control: compute the CMG momentum and the gimbal rate that
produces the commanded torque with the standard CMG torque equation,
check the torque amplification versus a reaction wheel at the same
momentum, compute the total momentum of a roof or pyramid cluster for a
slew, evaluate the singularity measure of the cluster, and derive the
gimbal rates needed for a commanded torque with the pseudoinverse
steering law. Produces the gimbal rates, the achieved torque, the
cluster momentum envelope, and the singularity verdict that gate CMG
selection for agile spacecraft pointing.

Does NOT do: reaction wheel torque control with momentum desaturation
(reaction-wheel-control owns the wheel law and the desat dipole),
actuator selection sizing for slew with momentum wheels (attitude-
control-sizing), magnetorquer laws, or star-tracker attitude
determination. This leaf is the CMG actuator cluster math.

## Model (implement exactly)

- Single CMG torque: for a CMG with momentum h along the rotor axis and
  gimbal axis g, torque tau = -g x h * delta_dot (sign convention
  stated); magnitude |tau| = h * delta_dot (torque amplification: a
  small rotor at high gimbal rate produces a large torque, compare with
  a reaction wheel tau = I_wheel * alpha_wheel at the same momentum).
- Cluster geometry: roof array or pyramid with the gimbal axes at a
  fixed skew angle beta from the base plane; provide the standard
  pyramid geometry function returning the gimbal axis and momentum
  direction unit vectors for each of the N units (N = 4 typical).
- Cluster momentum: total h_cluster(gimbal_angles) = sum of the unit
  momentum vectors; compute the envelope as the max momentum magnitude
  over the gimbal angle grid and check the slew momentum requirement
  inside the envelope (2D scan of the skew-symmetric plane, documented).
- Steering law: tau = J(gimbal_angles) * delta_dot with J the Jacobian
  (columns -g_i x h_i); invert with the pseudoinverse
  delta_dot = J^T (J J^T)^-1 tau and add the null-space term for
  singularity avoidance (module gain and the standard null vector).
- Singularity measure: S = det(J J^T) or the smallest singular value of
  J; classify the gimbal state as nominal (S > S_thresh), near
  singularity, or singular (S <= 0); report the margin.
- Gimbal rate limits: clip delta_dot to the max gimbal rate and compute
  the achieved torque; flag saturation.
Functions:
- cmg_torque(g_axis, h_vector, delta_dot) -> tau
- pyramid_geometry(skew_angle, num_units) -> (gimbal_axes, h_dirs)
- cluster_momentum(gimbal_angles, geometry) -> h_cluster vector
- momentum_envelope(geometry, grid) -> max magnitude
- jacobian(gimbal_angles, geometry) -> J
- steering_law(gimbal_angles, tau_cmd, geometry) -> delta_dot
- singularity_measure(gimbal_angles, geometry) -> S
- singularity_verdict(s_measure, threshold) -> str
- cmg_cluster_summary(...) -> dict (gimbal rates, achieved torque,
  singularity verdict, saturation flag)
ValueError on: zero momentum, delta_dot over limit (clip with flag
instead for the steering path), non-finite inputs, num_units < 3.

## Worked example

- Single CMG h = 50 Nms, gimbal rate 1 rad/s -> torque 50 Nm; assert.
- 4-CMG pyramid with skew 53.13 deg (standard), compute the Jacobian at
  a nominal gimbal set, the steering law for a commanded 20 Nm roll
  torque, the achieved torque within tolerance, and the singularity
  measure > 0.
- Momentum envelope: max cluster momentum magnitude >= the design slew
  momentum (assert).
Keep at least 20 test methods.

## Corpus tasks (ids w25-control-moment-gyro-1/2)

Distinctive tokens: control moment gyro, CMG, gimbal rate, gimbal axis,
torque amplification, steering law, singularity, momentum envelope,
pyramid cluster, gimbal lock. Avoid: reaction wheel, wheel momentum
desaturation, magnetorquer dipole, slew momentum wheel (owned by
reaction-wheel-control / attitude-control-sizing).

1. "derive the gimbal rates for the four CMG pyramid cluster to produce
   the commanded roll torque and check the singularity measure of the
   gimbal state"
2. "size the control moment gyro cluster momentum envelope for the agile
   slew and compute the torque amplification versus the reaction wheel"

## SKILL body notes

Pair with reaction-wheel-control (alternate actuator), attitude-control-
sizing (actuator selection), attitude-dynamics (torque environment).
Worked example uses module constants and real outputs. Compliance: ECSS
ADCS design practice referenced by name; no reproduced tables.
