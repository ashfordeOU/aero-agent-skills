"""Document control logic for aerospace manufacturing.

Paraphrase of AS9100 document control practice (clause framing,
summarized, not copied): controlled documents are approved before
issue, tracked in a master list, used at the current revision, and
obsolete revisions are removed from active use and retained in the
register as history. The module is deterministic over register
entries; it computes no physical quantities.

Register entry keys: doc_number, title, revision, issue_date,
status (draft, issued, obsolete), author, approver.
"""

import re

STATUSES = ("draft", "issued", "obsolete")

LETTER_RE = re.compile(r"[A-Z]")


def _clean(text):
    return (text or "").strip()


def revision_compare(a, b):
    """Compare two revision identifiers: uppercase single letters or
    positive integers. Returns -1, 0, or 1.

    Raises ValueError for an empty identifier or a mixed
    letter/integer pair, which a consistent register never contains.
    """
    a = _clean(a).upper()
    b = _clean(b).upper()
    if not a or not b:
        raise ValueError("revision must be a non-empty string")
    a_int = a.isdigit() and int(a) > 0
    b_int = b.isdigit() and int(b) > 0
    if a_int and b_int:
        return (int(a) > int(b)) - (int(a) < int(b))
    if LETTER_RE.fullmatch(a) and LETTER_RE.fullmatch(b):
        return (a > b) - (a < b)
    raise ValueError(
        "revision pair must be both letters or both integers, got %r and %r" % (a, b)
    )


def approval_ok(entry):
    """Approved before issue: an approver is recorded and is not the
    author (independent approval).

    Raises ValueError for a non-dict entry.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict, got %r" % (entry,))
    author = _clean(entry.get("author"))
    approver = _clean(entry.get("approver"))
    if not author or not approver:
        return False
    return approver.lower() != author.lower()


def register_validity(entry):
    """Master-list entry check. Returns 'valid' or a reason string.

    Checks doc_number, title, revision, issue_date, status, and the
    approval-before-issue rule for issued entries. Raises ValueError
    for a non-dict entry.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict, got %r" % (entry,))
    if not _clean(entry.get("doc_number")):
        return "missing-doc-number"
    if not _clean(entry.get("title")):
        return "missing-title"
    if not _clean(entry.get("revision")):
        return "missing-revision"
    if not _clean(entry.get("issue_date")):
        return "missing-issue-date"
    status = entry.get("status")
    if status not in STATUSES:
        return "unknown-status"
    if status == "issued" and not approval_ok(entry):
        return "missing-approval"
    return "valid"


def use_verdict(entry, current_revision):
    """Verdict for a document copy in use.

    'current' when the issued entry matches the master-list revision,
    'superseded' when the copy predates it or the entry is obsolete,
    'unreleased' for a draft, and 'future-revision' when the copy is
    ahead of the master list. Raises ValueError when the entry is not
    a valid issued entry or the revision pair is incomparable.
    """
    valid = register_validity(entry)
    if valid != "valid":
        raise ValueError("entry invalid: %s" % valid)
    if entry["status"] == "draft":
        return "unreleased"
    if entry["status"] == "obsolete":
        return "superseded"
    cmp_res = revision_compare(entry["revision"], current_revision)
    if cmp_res < 0:
        return "superseded"
    if cmp_res > 0:
        return "future-revision"
    return "current"


def master_list_check(entries, doc_number, revision):
    """Use verdict for the master-list copy of doc_number at revision.

    Matches the exact doc number and revision pair, then returns the
    use verdict for that listed copy. 'unlisted' when the pair is
    absent from the master list (an unlisted copy is not controlled).
    Raises ValueError for a non-list master list.
    """
    if not isinstance(entries, (list, tuple)):
        raise ValueError("master list must be a list or tuple")
    target_doc = _clean(doc_number)
    target_rev = _clean(revision)
    for entry in entries:
        if _clean(entry.get("doc_number")) != target_doc:
            continue
        if _clean(entry.get("revision")) != target_rev:
            continue
        return use_verdict(entry, target_rev)
    return "unlisted"


def current_revision(entries, doc_number):
    """Highest issued revision in the master list for doc_number, or
    None when the document is unlisted or has no issued entry.

    Draft and obsolete entries never define the current revision.
    """
    if not isinstance(entries, (list, tuple)):
        raise ValueError("master list must be a list or tuple")
    target = _clean(doc_number)
    best = None
    for entry in entries:
        if _clean(entry.get("doc_number")) != target:
            continue
        if entry.get("status") != "issued":
            continue
        rev = _clean(entry.get("revision"))
        if not rev:
            continue
        if best is None or revision_compare(rev, best) > 0:
            best = rev
    return best


def obsolete_action(entry):
    """Disposition for an obsolete revision: remove from active use,
    mark status obsolete, retain in the master list as history.

    Raises ValueError for a non-dict entry.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict, got %r" % (entry,))
    return {
        "doc_number": _clean(entry.get("doc_number")),
        "revision": _clean(entry.get("revision")),
        "status": "obsolete",
        "action": "remove-from-active-use",
        "retain": "master-list-history",
    }
