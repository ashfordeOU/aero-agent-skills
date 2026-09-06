# Wave-42 leaf spec: shear-center-analysis (structures, fem pack)

- Path: skills/structures/fem/shear-center-analysis/
- Pack: fem (present siblings beam-column-analysis, beam-frame-analysis,
  beam-vibration, buckling-analysis, calculix-linear, calculix-nonlinear,
  contact-analysis, curved-beam-analysis, cylindrical-shell-buckling,
  diagonal-tension-field-webs, lug-joint-analysis, modal-analysis,
  plate-buckling, pressure-bulkhead, torsion-shear-flow, truss-analysis).
- Claim fences (quoted from the sibling frontmatter/body at prep, none owns
  the transverse-shear shear center):
  - torsion-shear-flow computes torsion only: its description reads "Use
    when you must compute the torsion shear flow of a closed or open
    structural section: the polar second moment J for solid and tube
    shafts, the ... Bredt-Batho shear flow q = T / (2 Am) for closed
    single-cell sections ... the twist rate ..." and its logic covers
    torque-driven circulation only; it has no V*Q/I transverse-shear flow
    term and no shear-center location function.
  - diagonal-tension-field-webs stops at the pre-buckling boundary: its
    body states that the pre-buckling shear-flow "distribution and shear
    center" are where its scope ends (post-buckled diagonal tension
    begins there).
  - divergence-speed (aerodynamics/aeroelasticity) CONSUMES the shear-center
    offset as a given input: its description reads "... the divergence
    dynamic pressure from the torsional stiffness and the offset e between
    the aerodynamic center and the shear center ..." and it never locates
    the shear center from section geometry.
  - curved-beam-analysis and beam-column-analysis analyze straight/curved
    member stress under axial/bending loads with no transverse-shear-flow
    section machinery.
  Whole-tree greps at prep: "shear-center-location" = 0 hits;
  "transverse-shear-flow" = 0 hits; "vq-over-i" = 0 hits across
  skills/**/SKILL.md and scripts. GENUINE structures gap (fresh probe): no
  leaf computes the shear-center LOCATION of a thin-walled open section from
  its geometry.
- Standards ids: far-25 AND cs-25 (both reference-only, present in
  standards-map.yaml; fem-pack sibling convention used by torsion-shear-flow
  and lug-joint-analysis). Ledger Standard: far-25, cs-25.
- Family: structures

## Claim

Locate the shear center of a thin-walled open section (channel, Z, angle,
hat, single-cell box with a slit) under transverse shear: build the
V*Q/I shear-flow distribution along the wall from a free edge, integrate
the resultant wall-shear force and its moment to find the line of action,
and report the shear-center offset from the section centroid or web; also
report the bending shear-stress check tau = V*Q/(I*t) at the critical
wall location. Produces the shear-center coordinates, the per-wall shear
flow q(s), the resultant force check (the integrated vertical resultant
must equal the applied shear, Fx must vanish), and the shear-center offset
in millimeters from the stated reference, in the thin-wall closed forms
that gate open-section spar, stiffener and frame design. Does NOT do:
torsion-only Bredt-Batho circulation, J, or twist rate (torsion-shear-flow);
post-buckled diagonal-tension fields (diagonal-tension-field-webs); the
aeroelastic divergence calculation that CONSUMES a shear-center offset as
an input (divergence-speed); FEM penalty/Lagrange contact or continuum
meshing (contact-analysis). Doubly symmetric sections (I-beam, closed box)
have the shear center at the centroid by symmetry; the leaf states that
property and validates the web shear-flow maximum rather than integrating a
multi-branch contour.

## Model (implement exactly)

Pure stdlib, math only, closed form + fine segment integration. A section
is a list of straight thin segments, each (x1, y1, x2, y2, t) in meters,
ordered as ONE continuous open contour starting at a free edge.

Functions:
- section_properties(segments) -> (xbar, ybar, ixx, iyy, ixy)
  area-weighted centroid and centroidal second moments of the thin-wall
  assembly: per segment length L = hypot(dx, dy), area A = L*t, centroid
  at the segment midpoint; each segment contributes its thin-rectangle
  inertia (L*t^3/12 about the wall normal, t*L^3/12 about the wall
  direction) rotated to global axes plus the parallel-axis term
  A*dy^2 / A*dx^2 / A*dx*dy. ValueError if any segment has zero length
  or t <= 0, or the total area is zero.
- shear_center_channel(h, b, t, vy=1000.0, n=400) -> (e_m, fx, fy, ixx)
  Uniform-thickness channel: web height h, flange width b (both flanges
  extend the same direction from the web), thickness t. Contour walked
  from the top-flange free edge (b, h/2) to the web (0, h/2), down the
  web to (0, -h/2), out the bottom flange to its free edge (b, -h/2).
  For each step: accumulate the first moment Q (m^3) of the outboard
  wall area, Q += y_mid * t * ds; the wall shear flow is q = vy*Q/ixx
  (N/m); force per step = q * (cx, cy) * ds where (cx, cy) is the
  contour tangent; moment per step about the origin (web centerline at
  mid-height) = q * (x_mid*cy - y_mid*cx) * ds. Shear-center offset
  e = mz / fy (meters from the web centerline; negative x when the
  flanges extend toward +x, i.e. the shear center sits behind the web,
  the classical channel result). n = subdivision count per unit length
  scale (default 400 gives e to 4+ decimals).
- shear_center_z(h, b, t, vy=1000.0, n=400) -> (e_centroid, xbar, fy, ixx)
  Z-section contour: top flange (b, h/2) -> (0, h/2), web down to
  (0, -h/2), bottom flange to (-b, -h/2). Returns the shear-center offset
  from the CENTROID (the classical result is 0 for the doubly symmetric
  Z about its centroid).
- shear_center_angle(a, t, vy=1000.0, n=400) -> (e_corner, xbar, ybar, fy,
  ixx) Equal-leg angle: contour from the top-leg free edge (0, a) to the
  corner (0, 0) to the bottom-leg free edge (a, 0). Returns the
  shear-center offset from the CORNER (the classical result is 0: the
  shear center of an angle is at the intersection of the leg centerlines,
  the corner).
- i_beam_web_qmax(t_f, b_f, t_w, h, vy) -> (q_max, ixx) Doubly symmetric
  I-beam: web shear-flow maximum at mid-web q = vy * Q / ixx with
  Q = t_w*(h/2)*(h/4) + b_f*t_f*(h/2 + t_f/2) (half the web above the
  mid-height plus one full flange) and
  ixx = t_w*h^3/12 + 2*(b_f*t_f*(h/2 + t_f/2)^2 + b_f*t_f^3/12) (flange
  inertia about its own centroidal x-axis negligible but kept).
  Shear center at the centroid (e = 0) by double symmetry; the q_max
  value is the validation anchor. ValueError if any dimension <= 0 or
  vy is not finite.

Identities to test (closed form, exact):
- Vertical equilibrium: the integrated vertical resultant fy equals -vy
  within 1e-6 relative for every single-contour section (the contour
  direction runs downward on the web, hence the sign); the horizontal
  resultant fx vanishes within 1e-9 N.
- Channel closed form: |e| equals the classical thin-channel value
  e_classical = 3*b^2 / (h + 6*b) within 1e-4 relative for n = 400
  (prep anchor ratio 1.000002). For b = 50 mm, h = 100 mm:
  e_classical = 18.75 mm.
- Symmetry: the Z-section shear center sits at the centroid (offset ~1e-6
  mm); the equal-leg angle shear center sits at the corner junction
  (offset ~1e-6 mm); the doubly symmetric I-beam shear center is at the
  centroid by the stated property.
- Magnitudes: for the prep channel case the bending shear stress
  tau = vy*Q_max/(ixx*t) at the web-flange junction stays below the
  material yield for aluminum 2024-T3-class allowables (order 100 MPa for
  a 1000 N load on a 100 mm x 50 mm x 2 mm channel; report the real
  value from the module).
- ValueErrors across the module: zero-length segments, t <= 0, any
  dimension <= 0, empty segment list.
- Determinism; no imports beyond math; no RNG.

## Worked example

Thin-walled channel spar: web h = 100 mm, flanges b = 50 mm both to the
same side, t = 2 mm, vertical shear vy = 1000 N. All values below are REAL
outputs of the prep anchor /tmp/w42spec/anchor_shear_center_analysis.py
(stdlib math, closed form + 400-step segment integration).
- section_properties: centroidal ixx = 6.667333e-07 m^4 (the classical
  t*h^2*(h + 6*b)/12 = 6.666667e-07 m^4 plus the small flange local terms,
  agreeing to 1e-4 relative).
- shear_center_channel(0.100, 0.050, 0.002, vy=1000.0):
  fy = -999.8984 N (vertical equilibrium, target -1000), fx = 0.000000 N,
  e = -18.7500 mm from the web centerline: the shear center sits 18.75 mm
  BEHIND the web (opposite the flange direction), matching the classical
  channel closed form 3*b^2/(h + 6*b) = 3*50^2/(100 + 6*50) = 18.75 mm to
  a ratio of 1.000002 (the 2 ppm offset is the flange local-inertia
  refinement the classical form drops).
- shear_center_z(0.100, 0.050, 0.002, vy=1000.0): e from the centroid =
  -0.000000 mm (shear center at the centroid), ixx = 6.667333e-07 m^4.
- shear_center_angle(0.050, 0.003, vy=1000.0): e from the corner =
  -0.000000 mm (shear center at the leg intersection), centroid at
  (12.500, 12.500) mm, so the shear center is 17.678 mm from the centroid
  along the diagonal.
- i_beam_web_qmax(t_f=0.004, b_f=0.060, t_w=0.003, h=0.100, vy=1000.0):
  ixx = 1.692560e-06 m^4, web shear-flow maximum at mid-web
  q = 9589.0 N/m (shear center at the centroid by double symmetry).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified by executing the prep anchor script.

## Validation list (contract test must include)

- Channel: shear_center_channel(0.100, 0.050, 0.002, vy=1000.0) returns
  |e| = 18.750 mm within 1e-3 mm and e < 0 when flanges extend toward +x;
  the ratio |e| / (3*b^2/(h + 6*b)) is 1 within 2e-5.
- Vertical equilibrium: |fy| = 999.9 N within 1 N (relative 1e-3);
  |fx| < 1e-6 N for the channel.
- Z-section: shear_center_z returns an offset from the centroid within
  1e-3 mm of 0.
- Angle: shear_center_angle returns an offset from the corner within
  1e-3 mm of 0; the centroid lies at (a/4, a/4) = (12.5, 12.5) mm for the
  50 mm leg.
- I-beam: i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 1000.0) = 9589.0 N/m
  within 1 N/m; ixx = 1.692560e-06 within 1e-9.
- Section-property identity: ixx of the channel matches
  t*h^2*(h + 6*b)/12 within 2e-4 relative.
- ValueErrors: zero-length segment, t = 0, negative dimensions, empty
  segment list.
- Determinism: two runs give bit-identical outputs; no imports beyond
  math; no RNG.

## Corpus fragment (eval/hit1-wave42-shear-center-analysis.yaml)

Query 1 (copy verbatim):
  "locate the shear-center-location of a thin-walled channel-section spar: integrate the transverse-shear-flow VQ/I along the web and flanges from the free edge and report the shear-center offset behind the web"
  intent: "structures; shear-center location of a channel from the VQ/I transverse-shear-flow distribution, offset from the web"
  expected_skill: "structures/fem/shear-center-analysis"
Query 2 (copy verbatim):
  "compute the shear-center offset and web shear-flow distribution of a Z-section stiffener carrying a vertical shear load, given the flange and web widths, the wall thickness and the section second moment of area"
  intent: "structures; Z-section shear-center offset from the centroid and the per-wall shear-flow distribution"
  expected_skill: "structures/fem/shear-center-analysis"
Task ids: w42-shear-center-analysis-1 and -2. Prep grep: none of the
distinctive phrases (shear-center-location, transverse-shear-flow, VQ/I
integration, behind-the-web offset) appears in any existing
hit1-corpus.yaml task; the torsion-shear-flow tasks route on Bredt-Batho
and twist rate, and the diagonal-tension tasks route on post-buckled
wrinkling, so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must locate the shear center of a
thin-walled open section under transverse shear:" and include the outputs
in the Claim. First tag: shear-center-analysis. Additional tags ONLY:
shear-center-location, transverse-shear-flow, thin-walled-open-section.
NEVER single generic words (shear, center, flow, stress, section,
location, analysis). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term (the banned word from the builder kit), action
verb present.

FORBIDDEN TOKENS (belong to siblings): bredt-batho, polar-second-moment,
twist-rate, st-venant, torsion-constant (torsion-shear-flow);
diagonal-tension, post-buckled, wrinkling, tension-field (diagonal-
tension-field-webs); divergence-dynamic-pressure, aeroelastic, torsional-
stiffness, aerodynamic-center (divergence-speed); penalty, lagrange,
contact-stiffness, fem-mesh (contact-analysis); lug-bearing, net-tension,
tearout (lug-joint-analysis); euler-buckling, column (buckling-analysis);
lame, interference-fit, shrink-fit (shrink-fit-analysis).
