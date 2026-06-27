"""Fault injection / recovery (deterministic, no model)."""
import pytest

from retailcare.data.seed import seed
from retailcare.tools import faults
from retailcare.tools.recovery import MAX_RETRIES, call_with_recovery


@pytest.fixture(autouse=True)
def _setup():
    seed(reset=True)
    faults.clear()
    yield
    faults.clear()


def test_transient_fault_then_recover():
    faults.inject("get_order", "timeout", times=MAX_RETRIES)  # fail twice, then succeed
    result, err = call_with_recovery("get_order", {"user_id": "u1", "order_id": "O1001"})
    assert err is None
    assert result["order_id"] == "O1001"


def test_permanent_fault_gives_up_and_signals_escalation():
    faults.inject("get_order", "error", times=99)
    result, err = call_with_recovery("get_order", {"user_id": "u1", "order_id": "O1001"})
    assert result is None
    assert "escalate_to_human" in err


def test_stale_data_is_flagged():
    faults.inject("get_order", "stale", times=1)
    result, err = call_with_recovery("get_order", {"user_id": "u1", "order_id": "O1001"})
    assert err is None and result.get("_stale") is True


def test_no_fault_normal_path():
    result, err = call_with_recovery("get_order", {"user_id": "u1", "order_id": "O1001"})
    assert err is None and "_stale" not in result
