"""Single import point for P3 functions: real modules win, stubs are the fallback."""
try:
    from backend.ai import owner_message, structure_idea
except ImportError:
    from backend.app.stubs.ai import owner_message, structure_idea

try:
    from backend.impact import compute_impact
except ImportError:
    from backend.app.stubs.impact import compute_impact

__all__ = ["structure_idea", "owner_message", "compute_impact"]
