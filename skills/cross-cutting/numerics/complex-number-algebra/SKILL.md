---
name: complex-number-algebra
description: "Use when you must compute complex-number algebra with the Python standard library: form a complex value from rectangular or polar coordinates, add, subtract, multiply and divide complex values, take the conjugate, modulus and argument, raise a complex value to an integer power by De Moivre's formula, generate the n-th roots of unity, and convert between rectangular, polar and Euler exponential forms, verifying identities such as z times its conjugate equals the squared modulus and e to the i pi plus 1 equals 0. Produces the algebra result set that gates phasor, impedance, frequency-response and AC circuit work that needs an explicit complex toolkit. Trigger: complex-number-algebra, complex-arithmetic, polar-form, euler-formula, de-moivre, roots-of-unity, phasor-math, rectangular-form, complex-conjugate."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [complex-number-algebra, complex-arithmetic, polar-form, euler-formula, de-moivre, roots-of-unity, phasor-math]
  version: 0.1.0
  author: AeroSkills
---

# Complex-Number Algebra (cross-cutting/numerics/complex-number-algebra)

Use when you must compute complex-number algebra with the Python
standard library: forming a value from rectangular or polar
coordinates, the four arithmetic operations, conjugate, modulus and
argument, integer powers by De Moivre's formula, the n-th roots of
unity, and conversions between rectangular, polar and Euler
exponential forms. This leaf implements the scalar complex algebra
kernel as pure math over (re, im) float tuples, stdlib only, so every
operation is transparent, deterministic and assertable to exact float
equality on rational results. It pairs with
cross-cutting/numerics/quaternion-algebra (the in-pack precedent: a
pure algebra kernel that reimplements its product over coordinates
rather than delegating). It does not do spectral analysis of sampled
signals, filter coefficient synthesis, polynomial root solving,
matrix linear algebra or quaternion algebra, which belong to the
sibling leaves listed below.

## Domain quick reference

- Representation: a complex value is a tuple (re, im) of floats,
  built by rect(re, im). No cmath: arithmetic is implemented over the
  coordinates.
- Modulus and argument: |z| = math.hypot(re, im), arg(z) =
  math.atan2(im, re) in radians in (-pi, pi]; polar(z) returns
  (modulus, arg), and mag_phase is the same pair under the phasor
  vocabulary.
- Product: (re1 + i*im1)*(re2 + i*im2) = (re1*re2 - im1*im2) + i*(re1*im2
  + re2*im1).
- Quotient: z1/z2 multiplies by the conjugate of z2 over |z2|^2, so
  ((re1*re2 + im1*im2), (im1*re2 - re1*im2)) / (re2^2 + im2^2);
  ValueError when the denominator is exactly zero.
- Conjugate identity: z * conj(z) = (|z|^2, 0), e.g. (3+4i)(3-4i) = 25.
- Polar form: from_polar(r, theta) = (r*cos(theta), r*sin(theta));
  ValueError for a negative radius.
- Euler exponential form: exp_imag(theta) = (cos(theta), sin(theta)) =
  e^(i*theta); Euler identity e^(i*pi) + 1 = 0.
- De Moivre power: complex_pow(z, n) computes z^n = r^n*(cos(n*theta)
  + i*sin(n*theta)) for integer n >= 0 via from_polar(modulus(z)**n,
  n*arg(z)); ValueError for negative n and for 0^0.
- Roots of unity: roots_of_unity(n) lists e^(2*pi*i*k/n) for k in
  0..n-1; ValueError when n <= 0. Near-zero coordinates are rounded to
  0.0 so the 4th roots are exactly (1,0), (0,1), (-1,0), (0,-1).
- The n roots sum to 0 and every k-th root raised to n returns
  (1, 0): both identities are deterministic contract checks.
- NACA-TR-824 is the pack reference convention only; no complex-math
  standard exists in standards-map.yaml, and the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Form the values: rect(re, im) for rectangular inputs, or
   from_polar(r, theta) when the inputs come in magnitude and phase.
2. Run the arithmetic: complex_add, complex_sub, complex_mul,
   complex_div (the quotient raises ValueError on an exact zero
   denominator).
3. Read the geometry: modulus, arg (radians) or
   math.degrees(arg(z)), conjugate, and polar(z) or its alias
   mag_phase(z) for the phasor vocabulary.
4. Raise to an integer power with complex_pow(z, n) by De Moivre's
   formula; the real-axis cleanup returns exactly (16.0, 0.0) for
   (1+i)^8.
5. Generate the n-th roots of unity with roots_of_unity(n) when a
   rotation grid or n-fold symmetry check is needed.
6. Verify identities: complex_mul(z, conjugate(z)) equals
   (modulus(z)**2, 0.0), from_polar(*polar(z)) round-trips to z, and
   complex_add(exp_imag(math.pi), (1, 0)) equals (0, 0) to float
   precision.
7. Collect the full result set for a value pair with complex_algebra
   (z1, z2, n=None); pass n to include power_z1_n and roots_n.
8. Compare results with is_close(z1, z2, tol=1e-9) and confirm the
   contract test below.

## Worked example

Run on the module (scripts/complex_number_algebra_logic.py), real
outputs shown:

- (3+4i) * (2-i): complex_mul((3, 4), (2, -1)) = (10.0, 5.0), exact.
- (1+2i) / (3-4i): complex_div((1, 2), (3, -4)) = (-0.2, 0.4), exact
  (conjugate denominator (3+4i): numerator (1+2i)(3+4i) = -5+10i over
  3^2+4^2 = 25).
- (3+4i) * conjugate((3, 4)) = (25.0, 0.0) = |3+4i|^2, exact.
- (1+i)^8: De Moivre with r = sqrt(2), theta = pi/4 gives r^8 = 16,
  8*theta = 2*pi, and complex_pow((1, 1), 8) = (16.0, 0.0), exact.
- 4th roots of unity: [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0),
  (0.0, -1.0)], which sum to (0.0, 0.0).
- from_polar(1, pi/2) = (6.1e-17, 1.0), equal to (0, 1) within 1e-12.
- exp_imag(math.pi) + (1, 0) = (0.0, 1.2e-16), so e^(i*pi) + 1 = 0
  within 1e-12.
- polar((3, 4)) = (5.0, 0.927295218 rad), argument 53.130 degrees.

## Verification

- Rational results assert exact float equality: the (10.0, 5.0)
  product, the (-0.2, 0.4) quotient, the (25.0, 0.0) conjugate
  product, and complex_pow((1, 1), 8) == (16.0, 0.0).
- Transcendental identities use math.isclose at 1e-12: the Euler
  identity, the polar round trip, and the De Moivre check that every
  k-th root of unity raised to n returns (1, 0).
- ValueError rejection: division by (0, 0), negative exponent in
  complex_pow, 0^0, negative radius in from_polar, and n <= 0 in
  roots_of_unity.
- Determinism: no RNG anywhere; repeated runs return identical dicts
  from complex_algebra.
- Run the offline contract test: python3
  scripts/test_complex_number_algebra.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/quaternion-algebra: the in-pack pure algebra
  kernel precedent (4-element algebra over coordinates).
- cross-cutting/numerics/fast-fourier-transform: consumes complex
  values as the output of spectral transforms of sampled signals.
- cross-cutting/numerics/digital-filter-design: pole and zero
  placement work that uses complex arithmetic on the frequency grid.
- cross-cutting/numerics/root-finding: solving for polynomial roots,
  outside this leaf's scope.
- cross-cutting/numerics/matrix-operations: dense linear algebra on
  arrays, outside this leaf's scope.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_complex_number_algebra.py

The test covers the worked-example arithmetic (exact product,
quotient, conjugate and modulus results), De Moivre powers including
the exact (16.0, 0.0) case, the n-th roots of unity and their sum and
power identities for n = 2..8, polar and Euler round trips at 1e-12,
the complex_algebra convenience dict key and value contract, is_close
tolerance behavior, determinism, and ValueError rejection of division
by zero, negative and zero-zero powers, negative radii and non-positive
root counts.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 is the numerics
  pack reference convention (reference-only in standards-map.yaml); no
  complex-math standard exists there. All relations above are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
