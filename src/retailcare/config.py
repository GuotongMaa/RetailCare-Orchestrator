"""Central configuration + LLM client for RetailCare Orchestrator.

Model layer goes through LiteLLM so any OpenAI-compatible model can be swapped
(DeepSeek flash/pro, Qwen, GPT, Claude). DeepSeek v4 is a *reasoning* model:
reasoning tokens are emitted before the answer and consume the output budget,
so we (a) keep a generous max_tokens and (b) read `content` (not reasoning).

Env is loaded from `.claude/.env` first (where the user stores keys), then a
project-root `.env`. Both are git-ignored.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]

# Load keys: .claude/.env wins for secrets, project .env can override non-secrets.
load_dotenv(_ROOT / ".claude" / ".env", override=False)
load_dotenv(_ROOT / ".env", override=False)


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "deepseek-v4-flash")
    model_weak: str = os.getenv("RETAILCARE_MODEL_WEAK", "deepseek-v4-flash")
    model_strong: str = os.getenv("RETAILCARE_MODEL_STRONG", "deepseek-v4-pro")
    max_tokens: int = int(os.getenv("RETAILCARE_MAX_TOKENS", "2048"))
    temperature: float = field(default_factory=lambda: _f("RETAILCARE_TEMPERATURE", 0.0))
    price_in_per_m: float = field(default_factory=lambda: _f("RETAILCARE_PRICE_IN_PER_M", 0.28))
    price_out_per_m: float = field(default_factory=lambda: _f("RETAILCARE_PRICE_OUT_PER_M", 0.42))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./retailcare.db")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./.chroma")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


settings = Settings()


@dataclass
class LLMResult:
    content: str
    reasoning: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float

    def cost_usd(self, s: Settings = settings) -> float:
        return (
            self.prompt_tokens / 1_000_000 * s.price_in_per_m
            + self.completion_tokens / 1_000_000 * s.price_out_per_m
        )


# Process-wide usage accumulator (feeds cost_per_task metric / E6 Pareto).
class _Usage:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0

    def add(self, r: LLMResult) -> None:
        self.calls += 1
        self.prompt_tokens += r.prompt_tokens
        self.completion_tokens += r.completion_tokens
        self.cost_usd += r.cost_usd()

    def snapshot(self) -> dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }

    def reset(self) -> None:
        self.__init__()


usage = _Usage()


def chat(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    s: Settings = settings,
    **kwargs,
) -> LLMResult:
    """Single chat completion via LiteLLM against an OpenAI-compatible endpoint."""
    import litellm

    model = model or s.model
    t0 = time.time()
    resp = litellm.completion(
        model=f"openai/{model}",
        api_base=s.base_url,
        api_key=s.api_key,
        messages=messages,
        max_tokens=max_tokens or s.max_tokens,
        temperature=s.temperature if temperature is None else temperature,
        **kwargs,
    )
    latency = time.time() - t0
    msg = resp.choices[0].message
    u = resp.usage
    result = LLMResult(
        content=(msg.content or "").strip(),
        reasoning=(getattr(msg, "reasoning_content", None) or "").strip(),
        model=model,
        prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(u, "completion_tokens", 0) or 0,
        latency_s=latency,
    )
    usage.add(result)
    return result


def ping(model: str | None = None) -> bool:
    """Smoke test: confirm the configured model answers. Returns True on success."""
    if not settings.configured:
        print("❌ OPENAI_API_KEY not set (check .claude/.env or .env)")
        return False
    try:
        r = chat(
            [{"role": "user", "content": "Reply with exactly the word: PONG"}],
            model=model,
            max_tokens=300,
        )
    except Exception as e:  # pragma: no cover - network/credential failure path
        print(f"❌ model call failed: {e!r}")
        return False
    ok = "PONG" in r.content.upper()
    print(f"{'✅' if ok else '⚠️'} model={r.model} content={r.content!r} "
          f"latency={r.latency_s:.2f}s tokens(in/out)={r.prompt_tokens}/{r.completion_tokens} "
          f"cost=${r.cost_usd():.6f}")
    return ok


if __name__ == "__main__":  # `python -m retailcare.config --ping`
    import sys

    if "--ping" in sys.argv:
        sys.exit(0 if ping() else 1)
    print(f"base_url={settings.base_url} model={settings.model} "
          f"strong={settings.model_strong} weak={settings.model_weak} "
          f"configured={settings.configured} db={settings.database_url}")
