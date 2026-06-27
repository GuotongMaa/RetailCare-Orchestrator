"""Injectable clock (C2): deterministic in mock world, real in prod."""
import os
from datetime import datetime, timedelta

import pytest

from retailcare import clock
from retailcare.data.seed import NOW, seed
from retailcare.tools import impl
from retailcare.tools.schema import CheckReturnEligibilityIn


@pytest.fixture(autouse=True)
def _reset_clock():
    yield
    clock.set_now(None)
    os.environ.pop("RETAILCARE_NOW", None)


def test_override_wins():
    dt = datetime(2030, 1, 1)
    clock.set_now(dt)
    assert clock.now() == dt


def test_env_var_used_when_no_override():
    clock.set_now(None)
    os.environ["RETAILCARE_NOW"] = "2029-05-05T00:00:00"
    assert clock.now() == datetime(2029, 5, 5)


def test_falls_back_to_wall_clock():
    clock.set_now(None)
    os.environ.pop("RETAILCARE_NOW", None)
    assert abs((clock.now() - datetime.utcnow()).total_seconds()) < 5


def test_seed_pins_clock_to_seed_epoch():
    seed(reset=True)
    assert clock.now() == NOW


def test_eligibility_flips_when_clock_advances_past_window():
    seed(reset=True)  # pins clock to NOW; I1 returnable_until = NOW + 23d
    e = impl.check_return_eligibility(CheckReturnEligibilityIn(
        user_id="u1", order_id="O1001", item_id="I1", reason="size"))
    assert e.eligible  # in window at seed epoch
    clock.set_now(NOW + timedelta(days=24))  # advance past the window
    e2 = impl.check_return_eligibility(CheckReturnEligibilityIn(
        user_id="u1", order_id="O1001", item_id="I1", reason="size"))
    assert not e2.eligible and e2.reason_code == "out_of_window"
