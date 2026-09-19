"""Cleaning process selection for flight hardware under contamination control.

Anchor: ECSS-Q-ST-70-01 operations clause (choosing the cleaning process a
given hardware item can take, among solvent wipe, aqueous immersion, plasma
and carbon-dioxide snow). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the hardware description: its materials, the contaminant that has
   to come off, the cleanliness level it must reach, and the constraints it
   carries (blind cavities, bonded joints, optical or electrostatic
   sensitivity, whether it may be immersed or taken to vacuum).
2. Screen every candidate process for admissibility: material compatibility,
   trapped-liquid geometry, sensitivity to the mechanism the process uses, and
   whether the process leaves a residue the hardware cannot carry.
3. Score the admissible candidates on how well the mechanism removes the
   contaminant present, on the cleanliness level the process can reach, and on
   the penalty for a wet process that has to be dried out afterwards.
4. Rank the survivors and return the recommended process with the reason each
   rejected candidate was excluded. When no candidate survives, refuse: there
   is no default process, and the hardware design has to change instead.
"""

import math

__all__ = [
    "PROCESSES",
    "CONTAMINANT_TYPES",
    "SCORE_TOLERANCE",
    "process_profile",
    "validate_hardware",
    "material_compatible",
    "geometry_admissible",
    "sensitivity_admissible",
    "residue_admissible",
    "exclusion_reasons",
    "admissible_processes",
    "removal_effectiveness",
    "level_capability_score",
    "score_process",
    "rank_processes",
    "select_cleaning_process",
]

CONTAMINANT_TYPES = ("particulate", "molecular-film", "ionic-salt", "machining-oil")

# Each profile paraphrases what the mechanism does, not standard text.
#   materials_excluded : material families the mechanism attacks
#   wets               : the process leaves liquid that must be dried out
#   needs_vacuum       : the process runs in a vacuum chamber
#   residue            : residue the process itself can leave behind
#   reach_blind_cavity : the mechanism reaches into a blind cavity
#   removal            : effectiveness per contaminant type, 0..1
#   best_level_rank    : cleanest particulate ladder rank the process reaches
PROCESSES = {
    "solvent-wipe": {
        "materials_excluded": ("unsealed-polystyrene", "crazing-sensitive-acrylic"),
        "wets": True,
        "needs_vacuum": False,
        "residue": "solvent-film",
        "reach_blind_cavity": False,
        "abrasive": True,
        "removal": {
            "particulate": 0.65,
            "molecular-film": 0.80,
            "ionic-salt": 0.35,
            "machining-oil": 0.85,
        },
        "best_level_rank": 2,
    },
    "aqueous-immersion": {
        "materials_excluded": ("open-cell-foam", "unsealed-magnesium", "honeycomb-core"),
        "wets": True,
        "needs_vacuum": False,
        "residue": "water-spot",
        "reach_blind_cavity": True,
        "abrasive": False,
        "removal": {
            "particulate": 0.85,
            "molecular-film": 0.60,
            "ionic-salt": 0.95,
            "machining-oil": 0.70,
        },
        "best_level_rank": 1,
    },
    "plasma": {
        "materials_excluded": ("bare-polymer-film", "thermal-control-paint"),
        "wets": False,
        "needs_vacuum": True,
        "residue": None,
        "reach_blind_cavity": True,
        "abrasive": False,
        "removal": {
            "particulate": 0.30,
            "molecular-film": 0.95,
            "ionic-salt": 0.20,
            "machining-oil": 0.90,
        },
        "best_level_rank": 0,
    },
    "co2-snow": {
        "materials_excluded": ("soft-gold-plating",),
        "wets": False,
        "needs_vacuum": False,
        "residue": None,
        "reach_blind_cavity": False,
        "abrasive": True,
        "removal": {
            "particulate": 0.90,
            "molecular-film": 0.55,
            "ionic-salt": 0.15,
            "machining-oil": 0.45,
        },
        "best_level_rank": 0,
    },
}

REQUIRED_HARDWARE_KEYS = (
    "hardware_id",
    "materials",
    "contaminant",
    "required_level_rank",
)

# Scores are sums of tabulated fractions; a genuine tie must not be broken by
# the last bit of a float sum.
SCORE_TOLERANCE = 1e-12

# Penalties applied to an admissible but awkward candidate.
WET_PROCESS_PENALTY = 0.10
ABRASIVE_ON_SOFT_PENALTY = 0.15


def process_profile(name):
    """Return the profile of a known cleaning process."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("process name must be a non-empty string")
    key = name.strip()
    if key not in PROCESSES:
        raise ValueError(
            "unknown cleaning process %r; known: %s"
            % (name, ", ".join(sorted(PROCESSES)))
        )
    return PROCESSES[key]


def validate_hardware(hardware):
    """Return a normalized hardware description, raising on bad input."""
    if not isinstance(hardware, dict):
        raise ValueError("hardware must be a mapping")
    for key in REQUIRED_HARDWARE_KEYS:
        if key not in hardware:
            raise ValueError("hardware missing required key '%s'" % key)
    hardware_id = hardware["hardware_id"]
    if not isinstance(hardware_id, str) or not hardware_id.strip():
        raise ValueError("hardware_id must be a non-empty string")
    materials = hardware["materials"]
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("materials must be a non-empty sequence")
    normalized_materials = []
    for index, material in enumerate(materials):
        if not isinstance(material, str) or not material.strip():
            raise ValueError("materials[%d] must be a non-empty string" % index)
        normalized_materials.append(material.strip())
    contaminant = hardware["contaminant"]
    if contaminant not in CONTAMINANT_TYPES:
        raise ValueError(
            "contaminant must be one of %s, got %r"
            % (", ".join(CONTAMINANT_TYPES), contaminant)
        )
    rank = hardware["required_level_rank"]
    if isinstance(rank, bool) or not isinstance(rank, int):
        raise ValueError("required_level_rank must be an integer ladder index")
    if rank < 0:
        raise ValueError("required_level_rank must not be negative, got %d" % rank)
    return {
        "hardware_id": hardware_id.strip(),
        "materials": normalized_materials,
        "contaminant": contaminant,
        "required_level_rank": rank,
        "blind_cavities": bool(hardware.get("blind_cavities", False)),
        "immersion_permitted": bool(hardware.get("immersion_permitted", True)),
        "vacuum_permitted": bool(hardware.get("vacuum_permitted", True)),
        "optically_sensitive": bool(hardware.get("optically_sensitive", False)),
        "electrostatic_sensitive": bool(hardware.get("electrostatic_sensitive", False)),
        "residue_free_required": bool(hardware.get("residue_free_required", False)),
        "post_rinse_step": bool(hardware.get("post_rinse_step", False)),
        "soft_surface": bool(hardware.get("soft_surface", False)),
    }


def material_compatible(process_name, hardware):
    """Return True when no hardware material is attacked by the process."""
    profile = process_profile(process_name)
    item = validate_hardware(hardware)
    excluded = set(profile["materials_excluded"])
    return not any(material in excluded for material in item["materials"])


def geometry_admissible(process_name, hardware):
    """Return True when the geometry does not defeat or trap the process."""
    profile = process_profile(process_name)
    item = validate_hardware(hardware)
    if item["blind_cavities"]:
        if not profile["reach_blind_cavity"]:
            return False
        if profile["wets"] and not item["immersion_permitted"]:
            return False
    if profile["wets"] and not item["immersion_permitted"]:
        return False
    if profile["needs_vacuum"] and not item["vacuum_permitted"]:
        return False
    return True


def sensitivity_admissible(process_name, hardware):
    """Return True when the mechanism does not threaten a sensitive surface."""
    profile = process_profile(process_name)
    item = validate_hardware(hardware)
    if item["optically_sensitive"] and profile["abrasive"] and profile["wets"]:
        return False
    if item["electrostatic_sensitive"] and process_name == "co2-snow":
        return False
    return True


def residue_admissible(process_name, hardware):
    """Return True when any residue the process leaves can be carried."""
    profile = process_profile(process_name)
    item = validate_hardware(hardware)
    if profile["residue"] is None:
        return True
    if not item["residue_free_required"]:
        return True
    # A residue-free finish is still reachable if the flow declares the rinse
    # or dry step that takes the residue back off.
    return item["post_rinse_step"]


def exclusion_reasons(process_name, hardware):
    """Return the reasons one process is not admissible for this hardware."""
    reasons = []
    if not material_compatible(process_name, hardware):
        reasons.append("attacks a material of the item")
    if not geometry_admissible(process_name, hardware):
        reasons.append("geometry or facility constraint blocks the process")
    if not sensitivity_admissible(process_name, hardware):
        reasons.append("mechanism threatens a sensitive surface")
    if not residue_admissible(process_name, hardware):
        reasons.append("leaves a residue the item cannot carry")
    return reasons


def admissible_processes(hardware):
    """Return the process names that survive every admissibility screen."""
    validate_hardware(hardware)
    return [name for name in sorted(PROCESSES) if not exclusion_reasons(name, hardware)]


def removal_effectiveness(process_name, contaminant):
    """Return the tabulated removal effectiveness for a contaminant type."""
    profile = process_profile(process_name)
    if contaminant not in CONTAMINANT_TYPES:
        raise ValueError("unknown contaminant type %r" % (contaminant,))
    return float(profile["removal"][contaminant])


def level_capability_score(process_name, required_level_rank):
    """Return 1.0 when the process reaches the level, tapering when it cannot."""
    profile = process_profile(process_name)
    if isinstance(required_level_rank, bool) or not isinstance(required_level_rank, int):
        raise ValueError("required_level_rank must be an integer ladder index")
    if required_level_rank < 0:
        raise ValueError("required_level_rank must not be negative")
    shortfall = profile["best_level_rank"] - required_level_rank
    if shortfall <= 0:
        return 1.0
    return max(0.0, 1.0 - 0.25 * float(shortfall))


def score_process(process_name, hardware):
    """Return the ranking score of one admissible process for this hardware."""
    item = validate_hardware(hardware)
    reasons = exclusion_reasons(process_name, hardware)
    if reasons:
        raise ValueError(
            "%s is not admissible for %s: %s"
            % (process_name, item["hardware_id"], "; ".join(reasons))
        )
    profile = process_profile(process_name)
    score = removal_effectiveness(process_name, item["contaminant"])
    score = score * level_capability_score(process_name, item["required_level_rank"])
    if profile["wets"]:
        score = score - WET_PROCESS_PENALTY
    if profile["abrasive"] and item["soft_surface"]:
        score = score - ABRASIVE_ON_SOFT_PENALTY
    return score


def rank_processes(hardware):
    """Return admissible processes ordered best first, ties by name."""
    names = admissible_processes(hardware)
    scored = [(name, score_process(name, hardware)) for name in names]

    def _order(entry):
        return (-entry[1], entry[0])

    ordered = sorted(scored, key=_order)
    # Re-seat entries whose scores are equal within tolerance onto name order,
    # so a float sum cannot decide a genuine tie.
    result = []
    for name, value in ordered:
        placed = False
        for position, (kept_name, kept_value) in enumerate(result):
            if math.isclose(value, kept_value, rel_tol=0.0, abs_tol=SCORE_TOLERANCE):
                if name < kept_name:
                    result.insert(position, (name, value))
                    placed = True
                    break
        if not placed:
            result.append((name, value))
    return result


def select_cleaning_process(hardware):
    """Run the full cleaning-process selection for one hardware item.

    hardware keys: hardware_id, materials, contaminant, required_level_rank,
    plus the optional flags blind_cavities, immersion_permitted,
    vacuum_permitted, optically_sensitive, electrostatic_sensitive,
    residue_free_required, post_rinse_step and soft_surface.
    """
    item = validate_hardware(hardware)
    ranked = rank_processes(hardware)
    rejected = {}
    for name in sorted(PROCESSES):
        reasons = exclusion_reasons(name, hardware)
        if reasons:
            rejected[name] = reasons
    findings = []
    if not ranked:
        findings.append(
            "no cleaning process is admissible for %s; the item has to be "
            "re-designed or dispositioned, not cleaned by default"
            % item["hardware_id"]
        )
        return {
            "hardware_id": item["hardware_id"],
            "selected": None,
            "ranked": [],
            "rejected": rejected,
            "findings": findings,
            "decided": False,
        }
    best_name, best_score = ranked[0]
    if level_capability_score(best_name, item["required_level_rank"]) < 1.0:
        findings.append(
            "%s does not reach the required cleanliness level on its own; "
            "plan a follow-on process or a tighter level allocation" % best_name
        )
    if len(ranked) > 1 and math.isclose(
        best_score, ranked[1][1], rel_tol=0.0, abs_tol=SCORE_TOLERANCE
    ):
        findings.append(
            "%s and %s score equally; the choice is being made on name order "
            "and needs an engineering tie-break" % (best_name, ranked[1][0])
        )
    return {
        "hardware_id": item["hardware_id"],
        "selected": best_name,
        "selected_score": best_score,
        "ranked": ranked,
        "rejected": rejected,
        "findings": findings,
        "decided": True,
    }
