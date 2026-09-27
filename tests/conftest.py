import json
from pathlib import Path

import pytest

from addp.protocol import timestamp, Validator

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class Clock:
    def __init__(self):
        self.now = timestamp("2030-01-01T00:00:00Z")

    def __call__(self):
        return self.now


@pytest.fixture
def validator():
    return Validator()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def resource():
    return load("valid/resource.json")


@pytest.fixture
def query():
    return load("valid/query.json")
