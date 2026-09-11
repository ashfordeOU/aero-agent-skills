"""
e1006_char_uniqueness_logic.py

ECSS-E-ST-10C §8.2.5 requirement uniqueness checker.
Determines whether requirements in a set are unique in wording and content,
flagging exact duplicates and near-duplicates above a configurable similarity
threshold. Stdlib only; deterministic and offline.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple


_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "shall", "should", "must", "will", "may",
    "be", "is", "are", "was", "were", "been", "that", "which", "this",
    "these", "those", "it", "its", "as", "not", "no", "if", "when",
}


# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Return a canonical lowercase, whitespace-collapsed form of *text*.

    Steps: Unicode NFC → strip diacritics → lowercase → collapse all
    whitespace → strip leading/trailing space.  Punctuation is retained so
    that requirements differing only in punctuation are still distinct (a
    deliberate design choice: punctuation can change meaning in requirements).
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__!r}")
    nfc = unicodedata.normalize("NFC", text)
    lower = nfc.lower()
    collapsed = re.sub(r"\s+", " ", lower).strip()
    return collapsed


def tokenize(text: str) -> Set[str]:
    """Split normalised *text* into a set of meaningful word tokens.

    Removes stopwords so that near-duplicate detection focuses on
    substantive vocabulary.  Returns an empty set for blank text.
    """
    words = re.findall(r"[a-z0-9]+", normalize_text(text))
    return {w for w in words if w not in _STOPWORDS}


# ---------------------------------------------------------------------------
# Similarity metric
# ---------------------------------------------------------------------------

def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Return the Jaccard similarity coefficient for two token sets.

    Returns 0.0 when both sets are empty (no meaningful content to compare).
    Returns 1.0 when both sets are identical and non-empty.
    """
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_requirements(requirements: List[Dict]) -> None:
    """Raise ValueError for any requirement missing or having empty id/text."""
    if not isinstance(requirements, list):
        raise TypeError("requirements must be a list")
    seen_ids: Set[str] = set()
    for i, req in enumerate(requirements):
        if not isinstance(req, dict):
            raise TypeError(f"requirement at index {i} must be a dict")
        if "id" not in req:
            raise ValueError(f"requirement at index {i} is missing 'id' field")
        if "text" not in req:
            raise ValueError(f"requirement at index {i} is missing 'text' field")
        req_id = req["id"]
        req_text = req["text"]
        if not isinstance(req_id, str) or not req_id.strip():
            raise ValueError(
                f"requirement at index {i} has an empty or non-string 'id'"
            )
        if not isinstance(req_text, str) or not req_text.strip():
            raise ValueError(
                f"requirement '{req_id}' has an empty or non-string 'text'"
            )
        if req_id in seen_ids:
            raise ValueError(f"duplicate requirement id: '{req_id}'")
        seen_ids.add(req_id)


# ---------------------------------------------------------------------------
# Core detection functions
# ---------------------------------------------------------------------------

def find_exact_duplicates(
    requirements: List[Dict],
) -> List[Tuple[str, str]]:
    """Return pairs of requirement ids whose normalised text is identical.

    Each pair is reported once (ordered by first-occurrence index), so
    (A, B) appears but not (B, A).
    """
    pairs: List[Tuple[str, str]] = []
    normalised: Dict[str, str] = {}  # normalised_text → first id

    for req in requirements:
        norm = normalize_text(req["text"])
        if norm in normalised:
            pairs.append((normalised[norm], req["id"]))
        else:
            normalised[norm] = req["id"]

    return pairs


def find_near_duplicates(
    requirements: List[Dict],
    threshold: float = 0.85,
    exclude_pairs: Optional[Set[Tuple[str, str]]] = None,
) -> List[Tuple[str, str, float]]:
    """Return triples (id_a, id_b, similarity) for pairs above *threshold*.

    Pairs already reported as exact duplicates (passed in *exclude_pairs*)
    are skipped to avoid double-reporting.  Similarity is rounded to four
    decimal places.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {threshold!r}")

    exclude: Set[Tuple[str, str]] = exclude_pairs or set()
    triples: List[Tuple[str, str, float]] = []

    tokens: Dict[str, Set[str]] = {
        req["id"]: tokenize(req["text"]) for req in requirements
    }
    ids = [req["id"] for req in requirements]

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            id_a, id_b = ids[i], ids[j]
            if (id_a, id_b) in exclude or (id_b, id_a) in exclude:
                continue
            sim = jaccard_similarity(tokens[id_a], tokens[id_b])
            if sim >= threshold:
                triples.append((id_a, id_b, round(sim, 4)))

    return triples


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def check_uniqueness(
    requirements: List[Dict],
    near_dup_threshold: float = 0.85,
) -> Dict:
    """Verify uniqueness of *requirements* per ECSS-E-ST-10C §8.2.5.

    Parameters
    ----------
    requirements:
        List of dicts, each with str keys 'id' and 'text'.
    near_dup_threshold:
        Jaccard similarity score at or above which two requirements are
        considered near-duplicates (default 0.85).

    Returns
    -------
    dict with keys:
        total               int   — number of requirements examined
        exact_duplicate_pairs  list[(id_a, id_b)]
        near_duplicate_pairs   list[(id_a, id_b, score)]
        compliant           bool  — True iff no findings
        findings            list[str] — human-readable finding descriptions
    """
    _validate_requirements(requirements)

    exact_pairs = find_exact_duplicates(requirements)
    exact_set: Set[Tuple[str, str]] = set(exact_pairs)

    near_pairs = find_near_duplicates(
        requirements,
        threshold=near_dup_threshold,
        exclude_pairs=exact_set,
    )

    findings: List[str] = []
    for id_a, id_b in exact_pairs:
        findings.append(
            f"EXACT-DUPLICATE: requirements '{id_a}' and '{id_b}' have "
            "identical normalised text — one must be removed or reworded."
        )
    for id_a, id_b, score in near_pairs:
        findings.append(
            f"NEAR-DUPLICATE (similarity={score:.4f}): requirements '{id_a}' "
            f"and '{id_b}' share {score*100:.1f}% of substantive vocabulary — "
            "review for unintended duplication."
        )

    return {
        "total": len(requirements),
        "exact_duplicate_pairs": exact_pairs,
        "near_duplicate_pairs": near_pairs,
        "compliant": len(findings) == 0,
        "findings": findings,
    }
