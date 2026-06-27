"""Structured-state tests: digest projection, tool effects, idempotency (no model)."""
from retailcare.graph.digest import (
    apply_tool_effect,
    derive_idempotency_key,
    render_digest,
)
from retailcare.graph.state import merge_dict

# ---- merge reducer (D4) ----

def test_merge_dict_accumulates_not_clobbers():
    old = {"I1": {"eligible": True}}
    new = {"I2": {"eligible": False}}
    merged = merge_dict(old, new)
    assert merged == {"I1": {"eligible": True}, "I2": {"eligible": False}}


# ---- idempotency derivation (D3) ----

def test_idempotency_deterministic_and_business_scoped():
    a = derive_idempotency_key("t1", "create_return_request",
                               {"order_id": "O1", "item_id": "I1", "idempotency_key": "x"})
    b = derive_idempotency_key("t1", "create_return_request",
                               {"order_id": "O1", "item_id": "I1", "idempotency_key": "DIFFERENT"})
    c = derive_idempotency_key("t1", "create_return_request",
                               {"order_id": "O1", "item_id": "I2"})
    assert a == b          # model key does not affect it
    assert a != c          # different item -> different key
    assert a.startswith("idem-")


def test_idempotency_compensation_keyed_on_reason_amount():
    a = derive_idempotency_key("t1", "issue_compensation", {"reason": "late", "amount": 5})
    b = derive_idempotency_key("t1", "issue_compensation", {"reason": "Late ", "amount": 5})
    assert a == b  # reason normalised (case/space-insensitive)


def test_idempotency_compensation_amount_int_vs_float_collapse():
    # Regression (QA finding): json.loads("15") -> int, "15.0" -> float; both must
    # map to ONE key or compensation double-pays on retry.
    a = derive_idempotency_key("t1", "issue_compensation", {"reason": "delay", "amount": 15})
    b = derive_idempotency_key("t1", "issue_compensation", {"reason": "delay", "amount": 15.0})
    assert a == b


# ---- tool effects on structured state (D5/D8) ----

def test_effect_sets_intent_and_focus():
    up = apply_tool_effect({}, "get_order", {"order_id": "O1001"},
                           {"order_id": "O1001"}, None)
    assert up["intent"] == "order_status"
    assert up["focus"] == {"order_id": "O1001"}


def test_effect_caches_eligibility_findings():
    up = apply_tool_effect({}, "check_return_eligibility",
                           {"order_id": "O1001", "item_id": "I1", "reason": "size"},
                           {"eligible": True, "refund_amount": 29.0, "requires_human": False,
                            "reason_code": "ok"}, None)
    assert up["findings"]["I1"]["refund_amount"] == 29.0
    assert up["focus"] == {"order_id": "O1001", "item_id": "I1"}


def test_effect_pushes_focus_stack_on_order_change():
    state = {"focus": {"order_id": "O1001", "item_id": "I1"}}
    up = apply_tool_effect(state, "get_shipment", {"order_id": "O1003"},
                           {"order_id": "O1003"}, None)
    assert up["focus"] == {"order_id": "O1003"}
    assert up["focus_stack"][-1] == {"order_id": "O1001", "item_id": "I1"}


def test_effect_no_state_advance_on_error():
    up = apply_tool_effect({}, "get_order", {"order_id": "O1001"}, None, "boom")
    assert up == {}


def test_effect_marks_terminal_status():
    up = apply_tool_effect({}, "create_return_request",
                           {"order_id": "O1001", "item_id": "I1"},
                           {"ticket_id": "T123"}, None)
    assert up["task_status"] == "resolved"
    up2 = apply_tool_effect({}, "escalate_to_human", {}, {"handoff_id": "H1"}, None)
    assert up2["task_status"] == "escalated"


# ---- digest projection (D1/D9) ----

def test_digest_empty_on_empty_state():
    assert render_digest({}) == ""


def test_digest_includes_intent_focus_and_relevant_findings_only():
    state = {
        "intent": "returns",
        "focus": {"order_id": "O1001", "item_id": "I1"},
        "findings": {
            "I1": {"eligible": True, "refund_amount": 29.0, "requires_human": False,
                   "reason_code": "ok"},
            "I9": {"eligible": True, "refund_amount": 80.0, "requires_human": False,
                   "reason_code": "ok"},
        },
        "task_status": "gathering_info",
    }
    d = render_digest(state)
    assert d.startswith("[current_state]")
    assert "intent: returns" in d
    assert "focus: order_id=O1001 item_id=I1" in d
    assert "verified I1" in d
    assert "verified I9" not in d  # only the focused item is shown (D9)


def test_digest_respects_char_cap():
    state = {"intent": "returns", "plan": [{"step": f"s{i}", "status": "todo"} for i in range(500)]}
    assert len(render_digest(state)) <= 1300  # cap (1200) + small marker allowance


def test_digest_shows_prior_order_after_switch():
    state = {"intent": "shipping", "focus": {"order_id": "O1003"},
             "focus_stack": [{"order_id": "O1001", "item_id": "I1"}]}
    d = render_digest(state)
    assert "prior: O1001" in d
