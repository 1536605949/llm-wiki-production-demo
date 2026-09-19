from __future__ import annotations
import json, urllib.request
from .config import Settings

class OpenAICompatibleLLM:
    def __init__(self, settings: Settings):
        self.s = settings

    def chat(self, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self.s.model,
            "messages": [{"role":"system","content":system},{"role":"user","content":user}],
            "temperature": 0.2,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.s.base_url + "/chat/completions",
            data=payload,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {self.s.api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.s.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

def make_llm(settings: Settings):
    if settings.provider == "mock":
        return None
    if settings.provider == "openai_compatible":
        return OpenAICompatibleLLM(settings)
    raise ValueError(f"Unsupported provider: {settings.provider}")
