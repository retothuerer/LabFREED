import yaml
from pathlib import Path
import sys

TEMPLATE = """
import pytest # noqa: F401
from labfreed.pac_id import PAC_ID, IDSegment # noqa: F401

def from_url(url):
    return PAC_ID.from_url(url, suppress_validation_errors=True)

{test_class}
"""

def format_identifier_checks(identifier_list):
    checks = []
    for i, seg in enumerate(identifier_list):
        if seg.get("key") is not None:
            checks.append(f"        assert segs[{i}].key == {repr(seg['key'])}")
        else:
            checks.append(f"        assert not segs[{i}].key")
        checks.append(f"        assert segs[{i}].value == {repr(seg['value'])}")
    return "\n".join(checks)

def generate_test_function(name, spec):
    lines = [f"    def test_{name}(self):"]

    if "comment" in spec:
        lines.append(f'        """{spec["comment"]}"""')

    lines.append(f"        pac = from_url({repr(spec['test_url'])})")

    if "is_valid" in spec:
        lines.append(f"        assert pac.is_valid" if spec["is_valid"] else "        assert not pac.is_valid")

    if "issuer" in spec:
        lines.append(f"        assert pac.issuer == {repr(spec['issuer'])}")

    if "to_url" in spec:
        lines.append(f"        assert pac.to_url(use_short_notation=False) == {repr(spec['to_url'])}")

    if "to_url_short" in spec:
        lines.append(f"        assert pac.to_url(use_short_notation=True) == {repr(spec['to_url_short'])}")

    if "identifier" in spec:
        lines.append(f"        segs = pac.identifier")
        lines.append(f"        assert len(segs) == {len(spec['identifier'])}")
        lines.append(format_identifier_checks(spec["identifier"]))

    if "categories" in spec:
        lines.append(f"        cats = pac.categories")
        lines.append(f"        assert len(cats) == {len(spec['categories'])}")
        for i, cat in enumerate(spec["categories"]):
            lines.append(f"        assert cats[{i}].key == {repr(cat['key'])}")
            segments = cat.get("segments", [])
            lines.append(f"        assert len(cats[{i}].segments) == {len(segments)}")
            for j, seg in enumerate(segments):
                if seg.get("key") is not None:
                    lines.append(f"        assert cats[{i}].segments[{j}].key == {repr(seg['key'])}")
                else:
                    lines.append(f"        assert cats[{i}].segments[{j}].key is None")
                lines.append(f"        assert cats[{i}].segments[{j}].value == {repr(seg['value'])}")

    if spec.get("warnings_expected"):
        lines.append(f"        assert len(pac.warnings()) > 0")

    return "\n".join(lines)


def generate_test_class_source(doc):
    class_name = f"Test_{doc.get('name', 'Unnamed').replace('-', '_')}"
    test_defs = doc.get("tests", {})
    test_methods = "\n\n".join(
        generate_test_function(name, spec) for name, spec in test_defs.items()
    )
    return class_name, f"class {class_name}:\n\n{test_methods}"

def main(yaml_path: Path):
    with open(yaml_path, "r") as f:
        docs = list(yaml.safe_load_all(f))

    for doc in docs:
        class_name, test_class_code = generate_test_class_source(doc)
        file_name = f"test_standard_tests_{class_name[4:]}.py"  # strip 'Test' prefix for file
        output_path = yaml_path.parent / file_name
        code = TEMPLATE.format(test_class=test_class_code)
        output_path.write_text(code)
        print(f"✅ Wrote: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        yaml_file = Path(sys.argv[1])
    else:
        yaml_file = Path(__file__).parent / "test_definitions.yaml"

    main(yaml_file)
