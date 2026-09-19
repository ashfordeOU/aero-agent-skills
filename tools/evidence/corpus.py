#!/usr/bin/env python3
"""Content hashes for the corpus a verdict was issued against.

This is the field that makes "adding capabilities is a data change, not a
re-qualification event" checkable instead of merely asserted.  A record binds

  * the digest of the whole corpus subtree that was in scope, and
  * the digest of the one leaf the record is about.

Adding a leaf moves the corpus root digest and leaves every existing leaf
digest untouched, so an auditor can see for themselves that nothing already
verified was disturbed.  Editing a verified leaf moves that leaf's digest, and
every stored observation about it is stale from that moment.

aero-corpus-digest/1
--------------------
* Walk the subtree, depth-first, and collect every regular file.
* Drop build noise that is not content: __pycache__ directories, *.pyc, and
  .DS_Store.  Nothing else is skipped; a skip list is a place to hide things.
* Sort the surviving paths by their POSIX-relative byte string.
* For each: emit  b"<relative-path>\\x00<sha256-hex>\\n".
* The subtree digest is sha256 over that concatenation.

Path separators are normalised to "/" so a digest taken on one operating
system equals the digest taken on another.  Paths are relative to the corpus
root and never absolute: a record must be readable by someone who does not
have, and must not learn, the issuer's filesystem layout.
"""

import os

from . import canonical

DIGEST_SPEC = "aero-corpus-digest/1"

SKIP_DIRS = ("__pycache__",)
SKIP_SUFFIXES = (".pyc", ".pyo")
SKIP_NAMES = (".DS_Store",)


def _keep(name):
    if name in SKIP_NAMES:
        return False
    return not name.endswith(SKIP_SUFFIXES)


def iter_files(base):
    """Yield POSIX-relative paths of content files under base, sorted."""
    found = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in filenames:
            if not _keep(filename):
                continue
            absolute = os.path.join(dirpath, filename)
            if not os.path.isfile(absolute) or os.path.islink(absolute):
                continue
            found.append(os.path.relpath(absolute, base).replace(os.sep, "/"))
    found.sort()
    return found


def digest_tree(base):
    """Digest one subtree.  Returns (digest, file_count, byte_count, entries)."""
    entries = []
    blob = bytearray()
    byte_count = 0
    for relative in iter_files(base):
        absolute = os.path.join(base, relative.replace("/", os.sep))
        with open(absolute, "rb") as fh:
            data = fh.read()
        file_digest = canonical.digest_bytes(data)
        byte_count += len(data)
        entries.append((relative, file_digest))
        blob += relative.encode("utf-8") + b"\x00" + file_digest.split(":", 1)[1].encode("ascii") + b"\n"
    return canonical.digest_bytes(bytes(blob)), len(entries), byte_count, entries


def corpus_binding(root, subtree="skills"):
    """Bind the whole corpus subtree.  root is the repository root."""
    base = os.path.join(root, subtree)
    if not os.path.isdir(base):
        raise FileNotFoundError("corpus subtree not found: %s" % subtree)
    tree_digest, file_count, byte_count, _entries = digest_tree(base)
    return {
        "digest_spec": DIGEST_SPEC,
        "algorithm": canonical.DIGEST_ALGORITHM,
        "subtree": subtree,
        "subtree_digest": tree_digest,
        "file_count": file_count,
        "byte_count": byte_count,
    }


def leaf_binding(root, leaf_ref):
    """Bind one leaf.  leaf_ref is a repository-relative POSIX path."""
    base = os.path.join(root, leaf_ref.replace("/", os.sep))
    if not os.path.isdir(base):
        raise FileNotFoundError("leaf not found: %s" % leaf_ref)
    tree_digest, file_count, byte_count, entries = digest_tree(base)
    return {
        "digest_spec": DIGEST_SPEC,
        "algorithm": canonical.DIGEST_ALGORITHM,
        "ref": leaf_ref,
        "leaf_digest": tree_digest,
        "file_count": file_count,
        "byte_count": byte_count,
        "files": [{"path": p, "digest": d} for p, d in entries],
    }
