from backend.ai.matching import Match, SpaceCandidate, match_spaces
from backend.ai.schemas import Category, IdeaDossier, Setting
from backend.ai.structure import structure_dossier, structure_idea


def owner_message(idea, space, slot) -> str:
    """Contract function: booking request text for the space owner (see backend.ai.contract)."""
    from backend.ai.contract import owner_message as _owner_message

    return _owner_message(idea, space, slot)


__all__ = ["Category", "IdeaDossier", "Match", "Setting", "SpaceCandidate", "match_spaces", "owner_message",
           "structure_dossier", "structure_idea"]
