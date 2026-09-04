# Wave-32 leaf spec: complex-number-algebra (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/complex-number-algebra/
- Pack: numerics. In-pack precedent: quaternion-algebra (pure algebra
  kernel leaf). Siblings: fast-fourier-transform (complex as spectral
  OUTPUT), digital-filter-design (pole-pair notes), matrix-operations,
  root-finding, eigenvalue-decomposition.
- Standards id: naca-tr-824 (reference-only; verified pack convention
  across all numerics siblings). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compute complex-number algebra with the Python standard library: form a
complex value from rectangular or polar coordinates, add, subtract,
multiply and divide complex values, take the conjugate, modulus and
argument, raise a complex value to an integer power by De Moivre's
formula, generate the n-th roots of unity, convert between rectangular,
polar and Euler exponential forms, and verify identities such as
z*conj(z) = |z|^2 and e^(i*pi) + 1 = 0. Produces the algebra result set
that gates phasor, impedance, frequency-response and spectral work that
needs an explicit complex toolkit.

Does NOT do: spectral analysis of sampled signals (fast-fourier-transform
owns the DFT/FFT and the magnitude and phase SPECTRA of a time series);
IIR/FIR filter design (digital-filter-design and fir-filter-design own
coefficient synthesis); solving for polynomial complex roots
(root-finding and eigenvalue-decomposition own root solvers - do not add
general polynomial root finding here); quaternion algebra
(quaternion-algebra owns the 4-element rotation algebra); matrix
operations (matrix-operations owns dense linear algebra). This leaf owns
the scalar complex-number algebra kernel only: representation,
arithmetic, powers, roots of unity, conversions.

## Model (implement exactly)

Represent a complex number as a tuple (re, im) of floats. cmath is
stdlib but the leaf must implement the arithmetic itself as pure math
over re/im tuples (the quaternion-algebra precedent reimplements the
product rather than delegating), so the logic is transparent,
deterministic and testable to exact assertions.

Functions (pure stdlib math only, no cmath calls for the core ops):

- rect(re, im) -> (re, im) as a 2-tuple. (No normalization.)
- modulus(z) -> hypot: math.hypot(re, im) (exact, overflow-safe).
- arg(z) -> math.atan2(im, re) in radians in (-pi, pi].
- conjugate(z) -> (re, -im).
- complex_add(z1, z2) -> (re1+re2, im1+im2).
- complex_sub(z1, z2) -> (re1-re2, im1-im2).
- complex_mul(z1, z2) -> (re1*re2 - im1*im2, re1*im2 + re2*im1).
- complex_div(z1, z2) -> multiply by conjugate over |z2|^2:
  denom = re2^2 + im2^2; ValueError if denom == 0;
  ((re1*re2 + im1*im2)/denom, (im1*re2 - re1*im2)/denom).
- polar(z) -> (modulus, arg) 2-tuple.
- from_polar(r, theta) -> (r*math.cos(theta), r*math.sin(theta)).
  ValueError if r < 0.
- exp_imag(theta) -> (math.cos(theta), math.sin(theta)) = e^(i theta).
- complex_pow(z, n) -> De Moivre: z^n = r^n * (cos(n*theta) +
  i*sin(n*theta)); n integer >= 0; ValueError for negative n and for
  n=0 with z = (0,0) (0^0 undefined). Use from_polar(modulus(z)**n,
  n*arg(z)); round tiny imaginary parts caused by float trig when the
  result is on the real axis (abs(im) < 1e-12 -> 0.0) so (1+i)^8 gives
  exactly (16.0, 0.0).
- roots_of_unity(n) -> list of n tuples e^(2*pi*i*k/n) for k in
  0..n-1: [(math.cos(2*pi*k/n), math.sin(2*pi*k/n)) for k in range(n)].
  ValueError if n <= 0. Round near-zero coordinates (< 1e-12) to 0.0 so
  the 4th roots are exactly (1,0), (0,1), (-1,0), (0,-1).
- mag_phase(z) -> (modulus, arg) - alias of polar for the phasor
  vocabulary.
- is_close(z1, z2, tol=1e-9) -> max(abs(re1-re2), abs(im1-im2)) < tol.

Convenience dict:
- complex_algebra(z1, z2, n=None) -> {z1, z2, sum, difference, product,
  quotient, conjugate_z1, modulus_z1, argument_z1_deg, polar_z1,
  power_z1_n (when n is not None), roots_n (when n is not None)} where
  argument_z1_deg = math.degrees(arg(z1)). ValueErrors propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Run your module and take the real printed outputs as assert targets
(many are EXACT rational results; transcendental identities via
math.isclose at 1e-12):

- (3,4) * (2,-1): exact (10, 5) -> (10+5i).
- (1,2) / (3,-4): divide by the conjugate denominator: (1+2i)/(3-4i)
  = ((1+2i)(3+4i))/(3^2+4^2) = ((-5)+(10)i)/25 = (-0.2, 0.4) exactly.
  The function formula (re1*re2 + im1*im2, im1*re2 - re1*im2)/denom
  with (re1,im1)=(1,2), (re2,im2)=(3,-4) gives re = (3-8)/25 = -0.2,
  im = (6+4)/25 = 0.4.  CORRECT.
- (3,4) * conjugate(3,4) = (25, 0) = |z|^2 exactly.
- (1,1)^8: De Moivre r = sqrt(2), theta = pi/4 -> r^8 = 16, 8*theta =
  2*pi -> (16, ~0) -> rounded (16.0, 0.0).
- 4th roots of unity: [(1,0), (0,1), (-1,0), (0,-1)], sum to (0,0).
- from_polar(1, pi/2) -> (0, 1) exactly (within 1e-12).
- exp_imag(pi) + (1,0) = (0, ~0) -> e^(i*pi)+1 = 0 within 1e-12.
- complex_div((1,2),(3,-4)) = (-0.2, 0.4) exactly.

If a value is outside its bound or does not match, your implementation
has a bug: find it before writing tests. Show real outputs in the SKILL
worked example (do not invent them).

## Validation list (contract test must include)

- ValueError: division by zero (complex_div((1,2),(0,0))); negative n in
  complex_pow; n=0 with z=(0,0); from_polar negative radius; n <= 0 in
  roots_of_unity.
- Exact rational assertions: the product, quotient, conjugate and
  modulus cases above assert exact float equality (10.0, 5.0 etc.).
- De Moivre identity: complex_pow((1,1),8) == (16.0, 0.0).
- Conjugate identity: complex_mul(z, conjugate(z))[0] == modulus(z)**2.
- Roots of unity: len == n; k-th root raised to n returns (1,0) within
  1e-12 (verify with complex_pow); sum of all n roots == (0,0) within
  1e-12 for n = 2, 3, 4, 5.
- Polar round trip: from_polar(*polar(z)) == z within 1e-12 for several
  z including negative-imaginary cases.
- Euler identity: exp_imag(math.pi) == (-1.0, ~0) within 1e-12.
- Determinism: no RNG, run-to-run identical.
- Convenience dict contains exactly the documented keys; n=None omits
  the power/roots keys.

## Corpus fragment (eval/hit1-wave32-complex-number-algebra.yaml)

Query 1 (copy verbatim):
  "compute the product quotient and polar form of two complex numbers for an AC impedance phasor calculation, and verify z times its conjugate equals the squared modulus"
  intent: "cross-cutting; complex number arithmetic and polar conversion"
  expected_skill: "cross-cutting/numerics/complex-number-algebra"
Query 2 (copy verbatim):
  "determine the fourth roots of unity and the power of a complex number by De Moivre formula for a frequency-domain rotation check"
  intent: "cross-cutting; De Moivre powers and roots of unity"
  expected_skill: "cross-cutting/numerics/complex-number-algebra"
Task ids: w32-complex-number-algebra-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute complex-number algebra
with the Python standard library:" and include the outputs in the Claim.
First tag: complex-number-algebra. Additional tags ONLY: complex-
arithmetic, polar-form, euler-formula, de-moivre, roots-of-unity,
phasor-math. NEVER single generic words (complex, numbers, algebra,
arithmetic, math). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): magnitude spectrum, phase
spectrum, frequency bin, Parseval, FFT, DFT, Cooley-Tukey
(fast-fourier-transform); filter coefficients, cutoff, passband, IIR,
FIR (digital-filter-design / fir-filter-design); polynomial roots,
eigenvalue, Jacobi, power iteration (root-finding /
eigenvalue-decomposition); quaternion, rotation algebra
(quaternion-algebra). The word "phasor" is allowed in the description
(as an application domain) but not "spectrum".

Tags: [complex-number-algebra, complex-arithmetic, polar-form,
euler-formula, de-moivre, roots-of-unity, phasor-math]

Sibling-citation lines for Related leaves: quaternion-algebra (in-pack
pure-algebra precedent), fast-fourier-transform, digital-filter-design,
root-finding, matrix-operations. Standards note: naca-tr-824 pack
convention; no complex-math standard exists in standards-map.yaml.

Ledger Standard: naca-tr-824.
