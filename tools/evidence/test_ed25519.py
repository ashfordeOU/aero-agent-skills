#!/usr/bin/env python3
"""Cross-validation for the stdlib Ed25519.

Hand-written crypto is only trustworthy if it agrees with implementations
nobody suspects. This asserts three independent things:

  1. RFC 8032 section 7.1 published test vectors.
  2. Agreement with pyca/cryptography, both directions -- our signature
     verifies there, theirs verifies here.
  3. Agreement with the OpenSSL CLI, a separate codebase again.

2 and 3 are skipped (loudly, not silently) where the reference is absent,
because a machine without them must not report a pass it did not earn.

Plus the negative cases, which are the ones that matter for a verifier
handling untrusted input: a flipped bit, a truncated signature, the wrong
key, a tampered message, and a non-canonical scalar must all be rejected,
and none of them may raise.

Run: python3 tools/evidence/test_ed25519.py
"""

import binascii
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ed25519  # noqa: E402


CROSSVAL_REQUIRED = os.environ.get("AERO_REQUIRE_CROSSVAL") == "1"


def no_crossval(reason):
    """A reference implementation is missing.

    Our Ed25519 is hand-rolled from RFC 8032; agreement with independent
    codebases is the only thing that catches a silent signature bug. On any
    host that exists to prove that -- CI, a release machine -- an absent
    reference implementation is a failure, not a skip, so the proof cannot
    quietly stop happening. Set AERO_REQUIRE_CROSSVAL=1 there.
    """
    if CROSSVAL_REQUIRED:
        raise AssertionError(
            "cross-validation is required here but cannot run: %s. "
            "Install the reference implementation, or unset "
            "AERO_REQUIRE_CROSSVAL if this host is not meant to prove it."
            % reason)
    raise unittest.SkipTest(reason)


def h(x):
    return binascii.unhexlify(x.replace(" ", ""))


class RFC8032Vectors(unittest.TestCase):
    """RFC 8032 section 7.1. The document is the authority, not our code."""

    VECTORS = [
        # (secret, public, message, signature)
        ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
         "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
         "",
         "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8"
         "821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
        ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
         "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
         "72",
         "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085a"
         "c1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
        ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
         "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
         "af82",
         "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff"
         "9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
    ]

    def test_public_key_derivation(self):
        for sec, pub, _, _ in self.VECTORS:
            self.assertEqual(ed25519.public_key(h(sec)).hex(), pub)

    def test_signature_matches_the_vector(self):
        for sec, _, msg, sig in self.VECTORS:
            self.assertEqual(ed25519.sign(h(sec), h(msg)).hex(), sig)

    def test_vector_signature_verifies(self):
        for _, pub, msg, sig in self.VECTORS:
            self.assertTrue(ed25519.verify(h(pub), h(msg), h(sig)))


class AgreesWithPyca(unittest.TestCase):
    """Independent implementation #1."""

    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519 as ref
            cls.ref = ref
        except ImportError:
            no_crossval("pyca/cryptography absent")

    def test_our_signature_verifies_there(self):
        sec = os.urandom(32)
        msg = b"evidence record digest placeholder"
        sig = ed25519.sign(sec, msg)
        pk = self.ref.Ed25519PublicKey.from_public_bytes(ed25519.public_key(sec))
        pk.verify(sig, msg)          # raises on failure

    def test_their_signature_verifies_here(self):
        from cryptography.hazmat.primitives import serialization
        sk = self.ref.Ed25519PrivateKey.generate()
        raw_pub = sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        msg = b"issued by a different implementation"
        self.assertTrue(ed25519.verify(raw_pub, msg, sk.sign(msg)))

    def test_public_keys_agree(self):
        from cryptography.hazmat.primitives import serialization
        sec = os.urandom(32)
        sk = self.ref.Ed25519PrivateKey.from_private_bytes(sec)
        theirs = sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.assertEqual(ed25519.public_key(sec), theirs)


class AgreesWithOpenSSL(unittest.TestCase):
    """Independent implementation #2 -- a separate codebase again."""

    @classmethod
    def setUpClass(cls):
        cls.openssl = shutil.which("openssl")
        if not cls.openssl:
            no_crossval("openssl absent")
        # An openssl without Ed25519 is not a reference implementation.
        # Apple ships LibreSSL 3.3 as /usr/bin/openssl and it has none: it
        # reports "unsupported algorithm" while loading the PUBLIC KEY,
        # before any signature is examined. Asserting through that says our
        # signer was rejected when the truth is the checker cannot read the
        # key, and it turns the pre-push gate red on a clean tree.
        #
        # The probe uses a key written by the REFERENCE library, never one of
        # ours: if openssl cannot load even that, the gap is openssl's. A key
        # it loads but whose signature it rejects remains a failure - that is
        # the finding this class exists to make.
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519 as ref
        except ImportError:
            no_crossval("needs cryptography to write the probe key")
        probe_pem = (ref.Ed25519PrivateKey.generate().public_key()
                     .public_bytes(
                         encoding=serialization.Encoding.PEM,
                         format=serialization.PublicFormat.SubjectPublicKeyInfo))
        with tempfile.TemporaryDirectory() as d:
            probe_path = os.path.join(d, "probe.pem")
            with open(probe_path, "wb") as fh:
                fh.write(probe_pem)
            probe = subprocess.run(
                [cls.openssl, "pkey", "-pubin", "-noout", "-in", probe_path],
                capture_output=True, text=True, timeout=30)
        if probe.returncode != 0:
            ver = subprocess.run([cls.openssl, "version"], capture_output=True,
                                 text=True).stdout.strip() or "this openssl"
            no_crossval("%s cannot load an Ed25519 public key written by the "
                        "reference library, so it cannot cross-validate one"
                        % ver)

    def test_openssl_verifies_our_signature(self):
        try:
            # Both imports inside the try: `serialization` sat outside it, so
            # an absent cryptography raised ImportError and errored the test
            # instead of reaching the skip written on the next line.
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519 as ref
        except ImportError:
            no_crossval("needs cryptography to write the PEM")

        sec = os.urandom(32)
        msg = b"cross-checked against a third codebase"
        sig = ed25519.sign(sec, msg)

        pub_pem = (ref.Ed25519PrivateKey.from_private_bytes(sec)
                   .public_key()
                   .public_bytes(encoding=serialization.Encoding.PEM,
                                 format=serialization.PublicFormat.SubjectPublicKeyInfo))
        with tempfile.TemporaryDirectory() as d:
            pub = os.path.join(d, "pub.pem")
            sgn = os.path.join(d, "sig.bin")
            dat = os.path.join(d, "msg.bin")
            for path, blob in ((pub, pub_pem), (sgn, sig), (dat, msg)):
                with open(path, "wb") as fh:
                    fh.write(blob)
            r = subprocess.run(
                [self.openssl, "pkeyutl", "-verify", "-pubin", "-inkey", pub,
                 "-rawin", "-in", dat, "-sigfile", sgn],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0,
                             "openssl rejected our signature: %s%s"
                             % (r.stdout, r.stderr))


class RejectsBadInput(unittest.TestCase):
    """A verifier meets untrusted bytes. It must say no, not crash."""

    def setUp(self):
        self.sec = os.urandom(32)
        self.pub = ed25519.public_key(self.sec)
        self.msg = b"the record this signature covers"
        self.sig = ed25519.sign(self.sec, self.msg)

    def test_the_good_case_passes(self):
        self.assertTrue(ed25519.verify(self.pub, self.msg, self.sig))

    def test_a_tampered_message_is_rejected(self):
        self.assertFalse(ed25519.verify(self.pub, self.msg + b"!", self.sig))

    def test_a_flipped_signature_bit_is_rejected(self):
        bad = bytearray(self.sig)
        bad[0] ^= 1
        self.assertFalse(ed25519.verify(self.pub, self.msg, bytes(bad)))

    def test_a_flipped_key_bit_is_rejected(self):
        bad = bytearray(self.pub)
        bad[0] ^= 1
        self.assertFalse(ed25519.verify(bytes(bad), self.msg, self.sig))

    def test_a_different_key_is_rejected(self):
        other = ed25519.public_key(os.urandom(32))
        self.assertFalse(ed25519.verify(other, self.msg, self.sig))

    def test_a_truncated_signature_is_rejected_not_raised(self):
        self.assertFalse(ed25519.verify(self.pub, self.msg, self.sig[:63]))

    def test_a_short_key_is_rejected_not_raised(self):
        self.assertFalse(ed25519.verify(self.pub[:31], self.msg, self.sig))

    def test_empty_input_is_rejected_not_raised(self):
        self.assertFalse(ed25519.verify(b"", self.msg, b""))

    def test_a_non_canonical_scalar_is_rejected(self):
        # s >= group order: the classic malleability case. Accepting it
        # means two distinct signatures verify for one message.
        bad = bytearray(self.sig)
        bad[32:] = int.to_bytes(ed25519.Q + 1, 32, "little")
        self.assertFalse(ed25519.verify(self.pub, self.msg, bytes(bad)))

    def test_a_wrong_length_secret_is_refused_loudly(self):
        # Signing is ours to get right, so this one RAISES rather than
        # returning a bad signature.
        with self.assertRaises(ValueError):
            ed25519.sign(b"too short", self.msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
