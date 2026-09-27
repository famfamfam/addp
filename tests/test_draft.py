"""The draft must not drift from the tested fixtures and measurements."""
import json
import re
import sys

import pytest
from lxml import etree

from addp.protocol import strict_json
from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
from build_draft import EXAMPLES, fold, HEADER, unfold  # noqa: E402

DRAFT = ROOT / "rfc/draft-kibin-addp-00.xml"
XI = "{http://www.w3.org/2001/XInclude}include"


@pytest.fixture(scope="module")
def tree():
    return etree.parse(str(DRAFT), etree.XMLParser(resolve_entities=True, no_network=True))


def test_every_example_is_a_folded_fixture(tree):
    included = {e.get("href") for e in tree.iter(XI) if e.get("parse") == "text"}
    assert included == {f"examples/{name}.json" for name in EXAMPLES}
    for name, source in EXAMPLES.items():
        fixture = (ROOT / source).read_text(encoding="utf-8")
        in_draft = (ROOT / "rfc/examples" / f"{name}.json").read_text(encoding="utf-8")
        assert unfold(in_draft) == fixture.rstrip("\n") + "\n", f"{name}: run tools/build_draft.py"
        assert all(len(line) <= 69 for line in in_draft.splitlines())


def test_inline_json_examples_parse(tree):
    for block in tree.iter("sourcecode"):
        if block.get("type") == "json" and block.text and block.text.strip():
            strict_json(block.text.encode("utf-8"))


def test_folding_round_trip():
    line = '  "sha256": "' + "a" * 64 + '"'
    folded = fold(line + "\n")
    assert folded.startswith(HEADER + "\n\n")
    assert unfold(folded) == line + "\n"
    spaced = "x" * 67 + "  " + "y" * 10
    assert unfold(fold(spaced)) == spaced + "\n"


def test_measurement_table_matches_results(tree):
    results = json.loads((ROOT / "docs/measurements.json").read_text(encoding="utf-8"))
    table = tree.find(".//table[@anchor='tab-measure']")
    rows = [[("".join(td.itertext())).strip() for td in tr.findall("td")] for tr in table.iter("tr")]
    rows = [r for r in rows if r]
    keys = ["result_json_pretty", "result_json_compact", "result_csv_same_data", "decision_view_json_compact"]
    for row, key in zip(rows, keys, strict=True):
        m = results["measurements"][key]
        assert row[1:] == [str(m["utf8_bytes"]), str(m["tokens"]["cl100k_base"]), str(m["tokens"]["o200k_base"])], key


def test_author_and_name(tree):
    text = DRAFT.read_text(encoding="utf-8")
    assert 'fullname="Aleksandr Kibin"' in text
    # "AWP" may appear only in the bibliography entry for the unrelated agent.json project.
    own = re.sub(r'<reference anchor="AGENT-JSON".*?</reference>', "", text, flags=re.S)
    assert not re.search(r"placeholder|editor@example|\bAWP\b|agent-web", own, re.IGNORECASE)
    assert tree.getroot().get("docName") == DRAFT.stem
