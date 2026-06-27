"""Trace hygiene: structured logs should preserve business IDs but redact PII/secrets."""
from retailcare.trace.logger import Trace


def test_trace_redacts_common_pii_and_secrets():
    tr = Trace()
    tr.log(
        "message",
        "user",
        text="Email me at customer@example.com or call +1 415-555-1212 about O1001.",
        api_key="sk-real-secret",
        nested={"authorization": "Bearer token", "order_id": "O1001"},
    )

    payload = tr.events[0].payload
    assert "customer@example.com" not in payload["text"]
    assert "+1 415-555-1212" not in payload["text"]
    assert "[REDACTED_EMAIL]" in payload["text"]
    assert "[REDACTED_PHONE]" in payload["text"]
    assert payload["api_key"] == "[REDACTED]"
    assert payload["nested"]["authorization"] == "[REDACTED]"
    assert payload["nested"]["order_id"] == "O1001"
