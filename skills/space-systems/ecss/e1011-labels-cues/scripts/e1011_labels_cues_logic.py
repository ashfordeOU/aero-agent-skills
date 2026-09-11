"""
ECSS-E-ST-10-11C §4.7.3 — Labels and Cues compliance logic.

Deterministic, offline, stdlib only.
Implements label validation, colour-coding convention checks, and
warning-cue redundancy verification per the HFE design rules.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_LABEL_LENGTH = 50  # default character-length ceiling for label text

# Approved HFE colour palette (lower-cased for matching)
_VALID_COLOURS = frozenset(["red", "amber", "yellow", "green", "white", "grey", "blue", "black"])

# Colour-to-status-class mapping (paraphrased from HFE colour-coding practice;
# amber and yellow are treated as equivalent — both map to caution).
_COLOUR_STATUS_MAP = {
    "red":    "danger",
    "amber":  "caution",
    "yellow": "caution",
    "green":  "nominal",
    "white":  "information",
    "grey":   "information",
    "blue":   "selected",
    "black":  "inactive",
}

# Approved cueing modalities
_VALID_MODALITIES = frozenset(["visual", "auditory", "tactile", "haptic"])

# Criticality levels (ordered from least to most severe)
_CRITICALITY_LEVELS = ("non-critical", "caution", "warning", "emergency")

# Criticality levels that require at least two cueing modalities
_REDUNDANT_CUE_THRESHOLD = frozenset(["warning", "emergency"])


# ---------------------------------------------------------------------------
# Label validation
# ---------------------------------------------------------------------------

def validate_label(label_text, item_id, max_length=MAX_LABEL_LENGTH):
    """
    Verify a single label entry against HFE §4.7.3 label requirements.

    Parameters
    ----------
    label_text : str  — the text displayed on the label
    item_id    : str  — unique identifier for the labelled item
    max_length : int  — project character-length ceiling (default 50)

    Returns
    -------
    dict with keys:
        item_id   : str
        label_text: str
        compliant : bool
        findings  : list[str]

    Raises
    ------
    TypeError  if label_text or item_id is not a str
    ValueError if max_length is not a positive int
    """
    if not isinstance(label_text, str):
        raise TypeError(f"label_text must be str, got {type(label_text).__name__}")
    if not isinstance(item_id, str):
        raise TypeError(f"item_id must be str, got {type(item_id).__name__}")
    if not isinstance(max_length, int) or max_length <= 0:
        raise ValueError(f"max_length must be a positive int, got {max_length!r}")

    findings = []

    if not label_text.strip():
        findings.append("label_text is empty")

    if len(label_text) > max_length:
        findings.append(
            f"label_text length {len(label_text)} exceeds limit of {max_length} characters"
        )

    if not item_id.strip():
        findings.append("item_id is empty")

    return {
        "item_id": item_id,
        "label_text": label_text,
        "compliant": len(findings) == 0,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Colour-coding validation
# ---------------------------------------------------------------------------

def validate_colour_coding(colour, status_intent, item_id):
    """
    Verify that a colour-coded indicator's colour matches its status intent.

    Parameters
    ----------
    colour        : str  — colour name (case-insensitive)
    status_intent : str  — intended status class (e.g. 'danger', 'caution')
    item_id       : str  — identifier for the indicator

    Returns
    -------
    dict with keys: item_id, colour, status_intent, compliant, findings

    Raises
    ------
    TypeError if any parameter is not a str
    """
    if not isinstance(colour, str):
        raise TypeError(f"colour must be str, got {type(colour).__name__}")
    if not isinstance(status_intent, str):
        raise TypeError(f"status_intent must be str, got {type(status_intent).__name__}")
    if not isinstance(item_id, str):
        raise TypeError(f"item_id must be str, got {type(item_id).__name__}")

    findings = []
    colour_norm = colour.lower().strip()
    intent_norm = status_intent.lower().strip()

    if colour_norm not in _VALID_COLOURS:
        findings.append(
            f"colour '{colour}' is not in the approved HFE palette: "
            f"{sorted(_VALID_COLOURS)}"
        )
    else:
        mapped = _COLOUR_STATUS_MAP[colour_norm]
        if mapped != intent_norm:
            findings.append(
                f"colour '{colour}' maps to status class '{mapped}' "
                f"but status_intent is '{status_intent}'"
            )

    return {
        "item_id": item_id,
        "colour": colour,
        "status_intent": status_intent,
        "compliant": len(findings) == 0,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Warning-cue validation
# ---------------------------------------------------------------------------

def validate_warning_cue(cue):
    """
    Verify a warning-cue entry against HFE §4.7.3 cue requirements.

    Parameters
    ----------
    cue : dict with required keys:
        item_id    : str
        criticality: str  — one of 'non-critical', 'caution', 'warning', 'emergency'
        modalities : list[str]  — from {'visual', 'auditory', 'tactile', 'haptic'}
        detectable : bool

    Returns
    -------
    dict with keys: item_id, criticality, modalities, compliant, findings

    Raises
    ------
    TypeError  if field types are wrong
    ValueError if required keys are missing or criticality is unknown
    """
    required_keys = {"item_id", "criticality", "modalities", "detectable"}
    missing_keys = required_keys - set(cue.keys())
    if missing_keys:
        raise ValueError(f"cue dict missing required keys: {sorted(missing_keys)}")

    item_id = cue["item_id"]
    criticality = cue["criticality"]
    modalities = cue["modalities"]
    detectable = cue["detectable"]

    if not isinstance(item_id, str):
        raise TypeError("cue['item_id'] must be str")
    if not isinstance(criticality, str):
        raise TypeError("cue['criticality'] must be str")
    if not isinstance(modalities, list):
        raise TypeError("cue['modalities'] must be list")
    if not isinstance(detectable, bool):
        raise TypeError("cue['detectable'] must be bool")

    if criticality not in _CRITICALITY_LEVELS:
        raise ValueError(
            f"criticality '{criticality}' is not valid; "
            f"must be one of {_CRITICALITY_LEVELS}"
        )

    findings = []

    if not detectable:
        findings.append(
            "cue is not confirmed detectable in the operational environment"
        )

    if not modalities:
        findings.append("no cueing modality specified")
    else:
        unknown = sorted(set(modalities) - _VALID_MODALITIES)
        if unknown:
            findings.append(
                f"unknown modalities {unknown}; approved: {sorted(_VALID_MODALITIES)}"
            )

    if criticality in _REDUNDANT_CUE_THRESHOLD and len(modalities) < 2:
        findings.append(
            f"criticality '{criticality}' requires at least 2 cueing modalities "
            f"for redundancy; got {len(modalities)}"
        )

    return {
        "item_id": item_id,
        "criticality": criticality,
        "modalities": modalities,
        "compliant": len(findings) == 0,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Aggregate assessment
# ---------------------------------------------------------------------------

def assess_labels_and_cues(labels, colour_codings, warning_cues):
    """
    Run the full §4.7.3 assessment over a panel's marking inventory.

    Parameters
    ----------
    labels         : list[dict]  — each dict has 'label_text' and 'item_id'
    colour_codings : list[dict]  — each dict has 'colour', 'status_intent', 'item_id'
    warning_cues   : list[dict]  — each dict as required by validate_warning_cue

    Returns
    -------
    dict with keys:
        label_results   : list[dict]
        colour_results  : list[dict]
        cue_results     : list[dict]
        overall_compliant: bool
        total_findings  : int
    """
    if not isinstance(labels, list):
        raise TypeError("labels must be a list")
    if not isinstance(colour_codings, list):
        raise TypeError("colour_codings must be a list")
    if not isinstance(warning_cues, list):
        raise TypeError("warning_cues must be a list")

    label_results = [
        validate_label(l["label_text"], l["item_id"]) for l in labels
    ]
    colour_results = [
        validate_colour_coding(c["colour"], c["status_intent"], c["item_id"])
        for c in colour_codings
    ]
    cue_results = [
        validate_warning_cue(c) for c in warning_cues
    ]

    total = sum(
        len(r["findings"])
        for r in label_results + colour_results + cue_results
    )

    return {
        "label_results": label_results,
        "colour_results": colour_results,
        "cue_results": cue_results,
        "overall_compliant": total == 0,
        "total_findings": total,
    }
