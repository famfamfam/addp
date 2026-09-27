import gzip
import json
from pathlib import Path

import pytest

from addp.discovery import check_query
from addp.protocol import Fetcher, MAX_BYTES, ProtocolError, strict_json
from conftest import ROOT, load


@pytest.mark.parametrize("path", sorted((ROOT / "examples/valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid_fixture(path, validator):
    value = strict_json(path.read_bytes())
    validator.check(path.stem, value)
    if path.stem == "query":
        check_query(value, validator)


@pytest.mark.parametrize("path", sorted((ROOT / "examples/invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid_fixture(path, validator):
    case = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(ProtocolError) as error:
        if case["schema"] == "query":
            check_query(case["instance"], validator)
        else:
            validator.check(case["schema"], case["instance"])
    assert error.value.code == case["error"]


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'{"a":NaN}', b'"\xff"', b"[" * 40 + b"0" + b"]" * 40])
def test_strict_json(data):
    with pytest.raises(ProtocolError):
        strict_json(data)


def test_noncritical_extension(validator):
    value = load("valid/manifest.json")
    value["extensions"] = {"https://example.org/display": {"label": "untrusted"}}
    validator.check("manifest", value)


def test_fixed_problem(validator):
    result = ProtocolError("unsupported_query", "secret internal detail").problem()
    validator.check("problem", result)
    assert result["status"] == 422 and "detail" not in result
    assert result["title"] == "Unprocessable Content"  # RFC 9110 phrase on every Python version.


@pytest.mark.parametrize("value", ["garbageZ", "2030-99-99T00:00:00Z", "20300101T000000Z",
                                   "2030-01-01T00:00:00+00:00", "2030-01-01"])
def test_bad_timestamps_rejected_not_crashing(validator, value):
    resource = load("valid/resource.json")
    resource["valid_until"] = value
    with pytest.raises(ProtocolError, match="invalid_message"):
        validator.check("resource", resource)


def test_fractional_seconds_accepted(validator):
    resource = load("valid/resource.json")
    resource["valid_until"] = "2030-01-01T00:00:00.123456789Z"
    validator.check("resource", resource)


@pytest.mark.parametrize("name", ["not a uri", "relative/path", "https://example.org/x#frag"])
def test_extension_names_must_be_absolute_uris(validator, name):
    manifest = load("valid/manifest.json")
    manifest["extensions"] = {name: 1}
    with pytest.raises(ProtocolError, match="invalid_message"):
        validator.check("manifest", manifest)


def test_fetch_pins_ip_and_omits_credentials():
    calls = []
    def transport(url, ip, headers):
        calls.append((url, ip, headers))
        return 200, {"Content-Type": "application/json"}, b'{"ok":true}'
    value = Fetcher(lambda _: ["93.184.216.34"], transport).get("https://shop.example/a")
    assert value == {"ok": True}
    assert calls[0][1:] == ("93.184.216.34", {"Accept": "application/json"})


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fd00::1", "::ffff:127.0.0.1"])
def test_private_destination(ip):
    def never(*args):
        pytest.fail("transport must not be invoked")
    with pytest.raises(ProtocolError, match="forbidden"):
        Fetcher(lambda _: [ip], never).get("https://shop.example/a")


def test_rebinding_on_redirect():
    addresses = iter([["93.184.216.34"], ["127.0.0.1"]])
    calls = []
    def transport(url, ip, headers):
        calls.append(url)
        return 302, {"Location": "/second"}, b""
    with pytest.raises(ProtocolError, match="forbidden"):
        Fetcher(lambda _: next(addresses), transport).get("https://shop.example/first")
    assert len(calls) == 1


def test_cross_origin_redirect():
    with pytest.raises(ProtocolError, match="forbidden"):
        Fetcher(lambda _: ["93.184.216.34"], lambda *args: (302, {"Location": "https://other.example/a"}, b"")).get("https://shop.example/a")


def test_gzip_limits():
    payload = gzip.compress(b"x" * (MAX_BYTES + 1))
    with pytest.raises(ProtocolError, match="limit_exceeded"):
        Fetcher(lambda _: ["93.184.216.34"], lambda *args: (200, {"Content-Type": "application/json", "Content-Encoding": "gzip"}, payload)).get("https://shop.example/a")


def test_oversized_raw():
    with pytest.raises(ProtocolError, match="limit_exceeded"):
        strict_json(b" " * (MAX_BYTES + 1))


@pytest.mark.parametrize("url", ["http://shop.example/a", "https://user:password@shop.example/a", "https://shop.example/a#fragment", "https://shop.example/\nattack"])
def test_invalid_fetch_url(url):
    with pytest.raises(ProtocolError):
        Fetcher(lambda _: ["93.184.216.34"], lambda *args: pytest.fail("not fetched")).get(url)
