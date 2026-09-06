# Wave-44 leaf spec: statically-indeterminate (structures, fem pack)

- Path: skills/structures/fem/statically-indeterminate/
- Pack: fem (22 leaves present at prep: beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, crippling-analysis, curved-beam-analysis,
  cylindrical-shell-buckling, diagonal-tension-field-webs, hertzian-contact-stress,
  lug-joint-analysis, metallic-fastener-joints, modal-analysis,
  plastic-collapse-analysis, plate-buckling, pressure-bulkhead, shear-center-analysis,
  shrink-fit-analysis, torsion-shear-flow, truss-analysis;
  statically-indeterminate and restrained-warping are the two wave-44
  additions of the family). Claim fences (quoted from the sibling
  frontmatter and bodies at prep; none owns the elastic redundancy
  analysis of beams and continuous beams):
  - beam-frame-analysis (this pack) is the NUMERIC stiffness-method
    complement: its description opens "Use when you must solve a
    two-dimensional rigid-jointed frame with the Euler Bernoulli beam
    element: build the local beam element stiffness from the axial and
    bending contributions, rotate it into the global frame with the member
    orientation, assemble the global stiffness matrix, apply the fixed
    support conditions, solve for the nodal displacements and rotations
    with a compact elimination solver, and recover the support reactions
    and the member end actions." That leaf distributes no moments: no
    compatibility equation on redundant reactions, no fixed-end-moment
    release iteration, no carry-over cycle. It owns the 6x6 Euler-Bernoulli
    element assembly, the tags rigid-jointed-frame, euler-bernoulli-beam-
    element, rotation-degree-of-freedom, bending-moment-recovery and
    portal-frame, and the triggers "beam frame analysis", "rigid jointed
    frame", "portal frame" and "Euler Bernoulli beam element". This leaf
    reaches the same rigid-jointed frames only through the classical hand
    methods (moment distribution over the top joints of a no-sway frame,
    slope-deflection joint equations) and MUST NOT reuse any of those tags
    or triggers.
  - truss-analysis (this pack) is the pin-jointed axial-only direct
    stiffness method: "Compute the response of a 2D pin-jointed truss with
    the direct stiffness method: build each element stiffness matrix from
    E, A, L and orientation, assemble the global stiffness matrix, apply
    support conditions, solve the nodal displacements by Gaussian
    elimination, then recover member axial forces and support reactions."
    Its tags include gaussian-elimination, direct-stiffness-method,
    element-stiffness-matrix, global-stiffness-matrix, nodal-displacements,
    member-forces and plane-truss. This leaf never assembles a structure
    stiffness matrix and never claims Gaussian elimination or a direct
    stiffness method as its method: the only linear solves here are the
    small simultaneous sets of the three-moment equations and the two
    slope-deflection joint equations of one symmetric frame, incidental
    arithmetic of the classical methods and never a headline claim.
  - plastic-collapse-analysis (this pack, wave-43) is the LIMIT-state
    complement: its description opens "Use when you must find the plastic
    collapse (limit) load of a beam or a simple frame" and its body reads
    "the plastic hinge mechanisms of statically indeterminate beams and
    frames whose collapse loads come from the kinematic (virtual work) and
    static (equilibrium plus yield) theorems". Its only mention of
    statically indeterminate beams is that limit context: it forms plastic
    hinges at the elastic moment peaks and stops at the collapse load
    factor; it explicitly "Does NOT do: elastic stiffness-method frames,
    nodal displacements, rotations, elastic member end actions, support
    reactions". This leaf is the direct elastic complement: the fixed-end
    moments, interior support moments and reactions that plastic-collapse
    analysis consumes as its "elastic moment peaks" (the 3*W*L/16 propped
    hogging peak and the W*L/8 fixed-fixed peaks of its worked example are
    exactly the elastic fixed-end moment results this leaf derives from
    the standard load cases).
  - beam-vibration (this pack) claims natural frequencies of "a continuous
    beam member": its "continuous beam" means the continuous
    (distributed-mass) Euler-Bernoulli member, not a multi-span redundant
    beam on interior supports. No overlap.
  - beam-column-analysis and buckling-analysis (this pack) own elastic
    stability of compression members: Euler buckling loads, effective
    length K factors, the secant formula with a primary end moment. No
    redundancy distribution there.
  - thermal-stress-analysis (structures/thermal-structures) mentions a
    redundant structure only as a constraint for thermal expansion ("the
    constraint can be geometric (a member welded or bolted between rigid
    supports) or kinematic (a thermal gradient in a redundant structure)");
    it computes E*alpha*dT axial restraint stresses and bimetallic
    curvature from temperature change, not a mechanical-load force
    distribution by three-moment, moment distribution or consistent
    deformation. Thermal effects are out of this leaf's scope.
  - restrained-warping (this pack, same wave) claims non-uniform torsion
    of thin-walled open sections (bimoment, warping constant, the
    St-Venant versus warping torque split), a different phenomenon from
    redundant flexure.
  Whole-tree greps at prep (real runs, all exit 0): the hyphenated tokens
  moment-distribution, slope-deflection, three-moment, consistent-
  deformation, fixed-end-moment and statically-indeterminate each give 0
  hits in skills/ SKILL.md bodies and 0 hits in eval/hit1-corpus.yaml; the
  prose forms "moment distribution", "slope deflection", "three moment",
  "consistent deformation", "fixed end moment", "Hardy-Cross" and
  "Clapeyron" give 0 hits in the whole tree; the only "statically
  indeterminate" hits are two in plastic-collapse-analysis (the limit
  context quoted above); the only "continuous beam" hits are the two
  beam-vibration distributed-member sentences; in eval/hit1-corpus.yaml
  the words "redundant"/"indeterminate"/"fixed end"/"force method" match
  only the wave-43 plastic-collapse tasks (limit intent) and non-structural
  reliability senses (redundant actuation channels, MIL-STD-1553 bus
  redundancy, AFDX redundant networks, RBD parallel units, redundant
  effectors, CCF beta-factor), never structural redundancy. GENUINE
  STRUCTURES gap (fresh probe): no leaf computes the elastic force
  distribution of indeterminate beams: no fixed-end-moment catalog, no
  three-moment (Clapeyron) interior support moments, no Hardy-Cross
  moment-distribution iteration with carry-over, no slope-deflection joint
  rotations, no consistent-deformation (force method) redundant reactions;
  beam-frame-analysis is numeric element assembly, truss-analysis is
  pin-jointed axial DSM, and plastic-collapse-analysis is the limit state.
- Standards id: far-25, cs-25 (reference-only, both present in
  standards-map.yaml, matching the fem siblings; FAR 25.303 / CS 25.303
  require the structure to withstand 1.5 times the limit loads without
  failure, and the elastic end moments and reactions computed here are the
  limit-load force distribution that the downstream strength and margin
  checks, including the 1.5 ultimate-factor check, consume). Ledger
  Standard: far-25, cs-25.
- Family: structures

## Claim

Analyze the elastic redundancy of beams, continuous beams and one
no-sway frame by the classical hand methods: compute the fixed-end moments
of the standard load cases for a both-ends-fixed prismatic member (uniform
load w over the span: |M_FE| = w*L**2/12 hogging at each end; central
point load P: |M_FE| = P*L/8 hogging at each end; the Roark fixed-end
table values), the propped-cantilever fixed-end results that follow when
one end is released (uniform: w*L**2/8 hogging at the fixed end with
reactions 5*w*L/8 at the fixed end and 3*w*L/8 at the prop; central:
3*P*L/16 hogging with reactions 11*P/16 and 5*P/16, both equal to the
fixed-end moment plus the 1/2 carry-over of the released end, the classic
moment-distribution identity), the interior support moments of continuous
beams with simple end supports from the three-moment (Clapeyron) equation
M_{j-1}*L_j + 2*M_j*(L_j + L_{j+1}) + M_{j+1}*L_{j+1} = -6*(t_j +
t_{j+1}) with the load terms t = A*xbar/L of the simple-span free bending
moment diagram (uniform w: t = w*L**3/24; central P: t = P*L**2/16),
reproducing the continuous-beam table values (two equal spans under
uniform w: interior support moment w*L**2/8 hogging; three equal spans:
w*L**2/10 hogging at each interior support), the member end moments by the
moment distribution (Hardy-Cross) method with stiffness distribution
factors from the 4*E*I/L member stiffnesses and the 1/2 carry-over factor,
the end moments and joint rotations by the slope-deflection equations
m = (2*E*I/L)*(2*theta_i + theta_j) + FEM with clockwise-positive member
end moments and clockwise-positive joint rotations, and the redundant
reactions of the propped cantilever by the consistent-deformation (force)
method with the flexibility coefficient f_BB = L**3/(3*E*I) closing the
released-cantilever deflections of the Shigley A-9 load cases (uniform:
delta_B = w*L**4/(8*E*I) giving R_B = 3*w*L/8; central: delta_B =
5*P*L**3/(48*E*I) giving R_B = 5*P/16), recovering the support reactions
from the end moments with R_left = R0 + (M_right - M_left)/L per span
(R0 the simple-span reaction), the joint rotations and member end moments
of a symmetric fixed-base portal frame under a central beam load (no
sidesway) by moment distribution over the two top joints with the column
and beam stiffnesses 4*E*I/h and 4*E*I/Lb, cross-checked against the
direct solution of the two slope-deflection joint-equilibrium equations
and the closed form theta_B = (W*Lb/8)/(4*E*I/h + 2*E*I/Lb) = -theta_C.
Produces the fixed-end moment magnitudes, the Clapeyron load terms, the
interior support moments of continuous beams, the member end moments and
joint rotations, the support reactions, the method-agreement residuals
(three-moment equals moment distribution, slope-deflection equals the
Hardy-Cross carry-over result, moment distribution equals the direct
joint-equation solve on the frame), the carry-over identities of the
propped cantilever and the equilibrium checks (reaction sums and joint
moment balances) that verify a hand-calc or stdlib-only elastic redundancy
analysis of beams and continuous beams. Does NOT do: plastic hinges,
mechanisms, collapse loads, limit analysis or the tags plastic-hinge,
collapse-mechanism, limit-analysis-beam, fully-plastic-moment, shape-factor,
collapse-load-factor (plastic-collapse-analysis, the limit complement);
stiffness-matrix assembly, the 6x6 Euler-Bernoulli element, global matrix
solves, the tags rigid-jointed-frame, euler-bernoulli-beam-element,
rotation-degree-of-freedom, bending-moment-recovery or portal-frame and
the trigger "portal frame" (beam-frame-analysis, numeric element
stiffness; this leaf reaches rigid-jointed frames only through the
classical moment distribution and slope-deflection hand methods and its
frame catalog is the single symmetric no-sway fixed-base portal under a
central beam load); pin-jointed axial trusses, direct stiffness assembly,
Gaussian elimination as a claimed method or the tags direct-stiffness-
method, gaussian-elimination, nodal-displacements, member-forces,
element-stiffness-matrix, global-stiffness-matrix or plane-truss
(truss-analysis); Euler column buckling, effective length or the secant
formula (buckling-analysis, beam-column-analysis); natural frequencies of
a continuous beam member (beam-vibration); thermal E*alpha*dT restraint
stresses or bimetallic curvature in a redundant structure
(thermal-stress-analysis); warping restraint, bimoment or the warping
constant (restrained-warping, same wave). Scope: prismatic members with a
common E*I across the continuous-beam spans and across all frame members,
loads only as a uniform load over the full span or a point load at
midspan, simple end supports for the continuous-beam catalog, no support
settlement, no sidesway and no axial deformation coupling in the frame
case, no temperature, no material nonlinearity and no dynamics; the
methods of Roark's fixed-end and continuous-beam tables, the Shigley A-9
beam deflection cases and the Bruhn redundant-structure (force method)
presentation, named and paraphrased, never reproduced. SI units (metres,
newtons, newtons per metre, newton metres, radians, pascals). Deterministic,
pure stdlib.

## Model (implement exactly)

Pure stdlib, math only. All functions take plain SI floats. No module
constants beyond math. Sign conventions (pin these exactly; every function
below derives from them):

- Beam internal moment M(x) is SAGGING POSITIVE across each span: hogging
  support moments are NEGATIVE floats. The support moment at an interior
  support of a gravity-loaded continuous beam is therefore negative, and
  its magnitude is the hogging moment.
- Member end moments in moment distribution and slope-deflection are
  CLOCKWISE POSITIVE on the member end. For a downward transverse load on
  a both-ends-fixed member the fixed-end moment is hogging at both ends:
  FEM_left = -|M_FE| (counterclockwise on the member) and FEM_right =
  +|M_FE| (clockwise on the member). Joint rotations theta are CLOCKWISE
  POSITIVE. Mapping at a support section: the clockwise-positive
  member-end moment at a LEFT end equals the sagging-positive internal
  moment there, and at a RIGHT end it equals its negative, so the
  sagging-positive interior support moment M_j equals -end_moments[j-1][1]
  of the span to its left and end_moments[j][0] of the span to its right;
  joint equilibrium makes the two member-end moments at a joint sum to
  zero.
- Three-moment (Clapeyron) equation over the adjacent spans j (left,
  length L_j, load term t_j) and j+1 (right, length L_{j+1}, load term
  t_{j+1}) between the supports j-1, j and j+1, with M_j the sagging-
  positive interior support moment and M_0 = M_n = 0 at the simple end
  supports:

      M_{j-1}*L_j + 2*M_j*(L_j + L_{j+1}) + M_{j+1}*L_{j+1}
          = -6*(t_j + t_{j+1})

  with t = A*xbar/L from the simple-span free bending moment diagram A and
  its centroid distance xbar from the near support: uniform w over the
  full span: A = w*L**3/12, xbar = L/2, t = w*L**3/24; central load P:
  A = P*L**2/8, xbar = L/2, t = P*L**2/16. Closed forms this leaf must
  reproduce: two equal spans under uniform w give M_interior = -w*L**2/8;
  three equal spans give -w*L**2/10 at each interior support (Roark and
  Shigley continuous-beam table values).
- Span reactions from the support moments (sagging-positive convention,
  R0 the simple-span reaction: w*L/2 for uniform, P/2 for central):

      R_left  = R0 + (M_right_end - M_left_end)/L
      R_right = R0 + (M_left_end - M_right_end)/L

  with M_left_end = M_{j-1} and M_right_end = M_j for span j (0.0 at the
  simple ends). Example: the two-span beam gives R_A = w*L/2 + M_B/L with
  M_B negative, i.e. the classic end-span reaction w*L/2 - |M_B|/L.
- Slope-deflection (clockwise-positive member end moments, theta
  clockwise positive, no settlement, sway term zero in this catalog):

      M_ab = (2*E*I/L)*(2*theta_a + theta_b) + FEM_ab
      M_ba = (2*E*I/L)*(2*theta_b + theta_a) + FEM_ba

  Propped cantilever (A fixed, B a roller): M_ba = 0 fixes theta_B =
  -FEM_ba*L/(4*E*I): uniform -w*L**3/(48*E*I), central -P*L**2/(32*E*I),
  and M_ab then carries the hogging fixed-end moment -3*|M_FE|/2 ... in
  magnitudes: uniform w*L**2/8, central 3*P*L/16.
- Consistent deformation (force method) on the propped cantilever: release
  the prop B; the redundant R_B closes the released-cantilever tip
  deflection delta_B against the unit-load flexibility f_BB = L**3/
  (3*E*I), R_B*f_BB = delta_B, with the Shigley A-9 cantilever cases:
  uniform delta_B = w*L**4/(8*E*I) giving R_B = 3*w*L/8; central delta_B
  = 5*P*L**3/(48*E*I) giving R_B = 5*P/16. R_A = total - R_B and the
  hogging fixed-end moment magnitude follows from statics (w*L**2/8,
  3*P*L/16). Carry-over identity: the propped fixed-end moment magnitude
  equals the both-ends-fixed FEM plus the 1/2 carry-over of the released
  end (w*L**2/12 + w*L**2/24 for uniform; P*L/8 + P*L/16 for central).
- Moment distribution (Hardy-Cross): each member end starts at its
  fixed-end moment; each joint in turn is released by adding the negative
  of its unbalanced sum, split by the distribution factors DF_e = k_e/
  sum(k) with k = 4*E*I/L (common E*I, so DFs proportional to 1/L),
  carrying one half of each balancing moment to the far end of the same
  member; simple end supports have DF = 1; repeat until the largest
  |balancing moment| falls below the tolerance. This converges to the
  exact solution of the joint-rotation equations, so the support moments
  agree with the three-moment equation to the tolerance.
- Symmetric fixed-base portal frame (the one frame case): beam span Lb
  between the top joints B and C, columns of height h fixed at the bases A
  and D, common E*I, central load W on the beam, no sidesway by symmetry.
  FEM = W*Lb/8 hogging at each beam end; the top-joint distribution
  factors are 0.6 (column) and 0.4 (beam) at h = 4 m, Lb = 6 m from the
  4*E*I/h and 4*E*I/Lb stiffnesses; the bases never release, so the base
  moment equals one half of the column top moment (carry-over). Joint
  equilibrium and symmetry give theta_B = (W*Lb/8)/(4*E*I/h + 2*E*I/Lb) =
  -theta_C, column top moment magnitude (4*E*I/h)*theta_B, column base
  moment magnitude (2*E*I/h)*theta_B, beam end moment magnitude W*Lb/8 -
  (2*E*I/Lb)*theta_B, beam midspan sagging moment W*Lb/4 minus the beam
  end moment magnitude, base vertical reactions W/2 each and zero
  horizontal reactions. Cross-check (implemented in the anchor and
  reproduced by the contract test): the two joint-equilibrium
  slope-deflection equations

      (4*E*I/Lb + 4*E*I/h)*theta_B + (2*E*I/Lb)*theta_C = +W*Lb/8
      (2*E*I/Lb)*theta_B + (4*E*I/Lb + 4*E*I/h)*theta_C = -W*Lb/8

  solved directly for theta_B and theta_C must reproduce the moment-
  distribution end moments. This direct 2x2 solve is a verification
  cross-check only, never a claimed method of the leaf and never a tag or
  trigger (truss-analysis owns gaussian-elimination and
  direct-stiffness-method).

Functions:

- fixed_end_moment_uniform(w, L) -> float: w*L**2/12, the fixed-end moment
  magnitude at each end of a both-ends-fixed member. ValueError if w <= 0
  or L <= 0.
- fixed_end_moment_central(P, L) -> float: P*L/8. ValueError if P <= 0 or
  L <= 0.
- clapeyron_term_uniform(w, L) -> float: w*L**3/24. ValueError if w <= 0
  or L <= 0.
- clapeyron_term_central(P, L) -> float: P*L**2/16. ValueError if P <= 0
  or L <= 0.
- three_moment_support_moments(lengths, terms) -> list of n - 1 interior
  support moments (sagging positive, hogging negative) of a continuous
  beam on simple end supports: solves the Clapeyron set above for the
  n spans of lengths (n >= 2) with one load term per span. ValueErrors:
  fewer than two spans; len(terms) != len(lengths); any length or term
  <= 0.
- support_reactions_continuous(lengths, loads, moments) -> list of n + 1
  upward support reactions from the span rule above; loads is a list of
  (kind, magnitude) pairs, kind "uniform" (R0 = w*L/2) or "central" (R0 =
  P/2). ValueErrors: len(loads) != len(lengths); unknown kind; magnitude
  <= 0.
- hardycross_beam(lengths, loads, tol = 1e-9, max_iter = 50000) -> dict
  with keys "end_moments" (per span the (M_left, M_right)
  clockwise-positive member end moments), "support_moments" (interior
  support moments in the sagging-positive convention, taken as
  -end_moments[j-1][1] for each interior support j) and "iterations",
  by the release cycle above. ValueErrors: unknown load kind; magnitude
  <= 0. Raises RuntimeError if max_iter is exhausted without reaching tol.
- slope_deflection_member(ei, length, theta_left, theta_right, fem_left,
  fem_right) -> (M_left, M_right) tuple from the slope-deflection
  equations above (no sway term). ValueError if ei <= 0 or length <= 0.
- propped_cantilever(config, q, length, ei) -> dict with keys "config",
  "fixed_reaction", "prop_reaction", "fixed_end_moment" (hogging
  magnitude at the fixed end A), "prop_rotation" (theta_B, clockwise
  positive, a negative value), "flexibility" (f_BB = L**3/(3*E*I)),
  "released_deflection" (delta_B of the released cantilever),
  "consistency_residual" (R_B*f_BB - delta_B), "peak_sagging_moment",
  "peak_sagging_location", "hardycross_fixed_end_moment", 
  "sd_fixed_end_moment" and "sd_prop_end_moment" (0.0 by the roller
  condition). config "uniform" (q = w in N/m): R_B = 3*w*L/8, R_A =
  5*w*L/8, |M_A| = w*L**2/8, theta_B = -w*L**3/(48*E*I), delta_B =
  w*L**4/(8*E*I), peak sagging 9*w*L**2/128 at x = 5*L/8 from A. config
  "central" (q = P in N at midspan): R_B = 5*P/16, R_A = 11*P/16, |M_A| =
  3*P*L/16, theta_B = -P*L**2/(32*E*I), delta_B = 5*P*L**3/(48*E*I), peak
  sagging 5*P*L/32 under the load. ValueErrors: config not in ("uniform",
  "central"); q <= 0; length <= 0; ei <= 0.
- portal_frame_fixed_base(total_load, span, height, ei, tol = 1e-9) ->
  dict with keys "beam_end_moment_magnitude", "column_top_moment_magnitude",
  "column_base_moment_magnitude", "beam_midspan_sagging_moment", "theta_B",
  "theta_C", "reaction_vertical_each_base", "reaction_horizontal_each_base",
  "hardycross" (member end moments keyed ("col1", "a"/"b"), ("beam",
  "a"/"b"), ("col2", "a"/"b"), clockwise positive), "sd" (closed-form
  member end moments m_ab, m_ba, m_bc, m_cb, m_cd, m_dc) and
  "iterations", by the release cycle over the top joints B and C with the
  bases A and D fixed. ValueError if any of total_load, span, height, ei
  <= 0. Raises RuntimeError if the cycle does not converge.
- slope_deflection_frame_solve(total_load, span, height, ei) -> dict with
  keys "theta_B", "theta_C", "det" and "moments" (m_ab, m_ba, m_bc, m_cb,
  m_cd, m_dc from the member end moment equations evaluated at the solved
  rotations): the direct 2x2 joint-equation cross-check of the frame.
  ValueError if any of total_load, span, height, ei <= 0.

Identities to test (closed form, deterministic):
- Fixed-end magnitudes: fem_uniform(12000, 5) = 25000.0 = 12000*25/12;
  fem_uniform(10000, 6) = 30000.0; fem_central(30000, 4) = 15000.0 =
  30000*4/8; propped magnitudes w*L**2/8 = 24000.0 (w 12000, L 4) and
  3*P*L/16 = 15000.0 (P 20000, L 4); carry-over identity residual
  |M_A| - (FEM + FEM/2) = 0.0 in both cases.
- Clapeyron terms: clapeyron_term_uniform(12000, 5) = 62500.0;
  clapeyron_term_central(30000, 4) = 30000.0.
- Two-span beam (L1 = 5 m uniform 12000 N/m, L2 = 4 m central 30000 N):
  M_B = -30833.3333333333, equal to the closed form -3*(t1 + t2)/(L1 +
  L2); reactions 23833.3333333333, 58875.0, 7291.6666666667 N summing to
  90000.0 (equilibrium residual 1.45519152284e-11); the moment
  distribution support moment agrees with the three-moment result (anchor
  residual 0.0) in 23 iterations with |member end moment| at the simple
  ends below 5e-10 N m; span-1 peak sagging 23667.8240740741 N m at x =
  1.98611111111 m from A; span-2 midspan sagging 14583.3333333333 N m.
- Three-span beam (three equal spans L = 6 m, uniform 10000 N/m): M_1 =
  M_2 = -36000.0 = -w*L**2/10, the Roark/Shigley continuous-beam table
  value; reactions 24000.0, 66000.0, 66000.0, 24000.0 N summing to
  180000.0 (residual 0.0); hardycross agreement within 3.20142135024e-10
  in 25 iterations; end-span peak sagging 28800.0 N m at x = 2.4 m;
  interior-span peak sagging 9000.0 N m at midspan.
- Propped cantilever central (P = 20000 N, L = 4 m, E*I = 4.0e7 N m^2):
  fixed reaction 13750.0 N, prop reaction 6250.0 N, fixed-end moment
  15000.0 N m, theta_B = -2.5e-4 rad, f_BB = 5.33333333333e-07 m/N,
  delta_B = 3.33333333333e-03 m, consistency residual R_B*f_BB - delta_B
  = 0.0, peak sagging 12500.0 N m under the load; the slope-deflection and
  Hardy-Cross fixed-end moments are both 15000.0 and the prop end moment
  is 0.0.
- Propped cantilever uniform (w = 12000 N/m, L = 4 m): fixed reaction
  30000.0 N, prop reaction 18000.0 N, fixed-end moment 24000.0 N m,
  theta_B = -4.0e-4 rad, delta_B = 9.6e-03 m, consistency residual
  1.73472347598e-18, peak sagging 13500.0 N m at x = 2.5 m.
- Slope-deflection member identities: with theta_left = 0, theta_right =
  -2.5e-4, FEM pair (-10000.0, +10000.0) the member returns (-15000.0,
  0.0) exactly (prop end moment zero is the roller condition); with
  theta_right = -4.0e-4 and FEM pair (-16000.0, +16000.0) it returns
  (-24000.0, 0.0).
- Frame (W = 60000 N, Lb = 6 m, h = 4 m, E*I = 4.0e7 N m^2): beam end
  moment magnitude 33750.0 N m hogging at each end, column top moment
  33750.0 N m, column base moment 16875.0 N m (= top/2, the carry-over),
  beam midspan sagging moment 56250.0 N m (= 90000 - 33750), theta_B =
  8.4375e-4 rad = -theta_C (identity residual 0.0), base vertical
  reactions 30000.0 N each, horizontal reactions 0.0; moment distribution
  converges in 12 iterations and the maximum difference from the direct
  2x2 joint-equation solve over all six member end moments is
  3.49245965481e-10 N m; joint equilibrium residuals 0.0 (joint B) and
  5.67524693906e-10 N m (joint C).
- ValueErrors across the module: w = 0 and L = 0 on the FEM functions;
  negative term load; a one-span three-moment call; arity mismatch on the
  terms; wrong loads arity; unknown load kind "triangular"; unknown
  hardycross kind "parabolic"; ei = 0 on slope_deflection_member; config
  "triangular" and negative q on propped_cantilever (11 anchor cases,
  each raises).
- Determinism; no imports beyond math; no RNG; identical bits on repeated
  runs.

## Worked example

E = 200 GPa, I = 2.0e-4 m^4, so E*I = 4.0e7 N m^2 throughout. All values
below are REAL outputs of the prep anchor /tmp/w44spec/anchor_indet.py
(pure stdlib math, exit 0), which implements every function of the Model
and runs the checks listed here.

- Fixed-end moments and Clapeyron terms:
  - fem_uniform(w = 12000 N/m, L = 5 m) = w*L**2/12 = 25000.0 N m hogging
    at each end; fem_uniform(10000, 6) = 30000.0; fem_central(P = 30000 N,
    L = 4 m) = P*L/8 = 15000.0 at each end.
  - clapeyron_term_uniform(12000, 5) = w*L**3/24 = 62500.0 N m^2;
    clapeyron_term_central(30000, 4) = P*L**2/16 = 30000.0 N m^2: the
    areas of the simple-span free moment diagrams about the near supports.
- Propped cantilever, central load P = 20000 N, L = 4 m (r = 1, the prop
  reaction is the single redundant):
  - Consistent deformation: release the prop. The released cantilever tip
    deflection under the midspan load (Shigley A-9 case) is delta_B =
    5*P*L**3/(48*E*I) = 0.00333333333333 m and the unit-load flexibility
    is f_BB = L**3/(3*E*I) = 5.33333333333e-07 m/N; closing the gap gives
    R_B = delta_B/f_BB = 6250.0 N (5*P/16) with consistency residual
    R_B*f_BB - delta_B = 0.0. Statics give R_A = 13750.0 N (11*P/16) and
    the hogging fixed-end moment |M_A| = 3*P*L/16 = 15000.0 N m.
  - Slope-deflection: the roller condition M_ba = 0 gives theta_B =
    -P*L**2/(32*E*I) = -2.5e-4 rad and M_ab = -15000.0 N m (hogging 15000
    at the fixed end); the Hardy-Cross release of the prop end (balance
    -10000.0, carry -5000.0 to A on top of the FEM -10000.0) gives the
    same -15000.0 N m, the carry-over identity 3*P*L/16 = P*L/8 + P*L/16
    holding with residual 0.0.
  - Peak sagging moment 5*P*L/32 = 12500.0 N m under the load at x = 2.0 m:
    the fixed-end hogging peak (15000) dominates the elastic moment
    diagram, the familiar 3*W*L/16 first-yield context of the limit-state
    sibling.
- Propped cantilever, uniform w = 12000 N/m, L = 4 m:
  - R_B = 3*w*L/8 = 18000.0 N, R_A = 5*w*L/8 = 30000.0 N, |M_A| = w*L**2/8
    = 24000.0 N m, theta_B = -w*L**3/(48*E*I) = -4.0e-4 rad, delta_B =
    w*L**4/(8*E*I) = 9.6e-03 m, consistency residual 1.73472347598e-18,
    peak sagging 9*w*L**2/128 = 13500.0 N m at x = 5*L/8 = 2.5 m;
    carry-over identity 24000.0 = 16000.0 + 8000.0 (w*L**2/12 + w*L**2/24)
    residual 0.0.
- Two-span continuous beam, L1 = 5 m uniform w1 = 12000 N/m, L2 = 4 m
  central P2 = 30000 N, simple ends (r = 1, the interior support moment
  M_B is the single redundant):
  - Three-moment (Clapeyron): with t1 = 62500.0 and t2 = 30000.0,
    2*M_B*(L1 + L2) = -6*(t1 + t2), M_B = -30833.3333333333 N m, equal to
    the closed form -3*(t1 + t2)/(L1 + L2); the hogging interior support
    moment magnitude is 30833.3333333333 N m.
  - Reactions from the end moments: R_A = w1*L1/2 + M_B/L1 =
    23833.3333333333 N, R_B = 36166.6666666667 + 22708.3333333333 =
    58875.0 N, R_C = 7291.6666666667 N; the sum 90000.0 N equals
    w1*L1 + P2 with equilibrium residual 1.45519152284e-11.
  - Moment distribution (Hardy-Cross): fixed-end moments -25000.0/+25000.0
    on span 1 and -15000.0/+15000.0 on span 2; joint B distribution
    factors 0.444444444 (span 1) and 0.555555556 (span 2) from the 1/L
    stiffnesses, end supports released with DF = 1, carry-over 1/2.
    Converges in 23 iterations to member end moments at B of
    +30833.3333333333 (span 1 right end) and -30833.3333333333 (span 2
    left end), i.e. the support moment -30833.3333333333 in the
    sagging-positive convention, identical to the three-moment result
    (residual 0.0); the simple-end member end moments sit below 5e-10
    N m.
  - Moment diagram peaks: span 1 peaks at x = R_A/w1 = 1.98611111111 m
    from A with sagging moment 23667.8240740741 N m; span 2 peaks under
    the central load at midspan with 14583.3333333333 N m (30000 - 30833.33
    /2).
- Three-span continuous beam, three equal spans L = 6 m, uniform w =
  10000 N/m (r = 2):
  - Three-moment set: M_1 = M_2 = -36000.0 N m, the Roark/Shigley
    continuous-beam table value -w*L**2/10 for three equal spans; the
    two-span equal-span value -w*L**2/8 is the two-span member of the same
    table.
  - Reactions 24000.0, 66000.0, 66000.0, 24000.0 N (end supports w*L/2 -
    |M|/L = 30000 - 6000), summing to 180000.0 = 3*w*L with residual 0.0.
  - Moment distribution agrees within 3.20142135024e-10 N m in 25
    iterations; the end-span sagging peak is 28800.0 N m at x = 2.4 m and
    the interior span peaks at 9000.0 N m at midspan.
- Symmetric fixed-base portal frame, W = 60000 N central on the beam,
  Lb = 6 m, columns h = 4 m (r = 3, no sidesway by symmetry):
  - FEM = W*Lb/8 = 45000.0 N m hogging at each beam end; the top-joint
    distribution factors are 0.6 (column, 4*E*I/h) and 0.4 (beam,
    4*E*I/Lb). Moment distribution over joints B and C converges in 12
    iterations to: beam end moments +-33750.0 N m (hogging magnitude
    33750.0 at each beam end), column top moments +-33750.0, column base
    moments +-16875.0 (the carry-over halves of the top moments), with
    joint equilibrium residuals 0.0 (B) and 5.67524693906e-10 N m (C).
  - Closed form and cross-check: theta_B = (W*Lb/8)/(4*E*I/h + 2*E*I/Lb)
    = 45000.0/53333333.3333333 = 8.4375e-4 rad and theta_C = -8.4375e-4
    rad (theta_C + theta_B residual 0.0); the direct 2x2 solve of the two
    joint-equilibrium slope-deflection equations reproduces every member
    end moment, maximum difference over the six end moments
    3.49245965481e-10 N m. Base vertical reactions 30000.0 N each (sum
    60000.0), horizontal reactions 0.0.
  - Beam moment diagram: midspan sagging moment W*Lb/4 - 33750.0 =
    56250.0 N m; the elastic beam end moments (33750 hogging) are the
    values the limit-state sibling would take as the elastic peaks on the
    way to its plastic mechanism.
- ValueErrors (11 anchor cases, each raises ValueError): w = 0 on
  fixed_end_moment_uniform; L = 0 on fixed_end_moment_central; negative
  load on clapeyron_term_uniform; a one-span three-moment call; a
  two-term call on three spans; wrong loads arity on
  support_reactions_continuous; unknown load kind "triangular"; unknown
  hardycross kind "parabolic"; ei = 0 on slope_deflection_member; config
  "triangular" on propped_cantilever; negative q on propped_cantilever.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w44spec/anchor_indet.py (stdlib math,
exit 0).

## Validation list (contract test must include)

- fixed_end_moment_uniform(12000, 5) = 25000.0 within 1e-9 relative and
  (10000, 6) = 30000.0; fixed_end_moment_central(30000, 4) = 15000.0
  within 1e-9; each equals the closed form w*L**2/12 or P*L/8 by
  construction.
- clapeyron_term_uniform(12000, 5) = 62500.0 and clapeyron_term_central
  (30000, 4) = 30000.0 within 1e-9 relative; each equals A*xbar/L of the
  simple-span free moment diagram.
- three_moment_support_moments on the two-span case returns
  [-30833.3333333333] within 1e-6 relative, equal to
  -3*(t1 + t2)/(L1 + L2); on the three-span equal case returns
  [-36000.0, -36000.0] within 1e-9, equal to -w*L**2/10 at both interior
  supports.
- support_reactions_continuous: two-span [23833.3333333333, 58875.0,
  7291.6666666667] and three-span [24000.0, 66000.0, 66000.0, 24000.0],
  each within 1e-6 relative; the reaction sum equals the applied load sum
  within 1e-9 relative (anchor residuals 1.45519152284e-11 and 0.0).
- hardycross_beam: support moments equal the three-moment results within
  1e-6 relative (two-span residual 0.0, three-span 3.20142135024e-10);
  member end moments at an interior joint sum to zero within 1e-6 N m;
  simple-end member end moments below 1e-6 N m; the support moment equals
  -end_moments[j-1][1] and end_moments[j][0] within 1e-9 relative.
- slope_deflection_member(4.0e7, 4.0, 0.0, -2.5e-4, -10000.0, 10000.0) =
  (-15000.0, 0.0) within 1e-6 relative and (4.0e7, 4.0, 0.0, -4.0e-4,
  -16000.0, 16000.0) = (-24000.0, 0.0): the zero prop end moment is the
  roller condition of the propped cantilever.
- propped_cantilever("central", 20000.0, 4.0, 4.0e7): fixed_reaction
  13750.0, prop_reaction 6250.0, fixed_end_moment 15000.0,
  prop_rotation -2.5e-4, flexibility 5.33333333333e-07,
  released_deflection 3.33333333333e-03, peak_sagging_moment 12500.0,
  each within 1e-6 relative; consistency_residual within 1e-12 N
  (anchor 0.0); hardycross_fixed_end_moment and sd_fixed_end_moment both
  15000.0 within 1e-6; sd_prop_end_moment 0.0.
- propped_cantilever("uniform", 12000.0, 4.0, 4.0e7): 30000.0, 18000.0,
  24000.0, -4.0e-4, 9.6e-03, 13500.0 at 2.5, each within 1e-6 relative;
  consistency_residual within 1e-15 N (anchor 1.73472347598e-18).
- Carry-over identity: propped fixed-end moment minus (FEM + FEM/2) within
  1e-9 relative for both configs (anchor residual 0.0).
- portal_frame_fixed_base(60000.0, 6.0, 4.0, 4.0e7):
  beam_end_moment_magnitude 33750.0, column_top_moment_magnitude 33750.0,
  column_base_moment_magnitude 16875.0, beam_midspan_sagging_moment
  56250.0, theta_B 8.4375e-4, theta_C -8.4375e-4,
  reaction_vertical_each_base 30000.0, reaction_horizontal_each_base 0.0,
  each within 1e-6 relative; theta_C + theta_B within 1e-15 (anchor 0.0);
  column_base_moment_magnitude equals half the top moment.
- slope_deflection_frame_solve(60000.0, 6.0, 4.0, 4.0e7): theta_B
  8.4375e-4 and theta_C -8.4375e-4 within 1e-9 relative; every member end
  moment of the "moments" dict matches the corresponding
  portal_frame_fixed_base "hardycross" end moment within 1e-6 relative
  (anchor max residual 3.49245965481e-10); the joint equilibrium sums are
  zero within 1e-6 N m.
- Peak moment diagnostics of the worked example (if the module exposes
  the moment line): two-span span-1 peak 23667.8240740741 at
  1.98611111111, span-2 midspan 14583.3333333333, three-span end-span peak
  28800.0 and interior 9000.0 within 1e-6 relative.
- ValueErrors: the 11 anchor cases of the worked example each raise
  ValueError (nonpositive w, L, P, load, ei; one-span call; arity
  mismatches; unknown kinds; unknown config).
- Determinism: two identical runs return identical bits; no imports beyond
  math; no RNG. Contract test file named test_statically_indeterminate.py
  (underscores), unittest, offline in under 20 seconds; logic file named
  statically_indeterminate_logic.py.

## Corpus fragment (eval/hit1-wave44-statically-indeterminate.yaml)

Query 1 (copy verbatim):
  "analyze a statically indeterminate propped cantilever and a continuous
  beam elastically: compute the fixed-end moments of the standard load
  cases, find the interior support moment of the two-span continuous beam
  with the three-moment (Clapeyron) equation, verify it with moment
  distribution (Hardy-Cross) using the stiffness distribution factors and
  the 1/2 carry-over factor, and report the support reactions and end
  moments"
  intent: "structures; elastic redundancy analysis of statically
  indeterminate beams and continuous beams: fixed-end moments of the
  standard load cases, three-moment (Clapeyron) interior support moments,
  moment distribution (Hardy-Cross) verification with distribution
  factors and carry-over, support reactions and end moments"
  expected_skill: "structures/fem/statically-indeterminate"
Query 2 (copy verbatim):
  "find the redundant reactions and the fixed-end moment of a statically
  indeterminate propped cantilever by the consistent deformation (force)
  method with flexibility coefficients and by slope-deflection with joint
  rotations, then report the continuous beam support moments and the
  fixed-base frame end moments under a central beam load"
  intent: "structures; elastic redundant analysis by the consistent
  deformation (force) method with flexibility coefficients and by
  slope-deflection joint rotations: propped cantilever reactions and
  fixed-end moments, continuous-beam support moments, fixed-base frame
  end moments"
  expected_skill: "structures/fem/statically-indeterminate"
Task ids: w44-statically-indeterminate-1 and -2. Prep grep and probe: the
distinctive tokens moment-distribution, slope-deflection, three-moment,
consistent-deformation, fixed-end-moment and statically-indeterminate
each match 0 existing skills/ tasks and 0 eval/hit1-corpus.yaml tasks
(real greps); the prose forms "moment distribution", "Hardy-Cross" and
"Clapeyron" appear nowhere in the tree; the corpus words "redundant" (14
hits) are all reliability or avionics senses (redundant actuation
channels, MIL-STD-1553 bus redundancy, AFDX redundant networks, RBD
parallel units, redundant effectors, beta-factor CCF channels) plus the
two wave-43 plastic-collapse tasks, whose "statically indeterminate
beams" and "propped cantilever" words live inside the LIMIT intent
("plastic collapse (limit) analysis of statically indeterminate beams:
plastic section modulus and shape factor closed forms, plastic hinge
mechanisms and collapse loads by the kinematic (virtual work) theorem"),
so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must find the elastic end moments and
support reactions of statically indeterminate beams and continuous beams:"
and include the outputs in the Claim. First tag: statically-indeterminate.
Additional tags ONLY: three-moment-equation, moment-distribution,
fixed-end-moment, slope-deflection, consistent-deformation,
continuous-beam-support-moment. NEVER single generic words (moment, beam,
frame, load, support, reaction, elastic, structure, analysis, method,
distribution, deflection, rotation, force, span, continuous, indeterminate,
redundant, portal, stiffness) and NEVER sibling tokens: plastic-hinge,
collapse-mechanism, limit-analysis-beam, fully-plastic-moment, shape-factor,
collapse-load-factor (plastic-collapse-analysis, which owns them and the
limit load meaning of "statically indeterminate beams"), portal-frame,
rigid-jointed-frame, euler-bernoulli-beam-element,
rotation-degree-of-freedom, bending-moment-recovery (beam-frame-analysis,
which owns the 6x6 element assembly, the tag portal-frame and the trigger
"portal frame"), gaussian-elimination, direct-stiffness-method,
nodal-displacements, member-forces, element-stiffness-matrix,
global-stiffness-matrix, plane-truss (truss-analysis, which owns
gaussian-elimination and direct-stiffness-method as triggers),
euler-buckling, buckling-load, effective-length, secant-formula
(buckling-analysis, beam-column-analysis), natural-frequency, mode-shape
(beam-vibration, modal-analysis), bimoment, warping-constant,
restrained-warping (same wave), thermal-stress (thermal-stress-analysis),
crippling, inter-rivet-buckling, hertzian, net-section or
metallic-fastener-joints. 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term (the banned word from the builder kit), action
verb present. Recommended wording (outputs in Claim order):
"Use when you must find the elastic end moments and support reactions of
statically indeterminate beams and continuous beams: compute the
fixed-end moments (uniform w*L^2/12 and central P*L/8 hogging at both
fixed ends; w*L^2/8 and 3*P*L/16 hogging at the fixed end of a propped
cantilever), solve the interior support moments with the three-moment
(Clapeyron) equation, apply the moment distribution (Hardy-Cross) method
with distribution factors and the 1/2 carry-over factor, and
the slope-deflection and consistent deformation (force) methods with
flexibility coefficients for propped cantilevers and small frames.
Produces the fixed-end moments, interior support moments, member end
moments, joint rotations, support reactions and the equilibrium and
method-agreement checks in a stdlib-only elastic redundancy analysis.
Trigger: moment distribution, three-moment equation, slope deflection,
fixed-end moment, consistent deformation, statically indeterminate beam,
continuous beam support moment."
The sibling triggers "portal frame", "beam frame analysis", "rigid jointed
frame", "Euler Bernoulli beam element", "truss analysis", "direct
stiffness method", "Gaussian elimination", "nodal displacements", "member
forces", "plastic collapse", "plastic hinge", "collapse mechanism",
"fully plastic moment", "shape factor", "Euler buckling", "natural
frequency" and "thermal stress" must not appear.
