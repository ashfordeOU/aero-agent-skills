"""
ECSS-E-ST-10C §5.5 Interface Baseline Control and Change Approval Logic

Implements deterministic, offline checks for:
- Interface baseline state machine (draft → proposed → approved → superseded)
- Change request categorization (minor vs. major)
- Interface Change Board (ICB) quorum validation and vote evaluation
- Stakeholder agreement completeness
- Auditable change log verification
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


# ---------------------------------------------------------------------------
# Baseline state definitions
# ---------------------------------------------------------------------------

BASELINE_STATES = ("draft", "proposed", "approved", "superseded")

# Permitted state transitions per §5.5 baseline control rules
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "draft":      {"proposed"},
    "proposed":   {"approved", "draft"},
    "approved":   {"superseded", "proposed"},
    "superseded": set(),          # terminal — no further transitions permitted
}

# ---------------------------------------------------------------------------
# Change categorization
# ---------------------------------------------------------------------------

def categorize_change_request(
    affects_function: bool,
    affects_timing: bool,
    affects_physical: bool,
) -> str:
    """
    Return 'major' when any interface-definition dimension is affected;
    return 'minor' for purely editorial changes (no impact on any dimension).

    Reference: ECSS-E-ST-10C §5.5.2 change categorization criteria.
    """
    if affects_function or affects_timing or affects_physical:
        return "major"
    return "minor"


# ---------------------------------------------------------------------------
# ICB quorum and voting
# ---------------------------------------------------------------------------

def check_icb_quorum(voter_ids: List[str], required_quorum: int) -> bool:
    """
    Return True when the number of present ICB members meets the required
    quorum.  Raises ValueError if required_quorum is less than 1.
    """
    if required_quorum < 1:
        raise ValueError(f"required_quorum must be >= 1, got {required_quorum}")
    return len(voter_ids) >= required_quorum


def evaluate_icb_vote(votes: Dict[str, str], required_quorum: int) -> Dict:
    """
    Evaluate an ICB vote and return a result dict with keys:
      approved (bool), reason (str), yes (int), no (int), abstain (int)

    Raises ValueError for any vote value outside {"yes", "no", "abstain"}.
    Returns approved=False with reason='quorum_not_met' when quorum is missed.
    """
    if len(votes) < required_quorum:
        return {
            "approved": False,
            "reason": "quorum_not_met",
            "yes": 0,
            "no": 0,
            "abstain": 0,
        }

    yes_count = 0
    no_count = 0
    abstain_count = 0
    invalid_voters: List[str] = []

    for voter, value in votes.items():
        normalised = value.strip().lower()
        if normalised == "yes":
            yes_count += 1
        elif normalised == "no":
            no_count += 1
        elif normalised == "abstain":
            abstain_count += 1
        else:
            invalid_voters.append(voter)

    if invalid_voters:
        raise ValueError(
            f"Invalid vote values from ICB members: {invalid_voters}. "
            "Accepted values are 'yes', 'no', or 'abstain'."
        )

    approved = yes_count > no_count
    return {
        "approved": approved,
        "reason": "majority" if approved else "not_majority",
        "yes": yes_count,
        "no": no_count,
        "abstain": abstain_count,
    }


# ---------------------------------------------------------------------------
# Stakeholder agreement completeness
# ---------------------------------------------------------------------------

def check_agreement_completeness(
    required_signatories: List[str],
    recorded_agreements: Dict[str, str],
) -> Dict:
    """
    Compare the list of required signatories against the dict of recorded
    agreements (signatory_id → agreement_text).

    Returns a dict with:
      complete (bool), missing_agreements (list), agreement_count (int),
      required_count (int)
    """
    missing = [s for s in required_signatories if s not in recorded_agreements]
    return {
        "complete": len(missing) == 0,
        "missing_agreements": missing,
        "agreement_count": len(recorded_agreements),
        "required_count": len(required_signatories),
    }


# ---------------------------------------------------------------------------
# State transition validation
# ---------------------------------------------------------------------------

def validate_state_transition(current_state: str, proposed_state: str) -> bool:
    """
    Return True when proposed_state is a permitted successor to current_state
    per the §5.5 baseline state machine.  Raises ValueError for unknown states.
    """
    if current_state not in BASELINE_STATES:
        raise ValueError(f"Unknown baseline state: '{current_state}'")
    if proposed_state not in BASELINE_STATES:
        raise ValueError(f"Unknown proposed state: '{proposed_state}'")
    return proposed_state in VALID_TRANSITIONS.get(current_state, set())


# ---------------------------------------------------------------------------
# Audit trail check
# ---------------------------------------------------------------------------

def check_audit_trail(change_log: List[str], min_entries: int = 1) -> bool:
    """
    Return True when the change log contains at least min_entries entries.
    A baseline with an empty change log has not been auditably transitioned.
    """
    if min_entries < 1:
        raise ValueError("min_entries must be >= 1")
    return len(change_log) >= min_entries


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ChangeRequest:
    """Represents a single change request against a baselined interface."""
    cr_id: str
    description: str
    affects_function: bool
    affects_timing: bool
    affects_physical: bool
    requester: str

    def __post_init__(self) -> None:
        if not self.cr_id:
            raise ValueError("cr_id must not be empty")
        if not self.requester:
            raise ValueError("requester must not be empty")

    @property
    def category(self) -> str:
        return categorize_change_request(
            self.affects_function,
            self.affects_timing,
            self.affects_physical,
        )


@dataclass
class InterfaceBaseline:
    """Tracks the versioned baseline state of a single interface document."""
    interface_id: str
    version: str
    state: str
    owner: str
    change_log: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must not be empty")
        if not self.version:
            raise ValueError("version must not be empty")
        if not self.owner:
            raise ValueError("owner must not be empty")
        if self.state not in BASELINE_STATES:
            raise ValueError(f"Unknown initial state: '{self.state}'")

    def transition_to(self, new_state: str, actor: str, reason: str) -> None:
        """
        Advance the baseline to new_state.  Raises ValueError when the
        transition is not permitted.  Records the transition in the change log.
        """
        if not validate_state_transition(self.state, new_state):
            raise ValueError(
                f"Transition from '{self.state}' to '{new_state}' is not "
                "permitted by the §5.5 baseline state machine."
            )
        entry = f"{actor}: {self.state} -> {new_state} | {reason}"
        self.change_log.append(entry)
        self.state = new_state
