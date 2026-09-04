# Wave-33 leaf spec: beam-vibration (structures, fem pack)

- Path: skills/structures/fem/beam-vibration/
- Pack: fem. Sibling: structures/fem/modal-analysis (2-DOF lumped
  mass-spring natural frequencies/mode shapes only - its own title and
  every sibling fence describe it that way); loads/random-vibration-
  analysis (SDOF Miles PSD), loads/shock-response-spectrum (SDOF);
  cross-cutting/numerics/eigenvalue-decomposition (generic matrix
  eigensolver, no continuous-member physics). This leaf owns continuous
  distributed-parameter Euler-Bernoulli beam natural frequencies.
- Standards id: far-25 (reference-only). Ledger Standard: far-25.
- Family: structures

## Claim

Compute the exact natural frequencies of a continuous Euler-Bernoulli
beam under pinned-pinned, cantilever, clamped-clamped, and free-free
end conditions from the transcendental characteristic-equation roots,
plus a Rayleigh-quotient fundamental estimate for non-uniform members.
Produces the member natural frequencies in hertz for vibration
clearance and excitation checks - the continuous-member complement to
the discrete 2-DOF lumped modal-analysis leaf.

Does NOT do: 2-DOF mass-spring systems (modal-analysis); SDOF random
vibration or shock spectra (loads pack); matrix eigensolvers
(cross-cutting numerics); finite-element assembly; forced response.

## Model (implement exactly)

Conventions: bending stiffness EI (N m^2), mass per unit length m
(kg/m), length L (m). Exact frequencies from the characteristic
equation roots beta_n L:
- Pinned-pinned: beta_n L = n pi; f_n = (n pi / L)^2 sqrt(EI/m) / 2pi
  = n^2 pi^2 sqrt(EI / (m L^4)) / 2pi.
- Cantilever: roots of cos x cosh x = -1; beta_1 L = 1.87510407,
  beta_2 L = 4.69409113, beta_3 L = 7.85475744.
- Clamped-clamped and free-free: roots of cos x cosh x = 1;
  beta_1 L = 4.73004074, beta_2 L = 7.85320462.
- f_n = (beta_n L)^2 sqrt(EI / (m L^4)) / 2pi.
- Rayleigh quotient fundamental (non-uniform / shape check):
  omega^2 = int_0^L EI phi''^2 dx / int_0^L m phi^2 dx. For a uniform
  cantilever with the parabolic shape phi = (x/L)^2 this gives
  omega^2 = 20 EI / (m L^4) (upper bound, about 1.272x the exact
  fundamental 3.51602^2 = 12.3624... check the ratio sqrt(20)/3.51602).

Functions (pure stdlib):

- pinned_pinned_frequency(mode_n, ei, mass_per_len, length_m) -> Hz
  (formula above). ValueErrors on non-positive inputs, n < 1.
- characteristic_root(mode_n, bc, tol=1e-12) -> beta_n L by bisection:
  cantilever: cos x cosh x = -1, root n lies in ((n-1)pi, n pi) for
  n >= 1 (n=1 in (pi/2? - use a safe bracket helper; documented
  intervals: n=1 in (1.8, 2.0), n>=2 in ((n-1)pi, n pi)); clamped/
  free-free: cos x cosh x = 1, root n in ((n-1)pi + pi/2? use the
  documented bracket (n-0.5)pi +/- margin - the builder must verify the
  bisection brackets contain the published roots). Provide pinned-pinned
  exact roots separately (n pi).
- beam_frequency(beta_n_L, ei, mass_per_len, length_m) -> Hz =
  (beta_n_L)^2 sqrt(EI / (m L^4)) / 2pi. ValueErrors on non-positive
  inputs.
- cantilever_frequency(mode_n, ei, mass_per_len, length_m) -> Hz.
- clamped_clamped_frequency(mode_n, ei, mass_per_len, length_m) -> Hz.
- free_free_frequency(mode_n, ei, mass_per_len, length_m) -> Hz
  (zero-frequency rigid-body modes exist; report only the elastic
  modes n >= 1; document that the first elastic free-free root is
  4.73004074).
- rayleigh_fundamental(ei, mass_per_len, length_m, shape="cantilever-
  parabola") -> Hz using omega^2 = 20 EI/(m L^4) for the uniform
  cantilever parabola (the only shape required; document it as an upper
  bound to the exact fundamental).
- beam_mode_frequencies(bc, n_modes, ei, mass_per_len, length_m) ->
  list of Hz for modes 1..n_modes for the given boundary condition.
  ValueErrors on invalid bc names.

## Worked example

Aluminum beam: E = 73.1 GPa, rho = 2780 kg/m3, cross-section 50 x
100 mm, L = 2 m. I = b h^3 / 12 = 0.05 * 0.1^3 / 12 = 4.1667e-6 m^4;
m = rho * b * h = 13.9 kg/m.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- Cantilever roots by bisection: 1.875104, 4.694091, 7.854757 (match
  published Blevins values to 5-6 dp).
- Cantilever f1 about 20.709 Hz, f2 about 129.780 Hz, f3 about
  363.389 Hz.
- Pinned-pinned f1 about 58.131 Hz.
- Clamped-clamped f1 about 131.776 Hz.
- Rayleigh x^2 cantilever estimate about 26.340 Hz = 1.272x the exact
  f1 (upper-bound property).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive ei/mass/length; mode < 1; invalid bc name.
- Published-root assertions: cantilever roots within 1e-5 of
  1.87510407 / 4.69409113 / 7.85475744; clamped roots within 1e-5 of
  4.73004074 / 7.85320462.
- Pinned-pinned closed form: f1 of the worked beam about 58.131 Hz and
  exactly f_n = n^2 f_1 (assert the ratio).
- Rayleigh bound: rayleigh_fundamental > cantilever f1 (about 1.272x).
- Free-free: first elastic mode frequency equals the clamped-clamped
  first mode (same root 4.73004074); document zero rigid-body modes.
- Determinism: identical floats run-to-run.
- beam_mode_frequencies returns n_modes entries ascending.

## Corpus fragment (eval/hit1-wave33-beam-vibration.yaml)

Query 1 (copy verbatim):
  "compute the first three natural frequencies of the euler bernoulli cantilever beam from the characteristic equation roots and the bending stiffness"
  intent: "structures; continuous Euler-Bernoulli cantilever beam natural frequencies from characteristic roots"
  expected_skill: "structures/fem/beam-vibration"
Query 2 (copy verbatim):
  "estimate the fundamental frequency of the non uniform cantilever spar with the rayleigh quotient method for a vibration clearance check"
  intent: "structures; Rayleigh-quotient fundamental frequency of a beam member"
  expected_skill: "structures/fem/beam-vibration"
Task ids: w33-beam-vibration-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the natural
frequencies of a continuous beam member:" and include the outputs in
the Claim. First tag: beam-vibration. Additional tags ONLY:
euler-bernoulli-beam, characteristic-equation-roots, cantilever-beam,
pinned-pinned-beam, clamped-beam-frequency, rayleigh-quotient. NEVER
single generic words (beam, frequency, vibration, mode, modal,
structure). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): mass spring, two degree of
freedom, mode shape ratio, lumped (modal-analysis 2-DOF); Miles, PSD,
shock response spectrum (loads pack); matrix eigenvalue, Jacobi, power
iteration (cross-cutting eigenvalue-decomposition); truss, frame,
buckling, plate. The tokens "continuous beam", "characteristic
equation", "cantilever", "Euler-Bernoulli", "Rayleigh quotient" are
this leaf's own.

Tags: [beam-vibration, euler-bernoulli-beam,
characteristic-equation-roots, cantilever-beam, pinned-pinned-beam,
clamped-beam-frequency, rayleigh-quotient]

Sibling-citation lines for Related leaves:
structures/fem/modal-analysis (discrete 2-DOF sibling; this leaf is the
continuous-member complement),
structures/loads/random-vibration-analysis,
cross-cutting/numerics/eigenvalue-decomposition.

Ledger Standard: far-25.
