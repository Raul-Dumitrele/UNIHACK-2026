"""Developer tool, run by hand: compare registry.json with the current public list. Changes nothing.

    python -m backend.ai.llm.sync_registry

Fetches data.json from github.com/mnfst/awesome-free-llm-apis (the source the registry was built from)
and prints providers and models that were added or removed. Update registry.json yourself, then run
check and bench. The application never downloads this list.
"""
import sys

import httpx

from backend.ai.llm.providers import load_registry

SOURCE = "https://raw.githubusercontent.com/mnfst/awesome-free-llm-apis/main/data.json"
NAME_TO_ID = {
    "Google Gemini": "gemini", "Groq": "groq", "OpenRouter": "openrouter", "Cohere": "cohere", "NVIDIA NIM": "nvidia",
    "Cloudflare Workers AI": "cloudflare", "Z AI (Zhipu AI)": "zai", "Aion Labs": "aionlabs", "Gonka Broker": "gonka",
    "LLM7.io": "llm7", "Kilo Code": "kilo", "OVHcloud AI Endpoints": "ovh", "ModelScope": "modelscope",
    "SiliconFlow": "siliconflow",
}


def diff(remote: dict, registry) -> list[str]:
    ours = {p.id: set(p.models) for p in registry}
    lines = []
    seen = set()
    for prov in remote.get("providers", []):
        pid = NAME_TO_ID.get(prov.get("name"), prov.get("name"))
        seen.add(pid)
        theirs = {m.get("id") for m in prov.get("models", []) if m.get("id") and not m["id"].startswith("+")}
        if pid not in ours:
            lines.append(f"+ furnizor nou: {prov.get('name')} ({prov.get('baseUrl')}) cu {len(theirs)} modele")
            continue
        for m in sorted(theirs - ours[pid]):
            lines.append(f"+ {pid}: model nou {m}")
        for m in sorted(ours[pid] - theirs):
            lines.append(f"- {pid}: {m} nu mai e în listă (sau a fost adăugat manual)")
    for pid in sorted(set(ours) - seen):
        lines.append(f"- furnizor absent din listă: {pid}")
    return lines


def main() -> int:
    remote = httpx.get(SOURCE, timeout=20).json()
    lines = diff(remote, load_registry())
    print(f"Sursa: {SOURCE} (lastUpdated: {remote.get('lastUpdated', '?')})")
    print("\n".join(lines) if lines else "Registrul e la zi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
