#!/usr/bin/env python3
"""The environment facts a verdict's determinism actually depends on.

Scope discipline: this block records what could change a gate's answer, and
nothing else.  It deliberately does NOT record the hostname, the user, the
working directory, the CPU model, the wall clock, or the process environment.
Those identify the issuer rather than the computation, an evidence record is
meant to be handed to a third party, and every one of them is a way for a
record to stop being portable.

The libm fingerprint is here because this corpus has already been bitten by
it.  math.pow, 10**x and math.log10 are not correctly rounded, so which side
of the last bit a result lands on differs between C libraries.  A contract
test that asserts a strict inequality at that boundary passes on a macOS build
host and fails on a Linux runner.  A stored observation about near-boundary
comparisons is only meaningful together with the fingerprint of the library
that produced the numbers, so the fingerprint travels with it, and a regrade
reports whether the two match.
"""

import math
import platform
import sys

from . import canonical

ENVIRONMENT_SPEC = "aero-evidence-environment/1"

# Each probe is an expression whose exact last bit differs between C math
# libraries.  The value is captured as its shortest round-trip repr, so the
# fingerprint changes if any of them lands differently.
PROBES = (
    ("log10_pow_roundtrip", lambda: 20.0 * math.log10(10.0 ** (-20.0 / 20.0))),
    ("pow_10_neg_tenth", lambda: math.pow(10.0, -0.1)),
    ("log10_thousand", lambda: math.log10(1000.0)),
    ("exp_one", lambda: math.exp(1.0)),
    ("sin_large_argument", lambda: math.sin(1e22)),
    ("sqrt_two", lambda: math.sqrt(2.0)),
    ("atan2_one_three", lambda: math.atan2(1.0, 3.0)),
    ("tenth_plus_fifth", lambda: 0.1 + 0.2),
    ("fsum_ten_tenths", lambda: math.fsum([0.1] * 10)),
    ("pow_two_half", lambda: math.pow(2.0, 0.5)),
)


def libm_probes():
    out = []
    for name, fn in PROBES:
        try:
            out.append({"probe": name, "repr": repr(fn())})
        except Exception as exc:  # noqa: BLE001 - a probe that cannot run is a fact
            out.append({"probe": name, "repr": None, "error": type(exc).__name__})
    return out


def capture():
    """Return the environment block for a record body."""
    probes = libm_probes()
    info = sys.float_info
    return {
        "spec": ENVIRONMENT_SPEC,
        "interpreter": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "version_info": list(sys.version_info[:3]),
        },
        "platform": {
            # Family and word size only.  The host's name, its release string
            # and its CPU model are not determinism inputs for these gates and
            # would make the record identify the machine that issued it.
            "system": platform.system(),
            "machine": platform.machine(),
            "byteorder": sys.byteorder,
            "pointer_bits": 64 if sys.maxsize > 2**32 else 32,
        },
        "float": {
            "mant_dig": info.mant_dig,
            "max_exp": info.max_exp,
            "min_exp": info.min_exp,
            "radix": info.radix,
            "rounds": info.rounds,
            "epsilon": canonical.num(info.epsilon),
        },
        "hash_randomization": bool(sys.flags.hash_randomization),
        "libm": {
            "probes": probes,
            "fingerprint": canonical.digest(probes),
        },
    }


def compare(stored, current):
    """Field-by-field comparison of two environment blocks."""
    differences = []

    def walk(a, b, path):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                walk(a.get(key), b.get(key), path + [key])
        elif a != b:
            differences.append({"field": ".".join(path), "stored": a, "current": b})

    walk(stored, current, [])
    return {
        "match": not differences,
        "libm_fingerprint_match": stored.get("libm", {}).get("fingerprint")
        == current.get("libm", {}).get("fingerprint"),
        "differences": differences,
    }
