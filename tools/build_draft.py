"""Fold example files per RFC 8792 and render the Internet-Draft.

The XML source includes examples from rfc/examples/. Those files are generated
here from examples/, so the draft cannot drift from the tested fixtures.
Rendering runs xml2rfc without network access; references are local files.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DRAFT = "draft-kibin-addp-00"
WIDTH = 69
HEADER = "=============== NOTE: '\\' line wrapping per RFC 8792 ================"
EXAMPLES = {name: f"examples/valid/{name}.json" for name in (
    "manifest", "resource", "head", "part", "delta", "query", "result", "problem",
    "capability", "intent", "quote", "operation")}
EXAMPLES.update({"ucp-profile-subset": "examples/ucp/profile-subset.json",
                 "ucp-search-response": "examples/ucp/search-response.json"})


def fold(text):
    """Single-backslash folding (RFC 8792, Section 7)."""
    lines = text.rstrip("\n").split("\n")
    if all(len(line) <= WIDTH for line in lines):
        return "\n".join(lines) + "\n"
    if any(line.endswith("\\") for line in lines):
        raise ValueError("Line ends in a backslash; the '\\\\' strategy would be required")
    out = [HEADER, ""]
    for line in lines:
        while len(line) > WIDTH:
            cut = WIDTH - 1
            # A continuation line must not start with whitespace: unfolding strips it.
            while cut > 1 and line[cut] in " \t":
                cut -= 1
            out.append(line[:cut] + "\\")
            line = line[cut:]
        out.append(line)
    return "\n".join(out) + "\n"


def unfold(text):
    lines = text.rstrip("\n").split("\n")
    if lines[:2] != [HEADER, ""]:
        return "\n".join(lines) + "\n"
    out, pending = [], None
    for line in lines[2:]:
        if pending is not None:
            line = pending + line.lstrip(" \t")
        if line.endswith("\\"):
            pending = line[:-1]
        else:
            out.append(line)
            pending = None
    if pending is not None:
        raise ValueError("Dangling continuation")
    return "\n".join(out) + "\n"


def write_examples():
    target = ROOT / "rfc/examples"
    target.mkdir(parents=True, exist_ok=True)
    for name, source in EXAMPLES.items():
        text = (ROOT / source).read_text(encoding="utf-8")
        folded = fold(text)
        if unfold(folded) != text.rstrip("\n") + "\n":
            raise ValueError(f"Folding changed {source}")
        (target / f"{name}.json").write_text(folded, encoding="utf-8", newline="\n")


def expand():
    """Resolve XIncludes ourselves; the result is the single file Datatracker accepts."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=True, no_network=True)
    tree = etree.parse(str(ROOT / "rfc" / f"{DRAFT}.xml"), parser)
    tree.xinclude()
    target = ROOT / "build" / f"{DRAFT}.xml"
    tree.write(str(target), xml_declaration=True, encoding="utf-8")
    return target


def render():
    (ROOT / "build").mkdir(exist_ok=True)
    source = expand()
    exe = shutil.which("xml2rfc", path=str(Path(sys.executable).parent)) or "xml2rfc"
    command = [exe, "--no-network", "--path", str(ROOT / "build"), "--text", "--html", str(source)]
    return subprocess.run(command, cwd=ROOT).returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples-only", action="store_true")
    args = parser.parse_args()
    write_examples()
    print(f"Wrote {len(EXAMPLES)} example files to rfc/examples")
    if not args.examples_only:
        sys.exit(render())


if __name__ == "__main__":
    main()
