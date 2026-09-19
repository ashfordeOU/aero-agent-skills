"""Evidence records and regrade for the Aero Agent Skills conformance harness.

The paid product is a verified vertical; the thing being sold is a verdict
somebody else can check.  This package is the mechanism behind that verdict:

    record      a sealed, plain-JSON statement of what was measured, against
                which corpus, which standards editions, which harness and
                specification versions, in which environment - with an
                append-only amendment history.

    regrade     re-deciding stored records against a changed checker, with no
                re-execution of the underlying work.

Everything here is standard library only and touches the network never.
Read DESIGN.md in this directory before extending it; it records what the
schema deliberately does not capture, and why.
"""

__version__ = "1.0.0"
