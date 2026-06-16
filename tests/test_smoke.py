"""M0 smoke tests — no network required (model ping is a separate, gated step)."""
from retailcare import __version__
from retailcare.config import LLMResult, Settings, settings


def test_version():
    assert __version__


def test_settings_defaults():
    s = Settings()
    assert s.base_url.startswith("http")
    assert s.model  # a default model id is always present
    assert s.model_strong and s.model_weak


def test_cost_computation():
    r = LLMResult(
        content="ok", reasoning="", model="x",
        prompt_tokens=1_000_000, completion_tokens=1_000_000, latency_s=0.1,
    )
    expected = settings.price_in_per_m + settings.price_out_per_m
    assert abs(r.cost_usd() - expected) < 1e-9
