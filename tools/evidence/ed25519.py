#!/usr/bin/env python3
"""Ed25519 (RFC 8032), pure standard library.

Why this is here rather than a dependency
-----------------------------------------
The product claim is "a verdict somebody else can check". A verifier that
first requires `pip install cryptography` is a verifier most people will not
run, and a format nobody can check without a toolchain does not become a
standard. Verification has to work on a bare Python 3, offline, anywhere.

So the VERIFIER is stdlib. The implementation is the RFC 8032 reference
algorithm, and the test suite cross-validates every operation against two
independent implementations (pyca/cryptography and the OpenSSL CLI) as well
as the RFC's own published test vectors. Hand-written crypto that agrees
with two references on the RFC's vectors is a transcription, not an
invention -- but see the warning below, which is real.

WARNING -- not constant time
----------------------------
`point_mul` branches on the bits of the scalar, so signing leaks timing
information about the private key. That is acceptable for this use and only
this use: signing happens offline, on a controlled machine, from a key that
never leaves it. Do NOT use this module to sign on a shared host, in a
request handler, or anywhere an attacker can time the operation. Verifying
is safe -- it touches no secret.

If signing ever moves somewhere hostile, swap `sign()` for
pyca/cryptography and keep `verify()` as it is: the wire format is
identical, and that is the whole point of using a standard rather than
inventing one.
"""

import hashlib

# Curve25519 field and group order -- RFC 8032 section 5.1.
P = 2 ** 255 - 19
Q = 2 ** 252 + 27742317777372353535851937790883648493

_D = -121665 * pow(121666, P - 2, P) % P
_SQRT_M1 = pow(2, (P - 1) // 4, P)


def _sha512(b):
    return hashlib.sha512(b).digest()


def _sha512_modq(b):
    return int.from_bytes(_sha512(b), "little") % Q


# Points are extended coordinates (X, Y, Z, T) with x = X/Z, y = Y/Z.
def _point_add(a, b):
    A = (a[1] - a[0]) * (b[1] - b[0]) % P
    B = (a[1] + a[0]) * (b[1] + b[0]) % P
    C = 2 * a[3] * b[3] * _D % P
    D = 2 * a[2] * b[2] % P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def _point_mul(s, p):
    """Scalar multiply. NOT constant time -- see the module warning."""
    q = (0, 1, 1, 0)                      # neutral element
    while s > 0:
        if s & 1:
            q = _point_add(q, p)
        p = _point_add(p, p)
        s >>= 1
    return q


def _point_equal(a, b):
    # x1/z1 == x2/z2  <=>  x1*z2 == x2*z1
    if (a[0] * b[2] - b[0] * a[2]) % P != 0:
        return False
    if (a[1] * b[2] - b[1] * a[2]) % P != 0:
        return False
    return True


def _recover_x(y, sign):
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * _SQRT_M1 % P
    if (x * x - x2) % P != 0:
        return None
    if (x & 1) != sign:
        x = P - x
    return x


_GY = 4 * pow(5, P - 2, P) % P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % P)


def _compress(p):
    zinv = pow(p[2], P - 2, P)
    x = p[0] * zinv % P
    y = p[1] * zinv % P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % P)


def _secret_expand(secret):
    if len(secret) != 32:
        raise ValueError("an Ed25519 private key is exactly 32 bytes")
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= (1 << 254)
    return a, h[32:]


# ------------------------------------------------------------------ public

def public_key(secret):
    """32-byte public key for a 32-byte private key."""
    a, _ = _secret_expand(secret)
    return _compress(_point_mul(a, _G))


def sign(secret, message):
    """64-byte signature. NOT constant time -- see the module warning."""
    a, prefix = _secret_expand(secret)
    A = _compress(_point_mul(a, _G))
    r = _sha512_modq(prefix + message)
    R = _compress(_point_mul(r, _G))
    h = _sha512_modq(R + A + message)
    s = (r + h * a) % Q
    return R + int.to_bytes(s, 32, "little")


def verify(public, message, signature):
    """True iff `signature` is valid for `message` under `public`.

    Returns False rather than raising on malformed input: a caller checking
    a record wants a verdict, and a crash on a corrupt signature is an
    availability bug in anything that verifies untrusted records.
    """
    if not isinstance(public, (bytes, bytearray)) or len(public) != 32:
        return False
    if not isinstance(signature, (bytes, bytearray)) or len(signature) != 64:
        return False
    A = _decompress(bytes(public))
    if A is None:
        return False
    R = _decompress(bytes(signature[:32]))
    if R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= Q:                      # reject non-canonical / malleable s
        return False
    h = _sha512_modq(bytes(signature[:32]) + bytes(public) + message)
    return _point_equal(_point_mul(s, _G), _point_add(R, _point_mul(h, A)))
