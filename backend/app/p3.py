"""Single import point for P3 functions: real modules win, stubs are the fallback."""
try:
    from backend.ai import owner_message, structure_idea
except ImportError:
    from backend.app.stubs.ai import owner_message, structure_idea

try:
    from backend.impact import compute_impact
except ImportError:
    from backend.app.stubs.impact import compute_impact

try:
    from backend.ai.references import find_references
except ImportError:
    from backend.app.stubs.ai import find_references

try:
    from backend.ai.costs import estimate_cost
except ImportError:
    from backend.app.stubs.ai import estimate_cost

try:
    from backend.ai.proiect import generate_dosar
except ImportError:
    from backend.app.stubs.ai import generate_dosar

__all__ = ["structure_idea", "owner_message", "compute_impact", "find_references", "estimate_cost", "generate_dosar"]
