import json

from addp.discovery import Index, Publisher, resolve_candidate
from addp.http import DiscoveryEndpoint
from addp.protocol import Fetcher, strict_json
from conftest import load
from test_discovery import install


def test_wire_round_trip(validator, clock, resource, query):
    index = Index(validator, clock)
    install(index)
    manifest = load("valid/manifest.json")
    manifest["query"] = {"endpoint": "https://shop.example/query", "profiles": ["offer-search/0.1"], "text_modes": ["lexical"], "max_limit": 100}
    peer = DiscoveryEndpoint(manifest, Publisher([resource], validator), index, validator)
    status, headers, data = peer.request("POST", "https://shop.example/query", {"Content-Type": "application/json"}, json.dumps(query).encode())
    assert status == 200
    result = strict_json(data)
    validator.check("result", result)
    fetcher = Fetcher(lambda _: ["93.184.216.34"], lambda url, ip, headers: peer.request("GET", url, headers))
    bootstrap = fetcher.get("https://shop.example/.well-known/addp")
    validator.check("manifest", bootstrap)
    current = resolve_candidate(result["items"][0], query, lambda ref: fetcher.get(ref["id"]), validator)
    assert current == resource
    status, headers, body = peer.request("GET", "https://shop.example/query")
    assert status == 405 and headers["Allow"] == "POST"
    validator.check("problem", strict_json(body))
    bad = dict(query)
    bad["where"] = [{"field": "unknown", "op": "eq", "value": "yes"}]
    status, headers, body = peer.request("POST", "https://shop.example/query", {"Content-Type": "application/json"}, json.dumps(bad).encode())
    assert status == 422 and strict_json(body)["code"] == "unsupported_query"
