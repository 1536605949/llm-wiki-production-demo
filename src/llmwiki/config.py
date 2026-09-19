from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    provider: str = "mock"
    base_url: str = "http://localhost:11434/v1"
    model: str = "qwen3:8b"
    api_key: str = "ollama"
    timeout_seconds: int = 120
    auto_git_commit: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=os.getenv("LLMWIKI_PROVIDER", "mock"),
            base_url=os.getenv("LLMWIKI_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
            model=os.getenv("LLMWIKI_MODEL", "qwen3:8b"),
            api_key=os.getenv("LLMWIKI_API_KEY", "ollama"),
            timeout_seconds=int(os.getenv("LLMWIKI_TIMEOUT_SECONDS", "120")),
            auto_git_commit=os.getenv("LLMWIKI_AUTO_GIT_COMMIT", "false").lower()
            in {"1", "true", "yes", "on"},
        )
