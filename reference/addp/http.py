"""In-process HTTP boundary for conformance tests; this opens no sockets."""
import json
from urllib.parse import urlsplit

from .protocol import ProtocolError, origin, require, strict_json


class DiscoveryEndpoint:
    def __init__(self, manifest, publisher, index, validator, documents=None):
        validator.check("manifest", manifest)
        self.manifest = manifest
        self.publisher = publisher
        self.index = index
        self.validator = validator
        self.documents = documents or {}

    def request(self, method, url, headers=None, body=b"", principal="public"):
        try:
            require(origin(url) == self.manifest["origin"], "forbidden")
            headers = {k.lower(): v for k, v in (headers or {}).items()}
            if url == self.manifest.get("query", {}).get("endpoint"):
                require(method == "POST", "method_not_allowed")
                require(headers.get("content-type", "").split(";")[0].strip() == "application/json", "unsupported_media_type")
                require(headers.get("content-encoding", "identity") == "identity", "unsupported_media_type")
                value = self.index.query(strict_json(body), principal)
            else:
                require(method == "GET", "method_not_allowed")
                if urlsplit(url).path == "/.well-known/addp" and not urlsplit(url).query:
                    value = self.manifest
                elif url in self.documents:
                    value = self.documents[url]
                else:
                    value = self.publisher.resolve({"publisher": self.manifest["origin"], "namespace": "addp", "id": url})
            return self._response(200, "application/json", value)
        except ProtocolError as error:
            problem = error.problem()
            status, headers, data = self._response(problem["status"], "application/problem+json", problem)
            if status == 405:
                headers["Allow"] = "POST" if url == self.manifest.get("query", {}).get("endpoint") else "GET"
            return status, headers, data

    @staticmethod
    def _response(status, media_type, value):
        data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return status, {"Content-Type": media_type, "Content-Length": str(len(data))}, data
