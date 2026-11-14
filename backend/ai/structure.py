from backend.ai.config import get_settings
from backend.ai.fallback import build_fallback
from backend.ai.gemini import ask_gemini
from backend.ai.schemas import IdeaDossier


def structure_dossier(text: str) -> IdeaDossier:
    """Idea text -> P3's detailed dossier. Never raises: Gemini first, deterministic fallback otherwise."""
    text = (text or "").strip()
    draft = ask_gemini(text, get_settings()) if text else None
    if draft is not None:
        return IdeaDossier(**draft.model_dump(), source="gemini")
    return IdeaDossier(**build_fallback(text).model_dump(), source="fallback")


def structure_idea(text: str):
    """Contract function (docs/CONTRACT.md): idea text -> Structurat, as P1 stores it on the Idea."""
    from backend.ai.contract import to_structurat  # imports backend.app.schemas (contract types)

    return to_structurat(structure_dossier(text), text)
