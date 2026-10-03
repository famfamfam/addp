"""Check public documents and fixtures without a parent checkout or network."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jsonschema import Draft202012Validator
from tools.generate_schemas import build, MESSAGES
from tools.validation import ROOT, load, validate, semantic, verify, require, instant


def check_links():
    sources = list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md")) + list((ROOT / "examples").glob("*.md"))
    count = 0
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)", text):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target_path = unquote(target.split("#", 1)[0])
            resolved = (path.parent / target_path).resolve()
            require(resolved.is_relative_to(ROOT.resolve()), "link_escapes_package")
            require(resolved.exists(), f"broken_link:{path.relative_to(ROOT)}:{target}")
            require(not ({"notes", "work", ".venv"} & set(resolved.relative_to(ROOT).parts)), "private_link")
            count += 1
    return count


def check_examples():
    schema = load(ROOT / "schemas/0.1/protocol.schema.json")
    Draft202012Validator.check_schema(schema)
    require(schema == build(), "generated_schema_drift")
    cases = load(ROOT / "examples/cases.json")
    kinds = set()
    for name in cases["valid"]:
        d = load(ROOT / "examples" / name)
        validate(d)
        semantic(d)
        kinds.add(d["kind"])
    require(kinds == set(MESSAGES), "missing_message_example")
    for case in cases["signed"]:
        verify(load(ROOT / "examples" / case["file"]), load(ROOT / "examples" / case["key"]), case["role"], instant(case["as_of"]))
    for case in cases["invalid"]:
        d = load(ROOT / "examples" / case["file"])
        if case["stage"] == "semantic":
            validate(d)
        try:
            (validate if case["stage"] == "schema" else semantic)(d)
        except ValueError as exc:
            require(str(exc) == case["error"], f"wrong_error:{case['file']}:{exc}")
        else:
            raise ValueError(f"negative_accepted:{case['file']}")
    listed = set(cases["valid"]) | {c["file"] for c in cases["signed"] + cases["invalid"]}
    actual = {p.relative_to(ROOT / "examples").as_posix() for folder in ["valid", "signed", "invalid"]
              for p in (ROOT / "examples" / folder).glob("*.json")}
    require(listed == actual, "unlisted_or_missing_fixture")
    return len(cases["valid"]), len(cases["signed"]), len(cases["invalid"])


def main():
    valid, signed, invalid = check_examples()
    links = check_links()
    print(f"PASS: {valid} valid documents; {signed} signed documents; {invalid} expected rejections; {links} local links")
    print("Scope: offline document checks only. No live blockchain, checkout or fraud-prevention claim.")


if __name__ == "__main__":
    main()
