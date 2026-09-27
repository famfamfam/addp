"""Refresh bibliography entries from bib.ietf.org. Needs network; the build does not."""
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RFCS = [2119, 3339, 3552, 3986, 4648, 6454, 6973, 7493, 8126, 8174, 8259, 8414, 8615, 8693, 8792,
        9110, 9396, 9457, 9728]
# Internet-Drafts are pinned to a revision; bump deliberately when a new one appears.
DRAFTS = ["draft-cui-ai-agent-discovery-invocation-02", "draft-rosenberg-ai-protocols-00"]


def fetch(url, anchor):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(32769)
    if len(data) > 32768:
        raise ValueError("Unexpected bibliography size")
    element = ET.fromstring(data)
    if element.tag != "reference" or element.get("anchor") != anchor:
        raise ValueError(f"Unexpected bibliography entry {anchor}")
    return data


def main():
    directory = ROOT / "rfc/references"
    directory.mkdir(parents=True, exist_ok=True)
    entries = [(f"RFC{n}", f"https://bib.ietf.org/public/rfc/bibxml/reference.RFC.{n}.xml") for n in RFCS]
    for draft in DRAFTS:
        anchor = "I-D." + draft.removeprefix("draft-").rsplit("-", 1)[0]
        entries.append((anchor, f"https://bib.ietf.org/public/rfc/bibxml3/reference.I-D.{draft}.xml"))
    manifest = {}
    for anchor, url in entries:
        data = fetch(url, anchor)
        (directory / f"{anchor}.xml").write_bytes(data)
        manifest[anchor] = {"url": url, "sha256": hashlib.sha256(data).hexdigest()}
    (directory / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Saved {len(manifest)} bibliography entries from bib.ietf.org")


if __name__ == "__main__":
    main()
