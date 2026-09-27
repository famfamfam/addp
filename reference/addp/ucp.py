"""Read-only mapping of a pinned UCP catalog subset, not a full UCP implementation."""
from .protocol import CURRENCIES, ProtocolError, origin, require, validate_origin

VERSION = "2026-08-25"
SEARCH = "dev.ucp.shopping.catalog.search"
LOOKUP = "dev.ucp.shopping.catalog.lookup"


class UCPAdapter:
    def __init__(self, publisher, profile, validator):
        validate_origin(publisher)
        self.publisher = publisher
        self.validator = validator
        ucp = profile.get("ucp", {})
        require(ucp.get("version") == VERSION, "unsupported_profile")
        services = ucp.get("services", {}).get("dev.ucp.shopping", [])
        compatible = [s for s in services if s.get("version") == VERSION and s.get("transport") == "rest"]
        require(len(compatible) == 1, "unsupported_profile", "one pinned REST service required")
        self.endpoint = compatible[0]["endpoint"].rstrip("/")
        require(origin(self.endpoint) == publisher, "forbidden")
        capabilities = ucp.get("capabilities", {})
        for name in (SEARCH, LOOKUP):
            require(any(c.get("version") == VERSION for c in capabilities.get(name, [])), "unsupported_profile")

    def search_request(self, text, currency, limit=10):
        # Avoid sending the user's budget. Apply hard constraints after normalization.
        require(isinstance(text, str) and 0 < len(text) <= 512)
        require(currency in CURRENCIES)
        require(type(limit) is int and 1 <= limit <= 100)
        return self.endpoint + "/catalog/search", {
            "query": text, "context": {"currency": currency}, "pagination": {"limit": limit}}

    def lookup_request(self, ref):
        require(ref["publisher"] == self.publisher and ref["namespace"] == "ucp.catalog", "forbidden")
        return self.endpoint + "/catalog/lookup", {"ids": [ref["id"]]}

    def normalize(self, response):
        require(response.get("ucp", {}).get("version") == VERSION, "unsupported_profile")
        require(isinstance(response.get("products"), list))
        resources = []
        seen = set()
        try:
            for product in response["products"]:
                require(isinstance(product["id"], str) and isinstance(product["title"], str))
                for variant in product["variants"]:
                    identifier = variant["id"]
                    require(identifier not in seen, detail="duplicate variant")
                    seen.add(identifier)
                    facts = {"name": variant["title"], "unit_price_minor": variant["price"]["amount"],
                             "currency": variant["price"]["currency"]}
                    available = variant.get("availability", {}).get("available")
                    if type(available) is bool:
                        facts["availability"] = "in_stock" if available else "out_of_stock"
                    resource = {"version": "0.1", "ref": {"publisher": self.publisher, "namespace": "ucp.catalog", "id": identifier},
                                "type": "https://schema.org/Offer", "profile": "offer-search/0.1", "revision": None,
                                "facts": facts, "capabilities": [], "valid_until": None}
                    self.validator.check("resource", resource)
                    resources.append(resource)
        except (KeyError, TypeError) as exc:
            raise ProtocolError("invalid_message", "unsupported UCP catalog shape") from exc
        return resources
