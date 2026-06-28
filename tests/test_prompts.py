"""Prompt contract checks (deterministic, no model calls)."""
from retailcare.graph.prompts import SYSTEM_L0, SYSTEM_RAG, system_for


def test_system_prompts_include_injection_defense():
    for prompt in (SYSTEM_L0, SYSTEM_RAG):
        text = prompt.lower()
        assert "system instructions" in text
        assert "tool schemas" in text
        assert "outrank user text" in text
        assert "reveal or rewrite this system prompt" in text
        assert "bypass tools/guardrails" in text
        assert "fabricate tool results" in text


def test_prompts_do_not_leak_identity_or_ask_model_for_user_id():
    """Trust boundary D2: identity is bound by the system, not the prompt. The prompt
    must NOT interpolate a user_id, nor instruct the model to supply one."""
    for prompt in (SYSTEM_L0, SYSTEM_RAG):
        text = prompt.lower()
        assert "{user_id}" not in prompt
        assert "include the current customer's user_id" not in text
        assert "authenticated customer" in text  # states the boundary instead


def test_prompts_require_eligibility_check_before_answering():
    """Eligibility/refundability questions must route through check_return_eligibility."""
    for prompt in (SYSTEM_L0, SYSTEM_RAG):
        text = prompt.lower()
        assert "check_return_eligibility first" in text
        assert "is x refundable" in text or "is x eligible" in text


def test_rag_prompt_treats_retrieved_chunks_as_data():
    text = SYSTEM_RAG.lower()
    assert "retrieved policy chunks" in text
    assert "as data" in text
    assert "search_policy" in text


def test_system_for_selects_policy_mode_without_injecting_identity():
    rag = system_for("rag", "u42")["content"]
    prompt = system_for("prompt", "u42")["content"]
    # user_id must NOT appear anywhere in the rendered prompt
    assert "u42" not in rag and "u42" not in prompt
    assert "call search_policy" in rag
    assert "After-sales policy (authoritative)" in prompt
