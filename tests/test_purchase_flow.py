"""The whole path in one place: index, decision view, proposal, re-check, approval, execution.

The model is simulated: it picks a handle from the decision view. Everything
after that is what a host application does with a proposal. Runtime.run() only
executes; the host has to call the discovery checks first, as done here.
"""
import pytest

from addp.discovery import Handles, Index, Publisher, decision_view, resolve_candidate
from addp.execution import Journal, new_operation_id, Runtime, SandboxService
from addp.protocol import ProtocolError
from conftest import load, ROOT
from test_discovery import install

BINDING = ("addp-sandbox", "0.1", "commit")
CAPABILITY = (ROOT / "examples/valid/capability.json").read_bytes()
LOCAL = [{"field": "colour", "op": "eq", "value": "black"}]  # Kept from the index for privacy.


@pytest.fixture
def shop(tmp_path, validator, clock, resource):
    resource["facts"]["colour"] = "black"
    index = Index(validator, clock)
    install(index)
    service = SandboxService(tmp_path / "service.sqlite", validator, clock)
    service.issue("g1", "i7", resource["ref"]["publisher"], "EUR", 35000, clock() + 3600)
    journal = Journal(tmp_path / "journal.sqlite", validator, clock)
    return index, resource, journal, service


def propose(index, query, clock):
    """Query the index, build the decision view, and let the "model" pick the first handle."""
    handles = Handles(clock)
    view = decision_view(index.query(query)["items"], handles, {"index-A": "ok"}, unresolved=["max_total"])
    assert view["items"][0]["delivered_total"] == "unknown"
    return handles.get(view["items"][0]["handle"])


def buy(shop, validator, clock, query, quote=None, **faults):
    index, resource, journal, service = shop
    candidate = propose(index, query, clock)
    current = resolve_candidate(candidate, query, Publisher([resource], validator).resolve, validator, LOCAL)
    intent = load("valid/intent.json")
    assert intent["target"]["ref"] == current["ref"]
    journal.approve(intent, approval_method="test-user-confirmation")  # The user saw `current`.
    quote = quote or load("valid/quote.json")
    service.put_quote(quote)
    operation = new_operation_id()
    state = Runtime(journal, {BINDING: service}).run(operation, intent["id"], quote, "g1", CAPABILITY, **faults)
    return operation, state


def effects(service):
    with service.connect() as db:
        return db.execute("SELECT count(*) FROM effects").fetchone()[0]


def test_find_check_approve_buy(shop, validator, clock, query):
    _, _, journal, service = shop
    _, state = buy(shop, validator, clock, query)
    assert state == "succeeded"
    assert journal.held("i7") == 33399
    assert effects(service) == 1


def test_price_change_within_limits_is_not_an_error(shop, validator, clock, query):
    _, resource, _, service = shop
    resource["facts"]["unit_price_minor"] = 32800  # The index still says 32900.
    resource["revision"] = "r9"
    _, state = buy(shop, validator, clock, query)
    assert state == "succeeded"  # The amount paid is fixed by the quote, not by the index.
    assert effects(service) == 1


@pytest.mark.parametrize("change", ["price-above-limit", "condition", "private-colour", "deleted"])
def test_changed_facts_stop_before_approval(shop, validator, clock, query, change):
    _, resource, journal, service = shop
    resource["revision"] = "r9"
    if change == "price-above-limit":
        resource["facts"]["unit_price_minor"] = 35100
    elif change == "condition":
        resource["facts"]["condition"] = "used"
    elif change == "private-colour":
        resource["facts"]["colour"] = "silver"
    else:
        resource["ref"]["id"] += "-gone"  # The publisher no longer has the candidate.
    with pytest.raises(ProtocolError, match="constraint_failed|not_found"):
        buy(shop, validator, clock, query)
    with journal.connect() as db:
        assert db.execute("SELECT count(*) FROM intents").fetchone()[0] == 0
    assert effects(service) == 0


def test_total_above_limit_stops_before_dispatch(shop, validator, clock, query):
    _, _, journal, service = shop
    quote = load("valid/quote.json")
    quote["total"]["amount_minor"] = 35100  # Item 32900 plus shipping: only the quote shows it.
    with pytest.raises(ProtocolError, match="constraint_failed"):
        buy(shop, validator, clock, query, quote)
    assert journal.held("i7") == 0
    assert effects(service) == 0


def test_lost_response_settles_once(shop, validator, clock, query):
    _, _, journal, service = shop
    operation, state = buy(shop, validator, clock, query, lose_response=True)
    assert state == "unknown"
    restarted = Runtime(Journal(journal.path, validator, clock),
                        {BINDING: SandboxService(service.path, validator, clock)})
    assert restarted.recover(operation) == "succeeded"
    assert restarted.recover(operation, grant_id="g1") == "succeeded"
    assert restarted.journal.held("i7") == 33399
    assert effects(service) == 1
