"""M1 tool-layer tests — no network. Validates contracts, eligibility, idempotency."""
import pytest
from pydantic import ValidationError

from retailcare.data.seed import seed
from retailcare.tools import impl
from retailcare.tools.schema import (
    CheckReturnEligibilityIn,
    CreateReturnRequestIn,
    GetCouponIn,
    GetOrderIn,
    GetShipmentIn,
    IssueCompensationIn,
    SearchPolicyIn,
)


@pytest.fixture(autouse=True)
def _seed():
    seed(reset=True)


# ---- read tools ----

def test_get_order_with_items():
    o = impl.get_order(GetOrderIn(user_id="u1", order_id="O1001"))
    assert o.user_id == "u1"
    assert {i.item_id for i in o.items} == {"I1", "I2"}


def test_get_order_not_found():
    with pytest.raises(impl.ToolError):
        impl.get_order(GetOrderIn(user_id="u1", order_id="NOPE"))


def test_get_order_rejects_cross_user_access():
    with pytest.raises(impl.ToolError, match="not found or not accessible"):
        impl.get_order(GetOrderIn(user_id="u1", order_id="O1002"))


def test_get_shipment_exception_status():
    sh = impl.get_shipment(GetShipmentIn(user_id="u3", order_id="O1003"))
    assert sh.status == "exception"


def test_search_policy_returns_versioned_chunks():
    chunks = impl.search_policy(SearchPolicyIn(query="refund return window"))
    assert chunks and all(c.version for c in chunks)


def test_get_coupon():
    coupons = impl.get_coupon(GetCouponIn(user_id="u1"))
    assert any(c.code == "WELCOME10" and c.status == "active" for c in coupons)


# ---- eligibility ----

def test_eligibility_in_window_ok():
    e = impl.check_return_eligibility(CheckReturnEligibilityIn(
        user_id="u1", order_id="O1001", item_id="I1", reason="size"))
    assert e.eligible and e.reason_code == "ok" and not e.requires_human
    assert e.refund_amount == 29.0


def test_eligibility_non_returnable():
    e = impl.check_return_eligibility(CheckReturnEligibilityIn(
        user_id="u1", order_id="O1001", item_id="I2", reason="changed mind"))
    assert not e.eligible and e.reason_code == "non_returnable_category"


def test_eligibility_out_of_window():
    e = impl.check_return_eligibility(CheckReturnEligibilityIn(
        user_id="u2", order_id="O1002", item_id="I3", reason="broke"))
    assert not e.eligible and e.reason_code == "out_of_window"


def test_eligibility_high_value_requires_human():
    e = impl.check_return_eligibility(CheckReturnEligibilityIn(
        user_id="u2", order_id="O1002", item_id="I4", reason="defective"))
    assert e.eligible and e.requires_human and e.refund_amount >= 200


# ---- write tools: idempotency + validation ----

def test_create_return_request_idempotent_on_order_item():
    a = impl.create_return_request(CreateReturnRequestIn(
        user_id="u1", order_id="O1001", item_id="I1", reason="size", idempotency_key="k1"))
    b = impl.create_return_request(CreateReturnRequestIn(
        user_id="u1", order_id="O1001", item_id="I1", reason="size",
        idempotency_key="k2-different"))
    assert a.ticket_id == b.ticket_id  # deduped on (order_id, item_id), NOT on the key
    assert b.deduped is True


def test_get_order_reflects_return_status_after_ticket():
    # before: no return status
    o = impl.get_order(GetOrderIn(user_id="u1", order_id="O1001"))
    assert all(i.return_status is None for i in o.items)
    # create a return for I1
    impl.create_return_request(CreateReturnRequestIn(
        user_id="u1", order_id="O1001", item_id="I1", reason="wrong size",
        idempotency_key="rs1"))
    # after: I1 shows return_requested, I2 unaffected
    o2 = impl.get_order(GetOrderIn(user_id="u1", order_id="O1001"))
    by_id = {i.item_id: i.return_status for i in o2.items}
    assert by_id["I1"] == "return_requested"
    assert by_id["I2"] is None


def test_create_return_request_rejects_ineligible():
    with pytest.raises(impl.ToolError):
        impl.create_return_request(CreateReturnRequestIn(
            user_id="u1", order_id="O1001", item_id="I2", reason="x", idempotency_key="k3"))


def test_create_return_request_rejects_cross_user_order():
    with pytest.raises(impl.ToolError, match="not found or not accessible"):
        impl.create_return_request(CreateReturnRequestIn(
            user_id="u1", order_id="O1002", item_id="I4", reason="x", idempotency_key="k4"))


def test_write_requires_idempotency_key():
    with pytest.raises(ValidationError):
        CreateReturnRequestIn(user_id="u1", order_id="O1001", item_id="I1",
                              reason="size", idempotency_key="")


def test_issue_compensation_idempotent_on_key():
    a = impl.issue_compensation(IssueCompensationIn(user_id="u1", reason="late", amount=5.0, idempotency_key="comp-1"))
    b = impl.issue_compensation(IssueCompensationIn(user_id="u1", reason="late", amount=5.0, idempotency_key="comp-1"))
    assert a.comp_id == b.comp_id and b.deduped is True
